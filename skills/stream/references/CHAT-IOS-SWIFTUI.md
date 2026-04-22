# Chat iOS — SwiftUI SDK Setup & Integration

Stream Chat iOS (SwiftUI) provides pre-built SwiftUI components for building rich messaging UIs. This file covers package installation, client setup, authentication, customization, and gotchas. For view blueprints, see [CHAT-IOS-SWIFTUI-blueprints.md](CHAT-IOS-SWIFTUI-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper logout).

- **Blueprint** — SwiftUI view structure and initialization
- **Wiring** — SDK calls for each component, exact property paths
- **Requirements** — Info.plist keys, SDK version, Xcode version

## Quick ref

- **Package (SwiftUI):** `StreamChatSwiftUI` via SPM — `https://github.com/getstream/stream-chat-swiftui`
- **Package (core only):** `StreamChat` via SPM — `https://github.com/getstream/stream-chat-swift`
- **First:** Installation → Info.plist → Client init → Connect user → Show views
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen

Full view blueprints: [CHAT-IOS-SWIFTUI-blueprints.md](CHAT-IOS-SWIFTUI-blueprints.md) — load only the section you are implementing.

---

## App Integration

### Installation (Swift Package Manager)

1. In Xcode: **File → Add Package Dependencies...**
2. Paste URL: `https://github.com/getstream/stream-chat-swiftui`
3. Select target: **`StreamChatSwiftUI`** — this includes the `StreamChat` core automatically
4. Add required `Info.plist` keys:

```xml
<key>NSPhotoLibraryUsageDescription</key>
<string>$(PRODUCT_NAME) needs access to your photo library to send images.</string>
<key>NSPhotoLibraryAddUsageDescription</key>
<string>$(PRODUCT_NAME) needs access to save photos to your library.</string>
<key>NSCameraUsageDescription</key>
<string>$(PRODUCT_NAME) needs access to your camera to send photos and videos.</string>
```

### Client Initialization

Initialize once at app launch. **Never** create `ChatClient` in a SwiftUI `View` body or computed property — doing so creates a new instance on every redraw.

Two equally valid patterns — pick one:

**Option A — App struct `init()` (pure SwiftUI, no UIKit dependency):**

```swift
import StreamChat
import StreamChatSwiftUI

@main
struct MyApp: App {
    @State private var streamChat: StreamChat

    init() {
        let config = ChatClientConfig(apiKey: .init("your_api_key"))
        let chatClient = ChatClient(config: config)
        _streamChat = State(wrappedValue: StreamChat(chatClient: chatClient))
    }

    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}
```

`@State` is required — `App` is a value type and SwiftUI can recreate it; `@State` ensures the `StreamChat` instance survives those re-creations. A plain `let` or `var` would be re-initialized. Use `_streamChat = State(wrappedValue:)` to initialize a `@State` property from `init()`.

**Option B — `AppDelegate` (required when you also need other `UIApplicationDelegate` callbacks):**

```swift
import StreamChat
import StreamChatSwiftUI

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
    var streamChat: StreamChat?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        let config = ChatClientConfig(apiKey: .init("your_api_key"))
        let chatClient = ChatClient(config: config)
        streamChat = StreamChat(chatClient: chatClient)
        return true
    }
}
```

Use Option B when the app needs `UIApplicationDelegate` callbacks for push notifications (`didRegisterForRemoteNotificationsWithDeviceToken`), background tasks, or URL handling.

`StreamChat` (the wrapper type from `StreamChatSwiftUI`) **must** be initialized before any SDK view renders. Rendering a view without it causes a `fatalError` crash.

### User Authentication

**Default — hardcoded token (no expiry):**

