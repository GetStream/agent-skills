# Stream Swift - building a CUSTOM chat UI on the low-level client (livestream / bespoke surfaces)

Some chat UIs are **not** a messenger. Livestream chat (Twitch / YouTube / Kalshi), live-shopping ticker chat, an overlay on a video, a betting feed, a high-volume "drop" room - these look nothing like channel-list + bubbles + composer, and the pre-built `StreamChatSwiftUI` components fight you the whole way. For these you **drop the components and build your own SwiftUI on the low-level `StreamChat` client + its State Layer**.

This page is the procedure for that path - the mirror image of [`design-matching.md`](design-matching.md) (which is for *customizing the pre-built components*). Run it when the decision below lands on "custom". It is grounded against StreamChat **5.5.x**; confirm every symbol against the project's pinned version (see "Grounding" at the end and [`docs-map.md`](docs-map.md) "When the docs fall short").

---

## Step 0: Decide components vs. custom - and LEAN HARD toward components

This decision is the whole ballgame. Get it wrong toward custom and you throw away avatars, grouping, reactions, threads, attachments, typing, read state, slow-mode, the composer with its attachment pickers and voice notes - hundreds of built, tested views - to rebuild a worse messenger by hand. Get it wrong toward components and you spend a day fighting the framework to force a shape it was never meant to take. **The first mistake is far more common and far more expensive, so the default is components.** Custom is the exception you justify, not the reflex.

**Default to the pre-built components ([`design-matching.md`](design-matching.md)).** Choose custom **only** when the design is genuinely not a messenger. Decide from concrete signals, not vibes:

