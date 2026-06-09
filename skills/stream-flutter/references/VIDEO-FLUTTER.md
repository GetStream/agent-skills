# Video - stream_video_flutter Setup & Integration

`stream_video_flutter` provides pre-built Flutter widgets for building video and audio calling experiences. This file covers package installation, client setup, authentication, call flows, customization, and gotchas. For widget blueprints, see [VIDEO-FLUTTER-blueprints.md](VIDEO-FLUTTER-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

- **Blueprint** - Widget structure and initialization
- **Wiring** - SDK calls for each component, exact property paths
- **Requirements** - Platform setup, SDK version, Flutter version

## Quick ref

- **Package (pre-built UI):** `stream_video_flutter` via pub.dev
- **Package (core only):** `stream_video` via pub.dev
- **Version:** `^1.4.0` | **Dart SDK:** `^3.8.0` | **Flutter:** `>=3.32.0`
- **First:** Installation -> platform setup -> client init -> `call.getOrCreate()` -> `call.join()` -> show `StreamCallContainer`
- **Auth:** `User.regular` + token/`tokenLoader` for real accounts; **`User.guest`** (no token) for no-backend "just a name" sign-in; `User.anonymous` for watch-only livestream viewers. Never use dev tokens to fake a login. See User Authentication.
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/video/docs/flutter/`

Full widget blueprints: [VIDEO-FLUTTER-blueprints.md](VIDEO-FLUTTER-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation

> **Docs:** [Installation](https://getstream.io/video/docs/flutter/setup/installation/) · [Quickstart](https://getstream.io/video/docs/flutter/setup/quickstart/)

```yaml
# pubspec.yaml
dependencies:
  stream_video_flutter: ^1.4.0 # pre-built UI + core
  # OR for core only (no pre-built widgets)
  stream_video: ^1.4.0
  # Video filters
  stream_video_filters: ^1.4.0 # optional, only if using blur/virtual background
```

```bash
flutter pub get
```

Install only what is needed. Do not add `stream_video` separately when `stream_video_flutter` is chosen - the UI package re-exports it.

### Platform Setup

Complete platform setup **before** wiring the client. Missing permissions cause silent failures or crashes at call time, not at install time.

> **Docs:** [Installation](https://getstream.io/video/docs/flutter/setup/installation/)

#### Android

Add permissions to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS"/>
<uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30"/>
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT"/>
```

Set the minimum SDK version and compile SDK in `android/app/build.gradle`:

```kotlin
// android/app/build.gradle.kts
android {
    compileSdk = 36
    defaultConfig {
        minSdk = maxOf(24, flutter.minSdkVersion)
    }
}
```

Older projects with the Groovy `android/app/build.gradle` use `compileSdkVersion 36`
and `minSdkVersion 24` instead. Check which file your project has before editing.

Plugin versions (AGP, Gradle, Kotlin) are declared in `android/settings.gradle.kts`
(or the legacy `android/settings.gradle`/`build.gradle`).

```kotlin
// android/settings.gradle.kts
plugins {
    id("com.android.application") version "8.12.1" apply false
    id("org.jetbrains.kotlin.android") version "2.2.0" apply false
}
```

**Android PiP (Picture-in-Picture):** Since v0.10.0, extend `StreamFlutterActivity` instead of `FlutterActivity` in `MainActivity.kt`:

```kotlin
import io.getstream.video.flutter.stream_video_flutter.StreamFlutterActivity

class MainActivity : StreamFlutterActivity()
```

On Android 6+ (API 23+), camera and microphone are **runtime** permissions. The manifest entries are required but not sufficient - request them before joining a call:

```dart
import 'package:permission_handler/permission_handler.dart';

await [Permission.camera, Permission.microphone].request();
```

Add `permission_handler` to `pubspec.yaml` if not already present. Use `flutter pub add permission_handler` to resolve version automaticaly.

#### iOS

Add these keys to `ios/Runner/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>Video calls require camera access.</string>
<key>NSMicrophoneUsageDescription</key>
<string>Video calls require microphone access.</string>
```

Set the minimum deployment target to iOS 15.0 (the podspec minimum is 14.0, but
Stream's reference apps target 15). **Flutter 3.32+ enables Swift Package Manager by
default** (`flutter config` -> `enable-swift-package-manager: true`), so a fresh
`flutter create` produces **no `ios/Podfile`** - the Stream plugins resolve as Swift
packages.

> ### ⚠️ iOS + Swift Package Manager: do BOTH of these or the build fails
>
> On a fresh `flutter create` (3.44), the iOS deployment target is **13.0**, which is
> below `stream_video_flutter`'s minimum (14.0). You must raise it in **two** places -
> setting only the Xcode target is the #1 obstacle and produces a misleading error.
>
> **1. Xcode project deployment target** (governs the app binary), in all 3 configs:
>
> ```bash
> # ios/Runner.xcodeproj/project.pbxproj - Debug/Release/Profile
> sed -i '' 's/IPHONEOS_DEPLOYMENT_TARGET = 13.0;/IPHONEOS_DEPLOYMENT_TARGET = 15.0;/g' ios/Runner.xcodeproj/project.pbxproj
> ```
>
> Equivalently in Xcode: Runner target -> General -> Minimum Deployments -> iOS 15.0.
>
> **2. `MinimumOSVersion` in `ios/Flutter/AppFrameworkInfo.plist`** (governs the
> generated SPM plugin package). **This is the step everyone misses.** Flutter
> generates the plugin SPM package's platform
> (`ios/Flutter/ephemeral/Packages/FlutterGeneratedPluginSwiftPackage/Package.swift`
> -> `.iOS("…")`) from this key. On Flutter 3.44 the key is **absent and defaults to
> 13.0**, so even with the Xcode target at 15.0 the build still fails with:
>
> > To fix this error, increase your app's minimum platform version from 13.0 to at
> > least 14.0 or remove the stream-video-flutter dependency.
>
> Add the key (the file has no `MinimumOSVersion` by default - insert it):
>
> ```xml
> <!-- ios/Flutter/AppFrameworkInfo.plist, inside the top-level <dict> -->
> <key>MinimumOSVersion</key>
> <string>15.0</string>
> ```

Only if the project still uses CocoaPods (an `ios/Podfile` exists) also set
`platform :ios, '15.0'` at the top of the Podfile. Don't add a Podfile to an
SPM project just to set the deployment target - it triggers a "non-standard Podfile /
migrate to Swift Package Manager" warning and a redundant CocoaPods integration.

#### Silence analyzer noise from the SPM checkout (do this once, right after install)

With SPM, the iOS build checks out each plugin's **entire repo** into
`build/ios/SourcePackages/<pkg>/`, including the SDK's own `example/` app and `test/`
dirs. Those Dart files import packages the host app doesn't have (`firebase_core`,
`mocktail`, `alchemist`), so the Dart analyzer and the IDE report 100+ phantom
`uri_does_not_exist` / undefined-name errors that can block "Run". The app code is
fine - exclude the build output from analysis in `analysis_options.yaml`:

```yaml
analyzer:
  exclude:
    - build/**
```

Then restart the Dart analysis server / reload the IDE window to drop cached
diagnostics. Trust `flutter analyze` (whole project, clean) and `flutter build bundle`
(exit 0 - compiles all Dart against the real SDK) over IDE squiggles.

### Client Initialization

> **Docs:** [Quickstart](https://getstream.io/video/docs/flutter/setup/quickstart/) · [Authentication](https://getstream.io/video/docs/flutter/guides/authentication/)

Initialize `StreamVideo` **once** before `runApp`. Never create it inside a `build` method, `StatelessWidget`, or a computed getter that re-runs on rebuild.

```dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final client = StreamVideo(
    'your_api_key',
    user: User.regular(
      userId: 'user-id',
      name: 'User Name',
      image: 'https://example.com/avatar.jpg',
    ),
    userToken: 'your_user_token', // raw JWT string
  );

  runApp(MyApp(client: client));
}
```

`StreamVideo` registers a singleton on construction. Access it anywhere in the app with:

```dart
StreamVideo.instance
```

Accessing `StreamVideo.instance` before construction throws a `StateError`.

---

## User Authentication

> **Docs:** [Authentication](https://getstream.io/video/docs/flutter/guides/authentication/)

The API key and secret are shared between Chat and Video - one Stream project, one key.

### Static token (no expiry)

```dart
final client = StreamVideo(
  'your_api_key',
  user: User.regular(userId: 'alice', name: 'Alice Smith'),
  userToken: 'your_static_token', // raw JWT string, NOT UserToken.jwt(...)
);
```

Token generation: `stream token <user_id>` (same CLI as Chat).

### Token provider (expiring tokens)

Pass a `tokenLoader` closure that is called automatically when the token expires:

```dart
final client = StreamVideo(
  'your_api_key',
  user: User.regular(userId: 'alice', name: 'Alice Smith'),
  tokenLoader: (userId) async {
    final newToken = await yourAuthService.fetchVideoToken(userId);
    return newToken; // Future<String>
  },
);
```

With a `tokenLoader`, the initial `userToken` can be omitted - the loader is called for the
first token and on every expiry.

### Switching users / resetting the client

To switch the signed-in user (or log out), tear down the existing `StreamVideo` singleton
before constructing a new one:

```dart
await StreamVideo.reset(disconnect: true); // no-op if none exists; safe to always call
```

- Use `StreamVideo.reset({bool disconnect = false})` before creating a new instance. Pass `disconnect: true` to close the WebSocket.
- `connect()` is safe to call multiple times; it reuses/returns the current connection if already connecting/connected. If it fails, reset before trying again.
- Choose the correct user type: use `User.regular` for static tokens, or `User.guest` for name-only sign-in with no backend.

### Guest users (no login, no backend)

Use a **guest user** when you don't have a backend or don't need user logins—just a name (or nothing). Pass `User.guest(...)` and leave out `userToken`; the SDK handles the rest, fetching a guest token automatically. Never use development tokens for this.

```dart
StreamVideo(
  'your_api_key',
  user: User.guest(userId: 'jane', name: 'Jane'), // userId is only a hint
);

// Connect explicitly so the guest token is fetched and the real id is assigned
// before you do anything else (or rely on autoConnect and await the same call):
final result = await StreamVideo.instance.connect();

// IMPORTANT: the server issues a *generated* guest id that differs from the one
// you passed. Read it back and use THIS everywhere (call members, your own UI):
final realUserId = StreamVideo.instance.currentUser.id;
```

### Anonymous users (watch-only)

`User.anonymous()` is **not** for interactive calling. Anonymous users **cannot open a
WebSocket**, so they receive no call events (participant joins, etc.) - `connect()`
explicitly rejects them. They can only **watch** a livestream or join a specific call, and
they require a token whose payload pins the allowed calls via `call_cids`
(e.g. `{"user_id": "!anon", "role": "viewer", "call_cids": ["livestream:123"]}`). Use them
only for livestream viewers, never for 1:1 / group calling or anything that needs presence.

> **Don't use development tokens to fake a no-backend login.** Dev tokens require disabling
> auth checks for the whole app (insecure) and aren't an SDK auth type here. For no-backend
> name-only sign-in use **guest**; for production accounts use `User.regular` + `tokenLoader`.

---

## Making and Joining Calls

> **Docs:** [Joining & Creating Calls](https://getstream.io/video/docs/flutter/guides/joining-and-creating-calls/)

### Create a Call object

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.defaultType(), // factory - note the parentheses
  id: 'my-call-id',
);
```

`makeCall` is synchronous and returns a `Call` object. It does **not** contact the server yet.

### Get or create the call server-side

```dart
await call.getOrCreate();
```

Creates the call on Stream's server if it does not exist, or fetches the existing one. Always call this before `join()`.

### Join a call

```dart
final result = await call.join();
result.fold(
  success: (_) {
    // Navigate to the active call screen
  },
  failure: (failure) {
    debugPrint('Join failed: ${failure.error.message}');
  },
);
```

`join()` establishes the WebRTC connection. It returns a `Result` - always check it. Ignoring a failure leaves the UI stuck on a call screen with no active media.

### Leave a call

```dart
await call.leave();
```

Disconnects the current user. Other participants remain in the call.

### End a call for all participants

```dart
await call.end();
```

Terminates the session for everyone. Requires the caller to have host or admin permissions on the call.

### Start a ringing call

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.defaultType(),
  id: const Uuid().v4(),
);
await call.getOrCreate(
  memberIds: ['alice', 'bob'],
  ringing: true,
);
```

`ringing: true` sends push notifications to all members. Requires push configuration for each target platform.

To ring members of an **existing** call:

```dart
await call.ring(userIds: ['alice', 'bob']); // note: userIds, not memberIds
```

> **Full ringing flow:** outgoing ring, incoming-call handling across foreground /
> background / terminated states, CallKit (iOS) + FCM (Android) setup, accept/reject/end,
> and missed calls live in the dedicated pair: [`RINGING-FLUTTER.md`](RINGING-FLUTTER.md) +
> [`RINGING-FLUTTER-blueprints.md`](RINGING-FLUTTER-blueprints.md). This snippet only
> creates the outgoing call - it does not configure push.

### Ringing events

`flutter_callkit_incoming` was removed in v1.0.0. The ringing event API was renamed:

| v0.x                          | v1.x                                                 |
| ----------------------------- | ---------------------------------------------------- |
| `onCallKitEvent`              | `onRingingEvent`                                     |
| `CallKitEvent`                | `RingingEvent`                                       |
| `nameCaller`                  | `callerName`                                         |
| `pushParams`                  | `pushConfiguration` (`StreamVideoPushConfiguration`) |
| `callerCustomizationCallback` | **Removed**                                          |
| `backgroundVoipCallHandler`   | **Removed**                                          |

```dart
// onRingingEvent is a method that registers a listener and returns a subscription
final sub = StreamVideo.instance.onRingingEvent((event) {
  // handle RingingEvent
});
// later: sub?.cancel();
```

---

## Call Controls

> **Docs:** [Camera](https://getstream.io/video/docs/flutter/guides/camera-and-microphone/camera/) · [Microphone & Audio](https://getstream.io/video/docs/flutter/guides/camera-and-microphone/microphone-and-audio/) · [Camera Zoom](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/camera-zoom/) · [Camera Focus](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/camera-focus/)

All device controls are methods on `Call` directly (there are no `call.camera` / `call.microphone` manager objects):

```dart
// Camera
await call.setCameraEnabled(enabled: true);
await call.setCameraEnabled(enabled: false);
await call.flipCamera();                          // switch front/back
await call.setZoom(zoomLevel: 2.0);               // zoom (v0.9.1+)
await call.focus(focusPoint: const Point(0.5, 0.5)); // tap-to-focus (v0.9.1+)

// Microphone
await call.setMicrophoneEnabled(enabled: true);
await call.setMicrophoneEnabled(enabled: false);

// Audio output (speaker vs earpiece) - pick an RtcMediaDevice and set it
await call.setAudioOutputDevice(device);
// For the common speakerphone toggle, use the pre-built widget instead:
// ToggleSpeakerphoneOption(call: call)

// Screen sharing (see Screen Sharing section)
await call.setScreenShareEnabled(enabled: true);

// Kick a participant (requires host/admin) - userId is positional
await call.kickUser('alice');  // v0.10.4+

// Ring specific members of an existing call
await call.ring(userIds: ['alice', 'bob']);

// Track call duration
call.callDurationStream  // Stream<Duration> (v0.9.3+)
```

All `set*Enabled` methods and `flipCamera()` return `Future<Result<None>>` - check the result in production code.

**Read current device state** from the local participant:

```dart
final local = call.state.value.localParticipant;
final cameraOn = local?.isVideoEnabled ?? false;
final micOn = local?.isAudioEnabled ?? false;
```

---

## Call State and Participants

> **Docs:** [Call State](https://getstream.io/video/docs/flutter/guides/call-state/) · [Pinning Users](https://getstream.io/video/docs/flutter/ui-cookbook/participants/pinning-users/) · [Participants Sorting](https://getstream.io/video/docs/flutter/guides/participants-sorting/)

`call.state` is a `StateEmitter<CallState>` - it is NOT a `Stream`. Access the current value synchronously via `.value`, or convert with `.asStream()` for reactive widgets:

```dart
// Current snapshot (synchronous)
final state = call.state.value;
final participants = state.callParticipants;   // all, including local
final local = state.localParticipant;          // CallParticipantState?
final others = state.otherParticipants;        // everyone except local

// Reactive - rebuild when state changes
StreamBuilder<CallState>(
  stream: call.state.asStream(),  // StateEmitter is not a Stream - convert it
  initialData: call.state.value,
  builder: (context, snapshot) {
    final state = snapshot.requireData;
    return ListView(
      children: state.otherParticipants.map((p) => Text(p.name)).toList(),
    );
  },
)
```

There is no `remoteParticipants` getter on `CallState` - use `otherParticipants`.

**`CallParticipantState` key properties** (the participant model in `CallState` - not the `CallParticipant` coordinator model):

| Property            | Type                    | Description                              |
| ------------------- | ----------------------- | ---------------------------------------- |
| `userId`            | `String`                | Participant user ID                      |
| `name`              | `String`                | Display name                             |
| `image`             | `String?`               | Avatar URL                               |
| `isVideoEnabled`    | `bool`                  | Camera on                                |
| `isAudioEnabled`    | `bool`                  | Microphone active                        |
| `isSpeaking`        | `bool`                  | Currently speaking                       |
| `isDominantSpeaker` | `bool`                  | Loudest active speaker                   |
| `videoTrack`        | `TrackState?`           | Video track state                        |
| `audioLevels`       | `List<double>`          | Audio level samples (v0.8.3+)            |
| `pin`               | `CallParticipantPin?`   | Pin state (v0.8.4+, replaced `isPinned`) |
| `participantSource` | `SfuParticipantSource?` | WebRTC / RTMP / WHIP source (v0.10.4+)   |

**Active speakers** (available as top-level `CallState` property since v0.8.3):

```dart
final activeSpeakers = call.state.value.activeSpeakers; // List<CallParticipantState>
```

**Partial state** - subscribe only to a slice of state (more efficient than full `CallState` rebuilds). `partialState` is a generic method taking a selector; in widgets prefer the `PartialCallStateBuilder` widget:

```dart
// Stream of a selected slice (v0.10.0+)
final countStream = call.partialState((state) => state.callParticipants.length);

// Widget form - rebuilds only when the selected value changes
PartialCallStateBuilder<bool>(
  call: call,
  selector: (state) => state.localParticipant?.isAudioEnabled ?? false,
  builder: (context, micOn) => Icon(micOn ? Icons.mic : Icons.mic_off),
)
```

**Participant pinning** (v0.8.4+) - `pinned` is required on both methods:

```dart
// Pin locally only (synchronous - no await)
call.setParticipantPinnedLocally(userId: 'alice', sessionId: session, pinned: true);

// Pin for everyone (requires admin/host)
await call.setParticipantPinnedForEveryone(userId: 'alice', sessionId: session, pinned: true);
```

---

## Video Rendering

> **Docs:** [Video Renderer](https://getstream.io/video/docs/flutter/ui/video-render/)

Use `StreamVideoRenderer` to render a participant's video track. `videoTrackType` is **required**:

```dart
import 'package:stream_video_flutter/stream_video_flutter.dart';

StreamVideoRenderer(
  call: call,
  participant: participant,           // CallParticipantState
  videoTrackType: SfuTrackType.video, // required; SfuTrackType.screenShare for screen share
  videoFit: VideoFit.cover,           // optional, defaults to cover
)
```

`videoFit` controls scaling: `VideoFit.cover` fills the container (may crop); `VideoFit.contain` fits without cropping.

For the local preview before joining, prefer the pre-built `StreamLobbyView` (see Lobby section). For a manual preview, read `call.state.value.localParticipant` and pass it to `StreamVideoRenderer`.

---

## Pre-built UI (StreamCallContainer)

> **Docs:** [UI Overview](https://getstream.io/video/docs/flutter/ui/overview/) · [Call Container](https://getstream.io/video/docs/flutter/ui/call-container/) · [Call Content](https://getstream.io/video/docs/flutter/ui/call-content/)

`StreamCallContainer` renders the complete call UI - participant grid, controls, and camera feed. Use it unless you need a fully custom layout.

```dart
import 'package:stream_video_flutter/stream_video_flutter.dart';

class ActiveCallPage extends StatelessWidget {
  const ActiveCallPage({super.key, required this.call});

  final Call call;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: StreamCallContainer(
        call: call,
        onBackPressed: () => Navigator.of(context).pop(),
        onLeaveCallTap: () async {
          await call.leave();
          if (context.mounted) Navigator.of(context).pop();
        },
      ),
    );
  }
}
```

`StreamCallContainer` handles incoming/outgoing ringing states and the active call grid automatically when the call was started with `ringing: true`.

Do not embed `StreamCallContainer` inside a `SingleChildScrollView` or `CustomScrollView` - it manages its own layout and fill.

For a composable middle ground between the all-in-one container and a fully custom layout, use `StreamCallContent` (call screen) and `StreamCallParticipants` (participant layouts with `ParticipantLayoutMode.grid` / `.spotlight` / `.pictureInPicture`).

---

## Lobby / Pre-join Screen (StreamLobbyView)

> **Docs:** [Call Lobby](https://getstream.io/video/docs/flutter/ui-cookbook/layouts/call-lobby/) · [Initial Call Configuration](https://getstream.io/video/docs/flutter/guides/camera-and-microphone/initial-call-configuration/)

`StreamLobbyView` is the pre-built pre-join screen: camera preview, device toggles, and a join button. Do not hand-build a preview screen unless the design requires it.

```dart
StreamLobbyView(
  call: call,
  onJoinCallPressed: (CallConnectOptions connectOptions) async {
    final result = await call.join(connectOptions: connectOptions);
    result.fold(
      success: (_) { /* navigate to call screen */ },
      failure: (error) { /* show error */ },
    );
  },
)
```

The `CallConnectOptions` passed to the callback reflect the camera/mic toggles the user chose in the lobby - forward them to `call.join(connectOptions:)`.

---

## Screen Sharing

> **Docs:** [Screen Sharing](https://getstream.io/video/docs/flutter/advanced/screen-sharing/)

```dart
// Start / stop sharing the local screen
await call.setScreenShareEnabled(enabled: true);
await call.setScreenShareEnabled(enabled: false);

// Optional constraints (resolution, etc.)
await call.setScreenShareEnabled(
  enabled: true,
  constraints: const ScreenShareConstraints(),
);
```

Render a participant's screen-share track with `StreamVideoRenderer(videoTrackType: SfuTrackType.screenShare, ...)`. The pre-built `ToggleScreenShareOption` control widget is also available.

**iOS broadcast mode** requires the separate `stream_video_screen_sharing` package (native `BroadcastSampleHandler`) plus a Broadcast Upload Extension target in Xcode. **Android** requires a foreground service; screen audio capture is supported via `captureScreenAudio`. Full platform setup: <https://getstream.io/video/docs/flutter/advanced/screen-sharing/>

---

## Recording

> **Docs:** [Call Recording](https://getstream.io/video/docs/flutter/advanced/call-recording/)

```dart
await call.startRecording();          // requires call-type permission
await call.stopRecording();
final recordings = await call.listRecordings();
```

Recording state is on `call.state` - the pre-built `ToggleRecordingOption` widget wires this up. Recordings are processed server-side and listed per session.

---

## Closed Captions and Transcription

> **Docs:** [Closed Captions](https://getstream.io/video/docs/flutter/guides/closed_captions/) · [Closed Caption UI](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/closed_caption/) · [Transcriptions](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/transcriptions/)

```dart
// Closed captions
await call.startClosedCaptions();     // optional: language, enableTranscription
await call.stopClosedCaptions();

// Live captions stream
call.closedCaptions  // Stream<List<StreamClosedCaption>>

// Transcription (server-side transcript files)
await call.startTranscription();      // optional: external storage
await call.stopTranscription();
```

Caption display behavior (visible captions count, visibility duration) is configurable via `DefaultCallPreferences` passed when creating the call. The pre-built `ToggleClosedCaptionsOption` widget is available.

---

## Picture-in-Picture

> **Docs:** [Picture-in-Picture](https://getstream.io/video/docs/flutter/advanced/picture-in-picture/)

Two parts: the Android activity (below) and the per-screen configuration.

**Android:** extend `StreamFlutterActivity` in `MainActivity.kt` (see Platform Setup).

**Configuration:** pass `PictureInPictureConfiguration` to `StreamCallContent` (or `LivestreamPlayer` for livestreams):

```dart
StreamCallContent(
  call: call,
  pictureInPictureConfiguration: const PictureInPictureConfiguration(
    enablePictureInPicture: true,
    // pipTrackPriority: PipTrackPriority.screenShare (default) or .camera
    // androidPiPConfiguration / iOSPiPConfiguration for platform tweaks
  ),
)
```

PiP engages automatically when the app goes to background. iOS is supported via the `iOSPiPConfiguration`. A `sort` comparator controls which participant shows in the PiP window (defaults to speaker / screen-sharer priority).

---

## Also available (entry points only)

> **Docs:** [Reactions](https://getstream.io/video/docs/flutter/guides/reactions/) · [Custom Data](https://getstream.io/video/docs/flutter/advanced/custom-data/) · [Background Modes](https://getstream.io/video/docs/flutter/advanced/background-modes/)

- **Reactions:** `call.sendReaction(...)`; auto-dismiss configurable via `DefaultCallPreferences.reactionAutoDismissTime`
- **Custom realtime events:** `call.sendCustomEvent(...)`
- **RTMP broadcast out:** `call.startRtmpBroadcasts(...)` / `call.stopRtmpBroadcast(...)`
- **Per-call preferences:** pass `DefaultCallPreferences(...)` when creating the call - reconnect timeouts, captions display, reactions, per-call audio policy (v1.4.0+)
- **Background behavior:** `StreamVideoOptions(muteVideoWhenInBackground:, muteAudioWhenInBackground:, keepConnectionsAliveWhenInBackground:)`
- **Multiple simultaneous calls:** `StreamVideoOptions(allowMultipleActiveCalls: true)` (v0.9.5+); pair with `Call.ensureNativeFactory()` for pre-join media (v1.4.0+)

---

## Audio Configuration (v1.3.0+)

> **Docs:** [Microphone & Audio](https://getstream.io/video/docs/flutter/guides/camera-and-microphone/microphone-and-audio/) · [High-Fidelity Audio](https://getstream.io/video/docs/flutter/guides/camera-and-microphone/high-fidelity-audio/)

`audioConfigurationPolicy` replaces the old `androidAudioConfiguration` parameter:

```dart
StreamVideo(
  'your_api_key',
  user: User.regular(userId: 'alice'),
  userToken: token, // raw JWT string
  options: StreamVideoOptions(
    audioConfigurationPolicy: AudioConfigurationPolicy.broadcaster(),
    // or: .viewer(), .hiFi(), .custom(...)
  ),
);
```

Predefined policies:

| Policy                                   | Use case                                  |
| ---------------------------------------- | ----------------------------------------- |
| `AudioConfigurationPolicy.broadcaster()` | Host/sender - optimized for publishing    |
| `AudioConfigurationPolicy.viewer()`      | Viewer/listener - optimized for receiving |
| `AudioConfigurationPolicy.hiFi()`        | Music or high-fidelity audio calls        |
| `AudioConfigurationPolicy.custom(...)`   | Full manual control                       |

For per-call audio config overrides, set on `DefaultCallPreferences` (v1.4.0+).

> **`androidAudioConfiguration` is deprecated** - use `audioConfigurationPolicy` instead.

---

## Noise Cancellation

> **Docs:** [Noise Cancellation](https://getstream.io/video/docs/flutter/guides/camera-and-microphone/noise-cancellation/)

Noise cancellation requires the **separate** `stream_video_noise_cancellation` package - it is NOT built into `stream_video_flutter`:

```yaml
# pubspec.yaml
stream_video_noise_cancellation: ^1.4.0
```

```dart
import 'package:stream_video_noise_cancellation/stream_video_noise_cancellation.dart';

StreamVideo(
  'your_api_key',
  user: user,
  userToken: token,
  options: StreamVideoOptions(
    audioProcessor: NoiseCancellationAudioProcessor(),
  ),
);
```

Whether it engages per call is controlled by the call type's noise cancellation settings (`NoiseCancellationSettingsMode.autoOn` enables it automatically).

---

## Video Filters

> **Docs:** [Video Filters](https://getstream.io/video/docs/flutter/advanced/video-filters/)

```yaml
stream_video_filters: ^1.4.0
```

Do not import from `stream_video_flutter` for filters - import from `stream_video_filters`.

---

## Call Types

> **Docs:** [Call Types](https://getstream.io/video/docs/flutter/guides/call-types/)

| Type                               | Use case                                                |
| ---------------------------------- | ------------------------------------------------------- |
| `StreamCallType.defaultType()`     | Standard peer-to-peer and small-group video/audio calls |
| `StreamCallType.audioRoom()`       | Audio-only group rooms                                  |
| `StreamCallType.liveStream()`      | One-to-many broadcasting                                |
| `StreamCallType.custom('my-type')` | Custom call type configured in the dashboard            |

All call types are factory constructors - there is no public unnamed `StreamCallType(...)` constructor. Use `StreamCallType.defaultType()` for most calling scenarios. `audio_room` and `livestream` have different permission and layout models.

**Livestream:** For one-to-many broadcasts with host/viewer split, backstage mode, `goLive()`/`stopLive()`, and HLS viewer support, load the dedicated references instead of this file:

- SDK patterns, backstage, goLive/stopLive, HLS -> [`LIVESTREAM-FLUTTER.md`](LIVESTREAM-FLUTTER.md)
- Mode selection, creator widget, viewer widget blueprints -> [`LIVESTREAM-FLUTTER-blueprints.md`](LIVESTREAM-FLUTTER-blueprints.md)

**Advanced use cases:** For audio rooms (request-to-speak), multiple simultaneous calls, Chat + Video in one app, TikTok-style livestream feeds, and the advanced call-management surface (queryCalls, call events, preferences, moderation, session timers, network handling), load:

- SDK patterns -> [`VIDEO-ADVANCED-FLUTTER.md`](VIDEO-ADVANCED-FLUTTER.md)
- Use-case blueprints -> [`VIDEO-ADVANCED-FLUTTER-blueprints.md`](VIDEO-ADVANCED-FLUTTER-blueprints.md)

---

## Roles and Permissions

> **Docs:** [Permissions & Moderation](https://getstream.io/video/docs/flutter/guides/permissions-and-moderation/) · [Permission Requests UI](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/permission-requests/)

Stream Video access control has three layers. **It is configured server-side (Stream
Dashboard / API), not in the Flutter app** - the SDK only reads the result and lets you
request/grant capabilities at runtime.

1. **Roles** - a user has an app-level role (`user`, `moderator`, `admin`, ...) and can
   also be assigned a per-call role via call membership (commonly `host`). Built-in call
   roles: `user`, `moderator`, `host`, `admin`, `call_member`.
2. **Capabilities (permissions)** - granular actions a participant may perform, identified
   by string aliases (e.g. `send-audio`, `join-backstage`). In Dart these are the
   `CallPermission` enum.
3. **Grants** - the per-call-type mapping of role -> list of capabilities, e.g.
   `grants: { host: ['join-backstage', 'send-audio', 'send-video'], user: ['send-audio'] }`.
   A user's effective capabilities are computed from app-level + call-level roles against
   the call type's grants.

### Reading capabilities in the SDK

```dart
// Does the local user currently have a capability?
final canPublish = call.hasPermission(CallPermission.sendAudio);

// All current capabilities for the local user:
final List<CallPermission> caps = call.state.value.ownCapabilities;
```

`ownCapabilities` is reactive - it updates (and emits `StreamCallPermissionsUpdatedEvent`
on `call.callEvents`) when a host grants or revokes a capability.

### Requesting / granting at runtime

```dart
// Participant asks for a capability they lack (e.g. listener wants to speak):
await call.requestPermissions([CallPermission.sendAudio]);

// A user WITH update-call-permissions (host/admin) grants or revokes:
await call.grantPermissions(userId: 'alice', permissions: [CallPermission.sendAudio]);
await call.revokePermissions(userId: 'alice', permissions: [CallPermission.sendAudio]);

// Host handles incoming requests:
call.onPermissionRequest = (StreamCallPermissionRequestEvent req) {
  // inspect req.user, req.permissions, then grantPermissions(...)
};
```

### `CallPermission` capability aliases (Dart enum -> server string)

| Capability group         | `CallPermission` values (alias)                                                                                                                                                                                                         |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Join / read              | `joinCall` (`join-call`), `readCall` (`read-call`), `joinEndedCall` (`join-ended-call`), `joinBackstage` (`join-backstage`)                                                                                                             |
| Publish media            | `sendAudio` (`send-audio`), `sendVideo` (`send-video`), `screenshare` (`screenshare`)                                                                                                                                                   |
| Moderation               | `muteUsers` (`mute-users`), `blockUsers` (`block-users`), `kickUser` (`kick-user`), `endCall` (`end-call`), `removeCallMember` (`remove-call-member`), `updateCallMember` (`update-call-member`), `pinForEveryone` (`pin-for-everyone`) |
| Call management          | `createCall` (`create-call`), `updateCall` (`update-call`), `updateCallSettings` (`update-call-settings`), `updateCallPermissions` (`update-call-permissions`), `changeMaxDuration` (`change-max-duration`)                             |
| Broadcast / record       | `startBroadcastCall` / `stopBroadcastCall`, `startRecordCall` / `stopRecordCall`, `startFrameRecordCall` / `stopFrameRecordCall`, `startIndividualRecordCall` / `stopIndividualRecordCall`, `startRawRecordCall` / `stopRawRecordCall`  |
| Transcription / captions | `startTranscriptionCall` / `stopTranscriptionCall`, `startClosedCaptionsCall` / `stopClosedCaptionsCall`, `sendClosedCaptionsCall` (`send-closed-captions-call`)                                                                        |
| Misc                     | `createReaction` (`create-reaction`), `enableNoiseCancellation` (`enable-noise-cancellation`)                                                                                                                                           |

This enum is the source of truth in the SDK; the dashboard exposes the same string
aliases. To enumerate all server-side permissions at runtime, call the
`listPermissions()` API.

> **Where this matters most:** the `livestream` and `audio_room` call types are built
> around capability gating - `join-backstage` controls who can enter before going live,
> and `send-audio` controls who can speak. Misconfigured grants are the usual cause of
> "viewers can hear the host before the stream starts" or "listeners can't unmute". See
> the backstage security note in [`LIVESTREAM-FLUTTER.md`](LIVESTREAM-FLUTTER.md) and the
> request-to-speak loop in [`VIDEO-ADVANCED-FLUTTER.md`](VIDEO-ADVANCED-FLUTTER.md).

---

## Troubleshooting

> **Docs:** [Troubleshooting](https://getstream.io/video/docs/flutter/advanced/troubleshooting/) · [Network Disruptions](https://getstream.io/video/docs/flutter/advanced/network-disruptions/)

### Connection issues

**Expired token** - when using expiring tokens, always supply a `tokenLoader` so the SDK can refresh automatically without a manual reconnect.

**Wrong API key** - use the key from the Stream dashboard for your project. Tokens are signed per-project; using another project's key silently rejects every request.

**User/token mismatch** - the token must be signed for the same `userId` passed to `User.regular(userId:)`. Mismatched IDs cause an auth error even when both values look valid.

### Platform permission failures

**Android runtime denial** - manifest entries are required but insufficient on Android 6+. Call `Permission.camera.request()` and `Permission.microphone.request()` (via `permission_handler`) before joining. Without runtime grants, the camera/mic opens silently empty.

**iOS silent failure** - if `NSCameraUsageDescription` or `NSMicrophoneUsageDescription` are absent from `Info.plist`, iOS denies access with no system prompt and no error. The call connects but the local track is empty.

### Ringing issues

**Calling yourself** - caller and callee must be different users. A user cannot receive a ringing notification for their own call.

**Unknown member** - the callee must have connected to Stream at least once so the platform knows their push token. Ensure all ring targets have signed in before testing.

**Reused call ID** - ringing fires only once per call ID. Always generate a fresh ID (e.g. `const Uuid().v4()`) for every ringing call.

---

## Gotchas

- **Initialize `StreamVideo` before `runApp`.** Creating it inside a `build` method creates a new instance on every rebuild - each construction resets the singleton.
- **Always `await call.getOrCreate()` before `call.join()`.** Calling `join()` on a call that does not exist server-side returns a failure result.
- **Always check `call.join()` result.** `join()` does not throw - it returns a `Result`. Ignoring a failure leaves the UI on the call screen with no active WebRTC session.
- **Use `call.leave()` for a single user exit; `call.end()` only when closing for everyone.** `end()` disconnects all participants and requires host/admin permissions.
- **Request Android runtime permissions before joining.** Manifest entries alone are not enough on API 23+.
- **Never put the API secret in app code.** Only the API key and user token belong in the app; the secret stays server-side.
- **The API key is shared between Chat and Video.** One Stream project, one key - token generation with the CLI is the same command for both products.
- **`StreamVideo.instance` throws before construction.** Always construct `StreamVideo(...)` in `main()` before any widget or service accesses the singleton.
- **`flutter_callkit_incoming` removed in v1.0.0.** If upgrading from v0.x, replace `onCallKitEvent`/`CallKitEvent` with `onRingingEvent`/`RingingEvent` and update push configuration from `pushParams` to `pushConfiguration`.
- **Video filters moved to `stream_video_filters` in v1.0.0.** Add the separate package if you use blur/virtual background.
- **Android PiP requires `StreamFlutterActivity` since v0.10.0.** Extend `StreamFlutterActivity` in `MainActivity.kt` instead of `FlutterActivity`.
- **Android build tooling updated in v0.11.0.** Requires compileSDK 36, AGP >=8.12.1, Gradle >=8.13, Kotlin 2.2.0.
- **`isPinned` replaced by `pin` object in v0.8.4.** Use `participant.pin != null` instead of `participant.isPinned`.
- **`androidAudioConfiguration` deprecated in v1.3.0.** Use `audioConfigurationPolicy` instead.
- **`CompositeSubscription` is an rxdart type, not re-exported by `stream_video`.** Anything returning it (e.g. the ringing observers) needs `import 'package:rxdart/rxdart.dart';` and `rxdart` in `pubspec.yaml`; cancel with `dispose()`/`cancel()`/`clear()` (no `cancelAll()`).
- **`call.state` is a `StateEmitter`, not a `Stream`.** Use `call.state.value` for snapshots, `call.state.asStream()` for `StreamBuilder`, or `PartialCallStateBuilder` for slice-based rebuilds.
- **`StreamVideoRenderer` requires `videoTrackType`.** Pass `SfuTrackType.video` (or `.screenShare`); omitting it does not compile.
- **There are no `call.camera` / `call.microphone` / `call.speakerphone` objects.** Device controls are methods on `Call`: `setCameraEnabled`, `setMicrophoneEnabled`, `flipCamera`, `setAudioOutputDevice`.
- **Noise cancellation needs `stream_video_noise_cancellation`.** Wire `audioProcessor: NoiseCancellationAudioProcessor()` in `StreamVideoOptions`.
- **No `ios/Podfile` on fresh projects.** Flutter 3.32+ defaults to Swift Package Manager, so `flutter create` ships no Podfile - the Stream plugins are Swift packages. Set the iOS deployment target in `ios/Runner.xcodeproj/project.pbxproj` (`IPHONEOS_DEPLOYMENT_TARGET`, all 3 configs) / Xcode, not a Podfile. Adding a Podfile just for the target triggers a "non-standard Podfile / migrate to SPM" warning.
- **Android uses the Kotlin DSL `build.gradle.kts`.** Recent `flutter create` generates `android/app/build.gradle.kts` with `minSdk`/`compileSdk` (no `Version` suffix) defaulting to `flutter.minSdkVersion`/`flutter.compileSdkVersion`. Raise the floor with `minSdk = maxOf(24, flutter.minSdkVersion)` and `compileSdk = maxOf(36, flutter.compileSdkVersion)` rather than pasting the Groovy `minSdkVersion 24` / `compileSdkVersion 36` snippets, which won't parse in `.kts`.
- **Fresh `flutter create` (3.44) sets `IPHONEOS_DEPLOYMENT_TARGET = 13.0` in three places** in `ios/Runner.xcodeproj/project.pbxproj` (Debug/Release/Profile). Bump all three to 15.0 — a one-liner works: `sed -i '' 's/IPHONEOS_DEPLOYMENT_TARGET = 13.0;/IPHONEOS_DEPLOYMENT_TARGET = 15.0;/g' ios/Runner.xcodeproj/project.pbxproj`.
- **The pbxproj target alone is NOT enough under SPM — also set `MinimumOSVersion` in `ios/Flutter/AppFrameworkInfo.plist`.** Flutter derives the generated plugin SPM package's platform from this key, which is absent (defaults to 13.0) on 3.44, so the build fails with _"increase your app's minimum platform version from 13.0 to at least 14.0"_ even after fixing the Xcode target. Add `<key>MinimumOSVersion</key><string>15.0</string>`. See the iOS Platform Setup section for the full two-step fix + verification.
- **SPM checkout floods the analyzer with phantom errors.** `build/ios/SourcePackages/<pkg>/` contains the SDK's own `example/`+`test/` Dart (importing `firebase_core`, `mocktail`, …). Add `analyzer: { exclude: [build/**] }` to `analysis_options.yaml` so the IDE/`flutter analyze` only sees your code.
- **`CallConnectOptions` defaults every track to DISABLED.** A bare `call.join()` / `CallConnectOptions()` publishes neither camera nor mic. For a video call pass `CallConnectOptions(camera: TrackOption.enabled(), microphone: TrackOption.enabled(), speakerDefaultOn: true)` explicitly; for audio-only use `camera: TrackOption.disabled(), microphone: TrackOption.enabled()`.
- **`StreamVideoOptions` is not `const`-constructible, and `TrackOption.enabled()/.disabled()` are non-const factories.** Don't write `const CallConnectOptions(...)` with `TrackOption.enabled()` inside — it won't compile.
