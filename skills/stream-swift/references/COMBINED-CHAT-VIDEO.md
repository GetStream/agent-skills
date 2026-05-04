# Combined Chat + Video: SDK Collision Guide

Load this file when the app uses both Stream Chat and Stream Video. Covers type-name collisions, file isolation strategies, and UIKit/SwiftUI setup blueprints for combined apps.

---

## Why collisions happen

Both SDKs model the same domain concepts, but with different type names. Some names collide when importing both SDKs' SwiftUI layers in the same file; others are just conceptually similar (different names for the same idea).

### Type-name mapping

| Concept | Chat type | Video type |
|---|---|---|
| Authenticated user | `UserInfo` (`StreamChat`) | `User` (`StreamVideo`) |
| Auth token | `Token` (`StreamChat`) | `UserToken` (`StreamVideo`) |
| SwiftUI SDK wrapper | `StreamChat` (`StreamChatSwiftUI`) | `StreamVideoUI` (`StreamVideoSwiftUI`) |
| SwiftUI view customization | `ViewFactory` (`StreamChatSwiftUI`) | `ViewFactory` (`StreamVideoSwiftUI`) |
| SwiftUI dependency injection | `@Injected`, `InjectionKey`, `InjectedValues` (`StreamChatSwiftUI`) | same names (`StreamVideoSwiftUI`) |

### Which collisions actually cause compiler errors

**`User` / `Token` (both layers)** - importing `StreamChat` and `StreamVideo` in the same file causes **"Ambiguous use of 'init'"** for `User` and `Token`. Fix: never construct `User` or `Token`/`UserToken` instances in the same file as their Chat counterparts.

**SwiftUI layer** - `ViewFactory`, `@Injected`, `InjectionKey`, `InjectedValues` exist in **both** `StreamChatSwiftUI` and `StreamVideoSwiftUI`. Importing both in the same file produces an "ambiguous use" compiler error.

**UIKit layer** - `StreamVideoUIKit` depends on `StreamVideoSwiftUI`, so the SwiftUI-layer collisions apply to UIKit apps too if `StreamChatSwiftUI` is also present. Additionally, the `User`/`Token` core collisions apply whenever both `StreamChat` and `StreamVideo` are imported together.

**Fix for all cases: file isolation.** Never import both SDKs in the same file. Keep all SDK-specific construction in its own service file.

---

## SwiftUI combined apps

**Rule: never import both `StreamChatSwiftUI` and `StreamVideoSwiftUI` in the same file.**

File layout:

```
ChatService.swift        -> import StreamChat, StreamChatSwiftUI   (only)
ChatViewFactory.swift    -> import StreamChatSwiftUI                (only)
VideoService.swift       -> import StreamVideo, StreamVideoSwiftUI  (only)
VideoViewFactory.swift   -> import StreamVideoSwiftUI               (only)
MyApp.swift              -> no Stream imports - calls both services
```

**ChatService.swift:**

```swift
import StreamChat
import StreamChatSwiftUI

final class ChatService {
    static let shared = ChatService()

    private(set) var streamChat: StreamChat?

    private init() {}

    func setUp(apiKey: String, userId: String, userName: String, token: String) {
        let config = ChatClientConfig(apiKey: .init(apiKey))
        let chatClient = ChatClient(config: config)
        streamChat = StreamChat(chatClient: chatClient)
        let userInfo = UserInfo(id: userId, name: userName)
        let chatToken = Token(stringLiteral: token)
        chatClient.connectUser(userInfo: userInfo, token: chatToken) { error in
            if let error { print("Chat connect error: \(error)") }
        }
    }
}
```

**VideoService.swift:**

