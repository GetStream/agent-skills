# Video - UIKit SDK Setup & Integration

`StreamVideoUIKit` is a thin UIKit wrapper around the same `StreamVideo` core used by the SwiftUI SDK. `CallViewModel` (from `StreamVideoSwiftUI`) is the central state object - it is used directly in UIKit apps. This file covers package setup, client initialization, `CallViewController`, and call state observation. For view controller blueprints, see [VIDEO-UIKIT-blueprints.md](VIDEO-UIKIT-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production).

> **Combining Chat + Video?** File isolation is required - the same collision rules as SwiftUI apply because `StreamVideoUIKit` depends on `StreamVideoSwiftUI`. See [`COMBINED-CHAT-VIDEO.md`](COMBINED-CHAT-VIDEO.md).

## Quick ref

- **Packages:** `StreamVideo` + `StreamVideoSwiftUI` + `StreamVideoUIKit` via SPM - `https://github.com/getstream/stream-video-swift`
- **First:** Installation -> Info.plist -> Client init -> `StreamVideoUI` -> `CallViewModel` -> `CallViewController`
- **Docs:** `https://getstream.io/video/docs/ios/`

Full view blueprints: [VIDEO-UIKIT-blueprints.md](VIDEO-UIKIT-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation (Swift Package Manager)

Add from `https://github.com/getstream/stream-video-swift` to the app target:
- `StreamVideo` - core client and models
- `StreamVideoSwiftUI` - `CallViewModel`, `CallModifier`, `ViewFactory`
- `StreamVideoUIKit` - `CallViewController`

### Client Initialization

Initialize `StreamVideo` and `StreamVideoUI` **once** in `AppDelegate`. The setup is identical to the SwiftUI `AppDelegate` path - `StreamVideoUI` must be created before any call view renders.

```swift
import UIKit
import StreamVideo
import StreamVideoSwiftUI

class AppDelegate: NSObject, UIApplicationDelegate {
    var streamVideo: StreamVideo?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        let user = User(id: "user-id", name: "User Name", imageURL: nil, customData: [:])
        let token = UserToken(rawValue: "your_static_token")
        let client = StreamVideo(apiKey: "your_api_key", user: user, token: token)
        streamVideo = client
        _ = StreamVideoUI(streamVideo: client)
        return true
    }
}
```

`StreamVideoUI` **must** be initialized before any call view renders. Creating a call view without it causes a crash.

---

## User Authentication

Same as the SwiftUI SDK - `StreamVideo` is the same core client.

### Static token

```swift
let user = User(id: "alice", name: "Alice Smith", imageURL: nil, customData: [:])
let token = UserToken(rawValue: "your_static_token")
let client = StreamVideo(apiKey: "your_api_key", user: user, token: token)
```

Token generation: `stream token <user_id>`.

### Token provider (expiring tokens)

```swift
let client = StreamVideo(
    apiKey: "your_api_key",
    user: user,
    token: initialToken,
    tokenProvider: { result in
        yourAuthService.fetchToken(for: user.id) { fetchResult in
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

## CallViewModel

`CallViewModel` is from `StreamVideoSwiftUI` and is used directly in UIKit. Create **one instance** at the root of the call flow and share it across view controllers.

```swift
import StreamVideoSwiftUI

let callViewModel = CallViewModel()
```

Use it to start, join, and leave calls - same API as in SwiftUI:

```swift
// Join an existing call (no ringing)
callViewModel.joinCall(callType: "default", callId: "my-call-id")

// Start a ringing call
callViewModel.startCall(callType: "default", callId: UUID().uuidString, members: members, ring: true)

// Leave
callViewModel.hangUp()
```

---

## CallViewController

`CallViewController` is the main UIKit call screen. It wraps a `CallViewModel` and manages its own full-screen layout.

> **Always subclass `CallViewController` - do not use it directly.** The default `setupVideoView()` creates a `UIHostingController` for the SwiftUI call UI but immediately discards it. ARC releases the hosting controller while its view is still on screen, tearing down SwiftUI's gesture recognizers and making all buttons untappable. See the `VideoCallViewController` blueprint in [VIDEO-UIKIT-blueprints.md](VIDEO-UIKIT-blueprints.md).

### Creating

```swift
import StreamVideoUIKit

// Always use your VideoCallViewController subclass (see blueprints)
let callVC = VideoCallViewController(viewModel: callViewModel)
```

### Starting a call

Call `startCall` on the view controller **before** presenting it:

```swift
callVC.startCall(callType: "default", callId: callId, members: members)
callVC.modalPresentationStyle = .fullScreen
present(callVC, animated: true)
```

To join an existing call without ringing, pass `ring: false` (the default):

```swift
callVC.startCall(callType: "default", callId: existingCallId, members: [])
```

There is no separate `joinCall` method on `CallViewController` - `startCall` with `ring: false` both creates and joins.

### Observing call state and dismissing

There is no delegate. Observe `callViewModel.$callingState` via Combine to react to call lifecycle events:

```swift
import Combine
import StreamVideoSwiftUI

private var cancellables = Set<AnyCancellable>()

callViewModel.$callingState
    .receive(on: DispatchQueue.main)
    .sink { [weak self] state in
        if state == .idle {
            self?.dismiss(animated: true)
        }
    }
    .store(in: &cancellables)
```

### `callingState` values

| State | When |
|---|---|
| `.idle` | No active or pending call |
| `.outgoing` | Ringing, waiting for others |
| `.incoming(IncomingCall)` | Remote user is calling |
| `.joining` | Connecting |
| `.inCall` | Active call |
| `.reconnecting` | Reconnecting after network drop |

---

## Info.plist Requirements

```xml
<key>NSCameraUsageDescription</key>
<string>Video calls require camera access.</string>
<key>NSMicrophoneUsageDescription</key>
<string>Video calls require microphone access.</string>
```

---

## Gotchas

- **`StreamVideoUI` must be initialized before any call view renders.** Same rule as SwiftUI - create it in `AppDelegate` before presenting `CallViewController`.
- **Never use `CallViewController` directly - always subclass it and override `setupVideoView()`.** The default implementation discards the `UIHostingController` immediately after creation; ARC releases it, making all call screen buttons untappable. The `VideoCallViewController` blueprint in [VIDEO-UIKIT-blueprints.md](VIDEO-UIKIT-blueprints.md) fixes this with `addChild`/`didMove(toParent:)` and a retained `callHostingController` property.
- **`CallViewModel()` must not be a stored `let` or eagerly initialized `var` property.** `CallViewModel.init()` accesses `@Injected(\.streamVideo)` immediately - if `StreamVideoUI` hasn't been set up yet, it crashes with "Video client was not setup". Always declare it `private lazy var callViewModel = CallViewModel()` so creation is deferred until first access.
- **`CallViewModel` is from `StreamVideoSwiftUI`, not `StreamVideoUIKit`.** Import `StreamVideoSwiftUI` in files that declare or use `CallViewModel`.
- **Always `import UIKit`** in any file that uses `UIViewController`, `UIApplicationDelegate`, `UIApplication`, or other UIKit types - even when Stream imports are present, `import UIKit` is still required.
- **There is no `CallViewControllerDelegate`.** Use Combine to subscribe to `callViewModel.$callingState` for lifecycle events.
- **Handle `.incoming` state by presenting `CallViewController` modally.** If you only observe `.idle` and ignore `.incoming`, the SDK renders the incoming call UI without a backing `UIViewController` - buttons will not receive touches. Check `presentedViewController == nil` before presenting to avoid stacking duplicate call screens.
- **There is no `joinCall` on `CallViewController`.** Use `startCall` with `ring: false` (the default) to join an existing call.
- **Call `startCall` before presenting the view controller**, not after.
- **Never use dev tokens in production.** `devToken()` disables token auth.
- **File isolation is required when combining with Chat.** `StreamVideoUIKit` depends on `StreamVideoSwiftUI`, which exports colliding names. See [`COMBINED-CHAT-VIDEO.md`](COMBINED-CHAT-VIDEO.md).
