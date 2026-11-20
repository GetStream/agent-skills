# Recon script

This plugin does not ship the recon script as code. When an audit starts, write
the script below to a scratch directory outside the audited repository, run it
from there with `bash`, and delete it when the audit ends. Do not commit it, and
do not write it into the skill directory or the audited repository.

To copy it exactly, extract the fenced block instead of retyping it:

```bash
umask 077
awk '/^````bash$/{f=1;next} /^````$/{f=0} f' <path-to>/recon.md > <scratch>/recon.sh
bash <scratch>/recon.sh <repo> [--untracked] [--include-tests] [--history] > <scratch>/recon-output.md
```

What it does:

- Read-only. It runs `git` read commands, `grep` and `perl` on the repository and
  prints Markdown to stdout. It fetches nothing and runs no build.
- Section 0 records the scope: remote, commit, worktree state, submodules, LFS
  and resolution files.
- Section 1 inventories languages, manifests, vendored and native code,
  executables and binaries, build plugins and install scripts, distribution
  channels, CI files and sensitive file names.
- Section 2 lists pattern leads labelled with catalog IDs from
  references/checklist.md. It includes a table of every JWT in the repository,
  with the algorithm, the claim names and the expiry, but never the signature.
- Section 3 covers CI and supply chain. Section 4 lists resolved dependency
  versions, and the advisory commands to run for each ecosystem. It doesn't run
  them, because they send package names to public databases.
- `--history` also searches git history for secrets, secret-looking assignments,
  deleted sensitive files and JWTs. It skips refs with unreadable objects and
  names them.
- Secret values are masked as a prefix, the length and a sha256 fingerprint,
  unless you pass `--show-secret-values`. Don't use that flag when the output
  goes into notes or a report.
- Exit status: 0 complete, 2 usage error, 3 some searches failed. The output
  ends with a status line that names what was skipped.

Every hit is a lead to triage, not a finding.

````bash
# Attack-surface recon for an SDK repository. Read-only. Prints Markdown to stdout.
#
# Usage: recon.sh [repo-path] [--untracked] [--include-tests] [--history]
#                 [--show-secret-values] [--max N]
#   --untracked           also search untracked (not ignored) files; by default only
#                         tracked files are searched, as they are in the working tree
#   --include-tests       also search test, fixture and mock paths for pattern leads
#                         (secret search always includes them)
#   --history             also search git history for high-confidence secrets and JWTs
#                         (slow on long histories: minutes)
#   --show-secret-values  print matched secret values in full (default: masked as
#                         prefix + length + sha256 fingerprint)
#   --max N               hits shown per pattern (default 25); counts are always complete
#
# Every hit is a lead, not a finding: read the code before reporting anything.
# Exit status: 0 complete, 2 usage error, 3 some searches failed (see the end of the output).
# Works with bash 3.2 (macOS) and GNU/BSD userlands; needs git (optional) and perl.

umask 077

REPO=""
INCLUDE_TESTS=0
HISTORY=0
UNTRACKED=0
SHOW_SECRETS=0
MAX=25

usage() { sed -n '1,17p' "$0"; }
die_usage() { echo "recon.sh: $1" >&2; echo "Run with --help for usage." >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --include-tests) INCLUDE_TESTS=1 ;;
    --history) HISTORY=1 ;;
    --untracked) UNTRACKED=1 ;;
    --show-secret-values) SHOW_SECRETS=1 ;;
    --max)
      [ $# -ge 2 ] || die_usage "--max needs a value"
      shift
      case "$1" in ''|*[!0-9]*) die_usage "--max must be a positive integer, got '$1'" ;; esac
      [ "$1" -gt 0 ] || die_usage "--max must be a positive integer, got '$1'"
      MAX="$1" ;;
    -h|--help) usage; exit 0 ;;
    -*) die_usage "unknown option '$1'" ;;
    *) [ -z "$REPO" ] || die_usage "more than one repository path given"; REPO="$1" ;;
  esac
  shift
done
[ -n "$REPO" ] || REPO="."
cd "$REPO" 2>/dev/null || die_usage "cannot cd to '$REPO'"
command -v perl >/dev/null 2>&1 || die_usage "perl is required (for secret masking)"

WORK=$(mktemp -d 2>/dev/null || mktemp -d -t recon) || { echo "recon.sh: cannot create a temp dir" >&2; exit 3; }
trap 'rm -rf "$WORK"' EXIT
trap 'rm -rf "$WORK"; exit 130' HUP INT TERM
ERRORS="$WORK/errors"
: > "$ERRORS"
note_error() { echo "$1" >> "$ERRORS"; }

USE_GIT=0
if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then USE_GIT=1; fi

# Paths that never ship or are pure noise.
NOISE_DIRS="node_modules Pods Carthage .build build DerivedData derived_data .gradle .dart_tool out coverage .next vendor/bundle spm_cache .swiftpm"
TEST_GLOBS="**/Tests/** **/tests/** **/test/** **/__tests__/** **/*Tests/** **/*Tests*/** **/*Test/** **/TestTools/** **/*TestTools*/** **/*Mock*/** **/Mocks/** **/mocks/** **/androidTest/** **/testFixtures/** **/fixtures/** **/Fixtures/** **/__Snapshots__/** **/__snapshots__/** **/*.snap **/spec/** **/*_test.go **/*.test.* **/*.spec.*"
# Excluded from general leads only; each gets a focused check below.
FOCUSED_GLOBS="**/*.min.js **/*.map **/*.lock **/package-lock.json **/*.pbxproj **/*.svg"

NOISE_EXCLUDES=()
for d in $NOISE_DIRS; do NOISE_EXCLUDES+=(":(exclude,glob)**/$d/**"); done
LEAD_EXCLUDES=("${NOISE_EXCLUDES[@]}")
if [ "$INCLUDE_TESTS" -eq 0 ]; then
  for g in $TEST_GLOBS; do LEAD_EXCLUDES+=(":(exclude,glob)$g"); done
fi
for g in $FOCUSED_GLOBS; do LEAD_EXCLUDES+=(":(exclude,glob)$g"); done

GREP_NOISE=()
for d in $NOISE_DIRS .git; do GREP_NOISE+=("--exclude-dir=$(basename "$d")"); done
GREP_LEAD=("${GREP_NOISE[@]}")
if [ "$INCLUDE_TESTS" -eq 0 ]; then
  for d in Tests tests test __tests__ androidTest testFixtures fixtures Fixtures __Snapshots__ __snapshots__ spec TestTools Mocks mocks; do GREP_LEAD+=("--exclude-dir=$d"); done
fi
GREP_LEAD+=("--exclude=*.min.js" "--exclude=*.map" "--exclude=*.lock" "--exclude=package-lock.json" "--exclude=*.pbxproj" "--exclude=*.svg")

GIT_GREP_FLAGS=()
[ "$UNTRACKED" -eq 1 ] && GIT_GREP_FLAGS+=("--untracked")

# search <scope: lead|all> <grep-flags> <regex>  -> path:line:text
search() {
  local scope="$1" flags="$2" re="$3" rc
  if [ "$USE_GIT" -eq 1 ]; then
    if [ "$scope" = all ]; then
      git grep "${GIT_GREP_FLAGS[@]}" -nIE $flags -e "$re" -- . "${NOISE_EXCLUDES[@]}" 2>>"$WORK/stderr"
    else
      git grep "${GIT_GREP_FLAGS[@]}" -nIE $flags -e "$re" -- . "${LEAD_EXCLUDES[@]}" 2>>"$WORK/stderr"
    fi
    rc=$?
  else
    if [ "$scope" = all ]; then
      grep -rnIE $flags "${GREP_NOISE[@]}" -e "$re" . 2>>"$WORK/stderr" | sed 's|^\./||'
    else
      grep -rnIE $flags "${GREP_LEAD[@]}" -e "$re" . 2>>"$WORK/stderr" | sed 's|^\./||'
    fi
    rc=${PIPESTATUS[0]}
  fi
  [ "$rc" -le 1 ] || note_error "search failed (exit $rc): ${re:0:80}"
  return 0
}

