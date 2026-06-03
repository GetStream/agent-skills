# Feeds Compose - Screen Blueprints

Load only the section you are implementing. For setup, client initialization, auth, and gotchas, see [FEEDS-COMPOSE.md](FEEDS-COMPOSE.md).

Per [`RULES.md`](../RULES.md) → *Blueprints are mandatory, on every turn*: any Stream Feeds screen, Composable, navigation handler, deep-link route, or UI customization must be preceded by reading the matching section below — including on follow-up turns inside an existing session.

> **Stream Feeds has no pre-built UI components.** Every screen here is custom Compose driven by `FeedState` / `ActivityState` `StateFlow`s. There is no drop-in `FeedScreen` and no Stream-supplied theme — render against your project's existing Compose theme (typically `MaterialTheme`).

> **DI shape.** `FeedsClient` is not in the DI graph — it only exists after `connect()` succeeds, so `@Inject FeedsClient` has nothing to bind to. Inject `FeedsSessionManager` as a singleton (Hilt `@Singleton`, Koin `single`); for child VMs that need the `FeedsClient`, pass it from the `is FeedsSession.Connected` branch via this file's `companion object factory(client)` pattern, Hilt `@AssistedInject` keyed on `client`, or Koin `parametersOf(client)`. See the [Root Navigation Blueprint](#root-navigation-blueprint) for the call-site code.

---

## Request → Blueprint section

