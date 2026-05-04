# Feeds - Swift SDK Setup & Integration

Stream Feeds Swift provides a headless data SDK - **there are no pre-built UI components**. You build all views yourself. The SDK gives you observable state objects (`FeedState`, `ActivityState`) that drive your SwiftUI or UIKit UI. This file covers package installation, client setup, authentication, and all major data operations. For view blueprints, see [FEEDS-SWIFTUI-blueprints.md](FEEDS-SWIFTUI-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper logout).

- **Blueprint** - SwiftUI view structure for common Feeds screens
- **Wiring** - SDK calls for each feature, exact property paths
- **No pre-built UI** - every view is custom; the SDK owns the data layer only

## Quick ref

- **Package:** `StreamFeeds` via SPM - `https://github.com/GetStream/stream-feeds-swift`
- **Imports:** `import StreamFeeds` + `import StreamCore` (for `APIKey`, `UserToken`, `User`, `LogConfig`)
- **First:** Installation -> Client init -> `connect()` -> Create `Feed` objects -> Observe `FeedState` -> Build UI
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** `https://getstream.io/activity-feeds/docs/sdk/swift/`

Full view blueprints: [FEEDS-SWIFTUI-blueprints.md](FEEDS-SWIFTUI-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation (Swift Package Manager)

Check if the SDK is already installed in the project. If not, ask the user to add the package from `https://github.com/GetStream/stream-feeds-swift` and link the `StreamFeeds` target to the app.

### Client Initialization

Initialize `FeedsClient` **once** at app launch. **Never** create it in a SwiftUI `View` body or computed property.

Unlike Chat/Video, Feeds has no wrapper class (`StreamChat`, `StreamVideoUI`). The client is held directly.

**Option A - App struct `init()` with `@StateObject AppState`:**

```swift
import StreamCore
import StreamFeeds
import SwiftUI

@main
struct MyApp: App {
    @StateObject private var appState = AppState.shared

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(appState)
        }
    }
}

@MainActor
final class AppState: ObservableObject {
    static let shared = AppState()
    private init() {}

    @Published var viewState: ViewState = .loggedOut

    enum ViewState {
        case connecting
        case loggedIn(FeedsClient)
        case loggedOut
    }

    func connect(apiKey: String, user: User, token: UserToken) async throws {
        viewState = .connecting
        let client = FeedsClient(
            apiKey: APIKey(apiKey),
            user: user,
            token: token
        )
        try await client.connect()
        viewState = .loggedIn(client)
    }

    func disconnect(client: FeedsClient) async {
        await client.disconnect()
        viewState = .loggedOut
    }
}
```

**Option B - `AppDelegate` (required for push notifications):**

```swift
import StreamCore
import StreamFeeds
import SwiftUI

@main
struct MyApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup { RootView() }
    }
}

class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        return true
    }

    func application(_ application: UIApplication,
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Task {
            if let client = AppState.shared.client {
                let tokenString = deviceToken.map { String(format: "%02hhx", $0) }.joined()
                try? await client.createDevice(id: tokenString)
            }
        }
    }
}
```

Use Option B when you need `didRegisterForRemoteNotificationsWithDeviceToken` for push notifications.

### User Authentication

**Static token (no expiry):**

```swift
import StreamCore
import StreamFeeds

let user = User(
    id: "alice",
    name: "Alice Smith",
    imageURL: URL(string: "https://example.com/alice.jpg"),
    role: "user"
)
let token = UserToken(rawValue: "your_static_token_here")

let client = FeedsClient(
    apiKey: APIKey("your_api_key"),
    user: user,
    token: token
)
try await client.connect()
```

**Token provider (expiring tokens):**

```swift
let client = FeedsClient(
    apiKey: APIKey("your_api_key"),
    user: user,
    token: initialToken,
    tokenProvider: { result in
        yourAuthService.fetchFeedsToken(for: user.id) { fetchResult in
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

### Logout / Disconnect

```swift
await client.disconnect()
```

Always `await` disconnect before connecting another user or releasing the client reference.

---

## Feeds and FeedId

A **feed** is identified by a `FeedId(group:id:)` - a group (e.g. `"user"`, `"timeline"`, `"notification"`) plus a user or entity ID.

```swift
let userFeedId       = FeedId(group: "user", id: client.user.id)       // "user:alice"
let timelineFeedId   = FeedId(group: "timeline", id: client.user.id)    // "timeline:alice"
let notificationFeedId = FeedId(group: "notification", id: client.user.id)
```

**Get a Feed object from the client - two forms:**

```swift
// Simple lookup by FeedId
let feed: Feed = client.feed(for: FeedId(group: "user", id: userId))

// With a query (filter + initial data)
let query = FeedQuery(
    feed: FeedId(group: "user", id: client.user.id),
    activityFilter: .exists(.expiresAt, false),          // exclude stories
    data: .init(
        members: [.init(userId: client.user.id)],
        visibility: .public
    )
)
let feed: Feed = client.feed(for: query)
```

`Feed` is the primary handle for all operations on a feed. It exposes a `state: FeedState` observable object.

---

## FeedState

`FeedState` is an `ObservableObject` with `@Published` properties. Observe it in SwiftUI via `@ObservedObject`:

```swift
@ObservedObject var feedState: FeedState = feed.state
```

**Key properties:**

| Property | Type | Description |
|---|---|---|
| `activities` | `[ActivityData]` | Regular activities (paginated) |
| `aggregatedActivities` | `[AggregatedActivityData]` | Grouped activities (notification feeds) |
| `following` | `[FollowData]` | Feeds this feed follows |
| `followers` | `[FollowData]` | Feeds following this feed |
| `followRequests` | `[FollowData]` | Pending incoming follow requests |
| `notificationStatus` | `NotificationStatus?` | Unread/read counts for notification feeds |
| `ownCapabilities` | `[String]` | Permissions the current user has on this feed |
| `canLoadMoreActivities` | `Bool` | Whether more activities are available to paginate |
| `members` | `[MemberData]` | Feed members |

---

## Fetching Activities

```swift
// Initial load - creates the feed if it doesn't exist
try await feed.getOrCreate()

// Refresh (same call - always idempotent)
try await feed.getOrCreate()

// Pagination
guard feed.state.canLoadMoreActivities else { return }
try await feed.queryMoreActivities(limit: 10)
```

Iterate `feed.state.activities` in your SwiftUI list after calling `getOrCreate()`.

---

## Activity Operations

### Create (add a post)

```swift
try await feed.addActivity(
    request: .init(
        attachmentUploads: attachments,          // [AnyAttachmentPayload] - optional
        mentionedUserIds: mentionedUserIds,       // [String] - optional
        text: "Hello world",
        type: "post"
    )
)
```

### Create a story (expires in 24 hours)

```swift
let expiresAt = ISO8601DateFormatter().string(from: Date().addingTimeInterval(24 * 3600))
try await feed.addActivity(
    request: .init(
        expiresAt: expiresAt,
        text: nil,
        type: "post"
    )
)
```

Stories have `expiresAt` set. Filter them in/out via `FeedQuery(activityFilter: .exists(.expiresAt, true/false))`.

### Update

```swift
try await feed.updateActivity(
    id: activity.id,
    request: .init(attachments: activity.attachments, text: newText)
)
```

### Delete

```swift
try await feed.deleteActivity(id: activity.id)
```

### Repost

```swift
try await feed.repost(activityId: activityId, text: nil)
```

Reposted activities have `activity.parent` set to the original `ActivityData`.

---

## ActivityData Model

The central data model for a single activity post:

| Property | Type | Description |
|---|---|---|
| `id` | `String` | Unique activity ID |
| `text` | `String?` | Post text |
| `type` | `String` | Activity type (e.g. `"post"`) |
| `user` | `UserData` | Author |
| `createdAt` / `updatedAt` | `Date` | Timestamps |
| `attachments` | `[Attachment]` | Image/video attachments |
| `poll` | `PollData?` | Embedded poll |
| `parent` | `ActivityData?` | Original activity for reposts |
| `ownReactions` | `[FeedsReactionData]` | Current user's reactions |
| `reactionGroups` | `[String: ReactionGroupData]` | All reactions grouped by type |
| `reactionCount` | `Int` | Total reaction count |
| `ownBookmarks` | `[BookmarkData]` | Current user's bookmarks |
| `bookmarkCount` | `Int` | Total bookmark count |
| `commentCount` | `Int` | Total comment count |
| `shareCount` | `Int` | Total share count |
| `expiresAt` | `String?` | ISO8601 expiry - `nil` for posts, set for stories |
| `visibility` | `ActivityDataVisibility` | `.public` / `.private` |
| `mentionedUsers` | `[UserData]` | Tagged users |
| `custom` | `[String: RawJSON]` | Custom extra data |

**Check if current user has reacted:**

```swift
let hasLiked = !activity.ownReactions.filter { $0.type == "heart" }.isEmpty
let likeCount = activity.reactionGroups["heart"]?.count ?? 0
```

---

## Reactions

```swift
// Add a reaction (e.g. like/heart)
try await feed.addReaction(
    activityId: activity.id,
    request: .init(createNotificationActivity: true, type: "heart")
)

// Remove a reaction
try await feed.deleteReaction(activityId: activity.id, type: "heart")
```

Common reaction types: `"heart"`, `"like"`, `"wow"`, `"sad"`. You define the types; the SDK is type-agnostic.

---

## Bookmarks

```swift
// Add
try await feed.addBookmark(activityId: activity.id)

// Remove
try await feed.deleteBookmark(activityId: activity.id)

// Check
let isBookmarked = !activity.ownBookmarks.isEmpty
```

---

## Comments

Comments are accessed via an `Activity` object (distinct from `ActivityData`). Get the `Activity` handle from the client:

```swift
let activity: Activity = feedsClient.activity(for: activityId, in: feed.feed)
```

Observe comment state via `@StateObject var state: ActivityState = activity.state`:

```swift
@StateObject var activityState: ActivityState

init(activityId: String, feed: Feed, feedsClient: FeedsClient) {
    let activity = feedsClient.activity(for: activityId, in: feed.feed)
    _activityState = StateObject(wrappedValue: activity.state)
    // hold `activity` reference in @State
}
```

**Load comments:**

```swift
try await activity.get()
// Then read: activityState.comments: [ThreadedCommentData]
```

**Add a comment:**

```swift
try await activity.addComment(
    request: .init(
        comment: text,
        createNotificationActivity: true,
        parentId: parentCommentId  // nil for top-level, set for replies
    )
)
```

**Update / Delete:**

```swift
try await activity.updateComment(commentId: id, request: .init(comment: newText))
try await activity.deleteComment(commentId: id)
```

**React to a comment:**

```swift
try await activity.addCommentReaction(commentId: comment.id, request: .init(type: "heart"))
try await activity.deleteCommentReaction(commentId: comment.id, type: "heart")
```

**`ThreadedCommentData`** key properties: `id`, `text`, `user`, `replies: [CommentData]?`, `replyCount`, `reactionGroups`, `ownReactions`, `parentId`.

---

## Follow Graph

All follow operations are called on a `Feed` object (the current user's feed):

```swift
// Follow another user's feed
try await feed.follow(
    FeedId(group: "user", id: targetUserId),
    createNotificationActivity: true
)

// Unfollow
try await feed.unfollow(FeedId(group: "user", id: targetUserId))

// Accept / reject a follow request (for private feeds)
try await feed.acceptFollow(FeedId(group: "user", id: requestingUserId))
try await feed.rejectFollow(FeedId(group: "user", id: requestingUserId))

// Remove a follower
try await feed.removeFollower(FeedId(group: "user", id: followerUserId))
```

**Read follow state from `FeedState`:**

```swift
feed.state.following       // [FollowData] - feeds this user follows
feed.state.followers       // [FollowData] - feeds following this user
feed.state.followRequests  // [FollowData] - pending incoming requests
```

**`FollowData`** key properties: `sourceFeed: FeedData`, `targetFeed: FeedData`, `status: FollowStatus` (`.accepted` / `.pending`), `isFollowing`, `isFollower`, `isFollowRequest`.

**Follow suggestions:**

```swift
let suggestions: [FeedData] = try await feed.queryFollowSuggestions(limit: 10)
```

---

## Notification Feed

The notification feed uses a different `FeedId` group (`"notification"`) and exposes aggregated activities instead of individual ones.

```swift
let notificationFeed = client.feed(for: FeedId(group: "notification", id: client.user.id))
try await notificationFeed.getOrCreate()

// Observe
@ObservedObject var state: FeedState = notificationFeed.state
// state.aggregatedActivities: [AggregatedActivityData]
// state.notificationStatus?.unread - badge count
// state.notificationStatus?.readActivities - Set<String> of read activity IDs
```

**Mark activities as read:**

```swift
// Mark all read
try await notificationFeed.markActivity(request: .init(markAllRead: true))

// Mark specific activity read
try await notificationFeed.markActivity(request: .init(readActivities: [activityId]))
```

**`AggregatedActivityData`** key properties: `id`, `activities: [ActivityData]`, `actorCount`, `verb` (aggregation verb like `"react"`, `"comment"`), `notificationContext` (links back to the source activity).

---

## Push Notifications

Register the device token after connecting:

```swift
try await client.createDevice(id: deviceTokenHexString)
```

Call this once after `connect()` completes and the APNs token is available. The SDK uses this token to deliver push notifications for followed activity, reactions, and comments.

---

## Logging

Enable before creating the `FeedsClient`:

```swift
import StreamCore

LogConfig.level = .debug
```

Levels: `.debug`, `.info`, `.warning`, `.error`.

---

## Custom Extra Data

Activities, users, and reactions accept a `custom: [String: RawJSON]` dictionary:

```swift
// On an activity
try await feed.addActivity(
    request: .init(
        custom: ["category": .string("sports"), "score": .number(42)],
        text: "Just scored!",
        type: "post"
    )
)

// Read from an ActivityData
let category = activity.custom["category"]?.stringValue
```

`RawJSON` accessors: `.stringValue`, `.numberValue`, `.boolValue`, `.dictionaryValue`, `.arrayValue`.

---

## Gotchas

- **No pre-built UI.** `StreamFeeds` is headless - there is no `FeedListView`, `ActivityView`, or similar. Build all UI yourself against `FeedState` and `ActivityState`.
- **Always `await client.connect()` before any feed operations.** Calling `feed.getOrCreate()` before `connect()` throws.
- **Always `await client.disconnect()` before connecting another user.** Like Chat, skip this and you risk state corruption.
- **`feed.state` is the same instance across calls.** Never replace it - just keep an `@ObservedObject` reference to the instance returned by `feed.state`.
- **Use `@StateObject` at the ownership site, `@ObservedObject` in child views.** `FeedState` and `ActivityState` are reference types; `@StateObject` keeps them alive, `@ObservedObject` observes the same instance without owning it.
- **`FeedId` group names are case-sensitive and must match your dashboard feed group configuration.** Using `"User"` when the group is `"user"` silently creates a new feed group.
- **Stories vs posts are the same activity type, differentiated by `expiresAt`.** Use `FeedQuery(activityFilter: .exists(.expiresAt, false))` for posts and `.exists(.expiresAt, true)` for stories so they don't mix.
- **`client.activity(for:in:)` returns an `Activity` handle, not `ActivityData`.** `ActivityData` is the plain model from `FeedState.activities`. The `Activity` handle gives you the async operations (`addComment`, `get`, etc.) and its own `ActivityState`.
- **`createNotificationActivity: true` is required for follow/reaction notifications to appear in the target user's notification feed.** Omitting it silently drops the notification delivery.
- **Never store the Stream secret in the app.** Token generation must happen server-side.
- **Never use dev tokens in production.** `devToken()` disables token auth and lets any client impersonate any user.
- **`import StreamCore` is always required alongside `import StreamFeeds`** for types like `APIKey`, `UserToken`, `User`, `LogConfig`, and `RawJSON`. Missing it causes "cannot find type" errors.
