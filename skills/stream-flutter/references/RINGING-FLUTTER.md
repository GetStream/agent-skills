# Ringing - Flutter Incoming/Outgoing Calls & Push

Ringing calls (1:1 and group) with push notifications, CallKit (iOS), and FCM (Android):
outgoing ring, incoming-call handling across foreground / background / terminated states,
and the platform setup that makes background ringing work. For runnable blueprints, see [RINGING-FLUTTER-blueprints.md](RINGING-FLUTTER-blueprints.md).

Prerequisites: package install, client init, and call basics from
[`VIDEO-FLUTTER.md`](VIDEO-FLUTTER.md). Ringing is the `default` call type plus push - not
a separate call type.

Rules: [../RULES.md](../RULES.md).

## Quick ref

- **Extra package:** `stream_video_push_notification` (same version as `stream_video_flutter`)
- **Outgoing:** `makeCall(callType: StreamCallType.defaultType(), id: uuid)` -> `getOrCreate(memberIds: [...], ringing: true, video: bool)`
- **Incoming (foreground):** `StreamVideo.instance.observeCoreRingingEvents(onCallAccepted: ...)`
- **Incoming (background):** top-level FCM handler -> `StreamVideo.create(...)` -> `observeCoreRingingEventsForBackground()` -> `handleRingingFlowNotifications(message.data)`
- **Incoming (terminated, Android only):** `consumeAndAcceptActiveCall(onCallAccepted: ...)`
- **iOS:** VoIP push + CallKit via one line in `AppDelegate` + Push Notifications capability
- **Android:** FCM via `google-services.json` + the Google Services Gradle plugin
- **In-call UI:** `StreamCallContainer(call: call)` renders incoming/outgoing/active automatically
- **Docs:** [Incoming Calls Overview](https://getstream.io/video/docs/flutter/advanced/incoming-calls/overview/)

Full blueprints (push init, outgoing ring, observers, background handler, AppDelegate,
manifest, CallScreen): [RINGING-FLUTTER-blueprints.md](RINGING-FLUTTER-blueprints.md).

---

## Mental model

"Ringing" = a caller creates a call with `ringing: true` and `memberIds`; Stream notifies
those members. How the incoming call surfaces depends on app state:

| App state                        | Delivery                                  | Surfaces as                                       |
| -------------------------------- | ----------------------------------------- | ------------------------------------------------- |
| Foreground / in-app              | WebSocket (`CoordinatorCallRingingEvent`) | Your in-app screen (or `StreamCallContainer`)     |
| Background / terminated, iOS     | VoIP push (APNs)                          | Native **CallKit** screen (handled by the plugin) |
| Background / terminated, Android | FCM high-priority data message            | SDK's full-screen/heads-up ringing notification   |
| Missed call / notify             | Regular push (APNs/FCM)                   | Non-interactive notification (can deeplink)       |

WebSocket delivery only works in the foreground; background/terminated needs push. iOS uses
VoIP/CallKit; Android uses FCM. Set `StreamVideoOptions(keepConnectionsAliveWhenInBackground: true)`
for reliable background incoming calls.

> **Docs:** [Incoming Calls Overview](https://getstream.io/video/docs/flutter/advanced/incoming-calls/overview/)

---

## Packages

```yaml
# pubspec.yaml
dependencies:
  stream_video_flutter: ^1.4.0
  stream_video_push_notification: ^1.4.0 # CallKit (iOS) + FCM ringing (Android)
  firebase_core: ^4.1.1 # Android FCM
  firebase_messaging: ^16.0.2 # Android FCM
  permission_handler: ^11.0.0 # POST_NOTIFICATIONS on Android 13+
  rxdart: ^0.28.0 # CompositeSubscription (returned by observeCoreRingingEvents)
```

`stream_video_push_notification` bundles CallKit/PushKit on iOS. Run `flutterfire configure` to generate
`firebase_options.dart`.

---

## Client init with push

Initialize Firebase first, then construct `StreamVideo` with a
`pushNotificationManagerProvider`. The push manager registers FCM + APNs/VoIP device tokens
automatically on `connect()`.

```dart
WidgetsFlutterBinding.ensureInitialized();
await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

StreamVideo(
  apiKey,
  user: user,
  userToken: token,
  options: StreamVideoOptions(
    keepConnectionsAliveWhenInBackground: true, // needed for background incoming calls
  ),
  pushNotificationManagerProvider: StreamVideoPushNotificationManager.create(
    iosPushProvider: const StreamVideoPushProvider.apn(name: 'your-apn-provider'),
    androidPushProvider: const StreamVideoPushProvider.firebase(name: 'your-fcm-provider'),
    pushConfiguration: const StreamVideoPushConfiguration(
      ios: IOSPushConfiguration(iconName: 'IconMask'),
    ),
    registerApnDeviceToken: true, // register the standard APNs token too (iOS call.missed)
  ),
)..connect();
```

- The `name:` strings **must exactly match** the provider names you create in the Stream
  Dashboard (Video & Audio -> Push Notifications).
- `StreamVideoPushNotificationManager.create(...)` returns a provider function (not the
  manager) of the exported type `PNManagerProvider` — assign it to
  `pushNotificationManagerProvider`, or wrap it in a `PNManagerProvider buildPushManagerProvider() {...}`
  helper shared by login init, startup re-connect, and the background isolate. Required:
  `iosPushProvider`, `androidPushProvider`. Optional: `pushConfiguration`,
  `registerApnDeviceToken` (default `false`).
- Device registration is automatic on `connect()` and auto-removed on `disconnect()`.
  Disable with `connect(registerPushDevice: false)`.

> **Docs:** [Push Notifications](https://getstream.io/video/docs/flutter/advanced/incoming-calls/push-notifications/) · [Providers Configuration](https://getstream.io/video/docs/flutter/advanced/incoming-calls/providers-configuration/)

### Dashboard providers

Create two push providers in the Stream Dashboard:

- **APN provider** (iOS): upload a `.p8` key (Key ID + Team ID + Bundle ID), select
  **Sandbox & Production**. Referenced by `StreamVideoPushProvider.apn(name: ...)`.
- **Firebase provider** (Android): upload the FCM service-account private-key JSON.
  Referenced by `StreamVideoPushProvider.firebase(name: ...)`.

Recommended split: **APNs for iOS, Firebase for Android.** Firebase-on-iOS for video is not
fully supported.

> **Docs:** [Providers Configuration](https://getstream.io/video/docs/flutter/advanced/incoming-calls/providers-configuration/)

---

## Ship the code, defer the config (recommended for new apps)

Background push needs external setup the agent **cannot** do (a Firebase project +
`google-services.json`, an APNs `.p8` key, two Dashboard providers, Xcode capabilities).
**Foreground / in-app ringing needs none of it** — it works over the WebSocket as soon as
two signed-in devices are open. So wire all the push code up front, but let the app still
compile and run before the config exists, and turn background ringing on automatically once
the user finishes it. This is almost always what "add ringing" means for a fresh app.

Three moves make this clean:

1. **Placeholder `firebase_options.dart`** so the project compiles before `flutterfire
configure` runs. `flutterfire configure` overwrites it. Make `currentPlatform` throw so
   nothing silently half-works:

   ```dart
   import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;

   class DefaultFirebaseOptions {
     static FirebaseOptions get currentPlatform => throw UnsupportedError(
           'Run `flutterfire configure` to generate real options.',
         );
   }
   ```

2. **Guard `Firebase.initializeApp`** and gate FCM listeners on the result, so a missing
   config degrades to foreground-only instead of crashing on launch:

   ```dart
   bool pushMessagingAvailable = false;

   Future<bool> initFirebaseMessaging() async {
     try {
       await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
       FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
       return pushMessagingAvailable = true;
     } catch (e) {
       debugPrint('[push] Firebase not configured yet — foreground ringing only. ($e)');
       return pushMessagingAvailable = false;
     }
   }
   // In HomeScreen.initState: always observeCoreRingingEvents (WebSocket / foreground);
   // only wire FirebaseMessaging.onMessage + terminated-state consume when
   // `pushMessagingAvailable`.
   ```

3. **Put the leftover config in a `PUSH_SETUP.md`** checklist (Dashboard providers + their
   names, `flutterfire configure`, the google-services Gradle plugin, Xcode capabilities) and
   keep the provider names in a tiny `push_config.dart` the user edits — no code changes
   needed to activate background ringing.

The `connect()` call still attaches the push manager in this mode; device-token registration
failures before config are logged and harmless.

---

## Outgoing ring

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.defaultType(),
  id: const Uuid().v4(), // unique id per call - reusing ids breaks ringing
);
final result = await call.getOrCreate(
  memberIds: ['alice', 'bob'],
  ringing: true,
  video: true, // false for an audio-only ring
);
result.fold(
  success: (_) { /* navigate to CallScreen */ },
  failure: (failure) {
    debugPrint('getOrCreate failed: ${failure.error.message}');
  },
);
```

Ring members of an **existing** call (must already be members - call `addMembers` first for
new users):

```dart
await call.ring(userIds: ['carol']); // userIds, not memberIds; empty rings all absent members
```

> **Docs:** [Ringing](https://getstream.io/video/docs/flutter/advanced/incoming-calls/ringing/)

---

## Incoming calls

### Foreground (WebSocket)

Register one observer high in the widget tree (e.g. the home screen). It fires for incoming,
accepted, declined, and ended ringing events while the app is foregrounded:

```dart
final sub = StreamVideo.instance.observeCoreRingingEvents(
  onCallAccepted: (call) {
    // user accepted (in-app or via CallKit) -> show the call screen
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => CallScreen(call: call)));
  },
);
// returns a CompositeSubscription - cancel it in dispose: sub.cancel();
```

Lower-level alternatives: observe `StreamVideo.instance.state.incomingCall`
(`StateEmitter<Call?>`) for the `Call` object, or
`StreamVideo.instance.events` for the raw `CoordinatorCallRingingEvent` (has `.video`).

### Background / terminated (FCM data message)

Define a **top-level** function annotated `@pragma('vm:entry-point')` and register it with
`FirebaseMessaging.onBackgroundMessage(...)`. It runs in a separate isolate, so it must
re-create a **non-singleton** `StreamVideo` via `StreamVideo.create(...)`:

```dart
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  final user = await loadStoredUser();   // persist creds at login (e.g. flutter_secure_storage)
  if (user == null) return;

  final streamVideo = StreamVideo.create(
    apiKey,
    user: user.user,
    userToken: user.token,
    pushNotificationManagerProvider: StreamVideoPushNotificationManager.create(
      iosPushProvider: const StreamVideoPushProvider.apn(name: 'your-apn-provider'),
      androidPushProvider: const StreamVideoPushProvider.firebase(name: 'your-fcm-provider'),
      registerApnDeviceToken: true,
    ),
  )..connect();

  final subscription = streamVideo.observeCoreRingingEventsForBackground();
  streamVideo.disposeAfterResolvingRinging(disposingCallback: subscription.cancel);
  await streamVideo.handleRingingFlowNotifications(message.data);
}
```

- `observeCoreRingingEventsForBackground()` subscribes to incoming + declined only and
  returns a `CompositeSubscription`.
- `disposeAfterResolvingRinging(disposingCallback:)` tears the isolate's client down ~1s
  after the ringing resolves (accept / decline / timeout / ended).
- `handleRingingFlowNotifications(Map payload, {bool handleMissedCall = true})` shows the
  ringing notification for `call.ring` and the missed-call notification for `call.missed`.
  It only acts on payloads where `sender == 'stream.video'`.

Foreground FCM messages can be routed the same way via
`FirebaseMessaging.onMessage.listen((m) => StreamVideo.instance.handleRingingFlowNotifications(m.data))`.

### Terminated state, Android only

When the app is launched cold by accepting an Android notification, consume the accepted
call after the first frame. **Guard against iOS** - iOS terminated calls are handled
natively by CallKit/PushKit:

```dart
if (!CurrentPlatform.isIos) {
  WidgetsBinding.instance.addPostFrameCallback((_) {
    StreamVideo.instance.consumeAndAcceptActiveCall(
      onCallAccepted: (call) {
        Navigator.of(context).push(MaterialPageRoute(builder: (_) => CallScreen(call: call)));
      },
    );
  });
}
```

`consumeAndAcceptActiveCall` only consumes calls the user explicitly accepted, ensures a
WebSocket connection, then accepts. (`consumeIncomingCall({uuid, cid})` is the lower-level
single-call variant.)

> **Docs:** [Ringing](https://getstream.io/video/docs/flutter/advanced/incoming-calls/ringing/) · [Android / Firebase Integration](https://getstream.io/video/docs/flutter/advanced/incoming-calls/android-firebase-integration/) · [iOS / CallKit Integration](https://getstream.io/video/docs/flutter/advanced/incoming-calls/ios-callkit-integration/)

---

## Accept / reject / end

```dart
await call.accept();                              // only valid while CallStatusIncoming
await call.reject(reason: CallRejectReason.decline()); // also leaves the call
await call.end();                                 // only valid while CallStatusActive
```

`CallRejectReason` factories (string `value`): `.decline()` (callee declines), `.cancel()`
(caller cancels), `.busy()`, `.timeout()`, `.callEnded()`, `.userRespondedElsewhere()`,
`.custom(String)`, and the ring-flow reasons `.creatorRejected()` /
`.allOtherParticipantsRejected()`.

`StreamCallContainer(call: call)` wires accept/reject/end UI automatically and switches
between incoming, outgoing, and active screens based on `CallStatus`. Pass
`incomingCallWidgetBuilder` / `outgoingCallWidgetBuilder` to customize those screens.

### Ring settings and auto-end

```dart
final result = await call.getOrCreate(
  memberIds: ['alice'],
  ringing: true,
  ring: const StreamRingSettings(
    autoCancelTimeout: Duration(seconds: 30),  // server: auto_cancel_timeout (caller side)
    autoRejectTimeout: Duration(seconds: 30),  // server: incoming_call_timeout (callee side)
  ),
);
result.fold(
  success: (_) { /* proceed */ },
  failure: (failure) {
    debugPrint('getOrCreate failed: ${failure.error.message}');
  },
);
```

`dropIfAloneInRingingFlow` (a `DefaultCallPreferences` field, default `true`) auto-ends the
call when only one participant remains in the ringing flow.

> **Docs:** [Ringing](https://getstream.io/video/docs/flutter/advanced/incoming-calls/ringing/) · [Call Container](https://getstream.io/video/docs/flutter/ui/call-container/)

---

## iOS setup (VoIP + CallKit)

1. **Deployment target iOS 14.0+** - `stream_video_push_notification` requires it. Set
   `platform :ios, '14.0'` in `ios/Podfile` and `IPHONEOS_DEPLOYMENT_TARGET = 14.0` for all
   three build configs.
2. **Capabilities** (Xcode -> Signing & Capabilities):
   - **Push Notifications** (creates the `aps-environment` entitlement - without it iOS
     silently drops VoIP and regular pushes).
   - **Background Modes**: Voice over IP, Remote notifications, Background processing.
3. **`Info.plist`** `UIBackgroundModes` array: `audio`, `processing`, `remote-notification`,
   `voip`; plus `NSCameraUsageDescription` and `NSMicrophoneUsageDescription`.
4. **`AppDelegate.swift`** - one line registers PushKit/VoIP and CallKit reporting (the
   plugin does the rest):
   ```swift
   import stream_video_push_notification
   // in didFinishLaunchingWithOptions:
   StreamVideoPKDelegateManager.shared.registerForPushNotifications()
   ```
5. **`registerApnDeviceToken: true`** in the push manager - the VoIP token is separate from
   the standard APNs token; the standard token is needed for `call.missed` on iOS.

Full `AppDelegate` (incl. optional foreground standard-push display):
[RINGING-FLUTTER-blueprints.md](RINGING-FLUTTER-blueprints.md) > iOS AppDelegate.

> **Docs:** [iOS / CallKit Integration](https://getstream.io/video/docs/flutter/advanced/incoming-calls/ios-callkit-integration/) (note: docs show the older `GeneratedPluginRegistrant.register(with: self)` AppDelegate — the Flutter 3.35+ `FlutterImplicitEngineDelegate`/`SceneDelegate` template in the blueprint is more current).

---

## Android setup (FCM)

1. **`google-services.json`** at `android/app/`.
2. **Gradle plugin** `com.google.gms.google-services` (e.g. version `4.3.15`) applied in
   `android/app/build.gradle`; declared in `android/settings.gradle`.
3. **`MainActivity`** can be a plain `FlutterActivity`; set
   `android:launchMode="singleInstance"` (or `singleTask`) on its `<activity>` so tapping a
   notification reuses the existing instance instead of stacking call screens.
4. **`AndroidManifest.xml`** permissions: `INTERNET`, `CAMERA`, `RECORD_AUDIO`,
   `ACCESS_NETWORK_STATE`, `MODIFY_AUDIO_SETTINGS`, the Bluetooth set
   (`BLUETOOTH`/`BLUETOOTH_ADMIN` `maxSdkVersion=30`, `BLUETOOTH_CONNECT`), and
   `POST_NOTIFICATIONS`. Foreground-service permissions come transitively from the plugin.
5. **Android 13+** - request `POST_NOTIFICATIONS` at runtime (`permission_handler`).
6. **Android 14+** - call
   `StreamVideoPushNotificationManager.ensureFullScreenIntentPermission()` so lock-screen
   full-screen ringing is allowed.

> **Docs:** [Android / Firebase Integration](https://getstream.io/video/docs/flutter/advanced/incoming-calls/android-firebase-integration/)

---

## Customization (entry points)

- **Caller display name (CallKit / notification):** set when creating the call -
  `getOrCreate(custom: {'display_name': 'Team standup'})`. The SDK prefers
  `call_display_name` (from custom `display_name`/`name`/`title`), falling back to the
  caller's name.
- **iOS CallKit** via `IOSPushConfiguration`: `iconName`, `ringtonePath` (bundle a
  `Ringtone.caf`), `handleType` (`'generic'`/`'number'`/`'email'`), `supportsVideo`,
  `supportsHolding`, audio-session options.
- **Android notification** via `AndroidPushConfiguration`:
  `incomingCallNotification: IncomingCallNotificationParams(...)` (full-screen logo/colors,
  `textAccept`/`textDecline`, `showCallHandle`),
  `missedCallNotification: MissedCallNotificationParams(...)` (`showNotification`,
  `subtitle`, `callbackText`, `showCallbackButton`), `ringtonePath` (a file under
  `android/app/src/main/res/raw/`, name without extension), channel names,
  `showFullScreenOnLockScreen`.

> **Docs:** [Customization](https://getstream.io/video/docs/flutter/advanced/incoming-calls/customization/)

---

## Missed calls

- On iOS, missed-call pushes need the standard APNs token: set
  `registerApnDeviceToken: true`.
- The backend only sends a missed-call push if the **Call Missed** notification template is
  enabled **and** has a non-empty body (Dashboard -> call type -> Notification templates).
- `handleRingingFlowNotifications(...)` shows the missed-call notification by default; pass
  `handleMissedCall: false` to render it yourself.

> **Docs:** [Push Notifications](https://getstream.io/video/docs/flutter/advanced/incoming-calls/push-notifications/) · [Customization](https://getstream.io/video/docs/flutter/advanced/incoming-calls/customization/)

---

## Gotchas

- **Provider names must match the Dashboard exactly** for `.apn(name:)` / `.firebase(name:)`.
- **Background handler must be top-level + `@pragma('vm:entry-point')`** and use
  `StreamVideo.create(...)` (non-singleton) - the singleton does not exist in the FCM
  isolate.
- **Persist user credentials at login** (e.g. `flutter_secure_storage`) so the background
  isolate can re-authenticate and `connect()`.
- **Terminated-state consume is Android-only** - guard with `if (CurrentPlatform.isIos) return;`.
- **`registerApnDeviceToken` + Stream Chat on Firebase = duplicate pushes.** If the same app
  also uses Stream Chat via Firebase, leave `registerApnDeviceToken` at `false` to avoid
  duplicate `call.notification`/`call.missed` (APNs + Firebase); rely on Firebase for
  standard pushes.
- **iOS Simulator cannot receive VoIP pushes** - test CallKit on a real device.
- **Unique call ids** - generate a fresh `Uuid().v4()` per ringing call; reusing an id
  breaks ringing.
- **Don't ring yourself**, and every ring target must already exist and have connected to
  Stream at least once (so a push token is registered).
- **iOS Push Notifications capability is mandatory** - missing `aps-environment` means iOS
  silently drops all pushes.
- **Clear stale devices** when push misbehaves: `getDevices()` then
  `removeDevice(pushToken: ...)` per stale token.
