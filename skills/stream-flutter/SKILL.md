---
name: stream-flutter
description: "Build and integrate Stream Chat, Video, and Feeds in Flutter apps. Use for Flutter/Dart project work with Stream package setup, auth wiring, and widget blueprints. Supports stream_chat_flutter (pre-built Chat UI), stream_chat_flutter_core (custom Chat UI), stream_video_flutter (Video calling and livestreaming), and stream_feed / stream_feed_flutter_core (Activity Feeds, no pre-built UI). Also migrates Flutter apps from the Sendbird Chat SDK (sendbird_chat_sdk / sendbird_uikit) to Stream Chat."
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
  Bash(getstream token *),
  Bash(getstream env *),
  Bash(getstream api *),
  Bash(getstream login *),
  Bash(getstream init *)
---

# Stream Flutter - skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session - every non-negotiable rule is stated there, nowhere else.

This file is the **single entrypoint**: intent classification, local project detection, and module pointers for Stream work in Flutter apps.

---

## Step 0: Intent classifier (mandatory first - never skip)

Before any tool call, decide the **track** from the user's input alone - no probes first.

### Signals -> track

| Signal in user input                                                                                                                                          | Track                                                                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Explicit package/widget token: `stream_chat_flutter`, `StreamChannelListView`, `StreamMessageListView`, `StreamChatClient`, etc.                              | **C - Reference lookup**                                                                                                                            |
| Explicit video token: `stream_video_flutter`, `StreamCallContainer`, `StreamVideo`, `StreamVideoRenderer`, `goLive`, `stopLive`, `livestream` call type       | **C - Reference lookup**                                                                                                                            |
| Explicit feeds token: `stream_feed`, `stream_feed_flutter_core`, `StreamFeedClient`, `FlatFeedCore`, `FlatFeed`, `FeedBloc`, `activity feed`, `feeds flutter` | **C - Reference lookup**                                                                                                                            |
| Words "docs" or "documentation" around Stream Flutter work                                                                                                    | **C - Reference lookup**                                                                                                                            |
| "How do I {X} in Flutter?", "What does {widget/method} do?"                                                                                                   | **C - Reference lookup**                                                                                                                            |
| "Build me a new Flutter app", "create a Flutter chat app" + Stream                                                                                            | **A - New app**                                                                                                                                     |
| "Build a Flutter video call app", "create a livestream app in Flutter"                                                                                        | **A - New app** (load `VIDEO-FLUTTER.md` + `VIDEO-FLUTTER-blueprints.md` or `LIVESTREAM-FLUTTER.md` + `LIVESTREAM-FLUTTER-blueprints.md`)           |
| "Build an audio room / Twitter Spaces clone", "TikTok-style live feed", "call while livestreaming", "chat with video calls", "two calls at once"              | **A or B** (load `VIDEO-ADVANCED-FLUTTER.md` + `VIDEO-ADVANCED-FLUTTER-blueprints.md` on top of the Video/Livestream pair)                          |
| "Add ringing / incoming calls", "video call with push notifications", "CallKit", "VoIP push", "FCM ringing", "missed call notification"                       | **A or B** (load `RINGING-FLUTTER.md` + `RINGING-FLUTTER-blueprints.md` on top of the Video pair)                                                   |
| "Build a Flutter feeds app", "create an activity feed app", "build a social feed in Flutter", "create a Twitter/Instagram clone"                              | **A - New app** (load `FEEDS-FLUTTER.md` + `FEEDS-FLUTTER-blueprints.md`; use Twitter-style UI unless the user explicitly specifies otherwise)      |
| "Add/integrate Stream into this app", "wire Chat into my Flutter project"                                                                                     | **B - Existing app**                                                                                                                                |
| "Add video calling to my Flutter app", "integrate Stream Video into my existing app"                                                                          | **B - Existing app** (load `VIDEO-FLUTTER.md` + `VIDEO-FLUTTER-blueprints.md`)                                                                      |
| "Add a feed to my Flutter app", "integrate Stream Feeds into my existing app", "add activity feed"                                                            | **B - Existing app** (load `FEEDS-FLUTTER.md` + `FEEDS-FLUTTER-blueprints.md`; use Twitter-style UI unless the user explicitly specifies otherwise) |
| "Install Stream packages", "set up Stream in Flutter", "wire auth/token" with no broader feature request                                                      | **D - Bootstrap / setup**                                                                                                                           |
| "Migrate my Flutter app from Sendbird", "replace `sendbird_chat_sdk` / `sendbird_uikit` with Stream", "switch off Sendbird / SendbirdUIKit"                    | **M - Migrate from Sendbird** ([`sendbird-migration.md`](sendbird-migration.md))                                                                    |
| Bare `/stream-flutter` with no args                                                                                                                           | List the tracks briefly and wait                                                                                                                    |

