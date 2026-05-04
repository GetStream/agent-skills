# Stream Agent Skills

Give your AI coding agent the ability to build, query, and manage [Stream](https://getstream.io) - Chat, Video, Feeds, Moderation, and React Native Chat.

## Install

```bash
npx skills add GetStream/agent-skills
```

That installs all five skills below - a router (`stream`) plus four specialists (`stream-cli`, `stream-docs`, `stream-builder`, `stream-react-native`). Use `/stream` and the agent picks the right one for the task, or invoke a sub-skill directly with `/stream-cli`, `/stream-docs`, `/stream-builder`, or `/stream-react-native`.

### Install - direct from GitHub (no third-party CLI)

If you'd rather not route through `skills.sh`, clone this repo into your skills directory:

```bash
# Claude Code
git clone https://github.com/GetStream/agent-skills ~/.claude/skills/stream-pack

# Or download a tagged release tarball
curl -L https://github.com/GetStream/agent-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills/
```

This is byte-for-byte the same content `npx skills add` installs, fetched directly from GitHub.

## Skills

### Core

| Skill | Purpose | When to use |
|---|---|---|
| `/stream` | **Router** - classifies intent and dispatches | Always start here if you don't know which sub-skill applies |

The router skill at [`skills/stream/`](skills/stream/) also owns the cross-cutting [`RULES.md`](skills/stream/RULES.md) - non-negotiables that every sub-skill inherits.

### Sub-skills

| Skill | Purpose | When to use |
|---|---|---|
| `/stream-cli` | Query Stream data, run `stream api / config / auth`, install the CLI binary | "list channels", "show flagged", "find users", `stream api ...`, "install the CLI" |
| `/stream-docs` | Search live SDK documentation from getstream.io | Explicit SDK token (Chat React, Video iOS, ...), "docs", "how do I ... in <framework>" |
| `/stream-builder` | Scaffold a new app, or add Chat/Video/Feeds/Moderation to an existing one | "build me a ... app", "scaffold", "add Chat to this app", "integrate Video" |
| `/stream-react-native` | Create, build, or integrate Stream Chat React Native v9 in RN CLI or Expo apps | React Native, Expo, `stream-chat-react-native`, `stream-chat-expo`, v9 migration, ChannelList, MessageList, threads, theming, offline |

## What gets installed

This pack is **markdown only** - no code, no postinstall scripts, no binaries. Network-touching install paths are listed below so you can audit before running.

| Step | Trigger | What it does | Source |
|---|---|---|---|
| `npx skills add GetStream/agent-skills` | Manual, by you | Fetches this repo's markdown into your skills directory via the [`skills.sh` CLI](https://skills.sh/docs/cli) ([source](https://github.com/skills-sh/skills-cli)). | GitHub (`GetStream/agent-skills`) |
| `curl -sSL https://getstream.io/cli/install.sh \| bash` | Agent runs only after you approve | Installs the `stream` CLI binary. Skipped entirely for docs-only usage (`/stream-docs`) and React Native reference lookup (`/stream-react-native` Track C). Full audit of what the installer does - including SHA-256 verification and TTY confirmation - in [`skills/stream-cli/bootstrap.md`](skills/stream-cli/bootstrap.md#what-the-installer-does). | `getstream.io/cli/` |
| Frontend skill installs (builder only) | Agent asks first, then runs | Installs three third-party skill packs for UI scaffolding - see below. | GitHub (listed) |
| React Native app scaffold (`/stream-react-native`) | Agent runs only when asked to create a new RN/Expo Chat app | Runs `npx create-expo-app@latest` or `npx @react-native-community/cli@latest init`, then continues with Stream Chat setup. Expo apps use dev-client/native-build setup. | npm / framework registries |
| React Native package installs (`/stream-react-native`) | Agent runs only while creating or wiring an RN/Expo app | Installs `stream-chat-react-native` or `stream-chat-expo` plus required peer dependencies for Chat RN v9, using the project's package manager or `npx expo install`. Expo lane includes `expo-dev-client`. | npm / Expo package registry |

### Frontend skills (builder only)

When you ask the agent to scaffold a new app or enhance an existing one via `/stream-builder`, Step 3 can install three helper skill packs. **The agent surfaces the full list and waits for your confirmation before running any install.**

| Skill | Purpose | Source |
|---|---|---|
| `vercel-react-best-practices` | React/Next.js idioms | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `web-design-guidelines` | Generic UI design polish | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `frontend-design` | Frontend structure | [`anthropics/skills`](https://github.com/anthropics/skills) |

Decline and the builder still runs - Stream reference files cover the SDK wiring; the frontend skills only tune generic UI quality. The CLI and docs skills never trigger these installs.

## What your agent can do

- **Scaffold a full app** - Next.js + Tailwind + Stream SDKs, wired end-to-end in one shot (`/stream-builder`)
- **Add products to existing apps** - drop Chat, Video, or Feeds into a project that's already running (`/stream-builder`)
- **Create and extend React Native Chat apps** - create a new Expo/RN CLI Chat app or wire Stream Chat RN v9 into an existing app, including ChannelList, MessageList, threads, theming, offline support, and v9 migration (`/stream-react-native`)
- **Query live data** - "any active calls?", "show flagged messages", "list my channels" - natural language to CLI (`/stream-cli`)
- **Set up moderation** - blocklists, automod config, and content policies via the Stream CLI (`/stream-cli`)
- **Answer SDK questions** - token patterns, strict mode, client/server instantiation, theme wiring (`/stream-builder` or `/stream-docs`)
- **Search live SDK docs** - ask questions about any Stream SDK, framework, or version; answers come verbatim from getstream.io with citations (`/stream-docs`)

## How it works

The skill pack is markdown only - no code, no build step. The agent reads the `stream` router's `SKILL.md`, classifies intent, then either skips straight to docs (`stream-docs` - no CLI required) or runs the CLI gate and context probe before routing to the right sub-skill:

| Intent | Sub-skill |
|---|---|
| Build a new web app | `stream-builder` (Track A) |
| Create a new React Native or Expo Chat v9 app | `stream-react-native` (Track A) |
| Add a product to an existing app | `stream-builder` (Track E) |
| Data queries and CLI operations | `stream-cli` (Track B) |
| Install the Stream CLI | `stream-cli` (Track C) |
| SDK wiring during builder/enhance | `stream-builder` + its `sdk.md` and `references/*.md` |
| React Native or Expo Chat v9 creation/setup/integration | `stream-react-native` + its `sdk.md` and `references/*.md` |
| Search the official SDK documentation (no CLI needed) | `stream-docs` (Track D) |

Cross-cutting web/router rules (secrets, login screen, strict mode, package manager, base UI, moderation Dashboard-only, ...) live once in [`skills/stream/RULES.md`](skills/stream/RULES.md). React Native-specific non-negotiables live in [`skills/stream-react-native/RULES.md`](skills/stream-react-native/RULES.md).

## Contents

- [`skills/stream/`](skills/stream/) - **Router skill**
  - [`SKILL.md`](skills/stream/SKILL.md) - entrypoint: intent classifier, dispatch table, hand-off rules
  - [`RULES.md`](skills/stream/RULES.md) - non-negotiable rules, stated once
- [`skills/stream-cli/`](skills/stream-cli/) - **CLI sub-skill**
  - [`SKILL.md`](skills/stream-cli/SKILL.md) - CLI workflow, credential resolution, exit-code recovery
  - [`cli-cookbook.md`](skills/stream-cli/cli-cookbook.md) - body examples for tricky endpoints, filter/sort syntax
  - [`bootstrap.md`](skills/stream-cli/bootstrap.md) - CLI binary installer audit
  - [`preflight.md`](skills/stream-cli/preflight.md) - project signals + CLI gate + auth check (used by builder too)
- [`skills/stream-docs/`](skills/stream-docs/) - **Docs sub-skill**
  - [`SKILL.md`](skills/stream-docs/SKILL.md) - live documentation lookup with cited sources
- [`skills/stream-builder/`](skills/stream-builder/) - **Builder sub-skill**
  - [`SKILL.md`](skills/stream-builder/SKILL.md) - scaffold execution (Steps 0-7)
  - [`builder-ui.md`](skills/stream-builder/builder-ui.md) - UI shell, login screen, theme
  - [`enhance.md`](skills/stream-builder/enhance.md) - add Stream to an existing app
  - [`sdk.md`](skills/stream-builder/sdk.md) - cross-cutting SDK wiring patterns
  - [`references/`](skills/stream-builder/references/) - per-product setup, gotchas, and component blueprints
- [`skills/stream-react-native/`](skills/stream-react-native/) - **React Native Chat sub-skill**
  - [`SKILL.md`](skills/stream-react-native/SKILL.md) - RN/Expo intent classifier, project detection, module pointers
  - [`RULES.md`](skills/stream-react-native/RULES.md) - Chat RN v9 non-negotiable rules
  - [`credentials.md`](skills/stream-react-native/credentials.md) - API key, token, and optional requested demo-data flow
  - [`builder.md`](skills/stream-react-native/builder.md) + [`sdk.md`](skills/stream-react-native/sdk.md) - shared RN CLI and Expo integration flow
  - [`references/`](skills/stream-react-native/references/) - `llms.txt` docs lookup, Chat RN v9 setup, gotchas, and screen blueprints
- [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) - Cursor plugin manifest
