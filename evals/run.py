#!/usr/bin/env python3
"""Skill eval harness. Runs prompts against the skills with `claude -p`, grades the
outcome, and reports. Stdlib only.

Layout (compatible with `claude plugin eval` so the runner can be swapped later):

  evals/cases/<case>/prompt.md      frontmatter + the prompt
  evals/cases/<case>/graders/*.md   one grader per file (frontmatter: type, ...)
  evals/fixtures/<name>/            fixture apps, copied into the workspace
  evals/fixtures/creds/.stream/     app credentials, copied when `creds: true`
  evals/results/<stamp>-<config>/   transcripts, per-run results, summary

Configurations: A = v1 skills (git tag v1-skills), B = v2 skills (v2/ + the
v1 platform packs), C = control (no skills). Each run gets a fresh workspace, a
fresh HOME (seeded with the eval test account's CLI auth from
evals/fixtures/creds/auth.yaml and a symlink to the real docs cache), and a
CLAUDE_CONFIG_DIR from the RUNNER POOL (evals/runners/<n>, each its own OAuth login) -
so nothing from the operator's own skills, settings, memory, or logins leaks in, and
no refresh-token rotation in a runner can log the operator out. This is
process-level isolation, not an OS sandbox: --dangerously-skip-permissions, full
network, runs as the operator.

prompt.md frontmatter: name, runs (1), max_turns (10), timeout_seconds (300),
model, fixture, creds (false: copy the eval app's .stream/ project credentials into
the workspace), account_auth (false: seed the operator's rotating CLI account login
into the sandbox HOME and carry the rotated token back afterwards; runs serialized),
append_system_prompt, invoke (stream: prefix the prompt with `/stream` in A and B;
another skill name; or none for a bare prompt - C always gets the bare prompt),
skills (a synthetic skill set under fixtures/<set>/{A,B}/ installed instead of the real packs).

Grader frontmatter: type (regex | tool_used | tool_order | file_exists | script |
llm), scored (true; false = unscored indicator), configs (A | [A, C] - score the grader
only in those configurations), plus per type:
  regex       target: last_message | files | trace; match: contains | not_contains;
              flags: i; files: <glob> (target files only: narrow to changed files whose
              workspace-relative path or name matches); body = pattern. Over files the
              pattern is matched PER FILE - contains passes if some one file matches,
              not_contains if no file does - lockfiles are never read, and comments are
              stripped first (comments: keep to match them too).
  tool_used   tool; input_match (regex over the JSON input); min (1); max
  tool_order  before; after (each a regex over "<tool> <json input>")
  file_exists path (glob, workspace-relative); match: exists | not_exists
  changed_files  min (0); max - how many files the agent created or modified
  script      body = bash, run in the workspace; exit 0 = pass. Env:
              EVAL_WORKSPACE, EVAL_ROOT (this dir), EVAL_TRANSCRIPT,
              EVAL_LAST_MESSAGE (file paths), EVAL_CHANGED_FILES (newline list).
              Shared checks live in evals/graders/ (e.g. no_invented_api.py)
  llm         scope: last_message | transcript | files:<glob>; body = criteria

Scoring: the unit of measurement is the GRADER, not the case. A run's `pass` (every
scored grader passed) is kept for the exit code, but the summary and compare.py report
graders passed / graders scored, so a 16-grader build and a 1-grader routing question
weigh what they actually checked. Runs that timed out or hit the turn budget are
labeled (T) and counted, with their failures flagged as ambiguous: a pass in a truncated
run is a pass, a failure may only be the budget. Each run records its provenance: agent and judge model, Claude Code
version, repo SHA (+ dirty flag), the v1-skills tag SHA in A, and a digest of the
installed skill text, so a run can be attributed to exactly the skills it tested.
Judge cost is metered separately (metrics.judge_cost_usd) and added to the totals.

Usage:
  python3 evals/run.py --config B                    # every case
  python3 evals/run.py --config C --case "how-does*"  # a subset
  python3 evals/run.py --list
"""

import argparse
import fnmatch
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
CASES = EVALS / "cases"
FIXTURES = EVALS / "fixtures"
RESULTS = EVALS / "results"
IGNORED_DIRS = {"node_modules", ".git", ".claude", ".next", "dist", ".design-verify"}
V2_DELETED = {"stream-builder", "stream-docs"}


# ----------------------------------------------------------------- frontmatter

def parse_frontmatter(text):
    """Flat YAML subset: `key: value`, lists as [a, b], bools, ints."""
    meta, body = {}, text
    if text.startswith("---"):
        parts = text.split("\n---", 1)
        if len(parts) == 2:
            head, body = parts[0][3:], parts[1]
            if body.startswith("\n"):
                body = body[1:]
            for line in head.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or ":" not in line:
                    continue
                key, value = line.split(":", 1)
                meta[key.strip()] = coerce(value.strip())
    return meta, body.strip()


def coerce(value):
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [coerce(v.strip()) for v in inner.split(",")] if inner else []
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    low = value.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


# ----------------------------------------------------------------------- cases

def load_cases(pattern):
    cases = []
    for prompt_file in sorted(CASES.glob("*/prompt.md")):
        case_dir = prompt_file.parent
        if pattern and not any(fnmatch.fnmatch(case_dir.name, p.strip()) for p in pattern.split(",")):
            continue
        meta, prompt = parse_frontmatter(prompt_file.read_text())
        graders = []
        for gf in sorted((case_dir / "graders").glob("*.md")):
            gmeta, gbody = parse_frontmatter(gf.read_text())
            gmeta["name"] = gf.stem
            gmeta["body"] = gbody
            graders.append(gmeta)
        cases.append({"dir": case_dir, "name": meta.get("name", case_dir.name),
                      "meta": meta, "prompt": prompt, "graders": graders})
    return cases


# ------------------------------------------------------------------ workspace

