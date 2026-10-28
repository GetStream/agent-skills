# Stream Flutter - push setup (Chat push + Video ringing)

Triggered by requests like "add push notifications for chat", "incoming calls should ring when the app is closed", "CallKit", "FCM ringing", or "missed call notification". The SDK calls are in the docs; this runbook covers the order, the external setup the agent cannot do, and the traps. Obey [`RULES.md`](RULES.md) throughout - the APNs key and Firebase service account go to Stream via the CLI, never into the app or git.


Docs to fetch as you go ([`docs-map.md`](docs-map.md)):

- Chat: the "Push notifications" row under Chat -> Production.
- Video: the "Ringing and push" section (overview, ringing, providers, push notifications, CallKit, Android FCM + Telecom, customization).

---

## Step 0: Scope it

| User wants | Delivery | Stream providers | Client packages |
|---|---|---|---|
| Chat push (new message while backgrounded) | FCM on Android; APNs (via Firebase by default) on iOS | one `firebase` (+ optional `apn`) | `firebase_core`, `firebase_messaging`, `flutter_local_notifications` |
| Video ringing (incoming call wakes the app) | VoIP push + CallKit on iOS; high-priority FCM data on Android | one `apn`, one `firebase` | `stream_video_push_notification`, `firebase_core`, `firebase_messaging`, `permission_handler`, `rxdart`, `uuid` |
| Both | both | both | both |

How a ringing call surfaces by app state:

| App state | Delivery | Surfaces as |
|---|---|---|
| Foreground | WebSocket (`CoordinatorCallRingingEvent`) | your in-app screen / `StreamCallContainer` |
| Background / terminated, iOS | VoIP push (APNs) | native CallKit screen (the plugin handles it) |
| Background / terminated, Android | FCM high-priority data message | SDK full-screen / heads-up ringing notification |
| Missed call / notify | regular push | non-interactive notification |

**Foreground ringing needs no push config at all** - it works over the WebSocket between two signed-in devices. Only background / terminated delivery needs Steps 1-3.

**Both products in one app:** if Chat uses Firebase on iOS, leave the Video push manager's `registerApnDeviceToken` at `false` - otherwise `call.notification` / `call.missed` arrive twice (APNs + Firebase).

---

## Step 1: External setup (the user does this; the agent writes it down)

The agent cannot create a Firebase project, download an APNs key, or toggle Xcode capabilities. Do not block on it - see Step 4 "ship the code, defer the config" - but list exactly what is needed in a `PUSH_SETUP.md` in the project:

1. **Firebase project** + `flutterfire configure` (generates `lib/firebase_options.dart`, `android/app/google-services.json`, `ios/Runner/GoogleService-Info.plist`).
2. **Firebase service-account JSON** (Firebase console -> Project settings -> Service accounts -> Generate new private key).
3. **APNs auth key `.p8`** (Apple Developer -> Keys -> + -> Apple Push Notifications service). Capture Key ID, Team ID, and the bundle id. One token key powers both alert and VoIP push.
4. **Xcode -> Runner -> Signing & Capabilities:** Push Notifications (creates `aps-environment` - without it iOS silently drops every push); for ringing also Background Modes -> Voice over IP, Remote notifications, Background processing.

---

## Step 2: Create the Stream push providers via the CLI

Pipe the secrets over stdin with `jq --rawfile` so they never appear in the chat or a file in the repo. Names are yours to choose - they must match the code exactly.

```bash
# Firebase (Android; and iOS Chat push via Firebase)
jq -n --rawfile creds /path/service-account.json \
  '{push_provider:{type:"firebase",name:"firebase",firebase_credentials:$creds}}' \
  | getstream api UpsertPushProvider --request -

# APNs (iOS VoIP / CallKit for Video ringing; also standard APNs for call.missed)
jq -n --rawfile key /path/AuthKey_<KEYID>.p8 \
  '{push_provider:{type:"apn",name:"apn",apn_auth_type:"token",apn_auth_key:$key,apn_key_id:"<KEYID>",apn_team_id:"<TEAMID>",apn_topic:"<BUNDLE_ID>",apn_development:true}}' \
  | getstream api UpsertPushProvider --request -
```

- `apn_development:true` = sandbox (debug builds from Xcode); `false` for TestFlight / App Store. A mismatch means silent no-delivery.
- Check the field schema with `getstream api UpsertPushProvider --schema`; confirm with `getstream api ListPushProviders`.
- For Video, the recommended split is **APNs for iOS, Firebase for Android** (Firebase-on-iOS for video is not fully supported).
- Video missed-call pushes are sent only when the call type's **Call Missed** notification template is enabled and has a non-empty body (Dashboard -> call type -> Notification templates).

---

## Step 3: Native project setup

**iOS (ringing):**

- Deployment target and SPM: iOS 15.0 (`firebase_core` requires it), as in [`RULES.md`](RULES.md) "Video -> Build blockers" (`IPHONEOS_DEPLOYMENT_TARGET` in the pbxproj; no Podfile on SPM projects). The callkit docs page assumes a Podfile - ignore that part on SPM projects.
- `Info.plist` `UIBackgroundModes`: `audio`, `processing`, `remote-notification`, `voip`; plus camera / microphone usage strings.
- `AppDelegate.swift`: one call registers PushKit + CallKit reporting. On the Flutter 3.41+ template (`FlutterImplicitEngineDelegate`), keep plugin registration in `didInitializeImplicitFlutterEngine` and add only the Stream lines - the docs still show the older `GeneratedPluginRegistrant.register(with: self)` form:

  ```swift
  import stream_video_push_notification
  // in application(_:didFinishLaunchingWithOptions:), before `return super.application(...)`:
  StreamVideoPKDelegateManager.shared.registerForPushNotifications()
  UNUserNotificationCenter.current().delegate = self
  ```

