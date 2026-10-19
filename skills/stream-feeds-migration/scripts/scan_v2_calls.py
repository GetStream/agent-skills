#!/usr/bin/env python3
"""Find the Activity Feeds v2 write paths in an app's source code.

Walks a repository and lists every call site that writes v2 data: activities
(add, add to many, update, partial update, remove, to-targets), reactions
(add, child reactions, update, delete), follows, users and collections, plus
raw REST calls to the v2 API. Each hit records the file, line, call kind, the
feed group and reaction kind when they are string literals, and a short
snippet so the fields can be read without opening every file. Feed groups
are the string literals near each call (feed_groups_nearby), so confirm them
at the call site.

The result is the starting point for the code inventory in SKILL.md: read the
call sites it lists, then build the inventory from them.

Only the standard library is used, and nothing is sent anywhere: this reads
files under --root and writes one JSON file.

Usage:
    scan_v2_calls.py [--root DIR] [--out PATH] [--context N]

Secrets: snippets never carry long key-like tokens or string literals on lines
that mention a secret; they are replaced with <redacted>.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

SOURCE_EXTENSIONS = {
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js", ".ts": "js", ".tsx": "js",
    ".py": "python", ".rb": "ruby", ".php": "php", ".go": "go",
    ".java": "java", ".kt": "java", ".cs": "dotnet", ".swift": "swift",
}

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", ".next", "out", "coverage",
    "venv", ".venv", "env", "__pycache__", "target", "bin", "obj", "Pods", ".gradle",
}

# A file that references a v2 SDK or the v2 API host. Generic method names
# (follow, update, delete) only count in these files.
SDK_MARKERS = [
    r"""require\(\s*['"]getstream['"]\s*\)""", r"""from\s+['"]getstream['"]""",
    r"^\s*import\s+stream\b", r"^\s*from\s+stream\b", r"stream\.connect\(",
    r"""require\s+['"]stream['"]""", r"Stream::Client", r"GetStream\\\\Stream",
    r"github\.com/GetStream/stream-go2", r"io\.getstream\.client", r"\bStream\.Net\b",
    r"\bStreamClient\b", r"GetStreamIO", r"stream-io-api\.com",
]
SDK_MARKER_RE = re.compile("|".join(SDK_MARKERS), re.MULTILINE)

# Method names, compared lowercased with underscores removed, mapped to a kind.
DISTINCTIVE_METHODS = {
    "addactivity": "add_activity", "addactivityasync": "add_activity",
    "addactivities": "add_activities", "addactivitiesasync": "add_activities",
    "addtomany": "add_to_many", "addtomanyasync": "add_to_many",
    "updateactivities": "update_activities", "updateactivitiesasync": "update_activities",
    "updateactivity": "update_activities", "updateactivityasync": "update_activities",
    "activitypartialupdate": "partial_update", "activitiespartialupdate": "partial_update",
    "partialupdateactivity": "partial_update", "partialupdateactivities": "partial_update",
    "updateactivitybyid": "partial_update", "updateactivitybyforeignid": "partial_update",
    "updateactivitiesbyid": "partial_update", "updateactivitiesbyforeignid": "partial_update",
    "removeactivity": "remove_activity", "removeactivityasync": "remove_activity",
    "removeactivitybyforeignid": "remove_activity",
    "updateactivitytotargets": "update_to_targets", "updatetotargets": "update_to_targets",
    "followmany": "follow_many", "followmanyasync": "follow_many",
    "unfollowmany": "unfollow_many", "unfollowmanyasync": "unfollow_many",
    "addchild": "reaction_add_child", "addchildasync": "reaction_add_child",
}
SDK_FILE_METHODS = {
    "follow": "follow", "followasync": "follow", "followfeed": "follow",
    "unfollow": "unfollow", "unfollowasync": "unfollow", "unfollowfeed": "unfollow",
}

METHOD_CALL_RE = re.compile(r"[.:>]\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(")
REACTION_CALL_RE = re.compile(
    r"reactions?\s*(?:\(\s*\))?\s*(?:\.|->)\s*(add|update|delete|remove)(?:_?async)?\s*\(", re.IGNORECASE)
USER_CALL_RE = re.compile(
    r"""(?:users?\s*(?:\(\s*\))?\s*(?:\.|->)\s*(?:add|update|upsert|create)(?:_?async)?\s*\()|"""
    r"""(?:\.user\s*\([^)]*\)\s*\.\s*(?:create|update|getorcreate|getOrCreate)\s*\()""", re.IGNORECASE)
COLLECTION_CALL_RE = re.compile(
    r"collections?\s*(?:\(\s*\))?\s*(?:\.|->)\s*(add|upsert|update|insert|delete)(?:_?many)?(?:_?async)?\s*\(",
    re.IGNORECASE)
REST_RE = re.compile(r"/api/v1\.0/(feed|reaction|activities|follow_many|unfollow_many|collections|user)\b")

FEED_GROUP_RES = [
    re.compile(r"""\bfeed\s*\(\s*['"`]([A-Za-z0-9_\-]+)['"`]""", re.IGNORECASE),
    re.compile(r"""(?:Flat|Aggregated|Notification)Feed\s*\(\s*['"`]([A-Za-z0-9_\-]+)['"`]""", re.IGNORECASE),
]
# "group:id" literals (to-targets, follow sources and targets). Object refs
# look the same ("post:123"), so these only count on lines about feeds.
FEED_ID_LITERAL_RE = re.compile(r"""['"`]([A-Za-z0-9_\-]+):[^'"`\s]*['"`]""")
FEED_CONTEXT_RE = re.compile(r"""\b(to|target|targets|source|feeds?|follow\w*|unfollow\w*)\b\s*[:=(\[]""", re.IGNORECASE)
# The reaction kind as the first literal argument (JS, Python, Ruby, PHP, .NET),
# or a kind field in a request object (Go structs, JS/PHP option objects).
# Java passes the user id first, so only the kind field form is used there.
REACTION_KIND_ARG_RE = re.compile(r"""(?:add|add_?child)(?:_?async)?\s*\(\s*['"]([A-Za-z0-9_\-]+)['"]""", re.IGNORECASE)
REACTION_KIND_FIELD_RE = re.compile(r"""\bkind['"]?\s*(?:=>|[:=])\s*['"]([A-Za-z0-9_\-]+)['"]""", re.IGNORECASE)

# The function a call sits in, found by looking upward from the call. Apps
# usually wrap the SDK (postService.create -> feed.addActivity); the payload is
# then built at the wrapper's call sites, which are listed as wrapper_call.
ENCLOSING_FN_RES = [
    re.compile(r"(?:async\s+)?function\s*\*?\s*([A-Za-z_$][\w$]*)\s*\("),            # JS function
    re.compile(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"),  # JS arrow
    re.compile(r"^\s*(?:async\s+)?([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{"),           # JS/TS method
    re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\("),                        # Python
    re.compile(r"^\s*def\s+(?:self\.)?([A-Za-z_]\w*[!?]?)"),                            # Ruby
    re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)\s*\("),                  # Go
    re.compile(r"function\s+([A-Za-z_]\w*)\s*\("),                                      # PHP
    re.compile(r"^\s*(?:public|private|protected|internal|static|async|override|final|\s)*[\w<>\[\],?\s]+\s+([A-Za-z_]\w*)\s*\([^;]*$"),  # Java/C#
]
GENERIC_FN_NAMES = {"main", "run", "init", "handler", "handle", "execute", "process", "constructor",
                    "if", "for", "while", "switch", "catch", "function", "return", "retry", "pool"}
FN_LOOKBACK_LINES = 40

SECRET_TOKEN_RE = re.compile(r"[A-Za-z0-9]{40,}")
STRING_LITERAL_RE = re.compile(r"""(['"])(?:(?!\1).)*\1""")


def redact(line: str) -> str:
    line = SECRET_TOKEN_RE.sub("<redacted>", line)
    if re.search(r"secret|password|token", line, re.IGNORECASE):
        line = STRING_LITERAL_RE.sub("'<redacted>'", line)
    return line.rstrip()


def norm(name: str) -> str:
    return name.lower().replace("_", "")


def classify(line: str, sdk_file: bool):
    """Yield (kind, detail) for each v2 write on a line."""
    for m in REACTION_CALL_RE.finditer(line):
        verb = m.group(1).lower()
        if verb == "add" or sdk_file:
            yield ("reaction_" + ("delete" if verb == "remove" else verb)), None
    if USER_CALL_RE.search(line) and sdk_file:
        yield "user_write", None
    if COLLECTION_CALL_RE.search(line) and sdk_file:
        yield "collection_write", None
    for m in METHOD_CALL_RE.finditer(line):
        name = norm(m.group(1))
        if name in DISTINCTIVE_METHODS:
            yield DISTINCTIVE_METHODS[name], None
        elif sdk_file and name in SDK_FILE_METHODS:
            yield SDK_FILE_METHODS[name], None
    if REST_RE.search(line):
        yield "rest_call", None


def feed_groups(window: str):
    found = []
    for rx in FEED_GROUP_RES:
        found += rx.findall(window)
    for line in window.splitlines():
        if FEED_CONTEXT_RE.search(line):
            found += FEED_ID_LITERAL_RE.findall(line)
    groups = []
    for g in found:
        if g not in groups and not g.isdigit() and g.lower() not in ("http", "https", "su", "so", "sa", "sr"):
            groups.append(g)
    return groups


def indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def opens_block(line: str) -> bool:
    """True when a definition line opens a multi-line body."""
    stripped = re.sub(r"(//|#).*$", "", line).rstrip()
    return stripped.endswith(("{", "=>", ":", "(", "do")) or stripped.endswith("=> {")


def enclosing_function(lines, index):
    """Name of the function a call at lines[index] sits in, if one is found.

    Uses indentation as scope: a definition counts only when the call is
    indented deeper than it and no line in between returns to its indentation
    (which would mean the function already ended). One-line helpers are
    skipped. A call directly inside a generic entry point (main, run, ...)
    is not wrapped.
    """
    call_indent = indent(lines[index])
    closed_at = None  # smallest indentation seen between the call and line j
    for j in range(index - 1, max(-1, index - FN_LOOKBACK_LINES), -1):
        line = lines[j]
        if not line.strip():
            continue
        ind = indent(line)
        for rx in ENCLOSING_FN_RES:
            m = rx.search(line)
            if not m:
                continue
            in_scope = ind < call_indent and (closed_at is None or closed_at > ind) and opens_block(line)
            if not in_scope:
                break
            name = m.group(1)
            if name.lower() in GENERIC_FN_NAMES or len(name) < 3:
                return None, None
            return name, j
        closed_at = ind if closed_at is None else min(closed_at, ind)
    return None, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=".", help="repository root to scan (default: current directory)")
    parser.add_argument("--out", default="v2-code-scan.json", help="output file path")
    parser.add_argument("--context", type=int, default=4, help="snippet lines after each call (default 4)")
    parser.add_argument("--max-files", type=int, default=50000, help="stop after this many source files")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    calls, sdk_files, scanned = [], [], 0
    sources = {}                      # rel path -> (lang, lines)
    wrappers = {}                     # function name -> {"kinds", "defined_at"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for filename in filenames:
            lang = SOURCE_EXTENSIONS.get(os.path.splitext(filename)[1])
            if not lang:
                continue
            scanned += 1
            if scanned > args.max_files:
                break
            path = os.path.join(dirpath, filename)
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            rel = os.path.relpath(path, root)
            sdk_file = bool(SDK_MARKER_RE.search(text))
            if sdk_file:
                sdk_files.append(rel)
            lines = text.splitlines()
            sources[rel] = (lang, lines)
            for i, line in enumerate(lines):
                kinds = list(dict.fromkeys(k for k, _ in classify(line, sdk_file)))
                if not kinds:
                    continue
                start, end = max(0, i - 2), min(len(lines), i + 1 + args.context)
                window = "\n".join(lines[start:end])
                kind_lits = REACTION_KIND_FIELD_RE.findall(line)
                if lang != "java":
                    kind_lits = REACTION_KIND_ARG_RE.findall(line) + kind_lits
                calls.append({
                    "file": rel,
                    "line": i + 1,
                    "lang": lang,
                    "kinds": kinds,
                    "sdk_file": sdk_file,
                    # literals within the snippet window: nearby, not proven
                    # to belong to this call; read the call site to confirm.
                    "feed_groups_nearby": feed_groups(window),
                    "reaction_kinds": kind_lits if any(k.startswith("reaction_") for k in kinds) else [],
                    "snippet": [redact(l) for l in lines[start:end]],
                })
                if kinds != ["rest_call"]:
                    name, def_line = enclosing_function(lines, i)
                    if name:
                        w = wrappers.setdefault(name, {"kinds": [], "defined_at": set()})
                        w["kinds"] = list(dict.fromkeys(w["kinds"] + kinds))
                        w["defined_at"].add((rel, def_line))

    # Call sites of the functions that wrap v2 writes: that is where the
    # payload (fields, feed group, kind) is usually built.
    for name, w in wrappers.items():
        call_re = re.compile(r"(?<![.\w$>:])" + re.escape(name) + r"\s*\(")
        for rel, (lang, lines) in sources.items():
            for i, line in enumerate(lines):
                if (rel, i) in w["defined_at"] or not call_re.search(line):
                    continue
                start, end = max(0, i - 1), min(len(lines), i + 1 + max(args.context, 10))
                window = "\n".join(lines[start:end])
                calls.append({
                    "file": rel,
                    "line": i + 1,
                    "lang": lang,
                    "kinds": ["wrapper_call"],
                    "wraps": {"function": name, "kinds": w["kinds"]},
                    "sdk_file": rel in sdk_files,
                    "feed_groups_nearby": feed_groups(window),
                    "reaction_kinds": [],
                    "snippet": [redact(l) for l in lines[start:end]],
                })

    result = {"root": root, "files_scanned": scanned, "sdk_files": sdk_files, "calls": calls}
    with open(args.out, "w") as handle:
        json.dump(result, handle, indent=2)

    kinds = Counter(k for c in calls for k in c["kinds"])
    groups = Counter(g for c in calls for g in c["feed_groups_nearby"])
    rkinds = Counter(k for c in calls for k in c["reaction_kinds"])
    print("wrote {}".format(args.out))
    print("source files scanned: {} (referencing a v2 SDK or the v2 API: {})".format(scanned, len(sdk_files)))
    print("call sites: {}".format(len(calls)))
    for kind, n in sorted(kinds.items()):
        print("  {:<20} {}".format(kind, n))
    print("feed groups named in literals: {}".format(", ".join(sorted(groups)) or "(none - built at runtime?)"))
    print("reaction kinds named in literals: {}".format(", ".join(sorted(rkinds)) or "(none - built at runtime?)"))
    if wrappers:
        print("functions wrapping v2 writes: {}".format(", ".join(
            "{} ({})".format(n, "/".join(w["kinds"])) for n, w in sorted(wrappers.items()))))
    if not calls:
        print("\nNo v2 write calls found. Check --root, or the app may write through a wrapper "
              "or another service.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