```swift
import StreamVideo
import StreamVideoSwiftUI

final class VideoService {
    static let shared = VideoService()

    private(set) var streamVideo: StreamVideo?
    private var streamVideoUI: StreamVideoUI?   // must stay alive; not exposed

    private init() {}

    func setUp(apiKey: String, userId: String, userName: String, token: String) {
        let user = User(id: userId, name: userName, imageURL: nil, customData: [:])
        let videoToken = UserToken(rawValue: token)
        let client = StreamVideo(apiKey: apiKey, user: user, token: videoToken)
        streamVideo = client
        streamVideoUI = StreamVideoUI(streamVideo: client)
    }
}
```

**MyApp.swift - no Stream imports:**

```swift
@main
struct MyApp: App {
    init() {
        ChatService.shared.setUp(apiKey: "your_api_key", userId: "alice", userName: "Alice", token: "your_token")
        VideoService.shared.setUp(apiKey: "your_api_key", userId: "alice", userName: "Alice", token: "your_token")
    }

    var body: some Scene {
        WindowGroup { RootView() }
    }
}
```

The same JWT token and API key work for both Chat and Video. Both services are initialized with the same credentials.

---

## UIKit combined apps

**File isolation is required.** `StreamVideoUIKit` depends on `StreamVideoSwiftUI`, which exports `ViewFactory`, `@Injected`, `InjectionKey`, and `InjectedValues`. Importing `StreamVideoSwiftUI` and `StreamChatSwiftUI` in the same file causes ambiguous-use compiler errors. The same rule as SwiftUI applies: one file per SDK.

Additionally, importing `StreamChat` and `StreamVideo` in the same file causes **"Ambiguous use of 'init'"** errors for `User` and `Token` types. Keep all SDK-specific construction in isolated files.

File layout:

```
ChatService.swift     -> import StreamChat, StreamChatUI            (only)
VideoService.swift    -> import StreamVideo, StreamVideoSwiftUI, StreamVideoUIKit  (only)
AppDelegate.swift     -> no Stream imports - calls both services
```

**ChatService.swift (UIKit):**

```swift
import StreamChat
import StreamChatUI

final class ChatService {
    static let shared = ChatService()
    private(set) var client: ChatClient?
    private init() {}

    func setUp(apiKey: String, userId: String, userName: String, token: String) {
        let config = ChatClientConfig(apiKey: .init(apiKey))
        let chatClient = ChatClient(config: config)
        client = chatClient
        let userInfo = UserInfo(id: userId, name: userName)
        let chatToken = Token(stringLiteral: token)
        chatClient.connectUser(userInfo: userInfo, token: chatToken) { error in
            if let error { print("Chat connect error: \(error)") }
        }
    }
}
```

**VideoService.swift (UIKit):**

```swift
import StreamVideo
import StreamVideoSwiftUI
import StreamVideoUIKit

final class VideoService {
    static let shared = VideoService()
    private(set) var client: StreamVideo?
    private var videoUI: StreamVideoUI?
    private init() {}

    func setUp(apiKey: String, userId: String, userName: String, token: String) {
        let user = User(id: userId, name: userName, imageURL: nil, customData: [:])
        let videoToken = UserToken(rawValue: token)
        let streamVideo = StreamVideo(apiKey: apiKey, user: user, token: videoToken)
        client = streamVideo
        videoUI = StreamVideoUI(streamVideo: streamVideo)
    }
}
```

**AppDelegate.swift - no Stream imports:**

```swift
import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        ChatService.shared.setUp(apiKey: "your_api_key", userId: "alice", userName: "Alice", token: "your_token")
        VideoService.shared.setUp(apiKey: "your_api_key", userId: "alice", userName: "Alice", token: "your_token")
        return true
    }
}
```

Access the clients elsewhere via `ChatService.shared.client` and `VideoService.shared.client`.

---

## Shared resources

- **Same API key** - one Stream project covers both Chat and Video.
- **Same JWT format** - `stream token <user_id>` generates a token valid for both products. The CLI uses the app's secret server-side; only the API key and token go into the app.
- **Same user ID** - the user ID must match in both SDK initializations if the same person is using both Chat and Video.
