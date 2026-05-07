# Video - SwiftUI SDK Setup & Integration

Stream Video SwiftUI provides pre-built SwiftUI components for building video and audio calling experiences. This file covers package installation, client setup, authentication, call flows, customization, and gotchas. For view blueprints, see [VIDEO-SWIFTUI-blueprints.md](VIDEO-SWIFTUI-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production).

- **Blueprint** - SwiftUI view structure and initialization
- **Wiring** - SDK calls for each component, exact property paths
- **Requirements** - Info.plist keys, SDK version, Xcode version

## Quick ref

- **Package (SwiftUI):** `StreamVideoSwiftUI` via SPM - `https://github.com/getstream/stream-video-swift`
- **Package (core only):** `StreamVideo` via SPM - same repo
- **First:** Installation -> Info.plist -> Client init -> CallViewModel -> Make/join call
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/video/docs/ios/`

Full view blueprints: [VIDEO-SWIFTUI-blueprints.md](VIDEO-SWIFTUI-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation (Swift Package Manager)

Check if the SDK is already installed in the project. If not, ask the user to follow the [installation guide](https://getstream.io/video/docs/ios/basics/installation/).

Add **both** packages from `https://github.com/getstream/stream-video-swift` to the app target:
- `StreamVideo` - core (required for non-UI work)
- `StreamVideoSwiftUI` - SwiftUI component layer (already depends on `StreamVideo`)

### Client Initialization

Initialize `StreamVideo` **once** at app launch. **Never** create it in a SwiftUI `View` body or computed property - doing so creates a new instance on every redraw.

Wrap it with `StreamVideoUI` before any SDK view renders. Two patterns - pick one:

> **Combining Chat + Video?** `ViewFactory`, `@Injected`, `InjectionKey`, and `InjectedValues` collide between `StreamVideoSwiftUI` and `StreamChatSwiftUI`. Never import both in the same file. See [`COMBINED-CHAT-VIDEO.md`](COMBINED-CHAT-VIDEO.md) for the full collision table and file isolation blueprints. The `VideoService.swift` blueprint is in `VIDEO-SWIFTUI-blueprints.md`.

**Option A - App struct `init()` (pure SwiftUI, no UIKit dependency):**

```swift
import StreamVideo
import StreamVideoSwiftUI

@main
struct MyApp: App {
    @State private var streamVideo: StreamVideo
    @State private var streamVideoUI: StreamVideoUI

    init() {
        let user = User(
            id: "user-id",
            name: "User Name",
            imageURL: nil,
            customData: [:]
        )
        let token = UserToken(rawValue: "your_static_token")
        let client = StreamVideo(apiKey: "your_api_key", user: user, token: token)
        _streamVideo = State(wrappedValue: client)
        _streamVideoUI = State(wrappedValue: StreamVideoUI(streamVideo: client))
    }

    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}
```

`@State` is required - `App` is a value type and SwiftUI can recreate it; `@State` ensures both instances survive those re-creations.

**Option B - `AppDelegate` (required for CallKit, push notifications, background tasks):**

```swift
import StreamVideo
import StreamVideoSwiftUI

@main
struct MyApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

class AppDelegate: NSObject, UIApplicationDelegate {
    var streamVideo: StreamVideo?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let user = User(id: "user-id", name: "User Name", imageURL: nil, customData: [:])
        let token = UserToken(rawValue: "your_static_token")
        let client = StreamVideo(apiKey: "your_api_key", user: user, token: token)
        streamVideo = client
        _ = StreamVideoUI(streamVideo: client)
        return true
    }
}
```

`StreamVideoUI` **must** be initialized before any SDK view renders. Rendering a call view without it causes a crash.

---

## User Authentication

The API key and secret are shared between Stream Chat and Video - one project, one key.

### Static token (no expiry)

```swift
let user = User(
    id: "alice",
    name: "Alice Smith",
    imageURL: URL(string: "https://example.com/alice.jpg"),
    customData: [:]
)
let token = UserToken(rawValue: "your_static_token")
let streamVideo = StreamVideo(apiKey: "your_api_key", user: user, token: token)
```

