# Video - stream_video_flutter Setup & Integration

`stream_video_flutter` provides pre-built Flutter widgets for building video and audio calling experiences. This file covers package installation, client setup, authentication, call flows, customization, and gotchas. For widget blueprints, see [VIDEO-FLUTTER-blueprints.md](VIDEO-FLUTTER-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

- **Blueprint** - Widget structure and initialization
- **Wiring** - SDK calls for each component, exact property paths
- **Requirements** - Platform setup, SDK version, Flutter version

## Quick ref

- **Package (pre-built UI):** `stream_video_flutter` via pub.dev
- **Package (core only):** `stream_video` via pub.dev
- **First:** Installation -> platform setup -> client init -> `call.getOrCreate()` -> `call.join()` -> show `StreamCallContainer`
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/video/docs/flutter/`

Full widget blueprints: [VIDEO-FLUTTER-blueprints.md](VIDEO-FLUTTER-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation

Check pub.dev for the latest version before adding. At time of writing:

```yaml
# pubspec.yaml
dependencies:
  stream_video_flutter: ^0.8.0   # pre-built UI + core
  # OR for core only (no pre-built widgets)
  stream_video: ^0.8.0
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

Set the minimum SDK version in `android/app/build.gradle`:

```groovy
android {
    defaultConfig {
        minSdkVersion 24  // stream_video_flutter requires API 24+
    }
}
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

---

## Call Controls

```dart
// Camera
await call.camera.enable();
await call.camera.disable();
await call.camera.flip();     // switch front/back

// Microphone
await call.microphone.enable();
await call.microphone.disable();

// Speaker
await call.speakerphone.enable();
await call.speakerphone.disable();
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

## Gotchas

- **Initialize `StreamVideo` before `runApp`.** Creating it inside a `build` method creates a new instance on every rebuild - each construction resets the singleton.
- **Always `await call.getOrCreate()` before `call.join()`.** Calling `join()` on a call that does not exist server-side returns a failure result.
- **Always check `call.join()` result.** `join()` does not throw - it returns a `Result`. Ignoring a failure leaves the UI on the call screen with no active WebRTC session.
- **Use `call.leave()` for a single user exit; `call.end()` only when closing for everyone.** `end()` disconnects all participants and requires host/admin permissions.
- **Request Android runtime permissions before joining.** Manifest entries alone are not enough on API 23+.
- **Never put the API secret in app code.** Only the API key and user token belong in the app; the secret stays server-side.
- **The API key is shared between Chat and Video.** One Stream project, one key - token generation with the CLI is the same command for both products.
- **`StreamVideo.instance` throws before construction.** Always construct `StreamVideo(...)` in `main()` before any widget or service accesses the singleton.
