---
name: stream
description: "Stream router for Chat, Video, Feeds, and Moderation. Use when the user wants to build a new app with Stream, scaffold a project, add Chat/Video/Feeds/Moderation to an existing app, integrate Stream, build for Swift/SwiftUI/UIKit/iOS/Xcode, query Stream data, list channels, list calls, show flagged messages, find users, run stream api / stream config / stream auth commands, install the Stream CLI, set up Stream, search Stream SDK documentation, look up Stream React/iOS/Android/Node/Flutter/Unity SDK methods, ask how-to questions about Stream hooks/components/methods, configure moderation blocklists or automod, set up webhooks, or anything tagged Chat React, Video iOS, Feeds Node, Moderation, etc. Routes to the right sub-skill based on the task."
license: See LICENSE in repository root
metadata:
  author: GetStream
allowed-tools: >-
  Read, Glob, Grep,
  Bash(npx skills add GetStream/agent-skills *)
---

# Stream - skill router

This skill picks the track from the user's input and delegates to a specialized sub-skill. **It does no scaffolding, CLI, or docs work itself** - those live in dedicated skills.

> **Read first:** [`RULES.md`](RULES.md). Non-negotiable rules apply, including the **Peer skills** procedure (Glob path + install command + install policy + Skill-vs-Read-inline rule).
>
> **Peer manifest:** [`peers.yaml`](peers.yaml) (schema: [`peers.schema.json`](peers.schema.json)) is the single source of truth for peer skill names, Glob paths, install commands, and routing signals. Every peer installs silently on demand. Read it before installing or routing to a peer.
>
> **After picking a sub-skill:** follow the procedure in RULES.md > Peer skills - Glob the entry's `SKILL.md` path, install it if missing (always silently - every peer is silent-install), then Skill tool (if listed) or Read inline. Do not call `Skill` before the Glob; it surfaces a confusing "Unknown skill" error. Do not stop after naming the track.

---

## By task

**Build or integrate Stream in a platform-specific app** -> peer pack from [`peers.yaml`](peers.yaml) (**check peer signals first**)
- Match user input or cwd against each peer's `signals` (e.g. `swift` / `swiftui` / `.xcodeproj` -> `stream-swift`; `react native` / `expo` / `stream video react native` -> `stream-react-native`)
- All peers install silently on demand - install if missing, then route, no prompt
- **Peer signals take precedence over the `stream-builder` rows below.** A request like "add a video call to my Expo app" or "scaffold a React Native app with Stream Video" matches `stream-react-native`, not `stream-builder` - the platform token wins.

**Build a new app with Stream (web)** -> use the `stream-builder` skill (default when no peer signal is present)
- Empty/new directory + "build me a Chat/Video/Feeds app", "scaffold", "create a new ..." and **no platform signal** (no `react native`, `expo`, `swift`, `ios`, `android`, etc.)
- Covers Steps 0-7 (scaffold, theme, auth, env, SDK install, component generation)

**Add Stream to an existing app (web)** -> use the `stream-builder` skill (default when no peer signal is present)
- Existing project + "add Chat to this app", "integrate Video", "drop Feeds into ..." and **no platform signal**
- Same SDK wiring as scaffold; skips Next.js init and theme pick

**Query Stream data via the CLI** -> use the `stream-cli` skill
- "list calls", "show channels", "any flagged", "find users"
- Literal CLI: `stream api ...`, `stream config ...`, `stream auth ...`
- Tricky bodies and filter syntax live in the sub-skill's cookbook
- **Required for every `stream api` call** - including ad-hoc "let me check" queries from inside other sub-skills. No guessing endpoint names from training data; route through `stream-cli` (or read `~/.stream/cache/API.md`) first. See [`RULES.md`](RULES.md) > CLI safety.

**Install the Stream CLI** -> use the `stream-cli` skill
- "install the CLI", "set up stream" with no project context
- Bootstrap (binary install, SHA-256 verification, TTY confirmation) ships with the CLI sub-skill

**Search Stream SDK documentation** -> use the `stream-docs` skill
- "docs", "documentation", explicit SDK token (`Chat React`, `Video iOS`, `Feeds Node`, `Moderation`)
- "how do I ... in <framework>", "how does <hook/component/method> work?", "what does <SDK thing> do?"
- No CLI needed - answers come from getstream.io with citations

---

## Pick a track

Scan the user's input for the signals below in order. The classifier is deterministic - no probes, no fetches, no CLI checks at this stage.