Token generation: `stream token <user_id>` (same CLI as Chat).

### Token provider (expiring tokens)

Pass a `tokenProvider` closure - called automatically when the token expires:

```swift
let streamVideo = StreamVideo(
    apiKey: "your_api_key",
    user: user,
    token: initialToken,
    tokenProvider: { result in
        yourAuthService.fetchVideoToken(for: user.id) { fetchResult in
            switch fetchResult {
            case .success(let tokenString):
                result(.success(UserToken(rawValue: tokenString)))
            case .failure(let error):
                result(.failure(error))
            }
        }
    }
)
```

---

## Import rules

`StreamVideoSwiftUI` re-exports most of the core `StreamVideo` types used in views. However, certain low-level types are only available from `StreamVideo` itself and require an explicit import:

| Type | Required import |
|---|---|
| `StreamVideo` (client) | `StreamVideo` |
| `User`, `UserToken` | `StreamVideo` |
| `Call` | `StreamVideo` |
| `CallParticipant` | `StreamVideo` |
| `RTCVideoTrack` | `StreamVideo` |
| `Member` | `StreamVideo` |
| `LogConfig` | `StreamVideo` |
| `CallViewModel`, `CallModifier`, `CallContainer` | `StreamVideoSwiftUI` |
| `VideoCallParticipantView` | `StreamVideoSwiftUI` |
| `DefaultViewFactory`, `ViewFactory` | `StreamVideoSwiftUI` |

**Rule:** any file that declares a `User`, `UserToken`, `CallParticipant`, `Member`, `Call`, or `RTCVideoTrack` variable must `import StreamVideo`. Omitting it causes a "cannot find type" build error even when `StreamVideoSwiftUI` is already imported.

---

## CallViewModel

`CallViewModel` is the central state manager for call UI. Create **one instance** at the root of the call flow, owned via `@StateObject`. Pass it down the view hierarchy as `@ObservedObject`. Never create a second instance for the same call session - doing so loses all state.

```swift
// Root view - owns the single instance
@StateObject var callViewModel = CallViewModel()

// Child views - observe the same instance, never create a new one
@ObservedObject var callViewModel: CallViewModel
```

**Never access call state through `CallState.shared` or any other singleton.** Always read state from the `callViewModel` you own or were passed:

```swift
// Correct
callViewModel.call?.state.participants
callViewModel.call?.state.localParticipant

// Wrong - bypasses the owned CallViewModel, state goes stale
CallState.shared.participants
```

### `callingState` tracks the current call phase

| State | When |
|---|---|
| `.idle` | No active or pending call |
| `.outgoing` | Outgoing ringing call, waiting for others to join |
| `.incoming(IncomingCall)` | Remote user is calling this device |
| `.joining` | Connecting to the call |
| `.inCall` | Active call session |
| `.reconnecting` | Reconnecting after network drop |
| `.disconnecting` | Leaving the call |

### Error state

`CallViewModel` publishes errors via `callViewModel.error: Error?`. Observe it in any view that triggers call actions and surface it with `.alert`. Clear the error by setting `callViewModel.error = nil`.

```swift
.alert(
    "Call Error",
    isPresented: Binding(
        get: { callViewModel.error != nil },
        set: { if !$0 { callViewModel.error = nil } }
    )
) {
    Button("OK") { callViewModel.error = nil }
} message: {
    Text(callViewModel.error?.localizedDescription ?? "Unknown error")
}
```

Apply this pattern on every view that calls `joinCall`, `startCall`, `acceptCall`, `rejectCall`, or `hangUp`. A single alert applied to the `CallModifier`-wrapped root view is sufficient if child views do not need their own messaging.

---

## Making and Joining Calls

### Join an existing call (no ringing)

```swift
callViewModel.joinCall(callType: "default", callId: "my-call-id")
```

Joins the call if it exists, or creates and joins it if it does not.

### Start an outgoing ringing call

