# Feeds - Android Kotlin SDK Setup & Integration

Stream Feeds Android is a **headless data SDK** — there are no pre-built UI components. You build all Composables yourself; the SDK exposes observable `StateFlow`s on `FeedState` and `ActivityState` that drive your UI. This file covers Gradle setup, client setup, authentication, and the major data operations. For Compose blueprints, see [FEEDS-COMPOSE-blueprints.md](FEEDS-COMPOSE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no fake credentials, client lifetime, version lookup).

- **Blueprint** — Compose screen structure for common Feeds surfaces
- **Wiring** — SDK calls per feature with exact property paths
- **No pre-built UI** — every screen is custom; the SDK owns the data layer only

## Quick ref

- **Artifact:** `io.getstream:stream-feeds-android-client` via Maven Central
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

**Compose deps the blueprints rely on.** The default Android Studio "Empty Compose Activity" template ships Material3, the Compose BOM, and `lifecycle-runtime-ktx`, but **not** the three below. The blueprints in [`FEEDS-COMPOSE-blueprints.md`](FEEDS-COMPOSE-blueprints.md) won't compile without them:

- `androidx.lifecycle:lifecycle-runtime-compose`
- `androidx.lifecycle:lifecycle-viewmodel-compose`
- `androidx.compose.material:material-icons-extended`

Add them to the app module — via the version catalog if one is in use, otherwise inline in `app/build.gradle.kts`.

### Client Initialization

> **`FeedsClient` is bound to one user for its lifetime.** `FeedsClient(...)` is a top-level factory function that returns a `FeedsClient` interface implementation; the `User` and `tokenProvider` you pass in are fixed and cannot be swapped afterwards. To operate as a different user, `disconnect()` the current client and call `FeedsClient(...)` again with the new `User`. *You* own the reference; the SDK does not register a global accessor.

Because of this, construction happens at login. Model the lifecycle as a sealed `FeedsSession` so the `Connected` variant carries the client. A singleton **`FeedsSessionManager`** owns the state, the long-lived coroutine scope, *and* the connect/disconnect logic — ViewModels are thin translators that call `manager.connect(...)` / `manager.disconnect()` and observe `manager.session`. Provide the manager via `@Singleton` (Hilt) / `single { ... }` (Koin), or own it from `Application` for non-DI samples.

```kotlin
import android.content.Context
import android.content.pm.ApplicationInfo
import io.getstream.android.core.api.authentication.StreamTokenProvider
import io.getstream.android.core.api.model.value.StreamApiKey
import io.getstream.android.core.api.model.value.StreamToken
import io.getstream.android.core.api.model.value.StreamUserId
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.logging.HttpLoggingLevel
import io.getstream.feeds.android.client.api.logging.LoggingConfig
import io.getstream.feeds.android.client.api.model.FeedsConfig
import io.getstream.feeds.android.client.api.model.User
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

sealed interface FeedsSession {
    data object Disconnected : FeedsSession
    data object Connecting : FeedsSession
    data class Connected(val client: FeedsClient) : FeedsSession
    data class Failed(val message: String) : FeedsSession
}

class FeedsSessionManager(
    private val context: Context,
    private val apiKey: String,
) {
    // The manager's job is connect/disconnect — long-lived async work that must
    // outlive any one screen. Owning the scope here keeps lifetime explicit.
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    // Serializes ops so a switch-user flow (disconnect() then connect(next))
    // can't interleave — the second op waits for the first to finish.
    private val mutex = Mutex()

    private val _session = MutableStateFlow<FeedsSession>(FeedsSession.Disconnected)
    val session: StateFlow<FeedsSession> = _session.asStateFlow()

    fun connect(user: User, token: String) {
        scope.launch {
            mutex.withLock {
                if (_session.value is FeedsSession.Connecting || _session.value is FeedsSession.Connected) return@withLock
                _session.value = FeedsSession.Connecting
                val client = buildClient(user, token)
                client.connect().fold(
                    onSuccess = { _session.value = FeedsSession.Connected(client) },
                    onFailure = { _session.value = FeedsSession.Failed(it.message ?: "Connection failed") },
                )
            }
        }
    }

    fun disconnect() {
        scope.launch {
            mutex.withLock {
                val current = _session.value
                if (current is FeedsSession.Disconnected) return@withLock
                (current as? FeedsSession.Connected)?.client?.disconnect()
                _session.value = FeedsSession.Disconnected
            }
        }
    }

    private fun buildClient(user: User, token: String): FeedsClient {
        val tokenProvider = object : StreamTokenProvider {
            override suspend fun loadToken(userId: StreamUserId): StreamToken =
                StreamToken.fromString(token)
        }
        return FeedsClient(
            context = context.applicationContext,
            apiKey = StreamApiKey.fromString(apiKey),
            user = user,
            tokenProvider = tokenProvider,
            config = FeedsConfig(
                loggingConfig = LoggingConfig(
                    httpLoggingLevel = if ((context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0) HttpLoggingLevel.Body else HttpLoggingLevel.None,
                ),
            ),
        )
    }
}

class App : Application() {
    val sessionManager: FeedsSessionManager by lazy {
        FeedsSessionManager(this, apiKey = "<api_key_from_step_A>")
    }
}
```