Ask the user for their Stream token from the [Stream Dashboard](https://dashboard.getstream.io) (User Explorer → generate token). Access the client via `@Injected(\.chatClient)` in any view or call it where you have a `chatClient` reference:

```swift
@Injected(\.chatClient) private var chatClient

let userInfo = UserInfo(
    id: "user-id",
    name: "User Name",
    imageURL: nil
)

let token = Token(stringLiteral: "your_static_token_here")
chatClient.connectUser(userInfo: userInfo, token: token) { error in
    if let error { print("Connect failed: \(error)") }
}
```

**Token provider (expiring tokens — use only if the user asks for it):**

Use this when the user has a backend endpoint that issues Stream JWTs. The provider is called automatically when the token expires:

```swift
@Injected(\.chatClient) private var chatClient

let userInfo = UserInfo(
    id: currentUser.id,
    name: currentUser.name,
    imageURL: currentUser.avatarURL
)

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

### Disconnect and Logout

```swift
@Injected(\.chatClient) private var chatClient

// Temporarily pause updates (e.g. user navigates away from chat section)
chatClient.disconnect { error in /* handle */ }

// Full logout — clears offline storage. WAIT for the callback before any other action.
chatClient.logout {
    // Safe to log in a different user only AFTER this fires
}
```

### Creating Channels

```swift
@Injected(\.chatClient) private var chatClient

let channelId = ChannelId(type: .messaging, id: UUID().uuidString)
let controller = try chatClient.channelController(
    createChannelWithId: channelId,
    name: "General",
    members: [currentUserId, otherUserId]
)
controller.synchronize { error in
    if let error { print("Channel sync failed: \(error)") }
}
```

### Showing the Channel List

```swift
struct ContentView: View {
    var body: some View {
        ChatChannelListView(title: "Messages")
    }
}
```

`ChatChannelListView` includes its own `NavigationView` — never wrap it in `NavigationView` or `NavigationStack`. Set the title via the `title` parameter in the initializer. Navigation to individual channel views is handled automatically.

---

## Client Patterns

### Controller Management

**Create controllers as `@State` variables — never as computed properties.**

Each SwiftUI redraw creates a new controller instance from a computed var, causing unpredictable state and re-fetches.

```swift
@Injected(\.chatClient) private var chatClient

// Wrong — new instance on every redraw
var channelListController: ChatChannelListController {
    chatClient.channelListController(query: .init(...))
}

// Correct — single stable instance
@State private var channelListController: ChatChannelListController?

.task {
    guard let userId = chatClient.currentUserId else { return }
    channelListController = chatClient.channelListController(
        query: .init(
            filter: .containMembers(userIds: [userId]),
            sort: [.init(key: .lastMessageAt, isAscending: false)]
        )
    )
}
```

Pass the controller to `ChatChannelListView(channelListController:)` once created.

### Dependency Injection

Access SDK instances in custom SwiftUI views without prop-drilling:

```swift
import StreamChatSwiftUI

struct CustomView: View {
    @Injected(\.chatClient) var chatClient
    @Injected(\.fonts) var fonts
    @Injected(\.colors) var colors
    @Injected(\.images) var images

    var body: some View { /* ... */ }
}
```

---

## ChatClientConfig Options

All config changes must happen before `ChatClient(config:)` is called.

```swift
var config = ChatClientConfig(apiKey: .init("your_api_key"))

// Offline support (all enabled by default)
config.isLocalStorageEnabled = true
config.queuedActionsMaxHoursThreshold = 12      // retain queued offline actions for N hours
config.isAutomaticSyncOnReconnectEnabled = true  // auto-sync missed events on reconnect
config.staysConnectedInBackground = true         // stay connected up to 5 min when backgrounded

// Required if you add a Notification Service Extension
config.applicationGroupIdentifier = "group.com.yourcompany.yourapp"

let chatClient = ChatClient(config: config)
```

Offline-queueable actions: send/edit/delete messages, add/remove reactions, pin/unpin messages, save drafts.

**Simulator note:** Reconnection after backgrounding is unreliable on the iOS Simulator — test offline behavior on a real device.

---

## State Layer (async/await API)

The state layer is the modern alternative to controllers and delegates. All objects expose `@Published` properties for SwiftUI reactivity, and mutations are `async`/`await`.

**Channel state and messaging:**

```swift
let chat = chatClient.makeChat(for: ChannelId(type: .messaging, id: "general"))

try await chat.get(watch: true)          // load latest state + subscribe to real-time updates
let messages = chat.state.messages
let members  = chat.state.members

try await chat.sendMessage(with: "Hello!")
try await chat.loadOlderMessages()       // pagination
try await chat.sendReaction(to: messageId, with: "like", score: 1, enforceUnique: true)
try await chat.deleteReaction(from: messageId, with: "like")
```

**Reply to a message:**

```swift
try await chat.reply(to: parentMessageId, text: "Got it!", showReplyInChannel: true)
```

**Channel list with pagination:**

```swift
let query = ChannelListQuery(
    filter: .containMembers(userIds: [currentUserId]),
    sort: [Sorting(key: .lastMessageAt, isAscending: false)],
    pageSize: 20
)
let channelList = chatClient.makeChannelList(with: query)
try await channelList.get()
let channels = channelList.state.channels
try await channelList.loadMoreChannels()
```

**Observe state changes in SwiftUI:**

```swift
channelList.state.$channels
    .sink { channels in /* update UI */ }
    .store(in: &cancellables)
```

**Other state objects** (all follow the same `make*` → `get()` → `loadMore*()` → `.state.*` pattern):
`MemberList`, `MessageSearch`, `ReactionList`, `UserList`, `UserSearch`, `ConnectedUser`.

**User-level actions via `ConnectedUser`:**

```swift
let connectedUser = try chatClient.makeConnectedUser()
try await connectedUser.muteUser("user-id")
try await connectedUser.blockUser("user-id")
try await connectedUser.markAllChannelsRead()
let unread = connectedUser.state.user.unreadCount
```

---

## Event Listening

Store the returned `AnyCancellable` — releasing it cancels the subscription.

```swift
// All events
chatClient.subscribe { event in print(event) }
    .store(in: &cancellables)

// Specific event type
chatClient.subscribe(toEvent: ConnectionStatusUpdated.self) { event in }
    .store(in: &cancellables)

// Scoped to a channel
let chat = chatClient.makeChat(for: channelId)
chat.subscribe { event in }
    .store(in: &cancellables)

chat.subscribe(toEvent: ChannelHiddenEvent.self) { event in }
    .store(in: &cancellables)
```

---

## Push Notifications

Push notifications require `UIApplicationDelegate` — use the AppDelegate entry point (Option B) when enabling push.

**Xcode capabilities:** Add `Push Notifications` and `Background Modes → Remote notifications`.

**Stream Dashboard:** Push Notifications → New Configuration → APN → fill bundle ID, team ID, key ID, `.p8` token.

**Request permission and register** (call inside `connectUser` completion):

```swift
UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
    guard granted else { return }
    DispatchQueue.main.async { UIApplication.shared.registerForRemoteNotifications() }
}
```

**Register device token** (in `AppDelegate`):

```swift
func application(_ application: UIApplication,
                 didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    guard chatClient.currentUserId != nil else { return }
    chatClient.currentUserController().addDevice(.apn(token: deviceToken)) { error in
        if let error { log.warning("Adding device failed: \(error)") }
    }
}
```

For multi-bundle setups (dev/prod), pass `providerName` matching the Dashboard configuration name:
```swift
.addDevice(.apn(token: deviceToken, providerName: "MyApp-Production"))
```

**Remove token on logout** (prevents notifications to logged-out devices):

```swift
if let deviceId = chatClient.currentUserController().currentUser?.devices.last?.id {
    chatClient.currentUserController().removeDevice(id: deviceId) { _ in }
}
```

**Handle notification taps** (implement `UNUserNotificationCenterDelegate`):

```swift
func userNotificationCenter(_ center: UNUserNotificationCenter,
                             didReceive response: UNNotificationResponse,
                             withCompletionHandler completionHandler: @escaping () -> Void) {
    defer { completionHandler() }
    guard let info = try? ChatPushNotificationInfo(content: response.notification.request.content),
          let cid = info.cid else { return }
    // Navigate to the channel — see blueprints for the full pattern
    navigateToChannel(cid)
}
```

Set `UNUserNotificationCenter.current().delegate` in `AppDelegate.application(_:didFinishLaunchingWithOptions:)`.

**Notification Service Extension** (enrich notifications before display; requires App Groups):

```swift
// Info.plist: add applicationGroupIdentifier to both app and extension targets
// ChatClientConfig: config.applicationGroupIdentifier = "group.com.yourcompany.yourapp"

