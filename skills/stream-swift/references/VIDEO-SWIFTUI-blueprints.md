# Video SwiftUI - View Blueprints

Load only the section you are implementing. For setup, client initialization, and gotchas, see [VIDEO-SWIFTUI.md](VIDEO-SWIFTUI.md).

---

## App Entry Point Blueprint

No wrapper class is needed for Video-only apps. Initialize `StreamVideo` and `StreamVideoUI` directly in the app entry point.

### Option A - App struct `init()` (pure SwiftUI, default choice)

```swift
import SwiftUI
import StreamVideo
import StreamVideoSwiftUI

@main
struct VideoApp: App {
    @State private var streamVideo: StreamVideo
    @State private var streamVideoUI: StreamVideoUI

    init() {
        let user = User(
            id: "your-user-id",
            name: "Your Name",
            imageURL: nil,
            customData: [:]
        )
        let token = UserToken(rawValue: "your_token")
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

### Option B - `AppDelegate` (required for CallKit, push notifications, background tasks)

```swift
import SwiftUI
import StreamVideo
import StreamVideoSwiftUI

@main
struct VideoApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

class AppDelegate: NSObject, UIApplicationDelegate {
    var streamVideo: StreamVideo?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        let user = User(id: "your-user-id", name: "Your Name", imageURL: nil, customData: [:])
        let token = UserToken(rawValue: "your_token")
        let client = StreamVideo(apiKey: "your_api_key", user: user, token: token)
        streamVideo = client
        _ = StreamVideoUI(streamVideo: client)
        return true
    }
}
```

**Wiring (both options):**
- `@State` is required in Option A - `App` is a value type; `@State` pins both instances across SwiftUI re-creations
- `StreamVideoUI` must be alive before any call view renders - initialize before showing `RootView`
- Use `_streamVideo = State(wrappedValue:)` syntax to set `@State` properties from `init()`
- Do **not** introduce a `VideoCallBridge`, `CallManager`, `StreamService`, or any other wrapper - the SDK types are the ownership layer

---

## Combined Chat + Video: File Isolation Blueprint

Only needed when the app imports **both** `StreamChatSwiftUI` and `StreamVideoSwiftUI`. `ViewFactory`, `@Injected`, `InjectionKey`, and `InjectedValues` exist in both modules - importing both in the same file causes an "ambiguous use" compiler error. The fix is file isolation - one file per SDK. See [`COMBINED-CHAT-VIDEO.md`](COMBINED-CHAT-VIDEO.md) for the full guide including UIKit patterns.

```swift
// VideoService.swift - import isolation only, no logic
import StreamVideo
import StreamVideoSwiftUI

final class VideoService {
    static let shared = VideoService(
        apiKey: "your_api_key",
        userId: "alice",
        userName: "Alice",
        token: "your_token"
    )

    let streamVideo: StreamVideo
    private let streamVideoUI: StreamVideoUI  // must stay alive; not exposed

    init(apiKey: String, userId: String, userName: String, token: String) {
        let user = User(id: userId, name: userName, imageURL: nil, customData: [:])
        let videoToken = UserToken(rawValue: token)
        streamVideo = StreamVideo(apiKey: apiKey, user: user, token: videoToken)
        streamVideoUI = StreamVideoUI(streamVideo: streamVideo)
    }
}
```

```swift
// MyApp.swift - no Stream imports needed here
@main
struct MyApp: App {
    init() {
        _ = VideoService.shared   // triggers init, keeps instances alive
        _ = ChatService.shared
    }

    var body: some Scene {
        WindowGroup { RootView() }
    }
}
```

**Wiring:**
- `streamVideoUI` is `private` - callers never touch it; it just needs to stay alive
- `streamVideo` is `let` - set once at init, never mutated
- No `setUp()` method, no optional properties, no two-phase init
- The same JWT token and API key work for both Chat and Video

---

## Root / Call Gate Blueprint

The SDK ships a `CallModifier` that handles all call-state overlays - incoming, outgoing, joining, and active call - without manual state switching. Apply it once at the root of your content view.

```swift
import SwiftUI
import StreamVideoSwiftUI

struct RootView: View {
    @StateObject var callViewModel = CallViewModel()

    var body: some View {
        HomeView(callViewModel: callViewModel)
            .modifier(CallModifier(viewModel: callViewModel))
    }
}
```

To use a custom `ViewFactory`, pass it to the modifier:

```swift
// VideoViewFactory.swift - import StreamVideoSwiftUI only
import StreamVideoSwiftUI

class VideoViewFactory: ViewFactory {
    static let shared = VideoViewFactory()
    private init() {}
}
```

```swift
// RootView - import StreamVideoSwiftUI only
import StreamVideoSwiftUI

struct RootView: View {
    @StateObject var callViewModel = CallViewModel()

