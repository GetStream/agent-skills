---
name: stream-swift
description: "Build, integrate, and answer how-to questions for Stream Chat, Video, and Feeds in Swift / SwiftUI / UIKit / iOS apps. Routes each request to the exact official iOS docs page, fetches it live, and applies it - with a curated setup flow and iOS-specific pitfalls."
license: See LICENSE in repository root
compatibility: Requires an Xcode or Swift/iOS project for build/integrate work. Docs lookups need only network access.
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
  Bash(cat Package.swift), Bash(cat Package.resolved), Bash(cat Podfile),
  Bash(jq *),
  Bash(stream token *),
  Bash(stream chat *),
  Bash(stream api *),
  Bash(stream config *),
  Bash(stream --safe *)
---

# Stream Swift - docs orchestrator for iOS

This skill is **small on purpose**. It does not bundle SDK reference dumps - the official iOS docs are the source of truth and they cover the *entire* surface (Chat, Video, Feeds; SwiftUI and UIKit; polls, drafts, voice, AI, push, screen share, CallKit, SIP, transcriptions, moderation, and more).

Your job is to **orchestrate**: classify the request, point to the *exact* docs page, fetch it live, and apply it inside the user's project - while obeying the curated rules and pitfalls that the docs do not shout about.

**Rules (read once per session):** [`RULES.md`](RULES.md) - non-negotiable rules + iOS pitfalls. Read before writing any code.

---

## The docs convention (the core mechanism)

Every Stream docs page has a Markdown twin that coding agents can read directly: **take the page URL, drop the trailing `/`, add `.md`.**

```
https://getstream.io/chat/docs/sdk/ios/basics/integration/   ->   https://getstream.io/chat/docs/sdk/ios/basics/integration.md
```

Always fetch the `.md` variant - it is clean Markdown with verbatim code, no page chrome.

Per-product **index** pages list every doc page with its `.md` URL. Fetch these to discover or confirm a page:

| Product | Live index (always current) | Page URL shape |
|---|---|---|
| Chat (iOS SDK: UI + State Layer) | `https://getstream.io/cli/docs/chat-sdk-ios.md` | `https://getstream.io/chat/docs/sdk/ios/...md` |
| Chat (low-level client API reference) | `https://getstream.io/cli/docs/chat-ios-swift.md` | `https://getstream.io/chat/docs/ios-swift/...md` |
| Video | `https://getstream.io/cli/docs/video-ios.md` | `https://getstream.io/video/docs/ios/...md` |
| Feeds | `https://getstream.io/cli/docs/activity-feeds-ios.md` | `https://getstream.io/activity-feeds/docs/ios/...md` |

**URL grounding:** only fetch a page URL that you got from [`docs-map.md`](docs-map.md) or from a live index fetch in this conversation. Do not invent doc paths from memory - many look guessable but are wrong. If a page is not in the map, fetch the live index and pick from it.

---

## Step 0: Classify the request (always first)

From the user's words alone, resolve three things:

1. **Product** - Chat, Video, Feeds, or a combination.
2. **Framework** - SwiftUI, UIKit, or mixed (default to SwiftUI when the user is starting fresh and has not said).
3. **Mode** - one of:
   - **How-to / reference** ("how do I add reactions?", "what does CallViewModel do?", "theming") -> go straight to **Docs lookup**. No setup, no credentials.
   - **Integrate** ("add Chat to my app", "wire Video into this project") -> run **Setup** ([`setup.md`](setup.md)) then **Docs lookup** for the feature.
   - **New app** ("build a livestream app", "new SwiftUI chat app") -> **Setup** then **Docs lookup**, scoped to the requested screens.
   - **Push setup** ("add push notifications for chat", "ringing should wake the app on a call", VoIP, CallKit) -> run [`push.md`](push.md): create the Stream push provider(s) via the CLI and wire the client capabilities + code. Uses the Stream CLI like Setup.

There is also a **styling-depth** flag, orthogonal to the mode above: if the request carries a **target appearance** - an attached screenshot, a Figma link, or "make it look like WhatsApp / iMessage / Telegram / Slack / <app>" - then **before** Docs lookup, run the decomposition in [`design-matching.md`](design-matching.md). A reference design is a checklist of regions (header, composer buttons, where the timestamp + read receipts sit, bubble shape/tail, date separators, attachments...), and most of them differ from Stream's defaults *structurally*, not just by color. Do **not** stop at the wallpaper and bubble color - that is the known failure mode. Decompose every region first (capturing its **dimensions**, not just colors), then route each to one of **three axes** - theming token (`Appearance`), `Styles` modifier (`factory.styles`, for padding/insets/corner-radius/chrome), or `ViewFactory` slot (structure). Routing padding to theming, or structure to a color, is the core failure. Recurring traps the doc guards against: (1) overriding a **composite slot** (`makeMessageItemView`, the header, the composer, `makeComposerInputTrailingView`) silently **drops the sub-features the default rendered** - the incoming-message avatar, grouping, reactions, replies, status, or the send/voice/edit/slow-mode button - unless you read the default's `body` and reproduce them; (2) the **channel header modifier is applied to a divider above the composer**, so a header rendered there via `safeAreaInset`/`VStack` lands at the bottom - use `.toolbar` placements instead, and never fake the header in the app root for one channel; (3) the **composer send/voice button lives *inside* the field** (`makeComposerInputTrailingView`), so moving buttons to the right of the field needs a relayout, not just `makeTrailingComposerView`; (4) **bubble/collage padding** is `Styles` (`makeMessageAttachmentsViewModifier`), not theming. The match is **not done until you build, run, seed data that triggers every region, compare region-by-region against the reference on the real navigation path, and iterate** ([`design-matching.md`](design-matching.md) Step 5), reverting any throwaway verification scaffold - the UI must be as close to the reference as possible, not approximately like it. **Implement every region, the composer included** - never deliver a partial match with the rest labelled "known cosmetic gaps"; a region left at the SDK default is a FAIL, not a footnote. And **work in batches to stay fast**: ground the pinned SDK version + checkout once, read all the source you need in one pass, implement all regions, then build once on a persistent `-derivedDataPath` against one pinned simulator - don't rebuild-and-screenshot after every small edit (see [`design-matching.md`](design-matching.md) "Work in batches").