| User request signal | Section(s) to read |
|---|---|
| "set up Stream Feeds", "initialize FeedsClient", session lifecycle, `Application` class, manifest wiring | [Session Manager Blueprint](#session-manager-blueprint) — foundational, read first for any path that touches `FeedsClient` |
| "single demo user", "no login screen", "auto-connect on launch" | [Auto-Connect (Single Demo User) Blueprint](#auto-connect-single-demo-user-blueprint) — uses the Session Manager Blueprint |
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

## Session Manager Blueprint

This is the foundational blueprint — every path that touches `FeedsClient` (login, root nav, every screen ViewModel) reads from `manager.session`. Read this first.

`FeedsClient` is bound to one user for its lifetime — the `User` and `tokenProvider` are fixed at construction and cannot be swapped afterwards. So construction happens at login, not in `Application.onCreate()`. To switch users you `disconnect()` and replace the client.

Model the lifecycle as a sealed `FeedsSession` so the `Connected` variant carries the client — `when (session)` becomes exhaustive and the type system rules out "connected but null client". A singleton **`FeedsSessionManager`** owns the session state, the long-lived coroutine scope, and the connect/disconnect logic. ViewModels become thin: they translate view events into manager calls and observe `manager.session`. The manager owns its own scope (justified — that's the entity whose responsibility *is* long-lived async work). Provide it via `@Singleton` (Hilt) / `single { ... }` (Koin), or own it from `Application` for non-DI samples.

```kotlin
package com.example.streamfeeds

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
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val mutex = Mutex()

    private val _session = MutableStateFlow<FeedsSession>(FeedsSession.Disconnected)
    val session: StateFlow<FeedsSession> = _session.asStateFlow()

    fun connect(user: User, token: String) {
        scope.launch {
            mutex.withLock {
                // Allow retry from Failed/Disconnected; ignore double-taps mid-flight.
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

> Under Hilt, drop `App.sessionManager` and annotate the manager `@Singleton class FeedsSessionManager @Inject constructor(@ApplicationContext context: Context, @Named("streamApiKey") apiKey: String)`. ViewModels `@Inject` it directly. Under Koin, `single { FeedsSessionManager(androidContext(), getProperty("streamApiKey")) }`.

Register the application class in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    android:label="@string/app_name">
    <!-- activities ... -->
</application>
```

For an expiring (backend-issued) token, replace the static `StreamToken.fromString(token)` inside `buildClient(...)` with a `StreamTokenProvider` that calls your auth service in `loadToken(userId)`. The SDK re-invokes `loadToken` on expiry — see [FEEDS-COMPOSE.md → User Authentication](FEEDS-COMPOSE.md#user-authentication).

**Wiring:**
- The manager is the *only* writer of `_session`. ViewModels never set state directly — they call `manager.connect(...)` / `manager.disconnect()` and observe `manager.session`.
- `manager.session` starts `Disconnected`. Composables observe via `collectAsStateWithLifecycle()` and `when`-switch on the variant; the `Connected` branch destructures `client` from the state, so there is no nullable-client path to handle.
- Login transitions: `Disconnected` → `Connecting` → `Connected(client)` on success or `Failed(message)` on error.
- Logout: the manager `disconnect()`s the current client and flips state to `Disconnected` in a single launch on its own scope, so the operation completes even if the calling screen is gone.

---

## Auto-Connect (Single Demo User) Blueprint

Uses the [Session Manager Blueprint](#session-manager-blueprint). Skip `LoginScreen` and auto-connect a hardcoded user from `Application.onCreate()`. Compose then collects `manager.session` and renders `Connecting` / `Connected` / `Failed` directly — there's no `Login` route in the nav graph.

```kotlin
class App : Application() {
    val sessionManager: FeedsSessionManager by lazy {
        FeedsSessionManager(this, apiKey = "<api_key_from_step_A>")
    }

    override fun onCreate() {
        super.onCreate()
        sessionManager.connect(
            user = User(id = "demo-user", name = "Demo User"),
            token = "<static_dev_token>",
        )
    }
}
```

For real apps, issue tokens from your backend instead of hardcoding — see [FEEDS-COMPOSE.md → User Authentication](FEEDS-COMPOSE.md#user-authentication).

---

## Login / Connect User Blueprint

`LoginScreen` is a stateless Composable. It takes `isConnecting`, `error`, and `onConnect` from above and renders the form — all the connect/disconnect logic lives in `RootViewModel` (see the [Root Navigation Blueprint](#root-navigation-blueprint)).

```kotlin
@Composable
fun LoginScreen(
    isConnecting: Boolean,
    error: String?,
    onConnect: (userId: String, displayName: String, token: String) -> Unit,
) {
    var userId by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }

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
            onClick = { onConnect(userId, displayName.ifBlank { userId }, "your_static_token_here") },
        ) {
            if (isConnecting) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    strokeWidth = 2.dp,
                    color = LocalContentColor.current,
                )
            } else {
                Text("Connect")
            }
        }
        error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
        }
    }
}
```

**Wiring:**
- The Composable is dumb — no `lifecycleScope`, no client construction, no `sessionManager` reference. `RootScreen` passes `viewModel::onLoginClicked` as `onConnect` and drives `isConnecting` from the `Connecting` variant (see the Root Navigation Blueprint).
- For a real app, source the user id from your auth store / DataStore in the ViewModel; treat the on-screen text fields as a dev-time stand-in.
- For an expiring token, swap the static `StreamToken.fromString(...)` inside `FeedsSessionManager.buildClient(...)` for a `StreamTokenProvider` that fetches from your backend.

---

## Root Navigation Blueprint

Gate the app on `FeedsSession`. `RootViewModel` is a thin translator from view events to `FeedsSessionManager` calls — it does not own the scope, the state, or the lifecycle policy. `RootScreen` `when`-switches on the sealed state, so each branch knows statically whether a client is available.

```kotlin
import io.getstream.feeds.android.client.api.model.User

class RootViewModel(
    private val sessionManager: FeedsSessionManager,
) : ViewModel() {

    val session: StateFlow<FeedsSession> = sessionManager.session

    fun onLoginClicked(userId: String, displayName: String, token: String) {
        sessionManager.connect(User(id = userId, name = displayName), token)
    }

    fun onLogoutClicked() {
        sessionManager.disconnect()
    }

    companion object {
        fun factory(sessionManager: FeedsSessionManager): ViewModelProvider.Factory =
            viewModelFactory { initializer { RootViewModel(sessionManager) } }
    }
}

@Composable
fun RootScreen(viewModel: RootViewModel) {
    val session by viewModel.session.collectAsStateWithLifecycle()

    when (val s = session) {
        FeedsSession.Disconnected ->
            LoginScreen(isConnecting = false, error = null, onConnect = viewModel::onLoginClicked)
        FeedsSession.Connecting ->
            LoginScreen(isConnecting = true, error = null, onConnect = viewModel::onLoginClicked)
        is FeedsSession.Failed ->
            LoginScreen(isConnecting = false, error = s.message, onConnect = viewModel::onLoginClicked)
        is FeedsSession.Connected ->
            FeedsRoot(client = s.client, onLogout = viewModel::onLogoutClicked)
    }
}
```

**Wiring:**
- The `when` is exhaustive on a sealed interface — adding a new variant (e.g. `Reconnecting`) becomes a compile error until every screen handles it. No nullable client to defend against.
- `RootViewModel` exposes `sessionManager.session` as-is — no private flow, no shadowing. A logout from anywhere (e.g. a deep settings screen) calls `sessionManager.disconnect()` and every observer re-renders.
- Child ViewModels that need the client receive it through their own constructor — created from the `is FeedsSession.Connected` branch with `s.client` in scope, so the ViewModel never sees a nullable client.
- For a single-Activity Compose project, host this inside a `NavHost` and route to feeds destinations from the `Connected` branch.
- Obtain `RootViewModel` from a Compose host with `val app = LocalContext.current.applicationContext as App; viewModel(factory = RootViewModel.factory(app.sessionManager))`. Under Hilt, drop the factory and `@Inject` the `FeedsSessionManager` directly (`@HiltViewModel class RootViewModel @Inject constructor(sessionManager: FeedsSessionManager)`). Child ViewModels (`TimelineViewModel`, `NotificationsViewModel`, etc.) only need the `FeedsClient` — expose `companion object factory(client: FeedsClient)` and obtain them with `viewModel(factory = ...)` from the `is FeedsSession.Connected` branch where `client` is in scope.

---

## Timeline (Activity List) Blueprint

The timeline feed (`timeline:<userId>`) shows posts from feeds the user follows. Build the `Feed` once in a ViewModel and observe its state.

```kotlin
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.ActivityData
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.model.FeedInputData
import io.getstream.feeds.android.client.api.model.FeedMemberRequestData
import io.getstream.feeds.android.client.api.model.FeedVisibility
import io.getstream.feeds.android.client.api.state.Feed
import io.getstream.feeds.android.client.api.state.query.FeedQuery
import io.getstream.feeds.android.network.models.AddReactionRequest

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

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init {
        viewModelScope.launch {
            timeline.getOrCreate()
                .onFailure { _error.value = it.message }
                .onSuccess {
                    // Ensure timeline:<user_id> follows user:<user_id> so own posts show up.
                    // Skip this if your backend already handles that. This is just a client-side fallback.
                    if (timeline.state.following.first().none { it.targetFeed.fid == ownTimeline.fid }) {
                        timeline.follow(ownTimeline.fid, createNotificationActivity = false)
                    }
                }
        }
    }

    fun onScrolledToEnd() {
        if (!timeline.state.canLoadMoreActivities) return
        viewModelScope.launch { timeline.queryMoreActivities() }
    }

    fun onPullToRefresh() {
        viewModelScope.launch { timeline.getOrCreate() }
    }

    fun onLikeClicked(activity: ActivityData) {
        viewModelScope.launch {
            if (activity.ownReactions.any { it.type == "heart" }) {
                timeline.deleteActivityReaction(activity.id, "heart")
            } else {
                timeline.addActivityReaction(
                    activity.id,
                    AddReactionRequest(type = "heart", createNotificationActivity = true),
                )
            }
        }
    }

    fun onRepostClicked(activityId: String) {
        viewModelScope.launch { timeline.repost(activityId, text = null) }
    }

    fun onBookmarkClicked(activity: ActivityData) {
        viewModelScope.launch {
            if (activity.ownBookmarks.isNotEmpty()) timeline.deleteBookmark(activity.id)
            else timeline.addBookmark(activity.id)
        }
    }

    companion object {
        fun factory(client: FeedsClient): ViewModelProvider.Factory = viewModelFactory {
            initializer { TimelineViewModel(client) }
        }
    }
}
```

```kotlin
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
            .distinctUntilChanged()
            .collect { lastVisible ->
                if (lastVisible != null && lastVisible >= activities.lastIndex - 2) {
                    viewModel.onScrolledToEnd()
                }
            }
    }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = onCreatePostClick) { Icon(Icons.Default.Add, "Post") }
        },
    ) { padding ->
        LazyColumn(state = listState, contentPadding = padding) {
            items(activities, key = { it.id }) { activity ->
                ActivityRow(
                    activity = activity,
                    onLikeClick = { viewModel.onLikeClicked(activity) },
                    onRepostClick = { viewModel.onRepostClicked(activity.id) },
                    onBookmarkClick = { viewModel.onBookmarkClicked(activity) },
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
- Obtain from a Compose host inside the `is FeedsSession.Connected` branch: `val viewModel: TimelineViewModel = viewModel(factory = TimelineViewModel.factory(s.client))`. The other client-bound ViewModels in this file (`NotificationsViewModel`, `ProfileViewModel`, `CommentsViewModel`) follow the same shape — add a `companion object factory(client: FeedsClient, ...) { viewModelFactory { initializer { ... } } }` and obtain them the same way. Under Hilt, drop the factory and use `hiltViewModel()`.
- The `timeline:<userId>` feed does **not** automatically follow `user:<userId>`. Add the self-follow once after `getOrCreate()` if the user should see their own posts.
- This blueprint puts posts and stories in **separate feed groups** (`timeline:<userId>` for posts, `story:<userId>` for stories), so no `expiresAt` filter is needed. If your project mixes both into one group, add `activityFilter = ActivitiesFilterField.expiresAt.doesNotExist()` to the `FeedQuery` here so stories don't leak into the timeline.
- **Surface failures, don't swallow them.** SDK suspend operations return `Result<…>` — chain `.onFailure { }` to expose errors as a `StateFlow<String?>` the screen can render (snackbar / banner). A bare `viewModelScope.launch { feed.getOrCreate() }` hides network failures and leaves the UI stuck on an empty list. Apply the same pattern in `NotificationsViewModel`, `ProfileViewModel`, `CommentsViewModel`.

---

## Activity Row Blueprint

```kotlin
import io.getstream.feeds.android.client.api.model.ActivityData

@Composable
fun ActivityRow(
    activity: ActivityData,
    onLikeClick: () -> Unit,
    onRepostClick: () -> Unit,
    onBookmarkClick: () -> Unit,
    onCommentClick: () -> Unit,
) {
    // `base` is the original activity for reposts (used for display). Reactions and
    // bookmarks always attach to the wrapper (`activity`) — that's the thing the
    // current user actually interacted with.
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

            TextButton(onClick = onLikeClick) {
                Icon(if (hasLiked) Icons.Default.Favorite else Icons.Default.FavoriteBorder, null)
                Spacer(Modifier.width(4.dp))
                Text("$likeCount")
            }

            TextButton(onClick = onRepostClick) {
                Icon(Icons.Default.Repeat, null)
                Spacer(Modifier.width(4.dp))
                Text("${activity.shareCount}")
            }

            IconButton(onClick = onBookmarkClick) {
                Icon(if (isBookmarked) Icons.Default.Bookmark else Icons.Default.BookmarkBorder, null)
            }
        }
    }
}
```

**Wiring:**
- Reactions live on `activity.ownReactions` (current user's) and `activity.reactionGroups[type]?.count` (totals). Compute booleans inline; don't cache them across recompositions.
- Reposts surface as activities with `parent != null`. Render the parent's text/attachments and a small "reposted" header.
- The row is callback-only — no `Feed` reference, no `rememberCoroutineScope()`. Mutations run in `viewModelScope` so they survive the row scrolling out of composition (a `rememberCoroutineScope()` inside the row would cancel a half-finished like/repost the moment the user scrolled).

---

## Activity Composer Blueprint

The actual `addActivity` call runs in `viewModelScope`, never `rememberCoroutineScope()` — dismissing the sheet (or the user backgrounding the app) must not abort the post, especially with attachment uploads in flight. The Composable is dumb: it owns the text field state and forwards user intent.

```kotlin
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.FeedAddActivityRequest
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.state.Feed

class ComposerViewModel(
    client: FeedsClient,
    postingFid: FeedId,
    storiesFid: FeedId,
) : ViewModel() {

    private val postingFeed: Feed = client.feed(postingFid)
    private val storiesFeed: Feed = client.feed(storiesFid)

    sealed interface UiState {
        data object Idle : UiState
        data object Posting : UiState
        data object Done : UiState
        data class Error(val message: String) : UiState
    }

    private val _state = MutableStateFlow<UiState>(UiState.Idle)
    val state: StateFlow<UiState> = _state.asStateFlow()

    @OptIn(ExperimentalTime::class)
    fun onPostClicked(text: String, asStory: Boolean) {
        if (text.isBlank() || _state.value is UiState.Posting) return
        viewModelScope.launch {
            _state.value = UiState.Posting
            val target = if (asStory) storiesFeed else postingFeed
            val expiresAt = if (asStory) Clock.System.now().plus(1.days).toString() else null
            target.addActivity(
                FeedAddActivityRequest(
                    type = "post",
                    text = text,
                    feeds = listOf(target.fid.rawValue),
                    expiresAt = expiresAt,
                )
            ).fold(
                onSuccess = { _state.value = UiState.Done },
                onFailure = { _state.value = UiState.Error(it.message ?: "Post failed") },
            )
        }
    }

    fun onDismissed() {
        // Sheet went away — clear surfaced result/error state so the next open is fresh.
        // An in-flight Posting keeps running in viewModelScope (intended).
        if (_state.value !is UiState.Posting) _state.value = UiState.Idle
    }

    companion object {
        fun factory(client: FeedsClient, postingFid: FeedId, storiesFid: FeedId): ViewModelProvider.Factory =
            viewModelFactory { initializer { ComposerViewModel(client, postingFid, storiesFid) } }
    }
}
```

```kotlin
@Composable
fun ActivityComposerSheet(
    viewModel: ComposerViewModel,
    onDismiss: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    var text by rememberSaveable { mutableStateOf("") }
    var postAsStory by rememberSaveable { mutableStateOf(false) }

    val dismiss: () -> Unit = {
        viewModel.onDismissed()
        onDismiss()
    }

    LaunchedEffect(state) {
        if (state is ComposerViewModel.UiState.Done) dismiss()
    }

    ModalBottomSheet(onDismissRequest = dismiss) {
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

            val posting = state is ComposerViewModel.UiState.Posting
            Button(
                enabled = text.isNotBlank() && !posting,
                onClick = { viewModel.onPostClicked(text, postAsStory) },
            ) { Text(if (posting) "Posting…" else "Post") }

            (state as? ComposerViewModel.UiState.Error)?.let {
                Text(it.message, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
```

**Wiring:**
- All SDK calls run in `viewModelScope` — the post (and any attachment uploads) survives sheet dismissal, config changes, and recomposition. **Don't** use `rememberCoroutineScope()` for SDK operations: it's tied to the Composable's lifetime, and a dismiss mid-upload silently aborts the post.
- The VM exposes view-events (`onPostClicked`, `onDismissed`) — "*this happened in the view*" — and decides internally what state to transition to. The Composable never reaches in to clear specific state (e.g. no `consumeDone()`); it just tells the VM what the user did. Apply this convention across every VM in this file: `onLikeClicked`, `onScrolledToEnd`, `onPullToRefresh`, `onSendClicked`, `onFollowClicked`, `onMarkAllReadClicked`, etc. — never imperative names like `toggleLike`, `loadMore`, `submit`, `markAllRead`.
- The composer takes both feed ids; the story toggle picks which feed receives the activity *and* whether `expiresAt` is set. Keeping stories in a separate group means no `expiresAt` filter is needed in the timeline.
- The Composable owns only transient UI state (`text`, `postAsStory`) via `rememberSaveable` so rotation preserves typed input. All operation state (`Posting`/`Done`/`Error`) lives on the ViewModel.
- For attachments, see [FEEDS-COMPOSE.md → Create with attachments](FEEDS-COMPOSE.md#create-with-attachments). The picker + URI-copy work belongs in `ComposerViewModel.onPostClicked(...)` too — the cacheDir cleanup `try { … } finally { files.forEach { it.delete() } }` shown there must run in `viewModelScope` for the same reason.

---

## Comments Sheet Blueprint

Comments live on an `Activity` handle obtained from the client. `ActivityState.comments: StateFlow<List<ThreadedCommentData>>` holds threaded comments after `activity.get()` resolves.

```kotlin
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.model.ThreadedCommentData
import io.getstream.feeds.android.client.api.model.request.ActivityAddCommentRequest
import io.getstream.feeds.android.client.api.state.Activity
import io.getstream.feeds.android.network.models.AddCommentReactionRequest

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

    fun onReplyClicked(parentId: String?) { _replyParentId.value = parentId }

    fun onSendClicked(text: String) {
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

    fun onLikeClicked(comment: ThreadedCommentData) {
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
@Composable
fun CommentsSheet(viewModel: CommentsViewModel, onDismiss: () -> Unit) {
    val comments by viewModel.activity.state.comments.collectAsStateWithLifecycle()
    val replyParent by viewModel.replyParentId.collectAsStateWithLifecycle()
    var text by remember { mutableStateOf("") }

    val flat = remember(comments) { flattenComments(comments) }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(Modifier.fillMaxWidth().heightIn(max = 600.dp)) {
            LazyColumn(Modifier.weight(1f)) {
                items(flat, key = { it.comment.id }) { (comment, depth) ->
                    CommentRow(
                        comment = comment,
                        depth = depth,
                        currentUserId = viewModel.currentUserId,
                        onReplyClick = { viewModel.onReplyClicked(comment.parentId ?: comment.id) },
                        onLikeClick = { viewModel.onLikeClicked(comment) },
                    )
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
                        viewModel.onSendClicked(text)
                        text = ""
                    },
                ) { Icon(Icons.Default.Send, null) }
            }
        }
    }
}

private data class FlatComment(val comment: ThreadedCommentData, val depth: Int)

private fun flattenComments(
    comments: List<ThreadedCommentData>,
    depth: Int = 0,
): List<FlatComment> = comments.flatMap { c ->
    listOf(FlatComment(c, depth)) + flattenComments(c.replies.orEmpty(), depth + 1)
}

@Composable
private fun CommentRow(
    comment: ThreadedCommentData,
    depth: Int,
    currentUserId: String,
    onReplyClick: () -> Unit,
    onLikeClick: () -> Unit,
) {
    val hasLiked = comment.ownReactions.any { it.type == "heart" }
    Row(Modifier.fillMaxWidth().padding(start = (12 + depth * 24).dp, end = 12.dp, top = 12.dp, bottom = 12.dp)) {
        Box(Modifier.size(32.dp)) // avatar placeholder
        Spacer(Modifier.width(8.dp))
        Column(Modifier.weight(1f)) {
            Text(comment.user.name ?: comment.user.id, style = MaterialTheme.typography.titleSmall)
            comment.text?.let { Text(it) }
            Row {
                TextButton(onClick = onReplyClick) { Text("Reply") }
                TextButton(onClick = onLikeClick) {
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
- `activity.get()` populates `activityState.comments`.
- `parentId` on `addComment` drives reply threading: `null` for top-level, set to the parent comment id for a reply. Replies arrive under `comment.replies`.
- `client.activity(...)` returns the `Activity` handle — distinct from `ActivityData`. Build it once in the ViewModel `init`.
- The threaded tree is flattened to a list before rendering so every comment lives directly inside `LazyColumn`'s `items {}` block. Rendering replies via a nested `forEach` would put them outside the item scope, so `LazyColumn` couldn't key/reuse/animate them.

---

## Profile / Follow Graph Blueprint

```kotlin
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.model.FeedSuggestionData
import io.getstream.feeds.android.client.api.state.Feed

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

    fun onFollowClicked(target: FeedId) {
        viewModelScope.launch { feed.follow(target, createNotificationActivity = true) }
    }
    fun onUnfollowClicked(target: FeedId) { viewModelScope.launch { feed.unfollow(target) } }
    fun onAcceptFollowClicked(source: FeedId) { viewModelScope.launch { feed.acceptFollow(source) } }
    fun onRejectFollowClicked(source: FeedId) { viewModelScope.launch { feed.rejectFollow(source) } }
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
                    Text(req.sourceFeed.createdBy.name ?: req.sourceFeed.fid.id, modifier = Modifier.weight(1f))
                    Button(onClick = { viewModel.onAcceptFollowClicked(req.sourceFeed.fid) }) { Text("Accept") }
                    Spacer(Modifier.width(8.dp))
                    OutlinedButton(onClick = { viewModel.onRejectFollowClicked(req.sourceFeed.fid) }) { Text("Reject") }
                }
            }
        }

        item { SectionHeader("Following (${following.size})") }
        items(following, key = { it.targetFeed.fid.rawValue }) { f ->
            Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(f.targetFeed.createdBy.name ?: f.targetFeed.fid.id, modifier = Modifier.weight(1f))
                OutlinedButton(onClick = { viewModel.onUnfollowClicked(f.targetFeed.fid) }) { Text("Unfollow") }
            }
        }

        item { SectionHeader("Followers (${followers.size})") }
        items(followers, key = { it.sourceFeed.fid.rawValue }) { f ->
            Text(
                f.sourceFeed.createdBy.name ?: f.sourceFeed.fid.id,
                Modifier.fillMaxWidth().padding(12.dp),
            )
        }

        if (suggestions.isNotEmpty()) {
            item { SectionHeader("Who to Follow") }
            items(suggestions, key = { it.feed.fid.rawValue }) { suggestion ->
                Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(suggestion.feed.createdBy.name ?: suggestion.feed.fid.id, modifier = Modifier.weight(1f))
                    Button(onClick = { viewModel.onFollowClicked(suggestion.feed.fid) }) { Text("Follow") }
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
import io.getstream.feeds.android.client.api.FeedsClient
import io.getstream.feeds.android.client.api.model.FeedId
import io.getstream.feeds.android.client.api.state.Feed
import io.getstream.feeds.android.network.models.MarkActivityRequest

class NotificationsViewModel(client: FeedsClient) : ViewModel() {
    val feed: Feed = client.feed(FeedId("notification", client.user.id))

    init { viewModelScope.launch { feed.getOrCreate() } }

    fun onMarkAllReadClicked() {
        viewModelScope.launch { feed.markActivity(MarkActivityRequest(markAllRead = true)) }
    }
    fun onNotificationClicked(activityId: String) {
        viewModelScope.launch { feed.markActivity(MarkActivityRequest(markRead = listOf(activityId))) }
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
                    TextButton(onClick = viewModel::onMarkAllReadClicked) { Text("Mark all read") }
                }
            },
        )
    }) { padding ->
        LazyColumn(contentPadding = padding) {
            items(aggregated, key = { it.group }) { group ->
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
                        first?.createdAt?.let { date ->
                            Text(
                                text = DateUtils.getRelativeTimeSpanString(
                                    date.time,
                                    System.currentTimeMillis(),
                                    DateUtils.MINUTE_IN_MILLIS,
                                ).toString(),
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
    return when (group.activities.firstOrNull()?.type) {
        "reaction"         -> "$names$extra reacted to your post"
        "comment"          -> "$names$extra commented on your post"
        "comment_reaction" -> "$names$extra reacted to your comment"
        "follow"           -> "$names$extra followed you"
        else               -> "$names$extra interacted with your post"
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
                onClick = {
                    if (ownStories.isEmpty()) onCreateStoryClick() else onOpenStories(ownStories)
                },
            )
        }
        items(storyGroups, key = { it.group }) { group ->
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
    contentDescription: String = "Open stories",
) {
    val color = if (hasUnwatched)
        MaterialTheme.colorScheme.primary
    else
        MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)

    Box(
        modifier = modifier
            .size(72.dp)
            .clip(CircleShape)
            .clickable(onClick = onClick, role = Role.Button, onClickLabel = contentDescription)
            .border(3.dp, color, CircleShape)
            .semantics { this.contentDescription = contentDescription },
    )
}
```

**Wiring:**
- The own-stories feed is filtered to `expiresAt.exists()` — build it via `FeedQuery(activityFilter = ActivitiesFilterField.expiresAt.exists())`.
- The aggregated stories feed surfaces `aggregatedActivities` (one group per user). Use `group.activities` for the actual stories to display in the viewer.
- Mark a story as watched after the user views it: `storiesFeed.markActivity(MarkActivityRequest(markWatched = listOf(storyId)))`.
