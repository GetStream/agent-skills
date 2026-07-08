---
name: stream-android
description: "Build and integrate Stream Chat, Video, and Feeds in Android apps. Use for Jetpack Compose, Android Studio, and Gradle project work — including Stream package setup, auth and token wiring, screen blueprints, and any follow-up Stream UI work such as adding screens, navigating between channel list and channel/message screens, channel tap handling, deep links, push routing, theming, custom channel/message UI, video calling flows (joining/starting calls, ringing, custom call controls and participant tiles), and Feeds surfaces (timeline, activity composer, threaded comments, follow graph / profile, notification feed, stories)."
license: See LICENSE in repository root
compatibility: Requires an Android Studio / Gradle project (Kotlin). The `getstream` CLI (binary name `getstream`) is the default path for the credentials flow (API key fetch, token mint, and any product-specific setup - see `credentials.md`); only optional when the user pastes the API key and token themselves.
metadata:
  author: GetStream
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash(ls *)
  - Bash(grep *)
  - Bash(find . *)
  - Bash(cat **/settings.gradle)
  - Bash(cat **/settings.gradle.kts)
  - Bash(cat **/build.gradle)
  - Bash(cat **/build.gradle.kts)
  - Bash(cat gradle/libs.versions.toml)
  - Bash(command -v getstream)
  - Bash(getstream *)
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
| Explicit product/framework token: `Chat Compose`, `Chat XML`, `Video Android`, `Video Compose`, `Feeds Android`, `Feeds Compose`, etc. | **C - Reference lookup** |
| Words "docs" or "documentation" around Stream Android/Compose work | **C - Reference lookup** |
| "How do I {X} in Compose/XML/Android?", "What does {SDK type/Composable/View/Fragment} do?" | **C - Reference lookup** |
| "Build me a new Android app", "create a Compose app", "new Android app" + Stream product | **A - New app** |
| "Add/integrate Stream into this app", "wire Chat/Video/Feeds into my Android project" | **B - Existing app** |
| "Install Stream packages", "set up Stream in Android Studio", "wire auth/token flow" with no broader feature request | **D - Bootstrap / setup** |
| Request carries a **target appearance** - a screenshot, a Figma frame, or "make the chat look like WhatsApp / Telegram / Slack / \<app\>" | **B (or A)** + the **styling-depth flag** below -> [`design-matching.md`](design-matching.md) |
| Bare `/stream-android` with no args | List the tracks briefly and wait |

### Disambiguation flow

If the request is ambiguous between **build/integrate** and **reference lookup**, ask one short question and wait:

> Do you want me to wire this into the project, or just map the Android SDK pattern and files?

### After classification

- **Tracks A, B, D** -> run **Step 0.5 (credentials)** first, **then Project signals** once per session, then continue in [`builder.md`](builder.md) and [`sdk.md`](sdk.md). Do not probe the project before credentials.
- **Track C** -> skip both steps if the product + UI layer are explicit. Only run Project signals on demand if the SDK or UI layer is ambiguous.

### Styling-depth flag (orthogonal to the track)

If the request carries a **target appearance** - an attached screenshot, a Figma frame, or "make the chat look like WhatsApp / Telegram / Slack / \<app\>" - run [`design-matching.md`](design-matching.md) **before** writing UI code. It sits on top of the Track A/B work (it is *how* you build the requested UI), not instead of it. A reference is a **checklist of regions** (header, composer, where the timestamp + read receipts sit, bubble shape/tail, channel-list rows, date separators, attachments...), and most differ from Stream's Compose defaults **structurally**, not just by color - setting the accent + wallpaper and stopping is the known failure. Classify each screenshot to its screen (channel list vs message vs thread - Step 0), decompose every region capturing **dimensions** not just colors, then route each difference to one of the **two axes**: a theming token (`StreamDesign.Colors`/`Typography`) or a `ChatComponentFactory` slot (structure - padding / corner-radius / bubble-shape / composer layout live here; Android has **no `Styles` axis**, so those are structure, not theming). Recurring traps the doc guards against: overriding a **composite slot** (`MessageContainer`, the header, `MessageComposer`) silently drops the sub-features the default drew (incoming avatar, grouping, reactions, replies, status, send/voice) unless you reproduce them; the **message-header trailing slot defaults to a channel avatar** (override it for action icons); the **composer** differs by row count / field shape / alignment far more than by icon set; **DMs must not be prefixed with `#`** in the list or titled "Channel" in the header. The match is **not done** until you build, seed data that triggers every region, compare region-by-region on the real navigation path, and iterate - implement **every** region, the composer included; a region left at the SDK default is a FAIL, not a footnote.

---

## Step 0.5: Credentials, token, and seed data (tracks A, B, D only)

**Order:** intent classification -> **Step 0.5 (this step)** -> Project signals probe -> track work. Do this **before** running the Project signals shell command, even if a track table below lists "Detect" as phase 1. Run **once per session** for tracks A, B, and D. Skip for Track C.

Follow [`credentials.md`](credentials.md) to:

- collect the Stream API key from the dashboard (or from the user)
- generate a user token via the Stream CLI (or accept one from the user)
- run any product-specific setup (Chat: optionally seed channels; Feeds: confirm feed groups; Video: nothing — calls are ephemeral)

