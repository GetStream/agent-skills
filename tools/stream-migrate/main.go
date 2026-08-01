// Command stream-migrate rewrites a Go integration from the legacy
// stream-chat-go SDK to the generated getstream-go SDK.
//
// It is deliberately conservative. Detection is type-aware (go/types decides
// which method on which legacy type is being called, not a regex), rewrites
// come from a fixed mapping table, and any call the table does not cover is
// reported rather than guessed at. The report is the point: it separates what
// was rewritten safely, what was rewritten but changes runtime behavior, what
// needs a human decision, and what was left alone.
//
// Usage:
//
//	go run github.com/GetStream/agent-skills/tools/stream-migrate@latest ./path   # preview
//	go run github.com/GetStream/agent-skills/tools/stream-migrate@latest -w ./path # apply
package main

import (
	"bytes"
	"flag"
	"fmt"
	"go/ast"
	"go/format"
	"go/token"
	"go/types"
	"os"
	"sort"
	"strings"

	"golang.org/x/tools/go/ast/astutil"
	"golang.org/x/tools/go/packages"
)

var (
	legacyPath = "github.com/GetStream/stream-chat-go/v8"
	targetPath = "github.com/GetStream/getstream-go/v5"
)

func main() {
	write := flag.Bool("w", false, "write changes back to source files instead of printing them")
	flag.StringVar(&legacyPath, "legacy", legacyPath, "legacy module path to migrate from")
	flag.StringVar(&targetPath, "target", targetPath, "generated module path to migrate to")
	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "usage: stream-migrate [-w] [dir]\n\n")
		flag.PrintDefaults()
	}
	flag.Parse()

	dir := flag.Arg(0)
	if dir == "" {
		dir = "."
	}
	if err := run(dir, *write); err != nil {
		fmt.Fprintln(os.Stderr, "stream-migrate:", err)
		os.Exit(1)
	}
}

// finding is one classified legacy call site.
type finding struct {
	pos      token.Position
	kind     kind
	name     string
	note     string // why it needs a decision, or why it was not migrated
	behavior string // set when the rewrite changes runtime behavior
}

type kind int

const (
	rewritten kind = iota
	needsDecision
	notMigrated
)

func run(dir string, write bool) error {
	cfg := &packages.Config{
		Mode: packages.NeedName | packages.NeedFiles | packages.NeedCompiledGoFiles |
			packages.NeedSyntax | packages.NeedTypes | packages.NeedTypesInfo |
			packages.NeedImports | packages.NeedDeps,
		Dir: dir,
	}
	pkgs, err := packages.Load(cfg, "./...")
	if err != nil {
		return err
	}
	if packages.PrintErrors(pkgs) > 0 {
		fmt.Fprintln(os.Stderr, "note: the package has build errors; migrating anyway, but verify the result carefully")
	}

	var report []finding
	responseReads := 0
	for _, pkg := range pkgs {
		for _, file := range pkg.Syntax {
			found, changed, reads := migrateFile(pkg, file)
			responseReads += reads
			report = append(report, found...)
			if !changed {
				continue
			}
			if err := fixImports(pkg, file); err != nil {
				return err
			}
			if err := emit(pkg, file, write); err != nil {
				return err
			}
		}
	}
	printReport(os.Stderr, report, responseReads)
	return nil
}

// migrateFile rewrites every covered legacy call in the file and returns what
// it found. Traversal is pre-order and prunes a rewritten subtree, so nested
// calls that a parent rewrite consumes (ban options folded into a request
// struct, for example) are not then reported as uncovered.
func migrateFile(pkg *packages.Package, file *ast.File) ([]finding, bool, int) {
	var found []finding
	changed := false
	responses := map[string]bool{} // variables holding a migrated response
	astutil.Apply(file, func(cur *astutil.Cursor) bool {
		call, ok := cur.Node().(*ast.CallExpr)
		if !ok {
			return true
		}
		m, ok := matchLegacy(pkg.TypesInfo, call)
		if !ok {
			return true
		}
		pos := pkg.Fset.Position(call.Pos())

		r, known := callRules[m.name]
		switch {
		case !known:
			found = append(found, finding{pos: pos, kind: notMigrated, name: m.name,
				note: "the migration guide does not document this operation yet"})
			return true
		case r.review != "":
			found = append(found, finding{pos: pos, kind: needsDecision, name: m.name, note: r.review})
			return true
		}

		replacement := r.build(m.recv, call)
		if replacement == nil {
			found = append(found, finding{pos: pos, kind: needsDecision, name: m.name,
				note: "the call does not match the shape this rule expects, so it needs migrating by hand"})
			return true
		}
		if name, ok := assignedName(cur, call); ok && !r.object {
			responses[name] = true
		}
		cur.Replace(replacement)
		changed = true
		found = append(found, finding{pos: pos, kind: rewritten, name: m.name, behavior: r.behavior})
		return false
	}, nil)

	typeFindings, typesChanged := migrateTypeRefs(pkg, file, found)
	reads := migrateResponseFields(file, responses)
	return append(found, typeFindings...), changed || typesChanged || reads > 0, reads
}

