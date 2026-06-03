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
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/video/docs/flutter/`

Full widget blueprints: [VIDEO-FLUTTER-blueprints.md](VIDEO-FLUTTER-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation

```yaml
# pubspec.yaml
dependencies:
  stream_video_flutter: ^1.4.0   # pre-built UI + core
  # OR for core only (no pre-built widgets)
  stream_video: ^1.4.0
  # Video filters (separate package since v1.0.0)
  stream_video_filters: ^1.4.0   # optional, only if using blur/virtual background
```

```bash
flutter pub get
```

Install only what is needed. Do not add `stream_video` separately when `stream_video_flutter` is chosen - the UI package re-exports it.

### Platform Setup

Complete platform setup **before** wiring the client. Missing permissions cause silent failures or crashes at call time, not at install time.

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

```groovy
android {
    compileSdkVersion 36  // required since stream_video_flutter v0.11.0
    defaultConfig {
        minSdkVersion 24  // stream_video_flutter requires API 24+
    }
}
```

Also update the project-level `android/build.gradle` to use AGP ≥8.12.1 and Gradle ≥8.13, and Kotlin 2.2.0+ (required since v0.11.0):

```groovy
// android/settings.gradle (or build.gradle depending on project structure)
id 'com.android.application' version '8.12.1' apply false
// Kotlin 2.2.0+
id 'org.jetbrains.kotlin.android' version '2.2.0' apply false
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

Add `permission_handler` to `pubspec.yaml` if not already present.

#### iOS

Add these keys to `ios/Runner/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>Video calls require camera access.</string>
<key>NSMicrophoneUsageDescription</key>
<string>Video calls require microphone access.</string>
```

Set minimum deployment target to iOS 14.0+ in `ios/Podfile`:

```ruby
platform :ios, '14.0'
```

And in Xcode: select the Runner target -> General -> Minimum Deployments -> iOS 14.0.

### Client Initialization

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
    userToken: UserToken.jwt('your_user_token'),
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

The API key and secret are shared between Chat and Video - one Stream project, one key.

### Static token (no expiry)

```dart
final client = StreamVideo(
  'your_api_key',
  user: User.regular(userId: 'alice', name: 'Alice Smith'),
  userToken: UserToken.jwt('your_static_token'),
);
```

Token generation: `stream token <user_id>` (same CLI as Chat).

### Token provider (expiring tokens)

Pass a `tokenLoader` closure that is called automatically when the token expires:

```dart
final client = StreamVideo(
  'your_api_key',
  user: User.regular(userId: 'alice', name: 'Alice Smith'),
  userToken: UserToken.jwt(initialToken),
  tokenLoader: (userId) async {
    final newToken = await yourAuthService.fetchVideoToken(userId);
    return newToken;
  },
);
```

---

## Making and Joining Calls

### Create a Call object

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.defaultType,
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
  failure: (error) {
    // Show error to the user
    debugPrint('Join failed: $error');
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
  callType: StreamCallType.defaultType,
  id: const Uuid().v4(),
);
await call.getOrCreate(
  memberIds: ['alice', 'bob'],
  ringing: true,
);
```

`ringing: true` sends push notifications to all members. Requires push configuration for each target platform.

To ring members of an **existing** call (v1.0.0+):

```dart
await call.ring(memberIds: ['alice', 'bob']);
```

### Ringing events (v1.0.0 — renamed from CallKit API)

`flutter_callkit_incoming` was removed in v1.0.0. The ringing event API was renamed:

| v0.x | v1.x |
|---|---|
| `onCallKitEvent` | `onRingingEvent` |
| `CallKitEvent` | `RingingEvent` |
| `nameCaller` | `callerName` |
| `pushParams` | `pushConfiguration` (`StreamVideoPushConfiguration`) |
| `callerCustomizationCallback` | **Removed** |
| `backgroundVoipCallHandler` | **Removed** |

```dart
StreamVideo.instance.onRingingEvent = (event) {
  // handle RingingEvent
};
```

---

## Call Controls

```dart
// Camera
await call.camera.enable();
await call.camera.disable();
await call.camera.flip();     // switch front/back
await call.camera.setZoom(2.0);  // zoom (v0.9.1+)
await call.camera.focus(offset);  // tap-to-focus (v0.9.1+)