### Styling-depth flag (orthogonal to Tracks A/B/C/D)

If the request carries a **target appearance** — an attached screenshot, a Figma frame, or "make it look like WhatsApp / iMessage / Telegram / Slack / <app>" — then **before** feature work (Track A or B), **first run the strategy decision below** (components vs custom): if it lands on components, run [`design-matching.md`](design-matching.md); if it lands on custom (livestream / overlay / bespoke), run [`custom-ui.md`](custom-ui.md) instead — same region-by-region rigor, different mechanism. The rest of this paragraph is the components case (the common one). A reference design is a checklist of regions (header, composer buttons, where the timestamp + read receipts sit, bubble shape/tail, date separators, attachments...), and most of them differ from Stream's defaults **structurally**, not just by color. Do **not** stop at the wallpaper and bubble color — that is the known failure mode. Decompose every region first (capturing its **dimensions**, not just colors), then route each to one of **two axes**: (1) **Theming** — `StreamTheme` (a `ThemeExtension` on `MaterialApp.theme.extensions`) owns design foundations (spacing / radius / typography / colors) **and** all fine-grained/leaf styling including the whole message row (`messageItemTheme` bubble/text/attachment/metadata, `reactionsTheme`, `reactionPickerTheme`, `avatarTheme`, `textInputTheme`, `mediaViewerTheme`, …), while `StreamChatThemeData` (passed to `StreamChat(themeData:)`) owns only the chat composite-widget slots (the three headers, message-list background/wallpaper, channel-list item, quoted message, thread tile, poll themes); (2) **Widget replacement** — the component factory, populated via **core named slots** on `StreamComponentBuilders(...)` (~48 leaf slots: `messageBubble`, `messageText`, `reactions`, `reactionPicker`, `mediaViewer`, `jumpToUnreadButton`, `textInput`, `avatar`, …) **and** **chat slots** via `streamChatComponentBuilders(...) → extensions:` (~30 composite slots: `messageItem`, `messageComposer` + sub-slots, `channelListItem`, per-attachment builders, …), passed to `StreamChat(componentBuilders: StreamComponentBuilders(...))` (global) or `StreamComponentFactory(builders: …, child: …)` (scoped); plus per-widget builders (`messageBuilder`, `itemBuilder`) for a single instance. Recurring traps the doc guards against: (a) overriding a **composite widget** (`messageItem` builder, `messageComposer` builder, `messageBuilder` on `StreamMessageListView`) silently drops the sub-features the default rendered — the incoming-message avatar, grouping, reactions, replies, status, or the send/voice/edit/slow-mode button — unless you read the default's `build()` and reproduce them (grouping state is available inside a custom `messageItem` via `StreamMessageLayout.of(context)`); (b) **model-driven title logic** must live in one shared helper used by both the channel list `itemBuilder` and the header, so the two surfaces cannot diverge; (c) route deliberately — bubble padding / color / shape live on **`StreamTheme`** (`StreamTheme.messageItemTheme.bubble`), not on `StreamChatThemeData`, while structural changes (send button outside the field, metadata inside the bubble, a bubble tail, a Slack-style flat row) need **widget replacement** (component factory or a per-widget builder). The match is **not done until you run, seed data that triggers every region, compare region-by-region against the reference on the real navigation path, and iterate** ([`design-matching.md`](design-matching.md) Step 5), deleting any throwaway verification scaffold — the UI must be as close to the reference as possible, not approximately like it. **Implement every region, the composer included** — never deliver a partial match with the rest labelled "known cosmetic gaps"; a region left at the SDK default is a FAIL, not a footnote. And **work in batches**: ground the pinned SDK version + local checkout once, read the source you need in one pass, implement all regions, then verify once on hot reload — don't rebuild-and-screenshot after every small edit.

