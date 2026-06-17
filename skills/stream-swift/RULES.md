# Stream Swift - non-negotiable rules + iOS pitfalls

Every rule below is stated once. Read it before writing code. The docs cover *how* to use each API; this file covers what the docs do not shout about and what breaks builds.

---

## Secrets and auth

- Never hardcode a Stream API **secret** in app code, `Info.plist`, or chat. The client holds only the **API key** and a **user token**; the secret stays server-side / in the CLI.
- Token model: backend-issued token when a backend exists; CLI token (`stream token <user_id>` or `... --ttl <duration>`) for local/demo (preferred when no backend); a static pasted token only when the user insists.
- Never invent or fabricate credentials. Never use `devToken()` in production - it lets any client impersonate any user.
- In generated code, reference credentials via named constants (`Config.apiKey`, `Config.userToken`) in a dedicated config file - never embed raw values inline.

## No wrapper or bridge abstractions

Do not introduce `VideoCallBridge`, `CallManager`, `StreamWrapper`, `SDKAdapter`, or similar middle layers. Use SDK types directly: `StreamVideo` / `StreamVideoUI` at app init, `CallViewModel` as `@StateObject` in the root call view, `callViewModel.call?.state` for call state.

The **only** exception is a thin file-isolation service for combined Chat + Video apps (see pitfalls). Even then it just holds the SDK instances - no methods, no extra logic.

## Project ownership

Preserve the app's existing architecture. Do not convert UIKit to SwiftUI, do not replace CocoaPods with SPM, and do not flatten an existing coordinator / DI / navigation setup unless the user asks. If there is no iOS project, tell the user to create it in Xcode first - do not scaffold from the CLI.

**Do not change the app's entry point or navigation unless asked.** The default Chat integration is **channel list → tap → pushed message screen**. Do not make the app open one hard-coded channel directly (`ChatChannelView` as the root) as a shipped behaviour - that is an architecture change the user did not request, and it hides header/navigation bugs because the direct-open path never exercises `makeChannelHeaderViewModifier` / `makeChannelDestination`. Any temporary scaffold used to screenshot a screen (e.g. a direct-open root for design verification) is **throwaway: DELETE it before delivery** (not merely disable it - no `verifyMessageScreen`-style flag, dead `if/else` branch, or scaffold-only constant/import may remain in the shipped code) and re-verify on the real navigation path. "Make the channel look like X" is a styling request, not a request to change how the app is entered.

## Match the Chat UI layer to the vertical

Stream Chat has two layers; picking the wrong one is an architecture mistake, not a styling one.

- **Pre-built UI components** (`StreamChatSwiftUI` / `StreamChatUI`, customized via ViewFactory + theming) - for standard-messenger verticals: social / community chat, marketplace, workplace (Slack-like), support, DMs. Their UI already resembles these apps; customize, do not rebuild.
- **Custom UI on the low-level `StreamChat` client + State Layer** - for livestream chat (Twitch / YouTube / Kalshi), live shopping, overlay / ticker chat, and any bespoke surface. The pre-built components fight this kind of UI; do not recommend or wire them here. Build views directly on the State Layer (`LivestreamChat` for high volume, else `Chat`, `ChannelList`, etc.) / Controllers, with `StreamChat` (+ optional `StreamChatCommonUI`) linked but **not** `StreamChatSwiftUI`. Run [`custom-ui.md`](custom-ui.md) (the decision + the build procedure); see [`docs-map.md`](docs-map.md) "Chat - Custom UI" for the docs it routes to.

**Default to components, and lean hard that way.** The expensive, common mistake is over-choosing custom - rebuilding a worse messenger by hand and throwing away avatars, grouping, reactions, threads, attachments, typing, receipts, and the composer's pickers/voice notes. The litmus test: *if theming + a few `ViewFactory` slots + `Styles` could match the design, it is a components job* (even strong reskins like WhatsApp). Pick custom only when you'd otherwise be replacing the row, composer, header, AND list all at once - using the SDK purely as a data source. When unsure which applies, build the components version first (faster to confirm-or-reject), or ask before writing code (see [`SKILL.md`](SKILL.md)).

## Permissions: match the channel type to the vertical

Stream Chat's built-in channel types ship sensible default permission policies - start from the one that fits the vertical instead of hand-rolling permissions:

| Vertical | Channel type | Default posture |
|---|---|---|
| Social / dating / marketplace DMs | `messaging` | Membership-gated: members read/write; not public |
| Workplace / Slack-like | `team` | Membership + roles for broader team spaces |
| Livestream / live-shopping | `livestream` | Public read/write without membership; supports guest + anonymous viewers |
| In-game chat | `gaming` | Game-tuned defaults |
| User-to-LLM chat | `ai` | AI chat defaults |

