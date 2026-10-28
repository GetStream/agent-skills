---
name: stream-flutter
description: "Build, integrate, migrate to, and answer how-to questions for Stream Chat, Video, and Feeds in Flutter / Dart apps. Supports stream_chat_flutter (pre-built Chat UI), stream_chat_flutter_core (custom Chat UI), stream_video_flutter (calls, ringing, audio rooms, livestreaming), and stream_feeds (Activity Feeds v3, no pre-built UI). Routes each request to the exact official Flutter docs page, fetches it live, and applies it - with a curated setup flow, a push / ringing runbook, design-matching and custom-UI runbooks, a Sendbird -> Stream Chat migration runbook, and Flutter-specific pitfalls."
license: See LICENSE in repository root
compatibility: Requires a Flutter project for build/integrate work (or scaffolds one when asked to create a new app). Credentials and seeding use the getstream CLI. Docs lookups need only network access.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  WebFetch(domain:getstream.io),
  WebFetch(domain:github.com),
  WebFetch(domain:raw.githubusercontent.com),
  WebFetch(domain:pub.dev),
  Bash(ls *),
  Bash(grep *),
  Bash(find . *),
  Bash(find ~/.pub-cache *),
  Bash(cat pubspec.yaml), Bash(cat pubspec.lock),
  Bash(jq *),
  Bash(flutter pub *),
  Bash(flutter create *),
  Bash(flutter run *),
  Bash(flutter analyze *), Bash(flutter analyze),
  Bash(flutter build *),
  Bash(flutter devices),
  Bash(flutter emulators *), Bash(flutter emulators),
  Bash(getstream *),
  Bash(sips *), Bash(awk *), Bash(adb *), Bash(xcrun simctl *),
  Bash(flutter drive *), Bash(flutter test *), Bash(flutterfire *)
---

# Stream Flutter - docs orchestrator for Flutter

This skill is **small on purpose**. It does not bundle SDK reference dumps - the official Flutter docs are the source of truth and cover the whole surface (Chat UI + core + low-level client, Video calls / ringing / livestream, Feeds).

Your job is to **orchestrate**: classify the request, point to the *exact* docs page, fetch it live, and apply it inside the user's project - while obeying the curated rules and pitfalls the docs do not shout about.

**Rules (read once per session):** [`RULES.md`](RULES.md) - non-negotiable rules + Flutter pitfalls. Read before writing any code.

---

## The docs convention (the core mechanism)

Every Stream docs page has a Markdown twin: **take the page URL, drop the trailing `/`, add `.md`.**

```
https://getstream.io/chat/docs/sdk/flutter/basics/installation/   ->   https://getstream.io/chat/docs/sdk/flutter/basics/installation.md
```

Always fetch the `.md` variant - clean Markdown with verbatim code, no page chrome.

Per-product **index** pages list every page with its `.md` URL:

| Product | Live index (always current) | Page URL shape |
|---|---|---|
| Chat (Flutter SDK: `stream_chat_flutter` + `_core`) | `https://getstream.io/cli/docs/chat-sdk-flutter.md` | `https://getstream.io/chat/docs/sdk/flutter/...md` |
| Chat (low-level client API reference) | `https://getstream.io/cli/docs/chat-flutter-dart.md` | `https://getstream.io/chat/docs/flutter-dart/...md` |
| Video | `https://getstream.io/cli/docs/video-flutter.md` | `https://getstream.io/video/docs/flutter/...md` |
| Feeds | `https://getstream.io/cli/docs/activity-feeds-flutter.md` | `https://getstream.io/activity-feeds/docs/flutter/...md` |

**URL grounding:** only fetch a page URL you got from [`docs-map.md`](docs-map.md) or from a live index fetch in this conversation. Do not invent doc paths from memory - many look guessable but are wrong. If a page is not in the map, fetch the live index and pick from it.

---

## Step 0: Classify the request (always first)

From the user's words alone - no probes first - resolve three things:

1. **Product** - Chat, Video (calls, ringing, audio rooms, livestream), Feeds, or a combination.
2. **Package / layer** - Chat: `stream_chat_flutter` (pre-built UI, the default) or `stream_chat_flutter_core` (custom UI - see the strategy decision below). Video: `stream_video_flutter`. Feeds: `stream_feeds` (never the deprecated `stream_feed`).
3. **Mode** - one of:
   - **How-to / reference** ("how do I add reactions?", "what does `StreamCallContainer` do?", "theming", explicit widget/package tokens, "docs") -> go straight to **Docs lookup**. No setup, no credentials.
   - **Integrate** ("add Chat to my app", "wire Video into this project") -> run [`setup.md`](setup.md), then **Docs lookup** for the feature.
   - **New app** ("build a Flutter chat app", "create a livestream app", "build a Twitter-style feed") -> [`setup.md`](setup.md) (it scaffolds when asked), then **Docs lookup**, scoped to the requested screens. Feeds defaults to Twitter-style UI.
   - **Setup only** ("install Stream", "wire auth/token") -> [`setup.md`](setup.md) and stop.
   - **Push / ringing** ("push notifications", "incoming calls when the app is closed", "CallKit", "FCM", "missed calls") -> [`push.md`](push.md) (after setup if the app is not wired yet).
   - **Advanced Video patterns** (TikTok-style livestream feed, 1:1 call while livestreaming, two calls at once, audio-room lobby, shared call state, Chat + Video in one app) -> [`video-patterns.md`](video-patterns.md) plus the docs it routes to.
   - **Migrate from Sendbird** ("replace `sendbird_chat_sdk` / `sendbird_uikit` with Stream", "switch off Sendbird") -> run [`sendbird-migration.md`](sendbird-migration.md): detect the Sendbird integration shape, swap packages + init, re-implement each touchpoint while changing as little app code as possible, re-apply theming, and verify **design + functional fidelity per screen** against the Sendbird original. It reuses [`setup.md`](setup.md) for credentials and the rigor of [`design-matching.md`](design-matching.md); when the code migration is verified it **asks** whether to also migrate the data and hands off to [`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md).
   - **AI assistant / LLM chat** -> stay on the pre-built Chat components and route through the "AI assistants" docs rows in [`docs-map.md`](docs-map.md); the backend contract is [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) (the model runs on a backend agent, never in the app).

Bare `/stream-flutter` with no args: list the modes briefly and wait. If it is ambiguous between build and how-to, ask one question:

> Do you want me to wire this into the project, or just show the Flutter SDK pattern?

### Styling-depth flag (orthogonal to the mode)

If the request carries a **target appearance** - a screenshot, a Figma frame, "make it look like WhatsApp / iMessage / Telegram / Slack / <app>" - then **before** feature work, first run the strategy decision below:

- **Components** -> run [`design-matching.md`](design-matching.md): read its **procedure half in full** (everything above the `# Reference` divider - it may span two Reads), then Grep its Reference half per region while implementing.
- **Custom** (livestream / overlay / bespoke) -> run [`custom-ui.md`](custom-ui.md) instead - same region-by-region rigor, different mechanism.

A reference design is a checklist of regions (header, composer buttons, timestamp + read-receipt placement, bubble shape/tail, date separators, attachments, ...), and most differ from Stream's defaults **structurally**, not just by color. Decompose every region first (with its **dimensions**), then route each to theming or widget replacement ([`RULES.md`](RULES.md) "Design fidelity"). The match is **not done until you run, seed data that triggers every region, compare region by region against the reference on the real navigation path, and iterate** ([`design-matching.md`](design-matching.md) Step 5). Implement every region, the composer included - a region left at the SDK default is a FAIL, not a footnote. Work in batches: ground the pinned SDK version once, read the source you need in one pass, implement all regions, then verify on hot reload.

### Chat only: pick the UI strategy first (before any code)

Stream Chat ships **two layers**, and choosing between them is an architecture decision that dwarfs any styling choice. **Default to the pre-built components.**

| Strategy | Use when the design is... | Mechanism | Runbook |
|---|---|---|---|
| **Pre-built UI components** (`stream_chat_flutter`) - **the default** | A messenger: bubbles, or channel list -> conversation, or per-message avatar / timestamp / receipts / reactions / attachments. Social, marketplace, workplace, support, DMs. "Make it look like WhatsApp / iMessage / Telegram / Slack." | Theming (`StreamTheme` + `StreamChatThemeData`) + widget replacement (component factory `StreamComponentBuilders` / `streamChatComponentBuilders` / `StreamComponentFactory`, plus per-widget builders) | [`design-matching.md`](design-matching.md) |
| **Custom UI on `stream_chat_flutter_core`** - the exception | Not a messenger: a flat author-inline feed, an overlay / ticker on video, high-volume livestream chat (Twitch / YouTube / Kalshi), live shopping, or read-only anonymous / guest viewers vastly outnumbering posters (-> `livestream` channel type). | Your own widgets on the headless core controllers (+ the low-level client); **no** `stream_chat_flutter` widgets | [`custom-ui.md`](custom-ui.md) |

**Lean hard toward components.** The litmus test: *if theming + a few component-builder slots could get there, it is a components job* - even strong messenger reskins. Pick custom only when matching the design means replacing the message row, composer, header, AND list at once - using the SDK purely as a data source. Over-choosing custom (rebuilding a worse messenger and losing avatars / grouping / reactions / threads / attachments / typing / receipts / pickers) is the common, expensive mistake. When unsure, build the components version first. Treat "livestream" / "live shopping" as signals, not labels: a livestream app that wants a normal bubble chat panel stays on components.

**Workplace / Slack-style is a components job too.** The message row is flat and left-aligned (rounded-square avatar, author + status + timestamp line, body, bottom reaction pills, thread-reply summary) with no incoming/outgoing split - override the `messageItem` component builder (a composite slot - reproduce its sub-features) and customize the header. Workplace apps are thread-first: wire the thread summary and thread screen. Archetype details: [`design-matching.md`](design-matching.md).

The strategy also picks the **channel type and permission model** (`messaging` membership-gated vs `livestream` public + anonymous viewers) - see [`RULES.md`](RULES.md) "Permissions". If it is genuinely unclear, ask one question:

> Does this chat look like a standard messenger (channel list + bubbles), or a bespoke surface like livestream/overlay chat? It decides whether we customize the pre-built components or build custom UI on `stream_chat_flutter_core`.

---

## Step 1: Docs lookup (every request ends here)

1. Open [`docs-map.md`](docs-map.md). Find the row matching product + layer + feature -> it gives the exact `.md` URL(s).
2. If the feature is not in the map, fetch the live index for the product (table above) and pick the best-matching page.
3. **Fetch the `.md` page(s)** with WebFetch. Fetch at most 3 pages per request; if more are needed, hand the user the index URL.
4. Apply the page's guidance to the user's project: use its code where possible, adapting only to the existing app shape (navigation, state management, DI).
5. **Cite the page** you used: `Source: [Title](https://getstream.io/...)`. Never answer SDK specifics from training data - if you did not fetch it this conversation, fetch it now or say you could not find it.
6. **If the docs do not fully cover it** - an exact component-builder slot, a theme property, a default widget's sub-features, an undocumented option, real wiring - escalate to the **SDK source + example apps** at the version `pubspec.lock` pins (see "When the docs fall short" in [`docs-map.md`](docs-map.md)). Say where you found it rather than presenting it as documented. For **matching a reference design** this escalation is the norm: when you override a composite slot, read the default widget's `build()` and enumerate every sub-feature it renders so you reproduce them instead of silently dropping them.
7. **Apply best practices** - no query spam, no clients or controllers in `build`, authenticate once ([`RULES.md`](RULES.md) "Mindful API usage"), and read the vertical's best-practices page (e.g. livestream chat) before scaling.

---

## Setup (integrate / new app / migrate)

Run [`setup.md`](setup.md) once per session before feature work. It covers, in order:

1. **Project signals** - detect the Flutter project / Stream dependencies / empty dir, and the Chat **v10 version check**.
2. **Credentials** - API key + user token via the Stream CLI (or pasted), optional seed channels / posts, Feeds self-follow.
3. **Install** - the right packages with `flutter pub add`.
4. **Platform setup** - the iOS / Android / web / macOS steps the docs do not fully cover.
5. **Wire the client** - initialize once, connect the user.

Then return here for **Docs lookup** on the specific screens.

---

## What this skill carries

There are no bundled SDK reference or blueprint files - anything that used to live there now comes from the live docs via the map, which keeps the skill current and covers far more. The curated, non-doc content is:

- [`RULES.md`](RULES.md) - rules and pitfalls (build-breakers, permissions, v10 / Video / Feeds gotchas).
- [`docs-map.md`](docs-map.md) - intent -> docs page routing, plus where to read SDK source.
- [`setup.md`](setup.md) - the CLI-driven setup flow.
- [`push.md`](push.md) - Chat push + Video ringing (CallKit / FCM / Telecom), automating what the docs only describe.
- [`video-patterns.md`](video-patterns.md) - Video patterns with no docs page.
- [`design-matching.md`](design-matching.md) - reproducing a reference design with the **pre-built components**.
- [`custom-ui.md`](custom-ui.md) - the **custom** `stream_chat_flutter_core` path.
- [`sendbird-migration.md`](sendbird-migration.md) - the Sendbird -> Stream Chat migration procedure.