### Chat only: pick the UI strategy first (before any code)

Stream Chat ships **two layers**, and choosing between them is an **architecture decision that dwarfs any styling choice** — getting it wrong wastes a day either way. So decide deliberately, and **default to the pre-built components**:

| Strategy | Use when the design is... | Mechanism | Runbook |
|---|---|---|---|
| **Pre-built UI components** (`stream_chat_flutter`) — **the default** | A messenger: bubbles, or a channel list → conversation, or per-message avatar/timestamp/receipts/reactions/attachments. Social, marketplace, workplace, support, DMs. "Make it look like WhatsApp / iMessage / Telegram / Slack." | Customize via the two axes — theming (`StreamTheme` for foundations + the message row/leaf widgets, `StreamChatThemeData` for the chat composite widgets) + widget replacement (the component factory `StreamComponentBuilders` / `streamChatComponentBuilders` / `StreamComponentFactory`, plus per-widget builders) | [`design-matching.md`](design-matching.md) |
| **Custom UI on `stream_chat_flutter_core`** — the exception | Not a messenger: a flat bubble-less author-inline feed, an overlay/ticker on video, high-volume ephemeral livestream chat (Twitch / YouTube / Kalshi), live shopping, or anonymous/guest read-only viewers vastly outnumbering posters (→ `livestream` channel type). Every message rendered identically; bespoke app chrome around it. | Build your own widgets on the headless `stream_chat_flutter_core` controllers (+ the low-level client); **no** `stream_chat_flutter` widgets | [`custom-ui.md`](custom-ui.md) |

**Lean hard toward components.** They're built to be *customized*, and the litmus test is: *if the two axes — theming (`StreamTheme` + `StreamChatThemeData`) + a few component-builder slots — could get there, it's a components job* — even strong messenger reskins. Pick **custom only** when matching the design would mean replacing the message row, composer, header, AND list all at once — i.e. you'd be using the SDK purely as a data source, not for any of its widgets. Over-choosing custom (rebuilding a worse messenger by hand, losing avatars/grouping/reactions/threads/attachments/typing/receipts/pickers) is the common, expensive mistake; over-choosing components costs a few hours of fighting layout. **When unsure, build the components version first** — it's faster to confirm-or-reject. And treat **"livestream" / "live-shopping" as signals, not labels**: they point to custom only when the *shape* matches (flat identical rows, overlay/ticker, high volume, read-only viewers) — a livestream app that wants a normal bubble/channel-list chat panel stays on **components**. This is the full decision rubric; [`custom-ui.md`](custom-ui.md) is the build runbook you follow *after* the decision lands on custom, not a doc you open to decide.

**Workplace / Slack-style hybrid is a components job too.** A Slack/Teams/Discord surface is a channel list + message list + composer, so it stays on the pre-built components — but two things differ from a messenger and must be matched, not punted: (1) the **message row** is flat and left-aligned (avatar-top rounded-square, an author·custom-status·timestamp header line, body, **bottom reaction pills**, and a **thread-reply summary**), with **no incoming/outgoing bubble split** — reproduce it by overriding the `messageItem` component builder (a composite slot — reproduce its sub-features); (2) the **header** and chrome are custom. The full workplace archetype is in [`design-matching.md`](design-matching.md). Workplace apps are also **thread-first**, so wire the thread-reply summary and thread screen.

The strategy also picks the **channel type and permission model** (e.g. `messaging` membership-gated for social/marketplace vs `livestream` public + anonymous viewers) — see [`RULES.md`](RULES.md) → "Surface permission prerequisites proactively", and Step 0.5 → "Permissions awareness". Decide both axes together.

If it's genuinely unclear, ask one question:

> Does this chat look like a standard messenger (channel list + bubbles), or a bespoke surface like livestream/overlay chat? It decides whether we customize the pre-built components or build custom UI on `stream_chat_flutter_core`.

### Disambiguation flow

If the request is ambiguous between **build/integrate** and **reference lookup**, ask one short question and wait:

> Do you want me to wire this into the project, or just map the Flutter SDK pattern and widgets?

### After classification