**Android:**

- `google-services.json` in `android/app/`; apply `com.google.gms.google-services` in `android/app/build.gradle.kts` (`id("com.google.gms.google-services")`) and declare its version in `android/settings.gradle.kts` (Kotlin DSL - Groovy snippets do not parse).
- `android:launchMode="singleInstance"` (or `singleTask`) on the main `<activity>` so notification taps do not stack call screens.
- Manifest: `POST_NOTIFICATIONS` plus the Video permissions from the install page (foreground-service permissions come from the plugin). Request `POST_NOTIFICATIONS` at runtime on Android 13+ and `BLUETOOTH_CONNECT` before calls; on Android 14+ call `StreamVideoPushNotificationManager.ensureFullScreenIntentPermission()` for lock-screen ringing.
- **Android 17 Telecom:** the ringing flow registers calls with Jetpack Telecom by default on Android 17+ devices (`AndroidPushConfiguration(telecom: TelecomPushConfiguration(...))`). For an app targeting API 37+, Android 17 drops the ringtone of a push-started call unless it is in Telecom - so keep Telecom enabled unless the app rings some other way. The plugin needs a JDK 17+ Gradle build. Details: the Telecom section of `https://getstream.io/video/docs/flutter/advanced/incoming-calls/android-firebase-integration.md`.

---

## Step 4: Client code

### Ship the code, defer the config (default for new apps)

Wire all push code now, but keep the app compiling and running before Step 1 is done, degrading to foreground-only ringing:

1. **Placeholder `lib/firebase_options.dart`** whose `DefaultFirebaseOptions.currentPlatform` throws `UnsupportedError('Run flutterfire configure ...')`. `flutterfire configure` overwrites it.
2. **Guard `Firebase.initializeApp`** in a `try` and record `pushMessagingAvailable`; register `FirebaseMessaging.onBackgroundMessage` and the FCM listeners only when it succeeds. Always wire the foreground WebSocket observers.
3. Keep provider names in a small `push_config.dart` the user edits, and list the remaining manual steps in `PUSH_SETUP.md` - no code changes needed to activate background delivery later.

### Chat push

Per the Chat "Push notifications" docs ([`docs-map.md`](docs-map.md)):

- Register **after** `connectUser` and again on every `FirebaseMessaging.instance.onTokenRefresh`: `client.addDevice(token, PushProvider.firebase, pushProviderName: '<name>')`.
- On logout, `await client.removeDevice(token)` **before** `disconnectUser()`.
- Android receives data-only messages - render them with `flutter_local_notifications`. The background handler is a **top-level** `@pragma('vm:entry-point')` function; inside it connect with `connectWebSocket: false` and fetch the message by id from the payload.
- Push is sent whether or not the user is connected - handle or suppress foreground `onMessage` for the open channel. Push needs channel **membership** (watching is not enough) and only fires for new messages; muted channels, `skip_push`, and push disabled on the channel type suppress it.

### Video ringing

Per the ringing / providers docs:

- Create the client with `pushNotificationManagerProvider: StreamVideoPushNotificationManager.create(iosPushProvider: const StreamVideoPushProvider.apn(name: 'apn'), androidPushProvider: const StreamVideoPushProvider.firebase(name: 'firebase'), ...)` and `StreamVideoOptions(keepConnectionsAliveWhenInBackground: true)`. Device tokens register on `connect()` and unregister on disconnect. Share one `buildPushManagerProvider()` helper between login, app start, and the background isolate.
- Outgoing: a fresh `Uuid().v4()` id, then `getOrCreate(memberIds: [...], ringing: true, video: ...)`. Set `custom: {'display_name': ...}` for the CallKit / notification caller name.
- Foreground: `StreamVideo.instance.observeCoreRingingEvents(onCallAccepted: ...)` (returns an rxdart `CompositeSubscription` - dispose it).
- Background (Android FCM): the top-level `@pragma('vm:entry-point')` handler builds a non-singleton client with `StreamVideo.create(...)` from **persisted** credentials (e.g. `flutter_secure_storage`, saved at login), then `handleRingingFlowNotifications(message.data)`.
- Terminated (Android only): `consumeAndAcceptActiveCall(onCallAccepted: ...)` on start - guard with `if (CurrentPlatform.isIos) return;`.
- iOS standard APNs token (`registerApnDeviceToken: true`) is needed for `call.missed` on iOS - unless Chat already uses Firebase on iOS (see Step 0).

---

## Step 5: Verify

- [ ] Two **physical** devices (iOS simulators never receive VoIP / APNs), two different users, both connected at least once.
- [ ] Foreground: the callee's in-app ringing screen appears; accept / decline / caller-cancel all end correctly.
- [ ] Background and terminated: CallKit (iOS) / full-screen notification (Android) appears and accepting opens the call.
- [ ] A fresh call id per test call (ringing fires once per id).
- [ ] Chat: a message from another member arrives as a notification while the app is backgrounded.
- [ ] Missed-call notification appears (template enabled with a body).
- [ ] When push misbehaves, list and clear stale devices (`getDevices()` -> `removeDevice(...)`) before debugging code.
