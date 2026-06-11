# AGENTS.md - Codex entrypoint for the Stream skill pack

The pack has a generic router, core specialists, and platform peers declared in [`skills/stream/peers.yaml`](skills/stream/peers.yaml).

**Router (start here):** [`skills/stream/SKILL.md`](skills/stream/SKILL.md) - classifies intent, dispatches to a sub-skill.
**Rules (read once per session):** [`skills/stream/RULES.md`](skills/stream/RULES.md) - core web, CLI, docs, and peer-pack routing rules. Platform sub-skills can add their own `RULES.md`.

## Sub-skills

| Sub-skill | Use for |
|---|---|
| [`skills/stream-docs/SKILL.md`](skills/stream-docs/SKILL.md) | Search live SDK documentation from getstream.io (no CLI required) |
| [`skills/stream-builder/SKILL.md`](skills/stream-builder/SKILL.md) | Scaffold a new app, or add Chat/Video/Feeds/Moderation to an existing one |
| [`skills/stream-swift/SKILL.md`](skills/stream-swift/SKILL.md) | Build or integrate Stream Chat/Video/Feeds in Swift/SwiftUI/UIKit/iOS apps |
| [`skills/stream-flutter/SKILL.md`](skills/stream-flutter/SKILL.md) | Build or integrate Stream Chat in Flutter apps (stream_chat_flutter and stream_chat_flutter_core) |

---

## Codex-specific

- **`getstream` CLI first:** The CLI and builder skills need the `getstream` binary. If it is missing, ask the user to install it from https://getstream.io and wait - do not fetch or run an install script. Onboarding (auth, org/app, credentials) runs through `getstream init`. The `stream-docs` skill does not need the CLI.
- **Batch shell** commands into single `bash -ce 'set -euo pipefail; ...'` invocations to minimize approval prompts.
- **Browser sign-in** (`getstream init` / `getstream login`) needs a **separate** terminal invocation so the browser can open.
- **Network:** scaffold (`npx`, `npm`, `getstream` install) needs network - approve **once** per session when prompted.
- **If terminal is denied:** print commands for the user to run locally; continue with Read/file work only.
- **Builder flow:** onboard via `getstream init`, then immediately execute Steps 0-7 from [`skills/stream-builder/SKILL.md`](skills/stream-builder/SKILL.md). No prompts needed.
- **ASCII only:** all files in this repo must contain ASCII characters only. No em/en dashes, smart quotes, ellipsis chars, arrows, checkmarks, or other non-ASCII glyphs - use plain ASCII equivalents (`-`, `'`, `"`, `...`, `->`, `OK`, etc.).

## Install

Install the `getstream` CLI from [getstream.io](https://getstream.io), then:

```bash
getstream skills
```

With no arguments this installs the default set (`stream`, `stream-builder`, `stream-docs`). `getstream init` also sets up your project (auth, org/app, credentials). Other skills install on demand via `getstream skills <name>`.
