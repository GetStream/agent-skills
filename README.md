# Stream Agent Skills

Give your AI coding agent the ability to build, query, and manage [Stream](https://getstream.io) - Chat, Video, Feeds, and Moderation.

```bash
npx skills add GetStream/agent-skills
```

## What your agent can do

- **Scaffold a full app** - Next.js + Tailwind + Stream SDKs, wired end-to-end in one shot
- **Add products to existing apps** - drop Chat, Video, or Feeds into a project that's already running
- **Query live data** - "any active calls?", "show flagged messages", "list my channels" - natural language to CLI
- **Set up moderation** - blocklists, automod config, and content policies via the Stream CLI
- **Answer SDK questions** - token patterns, strict mode, client/server instantiation, theme wiring
- **Search live SDK docs** - ask questions about any Stream SDK, framework, or version; answers come verbatim from getstream.io with citations

## How it works

The skill pack is markdown only - no code, no build step. Your agent reads `SKILL.md`, detects context (CLI state, credentials, project type), and routes to the right module:

| Intent | Module |
|---|---|
| Build a new app | `builder.md` + `builder-ui.md` |
| Add a product to an existing app | `builder.md` + `references/*.md` |
| Data queries and CLI operations | `cli.md` + `cli-cookbook.md` |
| SDK and integration questions | `sdk.md` + `references/*.md` |
| Install the Stream CLI | `bootstrap.md` |
| Search the official SDK documentation | `stream-docs/SKILL.md` |

## Contents

- [`skills/stream/SKILL.md`](skills/stream/SKILL.md) - entrypoint: context detection, intent routing, phase tables
- [`skills/stream/RULES.md`](skills/stream/RULES.md) - non-negotiable rules, stated once
- [`skills/stream/builder.md`](skills/stream/builder.md) - scaffold execution (Steps 0-7); [`builder-ui.md`](skills/stream/builder-ui.md) - UI shell and theme
- [`skills/stream/cli.md`](skills/stream/cli.md) + [`cli-cookbook.md`](skills/stream/cli-cookbook.md) - CLI workflow and query examples
- [`skills/stream/sdk.md`](skills/stream/sdk.md) - cross-cutting SDK patterns
- `skills/stream/references/*.md` - per-product setup, gotchas, and component blueprints
- [`skills/stream-docs/SKILL.md`](skills/stream-docs/SKILL.md) - live documentation lookup: resolves your SDK from project context or explicit input, then answers from getstream.io with cited sources