# Livestream - Flutter SDK Setup & Integration

Stream Video's `livestream` call type is built for one-to-many broadcasting. One host publishes audio and video; viewers receive it as WebRTC subscribers or via HLS. This file covers the call type, host/viewer flows, backstage mode, and gotchas. For full widget blueprints, see [LIVESTREAM-FLUTTER-blueprints.md](LIVESTREAM-FLUTTER-blueprints.md).

Rules: [../RULES.md](../RULES.md).

---

## Quick ref

- **Call type:** `StreamCallType('livestream')`
- **Package:** same `stream_video_flutter` as standard calls
- **Host path:** `getOrCreate()` -> `join()` -> backstage preview -> `call.goLive()` -> `call.stopLive()` -> `call.end()` -> `call.leave()`
- **Viewer path (WebRTC):** `getOrCreate()` -> `join()` -> watch `remoteParticipants` -> `call.leave()`
- **Viewer path (HLS):** get `call.state.value.egress?.hls?.playlistUrl` -> play with `video_player`
- **Docs:** `https://getstream.io/video/docs/flutter/advanced/livestreaming/`

---

## Call type: `livestream`

The `livestream` call type ships with a permission model designed for broadcasting:

| Role | Publish audio | Publish video | Receive | End call |
|---|---|---|---|---|
| Host / admin | Yes | Yes | Yes | Yes |
| Viewer (subscriber) | No | No | Yes | No |

Configure the call type in the Stream Dashboard before using it. Use `StreamCallType('livestream')` in all `makeCall` calls.

---

## Backstage mode

When a host joins a `livestream` call, the call starts in **backstage mode** by default. In backstage:

- The host can set up camera and mic
- Viewers who attempt to join receive a "call not yet live" response
- `call.state.value.backstage` is `true`

Call `await call.goLive()` to exit backstage and open the call to viewers. Call `await call.stopLive()` to return to backstage (or end the session entirely).

```dart
// Read backstage state from call state
final isBackstage = call.state.value.backstage;
```

---

## Host flow

### 1. Create and join (enters backstage)

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType('livestream'),
  id: 'my-livestream-id',
);
await call.getOrCreate();
final result = await call.join();
result.fold(
  success: (_) { /* show backstage preview */ },
  failure: (error) { /* show error */ },
);
```

The host is placed in backstage. Observe `call.state` to track the connection lifecycle.

### 2. Go live

```dart
await call.goLive();
```

Transitions the call from backstage to live. Viewers can now join. `call.state.value.backstage` becomes `false`.

### 3. Stop the broadcast

```dart
await call.stopLive();
```

Returns the call to backstage. Active WebRTC viewers are disconnected. The host remains connected.

### 4. End the call for everyone

```dart
await call.end();
```

Terminates the session for all participants. Requires the host to have owner/admin permissions.

### 5. Leave

```dart
await call.leave();
```

Always call `leave()` after `end()` to clean up local call state. Skipping it leaves the SDK in an inconsistent state.

---

## Viewer flow (WebRTC)

WebRTC viewers join as subscribers. They receive the host's audio and video tracks in real time.

```dart
// Join
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType('livestream'),
  id: 'my-livestream-id',
);
await call.getOrCreate();
await call.join();

// Watch host via remoteParticipants
final hostParticipant = call.state.value.remoteParticipants.firstOrNull;

// Leave
await call.leave();
```

If the call is still in backstage when the viewer joins, `remoteParticipants` will be empty until the host calls `goLive()`. Observe `call.state.value.backstage` to show a "waiting for stream" UI.

```dart
StreamBuilder<CallState>(
  stream: call.state,
  initialData: call.state.value,
  builder: (context, snapshot) {
    final state = snapshot.requireData;
    if (state.backstage) {
      return const WaitingForHostWidget();
    }
    final host = state.remoteParticipants.firstOrNull;
    if (host == null) return const WaitingForHostWidget();
    return StreamVideoRenderer(call: call, participant: host, videoFit: VideoFit.cover);
  },
)
```

---

## Viewer flow (HLS)

HLS is better for large audiences (thousands of viewers). It introduces higher latency (~10–30 s) but scales without per-viewer WebRTC connections. HLS viewers do **not** join the call via `join()`.

### Get the HLS URL

The HLS URL is at `call.state.value.egress?.hls?.playlistUrl`. It is populated after the host calls `goLive()` and the HLS broadcast initializes (a few seconds after `goLive()`).

```dart
// Poll until the HLS URL becomes available
StreamBuilder<CallState>(
  stream: call.state,
  initialData: call.state.value,
  builder: (context, snapshot) {
    final state = snapshot.requireData;
    final hlsUrl = state.egress?.hls?.playlistUrl;
    if (hlsUrl == null) {
      return const Center(child: CircularProgressIndicator());
    }
    return HLSPlayerWidget(hlsUrl: hlsUrl);
  },
)
```

### Flutter HLS playback

Use the `video_player` package to play HLS streams:

```yaml
# pubspec.yaml
dependencies:
  video_player: ^2.9.1
