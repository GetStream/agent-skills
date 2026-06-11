# Stream Agent Skills

Give your AI coding agent the ability to build, query, and manage [Stream](https://getstream.io) - Chat, Video, Feeds, Moderation, Swift/iOS integrations, and React Native Chat and Video.

## Install

Install the [Stream CLI](https://getstream.io), then:

```bash
getstream skills
```

With no arguments, `getstream skills` installs the default set - the `stream` router (which includes the CLI layer), `stream-builder`, and `stream-docs`. Platform packs (`stream-swift`, `stream-android`, `stream-react-native`, `stream-flutter`) install on demand via `getstream skills <name>` the first time a task needs them. To set up a project at the same time (auth, org/app selection, credentials), run `getstream init` instead.

Use `/stream` for generic routing, or invoke a skill directly with `/stream-builder`, `/stream-docs`, `/stream-swift`, `/stream-android`, `/stream-react-native`, or `/stream-flutter`.

## Skills

| Skill | Purpose | When to use |
|---|---|---|
| `/stream` | **Router + CLI** - classifies intent, dispatches, and runs `getstream` CLI commands | Start here; also handles data queries, app config, and onboarding |
| `/stream-docs` | Search live SDK documentation from getstream.io | Explicit SDK token (Chat React, Video iOS, ...), "docs", "how do I ... in <framework>" |
| `/stream-builder` | Scaffold a new web app, or add Chat/Video/Feeds/Moderation to an existing one | "build me a ... app", "scaffold", "add Chat to this app", "integrate Video" |
| `/stream-swift` | Build or integrate Stream in Swift/SwiftUI/UIKit/iOS apps | Swift, SwiftUI, UIKit, iOS, Xcode |
| `/stream-android` | Build or integrate Stream in Android/Jetpack Compose apps | Android, Jetpack Compose, Kotlin, Android Studio, Gradle |
| `/stream-react-native` | Create, build, or integrate Stream Chat or Stream Video React Native in RN CLI or Expo apps | React Native, Expo, `stream-chat-react-native`, `stream-chat-expo`, `@stream-io/video-react-native-sdk`, video call, livestream, audio room, ringing |
| `/stream-flutter` | Build or integrate Stream Chat in Flutter apps | Flutter, Dart, `stream_chat_flutter`, `stream_chat_flutter_core` |

The router (`/stream`) owns routing, the CLI layer (queries, app config, onboarding), and the cross-cutting rules in [`skills/stream/RULES.md`](skills/stream/RULES.md). Platform sub-skills can add their own `RULES.md`.

## What gets installed

The skills are plain markdown. Installation and on-demand skill fetching run through the `getstream` CLI; the only other network touch is the optional frontend-skill packs the builder can add with your consent.

| Step | Trigger | What it does | Source |
|---|---|---|---|
| `getstream skills <name>` | Agent, on demand (or you) | Fetches a skill's markdown into your skills directory via the `getstream` CLI. | GitHub (`GetStream/agent-skills`) |
| Frontend skill installs (builder only) | Agent asks first, then runs | Installs three third-party skill packs for UI scaffolding - see below. | GitHub (listed) |

### Frontend skills (builder only)

When you ask the agent to scaffold a new app or enhance an existing one via `/stream-builder`, Step 3 can install three helper skill packs. **The agent surfaces the full list and waits for your confirmation before running any install.**

| Skill | Purpose | Source |
|---|---|---|
| `vercel-react-best-practices` | React/Next.js idioms | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `web-design-guidelines` | Generic UI design polish | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `frontend-design` | Frontend structure | [`anthropics/skills`](https://github.com/anthropics/skills) |

Decline and the builder still runs - Stream reference files cover the SDK wiring; the frontend skills only tune generic UI quality. The docs skill never triggers these installs.

## What your agent can do

- **Scaffold a full app** - Next.js + Tailwind + Stream SDKs, wired end-to-end in one shot (`/stream-builder`)
- **Add products to existing apps** - drop Chat, Video, or Feeds into a project that's already running (`/stream-builder`)
- **Build and extend Swift apps** - wire Stream into SwiftUI or UIKit Xcode projects with iOS-specific setup patterns (`/stream-swift`)
- **Build and extend Android apps** - wire Stream into Jetpack Compose Android Studio / Gradle projects with Android-specific setup patterns (`/stream-android`)
- **Build and extend React Native apps** - wire Stream Chat or Stream Video into Expo or RN CLI projects (`/stream-react-native`)
- **Query live data** - "any active calls?", "show flagged messages", "list my channels" - natural language to the `getstream` CLI (`/stream`)
- **Configure apps and moderation** - channel types, roles, permissions, blocklists, automod - via the `getstream` CLI (`/stream`)
- **Answer SDK questions** - token patterns, strict mode, client/server instantiation, theme wiring (`/stream-builder` or `/stream-docs`)
- **Search live SDK docs** - ask questions about any Stream SDK, framework, or version; answers come verbatim from getstream.io with citations (`/stream-docs`)

## How it works

The `/stream` router classifies intent, runs `getstream` CLI commands itself (queries, app config, onboarding), and routes building and docs to dedicated sub-skills. Platform sub-skills such as `/stream-react-native` can also be invoked explicitly.

| Intent | Skill |
|---|---|
| Build a new app | `stream-builder` (Track A) |
| Add a product to an existing app | `stream-builder` (Track E) |
| Data queries, app config, and CLI operations | `stream` (CLI, built in) |
| SDK wiring during builder/enhance | `stream-builder` + its `sdk.md` and `references/*.md` |
| Build or integrate a React Native CLI/Expo app | `stream-react-native` + its `sdk.md` and `references/*.md` |
| Search the official SDK documentation (no CLI needed) | `stream-docs` (Track D) |
| Build or integrate a Swift/iOS app | `stream-swift` + its `builder.md`, `sdk.md`, and `references/*.md` |
| Build or integrate an Android app | `stream-android` + its `builder.md`, `sdk.md`, and `references/*.md` |
| Build or integrate a Flutter app | `stream-flutter` + its `builder.md`, `sdk.md`, and `references/*.md` |

> **Routing precedence:** when user input contains a platform signal (e.g. `react native`, `expo`, `stream video rn`, `swift`, `ios`, `flutter`), the matching platform peer wins over the web `stream-builder` rows. The web builder is the default only when no platform signal is present.

Cross-cutting rules (secrets, login screen, strict mode, package manager, base UI, moderation Dashboard-only, ...) live once in [`skills/stream/RULES.md`](skills/stream/RULES.md) and apply to every sub-skill.

## Contents

- [`skills/stream/`](skills/stream/) - **Router + CLI**
  - [`SKILL.md`](skills/stream/SKILL.md) - intent classifier, CLI command index, hand-off rules
  - [`RULES.md`](skills/stream/RULES.md) - non-negotiable rules, stated once
  - [`peers.yaml`](skills/stream/peers.yaml) - peer manifest (names, install commands, routing signals)
- [`skills/stream-docs/`](skills/stream-docs/) - **Docs sub-skill**
  - [`SKILL.md`](skills/stream-docs/SKILL.md) - live documentation lookup with cited sources
- [`skills/stream-builder/`](skills/stream-builder/) - **Builder sub-skill**
  - [`SKILL.md`](skills/stream-builder/SKILL.md) - scaffold execution (Steps 0-7)
  - [`builder-ui.md`](skills/stream-builder/builder-ui.md) - UI shell, login screen, theme
  - [`enhance.md`](skills/stream-builder/enhance.md) - add Stream to an existing app
  - [`sdk.md`](skills/stream-builder/sdk.md) - cross-cutting SDK wiring patterns
  - [`references/`](skills/stream-builder/references/) - per-product setup, gotchas, and component blueprints
- [`skills/stream-swift/`](skills/stream-swift/) - **Swift/iOS sub-skill**
  - [`SKILL.md`](skills/stream-swift/SKILL.md) - entrypoint: intent classifier, local project detection, module pointers
  - [`RULES.md`](skills/stream-swift/RULES.md) - Swift/iOS non-negotiable rules
  - [`builder.md`](skills/stream-swift/builder.md) + [`sdk.md`](skills/stream-swift/sdk.md) - shared Swift app integration flow and SDK ownership patterns
  - [`references/`](skills/stream-swift/references/) - product/framework-specific Swift references and blueprints
- [`skills/stream-react-native/`](skills/stream-react-native/) - **React Native Chat + Video sub-skill**
  - [`SKILL.md`](skills/stream-react-native/SKILL.md) - RN/Expo intent classifier with Chat/Video product router, project detection, module pointers
  - [`RULES.md`](skills/stream-react-native/RULES.md) - Chat and Video RN non-negotiable rules (incl. Chat + Video interop)
  - [`credentials.md`](skills/stream-react-native/credentials.md) - API key, token, and optional requested demo-data flow
  - [`builder.md`](skills/stream-react-native/builder.md) + [`sdk.md`](skills/stream-react-native/sdk.md) - shared RN CLI and Expo integration flow across products
  - [`references/`](skills/stream-react-native/references/) - `llms.txt` docs lookup (Chat + Video manifests), Chat RN setup/blueprints, Video RN setup/blueprints (`VIDEO-REACT-NATIVE.md`, `VIDEO-REACT-NATIVE-blueprints.md`), gotchas
- [`skills/stream-android/`](skills/stream-android/) - **Android sub-skill**
  - [`SKILL.md`](skills/stream-android/SKILL.md) - entrypoint: intent classifier, local project detection, module pointers
  - [`RULES.md`](skills/stream-android/RULES.md) - Android non-negotiable rules
  - [`builder.md`](skills/stream-android/builder.md) + [`sdk.md`](skills/stream-android/sdk.md) - shared Android app integration flow and SDK ownership patterns
  - [`references/`](skills/stream-android/references/) - product/framework-specific Android references and blueprints
- [`skills/stream-flutter/`](skills/stream-flutter/) - **Flutter sub-skill**
  - [`SKILL.md`](skills/stream-flutter/SKILL.md) - entrypoint: intent classifier, credentials/token flow, module pointers
  - [`RULES.md`](skills/stream-flutter/RULES.md) - Flutter non-negotiable rules
  - [`builder.md`](skills/stream-flutter/builder.md) + [`sdk.md`](skills/stream-flutter/sdk.md) - shared Flutter app integration flow and SDK ownership patterns
  - [`references/`](skills/stream-flutter/references/) - product/framework-specific Flutter references and blueprints