# High-confidence credential formats: AWS, Google, Slack, GitHub, GitLab, Stripe, Anthropic, OpenAI,
# Hugging Face, npm, PyPI, SendGrid, FCM legacy server keys, Google OAuth client secrets, Shopify,
# Slack and Discord webhooks. Valid as both POSIX ERE and Perl.
PROVIDER_RE='AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|xox[abposr]-[0-9A-Za-z-]{10,}|gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,}|glpat-[A-Za-z0-9_-]{20,}|sk_live_[0-9A-Za-z]{16,}|rk_live_[0-9A-Za-z]{16,}|sk_test_[0-9A-Za-z]{16,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-(proj-)?[A-Za-z0-9_-]{32,}|hf_[A-Za-z0-9]{34}|npm_[A-Za-z0-9]{36}|pypi-AgE[A-Za-z0-9_-]{50,}|SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}|AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{100,}|GOCSPX-[A-Za-z0-9_-]{28}|shpat_[a-fA-F0-9]{32}|hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+|discord(app)?\.com/api/webhooks/[0-9]+/[A-Za-z0-9_-]+'
export PROVIDER_RE

# Masks secret values: prefix(4) + length + sha256 fingerprint(8).
mask() {
  if [ "$SHOW_SECRETS" -eq 1 ]; then cat; return; fi
  perl -MDigest::SHA=sha256_hex -pe '
    BEGIN { $P = qr/$ENV{PROVIDER_RE}/; }
    sub fp { my $v = shift; return substr($v, 0, 4) . "...[masked len=" . length($v) . " sha256:" . substr(sha256_hex($v), 0, 8) . "]"; }
    s/(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})/fp($1)/ge;
    s/((?:_authToken|_auth|_password)\s*=\s*)(\S{8,})/$1 . fp($2)/ge;
    s{([a-z][a-z0-9+.-]*://[^/\s:@"\x27\$\\(){}]+:)([^/\s:@"\x27\$\\(){}]{3,})(@)}{$1 . fp($2) . $3}ge;
    s/($P)/fp($1)/ge;
    s/((?i:api[_-]?secret|client[_-]?secret|secret[_-]?key|private[_-]?key|signing[_-]?key|password|passwd|secret|token)["\x27]?\s*[:=]\s*["\x27])([^"\x27\s]{8,})(["\x27])/$1 . fp($2) . $3/ge;
    s/(-----BEGIN ([A-Z]+ )?PRIVATE KEY-----).*/$1 [key body not shown]/;
  '
}

# emit <title>  (hits on stdin)
emit() {
  local title="$1" tmp count
  tmp="$WORK/emit.$$.$RANDOM"
  mask > "$tmp"
  count=$(grep -c . "$tmp" | tr -d ' ')
  if [ "$count" -gt 0 ]; then
    echo "#### $title - $count hit(s)"
    echo '```'
    head -n "$MAX" "$tmp" | cut -c1-240
    if [ "$count" -gt "$MAX" ]; then
      echo "... ($((count - MAX)) more; top files:)"
      cut -d: -f1 "$tmp" | sort | uniq -c | sort -rn | head -8
    fi
    echo '```'
    echo
  fi
  rm -f "$tmp"
}

# s <title> <regex> [extra grep flags] [filter-out regex]   (general leads)
s() {
  local title="$1" re="$2" flags="${3:-}" drop="${4:-}"
  if [ -n "$drop" ]; then
    search lead "$flags" "$re" | grep -vE "$drop" | emit "$title"
  else
    search lead "$flags" "$re" | emit "$title"
  fi
}
# sa: same, over all files except build noise (tests, minified code, maps, project files included)
sa() {
  local title="$1" re="$2" flags="${3:-}" drop="${4:-}"
  if [ -n "$drop" ]; then
    search all "$flags" "$re" | grep -vE "$drop" | emit "$title"
  else
    search all "$flags" "$re" | emit "$title"
  fi
}

# NUL-safe file listing, printed one per line (paths with newlines are not supported)
list_files() {
  if [ "$USE_GIT" -eq 1 ]; then
    if [ "$UNTRACKED" -eq 1 ]; then
      git ls-files -z --cached --others --exclude-standard | tr '\0' '\n'
    else
      git ls-files -z | tr '\0' '\n'
    fi
  else
    find . -type f -not -path './.git/*' | sed 's|^\./||'
  fi
}
FILES="$WORK/files"
list_files | grep -vE '(^|/)(node_modules|Pods|Carthage|\.build|DerivedData|\.gradle|\.dart_tool|spm_cache)/' > "$FILES"

echo "# Recon: $(basename "$(pwd)")"
echo
echo "## 0. Scope record"
echo
if [ "$USE_GIT" -eq 1 ]; then
  echo "- Remote: $(git remote get-url origin 2>/dev/null | sed -E 's#(https?://)[^/@]+@#\1#' || echo none)"
  echo "- Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null); Commit: $(git rev-parse HEAD 2>/dev/null); Committed: $(git log -1 --format=%cI 2>/dev/null)"
  MODIFIED=$(git status --porcelain --untracked-files=no 2>/dev/null | grep -c .)
  UNTRACKED_N=$(git ls-files --others --exclude-standard 2>/dev/null | grep -c .)
  echo "- Worktree: $MODIFIED modified tracked file(s), $UNTRACKED_N untracked file(s) (not ignored)"
  if [ "$MODIFIED" -gt 0 ] || [ "$UNTRACKED_N" -gt 0 ]; then
    echo "  - WARNING: the worktree is not clean. Searches read tracked files as they are on disk (uncommitted edits included)$([ "$UNTRACKED" -eq 1 ] && echo ' plus untracked files' || echo '; untracked files are NOT searched (use --untracked)'). Decide whether the audit covers HEAD or the worktree, and say so in the report."
    git status --porcelain 2>/dev/null | head -15 | sed 's/^/    /'
  fi
  if [ -f .gitmodules ]; then
    echo "- Submodules:"; git submodule status 2>/dev/null | head -20 | sed 's/^/    /'
  else
    echo "- Submodules: none"
  fi
  if grep -qs 'filter=lfs' .gitattributes; then
    echo "- Git LFS: used ($(grep -c 'filter=lfs' .gitattributes) pattern(s)); $(command -v git-lfs >/dev/null 2>&1 && echo "$(git lfs ls-files 2>/dev/null | grep -c .) LFS file(s)" || echo 'git-lfs not installed: LFS contents may be pointer files')"
  else
    echo "- Git LFS: not used"
  fi
else
  echo "- Not a git work tree: searching all files under $(pwd)"
fi
echo "- Searched: $([ "$USE_GIT" -eq 1 ] && echo "git-tracked files$([ "$UNTRACKED" -eq 1 ] && echo ' + untracked')" || echo 'all files'); tests in pattern leads: $([ "$INCLUDE_TESTS" -eq 1 ] && echo yes || echo no); secret values: $([ "$SHOW_SECRETS" -eq 1 ] && echo SHOWN || echo masked); hits per pattern: $MAX"
LOCK_RE='(^|/)(Package\.resolved|Podfile\.lock|Cartfile\.resolved|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lockb?|pubspec\.lock|go\.sum|poetry\.lock|Pipfile\.lock|uv\.lock|Gemfile\.lock|Cargo\.lock|composer\.lock|packages\.lock\.json|gradle\.lockfile)$'
echo "- Resolution / lock files:"
grep -E "$LOCK_RE" "$FILES" | head -20 | sed 's/^/    /'
if [ "$USE_GIT" -eq 1 ]; then
  git ls-files -z --others --ignored --exclude-standard --directory 2>/dev/null | tr '\0' '\n' | grep -E "$LOCK_RE" | grep -vE '(^|/)(node_modules|Pods|\.build|DerivedData|spm_cache)/' | head -10 | sed 's/^/    (gitignored: a local resolution, not pinned by the repo) /'
fi
echo

echo "## 1. Inventory"
echo
echo "### Languages (files by extension)"
echo '```'
grep -E '\.[A-Za-z0-9]+$' "$FILES" | sed -E 's/.*\.([A-Za-z0-9]+)$/\1/' | sort | uniq -c | sort -rn | head -15
echo '```'
echo
echo "### Manifests"
echo '```'
grep -E '(^|/)(Package\.swift|Podfile|[^/]+\.podspec|Cartfile|build\.gradle(\.kts)?|settings\.gradle(\.kts)?|libs\.versions\.toml|gradle-wrapper\.properties|package\.json|pubspec\.yaml|go\.mod|requirements[^/]*\.txt|pyproject\.toml|Pipfile|setup\.py|setup\.cfg|Gemfile|[^/]+\.gemspec|[^/]+\.csproj|packages\.config|Directory\.Packages\.props|Cargo\.toml|composer\.json|CMakeLists\.txt|vcpkg\.json|conanfile\.(txt|py))$' "$FILES" | head -60
echo '```'
echo
echo "### [NATIVE-01, SUPPLY-03] Likely vendored / third-party code (heuristic: confirm from docs, update scripts and licence files)"
echo '```'
{
  grep -iE '(^|/)(LICEN[CS]E|COPYING)(\.[a-z]+)?$' "$FILES" | grep -vE '^(LICEN[CS]E|COPYING)' | sed 's|/[^/]*$||'
  grep -iE '(^|/)(vendor|vendored|third[_-]?party|external|extern|deps)/' "$FILES" | awk -F/ '{for(i=1;i<=NF;i++) if (tolower($i) ~ /^(vendor|vendored|third[_-]?party|external|extern|deps)$/) {o=$1; for(j=2;j<=i+1&&j<=NF;j++) o=o"/"$j; print o; break}}'
} | sort -u | head -30
echo "# directories whose source files carry third-party licence headers:"
search lead "-l" 'Permission is hereby granted, free of charge|Licensed under the Apache License|SPDX-License-Identifier|Redistribution and use in source and binary forms|GNU (Lesser )?General Public License' | grep -vE '(^|/)(LICEN[CS]E|COPYING|NOTICE)[^/]*$' | awk -F/ 'NF>2{print $1"/"$2"/"$3; next} {print $1"/"$2}' | sort | uniq -c | sort -rn | head -15
echo "# vendoring mentioned in docs and build files:"
if [ "$USE_GIT" -eq 1 ]; then
  git grep -nIiE 'vendor(ed|ing)|third[- ]party|do not edit|update_[a-z]+ version' -- '*.md' 'Makefile' '*.mk' '*.txt' ':(exclude)CHANGELOG.md' ':(exclude,glob)**/CHANGELOG*' 2>/dev/null | cut -c1-200 | head -15
fi
echo "# C/C++/ObjC/assembly source files per top-level directory (native code surface):"
grep -E '\.(c|cc|cpp|cxx|h|hpp|m|mm|s|S)$' "$FILES" | awk -F/ '{print (NF<3 ? $1 : $1"/"$2)}' | sort | uniq -c | sort -rn | head -10
echo '```'
echo
echo "### [SUPPLY-02, SUPPLY-04, SUPPLY-12] Executed or opaque content (symlinks, executables, binaries, build plugins, install scripts)"
echo '```'
if [ "$USE_GIT" -eq 1 ]; then
  echo "# symlinks:"; git ls-files -s 2>/dev/null | awk '$1=="120000"{sub(/^[^\t]*\t/,""); print}' | head -10
  echo "# executable files: $(git ls-files -s 2>/dev/null | awk '$1=="100755"' | grep -c .)"; git ls-files -s 2>/dev/null | awk '$1=="100755"{sub(/^[^\t]*\t/,""); print}' | head -15
fi
echo "# binary artifacts and binary dependencies:"
grep -iE '\.(xcframework|framework|a|so|dylib|dll|jar|aar|wasm|node|bundle)(/|$)' "$FILES" | sed -E 's#(\.(xcframework|framework|bundle))/.*#\1#' | sort -u | head -15
search all "" '\.binaryTarget\(|vendored_frameworks|vendored_libraries|prebuilt|\.xcframework' | grep -E '^[^:]*(Package\.swift|\.podspec|build\.gradle(\.kts)?|package\.json|CMakeLists\.txt):' | head -10
echo "# build plugins, codegen and install-time scripts:"
search all "" '\.plugin\(|\.buildTool\(|\.prebuildCommand\(|script_phases|prepare_command|"(pre|post)?install"[[:space:]]*:|"prepare"[[:space:]]*:|"prepublish(Only)?"[[:space:]]*:|cmdclass|build_ext' | grep -E '^[^:]*(Package\.swift|\.podspec|package\.json|setup\.py|pyproject\.toml|build\.gradle(\.kts)?):' | head -15
grep -E '(^|/)(build\.rs|buildSrc/|binding\.gyp)' "$FILES" | head -5
echo '```'
echo
echo "### [DIST-01, DIST-02, DIST-05] Distribution channels and products (build or dry-run each, then compare with scope)"
echo '```'
grep -qE '(^|/)Package\.swift$' "$FILES" && {
  echo "# SwiftPM: swift package describe --type json   (products, targets, resources)"
  echo "  products: $(perl -0ne 'my @n = /\.(?:library|executable|plugin)\(\s*name:\s*"([^"]+)"/g; print join(", ", @n)' Package.swift 2>/dev/null)"
  echo "  test-support-looking products: $(perl -0ne 'my @n = grep { /Test|Mock|Fixture|Stub/ } /\.library\(\s*name:\s*"([^"]+)"/g; print @n ? join(", ", @n) : "none"' Package.swift 2>/dev/null)"
  echo "  resources declared: $(grep -cE '\.process\(|\.copy\(' Package.swift 2>/dev/null) ($(grep -oE '\.(process|copy)\("[^"]+"\)' Package.swift 2>/dev/null | tr '\n' ' '))"
}
grep -E '\.podspec$' "$FILES" | head -5 | while IFS= read -r f; do echo "# CocoaPods: pod ipc spec '$f'   (resource_bundles, vendored_frameworks, script_phases)"; done
grep -qE '(^|/)package\.json$' "$FILES" && echo "# npm: npm pack --dry-run   (per package; compare with 'files', .npmignore, dist/)"
grep -qE '(^|/)build\.gradle(\.kts)?$' "$FILES" && echo "# Android/JVM: ./gradlew assembleRelease (or jar) + unzip -l; publishToMavenLocal for the POM"
grep -qE '(^|/)(pyproject\.toml|setup\.py)$' "$FILES" && echo "# Python: python -m build && unzip -l dist/*.whl"
grep -qE '\.gemspec$' "$FILES" && echo "# Ruby: gem build *.gemspec && tar -xOf *.gem data.tar.gz | tar -tz"
grep -qE '(^|/)Cargo\.toml$' "$FILES" && echo "# Rust: cargo package --list"
grep -qE '\.csproj$' "$FILES" && echo "# .NET: dotnet pack && unzip -l *.nupkg"
grep -qE '(^|/)pubspec\.yaml$' "$FILES" && echo "# Flutter/Dart: flutter pub publish --dry-run"
echo '```'
echo
echo "### CI, release and security docs"
echo '```'
grep -E '^(\.github/workflows/|\.github/actions/|\.gitlab-ci\.yml|\.circleci/|bitrise\.yml|codemagic\.yaml|azure-pipelines\.yml|Jenkinsfile|\.buildkite/|fastlane/(Fastfile|Appfile|Matchfile|Pluginfile|Gemfile)|\.travis\.yml|SECURITY\.md|\.github/SECURITY\.md|\.github/dependabot\.yml|renovate\.json|lefthook\.yml|\.pre-commit-config\.yaml|Makefile|Dangerfile)' "$FILES" | head -50
echo '```'
echo
echo "### Sensitive or binary files committed"
grep -iE '\.(p12|p8|pem|key|jks|keystore|pfx|cer|der|mobileprovision|provisionprofile|env|ipa|apk|aab|xcarchive|jar|aar|so|dylib|a|dll|exe|zip|tgz|tar\.gz|7z)$|(^|/)(google-services\.json|GoogleService-Info\.plist|credentials\.json|service[-_]account[^/]*\.json|\.env(\.[a-z]+)?|\.npmrc|\.pypirc|id_rsa|id_ed25519)$' "$FILES" | emit "[SECRET-01..06, SUPPLY-12] sensitive/binary file names"

echo "## 2. Pattern leads"
echo
echo "Labels in brackets are catalog IDs from references/checklist.md. Record a result for every catalog item in the coverage ledger, whether or not it has leads here."
echo
echo "### Secrets (all files incl. tests, maps and project files; values masked unless --show-secret-values)"
sa "[SECRET-01..06] private keys" '-----BEGIN ([A-Z]+ )?PRIVATE KEY-----'
sa "[SECRET-01..06] cloud, provider, CI and registry tokens; webhook URLs" "$PROVIDER_RE"
sa "[SECRET-01..06] credentials embedded in URLs (scheme://user:password@host)" '[a-z][a-z0-9+.-]*://[^/[:space:]:@"'"'"'$\\(){}]+:[^/[:space:]:@"'"'"'$\\(){}]{3,}@' '' '://(user|username|USER|USERNAME|name):(pass|password|PASSWORD|secret)@'
sa "[SECRET-06] registry and machine credentials in config files" '_authToken|_auth[[:space:]]*=|_password[[:space:]]*=|^machine[[:space:]]+[^[:space:]]+[[:space:]]+(login|password)'
sa "[SECRET-01, SECRET-03, SECRET-07] secret-looking assignments" '(api[_-]?secret|client[_-]?secret|secret[_-]?key|private[_-]?key|signing[_-]?key|password|passwd)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'[:space:]]{8,}["'"'"']' -i 'placeholder|YOUR_|<[a-z_]+>|example|dummy|changeme|xxxx|\*\*\*\*'
sa "[SECRET-03, AUTH-01] JWT locations (claims are decoded in the next table)" 'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'

echo "### [AUTH-01, AUTH-03, SECRET-03] JWTs: header and claims (signatures never shown)"
echo
search all "-o" 'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}' > "$WORK/jwts"
if [ -s "$WORK/jwts" ]; then
  echo '```'
  perl -MMIME::Base64 -MDigest::SHA=sha256_hex -e '
    sub b64u { my $s = shift; $s =~ tr{-_}{+/}; $s .= "=" x ((4 - length($s) % 4) % 4); return decode_base64($s); }
    sub day { my @g = gmtime(shift); return sprintf("%04d-%02d-%02d", $g[5] + 1900, $g[4] + 1, $g[3]); }
    my (%seen, %where, %tok, @order);
    while (<STDIN>) {
      chomp;
      next unless /^(.*?):(\d+):(eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)$/;
      my ($f, $l, $t) = ($1, $2, $3);
      my $fp = substr(sha256_hex($t), 0, 8);
      push @order, $fp unless $seen{$fp}++;
      push @{ $where{$fp} }, "$f:$l";
      $tok{$fp} = $t;
    }
    my ($none, $long, @out) = (0, 0);
    for my $fp (@order) {
      my ($h, $p) = split /\./, $tok{$fp};
      my $hj = b64u($h); my $pj = b64u($p);
      my ($alg) = $hj =~ /"alg"\s*:\s*"([^"]*)"/;
      my ($exp) = $pj =~ /"exp"\s*:\s*(\d+)/;
      my ($iat) = $pj =~ /"iat"\s*:\s*(\d+)/;
      my %c; my @claims = grep { !$c{$_}++ } ($pj =~ /"([A-Za-z0-9_:.-]+)"\s*:/g);
      my $life;
      if (!defined $exp) { $life = "exp: NONE (never expires)"; $none++; }
      else {
        $life = "exp: " . day($exp) . ($exp < time ? " (expired)" : "");
        if (defined $iat) { my $d = ($exp - $iat) / 86400; $life .= sprintf(", lifetime %.1f days", $d); $long++ if $d > 30; }
      }
      my @w = @{ $where{$fp} };
      my $at = join(", ", @w[0 .. ($#w < 3 ? $#w : 3)]) . (@w > 4 ? sprintf(" (+%d more)", @w - 4) : "");
      push @out, sprintf("sha256:%s  alg=%s%s  claims=[%s]  %s\n    at %s\n", $fp, ($alg // "?"), ((defined $alg && lc $alg eq "none") ? " (UNSIGNED)" : ""), join(",", @claims), $life, $at);
    }
    printf "# %d distinct JWT(s): %d without exp, %d with a lifetime over 30 days\n", scalar(@order), $none, $long;
    print @out;
  ' < "$WORK/jwts" | head -n $((MAX * 2 + 1))
  echo '```'
  echo "For each token: real or fixture? which environment and key? what does it grant? A token without exp is a permanent credential until the key is rotated (AUTH-01)."
  echo
fi

echo "### Tokens and authentication"
s "[AUTH-01, AUTH-02] expiry and refresh handling" 'expiresIn|expires_in|expiresAt|expires_at|expiration|isExpired|tokenExpired|TOKEN_EXPIRED|noExpir|neverExpir|refreshToken|refresh_token|tokenProvider|token_provider|tokenRefresh'
s "[AUTH-03, AUTH-04] dev, guest and unsigned tokens; client-side token minting" 'devToken|dev_token|developmentToken|\.development\(|guestToken|guest_token|anonymousUser|"alg"[[:space:]]*:[[:space:]]*"none"|jwt\.(encode|sign)|JWT\.create|Jwts\.builder|SignJWT|createToken\(|generateToken\(|HS256|HMAC<SHA256>'
s "[AUTH-05, AUTH-06, AUTH-08] auth headers and token handling" 'Authorization|Bearer |x-api-key|auth[_-]?type|access[_-]?token|refresh[_-]?token|tokenProvider|token_provider' -i
s "[AUTH-05] tokens and keys in URL query strings" '[?&"'"'"'](token|access_token|auth|authorization|api_key|apikey|key|signature|sig|password)=|URLQueryItem\(name: *"(token|access_token|auth|authorization|api_key|apikey|signature|password)"|appendQueryParameter\("(token|access_token|auth|authorization|api_key|apikey|signature|password)"|searchParams\.(set|append)\(["'"'"'](token|access_token|auth|authorization|api_key|apikey|signature|password)' -i
search lead "-l" 'var (debugD|d)escription|override fun toString|toString\(\)[[:space:]]*(\{|=)|def __(repr|str)__|inspect\.custom|CustomReflectable|customMirror' > "$WORK/descfiles"
while IFS= read -r f; do grep -qiE 'token|secret|authorization|password|bearer|credential' "$f" 2>/dev/null && echo "$f"; done < "$WORK/descfiles" | emit "[AUTH-08, LOG-05] files that define description/toString/repr and also handle tokens or secrets (check redaction)"
s "[AUTH-08] value types holding credentials (generated descriptions print every field: data class, record, struct, case class)" '(data class|record|struct|case class)[[:space:]]+[A-Za-z]*(Token|Credential|Secret|Password|Session|Auth)[A-Za-z]*[[:space:](<:{]'
s "[AUTH-07, STORE-07] tokens or secrets in plain storage" '(UserDefaults|NSUserDefaults|SharedPreferences|localStorage|sessionStorage|AsyncStorage|PlayerPrefs|MMKV|shared_preferences|document\.cookie)[^;]*(token|secret|password|credential|session)' -i
s "[AUTH-12] login flows (OAuth, SSO)" 'ASWebAuthenticationSession|SFAuthenticationSession|AppAuth|OIDAuthorization|code_challenge|code_verifier|redirect_uri|response_type=token|authorization_code|client_secret|oauth' -i
s "[AUTH-13, AUTH-14, STORE-10] local authentication, passwords and secret input fields" 'LAContext|evaluatePolicy|kSecAccessControl|SecAccessControlCreateWithFlags|BiometricPrompt|FingerprintManager|CryptoObject|isSecureTextEntry|SecureField|textContentType|oneTimeCode|autocorrectionType|TYPE_TEXT_VARIATION_PASSWORD|textPassword|autocomplete="(current-password|new-password|one-time-code)"|type="password"'
s "[AUTH-11, CRYPTO-05] signature / token verification" 'compare_digest|timingSafeEqual|secure_compare|hash_equals|hmac\.Equal|FixedTimeEquals|MessageDigest\.isEqual|HMAC|hmac|jwt\.(decode|verify)|algorithms?[[:space:]]*[:=]|SecKeyVerifySignature|Signature\.getInstance|verifySignature'

echo "### Transport"
s "[TLS-01] cleartext http:// URLs (benign hosts filtered)" 'http://[A-Za-z0-9]' '' 'http://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.0\.2\.2|\[::1\]|www\.w3\.org|schemas\.|www\.apple\.com/DTDs|xmlns|example\.(com|org)|ns\.adobe\.com|purl\.org|json-schema\.org|opensource\.org|www\.apache\.org/licenses)'
s "[TLS-01, TLS-05] ws:// URLs" 'ws://[A-Za-z0-9]' '' 'ws://(localhost|127\.0\.0\.1|0\.0\.0\.0|10\.0\.2\.2)'
sa "[TLS-01] cleartext / ATS exceptions (incl. project files)" 'NSAllowsArbitraryLoads|NSExceptionAllowsInsecureHTTPLoads|NSAllowsLocalNetworking|cleartextTrafficPermitted="true"|usesCleartextTraffic="true"'
s "[TLS-02, TLS-03, TLS-08] TLS validation overrides, custom trust, pinning, protocol versions" 'InsecureSkipVerify|verify[[:space:]]*=[[:space:]]*False|rejectUnauthorized[[:space:]]*:[[:space:]]*false|NODE_TLS_REJECT_UNAUTHORIZED|badCertificateCallback|ALLOW_ALL_HOSTNAME_VERIFIER|X509TrustManager|HostnameVerifier|checkServerTrusted|URLCredential\(trust|didReceive challenge|SecTrustEvaluate|ServerCertificateValidationCallback|CURLOPT_SSL_VERIFY(PEER|HOST)|VERIFY_NONE|trustAllCerts|onReceivedSslError|CertificatePinner|pinnedCertificates|publicKeyHash|tlsMinimumSupportedProtocol|minimumTLSVersion|TLSv1(\.1)?["'"'"']|\.tlsProtocol1[01]?[^0-9]'
s "[TLS-04, AUTH-06] redirect and cookie handling" 'willPerformHTTPRedirection|followRedirects|followSslRedirects|redirect:[[:space:]]*["'"'"']?(follow|manual)|allow_redirects|CheckRedirect|HTTPCookieStorage|CookieManager|cookieJar|withCredentials|credentials:[[:space:]]*["'"'"']include'

echo "### Storage"
s "[STORE-01, AUTH-07] preferences / web storage / game prefs" 'UserDefaults|NSUserDefaults|SharedPreferences|localStorage\.|sessionStorage\.|AsyncStorage|PlayerPrefs|document\.cookie|MMKV'
s "[STORE-01, STORE-07, AUTH-07] secure storage, protection classes, backup exclusion" 'kSecAttrAccessible[A-Za-z]*|kSecAttrSynchronizable|FileProtectionType|NSFileProtection[A-Za-z]*|NSPersistentStoreFileProtectionKey|completeFileProtection|isExcludedFromBackup|EncryptedSharedPreferences|AndroidKeyStore|MasterKey|flutter_secure_storage|Keychain|SecItemAdd'
s "[STORE-02, STORE-07] shared containers / external storage / backup flags" 'containerURL\(forSecurityApplicationGroupIdentifier|suiteName:|getExternalStorage|getExternalFilesDir|Environment\.getExternalStorageDirectory|MODE_WORLD_(READ|WRIT)ABLE|allowBackup|fullBackupContent|dataExtractionRules'
s "[STORE-03, INPUT-06] file write sinks and archive extraction" 'write\(to:|createFile\(atPath|moveItem\(|copyItem\(|removeItem\(|FileOutputStream|Files\.write|fs\.writeFile|writeFileSync|os\.WriteFile|ZipInputStream|ZipFile|extractall|SSZipArchive|ZIPFoundation|unzipItem|Archive\('
s "[STORE-03] file names derived from content (check containment)" 'lastPathComponent|standardizedFileURL|appendingPathComponent\([a-z]|fileURLWithPath:[^)]*relativeTo|path\.join\([^)]*(name|title|filename)|File\([a-zA-Z]+, *[a-z]+\.(name|title|fileName)|os\.path\.join\([^)]*(name|filename)|filepath\.Join\([^)]*(name|Name)'
s "[STORE-04, STORE-08] temp, cache and download locations; quarantine" 'temporaryDirectory|NSTemporaryDirectory|cachesDirectory|getCacheDir|createTempFile|mkstemp|mktemp|tmpfile|os\.tmpdir|tempfile\.|downloadsDirectory|quarantine|LSQuarantine|Zone\.Identifier'
s "[STORE-05] HTTP and media caches" 'URLCache|urlCache|requestCachePolicy|okhttp3\.Cache|HttpResponseCache|Cache-Control|diskCache|DiskCache|caches\.open|ImageCache|imageCache'
s "[STORE-06] clipboard" 'UIPasteboard|NSPasteboard|ClipboardManager|setPrimaryClip|ClipData|navigator\.clipboard|Clipboard\.(setData|getData|setString)|clipboard\.(writeText|readText)'
s "[STORE-11, IPC-08] screen capture and overlays" 'FLAG_SECURE|filterTouchesWhenObscured|isCaptured|capturedDidChange|userDidTakeScreenshotNotification|privacySensitive'

echo "### Session lifecycle"
s "[SESSION-01, SESSION-02, AUTH-10] logout, user switch and cleanup paths" 'logout|logOut|signOut|disconnectUser|clearCache|clearAll|deleteAll|removeAll\(|resetState|revoke|invalidateToken|wipe' -i
s "[SESSION-03, IPC-03] push registration and push payloads" 'registerForRemoteNotifications|didRegisterForRemoteNotifications|deviceToken|addDevice|removeDevice|FirebaseMessaging|onNewToken|UNNotificationServiceExtension|onMessageReceived|PushProvider'

echo "### Links, navigation, deep links"
s "[LINK-01..03] URL opening" 'UIApplication\.shared\.open|NSWorkspace\.shared\.open|openURL|OpenURLAction|Intent\.ACTION_VIEW|startActivity\(|launchUrl|canLaunchUrl|Linking\.openURL|window\.open\(|shell\.openExternal|location\.href[[:space:]]*=|location\.assign|SFSafariViewController|CustomTabsIntent'
s "[LINK-06, LINK-07] in-app browsers, target=_blank, data detectors" 'SFSafariViewController|CustomTabsIntent|target=["'"'"']_blank|window\.opener|noopener|dataDetectorTypes|autoLink|Linkify|NSDataDetector'
s "[IPC-01, IPC-02, IPC-05] deep link / IPC entry points" 'CFBundleURLSchemes|applinks:|onOpenURL|open url: URL|continue userActivity|exported="true"|<intent-filter|android:scheme|PendingIntent\.get|FLAG_MUTABLE|grantUriPermissions|<provider|registerReceiver|addEventListener\(["'"'"']message|onmessage[[:space:]]*='

echo "### Web content and script execution"
s "[RENDER-01..03, IPC-05, IPC-06] web views, HTML injection, eval" 'WKWebView|UIWebView|loadHTMLString|loadFileURL|evaluateJavaScript|WKScriptMessageHandler|addJavascriptInterface|setJavaScriptEnabled|setAllowFileAccess|setAllowUniversalAccessFromFileURLs|innerHTML|outerHTML|dangerouslySetInnerHTML|v-html|insertAdjacentHTML|document\.write|[^.a-zA-Z]eval\(|new Function\(|JSContext|JavaScriptCore|nodeIntegration|contextIsolation|webSecurity|DocumentType\.html|documentType: *\.html'
s "[INPUT-11, IPC-05] prototype pollution and string-evaluated timers (JS)" '__proto__|constructor\.prototype|lodash\.(merge|set|defaultsDeep)|_\.(merge|set|defaultsDeep)\(|deepmerge|setTimeout\(["'"'"']|setInterval\(["'"'"']'

echo "### Parsing, deserialization, injection"
s "[INPUT-08, INPUT-09] unsafe deserialization / XML" 'NSKeyedUnarchiver|unarchiveObject|unarchiveTopLevelObject|ObjectInputStream|readObject\(|pickle\.loads?|yaml\.load\(|unsafe_load|Marshal\.load|BinaryFormatter|unserialize\(|XMLParser|NSXMLParser|DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|libxml|resolveExternalEntities|NSExpression\(format|TypeNameHandling|activateDefaultTyping|enableDefaultTyping'
s "[INPUT-10, LINK-04] query / format string / command construction" 'NSPredicate\(format: *"[^"]*\\\(|String\(format: *[a-z]|NSLog\([a-z]|rawQuery\(|execSQL\(|sqlite3_exec|Runtime\.getRuntime\(\)\.exec|ProcessBuilder|subprocess\.|os\.system|child_process|execSync|Process\(\)|NSTask|popen\(|(^|[^.a-zA-Z_])system\(' '' 'case system\(|\.system\('
s "[INPUT-07] regex built from variables (ReDoS / injection)" 'NSRegularExpression\(pattern: *[a-z]|Regex\([a-z]|new RegExp\([a-z]|re\.compile\([a-z]|Pattern\.compile\([a-z]|regexp\.MustCompile\([a-z]|RegExp\([a-z]'
s "[INPUT-04] recursive generic JSON / tree types (check depth limits)" 'indirect enum|indirect case|case (array|object|dictionary)\(\[|sealed class Json|JsonElement|enum (RawJSON|JSON|AnyCodable|JSONValue)'

echo "### Crash-prone operations (relevant when input is untrusted; triage by data flow)"
search lead "" 'try!|as! |fatalError\(|preconditionFailure\(|precondition\(|!!\.|!!$|!! |\.first!|\.last!|unsafelyUnwrapped' | cut -d: -f1 | sort | uniq -c | sort -rn | head -15 | sed 's/^/    /' | { echo "#### [INPUT-01] force/trap operations per file (top 15)"; echo '```'; cat; echo '```'; echo; }
s "[INPUT-02, INPUT-03] numeric conversions that can trap or overflow" 'Int\([^)]*(Double|Float|CGFloat|\.rounded|\.value|duration|width|height|size|count)|Int32\(|UInt\(|toInt\(\)|Math\.toIntExact|int\(float|\* *1_?000_?000_?000|nanoseconds' '' 'Int\(exactly|Int\(clamping|Int\(truncatingIfNeeded'

echo "### Memory-unsafe code and concurrency escape hatches"
s "[NATIVE-02, NATIVE-03] unsafe pointers, C string functions, FFI" 'Unsafe(Mutable)?(Raw)?(Buffer)?Pointer|withUnsafe(Mutable)?(Bytes|BufferPointer)|memcpy|strcpy|strcat|sprintf|[^a-z]gets\(|alloca\(|unsafe[[:space:]]*\{|JNIEnv|extern "C"|Marshal\.(Copy|PtrToStructure)'
s "[CONC-01, CONC-03] concurrency safety escape hatches" '@unchecked Sendable|nonisolated\(unsafe\)|@preconcurrency|DispatchQueue\.main\.sync|@Volatile|synchronized\(|threading\.Lock'

echo "### Crypto, randomness and code loading"
s "[CRYPTO-01, CRYPTO-03] weak crypto / insecure randomness" 'Insecure\.(MD5|SHA1)|CC_MD5|CC_SHA1|kCCAlgorithmDES|kCCOptionECBMode|/ECB/|"DES|MessageDigest\.getInstance\("(MD5|SHA-?1)"|createHash\(["'"'"'](md5|sha1)|hashlib\.(md5|sha1)|Math\.random\(|java\.util\.Random|new Random\(|rand\.Seed|math/rand|random\.random\(|mt_rand|[^a-z]srand\(|[^a-zA-Z_]rand\(\)'
s "[CRYPTO-02, CRYPTO-04] keys, IVs, ciphers and key derivation" 'SecretKeySpec\(|IvParameterSpec\(|GCMParameterSpec|CCCrypt\(|CCKeyDerivationPBKDF|AES\.GCM|ChaChaPoly|SymmetricKey\(|createCipheriv|createDecipheriv|Cipher\.getInstance|crypto\.subtle|pbkdf2|PBKDF2|scrypt|argon2|bcrypt|SecKeyCreate|SecKeyEncrypt|KeyGenerator|KeyPairGenerator'
s "[CRYPTO-06, NATIVE-05, AI-09] code, models and config loaded at runtime" 'dlopen|dlsym|loadLibrary|System\.load\(|Bundle\(url:|Bundle\(path:|DexClassLoader|PathClassLoader|importScripts|import\(["'"'"']https?:|MLModel\(contentsOf|compileModel|\.gguf|\.safetensors|torch\.load|RemoteConfig|remoteConfig|CodePush|codePush|expo-updates'

echo "### Logging, errors and telemetry"
search lead "" '(print\(|debugPrint\(|NSLog\(|os_log\(|Logger\(|[A-Za-z_]*([Ll]og|[Ll]ogger|LOG|LOGGER)\.[a-zA-Z]+\(|console\.(log|debug|info|warn|error)|println\(|Timber\.)' > "$WORK/logcalls"
grep -iE '^[^:]*:[0-9]+:.*(token|secret|password|passwd|authorization|bearer|api_?key|cookie|session|credential)' "$WORK/logcalls" | emit "[LOG-01] log calls mentioning secrets"
grep -iE '^[^:]*:[0-9]+:.*(url|request|header|endpoint|query|curl|payload|body)' "$WORK/logcalls" | grep -viE '^[^:]*:[0-9]+:.*(token|secret|password)' | emit "[LOG-01, LOG-02, AUTH-05] log calls printing URLs, requests, headers or bodies (check what they contain)"
s "[LOG-01, LOG-03] verbose HTTP logging / cURL rendering / public log privacy" 'HttpLoggingInterceptor|Level\.BODY|privacy: *\.public|%\{public\}|logRequests|logResponses|cURL|curlRepresentation|LogLevel\.(debug|verbose|all)|logLevel *= *\.(debug|verbose|all)' -i
s "[LOG-05] error types and descriptions (check they don't carry tokens, URLs or headers)" 'LocalizedError|errorDescription|localizedDescription|failureReason|NSUnderlyingErrorKey|userInfo\[|class [A-Za-z]+(Error|Exception)[ (:]|extends (Error|Exception)'
s "[LOG-06, LOG-07] crash reporting, analytics and telemetry" 'Crashlytics|Sentry|Bugsnag|Datadog|Instabug|NewRelic|AppCenter|FirebaseAnalytics|Analytics\.(track|log)|Amplitude|Mixpanel|Segment|PostHog|setUserIdentifier|setCustomValue|setCustomKey|captureException|addBreadcrumb|[Tt]elemetry'
s "[LOG-04, LOG-08, API-05] debug features, test hooks and environment switches" 'ProcessInfo\.processInfo\.(arguments|environment)|CommandLine\.arguments|BuildConfig\.DEBUG|__DEV__|NODE_ENV|kDebugMode|isDebug|debugMode|enableDebug|skipAuth|disableAuth|allowInsecure|motionEnded|LogViewer|logViewer|exportLogs|shareLogs'

echo "### Permissions and device capabilities"
s "[IPC-07] capability requests" 'NS[A-Za-z]+UsageDescription|requestAuthorization|requestAccess\(|AVCaptureDevice|CLLocationManager|PHPhotoLibrary|CNContactStore|SFSpeechRecognizer|uses-permission|requestPermissions|navigator\.(geolocation|mediaDevices)'

echo "### AI / LLM surfaces"
s "[AI-01, AI-02, AI-05] tool calls, approvals, actions" 'autoApprove|auto_approve|requiresApproval|requires_approval|needsApproval|approvalPolicy|toolChoice|tool_choice|function_call|userInitiated|dangerously' -i
s "[AI-07, AI-08] prompts and message roles" 'systemPrompt|system_prompt|role[[:space:]]*[:=][[:space:]]*["'"'"']?(system|developer)|\.system\(|instructions[[:space:]]*[:=]'

echo "### Focused checks for files excluded from the general leads"
echo '```'
echo "# Xcode build phases running scripts (project.pbxproj):"
grep -E '\.pbxproj$' "$FILES" | while IFS= read -r f; do
  n=$(grep -c 'shellScript = ' "$f" 2>/dev/null)
  [ "${n:-0}" -gt 0 ] && echo "  $f: $n Run Script phase(s)" && grep -n 'shellScript = ' "$f" | cut -c1-200 | head -5 | sed 's/^/    /'
  grep -n 'CODE_SIGN_ENTITLEMENTS' "$f" 2>/dev/null | sed -E 's/^[[:space:]]+//' | sort -u -t= -k2 | head -5 | sed 's/^/    /'
done
echo "# minified bundles and source maps (shipped if inside a published folder):"
grep -E '\.min\.js$|\.map$' "$FILES" | head -15
echo "# active content in SVG files:"
grep -E '\.svg$' "$FILES" | while IFS= read -r f; do grep -lE '<script|[[:space:]]on[a-z]+=|javascript:' "$f" 2>/dev/null; done | head -10
echo '```'
echo

echo "## 3. Supply chain and CI"
echo
WF=()
if [ "$USE_GIT" -eq 1 ]; then
  while IFS= read -r -d '' f; do WF+=("$f"); done < <(git ls-files -z -- '.github/workflows/*' '.github/actions/**' 2>/dev/null)
else
  while IFS= read -r -d '' f; do WF+=("$f"); done < <(find .github/workflows .github/actions -type f -print0 2>/dev/null)
fi
if [ "${#WF[@]}" -gt 0 ]; then
  grep -nE 'pull_request_target|workflow_run|issue_comment' "${WF[@]}" 2>/dev/null | emit "[SUPPLY-05] privileged triggers (check for checkout of untrusted refs, and comment-triggered commands)"
  grep -nE '\$\{\{[[:space:]]*(github\.event\.(issue|pull_request|comment|review|review_comment|head_commit|commits|pages|discussion)|github\.head_ref|inputs\.)' "${WF[@]}" 2>/dev/null | emit "[SUPPLY-06] event/inputs interpolated into workflow (script injection if inside run:)"
  grep -nE 'uses:[[:space:]]*[^ .][^@[:space:]]*@' "${WF[@]}" 2>/dev/null | grep -vE '@[0-9a-f]{40}' | emit "[SUPPLY-07] actions not pinned to a commit SHA"
  grep -nE 'permissions:|contents:[[:space:]]*write|id-token:[[:space:]]*write|runs-on:[[:space:]]*\[?[[:space:]]*self-hosted|secrets\.[A-Z_]+' "${WF[@]}" 2>/dev/null | emit "[SUPPLY-08, SECRET-06] token permissions, secrets used, self-hosted runners"
fi
s "[SUPPLY-09] pipe-to-shell installs" '(curl|wget)[^|#]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z)?sh'
s "[SUPPLY-06] branch / PR names reaching shell (CI scripts, fastlane, plugins)" 'headRefName|head_ref|HEAD_REF|BRANCH_NAME|GITHUB_HEAD_REF|sh\("[^"]*#\{|system\("[^"]*#\{|`[^`]*#\{'
search all "" '\.branch\(|branch:[[:space:]]*["'"'"']|:branch[[:space:]]*=>|branch[[:space:]]*=[[:space:]]*["'"'"']|"git\+|github:[A-Za-z0-9_-]+/|revision:|:git[[:space:]]*=>|git[[:space:]]*=[[:space:]]*["'"'"']https?:' | grep -E '^[^:]*(Package\.swift|Podfile|\.podspec|Cartfile|pubspec\.yaml|package\.json|Gemfile|build\.gradle(\.kts)?|libs\.versions\.toml|go\.mod|Cargo\.toml|requirements[^/:]*\.txt|pyproject\.toml|composer\.json|\.csproj):' | emit "[SUPPLY-01] dependencies on branches / git refs (manifests only)"
echo "#### [SUPPLY-01, DIST-03] version requirements in manifests (ranges are normal for libraries; lock files only apply to the repo's own builds)"
echo '```'
grep -E '(^|/)(Package\.swift|[^/]+\.podspec|pubspec\.yaml|package\.json|build\.gradle(\.kts)?|libs\.versions\.toml|go\.mod|Cargo\.toml|pyproject\.toml|[^/]+\.gemspec|[^/]+\.csproj)$' "$FILES" | grep -vE '(^|/)(Tests?|Examples?|Samples?|Integration)/' | head -5 | while IFS= read -r m; do echo "# $m"; grep -nE '\.package\(|dependency|implementation|api\(|"[@a-z0-9/_.-]+": *"[~^<>=*0-9]|require |^[[:space:]]*[a-z0-9_-]+ *= *"|PackageReference' "$m" 2>/dev/null | head -15; done
echo '```'
echo
echo "#### [SUPPLY-09] tool downloads without an adjacent checksum check (scripts)"
echo '```'
grep -E '\.(sh|bash|zsh|rb|py|ya?ml)$|(^|/)(Makefile|Fastfile|Dockerfile|Githubfile)$' "$FILES" | while IFS= read -r f; do
  grep -nE '(curl|wget)[[:space:]]|gh release download|Invoke-WebRequest' "$f" 2>/dev/null | while IFS=: read -r ln rest; do
    start=$((ln>3?ln-3:1))
    if ! sed -n "${start},$((ln+6))p" "$f" | grep -qiE 'sha(1|256|512)?sum|shasum|checksum|gpg --verify|cosign|minisign|--hash|integrity'; then echo "$f:$ln:$(echo "$rest" | cut -c1-180)"; fi
  done
done | mask | head -"$MAX"
echo '```'
echo

echo "## 4. [DIST-03, DIST-04, NATIVE-01] Dependencies: resolved versions and advisory checks"
echo
echo "Nothing is fetched by this script. Advisory tools send package names and versions to public databases: fine for public dependencies, ask first for private ones. Record the tool, its version and the database date in the report, then check applicability (is the vulnerable code compiled in and reachable?)."
echo '```'
if [ -f Package.resolved ] || grep -qE 'Package\.resolved$' "$FILES"; then
  R=$( [ -f Package.resolved ] && echo Package.resolved || grep -E 'Package\.resolved$' "$FILES" | head -1 )
  echo "# SwiftPM pins ($R):"
  perl -0ne 'while (/"identity"\s*:\s*"([^"]+)".*?"location"\s*:\s*"([^"]+)".*?"state"\s*:\s*\{(.*?)\}/sg) { my ($i,$l,$st)=($1,$2,$3); my ($rev)=$st=~/"revision"\s*:\s*"([0-9a-f]+)"/; my ($v)=$st=~/"version"\s*:\s*"([^"]+)"/; my ($b)=$st=~/"branch"\s*:\s*"([^"]+)"/; printf "  %-32s %-12s %s %s\n", $i, ($v//("branch:".($b//"?"))), ($rev//""), $l; }' "$R" 2>/dev/null | head -30
  echo "  -> osv-scanner --lockfile='$R'"
fi
grep -E '(^|/)Podfile\.lock$' "$FILES" | head -3 | while IFS= read -r f; do echo "# CocoaPods: osv-scanner --lockfile='$f'"; done
grep -E '(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml)$' "$FILES" | head -3 | while IFS= read -r f; do echo "# npm: (cd '$(dirname "$f")' && npm audit --omit=dev --json)   or   osv-scanner --lockfile='$f'"; done
grep -qE '(^|/)build\.gradle(\.kts)?$' "$FILES" && echo "# Gradle: ./gradlew <module>:dependencies --configuration releaseRuntimeClasspath ; osv-scanner scan source -r ."
grep -E '(^|/)go\.mod$' "$FILES" | head -3 | while IFS= read -r f; do echo "# Go: (cd '$(dirname "$f")' && govulncheck ./...)   (reports only called vulnerable functions)"; done
grep -E '(^|/)Cargo\.lock$' "$FILES" | head -3 | while IFS= read -r f; do echo "# Rust: (cd '$(dirname "$f")' && cargo audit)"; done
grep -E '(^|/)Gemfile\.lock$' "$FILES" | head -3 | while IFS= read -r f; do echo "# Ruby: (cd '$(dirname "$f")' && bundle audit check --update)"; done
grep -E '(^|/)(poetry\.lock|Pipfile\.lock|uv\.lock|requirements[^/]*\.txt)$' "$FILES" | head -3 | while IFS= read -r f; do echo "# Python: pip-audit -r '$f' (or on the lock file)"; done
grep -E '(^|/)composer\.lock$' "$FILES" | head -3 | while IFS= read -r f; do echo "# PHP: (cd '$(dirname "$f")' && composer audit)"; done
grep -qE '\.csproj$' "$FILES" && echo "# .NET: dotnet list package --vulnerable --include-transitive"
grep -E '(^|/)pubspec\.lock$' "$FILES" | head -3 | while IFS= read -r f; do echo "# Dart: osv-scanner --lockfile='$f'"; done
echo "# tools available here: $(for t in osv-scanner govulncheck cargo-audit pip-audit bundle-audit npm; do command -v "$t" >/dev/null 2>&1 && printf '%s ' "$t"; done)"
echo "# vendored copies are invisible to these tools: check each against its upstream changelog and advisories."
echo '```'
echo

if [ "$HISTORY" -eq 1 ] && [ "$USE_GIT" -eq 1 ]; then
  echo "### [SECRET-04] Git history: commits that added or removed high-confidence secrets"
  echo '```'
  # history_search <regex>: all refs. If a ref can't be read (missing objects), find the refs that
  # contain the unreadable commit, exclude them by name, and record that in the status.
  HIST_EXCLUDES=()
  history_search() {
    local re="$1" rc bad commits ref
    git log "${HIST_EXCLUDES[@]}" --all --oneline -E -G"$re" > "$WORK/hist" 2> "$WORK/hist.err"; rc=$?
    if [ "$rc" -ne 0 ] && [ "${#HIST_EXCLUDES[@]}" -eq 0 ]; then
      bad=$(grep -oE '[0-9a-f]{40}' "$WORK/hist.err" | head -1)
      if [ -n "$bad" ]; then
        commits=$(git log --all --format='%H %T' 2>/dev/null | awk -v t="$bad" '$1==t || $2==t {print $1}')
        for c in $commits; do
          while IFS= read -r ref; do [ -n "$ref" ] && HIST_EXCLUDES+=("--exclude=$ref"); done < <(git for-each-ref --contains "$c" --format='%(refname)' 2>/dev/null)
        done
      fi
      if [ "${#HIST_EXCLUDES[@]}" -gt 0 ]; then
        note_error "history search skipped refs with unreadable objects ($(head -1 "$WORK/hist.err")): ${HIST_EXCLUDES[*]#--exclude=}"
        echo "# skipped refs with unreadable objects: ${HIST_EXCLUDES[*]#--exclude=} (check: git fsck)"
        git log "${HIST_EXCLUDES[@]}" --all --oneline -E -G"$re" > "$WORK/hist" 2> "$WORK/hist.err"; rc=$?
      fi
    elif [ "$rc" -ne 0 ]; then
      :
    else
      [ "${#HIST_EXCLUDES[@]}" -gt 0 ] && echo "# skipped refs with unreadable objects: ${HIST_EXCLUDES[*]#--exclude=}"
    fi
    if [ "$rc" -ne 0 ]; then
      note_error "history search over all refs failed (exit $rc: $(head -1 "$WORK/hist.err")); retried on HEAD only"
      echo "# all-refs search FAILED ($(head -1 "$WORK/hist.err")); results below cover HEAD's history only. Check: git fsck"
      git log HEAD --oneline -E -G"$re" > "$WORK/hist" 2>> "$WORK/stderr" || note_error "history search on HEAD failed too"
    fi
    head -40 "$WORK/hist"
  }
  history_search "-----BEGIN ([A-Z]+ )?PRIVATE KEY-----|$PROVIDER_RE"
  echo "# deleted sensitive files still in history:"
  { git log "${HIST_EXCLUDES[@]}" --all --diff-filter=D --name-only --pretty=format: 2>> "$WORK/stderr" || note_error "deleted-files history search failed"; } | grep -iE '\.(p12|p8|pem|key|jks|keystore|pfx|mobileprovision|env)$|(^|/)\.env(\.[a-z]+)?$|google-services\.json|GoogleService-Info\.plist|credentials\.json|service[-_]account|\.npmrc$|\.netrc$|(^|/)(secrets?|credentials?)[^/]*$|\.properties$|\.xcconfig$' | sort -u | head -20
  echo "# commits that added or removed secret-looking assignments (vendor-specific secrets have no fixed format):"
  history_search '([Ss]ecret|SECRET|[Pp]assword|PASSWORD|[Pp]rivate[_-]?[Kk]ey|PRIVATE_KEY|[Ss]igning[_-]?[Kk]ey|SIGNING_KEY)[A-Za-z_.-]*["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9_./+=-]{16,}'
  echo "# commits that added or removed JWTs (decode them: an old token without exp is still valid unless the key was rotated):"
  history_search 'eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
  echo '```'
  echo
fi

echo "---"
if [ -s "$ERRORS" ]; then
  echo "**Recon status: INCOMPLETE.** These searches failed, so their sections may be missing hits:"
  sed 's/^/- /' "$ERRORS" | sort -u | head -20
  [ -s "$WORK/stderr" ] && { echo; echo "First errors:"; echo '```'; sort -u "$WORK/stderr" | head -5; echo '```'; }
  exit 3
fi
echo "**Recon status: complete.** Leads only. Next: record scope, run the distribution pass, build the threat model, then trace each relevant lead from an attacker-controlled source to its sink."
````
