# Stream Flutter - integration review

Flutter checks for a read-only integration review. Run the procedure in stream
skill's integration-review.md; this file uses the same section names, and each
bullet here replaces the generic bullet on the same topic. The "Livestream"
section does the same for stream skill's livestream-review.md.

Chat SDK pages are under `getstream docs chat-sdk/flutter`, Chat API pages
under `getstream docs chat/flutter-dart`, Video pages under `getstream docs
video/flutter`. The Chat go-live checklist is `guides/go-live-checklist.md`.
Video has no go-live checklist on Flutter, so the Video bullets cite its
guides or the SDK code. Bullets that start with "Video", and the Calls and
Livestream sections, are Video checks; in a Chat-only app they are N/A.

Symbols were checked against `stream_video_flutter` 1.7.2 and
`stream_chat_flutter` 10.6.0. Review the versions `pubspec.lock` pins: read
the SDK source in `~/.pub-cache` at those versions, and adapt a check that
names a newer API. Chat 9.x and earlier differ too much for this file; scope
the upgrade with `guides/migration-guide-10-0.md` and review the rest from
the 9.x source.

## Measure, don't guess

A code read can't count requests: widgets rebuild, and a call made in `build`
runs on every rebuild. Without a running app, list request counts as
unverified. The review changes no code; these are for a debug run the
developer makes or agrees to:

- Chat: `StreamChatClient(apiKey, logLevel: Level.ALL)` and a
  `logHandlerFunction` that prints. The default level is `Level.WARNING`,
  and the SDK's loggers are detached, so a listener on `Logger.root` sees
  nothing. Docs: `basics/logging.md`.
- Video: `StreamVideoOptions(logPriority: Priority.verbose)`. The default is
  `Priority.none`, which logs nothing. Coordinator requests log under the
  `SV:CoordClient` tag with the endpoint in brackets (`[joinCall]`,
  `[getCall]`, `[getOrCreateCall]`, `[queryCalls]`): count those lines for
  one viewer opening one stream. Source: SDK code.
- Rebuild counts: `flutter run --profile` and DevTools "Track widget
  rebuilds". Profile mode, not debug. Docs:
  `guides/livestream-best-practices.md`.

## Initialization

- `StreamChatClient` is created once, before `runApp` or in a service the
  app owns, never in `build`, a getter, or a route builder. `StreamChat` sits
  above every Stream Chat widget, usually in `MaterialApp.builder`. Docs:
  `guides/initialize-stream-chat-widget-tree.md`.
- Video: `StreamVideo(...)` is created once per signed-in user. The
  constructor registers a singleton and throws if one exists; an account
  switch calls `StreamVideo.reset(disconnect: true)` first. Passing
  `failIfSingletonExists: false` to get past the error is a finding: it
  disconnects the existing instance, and with it a call in progress.
  Creating the client when a call screen opens, or once per screen, is a
  finding too. Source: SDK code.
- Video: for ringing, the client is built at app start from the stored
  session, and in the FCM background isolate with `StreamVideo.create`.
  Read push.md.
- Tokens: Chat connects with `connectUserWithProvider(user, provider)`,
  Video is built with `tokenLoader:`. `connectUser(user, token)` and
  `userToken:` keep the one token they were given, so an expiring token is
  never refreshed. `client.devToken(...)` in a shipped path is Fix now.
  Docs: `guides/go-live-checklist.md` (Chat), `guides/client-auth.md`
  (Video).
- Nothing secret is in a `--dart-define` value or in a `.env` file listed
  under `flutter: assets:`. Both end up inside the app. The API key is
  not a secret.
- Guest users: the server generates the id, so the app reads
  `StreamVideo.instance.currentUser.id` after `connect()` instead of
  reusing the id it passed. Anonymous Video users open no WebSocket and
  receive no events. Docs: `guides/client-auth.md`.

## Typical session

- Chat `connectUser*` is awaited once, from session or login code, before
  any chat UI shows. A second connect while one is in flight throws "User
  already getting connected". It throws on an invalid token too: the catch
  sends the user back to login and clears stored credentials.
- Video `connect()` returns a `Result`, and so does every call action
  (`getOrCreate`, `join`, `goLive`, `end`). They report a failure through
  the result, not by throwing, so a result that is never folded or checked
  hides it. Docs: `guides/livestreaming.md`, Error states.
