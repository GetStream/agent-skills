# Sendbird → Stream Chat iOS migration

A generic, repeatable procedure for migrating an **iOS app** (Swift / SwiftUI / UIKit)
from the **Sendbird Chat SDK** to **Stream Chat**. It is written to work on *any*
Sendbird project regardless of how the SDK was integrated — behind a service/wrapper,
directly in views, via a coordinator/singleton, or as spaghetti. Do **not** assume a
specific symbol exists (no "find `ChatService`"); instead **detect the shape** of the
integration and re-implement it in place.

Golden rule: **change as little application code as possible.** Preserve the app's
architecture, navigation, and public types. Swap what's *inside* the SDK touchpoints,
not the touchpoints themselves.

---

## 0. Detect the integration shape (do this first)

Before changing anything, map the existing Sendbird footprint:

```bash
# Which Sendbird products/symbols are used, and where?
grep -rn "import Sendbird" .            # SendbirdChatSDK / SendbirdUIKit / SendbirdSwiftUI
grep -rn "SBU\|SendbirdUI\|SendbirdChat\|GroupChannel\|OpenChannel" --include=*.swift .
# Package pins:
cat *.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved
```

Classify each touchpoint into one of these patterns and migrate it accordingly:

| Pattern found | How to migrate |
|---|---|
| **Wrapper / service** (a protocol or class that hides the SDK, e.g. `connect()`, `currentUser`) | Keep the protocol/public API **unchanged**. Re-implement the concrete type against Stream. Callers don't change. |
| **View model** (`@Observable` / `ObservableObject` calling the SDK directly) | Keep the VM's public surface (published state, methods). Replace SDK calls inside. |
| **Coordinator** (owns a `UINavigationController` / nav stack) | Keep the coordinator. Replace the VC it builds. |
| **Singleton manager** (`X.shared`) | Keep the singleton + its method signatures. Replace the SDK calls. |
| **Direct / inline** (SDK views & calls straight in a `View`/`VC`) | Swap the SDK view type and calls in place; keep surrounding layout/navigation. |
| **Redux / unidirectional** (Store + State + Action + pure reducer; effects re-dispatch) | Keep the store shape. The SDK touchpoints are **effects** (connect, send) and **derived values** (a `ChannelListQuery` computed from state). Effects do the async Stream work outside the reducer and re-dispatch result actions; the reducer stays pure. The view dispatches actions and renders `state` (e.g. a segmented filter writes via `dispatch(.selectScope)` and the list query is derived from `state.scope`). |
| **Spaghetti** (SDK calls scattered, no boundary) | Don't refactor the whole app. Migrate file-by-file; optionally introduce a *thin* boundary only where it reduces churn. Note it; don't rewrite unrelated code. |

The target UI framework is a **choice, not dictated by the source**: a Sendbird **UIKit** screen can migrate to Stream **SwiftUI** (`ChatChannelListView`/`ChatChannelView` + a `ViewFactory`) and vice-versa — pick whichever the team is standardizing on. Cross-framework (Sendbird UIKit → Stream SwiftUI) is a first-class option, not a workaround.

Also note the **shared infrastructure** (SDK init/bootstrap, credentials/config, demo-data
seeding). That layer always changes; the integration-specific abstractions above should not.

---

## 0.5 Design & functional fidelity (read this every time — it's the part that's always wrong)

Swapping the SDK so the app *builds and connects* is the easy 80%. The migration is judged on
the **last 20%: does each screen look and behave like the Sendbird original?** Those gaps are
almost never visible from the channel **list** — they live **inside the chat screen** (bubbles,
alignment, header buttons, composer, custom cards). If you only look at lists and call it done,
you will ship a wrong-looking app. Three habits prevent this:

**0. The source app IS the benchmark — build it first if it doesn't exist.** Never design a
migrated screen from scratch. If you're adding a *new* integration/use-case that has no Sendbird
original yet, **build the Sendbird version first** (in the source SDK), run and screenshot it, and
treat that as the spec — then migrate to Stream to match it. Going straight to the Stream version
means you're inventing a design with nothing to check against, and it will be wrong. (Use a git
worktree at the Sendbird baseline to build the reference without disturbing the Stream work.)

