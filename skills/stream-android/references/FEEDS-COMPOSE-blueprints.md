# Feeds Compose - Screen Blueprints

Load only the section you are implementing. For setup, client initialization, auth, and gotchas, see [FEEDS-COMPOSE.md](FEEDS-COMPOSE.md).

Per [`RULES.md`](../RULES.md) → *Blueprints are mandatory, on every turn*: any Stream Feeds screen, Composable, navigation handler, deep-link route, or UI customization must be preceded by reading the matching section below — including on follow-up turns inside an existing session.

> **Stream Feeds has no pre-built UI components.** Every screen here is custom Compose driven by `FeedState` / `ActivityState` `StateFlow`s. There is no drop-in `FeedScreen` and no Stream-supplied theme — render against your project's existing Compose theme (typically `MaterialTheme`).

---

## Request → Blueprint section

| User request signal | Section(s) to read |
|---|---|
| "set up Stream Feeds", "initialize FeedsClient", `Application` class, manifest wiring | [Application Class Blueprint](#application-class-blueprint) |
| "login screen", "connect user", token wiring | [Login / Connect User Blueprint](#login--connect-user-blueprint) |
| "navigate between screens", "skip login if connected", root host | [Root Navigation Blueprint](#root-navigation-blueprint) |
| "timeline", "feed screen", main activity list, "for-you" / following feed | [Timeline (Activity List) Blueprint](#timeline-activity-list-blueprint) |
| "activity row", post layout, like/repost/bookmark/comment buttons | [Activity Row Blueprint](#activity-row-blueprint) |
| "create post", "create activity", composer, attachments, story toggle | [Activity Composer Blueprint](#activity-composer-blueprint) |
| "comments screen", threaded comments, replies, comment reactions | [Comments Sheet Blueprint](#comments-sheet-blueprint) |
| "profile", follow / unfollow, follow requests, follow suggestions, who-to-follow | [Profile / Follow Graph Blueprint](#profile--follow-graph-blueprint) |
| "notifications", notification feed, badge, mark-as-read | [Notifications Blueprint](#notifications-blueprint) |
| "stories strip", create story, story viewer | [Stories Strip Blueprint](#stories-strip-blueprint) |

If the request is something not covered, do not fabricate APIs — say the blueprint is not bundled and fall back per [`RULES.md`](../RULES.md).

---

## Application Class Blueprint

`FeedsClient` is bound to one user for its lifetime — the `User` and `tokenProvider` are fixed at construction and cannot be swapped afterwards. So the `Application` does **not** build the client itself; it holds a slot that the login flow fills once the user is known. To switch users you `disconnect()` and replace the slot.

```kotlin
package com.example.streamfeeds

import android.app.Application
import io.getstream.feeds.android.client.api.FeedsClient

class App : Application() {

    /**
     * The current logged-in user's FeedsClient, or null if no user is signed in.
     * Set by the login flow after constructing a client with the user's User + tokenProvider.
     * Cleared on logout. Replace (don't mutate) when switching users.
     */
    @Volatile
    var feedsClient: FeedsClient? = null
}
```

Register it in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    android:label="@string/app_name">
    <!-- activities ... -->
</application>

<uses-permission android:name="android.permission.INTERNET" />
```

A small builder kept alongside `App` (or in a Hilt `@Singleton` provider) keeps the construction logic in one place — login calls into it, logout disposes the result:

```kotlin
import android.content.Context
import io.getstream.android.core.api.authentication.StreamTokenProvider
import io.getstream.android.core.api.model.value.StreamApiKey
import io.getstream.android.core.api.model.value.StreamToken
import io.getstream.android.core.api.model.value.StreamUserId
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.logging.HttpLoggingLevel
import io.getstream.feeds.android.client.api.logging.LoggingConfig
import io.getstream.feeds.android.client.api.model.FeedsConfig
import io.getstream.feeds.android.client.api.model.User

object FeedsClientFactory {
    fun create(
        context: Context,
        apiKey: String,
        user: User,
        token: String,
    ): FeedsClient {
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
                    httpLoggingLevel = if (BuildConfig.DEBUG) HttpLoggingLevel.Body else HttpLoggingLevel.None,
                ),
            ),
        )
    }
}
```

**Wiring:**
- The `feedsClient` slot starts `null`. Don't render any feed Composable while it is — gate the UI on connection state from a ViewModel (see the [Root Navigation Blueprint](#root-navigation-blueprint)).
- Login does: `App.feedsClient = FeedsClientFactory.create(...)` → `feedsClient.connect()`. Logout does: `feedsClient.disconnect()` → `App.feedsClient = null`.
- Switching users: `disconnect()` the old client, set `App.feedsClient` to a freshly-built client for the new user, then `connect()`. Don't try to reuse the old instance.
- For a Hilt project, replace the slot with a `@Singleton`-scoped state holder (e.g. a `MutableStateFlow<FeedsClient?>`) so ViewModels can collect the current client reactively.

---

## Login / Connect User Blueprint

Login is the place where the `FeedsClient` is **constructed**, not just connected. The `Application` holds an empty slot until login fills it with a client built from the chosen user's `User` + token. `connect()` runs immediately after.

```kotlin
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import io.getstream.feeds.android.client.api.model.User
import kotlinx.coroutines.launch

class LoginActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = application as App
        setContent {
            MaterialTheme {
                LoginScreen(
                    onConnect = { userId, displayName, token ->
                        lifecycleScope.launch {
                            // Replace any prior client first.
                            app.feedsClient?.disconnect()

                            val client = FeedsClientFactory.create(
                                context = applicationContext,
                                apiKey = "your_api_key",
                                user = User(id = userId, name = displayName),
                                token = token,
                            )
                            client.connect().fold(
                                onSuccess = {
                                    app.feedsClient = client
                                    startActivity(Intent(this@LoginActivity, FeedsActivity::class.java))
                                    finish()
                                },
                                onFailure = { /* show error, leave app.feedsClient null */ },
                            )
                        }
                    },
                )
            }
        }
    }
}

@Composable
fun LoginScreen(onConnect: (userId: String, displayName: String, token: String) -> Unit) {
    var userId by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }
    var isConnecting by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Stream Feeds", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        OutlinedTextField(value = userId, onValueChange = { userId = it }, label = { Text("User ID") })
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = displayName, onValueChange = { displayName = it }, label = { Text("Display name") })
        Spacer(Modifier.height(16.dp))
        Button(
            enabled = userId.isNotBlank() && !isConnecting,
            onClick = {
                isConnecting = true
                onConnect(userId, displayName.ifBlank { userId }, "your_static_token_here")
            },
        ) {
            if (isConnecting) CircularProgressIndicator(strokeWidth = 2.dp) else Text("Connect")
        }
    }
}
```

**Wiring:**
- The client is **constructed at login**, not in `Application.onCreate()`. There is no "connect a different user" path on an existing `FeedsClient` — see the *Application Class Blueprint* for why.
- `connect()` is `suspend`. Call it from an owned scope (`lifecycleScope`, `viewModelScope`) — never inside a Composable body.
- For a real app, source the user id and token from your auth store / DataStore in a ViewModel; pass them down rather than letting the user type a token.
- For an expiring token, swap the static `StreamToken.fromString(...)` inside `FeedsClientFactory.create(...)` for a `StreamTokenProvider` that fetches from your backend.

---

## Root Navigation Blueprint

Gate the app on connection state. Because `FeedsClient` is bound to one user for its lifetime (see [Application Class Blueprint](#application-class-blueprint)), the ViewModel owns construction at login and disposes the reference on logout — there is no pre-built client to "connect" later.

```kotlin
import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.User
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class RootViewModel(
    private val app: App,
    private val apiKey: String,
) : ViewModel() {

    enum class Stage { Disconnected, Connecting, Connected }

    private val _stage = MutableStateFlow(Stage.Disconnected)
    val stage = _stage.asStateFlow()

    val currentClient: FeedsClient?
        get() = app.feedsClient

    fun login(userId: String, displayName: String, token: String) {
        if (_stage.value != Stage.Disconnected) return
        viewModelScope.launch {
            _stage.value = Stage.Connecting
            app.feedsClient?.disconnect()
            val client = FeedsClientFactory.create(
                context = app.applicationContext,
                apiKey = apiKey,
                user = User(id = userId, name = displayName),
                token = token,
            )
            client.connect().fold(
                onSuccess = {
                    app.feedsClient = client
                    _stage.value = Stage.Connected
                },
                onFailure = {
                    app.feedsClient = null
                    _stage.value = Stage.Disconnected
                },
            )
        }
    }

    fun logout() {
        viewModelScope.launch {
            app.feedsClient?.disconnect()
            app.feedsClient = null
            _stage.value = Stage.Disconnected
        }
    }
}

@Composable
fun RootScreen(viewModel: RootViewModel) {
    val stage by viewModel.stage.collectAsStateWithLifecycle()
    when (stage) {
        RootViewModel.Stage.Disconnected -> LoginScreen(onConnect = viewModel::login)
        RootViewModel.Stage.Connecting   -> Box(Modifier.fillMaxSize(), Alignment.Center) { CircularProgressIndicator() }
        RootViewModel.Stage.Connected    -> {
            val client = viewModel.currentClient ?: return
            FeedsRoot(client = client, onLogout = viewModel::logout)
        }
    }
}
```

**Wiring:**
- The ViewModel reads/writes `app.feedsClient` (the slot from the [Application Class Blueprint](#application-class-blueprint)). For a Hilt project, replace this with a `@Singleton`-scoped `MutableStateFlow<FeedsClient?>` that ViewModels collect.
- `LoginScreen`'s `onConnect = viewModel::login` matches the `(userId, displayName, token) -> Unit` signature in the [Login blueprint](#login--connect-user-blueprint).
- For a single-Activity Compose project, host this inside a `NavHost` and route to feeds destinations after `Stage.Connected`.

---

## Timeline (Activity List) Blueprint

The timeline feed (`timeline:<userId>`) shows posts from feeds the user follows. Build the `Feed` once in a ViewModel and observe its state.

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.model.FeedInputData
import io.getstream.feeds.android.client.api.model.FeedMemberRequestData
import io.getstream.feeds.android.client.api.model.FeedVisibility
import io.getstream.feeds.android.client.api.state.Feed
import io.getstream.feeds.android.client.api.state.query.FeedQuery
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

class TimelineViewModel(private val client: FeedsClient) : ViewModel() {

    val timeline: Feed = client.feed(
        FeedQuery(
            fid = FeedId("timeline", client.user.id),
            data = FeedInputData(
                members = listOf(FeedMemberRequestData(client.user.id)),
                visibility = FeedVisibility.Public,
            ),
        )
    )
    val ownTimeline: Feed = client.feed(FeedId("user", client.user.id))

    init {
        viewModelScope.launch {
            timeline.getOrCreate()
            // Ensure timeline:<user_id> follows user:<user_id> so own posts show up.
            // Skip this if your backend already handles that. This is just a client-side fallback.
            if (timeline.state.following.first().none { it.targetFeed.fid == ownTimeline.fid }) {
                timeline.follow(ownTimeline.fid, createNotificationActivity = false)
            }
        }
    }

    fun loadMore() {
        if (!timeline.state.canLoadMoreActivities) return
        viewModelScope.launch { timeline.queryMoreActivities() }
    }

    fun refresh() {
        viewModelScope.launch { timeline.getOrCreate() }
    }
}
```

```kotlin
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable
fun TimelineScreen(
    viewModel: TimelineViewModel,
    onCommentClick: (activityId: String, feedId: String) -> Unit,
    onCreatePostClick: () -> Unit,
) {
    val activities by viewModel.timeline.state.activities.collectAsStateWithLifecycle()
    val listState = rememberLazyListState()

    // Pagination trigger
    LaunchedEffect(listState) {
        snapshotFlow { listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index }
            .collect { lastVisible ->
                if (lastVisible != null && lastVisible >= activities.lastIndex - 2) {
                    viewModel.loadMore()
                }
            }
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = onCreatePostClick) { Icon(Icons.Default.Add, "Post") }
        },
    ) { padding ->
        LazyColumn(state = listState, modifier = Modifier.padding(padding)) {
            items(activities, key = { it.id }) { activity ->
                ActivityRow(
                    activity = activity,
                    feed = viewModel.timeline,
                    currentUserId = viewModel.timeline.state.feedQuery.fid.id,
                    onCommentClick = { onCommentClick(activity.id, viewModel.timeline.fid.rawValue) },
                )
                HorizontalDivider()
            }
        }
    }
}
```

**Wiring:**
- Build the `Feed` object **once** in `init` of the ViewModel. Don't recreate it per recomposition.
- `feed.state.activities` is a `StateFlow<List<ActivityData>>`. Use `collectAsStateWithLifecycle()`.
- `getOrCreate()` is idempotent — call it again from a swipe-to-refresh.
- The `timeline:<userId>` feed does **not** automatically follow `user:<userId>`. Add the self-follow once after `getOrCreate()` if the user should see their own posts.

---

## Activity Row Blueprint

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.getstream.feeds.android.client.api.model.ActivityData
import io.getstream.feeds.android.client.api.state.Feed
import io.getstream.feeds.android.network.models.AddReactionRequest
import kotlinx.coroutines.launch

@Composable
fun ActivityRow(
    activity: ActivityData,
    feed: Feed,
    currentUserId: String,
    onCommentClick: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    val base = activity.parent ?: activity
    val hasLiked = activity.ownReactions.any { it.type == "heart" }
    val likeCount = activity.reactionGroups["heart"]?.count ?: 0
    val isBookmarked = activity.ownBookmarks.isNotEmpty()

    Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)) {
        if (activity.parent != null) {
            Text(
                text = "${activity.user.name ?: activity.user.id} reposted",
                style = MaterialTheme.typography.bodySmall,
            )
            Spacer(Modifier.height(4.dp))
        }

        Row(verticalAlignment = Alignment.Top) {
            // Avatar (use a Coil AsyncImage in real code)
            Box(Modifier.size(40.dp))
            Spacer(Modifier.width(12.dp))
            Column {
                Text(base.user.name ?: base.user.id, style = MaterialTheme.typography.titleSmall)
                base.text?.takeIf { it.isNotBlank() }?.let { Text(it) }
            }
        }

        Spacer(Modifier.height(8.dp))

        Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
            TextButton(onClick = onCommentClick) {
                Icon(Icons.Default.ChatBubbleOutline, null)
                Spacer(Modifier.width(4.dp))
                Text("${activity.commentCount}")
            }

            TextButton(onClick = {
                scope.launch {
                    if (hasLiked) {
                        feed.deleteActivityReaction(activity.id, "heart")
                    } else {
                        feed.addActivityReaction(
                            activity.id,
                            AddReactionRequest(type = "heart", createNotificationActivity = true),
                        )
                    }
                }
            }) {
                Icon(if (hasLiked) Icons.Default.Favorite else Icons.Default.FavoriteBorder, null)
                Spacer(Modifier.width(4.dp))
                Text("$likeCount")
            }

            TextButton(onClick = {
                scope.launch { feed.repost(activity.id, text = null) }
            }) {
                Icon(Icons.Default.Repeat, null)
                Spacer(Modifier.width(4.dp))
                Text("${activity.shareCount}")
            }

            IconButton(onClick = {
                scope.launch {
                    if (isBookmarked) feed.deleteBookmark(activity.id) else feed.addBookmark(activity.id)
                }
            }) {
                Icon(if (isBookmarked) Icons.Default.Bookmark else Icons.Default.BookmarkBorder, null)
            }
        }
    }
}
```

**Wiring:**
- Reactions live on `activity.ownReactions` (current user's) and `activity.reactionGroups[type]?.count` (totals). Compute booleans inline; don't cache them across recompositions.
- Reposts surface as activities with `parent != null`. Render the parent's text/attachments and a small "reposted" header.
- Use `rememberCoroutineScope()` for one-off mutating actions inside a row. For longer-lived flows (composing, editing) hoist to a ViewModel.

---

## Activity Composer Blueprint

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.getstream.feeds.android.client.api.file.FeedUploadPayload
import io.getstream.feeds.android.client.api.file.FileType
import io.getstream.feeds.android.client.api.model.FeedAddActivityRequest
import io.getstream.feeds.android.client.api.state.Feed
import java.io.File
import kotlin.time.Clock
import kotlin.time.Duration.Companion.days
import kotlin.time.ExperimentalTime
import kotlinx.coroutines.launch

@OptIn(ExperimentalTime::class)
@Composable
fun ActivityComposerSheet(
    postingFeed: Feed,
    onDismiss: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    var text by remember { mutableStateOf("") }
    var attachments by remember { mutableStateOf<List<File>>(emptyList()) }
    var postAsStory by remember { mutableStateOf(false) }
    var posting by remember { mutableStateOf(false) }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                label = { Text("What's happening?") },
                modifier = Modifier.fillMaxWidth().heightIn(min = 120.dp),
            )

            Row(verticalAlignment = Alignment.CenterVertically) {
                Switch(checked = postAsStory, onCheckedChange = { postAsStory = it })
                Spacer(Modifier.width(8.dp))
                Text("Post as Story (24h)")
            }

            Button(
                enabled = text.isNotBlank() && !posting,
                onClick = {
                    posting = true
                    scope.launch {
                        val expiresAt = if (postAsStory) {
                            Clock.System.now().plus(1.days).toString()
                        } else null

                        postingFeed.addActivity(
                            request = FeedAddActivityRequest(
                                type = "post",
                                text = text,
                                feeds = listOf(postingFeed.fid.rawValue),
                                expiresAt = expiresAt,
                                attachmentUploads = attachments.map {
                                    FeedUploadPayload(file = it, type = FileType.Image)
                                },
                            ),
                            attachmentUploadProgress = { _, _ -> /* optional */ },
                        )
                        posting = false
                        onDismiss()
                    }
                },
            ) { Text(if (posting) "Posting…" else "Post") }
        }
    }
}
```