def install_skills(config, workspace, case_meta=None):
    """Populate <workspace>/.claude/skills for the configuration.

    A case may name a synthetic skill set (`skills: test-skill`): A and B then install
    fixtures/<set>/A/* and fixtures/<set>/B/* instead of the real packs. C installs nothing."""
    if config == "C":
        return []
    target = workspace / ".claude" / "skills"
    target.mkdir(parents=True)
    installed = []
    synthetic = (case_meta or {}).get("skills")
    if synthetic:
        src = FIXTURES / str(synthetic) / config
        if not src.is_dir():
            sys.exit("synthetic skill set %s has no %s variant at %s" % (synthetic, config, src))
        for pack in sorted(p for p in src.iterdir() if p.is_dir()):
            shutil.copytree(pack, target / pack.name)
            installed.append(pack.name)
        return installed
    if config == "A":
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["bash", "-c", "git archive v1-skills skills | tar -x -C \"$0\"", tmp],
                           cwd=REPO, check=True)
            for pack in sorted((Path(tmp) / "skills").iterdir()):
                shutil.copytree(pack, target / pack.name)
                installed.append(pack.name)
    elif config == "B":
        v2 = REPO / "v2"
        for pack in sorted(p for p in v2.iterdir() if p.is_dir()):
            shutil.copytree(pack, target / pack.name)
            installed.append(pack.name)
        for pack in sorted(p for p in (REPO / "skills").iterdir() if p.is_dir()):
            if pack.name in installed or pack.name in V2_DELETED:
                continue
            shutil.copytree(pack, target / pack.name)
            installed.append(pack.name)
    return installed


JUDGE_VOTES = 1  # Opus 5 judge; the 3-vote majority was a workaround for Haiku's noise (--judge-votes)
JUDGE_MATERIAL_LIMIT = 60000
REAL_AUTH = Path.home() / ".stream" / "auth.yaml"
AUTH_LOCK = Path(tempfile.gettempdir()) / "stream-evals-auth.lock"


def prepare_home(run_ws_root, account_auth):
    """A per-run HOME so the agent never sees the operator's caches or, unless the
    case asks for it, the CLI account login.

    Account auth is a ROTATING credential: the CLI rotates the refresh token on use,
    so a static copy goes stale and two copies invalidate each other. Cases with
    `account_auth: true` get the CURRENT ~/.stream/auth.yaml copied in, and the
    rotated file is copied back after the run (see finish_home). Those cases hold
    a file lock for the whole run so concurrent suites never refresh the same pair.
    Everything else runs logged out - the realistic state for them anyway.
    """
    home = run_ws_root / "home"
    stream_dir = home / ".stream"
    stream_dir.mkdir(parents=True)
    if account_auth:
        if not REAL_AUTH.exists():
            sys.exit("case needs account auth but %s is missing - run `getstream login`" % REAL_AUTH)
        shutil.copy(REAL_AUTH, stream_dir / "auth.yaml")
        os.chmod(stream_dir / "auth.yaml", 0o600)
    real = Path.home() / ".stream"
    for name in ("config.yaml", "latest"):
        if (real / name).exists():
            shutil.copy(real / name, stream_dir / name)
    if (real / "docs").exists():
        os.symlink(real / "docs", stream_dir / "docs")
    return home


def finish_home(home, account_auth):
    """Carry a rotated account token back to the operator's login."""
    if not account_auth:
        return
    sandbox_auth = home / ".stream" / "auth.yaml"
    if sandbox_auth.exists() and sandbox_auth.read_bytes() != REAL_AUTH.read_bytes():
        shutil.copy(sandbox_auth, REAL_AUTH)
        os.chmod(REAL_AUTH, 0o600)
        print("    (account auth rotated during the run; carried back to %s)" % REAL_AUTH)


class AuthLock:
    """Serialize account-auth runs across concurrently running suites."""

    def __init__(self, enabled):
        self.enabled = enabled
        self.fh = None

    def __enter__(self):
        if self.enabled:
            import fcntl
            self.fh = open(AUTH_LOCK, "w")
            fcntl.flock(self.fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        if self.fh:
            import fcntl
            fcntl.flock(self.fh, fcntl.LOCK_UN)
            self.fh.close()


GETSTREAM_SHIM = """#!/bin/bash
# Eval sandbox shim. Skills are installed by the harness (or none, in the control) - never by the
# agent: `getstream skills <name> --claude` writes to the operator's real ~/.claude/skills (it does not
# honor the sandbox HOME), which contaminated 35 control runs on 2026-08-27/28.
if [ "$1" = "skills" ]; then
  echo "getstream skills is disabled in the eval sandbox: skills are preinstalled by the harness." >&2
  exit 2
fi
exec "%s" "$@"
"""


def install_shims(run_ws_root):
    """A bin/ dir put first on the agent's PATH. Returns it, or None if getstream is not installed."""
    real = shutil.which("getstream")
    if not real:
        return None
    bindir = run_ws_root / "bin"
    bindir.mkdir(exist_ok=True)
    shim = bindir / "getstream"
    shim.write_text(GETSTREAM_SHIM % real)
    shim.chmod(0o755)
    return bindir


def reachable_skill_text(workspace_root):
    """SKILL.md files an agent could reach by walking up from the workspace root, plus the operator's
    user-level skills dir. Claude Code and its built-in `run` skill both look there; the getstream CLI
    installs there. Must be empty before and after every run, in every configuration."""
    found = set()
    d = Path(workspace_root).resolve()
    while True:
        found.update(str(p) for p in d.glob(".claude/skills/*/SKILL.md"))
        if d.parent == d:
            break
        d = d.parent
    found.update(str(p) for p in (Path.home() / ".claude" / "skills").glob("*/SKILL.md"))
    return sorted(found)


def agent_env(config_dir, home):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir), HOME=str(home))
    env.pop("CLAUDECODE", None)
    bindir = Path(home).parent / "bin"
    if bindir.is_dir():
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    # Keep the expensive caches warm across runs; they hold no credentials.
    npm_cache = Path.home() / ".npm"
    if npm_cache.exists():
        env.setdefault("npm_config_cache", str(npm_cache))
    pw_cache = Path.home() / ".cache" / "ms-playwright"
    if pw_cache.exists():
        env.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(pw_cache))
    return env


