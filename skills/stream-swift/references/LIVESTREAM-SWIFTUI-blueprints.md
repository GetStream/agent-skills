# Livestream SwiftUI - View Blueprints

Load only the section you are implementing. For SDK setup, call type details, and gotchas, see [LIVESTREAM-SWIFTUI.md](LIVESTREAM-SWIFTUI.md). For standard `CallViewModel` and client initialization patterns, see [VIDEO-SWIFTUI-blueprints.md](VIDEO-SWIFTUI-blueprints.md).

---

## App Entry Point Blueprint

Use the same initialization pattern as a standard video app. The `livestream` call type does not require a different client setup.

```swift
import SwiftUI
import StreamVideo
import StreamVideoSwiftUI

@main
struct LivestreamApp: App {
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
            LivestreamRootView()
        }
    }
}
```

---

## Root View Blueprint

> **Do NOT use `CallModifier` for livestreaming.** `CallModifier` wraps the content in `VideoViewOverlay`, which overlays `CallContainer` on top of all child views whenever `callingState` is `.inCall`, `.joining`, or `.outgoing`. This replaces your custom creator/viewer UI with the SDK's default meeting screen. Livestream views manage their own state — no `CallModifier` needed.

```swift
import SwiftUI
import StreamVideoSwiftUI

struct LivestreamRootView: View {
    @StateObject private var callViewModel = CallViewModel()

    var body: some View {
        LivestreamModeSelectionView(callViewModel: callViewModel)
        // No CallModifier — creator and viewer views own their call UI entirely
    }
}
```

**Wiring:**
- `CallViewModel` is `@StateObject` — `LivestreamRootView` owns the call session for its lifetime
- Pass `callViewModel` down as `@ObservedObject` — never create a second instance
- `CallViewModel()` uses default settings (`audioOn: true`, `videoOn: true`). The `livestream` call type enforces no-publish for viewers via server-side permissions

---

## Mode Selection View Blueprint

Lets the user enter a call ID and choose between hosting (creator) or watching (viewer).

```swift
import SwiftUI
import StreamVideoSwiftUI

struct LivestreamModeSelectionView: View {
    @ObservedObject var callViewModel: CallViewModel
    @State private var callId = ""
    @State private var selectedMode: LivestreamMode?

    var body: some View {
        NavigationStack {
            VStack(spacing: 32) {
                Text("Livestream")
                    .font(.largeTitle.bold())

                TextField("Stream ID", text: $callId)
                    .textFieldStyle(.roundedBorder)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)

                VStack(spacing: 16) {
                    Button {
                        selectedMode = .creator
                    } label: {
                        Label("Go Live (Creator)", systemImage: "video.circle.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(callId.isEmpty)

                    Button {
                        selectedMode = .viewer
                    } label: {
                        Label("Watch Stream (Viewer)", systemImage: "play.circle.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .disabled(callId.isEmpty)
                }
            }
            .padding(24)
            .navigationDestination(isPresented: Binding(
                get: { selectedMode == .creator },
                set: { if !$0 { selectedMode = nil } }
            )) {
                CreatorLivestreamView(callId: callId, callViewModel: callViewModel) {
                    selectedMode = nil
                }
            }
            .navigationDestination(isPresented: Binding(
                get: { selectedMode == .viewer },
                set: { if !$0 { selectedMode = nil } }
            )) {
                ViewerLivestreamView(callId: callId, callViewModel: callViewModel) {
                    selectedMode = nil
                }
            }
        }
    }
}

enum LivestreamMode {
    case creator, viewer
}
```

**Wiring:**
- `selectedMode` drives navigation — `onExit` sets it to `nil` to pop back
- Both destination views receive the same `callViewModel` instance

---

## Creator View Blueprint

The creator view manages the full host lifecycle: join in backstage, preview camera, go live, monitor viewers, and end the stream.

