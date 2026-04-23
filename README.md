# Stream Agent Skills

Give your AI coding agent the ability to build, query, and manage [Stream](https://getstream.io) - Chat, Video, Feeds, Moderation, and Swift/iOS integrations.

## Install

```bash
npx skills add GetStream/agent-skills
```

This pack installs two skills:

- `/stream` for cross-platform scaffolding, CLI queries, integration, and live docs search
- `/stream-swift` for SwiftUI, UIKit, Xcode, and iOS Stream integration work

### Install — direct from GitHub (no third-party CLI)

If you'd rather not route through `skills.sh`, clone this repo into your skills directory:

```bash
# Claude Code
git clone https://github.com/GetStream/agent-skills ~/.claude/skills/stream-pack

# Or download a tagged release tarball
curl -L https://github.com/GetStream/agent-skills/archive/refs/heads/main.tar.gz | tar -xz -C ~/.claude/skills/
```

This is byte-for-byte the same content `npx skills add` installs, fetched directly from GitHub.

## What gets installed

This pack is **markdown only** — no code, no postinstall scripts, no binaries. Two install paths touch the network; each is listed below so you can audit before running.

| Step | Trigger | What it does | Source |
|---|---|---|---|
| `npx skills add GetStream/agent-skills` | Manual, by you | Fetches this repo's markdown into your skills directory via the [`skills.sh` CLI](https://skills.sh/docs/cli) ([source](https://github.com/skills-sh/skills-cli)). | GitHub (`GetStream/agent-skills`) |
| `curl -sSL https://getstream.io/cli/install.sh \| bash` | Agent runs only after you approve | Installs the `stream` CLI binary. Skipped entirely for docs-only usage (Track D). Full audit of what the installer does — including SHA-256 verification and TTY confirmation — in [`skills/stream/bootstrap.md`](skills/stream/bootstrap.md#what-the-installer-does). | `getstream.io/cli/` |
| Frontend skill installs (builder only) | Agent asks first, then runs | Installs three third-party skill packs for UI scaffolding — see below. | GitHub (listed) |

### Frontend skills (builder track only)

When you ask the agent to scaffold a new app (Track A) or enhance an existing one (Track E), Step 3 can install three helper skill packs. **The agent surfaces the full list and waits for your confirmation before running any install.**

| Skill | Purpose | Source |
|---|---|---|
| `vercel-react-best-practices` | React/Next.js idioms | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `web-design-guidelines` | Generic UI design polish | [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills) |
| `frontend-design` | Frontend structure | [`anthropics/skills`](https://github.com/anthropics/skills) |

Decline and the builder still runs — Stream reference files cover the SDK wiring; the frontend skills only tune generic UI quality. Tracks B (CLI queries), C (bootstrap), and D (docs search) never trigger these installs.

## What your agent can do

- **Scaffold a full app** - Next.js + Tailwind + Stream SDKs, wired end-to-end in one shot
- **Add products to existing apps** - drop Chat, Video, or Feeds into a project that's already running
- **Build and extend Swift apps** - wire Stream into SwiftUI or UIKit Xcode projects with iOS-specific setup patterns
- **Query live data** - "any active calls?", "show flagged messages", "list my channels" - natural language to CLI
- **Set up moderation** - blocklists, automod config, and content policies via the Stream CLI
- **Answer SDK questions** - token patterns, strict mode, client/server instantiation, theme wiring
- **Search live SDK docs** - ask questions about any Stream SDK, framework, or version; answers come verbatim from getstream.io with citations

## How it works

The skill pack is markdown only - no code, no build step. Each skill has its own `SKILL.md` entrypoint and routes to the right module set for the job:

| Intent | Module |
|---|---|
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
