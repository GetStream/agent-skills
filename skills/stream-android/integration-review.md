# Stream Android - integration review

Android checks for a read-only integration review. Run the procedure in stream
skill's integration-review.md; this file uses the same section names, and each
bullet here replaces the generic bullet on the same topic. SDK pages are under
`getstream docs chat-sdk/android`, API pages under `getstream docs
chat/android`. The go-live checklist is `guides/go-live-checklist.md`.

Video pages are under `getstream docs video/android`; ringing and push are in
`advanced/incoming-calls/`. Video has no go-live checklist or best-practices
page on Android, so the Video bullets below cite those pages or the SDK code.
Bullets that start with "Video", and the whole Calls section, are Video
checks; in a Video-only app the other bullets are N/A.

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

- Video: `loggingLevel = LoggingLevel(priority = Priority.VERBOSE,
  httpLoggingLevel = HttpLoggingLevel.BODY)` for a debug run. A ringing push
  dropped because the client wasn't built logs "StreamVideo is not
  initialised". Source: SDK code.

## Initialization

- `ChatClient.Builder.build()` runs in `Application.onCreate`. It opens no
  socket, so it's cheap. Built twice, the singleton is replaced: look for
  components that captured `ChatClient.instance()` earlier.
- Flag builder options left over from testing or tuning in release:
  `disableDistinctApiCalls()` (docs: `client/guides/optimizations.md`),
  `forceInsecureConnection()`, a custom `baseUrl`, a custom `OkHttpClient` with
  aggressive timeouts or interceptors rewriting Stream requests.
- Skip this one for an SDK that is a project or composite dependency. New
  releases are on Stream's own Maven repository, not Maven Central:
  `dependencyResolutionManagement.repositories` in `settings.gradle(.kts)`
  needs `maven("https://stream-io-repo.com")`, or the build can't resolve
  newer versions. An entry under `pluginManagement` doesn't count. Docs:
  `basics/installation.md`.
- Video: `StreamVideoBuilder.build()` runs in `Application.onCreate` whenever
  a user is stored, not only after login or when a call screen opens, and
  from the stored user and token, with no network call first: refreshing is
  the `tokenProvider`'s job. A push that arrives before the build, or after
  a failed fetch, is dropped with "StreamVideo is not initialised", so
  ringing never reaches a killed app. An app that keeps the user only in
  memory fails this too: the device stays registered, but nothing is built
  after the process dies. `build()` throws on a blank key or token, so the
  startup build is guarded and the session is saved only after a successful
  build; otherwise one bad session crashes every launch. Docs:
  `advanced/incoming-calls/push-providers/firebase.md`; source: SDK code.
- Video: the builder gets a `tokenProvider` backed by the app's server.
  Without one the SDK keeps reusing the static token, and expired tokens are
  never refreshed. Docs: `guides/client-auth.md`.
- Video: a second `build()` throws while a client exists. Switching users
  calls `StreamVideo.removeClient()` first; turning off
  `ensureSingleInstance` to get past the error is a finding. Source: SDK
  code.
- Video: `removeClient()` leaves the active call, so rebuilding the clients
  on a deep link or environment switch ends a call in progress. Rebuild only
  when the user changes. Source: SDK code.

## Typical session

- `connectUser` is guarded with `getCurrentUser() == null` or
  `clientState.initializationState`. Push devices register on connect.
- A failed connect is handled from the `connectUser` result or a token-error
  connection state. `initializationState` becomes `COMPLETE` before the socket
  authenticates, so routing on it alone never sees an invalid token. Source:
  SDK code.