```swift
import SwiftUI
import StreamVideo
import StreamVideoSwiftUI

struct CreatorLivestreamView: View {
    let callId: String
    @ObservedObject var callViewModel: CallViewModel
    let onExit: () -> Void

    @State private var isGoingLive = false
    @State private var isEndingStream = false

    private var call: Call? { callViewModel.call }
    private var isLive: Bool { !(call?.state.backstage ?? true) }
    private var viewerCount: Int { call?.state.remoteParticipants.count ?? 0 }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            switch callViewModel.callingState {
            case .joining:
                joiningOverlay
            case .inCall:
                livestreamContent
            default:
                joiningOverlay
            }
        }
        .navigationTitle(isLive ? "Live" : "Backstage")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                if !isLive {
                    Button("Cancel") {
                        callViewModel.hangUp()
                        onExit()
                    }
                    .foregroundStyle(.white)
                }
            }
        }
        .alert(
            "Stream Error",
            isPresented: Binding(
                get: { callViewModel.error != nil },
                set: { if !$0 { callViewModel.error = nil } }
            )
        ) {
            Button("OK") { callViewModel.error = nil }
        } message: {
            Text(callViewModel.error?.localizedDescription ?? "Unknown error")
        }
        .onAppear {
            guard callViewModel.callingState == .idle else { return }
            callViewModel.joinCall(callType: "livestream", callId: callId)
        }
        .onChange(of: callViewModel.callingState) { _, state in
            // Auto-exit if the call ends unexpectedly (e.g. network drop, kicked)
            if state == .idle {
                onExit()
            }
        }
    }

    @ViewBuilder
    private var joiningOverlay: some View {
        VStack(spacing: 16) {
            ProgressView()
                .tint(.white)
            Text("Setting up stream...")
                .foregroundStyle(.white)
        }
    }

    @ViewBuilder
    private var livestreamContent: some View {
        ZStack(alignment: .bottom) {
            cameraPreview
            VStack(spacing: 0) {
                Spacer()
                statusBadge
                    .padding(.bottom, 16)
                controlBar
                    .padding(.bottom, 32)
            }
        }
    }

    @ViewBuilder
    private var cameraPreview: some View {
        GeometryReader { geometry in
            if let local = call?.state.localParticipant {
                let frame = CGRect(origin: .zero, size: geometry.size)
                VideoCallParticipantView(
                    participant: local,
                    availableFrame: frame,
                    contentMode: .scaleAspectFill,
                    customData: [:],
                    call: call
                )
                .ignoresSafeArea()
            }
        }
    }

    @ViewBuilder
    private var statusBadge: some View {
        HStack(spacing: 8) {
            if isLive {
                Circle()
                    .fill(Color.red)
                    .frame(width: 8, height: 8)
                Text("LIVE")
                    .font(.caption.bold())
                    .foregroundStyle(.white)
                Text("·")
                    .foregroundStyle(.white.opacity(0.6))
                Image(systemName: "person.fill")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.8))
                Text("\(viewerCount)")
                    .font(.caption)
                    .foregroundStyle(.white.opacity(0.8))
            } else {
                Text("BACKSTAGE")
                    .font(.caption.bold())
                    .foregroundStyle(.white.opacity(0.8))
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(.black.opacity(0.6), in: Capsule())
    }

    @ViewBuilder
    private var controlBar: some View {
        HStack(spacing: 20) {
            micButton
            cameraButton
            flipCameraButton
            Spacer()
            if isLive {
                endStreamButton
            } else {
                goLiveButton
            }
        }
        .padding(.horizontal, 24)
    }

    private var micButton: some View {
        Button {
            callViewModel.toggleMicrophoneEnabled()
        } label: {
            Image(systemName: callViewModel.callSettings.audioOn
                  ? "mic.fill" : "mic.slash.fill")
                .font(.title2)
                .foregroundStyle(callViewModel.callSettings.audioOn ? .white : .red)
                .frame(width: 52, height: 52)
                .background(.ultraThinMaterial, in: Circle())
        }
    }

    private var cameraButton: some View {
        Button {
            callViewModel.toggleCameraEnabled()
        } label: {
            Image(systemName: callViewModel.callSettings.videoOn
                  ? "video.fill" : "video.slash.fill")
                .font(.title2)
                .foregroundStyle(callViewModel.callSettings.videoOn ? .white : .red)
                .frame(width: 52, height: 52)
                .background(.ultraThinMaterial, in: Circle())
        }
    }

    private var flipCameraButton: some View {
        Button {
            Task { try? await call?.camera.flip() }
        } label: {
            Image(systemName: "arrow.triangle.2.circlepath.camera.fill")
                .font(.title2)
                .foregroundStyle(.white)
                .frame(width: 52, height: 52)
                .background(.ultraThinMaterial, in: Circle())
        }
    }

    private var goLiveButton: some View {
        Button {
            Task {
                isGoingLive = true
                defer { isGoingLive = false }
                try? await call?.goLive()
            }
        } label: {
            Group {
                if isGoingLive {
                    ProgressView().tint(.white)
                } else {
                    Text("Go Live")
                        .font(.headline)
                        .foregroundStyle(.white)
                }
            }
            .frame(width: 100, height: 44)
            .background(Color.red, in: Capsule())
        }
        .disabled(isGoingLive)
    }

    private var endStreamButton: some View {
        Button {
            Task {
                isEndingStream = true
                defer { isEndingStream = false }
                try? await call?.stopLive()
                try? await call?.end()
                callViewModel.hangUp()
                // onExit() is called by the .onChange(of: callingState) observer
            }
        } label: {
            Group {
                if isEndingStream {
                    ProgressView().tint(.white)
                } else {
                    Text("End Stream")
                        .font(.headline)
                        .foregroundStyle(.white)
                }
            }
            .frame(width: 120, height: 44)
            .background(Color.red, in: Capsule())
        }
        .disabled(isEndingStream)
    }
}
```

