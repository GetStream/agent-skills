# Feeds - Android Kotlin SDK Setup & Integration

Stream Feeds Android is a **headless data SDK** — there are no pre-built UI components. You build all Composables yourself; the SDK exposes observable `StateFlow`s on `FeedState` and `ActivityState` that drive your UI. This file covers Gradle setup, client setup, authentication, and the major data operations. For Compose blueprints, see [FEEDS-COMPOSE-blueprints.md](FEEDS-COMPOSE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no fake credentials, client lifetime, version lookup).

- **Blueprint** — Compose screen structure for common Feeds surfaces
- **Wiring** — SDK calls per feature with exact property paths
- **No pre-built UI** — every screen is custom; the SDK owns the data layer only

> Stream Feeds V3 is in closed alpha at the time of writing — the public artifact metadata may surface SNAPSHOT or alpha versions on Maven Central / GitHub. Always look up the current coordinate before adding it to a project (see [`RULES.md` → Version lookup](../RULES.md#version-lookup)).

## Quick ref

- **Artifact:** `io.getstream:stream-feeds-android-client` via Maven Central
- **Imports:** Feeds-side types are reachable under `io.getstream.feeds.android.client.api.*` (and `io.getstream.feeds.android.network.models.*` for request/response data classes like `AddReactionRequest`, `MarkActivityRequest`, `UpdateActivityRequest`, `UpdateCommentRequest`, `AddCommentReactionRequest`). Core-side types live in nested subpackages — Kotlin imports aren't recursive, so import them explicitly: `io.getstream.android.core.api.model.value.{StreamApiKey, StreamToken, StreamUserId}` and `io.getstream.android.core.api.authentication.StreamTokenProvider`.
- **First:** Installation → Manifest → `FeedsClient(...)` build → `client.connect()` → create `Feed` objects → observe `FeedState` → build Composables
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** `https://getstream.io/activity-feeds/docs/android/` and the source at `https://github.com/GetStream/stream-feeds-android`

Full Compose blueprints: [FEEDS-COMPOSE-blueprints.md](FEEDS-COMPOSE-blueprints.md) — load only the section you are implementing.

---

## App Integration

### Installation (Gradle)

Check whether the SDK is already on the classpath. If not:

**With version catalog (`gradle/libs.versions.toml`):**

```toml
[versions]
stream-feeds = "<latest>"

[libraries]
stream-feeds-client = { module = "io.getstream:stream-feeds-android-client", version.ref = "stream-feeds" }
```

```kotlin
// app/build.gradle.kts
dependencies {
    implementation(libs.stream.feeds.client)
}
```

**Without version catalog:**

```kotlin
// app/build.gradle.kts
dependencies {
    implementation("io.getstream:stream-feeds-android-client:<latest>")
}
```

For the current version, follow [`RULES.md` → Version lookup](../RULES.md#version-lookup) (Maven Central / GitHub releases — never `search.maven.org`).

Add the `INTERNET` permission to `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

### Client Initialization

Build the `FeedsClient` once **per user session** and keep it in an app-scoped owner (`Application`, Hilt `@Singleton`, Koin `single`). **Never** create it inside a `@Composable`, a `remember { ... }` factory, or an Activity that recreates.

> **`FeedsClient` is bound to one user for its lifetime.** The `User` and `tokenProvider` are passed to the constructor and cannot be swapped afterwards — there is no method to change the signed-in user on an existing client. To operate as a different user you must `disconnect()` the current client and build a new `FeedsClient` with the new `User`. *You* own the reference; the SDK does not register a global accessor. "App-scoped" here therefore means "scoped to the current logged-in user", not "scoped to the process" — replace the reference when the user changes.

```kotlin
import android.app.Application
import io.getstream.android.core.api.authentication.StreamTokenProvider
import io.getstream.android.core.api.model.value.StreamApiKey
import io.getstream.android.core.api.model.value.StreamToken
import io.getstream.android.core.api.model.value.StreamUserId
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.logging.HttpLoggingLevel
import io.getstream.feeds.android.client.api.logging.LoggingConfig
import io.getstream.feeds.android.client.api.model.FeedsConfig
import io.getstream.feeds.android.client.api.model.User

class App : Application() {

    lateinit var feedsClient: FeedsClient
        private set

    override fun onCreate() {
        super.onCreate()

        val user = User(
            id = "alice",
            name = "Alice",
            imageURL = "https://example.com/alice.png",
        )

        val tokenProvider = object : StreamTokenProvider {
            override suspend fun loadToken(userId: StreamUserId): StreamToken =
                StreamToken.fromString("your_static_token_here")
        }

        feedsClient = FeedsClient(
            context = applicationContext,
            apiKey = StreamApiKey.fromString("your_api_key"),
            user = user,
            tokenProvider = tokenProvider,
            config = FeedsConfig(
                loggingConfig = LoggingConfig(
                    httpLoggingLevel = if (BuildConfig.DEBUG) HttpLoggingLevel.Body else HttpLoggingLevel.None,
                ),
            ),
        )
    }
}
```

Register the `Application` subclass in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    ...>
```

`FeedsClient` does **not** auto-connect. Call `client.connect()` once before any feed operation:

```kotlin
val result = feedsClient.connect()  // suspend fun, returns Result<StreamConnectedUser>
result.onFailure { /* handle error */ }
```

Do this from a lifecycle-aware coroutine scope (`viewModelScope`, `lifecycleScope`, or a Hilt `ApplicationScope`) — typically right after the user logs in.

### User Authentication

The SDK takes a `StreamTokenProvider` for both static and expiring tokens. The provider's `loadToken(userId)` is `suspend` — return the token from your backend, or return a stored static token.

**Static token (no expiry):**

```kotlin
val tokenProvider = object : StreamTokenProvider {
    override suspend fun loadToken(userId: StreamUserId): StreamToken =
        StreamToken.fromString("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
}
```

**Backend-issued (expiring) token:**

```kotlin
val tokenProvider = object : StreamTokenProvider {
    override suspend fun loadToken(userId: StreamUserId): StreamToken {
        val tokenString = yourAuthService.fetchFeedsToken(userId.value)
        return StreamToken.fromString(tokenString)
    }
}
```

The SDK calls `loadToken` again automatically when the token expires — no extra wiring.

### Disconnecting / switching users

The signed-in user is fixed at construction time. To switch identity you tear down the current client and build a new one:

```kotlin
feedsClient.disconnect()  // suspend fun — closes the WebSocket and clears in-memory state

// Build a fresh FeedsClient for the next user
val nextClient = FeedsClient(
    context = applicationContext,
    apiKey = StreamApiKey.fromString(apiKey),
    user = nextUser,                 // new User
    tokenProvider = nextTokenProvider, // new token source for that user
)
nextClient.connect()
```

Always `await disconnect()` before constructing the replacement — overlapping clients on the same user will desync state and waste a socket. Drop the old reference (set your `lateinit` / `@Singleton` to the new client) so it can be garbage-collected.

---

## Feeds and FeedId

A feed is identified by a `FeedId(group, id)` — a group name (e.g. `"user"`, `"timeline"`, `"notification"`) plus a user/entity id.

```kotlin
import io.getstream.feeds.android.client.api.model.FeedId

val userFeedId         = FeedId("user", client.user.id)         // "user:alice"
val timelineFeedId     = FeedId("timeline", client.user.id)
val notificationFeedId = FeedId("notification", client.user.id)
```

**Get a `Feed` handle from the client — three forms:**

```kotlin
import io.getstream.feeds.android.client.api.state.query.FeedQuery

// Simple lookup by group + id
val userFeed = client.feed(group = "user", id = "alice")

// By FeedId
val feed = client.feed(FeedId("timeline", "alice"))

// With a query (filter + initial data)
val query = FeedQuery(
    fid = FeedId("user", client.user.id),
    activityFilter = ActivitiesFilterField.expiresAt.doesNotExist(), // exclude stories
    data = FeedInputData(
        members = listOf(FeedMemberRequestData(client.user.id)),
        visibility = FeedVisibility.Public,
    ),
)
val feed = client.feed(query)
```

`Feed` is the primary handle for operations on a single feed. It exposes a `state: FeedState` observable.

---

## FeedState

`FeedState` exposes `StateFlow`s — collect them with `collectAsStateWithLifecycle()` in Compose.

```kotlin
import androidx.lifecycle.compose.collectAsStateWithLifecycle

val activities by feed.state.activities.collectAsStateWithLifecycle()
```

**Key properties (all `StateFlow<...>`):**

| Property | Type | Description |
|---|---|---|
| `activities` | `StateFlow<List<ActivityData>>` | Regular activities (paginated) |
| `aggregatedActivities` | `StateFlow<List<AggregatedActivityData>>` | Grouped activities (notification feeds) |
| `feed` | `StateFlow<FeedData?>` | Feed metadata |
| `following` | `StateFlow<List<FollowData>>` | Feeds this feed follows |
| `followers` | `StateFlow<List<FollowData>>` | Feeds following this feed |
| `followRequests` | `StateFlow<List<FollowData>>` | Pending incoming follow requests |
| `members` | `StateFlow<List<FeedMemberData>>` | Feed members |
| `pinnedActivities` | `StateFlow<List<ActivityPinData>>` | Pinned activities |
| `notificationStatus` | `StateFlow<NotificationStatusResponse?>` | `unread`/`unseen` counts and read activity ids |
| `canLoadMoreActivities` | `Boolean` | `true` while pagination is available |

`fid` and `feedQuery` are plain non-flow properties.

---

## Fetching Activities

```kotlin
// Initial load (or create if it doesn't exist)
feed.getOrCreate()  // suspend, Result<FeedData>

// Refresh (idempotent — same call)
feed.getOrCreate()

// Pagination
if (feed.state.canLoadMoreActivities) {
    feed.queryMoreActivities(limit = 20)
}
```

Render `feed.state.activities` in a `LazyColumn` after the first `getOrCreate()` resolves.

---

## Activity Operations

### Create (post)

```kotlin
import io.getstream.feeds.android.client.api.model.FeedAddActivityRequest

feed.addActivity(
    FeedAddActivityRequest(
        type = "post",
        text = "Hello, Stream Feeds!",
        feeds = listOf(feed.fid.rawValue),
    )
)
```

### Create with attachments

```kotlin
import io.getstream.feeds.android.client.api.file.FeedUploadPayload
import io.getstream.feeds.android.client.api.file.FileType

feed.addActivity(
    request = FeedAddActivityRequest(
        type = "post",
        text = "Trip photos",
        feeds = listOf(feed.fid.rawValue),
        attachmentUploads = files.map { FeedUploadPayload(file = it, type = FileType.Image) },
    ),
    attachmentUploadProgress = { payload, progress ->
        // optional progress callback
    },
)
```

### Create a story (expires in 24h)

Stories are activities with `expiresAt` set. Filter posts vs stories with `ActivitiesFilterField.expiresAt.exists()` / `.doesNotExist()`.

```kotlin
import kotlin.time.Clock
import kotlin.time.Duration.Companion.days

storiesFeed.addActivity(
    FeedAddActivityRequest(
        type = "post",
        text = null,
        feeds = listOf(storiesFeed.fid.rawValue),
        expiresAt = Clock.System.now().plus(1.days).toString(),
    )
)
```

> `kotlin.time.Clock` was stabilized in Kotlin 2.1; on older toolchains either keep the `@OptIn(ExperimentalTime::class)` annotation or fall back to `java.time.Instant.now().plusSeconds(86_400).toString()` (or `kotlinx-datetime`). The wire format is ISO-8601, which all three produce.

### Update

```kotlin
import io.getstream.feeds.android.network.models.UpdateActivityRequest

feed.updateActivity(id = activity.id, request = UpdateActivityRequest(text = newText))
```

### Delete

```kotlin
feed.deleteActivity(id = activity.id)
```

### Repost

```kotlin
feed.repost(activityId = original.id, text = "Adding my take")
```

The reposted activity has `parent` set to the original `ActivityData`.

---

## ActivityData Model

Central data model for a single activity:

| Property | Type | Description |
|---|---|---|
| `id` | `String` | Unique activity id |
| `text` | `String?` | Post text |
| `type` | `String` | Activity type (e.g. `"post"`) |
| `user` | `UserData` | Author |
| `createdAt` / `updatedAt` | `Date` | Timestamps |
| `attachments` | `List<Attachment>` | Image / video / file attachments |
| `poll` | `PollData?` | Embedded poll |
| `parent` | `ActivityData?` | Original activity for reposts |
| `ownReactions` | `List<FeedsReactionData>` | Current user's reactions |
| `reactionGroups` | `Map<String, ReactionGroupData>` | Reactions keyed by type |
| `reactionCount` | `Int` | Total reactions |
| `ownBookmarks` | `List<BookmarkData>` | Current user's bookmarks |
| `bookmarkCount` | `Int` | Total bookmarks |
| `commentCount` | `Int` | Total comments |
| `shareCount` | `Int` | Total shares |
| `expiresAt` | `Date?` | `null` for posts, set for stories |
| `visibility` | `ActivityDataVisibility` | `Public` / `Private` / `Tag` / `Unknown` |
| `mentionedUsers` | `List<UserData>` | Tagged users |
| `hidden` | `Boolean` | True if the current user has hidden it via `activityFeedback(hide = true)` |
| `isWatched` / `isRead` / `isSeen` | `Boolean?` | Story / notification flags |
| `custom` | `Map<String, Any?>` | Custom extra data |

**Check whether the current user has reacted:**

```kotlin
val hasLiked = activity.ownReactions.any { it.type == "heart" }
val likeCount = activity.reactionGroups["heart"]?.count ?: 0
```

---

## Reactions

```kotlin
import io.getstream.feeds.android.network.models.AddReactionRequest

// Add
feed.addActivityReaction(
    activityId = activity.id,
    request = AddReactionRequest(type = "heart", createNotificationActivity = true),
)

// Remove
feed.deleteActivityReaction(activityId = activity.id, type = "heart")
```

You define the reaction types — common ones are `"heart"`, `"like"`, `"wow"`, `"sad"`. The SDK is type-agnostic.

---

## Bookmarks

```kotlin
// Add (default folder)
feed.addBookmark(activityId = activity.id)

// Remove
feed.deleteBookmark(activityId = activity.id)

// Has the current user bookmarked it?
val isBookmarked = activity.ownBookmarks.isNotEmpty()
```

Use `AddBookmarkRequest(folderId = "...")` to add to a specific folder.

---

## Comments

Comments live on an `Activity` object (different from `ActivityData`). Get the handle from the client and observe its `ActivityState`:

```kotlin
val activity = client.activity(activityId = activityId, fid = feed.fid)
val activityState = activity.state  // ActivityState
```

**Load comments:**

```kotlin
activity.get()                      // populates activityState.comments
// activityState.comments: StateFlow<List<ThreadedCommentData>>

if (canLoadMore) {
    activity.queryMoreComments(limit = 20)
}
```

**Add a comment / reply:**

```kotlin
import io.getstream.feeds.android.client.api.model.request.ActivityAddCommentRequest

activity.addComment(
    ActivityAddCommentRequest(
        comment = text,
        activityId = activity.activityId,
        parentId = parentCommentId,        // null for top-level, set for replies
        createNotificationActivity = true,
    )
)
```

**Update / Delete:**

```kotlin
import io.getstream.feeds.android.network.models.UpdateCommentRequest

activity.updateComment(commentId = id, request = UpdateCommentRequest(comment = newText))
activity.deleteComment(commentId = id)
```

**React to a comment:**

```kotlin
import io.getstream.feeds.android.network.models.AddCommentReactionRequest

activity.addCommentReaction(
    commentId = comment.id,
    request = AddCommentReactionRequest(type = "heart", createNotificationActivity = true),
)
activity.deleteCommentReaction(commentId = comment.id, type = "heart")
```

**`ThreadedCommentData`** key fields: `id`, `text`, `user`, `replies: List<ThreadedCommentData>?`, `replyCount`, `reactionGroups`, `ownReactions`, `parentId`.

---

## Follow Graph

All follow operations are called on a `Feed` (typically the current user's feed):

```kotlin
// Follow another feed
feed.follow(
    targetFid = FeedId("user", targetUserId),
    createNotificationActivity = true,
)

// Unfollow
feed.unfollow(FeedId("user", targetUserId))

// Accept / reject a follow request (private feeds)
feed.acceptFollow(FeedId("user", requestingUserId))
feed.rejectFollow(FeedId("user", requestingUserId))
```

**Read state from `FeedState`:**

```kotlin
val following by feed.state.following.collectAsStateWithLifecycle()
val followers by feed.state.followers.collectAsStateWithLifecycle()
val requests by feed.state.followRequests.collectAsStateWithLifecycle()
```

`FollowData` exposes `sourceFeed: FeedData`, `targetFeed: FeedData`, `status: FollowStatus` (`Accepted` / `Pending` / `Rejected` / `Unknown`). There is no `isFollowing` / `isFollower` boolean — distinguish via `state.following` vs `state.followers`.

**Follow suggestions:**

```kotlin
val suggestions: List<FeedSuggestionData> =
    feed.queryFollowSuggestions(limit = 10).getOrDefault(emptyList())
```

`FeedSuggestionData` exposes `feed: FeedData` plus three nullable hints — `recommendationScore: Float?`, `reason: String?`, and `algorithmScores: Map<String, Float>?`. Treat all three as nullable in the UI.

> The `timeline:<userId>` feed does **not** automatically follow the user's own `user:<userId>` feed. If you want the user to see their own posts in the timeline, follow `user:<userId>` from `timeline:<userId>` once after `getOrCreate()`. The sample app does this in `FeedViewModel.followSelfIfNeeded(...)`.

---

## Notification Feed

The notification feed uses the `"notification"` group and surfaces grouped activity via `aggregatedActivities` instead of `activities`.

```kotlin
val notifications = client.feed(FeedId("notification", client.user.id))
notifications.getOrCreate()

val aggregated by notifications.state.aggregatedActivities.collectAsStateWithLifecycle()
val status by notifications.state.notificationStatus.collectAsStateWithLifecycle()
// status?.unread, status?.unseen, status?.readActivities
```

**Mark activities as read:**

```kotlin
import io.getstream.feeds.android.network.models.MarkActivityRequest

// All read
notifications.markActivity(MarkActivityRequest(markAllRead = true))

// Specific activities read
notifications.markActivity(MarkActivityRequest(markRead = listOf(activityId)))

// Specific activities seen (without marking them read)
notifications.markActivity(MarkActivityRequest(markSeen = listOf(activityId)))

// Mark all unread as seen
notifications.markActivity(MarkActivityRequest(markAllSeen = true))

// Mark a story as watched
storiesFeed.markActivity(MarkActivityRequest(markWatched = listOf(storyId)))
```

`AggregatedActivityData` key fields: `activities: List<ActivityData>`, `activityCount`, `userCount`, `group`, `isRead`, `isSeen`, `isWatched`.

---

## Push Notifications

After `connect()` completes and the FCM device token is available, register the device:

```kotlin
import io.getstream.feeds.android.client.api.model.PushNotificationsProvider

client.createDevice(
    id = deviceTokenString,
    pushProvider = PushNotificationsProvider.FIREBASE,
    pushProviderName = "your-firebase-config-name",
)
```

Other supported providers: `PushNotificationsProvider.HUAWEI`, `PushNotificationsProvider.XIAOMI`. The `pushProviderName` matches the push config you configured in the Stream dashboard.

---

## Logging

Pass a `LoggingConfig` via `FeedsConfig` at client construction:

```kotlin
import io.getstream.feeds.android.client.api.logging.HttpLoggingLevel
import io.getstream.feeds.android.client.api.logging.LoggingConfig
import io.getstream.feeds.android.client.api.model.FeedsConfig

FeedsClient(
    context = applicationContext,
    apiKey = StreamApiKey.fromString(apiKey),
    user = user,
    tokenProvider = tokenProvider,
    config = FeedsConfig(
        loggingConfig = LoggingConfig(
            httpLoggingLevel = if (BuildConfig.DEBUG) HttpLoggingLevel.Body else HttpLoggingLevel.None,
        ),
    ),
)
```

`HttpLoggingLevel` values: `None`, `Basic`, `Headers`, `Body`.

---

## WebSocket Events and Connection State

```kotlin
// Connection state
client.state.collect { state -> /* StreamConnectionState */ }

// Raw WebSocket events (when you need a custom side-effect on a particular event)
client.events.collect { event -> /* WSEvent */ }
```

Most UI doesn't need the raw stream — `FeedState` already updates on the right events automatically.

---

## Custom Extra Data

`ActivityData`, `UserData`, comments, and reactions all carry a `custom: Map<String, Any?>`:

```kotlin
feed.addActivity(
    FeedAddActivityRequest(
        type = "post",
        text = "Just scored!",
        feeds = listOf(feed.fid.rawValue),
        custom = mapOf("category" to "sports", "score" to 42),
    )
)

val category = activity.custom["category"] as? String
val score = (activity.custom["score"] as? Number)?.toInt()
```

Custom values round-trip through JSON, so cast defensively (`String`, `Number`, `Boolean`, `Map<*, *>`, `List<*>`).

---

## Gotchas

- **No pre-built UI.** `stream-feeds-android-client` is headless. There is no `FeedListScreen`, `ActivityRow`, or theme — build every Composable yourself against `FeedState` / `ActivityState`.
- **`FeedsClient` is bound to one user for its lifetime.** The `User` and `tokenProvider` are fixed at construction; there is no method to change the signed-in user afterwards. The SDK does not register a global accessor either — *you* hold the reference (in `Application`, a Hilt `@Singleton` provider, or a Koin `single`). To operate as a different user, `disconnect()` the current client, then **replace** the reference with a freshly-built client for the new user.
- **Always `client.connect()` before any feed call.** Calling `feed.getOrCreate()` before `connect()` fails. Connect once per user session, after the user logs in.
- **Always `await disconnect()` before constructing the next client.** Overlapping `FeedsClient` instances for the same user will desync state and waste a WebSocket connection.
- **Collect `FeedState` flows with `collectAsStateWithLifecycle()`, never `collectAsState()`** in production Composables — the lifecycle-aware variant suspends collection in the background and avoids leaking work after the screen is gone.
- **`feed.state` is the same instance across calls.** Don't replace it — keep one `Feed` reference per surface and observe its `state` flows directly.
- **Use `viewModels { factory }` / `hiltViewModel()` for state holders.** Don't `remember { FeedsClient(...) }` or build `Feed` objects inside a Composable body — hoist them into a ViewModel that takes the client as a constructor arg.
- **`FeedId` group names are case-sensitive** and must match the feed groups configured on your Stream dashboard. `"User"` and `"user"` are different groups; the wrong case silently creates a new (empty) feed group.
- **Stories vs posts share the activity type, differentiated by `expiresAt`.** Filter with `ActivitiesFilterField.expiresAt.exists()` for stories and `.doesNotExist()` for regular posts so they don't mix in the same feed.
- **`client.activity(activityId, fid)` returns an `Activity` handle, not `ActivityData`.** `ActivityData` is the plain model from `FeedState.activities`. The `Activity` handle exposes the suspend operations (`get()`, `addComment(...)`, `addCommentReaction(...)`) and its own `ActivityState` for comments + poll.
- **`createNotificationActivity = true` is required** on `addActivityReaction`, `addComment`, `follow`, etc. for the action to surface in the target user's notification feed. Omitting it silently drops the notification.
- **`timeline:<userId>` does not automatically follow `user:<userId>`.** If you want the user to see their own posts in the timeline, call `timelineFeed.follow(FeedId("user", userId))` once after `getOrCreate()` (typically `createNotificationActivity = false` to avoid notifying yourself).
- **Never store the Stream API secret in the app.** Token minting must happen server-side or via the `stream` CLI for local dev (see [`../credentials.md`](../credentials.md)).
- **`INTERNET` permission is required.** Without it, `connect()` fails with cryptic socket errors.
- **Feeds is in closed alpha (V3).** Public APIs may change between versions — verify against the source on `https://github.com/GetStream/stream-feeds-android` if a property name in your training data disagrees with this file.
