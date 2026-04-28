# Chat - Compose SDK Setup & Integration

Stream Chat Compose provides pre-built Jetpack Compose components for building rich messaging UIs. This file covers package installation, client setup, authentication, customization, and gotchas. For screen blueprints, see [CHAT-COMPOSE-blueprints.md](CHAT-COMPOSE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper logout).

- **Blueprint** - Compose screen structure and initialization
- **Wiring** - SDK calls for each component, exact property paths
- **Requirements** - `INTERNET` permission in `AndroidManifest.xml`, `minSdk` 21+, Kotlin + Jetpack Compose enabled in the app module.

## Quick ref

- **Target version:** Stream Chat Android **v7.x** (see [RULES.md](../RULES.md) - if your memory disagrees with the docs, trust the docs)
- **Artifact (Compose):** `io.getstream:stream-chat-android-compose` via Maven Central
- **Artifact (core only):** `io.getstream:stream-chat-android-client` (pulled in transitively by Compose)
- **First:** Installation -> Manifest -> `ChatClient` build -> `connectUser` -> `ChatTheme { ChannelsScreen() }`
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** If you can't find an information here, check the docs: `https://getstream.io/chat/docs/sdk/android/compose/overview/`

Full screen blueprints: [CHAT-COMPOSE-blueprints.md](CHAT-COMPOSE-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation (Gradle)

Check if the SDK is already installed in the project. If not:

**With version catalog (`gradle/libs.versions.toml`):**

```toml
[versions]
stream-chat-compose = "<latest>"

[libraries]
stream-chat-compose = { module = "io.getstream:stream-chat-android-compose", version.ref = "stream-chat-compose" }
```

```kotlin
// app/build.gradle.kts
dependencies {
    implementation(libs.stream.chat.compose)
}
```

**Without version catalog:**

```kotlin
// app/build.gradle.kts
dependencies {
    implementation("io.getstream:stream-chat-android-compose:<latest>")
}
```

If you don't know the latest version, ask the user to check the [installation guide](https://getstream.io/chat/docs/sdk/android/basics/getting-started/).

Add the `INTERNET` permission to `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

### Client Initialization

Initialize once in your `Application` class. **Never** create `ChatClient` in a `@Composable` body, a `remember { ... }` factory, or an `Activity.onCreate` that re-runs - the Builder registers a singleton, so the second build will fail or replace the first.

```kotlin
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

Register the `Application` subclass in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    ...>
```

After build time, retrieve the client anywhere via `ChatClient.instance()`. The Builder registers the singleton automatically - do **not** store your own copy as a top-level `lateinit var`.

### User Authentication

**Default - hardcoded token (no expiry):**

Ask the user for their Stream token from the [Stream Dashboard](https://dashboard.getstream.io) (User Explorer -> generate token):

```kotlin
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.models.User
import io.getstream.result.Result

val user = User(
    id = "user-id",
    name = "User Name",
    image = "https://example.com/avatar.png",
)

ChatClient.instance()
    .connectUser(user, token = "your_static_token_here")
    .enqueue { result ->
        when (result) {
            is Result.Success -> { /* connected */ }
            is Result.Failure -> { /* handle error */ }
        }
    }
```

**Token provider (expiring tokens - use only if the user asks for it):**

Use this when the user has a backend endpoint that issues Stream JWTs. The provider is called automatically by the SDK when the token expires:

```kotlin
import io.getstream.chat.android.client.token.TokenProvider

val tokenProvider = object : TokenProvider {
    override fun loadToken(): String {
        // Synchronous call to your backend - blocks the calling thread.
        // The SDK invokes this on a background dispatcher.
        return yourAuthService.fetchStreamToken(userId = user.id)
    }
}

ChatClient.instance()
    .connectUser(user, tokenProvider)
    .enqueue { /* ... */ }
```

`TokenProvider.loadToken()` is synchronous - block on your backend call inside it; the SDK runs the provider off the main thread and re-invokes it whenever the token expires.

### Disconnecting / switching users

Always wait for `disconnect()` to complete before connecting another user:

```kotlin
ChatClient.instance().disconnect(flushPersistence = false).enqueue { result ->
    when (result) {
        is Result.Success -> {
            ChatClient.instance().connectUser(nextUser, nextToken).enqueue { /* ... */ }
        }
        is Result.Failure -> { /* handle error */ }
    }
}
```

Pass `flushPersistence = true` only when you want to clear the offline cache (e.g. on full logout).

### Creating Channels

```kotlin
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.models.Channel
import io.getstream.result.Result

// Existing channel by id - call create() on the channel client.
val channelClient = ChatClient.instance().channel(channelType = "messaging", channelId = "general")
channelClient.create(memberIds = emptyList(), extraData = emptyMap()).enqueue { result ->
    when (result) {
        is Result.Success -> { val channel: Channel = result.value }
        is Result.Failure -> { /* handle error */ }
    }
}

// Distinct channel for a list of members - leave channelId empty so the backend
// derives a stable id from the member set.
ChatClient.instance().createChannel(
    channelType = "messaging",
    channelId = "",
    memberIds = listOf("alice", "bob"),
    extraData = emptyMap(),
).enqueue { /* ... */ }
```

`memberIds` must include the user ids you want as channel members; pass `emptyList()` for an empty channel that you populate later. Pass channel-level fields (name, image, custom keys) via `extraData` (see [Extra Data](#extra-data)).

### Showing the Channel List

Wrap any Stream Composable in `ChatTheme { ... }`. The drop-in `ChannelsScreen` renders the channel list, header, search, and navigation events:

```kotlin
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import io.getstream.chat.android.compose.ui.channels.ChannelsScreen
import io.getstream.chat.android.compose.ui.theme.ChatTheme

class ChannelsActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ChatTheme {
                ChannelsScreen(
                    onChannelClick = { channel ->
                        // navigate to ChannelActivity / ChannelScreen
                    },
                    onBackPressed = { finish() },
                )
            }
        }
    }
}
```

---

## Client Patterns

### ViewModel Management

**Create Stream ViewModels via `viewModels { factory }` - never inside Composables.**

The Compose SDK ships two factories:

- `ChannelListViewModelFactory` -> `ChannelListViewModel`
- `ChannelViewModelFactory` -> `MessageListViewModel`, `MessageComposerViewModel`, `AttachmentsPickerViewModel`

```kotlin
import androidx.activity.viewModels
import io.getstream.chat.android.compose.viewmodel.messages.ChannelViewModelFactory
import io.getstream.chat.android.compose.viewmodel.messages.MessageListViewModel
import io.getstream.chat.android.compose.viewmodel.messages.MessageComposerViewModel
import io.getstream.chat.android.compose.viewmodel.messages.AttachmentsPickerViewModel
import io.getstream.chat.android.compose.viewmodel.messages.MessageListOptions