**Wiring:**
- **No `CallModifier`** — `CreatorLivestreamView` owns the call UI entirely. `CallModifier` would overlay the SDK's default meeting screen on top of this view the moment `callingState` becomes `.inCall`, replacing the custom livestream UI. Never wrap livestream flows with `CallModifier`.
- `.onAppear` guards with `callingState == .idle` to prevent double-joining if the view re-appears
- `.onChange(of: callingState)` watches for `.idle` to call `onExit()` — this handles both the explicit "End Stream" path and unexpected disconnects (network drop, kicked). `onExit()` is NOT called directly after `hangUp()` in `endStreamButton`; the observer fires it once `callingState` settles to `.idle`
- `isLive` is derived from `call?.state.backstage` — no separate `Bool` state needed
- `callSettings.audioOn` / `.videoOn` — no `is` prefix
- `VideoCallParticipantView` requires `contentMode`, `customData`, and `call`
- `goLive()` and `stopLive()` are `@discardableResult async throws`
- `call?.end()` terminates the session server-side; `hangUp()` resets local `CallViewModel` state

---

## Viewer View Blueprint (WebRTC)

The viewer view joins the call as a subscriber and watches the creator's stream in real time.

```swift
import SwiftUI
import StreamVideo
import StreamVideoSwiftUI

struct ViewerLivestreamView: View {
    let callId: String
    @ObservedObject var callViewModel: CallViewModel
    let onExit: () -> Void

    private var call: Call? { callViewModel.call }
    private var isLive: Bool { !(call?.state.backstage ?? true) }
    private var hostParticipant: CallParticipant? {
        call?.state.remoteParticipants.first
    }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            switch callViewModel.callingState {
            case .joining:
                connectingOverlay
            case .inCall:
                if isLive, let host = hostParticipant {
                    watchingContent(host: host)
                } else {
                    waitingForHostOverlay
                }
            default:
                connectingOverlay
            }
        }
        .navigationTitle("Watch Stream")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button("Leave") {
                    callViewModel.hangUp()
                    // onExit() fires via .onChange below once state reaches .idle
                }
                .foregroundStyle(.white)
            }
        }
        .alert(
            "Stream Error",
            isPresented: Binding(
                get: { callViewModel.error != nil },
                set: { if !$0 { callViewModel.error = nil } }
            )
        ) {
            Button("OK") { callViewModel.error = nil }
        } message: {
            Text(callViewModel.error?.localizedDescription ?? "Unknown error")
        }
        .onAppear {
            guard callViewModel.callingState == .idle else { return }
            callViewModel.joinCall(callType: "livestream", callId: callId)
        }
        .onChange(of: callViewModel.callingState) { _, state in
            if state == .idle {
                onExit()
            }
        }
    }

    @ViewBuilder
    private var connectingOverlay: some View {
        VStack(spacing: 16) {
            ProgressView()
                .tint(.white)
            Text("Connecting...")
                .foregroundStyle(.white)
        }
    }

    @ViewBuilder
    private var waitingForHostOverlay: some View {
        VStack(spacing: 16) {
            Image(systemName: "antenna.radiowaves.left.and.right")
                .font(.system(size: 48))
                .foregroundStyle(.white.opacity(0.6))
            Text("Waiting for host to go live...")
                .font(.headline)
                .foregroundStyle(.white.opacity(0.8))
        }
    }

    @ViewBuilder
    private func watchingContent(host: CallParticipant) -> some View {
        ZStack(alignment: .topLeading) {
            GeometryReader { geometry in
                let frame = CGRect(origin: .zero, size: geometry.size)
                VideoCallParticipantView(
                    participant: host,
                    availableFrame: frame,
                    contentMode: .scaleAspectFill,
                    customData: [:],
                    call: call
                )
                .ignoresSafeArea()
            }

            liveBadge
                .padding(16)
        }
    }

    private var liveBadge: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(Color.red)
                .frame(width: 8, height: 8)
            Text("LIVE")
                .font(.caption.bold())
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(.black.opacity(0.6), in: Capsule())
    }
}
```