def prepare_workspace(case, config, run_dir, workspace_root):
    # Workspaces must live OUTSIDE this repo: Claude Code walks up to the git root
    # to load project skills, and the repo's own .claude/skills would leak into
    # every configuration (observed in the first run: C invoked a Stream skill).
    run_ws_root = workspace_root / run_dir.parent.name / run_dir.name
    if run_ws_root.exists():
        shutil.rmtree(run_ws_root)
    run_ws_root.mkdir(parents=True)
    home = prepare_home(run_ws_root, bool(case["meta"].get("account_auth")))
    install_shims(run_ws_root)
    workspace = run_ws_root / "workspace"
    fixture = case["meta"].get("fixture")
    if fixture:
        src = FIXTURES / fixture
        if not src.is_dir():
            sys.exit("fixture not found: %s" % src)
        shutil.copytree(src, workspace, symlinks=True)
    else:
        workspace.mkdir(parents=True)
    if case["meta"].get("creds"):
        creds = FIXTURES / "creds" / ".stream"
        if not creds.is_dir():
            sys.exit("creds fixture missing: %s (run `getstream init` there once)" % creds)
        shutil.copytree(creds, workspace / ".stream")
    installed = install_skills(config, workspace, case["meta"])
    return workspace, installed, home


def snapshot(workspace):
    """Hash every text file so graders can tell changed/new files from fixture files."""
    hashes = {}
    for path in walk_files(workspace):
        hashes[str(path.relative_to(workspace))] = hashlib.sha1(path.read_bytes()).hexdigest()
    return hashes


def walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def changed_files(workspace, before):
    out = []
    for path in walk_files(workspace):
        rel = str(path.relative_to(workspace))
        digest = hashlib.sha1(path.read_bytes()).hexdigest()
        if before.get(rel) != digest:
            out.append(path)
    return sorted(out)


# ------------------------------------------------------------------ the agent

RUNNERS = EVALS / "runners"   # gitignored; one persistent CLAUDE_CONFIG_DIR per runner


class Runner:
    """An independently authenticated Claude Code session for the eval agents.

    Each runner is a persistent CLAUDE_CONFIG_DIR with its own OAuth login (its own
    rotating refresh token). Runners never share a credential with the operator's session
    or with each other, so a refresh in one cannot log another out. A run checks a runner
    out under a lock (one process per runner at a time), verifies it is still authenticated,
    and returns it afterwards. Create runners with `run.py --add-runner`.
    """

    def __init__(self, path):
        self.path = path
        self.lock_fh = None

    @property
    def name(self):
        return self.path.name

    def status(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.path))
        env.pop("CLAUDECODE", None)
        try:
            proc = subprocess.run(["claude", "auth", "status", "--json"], env=env, capture_output=True,
                                  text=True, timeout=60, stdin=subprocess.DEVNULL)
            return json.loads(proc.stdout.strip())  # pretty-printed multi-line JSON
        except Exception as exc:  # noqa: BLE001 - any failure means "not usable"
            return {"loggedIn": False, "error": str(exc)}

    def logged_in(self):
        st = self.status()
        return bool(st.get("loggedIn") or st.get("logged_in") or st.get("authenticated"))

    def try_acquire(self):
        import fcntl
        self.lock_fh = open(self.path / ".lock", "w")
        try:
            fcntl.flock(self.lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            self.lock_fh.close()
            self.lock_fh = None
            return False

    def release(self):
        if self.lock_fh:
            import fcntl
            fcntl.flock(self.lock_fh, fcntl.LOCK_UN)
            self.lock_fh.close()
            self.lock_fh = None


def list_runners():
    if not RUNNERS.is_dir():
        return []
    return [Runner(p) for p in sorted(RUNNERS.iterdir()) if p.is_dir()]


def acquire_runner(wait=True):
    """Check out a free, authenticated runner; block until one frees up."""
    runners = list_runners()
    if not runners:
        sys.exit("no runners: create one with `python3 evals/run.py --add-runner` (browser login)")
    while True:
        dead = []
        for r in runners:
            if r.try_acquire():
                if r.logged_in():
                    return r
                r.release()
                dead.append(r.name)
        if dead and len(dead) == len(runners):
            sys.exit("no authenticated runner (%s) - re-login with `python3 evals/run.py --login-runner <name>`"
                     % ", ".join(dead))
        if not wait:
            return None
        time.sleep(15)


def add_runner(name=None):
    RUNNERS.mkdir(exist_ok=True)
    if name is None:
        name = "runner-%d" % (len(list_runners()) + 1)
    path = RUNNERS / name
    path.mkdir(exist_ok=True)
    print("Logging in runner %s (its own OAuth session; complete the browser flow)..." % name, flush=True)
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(path))
    env.pop("CLAUDECODE", None)
    subprocess.run(["claude", "auth", "login"], env=env, stdin=subprocess.DEVNULL)
    r = Runner(path)
    print("runner %s: %s" % (name, "authenticated" if r.logged_in() else "NOT authenticated"))
    return 0 if r.logged_in() else 1


def runners_status():
    rs = list_runners()
    if not rs:
        print("no runners")
        return 1
    for r in rs:
        busy = not r.try_acquire()
        if not busy:
            r.release()
        print("%-12s %-18s %s" % (r.name, "authenticated" if r.logged_in() else "NOT authenticated",
                                  "busy" if busy else "free"))
    return 0


def effective_prompt(case, config):
    """Explicit skill invocation: users invoke the skills as slash commands, so cases do too.
    `invoke: stream` (default) prefixes the prompt with `/stream`; `invoke: none` sends it
    bare. C has no skills installed, so it always gets the bare prompt (the control)."""
    prompt = case["prompt"]
    skill = str(case["meta"].get("invoke", "stream"))
    if config == "C" or skill == "none":
        return prompt
    return "/%s %s" % (skill, prompt)