- No manual socket handling on app lifecycle. `StreamChat` closes the Chat
  socket after `backgroundKeepAlive` (15 seconds by default) and reopens it
  on resume; the Video client does the same for its socket unless a call is
  active or `keepConnectionsAliveWhenInBackground` is set. An app calling
  `closeConnection()` / `openConnection()` or `disconnect()` from its own
  lifecycle observer fights both. Source: SDK code.
- `StreamChat` (and `StreamChatCore`) set `recoverStateOnReconnect = false`
  on the client. Channels watched outside a list controller are re-queried
  on `EventType.connectionRecovered`, or they miss what happened while
  offline. This is the exception to the generic check against re-querying
  on reconnect. Source: SDK code.

## Disconnecting

- Chat logout: `removeDevice(token)` first, then `await
  client.disconnectUser()`, then navigation. With offline storage,
  `disconnectUser(flushChatPersistence: true)`. Docs:
  `guides/go-live-checklist.md`; read push.md.
- Video logout: `await StreamVideo.reset(disconnect: true)`. Disconnecting
  unregisters the push device when a push manager is configured. Guard
  with `StreamVideo.isInitialized()`. Source: SDK code.
- An app with both products logs out of both.

## Fetching channels

- A `StreamChannelListController` is a `State` field created once and
  disposed in `dispose()`, not built in `build`. `doInitialLoad()` runs
  once; the `Stream*ListView` widgets call it themselves. Docs:
  `guides/go-live-checklist.md`.
- The filter has `Filter.in_('members', [userId])` plus a type, and the
  sort is `channelStateSort` on `last_message_at` or `last_updated`.
- Event filtering: each list passes an `eventHandler` that extends
  `StreamChannelListEventHandler` and ignores channels outside its filter
  in `onMessageNew`, `onNotificationMessageNew`, and
  `onNotificationAddedToChannel`. The default `onMessageNew` re-queries
  the list for a message in a watched channel that isn't in it, so a busy
  livestream channel watched next to a channel list costs a list query per
  message. Source: SDK code.
- `presence: true` is the controller's default. Set it to false when the
  list shows no online state.

## Fetching calls

- `StreamVideo.instance.queryCalls(filterConditions:, sorts:, limit:,
  next:)` with a filter scoped as the generic check says. For a list of
  live streams: `'backstage': false` and `'ended_at': {r'$exists': false}`.
  `watch: true` only where the list shows live state, and then no
  re-query on a timer. Docs: `guides/querying-calls.md`,
  `guides/livestreaming.md` (Finding live streams).

## Search

- Message search goes through `StreamMessageSearchListController.search`,
  which debounces and drops stale results. A custom user search debounces
  itself.

## Rendering and customization

- Extension points are `StreamTheme` and `StreamChatThemeData` for theming,
  and the component builders (`StreamComponentBuilders`,
  `streamChatComponentBuilders`) plus per-widget builders for structure.
  Read RULES.md, Design fidelity.
- An override of a composite slot (`messageItem`, `messageComposer`)
  renders everything the default widget rendered, or wraps the `Default*`
  widget.
  Returning the public widget from its own slot overflows the stack.
- No controller, channel, `Call`, query, or stream subscription is created
  in `build` or a `StatelessWidget` body. Controllers are disposed and
  subscriptions cancelled in `dispose()`.
- Video: screens read call state through `PartialCallStateBuilder` or
  `call.partialState(...)` with a static or top-level selector. An inline
  closure as the selector resubscribes on every parent rebuild, and a
  `StreamBuilder` on the whole `call.state` rebuilds the screen on every
  participant change. Docs: `guides/livestreaming.md`,
  `guides/call-and-participant-state.md`.
- A custom message list keys its items with `ValueKey(message.id)`. Docs:
  `guides/livestream-best-practices.md`.

## Calls

- The `Call` from `StreamVideo.instance.makeCall(...)` has one owner for
  the length of the session: the screen's `State`, or an object that
  outlives the screen when the call continues in picture-in-picture or
  across routes. The owner calls `leave()` when the session ends; a
  screen that owns the call does it in `dispose()`.
- `join()` returns a `Result`. `StreamCallContainer` handles its own join
  and reports a failure through `onCallDisconnected`; a custom screen folds
  the result and shows the failure.
- Camera and microphone are requested at runtime before a publishing join
  (for example `permission_handler`), and a denial is handled. Manifest
  and `Info.plist` entries are needed as well, the iOS usage strings
  included. Docs: `basics/installation.md`.