**Wiring:**
- Post stories to a separate `Feed` (`stories:<userId>` or whatever group your dashboard configures), not to the timeline. Stories are differentiated from posts by `expiresAt`.
- For attachments: `FeedUploadPayload(file = ..., type = FileType.Image)` for images, `FileType.Other` for everything else (video, audio, generic files — there is no dedicated `Video` / `File` value). The SDK uploads + attaches the URL automatically; the optional `attachmentUploadProgress` callback fires per file.
- Post-time URI handling (Android `content://` URIs) needs a copy-to-cache step before passing the `File` — use `application.contentResolver.openInputStream(uri)` and write to `cacheDir`.
- `kotlin.time.Clock` was stabilized in Kotlin 2.1; on older toolchains either keep the `@OptIn(ExperimentalTime::class)` annotation or fall back to `java.time.Instant.now().plusSeconds(86_400).toString()` (or `kotlinx-datetime`). All three produce the ISO-8601 string the wire format expects.
- For longer flows, hoist text/attachments/state into a ViewModel (the sample app does this in `FeedViewModel.onContentSubmit`).

---

## Comments Sheet Blueprint

Comments live on an `Activity` handle obtained from the client. `ActivityState.comments: StateFlow<List<ThreadedCommentData>>` holds threaded comments after `activity.get()` resolves.

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.model.ThreadedCommentData
import io.getstream.feeds.android.client.api.model.request.ActivityAddCommentRequest
import io.getstream.feeds.android.client.api.state.Activity
import io.getstream.feeds.android.network.models.AddCommentReactionRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class CommentsViewModel(
    client: FeedsClient,
    activityId: String,
    feedId: FeedId,
) : ViewModel() {

    val activity: Activity = client.activity(activityId, feedId)
    val currentUserId: String = client.user.id

    private val _replyParentId = MutableStateFlow<String?>(null)
    val replyParentId = _replyParentId.asStateFlow()

    init {
        viewModelScope.launch { activity.get() }
    }

    fun loadMore() {
        viewModelScope.launch { activity.queryMoreComments() }
    }

    fun startReply(parentId: String?) { _replyParentId.value = parentId }

    fun submit(text: String) {
        if (text.isBlank()) return
        viewModelScope.launch {
            activity.addComment(
                ActivityAddCommentRequest(
                    comment = text,
                    activityId = activity.activityId,
                    parentId = _replyParentId.value,
                    createNotificationActivity = true,
                )
            )
            _replyParentId.value = null
        }
    }

    fun toggleLike(comment: ThreadedCommentData) {
        viewModelScope.launch {
            if (comment.ownReactions.any { it.type == "heart" }) {
                activity.deleteCommentReaction(comment.id, "heart")
            } else {
                activity.addCommentReaction(
                    comment.id,
                    AddCommentReactionRequest(type = "heart", createNotificationActivity = true),
                )
            }
        }
    }
}
```

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

@Composable
fun CommentsSheet(viewModel: CommentsViewModel, onDismiss: () -> Unit) {
    val comments by viewModel.activity.state.comments.collectAsStateWithLifecycle()
    val replyParent by viewModel.replyParentId.collectAsStateWithLifecycle()
    var text by remember { mutableStateOf("") }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(Modifier.fillMaxWidth().heightIn(max = 600.dp)) {
            LazyColumn(Modifier.weight(1f)) {
                items(comments, key = { it.id }) { comment ->
                    CommentRow(
                        comment = comment,
                        currentUserId = viewModel.currentUserId,
                        onReply = { viewModel.startReply(comment.id) },
                        onToggleLike = { viewModel.toggleLike(comment) },
                    )
                    comment.replies?.forEach { reply ->
                        Box(Modifier.padding(start = 32.dp)) {
                            CommentRow(
                                comment = reply,
                                currentUserId = viewModel.currentUserId,
                                onReply = { viewModel.startReply(comment.id) },
                                onToggleLike = { viewModel.toggleLike(reply) },
                            )
                        }
                    }
                }
            }

            Row(
                Modifier.fillMaxWidth().padding(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                OutlinedTextField(
                    value = text,
                    onValueChange = { text = it },
                    placeholder = { Text(if (replyParent != null) "Reply…" else "Add a comment…") },
                    modifier = Modifier.weight(1f),
                )
                IconButton(
                    enabled = text.isNotBlank(),
                    onClick = {
                        viewModel.submit(text)
                        text = ""
                    },
                ) { Icon(Icons.Default.Send, null) }
            }
        }
    }
}

@Composable
private fun CommentRow(
    comment: ThreadedCommentData,
    currentUserId: String,
    onReply: () -> Unit,
    onToggleLike: () -> Unit,
) {
    val hasLiked = comment.ownReactions.any { it.type == "heart" }
    Row(Modifier.fillMaxWidth().padding(12.dp)) {
        Box(Modifier.size(32.dp)) // avatar placeholder
        Spacer(Modifier.width(8.dp))
        Column(Modifier.weight(1f)) {
            Text(comment.user.name ?: comment.user.id, style = MaterialTheme.typography.titleSmall)
            comment.text?.let { Text(it) }
            Row {
                TextButton(onClick = onReply) { Text("Reply") }
                TextButton(onClick = onToggleLike) {
                    Icon(if (hasLiked) Icons.Default.Favorite else Icons.Default.FavoriteBorder, null)
                    Spacer(Modifier.width(4.dp))
                    Text("${comment.reactionGroups["heart"]?.count ?: 0}")
                }
            }
        }
    }
}
```

