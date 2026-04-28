---
name: stream-android
description: "Build and integrate Stream Chat, Video, and Feeds in Android apps. Use for Jetpack Compose, classic Views (XML), Android Studio, and Gradle project work with Stream package setup, auth wiring, and screen blueprints."
license: See LICENSE in repository root
compatibility: Requires an Android Studio / Gradle project (Kotlin). Stream CLI is the default path for Step 0.5 (API key fetch, token mint, optional channel seeding); only optional when the user pastes the API key and token themselves.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(ls *),
  Bash(grep *),
  Bash(find . *),
  Bash(cat **/settings.gradle), Bash(cat **/settings.gradle.kts),
  Bash(cat **/build.gradle), Bash(cat **/build.gradle.kts),
  Bash(cat gradle/libs.versions.toml),
  Bash(stream token *),
  Bash(stream chat *),
  Bash(stream config *)
---

# Stream Android - skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session - every non-negotiable rule is stated there, nowhere else.

This file is the **single entrypoint**: intent classification, local project detection, and module pointers for Stream work in Android apps.

---

## Step 0: Intent classifier (mandatory first - never skip)

Before any tool call, decide the **track** from the user's input alone - no probes first.

### Signals -> track

| Signal in user input | Track |
|---|---|
| Explicit product/framework token: `Chat Compose`, `Chat XML`, `Chat UI Components`, `Video Android`, `Feeds Android`, etc. | **C - Reference lookup** |
| Words "docs" or "documentation" around Stream Android/Compose work | **C - Reference lookup** |
| "How do I {X} in Compose/XML/Android?", "What does {SDK type/Composable/View} do?" | **C - Reference lookup** |
| "Build me a new Android app", "create a Compose app", "new Android app" + Stream product | **A - New app** |
| "Add/integrate Stream into this app", "wire Chat/Video/Feeds into my Android project" | **B - Existing app** |
| "Install Stream packages", "set up Stream in Android Studio", "wire auth/token flow" with no broader feature request | **D - Bootstrap / setup** |
| Bare `/stream-android` with no args | List the tracks briefly and wait |

### Disambiguation flow

If the request is ambiguous between **build/integrate** and **reference lookup**, ask one short question and wait:

> Do you want me to wire this into the project, or just map the Android SDK pattern and files?

### After classification

- **Tracks A, B, D** -> run **Project signals** once per session, then continue in [`builder.md`](builder.md) and [`sdk.md`](sdk.md).
- **Track C** -> skip the probe if the product + UI layer are explicit. Only run it on demand if the SDK or UI layer is ambiguous.

---

## Step 0.5: Credentials, token, and seed data (tracks A, B, D only)

Run this once per session, right after intent classification, before the Project signals probe.

### Goal

Collect the Stream **API key**, a **user token**, and optionally seed a few channels — all before touching code — so the app has real data to show from the first run.

### Single upfront question (ask exactly once, then act immediately)

Post **one message** asking all three things together. Do not split into multiple rounds:

> To wire everything up with real data, I need a few quick answers:
>
> 1. **Credentials** — Should I fetch your API key from the dashboard and generate a token via the Stream CLI, or will you paste them yourself?
> 2. **Token expiry** — If I'm generating the token: should it expire? (e.g. `1h`, `1d`, `30m`) or never expire?
> 3. **Seed channels** — Should I pre-create a few channels with random usernames so the app has something to show immediately?
>
> If you want to handle everything yourself, just paste your API key and token and tell me whether to seed channels.

### After the user replies — act without further prompting

Once the user answers, execute all CLI steps in sequence **without pausing for confirmation between them**. Narrate each step briefly as you go (one line per action), but do not stop to ask "shall I continue?".

#### Step A — API key

```bash
stream config get-app
```

Extract the `api_key` field. Hold it in context.

#### Step B — Token

```bash
# Never-expiring
stream token <user_id>

# Expiring
stream token <user_id> --ttl <duration>
```

Hold the token in context. Use it (and the API key) in every code snippet — no placeholder strings.

#### Step C — Seed channels (only if the user said yes)

Create 3–5 channels with random realistic usernames. Use `messaging` as the default channel type.

```bash
# Create a channel and add members (repeat for each channel)
# IMPORTANT: include <token_user_id> in --members for every channel you want
# the connected user to see on first launch.
stream chat channel create --type messaging --id <channel-id> --members <token_user_id>,<user1>,<user2>
```

Generate short memorable channel IDs (e.g. `general`, `random`, `team-alpha`) and use a small set of random usernames (e.g. `alice`, `bob`, `carol`, `dave`, `eve`). The token user **must** appear in `--members` for at least one channel — without that, the channel list will render empty on first launch even though the seed succeeded.

After seeding, print a brief summary:

> Created channels: `general` (<token_user_id>, alice, bob), `random` (<token_user_id>, carol, dave), `team-alpha` (alice, eve)

#### Step D — Proceed automatically

After all CLI steps succeed, move straight to **Project signals** and then into `builder.md` — no additional prompt needed. If any CLI step fails, explain the error briefly and ask the user to paste the missing value manually before continuing.