If product and framework are explicit, do not probe - proceed. If genuinely ambiguous between "wire it in" and "just explain", ask one short question:

> Want me to wire this into the project, or just map the docs page and pattern?

### Chat only: pick the UI strategy first (before any code)

Stream Chat ships **two layers**, and the pre-built UI is not the right answer for every vertical. Decide from the app's vertical before routing:

| App vertical | UI looks like... | Strategy |
|---|---|---|
| Social / community chat, marketplace, workplace (Slack-like), support, DMs | A standard messenger: channel list + message bubbles + composer | **Pre-built UI components** (`StreamChatSwiftUI` / `StreamChatUI`), customized via ViewFactory + theming |
| Livestream chat (Twitch, YouTube, Kalshi), live shopping, overlay/ticker chat, bespoke surfaces | Nothing like a messenger - custom overlays, ephemeral high-volume feeds | **Custom UI on the low-level client + State Layer** - do **not** use the pre-built components |

The pre-built components are built to be *customized*, but for a livestream-style UI that means fighting them. There, drop to the low-level `StreamChat` client and its State Layer and build views from scratch. Route accordingly via [`docs-map.md`](docs-map.md) (it has separate "Pre-built UI" and "Custom UI" sections for Chat).

The vertical also picks the **channel type and permission model** (e.g. `messaging` membership-gated for social/marketplace vs `livestream` public + anonymous viewers) - see [`RULES.md`](RULES.md) "Permissions". Decide both axes together.

If the vertical is unclear, ask one question:

> Does this chat look like a standard messenger (channel list + bubbles), or a bespoke surface like livestream/overlay chat? It decides whether we use the pre-built components or build custom UI on the low-level client.

---

## Step 1: Docs lookup (every request ends here)

1. Open [`docs-map.md`](docs-map.md). Find the row matching product + framework + feature -> it gives the exact `.md` URL(s).
2. If the feature is not in the map, fetch the live index for the product (table above) and pick the best-matching page.
3. **Fetch the `.md` page(s)** with WebFetch. Fetch at most 3 pages per request; if more are needed, hand the user the index URL.
4. Apply the page's guidance to the user's project: use its code verbatim where possible, adapt only to fit the existing app shape (lifecycle, navigation, package manager).
5. **Cite the page** you used: `Source: [Title](https://getstream.io/...)`. Never answer SDK specifics from training data - if you did not fetch it this conversation, fetch it now or say you could not find it.
6. **If the docs do not fully cover it** - a specific UI customization, an exact `ViewFactory` signature, an undocumented option, real wiring - escalate to the **SDK source code + example apps** (see "When the docs fall short" in [`docs-map.md`](docs-map.md)). The source is the final source of truth; read the version the project actually pins, and say where you found it rather than presenting it as documented. For **matching a reference design**, this escalation is the norm, not the exception: most of the ~100 `ViewFactory` slots are undocumented, so read `ViewFactory.swift` (every slot) + `DefaultViewFactory.swift` (what each renders) + the relevant `Options/*.swift` - [`design-matching.md`](design-matching.md) routes each region to its slot and shows the grep commands. When you override a **composite** slot, also read the default *view* it returns (e.g. `MessageContainerView` for `makeMessageItemView`) and enumerate every sub-feature it renders, so you reproduce them instead of silently dropping them.
7. **Apply best practices.** Use the API mindfully - no `queryChannels` spam, no rendering loops, authenticate once - per [`RULES.md`](RULES.md) "Mindful API usage", and read the vertical's best-practices page (e.g. livestream) before scaling.

---

## Setup (integrate / new app only)

When the mode is integrate or new app, run [`setup.md`](setup.md) once per session before feature work. It covers, in order:

1. **Project signals** - detect Xcode project / Swift package / Podfile / empty dir.
2. **Credentials** - API key + user token via the Stream CLI (or user-pasted), optional seed channels.
3. **Install** - add the right Stream packages with the project's existing package manager.
4. **Wire the client** - initialize once at app launch, connect the user.

Then return here for **Docs lookup** on the specific screens.

If there is **no iOS project at all**, do not scaffold one from the CLI - tell the user to create the app in Xcode first, then continue.

---

## What this skill no longer carries

There are no `references/*.md` blueprint files. Anything that used to live there now comes from the live docs via the map. This keeps the skill current automatically and covers far more than the old bundled set. The only curated, non-doc content is [`RULES.md`](RULES.md) (rules + pitfalls), [`setup.md`](setup.md) (the CLI-driven setup flow), [`push.md`](push.md) (the CLI + code runbook for push / VoIP / CallKit, which automates what the docs only describe), and [`design-matching.md`](design-matching.md) (the procedure + region->`ViewFactory`-slot map for reproducing a reference screenshot / design, which the docs scatter across many pages or omit).
