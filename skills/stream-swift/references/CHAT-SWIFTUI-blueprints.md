# Chat SwiftUI - View Blueprints

Load only the section you are implementing. For setup, client initialization, and gotchas, see [CHAT-SWIFTUI.md](CHAT-SWIFTUI.md).

---

## ChatService.swift Blueprint (Combined Chat + Video Apps)

Use this pattern when the app also integrates `StreamVideo`. `ViewFactory`, `@Injected`, `InjectionKey`, and `InjectedValues` collide between `StreamChatSwiftUI` and `StreamVideoSwiftUI` - file isolation is required. See [`COMBINED-CHAT-VIDEO.md`](COMBINED-CHAT-VIDEO.md) for the full collision table and UIKit patterns.

```swift
// ChatService.swift
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

Call from the app entry point - which imports **neither** Stream SDK:

```swift
// MyApp.swift - no Stream imports here
@main
struct MyApp: App {
    init() {
        ChatService.shared.setUp(
            apiKey: "your_api_key",
            userId: "alice",
            userName: "Alice",
            token: "your_chat_token"
        )
        // VideoService.shared.setUp(...) in VideoService.swift
    }

    var body: some Scene {
        WindowGroup { RootView() }
    }
}
```

---

## App Entry Point Blueprint

Two patterns - pick one. Appearance customization must happen before `StreamChat` is initialized in either case.

### Option A - App struct `init()` (pure SwiftUI)

Preferred for apps that don't need `UIApplicationDelegate` callbacks.

```swift
import SwiftUI
import StreamChat
import StreamChatSwiftUI

@main
struct StreamChatApp: App {
    @State private var streamChat: StreamChat

    init() {
        let config = ChatClientConfig(apiKey: .init("your_api_key"))
        let chatClient = ChatClient(config: config)
        let appearance = AppearanceProvider.make()
        _streamChat = State(wrappedValue: StreamChat(chatClient: chatClient, appearance: appearance))
    }

    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}
```

### Option B - `AppDelegate` (required for push notifications, background tasks, URL handling)

```swift
import SwiftUI
import StreamChat
import StreamChatSwiftUI

@main
struct StreamChatApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            RootView()
        }
    }
}

class AppDelegate: NSObject, UIApplicationDelegate {
    var streamChat: StreamChat?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        let config = ChatClientConfig(apiKey: .init("your_api_key"))
        let chatClient = ChatClient(config: config)
        let appearance = AppearanceProvider.make()
        streamChat = StreamChat(chatClient: chatClient, appearance: appearance)
        return true
    }
}
```

**Wiring (both options):**
- Option A: `@State` is required - `App` is a value type and SwiftUI can recreate it; `@State` pins the instance across re-creations. A plain `let`/`var` would be re-initialized. Initialize via `_streamChat = State(wrappedValue:)` from `init()`.
- Option B: `StreamChat` is stored on `AppDelegate` (`var streamChat: StreamChat?`) - `AppDelegate` is a reference type with UIKit-managed lifetime, so a plain `var` is fine there.
- `ChatClient` and `StreamChat` are initialized once and never recreated
- `Appearance` must be passed at `StreamChat` init time - not settable afterward

---

## Login / Connect User Blueprint

Show a login screen before connecting. Invoke `connectUser` once per user session, not on every view appear.

```swift
struct LoginView: View {
    @Injected(\.chatClient) private var chatClient
    @State private var userId = ""
    @State private var name = ""
    @State private var isConnecting = false
    @State private var connectError: String?
    var onConnected: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Text("Sign In")
                .font(.largeTitle).bold()
            TextField("User ID", text: $userId)
                .textFieldStyle(.roundedBorder)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.never)
            TextField("Display Name", text: $name)
                .textFieldStyle(.roundedBorder)
            if let error = connectError {
                Text(error).foregroundStyle(.red).font(.caption)
            }
            Button {
                connect()
            } label: {
                Group {
                    if isConnecting {
                        ProgressView()
                    } else {
                        Text("Connect")
                    }
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(userId.isEmpty || isConnecting)
        }
        .padding()
    }

    private func connect() {
        isConnecting = true
        connectError = nil
        let userInfo = UserInfo(id: userId, name: name.isEmpty ? userId : name)
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
        chatClient.connectUser(userInfo: userInfo, tokenProvider: tokenProvider) { error in
            DispatchQueue.main.async {
                isConnecting = false
                if let error {
                    connectError = error.localizedDescription
                } else {
                    onConnected()
                }
            }
        }
    }
}
```

**Wiring:**
- `TokenProvider` closure is called by the SDK on initial connect and on every token expiry
- `chatClient.connectUser` is async via callback - update UI on `DispatchQueue.main`
- Backend endpoint must return a plain JWT string (or JSON with a `token` field - parse accordingly)

---

## Root Navigation Blueprint

Gates the app on login state. Skips login if the user is already connected (e.g. token still valid from last session).

```swift
struct RootView: View {
    @Injected(\.chatClient) private var chatClient
    @State private var isConnected = false