class NotificationService: UNNotificationServiceExtension {
    var contentHandler: ((UNNotificationContent) -> Void)?

    override func didReceive(_ request: UNNotificationRequest,
                             withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void) {
        self.contentHandler = contentHandler
        guard let content = request.content.mutableCopy() as? UNMutableNotificationContent else {
            return contentHandler(request.content)
        }
        var config = ChatClientConfig(apiKey: .init("your_api_key"))
        config.applicationGroupIdentifier = "group.com.yourcompany.yourapp"
        let client = ChatClient(config: config)
        client.setToken(token: "<# User Token #>")
        _ = ChatRemoteNotificationHandler(client: client, content: content)
            .handleNotification { chatContent in
                if case let .message(n) = chatContent {
                    content.title = n.message.author.name ?? ""
                    content.subtitle = n.message.text
                }
                contentHandler(content)
            }
    }

    override func serviceExtensionTimeWillExpire() {
        if let handler = contentHandler,
           let content = request?.content.mutableCopy() as? UNMutableNotificationContent {
            handler(content)
        }
    }
}
```

---

## Extra Data

Attach arbitrary `[String: RawJSON]` to users, messages, and channels.

**Set extra data:**

```swift
// On the current user
chatClient.currentUserController().updateUserData(
    name: "John",
    imageURL: nil,
    userExtraData: ["email": .string("john@example.com"), "isPremium": .bool(true)]
)