```swift
let members: [Member] = [
    .init(userId: "alice"),
    .init(userId: "bob")
]
callViewModel.startCall(
    callType: "default",
    callId: UUID().uuidString,
    members: members,
    ring: true
)
```

Setting `ring: true` sends push notifications to all members. Requires the app to be set up with APNs and Stream's push integration.

### Accept or reject an incoming ringing call

```swift
// Accept
callViewModel.acceptCall(callType: callInfo.callType, callId: callInfo.callId)

// Reject
callViewModel.rejectCall(callType: callInfo.callType, callId: callInfo.callId)
```

### Leave a call

```swift
callViewModel.hangUp()
```

### End a call for all participants

```swift
try await callViewModel.call?.end()
```

Requires the caller to have host/owner permissions on the call.

---

## Call Controls

Toggle camera, microphone, and speaker during an active call:

```swift
// Camera on/off
callViewModel.toggleCameraEnabled()

// Microphone on/off
callViewModel.toggleMicrophoneEnabled()

// Flip front/back camera
try await callViewModel.call?.camera.flip()

// Speaker phone vs. earpiece
callViewModel.toggleSpeaker()
```

**Read current state** from `callViewModel.callSettings`:

```swift
callViewModel.callSettings.videoOn      // camera enabled
callViewModel.callSettings.audioOn      // microphone active
callViewModel.callSettings.speakerOn    // speaker phone on
```

---

## Call State and Participants

```swift
let call = callViewModel.call

call?.state.participants         // [CallParticipant] - local + remote
call?.state.localParticipant     // CallParticipant?
call?.state.remoteParticipants   // [CallParticipant]
call?.state.dominantSpeaker      // CallParticipant? - loudest active audio
```

**`CallParticipant` key properties:**

| Property | Type | Description |
|---|---|---|
| `id` | `String` | Participant user ID |
| `name` | `String` | Display name |
| `profileImageURL` | `URL?` | Avatar URL |
| `hasVideo` | `Bool` | Camera enabled |
| `hasAudio` | `Bool` | Microphone active |
| `isSpeaking` | `Bool` | Currently speaking |
| `isDominantSpeaker` | `Bool` | Loudest active speaker |
| `track` | `RTCVideoTrack?` | Renderable video track |
| `trackSize` | `CGSize` | Current rendered track size |

---

## Info.plist Requirements

Add both keys before any call attempt - missing them causes a silent crash on first camera or mic access:

```xml
<key>NSCameraUsageDescription</key>
<string>Video calls require camera access.</string>
<key>NSMicrophoneUsageDescription</key>
<string>Video calls require microphone access.</string>
```

Audio-only calls (`audio_room`) still require `NSMicrophoneUsageDescription`.

---

## Customization (ViewFactory)

`ViewFactory` defines swappable UI slots for the call screen. Create a singleton subclass, override only the slots you need, and pass it to `CallContainer`.

```swift
class CustomVideoViewFactory: ViewFactory {
    static let shared = CustomVideoViewFactory()
    private init() {}

    // Override slots below - all unoverridden slots use SDK defaults
}
```

Pass to `CallContainer`:

```swift
CallContainer(viewFactory: CustomVideoViewFactory.shared, viewModel: callViewModel)
```