- A `CallConnectOptions` sets every device at once: a field you leave out
  takes the constructor default, which is disabled. `CallConnectOptions(
  camera: TrackOption.enabled())` joins with the microphone off. Without
  the argument, the call type's defaults apply. Source: SDK code.
- The UI follows `state.status`: `CallStatusReconnecting` is shown as such,
  and only `CallStatusDisconnected` or `CallStatusReconnectionFailed` end
  the screen. Docs: `ui-cookbook/network-disruption.md`.
- One call at a time: with the default `allowMultipleActiveCalls: false`,
  joining a second call leaves the first with `DisconnectReasonReplaced`.
  A screen that treats every disconnect as an error shows one here.
- Ringing: read RULES.md (Calls and state) and push.md.

## Push

Read push.md for the chain; it has the Flutter traps. In review terms:

- Provider names in code (`pushProviderName:`,
  `StreamVideoPushProvider.apn(name:)` / `.firebase(name:)`) match the
  dashboard for every flavor and every Stream app the build can point at.
- Chat: `addDevice` runs after `connectUser` and on every
  `onTokenRefresh`. The FCM background handler is a top-level
  `@pragma('vm:entry-point')` function.
- Video: the background handler builds its client with
  `StreamVideo.create` from credentials persisted at login. An app that
  keeps them only in memory can't ring after the process dies.
- iOS: the Push Notifications capability is present (`aps-environment`),
  and `apn_development` on the provider matches the build type.

## Unread counts

- Badges come from `client.state.totalUnreadCountStream` /
  `unreadChannelsStream` and `channel.state.unreadCountStream`, not from
  summing loaded channels.
- `livestream` channels report 0 because read events are off there.
  `StreamChatClient(isLocalUnreadCountEnabled: true)` keeps a local count
  for those channels only. Docs: `guides/livestream-best-practices.md`.

## Scale and release

- No `chatPersistenceClient` is assigned in an app whose chat is livestream
  chat. With mixed use, weigh it: persistence writes every incoming message
  to SQLite.
- `maximumMessageLimit` is set on the message list for livestream channels
  (200 to 500). It is null by default, so memory grows for the length of
  the stream. A custom list on `stream_chat_flutter_core` caps what it
  keeps itself.
- Release builds use `Level.WARNING` or `Level.SEVERE` for Chat and leave
  Video's `logPriority` at `Priority.none`, or at `Priority.error` routed
  to the app's crash reporter.
- In `pubspec.lock`, `stream_video`, `stream_video_flutter`, and the other
  `stream_video_*` packages are on one version, and so are `stream_chat`,
  `stream_chat_flutter_core`, `stream_chat_flutter`, and
  `stream_chat_persistence`. A `dependency_overrides` entry that points a
  Stream package at a branch or a local path is a finding; one pinned to
  a commit, with the reason written down, is a note.

Docs: `guides/livestream-best-practices.md`, `guides/go-live-checklist.md`.

## Livestream

Flutter detail for stream skill's livestream-review.md, group by group. A
bullet here replaces the generic bullet only where it covers the same thing;
every generic check without a bullet here still applies. Docs:
`guides/livestreaming.md`, `ui-cookbook/hosting-a-livestream.md`,
`ui-cookbook/watching-a-livestream.md`. Read RULES.md, Livestream, as well.

### Viewer join path

- Viewers load the call with `call.get()`, once, then join. `get()` watches
  by default, so the call object follows backstage, live, and ended from
  then on. The docs' viewer samples use `getOrCreate()`, which is the same
  request count but creates the call when it doesn't exist.
- Flutter has no create flag to turn off: `join()` always asks to create.
  So only the call type stops a viewer from creating a call. PASS when the
  viewer's role has no `create-call` grant. A viewer path that uses
  `get()` and stops on its failure never runs `join()` for a call that
  doesn't exist, which prevents the accident; with the grant unread, that
  is a PASS with the grant listed as unverified. Source: SDK code.
- `LivestreamPlayer` decides when to join from the call's state. On a call
  that was never loaded, the state says "not in backstage", so the default
  `autoJoinAsap` joins at once, is refused if the host isn't live, and
  that `Call` object can't be joined again. Loaded first, it waits and
  joins when the call goes live. PASS: one `get()`, then the player. FAIL:
  the player on a fresh `makeCall`, or `manualJoin` with a timer that
  retries `join()`. Source: SDK code.
