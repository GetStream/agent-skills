# AGENTS.md - Codex entrypoint for the Stream skill pack

The pack has a generic router (which includes the CLI), core specialists, and platform peers declared in [`skills/stream/peers.yaml`](skills/stream/peers.yaml).

**Router (start here):** [`skills/stream/SKILL.md`](skills/stream/SKILL.md) - classifies intent, dispatches to a sub-skill, and runs `getstream` CLI commands.
**Rules (read once per session):** [`skills/stream/RULES.md`](skills/stream/RULES.md) - core web, CLI, docs, and peer-pack routing rules. Platform sub-skills can add their own `RULES.md`.

## Sub-skills

| Sub-skill | Use for |
|---|---|
| [`skills/stream-docs/SKILL.md`](skills/stream-docs/SKILL.md) | Search live SDK documentation from getstream.io (no CLI required) |
| [`skills/stream-react/SKILL.md`](skills/stream-react/SKILL.md) | **Default for web React/Next.js.** Scaffold, enhance, audit, or migrate a React/Next.js app with Chat/Video/Feeds/Moderation |
| [`skills/stream-builder/SKILL.md`](skills/stream-builder/SKILL.md) | Framework-agnostic builder - only when named explicitly; web React/Next.js defaults to stream-react |
| [`skills/stream-swift/SKILL.md`](skills/stream-swift/SKILL.md) | Build or integrate Stream Chat/Video/Feeds in Swift/SwiftUI/UIKit/iOS apps |
| [`skills/stream-flutter/SKILL.md`](skills/stream-flutter/SKILL.md) | Build or integrate Stream Chat in Flutter apps (stream_chat_flutter and stream_chat_flutter_core) |

(Querying data and running CLI commands is handled by the router itself - see its **Stream CLI** section.)

---

## Codex-specific

- **`getstream` CLI first:** The web/platform build skills need the `getstream` binary. If it is missing, ask the user to install it from https://getstream.io and wait - do not fetch or run an install script. Onboarding (auth, org/app, credentials) runs through `getstream init`. **No CLI needed** for `stream-docs`, nor for read-only/local-only tracks - a platform pack's **audit** (e.g. `stream-react` Track F) and **migrate** (e.g. `stream-react` Track M) inspect/edit local files and the live docs only, so they skip onboarding entirely.
- **Batch shell** commands into single `bash -ce 'set -euo pipefail; ...'` invocations to minimize approval prompts.
- **Browser sign-in** (`getstream init` / `getstream login`) needs a **separate** terminal invocation so the browser can open.
- **Network:** scaffold (`npx`, `npm`) needs network - approve **once** per session when prompted.
- **If terminal is denied:** print commands for the user to run locally; continue with Read/file work only.
- **Builder flow (web):** for React/Next.js builds, onboard via `getstream init` then immediately execute Steps 0-7 from [`skills/stream-react/SKILL.md`](skills/stream-react/SKILL.md) (the default web pack). Use [`skills/stream-builder/SKILL.md`](skills/stream-builder/SKILL.md) only when the user names it explicitly. No prompts needed.
- **ASCII only:** all files in this repo must contain ASCII characters only. No em/en dashes, smart quotes, ellipsis chars, arrows, checkmarks, or other non-ASCII glyphs - use plain ASCII equivalents (`-`, `'`, `"`, `...`, `->`, `OK`, etc.).

## Install

Install the `getstream` CLI from [getstream.io](https://getstream.io), then:

```bash
getstream skills
```

With no arguments this installs the default set (`stream`, `stream-builder`, `stream-docs`). `getstream init` also sets up your project (auth, org/app, credentials). Other skills install on demand via `getstream skills <name>`.