class ChannelActivity : ComponentActivity() {
    private val factory by lazy {
        ChannelViewModelFactory(
            context = this,
            channelId = "messaging:general",
            messageListOptions = MessageListOptions(messageLimit = 30),
        )
    }

    private val listViewModel: MessageListViewModel by viewModels { factory }
    private val composerViewModel: MessageComposerViewModel by viewModels { factory }
    private val attachmentsPickerViewModel: AttachmentsPickerViewModel by viewModels { factory }
}
```

Pass the factory (or the resolved ViewModels) into the screen-level Composable. Drop-in screens like `ChannelScreen(viewModelFactory = factory)` resolve all three ViewModels from a single factory.

### Bound vs stateless components

Stream Compose components come in three flavors:

- **Screen** components (`ChannelsScreen`, `ChannelScreen`) - full screens with built-in ViewModels and navigation hooks
- **Bound** components (`ChannelList`, `MessageList`, `MessageComposer`) - take a ViewModel parameter
- **Stateless** components (under `ui/components/`) - take pure state and callbacks

Pick the highest-level component that still meets the customization need. Drop down only when you need to override behavior the screen doesn't expose.

Sub-piece customization (channel item rows, list headers, empty/loading states, message item parts, etc.) goes through **`ChatComponentFactory`**, not slot lambdas on the bound components. See [Component factory customization](#component-factory-customization) below.

---

## ChannelListViewModelFactory Options

```kotlin
import io.getstream.chat.android.compose.viewmodel.channels.ChannelListViewModelFactory
import io.getstream.chat.android.models.Filters
import io.getstream.chat.android.models.querysort.QuerySortByField

