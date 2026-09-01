# Skill evals

The only real test of a skill is running prompts with it. This directory holds a
harness that does exactly that: it runs each prompt through `claude -p` in an isolated
sandbox with a chosen set of skills installed, grades the outcome, and writes a report.

## The three documents

- **This file** - how to run the harness and what tests exist.
- **`FINDINGS.md`** - the cumulative log of what the evals taught us (judged findings,
  each with a disposition: skill / grader / fixture / harness / accepted / open).
- **`reports/<date>-<what>.md`** - one per comparison run: the objective pass/fail matrix
  and per-grader verdicts (generated), plus that run's judged findings (hand-written).

`PLAN.md` is the original test plan and decision record; it is upstream of all three.

## Running

```bash
python3 evals/run.py --check                      # pre-flight, no API calls: run before every suite
python3 evals/run.py --runners                    # runner pool status
python3 evals/run.py --config B                   # all cases, v2 skills
python3 evals/run.py --config C --case "migrate*" # a subset, no skills (control)
python3 evals/run.py --list                       # what cases exist
python3 evals/compare.py evals/results/<run-B> evals/results/<run-C> > evals/reports/<date>.md
```

Configurations: **A** = v1 skills (git tag `v1-skills`), **B** = v2 skills (`v2/` plus the
v1 platform packs), **C** = control, no skills at all. Comparing B to C answers "does the
skill earn its existence, per case"; A to B answers "did the rewrite lose anything".

Each run writes `evals/results/<stamp>-<config>/` with a `summary.md`, a `summary.json`,
and per case the full `transcript.jsonl`, the final message, and `result.json` (grader
verdicts, cost, turns, provenance). Defaults: agent model Opus 5 (`--model`), judge Opus 5
(`--judge-model`, one vote; `--judge-votes 3` for a majority), runs per case from the case's
frontmatter (`--runs` overrides). Cheap cases - the routing questions, the Sendbird snippet
transforms, the audit - run three times; builds run once. A full suite costs roughly $10 (C) to
$20 (B) including the judge and takes 30-45 minutes.

**What is measured.** The unit is the grader, not the case. A case has between 1 and 16
graders, so "cases passed" would mostly measure grader count; the summary and `compare.py`
report **scored graders passed / scored**, summed over a case's runs. A run's all-graders-pass
verdict is still recorded (and drives the exit code), as a secondary line. Runs that timed out,
ran out of turns, or errored are **counted and labeled `T`**, and their failures are tallied
separately as *ambiguous*: a pass in a truncated run is a pass (the file is there, the build
ran), a failure may only be the budget. (Stage 2 settled this: every build run truncated, one
of them at 12/12 - leaving them out would have left a headline made of routing questions.)
Judge spend is metered per run (`metrics.judge_cost_usd`) and shown next to agent spend; the
two are comparable in size for judge-heavy cases.

**Provenance.** Every `result.json` records the agent and judge model, Claude Code version,
repo SHA with a dirty flag, the `v1-skills` tag SHA in A, and a sha1 digest of the installed
skill text. Two runs with the same digest tested the same skills whatever the working tree
did in between; a digest that changes mid-suite means the freeze rule was broken.

**Single-shot.** `claude -p` is one turn of user input: the agent cannot ask and continue.
A case where the ideal behavior is *ask first* cannot be modeled - the run ends at the
question - and a `transcript`-scoped judge sees tool inputs and the final message, never tool
outputs. Write graders (and read verdicts) with that in mind.

## How a run is isolated

Process-level, not an OS sandbox. Per run: a fresh workspace under `/var/tmp/stream-evals/`
(outside this repo - Claude Code would otherwise load the repo's own `.claude/skills/`; on a
real disk, not tmpfs; and with **no `.claude` directory in any ancestor** - see below), a fresh
`HOME` containing only the CLI's non-secret config and a symlink to the docs cache
(`~/.stream/docs` only, never `~/.stream/skills/`, which holds the CLI-installed v1 packs and
would contaminate C), a `CLAUDE_CONFIG_DIR` from the **runner pool**, and a `bin/` first on
`PATH` holding a `getstream` shim that refuses the `skills` subcommand. Skills under test go
into `<workspace>/.claude/skills/`. The agent runs with `--dangerously-skip-permissions` and
full network, as the operator, in its own process group (killed at run end, so dev servers do
not outlive the run).

