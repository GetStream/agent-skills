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
- **Livestream chat:** use the `livestream` channel type and skip offline persistence in the app. The recommended settings (read events, typing indicators, connect events, uploads and custom events off; slow mode for high traffic) live on the **channel type**, so they apply to every `livestream` channel in the app. Source: the "Livestream chat" row in [`docs-map.md`](docs-map.md).

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

`guest` is stricter than `user` and needs the grants too. Check the current grants with `getstream api GetChannelType --name <type>` - defaults depend on the app's history. Grant what is missing in Dashboard -> Chat -> Roles & Permissions (permissions v2) or via `UpdateChannelType` - it replaces the whole `grants` object, so resubmit every role with your change. Pick the channel type to fit the vertical: `messaging` (membership-gated DMs/groups), `team` (workplace), `livestream` (public read/write, guests and anonymous viewers), `agent` (user-to-LLM; `user` and `guest` can create agent channels from the client). Never give the app the secret or an `admin` role. Reference: the "Permissions / channel types" row in [`docs-map.md`](docs-map.md).

### Version

This skill targets **`stream_chat_flutter` / `stream_chat_flutter_core` v10**. v9 and earlier have different widget names, controllers, theming and reaction/delete APIs. If the project pins 9.x, stop and follow [`setup.md`](setup.md) "Version prerequisite".
### Pitfalls the docs do not shout about

- **Builder placement differs per widget.** `StreamChannelListView` takes its builders top-level; `StreamMessageListView` puts behavior flags in `config: StreamMessageListViewConfiguration(...)` and slot builders (`empty` / `loading` / `error`) in `builders: StreamMessageListViewBuilders(...)`, while `messageBuilder`, `parentMessage`, `threadBuilder`, `onReplyTap` stay top-level.
- **Channel and thread screens - ready-made or composed.**
  - **Ready-made:** `StreamChannelPage` is the full channel screen (header, message list, composer, with reply, edit, voice recording and threads): `StreamChannel(channel: channel, child: const StreamChannelPage())`. Its threads open `StreamThreadPage(parent: parent)`.
  - **Composed** (when you need header params or list-level builders): `StreamChannelHeader` + `StreamMessageListView` + `StreamMessageComposer`. For threads, pass `StreamMessageListView(threadBuilder: (_, parent) => ThreadPage(parent: parent!))` - the list wraps the page in `StreamChannel`. `ThreadPage` is your `StatefulWidget` taking the parent `Message`, with a `late final StreamMessageComposerController(message: Message(parentId: parent.id))` field disposed in `dispose()`, and a `Scaffold` with `StreamThreadHeader(parent: parent)`, `StreamMessageListView(parentMessage: parent)` and `StreamMessageComposer(messageComposerController: _controller)` (not `const` in v10). Recreate the controller in `didUpdateWidget` if the parent can change.
- **Voice recording default:** `StreamMessageComposer(...)` defaults `enableVoiceRecording` to `true`; `MessageComposerProps(...)` / `StreamMessageComposer.fromProps(...)` default it to `false` - pass `enableVoiceRecording: true` when you build the props yourself.
- **Initial load:** `StreamChannelListView` and the other `Stream*ListView` / `PagedValueListView` widgets call `doInitialLoad()` themselves; call it in `initState` when you drive a controller from your own widget.
- **Filters:** it is `Filter.in_` (underscore), and the sort parameter is `channelStateSort:`. The token user must be a member of seeded channels or `Filter.in_('members', [userId])` returns nothing.
- **Message search:** pass exactly one of `searchQuery` / `messageFilter` (it asserts otherwise), and throttle input. The search controller pages with a `String` key: `PagedValueListenableBuilder<String, GetMessageResponse>`.
- **Polls** must be enabled on the channel type in the Dashboard before the composer shows them. **Drafts** are on by default.
- **Reactions** take a `Message` and a `Reaction` object (`channel.sendReaction(message, Reaction(type: 'like'))`), not an id + string. Counts live on `message.reactionGroups`. Configure reactions once in `StreamChat(configData: StreamChatConfigurationData(reactionIconResolver: ..., reactionType: ..., reactionPosition: ...))` - the resolver (subclass `DefaultReactionIconResolver`) is the type -> emoji map that the message reactions, picker and detail sheet read; custom reaction widgets read it via `StreamChatConfiguration.of(context).reactionIconResolver`.
- **Composer edit mode is explicit:** `controller.editMessage(msg)` enters it; `clear()` does **not** exit it - call `cancelEditMessage()`.
- **`ClientState` collections are immutable** (`client.state.channels` / `users` throw on mutation). Let the SDK manage state through queries and `watch()`.
- **`StreamChatCore` sets `recoverStateOnReconnect = false`.** Channels you watch outside a list controller need a re-query on `EventType.connectionRecovered`. Do not mix `StreamChatCore` and `StreamChat` in one tree.
- **`channel.state` is null before `watch()` / `query()`.** Custom message lists paginate manually (`channel.query(messagesPagination: ...)`).
- **Split view:** key the `StreamChannel` with `ValueKey(channel.cid)` so switching channels rebuilds its state.
- **Offline:** assign `client.chatPersistenceClient` **before** `connectUser`; flush on logout with `disconnectUser(flushChatPersistence: true)`.
- **Logout:** `await client.disconnectUser()` closes the WebSocket and resets the client state; then navigate out of the chat routes.