> **Never guess `ViewFactory` method signatures.** Verify against the [customization docs](https://getstream.io/video/docs/ios/ui-components/overview/) before overriding a slot.

---

## Call Types

| Type | Use case |
|---|---|
| `default` | Standard peer-to-peer and small-group video calls |
| `audio_room` | Audio-only group rooms |
| `livestream` | One-to-many broadcasting |

Use `default` for most calling scenarios. `audio_room` and `livestream` have different permission and layout models.

**Livestream:** For one-to-many broadcasts with a creator/viewer split, backstage mode, `goLive()`/`stopLive()`, and HLS viewer support, load the dedicated references instead of this file:
- SDK patterns, backstage, goLive/stopLive, HLS -> [`LIVESTREAM-SWIFTUI.md`](LIVESTREAM-SWIFTUI.md)
- Mode selection, creator view, viewer view blueprints -> [`LIVESTREAM-SWIFTUI-blueprints.md`](LIVESTREAM-SWIFTUI-blueprints.md)

---

## Troubleshooting

Source: [getstream.io/video/docs/ios/advanced/troubleshooting-calls/](https://getstream.io/video/docs/ios/advanced/troubleshooting-calls/)

### Connection Issues

A failed WebSocket connection prevents calls from being established.

**Expired token** - tokens have an expiry date. Verify at [jwt.io](https://jwt.io). When using expiring tokens always supply a `tokenProvider` so the SDK can refresh automatically without a manual reconnect.

**Wrong secret for token generation** - each Stream app has its own secret. Tokens from the docs examples are signed with demo app secrets; yours will be rejected. Generate tokens from your own dashboard secret or via `stream token <user_id>`.

**User-token mismatch** - the token must be signed for the same user ID passed to `StreamVideo(user:)`. Mismatched IDs produce an auth error even if both values look valid. Verify at [jwt.io](https://jwt.io).

**Third-party network debuggers** - tools such as Wormholy can intercept and block WebSocket traffic. Exclude Stream's hosts from any network debugger you have installed.

### Ringing Call Issues

A ringing failure means the callee's incoming call screen never appears. Two scenarios:

- **App in foreground:** the SDK shows an in-app screen via the active WebSocket. Fix connection issues first.
- **App in background or killed:** requires CallKit + APNs VoIP push. Without it, no incoming call screen appears.

**Calling yourself** - caller and callee must be different users. A user cannot receive a ringing notification for their own call.

**Unknown member** - the callee must have connected to Stream at least once so the platform knows their device token. Ensure all ring targets have signed in before testing.

**Reused call ID** - ringing fires only once per call ID. Always use a fresh `UUID().uuidString` for every ringing call. Reusing an ID silently skips the ring.

**CallKit checklist:**
- VoIP certificate bundle ID matches the dashboard setting
- App bundle ID is correct
- Push providers are created and their names match what is passed to the SDK
- Device is registered - confirm it appears in the `me` response of the `connection.ok` event
- Check "Webhook & Push Logs" in the dashboard for push failures
- If VoIP notifications stop arriving entirely, reinstall the app - iOS stops delivering them if the app fails to report a VoIP push to CallKit

### Logging

Enable debug logging **before** the `StreamVideo` instance is created:

```swift
LogConfig.level = .debug
```

Levels: `.debug`, `.info`, `.warning`, `.error`. Setting the level after init has no effect on already-established connections.

---

## Gotchas

- **`StreamVideoUI` must be initialized before any SDK view renders.** Accessing call views before setup causes a crash.
- **Never store `StreamVideo` or `StreamVideoUI` as computed properties or in a view body.** They are recreated on every redraw.
- **`CallViewModel` must be `@StateObject` at the ownership site, `@ObservedObject` in child views.** Never create a second `CallViewModel` for the same call - pass the owned instance down.
- **Never use `CallState.shared`.** Always access call state through `callViewModel.call?.state`. Singleton access bypasses the published state and leaves the UI stale.
- **Always `import StreamVideo` in files that use low-level types** (`User`, `UserToken`, `Call`, `CallParticipant`, `RTCVideoTrack`, `Member`, `LogConfig`). `StreamVideoSwiftUI` alone is not sufficient for these types - omitting the import causes a "cannot find type" build error.
- **Always handle `callViewModel.error`.** Use a `.alert` bound to `callViewModel.error` in every view that triggers call actions. Unhandled errors leave the user with no feedback and the UI stuck in a non-idle state.
- **`callViewModel.hangUp()` is the correct leave path.** Calling `call.leave()` directly bypasses `CallViewModel` state cleanup and leaves the UI stale.
- **Always add `NSCameraUsageDescription` and `NSMicrophoneUsageDescription` to Info.plist.** Without them the permission dialog never appears and the call fails silently.
- **The API key is shared between Chat and Video.** One Stream project, one API key and one secret - token generation is identical for both products.
- **Never use dev tokens in production.** `devToken()` disables token auth and allows any client to impersonate any user.