**Why the shim and the root.** The control can install skills itself: `getstream skills <name>
--claude` writes to the operator's real `~/.claude/skills` - it does not honor the sandbox
`HOME` - and the built-in `run` skill walks parent directories looking for
`.claude/skills/*/SKILL.md`. On 2026-08-27 a control agent did exactly that and 35 of 48
control runs in the quick-16 sweep read v1 skill text (all discarded and rerun). Three layers
now: skills are installed only by the harness (the shim refuses the CLI's installer in every
configuration; attempts are counted in `metrics.skill_install_attempts`), the workspace root
has no `.claude` ancestor, and `reachable_skill_text()` is checked by `--check` before a suite
and after **every run** - a hit marks the run `contaminated` and aborts the suite.

**Runner pool** (`evals/runners/<name>/`, gitignored): each runner is an independently
authenticated Claude Code session - its own `claude auth login`, its own rotating OAuth
token. Runners never share a credential with the operator's session or with each other, so
a token refresh in a runner cannot log the operator out. A run checks out a free runner under
a lock, verifies it is still authenticated, and returns it afterwards; the judge uses the same
pool. Manage with `--add-runner`, `--login-runner`, `--runners`. The pool is about credential
isolation, not throughput: suites run serially, so a second runner only lets a `--regrade`
run alongside a suite in flight.

The eval test account is a dedicated Stream account, separate from the operator's daily login;
its app is `stream-evals`. Cases marked `creds: true` get that app's project
credentials copied into the workspace. Cases marked `account_auth: true` additionally get
the machine's Stream CLI login - a rotating credential: the current `~/.stream/auth.yaml` is
copied in at run start and the rotated file carried back at run end, under a file lock so
concurrent suites never refresh the same pair. All other cases run logged out. Apps created
by tests are kept, not cleaned up.

Every run keeps its workspace (`--no-keep` deletes passing ones): graders are wrong more
often than agents, and a grader that wrongly *passes* can only be caught by regrading a kept
workspace. Prune `~/.cache/stream-evals/` by hand when disk gets tight. Run suites one at a
time: the host has 8.8 GB and design-match cases spawn Chromium. Keep the laptop awake during
runs - OAuth tokens expire on sleep and the run in flight dies.

## Anatomy of a case

```
evals/cases/<case>/prompt.md       frontmatter (runs, max_turns, timeout_seconds,
                                   fixture, creds) + the prompt text
evals/cases/<case>/graders/*.md    one grader per file; the file name says which failure
                                   it guards
evals/fixtures/<name>/             fixture apps and snippets copied into the workspace
```

Case names are the prompt itself, slugified - refer to a test by its prompt. In A and B the
prompt is sent as `/stream <prompt>` - users invoke the skills explicitly, so the cases do
too (`invoke: none` in the frontmatter sends it bare; C always gets the bare prompt). Grader
types: `regex` (over the final message, the trace, or changed files), `tool_used`,
`tool_order`, `file_exists`, `script` (bash in the workspace, exit code = verdict), `llm`
(Opus 5 judge with a criterion, forced pass/fail + reason; it runs with no tools and is told
so). `scored: false` makes a grader an unscored indicator (e.g. "was a Stream skill invoked" -
meaningless in C).

Regex graders over changed files match **per file**, never over a concatenation - `contains`
passes if some one file matches, `not_contains` if none does - so `a[\s\S]*b` cannot be
satisfied by `a` in one file and `b` in another. Lockfiles are never read. **Comments are
stripped before matching** (`//`, `/* */`, `#`; string literals preserved): a migration that
says `// Sendbird's 3600 seconds becomes 60` did not leave 3600 in the code, and a comment
naming `addMembers` is not a call to it - five of six snippet "failures" in the first sweep
were comments. `comments: keep` opts a grader out. The verdict quotes the matching line.
`files: <glob>` narrows to files whose workspace-relative path or bare name matches
(`*.tsx` = any depth); the `llm` type's `files:<glob>` scope uses the same selection (and
the judge sees comments).

