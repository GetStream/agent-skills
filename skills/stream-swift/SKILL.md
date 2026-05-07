---
name: stream-swift
description: "Build and integrate Stream Chat, Video, and Feeds in Swift apps. Use for SwiftUI, UIKit, Xcode, and iOS project work with Stream package setup, auth wiring, and view blueprints."
license: See LICENSE in repository root
compatibility: Requires an Xcode or Swift/iOS project. No Stream CLI required.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(ls *),
  Bash(grep *),
  Bash(find . *),
  Bash(cat Package.swift), Bash(cat Package.resolved), Bash(cat Podfile),
  Bash(stream token *),
  Bash(stream chat *),
  Bash(stream config *)
---

# Stream Swift - skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session - every non-negotiable rule is stated there, nowhere else.

This file is the **single entrypoint**: intent classification, local project detection, and module pointers for Stream work in Swift apps.

---

## Step 0: Intent classifier (mandatory first - never skip)

Before any tool call, decide the **track** from the user's input alone - no probes first.

### Signals -> track

| Signal in user input | Track |
|---|---|
| Explicit product/framework token: `Chat SwiftUI`, `Chat UIKit`, `Video iOS`, `Feeds Swift`, `Livestream SwiftUI`, etc. | **C - Reference lookup** |
| Words "docs" or "documentation" around Stream Swift/iOS work | **C - Reference lookup** |
| "How do I {X} in SwiftUI/UIKit/Xcode?", "What does {SDK type/method/view} do?" | **C - Reference lookup** |
| "Build me a new iOS app", "create a SwiftUI app", "new UIKit app" + Stream product | **A - New app** |
| "Build a livestream app", "creator and viewer mode", "go live", "one-to-many broadcast" | **A - New app** (load `LIVESTREAM-SWIFTUI.md` + `LIVESTREAM-SWIFTUI-blueprints.md`) |
| "Add/integrate Stream into this app", "wire Chat/Video/Feeds into my Xcode project" | **B - Existing app** |
| "Install Stream packages", "set up Stream in Xcode", "wire auth/token flow" with no broader feature request | **D - Bootstrap / setup** |
| Bare `/stream-swift` with no args | List the tracks briefly and wait |

### Disambiguation flow

If the request is ambiguous between **build/integrate** and **reference lookup**, ask one short question and wait:

> Do you want me to wire this into the project, or just map the Swift SDK pattern and files?

### After classification

- **Tracks A, B, D** -> run **Project signals** once per session, then continue in [`builder.md`](builder.md) and [`sdk.md`](sdk.md).
- **Track C** -> skip the probe if the product + framework are explicit. Only run it on demand if the SDK or UI layer is ambiguous.

---

## Step 0.5: Credentials, token, and seed data (tracks A, B, D only)

Run this once per session, right after intent classification, before the Project signals probe.

### Goal

Collect the Stream **API key**, a **user token**, and optionally seed a few channels - all before touching code - so the app has real data to show from the first run.

### Single upfront question (ask exactly once, then act immediately)

Post **one message** asking all relevant things together. Do not split into multiple rounds.

**For Chat projects:**

> To wire everything up with real data, I need a few quick answers:
>
> 1. **Credentials** - Should I fetch your API key from the dashboard and generate a token via the Stream CLI, or will you paste them yourself?
> 2. **Token expiry** - If I'm generating the token: should it expire? (e.g. `1h`, `1d`, `30m`) or never expire?
> 3. **Seed channels** - Should I pre-create a few channels with random usernames so the app has something to show immediately?
>
> If you want to handle everything yourself, just paste your API key and token and tell me whether to seed channels.

**For Feeds projects** (no channel seeding - feed groups are configured in the dashboard):

> To wire everything up with real data, I need a couple of quick answers:
>
> 1. **Credentials** - Should I fetch your API key from the dashboard and generate a token via the Stream CLI, or will you paste them yourself?
> 2. **Token expiry** - If I'm generating the token: should it expire? (e.g. `1h`, `1d`, `30m`) or never expire?
> 3. **Feed groups** - What feed groups do you need? (defaults: `user`, `timeline`, `notification` - tell me if you want different names)
>
> If you want to handle everything yourself, just paste your API key and token and confirm the feed group names.

**For Video projects** (calls are ephemeral - no seeding needed):

> To wire everything up, I need a couple of quick answers:
>
> 1. **Credentials** - Should I fetch your API key from the dashboard and generate a token via the Stream CLI, or will you paste them yourself?
> 2. **Token expiry** - If I'm generating the token: should it expire? (e.g. `1h`, `1d`, `30m`) or never expire?
>
> If you want to handle everything yourself, just paste your API key and token.

