---
name: stream-flutter
description: "Build and integrate Stream Chat and Video in Flutter apps. Use for Flutter/Dart project work with Stream package setup, auth wiring, and widget blueprints. Supports stream_chat_flutter (pre-built Chat UI), stream_chat_flutter_core (custom Chat UI), and stream_video_flutter (Video calling and livestreaming)."
license: See LICENSE in repository root
compatibility: Requires a Flutter project (pubspec.yaml). No Stream CLI required.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(ls *),
  Bash(grep *),
  Bash(find . *),
  Bash(cat pubspec.yaml), Bash(cat pubspec.lock),
  Bash(flutter pub *),
  Bash(stream token *),
  Bash(stream keys *),
  Bash(stream api *),
  Bash(stream auth *),
  Bash(stream config *)
---

# Stream Flutter - skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session - every non-negotiable rule is stated there, nowhere else.

This file is the **single entrypoint**: intent classification, local project detection, and module pointers for Stream work in Flutter apps.

---

## Step 0: Intent classifier (mandatory first - never skip)

Before any tool call, decide the **track** from the user's input alone - no probes first.

### Signals -> track

| Signal in user input | Track |
|---|---|
| Explicit package/widget token: `stream_chat_flutter`, `StreamChannelListView`, `StreamMessageListView`, `StreamChatClient`, etc. | **C - Reference lookup** |
| Explicit video token: `stream_video_flutter`, `StreamCallContainer`, `StreamVideo`, `StreamVideoRenderer`, `goLive`, `stopLive`, `livestream` call type | **C - Reference lookup** |
| Words "docs" or "documentation" around Stream Flutter work | **C - Reference lookup** |
| "How do I {X} in Flutter?", "What does {widget/method} do?" | **C - Reference lookup** |
| "Build me a new Flutter app", "create a Flutter chat app" + Stream | **A - New app** |
| "Build a Flutter video call app", "create a livestream app in Flutter" | **A - New app** (load `VIDEO-FLUTTER.md` + `VIDEO-FLUTTER-blueprints.md` or `LIVESTREAM-FLUTTER.md` + `LIVESTREAM-FLUTTER-blueprints.md`) |
| "Add/integrate Stream into this app", "wire Chat into my Flutter project" | **B - Existing app** |
| "Add video calling to my Flutter app", "integrate Stream Video into my existing app" | **B - Existing app** (load `VIDEO-FLUTTER.md` + `VIDEO-FLUTTER-blueprints.md`) |
| "Install Stream packages", "set up Stream in Flutter", "wire auth/token" with no broader feature request | **D - Bootstrap / setup** |
| Bare `/stream-flutter` with no args | List the tracks briefly and wait |

### Disambiguation flow

If the request is ambiguous between **build/integrate** and **reference lookup**, ask one short question and wait:

> Do you want me to wire this into the project, or just map the Flutter SDK pattern and widgets?

### After classification

- **Tracks A, B, D** -> run **Project signals** once per session, then continue in [`builder.md`](builder.md) and [`sdk.md`](sdk.md).
- **Track C** -> skip the probe if the product + package are explicit. Only run it on demand if the SDK layer is ambiguous.

---

## Step 0.5: Credentials, token, and seed data (tracks A, B, D only)

Run this once per session, right after intent classification, before the Project signals probe.

### Goal

Collect the Stream **API key**, a **user token**, and optionally seed channels or calls - all before touching code - so the app has real data to show from the first run.

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
stream keys
```

This prints the API key and copies the secret to clipboard. Extract the `API Key:` field from the output. Hold it in context. If the command returns a 401 error, the CLI session has expired — run `stream auth logout && stream auth login` to re-authenticate, then retry.

#### Step B - Token

```bash
# Never-expiring
stream token <user_id>

# Expiring
stream token <user_id> --ttl <duration>
```

Hold the token in context. Use it (and the API key) in every code snippet - no placeholder strings.

#### Step C - Seed channels (only if the user said yes)

Create 3-5 channels with random realistic usernames. Use `messaging` as the default channel type.

**Sub-step C1 — upsert all users** (seed users + the token user):

```bash
stream api UpdateUsers --body '{
  "users": {
    "<token_user_id>": {"id": "<token_user_id>", "name": "<Display Name>"},
    "alice": {"id": "alice", "name": "Alice"},
    "bob":   {"id": "bob",   "name": "Bob"},
    "carol": {"id": "carol", "name": "Carol"},
    "dave":  {"id": "dave",  "name": "Dave"}
  }
}'
```

**Sub-step C2 — create each channel** (no members in the body; members are added in C3):

```bash
stream api GetOrCreateChannel type=messaging id=<channel-id> \
  --body '{"data": {"name": "<Channel Name>"}}'
```

Repeat for each channel (e.g. `general`, `random`, `team-alpha`).

**Sub-step C3 — add members to each channel** using `add_members`. The token user **must** be in every channel so the `Filter.in_('members', [userId])` query in the app returns results.

```bash
stream api UpdateChannel type=messaging id=<channel-id> \
  --body '{
    "add_members": [
      {"user_id": "<token_user_id>"},
      {"user_id": "alice"},
      {"user_id": "bob"}
    ],
    "user_id": "<token_user_id>"
  }'
