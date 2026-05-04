# Chat UIKit - View Blueprints

Load only the section you are implementing. For setup, client initialization, and gotchas, see [CHAT-UIKIT.md](CHAT-UIKIT.md).

---

## AppDelegate Blueprint

```swift
// AppDelegate.swift
import UIKit
import StreamChat
import StreamChatUI

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    var chatClient: ChatClient!

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        configureAppearance()
        configureComponents()

        let config = ChatClientConfig(apiKey: .init("your_api_key"))
        chatClient = ChatClient(config: config)
        return true
    }

    private func configureAppearance() {
        Appearance.default.colorPalette.accentPrimary = .systemBlue
    }

    private func configureComponents() {
        // Register custom components before any chat UI loads
        // Components.default.channelContentView = CustomChannelListItemView.self
    }
}
```

**Wiring:**
- `Appearance.default` and `Components.default` must be configured before `ChatClient` is created and before any SDK view loads
- `chatClient` is a stored strong reference - never let it go out of scope

---

## SceneDelegate Blueprint

Modern UIKit apps with `UIWindowSceneDelegate` set up the window and root view controller here.

```swift
// SceneDelegate.swift
import UIKit
import StreamChat

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }

        let appDelegate = UIApplication.shared.delegate as! AppDelegate
        let chatClient = appDelegate.chatClient!

        let rootVC = makeRootViewController(chatClient: chatClient)
        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = rootVC
        window.makeKeyAndVisible()
        self.window = window
    }

    private func makeRootViewController(chatClient: ChatClient) -> UIViewController {
        // Show login if no user is connected yet
        if chatClient.currentUserId == nil {
            let loginVC = LoginViewController(chatClient: chatClient) { [weak self] in
                self?.switchToChannelList(chatClient: chatClient)
            }
            return UINavigationController(rootViewController: loginVC)
        } else {
            return makeChannelListNav(chatClient: chatClient)
        }
    }

    private func makeChannelListNav(chatClient: ChatClient) -> UINavigationController {
        let query = ChannelListQuery(
            filter: .containMembers(userIds: [chatClient.currentUserId ?? ""]),
            sort: [Sorting(key: .lastMessageAt, isAscending: false)]
        )
        let controller = chatClient.channelListController(query: query)
        let channelListVC = ChatChannelListVC.make(with: controller)
        return UINavigationController(rootViewController: channelListVC)
    }

    private func switchToChannelList(chatClient: ChatClient) {
        window?.rootViewController = makeChannelListNav(chatClient: chatClient)
    }
}
```

**Wiring:**
- `chatClient.currentUserId` is non-nil when a user is still connected from a previous session
- `switchToChannelList` replaces the root view controller after login - no navigation push needed

---

## Login View Controller Blueprint

```swift
// LoginViewController.swift
import UIKit
import StreamChat

class LoginViewController: UIViewController {
    private let chatClient: ChatClient
    private let onConnected: () -> Void

    private let userIdField = UITextField()
    private let nameField = UITextField()
    private let connectButton = UIButton(type: .system)
    private let activityIndicator = UIActivityIndicatorView(style: .medium)
    private let errorLabel = UILabel()

    init(chatClient: ChatClient, onConnected: @escaping () -> Void) {
        self.chatClient = chatClient
        self.onConnected = onConnected
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { fatalError() }

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Sign In"
        view.backgroundColor = .systemBackground
        setupLayout()
    }

    private func setupLayout() {
        userIdField.placeholder = "User ID"
        userIdField.borderStyle = .roundedRect
        userIdField.autocorrectionType = .no
        userIdField.autocapitalizationType = .none

        nameField.placeholder = "Display Name"
        nameField.borderStyle = .roundedRect

        connectButton.setTitle("Connect", for: .normal)
        connectButton.addTarget(self, action: #selector(connect), for: .touchUpInside)

        errorLabel.textColor = .systemRed
        errorLabel.font = .systemFont(ofSize: 13)
        errorLabel.numberOfLines = 0

        let stack = UIStackView(arrangedSubviews: [userIdField, nameField, errorLabel, connectButton, activityIndicator])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)

        NSLayoutConstraint.activate([
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            stack.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -24)
        ])
    }

    @objc private func connect() {
        guard let userId = userIdField.text, !userId.isEmpty else { return }
        let name = nameField.text?.isEmpty == false ? nameField.text! : userId

        connectButton.isEnabled = false
        activityIndicator.startAnimating()
        errorLabel.text = nil

        let userInfo = UserInfo(id: userId, name: name)
        let tokenProvider: TokenProvider = { completion in
            // Replace with your backend token endpoint
            guard let url = URL(string: "https://your-backend.com/api/stream-token?user_id=\(userId)") else {
                completion(.failure(NSError(domain: "Token", code: 0)))
                return
            }
            URLSession.shared.dataTask(with: url) { data, _, error in
                if let error {
                    completion(.failure(error))
                    return
                }
                guard let data, let tokenString = String(data: data, encoding: .utf8) else {
                    completion(.failure(NSError(domain: "Token", code: 1)))
                    return
                }
                completion(.success(Token(stringLiteral: tokenString.trimmingCharacters(in: .whitespacesAndNewlines))))
            }.resume()
        }

        chatClient.connectUser(userInfo: userInfo, tokenProvider: tokenProvider) { [weak self] error in
            DispatchQueue.main.async {
                self?.connectButton.isEnabled = true
                self?.activityIndicator.stopAnimating()
                if let error {
                    self?.errorLabel.text = error.localizedDescription
                } else {
                    self?.onConnected()
                }
            }
        }
    }
}
```