**1. Derive every value from the source — never guess, never accept Stream's default.**
For each screen, the design spec already exists: it's the Sendbird theme + the Sendbird SDK's
default behavior + (if runnable) the original app on screen. Extract concrete values:
- Colors: read the source theme (`SBUColorSet.primaryMain`, custom `SBUTheme`/`SBUColorSet`
  overrides, per-integration accent). The outgoing bubble is usually `primaryMain` **solid**
  with **white** text; incoming is light gray. Stream's defaults are a *pale tint of accent* —
  so if you don't set them explicitly, they're wrong. Compute Stream colors **from** the source
  values; don't approximate "a blue."
  - When you hand-build a view (a custom cell, card, header), pull the color of **each element**
    from the source theme — text included, not just backgrounds. Sendbird uses **emphasis tiers**
    (`onLight/onDark` × High/Mid/Low = ~88% / 50% / 38% opacity) and specific `SBUFontSet` sizes/
    weights per element. Match the tier per element: copying the layout but making every label
    full-strength white/black inverts the intended hierarchy (e.g. author should be *quieter* than
    the message). Don't reach for the *target* SDK's semantic palette (`textPrimary`, etc.) as a
    stand-in; it won't carry the source's tiering.
  - Some elements use the **secondary** color, not text/primary: a Sendbird **open-channel author
    name is `SBUColorSet.secondaryLight` (a green, #69C085 in dark)** — not a grey text tier and
    not `primaryMain`. Verify which palette slot an element actually uses; don't assume.
  - **Match what RENDERS, not what the theme code intends — the theme source can lie.** A
    per-integration `apply()` may set `ColorSet.primaryMain` and still not re-color the thing you
    expect: in the **SwiftUI** SDK, setting `ColorSet.primaryMain` does **not** repaint the message
    bubble — the outgoing bubble stays the SDK default purple **#8C45CC** regardless. (The **UIKit**
    SDK *does* propagate `SBUColorSet.primaryMain` to the bubble via `SBUTheme.set`.) So a theme file
    that says "indigo" can render purple. **Confirm every color against the running source app and
    pixel-sample it** (don't eyeball, don't trust the constant): screenshot the source, then
    `Image.open(png).getpixel()` / count the dominant saturated color, and set the Stream value to
    that exact hex. Read `SBUColorSet.swift`/`SBUFontSet.swift`/`SBUTheme.swift` (source at
    `github.com/sendbird/sendbird-uikit-ios`, `Sources/Theme/`) to *name* the value, but let the
    rendered pixel be the source of truth.
    - **Caveat — rendered ≠ always intended.** When the rendered color *contradicts the
      integration's own accent* (e.g. the bubble renders the SDK-default purple while the whole
      integration is branded indigo), that's likely an SDK quirk, not the design. Don't blindly
      replicate the quirk: prefer **brand consistency** (use the integration's accent for the
      bubble) and, if it's ambiguous, **ask** rather than guess — getting the same element "wrong"
      twice is the signal to stop guessing and confirm the intended color with the user.
- Layout/behavior: Sendbird's defaults are the spec. A **group channel** header shows a
  channel-**info** button on the right (not an avatar). An **open channel** lays messages out
  **left-aligned with the author name on top** (no my-side/their-side bubble split). The composer
  "+" opens an attachment/menu. Reproduce these, don't leave Stream's different defaults.

Then **classify the *kind* of difference** — it tells you which knob to reach for, and using the
wrong one is why a screen "looks migrated" but is still off:
- **Recolored** (same layout, different colors) → set the `Appearance` **palette** (§6).
- **Realigned** (same cell, moved side) → a **config flag** (e.g. `messageListAlignment`) (§4).
- **Rearranged** (the cell/item itself is restructured — elements reordered, bubble removed,
  author moved) → a flag **cannot** express this. **Override the item `ViewFactory` slot** with a
  custom view (`makeMessageItemView` for the whole message row) (§4/§6).
A flag flip when the answer is a custom item view is the single most common "still looks like
Stream, not Sendbird" miss.

**2. Inspect EVERY screen variant, and inside it run this checklist.** For each integration,
open the list **and the chat**, with at least one **incoming and one outgoing** message visible:

| Check | Common failure |
|---|---|
| **Outgoing** bubble **background** | left as Stream's pale accent tint instead of source's solid color |
| **Outgoing** bubble **text color** | dark/illegible on a solid bubble — set independently of background; **UIKit ignores `chatTextOutgoing`** (see §6) |
| **Incoming** bubble background + text | not matched to source gray |
| **Message alignment** | open/community channel rendered as normal split bubbles instead of left-aligned (§4) |
| **Message cell *layout*** | items **rearranged** in the source (e.g. author-on-top, no bubble) but you only flipped an alignment flag — a config flag can't restructure a cell; **override `makeMessageItemView`** (§4) |
| **Header right-side button** | missing the channel-**info** button a Sendbird group header has |
| **Composer button inventory** | Stream shows buttons the source doesn't (a **GIF/commands** button, a **voice/mic** button) or the wrong leading icon. Match it 1:1 (see §6 *Composer parity*) — Sendbird's leading button is a **"+"** (not a paperclip), there is **no GIF/commands** button, and the **mic** appears **only** where the source enables voice (per-integration). |
| **Composer suggestions** | quick-reply chips placed *outside* the composer instead of inside it (§6) |
| **Send-button / icon tint** | composer "+"/send left default instead of the integration accent |
| **Avatars** | invented colorful/gradient avatars where the source shows the **default grey person-circle** (no profile images set). Match the source's avatar shape, style, and size. |
| **Avatar shown in 1:1 / bot chat** | source **hides** the sender avatar (e.g. a concierge/support bot chat) but Stream shows one — hide it to match. |
| **Custom cards/widgets** | render as plain text, an empty bubble, or **awkwardly nested inside a default bubble** (clear the bubble bg, §6) |
| **Custom-view icons** (UIKit) | SF Symbol not shown — needs explicit `preferredSymbolConfiguration` + a sized frame (§6) |
| **Unread badge color** | left red; Sendbird tints it with the accent (UIKit `accentError`) |

