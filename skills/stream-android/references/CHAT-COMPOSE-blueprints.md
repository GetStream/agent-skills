# Chat Compose - Screen Blueprints

Load only the section you are implementing. For setup, client initialization, and gotchas, see [CHAT-COMPOSE.md](CHAT-COMPOSE.md).

---

## Application Class Blueprint

Build `ChatClient` once in `Application.onCreate()`. The Builder registers a singleton; retrieve it elsewhere via `ChatClient.instance()`.

```kotlin
package com.example.streamchat

import android.app.Application
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.client.logger.ChatLogLevel

class App : Application() {
    override fun onCreate() {
        super.onCreate()

        val logLevel = if (BuildConfig.DEBUG) ChatLogLevel.ALL else ChatLogLevel.NOTHING

        ChatClient.Builder("your_api_key", applicationContext)
            .logLevel(logLevel)
            .build()
    }
}
```

Register it in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    android:label="@string/app_name"
    android:theme="@style/Theme.StreamChat">
    <!-- activities ... -->
</application>

<uses-permission android:name="android.permission.INTERNET" />
```

**Wiring:**
- `Application.onCreate()` runs before any Activity, so `ChatClient.instance()` is safe to call from any Composable lifecycle.
- The Compose artifact transitively pulls in the offline + state plugins; no extra Builder calls are required for default state-layer behavior.

---

## Login / Connect User Blueprint

Show a login screen before connecting. Invoke `connectUser` once per user session, not on every Composable entry.

```kotlin
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.compose.ui.theme.ChatTheme
import io.getstream.chat.android.models.User
import io.getstream.result.Result

class LoginActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ChatTheme {
                LoginScreen(
                    onConnected = {
                        startActivity(Intent(this, ChannelsActivity::class.java))
                        finish()
                    },
                )
            }
        }
    }
}

@Composable
fun LoginScreen(onConnected: () -> Unit) {
    var userId by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var isConnecting by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Sign In", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        OutlinedTextField(value = userId, onValueChange = { userId = it }, label = { Text("User ID") })
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Display name") })
        error?.let {
            Spacer(Modifier.height(8.dp))
            Text(it, color = MaterialTheme.colorScheme.error)
        }
        Spacer(Modifier.height(16.dp))
        Button(
            enabled = userId.isNotBlank() && !isConnecting,
            onClick = {
                isConnecting = true
                error = null
                val user = User(id = userId, name = name.ifBlank { userId })
                ChatClient.instance()
                    .connectUser(user, token = "your_static_token_here")
                    .enqueue { result ->
                        isConnecting = false
                        when (result) {
                            is Result.Success -> onConnected()
                            is Result.Failure -> error = result.value.message
                        }
                    }
            },
        ) {
            if (isConnecting) CircularProgressIndicator(strokeWidth = 2.dp) else Text("Connect")
        }
    }
}
```

**Wiring:**
- `connectUser(...).enqueue { ... }` already hops back to the main thread for the callback - state updates are safe to write directly.
- For an expiring token, swap the `token = "..."` argument for a `TokenProvider` (see [CHAT-COMPOSE.md - User Authentication](CHAT-COMPOSE.md#user-authentication)).
- Auto-reconnect across app launches: check `ChatClient.instance().getCurrentUser() != null` before showing the login screen.

---

## Root Navigation Blueprint

Gate the app on connection state. Skips login if a previous session is still connected.

```kotlin
@Composable
fun RootScreen() {
    val currentUser = ChatClient.instance().getCurrentUser()
    var isConnected by remember { mutableStateOf(currentUser != null) }

    if (isConnected) {
        ChannelsScreenHost(
            onChannelClick = { /* navigate to ChannelScreen */ },
            onLogout = {
                ChatClient.instance().disconnect(flushPersistence = false).enqueue {
                    isConnected = false
                }
            },
        )
    } else {
        LoginScreen(onConnected = { isConnected = true })
    }
}
```

**Wiring:**
- `ChatClient.instance().getCurrentUser()` is non-null while a user is connected and survives process restarts when offline persistence is enabled (default in the Compose artifact).
- For a single-Activity Compose project, host this inside a `NavHost` and route to a separate channel-screen destination.

---

## Channel List Blueprint

### Drop-in `ChannelsScreen`

```kotlin
import io.getstream.chat.android.compose.ui.channels.ChannelsScreen
import io.getstream.chat.android.compose.ui.channels.SearchMode