Then tune only what the vertical needs:

- **Livestream viewers:** connect read-only viewers as **anonymous** (`connectAnonymousUser()` - read-only, can read `livestream` channels, no MAU cost) or as **guest** (`connectGuestUser(userInfo:)` - limited writes, pre-account). Do **not** mint a full per-user JWT for every anonymous viewer. Moderate with the `channel_moderator` role, not client-side `admin`.
- **Regular chat:** keep channels membership-gated; do not make `messaging` channels world-readable to imitate livestream - use the `livestream` type for that.
- **Roles:** user-level (`user`, `guest`, `anonymous`, `admin`) vs channel-level (`channel_member`, `channel_moderator`); built-in roles cannot be mixed across levels.

Security (non-negotiable): **permission checks apply to client-side calls only - server-side calls (API key + secret) bypass all permissions.** Never rely on client permissions to protect sensitive actions, never give the app the secret or an `admin` role, and never grant elevated permissions to ordinary client users. Customize policies in the Dashboard (Chat > Roles & Permissions) or via the API (`UpdateChannelType`, `CreateRole`) - never from app code. Routes: [`docs-map.md`](docs-map.md) "Permissions and roles".

## Client lifetime

Initialize Stream clients **once** at app launch or in an owned service object. Never create a client in a SwiftUI `View` body, a computed property that re-runs on redraw, or a transient callback with no owner. Store controllers / view models / SDK helpers as owned state (`@State`, `@StateObject`, `ObservableObject`, or stored properties).

On account switch, fully disconnect / log out the current user before connecting the next one - wait for logout completion (offline storage + optimistic updates can corrupt if you connect mid-logout).

## UI and concurrency

UI state changes belong on the main actor - hop back to the main actor before mutating SwiftUI or UIKit state from an SDK callback or async task. Match the project's existing concurrency style (async/await vs completion handlers) instead of rewriting unrelated code.

## Mindful API usage (best practices)

The SDK talks to a rate-limited, billed backend. Sloppy usage causes throttling, UI jank, and cost. Read the relevant best-practices page (routes in [`docs-map.md`](docs-map.md)) before building a vertical.

- **Do not spam `queryChannels` (or any query).** Query once with a filter + sort + sensible `pageSize`, paginate with `loadMore*`, then rely on `watch` + WebSocket events for live updates - do not re-query on every change. For a single channel, only one of `watch` / `query` / `create` is needed; do not chain redundant calls.
- **No rendering loops.** Never create a client, controller, query, or state object in a SwiftUI `body` or computed var - each redraw re-fires network calls. Own them as `@State` / `@StateObject` / stored properties (see Client lifetime). A list that re-fetches on every scroll, or a view that reconnects on every appear, is the symptom.
- **Authenticate once.** Connect the user once and reuse the connection. For expiring tokens supply a `tokenProvider` and let the SDK refresh - never poll, manually reconnect on expiry, or connect/disconnect in a loop. Wait for logout before connecting the next user. Never ship dev tokens or the API secret.
- **Respect budgets and limits.** There is a per-app query-channels budget plus global rate limits; back off on errors instead of retrying tightly, and paginate instead of requesting huge pages.

### Case-specific tuning

Defaults are tuned for standard messaging, not every vertical - configure to fit:

- **Livestream / live-shopping chat:** use the `livestream` channel type; **disable read events, typing indicators, connect events, file uploads, and custom messages**; disable offline/local storage (per-message write overhead bottlenecks under volume); enable slow mode for high traffic; pre-load users via batch upsert (up to 100 per call). The API auto-throttles typing/read events past ~100 watchers and messages past ~5/sec - design for it. Source: the livestream best-practices page.
- **Marketplace / workplace:** read the marketplace best-practices page before scaling channel and user counts.

## Docs discipline

The live iOS docs are the source of truth (see [`SKILL.md`](SKILL.md) for the `.md` convention and [`docs-map.md`](docs-map.md) for routing). Do not answer SDK specifics from training data. If you did not fetch it this conversation, fetch it. Cite the page. Never guess a `ViewFactory` / `ColorPalette` / method name - these look guessable but are routinely wrong; fetch the page first.

---

## iOS pitfalls (the build-breakers)

These are the mistakes the docs will not warn you about. Honor them every time.

### Chat + Video name collisions (most common build break)

When an app uses **both** SDKs, several names collide and cause "Ambiguous use of 'init'" / "ambiguous" compiler errors:

| Concept | Chat | Video |
|---|---|---|
| User | `UserInfo` (`StreamChat`) | `User` (`StreamVideo`) |
| Token | `Token` (`StreamChat`) | `UserToken` (`StreamVideo`) |
| SwiftUI wrapper | `StreamChat` (`StreamChatSwiftUI`) | `StreamVideoUI` (`StreamVideoSwiftUI`) |
| `ViewFactory`, `@Injected`, `InjectionKey`, `InjectedValues` | `StreamChatSwiftUI` | `StreamVideoSwiftUI` (same names) |

**Fix: file isolation.** Never import both SDKs in one file. Put each SDK's setup in its own service file (`ChatService.swift` imports only Chat; `VideoService.swift` imports only Video); the `App`/`AppDelegate` imports neither and just calls both services. `StreamVideoUIKit` depends on `StreamVideoSwiftUI`, so the same rule applies to UIKit combined apps. Same API key, same JWT, same user id work for both products. Docs: Chat side [video-integration](https://getstream.io/chat/docs/sdk/ios/guides/video-integration.md), Video side [chat-integration](https://getstream.io/video/docs/ios/advanced/chat-integration.md).

### SwiftUI lifecycle

- Initializing `StreamChat` / `StreamVideo` / `StreamVideoUI` in an `App` struct `init()` requires storing them in **`@State`** (`_x = State(wrappedValue:)`). `App` is a value type SwiftUI can recreate; a plain `let`/`var` gets re-initialized. Use `AppDelegate` instead when you need `UIApplicationDelegate` callbacks (push, CallKit, background, URL handling).
- The SwiftUI wrapper (`StreamChat` / `StreamVideoUI`) **must** exist before any SDK view renders - rendering first causes a `fatalError` / crash.

### Chat

