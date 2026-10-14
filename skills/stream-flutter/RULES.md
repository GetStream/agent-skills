# Stream Flutter - non-negotiable rules + Flutter pitfalls

Every rule below is stated once. Read it before writing code. The docs cover *how* to use each API (route through [`docs-map.md`](docs-map.md)); this file covers what the docs do not shout about and what breaks builds.


---

## Secrets and auth

- Never hardcode a Stream API **secret** in app code, `pubspec.yaml`, `dart_defines.json`, or chat. The client holds only the **API key** and a **user token**; the secret stays server-side / in the CLI.
- Token model: backend-issued token when a backend exists; CLI token (`getstream token <user_id>` or `... --ttl <duration>`) for local/demo (preferred when no backend); a static pasted token only when the user insists.
- Never invent or fabricate credentials. Never use dev tokens in production - they disable token auth and let any client impersonate any user. For no-backend "just a name" sign-in use **guest** users instead.
- One Stream project = one API key for Chat, Video, and Feeds; the same user JWT works for all of them.

## No wrapper or bridge abstractions

Do not introduce `ChatManager`, `VideoCallBridge`, `StreamWrapper`, `SDKAdapter`, `FeedsService`, or similar middle layers between the app and the SDK. Use SDK types directly: `StreamChatClient` + the `StreamChat` widget, `StreamChannel` per channel screen, controllers as `State` fields, `StreamVideo.instance` + `Call` objects, `StreamFeedsClient` + feed objects.

The only exceptions: a thin service that isolates initialization when the app uses multiple Stream products, and the documented patterns in [`video-patterns.md`](video-patterns.md) (e.g. the livestream-feed `CallManager`) that exist to solve a real concurrency problem.

## Project ownership

Preserve the app's existing architecture:

- Do **not** convert existing navigation (GoRouter, auto_route, Navigator) or state management (Provider, Riverpod, Bloc) unless the user asks. Inject the Stream client through the existing DI pattern - never add a second one.
- Do **not** change the app's entry point or navigation to show one hard-coded channel. The default Chat integration is **channel list -> tap -> pushed channel screen**. Any temporary scaffold used to screenshot a screen is throwaway: delete it before delivery and re-verify on the real navigation path.

If there is **no Flutter project**:

- When the user **explicitly asks to create a new app**, scaffold it yourself: `flutter create --org <reverse.domain> --project-name <name> --platforms android,ios <dir>`. An empty, pre-named directory is a strong signal of where it goes.
- Otherwise (integration/setup with no app), do **not** scaffold silently - tell them to run `flutter create my_app` first.

## Client lifetime

Initialize Stream clients **once**, before `runApp` (or in an owned service). Never create a client, controller, channel, `Call`, or query inside a `build` method, a `StatelessWidget` body, or a getter that re-runs on rebuild. Store controllers as `late final` fields on a `State` and dispose them in `dispose()`; cancel every stream subscription there too.

- **Chat:** `StreamChat` must be an ancestor of every Stream Chat widget (typically `MaterialApp(builder: (context, child) => StreamChat(client: client, child: child))`). Await `connectUser` before showing chat UI. On account switch, `await client.disconnectUser()` before connecting the next user.
- **Video:** `StreamVideo(...)` registers a singleton; `StreamVideo.instance` throws before construction. On account switch, `await StreamVideo.reset(disconnect: true)` **before** constructing a new `StreamVideo(...)` - the constructor throws if a singleton exists.
- **Feeds:** `StreamFeedsClient(apiKey: ..., user: ..., tokenProvider: ...)` once, then `await client.connect()` (it throws on failure, unlike most Feeds calls). Dispose feed objects you created when their screen goes away.

## UI and concurrency

Stream callbacks and futures complete on the main isolate - do not `compute()` / `Isolate.spawn()` Stream work. Prefer `StreamBuilder` / `ValueListenableBuilder` / the SDK builders (`PagedValueListenableBuilder`, `PartialCallStateBuilder`, `StateNotifierBuilder`) over manual `setState` + subscription juggling.