- `LivestreamPlayer` doesn't surface a failed join: the call disconnects,
  and the default `onCallDisconnected` leaves and pops the route without a
  message. Pass an `onCallDisconnected` that tells a failure
  (`DisconnectReasonFailure`, `DisconnectReasonReconnectionFailed`) from
  the end of the stream (`DisconnectReasonEnded`) and shows it. Source:
  SDK code; docs: `ui-cookbook/watching-a-livestream.md`.
- `join()` retries by itself when the media server can't be reached
  (`maxJoinRetries`, 3 by default, with backoff), and sends a join the API
  refuses only once. A failed join leaves the call, and a `Call` that was
  left can't be joined again: a later `join()` on the same object fails
  with "call was left" and sends nothing. So an app loop or timer around
  `join()` on one `Call` never succeeds, and viewers who came early stay
  stuck after the host goes live. The same loop with a new `makeCall` per
  attempt is a request loop in every waiting viewer. Both are FAILs. A
  retry button makes a new `Call`. Source: SDK code.
- From 1.7.0 a second `join()` while one is in flight returns the first
  one's result. Before that, the screen guards against double joins when
  it is re-entered or resumed. Source: SDK code.
- Anonymous viewers (`User.anonymous()`) receive no events, so they can't
  wait for Go Live on the call's state, and their token needs the
  `call_cids` claim. Guest viewers (`User.guest`) have no grants on the
  default `livestream` type until the `guest` role is given `read-call`
  and `join-call`. Docs: `guides/client-auth.md`.

### Host path

- The documented host flow is `getOrCreate(members: [MemberRequest(
  userId: <own id>, role: 'host')])` and then `join()`, both results
  checked. As the creator the host can join backstage and publish. A call
  created by the backend is as good: it sets the host as `created_by_id`,
  or the call type grants the host's role what the generic check lists.
- `goLive()` returns a `Result` that the UI checks, and the host screen
  shows backstage or live from `state.isBackstage`, not from a flag set
  when the button was tapped. `goLive(startHls: true, startRecording:
  true)` starts those with it.
- `end()` only works while the call is active; in any other status it
  returns a failure and the call is not ended on the server. The host
  flow checks the result, then calls `leave()`. Docs:
  `guides/livestreaming.md`.
- `leave()` in the host screen's `dispose()` is the documented safety net,
  and it also means that popping the screen takes the host out while the
  stream stays live. Back and swipe-back are guarded (for example
  `PopScope`) by a prompt that offers End, Stop Live, or stay. Source: the
  app code.
- Getting back in after a crash or an accidental leave: the host screen
  can be opened again for a call that is still live, and it builds a new
  `Call` for the same id, because a `Call` that was left can't be joined
  again. Source: SDK code.
- Publish state: the host joins without `connectOptions` (the call type's
  camera and microphone defaults apply) or passes camera and microphone
  both. See the `CallConnectOptions` check under Calls. The preview is
  `state.localParticipant`, with `isVideoEnabled` and `isAudioEnabled` for
  the indicators.
- Background, Android: `StreamBackgroundService.init(StreamVideo.instance)`
  runs after the client is built. It starts the foreground service for an
  active call; without one Android cuts camera and microphone access for
  an app in the background. The service needs the microphone permission
  granted before the call starts. Docs: `advanced/background-modes.md`.
- Background, iOS: `UIBackgroundModes` has `audio`. By default iOS gives
  no camera access in the background, so viewers get audio only; the docs
  describe when multitasking camera access changes that. Check which case
  the app is in, and that the host is told when the camera stops. Docs:
  `advanced/background-modes.md`, `advanced/picture-in-picture.md`.
- These two are setup checks. Whether the stream really continues when
  the phone is locked or a phone call comes in is unverified without a
  device test: list it under event readiness.
- `StreamVideoOptions(muteVideoWhenInBackground: true)` or
  `muteAudioWhenInBackground: true` mutes a host who switches apps, and
  unmutes on return. In a host app, report it and ask whether that is
  intended. Source: SDK code.
- The SDK doesn't keep the screen awake. The host screen holds a wake lock
  for the length of the stream. Source: the app code.
- Reconnecting: `reconnectTimeout` is `Duration.zero` by default, which
  means the SDK keeps trying. The host screen shows
  `CallStatusReconnecting` and doesn't call `end()` or `leave()` on it.
  Docs: `ui-cookbook/network-disruption.md`.