**Wiring:**
- `activity.get()` populates `activityState.comments` (initial page). Call `activity.queryMoreComments()` when scrolling to the bottom.
- `parentId` on `addComment` drives reply threading: `null` for top-level, set to the parent comment id for a reply. Replies arrive under `comment.replies`.
- `client.activity(...)` returns the `Activity` handle — distinct from `ActivityData`. Build it once in the ViewModel `init`.

---

## Profile / Follow Graph Blueprint

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.model.FeedSuggestionData
import io.getstream.feeds.android.client.api.state.Feed
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ProfileViewModel(client: FeedsClient) : ViewModel() {
    val feed: Feed = client.feed(FeedId("user", client.user.id))

    private val _suggestions = MutableStateFlow<List<FeedSuggestionData>>(emptyList())
    val suggestions = _suggestions.asStateFlow()

    init {
        viewModelScope.launch {
            feed.getOrCreate()
            _suggestions.value = feed.queryFollowSuggestions(limit = 10).getOrDefault(emptyList())
        }
    }

    fun follow(target: FeedId) = viewModelScope.launch {
        feed.follow(target, createNotificationActivity = true)
    }
    fun unfollow(target: FeedId) = viewModelScope.launch { feed.unfollow(target) }
    fun accept(source: FeedId) = viewModelScope.launch { feed.acceptFollow(source) }
    fun reject(source: FeedId) = viewModelScope.launch { feed.rejectFollow(source) }
}