def run_agent(case, workspace, config_dir, model_override, home, config):
    meta = case["meta"]
    cmd = ["claude", "-p", effective_prompt(case, config), "--output-format", "stream-json", "--verbose",
           "--dangerously-skip-permissions", "--max-turns", str(meta.get("max_turns", 10))]
    model = model_override or meta.get("model")
    if model:
        cmd += ["--model", str(model)]
    if meta.get("append_system_prompt"):
        cmd += ["--append-system-prompt", str(meta["append_system_prompt"])]
    env = agent_env(config_dir, home)
    timeout = int(meta.get("timeout_seconds", 300))
    started = time.time()
    # The agent starts dev servers (`npm run dev`, next-server, vite) and never stops them.
    # Run it in its own process group and kill the whole group when the run ends, or the
    # servers outlive the run, pile up across a suite, and eventually OOM the machine.
    proc = subprocess.Popen(cmd, cwd=workspace, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        raw, _ = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        kill_group(proc)
        raw, _ = proc.communicate()
        timed_out = True
    finally:
        kill_group(proc)
    return parse_transcript(raw or "", timed_out, time.time() - started), raw or ""


def kill_group(proc):
    import signal
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        time.sleep(1)
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def parse_transcript(raw, timed_out, wall):
    tools, last_message, metrics = [], "", {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "assistant":
            for c in ev.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    tools.append({"name": c.get("name", ""), "input": c.get("input", {})})
        elif ev.get("type") == "result":
            last_message = ev.get("result") or ""
            metrics = {"cost_usd": ev.get("total_cost_usd"), "turns": ev.get("num_turns"),
                       "duration_ms": ev.get("duration_ms"), "is_error": ev.get("is_error"),
                       "subtype": ev.get("subtype")}
    metrics["timed_out"] = timed_out
    metrics["wall_s"] = round(wall, 1)
    return {"tools": tools, "last_message": last_message, "metrics": metrics}


# ----------------------------------------------------------------------- graders

def tool_lines(transcript):
    return ["%s %s" % (t["name"], json.dumps(t["input"], sort_keys=True)) for t in transcript["tools"]]


def read_text(path):
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb"}

# Comment stripping for regex graders over files. A migration that explains itself in a comment
# ("Sendbird's 3600 seconds becomes 60") is not a migration that left 3600 in the code; and a
# comment that mentions addMembers is not code that calls it. String literals are preserved so
# `//` inside a URL is not treated as a comment.
_C_STYLE = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css", ".scss", ".java", ".kt", ".kts", ".swift",
            ".cs", ".cpp", ".cc", ".c", ".h", ".hpp", ".dart", ".go", ".rs", ".m", ".mm"}
_HASH_STYLE = {".py", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".rb", ".toml", ".env", ".gitignore"}
_C_COMMENT = re.compile(r'("(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|`(?:\\.|[^`\\])*`)|/\*[\s\S]*?\*/|//[^\n]*')
_HASH_COMMENT = re.compile(r'("(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\')|#[^\n]*')


def strip_comments(text, suffix):
    if suffix in _C_STYLE:
        return _C_COMMENT.sub(lambda m: m.group(1) or "", text)
    if suffix in _HASH_STYLE:
        return _HASH_COMMENT.sub(lambda m: m.group(1) or "", text)
    return text


def select_files(changed, workspace, pattern=None):
    """The changed files a grader reads. Lockfiles are never authored content and are huge,
    so they are always left out; a glob narrows further, matched against the
    workspace-relative path and against the bare file name (so `*.tsx` means any depth)."""
    out = []
    for p in changed:
        if p.name in LOCKFILES:
            continue
        if pattern:
            rel = os.path.relpath(str(p), str(workspace))
            if not (fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(p.name, pattern)):
                continue
        out.append(p)
    return out


def grade(grader, transcript, workspace, changed, run_dir, judge_model, config_dir):
    """Returns (pass, detail, cost_usd) - cost is nonzero only for llm graders."""
    if grader.get("type") == "llm":
        return judge(grader, transcript, workspace, changed, judge_model, config_dir)
    ok, detail = grade_deterministic(grader, transcript, workspace, changed, run_dir)
    return ok, detail, 0.0


def grade_deterministic(grader, transcript, workspace, changed, run_dir):
    gtype = grader.get("type")
    flags = re.I if "i" in str(grader.get("flags", "")) else 0
    if gtype == "regex":
        target = grader.get("target", "last_message")
        want = grader.get("match", "contains") == "contains"
        if target == "files":
            # Per file, never over a concatenation: a pattern like `a[\s\S]*b` must not be
            # satisfied by `a` in one file and `b` in another (or in the lockfile).
            files = select_files(changed, workspace, grader.get("files"))
            keep_comments = str(grader.get("comments", "strip")) == "keep"
            hits, sample = [], ""
            for p in files:
                text = read_text(p) if keep_comments else strip_comments(read_text(p), p.suffix)
                m = re.search(grader["body"], text, flags)
                if m:
                    hits.append(p)
                    if not sample:  # the matching line, so a verdict can be checked without opening the file
                        line = text[text.rfind("\n", 0, m.start()) + 1:].split("\n", 1)[0].strip()
                        sample = line[:90]
            found = bool(hits)
            names = ", ".join(os.path.relpath(str(p), str(workspace)) for p in hits[:3])
            return found == want, "pattern %s in %d/%d file(s)%s%s: %s" % (
                "found" if found else "absent", len(hits), len(files), (" [" + names + "]") if names else "",
                (" <%s>" % sample) if sample else "", grader["body"][:80])
        if target == "last_message":
            hay = transcript["last_message"]
        elif target == "trace":
            hay = "\n".join(tool_lines(transcript))
        else:
            return False, "unknown target %s" % target
        found = re.search(grader["body"], hay, flags) is not None
        return found == want, "pattern %s: %s" % ("found" if found else "absent", grader["body"][:80])
    if gtype == "tool_used":
        pattern = grader.get("input_match")
        count = 0
        for t in transcript["tools"]:
            if t["name"] != grader.get("tool"):
                continue
            if pattern and not re.search(str(pattern), json.dumps(t["input"], sort_keys=True), flags):
                continue
            count += 1
        lo, hi = int(grader.get("min", 1)), grader.get("max")
        ok = count >= lo and (hi is None or count <= int(hi))
        return ok, "%s x%d (min %d%s)" % (grader.get("tool"), count, lo, ", max %s" % hi if hi is not None else "")
    if gtype == "tool_order":
        lines = tool_lines(transcript)
        first = lambda pat: next((i for i, l in enumerate(lines) if re.search(str(pat), l, flags)), None)
        b, a = first(grader.get("before")), first(grader.get("after"))
        if b is None or a is None:
            return False, "before=%s after=%s (missing)" % (b, a)
        return b < a, "before@%d after@%d" % (b, a)
    if gtype == "changed_files":
        n = len(changed)
        lo, hi = int(grader.get("min", 0)), grader.get("max")
        ok = n >= lo and (hi is None or n <= int(hi))
        names = ", ".join(str(p.relative_to(workspace)) for p in changed[:8])
        return ok, "%d changed file(s)%s" % (n, (": " + names) if names else "")
    if gtype == "file_exists":
        hits = glob.glob(str(workspace / str(grader.get("path"))), recursive=True)
        exists = len(hits) > 0
        want = grader.get("match", "exists") == "exists"
        return exists == want, "%d match(es) for %s" % (len(hits), grader.get("path"))
    if gtype == "script":
        env = dict(os.environ, EVAL_WORKSPACE=str(workspace), EVAL_ROOT=str(EVALS),
                   EVAL_TRANSCRIPT=str(run_dir / "transcript.jsonl"),
                   EVAL_LAST_MESSAGE=str(run_dir / "last_message.md"),
                   EVAL_CHANGED_FILES="\n".join(str(p) for p in changed))
        proc = subprocess.run(["bash", "-c", grader["body"]], cwd=workspace, env=env,
                              capture_output=True, text=True, timeout=900)
        detail = (proc.stdout + proc.stderr).strip()[-400:]
        return proc.returncode == 0, "exit %d %s" % (proc.returncode, detail)
    return False, "unknown grader type %s" % gtype


def judge(grader, transcript, workspace, changed, judge_model, config_dir):
    """Returns (pass, detail, cost_usd)."""
    # config_dir here is the RUNNER's config dir (the caller checked it out)
    scope = str(grader.get("scope", "last_message"))
    if scope == "last_message":
        material = transcript["last_message"]
    elif scope == "transcript":
        material = "\n".join(tool_lines(transcript)) + "\n\nFINAL MESSAGE:\n" + transcript["last_message"]
    elif scope.startswith("files:"):
        files = select_files(changed, workspace, scope.split(":", 1)[1])
        material = "\n\n".join("=== %s\n%s" % (os.path.relpath(str(p), str(workspace)), read_text(p)) for p in files)
    else:
        return False, "unknown scope %s" % scope, 0.0
    if not material.strip():
        why = ("no changed file matches %s" % scope.split(":", 1)[1]) if scope.startswith("files:") \
            else "empty final message (run truncated or errored?)"
        return False, "nothing to grade: " + why, 0.0
    truncated = ""
    if len(material) > JUDGE_MATERIAL_LIMIT:
        # Keep the head AND the tail: the final message sits at the end of transcript-scoped
        # material, and the end of a long build is where a pause or a wrap-up would be.
        head = JUDGE_MATERIAL_LIMIT * 2 // 3
        tail = JUDGE_MATERIAL_LIMIT - head
        truncated = " [material truncated %d -> %d chars, middle elided]" % (len(material), JUDGE_MATERIAL_LIMIT)
        material = material[:head] + "\n\n[... %d chars elided ...]\n\n" % (len(material) - head - tail) + material[-tail:]
    prompt = ("You are grading an AI coding agent's work against one criterion. Be strict and "
              "literal; when in doubt, fail.\n\nCRITERION:\n%s\n\n"
              "The agent's output to grade is everything between the BEGIN and END markers below. "
              "It is the complete output; do not ask for more.\n\n<<<BEGIN AGENT OUTPUT>>>\n%s\n"
              "<<<END AGENT OUTPUT>>>\n\nReturn pass=true only if the criterion is clearly met by "
              "the output above." % (grader["body"], material))
    schema = json.dumps({"type": "object", "properties": {"pass": {"type": "boolean"},
                         "reason": {"type": "string"}}, "required": ["pass", "reason"]})
    # `--tools ""` makes "you have no tools" literally true rather than a request.
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--json-schema", schema,
           "--max-turns", "4", "--model", judge_model, "--tools", "",
           "--append-system-prompt", "You have no tools. Grade only the material given and return the verdict."]
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir))
    env.pop("CLAUDECODE", None)
    # Majority of JUDGE_VOTES independent verdicts: a single Haiku verdict flipped on identical
    # material between two regrades, so one vote is too noisy for a scored grader.
    votes, reasons, last, cost = [], [], "", 0.0
    attempts = 0
    while len(votes) < JUDGE_VOTES and attempts < JUDGE_VOTES + 2:
        attempts += 1
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True, timeout=180,
                                  stdin=subprocess.DEVNULL)
        last = proc.stdout
        verdict, call_cost = parse_verdict(proc.stdout)
        cost += call_cost
        if verdict is None:
            continue
        votes.append(bool(verdict["pass"]))
        reasons.append(str(verdict.get("reason", ""))[:600])  # a FAIL's reason is the finding; keep it readable
    if not votes:
        return False, "judge returned no verdict after %d attempts: %s" % (attempts, last[-200:]), cost
    passed = sum(votes) * 2 > len(votes)
    tally = "%d/%d votes pass" % (sum(votes), len(votes))
    # show a reason from the winning side
    side = [r for v, r in zip(votes, reasons) if v == passed]
    return passed, "%s%s - %s" % (tally, truncated, side[0] if side else reasons[0]), cost


