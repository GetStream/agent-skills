# Stream Swift - setup flow (integrate / new app)

Run this once per session for integrate or new-app requests, before feature work. How-to / reference requests skip this entirely and go straight to docs lookup. Obey [`RULES.md`](RULES.md) throughout.

---

## 1. Project signals (read-only probe)

Detect the project shape once:

```bash
bash -c 'echo "=== XCODE ==="; find . -maxdepth 3 \( -name "*.xcodeproj" -o -name "*.xcworkspace" \) -print 2>/dev/null; echo "=== MANIFESTS ==="; find . -maxdepth 3 \( -name "Package.swift" -o -name "Package.resolved" -o -name "Podfile" \) -print 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Interpret and hold in context:

- `*.xcodeproj` / `*.xcworkspace` -> existing Xcode app; preserve its UI layer and package manager.
- `Package.swift`, no Xcode project -> ask whether it is an app package, a shared module, or support code.
- `Podfile` -> keep CocoaPods unless the user wants to migrate.
- `EMPTY_CWD` / no Xcode project -> **stop**: tell the user to create the iOS app in Xcode first. Do not scaffold from the CLI.

State a one-line status (e.g. `SwiftUI app detected - MyApp.xcodeproj - ready for Stream wiring`).

---

## 2. Credentials (ask once, then act)

Collect the API key, a user token, and (Chat only) optional seed channels in **one** message, then execute without pausing between steps.

**Chat:**
> To wire this with real data I need: (1) should I fetch your API key and generate a token via the Stream CLI, or will you paste them? (2) token expiry (`1h`, `1d`, never)? (3) seed a few channels so the app shows data on first launch?

**Feeds:** same as Chat but replace seed channels with feed groups (defaults `user`, `timeline`, `notification`).

**Video:** API key + token only (calls are ephemeral - nothing to seed).

If the user says they will paste credentials, take them and skip the CLI steps below.

### CLI steps (run in sequence, narrate one line each)

```bash
# Onboard ONCE in the project dir: authenticate + select/create org & app + write
# project credentials. REQUIRED first — env/token/api all fail with
# "stream project is not initialized; run `getstream init` first" otherwise.
getstream init

# API key -> Secrets.xcconfig (read via Info.plist / Bundle.main); the secret is never printed
getstream env --target ios

# Token (never-expiring, or add --ttl <duration>)
getstream token <user_id>
getstream token <user_id> --ttl <duration>

# Seed channels (Chat only, if requested): create the users first, then each channel
getstream api UpdateUsers --request '{"users":{"<token_user_id>":{"id":"<token_user_id>","name":"Token User"},"alice":{"id":"alice","name":"Alice"}}}'
getstream api GetOrCreateChannel --type messaging --id <channel-id> --request '{"data":{"created_by_id":"<token_user_id>","members":[{"user_id":"<token_user_id>"},{"user_id":"alice"}]}}'
```

To seed messages, attribute the sender server-side with `message.user_id` and include `original_width`/`original_height` on image attachments (without them the SwiftUI media gallery treats images as landscape and stacks a 2-photo album vertically instead of side-by-side):
```bash
getstream api SendMessage --type messaging --id <channel-id> \
  --request '{"message":{"user_id":"alice","text":"Hi","attachments":[{"type":"image","image_url":"<url>","thumb_url":"<url>","original_width":1200,"original_height":900}]}}'