- **Tracks A, B, D** -> run **Project signals** once per session, then continue in [`builder.md`](builder.md) and [`sdk.md`](sdk.md). If the styling-depth flag was raised, run the design-match phase alongside per the UI-strategy decision — [`design-matching.md`](design-matching.md) for the pre-built components (the common case) or [`custom-ui.md`](custom-ui.md) for a bespoke `stream_chat_flutter_core` surface (design-match rigor is a mandatory phase, not an optional add-on).
- **Track C** -> skip the probe if the product + package are explicit. Only run it on demand if the SDK layer is ambiguous.
- **Track M** -> run [`sendbird-migration.md`](sendbird-migration.md): detect the existing Sendbird integration shape, swap packages/init/views/channels/messages, re-apply theming via the two axes, and verify design + functional fidelity per screen against the Sendbird original. Reuses Step 0.5 credentials and [`design-matching.md`](design-matching.md)/[`custom-ui.md`](custom-ui.md) rigor; hands off to the shared data-migration runbook when the code migration is done.

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

> **Guest-viewer requirement — surface this BEFORE building any app that signs viewers in as guests**. A guest connects with the `guest` role, which by default has minimal capabilities. On the `livestream` call type guests **cannot even read or join a call** until the integrator grants those capabilities to the `guest` role. When a guest-based viewer flow is in scope, tell the integrator it is a **prerequisite** to grant the `guest` role `read-call` and `join-call` (plus `create-call` if a viewer may open the call before the host) on the relevant call type via Stream Dashboard → Video & Audio → Call Types → <type> → Roles & Permissions (or the API), or to use authenticated `User.regular` viewers instead. Details: [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md) → Guest users, and [`references/LIVESTREAM-FLUTTER.md`](references/LIVESTREAM-FLUTTER.md) → Roles, permissions, and backstage security.

**For Feeds projects** (no pre-built UI; feed groups required):

Ask **one message** with all setup questions together — do not split into rounds:

> To wire everything up, I need a few quick answers:
>
> 1. **Credentials** - Should I fetch your API key from the dashboard and generate a token via the Stream CLI, or will you paste them yourself?
> 2. **Token expiry** - If I'm generating the token: should it expire? (e.g. `1h`, `1d`, `30m`) or never expire?
> 3. **Feed groups** - I need to create 3 feed groups in your Stream project (user, timeline, notification). Should I set these up automatically, or have you already created them?
> 4. **Seed posts** - Should I add a few sample posts so the feed has content from the first run?
>
> If you want to handle credentials yourself, just paste your API key and token.

Once the user replies, execute all steps without pausing. For feed groups, if the user said "set up automatically":

```bash
getstream api CreateFeedGroup --request '{"id": "user", "type": "flat"}'
getstream api CreateFeedGroup --request '{"id": "timeline", "type": "flat"}'
getstream api CreateFeedGroup --request '{"id": "notification", "type": "notification"}'
```

If the CLI commands fail (the Feeds API may use different endpoints than Chat), tell the user once:

> Please create these in Stream Dashboard → Activity Feeds → Feed Groups: `user` (Flat), `timeline` (Flat), `notification` (Notification).

For Feeds projects, always generate two separate helpers in `main` after `connect()`:

1. `_setupFollows(client)` — **always called, unconditionally.** Makes `timeline` follow `user` so the user's own posts appear there. Do not merge this into seed logic — once seed data exists the guard returns early and the follow call never runs.
2. `_seedPosts(client)` — only if the user said yes to seeding. Adds sample activities and exits early if data already exists.

See [`references/FEEDS-FLUTTER.md`](references/FEEDS-FLUTTER.md) for both implementations.

The package is `stream_feeds: ^0.5.1` — not the deprecated `stream_feed` or `stream_feed_flutter_core`.

### After the user replies - act without further prompting

Once the user answers, execute all CLI steps in sequence **without pausing for confirmation between them**. Narrate each step briefly as you go (one line per action), but do not stop to ask "shall I continue?".

#### Step A - API key

```bash
getstream env --target flutter
```

This writes the public API key to `dart_defines.json`; the app reads it via `String.fromEnvironment('STREAM_API_KEY')` and is run with `flutter run --dart-define-from-file=dart_defines.json`. If the command returns a 401 error, the CLI session has expired - run `getstream login` to re-authenticate, then retry.

**If `getstream` is not installed** (`command not found`): ask the user to install it from https://getstream.io and wait. Or, if the user prefers, skip the CLI entirely and have them paste the API key + a token per user (Dashboard -> Explorer has a token generator). Decide based on the user's answer to the upfront credentials question; don't stall.