def parse_verdict(stdout):
    """(verdict dict or None, cost_usd of the call)."""
    # The CLI may print warnings before the JSON document; parse from the first '{' line.
    lines = stdout.splitlines()
    start = next((i for i, l in enumerate(lines) if l.lstrip().startswith("{")), None)
    if start is None:
        return None, 0.0
    try:
        ev = json.loads("\n".join(lines[start:]))
    except ValueError:
        return None, 0.0
    cost = ev.get("total_cost_usd") if isinstance(ev.get("total_cost_usd"), (int, float)) else 0.0
    verdict = ev.get("structured_output")
    text = ev.get("result") if isinstance(ev.get("result"), str) else ""
    if verdict is None and text:
        try:
            verdict = json.loads(text)
        except ValueError:
            m = re.search(r'"pass"\s*:\s*(true|false)', text)
            if m:
                reason = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
                verdict = {"pass": m.group(1) == "true", "reason": reason.group(1) if reason else text[:300]}
    if isinstance(verdict, dict) and "pass" in verdict:
        return verdict, cost
    return None, cost


# ------------------------------------------------------------------ provenance

def git_out(*args):
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def claude_version():
    try:
        return subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30,
                              stdin=subprocess.DEVNULL).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def skills_digest(workspace):
    """sha1 over the installed skill text - the thing a run actually tested. Two runs with
    the same digest ran the same skills, whatever the repo SHA says (working tree edits count)."""
    root = workspace / ".claude" / "skills"
    if not root.is_dir():
        return None
    h = hashlib.sha1()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()[:12]


