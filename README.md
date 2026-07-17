# Stream Agent Skills

Give your AI coding agent the ability to build, query, and manage [Stream](https://getstream.io) - Chat, Video, Feeds, and Moderation across React / Next.js, React Native, Swift/iOS, Android, and Flutter apps.

Full documentation lives at [getstream.io/agent-skills](https://getstream.io/agent-skills/) - start with the [Quickstart](https://getstream.io/agent-skills/docs/quickstart/), or read up on [how the skills compare to MCP](https://getstream.io/agent-skills/docs/concepts/skills-vs-mcp/).

## Install

Install the [Stream CLI](https://getstream.io/agent-skills/docs/installation/), then:

```bash
getstream skills
```

With no arguments, `getstream skills` installs the default set - the `stream` router (which includes the CLI layer), `stream-builder`, and `stream-docs`. The web pack (`stream-react`) and platform packs (`stream-swift`, `stream-android`, `stream-react-native`, `stream-flutter`) install on demand via `getstream skills <name>` the first time a task needs them. To set up a project at the same time (auth, org/app selection, credentials), run `getstream init` instead.

Use `/stream` for generic routing, or invoke a skill directly with `/stream-react`, `/stream-builder`, `/stream-docs`, `/stream-swift`, `/stream-android`, `/stream-react-native`, or `/stream-flutter`. Step-by-step instructions are in the [installation guide](https://getstream.io/agent-skills/docs/installation/).

## Skills

Each skill has a reference page on the docs site - the skill names below link to them.

| Skill | Purpose | When to use |
|---|---|---|
| [`/stream`](https://getstream.io/agent-skills/docs/skills/stream/) | **Router + CLI** - classifies intent, dispatches, and runs `getstream` CLI commands | Start here; also handles data queries, app config, and onboarding |
| [`/stream-docs`](https://getstream.io/agent-skills/docs/skills/stream-docs/) | Search live SDK documentation from getstream.io | Explicit SDK token (Chat React, Video iOS, ...), "docs", "how do I ... in <framework>" |
| [`/stream-react`](https://getstream.io/agent-skills/docs/skills/stream-react/) | Build, enhance, audit, migrate, or migrate-from-Sendbird a React / Next.js web app - the default for all web React work | "build me a ... app", "add Chat to this app", "audit my video integration", "upgrade stream-chat-react", "migrate from Sendbird", `stream-chat-react`, `@stream-io/video-react-sdk`, `@stream-io/feeds-react-sdk` |
| [`/stream-builder`](https://getstream.io/agent-skills/docs/skills/stream-builder/) | Framework-agnostic builder - scaffold a new web app, or add Chat/Video/Feeds/Moderation to an existing one | Only when named explicitly ("use stream-builder"); web React work routes to `/stream-react` |
| [`/stream-swift`](https://getstream.io/agent-skills/docs/skills/stream-swift/) | Build or integrate Stream in Swift/SwiftUI/UIKit/iOS apps | Swift, SwiftUI, UIKit, iOS, Xcode |
| [`/stream-android`](https://getstream.io/agent-skills/docs/skills/stream-android/) | Build or integrate Stream in Android/Jetpack Compose apps | Android, Jetpack Compose, Kotlin, Android Studio, Gradle |
| [`/stream-react-native`](https://getstream.io/agent-skills/docs/skills/stream-react-native/) | Create, build, or integrate Stream Chat or Stream Video React Native in RN CLI or Expo apps | React Native, Expo, `stream-chat-react-native`, `stream-chat-expo`, `@stream-io/video-react-native-sdk`, video call, livestream, audio room, ringing |
| [`/stream-flutter`](https://getstream.io/agent-skills/docs/skills/stream-flutter/) | Build or integrate Stream Chat in Flutter apps | Flutter, Dart, `stream_chat_flutter`, `stream_chat_flutter_core` |

The router (`/stream`) owns routing, the CLI layer (queries, app config, onboarding), and the cross-cutting rules in [`skills/stream/RULES.md`](skills/stream/RULES.md) (explained in [Rules Every Skill Follows](https://getstream.io/agent-skills/docs/concepts/skill-rules/)). Platform sub-skills can add their own `RULES.md`.

## What gets installed

The skills are plain markdown. Installation and on-demand skill fetching run through the `getstream` CLI; the only other network touch is the optional frontend-skill packs the builder can add with your consent. The full trust model is documented in [Security and Trust](https://getstream.io/agent-skills/docs/concepts/security/).

| Step | Trigger | What it does | Source |
|---|---|---|---|
| `getstream skills <name>` | Agent, on demand (or you) | Fetches a skill's markdown into your skills directory via the `getstream` CLI. | GitHub (`GetStream/agent-skills`) |
| Frontend skill installs (builder only) | Agent asks first, then runs | Installs three third-party skill packs for UI scaffolding - see below. | GitHub (listed) |

### Frontend skills (builder only)

When you ask the agent to scaffold a new app or enhance an existing one via `/stream-builder`, Step 3 can install three helper skill packs. **The agent surfaces the full list and waits for your confirmation before running any install.** `/stream-react` never installs these - its builds rely on the Stream references plus Shadcn, and it only uses these packs if they are already present in the session.

| Skill | Purpose | Source |
|---|---|---|
| `vercel-react-best-practices` | React/Next.js idioms | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `web-design-guidelines` | Generic UI design polish | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `frontend-design` | Frontend structure | [`anthropics/skills`](https://github.com/anthropics/skills) |

Decline and the builder still runs - Stream reference files cover the SDK wiring; the frontend skills only tune generic UI quality. The docs skill never triggers these installs.

## What your agent can do

- **Scaffold a full app** - Next.js + Tailwind + Stream SDKs, wired end-to-end in one shot (`/stream-react`)
- **Add products to existing apps** - drop Chat, Video, or Feeds into a project that's already running (`/stream-react`)
- **Audit and migrate integrations** - review a Video integration against best practices, upgrade an SDK version from the live release guide, or migrate an existing Sendbird app to Stream Chat React (`/stream-react`)
- **Build and extend Swift apps** - wire Stream into SwiftUI or UIKit Xcode projects with iOS-specific setup patterns (`/stream-swift`)
- **Build and extend Android apps** - wire Stream into Jetpack Compose Android Studio / Gradle projects with Android-specific setup patterns (`/stream-android`)
- **Build and extend React Native apps** - wire Stream Chat or Stream Video into Expo or RN CLI projects (`/stream-react-native`)
- **Query live data** - "any active calls?", "show flagged messages", "list my channels" - natural language to the `getstream` CLI (`/stream`)
- **Configure apps and moderation** - channel types, roles, permissions, blocklists, automod - via the `getstream` CLI (`/stream`)
- **Answer SDK questions** - token patterns, strict mode, client/server instantiation, theme wiring (`/stream-react` or `/stream-docs`)
- **Search live SDK docs** - ask questions about any Stream SDK, framework, or version; answers come verbatim from getstream.io with citations (`/stream-docs`)

## How it works

The `/stream` router classifies intent, runs `getstream` CLI commands itself (queries, app config, onboarding), and routes building and docs to dedicated sub-skills. Platform sub-skills such as `/stream-react-native` can also be invoked explicitly.

| Intent | Skill |
|---|---|
| Build a new web app | `stream-react` (Track A) |
| Add a product to an existing app | `stream-react` (Track E) |
| Audit an existing Video integration | `stream-react` (Track F) |
| Migrate / upgrade an SDK version | `stream-react` (Track M) |
| Migrate a web app from Sendbird | `stream-react` (Track S) |
| Data queries, app config, and CLI operations | `stream` (CLI, built in) |
| SDK wiring during scaffold/enhance | `stream-react` + its `sdk.md` and `references/*.md` |
| Framework-agnostic builds, only when named explicitly | `stream-builder` |
| Build or integrate a React Native CLI/Expo app | `stream-react-native` + its `sdk.md` and `references/*.md` |
| Search the official SDK documentation (no CLI needed) | `stream-docs` (Track D) |
| Build or integrate a Swift/iOS app | `stream-swift` (docs orchestrator: `docs-map.md` + `setup.md`) |
| Build or integrate an Android app | `stream-android` + its `builder.md`, `sdk.md`, and `references/*.md` |
| Build or integrate a Flutter app | `stream-flutter` + its `builder.md`, `sdk.md`, and `references/*.md` |

> **Routing precedence:** when user input contains a platform signal (e.g. `react native`, `expo`, `stream video rn`, `swift`, `ios`, `flutter`), the matching platform peer wins over the web `stream-react` rows. The web pack is the default only when no platform signal is present; `stream-builder` runs only when the user names it explicitly.

Cross-cutting rules (secrets, login screen, strict mode, package manager, base UI, moderation Dashboard-only, ...) live once in [`skills/stream/RULES.md`](skills/stream/RULES.md) and apply to every sub-skill - see [Rules Every Skill Follows](https://getstream.io/agent-skills/docs/concepts/skill-rules/) for the rationale behind each.

## Contents

- [`skills/stream/`](skills/stream/) - **Router + CLI**
  - [`SKILL.md`](skills/stream/SKILL.md) - intent classifier, CLI command index, hand-off rules
  - [`RULES.md`](skills/stream/RULES.md) - non-negotiable rules, stated once
  - [`peers.yaml`](skills/stream/peers.yaml) - peer manifest (names, install commands, routing signals)
- [`skills/stream-docs/`](skills/stream-docs/) - **Docs sub-skill**
  - [`SKILL.md`](skills/stream-docs/SKILL.md) - live documentation lookup with cited sources
- [`skills/stream-react/`](skills/stream-react/) - **React web sub-skill** (default for web React / Next.js work)
  - [`SKILL.md`](skills/stream-react/SKILL.md) - five tracks: scaffold (Steps 0-7), enhance, Video audit, SDK migration, Sendbird migration
  - [`RULES.md`](skills/stream-react/RULES.md) - React/Next.js non-negotiable rules
  - [`builder.md`](skills/stream-react/builder.md) - provisioning, use-case matching, page flow
  - [`builder-ui.md`](skills/stream-react/builder-ui.md) - UI shell, login screen, theme, layout/sizing
  - [`enhance.md`](skills/stream-react/enhance.md) - add Stream to an existing React app
  - [`migrate.md`](skills/stream-react/migrate.md) - docs-driven SDK version migration (Track M)
  - [`sendbird-migration.md`](skills/stream-react/sendbird-migration.md) - migrate a Sendbird app to Stream Chat React (Track S)
  - [`sdk.md`](skills/stream-react/sdk.md) - cross-cutting SDK wiring patterns
  - [`references/`](skills/stream-react/references/) - per-product setup + blueprints, `docs-map.md`, design-matching, custom-ui, Sendbird mapping tables
- [`skills/stream-builder/`](skills/stream-builder/) - **Builder sub-skill** (explicit invocation only)
  - [`SKILL.md`](skills/stream-builder/SKILL.md) - scaffold execution (Steps 0-7)
  - [`builder-ui.md`](skills/stream-builder/builder-ui.md) - UI shell, login screen, theme
  - [`enhance.md`](skills/stream-builder/enhance.md) - add Stream to an existing app
  - [`sdk.md`](skills/stream-builder/sdk.md) - cross-cutting SDK wiring patterns
  - [`references/`](skills/stream-builder/references/) - per-product setup, gotchas, and component blueprints
- [`skills/stream-swift/`](skills/stream-swift/) - **Swift/iOS sub-skill** (docs orchestrator)
  - [`SKILL.md`](skills/stream-swift/SKILL.md) - entrypoint: the `.md` docs convention, intent classifier, docs-lookup loop
  - [`RULES.md`](skills/stream-swift/RULES.md) - Swift/iOS non-negotiable rules + curated iOS pitfalls
  - [`docs-map.md`](skills/stream-swift/docs-map.md) - intent -> exact official iOS docs page (Chat/Video/Feeds, SwiftUI/UIKit), plus best-practices pages and a source-code/example-app fallback (SDK repos) for what the docs do not cover
  - [`setup.md`](skills/stream-swift/setup.md) - CLI-driven credentials, install, and client-wiring flow
  - [`push.md`](skills/stream-swift/push.md) - seamless push runbook: APNs key, CLI push-provider creation, client wiring, VoIP + CallKit
  - [`design-matching.md`](skills/stream-swift/design-matching.md) - reproduce a reference design with the **pre-built components**: region -> `ViewFactory`/`Styles`/theming map
  - [`custom-ui.md`](skills/stream-swift/custom-ui.md) - the **components-vs-custom** decision + how to build a livestream/bespoke surface on the low-level client + State Layer
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