#### Step B - Token

```bash
# Never-expiring
getstream token <user_id>

# Expiring
getstream token <user_id> --ttl <duration>
```

Hold the token in context. Use it (and the API key) in every code snippet - no placeholder strings.

#### Step C - Seed channels (only if the user said yes)

Create 3-5 channels with random realistic usernames. Use `messaging` as the default channel type.

**Sub-step C1 — upsert all users** (seed users + the token user):

```bash
getstream api UpdateUsers --request '{
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
getstream api GetOrCreateChannel --type messaging --id <channel-id> \
  --request '{"data": {"custom": {"name": "<Channel Name>"}}}'
```

Repeat for each channel (e.g. `general`, `random`, `team-alpha`).

**Sub-step C3 — add members to each channel** using `add_members`. The token user **must** be in every channel so the `Filter.in_('members', [userId])` query in the app returns results.

```bash
getstream api UpdateChannel --type messaging --id <channel-id> \
  --request '{
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

### Permissions awareness (Chat - surface proactively)

Stream Chat checks permissions **per role, per scope on every client-side call** — but **server-side calls (the CLI and your backend, using the API _secret_) bypass all checks**. That asymmetry is the #1 source of "it worked when you seeded it, but the app 403s": seeding channels via the CLI succeeds regardless of grants, then the same query/join from the app hits the connected user's role and fails.

**When the app you're about to build does anything beyond chatting inside channels the user is already a member of, tell the integrator about the relevant grants _before_ writing the feature — don't wait for a runtime 403.** Map the scenario to the grant:

| App behaviour you're building                                                                    | Grant the connecting role needs on the channel type            | Default `messaging` for `user`/`guest` |
| ------------------------------------------------------------------------------------------------ | -------------------------------------------------------------- | -------------------------------------- |
| **Discover / browse groups** the user didn't create (`queryChannels` without a `members` filter) | `Read Channel` (`ReadChannel`)                                 | often **off**                          |
| **Join an existing group** (`channel.addMembers([myId])`)                                        | `Add Own Channel Membership` (`AddOwnChannelMembership`)       | often **off**                          |
| **Leave a group** (`channel.removeMembers([myId])`)                                              | `Remove Own Channel Membership` (`RemoveOwnChannelMembership`) | varies                                 |
| **Create a group**                                                                               | `Create Channel` (`CreateChannel`)                             | usually on                             |

`guest` users (name-only / no-backend sign-in) are stricter than `user` — if the app uses guest auth, the same grants must be added to the **`guest`** role too. Point the integrator to **Dashboard → Chat → Roles & Permissions** (permissions v2) for the role + `messaging` type, or `UpdateChannelType` via API/CLI. Full detail and the exact error string: [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md) → Channel permissions & roles (custom-UI builds: [`references/CHAT-CORE.md`](references/CHAT-CORE.md)).

This is a **prompt, not a blocker** — build the feature as requested, but call out the prerequisite in the same turn so discover/join/create don't silently fail on first run.

---

## Project signals (tracks A/B/D - once per session; Track C on demand only)

Read-only local probe. Use it to detect whether the user is in a Flutter project or an empty directory.

```bash
bash -c 'echo "=== FLUTTER ==="; find . -maxdepth 2 -name "pubspec.yaml" -print 2>/dev/null; echo "=== STREAM ==="; grep -rE "stream_chat|stream_video|stream_feed" . --include="pubspec.yaml" -l 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Hold the result in conversation context. Don't re-run it unless the user changes directory or the project shape clearly changed.

Use the result to produce a **one-line status**, for example:

- `Flutter app detected - stream_chat_flutter already in pubspec.yaml`
- `Flutter app detected - stream_video_flutter already in pubspec.yaml`
- `Flutter app detected - stream_feed already in pubspec.yaml`
- `Flutter app detected - no Stream dependency yet, ready to install`
- `No Flutter project found - user needs to run flutter create first`

### Version prerequisite (Chat - existing project)

When a Stream Chat dependency is already present, check the resolved version (`pubspec.yaml` constraint or the `version:` in `pubspec.lock`). **These skills target `stream_chat_flutter` / `stream_chat_flutter_core` v10 only.** If the project is pinned to **9.x or earlier**, stop before editing code and tell the user:

