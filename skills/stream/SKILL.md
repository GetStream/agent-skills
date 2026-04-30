---
name: stream
description: "The fastest way to build with Stream: Chat, Video, Feeds, and Moderation."
license: See LICENSE in repository root
compatibility: Requires Node.js, npm, and the stream CLI binary (see bootstrap.md). Docs-search mode requires only WebFetch — no CLI binary needed.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(stream *),
  Bash(npx *), Bash(npm install *),
  Bash(node -e *), Bash(openssl rand *),
  Bash(mv .scaffold*), Bash(rm -rf .scaffold),
  Bash(ls *),
  Bash(grep *),
  Bash(cat package.json), Bash(cat pubspec.yaml),
  Bash(cat go.mod), Bash(cat requirements.txt), Bash(cat pyproject.toml),
  WebFetch(domain:getstream.io)
---

# Stream — skill router

This file does one job: pick the track from the user's input. Everything else lives in dedicated files.

- **Rules:** read [`RULES.md`](RULES.md) once per session — every non-negotiable rule is stated there.
- **Preflight (tracks A, B, C, E only):** [`preflight.md`](preflight.md) — project signals, CLI gate, credentials + auth check, status line.
- **Install:** skill pack via `npx skills add GetStream/agent-skills` ([skills.sh](https://skills.sh/docs/cli)); CLI binary via [`bootstrap.md`](bootstrap.md). A git-clone alternative is in the [README](../../README.md#install--direct-from-github-no-third-party-cli).

---

## Pick a track

Scan the user's input for the signals below in order. The classifier is deterministic — no probes, no fetches, no CLI checks at this stage.

| Signal in user input | Track |
|---|---|
| Explicit SDK/framework token: `Chat React`, `Video iOS`, `Feeds Node`, `Moderation`, etc. (with or without version) | **D — Docs** |
| Words "docs" or "documentation" | **D** |
| "How do I {X} in {framework}?", "How does {hook/component/method} work?", "What does {SDK thing} do?" | **D** |
| Operational verbs + Stream noun: "list calls", "show channels", "any flagged", "find users", "check {anything}" | **B — CLI** |
| `stream api`, `stream config`, `stream auth` (literal CLI invocation) | **B** |
| "Build me a … app", "scaffold", "create a new …" + Stream product, in an empty/new directory | **A — Builder** |
| "Add Chat/Video/Feeds to this app", "integrate Stream into" — existing project | **E — Enhance** |
| "Install the CLI", "set up stream" with no project context | **C — Bootstrap** |
| Operational verb wrapped in how-to phrasing (e.g. "how do I list my calls?" — docs *or* CLI) | **Ask one disambiguator** |

**Track D carve-out.** Track D answers from documentation only — no preflight, no shell commands, no project inspection. A small read-only probe runs on demand inside `docs-search.md` Step 1a only when the SDK can't be resolved from explicit input.

**Disambiguator.** If the input fits more than one row (typically operational verb + how-to phrasing), ask one short question and wait. Don't probe before the answer:

> Want me to look up the SDK method (docs) or run it now via CLI?

After the answer, route as if the user had given that signal directly.

**Bare `/stream` with no args.** List the tracks below briefly and wait for input. No shell execution.

---

## Tracks

| When | Track | Module |
|---|---|---|
| empty dir, "build me a … app" | A — Build new app | [`builder.md`](builder.md) + [`builder-ui.md`](builder-ui.md) |
| "list calls", `stream api …` | B — CLI / data query | [`cli.md`](cli.md); tricky bodies → [`cli-cookbook.md`](cli-cookbook.md) |
| install the CLI / skill pack | C — Bootstrap | [`bootstrap.md`](bootstrap.md) |
| explicit SDK token, "how do I … in <framework>" | D — Docs search | [`docs-search.md`](docs-search.md) |
| "add Chat to this app", existing project | E — Enhance existing app | [`enhance.md`](enhance.md) (uses [`sdk.md`](sdk.md) + [`references/`](references/)) |

SDK wiring shared by tracks A and E lives in [`sdk.md`](sdk.md).

---

## Reference blueprints

Loaded only after the user names the product (tracks A and E):

| Product | Header (setup + gotchas) | Full blueprints (load per component) |
|---------|--------------------------|--------------------------------------|
| Chat | [`references/CHAT.md`](references/CHAT.md) | [`references/CHAT-blueprints.md`](references/CHAT-blueprints.md) |
| Feeds | [`references/FEEDS.md`](references/FEEDS.md) | [`references/FEEDS-blueprints.md`](references/FEEDS-blueprints.md) |
| Video | [`references/VIDEO.md`](references/VIDEO.md) | [`references/VIDEO-blueprints.md`](references/VIDEO-blueprints.md) |
| Moderation | [`references/MODERATION.md`](references/MODERATION.md) | [`references/MODERATION-blueprints.md`](references/MODERATION-blueprints.md) |

---

## Support

If the user asks for support or how to contact someone, direct them to [getstream.io/contact](https://getstream.io/contact/).
