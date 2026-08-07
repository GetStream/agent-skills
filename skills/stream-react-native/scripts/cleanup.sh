#!/usr/bin/env bash
# Remove the run artifacts a design match / migration leaves in the target project.
#
#   bash scripts/cleanup.sh <abs-project-dir>                  # DRY RUN — lists, removes nothing
#   bash scripts/cleanup.sh <abs-project-dir> --yes             # actually remove
#   bash scripts/cleanup.sh <abs-project-dir> --yes --keep-evidence
#   bash scripts/cleanup.sh <abs-project-dir> --gitignore        # append the paths to .gitignore
#
# Two real migrations left ~16 MB behind (`.baseline/`, `.after/`, `.designverify/`,
# `design-analysis.md`) because the only cleanup instruction was one prose line about a
# single file, and the capture folders were never mentioned anywhere. This is the gate.
#
# --keep-evidence retains `design-analysis.md` and the comparison contact sheets (the
# region-diff proof) while removing the raw captures and the throwaway venv. Use it when
# the delivered README cites that evidence — and do NOT delete anything the README links to.
#
# SAFETY: only names on the allowlist below are ever removed, only directly inside the
# given project directory, and never when that directory is $HOME, /, or the skill itself.
set -u

ALLOW_DIRS=(.baseline .verify .after .designverify .design .designvenv)
ALLOW_GLOBS=('design-analysis.md' 'compare-*.png' 'compare-*.txt')
EVIDENCE=('design-analysis.md' 'compare-*.png' 'compare-*.txt' .designverify)

DIR="${1:-}"; shift || true
APPLY=""; KEEP=""; GITIGNORE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --yes|-y) APPLY=1; shift;;
    --keep-evidence) KEEP=1; shift;;
    --gitignore) GITIGNORE=1; shift;;
    *) echo "unknown flag $1" >&2; exit 2;;
  esac
done

[ -n "$DIR" ] || { sed -n '2,18p' "$0"; exit 2; }
[ -d "$DIR" ] || { echo "CLEANUP_ERROR: not a directory: $DIR" >&2; exit 2; }
ABS=$(cd "$DIR" && pwd -P)
SKILL=$(cd "$(dirname "$0")/.." && pwd -P)
for bad in "$HOME" "/" "$SKILL"; do
  [ "$ABS" = "$(cd "$bad" 2>/dev/null && pwd -P)" ] && {
    echo "CLEANUP_ERROR: refusing to clean $ABS" >&2; exit 2; }
done
case "$ABS" in "$SKILL"/*) echo "CLEANUP_ERROR: $ABS is inside the skill directory" >&2; exit 2;; esac

kept=() targets=()
is_evidence() { local n="$1"; for e in "${EVIDENCE[@]}"; do case "$n" in $e) return 0;; esac; done; return 1; }

for d in "${ALLOW_DIRS[@]}"; do
  [ -e "$ABS/$d" ] || continue
  if [ -n "$KEEP" ] && is_evidence "$d"; then kept+=("$d"); else targets+=("$d"); fi
done
for g in "${ALLOW_GLOBS[@]}"; do
  for f in "$ABS"/$g; do
    [ -e "$f" ] || continue
    n=$(basename "$f")
    if [ -n "$KEEP" ] && is_evidence "$n"; then kept+=("$n"); else targets+=("$n"); fi
  done
done

if [ ${#targets[@]} -eq 0 ] && [ ${#kept[@]} -eq 0 ]; then
  echo "nothing to clean in $ABS"; exit 0
fi

total=0
echo "project: $ABS"
[ ${#kept[@]} -gt 0 ] && { echo "KEEPING (evidence):"; for k in "${kept[@]}"; do
  echo "  $k  ($(du -sh "$ABS/$k" 2>/dev/null | cut -f1))"; done; }
if [ ${#targets[@]} -gt 0 ]; then
  echo "$([ -n "$APPLY" ] && echo REMOVING || echo 'WOULD REMOVE (dry run — pass --yes)'):"
  for t in "${targets[@]}"; do
    sz=$(du -sk "$ABS/$t" 2>/dev/null | cut -f1); total=$((total + ${sz:-0}))
    echo "  $t  ($(du -sh "$ABS/$t" 2>/dev/null | cut -f1))"
    [ -n "$APPLY" ] && rm -rf -- "$ABS/$t"
  done
  # One decimal, not integer MB: 68 KB of contact sheets printed as "total: 0 MB", which
  # reads as "there was nothing to remove" right next to a list of things being removed.
  awk -v k="$total" 'BEGIN{ if (k < 1024) printf "total: %d KB\n", k; else printf "total: %.1f MB\n", k/1024 }'
fi

if [ -n "$GITIGNORE" ]; then
  GI="$ABS/.gitignore"
  added=0
  for p in "${ALLOW_DIRS[@]}" "${ALLOW_GLOBS[@]}"; do
    grep -qxF "$p" "$GI" 2>/dev/null && continue
    if [ $added -eq 0 ]; then
      printf '\n# Stream RN skill — design-match run artifacts\n' >> "$GI"; added=1
    fi
    echo "$p" >> "$GI"
  done
  [ $added -eq 1 ] && echo "appended the artifact paths to .gitignore" || echo ".gitignore already covers them"
fi

if [ -z "$APPLY" ] && [ ${#targets[@]} -gt 0 ]; then
  echo
  echo "Nothing was removed. Re-run with --yes once you have confirmed the list, and make sure"
  echo "the delivered README does not link to anything above (use --keep-evidence if it does)."
fi