### What NOT to do

- Never put the API **secret** in app code — the CLI uses it server-side only.
- Never invent or fabricate credentials.
- Never ask "should I continue?" between Step A, B, C, and D — execute the whole sequence once the user's upfront answers are in.

---

## Project signals (tracks A/B/D - once per session; Track C on demand only)

Read-only local probe. Use it to detect whether the user is in an Android Studio / Gradle project, a Kotlin module, or an empty directory.

```bash
bash -c 'echo "=== GRADLE ROOT ==="; find . -maxdepth 2 \( -name "settings.gradle.kts" -o -name "settings.gradle" -o -name "build.gradle.kts" -o -name "build.gradle" \) -print 2>/dev/null; echo "=== APP MODULES ==="; find . -maxdepth 3 -type f \( -name "build.gradle.kts" -o -name "build.gradle" \) -path "*/*/build.gradle*" -print 2>/dev/null; echo "=== VERSION CATALOG ==="; find . -maxdepth 3 -name "libs.versions.toml" -print 2>/dev/null; echo "=== MANIFESTS ==="; find . -maxdepth 4 -name "AndroidManifest.xml" -print 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Hold the result in conversation context. Don't re-run it unless the user changes directory or the project shape clearly changed.

Use the result to produce a **one-line status**, for example:

- `Compose app detected - app/build.gradle.kts - libs.versions.toml present - ready for Stream wiring`
- `Multi-module Gradle project detected - preserve existing module layout`
- `XML / View-based app detected - keep current UI layer unless the user asks to migrate`
- `No Gradle project found - user needs to create the app in Android Studio first`

---

## Module map

| Track | Module(s) |
|---|---|
| A - New app | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + relevant reference files |
| B - Existing app | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + relevant reference files |
| C - Reference lookup | [`sdk.md`](sdk.md) + relevant reference files |
| D - Bootstrap / setup | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) |

---

## Reference layout

Shared Android/Kotlin patterns live in **[`sdk.md`](sdk.md)**.

Product and UI-layer specifics live under **`references/`** using a flat naming scheme that can grow with the full Stream Android surface:

- **Reference:** `references/<PRODUCT>-<UI_LAYER>.md`
- **Blueprints:** `references/<PRODUCT>-<UI_LAYER>-blueprints.md`

Current extracted module:

- **Chat + Compose:** [`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md) + [`references/CHAT-COMPOSE-blueprints.md`](references/CHAT-COMPOSE-blueprints.md)

Future Android product coverage should stay in this naming family instead of creating more top-level skills:

- `CHAT-XML.md`
- `VIDEO-COMPOSE.md`
- `VIDEO-XML.md`
- `FEEDS-COMPOSE.md`
- `FEEDS-XML.md`

If the requested product/UI layer file is not bundled yet, say so plainly, use `sdk.md` for the shared Android patterns, and only switch to live docs if the user asks.

---

## Track A - New app

**Full detail:** [`builder.md`](builder.md) - use the **new-project path**.

| Phase | Name | What you do |
|---|---|---|
| **A1** | Detect | Run **Project signals**. If there is no Android app yet, tell the user to create one in Android Studio first. |
| **A2** | Choose lane | Confirm product(s) and UI layer: Compose, XML/Views, or mixed. |
| **A3** | Install + wire | Follow [`builder.md`](builder.md) + [`sdk.md`](sdk.md), then load only the needed product references. |
| **A4** | Verify | Confirm Gradle sync, `ChatClient` lifetime, auth, and first rendered screen. |

---

## Track B - Existing app

**Full detail:** [`builder.md`](builder.md) - use the **existing-project path**.

| Phase | Name | What you do |
|---|---|---|
| **B1** | Detect | Run **Project signals** and inspect the existing app structure before editing. |
| **B2** | Preserve | Keep the current UI layer, dependency strategy (version catalog vs inline), and navigation setup unless the user asks for a migration. |
| **B3** | Integrate | Use [`sdk.md`](sdk.md) for shared wiring, then load only the needed product reference files. |
| **B4** | Verify | Confirm the requested Stream flow builds and renders inside the existing app. |

---

## Track C - Reference lookup

Load only the relevant files for the requested product and UI layer.

- Shared lifecycle / auth / state patterns -> [`sdk.md`](sdk.md)
- Chat Compose setup and gotchas -> [`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md)
- Chat Compose screen structure -> [`references/CHAT-COMPOSE-blueprints.md`](references/CHAT-COMPOSE-blueprints.md)

If the user asks for an exact Video, Feeds, or XML module that is not bundled yet, say that clearly instead of inventing API details.

---

## Track D - Bootstrap / setup

Use when the user wants the install and wiring path more than a feature build:

- detect the project shape
- choose Compose vs XML ownership
- install Stream packages with the project's existing dependency strategy (version catalog or inline)
- wire auth and `ChatClient` lifetime via [`sdk.md`](sdk.md)
- stop before product-specific UI if the user only asked for setup
