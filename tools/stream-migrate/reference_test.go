package main

import (
	"os"
	"strings"
	"testing"
)

// referencePath is the Go symbol reference the skill actually uses. This tool
// is not shipped, so its only lasting job is keeping that document honest.
const referencePath = "../../skills/stream-backend/references/go.md"

// TestReferenceDocumentsEveryImplementedMapping guards against the drift that
// matters: a mapping verified here but missing from the reference is knowledge
// the skill cannot use, since the skill never sees this tool.
func TestReferenceDocumentsEveryImplementedMapping(t *testing.T) {
	raw, err := os.ReadFile(referencePath)
	if err != nil {
		t.Fatalf("read %s: %v", referencePath, err)
	}
	doc := string(raw)

	for name, r := range callRules {
		if r.build == nil {
			continue // decision-only rules carry their explanation in the report
		}
		if !strings.Contains(doc, name) {
			t.Errorf("%s is implemented and verified here but absent from %s, so the skill has no way to know about it",
				name, referencePath)
		}
	}
}

// TestReferenceFlagsTheBehaviorChanges checks that operations known to change
// runtime behavior are marked as such where a reader will see them. These are
// the ones that compile clean and still break production.
func TestReferenceFlagsTheBehaviorChanges(t *testing.T) {
	raw, err := os.ReadFile(referencePath)
	if err != nil {
		t.Fatalf("read %s: %v", referencePath, err)
	}
	doc := string(raw)

	for name, r := range callRules {
		if r.behavior == "" {
			continue
		}
		line := lineContaining(doc, name)
		if line == "" {
			continue // covered by the previous test
		}
		if !strings.Contains(line, "Behavior") {
			t.Errorf("%s changes runtime behavior but its row in the reference does not say so: %s", name, line)
		}
	}
}

func lineContaining(doc, needle string) string {
	for _, line := range strings.Split(doc, "\n") {
		if strings.Contains(line, "`"+needle+"(") {
			return line
		}
	}
	return ""
}
