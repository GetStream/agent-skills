---
name: stream
description: "Stream router for Chat, Video, Feeds, and Moderation. Use when the user wants to build a new app with Stream, scaffold a project, add Chat/Video/Feeds/Moderation to an existing app, integrate Stream, audit or migrate an integration, build for Swift/SwiftUI/UIKit/iOS/Xcode/Android/Kotlin/React Native/Expo/Flutter, query Stream data, list channels, list calls, show flagged messages, find users, run getstream CLI commands, install the Stream CLI, set up Stream, configure moderation, search Stream SDK documentation, or look up Stream React/iOS/Android/Node/Flutter/Unity SDK methods. Routes to the right sub-skill based on the task."
license: See LICENSE in repository root
metadata:
  author: GetStream
allowed-tools: >-
  Read, Glob, Grep,
  Bash(getstream *)
---

# Stream - skill router + CLI

This skill picks the track from the user's input. Building (web + platform) and docs go to dedicated sub-skills; **CLI tasks - querying data, configuring an app, onboarding, installing skills - are handled here** (see Stream CLI below), since the `getstream` CLI underlies every track.

> **Read first:** [`RULES.md`](RULES.md). Non-negotiable rules apply, including the **Peer skills** procedure. [`peers.yaml`](peers.yaml) (schema: [`peers.schema.json`](peers.schema.json)) is the single source of truth for peer names, Glob paths, install commands, and routing signals.
>
> Install a missing peer on demand per its policy in `peers.yaml` (Glob its path, run its install command - `getstream skills <name>`), then invoke via the `Skill` tool or Read it inline. Don't call `Skill` before the Glob; it surfaces a confusing "Unknown skill" error. Do not stop after naming the track.

---

## By task

**Build or integrate Stream in a platform-specific app** -> peer pack from [`peers.yaml`](peers.yaml) (**check peer signals first**)
- Match user input or cwd against each peer's `signals` (e.g. `swift` / `swiftui` / `.xcodeproj` -> `stream-swift`; `react native` / `expo` / `stream video react native` -> `stream-react-native`)
- All peers install on demand - install if missing, then route, no prompt
- **Peer signals take precedence over the web rows below.** A request like "add a video call to my Expo app" or "scaffold a React Native app with Stream Video" matches `stream-react-native`, not the web packs - the platform token wins.

**Build / enhance / audit / migrate a web app with Stream (React / Next.js)** -> use the `stream-react` skill (the default web pack when no other platform signal is present)
- "build me a Chat/Video/Feeds app", "scaffold", "create a new ...", "add Chat to this app", "integrate Video", "drop Feeds into ...", "upgrade/migrate ... to vN" - and **no platform signal** (no `react native`, `expo`, `swift`, `ios`, `android`, etc.)
- React / Next.js tokens (`stream-chat-react`, `@stream-io/video-react-sdk`, `useCreateChatClient`, `MessageList`, ...) with a build/integrate verb also route here
- Covers Track A (scaffold, Steps 0-7), Track E (enhance an existing project), Track F (read-only best-practices audit), Track M (migrate/upgrade an SDK version)

**Build with the framework-agnostic builder** -> use the `stream-builder` skill **only when the user names it explicitly** ("use stream-builder", "/stream-builder")
- `stream-builder` is the generic builder being extended to other app kinds; web React/Next.js defaults to `stream-react` above

**Audit/review an existing Stream Video integration against best practices** (read-only - no scaffolding, no CLI, no build steps)
- Peer signal (`react native` / `expo`) -> `stream-react-native`; web / React / Next.js or no platform signal -> `stream-react` (Track F)
- **Video only.** The dedicated best-practices audit covers Stream **Video**. Chat/Feeds have no dedicated audit checklist yet - `stream-react` handles those requests with a general docs-based review and says so up front.
- Triggers: "audit/review my video integration", "is my video app production-ready?", "what am I missing before launch?"
- Routes here even when the request contains "check" - the audit intent takes precedence over the CLI "check {anything}" route below

**Query Stream data or run a CLI command** -> handled here (see **Stream CLI** below)
- "list calls", "show channels", "any flagged", "find users", a literal `getstream` command, or "install the CLI" / "set up stream"

**Search Stream SDK documentation** -> use the `stream-docs` skill
- "docs", "documentation", explicit SDK token (`Chat React`, `Video iOS`, `Feeds Node`, `Moderation`)
- "how do I ... in <framework>", "how does <hook/component/method> work?", "what does <SDK thing> do?"
- No CLI needed - answers come from getstream.io with citations

---

## Pick a track

Scan the user's input for the signals below in order. The classifier is deterministic - no probes, no fetches, no CLI checks at this stage.