> Your project uses `stream_chat_flutter` v<found>. These instructions cover v10. A lot changed between v9 and v10 (widget names, controllers, theming, reaction/delete APIs). The official migration guides are at **https://github.com/GetStream/stream-chat-flutter/tree/master/migrations** — refer to the relevant version's guide for step-by-step instructions. Once you're on v10, I can continue with the full feature set.

If the user asks for help with the migration itself, fetch the relevant migration doc from the URL above and walk them through it step by step.

Only proceed with Chat work once the project resolves a v10 (`^10.0.0`) dependency. New installs always use `^10.0.0`, so this check applies to existing integrations only.

---

## Module map

| Track                                             | Module(s)                                                                                                             |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| A - New app                                       | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + relevant reference files                                            |
| B - Existing app                                  | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + relevant reference files                                            |
| C - Reference lookup                              | [`sdk.md`](sdk.md) + relevant reference files                                                                         |
| D - Bootstrap / setup                             | [`builder.md`](builder.md) + [`sdk.md`](sdk.md)                                                                       |
| M - Migrate from Sendbird                         | [`sendbird-migration.md`](sendbird-migration.md) (+ [`design-matching.md`](design-matching.md)/[`custom-ui.md`](custom-ui.md), [`sdk.md`](sdk.md), [`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md)) |
| Styling-depth flag (screenshot/Figma/"look like") | Pick the UI strategy first (Step 0). Components → [`design-matching.md`](design-matching.md); bespoke/livestream/overlay → [`custom-ui.md`](custom-ui.md). Run **before** feature work on Track A/B; region-by-region rigor + verification loop either way |

> **Feeds note (Track A/B):** Use Twitter-style UI by default. Only deviate if the user explicitly requests a different style (e.g., "Instagram grid", "Reddit-style votes").

---

## Reference layout

Shared Flutter/Dart patterns live in **[`sdk.md`](sdk.md)**.

Product and package specifics live under **`references/`** using a flat naming scheme:

- **Reference:** `references/<PRODUCT>-<PACKAGE>.md`
- **Blueprints:** `references/<PRODUCT>-<PACKAGE>-blueprints.md`

Current extracted modules:

- **Chat + pre-built UI (`stream_chat_flutter`):** [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md) + [`references/CHAT-FLUTTER-blueprints.md`](references/CHAT-FLUTTER-blueprints.md)
- **Chat + custom UI (`stream_chat_flutter_core`):** [`references/CHAT-CORE.md`](references/CHAT-CORE.md) + [`references/CHAT-CORE-blueprints.md`](references/CHAT-CORE-blueprints.md)
- **Chat advanced (push, offline, lifecycle — both UI tiers):** [`references/CHAT-ADVANCED-FLUTTER.md`](references/CHAT-ADVANCED-FLUTTER.md) + [`references/CHAT-ADVANCED-FLUTTER-blueprints.md`](references/CHAT-ADVANCED-FLUTTER-blueprints.md) - push notifications, offline/local persistence, connection lifecycle & backgrounding
- **Video (`stream_video_flutter`):** [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md) + [`references/VIDEO-FLUTTER-blueprints.md`](references/VIDEO-FLUTTER-blueprints.md)
- **Livestream (`stream_video_flutter`):** [`references/LIVESTREAM-FLUTTER.md`](references/LIVESTREAM-FLUTTER.md) + [`references/LIVESTREAM-FLUTTER-blueprints.md`](references/LIVESTREAM-FLUTTER-blueprints.md)
- **Video advanced use cases (`stream_video_flutter`):** [`references/VIDEO-ADVANCED-FLUTTER.md`](references/VIDEO-ADVANCED-FLUTTER.md) + [`references/VIDEO-ADVANCED-FLUTTER-blueprints.md`](references/VIDEO-ADVANCED-FLUTTER-blueprints.md) - audio rooms, multicall, chat+video, livestream feed, querying/events/preferences/moderation
- **Ringing / incoming calls + push (`stream_video_flutter` + `stream_video_push_notification`):** [`references/RINGING-FLUTTER.md`](references/RINGING-FLUTTER.md) + [`references/RINGING-FLUTTER-blueprints.md`](references/RINGING-FLUTTER-blueprints.md) - outgoing ring, foreground/background/terminated incoming, CallKit (iOS) + FCM (Android)
- **Feeds (`stream_feed` / `stream_feed_flutter_core`):** [`references/FEEDS-FLUTTER.md`](references/FEEDS-FLUTTER.md) + [`references/FEEDS-FLUTTER-blueprints.md`](references/FEEDS-FLUTTER-blueprints.md)

Additional Stream product coverage should stay in this naming family instead of creating more top-level skills.

---

## Track A - New app

**Full detail:** [`builder.md`](builder.md) - use the **new-project path**.

| Phase  | Name           | What you do                                                                                                                                                                                                                                                                        |
| ------ | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A1** | Detect         | Run **Project signals**. If there is no Flutter app yet, tell the user to run `flutter create my_app` first.                                                                                                                                                                       |
| **A2** | Choose lane    | Confirm package choice: `stream_chat_flutter` (pre-built UI, fastest), `stream_chat_flutter_core` (custom UI), `stream_video_flutter` (video/livestream), or `stream_feed` / `stream_feed_flutter_core` (activity feeds, no pre-built UI). For Chat, this is the same components-vs-custom call as Step 0's "pick the UI strategy first" — **default hard to `stream_chat_flutter`**; pick core only for genuinely non-messenger surfaces ([`custom-ui.md`](custom-ui.md)). For Feeds, default to Twitter-style UI. |
| **A3** | Install + wire | Follow [`builder.md`](builder.md) + [`sdk.md`](sdk.md), then load only the needed reference files.                                                                                                                                                                                 |
| **A4** | Verify         | Confirm `flutter pub get` succeeds, client connects, and first screen renders. If the app discovers/joins channels or uses guest auth, re-state the permission prerequisite (Step 0.5 → Permissions awareness) so those flows don't 403 on first run.                              |

---

## Track B - Existing app

**Full detail:** [`builder.md`](builder.md) - use the **existing-project path**.

| Phase  | Name      | What you do                                                                                                                                                                                                                                     |
| ------ | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **B1** | Detect    | Run **Project signals** and inspect the existing app structure before editing.                                                                                                                                                                  |
| **B2** | Preserve  | Keep the current navigation, state management, and widget architecture unless the user asks for a change.                                                                                                                                       |
| **B3** | Integrate | Use [`sdk.md`](sdk.md) for shared wiring, then load only the needed reference files.                                                                                                                                                            |
| **B4** | Verify    | Confirm the requested Stream flow builds and renders inside the existing app. If it discovers/joins channels or uses guest auth, re-state the permission prerequisite (Step 0.5 → Permissions awareness) so those flows don't 403 on first run. |

---

## Track C - Reference lookup

Load only the relevant files for the requested package.

- Shared lifecycle / auth / state / client-ownership patterns -> [`sdk.md`](sdk.md)
- Chat advanced production concerns — **push notifications, offline/local persistence, connection lifecycle & backgrounding** (both UI tiers) -> [`references/CHAT-ADVANCED-FLUTTER.md`](references/CHAT-ADVANCED-FLUTTER.md)
- Chat advanced wiring blueprints (FCM setup + background handler, persistence init, lazy-connect gate) -> [`references/CHAT-ADVANCED-FLUTTER-blueprints.md`](references/CHAT-ADVANCED-FLUTTER-blueprints.md)
- Chat pre-built UI setup, widgets, theming, **member/user lists, message search, composer flags (voice/polls/drafts), filter operators, permissions** -> [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md)
- Chat pre-built UI widget blueprints -> [`references/CHAT-FLUTTER-blueprints.md`](references/CHAT-FLUTTER-blueprints.md)
- Chat custom UI setup and controllers -> [`references/CHAT-CORE.md`](references/CHAT-CORE.md)
- Chat custom UI widget blueprints -> [`references/CHAT-CORE-blueprints.md`](references/CHAT-CORE-blueprints.md)
- Video setup, call types, controls, state, StreamCallContainer -> [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md)
- Video widget blueprints (entry point, join, call container, controls, participant tile) -> [`references/VIDEO-FLUTTER-blueprints.md`](references/VIDEO-FLUTTER-blueprints.md)
- Livestream SDK patterns (call type, backstage, goLive/stopLive, HLS) -> [`references/LIVESTREAM-FLUTTER.md`](references/LIVESTREAM-FLUTTER.md)
- Livestream widget blueprints (mode selection, creator, WebRTC viewer, HLS viewer) -> [`references/LIVESTREAM-FLUTTER-blueprints.md`](references/LIVESTREAM-FLUTTER-blueprints.md)
- Video advanced patterns (audio rooms, multicall, chat+video wiring, queryCalls, call events, preferences, moderation, session timers, network handling) -> [`references/VIDEO-ADVANCED-FLUTTER.md`](references/VIDEO-ADVANCED-FLUTTER.md)
- Video advanced use-case blueprints (audio room screen, TikTok-style livestream feed, floating call panel, chat-with-video) -> [`references/VIDEO-ADVANCED-FLUTTER-blueprints.md`](references/VIDEO-ADVANCED-FLUTTER-blueprints.md)
- Ringing SDK patterns (push-enabled init, outgoing ring, incoming foreground/background/terminated, CallKit/FCM setup, accept/reject/end, customization, missed calls) -> [`references/RINGING-FLUTTER.md`](references/RINGING-FLUTTER.md)
- Ringing blueprints (push init, background FCM handler, home-screen observers, outgoing ring, call screen, iOS AppDelegate, Android manifest/Gradle) -> [`references/RINGING-FLUTTER-blueprints.md`](references/RINGING-FLUTTER-blueprints.md)
- Feeds SDK setup, StreamFeedClient, feed types, activities, reactions, follow/unfollow, realtime -> [`references/FEEDS-FLUTTER.md`](references/FEEDS-FLUTTER.md)
- Feeds widget blueprints (Twitter-style by default: home feed, activity card, compose, profile, notifications; also Instagram/Reddit variants) -> [`references/FEEDS-FLUTTER-blueprints.md`](references/FEEDS-FLUTTER-blueprints.md)

---

## Track D - Bootstrap / setup

Use when the user wants the install and wiring path more than a feature build:

- detect the project shape
- choose `stream_chat_flutter` vs `stream_chat_flutter_core`
- add Stream dependencies to `pubspec.yaml` and run `flutter pub get`
- wire `StreamChatClient` and the `StreamChat` widget via [`sdk.md`](sdk.md)
- complete platform setup (Android permissions, iOS Info.plist keys) for the chosen packages
- stop before product-specific UI if the user only asked for setup

---

## Track M - Migrate from Sendbird

**Full detail:** [`sendbird-migration.md`](sendbird-migration.md). Migration is integration-shaped
(preserve the existing app), so it behaves like Track B with a Sendbird-specific runbook.

| Phase  | Name          | What you do                                                                                                                                                                                                 |
| ------ | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **M1** | Detect        | Run **Project signals**; grep the Sendbird footprint and classify each touchpoint's shape ([`sendbird-migration.md`](sendbird-migration.md) §0). Capture the Sendbird baseline and **create the fidelity matrix** (§0.5) — every **Sendbird-backed** screen (§0's touchpoints, not the whole app), region, and interaction enumerated as `pending` rows — before any code changes.                                                            |
| **M2** | Swap + wire   | Remove `sendbird_chat_sdk`/`sendbird_uikit`, add Stream packages; get credentials (Step 0.5); wire one `StreamChatClient` + `StreamChat` provider, repointing existing bootstraps without changing their public API (§1–§2). |
| **M3** | Re-implement  | Migrate each touchpoint per its pattern — views + navigation (§3), channels (§4), messages/custom attachments (§5); re-apply theming via the two axes (§6, [`design-matching.md`](design-matching.md)).      |
| **M4** | Verify        | **Finish the fidelity matrix (§0.5) — exit = zero `pending` rows, not a green build.** Every `render` row backed by the before/after pair it was compared against (preserve path: zero visual change); every `drive` row — the interactions the source actually has (reply/edit → composer, pickers, long-press, reactions, threads) — performed on the device: a screen that paints can still be behaviorally dead. Deferrals require a named, grounded missing SDK API and must be surfaced. Paste the matrix into the final report. Confirm Sendbird deps are fully removed.     |
| **M5** | Offer data    | Once the code migration builds, connects, and matches, **ask** whether to also migrate the Sendbird **data** and hand off to [`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md) (§10). |