**3. Verify on the real chat screen — and you can't tap in the simulator.** A list screenshot
hides every bubble/composer bug. Add a **temporary deep-link env hook** so you can open a
specific chat directly and screenshot it, e.g.:
```swift
if let raw = ProcessInfo.processInfo.environment["DEMO_CHANNEL"], let cid = try? ChannelId(cid: raw) {
    // show ChatChannelView(channelController: client.channelController(for: cid)) directly
}
```
Launch with `SIMCTL_CHILD_DEMO_CHANNEL=messaging:weekend-plans xcrun simctl launch …`. **Seed an
outgoing message** (server-side, `SendMessage … user_id=<current user>`) before shooting — an
incoming-only chat hides the outgoing-bubble color/text bug, which is the most common one. Compare
each shot against the Sendbird original (or its theme values) and iterate until they match.

---

## 1. Packages (SPM)

Remove the Sendbird packages and add Stream's. Stream uses **one core + per-UI-framework** packages.

| Remove (Sendbird) | Add (Stream) |
|---|---|
| `sendbird-chat-sdk-ios` (`SendbirdChatSDK`) | `github.com/GetStream/stream-chat-swift` → product **`StreamChat`** (core/low-level) |
| `sendbird-uikit-ios[-spm]` (`SendbirdUIKit`) | `github.com/GetStream/stream-chat-swift` → product **`StreamChatUI`** (UIKit) |
| `sendbird-swiftui-ios` (`SendbirdSwiftUI`) | `github.com/GetStream/stream-chat-swiftui` → product **`StreamChatSwiftUI`** (SwiftUI) |

Notes:
- **Link `StreamChat` explicitly** on the target. `StreamChatSwiftUI` does *not* re-export it; without it `import StreamChat` fails ("No such module 'StreamChat'").
- A SwiftUI app needs `StreamChat` + `StreamChatSwiftUI`. A UIKit app needs `StreamChat` + `StreamChatUI`. An app with **both** (common in these multi-variant projects) links all three — that's fine, they share one `ChatClient`.
- Stream resolves a transitive `StreamCore` package automatically.
- Pin the SwiftUI + core packages to the **same minor** (they ship in lockstep, e.g. `5.5.x`). `stream-chat-swiftui` declares `stream-chat-swift from: <same version>`.
- Info.plist usage strings carry over conceptually: Stream wants `NSPhotoLibraryUsageDescription`, `NSPhotoLibraryAddUsageDescription`, `NSCameraUsageDescription`.

---

## 2. Initialization & authentication

This is the biggest conceptual shift.

| Sendbird | Stream |
|---|---|
| `SendbirdChat.initialize(params:)` / `SendbirdUI.initialize(applicationId:)` | `ChatClient(config: ChatClientConfig(apiKey: .init(apiKey)))` |
| **Two UI layers each init separately** (`SendbirdUIKit.SendbirdUI` + `SendbirdSwiftUI.SendbirdUI`) | **One `ChatClient`** for SwiftUI *and* UIKit. SwiftUI also needs the `StreamChat` wrapper object created once before any view renders. |
| `SBUGlobals.currentUser = SBUUser(userId:)` then `SendbirdUI.connect { }` | `chatClient.connectUser(userInfo: UserInfo(id:name:imageURL:), token: token) { }` |
| **Test mode**: connecting with any userId auto-creates that user, no token | **Always token-authed**: `Token` (dev token from CLI/`getstream token <id>` for local; backend-issued in production). No "anyone can be anyone". |
| App ID is the only credential | API **key** (client-safe) + per-user **token**. Never ship the API **secret**. |

The two Sendbird bootstraps usually **collapse into one** Stream stack object:

```swift
@MainActor
final class StreamChatStack {
    static let shared = StreamChatStack()
    let chatClient: ChatClient
    private var streamChat: StreamChat?
    private var connectTask: Task<Void, Error>?

    private init() {
        var config = ChatClientConfig(apiKey: .init(Config.apiKey))
        config.isLocalStorageEnabled = true
        chatClient = ChatClient(config: config)
    }
    // Create the SwiftUI wrapper before any Stream view renders (App.init).
    func setUp(appearance: Appearance? = nil) {
        guard streamChat == nil else { return }
        streamChat = StreamChat(chatClient: chatClient, appearance: appearance ?? Appearance())
    }
    func connect() async throws {
        if let connectTask { try await connectTask.value; return }
        let task = Task<Void, Error> { [chatClient] in
            let token = try Token(rawValue: Config.userToken)
            try await withCheckedThrowingContinuation { c in
                chatClient.connectUser(userInfo: .init(id: Config.userId, name: Config.userName), token: token) {
                    if let e = $0 { c.resume(throwing: e) } else { c.resume() }
                }
            }
        }
        connectTask = task
        try await task.value
    }
}
```

If the app had separate SwiftUI/UIKit bootstraps, point both at this single stack; the
integration-specific connect call sites (`X.connect()`) keep the same shape.

---

## 3. UI components

### SwiftUI

| Sendbird (`SendbirdSwiftUI`) | Stream (`StreamChatSwiftUI`) |
|---|---|
| `GroupChannelListView()` | `ChatChannelListView(channelListController:title:embedInNavigationView:)` |
| `GroupChannelView(provider: GroupChannelViewProvider(channelURL:))` | `ChatChannelView(channelController: chatClient.channelController(for: cid))` |
| built-in nav + `NavigationView(.stack)` host required | `ChatChannelListView` **embeds its own** nav — pass `embedInNavigationView: false` to host it in your own navigation. Never wrap it in `NavigationStack`/`NavigationView`. |
| `.headerItem { .init().titleView { } }` / `.listItem { .init().channelName { } }` view converters | a custom `ViewFactory` (see §6) |
| channel-list filtered by member implicitly | `ChannelListQuery(filter: .containMembers(userIds: [currentUserId]))` |