// On a new message
channelController.createNewMessage(
    text: "Here's your ticket",
    extraData: ["ticketId": .string("abc-123"), "price": .double(20.0)]
)
```

**Read extra data:**

```swift
let email    = user.extraData["email"]?.stringValue
let premium  = user.extraData["isPremium"]?.boolValue
let ticketId = message.extraData["ticketId"]?.stringValue

// Nested
let meta  = message.extraData["metadata"]?.dictionaryValue
let value = meta?["key"]?.stringValue
```

Accessors: `stringValue`, `numberValue`, `boolValue`, `dictionaryValue`, `arrayValue`, `stringArrayValue`, `numberArrayValue`, `boolArrayValue`.

**Clean-access pattern:**

```swift
extension ChatUser {
    var email: String? { extraData["email"]?.stringValue }
    var isPremium: Bool { extraData["isPremium"]?.boolValue ?? false }
}
```

---

## Polls

Polls are **disabled by default** — enable in Stream Dashboard → your app → channel type → Polls.

**Configure poll creation UI:**

```swift
let pollsConfig = PollsConfig(
    multipleAnswers: PollsEntryConfig(configurable: true, defaultValue: false),
    anonymousPoll: .default,
    suggestAnOption: PollsEntryConfig(configurable: false, defaultValue: false),
    addComments: .default,
    maxVotesPerPerson: .default
)
streamChat = StreamChat(chatClient: chatClient, utils: Utils(pollsConfig: pollsConfig))
```

**Create a poll:**

```swift
channelController.createPoll(
    name: "Favourite language?",
    allowAnswers: true,
    allowUserSuggestedOptions: false,
    enforceUniqueVote: true,
    maxVotesAllowed: nil,
    votingVisibility: .public,
    options: [.init(text: "Swift"), .init(text: "Kotlin"), .init(text: "Rust")]
) { result in /* handle */ }
```

**Vote, comment, close:**

```swift
let ctrl = chatClient.pollController(messageId: message.id, pollId: poll.id)
ctrl.castPollVote(answerText: nil, optionId: option.id) { _ in }  // vote
ctrl.castPollVote(answerText: "Great idea!", optionId: nil) { _ in }  // comment
ctrl.removePollVote(voteId: vote.id) { _ in }
ctrl.closePoll { _ in }
```

---

## Logging

Disabled by default. Enable before `ChatClient` initialization, ideally only in debug builds.

```swift
#if DEBUG
LogConfig.level = .debug
LogConfig.subsystems = [.httpRequests, .webSocket]  // start here; broaden as needed
#endif
```

Levels: `.debug`, `.info`, `.warning`, `.error`.
Subsystems: `.all`, `.database`, `.httpRequests`, `.webSocket`, `.offlineSupport`, `.authentication`, `.audioPlayback`, `.audioRecording`, `.other`.

---

## Customization

### Appearance (colors, fonts, images)

Build the `Appearance` object before passing it to `StreamChat`. All changes propagate to every SDK component automatically.

```swift
var colors = Appearance.ColorPalette()
colors.accentPrimary = UIColor.systemBlue
colors.navigationBarTintColor = UIColor.systemBlue
colors.chatBackgroundOutgoing = UIColor.systemBlue.withAlphaComponent(0.15)

var fonts = Appearance.FontsSwiftUI()
fonts.body = .system(size: 16, weight: .regular)