### After the user replies - act without further prompting

Once the user answers, execute all CLI steps in sequence **without pausing for confirmation between them**. Narrate each step briefly as you go (one line per action), but do not stop to ask "shall I continue?".

#### Step A - API key

```bash
stream config get-app
```

Extract the `api_key` field. Hold it in context.

#### Step B - Token

```bash
# Never-expiring
stream token <user_id>

# Expiring
stream token <user_id> --ttl <duration>
```

Hold the token in context. Use it (and the API key) in every code snippet - no placeholder strings.

#### Step C - Seed channels (Chat projects only; only if the user said yes)

Create 3-5 channels with random realistic usernames. Use `messaging` as the default channel type.

```bash
# Create a channel and add members (repeat for each channel)
stream chat channel create --type messaging --id <channel-id> --members <user1>,<user2>
```

Generate short memorable channel IDs (e.g. `general`, `random`, `team-alpha`) and use a small set of random usernames (e.g. `alice`, `bob`, `carol`, `dave`, `eve`). Make sure the token user is a member of at least one channel so they can see it on first launch.

After seeding, print a brief summary:

> Created channels: `general` (alice, bob), `random` (carol, dave), `team-alpha` (alice, eve)

#### Step D - Proceed automatically

After all CLI steps succeed, move straight to **Project signals** and then into `builder.md` - no additional prompt needed. If any CLI step fails, explain the error briefly and ask the user to paste the missing value manually before continuing.

### What NOT to do

- Never put the API **secret** in app code - the CLI uses it server-side only.
- Never invent or fabricate credentials.
- Never ask "should I continue?" between Step A, B, C, and D - execute the whole sequence once the user's upfront answers are in.

---

## Project signals (tracks A/B/D - once per session; Track C on demand only)

Read-only local probe. Use it to detect whether the user is in an Xcode project, a Swift package, or an empty directory.