### UIKit

| Sendbird (`SendbirdUIKit`) | Stream (`StreamChatUI`) |
|---|---|
| `SBUGroupChannelListViewController()` / `(channelListQuery:)` | `ChatChannelListVC.make(with: chatClient.channelListController(query:))` |
| `SBUGroupChannelViewController(channelURL:)` / `(channel:)` | `let vc = ChatChannelVC(); vc.channelController = chatClient.channelController(for: cid)` |
| `SBUOpenChannelListViewController()` (open channels) | `ChatChannelListVC` with `ChannelListQuery(filter: .equal(.type, to: .livestream))` |
| `SBUOpenChannelViewController(channelURL:)` | `ChatChannelVC` on a `livestream` channel |
| `vc.leftBarButton` / `headerComponent?.leftBarButton` | standard `vc.navigationItem.leftBarButtonItem` |
| wrap in `UINavigationController` for a representable | same — `UINavigationController(rootViewController: vc)` |

---

## 4. Channels

| Sendbird concept | Stream concept |
|---|---|
| **Group channel** (members) | `messaging` channel type (membership-gated) |
| **Open channel** (public, large audience) | `livestream` channel type (public read/write, anonymous/guest viewers) |
| `channelURL` (string id) | `ChannelId(type: .messaging, id: "...")` (type + id) |
| `GroupChannelCreateParams` + `GroupChannel.createChannel(params:)` | `chatClient.channelController(createChannelWithId: cid, name:, members:, extraData:)` then `synchronize()` |
| distinct channel (`isDistinct = true`, hash of members) | `channelController(createDirectMessageChannelWith: Set<UserId>)` (auto-id) **or** a stable `createChannelWithId` |
| `GroupChannelListQuery` filters | `ChannelListQuery(filter:sort:pageSize:)` with `Filter<ChannelListFilterScope>` (`.containMembers`, `.equal(.type, to:)`, `$in`, …) |
| empty channels excluded from list by default | Stream lists empty channels too (no starter-message workaround needed) |

Pick the channel **type** by vertical: `messaging` for DMs/support/team, `livestream`
for community/open/live-shopping, `team` for Slack-like. The type carries default
permissions — start from it instead of hand-rolling.

**Open-channel message *layout* (the Sendbird-open-channel look).** This is the trap that looks
done but isn't. Sendbird open channels don't just left-align the bubbles — the **message cell is
a different shape**: a small avatar, the author name in **bold** with a timestamp on top, and the
message text **plainly underneath with NO bubble**, the whole row left-aligned full width. There
are two levels of fix, and **a config flag is not enough**:

- **Config only moves the bubbles.** `MessageListConfig(messageListType: .livestream,
  messageListAlignment: .leftAligned)` (set via `InjectedValues[\.utils].messageListConfig`,
  restored on leave) makes every message left-aligned — but it still renders the **default
  bubbled cell** with the avatar *below* the text. If the original simply left-aligns normal
  bubbles, stop here.
- **A rearranged cell needs a custom item view.** When the cell layout itself is restructured
  (author-on-top, no bubble — the Sendbird open-channel cell), the config can't express that.
  **Override `makeMessageItemView(options:)`** and return your own row (avatar + bold author +
  timestamp, text below, no bubble background, `.frame(maxWidth: .infinity, alignment: .leading)`).
  This is the right call whenever *"the items are rearranged"* — reach for a custom item view, not
  a flag. (It intentionally drops the my-side/their-side split and the default bubble chrome,
  which open channels don't have. You also lose long-press/reactions on that cell — fine for an
  open channel; reproduce them only if the source had them.)

  **Build the custom row from the source SDK's *exact* cell theme — colors AND fonts — not the
  target's semantic palette or an eyeball guess.** Read the source's cell theme values. Sendbird's
  dark open-channel cell (`SBUMessageCellTheme.dark` + `SBUFontSet`) is, verbatim:
  - author name → `ondark02` = **white @ 50%**, font `caption1` = **12pt bold**
  - message text → `ondark01` = **white @ 88%**, font `body3` = 14pt regular
  - timestamp → `ondark03` = **white @ 38%**, font `caption4` = 11pt regular
  - profile image 26pt.

  The point isn't these specific numbers — it's that the design has a deliberate **emphasis
  hierarchy** (message brightest, author muted, timestamp faintest). If you make the author as
  bright as the message (e.g. both `textPrimary`/white), the hierarchy inverts and it reads wrong
  even though every element is "present." Sendbird encodes this with `onDark/onLight` +
  High/Mid/Low-Emphasis tiers; pull the actual tier per element. Sendbird theme source lives at
  `github.com/sendbird/sendbird-uikit-ios` under `Sources/Theme/` (`SBUColorSet.swift`,
  `SBUFontSet.swift`, `SBUTheme.swift`).

  **Grouping gotcha when you build the custom row:** `options.showsAllInfo` marks the message
  Stream shows full info on, but Stream groups **avatar-at-bottom** — `showsAllInfo` (`firstMessageKey`)
  is true for the **newest** message of a same-author run, the *opposite* of Sendbird's
  author-on-top. Keying your author header off `showsAllInfo` tucks the *older* message of a run
  under the previous author (visible misattribution). Inverting it needs neighbour lookup the
  factory doesn't have, so the robust choice is to **show the author header on every message** —
  unambiguous, and a normal open-channel look.