val factory = ChannelListViewModelFactory(
    filters = Filters.and(
        Filters.eq("type", "messaging"),
        Filters.`in`("members", listOf(currentUserId)),
    ),
    querySort = QuerySortByField.descByName("last_updated"),
    channelLimit = 30,
    memberLimit = 30,
    messageLimit = 1,
)
```

`filters = null` falls back to the default query (`Filters.in("members", listOf(currentUserId))`). Use `Filters.and(...)`, `Filters.or(...)`, `Filters.eq(...)`, `Filters.in(...)` to compose filter expressions.

---

## State Layer (coroutines API)

The state layer exposes channel/message data as `StateFlow`s. Use it when you want `suspend` mutations and `collectAsStateWithLifecycle()` reads instead of bound ViewModels.

```kotlin
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.client.api.state.watchChannelAsState

val client = ChatClient.instance()
val channelState = client
    .watchChannelAsState(cid = "messaging:general", messageLimit = 30, coroutineScope = viewModelScope)

// Compose:
val state by channelState.collectAsStateWithLifecycle()
val messages = state?.messages?.collectAsStateWithLifecycle()?.value.orEmpty()
```

Common state-layer entry points:

- `client.watchChannelAsState(cid, messageLimit, scope)` -> `StateFlow<ChannelState?>`
- `client.queryChannelsAsState(request, scope)` -> `StateFlow<QueryChannelsState?>`
- `client.globalState` -> `GlobalState` with `user`, `totalUnreadCount`, `channelUnreadCount`, etc.

Send actions through the regular `ChatClient`/`ChannelClient` Call API:

```kotlin
val channelClient = client.channel("messaging", "general")
channelClient.sendMessage(Message(text = "Hello!")).enqueue { /* ... */ }
```

---

## Extra Data

Attach arbitrary `Map<String, Any>` to users, messages, channels, and attachments via the `extraData` parameter on each model.

**Set extra data:**

```kotlin
import io.getstream.chat.android.models.Message
import io.getstream.chat.android.models.User

// On the current user
val user = User(
    id = "alice",
    name = "Alice",
    image = "https://example.com/alice.png",
    extraData = mutableMapOf(
        "email" to "alice@example.com",
        "isPremium" to true,
    ),
)
ChatClient.instance().connectUser(user, token).enqueue { /* ... */ }

// On a new message
val message = Message(
    text = "Here's your ticket",
    extraData = mutableMapOf(
        "ticketId" to "abc-123",
        "price" to 20.0,
    ),
)
ChatClient.instance()
    .channel("messaging", "general")
    .sendMessage(message)
    .enqueue { /* ... */ }

// On a new channel
ChatClient.instance().createChannel(
    channelType = "messaging",
    channelId = "support",
    memberIds = listOf("alice", "bob"),
    extraData = mutableMapOf(
        "name" to "Support",
        "image" to "https://example.com/support.png",
        "team" to "red",
    ),
).enqueue { /* ... */ }
```

**Read extra data:**

```kotlin
val email = user.extraData["email"] as? String
val isPremium = user.extraData["isPremium"] as? Boolean ?: false
val ticketId = message.extraData["ticketId"] as? String
val price = (message.extraData["price"] as? Number)?.toDouble()

// Nested
val metadata = message.extraData["metadata"] as? Map<*, *>
val value = metadata?.get("key") as? String
```

`extraData` round-trips through JSON, so the values come back as `String`, `Double`/`Long` (numbers), `Boolean`, `Map<String, Any?>`, or `List<Any?>`. Cast defensively.

**Clean-access extension pattern:**

```kotlin
val User.email: String? get() = extraData["email"] as? String
val User.isPremium: Boolean get() = extraData["isPremium"] as? Boolean ?: false
```

`Channel` has top-level `name` and `image` properties that the SDK populates from `extraData["name"]` / `extraData["image"]` automatically - prefer the typed properties for those two keys.

---

## Logging

Disabled by default. Enable on the Builder, ideally only in debug builds:

```kotlin
ChatClient.Builder(apiKey, context)
    .logLevel(if (BuildConfig.DEBUG) ChatLogLevel.ALL else ChatLogLevel.NOTHING)
    .build()
```

Levels: `ChatLogLevel.ALL`, `DEBUG`, `WARN`, `ERROR`, `NOTHING`.

For finer control, pass a `ChatLoggerHandler` via `.loggerHandler(...)` and bridge to your existing logger (Timber, etc.).

---

## Customization

### ChatTheme

`ChatTheme` is the entry point for all theming - colors, typography, formatters, image loaders, the component factory, etc. Build it once at the top of every Stream screen. By default `ChatTheme()` already picks light vs dark colors via `isSystemInDarkTheme()`; only customize when you need to override.

```kotlin
import io.getstream.chat.android.compose.ui.theme.ChatTheme
import io.getstream.chat.android.compose.ui.theme.StreamDesign
import androidx.compose.foundation.isSystemInDarkTheme