// assignedName returns the variable a rewritten call's result is assigned to,
// so the fields read off it can be moved under Data.
func assignedName(cur *astutil.Cursor, call *ast.CallExpr) (string, bool) {
	assign, ok := cur.Parent().(*ast.AssignStmt)
	if !ok || len(assign.Rhs) != 1 || assign.Rhs[0] != call || len(assign.Lhs) == 0 {
		return "", false
	}
	ident, ok := assign.Lhs[0].(*ast.Ident)
	if !ok || ident.Name == "_" {
		return "", false
	}
	return ident.Name, true
}

// migrateResponseFields moves reads off a migrated response under Data, since
// the generated calls return StreamResponse[T] and the payload the legacy code
// read directly now lives one level down.
func migrateResponseFields(file *ast.File, responses map[string]bool) int {
	if len(responses) == 0 {
		return 0
	}
	count := 0
	astutil.Apply(file, func(cur *astutil.Cursor) bool {
		sel, ok := cur.Node().(*ast.SelectorExpr)
		if !ok {
			return true
		}
		ident, ok := sel.X.(*ast.Ident)
		if !ok || !responses[ident.Name] || sel.Sel.Name == "Data" {
			return true
		}
		cur.Replace(&ast.SelectorExpr{
			X:   &ast.SelectorExpr{X: ast.NewIdent(ident.Name), Sel: ast.NewIdent("Data")},
			Sel: ast.NewIdent(sel.Sel.Name),
		})
		count++
		return false
	}, nil)
	return count
}

// migrateTypeRefs rewrites references to legacy types that survive the call
// pass, such as a client held in a struct field. Rewriting calls alone is not
// enough: the value they are called on has to change type too, or nothing
// compiles. References with no unambiguous mapping are reported instead of
// guessed at.
func migrateTypeRefs(pkg *packages.Package, file *ast.File, existing []finding) ([]finding, bool) {
	var found []finding
	changed := false
	astutil.Apply(file, func(cur *astutil.Cursor) bool {
		sel, ok := cur.Node().(*ast.SelectorExpr)
		if !ok {
			return true
		}
		ident, ok := sel.X.(*ast.Ident)
		if !ok {
			return true
		}
		pkgName, ok := pkg.TypesInfo.Uses[ident].(*types.PkgName)
		if !ok || pkgName.Imported().Path() != legacyPath {
			return true
		}
		if to, ok := typeRewrites[sel.Sel.Name]; ok {
			cur.Replace(&ast.SelectorExpr{X: ast.NewIdent("getstream"), Sel: ast.NewIdent(to)})
			changed = true
			return false
		}
		pos := pkg.Fset.Position(sel.Pos())
		if !reportedAt(existing, pos) {
			found = append(found, finding{pos: pos, kind: needsDecision, name: sel.Sel.Name,
				note: "legacy type reference with no unambiguous equivalent; pick the request or response type the generated SDK uses here"})
		}
		return false
	}, nil)
	return found, changed
}

// reportedAt reports whether a finding already covers this line, so a call that
// was reported does not get reported again for each legacy type in its arguments.
func reportedAt(existing []finding, pos token.Position) bool {
	for _, f := range existing {
		if f.pos.Filename == pos.Filename && f.pos.Line == pos.Line {
			return true
		}
	}
	return false
}

// match is a legacy call site: the method name plus its receiver, if any.
type match struct {
	name string
	recv ast.Expr // nil for package-level functions such as NewClient
}

// matchLegacy reports whether the call targets the legacy SDK, using type
// information rather than the spelling of the identifier.
func matchLegacy(info *types.Info, call *ast.CallExpr) (match, bool) {
	sel, ok := call.Fun.(*ast.SelectorExpr)
	if !ok {
		return match{}, false
	}
	// Package-level function, for example stream.NewClient(...).
	if ident, ok := sel.X.(*ast.Ident); ok {
		if pkgName, ok := info.Uses[ident].(*types.PkgName); ok {
			if pkgName.Imported().Path() == legacyPath {
				return match{name: sel.Sel.Name}, true
			}
			return match{}, false
		}
	}
	// Method on a legacy type, for example client.UpsertUser(...).
	if s, ok := info.Selections[sel]; ok && s.Kind() == types.MethodVal {
		if pkgPath(s.Recv()) == legacyPath {
			return match{name: sel.Sel.Name, recv: sel.X}, true
		}
	}
	return match{}, false
}

func pkgPath(t types.Type) string {
	if p, ok := t.(*types.Pointer); ok {
		t = p.Elem()
	}
	named, ok := t.(*types.Named)
	if !ok || named.Obj().Pkg() == nil {
		return ""
	}
	return named.Obj().Pkg().Path()
}