## Mindful API usage (best practices)

The SDK talks to a rate-limited, billed backend. Read the relevant best-practices page (routes in [`docs-map.md`](docs-map.md)) before building a vertical.

- **Do not spam queries.** Query once with filter + sort + a sensible page size, paginate with the controller / `queryMore*`, then rely on watch + WebSocket events. Never re-query on every change.
- **No rendering loops.** A controller or query created in `build` re-fires network calls on every rebuild - the symptom is a list that resets pagination or a screen that reconnects on every appear.
- **Authenticate once.** For expiring tokens supply a token provider (`tokenOrProvider` / `tokenLoader` / `tokenProvider`) and let the SDK refresh - never poll or reconnect in a loop.
- **Throttle search-as-you-type**, and back off on errors instead of retrying tightly.
- **Livestream chat:** use the `livestream` channel type; disable read events, typing indicators, connect events, uploads and custom messages; skip offline persistence; enable slow mode for high traffic. Source: the "Livestream chat" row in [`docs-map.md`](docs-map.md).

## Docs discipline

The live Flutter docs are the source of truth (see [`SKILL.md`](SKILL.md) for the `.md` convention and [`docs-map.md`](docs-map.md) for routing). Do not answer SDK specifics from training data - if you did not fetch it this conversation, fetch it. Cite the page. Never guess a widget parameter, theme property, component-builder slot, or method name - they look guessable and are routinely wrong.

## Never declare an API missing without evidence

`stream_chat_flutter` re-exports `stream_chat_flutter_core` -> `stream_chat`, **and** `stream_core_flutter` (where `StreamTheme`, `StreamColorScheme`, `StreamComponentBuilders` / `StreamComponentFactory`, `StreamMessageLayout`, and the message-item theme live). `stream_chat_persistence` and `stream_chat_localizations` are **not** re-exported - import them explicitly. So a `grep 'class X' stream_chat_flutter/lib` that comes back empty means you looked in the wrong package, not that the API is gone.

Never report a symbol as missing / renamed / unsupported - or silently hand-roll a workaround - unless you can point to the failed check: a grep across the **whole resolved set** (all `stream_*` packages in `~/.pub-cache` at the versions `pubspec.lock` names) or a compile error against the pinned version.

## Never assume a default

Never assume a widget's default behavior, what a callback does, what a theme token controls, or that two widgets auto-wire to each other (a message list and a composer do not). Ground the claim against the pinned SDK source or drive it on the device. Unverified assumptions about defaults are where migrations and design-matches silently lose features.

---

## Chat

### Match the UI layer to the vertical

Two layers; picking the wrong one is an architecture mistake. **Default to the pre-built components** (`stream_chat_flutter`) for any messenger-shaped surface; use custom UI on `stream_chat_flutter_core` only for livestream / overlay / bespoke surfaces. The full rubric is in [`SKILL.md`](SKILL.md); the custom build runbook is [`custom-ui.md`](custom-ui.md).

### Permissions (surface them proactively)

Permission checks apply to **client-side calls only** - server-side calls (CLI / backend with the secret) bypass them. So seeding works while the same action 403s from the app (`StreamChatNetworkError` code 17: `"User '...' with role 'user' is not allowed to perform action ReadChannel in scope 'messaging'"`). **Whenever the app does more than chat inside channels the user already belongs to, name the required grant in the same turn you build the feature:**

| App behaviour | Grant on the channel type | Default for `user` / `guest` on `messaging` |
|---|---|---|
| Discover / browse channels the user is not in (`queryChannels` without a `members` filter) | `Read Channel` (`ReadChannel`) | often **off** |
| Self-join (`channel.addMembers([myId])`) | `Add Own Channel Membership` (`AddOwnChannelMembership`) | often **off** |
| Leave (`channel.removeMembers([myId])`) | `Remove Own Channel Membership` (`RemoveOwnChannelMembership`) | varies |
| Create a channel | `Create Channel` (`CreateChannel`) | usually on |

