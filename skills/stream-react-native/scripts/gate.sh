#!/usr/bin/env bash
# Run a verification command so its REAL exit status is reported.
#
#   bash scripts/gate.sh <abs-project-dir> <command...>
#
# Exists because two failure modes silently reported green in real runs:
#   1. A pipe returns the PIPE's exit status — `npx tsc --noEmit | head` prints 0
#      on a failing typecheck, `run-ios | tail` prints success on a build that
#      died with 65. (${PIPESTATUS[0]} is not a fix: this shell is zsh, where it
#      expands to nothing.)
#   2. `npx <tool>` outside the project resolves an unrelated registry package —
#      `npx tsc` in the wrong directory prints "This is not the tsc command you
#      are looking for", which reads like a pass.
#
# So: absolute cd, redirect (never pipe), echo the status, tail the log.
set -u
DIR="${1:-}"; shift || true
[ -d "$DIR" ] || { echo "GATE_ERROR: not a directory: $DIR"; exit 2; }
[ $# -gt 0 ] || { echo "GATE_ERROR: no command given"; exit 2; }

LOG="$(mktemp -t rn-gate)"
cd "$DIR" || exit 2
echo "GATE: cd $DIR && $*"
"$@" > "$LOG" 2>&1
EXIT=$?
echo "EXIT=$EXIT"
echo "LOG=$LOG"
TAIL="${GATE_TAIL:-30}"
echo "--- last $TAIL lines ---"
tail -n "$TAIL" "$LOG"

# `expo run:ios` exits non-zero on an osascript Automation-permission error AFTER
# "Build Succeeded" — the .app is built and installed. Say so instead of letting
# a real build success be read as a failure.
if [ $EXIT -ne 0 ] && grep -q "Build Succeeded" "$LOG" && grep -q "osascript" "$LOG"; then
  echo "NOTE: build succeeded; the non-zero exit is the osascript launch step, not the build."
  echo "      Launch and capture it yourself (scripts/sim.sh capture <bundleId> <out.png> --project <dir>)."
fi
exit $EXIT
