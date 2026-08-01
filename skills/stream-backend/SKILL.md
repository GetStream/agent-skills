---
name: stream-backend
description: "Migrate a server-side (backend) Stream integration from a legacy hand-written SDK to the generated OpenAPI SDK. First supported path: Go - github.com/GetStream/stream-chat-go to github.com/GetStream/getstream-go. Language-parameterized: it detects or asks the server language, then runs that language's migration. Triggers on 'migrate stream-chat-go to getstream-go', 'move off stream-chat-go', 'switch to getstream-go', 'upgrade my Stream server SDK', and server SDK tokens (stream-chat-go, getstream-go). NOT for client / frontend SDKs (iOS, Android, React, React Native, Flutter) - those have their own packs (stream-swift, stream-android, stream-react, stream-react-native, stream-flutter)."
license: See LICENSE in repository root
compatibility: Requires the customer's server-side project checkout, plus the toolchain of the language being migrated. For Go that means the Go toolchain, version 1.23 or newer, because the migration runs a codemod built with it. Fetches the official migration guide live, so network access to github.com and raw.githubusercontent.com is needed, and `go run` needs to reach the Go module proxy. No Stream account or CLI onboarding is required - this is a local-only, docs-driven code migration.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  WebFetch(domain:getstream.io),
  WebFetch(domain:github.com),
  WebFetch(domain:raw.githubusercontent.com),
  Bash(ls *),
  Bash(grep *),
  Bash(find * *),
  Bash(find . *),
  Bash(cat go.mod), Bash(cat go.sum),
  Bash(go build *), Bash(go vet *), Bash(go mod *), Bash(gofmt *)
---

# Stream Backend - server-side SDK migration

This skill is **small on purpose**. It does not bundle the SDK mappings - the official per-language migration guide is the source of truth, and this skill fetches it live and applies it to the user's project. That keeps the migration current with the SDK and avoids a second copy that drifts.

The server-side Stream SDKs are typed API clients generated from one OpenAPI spec - no UI, no state, no theming. That is why every language lives under this one skill (parameterized by language) rather than in a per-SDK pack the way the client SDKs do.

**Read first (every session):** the cross-cutting [`../stream/RULES.md`](../stream/RULES.md). Glob `../stream/SKILL.md`; if empty, install with `getstream skills stream`. This skill needs **no** CLI onboarding, auth, or provisioning - it only reads/edits local code and fetches the guide.

---

## Step 0: Classify (always first)

Resolve two things from the user's input and the project on disk:

1. **Is this a server-side migration?** If the request is about a **client / frontend** SDK (iOS/Swift, Android/Kotlin, React, React Native, Flutter), this is the wrong skill - route to the matching platform pack (`stream-swift`, `stream-android`, `stream-react`, `stream-react-native`, `stream-flutter`). Server-side signals: a `go.mod` / `composer.json` / `Gemfile` / `*.csproj` / `pom.xml` / `pyproject.toml` in the project, or a legacy server package like `stream-chat-go`.
2. **Which language?** Detect from the project files, or ask if it is not obvious.

### Language support

| Language | From (legacy SDK) | To (generated SDK) | Track |
|---|---|---|---|
| Go | `github.com/GetStream/stream-chat-go` | `github.com/GetStream/getstream-go` | [`migrate-go.md`](migrate-go.md) |
| Python | `stream-chat-python` | `stream-py` | not yet |
| Ruby | `stream-chat-ruby` | `getstream-ruby` | not yet |
| PHP | `stream-chat-php` | `getstream-php` | not yet |
| Java | `stream-chat-java` | `stream-sdk-java` | not yet |
| .NET / C# | `stream-chat-net` | `getstream-net` | not yet |

(Go shows the full module path because that is what the Go track detects; the other rows name the SDK repos. Exact package-manager coordinates land with each language's track.)

If the language is supported, Read its track file and follow it exactly. If the language is **not yet** supported, say so plainly, do not attempt a migration from memory, and point the user at the official migration guide for that SDK if one exists.

---

## Step 1: Run the migration track

For **Go**, Read [`migrate-go.md`](migrate-go.md) and follow it. It is docs-driven and read-only until the guide is fetched: detect the installed SDK, fetch the official guide, apply each documented transform, then verify with `go build` and `go vet`.

**Hard gate (applies to every language).** The guide is the source of truth. If it does not load, or an operation in the user's code is not covered by the guide, **stop** - report what you could not confirm and ask how to proceed. Never invent an API mapping; a guess that happens to compile is still a guess.

---

## Which products this covers

The legacy SDKs are **Chat** SDKs. `stream-chat-go` exposes Chat plus chat-era moderation (ban, mute, moderators, flags, blocklists) and has no Video, Feeds, or Call surface at all. So a migration from it covers Chat and chat moderation, because that is the entire surface there is to migrate.

Video and Feeds in the generated SDK are **new capability, not migration targets**: there is no legacy Go code calling them. If you want to start using Video or Feeds, that is adoption rather than migration, and the product docs are the right starting point. Feeds v2 to v3 is a different move again (the API and the SDKs both differ) and is not handled here.

Within Chat, the migration guide documents the common operations (setup and auth, users, channels, messages and reactions, ban/mute/moderators, devices). It does not yet document the whole legacy surface. Known gaps, which this skill reports rather than guesses at: file and image upload, unread counts, threads, drafts, polls, reminders, blocklists, flags and flag reports, commands, permissions and roles, import and export, and message translation.

## What this skill does not do (yet)

- **Client / frontend SDK migrations** - those belong in the platform packs listed in Step 0.
- **Build / integrate from scratch** - this skill migrates an existing integration; it does not scaffold new server code.
- **Data migration** - it migrates code, not stored data.

Additional languages are added the same way the Go track is: a `migrate-<lang>.md` procedure plus a row in the language table above.