```

Pick `--type` to match the vertical, not always `messaging`: `messaging` for social / marketplace / DMs, `team` for workplace, `livestream` for livestream / live-shopping (its permissions allow public + anonymous access). See [`RULES.md`](RULES.md) "Permissions". Use short channel ids (`general`, `random`) and a small set of usernames (`alice`, `bob`, `carol`). Make the token user a member of at least one channel so it shows on first launch. Print a one-line summary of what was created.

Never put the API **secret** in app code - the CLI uses it server-side only. Never fabricate credentials. If a CLI step fails, explain briefly and ask the user to paste the missing value.

---

## 3. Install the SDKs

**Pin Chat to the 5.x major - it is the minimum this skill targets.** Everything the Chat runbooks assume (the `Styles` protocol, the `StreamChatCommonUI` `Appearance`, the modern State Layer, `LiquidGlassStyles`) exists **only on v5** - default output built against v4 will not compile. Pin **both** Chat packages `from: "5.0.0"` (SPM up-to-next-major → the latest 5.x, blocks 6.0), on the **same minor** (they ship in lockstep; `stream-chat-swiftui` itself declares `stream-chat-swift from: <same version>`):

```swift
// Package.swift — Chat (SwiftUI): BOTH packages, same 5.x line
.package(url: "https://github.com/GetStream/stream-chat-swift.git", from: "5.0.0"),
.package(url: "https://github.com/GetStream/stream-chat-swiftui.git", from: "5.0.0"),
```

(UIKit-only apps take `stream-chat-swift` alone, product `StreamChatUI`, same `from: "5.0.0"`.) In Xcode's "Add Package Dependencies" dialog set **Dependency Rule → Up to Next Major → 5.0.0** for each.

**This is not the default resolution, so pin it explicitly.** Stream still ships a parallel **4.x** line (GitHub currently even tags a 4.x build as "Latest"), so an unpinned "add package" can silently resolve to v4 and break the code these runbooks generate. **Only use v4 if the customer explicitly asks for it** (a locked older app) - then say so, pin `~> 4.0.0` instead, and route docs through the **v4 tree** ([`docs-map.md`](docs-map.md) "Chat - v4": same paths with `/v4/` inserted after `ios/`), expecting the v5-only APIs to be absent. **Video** and **Feeds** are on their **own** version lines - `stream-video-swift` is currently **1.x**, not 5.x - so pin each to *its* own latest major and never force "5.x" onto them.

Use the project's existing package workflow; install only what the requested products need:

- **Xcode app, no `Package.swift`** -> guide the user through File -> Add Package Dependencies. For exact package names/URLs, fetch the installation doc from [`docs-map.md`](docs-map.md) (Chat: `basics/integration.md`; Video: `basics/installation.md`; Feeds: `installation.md`).
- **Swift package-managed** -> edit `Package.swift` directly.
- **CocoaPods** -> keep Pods unless the user asks to migrate.

---

## 4. Wire the client

Initialize the client once at an owned lifecycle entry point (`App` init, `AppDelegate`, or a service object) and connect the user. Reference credentials via named constants (`Config.apiKey`, `Config.userToken`), never inline.

The exact init + connect code lives in the docs - fetch the relevant page from [`docs-map.md`](docs-map.md) ("Getting started" / "Quickstart" / "Client and authentication") and apply it. Honor the lifecycle and combined-SDK pitfalls in [`RULES.md`](RULES.md). If channels were seeded, the app should render them on first launch with no hardcoded ids.

**SwiftUI vs UIKit differ at init - and UIKit has NO `StreamChat` wrapper.** In SwiftUI you construct the `StreamChat` wrapper object once (`StreamChat(chatClient:appearance:utils:)`) and it must exist before any SDK view renders. **UIKit has no equivalent wrapper type** - you create the `ChatClient`, connect the user, and present the SDK's view controllers directly; reaching for a `StreamChat(...)` object in a UIKit app is a common miswiring (there is nothing to construct and none is required). Minimal UIKit init (confirm every symbol against the live UIKit "Getting started" page - [`docs-map.md`](docs-map.md) "Chat - UIKit" - for the pinned version before shipping):

```swift
import StreamChat
import StreamChatUI   // UIKit components; there is NO `StreamChat` SwiftUI wrapper here

// once, e.g. in AppDelegate.application(_:didFinishLaunchingWithOptions:) — a @MainActor entry point
let config = ChatClientConfig(apiKey: .init(Config.apiKey))
let chatClient = ChatClient(config: config)          // hold this (AppDelegate property / service), never a local
chatClient.connectUser(
    userInfo: .init(id: Config.userID),
    token: try! Token(rawValue: Config.userToken)    // backend/CLI token; hop to the main actor before touching UI
)

// Theming/customization registries are @MainActor (see RULES.md) — set them here, at launch:
// Appearance.default.colorPalette.accentPrimary = .systemIndigo
// Components.default.channelVC = MyChannelVC.self

// Present the SDK view controllers directly — no wrapper object:
let listVC = ChatChannelListVC()
listVC.controller = chatClient.channelListController(
    query: .init(filter: .containMembers(userIds: [Config.userID]))
)
window?.rootViewController = UINavigationController(rootViewController: listVC)
```

---

## 5. Verify before stopping

- the right package is on the right target and resolves
- the client is initialized before any Stream view renders
- the requested user connects without leaking the secret
- the feature renders inside the existing navigation structure
- switching users / logout tears down the previous session cleanly

Then return to **Docs lookup** in [`SKILL.md`](SKILL.md) for each requested screen.