@Composable
fun ProfileScreen(viewModel: ProfileViewModel) {
    val following by viewModel.feed.state.following.collectAsStateWithLifecycle()
    val followers by viewModel.feed.state.followers.collectAsStateWithLifecycle()
    val requests by viewModel.feed.state.followRequests.collectAsStateWithLifecycle()
    val suggestions by viewModel.suggestions.collectAsStateWithLifecycle()

    LazyColumn(Modifier.fillMaxSize()) {
        if (requests.isNotEmpty()) {
            item { SectionHeader("Follow Requests") }
            items(requests, key = { it.sourceFeed.fid.rawValue }) { req ->
                Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(req.sourceFeed.createdBy?.name ?: req.sourceFeed.fid.id, modifier = Modifier.weight(1f))
                    Button(onClick = { viewModel.accept(req.sourceFeed.fid) }) { Text("Accept") }
                    Spacer(Modifier.width(8.dp))
                    OutlinedButton(onClick = { viewModel.reject(req.sourceFeed.fid) }) { Text("Reject") }
                }
            }
        }

        item { SectionHeader("Following (${following.size})") }
        items(following, key = { it.targetFeed.fid.rawValue }) { f ->
            Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(f.targetFeed.createdBy?.name ?: f.targetFeed.fid.id, modifier = Modifier.weight(1f))
                OutlinedButton(onClick = { viewModel.unfollow(f.targetFeed.fid) }) { Text("Unfollow") }
            }
        }

        item { SectionHeader("Followers (${followers.size})") }
        items(followers, key = { it.sourceFeed.fid.rawValue }) { f ->
            Text(
                f.sourceFeed.createdBy?.name ?: f.sourceFeed.fid.id,
                Modifier.fillMaxWidth().padding(12.dp),
            )
        }

        if (suggestions.isNotEmpty()) {
            item { SectionHeader("Who to Follow") }
            items(suggestions, key = { it.feed.fid.rawValue }) { suggestion ->
                Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(suggestion.feed.createdBy?.name ?: suggestion.feed.fid.id, modifier = Modifier.weight(1f))
                    Button(onClick = { viewModel.follow(suggestion.feed.fid) }) { Text("Follow") }
                }
            }
        }
    }
}