def provenance(config, agent_model, judge_model, workspace):
    info = {"agent_model": agent_model, "judge_model": judge_model, "claude_version": claude_version(),
            "repo_sha": git_out("rev-parse", "--short", "HEAD"),
            "repo_dirty": bool(git_out("status", "--porcelain")),
            "skills_digest": skills_digest(workspace)}
    if config == "A":
        info["v1_skills_sha"] = git_out("rev-parse", "--short", "v1-skills")
    return info


# ------------------------------------------------------------------------ main

FILE_GRADERS = {"script", "file_exists", "changed_files"}


def grader_applies(grader, config):
    """`configs: A` or `configs: [A, C]` restricts a grader to those configurations."""
    wanted = grader.get("configs")
    if wanted is None:
        return True
    if not isinstance(wanted, list):
        wanted = [wanted]
    return str(config) in [str(w) for w in wanted]


def needs_workspace(grader):
    if grader.get("type") in FILE_GRADERS:
        return True
    if grader.get("type") == "regex" and grader.get("target") == "files":
        return True
    if grader.get("type") == "llm" and str(grader.get("scope", "")).startswith("files:"):
        return True
    return False


def regrade(run_root, judge_model, keep_llm=False):
    """Re-run graders over a finished run's saved transcripts and kept workspaces.

    Graders were the wrong thing more often than agents were; this makes fixing a grader
    free instead of costing another agent run. Graders that need the workspace keep their
    old verdict when the workspace was not kept (passing runs delete theirs). With keep_llm,
    llm graders keep their previous verdict too - a deterministic-grader fix then regrades
    a whole suite for free.
    """
    run_root = Path(run_root).resolve()
    runner = acquire_runner()
    config_dir = runner.path
    cases = {c["dir"].name: c for c in load_cases(None)}
    summary, any_fail = [], False
    for result_file in sorted(run_root.glob("*/run-*/result.json")):
        old = json.loads(result_file.read_text())
        case = cases.get(old["case"])
        if not case:
            continue
        run_dir = result_file.parent
        raw = (run_dir / "transcript.jsonl").read_text()
        transcript = parse_transcript(raw, old["metrics"].get("timed_out", False), old["metrics"].get("wall_s", 0))
        transcript["metrics"] = old["metrics"]
        workspace = Path(old["workspace"]) if old.get("workspace") else None
        have_ws = workspace is not None and workspace.exists()
        changed = [workspace / p for p in old.get("changed_files", [])] if have_ws else []
        old_verdicts = {g["name"]: g for g in old["graders"]}
        results, scored_pass, judge_cost = [], True, 0.0
        print("[regrade] %s run %d" % (old["case"], old["run"]), flush=True)
        for g in case["graders"]:
            if not grader_applies(g, old.get("config")):
                continue
            if needs_workspace(g) and not have_ws and g["name"] in old_verdicts:
                prev = old_verdicts[g["name"]]
                ok, detail = prev["pass"], prev["detail"] + " (kept: workspace not retained)"
            elif keep_llm and g.get("type") == "llm" and g["name"] in old_verdicts \
                    and not str(old_verdicts[g["name"]].get("detail", "")).startswith("judge returned no verdict"):
                # keep a real verdict; a judge call that itself failed (spend limit, auth) is re-run
                prev = old_verdicts[g["name"]]
                ok, detail = prev["pass"], prev["detail"]
            else:
                try:
                    ok, detail, cost = grade(g, transcript, workspace or run_dir, changed, run_dir, judge_model, config_dir)
                    judge_cost += cost
                except Exception as exc:
                    ok, detail = False, "grader error: %s" % exc
            scored = g.get("scored", True)
            if scored and not ok:
                scored_pass = False
            results.append({"name": g["name"], "type": g.get("type"), "scored": scored, "pass": ok, "detail": detail})
            print("    %s %-40s %s%s" % ("PASS" if ok else "FAIL", g["name"], "" if scored else "(indicator) ", detail[:100]))
        # The regrade's judge spend replaces the original's: the same graders were re-judged
        # (unless llm verdicts were kept, in which case the original spend stands).
        if not keep_llm:
            old["metrics"]["judge_cost_usd"] = round(judge_cost, 6)
        old.update({"pass": scored_pass, "graders": results, "regraded": True})
        old.setdefault("provenance", {})["judge_model_regrade"] = judge_model
        result_file.write_text(json.dumps(old, indent=2))
        summary.append(old)
        any_fail |= not scored_pass
    write_summary(run_root, summary, run_root.name.rsplit("-", 1)[-1], run_root.name)
    runner.release()
    return 1 if any_fail else 0


def grader_tally(record):
    """(passed, scored) over the run's scored graders."""
    scored = [g for g in record["graders"] if g.get("scored", True)]
    return sum(1 for g in scored if g["pass"]), len(scored)


def run_status(metrics):
    if metrics.get("timed_out"):
        return "timeout"
    if metrics.get("contaminated"):
        return "contaminated"
    sub = metrics.get("subtype") or "?"
    if metrics.get("is_error") and sub == "success":
        # The CLI reports e.g. a spend-limit refusal as subtype "success" with is_error true and a
        # one-line "result"; that is an environment error, not an agent outcome. (is_error is also
        # true for error_max_turns - that keeps its own subtype.)
        return "error"
    return sub


def environment_error(transcript):
    """A run that never really ran: the CLI refused (spend limit, auth, rate limit) and returned
    the refusal as the result. Continuing a suite past this only produces empty runs."""
    m = transcript["metrics"]
    if not (m.get("is_error") and (m.get("subtype") or "") == "success"):
        return None
    msg = (transcript["last_message"] or "").strip()
    if (m.get("turns") or 0) <= 1 and (m.get("cost_usd") or 0) == 0:
        return msg[:200] or "CLI error with empty result"
    return None


def run_truncated(metrics):
    """A run that timed out, ran out of turns, or errored: labeled, not counted as content."""
    return bool(metrics.get("timed_out")) or run_status(metrics) != "success"