    var body: some View {
        HomeView(callViewModel: callViewModel)
            .modifier(CallModifier(viewFactory: VideoViewFactory.shared, viewModel: callViewModel))
    }
}
```

> **Combining Chat + Video?** `ViewFactory` is defined in both `StreamChatSwiftUI` and `StreamVideoSwiftUI`. Put `VideoViewFactory` in its own file (`VideoViewFactory.swift`) that imports only `StreamVideoSwiftUI`, and `ChatViewFactory` in its own file that imports only `StreamChatSwiftUI`. Same rule applies to `@Injected` and `InjectionKey` - they exist in both modules. See `sdk.md` -> "Combined Chat + Video apps".

**Wiring:**
- `CallModifier` is the recommended integration point - it manages all `callingState` transitions internally so you don't switch on them manually
- `CallViewModel` must be `@StateObject` - it owns call lifecycle for the entire session
- Verify the exact `CallModifier` initializer against the [SDK docs](https://getstream.io/video/docs/ios/) if the signature differs from above

---

## HomeView / Join-or-Start Call Blueprint

Lets the user enter a call ID to join an existing call, or create a new one. Errors from failed call attempts are surfaced in an alert.

```swift
import SwiftUI
import StreamVideoSwiftUI

struct HomeView: View {
    @ObservedObject var callViewModel: CallViewModel
    @State private var callId = ""

    var body: some View {
        VStack(spacing: 24) {
            Text("Video Call")
                .font(.largeTitle.bold())

            TextField("Call ID", text: $callId)
                .textFieldStyle(.roundedBorder)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)

            Button("Join Call") {
                guard !callId.isEmpty else { return }
                callViewModel.joinCall(callType: "default", callId: callId)
            }
            .buttonStyle(.borderedProminent)
            .disabled(callId.isEmpty)

            Button("New Call") {
                callViewModel.startCall(
                    callType: "default",
                    callId: UUID().uuidString,
                    members: []
                )
            }
            .buttonStyle(.bordered)
        }
        .padding()
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
    }
}
```

**Wiring:**
- `@ObservedObject` here - `HomeView` observes but does not own `callViewModel`
- `joinCall` joins an existing call or creates one if it does not exist
- `startCall` with `ring: false` (default) creates and joins immediately without ringing anyone
- The `.alert` clears `callViewModel.error` on dismiss so the same error does not reappear

---

## Full Call View Blueprint (CallContainer)

`CallContainer` is the complete in-call screen with participant grid, controls, and camera feed. Use it unless you are building a fully custom layout.

`ActiveCallView` receives the `CallViewModel` that was created at the root - it must **not** create a second instance. Creating a new `CallViewModel` here discards the call state that `joinCall`/`startCall` already established.

```swift
import SwiftUI
import StreamVideoSwiftUI

struct ActiveCallView: View {
    let callId: String
    @ObservedObject var callViewModel: CallViewModel

    var body: some View {
        CallContainer(
            viewFactory: DefaultViewFactory.shared,
            viewModel: callViewModel
        )
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
    }
}
```

**Wiring:**
- `@ObservedObject` - `ActiveCallView` observes the same instance that owns the call session
- `DefaultViewFactory.shared` provides all default UI slots; substitute a custom `ViewFactory` to replace individual slots
- Do not embed `CallContainer` inside a `ScrollView` or `NavigationStack` - it manages its own layout
- The `.alert` here catches errors that arise during the active call (e.g. network loss, permission denial)

---

## Custom Call Controls Blueprint

Replace the SDK's default controls bar with your own.

```swift
struct CustomCallControlsView: View {
    @ObservedObject var callViewModel: CallViewModel

    var body: some View {
        HStack(spacing: 24) {
            // Mic toggle
            Button {
                callViewModel.toggleMicrophoneEnabled()
            } label: {
                Image(systemName: callViewModel.callSettings.audioOn
                    ? "mic.fill" : "mic.slash.fill")
                    .font(.title2)
                    .foregroundStyle(callViewModel.callSettings.audioOn ? .primary : .red)
                    .frame(width: 56, height: 56)
                    .background(.ultraThinMaterial, in: Circle())
            }

            // Camera toggle
            Button {
                callViewModel.toggleCameraEnabled()
            } label: {
                Image(systemName: callViewModel.callSettings.videoOn
                    ? "video.fill" : "video.slash.fill")
                    .font(.title2)
                    .foregroundStyle(callViewModel.callSettings.videoOn ? .primary : .red)
                    .frame(width: 56, height: 56)
                    .background(.ultraThinMaterial, in: Circle())
            }

            // Flip camera
            Button {
                Task { try? await callViewModel.call?.camera.flip() }
            } label: {
                Image(systemName: "arrow.triangle.2.circlepath.camera.fill")
                    .font(.title2)
                    .frame(width: 56, height: 56)
                    .background(.ultraThinMaterial, in: Circle())
            }

            // Hang up
            Button {
                callViewModel.hangUp()
            } label: {
                Image(systemName: "phone.down.fill")
                    .font(.title2)
                    .foregroundStyle(.white)
                    .frame(width: 56, height: 56)
                    .background(Color.red, in: Circle())
            }
        }
        .padding(.horizontal)
    }
}
```

---

## Custom Participant Tile Blueprint

Renders a single participant's video track with name and audio status overlaid.

```swift
import SwiftUI
import StreamVideo        // CallParticipant, RTCVideoTrack
import StreamVideoSwiftUI // VideoCallParticipantView