@Composable
fun MyChatTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) {
        StreamDesign.Colors.defaultDark()
    } else {
        StreamDesign.Colors.default()
    }
    val typography = StreamDesign.Typography.default()

    ChatTheme(
        colors = colors,
        typography = typography,
        // optional: componentFactory, dateFormatter, messageTextFormatter,
        //           channelNameFormatter, messagePreviewFormatter, ...
        content = content,
    )
}
```

> **Never guess `StreamDesign.Colors` token names.** The palette is built around two scales (`brand`, `chrome`) plus semantic tokens with the prefixes `accent*`, `text*`, `backgroundCore*`, `borderCore*`, `borderUtility*`, `avatarPalette*`. If a token isn't in the table below, fetch the source (`StreamDesign.kt`) before using it - guessing names like `primaryAccent` or `textHighEmphasis` will not compile.

**Confirmed `StreamDesign.Colors` tokens (commonly used):**

| Token | What it controls |
|---|---|
| `accentPrimary` | Send button, primary action accent |
| `accentError` | Destructive actions, error states |
| `textPrimary` | Main text on default surfaces |
| `textSecondary` | Secondary metadata text |
| `textTertiary` | Lowest-priority text, input placeholder |
| `textOnAccent` | Text on accent / dark backgrounds |
| `textLink` | Hyperlinks, mentions |
| `backgroundCoreApp` | Global application background |
| `backgroundCoreSurfaceDefault` | Standard section background |
| `backgroundCoreSurfaceStrong` | Stronger section background |
| `borderCoreDefault` | Standard surface border / dividers |
| `borderCoreStrong` | Stronger surface border |
| `borderCoreSubtle` | Very light separators |

Read tokens at the call site via `ChatTheme.colors.<token>`. Full reference: see `StreamDesign.kt` in the SDK or [getstream.io/chat/docs/sdk/android/compose/general-customization/chat-theme/](https://getstream.io/chat/docs/sdk/android/compose/general-customization/chat-theme/).

### Date formatting

```kotlin
import io.getstream.chat.android.ui.common.helper.DateFormatter
import java.text.SimpleDateFormat
import java.util.Date

val dateFormatter = object : DateFormatter {
    private val date = SimpleDateFormat("dd/MM/yyyy")
    private val time = SimpleDateFormat("HH:mm")

    override fun formatDate(date: Date?) = date?.let(this.date::format).orEmpty()
    override fun formatTime(date: Date?) = date?.let(this.time::format).orEmpty()
    override fun formatRelativeTime(date: Date?) = /* ... */ ""
    override fun formatRelativeDate(date: Date) = /* ... */ ""
}

ChatTheme(dateFormatter = dateFormatter) { /* content */ }
```

### Message text formatting

Override how message text is rendered (links, mentions, custom spans):

```kotlin
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.graphics.Color
import io.getstream.chat.android.compose.ui.util.MessageTextFormatter

val formatter = MessageTextFormatter { message, currentUser ->
    buildAnnotatedString {
        append(message.text)
        addStyle(SpanStyle(color = Color.Blue), 0, minOf(3, message.text.length))
    }
}

ChatTheme(messageTextFormatter = formatter) { /* content */ }
```

`MessageTextFormatter.composite(default, custom)` lets you layer formatters; `MessageTextFormatter.defaultFormatter(...)` rebuilds the SDK default with extra spans.

### Custom attachment factories

Attachment rendering goes through `AttachmentFactory` instances on `ChatTheme(attachmentFactories = ...)`. Build a list that combines defaults with your own:

```kotlin
import io.getstream.chat.android.compose.ui.attachments.StreamAttachmentFactories
import io.getstream.chat.android.compose.ui.attachments.AttachmentFactory

val factories = listOf(
    myCustomFactory,                // matched first
) + StreamAttachmentFactories.defaultFactories()

