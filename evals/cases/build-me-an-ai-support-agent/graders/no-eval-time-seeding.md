---
type: tool_used
tool: Bash
input_match: getstream api \S* ?(UpsertUsers|SendMessage|CreateChannel(?!Type)|UpsertUser\b)|\b(node|npx|tsx|bun|deno run|npm run|pnpm|yarn) \S*seed
min: 0
max: 0
---
No demo users, channels or messages seeded through the CLI during the build.
Seeding through a script the agent wrote (`node server/seed.mjs`, `npm run seed`) counts the same as seeding through the CLI.
