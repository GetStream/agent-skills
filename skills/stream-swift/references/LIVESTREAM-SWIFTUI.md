# Livestream - SwiftUI SDK Setup & Integration

Stream Video's `livestream` call type is built for one-to-many broadcasting. One host publishes audio and video; viewers receive it as WebRTC subscribers or via HLS. This file covers the call type, host/viewer flows, backstage mode, and gotchas. For full view blueprints, see [LIVESTREAM-SWIFTUI-blueprints.md](LIVESTREAM-SWIFTUI-blueprints.md).

Rules: [../RULES.md](../RULES.md).

---

## Quick ref

- **Call type:** `livestream`
- **Package:** same `StreamVideoSwiftUI` + `StreamVideo` as standard calls
- **Host path:** join -> preview in backstage -> `call.goLive()` -> `call.stopLive()` -> `call.end()` -> `callViewModel.hangUp()`
- **Viewer path (WebRTC):** `callViewModel.joinCall(callType: "livestream", callId:)` -> watch remote participants -> `callViewModel.hangUp()`
- **Viewer path (HLS):** get `call.state.egress?.hls?.playlistUrl` -> feed to `AVPlayer` or `VideoPlayer`
- **Docs:** `https://getstream.io/video/docs/ios/advanced/livestreaming/`

---

## Call type: `livestream`

The `livestream` call type ships with a permission model designed for broadcasting:

| Role | Publish audio | Publish video | Receive | End call |
|---|---|---|---|---|
| Host / admin | Yes | Yes | Yes | Yes |
| Viewer (subscriber) | No | No | Yes | No |

Configure the call type in the Stream Dashboard before using it. Use `callType: "livestream"` in all join/start calls.

---

## Backstage mode

When a host joins a `livestream` call, the call starts in **backstage mode** by default. In backstage:
- The host can set up camera and mic
- Viewers who attempt to join receive a "call not yet live" response
- `call.state.backstage` is `true`

Call `call.goLive()` to exit backstage and open the call to viewers. Call `call.stopLive()` to return to backstage (or end the session entirely).

```swift
// Read backstage state from the owned callViewModel
let isBackstage = callViewModel.call?.state.backstage ?? true
```

---

## Host flow

### 1. Join (enters backstage)

```swift
// joinCall has no callSettings parameter — pass settings via CallViewModel.init(callSettings:) at the root
callViewModel.joinCall(callType: "livestream", callId: callId)
```

The host is placed in backstage. Use `callViewModel.callingState` to track `.joining` -> `.inCall`.

### 2. Go live

```swift
try await callViewModel.call?.goLive()
```

Transitions the call from backstage to live. Viewers can now join. `call.state.backstage` becomes `false`.

### 3. Stop the broadcast

```swift
try await callViewModel.call?.stopLive()
```

Returns the call to backstage. Active viewers are disconnected. The host remains connected.

### 4. End the call for everyone

```swift
try await callViewModel.call?.end()
```

Terminates the session for all participants. Call `callViewModel.hangUp()` immediately after to clean up local state.

### 5. Leave

```swift
callViewModel.hangUp()
```

Always call `hangUp()` instead of `call.leave()` directly - `hangUp()` triggers `CallViewModel` state cleanup.

---

## Viewer flow (WebRTC)

WebRTC viewers join as subscribers. They receive the host's audio and video tracks in real time.

```swift
// Join
callViewModel.joinCall(callType: "livestream", callId: callId)

// Watch via remoteParticipants - the host appears here once live
callViewModel.call?.state.remoteParticipants

// Leave
callViewModel.hangUp()
```

If the call is still in backstage when the viewer joins, the `callingState` stays at `.joining` until the host calls `goLive()`. Poll or observe `call.state.backstage` to show a "waiting for stream" UI.

---

## Viewer flow (HLS)

HLS is better for large audiences (thousands of viewers). It introduces higher latency (~10–30 s) but scales without per-viewer WebRTC connections.

### Get the HLS URL

`call.state.egress` is `EgressResponse?`. The HLS URL sits at `egress?.hls?.playlistUrl`:

```swift
// After the host calls goLive() and HLS broadcasting starts
if let playlistUrl = callViewModel.call?.state.egress?.hls?.playlistUrl,
   let url = URL(string: playlistUrl) {
    let player = AVPlayer(url: url)
    player.play()
}
```

### SwiftUI playback

```swift
import SwiftUI
import AVKit

struct HLSPlayerView: View {
    let hlsURL: URL

    var body: some View {
        VideoPlayer(player: AVPlayer(url: hlsURL))
            .ignoresSafeArea()
    }
}
```

