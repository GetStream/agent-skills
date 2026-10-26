# Stream Android - integration review

Android checks for a read-only integration review. Run the procedure and the
generic checks in stream skill's integration-review.md first; this file adds
what's specific to the Chat Android SDK. Each check names the docs page to
confirm it against: SDK pages are under `getstream docs chat-sdk/android`, API
pages under `getstream docs chat/android`. The go-live checklist is
`guides/go-live-checklist.md`.

## Measure, don't guess

Identical in-flight requests are merged, which hides duplicates in a code
read. Without a running app, list request counts as unverified. When the app
can be run:

- Build the client with `debugRequests(true)`, use the app normally, then
  `ApiRequestsAnalyser.get().dumpRequestByName("QueryChannels")` to count calls.
- `logLevel(ChatLogLevel.ALL)` and filter logcat on `Chat:`. For push problems
  use an unfiltered capture: the useful exceptions come from WorkManager.
- `clientState.connectionState`, `user`, and `initializationState` show
  whether the app is connected as the right user.

Docs: `basics/debugging.md`, `basics/troubleshooting.md`.

## Setup

- New releases are on Stream's own Maven repository, not Maven Central. If
  `dependencyResolutionManagement.repositories` in `settings.gradle(.kts)`
  lacks `maven("https://stream-io-repo.com")`, the build works but can't
  resolve newer versions. An entry under `pluginManagement` doesn't count.
  When the SDK is a project or composite dependency, this only affects the
  helper libraries. Docs: `basics/installation.md`.
- `ChatClient.Builder.build()` runs in `Application.onCreate`. It opens no
  socket, so it's cheap. Built lazily, push stays broken until the user opens
  chat; built twice, the singleton is replaced and in-memory state lost.
- Flag builder options left over from testing or tuning in release:
  `disableDistinctApiCalls()` (docs: `client/guides/optimizations.md`),
  `forceInsecureConnection()`, a custom `baseUrl`, a custom `OkHttpClient` with
  aggressive timeouts or interceptors rewriting Stream requests.

## Session

- `connectUser` runs from the session layer, guarded with
  `getCurrentUser() == null` or `clientState.initializationState`. Push
  devices register on connect, so connecting only on a chat screen means no
  push for users who never open chat.
- A failed connect is handled from the `connectUser` result or a token-error
  connection state. `initializationState` becomes `COMPLETE` before the socket
  authenticates, so routing on it alone never sees an invalid token. Source:
  SDK code.
