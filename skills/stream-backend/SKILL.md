---
name: stream-backend
description: "Migrate a server-side (backend) Stream integration from a legacy hand-written SDK to the generated OpenAPI SDK. Covers Go, Python, Ruby, PHP, Java and .NET: it detects or asks the language, then runs the same migration workflow for all of them. Triggers on 'migrate stream-chat-go to getstream-go', 'move off stream-chat-python', 'switch to the new Stream server SDK', 'upgrade my Stream backend SDK', and legacy server SDK tokens (stream-chat-go, stream-chat-python, stream-chat-ruby, stream-chat-php, stream-chat-java, stream-chat-net). NOT for client / frontend SDKs (iOS, Android, React, React Native, Flutter) - those have their own packs (stream-swift, stream-android, stream-react, stream-react-native, stream-flutter)."
license: See LICENSE in repository root
compatibility: Requires the customer's server-side project checkout and the toolchain of its language, which is used to verify the migration compiles and passes tests. Fetches reference material live, so network access to github.com and raw.githubusercontent.com is needed. No Stream account or CLI onboarding is required - this is a local-only code migration.
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
  Bash(cat *),
  Bash(go *), Bash(gofmt *),
  Bash(python *), Bash(python3 *), Bash(pip *), Bash(uv *), Bash(mypy *), Bash(pytest *),
  Bash(ruby *), Bash(bundle *), Bash(rspec *),
  Bash(php *), Bash(composer *),
  Bash(mvn *), Bash(gradle *), Bash(./gradlew *),
  Bash(dotnet *)
---

# Stream Backend - server-side SDK migration

Moves a backend integration from a legacy hand-written Stream SDK to the generated OpenAPI SDK.

This is an **assisted migration, not an automatic one**. The work is reading the customer's codebase, mapping each call onto the new API, and being explicit about what changed underneath. Some of it is mechanical, some needs a judgment about intent, and some has no equivalent at all. The workflow separates those three so the customer knows which is which, and **a human reviews the result before it ships**. Say that up front rather than implying a push-button migration.

**Read first (every session):** the cross-cutting [`../stream/RULES.md`](../stream/RULES.md). Glob `../stream/SKILL.md`; if empty, install with `getstream skills stream`. This skill needs no CLI onboarding, auth, or provisioning.

---

## Step 0: Classify

Resolve two things from the user's input and the project on disk.

**1. Is this server-side?** If the request is about a client SDK (iOS/Swift, Android/Kotlin, React, React Native, Flutter), this is the wrong skill; route to the matching platform pack. Server-side signals: a `go.mod`, `pyproject.toml` / `requirements.txt`, `Gemfile`, `composer.json`, `pom.xml` / `build.gradle`, or `*.csproj`, or a legacy server package in the dependency list.

**2. Which language?** Detect from the project files, or ask.

| Language | From (legacy) | To (generated) | Symbol reference |
|---|---|---|---|
| Go | `stream-chat-go` | `getstream-go` | [`references/go.md`](references/go.md) |
| Python | `stream-chat` | `getstream` | [`references/python.md`](references/python.md) |
| Ruby | `stream-chat-ruby` | `getstream` | not yet written |
| PHP | `get-stream/stream-chat` | `getstream/getstream` | not yet written |
| Java | `stream-chat-java` | `stream-sdk-java` | not yet written |
| .NET | `stream-chat-net` | `getstream-net` | not yet written |

Every language runs the **same workflow**: [`migrate.md`](migrate.md). What differs per language is the symbol mapping, which lives in a reference file, and the commands used to verify. Where a language has no symbol reference yet, the workflow still applies: derive each mapping from the SDK source and the live docs, and hold to the same rule that nothing is migrated unless it can be verified.

## Step 1: Run the workflow

Read [`migrate.md`](migrate.md) and follow it. It covers, in order: take an inventory of every legacy call site, classify each one, agree a plan with the user, apply in reviewable slices, verify, and report.

The operations themselves, including which ones change runtime behavior, are in [`references/operations.md`](references/operations.md). That file is language-independent; read it alongside the language's symbol reference.

**The rule that matters:** never migrate a call you cannot verify against the SDK source or the official documentation. A rewrite that happens to compile is still a guess. When you cannot confirm a mapping, leave the call alone and report it.

---

## Which products this covers

The legacy SDKs are **Chat** SDKs, so a migration from one covers Chat plus chat-era moderation, because that is the entire surface there is to migrate.

Video and Feeds in the generated SDK are **new capability, not migration targets**: there is no legacy code calling them. Adopting them is a separate piece of work, and the product documentation is the place to start. Feeds v2 to v3 is different again, since the API and the SDKs both changed, and is not handled here.

## What this skill does not do

- **Client / frontend SDK migrations.** Those belong in the platform packs listed in Step 0.
- **Build or integrate from scratch.** This migrates an existing integration; it does not scaffold new server code.
- **Data migration.** It migrates code, not stored data.