---

## Channel List Setup Blueprint

```swift
// ChannelListSetup.swift
import StreamChat
import StreamChatUI

func makeChannelListVC(chatClient: ChatClient) -> UINavigationController {
    let query = ChannelListQuery(
        filter: .containMembers(userIds: [chatClient.currentUserId ?? ""]),
        sort: [Sorting(key: .lastMessageAt, isAscending: false)]
    )
    let controller = chatClient.channelListController(query: query)
    let channelListVC = ChatChannelListVC.make(with: controller)
    channelListVC.title = "Messages"

    return UINavigationController(rootViewController: channelListVC)
}
```

**Wiring:**
- `ChatChannelListVC.make(with:)` wires the controller and delegate correctly. The VC calls `synchronize()` automatically on `viewDidLoad` - do not call it again manually.
- You can also assign via `channelListVC.controller = controller` if you cannot use the factory (e.g. storyboard instantiation)
- Navigation to `ChatMessageListVC` on cell tap is handled by the SDK's built-in `ChatChannelListRouter`
- Always embed `ChatChannelListVC` in a `UINavigationController` - the SDK router pushes message VCs onto it

---

## Custom Appearance Blueprint

Configure `Appearance.default` before any SDK view loads. Call from `AppDelegate.application(_:didFinishLaunchingWithOptions:)` before `ChatClient` initialization.

```swift
import StreamChatUI

func configureAppearance() {
    // Colors
    Appearance.default.colorPalette.accentPrimary = UIColor(named: "BrandPrimary") ?? .systemBlue
    Appearance.default.colorPalette.background = .systemBackground

    // Fonts
    Appearance.default.fonts.body = .systemFont(ofSize: 16)
    Appearance.default.fonts.headline = .boldSystemFont(ofSize: 17)
    Appearance.default.fonts.subheadline = .systemFont(ofSize: 15)

    // Images
    Appearance.default.images.sendButton = UIImage(systemName: "paperplane.fill")!
    Appearance.default.images.close = UIImage(systemName: "xmark")!
}
```