- Never wrap `ChatChannelListView` in `NavigationView` / `NavigationStack` - it includes its own. Set the title via the `title:` initializer parameter, not `.navigationTitle()`. To use your own nav container, pass `embedInNavigationView: false`.
- Controllers are stateful - store as `@State` or in an `ObservableObject`, never a computed var (a new instance per redraw re-fetches and loses state).
- `import StreamChat` **and** `import StreamChatSwiftUI` in any file using either - `ChatClient`, `UserInfo`, `Token`, controllers live in `StreamChat`; views + the `StreamChat` wrapper live in `StreamChatSwiftUI`. Access the client via `@Injected(\.chatClient)`, never `ChatClient.shared`.
- **Link the `StreamChat` product, not just `StreamChatSwiftUI`.** `StreamChatSwiftUI` only re-exports `StreamChatCommonUI` + `StreamCore`, **not** `StreamChat`. If only `StreamChatSwiftUI` is added to the target, `import StreamChat` fails with "No such module 'StreamChat'". Add the `StreamChat` product to the target too (it ships from the transitively-resolved `stream-chat-swift` package - no second package URL needed). Separately, an `ObservableObject` service with `@Published` needs `import Combine` once Stream modules are imported (SwiftUI's re-export is not always enough) - else "init(wrappedValue:) is not available due to missing import of defining module 'Combine'".
- **Matching a reference design is not a theming task - and there are THREE axes, not two.** When the request carries a target screenshot / Figma / "look like <app>", run [`design-matching.md`](design-matching.md) and decompose every region first. Setting the bubble color and wallpaper and stopping is the known failure - the composer button set, the timestamp + read-receipt placement (often *inside* the bubble), the bubble tail, the header, and the date-separator pill are all structural and need `ViewFactory` slots, not `ColorPalette`. The grouped 1/2/3/4+ photo collage, by contrast, is already the default (`MessageMediaAttachmentsContainerView`) - do not rebuild it. The three axes: **theming** (`Appearance`: colors/fonts/glyphs), **`Styles`** (`factory.styles`: insets/padding/corner-radius/chrome), **structure** (`ViewFactory`: which views & layout). Routing a problem to the wrong axis is the core failure mode.
- **Padding / insets / corner-radius are the `Styles` axis - not theming, not a `ViewFactory` slot.** "The green frame around the photo collage is too thick / the bubble padding is too big" comes from `factory.styles.makeMessageAttachmentsViewModifier` (default inset `spacingXs` all sides); the message bubble from `makeMessageViewModifier`; attachment cells from `makeMessageAttachmentItemViewModifier`; composer chrome from `makeComposerViewModifier` (container background) / `makeComposerInputViewModifier` (field background+border) / `makeComposerButtonViewModifier`. **`RegularStyles` is not `open` - you cannot subclass it.** Conform a class to `Styles` directly, implement the modifiers you want, and **re-supply the non-defaulted members RegularStyles provides** (composer background = `ComposerBackgroundRegularViewModifier`, input = `RegularInputViewModifier`, button = `RegularButtonViewModifier`, scroll/suggestions) using those public types - or the composer/field render **white/unstyled** because the `extension Styles` defaults are `EmptyViewModifier`. Assign it to your factory's `var styles`. Details + checklist in [`design-matching.md`](design-matching.md).
- **Overriding a composite slot drops every sub-feature the default rendered.** `makeMessageItemView`, `makeChannelHeaderViewModifier`, `makeMessageComposerViewType`, `makeComposerInputTrailingView`, and `makeChannelListItem` each draw many things internally. A custom replacement that only handles the case in front of you silently loses the **author avatar on incoming messages**, message **grouping**, reactions, replies, delivery status - or, for the composer input trailing, the **send / voice-record / confirm-edit / slow-mode** button. A near-empty test channel hides the loss. Before overriding one, read the default view's `body` in the pinned source, enumerate every sub-view, and reproduce each (reuse the SDK sub-views) or tell the user you dropped it.
- **The channel header modifier is applied to a zero-height divider between the message list and the composer - not the whole screen.** So rendering a header inside `makeChannelHeaderViewModifier` via `.safeAreaInset(.top)` or a `VStack` puts it **at the bottom, above the composer**. Customize the header with `.toolbar` placements (they reach the nav bar at the top regardless) + `.toolbarBackground`; only drop to a fully custom container/`makeChannelDestination` for a genuinely taller header - and **never** fake the header in the app's root view for one channel (it vanishes on the real push path). See [`design-matching.md`](design-matching.md) Step 2.5.
- **Match dimensions by MEASURING, not eyeballing - then verify and iterate.** The reference is a spec: reproduce header height, font/icon sizes, paddings, corner radius, and alignment - not just colors and presence. Do **not** pick round numbers by eye (the recurring composer failure). Find the screenshot's scale (`sips -g pixelWidth -g pixelHeight`; iOS shots are @2x/@3x → divide to points), measure each element in points, and **reuse the SDK design tokens** (`@Injected(\.tokens)`: `spacingXs=8`, `spacingMd=16`, `radius3xl=24`; composer field `defaultInputViewHeight=40`) rather than magic numbers, so custom views align with the un-overridden parts. A match is unverified until you build, seed data that triggers **every** region (incoming + outgoing, a run of same-author messages so avatars/grouping show, album, reactions, reply, long text, date separator), open the real message screen, **measure your render against the reference at the same scale**, compare region-by-region, and **iterate until each passes**. See [`design-matching.md`](design-matching.md) "How to actually get the dimensions right" + Step 5.

### Video

- `CallViewModel` is `@StateObject` at the single ownership site, `@ObservedObject` in children. Never create a second instance for the same call - state is lost.
- Read state via `callViewModel.call?.state`, never `CallState.shared` (singleton access leaves the UI stale). Leave a call with `callViewModel.hangUp()`, not `call.leave()`.
- `import StreamVideo` in any file declaring `User`, `UserToken`, `Call`, `CallParticipant`, `Member`, `RTCVideoTrack`, or `LogConfig` - `StreamVideoSwiftUI` alone is not enough and you get "cannot find type".
- Add `NSCameraUsageDescription` + `NSMicrophoneUsageDescription` to `Info.plist` before any call (missing keys = silent crash). Audio-only `audio_room` still needs the microphone key.
- Always surface `callViewModel.error` with an `.alert` on views that call `joinCall` / `startCall` / `acceptCall` / `hangUp`.

### Push notifications (Chat push, Video VoIP / CallKit)

Full runbook: [`push.md`](push.md). The traps:

- The APNs auth key (`.p8`) goes to **Stream** via the CLI (`UpsertPushProvider`), **never** into the app bundle, `Info.plist`, or git. Pipe it over stdin; do not paste its contents into chat.
- A single token `.p8` powers both alert push and VoIP - you do not need a separate VoIP certificate. The provider `name`(s) you create (`apn`, `voip`) must match the names referenced in client code (`addDevice(providerName:)`, `PushProviderInfo(name:)`).
- `apn_development` must match the build: `true` = sandbox (Xcode debug), `false` = TestFlight / App Store. A mismatch = silent no-delivery.
- **Real device only** - APNs and VoIP never fire on the simulator.
- A device registers only **after** the user connects (chat) / `StreamVideo` is initialized with the push config (video). Registering earlier is a no-op.
- VoIP/CallKit needs Background Modes (Voice over IP, Remote notifications, Background processing); plain Chat push needs only the Push Notifications capability.
- Add a Notification Service Extension only when rich/decrypted previews are wanted - it is not required for a basic alert or for ringing calls. Decide deliberately; do not add it by reflex.

### Feeds

Feeds has no pre-built UI components - the SDK gives you state objects (`FeedState`, activities, reactions, comments, follows), you build the views. Load the relevant Feeds docs page from [`docs-map.md`](docs-map.md) for the exact state API; do not assume a component exists.