// Microphone
await call.microphone.enable();
await call.microphone.disable();

// Speaker
await call.speakerphone.enable();
await call.speakerphone.disable();

// Kick a participant (requires host/admin)
await call.kickUser(userId: 'alice');  // v0.10.4+

// Ring specific members of an existing call (v1.0.0+)
await call.ring(memberIds: ['alice', 'bob']);

// Track call duration
call.callDurationStream  // Stream<Duration> (v0.9.3+)
```

**Read current device state** from the local participant:

```dart
final local = call.state.value.localParticipant;
final cameraOn = local?.isVideoEnabled ?? false;
final micOn = local?.isAudioEnabled ?? false;
```

---

## Call State and Participants

`call.state` is a `BehaviorSubject<CallState>`. Access the current value synchronously or observe changes reactively:

```dart
// Current snapshot (synchronous)
final state = call.state.value;
final participants = state.callParticipants;
final local = state.localParticipant;
final remote = state.remoteParticipants;

// Reactive - rebuild when state changes
StreamBuilder<CallState>(
  stream: call.state,
  initialData: call.state.value,
  builder: (context, snapshot) {
    final state = snapshot.requireData;
    return ListView(
      children: state.remoteParticipants.map((p) => Text(p.name)).toList(),
    );
  },
)
```

**`CallParticipant` key properties:**

| Property | Type | Description |
|---|---|---|
| `userId` | `String` | Participant user ID |
| `name` | `String` | Display name |
| `image` | `String?` | Avatar URL |
| `isVideoEnabled` | `bool` | Camera on |
| `isAudioEnabled` | `bool` | Microphone active |
| `isSpeaking` | `bool` | Currently speaking |
| `isDominantSpeaker` | `bool` | Loudest active speaker |
| `videoTrack` | `RtcVideoTrack?` | Renderable video track |
| `audioLevels` | `List<double>?` | Audio level samples (v0.8.3+) |
| `pin` | `ParticipantPin?` | Pin state (v0.8.4+, replaced `isPinned`) |
| `participantSource` | `ParticipantSource?` | WebRTC / RTMP / WHIP source (v0.10.4+) |

**Active speakers** (available as top-level `CallState` property since v0.8.3):

```dart
final activeSpeakers = call.state.value.activeSpeakers; // List<CallParticipantState>
```

**Partial state** — subscribe only to participant-level changes (more efficient than full `CallState` rebuilds):

```dart
call.partialState  // Stream<CallStatePartial> (v0.10.0+)
```

**Participant pinning** (v0.8.4+):

```dart
// Pin locally only
await call.setParticipantPinnedLocally(userId: 'alice', sessionId: session);

// Pin for everyone (requires admin/host)
await call.setParticipantPinnedForEveryone(userId: 'alice', sessionId: session);
```

---

## Video Rendering

Use `StreamVideoRenderer` to render a participant's video track:

```dart
import 'package:stream_video_flutter/stream_video_flutter.dart';