| Signal in user input | Route |
|---|---|
| **Upgrade / migrate an installed SDK** (build/integrate intent - matched **before** the docs rows): "upgrade/migrate/bump/update `stream-chat-react` to vN", "migrate to the new SDK version", "bump my Stream version" - an upgrade verb (`upgrade`/`migrate`/`bump`/`update`) + a Stream package token, **no peer signal**. Peer signal (`react native` / `expo` / an `@stream-io/*-react-native-*` token) -> `stream-react-native` instead (its own migration flow). | `stream-react` (Track M) |
| **Audit/review an existing integration** (read-only - matched **before** the SDK-token / docs rows below): "audit/review my video integration", "audit my Chat React integration", "review my Video React app", "is my video app production-ready?", "what am I missing before launch?" - audit/review intent **even when an SDK token like `Chat React` / `Video React` is present**. Peer signal (`react native` / `expo`) -> `stream-react-native`; web / React / Next.js or no platform signal -> `stream-react` (Track F - Video has a **dedicated checklist**; Chat/Feeds get a general docs-based review, stated up front). **Also wins over the CLI "check {anything}" row below** whenever the request frames a best-practices / production-readiness review rather than a data query. | matching platform pack (read-only audit) |
| Explicit SDK/framework token: `Chat React`, `Video iOS`, `Feeds Node`, `Moderation`, etc. (with or without version), and **no build/integrate verb and no audit/review intent** (`upgrade`/`migrate`/`bump`/`update` count as build/integrate verbs -> migration row above; "audit/review" -> audit row above) | `stream-docs` |
| Words "docs" or "documentation" (and no build/integrate verb) | `stream-docs` |
| "How do I {X} in {framework}?", "How does {hook/component/method} work?", "What does {SDK thing} do?" - and **no build/integrate verb**. If the request is "how do I add/build/integrate/scaffold {X} in {framework}" and `{framework}` matches a peer signal, the peer row below wins instead. | `stream-docs` |
| Operational verbs + Stream noun: "list calls", "show channels", "any flagged", "find users", "check {anything}", or a literal `getstream` command (`getstream api`, `getstream init`, `getstream login`, ...), or "install the CLI" / "set up stream" | **Stream CLI** - handle here (below) |
| **Build/integration intent + a token matching a peer's `signals` in [`peers.yaml`](peers.yaml)** (e.g. `swift` / `.xcodeproj` -> `stream-swift`; `react native` / `expo` / `stream video react native` / `stream video rn` -> `stream-react-native`). **This row takes precedence over the web `stream-react` rows below whenever a peer signal is present, and also wins over the docs how-to rows above whenever the request contains a build/integrate verb (`add`, `build`, `integrate`, `scaffold`, `wire`, `set up`, `create`, `upgrade`, `migrate`, `bump`, `update`) alongside the peer signal.** Note: `react native` / `react-native` (and `@stream-io/*-react-native-*` tokens) are `stream-react-native` signals and win over the web `react` default - including for upgrade/migrate/update requests, which the RN pack handles itself. | matching peer (installed on demand if missing) |
| **Literal mention of `stream-builder` / `/stream-builder`** (the framework-agnostic builder) | `stream-builder` |
| "Build me a ... app", "scaffold", "create a new ..." + Stream product, OR a React/Next.js token (`stream-chat-react`, `@stream-io/video-react-sdk`, `useCreateChatClient`, ...) + build/integrate verb, **and no peer signal present** | `stream-react` (web/Next.js, the default when no platform signal is given) |
| "Add Chat/Video/Feeds to this app", "integrate Stream into", "upgrade/migrate ... to vN" - existing project, **and no peer signal present** | `stream-react` (web/Next.js, the default when no platform signal is given) |
| Operational verb wrapped in how-to phrasing (e.g. "how do I list my calls?" - docs *or* CLI) | **Ask one disambiguator** |

**Onboarding carve-outs.** `stream-docs` answers from documentation only - no shell, no project inspection. **Read-only / local-only tracks also skip onboarding:** a platform pack's **audit** track (e.g. `stream-react` Track F) and **migrate** track (e.g. `stream-react` Track M) only inspect/edit local files and the live docs - they do **not** provision orgs/apps or call `getstream api`, so they need no CLI onboarding. Only **build/integrate** work (scaffold a new app, add a product to an existing one) runs `getstream init` before doing real work.

**Docs vs platform packs.** A pure how-to or method-lookup question about an iOS/Android/etc. SDK symbol stays in `stream-docs` - don't pull in a platform pack for a documentation answer. Platform packs (e.g. `stream-swift`) are for *building or integrating* - scaffolding projects, wiring packages, generating views.