- No `disconnectSocket()` on background: it drops the lifecycle observer and
  the SDK stops reconnecting on foreground ("messages stop arriving after a
  while"). Docs: `client/guides/handling-user-connection.md`.
- Video: `build()` connects in the background and only logs a failed
  connect. The app watches `StreamVideo.instance().state.connection` for
  `ConnectionState.Failed` and sends the user back to login on an auth
  error. Source: SDK code.

## Disconnecting

- Logout calls `disconnect(flushPersistence = true)`. On v7 `deleteDevice`
  defaults to `flushPersistence`, so `disconnect(flushPersistence = false)`
  leaves the device registered. On v6 `disconnect` has no `deleteDevice`: the
  app calls `deleteDevice(device)` itself. Docs:
  `guides/push-notifications.md`, Unsubscribing from Push Notifications.
- Logout awaits `disconnect(...)` before navigating, not
  `GlobalScope.launch` with a delay.
- Account switch uses `switchUser`.
- Video logout deletes the device (for example `getDevice().first()`, then
  `deleteDevice(it)`; any `Device` whose id is the registered token works),
  handles a failed delete, and then calls `StreamVideo.removeClient()`.
  `StreamVideo.logOut()` only clears the local token cache: the device stays
  registered to the old user, so their calls keep reaching the phone until
  someone else logs in on it, and after that too if the app allows
  multi-user devices. Source: SDK code (`logOut` is deprecated for this
  reason).

## Fetching channels

- Lists come from `ChannelListViewModel` or `queryChannelsAsState` held in a
  ViewModel, not `queryChannels(...).enqueue {}` in `onResume`.
- No `forceNewRequest()` to get fresh data: it defeats de-duplication.
- No `watch = false` / `state = false` on the request followed by complaints
  that the list is stale.
- Sorting uses `QuerySortByField`, not `QuerySortByReflection`, on hot lists.
- Paging uses the ViewModel's load-more or
  `QueryChannelsState.nextPageRequest`.
- Event filtering: each list passes a `chatEventHandlerFactory` whose handler
  extends `DefaultChatEventHandler` and returns `Skip` for channels outside
  the list's filter. `WatchAndAdd` costs a request per event. Docs:
  `client/channels.md`.

## Search

- Compose: `ChannelListViewModel` debounces (`searchDebounceMs`). XML: the
  debounce lives in `SearchInputView`, so a custom UI on `SearchViewModel` must
  debounce itself.

## Rendering and customization

- Extension points are `ChatTheme` and `ChatComponentFactory` (Compose), or
  `ChatUI` and style transformers (XML). A factory override handles its own
  case and delegates the rest to the default. Docs:
  `compose/general-customization/component-factory.md`.
- Capabilities come from `channel.ownCapabilities`. Docs:
  `compose/guides/implementing-own-capabilities.md`.
- No ViewModel built with `factory.create(...)` or inside `remember { }`: that
  skips the ViewModelStore, so `onCleared` never runs. Use
  `viewModel(key = ..., factory = ...)`, keyed per item when each list item
  needs its own instance; `viewModel()` inside an SDK screen that provides its
  own store is fine. Source: SDK code and Android practice.
- State is collected with `collectAsStateWithLifecycle`.
- A custom message list uses `watchChannelAsState`, not a one-off
  `queryChannel` plus polling.
- Every `subscribe` / `subscribeFor` either takes a `LifecycleOwner` or keeps
  the returned `Disposable` and disposes it, e.g. in `onCleared`. Source: SDK
  code.
- A custom message list that supports jump-to-message calls
  `loadNewestMessages` alongside a send when `endOfNewerMessages` is false;
  otherwise the sent message lands in the old page. Docs:
  `client/state-layer-overview.md`.
- A custom `fileUploader(...)` for private storage has a matching `cdn(...)`
  that signs downloads, or uploads work but files don't load. Docs:
  `client/custom-cdn.md`. `uploadAttachmentsNetworkType(UNMETERED)` keeps
  attachment messages pending on mobile data. Source: SDK code.

## Calls

- The `Call` from `streamVideo.call(type, id)` lives in a ViewModel or
  Activity field, not in a Composable body.
- `StreamCallActivity` (and `ComposeStreamCallActivity`) leaves the call on
  back, hang-up, and call-end events, but not in `finish()`: an app path that
  calls `finish()` or `safeFinish()` leaves first. A custom call screen calls
  `call.leave()` itself. For 1:1 calls, check that the screen closes when the
  other side leaves (`leaveWhenLastInCall`). Source: SDK code.
- `join`, `accept`, `reject`, `ring`, and `create` return `Result`: a
  `Failure` is shown, not ignored. With the prebuilt `StreamCallActivity`,
  a failure closes the screen (`closeScreenOnError`), which passes; showing
  the reason through an `onFailed` override is Worth doing at most.
- Permissions are granted before `join`: `LaunchCallPermissions`,
  `rememberCallPermissionsState`, or the app's own request. A
  `StreamCallActivity` call screen checks them itself. An audio-only app
  requests only `RECORD_AUDIO`. Read references/VIDEO-COMPOSE.md,
  Permissions.
- A custom accept path leaves `state.activeCall` first (docs:
  `advanced/incoming-calls/ringing.md`), or the builder sets
  `rejectCallWhenBusy` (source: SDK code). `StreamCallActivity` already
  leaves the active call before accepting.

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
  launch unless `requestPermissionOnAppLaunch` returns false. Video's
  `NotificationConfig` does the same by default.
- Video: link 5 of the push chain is the Initialization `tokenProvider`
  check; Video's `NotificationConfig` has no token provider of its own.
- Intermittent push: check the merged manifest for a dependency declaring
  `WAKE_LOCK` with a low `maxSdkVersion`. A `success` in the dashboard push log
  only means FCM accepted it.
- Video: `StreamVideoBuilder` gets a `notificationConfig` whose
  `pushDeviceGenerators` lists a generator with the dashboard's provider name.
  The default list is empty, so no device is registered and nothing rings in
  the background. Source: SDK code. Docs:
  `advanced/incoming-calls/push-providers/firebase.md`.
- Video: the same custom-service rule applies. One service that delegates to
  `FirebaseMessagingDelegate` serves Chat and Video: the delegate offers each
  message to every installed SDK. Source: stream-android-push code.
- Video: the merged manifest keeps `USE_FULL_SCREEN_INTENT`,
  `FOREGROUND_SERVICE_PHONE_CALL`, and `POST_NOTIFICATIONS`. A
  `tools:node="remove"` on them is fine only in an app that never rings.
  Source: SDK manifest.
- Video: the activity that resolves the SDK's intent actions
  (`INCOMING_CALL`, `ACCEPT_CALL`, and the rest), whether the app's own or
  the SDK's `ComposeStreamCallActivity`, declares them and
  `showWhenLocked`. Without them the push arrives but no screen opens. A
  subclass that is never launched is dead code, not a push break. Docs:
  `advanced/incoming-calls/push-notifications.md`.

## Unread counts

- App badge from `GlobalState.totalUnreadCount` or `channelUnreadCount`,
  per-channel badges from `Channel.unreadCount`.
- Livestream-type channels show 0 because read events are off there;
  `isLocalUnreadCountEnabled` tracks a local count. Docs:
  `client/livestream-chat.md`.

## Scale and release

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
- Release builds use `ChatLogLevel.NOTHING` or `ERROR`, and don't enable
  StrictMode or opt into `InternalStreamChatApi` in app code. Source: the app
  code.
- The base network security config doesn't permit cleartext, and release
  signing doesn't fall back to the debug keystore.
- Video release builds don't pass a `loggingLevel` at `DEBUG` or `VERBOSE`
  (the default is `ERROR`), and don't opt into `InternalStreamVideoApi`.
  Source: SDK code.
- All `stream-chat-android-*` artifacts are on one version, and so are all
  `stream-video-android-*` artifacts. Crashes or missing
  classes only in minified builds mean the consumer R8 rules aren't applied.
  Docs: `basics/troubleshooting.md`.
- On v6, scope the v7 upgrade with the migration guide under
  `migration-guides/`.

Docs: `basics/offline-support.md`, `client/livestream-chat.md`, and, for
`isAutomaticSyncOnReconnectEnabled` and `syncMaxThreshold`,
`client/state-layer-overview.md` and
`migration-guides/migrating-from-v6-to-v7.md`.
