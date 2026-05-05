# Chat - UIKit SDK Setup & Integration

Stream Chat UIKit provides pre-built UIKit components for building rich messaging UIs. This file covers package installation, client setup, authentication, customization, and gotchas. For view blueprints, see [CHAT-UIKIT-blueprints.md](CHAT-UIKIT-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper logout).

- **Blueprint** - UIKit view controller structure and initialization
- **Wiring** - SDK calls for each component, exact property paths
- **Requirements** - Info.plist keys, SDK version, Xcode version

## Quick ref

- **Package (UIKit):** `StreamChatUI` via SPM - `https://github.com/getstream/stream-chat-swift`
- **Package (core only):** `StreamChat` via SPM - `https://github.com/getstream/stream-chat-swift`
- **First:** Installation -> Info.plist -> Client init -> Connect user -> Show controllers
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/chat/docs/sdk/ios/`

Full view blueprints: [CHAT-UIKIT-blueprints.md](CHAT-UIKIT-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation (Swift Package Manager)

Check if the SDK is already installed in the project. If not, ask the user to check the installation guide in the [docs](https://getstream.io/chat/docs/sdk/ios/basics/integration/).

### Client Initialization

Initialize `ChatClient` once at app launch in `AppDelegate`. **Never** create `ChatClient` in a view controller `viewDidLoad` or any method that may be called repeatedly.

> **No `StreamChat` wrapper in UIKit.** Unlike the SwiftUI SDK, the UIKit layer does not require a `StreamChat` wrapper type. Use `ChatClient` directly; there is no equivalent of `StreamChat(chatClient:)` for UIKit apps.

> **Combining Chat + Video?** Importing `StreamChat` and `StreamVideo` in the same file causes "Ambiguous use of 'init'" for `User` and `Token` types. File isolation is required - same rule as SwiftUI. See [`COMBINED-CHAT-VIDEO.md`](COMBINED-CHAT-VIDEO.md) for the type-name mapping table and UIKit service file blueprints.

```swift
import StreamChat
import StreamChatUI

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    var chatClient: ChatClient!

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        let config = ChatClientConfig(apiKey: .init("your_api_key"))
        chatClient = ChatClient(config: config)
        return true
    }
}
```

Store `chatClient` as a strong property on `AppDelegate`. Access it from other places via:

```swift
let appDelegate = UIApplication.shared.delegate as! AppDelegate
let chatClient = appDelegate.chatClient
```

Or inject it into view controllers at creation time - prefer injection over `UIApplication.shared.delegate` casts in production code.

### User Authentication

Connect the user before presenting any chat UI. Typically called after your own auth flow completes.

**Static token (no expiry):**

```swift
let userInfo = UserInfo(id: "user-id", name: "User Name", imageURL: nil)
let token = Token(stringLiteral: "your_static_token_here")
chatClient.connectUser(userInfo: userInfo, token: token) { error in
    if let error { print("Connect failed: \(error)") }
}
```

**Token provider (expiring tokens - use only if the user asks for it):**

```swift
let userInfo = UserInfo(id: currentUser.id, name: currentUser.name)

let tokenProvider: TokenProvider = { completion in
    yourAuthService.fetchStreamToken(for: userInfo.id) { result in
        switch result {
        case .success(let tokenString):
            completion(.success(Token(stringLiteral: tokenString)))
        case .failure(let error):
            completion(.failure(error))
        }
    }
}

chatClient.connectUser(userInfo: userInfo, tokenProvider: tokenProvider) { error in
    if let error { print("Connect failed: \(error)") }
}
```

### Showing the Channel List

Create a `ChatChannelListVC` via its factory method and embed it in a `UINavigationController`. Navigation to individual channel views is handled automatically by the SDK's built-in router.

```swift
let query = ChannelListQuery(
    filter: .containMembers(userIds: [chatClient.currentUserId ?? ""]),
    sort: [Sorting(key: .lastMessageAt, isAscending: false)]
)
let controller = chatClient.channelListController(query: query)

let channelListVC = ChatChannelListVC.make(with: controller)

let nav = UINavigationController(rootViewController: channelListVC)
window?.rootViewController = nav
```

Use the static `make(with:)` factory method - it wires the controller and delegate correctly. You can also assign the controller directly via `channelListVC.controller = controller`, but the factory method is the preferred path. The VC calls `synchronize()` automatically on `viewDidLoad`.

---

## Components System

`Components` is the UIKit equivalent of SwiftUI's `ViewFactory`. Register custom subclasses globally before any chat UI is shown. All unregistered slots use SDK defaults.

```swift
// Register before presenting any chat UI (e.g. in AppDelegate)
Components.default.channelContentView = CustomChannelListItemView.self
Components.default.channelCell = CustomChannelListCell.self
Components.default.messageContentView = CustomMessageContentView.self
Components.default.channelListRouter = CustomChannelListRouter.self
```

**Key `Components.default` properties:**

| Property | Type | What it controls |
|---|---|---|
| `channelListVC` | `ChatChannelListVC.Type` | Channel list view controller |
| `channelCell` | `ChatChannelListCollectionViewCell.Type` | Channel list collection cell |
| `channelContentView` | `ChatChannelListItemView.Type` | Content inside each channel cell |
| `channelListRouter` | `ChatChannelListRouter.Type` | Navigation from channel list |
| `messageListVC` | `ChatMessageListVC.Type` | Message list view controller |
| `messageContentView` | `ChatMessageContentView.Type` | Individual message bubble |
| `messageComposerVC` | `ComposerVC.Type` | Composer view controller |
| `threadVC` | `ChatThreadVC.Type` | Thread replies view controller |

> **Never guess `Components` property names from training data.** Verify against the [Components docs](https://getstream.io/chat/docs/sdk/ios/uikit/components/) before registering a custom type.

Subclass the SDK component and override only what you need:

```swift
class CustomChannelListItemView: ChatChannelListItemView {
    override func updateContent() {
        super.updateContent()
        titleLabel.textColor = .systemBlue
    }
}