`guest` is stricter than `user` and needs the grants too. Grant them in Dashboard -> Chat -> Roles & Permissions (permissions v2) or via `UpdateChannelType`; verify, don't assume, since defaults depend on the app's history. Pick the channel type to fit the vertical: `messaging` (membership-gated DMs/groups), `team` (workplace), `livestream` (public read/write, guests and anonymous viewers), `ai` (user-to-LLM). Never give the app the secret or an `admin` role. Reference: the "Permissions / channel types" row in [`docs-map.md`](docs-map.md).

### Version

This skill targets **`stream_chat_flutter` / `stream_chat_flutter_core` v10**. v9 and earlier have different widget names, controllers, theming and reaction/delete APIs. If the project pins 9.x, stop and follow [`setup.md`](setup.md) "Version prerequisite".

### Pitfalls the docs do not shout about

- **Builder placement differs per widget.** `StreamChannelListView` takes its builders top-level; `StreamMessageListView` puts behavior flags in `config: StreamMessageListViewConfiguration(...)` and slot builders (`empty` / `loading` / `error`) in `builders: StreamMessageListViewBuilders(...)`, while `messageBuilder`, `parentMessage`, `threadBuilder`, `onReplyTap` stay top-level.
- **Thread page - the docs reference a `ThreadPage` they never define, and the SDK example builds its controller inside `build()`.** Use this shape: a `StatefulWidget` taking the parent `Message`; a `late final StreamMessageComposerController(message: Message(parentId: parent.id))` field, disposed in `dispose()` (without the `parentId`, replies land in the main channel); a `Scaffold` with `StreamThreadHeader(parent: parent)`, `StreamMessageListView(parentMessage: parent)`, and `StreamMessageComposer(messageComposerController: _controller)` (not `const` in v10). Return it from the channel list view's `threadBuilder` wrapped in `StreamChannel(channel: StreamChannel.of(context).channel, child: ThreadPage(parent: parent))`. Recreate the controller in `didUpdateWidget` if the parent can change.
- **Voice recording default flips to `false`** when you build the composer through `MessageComposerProps` / the component factory - re-enable it explicitly if the default composer showed it.
- **`StreamChannelListView` paginates itself**; the core `StreamChannelListController` does not auto-fetch - call `doInitialLoad()` in `initState`.
- **Filters:** it is `Filter.in_` (underscore), and the sort parameter is `channelStateSort:`. The token user must be a member of seeded channels or `Filter.in_('members', [userId])` returns nothing.
- **Message search:** pass exactly one of `searchQuery` / `messageFilter` (it asserts otherwise), and throttle input. The search controller pages with a `String` key: `PagedValueListenableBuilder<String, GetMessageResponse>`.
- **Polls** must be enabled on the channel type in the Dashboard before the composer shows them. **Drafts** are on by default.
- **Reactions** take a `Message` and a `Reaction` object (`channel.sendReaction(message, Reaction(type: 'like'))`), not an id + string. Counts live on `message.reactionGroups`. Keep **one** app-level reaction type -> emoji map; Flutter has no global SDK reaction-emoji config, so per-view literals desync the row, picker and overlay.
- **Composer edit mode is explicit:** `controller.editMessage(msg)` enters it; `clear()` does **not** exit it - call `cancelEditMessage()`.
- **`ClientState` collections are immutable** (`client.state.channels` / `users` throw on mutation). Let the SDK manage state through queries and `watch()`.
- **`StreamChatCore` sets `recoverStateOnReconnect = false`.** Channels you watch outside a list controller need a re-query on `EventType.connectionRecovered`. Do not mix `StreamChatCore` and `StreamChat` in one tree.
- **`channel.state` is null before `watch()` / `query()`.** Custom message lists paginate manually (`channel.query(messagesPagination: ...)`).
- **Split view:** key the `StreamChannel` with `ValueKey(channel.cid)` so switching channels rebuilds its state.
- **Offline:** assign `client.chatPersistenceClient` **before** `connectUser`; flush on logout with `disconnectUser(flushChatPersistence: true)`.
- **Logout only closes the WebSocket if the chat route is disposed** - force it with `Navigator.pushAndRemoveUntil(..., (r) => false)`.