- No `disconnectSocket()` on background. It drops the lifecycle observer and
  the SDK stops reconnecting on foreground ("messages stop arriving after a
  while"). Docs: `client/guides/handling-user-connection.md`.
- Logout calls `disconnect(flushPersistence = true)`. `deleteDevice` defaults
  to `flushPersistence`, so `disconnect(flushPersistence = false)` leaves the
  device registered (SDK source; the docs don't cover `deleteDevice`).
  Account switch uses `switchUser`.

## Channel lists

- Lists come from `ChannelListViewModel` or `queryChannelsAsState` held in a
  ViewModel, not `queryChannels(...).enqueue {}` in `onResume`.
- No `forceNewRequest()` to get fresh data: it defeats de-duplication.
- No `watch = false` / `state = false` on the request followed by complaints
  that the list is stale.
- Sorting uses `QuerySortByField`, not `QuerySortByReflection`, on hot lists.
- Paging uses the ViewModel's load-more or
  `QueryChannelsState.nextPageRequest`.
- With several lists, each passes its own `chatEventHandlerFactory`: extend
  `DefaultChatEventHandler` and return `Skip` for events outside the list's
  filter. The default adds any member channel to every list ("channels show up
  in the wrong tab"). `WatchAndAdd` costs a request per event, so keep the
  condition before it tight. Docs: `client/channels.md`.

## Search

- Compose: `ChannelListViewModel` debounces (`searchDebounceMs`). XML: the
  debounce lives in `SearchInputView`, so a custom UI on `SearchViewModel` must
  debounce itself.

## UI and customization

- Customization goes through `ChatTheme` and `ChatComponentFactory` (Compose)
  or `ChatUI` and style transformers (XML). Copied SDK source is a finding:
  record which extension point was missing under "Ask Stream". Docs:
  `compose/general-customization/component-factory.md`.
- Actions are gated on `channel.ownCapabilities`, not hardcoded roles that
  drift from dashboard permissions. Docs:
  `compose/guides/implementing-own-capabilities.md`.
- Compose: no ViewModel built with `factory.create(...)` or inside
  `remember { }`, which skips the ViewModelStore so `onCleared` never runs;
  use `viewModel(key = ..., factory = ...)`. `viewModel()` inside an SDK
  screen that provides its own store is fine. State is collected with
  `collectAsStateWithLifecycle`. Source: SDK code and Android practice.
- A custom message list uses `watchChannelAsState`, not a one-off
  `queryChannel` plus polling.
- Every `subscribe` / `subscribeFor` anywhere in the app either takes a
  `LifecycleOwner` or keeps the returned `Disposable` and disposes it, e.g. in
  `onCleared`. Otherwise each screen visit adds a listener. Source: SDK
  code.
- A custom message list that supports jump-to-message calls
  `loadNewestMessages` alongside a send when `endOfNewerMessages` is false;
  otherwise the sent message lands in the old page. Docs:
  `client/state-layer-overview.md`.
- A custom `fileUploader(...)` for private storage has a matching `cdn(...)`
  that signs downloads, or uploads work but files don't load.
  `uploadAttachmentsNetworkType(UNMETERED)` keeps attachment messages pending
  on mobile data. Docs: `client/custom-cdn.md` for the CDN; the network type
  is SDK source only.

## Push

- `.notifications(...)` is called on the builder. Without it the builder
  disables push, and an empty generator list does the same. Only the first
  valid generator is used.
- A custom `FirebaseMessagingService` delegates to
  `FirebaseMessagingDelegate.handleRemoteMessage` before returning early on
  unknown payloads, and `onNewToken` calls `registerFirebaseToken`. Another
  SDK's service winning the manifest merge has the same effect. Docs:
  `guides/push-notifications/push-providers/firebase.md`.
- `providerName` matches the dashboard for every build variant ("works in
  debug, not in release").
- With expiring tokens, `NotificationConfig(tokenProvider = ...)` is set and
  can fetch a token without UI. Without it, a push received while the app is
  killed uses the last saved token and fails once it expires ("push only works
  if the app was open recently"). Docs: `guides/push-notifications.md`.
- A custom message list calls `dismissChannelNotifications` when a channel
  opens.
- Expected behavior, not bugs: no push while connected
  (`ignorePushMessageWhenUserOnline`), and `POST_NOTIFICATIONS` requested on
  launch unless `requestPermissionOnAppLaunch` returns false.
- Intermittent push: check the merged manifest for a dependency declaring
  `WAKE_LOCK` with a low `maxSdkVersion`. A `success` in the dashboard push log
  only means FCM accepted it.

## Unread

- App badge from `GlobalState.totalUnreadCount` or `channelUnreadCount`,
  per-channel badges from `Channel.unreadCount`.
- Livestream-type channels show 0 because read events are off there;
  `isLocalUnreadCountEnabled` tracks a local count. Docs:
  `client/livestream-chat.md`.

## Scale

- High-volume channel types are in `ignoredOfflineChannelTypes`, with
  `MessageLimitConfig.channelMessageLimits` set. It's unset by default, which is
  why memory grows in long livestream sessions.
- `messageBufferConfig` drops the oldest events when full: only where that's
  acceptable. `userPresence = false` if presence isn't shown;
  `fastEventParsing` for very high event throughput.
- `isAutomaticSyncOnReconnectEnabled = false` with nothing replacing it
  leaves gaps after reconnects.
- Offline sends older than `syncMaxThreshold` are dropped, not retried ("my
  queued message never sent").

Docs: `basics/offline-support.md`, `client/livestream-chat.md`,
and, for `isAutomaticSyncOnReconnectEnabled` and `syncMaxThreshold`,
`client/state-layer-overview.md` and
`migration-guides/migrating-from-v6-to-v7.md`.

## Release

- No `ChatLogLevel.ALL` in release builds. Docs: `basics/logging.md`.
- Every `.enqueue()` handles `Result.Failure`.
- All `stream-chat-android-*` artifacts on one version.
- No StrictMode or `@OptIn(InternalStreamChatApi::class)` in release code. Crashes or missing classes only in
  minified builds mean the consumer R8 rules aren't applied. Docs:
  `basics/troubleshooting.md`.
- Release builds don't permit cleartext traffic in the base network security
  config, and don't fall back to debug signing.
- On v6, scope the v7 upgrade with the migration guide under
  `migration-guides/`.