@Composable
fun ChannelsScreenHost(
    onChannelClick: (cid: String) -> Unit,
    onLogout: () -> Unit,
) {
    ChannelsScreen(
        title = "Messages",
        isShowingHeader = true,
        searchMode = SearchMode.Channels,
        onChannelClick = { channel -> onChannelClick(channel.cid) },
        onHeaderAvatarClick = { onLogout() },
        onBackPressed = { /* finish or pop */ },
    )
}
```

### Custom filters and sort

```kotlin
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.compose.viewmodel.channels.ChannelListViewModelFactory
import io.getstream.chat.android.models.Filters
import io.getstream.chat.android.models.querysort.QuerySortByField

@Composable
fun FilteredChannelsScreen(onChannelClick: (cid: String) -> Unit) {
    val currentUserId = ChatClient.instance().getCurrentUser()?.id ?: return

    ChannelsScreen(
        viewModelFactory = ChannelListViewModelFactory(
            filters = Filters.and(
                Filters.eq("type", "messaging"),
                Filters.`in`("members", listOf(currentUserId)),
            ),
            querySort = QuerySortByField.descByName("last_updated"),
            channelLimit = 30,
        ),
        title = "Stream Chat",
        onChannelClick = { onChannelClick(it.cid) },
    )
}
```

**Wiring:**
- `ChannelsScreen` already includes its own header, search bar, list, and back-handling. Don't wrap it in another `Scaffold`.
- Set the title via the `title` parameter; `isShowingHeader = false` hides the header entirely.
- `searchMode` accepts `SearchMode.None`, `SearchMode.Channels`, or `SearchMode.Messages`.
- Navigation between the channel list and a channel screen is **not** automatic - implement `onChannelClick` and route to your channel destination.

### Bound `ChannelList` (custom shell)

```kotlin
import androidx.lifecycle.viewmodel.compose.viewModel
import io.getstream.chat.android.compose.ui.channels.list.ChannelList
import io.getstream.chat.android.compose.viewmodel.channels.ChannelListViewModel
import io.getstream.chat.android.compose.viewmodel.channels.ChannelListViewModelFactory

@Composable
fun CustomChannelListShell(onChannelClick: (cid: String) -> Unit) {
    val factory = ChannelListViewModelFactory(filters = null)
    val viewModel: ChannelListViewModel = viewModel(factory = factory)

    Scaffold(
        topBar = { TopAppBar(title = { Text("My channels") }) },
    ) { padding ->
        ChannelList(
            modifier = Modifier.padding(padding),
            viewModel = viewModel,
            onChannelClick = { onChannelClick(it.cid) },
        )
    }
}
```

---

## Custom Channel List Header Blueprint

Use the SDK's `ChannelListHeader` Composable when you want a channel-list shell with the SDK's connection/avatar/title behavior but your own surrounding layout. It exposes `currentUser`, `connectionState`, `title`, plus optional `leadingContent` and `trailingContent` slots.

```kotlin
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Icon
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.compose.ui.channels.header.ChannelListHeader
import io.getstream.chat.android.compose.ui.theme.ChatTheme

@Composable
fun CustomChannelListHeader(onAddChannel: () -> Unit) {
    val user by ChatClient.instance().clientState.user.collectAsState()
    val connectionState by ChatClient.instance().clientState.connectionState.collectAsState()

    ChannelListHeader(
        modifier = Modifier.fillMaxWidth(),
        currentUser = user,
        title = "My Chat App",
        connectionState = connectionState,
        onAvatarClick = { _ -> /* open profile */ },
        trailingContent = {
            Icon(
                imageVector = Icons.Default.Add,
                contentDescription = "New channel",
                tint = ChatTheme.colors.textPrimary,
                modifier = Modifier.clickable { onAddChannel() },
            )
        },
    )
}
```

**Wiring:**
- `ChatClient.instance().clientState.user` and `.connectionState` are `StateFlow`s the SDK keeps in sync with the live socket - collect them with `collectAsState()` (or `collectAsStateWithLifecycle()`) instead of caching the values.
- `ChannelListHeader` is also what `ChannelsScreen` renders by default - reach for this Composable when you've dropped to a custom shell with `ChannelList` and need the same header behavior.
- For a fully custom title/back-button bar, replace `ChannelListHeader` with your own `Row` / `TopAppBar` and ignore this Composable entirely.

---

## Channel (Message List) Blueprint

### Drop-in `ChannelScreen`

```kotlin
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import io.getstream.chat.android.compose.ui.messages.ChannelScreen
import io.getstream.chat.android.compose.ui.theme.ChatTheme
import io.getstream.chat.android.compose.viewmodel.messages.ChannelViewModelFactory
import io.getstream.chat.android.compose.viewmodel.messages.MessageListOptions