```

```dart
import 'package:video_player/video_player.dart';

class HLSPlayerWidget extends StatefulWidget {
  const HLSPlayerWidget({super.key, required this.hlsUrl});
  final String hlsUrl;

  @override
  State<HLSPlayerWidget> createState() => _HLSPlayerWidgetState();
}

class _HLSPlayerWidgetState extends State<HLSPlayerWidget> {
  late final VideoPlayerController _controller;

  @override
  void initState() {
    super.initState();
    _controller = VideoPlayerController.networkUrl(Uri.parse(widget.hlsUrl))
      ..initialize().then((_) {
        setState(() {});
        _controller.play();
        _controller.setLooping(true);
      });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_controller.value.isInitialized) {
      return const Center(child: CircularProgressIndicator());
    }
    return AspectRatio(
      aspectRatio: _controller.value.aspectRatio,
      child: VideoPlayer(_controller),
    );
  }
}
```

**Caution:** Create `VideoPlayerController` in `initState`, not in `build`. Creating it inside `build` reinitializes the player on every rebuild.

---

## Large-scale livestreams (v1.3.1+)

For high-viewer-count broadcasts, pass `hintHighScaleLivestreamPublisher: true` when creating the call. This hints the SFU to optimize for one-to-many distribution:

```dart
await call.getOrCreate(
  video: CallSettingsRequest(
    hintHighScaleLivestreamPublisher: true,
  ),
);
```

---

## Participant and viewer count

For WebRTC-connected viewers, read participant count from call state:

```dart
// Total connected participants (includes host)
final totalCount = call.state.value.callParticipants.length;

// Viewers only (excludes local participant)
final viewerCount = call.state.value.remoteParticipants.length;
```

This count reflects only WebRTC-connected users. HLS viewers are not included. For accurate total viewer counts across both paths, use your own backend counter or the Stream server-side event stream.

---

## Call settings for hosts and viewers

Set camera and mic state before joining by disabling them after `join()`:

```dart
// Host: camera and mic on (enabled by default)
await call.join();

// Viewer: disable camera and mic immediately after joining
await call.join();
await call.camera.disable();
await call.microphone.disable();
```

The `livestream` call type also enforces no-publish for viewers via server-side permissions, so even with default settings, viewers cannot broadcast audio or video.

---

## Platform requirements

Same as standard video calls - see [`VIDEO-FLUTTER.md`](VIDEO-FLUTTER.md) for the full list. Both camera and microphone `Info.plist` keys and Android manifest permissions are required even for viewer-only builds because `stream_video_flutter` links the media stack regardless of role.

---

## Gotchas

- **Never use `StreamCallContainer` in a livestream flow.** `StreamCallContainer` is designed for standard calls - it renders a participant grid and default controls that override the custom host/viewer UI. Livestream views own their entire UI.
- **Always observe `call.state.value.backstage` for live status.** Do not maintain a separate `isLive` boolean - derive it from `backstage`.
- **Guard `join()` against double-calls.** Use a `_joined` flag or check that the call is not already in an active state before calling `join()`. Navigating back and re-entering a view can trigger a second `join()` while the previous session is still tearing down.
- **Never skip `getOrCreate()` before `join()`.** Calling `join()` on a call that does not exist server-side returns a failure.
- **`call.end()` followed by `call.leave()`.** `end()` terminates the session server-side but does not reset local call state. Always follow it with `leave()`.
- **`call.state.value.backstage` is `true` until `goLive()` is called.** A viewer who joins before `goLive()` will not see video until backstage ends. Show a "waiting for host" state and observe the state stream.
- **Never publish from a viewer.** The `livestream` call type blocks viewer publishing via server-side permissions. Do not show camera/mic enable controls in the viewer UI.
- **HLS latency is expected.** HLS viewers see the stream 10–30 seconds behind live. Do not attempt to synchronize WebRTC and HLS viewers.
- **`VideoPlayerController` must be created in `initState`, not `build`.** Creating it in `build` reinitializes the player on every rebuild.
- **HLS URL appears a few seconds after `goLive()`.** The HLS broadcast initialization is asynchronous. Poll `call.state.value.egress?.hls?.playlistUrl` until it is non-null before starting playback.
