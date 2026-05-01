# AGENTS.md — Codex entrypoint for the Stream skill pack

The pack splits across four skills under `skills/`. The `stream` skill is the router; the rest are specialists.

**Router (start here):** [`skills/stream/SKILL.md`](skills/stream/SKILL.md) — classifies intent, dispatches to a sub-skill.
**Rules (read once per session):** [`skills/stream/RULES.md`](skills/stream/RULES.md) — every non-negotiable rule, applies to every sub-skill.

## Sub-skills

| Sub-skill | Use for |
|---|---|
| [`skills/stream-cli/SKILL.md`](skills/stream-cli/SKILL.md) | Query Stream data, run `stream api / config / auth`, install the CLI binary |
| [`skills/stream-docs/SKILL.md`](skills/stream-docs/SKILL.md) | Search live SDK documentation from getstream.io (no CLI required) |
| [`skills/stream-builder/SKILL.md`](skills/stream-builder/SKILL.md) | Scaffold a new app, or add Chat/Video/Feeds/Moderation to an existing one |

---

## Codex-specific

- **`stream` CLI first:** For the CLI and builder skills, run [`skills/stream-cli/preflight.md`](skills/stream-cli/preflight.md) before any other Stream skill step — if the CLI is missing, follow [`skills/stream-cli/bootstrap.md`](skills/stream-cli/bootstrap.md) and get user approval to install; do not skip install or continue builder/API work without it. The `stream-docs` skill does not need the CLI.
- **Batch shell** commands into single `bash -ce 'set -euo pipefail; …'` invocations to minimize approval prompts.
- **`stream auth login`** needs a **separate** terminal invocation so the browser can open (PKCE).
- **Network:** scaffold (`npx`, `npm`, `stream` install) needs network — approve **once** per session when prompted.
- **If terminal is denied:** print commands for the user to run locally; continue with Read/file work only.
- **Builder flow:** preflight (CLI probe) then immediately execute Steps 0–7 from [`skills/stream-builder/SKILL.md`](skills/stream-builder/SKILL.md). No prompts needed.

## Install

```bash
npx skills add GetStream/agent-skills --skill '*'
```

`--skill '*'` selects all four skills (router + three specialists) without the per-skill picker; without `-y` the CLI still walks you through agent selection. The router auto-installs any missing sub-skill on first use, so a partial install will self-heal.