Gotcha: Stream only shows the **author name** (in the *default* bubbled cell) when
`channel.memberCount > 2` (`MessageViewModel.authorAndDateShown`). A public open channel seeded
with **0 members** shows avatars but no names — add several members when seeding community
channels. (A custom `makeMessageItemView` renders the author yourself, so it's unaffected — but
seed members anyway so the header member count looks real.) List open channels with a query
**not** scoped to your membership: `ChannelListQuery(filter: .equal(.type, to: .livestream))`.

---

## 5. Messages & custom attachments

| Sendbird | Stream |
|---|---|
| `channel.sendUserMessage("text")` | `channelController.createNewMessage(text: "text")` |
| `UserMessageCreateParams` + `customType` + `data` (JSON **string**) | `createNewMessage(text:extraData:)` where `extraData: [String: RawJSON]` (structured), or a **custom attachment** (`AnyAttachmentPayload`) |
| read `message.customType` / `message.data` | read `message.extraData["key"]` (a `RawJSON`), or `message.attachments(payloadType:)` |
| file/image via `sendFileMessage` | `createNewMessage(attachments: [try .init(localFileURL:)])` |

**Custom attachment / structured payload.** This is the part most likely to *look* migrated
but render as plain text. Do it as a real **custom attachment**, and mind three traps:

1. Define a custom `AttachmentPayload` and send it as an attachment (NOT message `extraData`):
   ```swift
   struct SupportCard: AttachmentPayload {
       static var type: AttachmentType { .init(rawValue: "support_card") }
       let kind: String; let title: String; let subtitle: String
   }
   channelController.createNewMessage(text: card.title, attachments: [AnyAttachmentPayload(payload: card)])
   ```
   Why not `extraData` + `makeMessageTextView`? Because **`makeMessageTextView` only fires for
   messages with no attachments**; and the message pipeline routes attachments elsewhere.

2. **Register a resolver or the custom slot is never called.** Custom attachments only reach
   `makeCustomAttachmentViewType` if `MessageTypeResolving.hasCustomAttachment` returns true.
   `MessageTypeResolver` is **not subclassable** — conform to the protocol and delegate the
   standard checks to a `MessageTypeResolver()` instance, overriding only `hasCustomAttachment`.
   Register it at init: `StreamChat(chatClient:utils: Utils(messageTypeResolver: MyResolver()))`.
   Then render: `func makeCustomAttachmentViewType(options:) -> some View { … options.message.attachments(payloadType: SupportCard.self) … }`.

3. **The server strips unknown custom fields** (both message `extraData` and attachment
   custom fields come back as `custom: {}`). Only KNOWN attachment fields survive — so map your
   payload's fields onto `title` / `text` via `CodingKeys` (`case subtitle = "text"`) and make
   `init(from:)` resilient (defaults for anything that may be dropped). Verify with
   `getstream api QueryChannels --request '{"filter_conditions":{"cid":"..."},"state":true}'`.

4. **Don't send right after `synchronize()`** — it races the local store (`ChannelDoesNotExist`
   / `ChannelNotCreatedYet`). For an **existing** channel use `channelController(for: cid)` (NOT
   `createChannelWithId`, which leaves an existing channel "not created"); let it settle before
   the first programmatic send. User-initiated sends are fine (channel is loaded by then).

> Client `createNewMessage` is the reliable write path for custom data; server-side CLI/REST
> seeding drops custom fields, so seed cross-user/agent demo content but post custom-attachment
> messages from the client.

---

## 6. Theming & view customization

| Sendbird | Stream |
|---|---|
| `SBUColorSet.primaryMain` (global, mutable) | `Appearance.colorPalette.accentPrimary` (+ `navigationBarTintColor`, `chatBackgroundIncoming/Outgoing`) |
| `SBUFontSet.body3` | `Appearance.fontsSwiftUI.body` (SwiftUI) / `Appearance.fonts` (UIKit) |
| `SBUIconSet.iconCreate` | `Appearance.images.composerSend` etc. |
| `SBUTheme.set(theme:)` / `set(colorScheme:)` to regenerate | set the palette on the `Appearance` (no regenerate step) |
| `ColorSet.restoreDefaultColors()` | re-assign a fresh palette |

Where to set it:
- **At init**: `StreamChat(chatClient:appearance:)` (SwiftUI) / `Appearance.default` (UIKit).
- **Per-screen at runtime** (the analog of Sendbird's global mutable `SBUColorSet`, e.g. a
  different accent per integration):
  - SwiftUI: write through the injected palette —
    `var c = InjectedValues[\.colors]; c.accentPrimary = color; InjectedValues[\.colors] = c`
  - UIKit: `Appearance.default.colorPalette.accentPrimary = color` (read when a VC is created).
  - Keep SwiftUI vs UIKit `Appearance` in **separate files** — both modules export an
    `Appearance` type; importing both in one file is ambiguous.

**View customization** — Sendbird's view-converter closures map to Stream's `ViewFactory`:

| Sendbird converter | Stream `ViewFactory` slot |
|---|---|
| channel-list `headerItem.titleView` | `makeChannelListHeaderViewModifier` (or `ChatChannelListView(title:)` for a plain title) |
| channel-list `listItem.channelName/.channelPreview/.coverImage` | `makeChannelListItem` (composite — read the default first, see below) |
| channel `headerItem.titleView` | `makeChannelHeaderViewModifier` *(applied to a divider above the composer — customize the header with `.toolbar`, not inside this modifier)* |
| message `listItem.userMessageView` (text/content only) | `makeMessageTextView` — **delegate to `DefaultViewFactory.shared.makeMessageTextView(options:)` for the non-custom case** so you don't lose default formatting |
| message cell **fully rearranged** (e.g. open-channel author-on-top, no bubble) | `makeMessageItemView(options:)` — replace the whole row. Use this, not a config flag, whenever the *layout* differs (see §4). |
| input `addButton` (custom attachment menu) | `makeLeadingComposerView` (the leading "+"), **or** a `.toolbar` menu that calls `createNewMessage(extraData:)` |
| input **quick-reply / suggestion chips** | **inside the composer** → `makeComposerInputView` (rebuild `ComposerInputView` with the chips in a `VStack` above it). A wrap via `makeMessageComposerViewType` puts them *outside/above* the whole bar — usually wrong; chips belong attached to the input. |
| `senderProfileImage` | `makeMessageAvatarView` / custom-avatar guide |

Minimal `ViewFactory`:
```swift
final class SupportFactory: ViewFactory {
    @Injected(\.chatClient) var chatClient
    var styles = RegularStyles()
    static let shared = SupportFactory()
    private init() {}

    @ViewBuilder
    func makeMessageTextView(options: MessageTextViewOptions) -> some View {
        if let card = SupportCard(extraData: options.message.extraData) {
            SupportCardView(card: card)                                   // custom
        } else {
            DefaultViewFactory.shared.makeMessageTextView(options: options) // default
        }
    }
}
// pass it in: ChatChannelView(viewFactory: SupportFactory.shared, channelController: ...)
```
**Composite-slot warning:** overriding `makeMessageItemView` / `makeChannelListItem` / the
composer drops every sub-feature the default rendered (avatar, grouping, reactions, status…).
Read the default view's `body` in the SDK source and reproduce them, or override a narrower slot.

### Composer parity — inventory the source composer button-by-button

The composer is where Stream's defaults differ most from Sendbird's, and the gaps are obvious to
anyone comparing screens. **Don't accept Stream's default composer** — make its button set match
the source's exactly, per integration:

- **Leading button.** Sendbird's is a **"+"** tinted with the accent (the attachment/menu trigger).
  Stream defaults to a **paperclip** — swap it for a "+" (`makeLeadingComposerView`) and tint it.
- **Remove what the source doesn't have.** Sendbird (default config) shows **no GIF/giphy** and
  **no slash-command** button. Stream may show a commands/attachment affordance you must strip.
  Set `Components.default.messageComposerVC`/composer options or override the composer view to drop
  trailing command/giphy buttons.
- **Voice/mic is per-integration.** Sendbird only shows the mic when that integration enabled it
  (`SendbirdUI.config.groupChannel.channel.isVoiceMessageEnabled`). Check each one — e.g. a DM and a
  team channel may enable it while a support/bot/open channel does not — and show/hide Stream's
  voice recording affordance to match. Don't show a mic where the source has none (a common
  complaint), and don't drop it where the source has one.
- **Tint everything** (leading "+", send) with the integration accent, not Stream's default blue.
- **Match placement of extras**: quick-reply/suggestion chips go *inside* the composer (above the
  input), not floating above the whole bar.
- **A custom leading "+" must stay vertically centered with the text field.** The composer row is
  laid out `HStack(alignment: .bottom)`, so a fixed-size custom button (`.frame(width: 36, height:
  36)`) sinks to the bottom and reads as misaligned. Match the **default** button's box so it lands
  in the same place: `Image(...).frame(width: tokens.iconSizeMd, height: tokens.iconSizeMd)
  .padding(tokens.buttonPaddingYLg)` (pull `@Injected(\.tokens)`); the default's padding is exactly
  what centers it on a single line. Don't eyeball a frame.

Inventory the source composer left-to-right and right-to-left and reproduce exactly that set — no
more, no less.

### Avatars — match the source's style, don't invent

If the source app shows the **default grey person-circle** (no profile images uploaded), Stream
must show the same — not a colorful gradient/initials avatar you made up. Match shape (circle vs
rounded-square), size, and the default glyph. And where the source **hides** the avatar entirely
(1:1 support/concierge bot chats often do), hide it in Stream too.

### Message bubble colors — set background AND text, and know SwiftUI ≠ UIKit

Set **four** values, not one (Stream derives nothing from the accent for bubbles):
`chatBackgroundOutgoing`, `chatTextOutgoing`, `chatBackgroundIncoming`, `chatTextIncoming`.
A solid Sendbird-style outgoing bubble needs `chatBackgroundOutgoing = <accent>` **and**
`chatTextOutgoing = .white` — set the background alone and the text stays dark/illegible.

**The UIKit trap:** SwiftUI's message view honors `chatTextOutgoing`, but **UIKit's
`ChatMessageContentView.messageTextColor` ignores it** — it returns `colorPalette.textPrimary`
(dark) for *both* directions. So in `StreamChatUI` the outgoing text is dark on your solid
bubble no matter what you set. Fix by subclassing and registering it:
```swift
final class BrandMessageContentView: ChatMessageContentView {
    override var messageTextColor: UIColor {
        content?.isSentByCurrentUser == true ? appearance.colorPalette.chatTextOutgoing : super.messageTextColor
    }
}
// Components.default.messageContentView = BrandMessageContentView.self
```