@Composable
private fun SectionHeader(text: String) {
    Text(text, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(16.dp))
}
```

**Wiring:**
- All follow operations live on the `Feed` for the **current user** (`user:<currentUserId>`), not the target user's feed.
- `state.following` / `state.followers` / `state.followRequests` are kept in sync by WebSocket events — no need to refetch after a `follow` / `unfollow` call.
- `queryFollowSuggestions(limit)` returns `FeedSuggestionData` (feed + recommendation score + reason). Trigger it once after the feed is loaded.

---

## Notifications Blueprint

The notification feed (`notification:<userId>`) surfaces grouped activity via `aggregatedActivities` instead of `activities`. `notificationStatus.unread` / `unseen` drive the badge count.

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.state.Feed
import io.getstream.feeds.android.network.models.MarkActivityRequest
import kotlinx.coroutines.launch

class NotificationsViewModel(client: FeedsClient) : ViewModel() {
    val feed: Feed = client.feed(FeedId("notification", client.user.id))

    init { viewModelScope.launch { feed.getOrCreate() } }

    fun markAllRead() = viewModelScope.launch {
        feed.markActivity(MarkActivityRequest(markAllRead = true))
    }
    fun markRead(activityId: String) = viewModelScope.launch {
        feed.markActivity(MarkActivityRequest(markRead = listOf(activityId)))
    }
}

@Composable
fun NotificationsScreen(viewModel: NotificationsViewModel) {
    val aggregated by viewModel.feed.state.aggregatedActivities.collectAsStateWithLifecycle()
    val status by viewModel.feed.state.notificationStatus.collectAsStateWithLifecycle()

    Scaffold(topBar = {
        TopAppBar(
            title = { Text("Notifications") },
            actions = {
                if ((status?.unread ?: 0) > 0) {
                    TextButton(onClick = viewModel::markAllRead) { Text("Mark all read") }
                }
            },
        )
    }) { padding ->
        LazyColumn(Modifier.padding(padding)) {
            items(aggregated, key = { it.id }) { group ->
                val first = group.activities.firstOrNull()
                val isRead = group.isRead == true
                Row(
                    Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(
                            text = displayText(group),
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        first?.createdAt?.let {
                            Text(
                                text = it.toString(),
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                    if (!isRead) {
                        Box(Modifier.size(8.dp)) // unread dot
                    }
                }
            }
        }
    }
}

private fun displayText(group: io.getstream.feeds.android.client.api.model.AggregatedActivityData): String {
    val names = group.activities.take(2).map { it.user.name ?: it.user.id }.joinToString(" and ")
    val extra = if (group.userCount > 2) " and ${group.userCount - 2} others" else ""
    return when (group.group) {
        "react"   -> "$names$extra reacted to your post"
        "comment" -> "$names$extra commented on your post"
        "follow"  -> "$names$extra followed you"
        else      -> "$names$extra ${group.group} your post"
    }
}
```

