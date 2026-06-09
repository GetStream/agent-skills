# Livestream - Flutter SDK Setup & Integration

Stream Video's `livestream` call type is built for one-to-many broadcasting. One host publishes audio and video; viewers receive it as WebRTC subscribers or via HLS. This file covers the call type, host/viewer flows, backstage mode, and gotchas. For full widget blueprints, see [LIVESTREAM-FLUTTER-blueprints.md](LIVESTREAM-FLUTTER-blueprints.md).

Rules: [../RULES.md](../RULES.md).

---

## Quick ref

- **Call type:** `StreamCallType.liveStream()`
- **Package:** same `stream_video_flutter` as standard calls
- **Host path:** `getOrCreate()` -> `join()` -> backstage preview -> `call.goLive()` -> `call.stopLive()` -> `call.end()` -> `call.leave()`
- **Viewer path (WebRTC):** `getOrCreate()` -> show the pre-built `LivestreamPlayer` (auto-joins, handles backstage/ended states)
- **Viewer path (HLS):** get `call.state.value.egress.hlsPlaylistUrl` -> play with `video_player`
- **Docs:** [Livestreaming guide](https://getstream.io/video/docs/flutter/guides/livestreaming/) · [Watching a livestream](https://getstream.io/video/docs/flutter/ui-cookbook/livestreaming/watching-a-livestream/) · [Broadcasting (HLS/RTMP)](https://getstream.io/video/docs/flutter/advanced/broadcasting/)
- **Beyond this file:** TikTok-style vertical livestream feeds (docs: [Livestream feed](https://getstream.io/video/docs/flutter/ui-cookbook/livestreaming/livestream-feed/)) and "viewer calls the host mid-broadcast" live in [`VIDEO-ADVANCED-FLUTTER.md`](VIDEO-ADVANCED-FLUTTER.md) + [`VIDEO-ADVANCED-FLUTTER-blueprints.md`](VIDEO-ADVANCED-FLUTTER-blueprints.md)

---

## Call type: `livestream`

> **Docs:** [Livestreaming guide](https://getstream.io/video/docs/flutter/guides/livestreaming/) · [Call types](https://getstream.io/video/docs/flutter/guides/call-types/)

The `livestream` call type ships with a permission model designed for broadcasting:

| Role                | Publish audio | Publish video | Receive | End call |
| ------------------- | ------------- | ------------- | ------- | -------- |
| Host / admin        | Yes           | Yes           | Yes     | Yes      |
| Viewer (subscriber) | No            | No            | Yes     | No       |

Configure the call type in the Stream Dashboard before using it. Use `StreamCallType.liveStream()` in all `makeCall` calls (factory constructor - `StreamCallType('livestream')` does not exist).

---

## Backstage mode

When a host joins a `livestream` call, the call starts in **backstage mode** by default. In backstage:

- The host can set up camera and mic
- Viewers who attempt to join receive a "call not yet live" response
- `call.state.value.isBackstage` is `true`

Call `await call.goLive()` to exit backstage and open the call to viewers. Call `await call.stopLive()` to return to backstage (or end the session entirely).

```dart
// Read backstage state from call state (the field is isBackstage, not backstage)
final isBackstage = call.state.value.isBackstage;
```

> **Docs:** [Livestreaming guide](https://getstream.io/video/docs/flutter/guides/livestreaming/)

---

## Roles, permissions, and backstage security

For the general permissions model (roles, capabilities, grants, `hasPermission`,
`grant/revokePermissions`) see [`VIDEO-FLUTTER.md`](VIDEO-FLUTTER.md) > Roles and
Permissions. This section covers the **livestream-specific gating** that most commonly
causes bugs.

> **Docs:** [Permissions & moderation](https://getstream.io/video/docs/flutter/guides/permissions-and-moderation/) · [Livestreaming guide](https://getstream.io/video/docs/flutter/guides/livestreaming/)

### Who can join backstage

While a livestream is in backstage (before `goLive()`), the server only admits users whose
effective capabilities include `join-backstage` (`CallPermission.joinBackstage`). By
default the `livestream` call type grants this to the **host** role only - regular
viewers' `join()` **fails** with a "call is not live" error until the host goes live.

```dart
// Mark the creator as host so they get join-backstage (set at create time):
await call.getOrCreate(
  members: [
    MemberRequest(userId: StreamVideo.instance.currentUser.id, role: 'host'),
  ],
);
```

The host's role and the `join-backstage` grant are configured **server-side** (Dashboard /
call type grants). The Flutter SDK does not assign roles - it only sends the desired role
on the member and reads back `call.state.value.ownCapabilities`.

### Backstage gotcha: `joinAheadTimeSeconds` lets viewers in early

`StreamBackstageSettings` has a `joinAheadTimeSeconds` field. When the call has a scheduled
start (`startsAt`) and `joinAheadTimeSeconds > 0`, **regular viewers can join the backstage
call that many seconds before `startsAt` - even without `join-backstage`**. From that
moment they receive the host's published audio and video.

```dart
await call.update(
  startsAt: DateTime.now().toUtc().add(const Duration(minutes: 5)),
  backstage: const StreamBackstageSettings(
    enabled: true,
    joinAheadTimeSeconds: 120, // viewers may join 2 min before startsAt
  ),
);
```

> **SECURITY GOTCHA - hosts can be heard/seen during "private" setup.** Backstage feels
> like a private green room, but `joinAheadTimeSeconds` is a hole in that assumption: any
> viewer who joins inside the join-ahead window hears and sees the host live, before
> `goLive()` is ever called. Mitigations:
> - Keep `joinAheadTimeSeconds` at `0` (the default) unless you specifically want a
>   pre-show lobby. If unset, viewers can only join once the call starts/goes live.
> - Treat the period between (`startsAt - joinAheadTimeSeconds`) and `goLive()` as
>   **public**. Do not say or show anything in front of the camera/mic that viewers should
>   not receive - or keep the host muted / camera off until `goLive()`.
> - If you grant `join-backstage` to a custom role, remember those users bypass the live
>   gate entirely (always, not just in the join-ahead window).

### Verify before treating backstage as private

```dart
// Are non-hosts currently able to be here? If startsAt is near and join-ahead is on,
// assume YES regardless of isBackstage.
final s = call.state.value;
final scheduledStart = s.startsAt;            // DateTime?
final joinAhead = s.settings.backstage.joinAheadTimeSeconds ?? 0;
// Anyone may already be receiving you if:
//   !s.isBackstage  (live)  OR
//   (scheduledStart != null && joinAhead > 0 &&
//      DateTime.now().toUtc().isAfter(scheduledStart.subtract(Duration(seconds: joinAhead))))
```

---

## Host flow

> **Docs:** [Livestreaming guide](https://getstream.io/video/docs/flutter/guides/livestreaming/) · [Hosting a livestream](https://getstream.io/video/docs/flutter/ui-cookbook/livestreaming/hosting-a-livestream/)

### 1. Create and join (enters backstage)

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.liveStream(),
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

// Optionally kick off server-side pipelines in the same step:
await call.goLive(startHls: true, startRecording: true);
```

Transitions the call from backstage to live. Viewers can now join. `call.state.value.isBackstage` becomes `false`. `goLive` returns `Result<CallMetadata>`.

### 3. Stop the broadcast

```dart
await call.stopLive();
```

Returns the call to backstage (`isBackstage` becomes `true` again); published tracks stop reaching viewers. The host remains connected.

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

> **Docs:** [Watching a livestream](https://getstream.io/video/docs/flutter/ui-cookbook/livestreaming/watching-a-livestream/) · [Livestreaming guide](https://getstream.io/video/docs/flutter/guides/livestreaming/)

**Use the pre-built `LivestreamPlayer`.** It auto-joins the call, renders the host video, and handles the backstage ("waiting for host"), ended, reconnecting, and no-video states - plus participant count, multi-host layouts, screen-share spotlight, recordings-when-ended, and PiP. Do not hand-build a viewer unless the design demands it.

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.liveStream(),
  id: 'my-livestream-id',
);
await call.getOrCreate();

// In the widget tree - no manual join() needed:
LivestreamPlayer(
  call: call,
  // joinBehaviour: LivestreamJoinBehaviour.autoJoinAsap (default)
  //   .autoJoinWhenLive - wait in a preview until the host goes live
  //   .manualJoin - you call join() yourself
  // connectOptions defaults to camera/mic disabled - correct for viewers
)
```

Useful `LivestreamPlayer` parameters: `showParticipantCount`, `showRecordingsWhenEnded`, `backButtonBuilder`, `livestreamBackstageWidgetBuilder` / `livestreamEndedWidgetBuilder` (custom waiting/ended screens), `showMultipleHosts` + `layoutMode`, `videoFit`, `pictureInPictureConfiguration`, `onCallDisconnected`.

### Fully custom viewer (only when LivestreamPlayer does not fit)

Viewers join as subscribers and render the host manually:

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.liveStream(),
  id: 'my-livestream-id',
);
await call.getOrCreate();
await call.join(); // CallConnectOptions defaults camera/mic to disabled

// Watch the host - otherParticipants excludes the local viewer
final hostParticipant = call.state.value.otherParticipants.firstOrNull;

// Leave
await call.leave();
```

If the call is still in backstage when the viewer joins, `otherParticipants` will be empty until the host calls `goLive()`. Observe `call.state.value.isBackstage` to show a "waiting for stream" UI.

```dart
StreamBuilder<CallState>(
  stream: call.state.asStream(), // StateEmitter is not a Stream - convert
  initialData: call.state.value,
  builder: (context, snapshot) {
    final state = snapshot.requireData;
    if (state.isBackstage) {
      return const WaitingForHostWidget();
    }
    final host = state.otherParticipants.firstOrNull;
    if (host == null) return const WaitingForHostWidget();
    return StreamVideoRenderer(
      call: call,
      participant: host,
      videoTrackType: SfuTrackType.video, // required
      videoFit: VideoFit.cover,
    );
  },
)
```

---

## Viewer flow (HLS)

> **Docs:** [Broadcasting (HLS/RTMP)](https://getstream.io/video/docs/flutter/advanced/broadcasting/) · [Watching a livestream](https://getstream.io/video/docs/flutter/ui-cookbook/livestreaming/watching-a-livestream/)

HLS is better for large audiences (thousands of viewers). It introduces higher latency (~10-30 s) but scales without per-viewer WebRTC connections. HLS viewers do **not** join the call via `join()`.

### Start HLS and get the URL

HLS only runs if it is started - via `call.goLive(startHls: true)`, an explicit `call.startHLS()`, or auto-broadcast enabled on the call type in the dashboard. Stop with `call.stopHLS()`.

The URL is at `call.state.value.egress.hlsPlaylistUrl` (`egress` is non-nullable; the field is flat). It populates a few seconds after the broadcast starts.

```dart
// Observe state until the HLS URL becomes available
StreamBuilder<CallState>(
  stream: call.state.asStream(),
  initialData: call.state.value,
  builder: (context, snapshot) {
    final state = snapshot.requireData;
    final hlsUrl = state.egress.hlsPlaylistUrl;
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

## Large-scale livestreams (v1.3.3+)

For high-viewer-count broadcasts, the **host** passes `hintHighScaleLivestreamPublisher: true` to `join()`. This hints the SFU to optimize for one-to-many distribution:

```dart
await call.join(hintHighScaleLivestreamPublisher: true);
```

---

## Participant and viewer count

> **Docs:** [Call state](https://getstream.io/video/docs/flutter/guides/call-state/)

For WebRTC-connected viewers, read participant count from call state:

```dart
// Total connected participants (includes host)
final totalCount = call.state.value.callParticipants.length;

// Viewers only (excludes local participant)
final viewerCount = call.state.value.otherParticipants.length;
```

This count reflects only WebRTC-connected users. HLS viewers are not included. For accurate total viewer counts across both paths, use your own backend counter or the Stream server-side event stream.

---

## Call settings for hosts and viewers

Set the initial camera/mic state via `CallConnectOptions` passed to `join()` - do not "join then disable":

```dart
// Host: publish camera and mic from the start
await call.join(
  connectOptions: CallConnectOptions(
    camera: TrackOption.enabled(),
    microphone: TrackOption.enabled(),
  ),
);

// Viewer: CallConnectOptions defaults camera and microphone to disabled,
// so a bare join() is already correct for viewers
await call.join();
```

To toggle later: `call.setCameraEnabled(enabled:)` / `call.setMicrophoneEnabled(enabled:)`.

The `livestream` call type also enforces no-publish for viewers via server-side permissions, so even with default settings, viewers cannot broadcast audio or video.

---

## Platform requirements

Same as standard video calls - see [`VIDEO-FLUTTER.md`](VIDEO-FLUTTER.md) for the full list. Both camera and microphone `Info.plist` keys and Android manifest permissions are required even for viewer-only builds because `stream_video_flutter` links the media stack regardless of role.

---

## Gotchas

- **Use `LivestreamPlayer` for viewers.** It handles join, backstage/ended states, host filtering, and PiP. Hand-roll the viewer UI only when the design demands it.
- **Never use `StreamCallContainer` in a livestream flow.** `StreamCallContainer` is designed for standard calls - it renders a participant grid and default controls that override the custom host/viewer UI. Use `LivestreamPlayer` (viewer) or a custom host view.
- **Always observe `call.state.value.isBackstage` for live status.** Do not maintain a separate `isLive` boolean - derive it from `isBackstage`. (The field is `isBackstage`; there is no `backstage` getter.)
- **Guard `join()` against double-calls.** Use a `_joined` flag or check that the call is not already in an active state before calling `join()`. Navigating back and re-entering a view can trigger a second `join()` while the previous session is still tearing down.
- **Never skip `getOrCreate()` before `join()`.** Calling `join()` on a call that does not exist server-side returns a failure.
- **`call.end()` followed by `call.leave()`.** `end()` terminates the session server-side but does not reset local call state. Always follow it with `leave()`.
- **`call.state.value.isBackstage` is `true` until `goLive()` is called.** A viewer who joins before `goLive()` will not see video until backstage ends. `LivestreamPlayer` shows its backstage state automatically; custom UIs must observe the state stream.
- **Never publish from a viewer.** The `livestream` call type blocks viewer publishing via server-side permissions. Do not show camera/mic enable controls in the viewer UI.
- **HLS must be started.** `goLive(startHls: true)`, `call.startHLS()`, or dashboard auto-broadcast - otherwise `egress.hlsPlaylistUrl` stays null forever.
- **HLS latency is expected.** HLS viewers see the stream 10-30 seconds behind live. Do not attempt to synchronize WebRTC and HLS viewers.
- **`VideoPlayerController` must be created in `initState`, not `build`.** Creating it in `build` reinitializes the player on every rebuild.
- **HLS URL appears a few seconds after the broadcast starts.** The initialization is asynchronous. Observe `call.state.value.egress.hlsPlaylistUrl` until it is non-null before starting playback.