### Design fidelity

- **Matching a reference design is not a theming task - there are TWO axes.** When the request carries a target appearance (screenshot, Figma, "make it look like <app>", or a migration's source app), run [`design-matching.md`](design-matching.md) and decompose every region first. Setting the bubble color and wallpaper and stopping is the known failure - the composer button set, metadata placement (author / timestamp / receipts relative to the bubble), bubble tail, header and date-separator pill are **structural** and need widget replacement. The grouped 1/2/3/4+ photo collage is already the default - do not rebuild it. The axes: **theming** (`StreamTheme` for foundations + the message row and every leaf widget; `StreamChatThemeData` for the chat composite widgets only) and **structure** (the component factory - core slots on `StreamComponentBuilders`, chat slots via `streamChatComponentBuilders(...)` - plus per-widget builders). Docs: the "Theming" and "Component factory" rows in [`docs-map.md`](docs-map.md).
- **Colors come from `StreamTheme`** (a `ThemeExtension` on `MaterialApp.theme.extensions`, built with `StreamColorScheme.fromSeed(...)` / `.light()` / `.dark()`), not from the Material `ColorScheme`. Fetch the theming page before writing any theme code.
- **Padding / insets / corner radius are theme VALUES, never a reason to replace a widget.** They live on `StreamTheme.messageItemTheme` (bubble / text / attachment padding, shapes) as content-kind-resolved `StreamMessageLayoutProperty` values - override with `resolveWith(...)`, preserving the branches you are not changing. If a token is not on `StreamChatThemeData`, look on `StreamTheme` before concluding it does not exist.
- **Overriding a composite slot drops every sub-feature the default rendered.** `messageItem` / `messageBuilder`, `messageComposer` (+ input sub-slots) and `itemBuilder` draw the incoming avatar, grouping, reactions, replies, delivery status - or the composer's send / voice / confirm-edit / slow-mode state machine. Before overriding one, read the default widget's `build()` in the pinned source, enumerate every sub-widget, and reproduce each (reuse the SDK's public sub-widgets) or tell the user what you dropped. **Never return a public widget from its own slot override** (`StreamMessageItem.fromProps`, `StreamMessageBubble`, `StreamMessageComposer`) - it re-enters the factory and stack-overflows; wrap the barrel-exported `Default*` widget instead (`DefaultStreamMessageItem`, `DefaultStreamMessageBubble`, `DefaultStreamMessageComposer`, `DefaultStreamMessageComposerInput`). (`StreamMessageItem.fromProps` is fine inside the per-widget `messageBuilder`.)
- **Match dimensions by MEASURING, not eyeballing - then verify and iterate.** Find the screenshot scale (`sips -g pixelWidth -g pixelHeight`; divide by 2/3 for iOS shots, by the density bucket for Android) and work in logical pixels. A match is unverified until you run, seed data that triggers every region (incoming + outgoing, a same-author run, album, reactions, reply, long text, date separator), open the real screen, and iterate region by region ([`design-matching.md`](design-matching.md) Steps 1 + 5).

---

## Video

### Build blockers (the docs do not cover these)

- **iOS deployment target 15.0 (Chat UI, Video, Firebase) under Swift Package Manager.** Flutter 3.32+ uses SPM by default, so a fresh `flutter create` has **no `ios/Podfile`** - do not add one just to set the target. The Flutter 3.44 template targets iOS 13.0, while `stream_chat_flutter` (via `file_picker`) and `stream_video_flutter` need 14.0 and `firebase_core` needs 15.0. Set the target to 15.0 in **both** `ios/Runner.xcodeproj/project.pbxproj` (`IPHONEOS_DEPLOYMENT_TARGET`, all three configs) **and** `ios/Flutter/AppFrameworkInfo.plist` (`<key>MinimumOSVersion</key><string>15.0</string>`, which drives the generated plugin package's platform). Only if a Podfile already exists, also set `platform :ios, '15.0'` there.
- **SPM can flood the analyzer with phantom errors** from the SDK's `example/` and `test/` sources copied into `build/`. Add `build/**` under `analyzer: exclude:` in `analysis_options.yaml` (the 3.44 template has no `analyzer:` block; if the file has one, extend it - a duplicate mapping key makes the analyzer reject the whole file). Trust `flutter analyze` over IDE squiggles.
- **Android:** new projects use the Kotlin DSL (`android/app/build.gradle.kts`); older ones use Groovy `build.gradle`. Raise floors with `minSdk = maxOf(24, flutter.minSdkVersion)` (and `compileSdk = maxOf(36, flutter.compileSdkVersion)` when needed) - Groovy `minSdkVersion 24` snippets do not parse in `.kts`.
- **Android PiP:** extend `StreamFlutterActivity` / `StreamFlutterFragmentActivity` in `MainActivity` (or wire `PictureInPictureHelper` into your own activity), set `android:supportsPictureInPicture="true"` on the activity, and create the client with `StreamVideoOptions(keepConnectionsAliveWhenInBackground: true)`.
- **Runtime permissions:** manifest entries are not enough on Android 6+ - request camera + microphone (`permission_handler`) before joining. Missing iOS `NSCameraUsageDescription` / `NSMicrophoneUsageDescription` = silent empty tracks.
- **`CompositeSubscription`** (returned by the ringing observers) is an rxdart type, not re-exported - add `rxdart` and import it; cancel with `dispose()` / `cancel()` / `clear()` (there is no `cancelAll()`, despite what some docs snippets show).

### Auth

- Expiring tokens: pass a `tokenLoader`; the SDK calls it for the first token and on every expiry.
- **Guests** (`User.guest`, no token): the server assigns a *generated* id that differs from the one you passed - after `connect()`, read `StreamVideo.instance.currentUser.id` and use that everywhere. The `guest` role has minimal capabilities: on `livestream` (and other restrictive types) it cannot read or join a call until you grant `read-call` + `join-call` (plus `create-call` if a viewer may open the call first) in Dashboard -> Video & Audio -> Call Types -> <type> -> Roles & Permissions. Surface this **before** building a guest-viewer flow.
- **Anonymous** users cannot open a WebSocket (no events, `connect()` rejects them) and need a token pinning `call_cids`. Watch-only livestream viewers only.

### Calls and state

- **`join()` creates the call if it does not exist** (it always sends `create: true`). Call `getOrCreate()` first only to set members, ringing or custom data.
- **`join()` returns a `Result`, it does not throw.** Always `fold` it; ignoring a failure leaves the UI on a dead call screen. `StreamCallContainer` handles its own `join()` Result and reports failures through `onCallDisconnected` (`CallDisconnectedProperties.reason`); for a custom failure UI, call `join()` yourself and render `StreamCallContent`.
- **Camera / mic on join come from the call type's settings** (`camera_default_on`, `mic_default_on`). A `CallConnectOptions` you pass sets camera, microphone, screen share, camera facing and speaker together - each field you omit takes its constructor default (disabled / front / speaker off). Pass both explicitly: hosts `camera: TrackOption.enabled(), microphone: TrackOption.enabled()`; viewers `disabled`; add `cameraFacingMode` / `speakerDefaultOn` when the call type uses them. `TrackOption.enabled()` is not const - no `const CallConnectOptions(...)`.
- There are **no `call.camera` / `call.microphone` objects** - device controls are methods on `Call` (`setCameraEnabled`, `setMicrophoneEnabled`, `flipCamera`, `setAudioOutputDevice`) returning `Result`.
- `call.state` is a `StateEmitter`, not a `Stream`: `.value` for snapshots, `.asStream()` / `.valueStream` for `StreamBuilder`, `PartialCallStateBuilder` for slice rebuilds. Remote participants are `otherParticipants` (no `remoteParticipants`); pinning is `participant.pin != null`.
- `StreamVideoRenderer` requires `videoTrackType` (`SfuTrackType.video` / `.screenShare`).
- `leave()` for a single user; `end()` closes the call for everyone (needs permission) and must be followed by `leave()`. Call `leave()` in `dispose()` as a safety net.
- `muteAllUsers()` mutes **you** too - use `muteOthers()` for "mute everyone else". In audio rooms, dismissing a speak request is not a revoke.
- `disableClientCapabilities` must run **before** `join()`. `androidAudioConfiguration` is deprecated - use `audioConfigurationPolicy`. Noise cancellation needs `stream_video_noise_cancellation`; filters need `stream_video_filters`.
- **Ringing:** a fresh call id per ringing call (`Uuid().v4()`), never ring yourself, and every callee must have connected at least once. See [`push.md`](push.md).
- **Call screen callbacks replace the default action:** with `onAcceptCallTap` / `onDeclineCallTap` / `onCancelCallTap` on `StreamCallContainer`, call `accept()` / `reject()` / `leave()` in your callback.
- **Custom call controls:** with a custom `callControlsWidgetBuilder` on `StreamCallContent`, also pass `callAppBarWidgetBuilder: (context, call) => CallAppBar(call: call, showBackButton: false, showLeaveCallAction: false)` so the screen has one leave action.

### Livestream

- Never use `StreamCallContainer` in a livestream flow - use `LivestreamPlayer` for viewers (it handles join, backstage / ended states, PiP) and a custom host view. Its default `onCallDisconnected` leaves the call and **pops the route** when the host ends the stream, so its ended view (`livestreamEndedWidgetBuilder`, recordings) never shows. To keep it, pass an `onCallDisconnected` that returns without popping on `DisconnectReasonEnded` ("Livestream: ... watch" in [`docs-map.md`](docs-map.md)). Viewer UIs key "ended" on `state.endedAt`, which the `call.ended` event sets in releases after 1.7.1; up to 1.7.1 it does not, so on those versions show your own ended state on `DisconnectReasonEnded`.
- Derive live state from `call.state.value.isBackstage`; do not keep a separate `isLive` flag. Guard `join()` against double calls when a screen is re-entered.
- The creator gets `join-backstage` via `MemberRequest(userId: ..., role: 'host')` at create time; roles and grants are configured server-side.
- **Backstage and `joinAheadTimeSeconds` are call-type settings:** set them on the `livestream` call type (Dashboard -> Video & Audio -> Call Types, or `UpdateCallType`; read them with `getstream api GetCallType --name livestream` - backstage is on by default). A per-call override (`getOrCreate(backstage:)` / `update(backstage:)`) requires the `update-call-settings` capability, which on `livestream` only `admin` has.
- **Backstage is not private when `joinAheadTimeSeconds > 0`:** viewers may join that many seconds before `startsAt` and receive the host's audio/video before `goLive()`. Keep it at 0 on the call type unless a pre-show lobby is wanted, or keep the host muted until live.
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
- **`state.following` / `followers` / `members` stay empty unless the query asks for them.** Read the feed through `client.feedFromQuery(FeedQuery(fid: ..., followingLimit: / followerLimit: / memberLimit: ...))` before relying on those lists (e.g. to show a Follow / Unfollow button or guard a follow). Each limit is at most 100.
- **Who follows whom:** who a user follows is the `following` of `timeline:<me>`; their followers are the `followers` of `user:<me>`.
- **Notifications:** reactions, comments and follows add an activity to the target's `notification` feed when you pass `createNotificationActivity: true`.
- `StateNotifierBuilder` comes from `flutter_state_notifier`, a separate dependency.
- **No pre-built UI.** Build every feed screen with Flutter widgets. Default to **Twitter-style** (home timeline, activity card with avatar / name / @handle / time / text / comment + like row, compose, profile with follow button, notifications) without asking; deviate only when the user explicitly asks (Instagram grid, Reddit-style votes, photo-first). The style changes widget composition only - SDK calls are the same.
- Never trigger `queryMore*` from `itemBuilder` on every rebuild - gate it on scroll position and a loading flag.