    var body: some View {
        Group {
            if isConnected {
                ChannelListScreen()
            } else {
                LoginView {
                    isConnected = true
                }
            }
        }
        .onAppear {
            // Skip login if SDK already has a connected user
            isConnected = chatClient.currentUserId != nil
        }
    }
}
```

**Wiring:**
- `chatClient.currentUserId` is non-nil when a user is connected (persists across foreground/background)
- `LoginView.onConnected` callback sets `isConnected = true` to trigger navigation

---

## Channel List Blueprint

### Default channel list (all channels the user is a member of)

```swift
struct ChannelListScreen: View {
    var body: some View {
        ChatChannelListView(title: "Messages")
    }
}
```

### Filtered and sorted channel list

```swift
struct ChannelListScreen: View {
    @State private var controller: ChatChannelListController?
    @Injected(\.chatClient) private var chatClient

    var body: some View {
        ChatChannelListView(channelListController: controller, title: "Messages")
            .task {
                guard let userId = chatClient.currentUserId else { return }
                controller = chatClient.channelListController(
                    query: .init(
                        filter: .containMembers(userIds: [userId]),
                        sort: [.init(key: .lastMessageAt, isAscending: false)]
                    )
                )
            }
    }
}
```

**Wiring:**
- `ChatChannelListView()` with no arguments uses the default query (all channels the current user is a member of)
- The `title` parameter in `ChatChannelListView` sets the navigation bar title - do **not** use `.navigationTitle()` or wrap in `NavigationView`
- `ChatChannelListView` includes its own `NavigationView` - never wrap it in another one
- `channelListController` must be created as `@State` - not a computed property - to avoid re-creation on redraws
- Navigation from the channel list into a channel view is handled by `ChatChannelListView` automatically

---

## Channel (Message List) Blueprint

Navigation from `ChatChannelListView` to a channel is automatic. For manual or deep-link navigation:

```swift
struct ChannelScreen: View {
    @Injected(\.chatClient) private var chatClient
    let channelId: ChannelId

    var body: some View {
        ChatChannelView(
            viewFactory: DefaultViewFactory.shared,
            channelController: chatClient.channelController(for: channelId)
        )
    }
}
```

**Deep-link example** (navigate to a specific channel by ID):

```swift
// From RootView or a coordinator:
NavigationLink(destination: ChannelScreen(channelId: ChannelId(type: .messaging, id: "general"))) {
    Text("Go to General")
}
```

**Wiring:**
- `DefaultViewFactory.shared` provides the default message, header, and composer implementations
- Substitute a custom `ViewFactory` conformance to swap individual sub-views

---

## Custom Appearance Blueprint

Build and apply appearance once in `AppDelegate` before `StreamChat` initialization.

```swift
enum AppearanceProvider {
    static func make() -> Appearance {
        var colors = Appearance.ColorPalette()
        colors.accentPrimary = UIColor(named: "BrandPrimary") ?? .systemBlue
        colors.navigationBarTintColor = UIColor(named: "BrandPrimary") ?? .systemBlue
        // Outgoing bubble tint
        colors.chatBackgroundOutgoing = (UIColor(named: "BrandPrimary") ?? .systemBlue).withAlphaComponent(0.12)

        var fonts = Appearance.FontsSwiftUI()
        fonts.body = .system(size: 16, weight: .regular, design: .default)
        fonts.headline = .system(size: 17, weight: .semibold)

        var images = Appearance.Images()
        images.composerSend = UIImage(systemName: "paperplane.fill")!
        images.close = UIImage(systemName: "xmark")!

        var appearance = Appearance()
        appearance.colorPalette = colors
        appearance.fontsSwiftUI = fonts
        appearance.images = images
        return appearance
    }
}
```

**Wiring:**
- `Appearance.ColorPalette()` - all semantic color tokens (accent, surface, text, border, chat, reaction, nav)
- `Appearance.FontsSwiftUI()` - SwiftUI `Font` values for body, caption, headline, footnote
- `Appearance.Images()` - `UIImage` overrides for composer icons, navigation icons, etc.
- Pass to `StreamChat(chatClient: chatClient, appearance: appearance)` - not settable after init

---

## ViewFactory Blueprints

Pass your factory to every root SDK view: `ChatChannelListView(viewFactory: CustomFactory.shared)` and `ChatChannelView(viewFactory: CustomFactory.shared, ...)`. A singleton pattern prevents multiple instances.

### Minimal factory scaffold

```swift
import StreamChatSwiftUI