// fixImports adds the target import, and drops the legacy one only when no
// reference to it survived the rewrite. A partially migrated file keeps both
// so that it still compiles.
func fixImports(pkg *packages.Package, file *ast.File) error {
	alias, ok := legacyAlias(file)
	if !ok {
		return nil
	}
	astutil.AddImport(pkg.Fset, file, targetPath)
	if !referencesPkg(file, alias) {
		astutil.DeleteNamedImport(pkg.Fset, file, importName(file), legacyPath)
	}
	return nil
}

// legacyAlias returns the identifier the file uses for the legacy package.
func legacyAlias(file *ast.File) (string, bool) {
	for _, imp := range file.Imports {
		if strings.Trim(imp.Path.Value, `"`) != legacyPath {
			continue
		}
		if imp.Name != nil {
			return imp.Name.Name, true
		}
		return "stream_chat", true // the legacy package's own name
	}
	return "", false
}

// importName returns the explicit import alias, or "" when the import is
// unnamed, which is the form astutil.DeleteNamedImport expects.
func importName(file *ast.File) string {
	for _, imp := range file.Imports {
		if strings.Trim(imp.Path.Value, `"`) == legacyPath && imp.Name != nil {
			return imp.Name.Name
		}
	}
	return ""
}

// referencesPkg reports whether any qualified reference to the given package
// identifier remains, for example a leftover stream.Message type.
func referencesPkg(file *ast.File, alias string) bool {
	found := false
	ast.Inspect(file, func(n ast.Node) bool {
		sel, ok := n.(*ast.SelectorExpr)
		if !ok {
			return true
		}
		if ident, ok := sel.X.(*ast.Ident); ok && ident.Name == alias {
			found = true
			return false
		}
		return true
	})
	return found
}

func emit(pkg *packages.Package, file *ast.File, write bool) error {
	var buf bytes.Buffer
	if err := format.Node(&buf, pkg.Fset, file); err != nil {
		return err
	}
	src, err := format.Source(buf.Bytes())
	if err != nil {
		src = buf.Bytes() // still emit, so the result can be inspected
	}
	name := pkg.Fset.File(file.Pos()).Name()
	if !write {
		fmt.Printf("// ==== %s ====\n%s\n", name, src)
		return nil
	}
	return os.WriteFile(name, src, 0o644)
}

// printReport groups findings the way someone deciding whether to ship the
// migration needs them, rather than in source order.
func printReport(w *os.File, report []finding, responseReads int) {
	var safe, behavioral, decide, manual []finding
	for _, f := range report {
		switch {
		case f.kind == rewritten && f.behavior == "":
			safe = append(safe, f)
		case f.kind == rewritten:
			behavioral = append(behavioral, f)
		case f.kind == needsDecision:
			decide = append(decide, f)
		default:
			manual = append(manual, f)
		}
	}

	fmt.Fprintln(w, "\n================ migration report ================")
	section(w, "APPLIED, SAFE: mechanical, no behavior change", safe, false)
	section(w, "APPLIED, BEHAVIOR CHANGED: read these before shipping", behavioral, true)
	section(w, "NEEDS A DECISION: not rewritten, finish by hand", decide, true)
	section(w, "NOT MIGRATED: no mapping, left untouched", manual, true)

	if responseReads > 0 {
		fmt.Fprintf(w, "\nRESPONSE READS MOVED UNDER Data: %d\n", responseReads)
		fmt.Fprintln(w, "      The generated calls return a response envelope, so reads were moved from")
		fmt.Fprintln(w, "      resp.Field to resp.Data.Field. Where the payload field itself also changed,")
		fmt.Fprintln(w, "      for example a single User becoming a Users map, the read needs adjusting by")
		fmt.Fprintln(w, "      hand; the compiler will point at those.")
	}

	fmt.Fprintf(w, "\n%d safe, %d behavior changed, %d need a decision, %d not migrated\n",
		len(safe), len(behavioral), len(decide), len(manual))
	if len(behavioral)+len(decide)+len(manual) > 0 {
		fmt.Fprintln(w, "verify with: go build ./... && go vet ./...")
	}
}

func section(w *os.File, title string, items []finding, withNotes bool) {
	fmt.Fprintf(w, "\n%s: %d\n", title, len(items))
	sort.Slice(items, func(i, j int) bool {
		if items[i].pos.Filename != items[j].pos.Filename {
			return items[i].pos.Filename < items[j].pos.Filename
		}
		return items[i].pos.Line < items[j].pos.Line
	})
	for _, f := range items {
		fmt.Fprintf(w, "  - %-22s %s:%d\n", f.name, filepath(f.pos.Filename), f.pos.Line)
		if !withNotes {
			continue
		}
		for _, note := range []string{f.note, f.behavior} {
			if note != "" {
				fmt.Fprintf(w, "      %s\n", note)
			}
		}
	}
}

func filepath(p string) string {
	if i := strings.LastIndex(p, "/"); i >= 0 {
		return p[i+1:]
	}
	return p
}