| Signal in the screenshot / requirements | Points to |
|---|---|
| Message **bubbles** (incoming left / outgoing right), or could be styled into them | **Components** |
| A **channel list** → tap → conversation, or any 1:1 / small-group DM | **Components** |
| Per-message **avatar + name + timestamp + read receipts**, replies, reactions, attachments | **Components** |
| The ask is "make our chat look like **WhatsApp / iMessage / Telegram / Slack / Messenger / Discord DMs**" | **Components** (it's a tweak - theming + `ViewFactory` + `Styles`) |
| Workplace / support / marketplace / social / dating chat | **Components** |
| A **flat, author-inline, bubble-less** feed (name in bold then text on one wrapping line), à la live chat | **Custom** |
| **No outgoing/incoming distinction** - every message rendered identically, regardless of sender | **Custom** |
| Chat is an **overlay / ticker / sidebar** on top of video or a non-chat surface, or shares the screen with bespoke app chrome (odds, product cards, reactions raining up) | **Custom** |
| **Very high volume + ephemeral** (hundreds of msgs/min, public viewers, nothing persisted) | **Custom** |
| Anonymous / guest **read-only viewers** vastly outnumber posters | **Custom** (and `livestream` channel type) |

**The litmus test:** *if you could get there by theming + a few `ViewFactory` slots + `Styles`, it is a components job.* Only when matching the design through the components would mean **overriding the message row, the composer, the header, AND the list all at once into shapes they resist** - i.e. you're using the SDK only as a data source, not for any of its views - does custom win. When the count of components you'd have to fully replace approaches "all of them", that is the signal to drop to the client instead. When genuinely unsure, **build the components version first** - it's faster to confirm-or-reject than to discover mid-custom-build that a tweak would have done.

If still ambiguous, ask one question (from [`SKILL.md`](SKILL.md)):
> Does this chat look like a standard messenger (bubbles / channel list), or a bespoke surface like livestream/overlay chat? It decides whether we customize the pre-built components or build custom UI on the low-level client.

State the decision and the signals that drove it before writing code. If the answer is **components**, stop here and go to [`design-matching.md`](design-matching.md). The rest of this page is the custom path.

---

## Step 1: Link the right products (custom ≠ StreamChatSwiftUI)

The custom path uses **`StreamChat`** (the client + State Layer) and, optionally, **`StreamChatCommonUI`** (design tokens, `Appearance`, image loading - see Step 6). It does **not** use `StreamChatSwiftUI`. Add `StreamChat` to the target (and `StreamChatCommonUI` only if you'll use its helpers); do **not** add `StreamChatSwiftUI`, and do not `import StreamChatSwiftUI` anywhere - no `ViewFactory`, no `ChatChannelListView`, none of it applies here. (A `ViewFactory`/`ColorPalette`/`Styles` mention is the tell that you've drifted back onto the components path by mistake.)

An `ObservableObject` service that holds `@Published` state needs `import Combine` once Stream modules are imported (the re-export isn't always enough) - else "init(wrappedValue:) is not available due to missing import of defining module 'Combine'".

---

## Step 2: Pick the State Layer object - `LivestreamChat` for high volume, else `Chat`

The modern async State Layer (under `Sources/StreamChat/StateLayer/`) gives you observable state objects you render yourself. Two channel objects, created from the connected `ChatClient`:

- **`LivestreamChat`** - `chatClient.makeLivestreamChat(for: cid)`. **In-memory, no local DB**, tuned for high-volume livestream channels; documented as more performant than `Chat` but with **fewer features (no read updates, no threads)**. This is the right default for a livestream/ticker feed. It adds livestream-only controls: `pause()` / `resume()` (freeze the feed while the user scrolls up - new messages don't reflow the list), `state.skippedMessagesAmount` (a "N new messages" pill while paused), `state.isPaused`, `enableSlowMode(cooldownDuration:)` / `disableSlowMode()`.
- **`Chat`** - `chatClient.makeChat(for: cid)`. Full-feature single-channel state (messages, reads, threads, typing, members, watchers) for a bespoke surface that still needs those features (e.g. a custom-styled support console). Heavier than `LivestreamChat`.

Both expose `@MainActor` `state` (`LivestreamChatState` / `ChatState`), an `ObservableObject` with `@Published var messages: [ChatMessage]`, `@Published var channel: ChatChannel?`, members/watchers, etc. Lifecycle on both:

```swift
let livestream = chatClient.makeLivestreamChat(for: ChannelId(type: .livestream, id: "game5"))
try await livestream.get()    // fetch the most recent page (resets state.messages/channel)
try await livestream.watch()  // open the WebSocket so new messages stream into state.$messages
// send:
try await livestream.sendMessage(with: "let's go")
// paginate older:
try await livestream.loadOlderMessages()
```

(`Chat` collapses these into `try await chat.get(watch: true)`. `LivestreamChat` splits `get()` and `watch()` - call both.)

> ⚠️ These names are verified in 5.5.x source. `LivestreamChat` is recent - on an older pinned version it may not exist; then use `Chat`, or the delegate-based `ChatChannelController` (`controller.messages` + `ChatChannelControllerDelegate.didUpdateMessages`). Confirm in the pinned source before coding (Grounding, below).

---

## Step 3: Connect the client - tune it for the vertical, and pick the viewer auth

Initialize the client **once** in an owned service (`@MainActor ObservableObject`), never in a view body (see [`RULES.md`](RULES.md) "Client lifetime"). For livestream, tune the config and the connect call:

```swift
var config = ChatClientConfig(apiKey: .init(apiKey))
config.isLocalStorageEnabled = false   // no offline DB: per-message disk writes bottleneck a high-volume ephemeral feed
let chatClient = ChatClient(config: config)
```

**Viewer auth - match it to whether the viewer posts (see [`RULES.md`](RULES.md) "Permissions"):**
- Read-only viewers (the majority on a livestream): `try await chatClient.connectAnonymousUser()` - no MAU cost, can read `livestream` channels, cannot write. Do **not** mint a full per-user JWT for every anonymous viewer.
- Pre-account but can post a little: `try await chatClient.connectGuestUser(userInfo:)`.
- A real, signed-in user who posts: `try await chatClient.connectUser(userInfo:token:)` with a backend/CLI token.

**Channel type:** use **`livestream`** (public read/write without a membership gate; supports guest + anonymous). Don't make a `messaging` channel world-readable to fake it. Per [`RULES.md`](RULES.md) "Case-specific tuning", also disable read events, typing indicators, connect events, file uploads and custom messages, and enable slow mode under load - the API auto-throttles typing/read past ~100 watchers and messages past ~5/sec, so design for it. Read the livestream best-practices page ([`docs-map.md`](docs-map.md)) before scaling.

---

## Step 4: Render the feed - observe state, render newest-at-bottom

Observe the state object **directly** with `@ObservedObject` - don't re-`@Published` its `messages` into another object (that just copies a hot array on every update). The view owns the channel object via its parent (the service); the view observes its `state`:

```swift
struct LiveChannelView: View {
    let livestream: LivestreamChat
    @ObservedObject private var state: LivestreamChatState

    init(livestream: LivestreamChat) {
        self.livestream = livestream
        _state = ObservedObject(wrappedValue: livestream.state)
    }
    // render state.messages …
}
```

**Message row - this is where livestream diverges most from a messenger.** No bubbles, no left/right split, no read receipts. The common shape is **avatar + bold author name inline with the message text**, wrapping as one paragraph. Concatenate `Text` so it flows and wraps as a single block:

```swift
(Text(authorName + ":").font(.system(size: F, weight: .bold))
 + Text(" " + message.text).font(.system(size: F)))
    .foregroundStyle(textColor)              // MEASURED — see below; usually NOT pure black
    .fixedSize(horizontal: false, vertical: true)
```

Pull fields off `ChatMessage`: `.text`, `.author` (`ChatUser` → `.name`, `.imageURL`, `.id`), `.createdAt`, `.id`, `.type` (skip/branch on `.system`/`.deleted` if your design shows them). Resolve the author label as `author.name ?? author.id` (names can be nil).

> **A custom feed is still a design match - apply [`design-matching.md`](design-matching.md)'s rigor to it, do NOT eyeball.** "Render a name + text" is not the spec; the reference's exact **font size**, **weight**, **color**, **avatar size**, and **row spacing** are. Building a custom row does not exempt you from measuring - it's the opposite, because here there are no SDK defaults to fall back on, so every number is yours to get right. The recurring miss on this path is shipping `.system(size: 17)` + `.foregroundStyle(.primary)` by reflex. Instead:
> - **Font size `F`: MEASURE it** off the reference (the cap/line-height method in [`design-matching.md`](design-matching.md) "How to actually get the dimensions right" - `sips` for scale, then measure ink height in points). Live-chat text is typically **~14-15pt**, not the 17 you'll guess.
> - **Weight: measure the username and the body SEPARATELY - they are usually different weights, and the body is lighter than your reflex.** The single biggest "the font is off" cause on this path is painting the whole row in one weight (or defaulting the body to `.regular` without checking). The author name is the emphasis (often `.bold`/`.semibold`); the **message body is lighter - frequently `.light`, not `.regular`** (a measured reference: name stroke ≈2.0pt vs body stroke ≈1.0pt at 15pt - the body is **half** the name's stroke, i.e. two weight steps down). Measure each per [`design-matching.md`](design-matching.md) "Weight is its own dimension" (horizontal dark-run width = stroke thickness), then map the **stroke-to-font-size ratio** to a SwiftUI `Font.Weight` and set them independently:
>
>   | stroke ÷ font size | SF `Font.Weight` |
>   |---|---|
>   | ≈0.045-0.06 | `.light` |
>   | ≈0.07-0.08 | `.regular` |
>   | ≈0.09-0.10 | `.medium` |
>   | ≈0.11-0.12 | `.semibold` |
>   | ≈0.13+ | `.bold` |
>
>   (e.g. body 1.0pt ÷ 15pt ≈ 0.067 → between light and regular; if it reads lighter than your `.regular` render, use `.light`. Name 2.0 ÷ 15 ≈ 0.13 → `.bold`.) **Re-measure your own render's stroke and iterate** - `.regular` body often renders heavier than the reference, so stepping to `.light` is common. Don't stop at "name bold, body regular" by reflex.
> - **Text color: SAMPLE it** ([`design-matching.md`](design-matching.md) "Follow EVERY color from the reference"). It is very often a **soft near-black** (measured cores ~`#191919`/`#1C1C1C`), **NOT** pure black / `.primary` / `.label` (which paint `#000`). Sample the darkest stroke cores and use that exact value; `.primary` is a guess and usually wrong. Check whether the username and message share one color or differ.
> - **Avatar size: MEASURE the diameter.** Livestream avatars are **small** (≈20-26pt - about one text line tall), far smaller than the ~32-40pt you'd reach for. Oversized avatars are the most obvious custom-feed tell. Match the measured diameter and the small leading inset (≈4-12pt).
> - **Avatar vertical alignment + row spacing are part of the spec.** Center the avatar on the **first text line** (the name line), not the whole multi-line block. **Anti-pattern (a real bug to avoid): do NOT nudge the text down with `.padding(.top, n)` to "align" it** - that de-centers the avatar (it shoves the name below the avatar's center and only works for single-line messages). Instead **top-align the row and constrain the avatar to the first line's height so it centers within it**, e.g. `HStack(alignment: .top) { avatar.frame(height: UIFont.systemFont(ofSize: F).lineHeight); nameAndBodyText }` - the avatar centers on the first-line box while the body still wraps beneath the name. Then **verify the centering by measurement** (avatar center-Y vs the name glyphs' center-Y ≈ 0), per [`design-matching.md`](design-matching.md)'s centering rule - don't eyeball it.
>
> Then verify with the **same-scale side-by-side crop** ([`design-matching.md`](design-matching.md) Step 7): stack your rendered feed against the reference at native @3x and compare size/weight/color/avatar - numbers alone won't catch "it still looks bigger/heavier."

**Ordering + scroll.** `state.messages` follows the object's ordering; for a "newest at the bottom, above the composer" feed render oldest→newest and pin to the bottom. For modest volume, sort by `createdAt` ascending for display; for true high volume, consume the SDK's native order rather than re-sorting each update. Use `ScrollViewReader` + `.defaultScrollAnchor(.bottom)` and scroll to the last id `.onChange(of: messages.count)`. Page older history in when the user reaches the top (`loadOlderMessages()`), guarded by `state.isLoadingOlderMessages` / `state.hasLoadedAllOldestMessages`.

**High-volume niceties (LivestreamChat):** when the user scrolls up, call `livestream.pause()` so incoming messages stop reflowing the list; show a "▾ N new messages" pill from `state.skippedMessagesAmount`; on tap, `try await livestream.resume()` and scroll to bottom.

---

## Step 5: Compose + send

There is no SDK composer here - build a plain field + button and post through the state object. Keep the field state local (`@State var text`), clear it optimistically, send in a `Task`:

```swift
private func send() {
    let body = text.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !body.isEmpty else { return }
    text = ""
    Task { try? await livestream.sendMessage(with: body) }
}
```

If the design shows it, surface slow-mode cooldown from `state.remainingCooldownDuration` (disable the button + show the countdown). Anonymous viewers can't post - hide or disable the composer for them.

---

## Step 6: StreamChatCommonUI - use it when it earns its keep, not by reflex

`StreamChatCommonUI` (importable standalone alongside `StreamChat`, **without** `StreamChatSwiftUI`) carries the shared, non-component primitives:
- **`Appearance`** with `colorPalette`, `fonts` / `fontsSwiftUI`, `images` (icon glyphs), and **design tokens** (`DesignSystemTokens`: `spacingXs`/`spacingMd`, `radiusLg`/`radius3xl`, icon sizes). Use these when you want your custom surface to **align with other Stream surfaces** in the same app (e.g. a components-based channel list elsewhere) - same spacing/radius/colors.
- **`MediaLoader`** protocol (+ a `StreamMediaLoader`) for cached image loading. There is **no prebuilt async-image SwiftUI view** and **no prebuilt avatar view** here - just the loader protocol.

**Decision: reach for it only when it saves real work.** For a **self-contained** custom surface (one livestream screen with no other Stream UI), plain SwiftUI is usually cleaner and more robust: `AsyncImage` for avatars (with a colored-initial `Circle` fallback so the feed looks right while images load or offline), system fonts, your own colors. Pull in `StreamChatCommonUI` when you specifically want (a) Stream's design tokens so the surface matches a sibling components screen, (b) its image cache/pipeline, or (c) its glyphs. Don't add a dependency on its `Appearance`/`MediaLoader` for a screen that a dozen lines of stock SwiftUI render fine. (The user's steer: "use StreamChatCommonUI if you think it's necessary" - necessity, not default.)

> Verify the exact `StreamChatCommonUI` symbols in the pinned source before importing - the token/loader API is recent and moves between versions. If you only need avatars + text, you likely need none of it.

---

## Step 7: Pitfalls specific to the custom path

- **This is a single immersive screen, not a pushed channel.** There's no channel-list→push and usually no `NavigationStack` - build a **custom header view** (back button, title, live badge, actions) as an ordinary view at the top of your `VStack`. (Contrast the components path, where the header is `makeChannelHeaderViewModifier` on a real nav bar - none of that applies here.) Don't reach for `.toolbar`/nav-bar machinery for a full-bleed overlay surface.
- **A centered title MUST be bounded so it can't overlap the trailing controls.** The trap: a `ZStack` of a centered title plus a leading/trailing `HStack`, with the title given only symmetric `.padding(.horizontal, n)`. A long title (e.g. "Game 5: New York at San Antonio") then extends under the share/action icons - because symmetric padding doesn't reserve the icons' actual width. Fix with a **3-zone layout that reserves equal side widths** = the wider side cluster, so the title centers on screen and physically cannot reach either side:
  ```swift
  let side: CGFloat = 76   // ≥ the wider of {back button} and {icon cluster / sponsor}
  HStack(alignment: .top, spacing: 8) {
      backButton.frame(width: side, alignment: .leading)
      VStack(spacing: 4) { title.lineLimit(1).minimumScaleFactor(0.7); liveBadge }
          .frame(maxWidth: .infinity)                       // centered, bounded by the two side frames
      trailingCluster.frame(width: side, alignment: .trailing)
  }
  ```
  Measure the title font from the reference too (it's usually a modest ~16-17pt); `minimumScaleFactor` only covers the rare over-long title, it is not a substitute for the reserved side widths.
- **The app's own chrome is not Stream.** A betting bar, product cards, a video player, reactions - those are your app's views sitting above/below the chat. Build them as normal SwiftUI; only the message feed + composer talk to the SDK. Keep the SDK out of those files.
- **Don't hardcode the channel title from the screenshot.** Resolve it from the model: `channel.name ?? extraData["name"]` then a sensible fallback. (Many Stream apps - including this skill's test app - store the channel name under `custom`/`extraData["name"]` because top-level `channel.name` is disabled; reading only `channel.name` yields a blank title. See [`design-matching.md`](design-matching.md) "blank-name trap".)
- **Observe on the main actor; don't create state objects in a view body.** The state objects are `@MainActor`; create the `LivestreamChat`/`Chat` once in the service after connect, not per redraw (a body-created channel object re-fetches every frame - [`RULES.md`](RULES.md) "Client lifetime" / "No rendering loops").
- **`get()` resets the feed; `watch()` is what makes it live.** Calling only `get()` shows a static snapshot that never updates. Call both (or `chat.get(watch: true)` on `Chat`).
- **Re-publishing `state.messages` into your own `@Published` defeats the optimization.** Observe `state` directly. For a hot feed, an extra array copy per message is exactly the overhead `LivestreamChat` exists to avoid.
- **Mind the message `type`.** `livestream` feeds still contain `system`/`deleted` messages; render or filter them deliberately rather than drawing them as normal lines.

---

## Step 8: Verify against the reference (mandatory, same rigor as the components path)

A custom UI is not done until it builds, runs against **real seeded data**, and matches the reference region by region (see [`design-matching.md`](design-matching.md) Step 5 for the discipline - it applies here too):
1. **Seed a `livestream` channel** with realistic, varied content (multiple authors, short and long/wrapping messages, emoji) via the CLI - so the feed exercises avatar fallback, name+text wrapping, ordering, and scroll-to-bottom. (CLI shape: `UpdateUsers` to create authors, `GetOrCreateChannel type=livestream …`, `SendMessage … message='{"text":"…","user_id":"…"}'` per line, server-side.)
2. **Build once** on a pinned, already-booted simulator reusing the project's DerivedData (so the Stream packages don't re-resolve); install, launch, **wait for connect + the initial fetch to finish** before screenshotting (a too-early shot catches the "connecting" state).
3. **Measure the reference** (`sips`; iOS shots are @2x/@3x → divide to points) for the repeating elements - avatar diameter, row spacing, composer height, any app-chrome bar - and match them, don't eyeball (see [`design-matching.md`](design-matching.md) "How to actually get the dimensions right").
4. **Compare every region** - header (back/title/badge/actions/sponsor), the feed row layout, the composer, and the app chrome - PASS/FAIL, and iterate until each passes. Implement **every** region, the composer and app chrome included - no "known gaps" ([`RULES.md`](RULES.md) design-match rule applies to custom UIs too).
5. Delete any throwaway verification scaffolding before delivery.

---

## Grounding (do not guess State Layer signatures)

Per [`RULES.md`](RULES.md) "Docs discipline": confirm every symbol above against the project's **pinned** version - the State Layer API (especially `LivestreamChat`, the `*State` `@Published` surface, and `StreamChatCommonUI`'s tokens/loader) is recent and differs across versions. Read the live docs first ([`docs-map.md`](docs-map.md) "Chat - Custom UI": `client/state-layer/state-layer-overview.md`, `client/livestream-chat.md`, and the `ios-swift/livestream-best-practices.md`), then escalate to the pinned source for exact signatures:

```bash
# pinned version, then the matching checkout (verify the tag - a sibling project's DerivedData may hold a different version):
CO="<DerivedData>/SourcePackages/checkouts/stream-chat-swift/Sources/StreamChat"
grep -rn "func makeLivestreamChat\|func makeChat\|func connectAnonymousUser\|func connectGuestUser" "$CO/StateLayer" "$CO/ChatClient.swift"
sed -n '1,120p' "$CO/StateLayer/LivestreamChatState.swift"   # the @Published surface you'll bind to
```

Say where you found anything source-derived rather than presenting it as documented.