### Custom message cells (cards/widgets) in UIKit

To render a structured card in a message cell, subclass `ChatMessageContentView`, register it via
`Components.default.messageContentView`, and in `updateContent()` add your card view to
`bubbleContentContainer` and hide `textView`. Two details that look "off" if missed:
- **Don't nest the card in the default bubble.** Clear it so the card reads as a standalone card:
  `bubbleView?.backgroundColor = .clear; bubbleView?.layer.borderWidth = 0` (for card messages
  only), and give the card its own background/border/cornerRadius/padding.
- **SF Symbol icons won't show at a sane size by default.** Set
  `imageView.preferredSymbolConfiguration = .init(pointSize: 22, weight: .semibold)`, pin an
  explicit `width/height` frame, and raise content-hugging/compression-resistance so the icon
  isn't squeezed to zero by the surrounding stack.

---

## 7. Seeding / demo data

Sendbird's client-side multi-user seeding (connect as user A, then B, then C — test mode
auto-creates them) **does not map** to Stream: the client can only act as the connected
user and can't mint other users.

- **Create users / cross-user messages**: server-side — Stream CLI (`getstream api UpdateUsers`,
  `GetOrCreateChannel`, `UpdateChannel add_members`, `SendMessage` with `user_id`) or your backend.
- **Channels the current user owns + that user's own messages**: the client can do these
  (`channelController(createChannelWithId:)`, `createNewMessage`). Keep a thin client-side
  "ensure my channels exist" step if the original app self-seeded.

Document this in the migrated app; don't try to reproduce client-side impersonation.

---

## 8. Pitfalls (build/runtime breakers)

- **Link `StreamChat`** (not only `StreamChatSwiftUI`) — see §1.
- **Don't wrap `ChatChannelListView`** in `NavigationStack`/`NavigationView`; use
  `embedInNavigationView: false` to host it yourself; set the title via the `title:` param.
- **A segmented/filtered channel list "jumps" when you switch filters** if each switch rebuilds
  `ChatChannelListView` via `.id(filter)` with a **fresh** controller — the list flashes empty →
  loaded. Fix: **cache one `ChatChannelListController` per filter** and **pre-warm them**
  (`synchronize()`) up front, so switching shows already-loaded channels instantly. Don't create a
  new controller in a computed `var` (it re-creates every render). For a custom *look* (e.g. an
  accent-tinted segmented control), build a small SwiftUI control rather than fighting
  `UISegmentedControl.appearance()` (a global proxy that bleeds across screens).
- **Create the `StreamChat` SwiftUI wrapper before any Stream view renders** (App `init`), or it crashes.
- **Don't create controllers/clients in a SwiftUI `body`** or computed var — own them as
  `@State`/`@StateObject`/stored properties (re-creating re-fires network calls).
- An `ObservableObject` with `@Published` needs `import Combine` once Stream modules are imported.
- Default arguments evaluated off the main actor (e.g. `init(userId: String = Config.userId)`,
  where `Config` is main-actor-isolated under MainActor-default isolation) warn — make the params
  optional (`= nil`) and resolve the default inside the (`@MainActor`) init body.