ChatTheme(attachmentFactories = factories) { /* content */ }
```

For a step-by-step custom-attachment guide, see [getstream.io/chat/docs/sdk/android/compose/guides/adding-custom-attachments/](https://getstream.io/chat/docs/sdk/android/compose/guides/adding-custom-attachments/).

### Component factory customization

Bound components do **not** expose `itemContent` / `emptyContent` / `loadingContent` / `trailingContent` slot lambdas. Sub-piece customization (channel item rows, list headers, empty/loading states, message item parts, the input row, etc.) goes through **`ChatComponentFactory`**, an interface with one `@Composable` method per overridable piece.

Override the pieces you want, then pass your factory to `ChatTheme(componentFactory = ...)`. Everything you don't override falls back to the SDK default.

```kotlin
import io.getstream.chat.android.compose.ui.theme.ChatComponentFactory
import io.getstream.chat.android.compose.ui.theme.ChatTheme
// Param types live alongside the factory under io.getstream.chat.android.compose.ui.theme.*

class CustomComponentFactory : ChatComponentFactory {
    // Override only what you need; default impls cover the rest.
    @Composable
    override fun RowScope.ChannelItemCenterContent(params: ChannelItemCenterContentParams) {
        // Custom name/last-message layout
    }
}

ChatTheme(componentFactory = CustomComponentFactory()) {
    ChannelsScreen(/* ... */)
}
```

Common factory entry points (look up the `Params` types in `ChatComponentFactory.kt`):

| Method | Overrides |
|---|---|
| `ChannelListItemContent(...)` | Whole channel row (incl. swipe wrapper) |
| `ChannelItemLeadingContent(...)` | Channel row avatar slot |
| `ChannelItemCenterContent(...)` | Channel row name + last message |
| `ChannelItemTrailingContent(...)` | Channel row timestamp + unread indicator |
| `ChannelListHeader(...)` | Header rendered by `ChannelsScreen` |
| `ChannelListEmptyContent(...)` | Empty-state of the channel list |
| `ChannelListLoadingIndicator(...)` | Initial-load placeholder |
| `MessageListEmptyContent(...)` | Empty-state of a channel |
| `MessageComposer(...)` / `MessageComposerInput(...)` | Composer surface and input row |

> **Never guess factory method or `Params` field names from training data.** They evolve between SDK versions - verify against `ChatComponentFactory.kt` (or the [component-architecture docs](https://getstream.io/chat/docs/sdk/android/compose/component-architecture/)) before overriding.

`ChannelsScreen` itself accepts a few high-level parameters that *are* available without a factory: `viewModelFactory`, `title`, `isShowingHeader`, `searchMode = SearchMode.{None,Channels,Messages}`, `onChannelClick`, `onSearchMessageItemClick`, `onHeaderAvatarClick`, `onBackPressed`. Use those for screen-level wiring and reach for `ChatComponentFactory` only when you need to replace a sub-piece.

---

## Gotchas

- **Never use `ChatClient.devToken(userId)` in production.** Dev tokens disable token verification and let any client impersonate any user.
- **Never store your Stream API secret in the app.** Secrets on-device can be extracted from rooted devices and enable destructive actions on your app instance.
- **Always wait for `disconnect()` completion before connecting another user.** The SDK uses Room for offline persistence and runs optimistic updates; connecting a new user while disconnect is in flight risks state corruption.
- **`ChatClient.Builder(...).build()` registers a singleton.** Calling it twice replaces the previous instance and orphans existing socket subscriptions. Build once in `Application.onCreate()`.
- **`ChatClient.instance()` throws if the Builder has not run yet.** Make sure your `Application` class is declared in the manifest (`<application android:name=".App" ... />`) and that `Application.onCreate()` has completed before any Stream Composable renders.
- **`INTERNET` permission is required.** Without it, every Stream API call fails silently or with cryptic socket errors.
- **Never instantiate Stream ViewModels inside Composables.** Use `viewModels { factory }` or `hiltViewModel()`. A `remember { factory.create(...) }` recreates state across configuration changes.
- **`ChannelListViewModelFactory(filters = null)` uses the default query** (`members in [currentUserId]`). Pass an explicit `Filters` expression only when you need a custom slice.
- **Drop-in screens already include their own `Scaffold` and back-handling.** Don't wrap `ChannelsScreen` / `ChannelScreen` in another `Scaffold`; pass the navigation callback (`onBackPressed`, `onChannelClick`) to integrate with your `NavHost`.
- **`TokenProvider.loadToken()` is synchronous.** Block on your backend call inside it; the SDK runs the provider off the main thread and re-invokes it on expiry.
- **State-layer extensions (`watchChannelAsState`, `queryChannelsAsState`) live under `io.getstream.chat.android.client.api.state`** and ship in `stream-chat-android-client` directly. You do not need a separate plugin to call them; the Compose artifact already brings the client in transitively.