```

Generate short memorable channel IDs (e.g. `general`, `random`, `team-alpha`) and use a small set of random usernames (e.g. `alice`, `bob`, `carol`, `dave`). The token user must be added to every channel — the channel list filter is `Filter.in_('members', [tokenUserId])` and will return nothing if the user is absent.

After seeding, print a brief summary:

> Created channels: `general` (token_user, alice, bob), `random` (token_user, carol, dave), `team-alpha` (token_user, alice, carol)

#### Step D - Proceed automatically

After all CLI steps succeed, move straight to **Project signals** and then into `builder.md` - no additional prompt needed. If any CLI step fails, explain the error briefly and ask the user to paste the missing value manually before continuing.

### What NOT to do

- Never put the API **secret** in app code - the CLI uses it server-side only.
- Never invent or fabricate credentials.
- Never ask "should I continue?" between Step A, B, C, and D - execute the whole sequence once the user's upfront answers are in.

---

## Project signals (tracks A/B/D - once per session; Track C on demand only)

Read-only local probe. Use it to detect whether the user is in a Flutter project or an empty directory.

```bash
bash -c 'echo "=== FLUTTER ==="; find . -maxdepth 2 -name "pubspec.yaml" -print 2>/dev/null; echo "=== STREAM ==="; grep -rE "stream_chat|stream_video" . --include="pubspec.yaml" -l 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Hold the result in conversation context. Don't re-run it unless the user changes directory or the project shape clearly changed.

Use the result to produce a **one-line status**, for example:

- `Flutter app detected - stream_chat_flutter already in pubspec.yaml`
- `Flutter app detected - stream_video_flutter already in pubspec.yaml`
- `Flutter app detected - no Stream dependency yet, ready to install`
- `No Flutter project found - user needs to run flutter create first`

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

Shared Flutter/Dart patterns live in **[`sdk.md`](sdk.md)**.

Product and package specifics live under **`references/`** using a flat naming scheme:

- **Reference:** `references/<PRODUCT>-<PACKAGE>.md`
- **Blueprints:** `references/<PRODUCT>-<PACKAGE>-blueprints.md`

Current extracted modules:

- **Chat + pre-built UI (`stream_chat_flutter`):** [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md) + [`references/CHAT-FLUTTER-blueprints.md`](references/CHAT-FLUTTER-blueprints.md)
- **Chat + custom UI (`stream_chat_flutter_core`):** [`references/CHAT-CORE.md`](references/CHAT-CORE.md) + [`references/CHAT-CORE-blueprints.md`](references/CHAT-CORE-blueprints.md)
- **Video (`stream_video_flutter`):** [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md) + [`references/VIDEO-FLUTTER-blueprints.md`](references/VIDEO-FLUTTER-blueprints.md)
- **Livestream (`stream_video_flutter`):** [`references/LIVESTREAM-FLUTTER.md`](references/LIVESTREAM-FLUTTER.md) + [`references/LIVESTREAM-FLUTTER-blueprints.md`](references/LIVESTREAM-FLUTTER-blueprints.md)

Future Stream product coverage (Feeds) should stay in this naming family instead of creating more top-level skills.

---

## Track A - New app

**Full detail:** [`builder.md`](builder.md) - use the **new-project path**.

| Phase | Name | What you do |
|---|---|---|
| **A1** | Detect | Run **Project signals**. If there is no Flutter app yet, tell the user to run `flutter create my_app` first. |
| **A2** | Choose lane | Confirm package choice: `stream_chat_flutter` (pre-built UI, fastest) or `stream_chat_flutter_core` (custom UI). |
| **A3** | Install + wire | Follow [`builder.md`](builder.md) + [`sdk.md`](sdk.md), then load only the needed reference files. |
| **A4** | Verify | Confirm `flutter pub get` succeeds, client connects, and first screen renders. |

---

## Track B - Existing app

**Full detail:** [`builder.md`](builder.md) - use the **existing-project path**.

| Phase | Name | What you do |
|---|---|---|
| **B1** | Detect | Run **Project signals** and inspect the existing app structure before editing. |
| **B2** | Preserve | Keep the current navigation, state management, and widget architecture unless the user asks for a change. |
| **B3** | Integrate | Use [`sdk.md`](sdk.md) for shared wiring, then load only the needed reference files. |
| **B4** | Verify | Confirm the requested Stream flow builds and renders inside the existing app. |

---

## Track C - Reference lookup

Load only the relevant files for the requested package.

- Shared lifecycle / auth / state patterns -> [`sdk.md`](sdk.md)
- Chat pre-built UI setup, widgets, theming -> [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md)
- Chat pre-built UI widget blueprints -> [`references/CHAT-FLUTTER-blueprints.md`](references/CHAT-FLUTTER-blueprints.md)
- Chat custom UI setup and controllers -> [`references/CHAT-CORE.md`](references/CHAT-CORE.md)
- Chat custom UI widget blueprints -> [`references/CHAT-CORE-blueprints.md`](references/CHAT-CORE-blueprints.md)
- Video setup, call types, controls, state, StreamCallContainer -> [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md)
- Video widget blueprints (entry point, join, call container, controls, participant tile) -> [`references/VIDEO-FLUTTER-blueprints.md`](references/VIDEO-FLUTTER-blueprints.md)
- Livestream SDK patterns (call type, backstage, goLive/stopLive, HLS) -> [`references/LIVESTREAM-FLUTTER.md`](references/LIVESTREAM-FLUTTER.md)
- Livestream widget blueprints (mode selection, creator, WebRTC viewer, HLS viewer) -> [`references/LIVESTREAM-FLUTTER-blueprints.md`](references/LIVESTREAM-FLUTTER-blueprints.md)

---

## Track D - Bootstrap / setup

Use when the user wants the install and wiring path more than a feature build:

- detect the project shape
- choose `stream_chat_flutter` vs `stream_chat_flutter_core`
- add Stream dependencies to `pubspec.yaml` and run `flutter pub get`
- wire `StreamChatClient` and the `StreamChat` widget via [`sdk.md`](sdk.md)
- complete platform setup (Android permissions, iOS Info.plist keys) for the chosen packages
- stop before product-specific UI if the user only asked for setup