Register the application class in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    ...>
```

`FeedsClient` does **not** auto-connect. The manager handles it — `client.connect()` is a suspend fun that returns `Result<StreamConnectedUser>`, and the manager flips `_session` to `Connected` / `Failed` based on the result.

For the full login + logout + user-switch flow, see [`FEEDS-COMPOSE-blueprints.md` → Login / Connect User Blueprint](FEEDS-COMPOSE-blueprints.md#login--connect-user-blueprint).

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

The signed-in user is fixed at construction time. To switch identity, drive both calls through the manager — `disconnect()` then `connect(nextUser, nextToken)`:

```kotlin
sessionManager.disconnect()                  // tears down current client, flips state to Disconnected
sessionManager.connect(nextUser, nextToken)  // builds a fresh FeedsClient and connects
```

Both calls are non-suspending (they enqueue onto the manager's internal scope).  UI observes `manager.session` and re-renders on each transition; no manual state writes from the call site.

If you need to chain the two synchronously (e.g. wait for disconnect to complete before connecting), expose a `suspend fun switchUser(user, token)` on the manager rather than coordinating from the call site.

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
import io.getstream.android.core.api.filter.doesNotExist
import io.getstream.feeds.android.client.api.state.query.ActivitiesFilterField
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

// Pagination — `limit: Int? = null` lets the server pick the page size; pass an Int to override.
if (feed.state.canLoadMoreActivities) {
    feed.queryMoreActivities()
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

`FileType` values: `Image` for images, `Other` for everything else (video, audio, generic files — there is no dedicated `Video` / `File` value). The SDK uploads each `FeedUploadPayload`, attaches the resulting URL to the activity, and fires the optional `attachmentUploadProgress` callback per file.

Picker results on Android come back as `content://` URIs, which aren't readable as plain `File`s. Copy each URI into `cacheDir` on `Dispatchers.IO`, then wrap `addActivity` in a `try { … } finally { files.forEach { it.delete() } }` so cancellation or failure mid-upload doesn't leak temp files.

```kotlin
val files = withContext(Dispatchers.IO) {
    uris.map { uri ->
        File(context.cacheDir, "att_${System.currentTimeMillis()}_${uri.hashCode()}.tmp")
            .also { out ->
                context.contentResolver.openInputStream(uri)?.use { input ->
                    out.outputStream().use(input::copyTo)
                }
            }
    }
}
try {
    feed.addActivity(/* request with attachmentUploads = files.map { FeedUploadPayload(it, FileType.Image) } */)
} finally {
    files.forEach { runCatching { it.delete() } }
}
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
// Add — returns Result<BookmarkData> for the new bookmark
feed.addBookmark(activityId = activity.id)

// Remove — also returns Result<BookmarkData> (the bookmark that was deleted), not Result<Unit>
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
activity.get()
// activityState.comments: StateFlow<List<ThreadedCommentData>>
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

`AggregatedActivityData` key fields: `activities: List<ActivityData>`, `activityCount`, `userCount`, `group`, `isRead`, `isSeen`, `isWatched`. `group` is unique within the list — use it as the `LazyColumn`/`LazyRow` key.

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
            httpLoggingLevel = HttpLoggingLevel.Body,
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

- **`FeedsClient` is bound to one user for its lifetime.** `FeedsClient(...)` is a top-level factory function; the `User` and `tokenProvider` you pass in are fixed and there is no method to change the signed-in user afterwards. The SDK does not register a global accessor either — *you* hold the reference, ideally inside a `FeedsSessionManager` (Hilt `@Singleton` / Koin `single` / Application field). To operate as a different user, drive `manager.disconnect()` then `manager.connect(nextUser, nextToken)` — the manager serializes the two so the new client doesn't overlap the old one.
- **Always `client.connect()` before any feed call.**  Connect once per user session, after the user logs in.
- **Don't overlap `FeedsClient` instances for the same user.** They will potentially desync state and waste a WebSocket connection.
- **`feed.state` is the same instance across calls.** Don't replace it — keep one `Feed` reference per surface and observe its `state` flows directly.
- **Use `viewModels { factory }` / `hiltViewModel()` for state holders.** Don't `remember { FeedsClient(...) }` or build `Feed` objects inside a Composable body — hoist them into a ViewModel that takes the client as a constructor arg.
- **`FeedId` group names are case-sensitive** and must match the feed groups configured on your Stream dashboard. `"User"` and `"user"` are different groups; the wrong case silently creates a new (empty) feed group.
- **`timeline:<userId>` does not automatically follow `user:<userId>`.** If you want the user to see their own posts in the timeline, call `timelineFeed.follow(FeedId("user", userId))` once after `getOrCreate()` (typically `createNotificationActivity = false` to avoid notifying yourself).