Wire the API key from `getstream env`'s output (e.g. `BuildConfig.STREAM_API_KEY`) and use the real user token in code snippets - never placeholder strings. If a track A/B/D task reaches code work and credentials haven't been collected yet, return to `credentials.md` before continuing.

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

Shared Android/Kotlin patterns live in **[`sdk.md`](sdk.md)**. The curated procedure for reproducing a
**reference design** with the pre-built Compose components (the region -> `ChatComponentFactory`-slot map
and the build/verify loop) lives in **[`design-matching.md`](design-matching.md)** - loaded via the
styling-depth flag above, on top of whichever track applies.

Product and UI-layer specifics live under **`references/`** using a flat naming scheme that can grow with the full Stream Android surface:

- **Reference:** `references/<PRODUCT>-<UI_LAYER>.md`
- **Blueprints:** `references/<PRODUCT>-<UI_LAYER>-blueprints.md`

Current extracted modules:

- **Chat + Compose:** [`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md) + [`references/CHAT-COMPOSE-blueprints.md`](references/CHAT-COMPOSE-blueprints.md)
- **Chat + XML:** [`references/CHAT-XML.md`](references/CHAT-XML.md) + [`references/CHAT-XML-blueprints.md`](references/CHAT-XML-blueprints.md)
- **Video + Compose:** [`references/VIDEO-COMPOSE.md`](references/VIDEO-COMPOSE.md) + [`references/VIDEO-COMPOSE-blueprints.md`](references/VIDEO-COMPOSE-blueprints.md)
- **Feeds + Compose:** [`references/FEEDS-COMPOSE.md`](references/FEEDS-COMPOSE.md) + [`references/FEEDS-COMPOSE-blueprints.md`](references/FEEDS-COMPOSE-blueprints.md)

> **Feeds has no pre-built UI components.** `FEEDS-COMPOSE.md` covers the headless data SDK (FeedsClient, FeedState, ActivityState); `FEEDS-COMPOSE-blueprints.md` is custom Composable scaffolding driven by those state flows. Load both for any Feeds request.

Future Android product coverage should stay in this naming family instead of creating more top-level skills.

If the requested product/UI layer file is not bundled yet, say so plainly, use `sdk.md` for the shared Android patterns, and only switch to live docs if the user asks.

---

## Track A - New app

**Full detail:** [`builder.md`](builder.md) - use the **new-project path**.

| Phase | Name | What you do |
|---|---|---|
| **A1** | Detect | After **Step 0.5 (credentials)**, run **Project signals**. If there is no Android app yet, tell the user to create one in Android Studio first. |
| **A2** | Choose lane | Confirm product(s) and UI layer: Compose, XML/Views, or mixed. |
| **A3** | Install + wire | Follow [`builder.md`](builder.md) + [`sdk.md`](sdk.md), then load only the needed product references. |
| **A4** | Verify | Confirm Gradle sync, `ChatClient` lifetime, auth, and first rendered screen. |

---

## Track B - Existing app

**Full detail:** [`builder.md`](builder.md) - use the **existing-project path**.

| Phase | Name | What you do |
|---|---|---|
| **B1** | Detect | After **Step 0.5 (credentials)**, run **Project signals** and inspect the existing app structure before editing. |
| **B2** | Preserve | Keep the current UI layer, dependency strategy (version catalog vs inline), and navigation setup unless the user asks for a migration. |
| **B3** | Integrate | Use [`sdk.md`](sdk.md) for shared wiring, then load only the needed product reference files. |
| **B4** | Verify | Confirm the requested Stream flow builds and renders inside the existing app. |

---

## Track C - Reference lookup

Load only the relevant files for the requested product and UI layer.

- Shared lifecycle / auth / state patterns -> [`sdk.md`](sdk.md)
- Chat Compose setup and gotchas -> [`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md)
- Chat Compose screen structure -> [`references/CHAT-COMPOSE-blueprints.md`](references/CHAT-COMPOSE-blueprints.md)
- Chat XML setup and gotchas -> [`references/CHAT-XML.md`](references/CHAT-XML.md)
- Chat XML screen structure -> [`references/CHAT-XML-blueprints.md`](references/CHAT-XML-blueprints.md)
- Video Compose setup and gotchas -> [`references/VIDEO-COMPOSE.md`](references/VIDEO-COMPOSE.md)
- Video Compose call/screen structure -> [`references/VIDEO-COMPOSE-blueprints.md`](references/VIDEO-COMPOSE-blueprints.md)
- Feeds Compose SDK patterns -> [`references/FEEDS-COMPOSE.md`](references/FEEDS-COMPOSE.md)
- Feeds Compose blueprints -> [`references/FEEDS-COMPOSE-blueprints.md`](references/FEEDS-COMPOSE-blueprints.md)

If the user asks for a product/UI-layer combo that is not bundled (e.g. Video XML, Feeds XML), say that clearly instead of inventing API details.

---

## Track D - Bootstrap / setup

Use when the user wants the install and wiring path more than a feature build:

- run **Step 0.5 (credentials)** first
- detect the project shape
- choose Compose vs XML ownership
- install Stream packages with the project's existing dependency strategy (version catalog or inline)
- wire auth and `ChatClient` lifetime via [`sdk.md`](sdk.md)
- stop before product-specific UI if the user only asked for setup