**Wiring:**
- All `Appearance.default` changes are global - they apply to every SDK component automatically
- Changes after the first SDK view has loaded may not take effect
- Verify available property names against [theming docs](https://getstream.io/chat/docs/sdk/ios/uikit/theming/) - do not guess

---

## Custom Channel List Item Blueprint

Subclass `ChatChannelListItemView` and override `updateContent()`. Register with `Components.default` before any SDK view loads.

```swift
import UIKit
import StreamChat
import StreamChatUI

final class CustomChannelListItemView: ChatChannelListItemView {
    private let unreadBadge = UILabel()

    override func setUpLayout() {
        super.setUpLayout()

        unreadBadge.font = .boldSystemFont(ofSize: 12)
        unreadBadge.textColor = .white
        unreadBadge.backgroundColor = .systemBlue
        unreadBadge.textAlignment = .center
        unreadBadge.layer.cornerRadius = 10
        unreadBadge.clipsToBounds = true
        // Add to the view hierarchy as needed
    }

    override func updateContent() {
        super.updateContent()

        let unreadCount = content?.unreadCount.messages ?? 0
        unreadBadge.isHidden = unreadCount == 0
        unreadBadge.text = "\(unreadCount)"
    }
}

// Register in AppDelegate before ChatClient init:
// Components.default.channelContentView = CustomChannelListItemView.self
```

**Wiring:**
- `content` is `ChatChannel?` - access channel properties directly (e.g. `content?.unreadCount`, `content?.name`)
- `updateContent()` is called by the SDK whenever the cell needs to refresh - always call `super.updateContent()` first
- Register via `Components.default.channelContentView` - not `channelCell` (which is the collection cell wrapper)

---

## Custom Channel List Router Blueprint

Subclass `ChatChannelListRouter` to intercept or replace the default navigation from the channel list to the message list.

**Pattern A - navigate to a `ChatMessageListVC` subclass (most common):**

```swift
import UIKit
import StreamChat
import StreamChatUI

final class CustomChannelListRouter: ChatChannelListRouter {
    override func showChannel(for cid: ChannelId) {
        guard let client = rootViewController?.controller.client else { return }
        let vc = CustomMessageListVC()
        vc.channelController = client.channelController(for: cid)
        navigationController?.pushViewController(vc, animated: true)
    }
}

final class CustomMessageListVC: ChatMessageListVC {
    // channelController is inherited - it must be set before the VC is pushed, not after viewDidLoad
    // Override SDK methods as needed
}

// Register in AppDelegate before ChatClient init:
// Components.default.channelListRouter = CustomChannelListRouter.self
```

**Pattern B - navigate to a completely custom `UIViewController`:**

```swift
import UIKit
import StreamChat
import StreamChatUI

final class CustomChannelListRouter: ChatChannelListRouter {
    override func showChannel(for cid: ChannelId) {
        guard let client = rootViewController?.controller.client else { return }
        let vc = MyChannelViewController(cid: cid, client: client)
        navigationController?.pushViewController(vc, animated: true)
    }
}

final class MyChannelViewController: UIViewController {
    private let cid: ChannelId
    private let chatClient: ChatClient

    init(cid: ChannelId, client: ChatClient) {
        self.cid = cid
        self.chatClient = client
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { fatalError() }
}

// Register in AppDelegate before ChatClient init:
// Components.default.channelListRouter = CustomChannelListRouter.self
```

**Wiring:**
- `rootViewController` is typed `ChatChannelListVC?` - `rootViewController?.controller.client` compiles correctly; `client` is a stored `let` property on the controller
- Pattern A: `channelController` is inherited from `ChatMessageListVC` - assign it before the push; the SDK reads it in `viewWillAppear`
- Pattern B: pass `client` and `cid` to your custom VC at init time rather than accessing them later through the router
- Override `showChannel(for cid: ChannelId, at messageId: MessageId?)` to also handle deep-links to specific messages
- The router is instantiated by the SDK - do not create it manually
- Other overridable methods: `showCurrentUserProfile()`, `didTapMoreButton(for:)`, `didTapDeleteButton(for:)`

---

## Custom Message Content Blueprint

Subclass `ChatMessageContentView` to customize the message bubble layout.

```swift
import UIKit
import StreamChat
import StreamChatUI

final class CustomMessageContentView: ChatMessageContentView {
    override func updateContent() {
        super.updateContent()
        // Access `content` (a ChatMessage?) for the current message
        // Modify sub-views as needed
        textView?.textColor = content?.isSentByCurrentUser == true ? .white : .label
    }
}

// Register in AppDelegate before ChatClient init:
// Components.default.messageContentView = CustomMessageContentView.self
```

**Wiring:**
- `content` is the `ChatMessage?` for this view - always guard for nil
- `isSentByCurrentUser` is a convenience property on `ChatMessage`
- Call `super.updateContent()` first to let the SDK set base state, then apply your overrides

---

## Logout Blueprint

```swift
import UIKit
import StreamChat

func logout(chatClient: ChatClient, completion: @escaping () -> Void) {
    chatClient.logout {
        DispatchQueue.main.async {
            completion()
        }
    }
}

// Usage - switch to login screen after logout:
logout(chatClient: chatClient) { [weak self] in
    let loginVC = LoginViewController(chatClient: chatClient) {
        // reconnect flow
    }
    self?.window?.rootViewController = UINavigationController(rootViewController: loginVC)
}
```

**Wiring:**
- `logout` completion fires on a background thread - always dispatch UI work to main
- Do not call `connectUser` inside `logout`'s closure: wait for `logout` to complete first, then call connect in the `completion` block
