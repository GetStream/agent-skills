# AGENTS.md - Codex entrypoint for the Stream skill pack

The pack splits across six skills under `skills/`. The `stream` skill is the generic router; the rest are specialists.

**Router (start here):** [`skills/stream/SKILL.md`](skills/stream/SKILL.md) - classifies intent, dispatches to a sub-skill.
**Rules (read once per session):** [`skills/stream/RULES.md`](skills/stream/RULES.md) - core web, CLI, docs, and peer-pack routing rules. Platform sub-skills can add their own `RULES.md`.

## Sub-skills

| Sub-skill | Use for |
|---|---|
| [`skills/stream-cli/SKILL.md`](skills/stream-cli/SKILL.md) | Query Stream data, run `stream api / config / auth`, install the CLI binary |
| [`skills/stream-docs/SKILL.md`](skills/stream-docs/SKILL.md) | Search live SDK documentation from getstream.io (no CLI required) |
| [`skills/stream-builder/SKILL.md`](skills/stream-builder/SKILL.md) | Scaffold a new app, or add Chat/Video/Feeds/Moderation to an existing one |
| [`skills/stream-swift/SKILL.md`](skills/stream-swift/SKILL.md) | Build or integrate Stream in Swift/SwiftUI/UIKit/iOS apps |
| [`skills/stream-react-native/SKILL.md`](skills/stream-react-native/SKILL.md) | Create, build, or integrate Stream Chat React Native in RN CLI or Expo apps |

---

## Codex-specific

- **`stream` CLI first:** For the CLI and builder skills, run [`skills/stream-cli/preflight.md`](skills/stream-cli/preflight.md) before any other Stream skill step - if the CLI is missing, follow [`skills/stream-cli/bootstrap.md`](skills/stream-cli/bootstrap.md) and get user approval to install; do not skip install or continue builder/API work without it. The `stream-docs` skill does not need the CLI.
- **React Native routing:** React Native is declared as a platform peer in [`skills/stream/peers.yaml`](skills/stream/peers.yaml), so `/stream` can route RN signals and `/stream-react-native` can be invoked directly.
- **React Native credentials:** For `stream-react-native` tracks A/B/D, follow [`skills/stream-react-native/credentials.md`](skills/stream-react-native/credentials.md). If the CLI is missing, use [`skills/stream-cli/bootstrap.md`](skills/stream-cli/bootstrap.md) and get user approval to install. React Native Track C reference lookup does not need the CLI.
- **Batch shell** commands into single `bash -ce 'set -euo pipefail; ...'` invocations to minimize approval prompts.
- **`stream auth login`** needs a **separate** terminal invocation so the browser can open (PKCE).
- **Network:** scaffold (`npx`, `npm`, `stream` install) needs network - approve **once** per session when prompted.
- **If terminal is denied:** print commands for the user to run locally; continue with Read/file work only.
- **Builder flow:** preflight (CLI probe) then immediately execute Steps 0-7 from [`skills/stream-builder/SKILL.md`](skills/stream-builder/SKILL.md). No prompts needed.
- **ASCII only:** all files in this repo must contain ASCII characters only. No em/en dashes, smart quotes, ellipsis chars, arrows, checkmarks, or other non-ASCII glyphs - use plain ASCII equivalents (`-`, `'`, `"`, `...`, `->`, `OK`, etc.).

## Install

```bash
npx skills add GetStream/agent-skills
```