class CustomFactory: ViewFactory {
    @Injected(\.chatClient) public var chatClient
    public static let shared = CustomFactory()
    private init() {}

    // Add overrides below - all unoverridden slots use SDK defaults
}
```

---

### Custom User Avatar Blueprint

```swift
struct CustomUserAvatarView: View {
    let user: ChatUser
    let size: CGSize

    var body: some View {
        AsyncImage(url: user.imageURL) { image in
            image.resizable().scaledToFill()
        } placeholder: {
            Circle()
                .fill(Color.gray.opacity(0.3))
                .overlay(
                    Text(user.name?.prefix(1).uppercased() ?? "?")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                )
        }
        .frame(width: size.width, height: size.height)
        .clipShape(Circle())
    }
}

// Register in the factory:
extension CustomFactory {
    func makeUserAvatarView(options: UserAvatarViewOptions) -> some View {
        CustomUserAvatarView(user: options.user, size: options.size)
    }
}
```

---

### Custom Channel List Item Blueprint

```swift
struct CustomChannelListItemView: View {
    let channel: ChatChannel
    let currentUserId: UserId?

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 4) {
                Text(channel.name ?? "Channel")
                    .font(.headline)
                if let latest = channel.latestMessages.first {
                    Text(latest.text)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                if let date = channel.lastMessageAt {
                    Text(date, style: .time)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
                if channel.unreadCount.messages > 0 {
                    Text("\(channel.unreadCount.messages)")
                        .font(.caption2.bold())
                        .foregroundStyle(.white)
                        .padding(6)
                        .background(Color.accentColor, in: Circle())
                }
            }
        }
        .padding(.vertical, 8)
    }
}

// Register in the factory:
extension CustomFactory {
    func makeChannelListItemView(options: ChannelListItemViewOptions) -> some View {
        CustomChannelListItemView(
            channel: options.channel,
            currentUserId: chatClient.currentUserId
        )
    }
}
```

---

### Custom Channel List Header Blueprint

```swift
struct CustomChannelListHeaderView: View {
    @Injected(\.chatClient) var chatClient

    var body: some View {
        HStack {
            Text("Messages")
                .font(.largeTitle.bold())
            Spacer()
            if let user = chatClient.currentUserController().currentUser {
                AsyncImage(url: user.imageURL) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    Circle().fill(Color.gray.opacity(0.3))
                }
                .frame(width: 36, height: 36)
                .clipShape(Circle())
            }
        }
        .padding(.horizontal)
    }
}

// Register in the factory:
// NOTE: Verify the exact Options type against https://getstream.io/chat/docs/sdk/ios/swiftui/view-customizations/
// before using - do not rely on training data for the parameter signature.
extension CustomFactory {
    func makeChannelListHeaderViewModifier(options: ChannelListHeaderViewModifierOptions) -> some ChatChannelListHeaderViewModifier {
        CustomChannelListHeader(title: options.title)
    }
}
```

---

### Custom Channel Header Blueprint

Customizes the navigation bar shown at the top of a chat channel (message list) view. Sourced from [getstream.io/chat/docs/sdk/ios/swiftui/chat-channel-components/channel-header/](https://getstream.io/chat/docs/sdk/ios/swiftui/chat-channel-components/channel-header/).

```swift
import SwiftUI
import StreamChat
import StreamChatSwiftUI

struct CustomChatChannelHeaderModifier: ChatChannelHeaderViewModifier {
    var channel: ChatChannel

    func body(content: Content) -> some View {
        content.toolbar {
            ToolbarItem(placement: .principal) {
                Text(channel.name ?? channel.cid.id)
                    .font(.headline)
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    // action
                } label: {
                    Image(systemName: "phone.fill")
                }
            }
        }
    }
}

// Register in the factory:
extension CustomFactory {
    func makeChannelHeaderViewModifier(
        options: ChannelHeaderViewModifierOptions
    ) -> some ChatChannelHeaderViewModifier {
        CustomChatChannelHeaderModifier(channel: options.channel)
    }
}
```

**Wiring:**
- `ChannelHeaderViewModifierOptions` exposes `options.channel: ChatChannel`
- `ChatChannelHeaderViewModifier` conformance requires implementing `body(content:) -> some View`
- Use `.toolbar { ToolbarItem(placement: .topBarTrailing) { ... } }` for trailing nav-bar buttons
- Use `.toolbar { ToolbarItem(placement: .principal) { ... } }` to replace the default title/avatar

---

### Custom Styles Blueprint (Liquid Glass vs Regular)

```swift
// Use the built-in iOS 26 Liquid Glass style (floating composer):
extension CustomFactory {
    public var styles: some Styles { LiquidGlassStyles() }
}

// Or define custom style overrides:
class MyStyles: Styles {
    var composerPlacement: ComposerPlacement = .docked