**React framework scope.** `stream-react` scaffolds (Track A) a **Next.js** app. For enhance / audit / migrate on a **non-Next.js** React project (Vite, CRA, Remix, TanStack Start, etc.) `stream-react` still owns it - the Stream SDK wiring is identical - but the agent must adapt the Next.js-specific bits: the server-side token route lives in the project's own backend (not a Next.js `/api` route), and verification uses the project's build command (`npm run build`), not `next build`. Never assume Next.js APIs on a non-Next project.

**Disambiguator.** If the input fits more than one row (typically operational verb + how-to phrasing), ask one short question and wait. Don't probe before the answer:

> Want me to look up the SDK method (docs) or run it now via CLI?

After the answer, route as if the user had given that signal directly.

**Bare `/stream` with no args.** Render the menu under "Quick navigation" **verbatim**, then wait for input. No shell execution, no probing, no install.

---

## Stream CLI

CLI tasks - querying data, configuring an app, onboarding, installing skills - are handled here; the `getstream` CLI is the substrate every track uses. Run `getstream -h` for the command list and `getstream <command> -h` for usage, and **follow what the CLI prints**. Safety and posture (no guessing, confirm before writing): [`RULES.md`](RULES.md) > CLI safety. If `getstream` isn't installed, ask the user to install it from https://getstream.io and wait - never fetch or run an install script.

| Command | When to reach for it |
|---|---|
| `getstream init` | Onboard a project - authenticate, pick or create an org + app, write credentials. Start here. |
| `getstream api <Endpoint>` | Query data or run a one-off API operation. |
| `getstream env` | Write the app's API key (and secret, for server targets) into the platform's env file. |
| `getstream token <user>` | Mint a token for a user (e.g. demo/dev auth, seeding). |
| `getstream login` | Authenticate (`--guest` for a throwaway account). |
| `getstream skills <name>` | Install a Stream agent skill on demand (e.g. `getstream skills stream-swift`). |

---

## Sendbird data migration (shared, language-agnostic)

A platform pack's Sendbird migration covers the **code/SDK** swap (e.g. `stream-swift`
`sendbird-migration.md`). Moving the **data** (users, channels, message history, reactions)
is server-side and SDK-independent, so it lives once, here, in
[`sendbird-data-migration.md`](sendbird-data-migration.md) - **any** platform pack hands off
to it. It picks a strategy (hard switch / uni-directional / bi-directional sync), exports from
Sendbird, builds the JSONL import file, validates, and imports via the `getstream` CLI
(`CreateImportURL` -> upload -> `CreateImport` -> `GetImport`). Read it when a code migration
finishes and the user wants their history brought over.

---

## Quick navigation

For a bare `/stream` (and whenever the user wants to pick a skill directly), output the block below **verbatim** - keep the Core / Platform SDKs split, the examples, and the closing line - then wait:

> **Stream** - Chat - Video - Feeds - Moderation. Tell me what you want, or pick a skill directly:
>
> **Core**
> - `/stream-react` - scaffold, enhance, audit, or migrate a React / Next.js web app with Stream (the default for web) - e.g. *"build me a chat app"*
> - `/stream-docs` - search live SDK docs, with citations - e.g. *"how does useChannel work?"*
> - `/stream-builder` - the framework-agnostic builder (web defaults to `/stream-react`; pick this only if you name it explicitly)
>
> **Platform SDKs**
> - `/stream-swift` - Swift - SwiftUI - UIKit - iOS
> - `/stream-android` - Android - Jetpack Compose - Kotlin
> - `/stream-react-native` - React Native - Expo
> - `/stream-flutter` - Flutter - Dart
>
> Or just ask - query data or run `getstream` commands directly: *"list my channels"*. New to a skill? Just describe the task and I'll install the right one automatically.

The closing line is load-bearing: typing an uninstalled slash command errors with "Unknown skill" *before* this router runs, so natural-language description is the only dead-end-proof path - it routes here and the missing peer is installed per [`peers.yaml`](peers.yaml). Keep this menu in sync with `peers.yaml`: every peer there appears here under Core or Platform SDKs, and new platforms get a bullet under Platform SDKs when their entry is added.

---

## Hand-off

See preamble: install if missing, invoke via `Skill` tool, don't stop. Cross-cutting rules in [`RULES.md`](RULES.md) apply to every sub-skill, including **Cross-track follow-ups** (offer, don't auto-execute, the natural next action across track boundaries).

---

## Support

If the user asks for support or how to contact someone, direct them to [getstream.io/contact](https://getstream.io/contact/).