StreamVideoRenderer(
  call: call,
  participant: participant,
  videoFit: VideoFit.cover,
)
```

`videoFit` controls scaling: `VideoFit.cover` fills the container (may crop); `VideoFit.contain` fits without cropping.

For the local preview before joining, read `call.state.value.localParticipant` and pass it to `StreamVideoRenderer`.

---

## Pre-built UI (StreamCallContainer)

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

---

## Audio Configuration (v1.3.0+)

`audioConfigurationPolicy` replaces the old `androidAudioConfiguration` parameter:

```dart
StreamVideo(
  'your_api_key',
  user: User.regular(userId: 'alice'),
  userToken: UserToken.jwt(token),
  streamVideoOptions: StreamVideoOptions(
    audioConfigurationPolicy: AudioConfigurationPolicy.broadcaster(),
    // or: .viewer(), .hiFi(), .custom(...)
  ),
);
```

Predefined policies:

| Policy | Use case |
|---|---|
| `AudioConfigurationPolicy.broadcaster()` | Host/sender — optimized for publishing |
| `AudioConfigurationPolicy.viewer()` | Viewer/listener — optimized for receiving |
| `AudioConfigurationPolicy.hiFi()` | Music or high-fidelity audio calls |
| `AudioConfigurationPolicy.custom(...)` | Full manual control |

For per-call audio config overrides, set on `DefaultCallPreferences` (v1.4.0+).

> **`androidAudioConfiguration` is deprecated** — use `audioConfigurationPolicy` instead.

---

## Noise Cancellation (v0.8.0+)

Noise cancellation is built in and can be enabled via call preferences. No additional package is needed.

---

## Video Filters (v1.0.0+)

Since v1.0.0, video filters (blur background, virtual background) are in a **separate package**:

```yaml
stream_video_filters: ^1.4.0
```

Do not import from `stream_video_flutter` for filters — import from `stream_video_filters`.

---

## Call Types

| Type | Use case |
|---|---|
| `StreamCallType.defaultType` | Standard peer-to-peer and small-group video/audio calls |
| `StreamCallType('audio_room')` | Audio-only group rooms |
| `StreamCallType('livestream')` | One-to-many broadcasting |

Use `StreamCallType.defaultType` for most calling scenarios. `audio_room` and `livestream` have different permission and layout models.

**Livestream:** For one-to-many broadcasts with host/viewer split, backstage mode, `goLive()`/`stopLive()`, and HLS viewer support, load the dedicated references instead of this file:
- SDK patterns, backstage, goLive/stopLive, HLS -> [`LIVESTREAM-FLUTTER.md`](LIVESTREAM-FLUTTER.md)
- Mode selection, creator widget, viewer widget blueprints -> [`LIVESTREAM-FLUTTER-blueprints.md`](LIVESTREAM-FLUTTER-blueprints.md)

---

## Troubleshooting

Source: `https://getstream.io/video/docs/flutter/`

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

---

## v1.x Breaking Changes Summary (from v0.8.0)

| Area | v0.x | v1.x |
|---|---|---|
| Package version | `^0.8.0` | `^1.4.0` |
| Dart SDK | `^3.6.x` | `^3.8.0` |
| Flutter min | `3.27.4` | `>=3.32.0` |
| Android compileSDK | 34 | **36** |
| Android AGP | any | **≥8.12.1** |
| Android Kotlin | any | **2.2.0+** |
| Android `MainActivity` | extends `FlutterActivity` | extends `StreamFlutterActivity` (PiP) |
| Ringing events | `onCallKitEvent` / `CallKitEvent` | `onRingingEvent` / `RingingEvent` |
| Push config | `pushParams` | `pushConfiguration` (`StreamVideoPushConfiguration`) |
| Caller name param | `nameCaller` | `callerName` |
| Video filters | bundled | separate `stream_video_filters` package |
| `CallPreferences` | on `CallStateNotifier` | on `CallState` → `DefaultCallPreferences` |
| Participant pin | `isPinned: bool` / `setParticipantPinned()` | `pin: ParticipantPin?` / `setParticipantPinnedLocally()` |
| Audio config | `androidAudioConfiguration` | `audioConfigurationPolicy` (deprecated) |

**New APIs since v0.8.0:**
- `call.ring(memberIds:)` — ring members of an existing call
- `call.kickUser(userId:)` — remove a participant
- `call.callDurationStream` — live call timer
- `call.partialState` — efficient participant-level state updates
- `call.camera.setZoom()` / `call.camera.focus()` — camera control
- `call.statsReporter` — aggregated call metrics, battery/thermal tracking
- `AudioConfigurationPolicy` — broadcaster / viewer / hiFi / custom presets
- `Call.ensureNativeFactory()` — per-call native factory for multi-call scenarios

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
- **Android build tooling updated in v0.11.0.** Requires compileSDK 36, AGP ≥8.12.1, Gradle ≥8.13, Kotlin 2.2.0.
- **`isPinned` replaced by `pin` object in v0.8.4.** Use `participant.pin != null` instead of `participant.isPinned`.
- **`androidAudioConfiguration` deprecated in v1.3.0.** Use `audioConfigurationPolicy` instead.