    func makeComposerInputViewModifier(
        options: ComposerInputModifierOptions
    ) -> some ViewModifier {
        MyComposerInputModifier()
    }
}

extension CustomFactory {
    public var styles: some Styles { MyStyles() }
}
```

**Wiring:**
- `LiquidGlassStyles()` - floating composer above keyboard, iOS 26 material treatment
- `RegularStyles()` - docked bottom composer (SDK default)
- Override individual modifier methods on a custom `Styles` conformance to mix-and-match

---

### Custom Injection Key Blueprint

Register your own services alongside the SDK's injectables and access them from any view or factory method.

```swift
// 1. Define a key
struct AnalyticsServiceKey: InjectionKey {
    static var currentValue: AnalyticsService = AnalyticsService()
}

// 2. Extend InjectedValues
extension InjectedValues {
    var analytics: AnalyticsService {
        get { Self[AnalyticsServiceKey.self] }
        set { Self[AnalyticsServiceKey.self] = newValue }
    }
}

// 3. Use in any view or factory method alongside SDK injectables
struct CustomMessageView: View {
    @Injected(\.analytics) var analytics
    @Injected(\.fonts) var fonts
    @Injected(\.colors) var colors

    var body: some View {
        // ...
    }
}

// 4. Override the value at app startup (e.g. for testing):
InjectedValues[\.analytics] = MockAnalyticsService()
```

---

## State Layer SwiftUI View Blueprint

Use the state layer when you want `async`/`await` mutations and `@Published` state instead of controller delegates.

```swift
import SwiftUI
import StreamChat

@MainActor
class ChannelViewModel: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var isLoading = false

    private var chat: Chat?
    private let channelId: ChannelId

    init(channelId: ChannelId) {
        self.channelId = channelId
    }

    func load(client: ChatClient) async {
        isLoading = true
        chat = client.makeChat(for: channelId)
        do {
            try await chat?.get(watch: true)
            messages = chat?.state.messages ?? []
        } catch {
            print("Load failed: \(error)")
        }
        isLoading = false
    }

    func send(text: String) async {
        try? await chat?.sendMessage(with: text)
        messages = chat?.state.messages ?? []
    }

    func loadOlder() async {
        try? await chat?.loadOlderMessages()
        messages = chat?.state.messages ?? []
    }
}

struct StateLayerChannelView: View {
    @StateObject private var viewModel: ChannelViewModel
    @Injected(\.chatClient) private var chatClient
    @State private var text = ""

    init(channelId: ChannelId) {
        _viewModel = StateObject(wrappedValue: ChannelViewModel(channelId: channelId))
    }

    var body: some View {
        VStack {
            ScrollView {
                LazyVStack(alignment: .leading) {
                    ForEach(viewModel.messages, id: \.id) { message in
                        Text(message.text).padding(.horizontal)
                    }
                }
            }
            HStack {
                TextField("Message", text: $text)
                    .textFieldStyle(.roundedBorder)
                Button("Send") {
                    Task { await viewModel.send(text: text); text = "" }
                }
            }
            .padding()
        }
        .task { await viewModel.load(client: chatClient) }
        .navigationTitle("Channel")
    }
}
```

---

## Channel Tap Handling Blueprint

### Custom navigation destination

Replace the default channel view with your own screen:

```swift
struct MyChannelView: View {
    let channel: ChatChannel
    var body: some View {
        Text("Custom view for \(channel.name ?? channel.cid.id)")
    }
}

extension CustomFactory {
    func makeChannelDestination(
        options: ChannelDestinationOptions
    ) -> @MainActor (ChannelSelectionInfo) -> MyChannelView {
        { info in MyChannelView(channel: info.channel) }
    }
}
```

### Deep-link to a channel from a push notification

```swift
struct RootView: View {
    @State private var selectedChannelId: String?

    var body: some View {
        ChatChannelListView(
            viewFactory: CustomFactory.shared,
            selectedChannelId: selectedChannelId
        )
        .onReceive(NotificationCenter.default.publisher(for: .navigateToChannel)) { note in
            if let cid = note.object as? ChannelId {
                selectedChannelId = cid.rawValue
            }
        }
    }
}
```

### Intercept taps without navigating

```swift
ChatChannelListView(viewFactory: CustomFactory.shared) { channel in
    // e.g. show an action sheet, analytics event, etc.
    print("Tapped: \(channel.name ?? "")")
}
```

### Use your own NavigationStack

When you need to embed `ChatChannelListView` inside your own `NavigationView` or `NavigationStack`, set `embedInNavigationView: false` to opt out of the SDK's built-in navigation container. Pass the title via the `title` parameter.

```swift
NavigationStack {
    ChatChannelListView(
        viewFactory: CustomFactory.shared,
        title: "Messages",
        embedInNavigationView: false
    )
}
```
