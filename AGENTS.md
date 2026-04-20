# AGENTS.md - Codex entrypoint for Stream skill pack

**Entrypoint:** **[`skills/stream/SKILL.md`](skills/stream/SKILL.md)** - router, phase tables, and module paths.
**Rules:** **[`skills/stream/RULES.md`](skills/stream/RULES.md)** - read once per session, every non-negotiable rule stated there.

---

## Codex-specific

- **`stream` CLI first:** For tracks A/B/C/E, run **`SKILL.md` › CLI gate** before any other Stream skill step — if the CLI is missing, follow **`bootstrap.md`** and get user approval to install; do not skip install or continue builder/API work without it. Track D (docs search) does not need the CLI.
- **Batch shell** commands into single `bash -ce 'set -euo pipefail; …'` invocations to minimize approval prompts.
- **`stream auth login`** needs a **separate** terminal invocation so the browser can open (PKCE).
- **Network:** scaffold (`npx`, `npm`, `stream` install) needs network - approve **once** per session when prompted.
- **If terminal is denied:** print commands for the user to run locally; continue with Read/file work only.
- **Builder flow** - A1 (CLI probe) then immediately execute Steps 0–7. No prompts needed.

## Install

```bash
npx skills add GetStream/agent-skills
```