struct ParticipantTileView: View {
    let participant: CallParticipant
    let availableFrame: CGRect
    let call: Call?

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            VideoCallParticipantView(
                participant: participant,
                availableFrame: availableFrame,
                contentMode: .scaleAspectFill,
                customData: [:],
                call: call
            )

            // Name + mute indicator
            HStack(spacing: 4) {
                Text(participant.name)
                    .font(.caption.bold())
                    .foregroundStyle(.white)
                if !participant.hasAudio {
                    Image(systemName: "mic.slash.fill")
                        .font(.caption)
                        .foregroundStyle(.white)
                }
            }
            .padding(6)
            .background(.black.opacity(0.5))
            .clipShape(RoundedRectangle(cornerRadius: 6))
            .padding(8)
        }
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .strokeBorder(participant.isSpeaking ? Color.green : .clear, lineWidth: 2)
        )
    }
}
```

**Wiring:**
- `VideoCallParticipantView` requires `contentMode`, `customData`, and `call` — all three must be provided
- `call` is `Call?` — pass `callViewModel.call` from the owning view
- `contentMode: .scaleAspectFill` fills the tile; use `.scaleAspectFit` to avoid cropping
- `availableFrame` sets the rendering resolution; read it from a `GeometryReader` on the tile's container

---

## Incoming Call View Blueprint

Custom incoming call screen with accept and reject buttons.

```swift
struct CustomIncomingCallView: View {
    let callInfo: IncomingCall
    @ObservedObject var callViewModel: CallViewModel

    var body: some View {
        VStack(spacing: 32) {
            AsyncImage(url: callInfo.caller.imageURL) { image in
                image.resizable().scaledToFill()
            } placeholder: {
                Circle().fill(Color.gray.opacity(0.3))
            }
            .frame(width: 100, height: 100)
            .clipShape(Circle())

            VStack(spacing: 8) {
                Text(callInfo.caller.name)
                    .font(.title.bold())
                Text("Incoming video call...")
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 48) {
                Button {
                    callViewModel.rejectCall(
                        callType: callInfo.callType,
                        callId: callInfo.callId
                    )
                } label: {
                    Image(systemName: "phone.down.fill")
                        .font(.largeTitle)
                        .foregroundStyle(.white)
                        .frame(width: 72, height: 72)
                        .background(Color.red, in: Circle())
                }

                Button {
                    callViewModel.acceptCall(
                        callType: callInfo.callType,
                        callId: callInfo.callId
                    )
                } label: {
                    Image(systemName: "video.fill")
                        .font(.largeTitle)
                        .foregroundStyle(.white)
                        .frame(width: 72, height: 72)
                        .background(Color.green, in: Circle())
                }
            }
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.ultraThinMaterial)
    }
}
```

**Wiring:**
- `callInfo.caller` exposes `name`, `imageURL`, `userId` of the person calling
- `rejectCall` sends a rejection notification to the caller and transitions state to `.idle`
- `acceptCall` joins the call and transitions state to `.joining` -> `.inCall`
- Replace this view in your `ViewFactory` by overriding the incoming call slot - check the [customization docs](https://getstream.io/video/docs/ios/ui-components/overview/) for the exact method signature

---

## Participant Grid Blueprint

Custom layout showing all remote participants in a scrollable grid, with the local participant in a corner PiP.

```swift
import SwiftUI
import StreamVideo        // CallParticipant
import StreamVideoSwiftUI // CallViewModel

struct ParticipantGridView: View {
    @ObservedObject var callViewModel: CallViewModel
    let columns = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .bottomTrailing) {
                // Remote participants grid
                ScrollView {
                    LazyVGrid(columns: columns, spacing: 8) {
                        ForEach(callViewModel.call?.state.remoteParticipants ?? [],
                                id: \.id) { participant in
                            let tileSize = geometry.size.width / 2 - 12
                            let frame = CGRect(x: 0, y: 0, width: tileSize, height: tileSize)
                            ParticipantTileView(
                                participant: participant,
                                availableFrame: frame,
                                call: callViewModel.call
                            )
                            .frame(width: tileSize, height: tileSize)
                        }
                    }
                    .padding(8)
                }

                // Local PiP
                if let local = callViewModel.call?.state.localParticipant {
                    let pipFrame = CGRect(x: 0, y: 0, width: 120, height: 160)
                    ParticipantTileView(
                        participant: local,
                        availableFrame: pipFrame,
                        call: callViewModel.call
                    )
                    .frame(width: 120, height: 160)
                    .padding(16)
                }
            }
        }
    }
}
```

**Wiring:**
- `remoteParticipants` excludes the local user - avoids showing your own video in the grid
- Pass the tile's rendered size as `availableFrame` so the SDK can request the correct track resolution
- The local PiP is positioned with `ZStack` alignment; adjust placement as needed
