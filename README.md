# Stream Agent Skills

Give your AI coding agent the ability to build, query, and manage [Stream](https://getstream.io) - Chat, Video, Feeds, Moderation, and Swift/iOS integrations.

## Install

```bash
npx skills add GetStream/agent-skills
```

That installs all four skills below - a router (`stream`) plus three specialists (`stream-cli`, `stream-docs`, `stream-builder`). Use `/stream` and the agent picks the right one for the task, or invoke a sub-skill directly with `/stream-cli`, `/stream-docs`, or `/stream-builder`.

### Install - direct from GitHub (no third-party CLI)

If you'd rather not route through `skills.sh`, clone this repo into your skills directory:

```bash
# Claude Code
git clone https://github.com/GetStream/agent-skills ~/.claude/skills/stream-pack

# Or download a tagged release tarball
curl -L https://github.com/GetStream/agent-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills/
```

This is byte-for-byte the same content `npx skills add` installs, fetched directly from GitHub.

### Install one skill at a time (Claude Code plugin marketplace)

The pack is registered as a Claude Code plugin marketplace, so you can install a single sub-skill if that's all you need:

```bash
/plugin marketplace add GetStream/agent-skills
/plugin install cli@stream-skills        # just the CLI sub-skill
/plugin install docs@stream-skills       # just the docs sub-skill
/plugin install builder@stream-skills    # just the builder sub-skill
/plugin install core@stream-skills       # just the router + RULES
```

The `npx skills add` install always pulls everything; the plugin marketplace path lets you opt in granularly.

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

## What gets installed

This pack is **markdown only** - no code, no postinstall scripts, no binaries. Two install paths touch the network; each is listed below so you can audit before running.

| Step | Trigger | What it does | Source |
|---|---|---|---|
| `npx skills add GetStream/agent-skills` | Manual, by you | Fetches this repo's markdown into your skills directory via the [`skills.sh` CLI](https://skills.sh/docs/cli) ([source](https://github.com/skills-sh/skills-cli)). | GitHub (`GetStream/agent-skills`) |
| `curl -sSL https://getstream.io/cli/install.sh \| bash` | Agent runs only after you approve | Installs the `stream` CLI binary. Skipped entirely for docs-only usage (`/stream-docs`). Full audit of what the installer does - including SHA-256 verification and TTY confirmation - in [`skills/stream-cli/bootstrap.md`](skills/stream-cli/bootstrap.md#what-the-installer-does). | `getstream.io/cli/` |
| Frontend skill installs (builder only) | Agent asks first, then runs | Installs three third-party skill packs for UI scaffolding - see below. | GitHub (listed) |

### Frontend skills (builder only)

When you ask the agent to scaffold a new app or enhance an existing one via `/stream-builder`, Step 3 can install three helper skill packs. **The agent surfaces the full list and waits for your confirmation before running any install.**

| Skill | Purpose | Source |
|---|---|---|
| `vercel-react-best-practices` | React/Next.js idioms | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `web-design-guidelines` | Generic UI design polish | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `frontend-design` | Frontend structure | [`anthropics/skills`](https://github.com/anthropics/skills) |

Decline and the builder still runs - Stream reference files cover the SDK wiring; the frontend skills only tune generic UI quality. The CLI and docs skills never trigger these installs.

## What your agent can do

<<<<<<< HEAD
- **Scaffold a full app** - Next.js + Tailwind + Stream SDKs, wired end-to-end in one shot
- **Add products to existing apps** - drop Chat, Video, or Feeds into a project that's already running
- **Build and extend Swift apps** - wire Stream into SwiftUI or UIKit Xcode projects with iOS-specific setup patterns
- **Query live data** - "any active calls?", "show flagged messages", "list my channels" - natural language to CLI
- **Set up moderation** - blocklists, automod config, and content policies via the Stream CLI
- **Answer SDK questions** - token patterns, strict mode, client/server instantiation, theme wiring
- **Search live SDK docs** - ask questions about any Stream SDK, framework, or version; answers come verbatim from getstream.io with citations

## How it works

The skill pack is markdown only - no code, no build step. Each skill has its own `SKILL.md` entrypoint and routes to the right module set for the job:
=======
- **Scaffold a full app** - Next.js + Tailwind + Stream SDKs, wired end-to-end in one shot (`/stream-builder`)
- **Add products to existing apps** - drop Chat, Video, or Feeds into a project that's already running (`/stream-builder`)
- **Query live data** - "any active calls?", "show flagged messages", "list my channels" - natural language to CLI (`/stream-cli`)
- **Set up moderation** - blocklists, automod config, and content policies via the Stream CLI (`/stream-cli`)
- **Answer SDK questions** - token patterns, strict mode, client/server instantiation, theme wiring (`/stream-builder` or `/stream-docs`)
- **Search live SDK docs** - ask questions about any Stream SDK, framework, or version; answers come verbatim from getstream.io with citations (`/stream-docs`)

## How it works

The skill pack is markdown only - no code, no build step. The agent reads the `stream` router's `SKILL.md`, classifies intent, then either skips straight to docs (`stream-docs` - no CLI required) or runs the CLI gate and context probe before routing to the right sub-skill:
>>>>>>> 1e839d1c54a5e9976e795b8c4c6dec9df36b1aa4

| Intent | Sub-skill |
|---|---|
<<<<<<< HEAD
| Build a new app | `builder.md` + `builder-ui.md` |
| Add a product to an existing app | `builder.md` + `references/*.md` |
| Data queries and CLI operations | `cli.md` + `cli-cookbook.md` |
| SDK wiring during builder/enhance | `sdk.md` + `references/*.md` |
| Install the Stream CLI | `bootstrap.md` |
| Search the official SDK documentation (no CLI needed) | `docs-search.md` |
| Build or integrate a Swift/iOS app | `skills/stream-swift/builder.md` + `skills/stream-swift/sdk.md` + `skills/stream-swift/references/*.md` |

## Contents

- [`skills/stream/SKILL.md`](skills/stream/SKILL.md) - entrypoint: intent classifier, conditional context detection, phase tables
- [`skills/stream/RULES.md`](skills/stream/RULES.md) - non-negotiable rules, stated once
- [`skills/stream/builder.md`](skills/stream/builder.md) - scaffold execution (Steps 0-7); [`builder-ui.md`](skills/stream/builder-ui.md) - UI shell and theme
- [`skills/stream/cli.md`](skills/stream/cli.md) + [`cli-cookbook.md`](skills/stream/cli-cookbook.md) - CLI workflow and query examples
- [`skills/stream/sdk.md`](skills/stream/sdk.md) - cross-cutting SDK patterns
- [`skills/stream/docs-search.md`](skills/stream/docs-search.md) - live documentation lookup: resolves your SDK from project context or explicit input, then answers from getstream.io with cited sources
- `skills/stream/references/*.md` - per-product setup, gotchas, and component blueprints
- [`skills/stream-swift/SKILL.md`](skills/stream-swift/SKILL.md) - Swift/iOS entrypoint: intent classifier, local project detection, module pointers
- [`skills/stream-swift/RULES.md`](skills/stream-swift/RULES.md) - Swift/iOS non-negotiable rules
- [`skills/stream-swift/builder.md`](skills/stream-swift/builder.md) + [`skills/stream-swift/sdk.md`](skills/stream-swift/sdk.md) - shared Swift app integration flow and SDK ownership patterns
- `skills/stream-swift/references/*.md` - product/framework-specific Swift references and blueprints
=======
| Build a new app | `stream-builder` (Track A) |
| Add a product to an existing app | `stream-builder` (Track E) |
| Data queries and CLI operations | `stream-cli` (Track B) |
| Install the Stream CLI | `stream-cli` (Track C) |
| SDK wiring during builder/enhance | `stream-builder` + its `sdk.md` and `references/*.md` |
| Search the official SDK documentation (no CLI needed) | `stream-docs` (Track D) |

Cross-cutting rules (secrets, login screen, strict mode, package manager, base UI, moderation Dashboard-only, ...) live once in [`skills/stream/RULES.md`](skills/stream/RULES.md) and apply to every sub-skill.

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
- [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) - Claude Code plugin manifest for granular installs
>>>>>>> 1e839d1c54a5e9976e795b8c4c6dec9df36b1aa4