var images = Appearance.Images()
images.composerSend = UIImage(systemName: "paperplane.fill")!

var appearance = Appearance()
appearance.colorPalette = colors
appearance.fontsSwiftUI = fonts
appearance.images = images

streamChat = StreamChat(chatClient: chatClient, appearance: appearance)
```

Key color token groups: accent, elevation, surface, text, border, avatar, badge, chat bubble, reaction, navigation.

### Channel Name Formatting

```swift
final class CustomChannelNameFormatter: ChannelNameFormatter {
    func format(channel: ChatChannel, forCurrentUserId currentUserId: UserId?) -> String? {
        channel.name ?? channel.lastActiveMembers
            .map { $0.name ?? $0.id }
            .joined(separator: ", ")
    }
}

let utils = Utils(channelNameFormatter: CustomChannelNameFormatter())
streamChat = StreamChat(chatClient: chatClient, utils: utils)
```

### View Customization (ViewFactory)

The `ViewFactory` protocol defines every swappable view slot in the SDK — channel list items, message bubbles, composer, avatars, reactions, attachments, and more. Create a singleton factory subclass, override only the slots you need, and pass it to your root view. All unoverridden slots fall back to the SDK defaults.

**Minimal custom factory:**

```swift
class CustomFactory: ViewFactory {
    @Injected(\.chatClient) public var chatClient
    public static let shared = CustomFactory()
    private init() {}

    // Override only the slots you need
    func makeUserAvatarView(options: UserAvatarViewOptions) -> some View {
        CustomUserAvatarView(user: options.user, size: options.size)
    }
}
```

**Inject into the root view:**

```swift
ChatChannelListView(viewFactory: CustomFactory.shared)
```

**Customizable slot categories:**

| Category | Slots | Examples |
|---|---|---|
| Avatars | 2 | Channel avatar, user avatar |
| Channel list | 11 | Header, items, empty state, loading, swipe actions, footer |
| Messages | 30+ | Text, attachments (image, video, file, Giphy, link), reactions, threads, system messages |
| Composer | 15+ | Input field, send button, attachment picker, voice recording, suggestions |
| Reactions & actions | 7 | Message actions popup, reaction details, read indicators |
| Thread list | 8 | Items, empty/loading states, header, footer |

**Styles — Regular vs Liquid Glass:**

```swift
class CustomFactory: ViewFactory {
    @Injected(\.chatClient) public var chatClient
    public static let shared = CustomFactory()
    private init() {}

    public var styles: some Styles { LiquidGlassStyles() } // iOS 26 floating composer
    // Default: RegularStyles() — docked bottom composer
}
```

**Extend the injection system with custom types:**

```swift
struct AnalyticsServiceKey: InjectionKey {
    static var currentValue: AnalyticsService = AnalyticsService()
}

extension InjectedValues {
    var analytics: AnalyticsService {
        get { Self[AnalyticsServiceKey.self] }
        set { Self[AnalyticsServiceKey.self] = newValue }
    }
}

// Access anywhere alongside SDK injectables:
@Injected(\.analytics) var analytics
```

**Build time tip:** When overriding 15+ slots, add explicit `typealias` return type declarations to reduce generic inference compile time:

```swift
typealias EmptyChannels = CustomEmptyChannelsView

