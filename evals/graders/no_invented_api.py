#!/usr/bin/env python3
"""Shared grader: the agent invented no Stream API.

Two checks over the workspace (cwd) and the files the agent changed (EVAL_CHANGED_FILES):

1. `npx tsc --noEmit` passes (a nonexistent method on a typed client is a type error).
2. Every named import from a Stream package (`stream-chat`, `stream-chat-react`,
   `@stream-io/*`) in the changed files exists in that package's published typings.

Exit 0 = pass. Prints what failed. Skips check 2 for packages that are not installed
(the import itself would then fail check 1).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Longest alternative first, and the name must end at a path boundary - otherwise
# "stream-chat-react" matches the "stream-chat" prefix and the wrong typings get checked.
STREAM_PKG = re.compile(r"^(@stream-io/[^/'\"]+|stream-chat-react|stream-chat)(?=/|$)")
IMPORT = re.compile(r"import\s+(?:type\s+)?\{([^}]*)\}\s+from\s+['\"]([^'\"]+)['\"]", re.S)

ws = Path.cwd()
changed = [Path(p) for p in os.environ.get("EVAL_CHANGED_FILES", "").split("\n") if p]
failures = []

# 1. type-check (only if the workspace is a TS project)
if (ws / "tsconfig.json").exists() and (ws / "node_modules").exists():
    proc = subprocess.run(["npx", "tsc", "--noEmit", "-p", "."], cwd=ws, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        errs = [l for l in (proc.stdout + proc.stderr).splitlines() if "error TS" in l]
        failures.append("tsc: %d error(s); first: %s" % (len(errs), errs[0][:200] if errs else proc.stdout[-200:]))
else:
    print("note: no tsconfig.json/node_modules in workspace; tsc check skipped")


# 2. named imports exist in the package typings
def typings_text(pkg, depth=0):
    """All .d.ts text of a package, plus (one level) the packages it re-exports wholesale -
    e.g. @stream-io/video-react-sdk does `export * from '@stream-io/video-react-bindings'`."""
    root = ws / "node_modules" / pkg
    if not root.exists():
        return None
    chunks = []
    for d in root.rglob("*.d.ts"):
        if "node_modules" in d.relative_to(root).parts:
            continue
        try:
            chunks.append(d.read_text(errors="replace"))
        except OSError:
            pass
    text = "\n".join(chunks)
    if depth == 0:
        for dep in set(re.findall(r"export\s+\*\s+from\s+['\"]([^'\"]+)['\"]", text)):
            if dep.startswith("."):
                continue
            sub = typings_text(dep, depth + 1)
            if sub:
                text += "\n" + sub
    return text


cache = {}
for f in changed:
    if f.suffix not in (".ts", ".tsx", ".js", ".jsx", ".mjs"):
        continue
    try:
        src = f.read_text(errors="replace")
    except OSError:
        continue
    for names, pkg in IMPORT.findall(src):
        m = STREAM_PKG.match(pkg)
        if not m:
            continue
        pkg_name = m.group(1)
        if pkg_name not in cache:
            cache[pkg_name] = typings_text(pkg_name)
        text = cache[pkg_name]
        if text is None:
            continue
        for raw in names.split(","):
            name = raw.strip().split(" as ")[0].replace("type ", "").strip()
            if not name:
                continue
            if not re.search(r"\b%s\b" % re.escape(name), text):
                failures.append("%s imports `%s` from %s - not in its typings" % (f.name, name, pkg_name))

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("ok: tsc clean and all Stream imports exist")
