# Contributing

This repository holds the Stream skill pack. Every folder in `skills/` ships in the Claude Code, Cursor, and Codex plugins, so only Stream skills go there. Conventions for writing and editing skills are in [`AGENTS.md`](AGENTS.md).

## Checking the plugin

`README.md` is the plugin's listing page in Anthropic's plugin directory, and the directory's automated review reads it, so keep it about installing and using the plugin. Repository details belong in this file.

CI runs the checks the directory applies to a submission (`.github/workflows/validate-plugin.yml`). To run them locally:

```bash
claude plugin validate . --profile directory --strict
```

### OpenAI plugin directory

The Codex manifest is `.codex-plugin/plugin.json`. It reuses `skills/`, `mcp.json`, and `brand-kit/logo.png`. Keep its `version` in step with `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`. Every upload needs a version the directory has not seen before.

OpenAI takes a ZIP upload at [platform.openai.com/plugins](https://platform.openai.com/plugins) and runs its automated checks there. No local validator exists. Build the ZIP from a commit so it holds only tracked files and no other vendor manifests:

```bash
git archive --format=zip --output=getstream-codex.zip HEAD .codex-plugin brand-kit skills mcp.json LICENSE README.md
```

OpenAI cannot add an MCP server to a plugin that was first submitted without one, so keep `mcpServers` in the manifest.

## How it works

The `/stream` router directs app work to platform skills and uses the `getstream` CLI for queries, app config, onboarding, and documentation. Platform skills such as `/stream-react-native` can also be invoked explicitly.

| Intent | Skill |
|---|---|
| Build a new web app | `stream-react` |
| Add a product to an existing web app | `stream-react` |
| Audit an existing web integration | `stream-react` |
| Migrate / upgrade a web SDK version | `stream-react` |
| Migrate a web app from Sendbird | `stream-react` + `sendbird-migration.md` |
| Data queries, app config, and CLI operations | `stream` (CLI, built in) |
| Build or integrate a React Native CLI/Expo app | `stream-react-native` |
| Migrate a React Native app from Sendbird | `stream-react-native` + `sendbird-migration.md` |
| Look up SDK documentation | `stream` via `getstream docs` |
| Build or integrate a Swift/iOS app | `stream-swift` (docs orchestrator: `docs-map.md` + `setup.md`) |
| Build or integrate an Android app | `stream-android` + its `builder.md`, `sdk.md`, and `references/*.md` |
| Build or integrate a Flutter app | `stream-flutter` (docs orchestrator: `docs-map.md` + `setup.md` + `push.md`) |
| Build or integrate a Unity Engine project | `stream-unity` (docs orchestrator: `docs-map.md` + `setup.md` + `ui.md` + `platforms.md`) |
| Build or integrate an Unreal Engine project | `stream-unreal` (docs orchestrator: `docs-map.md` + `setup.md` + `widgets.md` + `platforms.md`) |
| Build or review a Feeds v2 -> v3 sync mapping, and plan the code port | `stream-feeds-migration` (`SKILL.md` + `mapping-keys.md` + `code-inventory.md` + `porting-plan.md` + `fetch_sample.py` + `scan_v2_calls.py`) |

> **Routing precedence:** when user input contains a platform signal (e.g. `react native`, `expo`, `swift`, `ios`, `flutter`, `unity`, `unreal`), use the matching platform skill. For web or generic app work, use `stream-react`. A framework takes precedence over an OS: an Unreal app for iOS uses `stream-unreal`.

The router ([`skills/stream/SKILL.md`](skills/stream/SKILL.md)) handles routing and CLI discovery. Each platform skill contains its own integration guidance and supporting files.

For older CLI installations, [`stream-builder`](skills/stream-builder/SKILL.md) and [`stream-docs`](skills/stream-docs/SKILL.md) remain as compatibility entrypoints. They forward to platform-specific skills (React by default for web or generic app work) and `getstream docs`, respectively.

## Contents

- [`skills/stream/`](skills/stream/) - **Router + CLI**
  - [`SKILL.md`](skills/stream/SKILL.md) - Stream overview, CLI discovery, and skill routing
  - [`sendbird-data-migration.md`](skills/stream/sendbird-data-migration.md) - shared Sendbird data export, import, and cutover workflow
  - [`integration-review.md`](skills/stream/integration-review.md) - read-only integration review: procedure, cross-platform checks, and the report format
  - [`livestream-review.md`](skills/stream/livestream-review.md) - livestream and audio-room checks for the integration review: viewer join path, host path, call-type settings, audience scale, event readiness
- [`skills/stream-react/`](skills/stream-react/) - **React web sub-skill** (default for web React / Next.js work)
  - [`SKILL.md`](skills/stream-react/SKILL.md) - build and integrate Stream, audit an app, upgrade SDKs, and verify the result
  - [`integration-review.md`](skills/stream-react/integration-review.md) - React checks for an integration review: Video client, calls, and the livestream checks
  - [`chat-versions.md`](skills/stream-react/chat-versions.md) - pin the installed Chat React major, use that major's docs, find its migration guide
  - [`design-matching.md`](skills/stream-react/design-matching.md) - implement and verify a reference design
  - [`sendbird-migration.md`](skills/stream-react/sendbird-migration.md) - migrate a Sendbird app to Stream Chat React
  - [`sendbird-mapping.md`](skills/stream-react/sendbird-mapping.md) - Sendbird-to-Stream symbol mappings and behavioral differences
  - [`ai-support-agent.md`](skills/stream-react/ai-support-agent.md) - build an AI support agent with Stream Chat
- [`skills/stream-swift/`](skills/stream-swift/) - **Swift/iOS sub-skill** (docs orchestrator)
  - [`SKILL.md`](skills/stream-swift/SKILL.md) - entrypoint: the `.md` docs convention, intent classifier, docs-lookup loop
  - [`RULES.md`](skills/stream-swift/RULES.md) - Swift/iOS non-negotiable rules + curated iOS pitfalls
  - [`docs-map.md`](skills/stream-swift/docs-map.md) - intent -> exact official iOS docs page (Chat/Video/Feeds, SwiftUI/UIKit), plus best-practices pages and a source-code/example-app fallback (SDK repos) for what the docs do not cover
  - [`setup.md`](skills/stream-swift/setup.md) - CLI-driven credentials, install, and client-wiring flow
  - [`push.md`](skills/stream-swift/push.md) - seamless push runbook: APNs key, CLI push-provider creation, client wiring, VoIP + CallKit
  - [`design-matching.md`](skills/stream-swift/design-matching.md) - reproduce a reference design with the **pre-built components**: region -> `ViewFactory`/`Styles`/theming map
  - [`custom-ui.md`](skills/stream-swift/custom-ui.md) - the **components-vs-custom** decision + how to build a livestream/bespoke surface on the low-level client + State Layer
- [`skills/stream-react-native/`](skills/stream-react-native/) - **React Native sub-skill** (Chat, Video, and Feeds in RN CLI and Expo apps)
  - [`SKILL.md`](skills/stream-react-native/SKILL.md) - build and integrate Stream, audit an app, upgrade SDKs, and verify the result
  - [`chat-versions.md`](skills/stream-react-native/chat-versions.md) - pin the installed Chat RN major, use that major's docs, find its migration guide
  - [`ai-integration.md`](skills/stream-react-native/ai-integration.md) - AI assistants on the Chat SDK's `ai-components`, and what the backend agent must send
  - [`stream-agents.md`](skills/stream-react-native/stream-agents.md) - apps on Stream Agents (`@stream-io/stream-agents`): sessions shown with `AIConversation`, approvals, sign-ins, device tools
  - [`design-matching.md`](skills/stream-react-native/design-matching.md) - implement and verify a reference design
  - [`simulator-verification.md`](skills/stream-react-native/simulator-verification.md) - run, drive, and screenshot the app on a simulator or emulator
  - [`sendbird-migration.md`](skills/stream-react-native/sendbird-migration.md) - migrate a Sendbird app to Stream Chat React Native
  - [`sendbird-mapping.md`](skills/stream-react-native/sendbird-mapping.md) - Sendbird-to-Stream symbol mappings and behavioral differences
- [`skills/stream-android/`](skills/stream-android/) - **Android sub-skill**
  - [`SKILL.md`](skills/stream-android/SKILL.md) - entrypoint: intent classifier, local project detection, module pointers
  - [`RULES.md`](skills/stream-android/RULES.md) - Android non-negotiable rules
  - [`builder.md`](skills/stream-android/builder.md) + [`sdk.md`](skills/stream-android/sdk.md) - shared Android app integration flow and SDK ownership patterns
  - [`integration-review.md`](skills/stream-android/integration-review.md) - Android checks for an integration review
  - [`references/`](skills/stream-android/references/) - product/framework-specific Android references and blueprints
- [`skills/stream-flutter/`](skills/stream-flutter/) - **Flutter sub-skill** (docs orchestrator; Chat + Video + Feeds)
  - [`SKILL.md`](skills/stream-flutter/SKILL.md) - entrypoint: the `.md` docs convention, intent classifier, Chat UI-strategy decision, docs-lookup loop
  - [`RULES.md`](skills/stream-flutter/RULES.md) - Flutter non-negotiable rules + curated pitfalls (v10 Chat, Video build blockers, Feeds v3)
  - [`docs-map.md`](skills/stream-flutter/docs-map.md) - intent -> exact official Flutter docs page (Chat UI/core/client, Video, Feeds), plus a pub-cache source / example-app fallback
  - [`setup.md`](skills/stream-flutter/setup.md) - project detection, v10 check, CLI credentials + seed data, install, platform setup, client wiring
  - [`push.md`](skills/stream-flutter/push.md) - Chat push + Video ringing runbook: CLI push providers, CallKit / FCM / Telecom, ship-code-defer-config
  - [`integration-review.md`](skills/stream-flutter/integration-review.md) - Flutter checks for an integration review, including the livestream checks
  - [`video-patterns.md`](skills/stream-flutter/video-patterns.md) - Video patterns with no docs page (livestream feed, call over a broadcast, shared call state, Chat + Video glue)
  - [`design-matching.md`](skills/stream-flutter/design-matching.md) + [`custom-ui.md`](skills/stream-flutter/custom-ui.md) - pre-built components vs custom `stream_chat_flutter_core` UI
  - [`sendbird-migration.md`](skills/stream-flutter/sendbird-migration.md) - Sendbird -> Stream Chat migration runbook
- [`skills/stream-unity/`](skills/stream-unity/) - **Unity Engine sub-skill** (docs orchestrator; Chat + Video)
  - [`SKILL.md`](skills/stream-unity/SKILL.md) - entrypoint: product / Unity-version-and-target / feature-support gates, the `.md` docs convention plus the per-product coverage caveat (Unity C# vs the .NET server SDK on the same page), and the source-of-truth ladder
  - [`RULES.md`](skills/stream-unity/RULES.md) - Unity non-negotiable rules + the pitfalls that fail silently (the `DontDestroyOnLoad` client runner and duplicate clients, `Dispose()` not disconnecting, unbound video/audio tracks, the 5-participant video cap, IL2CPP stripping)
  - [`docs-map.md`](skills/stream-unity/docs-map.md) - intent -> exact official Unity docs page for Chat and Video, annotated with what kind of code each page carries, plus the source / samples / changelog fallback
  - [`setup.md`](skills/stream-unity/setup.md) - version-pinned install for both SDKs (`.unitypackage` import and the UPM manifest edit), CLI credentials, and the verified minimal client wiring with correct lifecycle
  - [`ui.md`](skills/stream-unity/ui.md) - building the UI yourself: the `ParticipantView` track-binding contract, self-preview, mobile orientation, visibility-driven subscriptions, and the Chat list / composer / typing patterns
  - [`platforms.md`](skills/stream-unity/platforms.md) - per-target player settings, IL2CPP and managed stripping, the Newtonsoft and WebRTC conflicts, Android/iOS/desktop/WebGL, and what push does and does not do
- [`skills/stream-feeds-migration/`](skills/stream-feeds-migration/) - **Feeds v2 -> v3 migration sub-skill**
  - [`SKILL.md`](skills/stream-feeds-migration/SKILL.md) - the workflow: credentials into the environment, sample the v2 app, read its v2 integration code when available, analyze, emit the `mapping` object, and state what the sample (and code) could not prove
  - [`mapping-keys.md`](skills/stream-feeds-migration/mapping-keys.md) - the full key catalogue with defaults, id-precedence and rename resolution rules, and a worked v2-shape -> mapping-key example for each common case
  - [`fetch_sample.py`](skills/stream-feeds-migration/fetch_sample.py) - stdlib-only sampler; reads credentials from the environment and writes `v3sync-sample.json`
  - [`code-inventory.md`](skills/stream-feeds-migration/code-inventory.md) - reading the app's v2 integration code: finding write paths, building the inventory, and cross-checking it against the sample
  - [`porting-plan.md`](skills/stream-feeds-migration/porting-plan.md) - planning the move of the app's code from v2 to v3: the switch-over order, a v2 -> v3 row per path, and the rules for porting when the user asks
  - [`scan_v2_calls.py`](skills/stream-feeds-migration/scan_v2_calls.py) - stdlib-only, read-only scanner that lists every v2 write call site in a repository (JS, Python, Ruby, PHP, Go, Java, .NET, REST), with secrets redacted
- [`skills/stream-unreal/`](skills/stream-unreal/) - **Unreal Engine sub-skill** (docs orchestrator; Chat only)
  - [`SKILL.md`](skills/stream-unreal/SKILL.md) - entrypoint: engine-version / feature-support / C++-vs-Blueprint gates, the `.md` docs convention plus the per-page Unreal-coverage caveat, and the source-of-truth ladder
  - [`RULES.md`](skills/stream-unreal/RULES.md) - Unreal non-negotiable rules + the pitfalls that fail silently (the `ApiKey`-before-`BeginPlay` trap, `TWeakObjectPtr` callbacks, client on the HUD, module deps)
  - [`docs-map.md`](skills/stream-unreal/docs-map.md) - intent -> exact official Unreal docs page, annotated with which pages actually carry Unreal code, plus the plugin-header / Doxygen / sample-project fallback
  - [`setup.md`](skills/stream-unreal/setup.md) - engine-version-aware plugin install, `Build.cs` module deps, CLI credentials, and the verified minimal client wiring
  - [`widgets.md`](skills/stream-unreal/widgets.md) - the shipped UMG chat widgets (undocumented upstream): `WBP_*` inventory, path-loading, `Setup`-before-`AddToViewport`, context model, theming, cooking
  - [`platforms.md`](skills/stream-unreal/platforms.md) - iOS/Android/desktop config, signing, build-vs-package, and on-device deploy + log reading