def write_summary(run_root, summary, config, stamp):
    (run_root / "summary.json").write_text(json.dumps(summary, indent=2))
    prov = next((r.get("provenance") for r in summary if (r.get("provenance") or {}).get("agent_model")), None) or {}
    lines = ["# Eval run %s (config %s)" % (stamp, config), ""]
    if prov:
        lines += ["agent %s, judge %s, claude %s, repo %s%s%s" % (
            prov.get("agent_model"), prov.get("judge_model"), prov.get("claude_version"),
            prov.get("repo_sha"), " (dirty)" if prov.get("repo_dirty") else "",
            ", v1-skills %s" % prov["v1_skills_sha"] if prov.get("v1_skills_sha") else ""), ""]
    lines += ["| case | run | graders | all pass | run status | failed graders | cost (agent+judge) | turns | wall |",
              "|---|---|---|---|---|---|---|---|---|"]
    tot_pass = tot_scored = 0
    tot_agent = tot_judge = 0.0
    truncated = ambiguous = 0
    for r in summary:
        failed = ", ".join(g["name"] for g in r["graders"] if g["scored"] and not g["pass"]) or "-"
        m = r["metrics"]
        p, s = grader_tally(r)
        agent_cost = m["cost_usd"] if isinstance(m.get("cost_usd"), (int, float)) else 0.0
        judge_cost = m.get("judge_cost_usd") or 0.0
        tot_agent += agent_cost
        tot_judge += judge_cost
        tot_pass += p
        tot_scored += s
        if run_truncated(m):
            # A pass in a truncated run is a pass; a failure may just be the budget. Count both,
            # flag the failures as ambiguous.
            truncated += 1
            ambiguous += s - p
        lines.append("| %s | %d | %d/%d%s | %s | %s | %s | $%.2f+%.2f | %s | %ss |" % (
            r["case"], r["run"], p, s, " T" if run_truncated(m) else "", "yes" if r["pass"] else "no",
            run_status(m), failed, agent_cost, judge_cost, m.get("turns"), m.get("wall_s")))
    lines += ["", "**graders passed: %d/%d** over %d run(s); runs with every grader passing: %d/%d; "
              "truncated runs (T): %d, holding %d failure(s) that may be budget rather than content; "
              "cost $%.2f agent + $%.2f judge = $%.2f" % (
                  tot_pass, tot_scored, len(summary), sum(1 for r in summary if r["pass"]), len(summary),
                  truncated, ambiguous, tot_agent, tot_judge, tot_agent + tot_judge)]
    (run_root / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines))