- For a large audience the host joins with
  `join(hintHighScaleLivestreamPublisher: true)`. Docs:
  `guides/livestreaming.md`.
- Resolution: the call type's target resolution applies unless the join
  passes `targetResolution` in `CallConnectOptions`. See the generic 720p
  check and `streaming/mobile-livestreaming.md` in `getstream docs
  video/api`.

### Call-type settings

- A per-call backstage override (`getOrCreate(backstage:)`,
  `update(backstage:)`) needs `update-call-settings`, which on the default
  `livestream` type only `admin` has. From a host client it fails; set it
  on the call type or server-side.
- Every `call.update(...)` clears `startsAt` unless the current value is
  passed again. A scheduled stream that is updated without it loses its
  join-ahead window. Read RULES.md, Livestream.

### Audience-scale behaviour

- The viewer count is `state.participantCount`, the session's total with
  the host in it, not `state.callParticipants.length`: `callParticipants`
  is truncated to 250 on large calls. `anonymousParticipantCount` is
  reported next to it. Both update while joined and while only watching
  the call. The livestreaming guide's sample counts `callParticipants`,
  which is fine for a small room only. Docs:
  `guides/call-and-participant-state.md`.
- No `Timer.periodic` around `get()`, `queryCalls`, or `queryMembers` in
  the viewer app. `get()` and `queryCalls(watch: true)` keep the calls
  they returned current. A stream that starts later is not added to a
  watched query: refresh the list on pull or from the backend.
- `call.sendReaction` and `call.sendCustomEvent` send one request per
  call; the SDK doesn't throttle them. The reaction button animates every
  tap locally and sends on a timer (see the generic check for how often),
  and a failed `Result` is not retried. Source: SDK code.
- Chat messages and reactions don't rebuild the video. A `setState` on
  the screen that holds the player, or a `Future` created in `build`,
  rebuilds or re-runs everything under it: keep the player, the chat
  panel, and the reaction layer in separate widgets with their own state.
  Source: the app code.
- The end of the stream: from 1.7.2 `call.ended` sets `state.endedAt`, and
  the viewer's status becomes `CallStatusDisconnected` with
  `DisconnectReasonEnded`. Up to 1.7.1 `endedAt` is not set, so the ended
  view keys on the disconnect reason. With `LivestreamPlayer` the default
  pops the route; to show the ended view, pass an `onCallDisconnected`
  that doesn't pop on `DisconnectReasonEnded`. Nothing calls `join()`
  again afterwards. Read RULES.md, Livestream.
- With the ended view kept, `showRecordingsWhenEnded` (true by default)
  makes every viewer list the call's recordings at the moment the stream
  ends. Set it to false unless replays are offered there and the viewer
  role may list them. Source: SDK code.
- Chat next to the stream: a `livestream`-type channel watched once, a
  custom list on `stream_chat_flutter_core` or `StreamMessageListView`
  with `maximumMessageLimit`, and no offline storage. See Scale and
  release. Docs: `guides/livestream-best-practices.md`,
  `guides/adding-chat-to-video-livestreams.md`.

### Playback and event readiness

- Blocked audio: N/A in a native Flutter app.
- HLS: the SDK has no HLS player. An app that uses HLS starts it
  (`goLive(startHls: true)` or `startHLS()`), reads
  `state.egress.hlsPlaylistUrl`, and plays it with a player package whose
  controller is created in `initState`. HLS viewers don't `join()`. N/A
  when viewers use `LivestreamPlayer` or a custom WebRTC view.
- Indicators: `livestreamNotConnectedBuilder` (or the default) shows
  reconnecting, `livestreamHostsUnavailableBuilder` (or the default)
  covers a joined viewer with no host video, and a custom view reads
  `participant.connectionQuality` and handles both states itself. Docs:
  `ui-cookbook/watching-a-livestream.md`,
  `ui-cookbook/network-quality-indicator.md`.
- Picture-in-picture: `MainActivity` extends `StreamFlutterActivity` (or
  the fragment variant), the activity has
  `android:supportsPictureInPicture="true"`, and the client is built with
  `keepConnectionsAliveWhenInBackground: true`. Docs:
  `advanced/picture-in-picture.md`.
- Versions: compare `pubspec.lock` with the latest releases on pub.dev and
  give both with the date. Below 1.7.0 (the in-flight join guard) and
  below 1.7.2 (`endedAt` on `call.ended`) the checks above behave
  differently; say so in the finding.