```bash
bash -c 'echo "=== XCODE ==="; find . -maxdepth 3 \( -name "*.xcodeproj" -o -name "*.xcworkspace" \) -print 2>/dev/null; echo "=== MANIFESTS ==="; find . -maxdepth 3 \( -name "Package.swift" -o -name "Package.resolved" -o -name "Podfile" \) -print 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Hold the result in conversation context. Don't re-run it unless the user changes directory or the project shape clearly changed.

Use the result to produce a **one-line status**, for example:

- `SwiftUI app detected - MyApp.xcodeproj - ready for Stream wiring`
- `UIKit workspace detected - Podfile present - preserve existing package manager`
- `No Xcode project found - user needs to create the app in Xcode first`

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

Shared Swift/iOS patterns live in **[`sdk.md`](sdk.md)**.

Product and framework specifics live under **`references/`** using a flat naming scheme that can grow with the full Stream Swift surface:

- **Reference:** `references/<PRODUCT>-<FRAMEWORK>.md`
- **Blueprints:** `references/<PRODUCT>-<FRAMEWORK>-blueprints.md`

Current extracted modules:

- **Chat + SwiftUI:** [`references/CHAT-SWIFTUI.md`](references/CHAT-SWIFTUI.md) + [`references/CHAT-SWIFTUI-blueprints.md`](references/CHAT-SWIFTUI-blueprints.md)
- **Chat + UIKit:** [`references/CHAT-UIKIT.md`](references/CHAT-UIKIT.md) + [`references/CHAT-UIKIT-blueprints.md`](references/CHAT-UIKIT-blueprints.md)
- **Video + SwiftUI:** [`references/VIDEO-SWIFTUI.md`](references/VIDEO-SWIFTUI.md) + [`references/VIDEO-SWIFTUI-blueprints.md`](references/VIDEO-SWIFTUI-blueprints.md)
- **Video + UIKit:** [`references/VIDEO-UIKIT.md`](references/VIDEO-UIKIT.md) + [`references/VIDEO-UIKIT-blueprints.md`](references/VIDEO-UIKIT-blueprints.md)
- **Livestream + SwiftUI:** [`references/LIVESTREAM-SWIFTUI.md`](references/LIVESTREAM-SWIFTUI.md) + [`references/LIVESTREAM-SWIFTUI-blueprints.md`](references/LIVESTREAM-SWIFTUI-blueprints.md)
- **Combined Chat + Video (SwiftUI or UIKit):** [`references/COMBINED-CHAT-VIDEO.md`](references/COMBINED-CHAT-VIDEO.md)
- **Feeds (SwiftUI or UIKit):** [`references/FEEDS-SWIFTUI.md`](references/FEEDS-SWIFTUI.md) + [`references/FEEDS-SWIFTUI-blueprints.md`](references/FEEDS-SWIFTUI-blueprints.md)

> **Feeds has no pre-built UI components.** `FEEDS-SWIFTUI.md` covers SDK patterns for both SwiftUI and UIKit - only the view layer differs. Load both files for any Feeds request.

Future Swift product coverage should stay in this naming family instead of creating more top-level skills.

---

## Track A - New app

**Full detail:** [`builder.md`](builder.md) - use the **new-project path**.

| Phase | Name | What you do |
|---|---|---|
| **A1** | Detect | Run **Project signals**. If there is no iOS app yet, tell the user to create one in Xcode first. |
| **A2** | Choose lane | Confirm product(s) and UI layer: SwiftUI, UIKit, or mixed. |
| **A3** | Install + wire | Follow [`builder.md`](builder.md) + [`sdk.md`](sdk.md), then load only the needed product references. |
| **A4** | Verify | Confirm package resolution, client lifetime, auth, and first rendered screen. |

---

## Track B - Existing app

**Full detail:** [`builder.md`](builder.md) - use the **existing-project path**.

| Phase | Name | What you do |
|---|---|---|
| **B1** | Detect | Run **Project signals** and inspect the existing app structure before editing. |
| **B2** | Preserve | Keep the current UI layer, package manager, and navigation architecture unless the user asks for a migration. |
| **B3** | Integrate | Use [`sdk.md`](sdk.md) for shared wiring, then load only the needed product reference files. |
| **B4** | Verify | Confirm the requested Stream flow builds and renders inside the existing app. |

---

## Track C - Reference lookup

Load only the relevant files for the requested product and UI layer.

- Shared lifecycle / auth / state patterns -> [`sdk.md`](sdk.md)
- Chat SwiftUI setup and gotchas -> [`references/CHAT-SWIFTUI.md`](references/CHAT-SWIFTUI.md)
- Chat SwiftUI view structure -> [`references/CHAT-SWIFTUI-blueprints.md`](references/CHAT-SWIFTUI-blueprints.md)
- Chat UIKit setup and gotchas -> [`references/CHAT-UIKIT.md`](references/CHAT-UIKIT.md)
- Chat UIKit view controller structure -> [`references/CHAT-UIKIT-blueprints.md`](references/CHAT-UIKIT-blueprints.md)
- Video SwiftUI setup and gotchas -> [`references/VIDEO-SWIFTUI.md`](references/VIDEO-SWIFTUI.md)
- Video SwiftUI view structure -> [`references/VIDEO-SWIFTUI-blueprints.md`](references/VIDEO-SWIFTUI-blueprints.md)
- Video UIKit setup and gotchas -> [`references/VIDEO-UIKIT.md`](references/VIDEO-UIKIT.md)
- Video UIKit view controller structure -> [`references/VIDEO-UIKIT-blueprints.md`](references/VIDEO-UIKIT-blueprints.md)
- Livestream SwiftUI (call type, backstage, goLive/stopLive, host/viewer flows, HLS) -> [`references/LIVESTREAM-SWIFTUI.md`](references/LIVESTREAM-SWIFTUI.md)
- Livestream SwiftUI view structure (mode selection, creator, WebRTC viewer, HLS viewer) -> [`references/LIVESTREAM-SWIFTUI-blueprints.md`](references/LIVESTREAM-SWIFTUI-blueprints.md)
- Combined Chat + Video (collision table, file isolation, UIKit + SwiftUI blueprints) -> [`references/COMBINED-CHAT-VIDEO.md`](references/COMBINED-CHAT-VIDEO.md)
- Feeds SDK patterns (setup, FeedState, activities, reactions, comments, follow, notifications) -> [`references/FEEDS-SWIFTUI.md`](references/FEEDS-SWIFTUI.md)
- Feeds SwiftUI view blueprints (timeline, row, composer, comments, profile, notifications) -> [`references/FEEDS-SWIFTUI-blueprints.md`](references/FEEDS-SWIFTUI-blueprints.md)

---

## Track D - Bootstrap / setup

Use when the user wants the install and wiring path more than a feature build:

- detect the project shape
- choose SwiftUI vs UIKit ownership
- install Stream packages with the project's existing package strategy
- wire auth and client lifetime via [`sdk.md`](sdk.md)
- stop before product-specific UI if the user only asked for setup