def self_check(workspace_root):
    """Static pre-flight: every called top-level name is defined (py_compile cannot tell -
    a missing helper broke the first Stage 1 attempt), cases parse, fixtures exist, and no
    skill text is reachable from the sandbox by walking up from the workspace root."""
    import ast, builtins
    tree = ast.parse(Path(__file__).read_text())
    defined = set(dir(builtins)) | {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    defined |= {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
    defined |= {a.asname or a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    problems = ["undefined name: %s" % c for c in sorted(calls - defined)]
    for case in load_cases(None):
        fx = case["meta"].get("fixture")
        if fx and not (FIXTURES / str(fx)).is_dir():
            problems.append("%s: fixture %s missing" % (case["dir"].name, fx))
        sk = case["meta"].get("skills")
        if sk:
            for cfg in ("A", "B"):
                if not (FIXTURES / str(sk) / cfg).is_dir():
                    problems.append("%s: synthetic skill set %s has no %s variant" % (case["dir"].name, sk, cfg))
        for g in case["graders"]:
            if g.get("type") not in ("regex", "tool_used", "tool_order", "file_exists", "changed_files", "script", "llm"):
                problems.append("%s/%s: unknown grader type %s" % (case["dir"].name, g["name"], g.get("type")))
    if not list_runners():
        problems.append("no runners (run --add-runner)")
    # Skill text reachable from the sandbox by directory walk. Claude Code and its built-in `run`
    # skill look for .claude/skills/*/SKILL.md in the workspace's ancestors, and the getstream CLI
    # installs there. Nothing may be there in any configuration - and main() re-checks after every run.
    for p in reachable_skill_text(workspace_root):
        problems.append("skill text reachable from the sandbox by directory walk: %s" % p)
    if not shutil.which("getstream"):
        problems.append("getstream CLI not on PATH (the sandbox shim wraps it)")
    print("\n".join(problems) if problems else "check ok: %d cases, %d runners, no skill text reachable from %s"
          % (len(load_cases(None)), len(list_runners()), workspace_root))
    return 1 if problems else 0


def main():
    global JUDGE_VOTES
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regrade", metavar="RUN_DIR", help="re-run graders over a finished run (no agent calls)")
    ap.add_argument("--regrade-keep-llm", action="store_true",
                    help="with --regrade: keep the previous llm verdicts, re-run only deterministic graders (free)")
    ap.add_argument("--add-runner", nargs="?", const="", metavar="NAME", help="create + log in a new runner (browser flow)")
    ap.add_argument("--login-runner", metavar="NAME", help="re-login an existing runner")
    ap.add_argument("--runners", action="store_true", help="show runner status")
    ap.add_argument("--check", action="store_true", help="static pre-flight: names, cases, fixtures, runners")
    ap.add_argument("--config", choices=["A", "B", "C"], default="B")
    ap.add_argument("--case", help="glob over case directory names")
    ap.add_argument("--runs", type=int, help="override runs per case")
    ap.add_argument("--model", default="claude-opus-5", help="agent model (default: Opus 5)")
    ap.add_argument("--judge-model", default="claude-opus-5", help="judge model (default: Opus 5)")
    ap.add_argument("--judge-votes", type=int, default=JUDGE_VOTES,
                    help="independent judge verdicts per llm grader, majority wins (default %d)" % JUDGE_VOTES)
    ap.add_argument("--no-keep", dest="keep", action="store_false", default=True,
                    help="delete the workspaces of passing runs (default: keep every workspace, so a "
                         "wrongly PASSING file grader can still be regraded; prune ~/.cache/stream-evals by hand)")
    ap.add_argument("--workspace-root", default="/var/tmp/stream-evals",
                    help="where run workspaces are created: outside this repo, on a real disk (not tmpfs), and with "
                         "NO .claude directory in any ancestor - ~/.cache/... sat under ~/.claude's parent and the "
                         "control found CLI-installed skills there")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    JUDGE_VOTES = max(1, args.judge_votes)
    if args.add_runner is not None:
        return add_runner(args.add_runner or None)
    if args.login_runner:
        return add_runner(args.login_runner)
    if args.runners:
        return runners_status()
    if args.check:
        return self_check(args.workspace_root)
    if args.regrade:
        return regrade(args.regrade, args.judge_model, keep_llm=args.regrade_keep_llm)

    cases = load_cases(args.case)
    if args.list:
        for c in cases:
            print("%-50s %d grader(s)" % (c["dir"].name, len(c["graders"])))
        return 0
    if not cases:
        sys.exit("no cases matched")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_root = RESULTS / ("%s-%s" % (stamp, args.config))
    run_root.mkdir(parents=True)
    workspace_root = Path(args.workspace_root).resolve() / run_root.name
    if REPO in workspace_root.parents or workspace_root == REPO:
        sys.exit("--workspace-root must be outside the repo (project skills would leak in)")
    summary, any_fail = [], False

    for case in cases:
        runs = args.runs or int(case["meta"].get("runs", 1))
        for i in range(1, runs + 1):
            run_dir = run_root / case["dir"].name / ("run-%d" % i)
            run_dir.mkdir(parents=True)
            account_auth = bool(case["meta"].get("account_auth"))
            runner = acquire_runner()
            config_dir = runner.path
            try:
                with AuthLock(account_auth):
                    workspace, installed, home = prepare_workspace(case, args.config, run_dir, workspace_root)
                    before = snapshot(workspace)
                    print("[%s] %s run %d/%d (runner %s) ..." % (args.config, case["dir"].name, i, runs, runner.name), flush=True)
                    transcript, raw = run_agent(case, workspace, config_dir, args.model, home, args.config)
                    finish_home(home, account_auth)
            finally:
                pass  # released after grading (the judge uses the same runner)
            (run_dir / "transcript.jsonl").write_text(raw)
            (run_dir / "last_message.md").write_text(transcript["last_message"])
            env_err = environment_error(transcript)
            if env_err:
                # Spend limit / auth / rate limit: every further run would fail the same way (the
                # quick-16 sweep produced 60 empty runs this way). Stop; results so far are kept.
                runner.release()
                shutil.rmtree(run_dir, ignore_errors=True)
                write_summary(run_root, summary, args.config, stamp)
                sys.exit("\nenvironment error from the CLI, suite aborted before %s run %d: %s\n"
                         "results so far: %s" % (case["dir"].name, i, env_err, run_root))
            # Provenance before grading: the skills digest reads the workspace as tested.
            prov = provenance(args.config, args.model, args.judge_model, workspace)
            changed = changed_files(workspace, before)
            results, scored_pass, judge_cost = [], True, 0.0
            for g in case["graders"]:
                if not grader_applies(g, args.config):
                    continue
                try:
                    ok, detail, cost = grade(g, transcript, workspace, changed, run_dir, args.judge_model, config_dir)
                    judge_cost += cost
                except Exception as exc:  # a broken grader is a failed grader, not a crashed run
                    ok, detail = False, "grader error: %s" % exc
                scored = g.get("scored", True)
                if scored and not ok:
                    scored_pass = False
                results.append({"name": g["name"], "type": g.get("type"), "scored": scored,
                                "pass": ok, "detail": detail})
                mark = "PASS" if ok else "FAIL"
                # Config tag on every line: two workers appending to one log interleave, and an
                # untagged FAIL under the other worker's header line reads as the wrong config.
                print("    [%s] %s %-40s %s%s" % (args.config, mark, g["name"], "" if scored else "(indicator) ", detail[:100]))
            if case["meta"].get("after_script"):
                # Case-level cleanup (e.g. undo a channel-type change the agent made on the
                # shared eval app) so the next run starts from the same state.
                subprocess.run(["bash", "-c", str(case["meta"]["after_script"])], cwd=workspace,
                               env=dict(os.environ, HOME=str(home)), capture_output=True, timeout=300)
            transcript["metrics"]["judge_cost_usd"] = round(judge_cost, 6)
            # Control integrity, checked after EVERY run in every configuration: did skill text become
            # reachable (the getstream CLI installs into the operator's real ~/.claude/skills), or did the
            # agent try to install skills? The shim refuses the install; the attempt is still recorded.
            leak = reachable_skill_text(workspace_root.parent)
            install_attempts = sum(1 for t in transcript["tools"] if t["name"] == "Bash"
                                   and re.search(r"\bgetstream\s+skills\b", str(t["input"].get("command", ""))))
            transcript["metrics"]["skill_install_attempts"] = install_attempts
            if leak:
                transcript["metrics"]["contaminated"] = leak
            record = {"case": case["dir"].name, "config": args.config, "run": i, "pass": scored_pass,
                      "skills": installed, "workspace": str(workspace) if not scored_pass or args.keep else None,
                      "metrics": transcript["metrics"], "graders": results,
                      "changed_files": [str(p.relative_to(workspace)) for p in changed],
                      "provenance": prov, "runner": runner.name}
            (run_dir / "result.json").write_text(json.dumps(record, indent=2))
            runner.release()
            summary.append(record)
            any_fail |= not scored_pass
            if leak:
                write_summary(run_root, summary, args.config, stamp)
                sys.exit("\nCONTROL INTEGRITY: skill text became reachable from the sandbox during %s run %d - "
                         "run marked contaminated, suite aborted:\n  %s\nRemove it, then rerun this case onward."
                         % (case["dir"].name, i, "\n  ".join(leak)))
            if scored_pass and not args.keep:
                shutil.rmtree(workspace.parent, ignore_errors=True)  # workspace + its HOME
            m = transcript["metrics"]
            p, s = grader_tally(record)
            print("    [%s] => %d/%d graders%s  cost $%.2f agent + $%.2f judge  turns %s  %ss%s" % (
                  args.config, p, s, "" if scored_pass else " (FAIL)", m.get("cost_usd") or 0.0, judge_cost,
                  m.get("turns"), m.get("wall_s"), "  [%s]" % run_status(m) if run_truncated(m) else ""), flush=True)

    write_summary(run_root, summary, args.config, stamp)
    print("\nresults: %s" % run_root)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