**Caution:** `AVPlayer(url:)` must not be created inside `body` - it is recreated on every redraw. Store it as `@State private var player = AVPlayer()` and configure it once in `.onAppear` or `.task`.

### Correct HLS player ownership

```swift
struct HLSPlayerView: View {
    let hlsURL: URL
    @State private var player = AVPlayer()

    var body: some View {
        VideoPlayer(player: player)
            .ignoresSafeArea()
            .onAppear {
                player.replaceCurrentItem(with: AVPlayerItem(url: hlsURL))
                player.play()
            }
    }
}
```

---

## Participant and viewer count

For WebRTC-connected viewers, read participant count from call state:

```swift
// Total connected participants (includes host)
let totalCount = callViewModel.call?.state.participants.count ?? 0

// Viewers only (excludes local participant)
let viewerCount = callViewModel.call?.state.remoteParticipants.count ?? 0
```

This count reflects only WebRTC-connected users. HLS viewers are not included. For accurate total viewer counts across both paths, use your own backend counter or the Stream server-side event stream.

---

## Call settings for hosts and viewers

`joinCall` has no `callSettings` parameter. Pass initial settings when constructing `CallViewModel`:

```swift
// Host: camera and mic on (default — CallViewModel() is equivalent)
@StateObject private var callViewModel = CallViewModel(callSettings: CallSettings(audioOn: true, videoOn: true))

// Viewer: camera and mic off
@StateObject private var callViewModel = CallViewModel(callSettings: CallSettings(audioOn: false, videoOn: false))
```

Because the root view owns a single `CallViewModel` instance, the mode (host vs viewer) must be known at the time `CallViewModel` is created, before `joinCall` is called. One pattern: create `CallViewModel` with the right settings after the user picks their mode on the mode selection screen.

The `livestream` call type also enforces no-publish for viewers via server-side permissions, so even with default settings, viewers cannot broadcast.

---

## Info.plist requirements

Same as standard video calls:

```xml
<key>NSCameraUsageDescription</key>
<string>The app uses the camera for livestreaming.</string>
<key>NSMicrophoneUsageDescription</key>
<string>The app uses the microphone for livestreaming.</string>
```

Viewers do not publish, but iOS still requires the keys for any app that links `StreamVideo`.

---

## Gotchas

- **Never use `CallModifier` in a livestream flow.** `CallModifier` wraps the content in `VideoViewOverlay`, which layers `CallContainer` on top of all child views whenever `callingState` is `.inCall`, `.joining`, or `.outgoing`. This completely replaces the custom creator/viewer UI with the SDK's default meeting screen (participant grid + controls). Livestream views own their call UI — `CallModifier` must not appear anywhere in the hierarchy above `CreatorLivestreamView` or `ViewerLivestreamView`.
- **Always observe `callingState` to detect unexpected disconnects.** After `hangUp()`, `callingState` resets to `.idle`. Views must observe this with `.onChange(of: callViewModel.callingState)` and call `onExit()` when `.idle` is reached — both for the explicit "end stream" path and for network drops or server kicks. Without this, the view stays on screen after a disconnect and cannot be dismissed.
- **Guard `joinCall` with `callingState == .idle`.** Call `joinCall` only when `callingState == .idle`. Without the guard, navigating back to a view and re-entering can trigger a second `joinCall` while a previous call session is still tearing down.
- **Never skip backstage on the host.** The host must join first via `callViewModel.joinCall` before calling `goLive()`. Calling `goLive()` on a `nil` call crashes.
- **`call.state.backstage` is the source of truth for live status.** Do not maintain a separate `isLive: Bool` property - observe `call.state.backstage` directly.
- **`callViewModel.hangUp()` after `call.end()`.** `call.end()` terminates the session server-side but does not reset local `CallViewModel` state. Always follow it with `hangUp()`.
- **HLS latency is expected.** HLS viewers see the stream 10–30 seconds behind live. Do not attempt to synchronize WebRTC and HLS viewers.
- **Viewer join before host goes live.** A viewer who joins before `goLive()` is called will not see video until backstage ends. Show a "waiting for host" state and observe `call.state.backstage` transitioning to `false`.
- **Never publish from a viewer.** The `livestream` call type blocks viewer publishing via server-side permissions. Do not show camera/mic controls in the viewer UI.
- **AVPlayer must be `@State`, not inline.** Creating `AVPlayer(url:)` inside a SwiftUI `body` or computed property recreates the player on every redraw and interrupts playback.