class ChannelActivity : ComponentActivity() {

    private val channelId: String
        get() = intent.getStringExtra(KEY_CHANNEL_ID) ?: "messaging:general"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ChatTheme {
                ChannelScreen(
                    viewModelFactory = ChannelViewModelFactory(
                        context = this,
                        channelId = channelId,
                        messageListOptions = MessageListOptions(
                            messageLimit = 30,
                            enforceUniqueReactions = true,
                        ),
                    ),
                    onBackPressed = { finish() },
                    onHeaderTitleClick = { /* show channel info */ },
                )
            }
        }
    }

    companion object {
        private const val KEY_CHANNEL_ID = "channelId"
        fun createIntent(context: Context, cid: String) =
            Intent(context, ChannelActivity::class.java).putExtra(KEY_CHANNEL_ID, cid)
    }
}
```

### Overriding the ViewModels (custom screen layout)

```kotlin
import androidx.activity.viewModels
import io.getstream.chat.android.compose.viewmodel.messages.AttachmentsPickerViewModel
import io.getstream.chat.android.compose.viewmodel.messages.ChannelViewModelFactory
import io.getstream.chat.android.compose.viewmodel.messages.MessageComposerViewModel
import io.getstream.chat.android.compose.viewmodel.messages.MessageListViewModel

class CustomChannelActivity : ComponentActivity() {

    private val factory by lazy {
        ChannelViewModelFactory(context = this, channelId = "messaging:general")
    }

    private val listViewModel: MessageListViewModel by viewModels { factory }
    private val composerViewModel: MessageComposerViewModel by viewModels { factory }
    private val attachmentsPickerViewModel: AttachmentsPickerViewModel by viewModels { factory }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ChatTheme {
                Column(Modifier.fillMaxSize()) {
                    MessageList(
                        modifier = Modifier.weight(1f),
                        viewModel = listViewModel,
                    )
                    MessageComposer(viewModel = composerViewModel)
                }
            }
        }
    }
}
```

**Wiring:**
- `ChannelViewModelFactory` resolves all three ViewModels (`MessageListViewModel`, `MessageComposerViewModel`, `AttachmentsPickerViewModel`) from a single factory instance.
- `MessageListOptions` controls page size, reaction uniqueness, system-message visibility, thread direction.
- `MessageComposer(viewModel = ...)` already calls `composerViewModel.sendMessage(...)` from its default send handler. Only pass `onSendMessage = { ... }` when you need to inject extra behavior (analytics, validation, intercepting drafts) - reproducing the default call buys nothing.
- `ChannelScreen` already wires the composer + attachments picker + message list together - drop down to bound components only if you need a non-standard layout.

---

## Custom ChatTheme Blueprint

Build appearance once and apply at every Stream screen root. Match light/dark with `isSystemInDarkTheme()`.

```kotlin
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import io.getstream.chat.android.compose.ui.theme.ChatTheme
import io.getstream.chat.android.compose.ui.theme.StreamDesign

@Composable
fun BrandChatTheme(content: @Composable () -> Unit) {
    val baseColors = if (isSystemInDarkTheme()) {
        StreamDesign.Colors.defaultDark()
    } else {
        StreamDesign.Colors.default()
    }

    val branded = baseColors.copy(
        accentPrimary = Color(0xFF7C3AED),
    )

    ChatTheme(
        colors = branded,
        typography = StreamDesign.Typography.default(),
        content = content,
    )
}
```

**Wiring:**
- `StreamDesign.Colors.default()` / `.defaultDark()` return a `data class` - use `.copy(...)` to override only the tokens you want. Common overrides: `accentPrimary`, `textPrimary`, `backgroundCoreApp`, `borderCoreDefault`. Re-brand the entire UI in one shot via `StreamDesign.Colors.default(brand = StreamDesign.ColorScale.from(brandColor = ...))` instead of overriding individual tokens.
- Pass the same `BrandChatTheme` at every Activity that hosts Stream content; nesting `ChatTheme` inside another `ChatTheme` is supported but redundant.

---

## Custom Channel Item Blueprint

`ChannelList` does **not** take an `itemContent` lambda. Override the channel row via `ChatComponentFactory.ChannelListItemContent(...)` and pass your factory to `ChatTheme(componentFactory = ...)`.

```kotlin
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyItemScope
import androidx.compose.material3.Badge
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.getstream.chat.android.compose.state.channels.list.ItemState
import io.getstream.chat.android.compose.ui.theme.ChatComponentFactory
import io.getstream.chat.android.compose.ui.theme.ChannelListItemContentParams
import io.getstream.chat.android.compose.ui.theme.ChatTheme