`--regrade <run-dir>` re-runs graders over saved transcripts and kept workspaces;
`--regrade-keep-llm` keeps the previous judge verdicts and re-runs only the deterministic
graders, so a regex fix regrades a whole suite for free.

Two rules keep A/B/C comparable: graders assert **outcomes** (what code came out, which
commands ran), never skill internals; and every grader is named for the failure it guards,
so a skill line with no grader is a deletion candidate and a grader that passes in C is
evidence its line can go.

One deliberate asymmetry: v1 predates the CLI's local docs (`getstream docs`), so the
"reads the docs" graders come in pairs - the local-docs grader scores in B and C
(`configs: [B, C]`; C is the control that shows whether the line earns its place), and an
A-only mirror (`configs: A`, e.g. `uses-web-docs`, `web-docs-read-before-first-edit`) asserts
the same behavior via `WebFetch` of getstream.io. Both still fail an agent that answers from
memory.

## What exists (30 cases)

**Routing tests** (no codebase; how the agent starts): build me a chat app; add a video
call to my Expo app; build an Unreal chat app for iOS; add in-game chat to my game; how
does useCreateChatClient work?; list my channels; what mapping do we need for our Feeds
v2 to v3 migration?; we're migrating off Sendbird; audit my video integration; how do I
list my calls?

**Existing codebase tests** (fixture in, changed files graded):
- Five Sendbird transforms on hand-made snippets - mute user, send handler, poll, file
  message, UIKit page - each grading one kill-list trap (seconds vs minutes, echo
  double-add, inverted poll boolean, atomic upload, `MessageInput` vs `MessageComposer`).
- Migrate this data into Stream - a mock Sendbird export; RFC3339 timestamps, one
  reaction row per user, 64-char channel ids, `getstream import` over the old CLI.
- Add UI for managing channel members (`chat-app`) - the React team's known failure;
  carries the shared no-invented-API grader.
- Upgrade stream-chat-react to the latest major (`chat-app-v13`).
- Audit my Stream integration (`chat-app-audit`, three planted violations; no edits allowed).
- Add chat to this app (`next-with-auth`: real cookie session + an existing token route
  to extend, never duplicate).
- The Create poll button does nothing - fix it (`chat-app-polls`; polls are disabled on
  the eval app's `messaging` type; an `after_script` resets the flag after each run).
- Make this chat app look like reference.png (`chat-app-design` + the WhatsApp screenshot).
- Migrate this app from Sendbird to Stream Chat (`sendbird-app`: a modern UIKit v3 app
  with the traps planted; the two extended-mapping indicators live here).

**New codebase tests** (empty dir; `account_auth: true`, so they run serialized):
build me a Slack-like team chat app; a Twitch-like livestreaming app; a Twitter-like
social app; an AI support agent; a Whatnot-style live shopping app (the label-vs-call-type
test); a chat app that looks like reference.png (Telegram screenshot); and the init-flow
test "build me a DM app", which starts with no project credentials and must follow the
CLI's headless `init --command` instructions.

**Fixtures** (`fixtures/`, source committed; `node_modules`, `.env`, screenshots and
credentials gitignored): `chat-app` sliced from `stream-chat-react/examples/tutorial`
(channel-list step) and its variants `-v13`, `-audit`, `-polls`, `-design`;
`react-dogfood` from `stream-video-js` (its `public/{mediapipe,tf,backgrounds}` runtime assets - 27 MB of wasm and jpeg - are not committed; the transcription case never loads them); hand-made `next-with-auth` and
`sendbird-app`; `sendbird-snippets/*`; `sendbird-export`; `designs/` (personal data,
never committed).

**Shared grader:** `graders/no_invented_api.py` - `tsc --noEmit` passes and every named
import from a Stream package exists in the installed package's typings. Guards the
"don't write Stream SDK code from memory" line directly.