### Design fidelity

- **Matching a reference design is not a theming task - there are TWO axes.** When the request carries a target appearance (screenshot, Figma, "make it look like <app>", or a migration's source app), run [`design-matching.md`](design-matching.md) and decompose every region first. Setting the bubble color and wallpaper and stopping is the known failure - the composer button set, metadata placement (author / timestamp / receipts relative to the bubble), bubble tail, header and date-separator pill are **structural** and need widget replacement. The grouped 1/2/3/4+ photo collage is already the default - do not rebuild it. The axes: **theming** (`StreamTheme` for foundations + the message row and every leaf widget; `StreamChatThemeData` for the chat composite widgets only) and **structure** (the component factory - core slots on `StreamComponentBuilders`, chat slots via `streamChatComponentBuilders(...)` - plus per-widget builders). Docs: the "Theming" and "Component factory" rows in [`docs-map.md`](docs-map.md).
- **Colors come from `StreamTheme`** (a `ThemeExtension` on `MaterialApp.theme.extensions`, built with `StreamColorScheme.fromSeed(...)` / `.light()` / `.dark()`), not from the Material `ColorScheme`. Fetch the theming page before writing any theme code.
- **Padding / insets / corner radius are theme VALUES, never a reason to replace a widget.** They live on `StreamTheme.messageItemTheme` (bubble / text / attachment padding, shapes) as content-kind-resolved `StreamMessageLayoutProperty` values - override with `resolveWith(...)`, preserving the branches you are not changing. If a token is not on `StreamChatThemeData`, look on `StreamTheme` before concluding it does not exist.
- **Overriding a composite slot drops every sub-feature the default rendered.** `messageItem` / `messageBuilder`, `messageComposer` (+ input sub-slots) and `itemBuilder` draw the incoming avatar, grouping, reactions, replies, delivery status - or the composer's send / voice / confirm-edit / slow-mode state machine. Before overriding one, read the default widget's `build()` in the pinned source, enumerate every sub-widget, and reproduce each (reuse the SDK's public sub-widgets) or tell the user what you dropped. **Never return a public widget from its own slot override** (`StreamMessageItem.fromProps`, `StreamMessageBubble`, `StreamMessageComposerInput`) - it re-enters the factory and stack-overflows; wrap the barrel-exported `Default*` widget instead. (`StreamMessageItem.fromProps` is fine inside the per-widget `messageBuilder`.)
- **Match dimensions by MEASURING, not eyeballing - then verify and iterate.** Find the screenshot scale (`sips -g pixelWidth -g pixelHeight`; divide by 2/3 for iOS shots, by the density bucket for Android) and work in logical pixels. A match is unverified until you run, seed data that triggers every region (incoming + outgoing, a same-author run, album, reactions, reply, long text, date separator), open the real screen, and iterate region by region ([`design-matching.md`](design-matching.md) Steps 1 + 5).

---

## Video

### Build blockers (the docs do not cover these)

- **iOS deployment target under Swift Package Manager (older Flutter only - apply if you hit the error).** Flutter 3.32+ uses SPM by default, so a fresh `flutter create` has **no `ios/Podfile`** - do not add one just to set the target. Recent templates (e.g. 3.47) already target iOS 15.0 and build without changes. On older templates (13.0 target) the build fails with *"increase your app's minimum platform version from 13.0 to at least 14.0"*; then raise the target to 15.0 in **both** `ios/Runner.xcodeproj/project.pbxproj` (`IPHONEOS_DEPLOYMENT_TARGET`, all three configs) **and** `ios/Flutter/AppFrameworkInfo.plist` (`<key>MinimumOSVersion</key><string>15.0</string>`, which drives the generated plugin package's platform). Only if a Podfile already exists, also set `platform :ios, '15.0'` there.
- **SPM can flood the analyzer with phantom errors** from the SDK's `example/` and `test/` sources copied into `build/`. Recent templates (e.g. 3.47) already exclude `build/**`. If yours does not, add `build/**` to the **existing** `analyzer: exclude:` list in `analysis_options.yaml` - never append a second `analyzer:` block (a duplicate mapping key makes the analyzer reject the whole file). Trust `flutter analyze` over IDE squiggles.
- **Android uses the Kotlin DSL** (`android/app/build.gradle.kts`). Raise floors with `minSdk = maxOf(24, flutter.minSdkVersion)` (and `compileSdk = maxOf(36, flutter.compileSdkVersion)` when needed) - Groovy `minSdkVersion 24` snippets do not parse in `.kts`.
- **Android PiP** requires `MainActivity` to extend `StreamFlutterActivity` instead of `FlutterActivity`.
- **Runtime permissions:** manifest entries are not enough on Android 6+ - request camera + microphone (`permission_handler`) before joining. Missing iOS `NSCameraUsageDescription` / `NSMicrophoneUsageDescription` = silent empty tracks.
- **`CompositeSubscription`** (returned by the ringing observers) is an rxdart type, not re-exported - add `rxdart` and import it; cancel with `dispose()` / `cancel()` / `clear()` (there is no `cancelAll()`, despite what some docs snippets show).

### Auth

- Expiring tokens: pass a `tokenLoader`; the SDK calls it for the first token and on every expiry.
- **Guests** (`User.guest`, no token): the server assigns a *generated* id that differs from the one you passed - after `connect()`, read `StreamVideo.instance.currentUser.id` and use that everywhere. The `guest` role has minimal capabilities: on `livestream` (and other restrictive types) it cannot read or join a call until you grant `read-call` + `join-call` (plus `create-call` if a viewer may open the call first) in Dashboard -> Video & Audio -> Call Types -> <type> -> Roles & Permissions. Surface this **before** building a guest-viewer flow.
- **Anonymous** users cannot open a WebSocket (no events, `connect()` rejects them) and need a token pinning `call_cids`. Watch-only livestream viewers only.

### Calls and state

- **`join()` creates the call if it does not exist** (it always sends `create: true`). Call `getOrCreate()` first only to set members, ringing or custom data.
- **`join()` returns a `Result`, it does not throw.** Always `fold` it; ignoring a failure leaves the UI on a dead call screen.
- **Camera / mic on join come from the call type's settings** (`camera_default_on`, `mic_default_on`), then any `CallConnectOptions` you pass are merged on top. Do not rely on dashboard defaults: hosts pass explicit `camera: TrackOption.enabled(), microphone: TrackOption.enabled()`; viewers pass `disabled`. `TrackOption.enabled()` is not const - no `const CallConnectOptions(...)`.
- There are **no `call.camera` / `call.microphone` objects** - device controls are methods on `Call` (`setCameraEnabled`, `setMicrophoneEnabled`, `flipCamera`, `setAudioOutputDevice`) returning `Result`.
- `call.state` is a `StateEmitter`, not a `Stream`: `.value` for snapshots, `.asStream()` / `.valueStream` for `StreamBuilder`, `PartialCallStateBuilder` for slice rebuilds. Remote participants are `otherParticipants` (no `remoteParticipants`); pinning is `participant.pin != null`.
- `StreamVideoRenderer` requires `videoTrackType` (`SfuTrackType.video` / `.screenShare`).
- `leave()` for a single user; `end()` closes the call for everyone (needs permission) and must be followed by `leave()`. Call `leave()` in `dispose()` as a safety net.
- `muteAllUsers()` mutes **you** too - use `muteOthers()` for "mute everyone else". In audio rooms, dismissing a speak request is not a revoke.
- `disableClientCapabilities` must run **before** `join()`. `androidAudioConfiguration` is deprecated - use `audioConfigurationPolicy`. Noise cancellation needs `stream_video_noise_cancellation`; filters need `stream_video_filters`.
- **Ringing:** a fresh call id per ringing call (`Uuid().v4()`), never ring yourself, and every callee must have connected at least once. See [`push.md`](push.md).

### Livestream

- Never use `StreamCallContainer` in a livestream flow - use `LivestreamPlayer` for viewers (it handles join, backstage / ended states, PiP) and a custom host view. Its default `onCallDisconnected` leaves the call and **pops the route** when the host ends the stream, so the ended view (`livestreamEndedWidgetBuilder`, recordings) never shows - pass your own `onCallDisconnected` if the design has one. Through 1.7.1 the ended view also needs `state.endedAt`, which the `call.ended` event does not set (fix pending in GetStream/stream-video-flutter#1452), so on those versions render your own ended state when the disconnect reason is `DisconnectReasonEnded`.
- Derive live state from `call.state.value.isBackstage`; do not keep a separate `isLive` flag. Guard `join()` against double calls when a screen is re-entered.
- The creator gets `join-backstage` via `MemberRequest(userId: ..., role: 'host')` at create time; roles and grants are configured server-side.
- **Backstage is not private when `joinAheadTimeSeconds > 0`:** viewers may join that many seconds before `startsAt` and receive the host's audio/video before `goLive()`. Keep it at 0 unless a pre-show lobby is wanted, or keep the host muted until live.
- HLS must be started (`goLive(startHls: true)` / `startHLS()`); `egress.hlsPlaylistUrl` arrives a few seconds later. HLS viewers do not `join()` and are not counted as participants; expect 10-30s latency. Create the `VideoPlayerController` in `initState`.
- High-scale hosts: `join(hintHighScaleLivestreamPublisher: true)`. Never show publish controls to viewers.

---

## Push notifications (Chat push, Video ringing)

Full runbook: [`push.md`](push.md). The traps:

- Provider `name`s created in Stream must **exactly** match the names in code (`pushProviderName:` / `StreamVideoPushProvider.apn(name:)` / `.firebase(name:)`).
- Real device only for iOS push and VoIP; the Push Notifications capability is mandatory (no `aps-environment` = silently dropped pushes).
- The FCM background handler must be a **top-level** `@pragma('vm:entry-point')` function; it runs in a separate isolate where no singleton exists.
- Chat: push needs channel **membership**, never fires while the user's WebSocket is open, and `removeDevice` must run **before** `disconnectUser`.

---

## Feeds

- **The package is `stream_feeds` (plural, v3).** `stream_feed` and `stream_feed_flutter_core` are the deprecated v2 SDK with a different API (`StreamFeedClient`, `setUser`, `FlatFeed`, `FeedBloc`) - never use or suggest them.
- Most calls return `Result<T>` - check it (`fold` / `getOrThrow()`); a failed like must not leave an optimistic count behind. The connected user is `client.user`.
- The built-in feed groups (`user`, `timeline`, `notification`, `foryou`, `story`, `stories`) already exist - do not create them.
- A user's timeline does not show their own posts unless the timeline follows their own `user` feed - set this up unconditionally on first connect (see [`setup.md`](setup.md)).
- Comments are a real Comments API (`addComment`, threaded), not a reaction with a text payload.
- **No pre-built UI.** Build every feed screen with Flutter widgets. Default to **Twitter-style** (home timeline, activity card with avatar / name / @handle / time / text / comment + like row, compose, profile with follow button, notifications) without asking; deviate only when the user explicitly asks (Instagram grid, Reddit-style votes, photo-first). The style changes widget composition only - SDK calls are the same.
- Never trigger `queryMore*` from `itemBuilder` on every rebuild - gate it on scroll position and a loading flag.