class BrandComponentFactory : ChatComponentFactory {

    @Composable
    override fun LazyItemScope.ChannelListItemContent(params: ChannelListItemContentParams) {
        val channel = params.channelItem.channel
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clickable { params.onChannelClick(channel) }
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = channel.name.ifBlank { channel.cid },
                    style = MaterialTheme.typography.titleMedium,
                )
                channel.messages.lastOrNull()?.let { last ->
                    Text(
                        text = last.text,
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 1,
                    )
                }
            }
            val unread = channel.unreadCount ?: 0
            if (unread > 0) {
                Badge { Text(unread.toString()) }
            }
        }
    }
}

@Composable
fun BrandedChannelsHost(onChannelClick: (Channel) -> Unit) {
    ChatTheme(componentFactory = BrandComponentFactory()) {
        ChannelsScreen(onChannelClick = onChannelClick)
    }
}
```

**Wiring:**
- `ChannelListItemContentParams` exposes `channelItem: ItemState.ChannelItemState` (with `channel`, `isMuted`, `typingUsers`, `draftMessage`, `isSelected`), plus `currentUser`, `onChannelClick`, `onChannelLongClick`. Unread count lives on `channel.unreadCount`, not on the item state.
- To override only a sub-piece of the row (avatar, name, trailing timestamp/unread), prefer `ChannelItemLeadingContent` / `ChannelItemCenterContent` / `ChannelItemTrailingContent` instead of replacing the whole row - they preserve the SDK swipe-action wrapper.
- Composables overridden on `ChatComponentFactory` need their original receiver (`LazyItemScope`, `RowScope`, etc.) - copy the receiver from the interface declaration, otherwise the override won't compile.

---

## Custom Channel Header Blueprint

Replace the channel-screen header without rebuilding the rest of the screen by passing your own `topBarContent` to a custom layout, or override the channel screen's header slot.

```kotlin
import io.getstream.chat.android.compose.ui.messages.header.MessageListHeader

@Composable
fun CustomChannelHeader(
    channelName: String,
    onBack: () -> Unit,
    onCall: () -> Unit,
) {
    Surface(tonalElevation = 2.dp) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, contentDescription = "Back") }
            Text(channelName, style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
            IconButton(onClick = onCall) { Icon(Icons.Default.Call, contentDescription = "Call") }
        }
    }
}
```

Then host it above a bound `MessageList`/`MessageComposer` instead of using `ChannelScreen`. If you need to keep `ChannelScreen` and only swap the bar, use the SDK's built-in `MessageListHeader` and pass your own `leadingContent` / `trailingContent` slots.

---

## Channel Tap Handling / Deep-link Blueprint

`ChannelsScreen` does not navigate on its own. Provide `onChannelClick` (and `onSearchMessageItemClick` when search is enabled) to route into your own destination. Deep-linking from a push notification means launching the channel destination directly with the `cid` you received.

### Route a tap into your channel destination

```kotlin
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController

@Composable
fun ChatNavGraph() {
    val nav = rememberNavController()
    NavHost(navController = nav, startDestination = "channels") {
        composable("channels") {
            ChatTheme {
                ChannelsScreen(
                    title = "Messages",
                    onChannelClick = { channel ->
                        nav.navigate("channel/${channel.cid}")
                    },
                    onBackPressed = { /* finish or pop */ },
                )
            }
        }
        composable("channel/{cid}") { backStack ->
            val cid = backStack.arguments?.getString("cid") ?: return@composable
            ChatTheme {
                ChannelScreen(
                    viewModelFactory = ChannelViewModelFactory(
                        context = LocalContext.current,
                        channelId = cid,
                    ),
                    onBackPressed = { nav.popBackStack() },
                )
            }
        }
    }
}
```

### Intercept a tap without navigating

When you only want analytics, an action sheet, or a custom side-effect on tap, do the work inside `onChannelClick` and skip the `nav.navigate(...)` call:

```kotlin
ChannelsScreen(
    onChannelClick = { channel ->
        analytics.track("channel_tapped", mapOf("cid" to channel.cid))
        // no navigation
    },
)
```

### Deep-link from a push notification

Push payloads include the `cid` (`"<type>:<id>"`) and an optional `messageId`. Launch the channel destination directly from the notification intent - skip the channel list:

```kotlin
class StartupActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val cid = intent.getStringExtra(EXTRA_CID)

        setContent {
            ChatTheme {
                if (cid != null) {
                    ChannelScreen(
                        viewModelFactory = ChannelViewModelFactory(
                            context = this,
                            channelId = cid,
                            messageId = intent.getStringExtra(EXTRA_MESSAGE_ID),
                        ),
                        onBackPressed = { finish() },
                    )
                } else {
                    ChannelsScreenHost(
                        onChannelClick = { /* navigate to channel/<cid> */ },
                        onLogout = { /* ... */ },
                    )
                }
            }
        }
    }

    companion object {
        const val EXTRA_CID = "cid"
        const val EXTRA_MESSAGE_ID = "messageId"

        fun createIntent(context: Context, cid: String, messageId: String? = null) =
            Intent(context, StartupActivity::class.java)
                .putExtra(EXTRA_CID, cid)
                .putExtra(EXTRA_MESSAGE_ID, messageId)
    }
}
```

**Wiring:**
- `Channel.cid` is the canonical `"<type>:<id>"` string - pass it as a single route argument instead of two separate fields.
- `ChannelViewModelFactory` accepts an optional `messageId` argument for jumping to a specific message inside the channel (used by push deep-links).
- `ChannelsScreen` does not expose a `selectedChannelId` parameter - if you want a master-detail layout that highlights the current channel, drop down to bound `ChannelList` + your own selection state.

---

## State Layer Compose Blueprint

Use the state layer when you want `StateFlow` reads + `suspend` mutations instead of bound ViewModels.

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.client.api.state.watchChannelAsState
import io.getstream.chat.android.models.Message
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn

class StateChannelViewModel(private val cid: String) : ViewModel() {

    private val client = ChatClient.instance()
    private val channelClient = client.channel(cid.substringBefore(":"), cid.substringAfter(":"))

    @OptIn(ExperimentalCoroutinesApi::class)
    val messages: StateFlow<List<Message>> =
        client.watchChannelAsState(cid = cid, messageLimit = 30, coroutineScope = viewModelScope)
            .filterNotNull()
            .flatMapLatest { it.messages }
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    fun send(text: String) {
        channelClient.sendMessage(Message(text = text)).enqueue()
    }
}
```

```kotlin
@Composable
fun StateChannelScreen(cid: String) {
    val viewModel: StateChannelViewModel = viewModel(factory = viewModelFactory {
        initializer { StateChannelViewModel(cid) }
    })
    val messages by viewModel.messages.collectAsStateWithLifecycle()

    Column(Modifier.fillMaxSize()) {
        LazyColumn(Modifier.weight(1f)) {
            items(messages, key = { it.id }) { message ->
                Text(
                    text = message.text,
                    modifier = Modifier.fillMaxWidth().padding(8.dp),
                )
            }
        }
        var draft by remember { mutableStateOf("") }
        Row(Modifier.padding(8.dp)) {
            OutlinedTextField(
                value = draft,
                onValueChange = { draft = it },
                modifier = Modifier.weight(1f),
            )
            Button(onClick = {
                viewModel.send(draft)
                draft = ""
            }) { Text("Send") }
        }
    }
}
```

**Wiring:**
- `watchChannelAsState(cid, messageLimit, scope)` returns `StateFlow<ChannelState?>`; `ChannelState.messages` is itself a `StateFlow<List<Message>>` you can collect inside Compose.
- Mutations (`sendMessage`, `sendReaction`, `markRead`) still go through the regular `ChannelClient` `Call` API.
- For a list of channels, swap to `client.queryChannelsAsState(request, scope)`.