public func makeEmptyChannelsView(options: EmptyChannelsViewOptions) -> CustomEmptyChannelsView {
    CustomEmptyChannelsView()
}
```

For concrete view code, see [CHAT-IOS-SWIFTUI-blueprints.md § ViewFactory Blueprints](CHAT-IOS-SWIFTUI-blueprints.md).

### Channel List Swipe Actions

Extend the default actions (leave, mute/unmute, delete) via `ChannelListConfig` without replacing the whole sheet:

```swift
let channelListConfig = ChannelListConfig(
    supportedMoreChannelActions: { options in
        var actions = ChannelAction.defaultActions(for: options)
        let freeze: @MainActor () -> Void = {
            InjectedValues[\.chatClient]
                .channelController(for: options.channel.cid)
                .freezeChannel { error in
                    error == nil ? options.onDismiss() : options.onError(error!)
                }
        }
        actions.insert(
            ChannelAction(
                title: "Freeze",
                iconName: "snowflake",
                action: freeze,
                confirmationPopup: ConfirmationPopup(
                    title: "Freeze channel",
                    message: "Are you sure?",
                    buttonTitle: "Freeze"
                ),
                isDestructive: false
            ),
            at: 0
        )
        return actions
    }
)
streamChat = StreamChat(chatClient: chatClient, utils: Utils(channelListConfig: channelListConfig))
```

To replace the sheet entirely, implement `makeMoreChannelActionsView` in your `ViewFactory`.

### Message Display Options

Configure per-message appearance via `MessageDisplayOptions` → `MessageListConfig` → `Utils`:

```swift
let messageDisplayOptions = MessageDisplayOptions(
    showIncomingMessageAvatar: true,
    showOutgoingMessageAvatar: false,
    showMessageDate: true,
    showAuthorName: true,
    animateChanges: true,
    shouldAnimateReactions: true,
    reactionsPlacement: .top        // .top or .bottom
)
streamChat = StreamChat(
    chatClient: chatClient,
    utils: Utils(messageListConfig: MessageListConfig(messageDisplayOptions: messageDisplayOptions))
)
```

Key toggles: `showIncomingMessageAvatar`, `showOutgoingMessageAvatar`, `showAvatarsInGroups`, `showMessageDate`, `showAuthorName`, `animateChanges`, `shouldAnimateReactions`, `showOriginalTranslatedButton`.
Layout: `reactionsPlacement`, `minimumSwipeGestureDistance`, `newMessagesSeparatorSize`.
Closures: `dateSeparator`, `spacerWidth`, `messageLinkDisplayResolver`, `reactionsTopPadding`.

### Channel List Tap Handling

Override navigation destination or intercept taps without replacing the channel list:

```swift
// Custom destination view
class CustomFactory: ViewFactory {
    func makeChannelDestination(options: ChannelDestinationOptions) -> @MainActor (ChannelSelectionInfo) -> CustomChannelDestination {
        { info in CustomChannelDestination(channel: info.channel) }
    }
}

// Intercept taps (no navigation — run your own logic)
ChatChannelListView(viewFactory: CustomFactory.shared) { channel in
    print("Tapped: \(channel.name ?? "")")
}

// Deep-link directly to a channel (e.g. from a push notification)
ChatChannelListView(viewFactory: CustomFactory.shared, selectedChannelId: cid.rawValue)

// Use your own NavigationView/NavigationStack — opt out of the SDK's built-in one
// and pass title via the title parameter
NavigationStack {
    ChatChannelListView(
        viewFactory: CustomFactory.shared,
        title: "Messages",
        embedInNavigationView: false
    )
}
```

---

## Gotchas

- **Never use dev tokens in production.** `devToken()` disables token auth and allows any client to impersonate any user.
- **Never store your Stream secret in the app.** Secrets on-device can be extracted from jailbroken devices and enable destructive actions on your app instance.
- **Always wait for `logout` completion before connecting another user.** The SDK uses persistent storage for offline support and optimistic updates. Connecting a new user while logout is in progress risks state corruption and crashes.
- **`StreamChat` must be initialized before any view renders.** Accessing SDK views before setup causes an immediate `fatalError`.
- **Never use `ChatClient.shared`.** Access the client via `@Injected(\.chatClient)` in views. The SDK registers the instance automatically when `StreamChat(chatClient:)` is initialized.
- **Import both `StreamChat` and `StreamChatSwiftUI` in every file that uses either module.** `ChatClient`, `UserInfo`, `Token`, and all controllers live in `StreamChat`; SwiftUI views and the `StreamChat` wrapper type live in `StreamChatSwiftUI`. Missing `import StreamChat` causes compile errors when accessing the client or creating controllers.
- **Never wrap `ChatChannelListView` in `NavigationView` or `NavigationStack`.** It includes its own built-in `NavigationView`. Set the navigation bar title via the `title` parameter in its initializer. If you must embed it in your own navigation container, set `embedInNavigationView: false` — and still pass `title` via the initializer, not `.navigationTitle()`.
- **Controllers are stateful — store them as `@State` or in an `@ObservableObject`**, not computed vars. Computed vars create new instances on every SwiftUI redraw.
- **The token provider is called automatically on expiry.** You do not need to call `connectUser` again — implement the provider closure correctly and the SDK handles refresh.
- **`channel("livestream", id)` takes no third argument in v5+.** Passing `{ name }` as a third parameter causes a compile error.