**Wiring:**
- **No `CallModifier`** — same reason as `CreatorLivestreamView`. Applying `CallModifier` at any level in the livestream hierarchy will intercept `.inCall` and show the default meeting UI
- `.onAppear` guards with `callingState == .idle` to prevent double-joining
- `.onChange(of: callingState)` calls `onExit()` when state reaches `.idle` — handles both Leave button and unexpected disconnects
- `isLive` is derived from `call?.state.backstage` — viewer shows the waiting overlay until host calls `goLive()`
- `VideoCallParticipantView` requires `contentMode`, `customData`, and `call`

---

## Viewer View Blueprint (HLS)

Use the HLS path for large-scale audiences where per-viewer WebRTC connections are impractical.

```swift
import SwiftUI
import AVKit
import StreamVideo
import StreamVideoSwiftUI

struct HLSViewerLivestreamView: View {
    let callId: String
    @ObservedObject var callViewModel: CallViewModel
    let onExit: () -> Void

    @State private var player = AVPlayer()
    @State private var isWaitingForStream = true

    private var call: Call? { callViewModel.call }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if isWaitingForStream {
                waitingOverlay
            } else {
                VideoPlayer(player: player)
                    .ignoresSafeArea()
                    .overlay(alignment: .topLeading) {
                        liveBadge.padding(16)
                    }
            }
        }
        .navigationTitle("Watch Stream")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(true)
        .toolbar {
            ToolbarItem(placement: .navigationBarLeading) {
                Button("Leave") {
                    player.pause()
                    onExit()
                }
                .foregroundStyle(.white)
            }
        }
        .task {
            await waitAndStartHLS()
        }
        .onDisappear {
            player.pause()
        }
    }

    @ViewBuilder
    private var waitingOverlay: some View {
        VStack(spacing: 16) {
            ProgressView()
                .tint(.white)
            Text("Waiting for stream...")
                .foregroundStyle(.white)
        }
    }

    private var liveBadge: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(Color.red)
                .frame(width: 8, height: 8)
            Text("LIVE")
                .font(.caption.bold())
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(.black.opacity(0.6), in: Capsule())
    }

    private func waitAndStartHLS() async {
        guard let call else { return }

        // Poll until egress.hls.playlistUrl is populated (host has gone live with HLS)
        while !Task.isCancelled {
            if let playlistUrl = call.state.egress?.hls?.playlistUrl,
               let hlsURL = URL(string: playlistUrl) {
                player.replaceCurrentItem(with: AVPlayerItem(url: hlsURL))
                player.play()
                isWaitingForStream = false
                return
            }
            try? await Task.sleep(for: .seconds(2))
        }
    }
}
```

**Wiring:**
- `player` is `@State` — created once, never recreated in `body`
- `waitAndStartHLS()` runs in `.task` — cancelled automatically when the view disappears
- `call.state.egress?.hls?.playlistUrl` — `egress` is `EgressResponse?`, HLS URL is at `egress.hls.playlistUrl` (not `egress.broadcasting.hlsPlaylistUrl`)
- HLS viewers do not join as WebRTC participants
- HLS latency is 10–30 s by design

---

## Complete Sample: Wiring the Three Views Together

```
LivestreamApp
  └── LivestreamRootView          (@StateObject CallViewModel — NO CallModifier)
        └── LivestreamModeSelectionView  (enter stream ID, choose mode)
              ├── CreatorLivestreamView  (join + backstage + goLive + controls)
              └── ViewerLivestreamView   (join as subscriber + watch)
```

Each view passes the **same** `callViewModel` downward. No view below `LivestreamRootView` creates its own `CallViewModel`.