**Wiring:**
- Use `aggregatedActivities`, **not** `activities`, for notification feeds.
- `notificationStatus.unread` is the unread badge; `unseen` is "user has not opened the notifications screen yet".
- `markActivity(markAllRead = true)` clears all unread; `markActivity(markRead = listOf(id))` clears one. Use `markSeen` / `markAllSeen` to clear the *unseen* count without marking activities as read.

---

## Stories Strip Blueprint

Stories are activities with `expiresAt` set, posted to a separate feed group (the sample app uses `story:<userId>` for own stories and `stories:<userId>` for the aggregated stories feed of followed users).

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.border
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import io.getstream.feeds.android.client.api.model.AggregatedActivityData

@Composable
fun StoriesStrip(
    ownStories: List<io.getstream.feeds.android.client.api.model.ActivityData>,
    storyGroups: List<AggregatedActivityData>,
    onCreateStoryClick: () -> Unit,
    onOpenStories: (List<io.getstream.feeds.android.client.api.model.ActivityData>) -> Unit,
) {
    LazyRow(contentPadding = PaddingValues(8.dp)) {
        item {
            StoryAvatar(
                hasUnwatched = ownStories.any { it.isWatched != true },
                onClick = if (ownStories.isEmpty()) onCreateStoryClick else { -> onOpenStories(ownStories) },
            )
        }
        items(storyGroups, key = { it.id }) { group ->
            StoryAvatar(
                hasUnwatched = group.activities.any { it.isWatched != true },
                onClick = { onOpenStories(group.activities) },
                modifier = Modifier.padding(horizontal = 8.dp),
            )
        }
    }
}

@Composable
private fun StoryAvatar(
    hasUnwatched: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val color = if (hasUnwatched)
        MaterialTheme.colorScheme.primary
    else
        MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)

    Box(
        modifier = modifier
            .size(72.dp)
            .clip(CircleShape)
            .border(3.dp, color, CircleShape),
    )
}
```

**Wiring:**
- The own-stories feed is filtered to `expiresAt.exists()` — build it via `FeedQuery(activityFilter = ActivitiesFilterField.expiresAt.exists())`.
- The aggregated stories feed surfaces `aggregatedActivities` (one group per user). Use `group.activities` for the actual stories to display in the viewer.
- Mark a story as watched after the user views it: `storiesFeed.markActivity(MarkActivityRequest(markWatched = listOf(storyId)))`.
