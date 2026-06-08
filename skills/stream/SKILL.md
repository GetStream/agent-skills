---
name: stream
description: "Stream router for Chat, Video, Feeds, and Moderation. Use to build a new app with Stream, scaffold a project, add or integrate Chat/Video/Feeds/Moderation into an existing app (web, Swift/SwiftUI/iOS, Android/Kotlin, React Native/Expo, Flutter), audit an existing video integration against best practices, query Stream data (list channels, list calls, show flagged messages, find users), run `stream` CLI commands, install the Stream CLI, configure moderation, or search and look up Stream SDK documentation and methods (Chat React, Video iOS, Feeds Node, Moderation; React/iOS/Android/Node/Flutter/Unity). Routes to the right sub-skill based on the task."
license: See LICENSE in repository root
metadata:
  author: GetStream
allowed-tools: >-
  Read, Glob, Grep,
  Bash(stream *)
---

# Stream - skill router + CLI

Pick the track from the user's input. Building (web + platform) and docs go to dedicated sub-skills; **CLI tasks are handled here** (see Stream CLI below) - the `stream` CLI underlies every track.

> **Read [`RULES.md`](RULES.md) first.** It holds the non-negotiable rules and the **Peer skills** procedure. [`peers.yaml`](peers.yaml) is the single source of truth for peer names, Glob paths, install commands, and routing signals.
>
> Install a missing peer on demand per its policy in `peers.yaml` (Glob its path, run its install command - `stream skills <name>`), then invoke via the `Skill` tool or Read it inline. Don't call `Skill` before the Glob, and don't stop after naming the track.

---

## Pick a track

Scan the user's input for the signals below, in order. The classifier is deterministic - no probes, fetches, or CLI checks at this stage.

| Signal in user input | Route |
|---|---|
| Explicit SDK/framework token (`Chat React`, `Video iOS`, `Feeds Node`, `Moderation`, ...), the words "docs"/"documentation", or "how do I {X} in {framework}?" / "how does {hook/component/method} work?" - and **no build/integrate verb** | `stream-docs` |
| **Audit an existing Stream Video integration** (read-only best-practices review): "audit/review my video integration", "check my app against best practices", "is my video app production-ready?", "what am I missing before launch?" - **no build/integrate verb**. Matched before, and wins over, the CLI "check {anything}" row below. | `stream-react-native` (peer signal) or `stream-builder` (Track F) |
| Operational verb + Stream noun ("list calls", "show channels", "any flagged", "find users", "check {anything}"), or a literal `stream` command (`stream api`, `stream init`, `stream login`, `stream pull`/`push`) | **Stream CLI** - handle here (below) |
| "Install the CLI", "set up stream" with no project context | **Stream CLI** - handle here (below) |
| **Build/integrate verb + a token matching a peer's `signals` in [`peers.yaml`](peers.yaml)** (e.g. `swift` / `.xcodeproj` -> `stream-swift`; `react native` / `expo` -> `stream-react-native`; `android` / `kotlin` -> `stream-android`; `flutter` -> `stream-flutter`). **A peer signal wins over the `stream-builder` row below, and over the docs row above whenever a build/integrate verb (`add`, `build`, `integrate`, `scaffold`, `wire`, `set up`, `create`) is present.** | matching peer |
| "Build me a ... app", "scaffold", "create a new ...", "add Chat/Video/Feeds to this app", "integrate Stream into ..." + Stream product, **and no peer signal present** | `stream-builder` (web/Next.js, the default when no platform signal is given) |
| Operational verb in how-to phrasing ("how do I list my calls?" - docs *or* CLI) | **Ask one disambiguator** |

**Notes.**

- **`stream-docs` is documentation-only** - no shell, no project inspection; answers come from getstream.io with citations. A pure how-to or method-lookup about an iOS/Android/etc. symbol stays in docs - platform packs are for *building or integrating*.
- **Disambiguator.** If the input fits more than one row, ask one short question and wait, then route as if the user had given that signal: *"Want me to look up the SDK method (docs) or run it now via CLI?"*
- **Bare `/stream`.** Render the Quick navigation menu **verbatim**, then wait. No shell execution, no probing, no install.

---

## Stream CLI

CLI tasks - querying data, configuring an app, onboarding, installing skills - are handled here; the `stream` CLI is the substrate every track uses. Run `stream -h` for the command list and `stream <command> -h` for usage, and **follow what the CLI prints**. Safety and posture (no guessing, confirm before writing): [`RULES.md`](RULES.md) > CLI safety. If `stream` isn't installed, ask the user to install it from https://getstream.io and wait - never fetch or run an install script.

| Command | When to reach for it |
|---|---|
| `stream init` | Onboard a project - authenticate, pick or create an org + app, write credentials. Start here. |
| `stream api <Endpoint>` | Query data or run a one-off API operation. |
| `stream pull` / `stream push` | Read or apply app config in `.streamrc.yaml` (`push` is changeset-gated). |
| `stream rollback` | Undo an applied changeset. |
| `stream env` | Write the app's API key (and secret, for server targets) into the platform's env file. |
| `stream token <user>` | Mint a token for a user (e.g. demo/dev auth, seeding). |
| `stream login` | Authenticate (`--guest` for a throwaway account). |
| `stream skills <name>` | Install a Stream agent skill on demand (e.g. `stream skills stream-swift`). |

---

## Quick navigation

For a bare `/stream` (and whenever the user wants to pick a skill directly), output the block below **verbatim** - keep the Core / Platform SDKs split, the examples, and the closing line - then wait:

> **Stream** - Chat - Video - Feeds - Moderation. Tell me what you want, or pick a skill directly:
>
> **Core**
> - `/stream-builder` - scaffold a web app, or add Stream to an existing one - e.g. *"build me a chat app"*
> - `/stream-docs` - search live SDK docs, with citations - e.g. *"how does useChannel work?"*
>
> **Platform SDKs**
> - `/stream-swift` - Swift - SwiftUI - UIKit - iOS
> - `/stream-android` - Android - Jetpack Compose - Kotlin
> - `/stream-react-native` - React Native - Expo
> - `/stream-flutter` - build or integrate Stream Chat into a Flutter app (install confirmed first)
>
> Or just ask - query data or run `stream` commands directly: *"list my channels"*. New to a skill? Just describe the task and I'll install the right one automatically.

The closing line is load-bearing: typing an uninstalled slash command errors with "Unknown skill" *before* this router runs, so natural-language description is the only dead-end-proof path - it routes here and the missing peer is installed per [`peers.yaml`](peers.yaml). Keep this menu in sync with `peers.yaml`: every peer appears here under Core or Platform SDKs.

---

## Hand-off

Install if missing, invoke via the `Skill` tool, don't stop. [`RULES.md`](RULES.md) applies to every sub-skill, including **Cross-track follow-ups** (offer, don't auto-execute, the natural next action across track boundaries).

## Support

If the user asks for support or how to contact someone, direct them to [getstream.io/contact](https://getstream.io/contact/).