Components.default.channelContentView = CustomChannelListItemView.self
```

---

## Appearance

Configure `Appearance.default` before `ChatClient` is created and before any chat UI is shown. Changes apply globally to all SDK components.

```swift
// Colors
Appearance.default.colorPalette.accentPrimary = UIColor.systemBlue
Appearance.default.colorPalette.background = UIColor.systemBackground

// Fonts
Appearance.default.fonts.body = UIFont.systemFont(ofSize: 16)
Appearance.default.fonts.headline = UIFont.boldSystemFont(ofSize: 17)

// Images (icons used across the SDK)
Appearance.default.images.sendButton = UIImage(systemName: "paperplane.fill")!
Appearance.default.images.close = UIImage(systemName: "xmark")!
```

> **Never guess `ColorPalette` property names.** Use only confirmed tokens or fetch the [theming docs](https://getstream.io/chat/docs/sdk/ios/uikit/theming/) before using a token.

**Confirmed `ColorPalette` tokens:**

| Token | What it controls |
|---|---|
| `accentPrimary` | Primary accent (send button, selection highlights) |
| `background` | Global background color |
| `background1` | Navigation bar and elevated surface background |
| `text` | Primary text color |

---

## ChatClientConfig Options

All config changes must happen before `ChatClient(config:)` is called.

```swift
var config = ChatClientConfig(apiKey: .init("your_api_key"))

// Offline support (all enabled by default)
config.isLocalStorageEnabled = true
config.isAutomaticSyncOnReconnectEnabled = true
config.staysConnectedInBackground = true

// Required if you add a Notification Service Extension
config.applicationGroupIdentifier = "group.com.yourcompany.yourapp"

chatClient = ChatClient(config: config)
```

---

## Controller Patterns

**Synchronize before reading data:**

`ChatChannelListController` does not load data until `synchronize()` is called. `ChatChannelListVC` calls it automatically on `viewDidLoad`. For controllers you observe manually, call it explicitly:

```swift
let controller = chatClient.channelListController(query: query)
controller.synchronize { error in
    if let error { print("Sync failed: \(error)") }
}
```

**Observe changes with `ChatChannelListControllerDelegate`:**

```swift
class ViewController: UIViewController, ChatChannelListControllerDelegate {
    private var channelListController: ChatChannelListController?

    override func viewDidLoad() {
        super.viewDidLoad()
        let query = ChannelListQuery(filter: .containMembers(userIds: [chatClient.currentUserId ?? ""]))
        channelListController = chatClient.channelListController(query: query)
        channelListController?.delegate = self
        channelListController?.synchronize()
    }

    func controller(_ controller: ChatChannelListController,
                    didChangeChannels changes: [ListChange<ChatChannel>]) {
        // React to insertions, deletions, moves, updates
        tableView.reloadData()
    }
}
```

**Load more channels (pagination):**

```swift
channelListController?.loadNextChannels(limit: 20) { error in
    if let error { print("Load more failed: \(error)") }
}
```

---

## Logout

Always wait for logout to complete before connecting another user:

```swift
chatClient.logout { [weak self] in
    // Safe to connect new user now
    self?.chatClient.connectUser(...)
}
```

---

## Gotchas

- **No `StreamChat` wrapper in UIKit.** The SwiftUI layer requires `StreamChat(chatClient:)` - UIKit does not. Use `ChatClient` directly.
- **`Appearance.default` and `Components.default` must be configured before any SDK view loads.** Changes after the first view controller appears may not take effect.
- **Always wait for `logout` completion before connecting another user.** The SDK uses persistent storage; connecting while logout is in progress risks state corruption and crashes.
- **Never use `ChatClient.shared` when you manage the client yourself.** If you initialize `ChatClient` in `AppDelegate`, access it via your stored reference, not `ChatClient.shared` - that requires the SDK to have registered the instance, which is not guaranteed in all configurations.
- **`ChatChannelListVC` must be embedded in a `UINavigationController`.** The SDK router pushes `ChatMessageListVC` onto the navigation stack automatically. Without a navigation controller, this push will silently fail.
- **Never call `synchronize()` on controllers already managed by a VC.** `ChatChannelListVC` calls `synchronize()` automatically on `viewDidLoad`. Calling it again externally causes duplicate fetches.
- **Never use dev tokens in production.** `devToken()` disables token auth and allows any client to impersonate any user.
- **Never store your Stream secret in the app.** Secrets on-device can be extracted from jailbroken devices and enable destructive actions on your app instance.
- **Import both `StreamChat` and `StreamChatUI` in every file that uses either module.** `ChatClient`, `UserInfo`, `Token`, and all controllers live in `StreamChat`; UIKit views and view controllers live in `StreamChatUI`. Missing either import causes compile errors.