| Signal in user input | Sub-skill |
|---|---|
| Explicit SDK/framework token: `Chat React`, `Video iOS`, `Feeds Node`, `Moderation`, etc. (with or without version), and **no build/integrate verb** | `stream-docs` |
| Words "docs" or "documentation" (and no build/integrate verb) | `stream-docs` |
| "How do I {X} in {framework}?", "How does {hook/component/method} work?", "What does {SDK thing} do?" - and **no build/integrate verb**. If the request is "how do I add/build/integrate/scaffold {X} in {framework}" and `{framework}` matches a peer signal, the peer row below wins instead. | `stream-docs` |
| Operational verbs + Stream noun: "list calls", "show channels", "any flagged", "find users", "check {anything}" | `stream-cli` |
| `stream api`, `stream config`, `stream auth` (literal CLI invocation) | `stream-cli` |
| "Install the CLI", "set up stream" with no project context | `stream-cli` |
| **Build/integration intent + a token matching a peer's `signals` in [`peers.yaml`](peers.yaml)** (e.g. `swift` / `.xcodeproj` -> `stream-swift`; `react native` / `expo` / `stream video react native` / `stream video rn` -> `stream-react-native`). **This row takes precedence over the web `stream-builder` rows below whenever a peer signal is present, and also wins over the docs how-to rows above whenever the request contains a build/integrate verb (`add`, `build`, `integrate`, `scaffold`, `wire`, `set up`, `create`) alongside the peer signal.** | matching peer (installed silently if missing) |
| "Build me a ... app", "scaffold", "create a new ..." + Stream product, in an empty/new directory, **and no peer signal present** | `stream-builder` (web/Next.js, the default when no platform signal is given) |
| "Add Chat/Video/Feeds to this app", "integrate Stream into" - existing project, **and no peer signal present** | `stream-builder` (web/Next.js, the default when no platform signal is given) |
| Operational verb wrapped in how-to phrasing (e.g. "how do I list my calls?" - docs *or* CLI) | **Ask one disambiguator** |

**Track D carve-out.** `stream-docs` answers from documentation only - no preflight, no shell commands, no project inspection. Every other sub-skill runs preflight before doing real work.

**Docs vs platform packs.** A pure how-to or method-lookup question about an iOS/Android/etc. SDK symbol stays in `stream-docs` - don't pull in a platform pack for a documentation answer. Platform packs (e.g. `stream-swift`) are for *building or integrating* - scaffolding projects, wiring packages, generating views.

**Disambiguator.** If the input fits more than one row (typically operational verb + how-to phrasing), ask one short question and wait. Don't probe before the answer:

> Want me to look up the SDK method (docs) or run it now via CLI?

After the answer, route as if the user had given that signal directly.

**Bare `/stream` with no args.** Render the menu under "Quick navigation" **verbatim**, then wait for input. No shell execution, no probing, no install.

---

## Quick navigation

For a bare `/stream` (and whenever the user wants to pick a skill directly), output the block below **verbatim** - keep the Core / Platform SDKs split, the examples, and the closing line - then wait:

> **Stream** - Chat - Video - Feeds - Moderation. Tell me what you want, or pick a skill directly:
>
> **Core**
> - `/stream-builder` - scaffold a web app, or add Stream to an existing one - e.g. *"build me a chat app"*
> - `/stream-cli` - query data, run `stream api / config / auth`, install the CLI - e.g. *"list my channels"*
> - `/stream-docs` - search live SDK docs, with citations - e.g. *"how does useChannel work?"*
>
> **Platform SDKs**
> - `/stream-swift` - Swift - SwiftUI - UIKit - iOS
> - `/stream-android` - Android - Jetpack Compose - Kotlin
> - `/stream-react-native` - React Native - Expo
>
> New to a skill? Just describe the task - I'll install the right one automatically.

The closing line is load-bearing: typing an uninstalled slash command errors with "Unknown skill" *before* this router runs, so natural-language description is the only dead-end-proof path - it routes here and the missing peer is installed per [`peers.yaml`](peers.yaml). Keep this menu in sync with `peers.yaml`: every peer there appears here under Core or Platform SDKs, and new platforms get a bullet under Platform SDKs when their entry is added.

---

## Hand-off

See preamble: install if missing, invoke via `Skill` tool, don't stop. Cross-cutting rules in [`RULES.md`](RULES.md) apply to every sub-skill, including **Cross-track follow-ups** (offer, don't auto-execute, the natural next action across track boundaries).

---

## Support

If the user asks for support or how to contact someone, direct them to [getstream.io/contact](https://getstream.io/contact/).