- **"Modifying state during view update"** from a `.task { await connect() }` that mutates
  `@State`: if the awaited call returns **synchronously** (e.g. the app already connected at a
  parent screen, so the stack's `connect()` returns immediately), the whole closure runs inside
  the current update and the state write is flagged. Put an `await Task.yield()` at the top of the
  async fn so the mutation lands on the next runloop tick.
- The injected appearance key is `\.colors` (a `ColorPalette`), not `\.appearance`. Note
  `ColorPalette` is a **reference type** — `var p = InjectedValues[\.colors]; p.x = …` warns
  "never mutated, use `let`" (you're mutating the shared object, not rebinding); use `let`.
- `Token` is `ExpressibleByStringLiteral` (for literals) but use `try Token(rawValue: stringVar)` for a `String`.

### Navigation back & UIKit nav items (the "can't go back" trap)

When you host a UIKit Stream VC (`ChatChannelListVC`/`ChatChannelVC`) inside SwiftUI with the
outer bar hidden + your own `UINavigationController`, a back-to-previous-screen button is your
responsibility — and it's easy to lose:

- **`ChatChannelListVC` re-installs its nav items in `setUpAppearance()`** — it sets
  `title = "Stream Chat"` AND `navigationItem.leftBarButtonItem = <current-user avatar>`.
  Setting your title/back button after `loadViewIfNeeded()` is **NOT enough**: `setUpAppearance()`
  runs (in `viewDidLoad` and again on trait changes) and clobbers them, leaving the user on a
  "Stream Chat" header with the avatar and **no way back**. The only robust fix is to **subclass
  and override `setUpAppearance()`**: call `super`, then set your `navigationItem.titleView` and a
  real back button as the `leftBarButtonItem`. `ChatChannelListVC.make(with:)` returns `Self`, so
  `MyListVC.make(with: controller)` gives you the subclass.
  ```swift
  final class BrandedChannelListVC: ChatChannelListVC {
      var onClose: (() -> Void)?
      override func setUpAppearance() {
          super.setUpAppearance()
          title = "Team Space"; navigationItem.titleView = brandedTitleLabel
          navigationItem.leftBarButtonItem = UIBarButtonItem(
              image: UIImage(systemName: "chevron.left"), style: .plain,
              target: self, action: #selector(close))   // → onClose() → dismiss()
      }
  }
  ```
  (`ChatChannelVC` puts its info on the *right*, so a left back button there survives without this.)
- Wire the back button to dismiss the SwiftUI push: pass `@Environment(\.dismiss)` into the
  representable and call it from the bar-button action.
- **Only customize the back button on the *root* of your hosted nav stack — never on a *pushed*
  chat VC.** A `ChatChannelVC` (or subclass) pushed from the list gets a working default back
  button (it pops to the list, tinted by `navigationBar.tintColor`). If you override its
  `navigationItem.leftBarButtonItem` with a custom action (e.g. one wired to a closure that's only
  set on the deep-link path), you **delete the working pop** and back does nothing in the chat.
  Set custom title views / right-bar buttons there, but leave the left item alone.
- **SwiftUI** Stream views (`ChatChannelListView` with `embedInNavigationView: false`,
  `ChatChannelView`) pushed inside a `NavigationView` get the system back button for free —
  don't hide that bar.
- **Don't drive a deep link with a hidden `NavigationLink(isActive:)` inside a `NavigationView`.**
  A programmatic, always-present `isActive` link coexisting with real row-tap `NavigationLink`s
  **corrupts the nav stack** — back then needs several taps before it works, and nested UIKit nav
  controllers can't pop at all. It's also deprecated (iOS 16). For an env-var deep link used only
  for screenshots, present with **`.fullScreenCover`** so it never touches the real nav stack;
  verify custom toolbar headers on the **real row-tap path** instead (they only render there).

### Per-screen dark mode for a UIKit integration — `overrideUserInterfaceStyle`, NOT `preferredColorScheme`

To render one UIKit-hosted integration dark (e.g. an open-channel hub), it's tempting to slap
`.preferredColorScheme(.dark)` on the SwiftUI host. **Don't** — applied to a `NavigationView`-pushed
view it disrupts the navigation hierarchy and **breaks the back button** (the symptom: every other
screen's back works, this one's doesn't). Force dark on the **UIKit** side instead:
- Set `overrideUserInterfaceStyle = .dark` on **each view controller** — the list VC *and* the
  pushed chat VC (in its `viewDidLoad`). Setting it only on the `UINavigationController` does **not**
  reliably cascade to the Stream message list / composer (they render white). The list and chat
  each need it set on themselves.
- Then the SwiftUI host needs no `preferredColorScheme`, and back works normally.

Note the earlier "trait change re-runs nav setup" risk still applies — which is exactly why the
list's title/back button belong in a `setUpAppearance()` override (above), not a one-time post-load
assignment.

### Headers

Both `makeChannelListHeaderViewModifier` and `makeChannelHeaderViewModifier` must set the title
via `.toolbar { ToolbarItem(placement: .principal) { … } }` (that's what the defaults do) — a
`VStack`/`safeAreaInset` header inside the channel header modifier lands at the bottom (it wraps
a zero-height divider above the composer). A custom `ViewFactory` class must declare both
`@Injected(\.chatClient) var chatClient` and `var styles = RegularStyles()` (only
`DefaultViewFactory` gets `styles` for free).

A Sendbird **group-channel** header has a channel-**info** button on the trailing edge; Stream's
default chat header has none. Add it in `makeChannelHeaderViewModifier` with a trailing
`.toolbar` item — `Image(systemName: "info.circle")` → push
`ChatChannelInfoView(channel: channel)` (e.g. a hidden `NavigationLink(isActive:)`). Set the
title with a `.principal` item in the same modifier.

---

## 9. Procedure checklist

1. **Detect** the integration shape and inventory Sendbird touchpoints (§0).
2. **Swap packages**: remove Sendbird, add `StreamChat` + `StreamChatSwiftUI`/`StreamChatUI` (§1).
3. **Credentials**: get an API key; issue a dev/backend token; put them in the config type
   (replace the Sendbird App ID). Never commit the secret.
4. **Wire one Stream stack** (client + SwiftUI wrapper + connect); repoint existing
   bootstraps/abstractions at it without changing their public API (§2).
5. **Migrate each touchpoint** per its pattern (§0 table), swapping views (§3), channels (§4),
   messages/custom attachments (§5).
6. **Re-apply theming + customizations** via `Appearance` + `ViewFactory` (§6). Derive every
   color/layout value **from the source** (§0.5), don't accept Stream defaults.
7. **Move seeding server-side** where it relied on client-side multi-user creation (§7). Seed an
   **outgoing** message per chat and **>2 members** on open channels (§4) so verification is real.
8. **Verify design + functional fidelity, per screen — including inside each chat** (§0.5). For
   every integration: open the list **and** the chat (deep-link env hook + screenshot, since the
   simulator can't tap), with an incoming **and** outgoing message visible, and run the §0.5
   checklist (bubble bg+text both directions, alignment, header info button, composer suggestion
   placement, custom card/icon rendering & padding, badge tint). Compare against the Sendbird
   original and iterate — a green build and a correct channel list are **not** "done".
