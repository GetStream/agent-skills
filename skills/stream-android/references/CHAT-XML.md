# Chat - XML SDK Setup & Integration

The Stream Chat XML SDK is the View-based Android SDK (artifact `stream-chat-android-ui-components`) — pre-built Views and Fragments for messaging UIs that drop into any AppCompat / Material project. This file covers Gradle setup, client setup, authentication, customization, and gotchas. For screen blueprints, see [CHAT-XML-blueprints.md](CHAT-XML-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper logout).

- **Blueprint** — Fragment / Activity structure and View wiring
- **Wiring** — SDK calls for each View and ViewModel, exact extension paths
- **Requirements** — `minSdk` 21+, AppCompat / Material theme on the host Activity, Kotlin

## Quick ref

- **Target version:** Stream Chat Android **v7.x** (see [RULES.md](../RULES.md) — if your memory disagrees with the docs, trust the docs)
- **Artifact (XML / Views):** `io.getstream:stream-chat-android-ui-components` via Maven Central
- **Artifact (core only):** `io.getstream:stream-chat-android-client` (pulled in transitively)
- **First:** Installation -> Manifest -> `ChatClient` build -> `connectUser` -> `ChannelListFragment` in an Activity
- **Per feature:** Jump to the relevant section or blueprint when wiring a screen
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/chat/docs/sdk/android/ui/overview/`

Full screen blueprints: [CHAT-XML-blueprints.md](CHAT-XML-blueprints.md) — load only the section you are implementing.

---

## App Integration

### Installation (Gradle)

Check if the SDK is already installed in the project. If not:

**With version catalog (`gradle/libs.versions.toml`):**

```toml
[versions]
stream-chat-ui-components = "<latest>"

[libraries]
stream-chat-ui-components = { module = "io.getstream:stream-chat-android-ui-components", version.ref = "stream-chat-ui-components" }
```

```kotlin
// app/build.gradle.kts
dependencies {
    implementation(libs.stream.chat.ui.components)
}
```

**Without version catalog:**

```kotlin
// app/build.gradle.kts
dependencies {
    implementation("io.getstream:stream-chat-android-ui-components:<latest>")
}
```

If you don't know the latest version, follow [`RULES.md`](../RULES.md) → *Version lookup*.

The host Activity's theme must descend from a `Theme.MaterialComponents.*` or `Theme.Material3.*` family — Stream Views read Material attributes (`colorPrimary`, `colorOnSurface`, …). Adding a fresh AppCompat-only theme will cause inflate-time crashes on Stream Views.

### Client Initialization

Initialize once in your `Application` class. **Never** create `ChatClient` inside an `Activity.onCreate` that re-runs, a Fragment, or a callback — the Builder registers a singleton.

```kotlin
import android.app.Application
import android.content.pm.ApplicationInfo
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.client.logger.ChatLogLevel

class App : Application() {
    override fun onCreate() {
        super.onCreate()

        val logLevel = if ((applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0) ChatLogLevel.ALL else ChatLogLevel.NOTHING

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

After build time, retrieve the client anywhere via `ChatClient.instance()`. The Builder registers the singleton automatically — do **not** store your own copy as a top-level `lateinit var`.

### User Authentication

**Default — hardcoded token (no expiry):**

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

**Token provider (expiring tokens):**

```kotlin
import io.getstream.chat.android.client.token.TokenProvider

val tokenProvider = object : TokenProvider {
    override fun loadToken(): String =
        yourAuthService.fetchStreamToken(userId = user.id)
}

ChatClient.instance()
    .connectUser(user, tokenProvider)
    .enqueue { /* ... */ }
```

`TokenProvider.loadToken()` is synchronous — block on your backend call inside it; the SDK runs the provider off the main thread and re-invokes it whenever the token expires.

### Disconnecting / switching users

For switching to another user, prefer `ChatClient.switchUser(...)` — it disconnects the current user, deletes the push device, and connects the new user atomically:

```kotlin
ChatClient.instance().switchUser(nextUser, nextToken).enqueue { result ->
    when (result) {
        is Result.Success -> { /* connected as next user */ }
        is Result.Failure -> { /* handle error */ }
    }
}
```

For a full logout (no follow-up `connectUser`), call `disconnect(flushPersistence = true)` to clear the offline cache. If you do roll your own switch via `disconnect(...).enqueue { connectUser(...) }`, always wait for `disconnect()` to complete before connecting — connecting in flight risks state corruption.

### Showing the Channel List

The drop-in `ChannelListFragment` renders the channel list, header, and search. Host it inside an `AppCompatActivity` and implement listener interfaces on the host — the Fragment auto-discovers them via `findListener()`:

```kotlin
import androidx.appcompat.app.AppCompatActivity
import io.getstream.chat.android.models.Channel
import io.getstream.chat.android.ui.feature.channels.ChannelListFragment

class ChannelsActivity :
    AppCompatActivity(R.layout.activity_channels),
    ChannelListFragment.ChannelListItemClickListener,
    ChannelListFragment.HeaderActionButtonClickListener,
    ChannelListFragment.HeaderUserAvatarClickListener {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) {
            supportFragmentManager.beginTransaction()
                .replace(R.id.container, ChannelListFragment.newInstance {
                    showHeader(true)
                    showSearch(true)
                })
                .commit()
        }
    }

    override fun onChannelClick(channel: Channel) { /* navigate to ChannelActivity */ }
    override fun onActionButtonClick() { /* new-channel sheet */ }
    override fun onUserAvatarClick() { /* open profile / logout */ }
}
```

The host Activity's `R.layout.activity_channels` is a single `FrameLayout` with `android:id="@+id/container"`. The Fragment supplies its own header, search, and list inflated from `StreamUiFragmentChannelListBinding`.

---

## ChatUI Global Config

`ChatUI` is the XML SDK's process-wide configuration object — the View-based equivalent of Compose's `ChatTheme(componentFactory = ...)`. Set fields once before any Stream View inflates (typically in `Application.onCreate()` or the host Activity before `setContentView`).

```kotlin
import io.getstream.chat.android.ui.ChatUI

ChatUI.fonts = MyChatFonts()
ChatUI.dateFormatter = MyDateFormatter()
ChatUI.channelNameFormatter = ChannelNameFormatter { channel, currentUser ->
    channel.name.ifEmpty { channel.cid }
}
ChatUI.messagePreviewFormatter = MessagePreviewFormatter { channel, message, currentUser ->
    message.text
}
ChatUI.userAvatarRenderer = MyUserAvatarRenderer()
ChatUI.channelAvatarRenderer = MyChannelAvatarRenderer()
```

> **Never guess `ChatUI` field names from training data.** Open `ChatUI.kt` in the SDK source before referencing a field — the public surface includes formatters (date, channel name, message preview), avatar renderers, attachment factory managers, fonts, and feature flags (`draftMessagesEnabled`, `autoTranslationEnabled`, `videoThumbnailsEnabled`, …).

`ChatUI` is set-and-leave: changing fields after a Stream View is already inflated does not refresh the live View — kill and recreate the Fragment / Activity to pick up changes.

---

## Themes and Styles

The XML SDK has two complementary styling paths. Use both.

### 1. Runtime style transformers (`TransformStyle`)

Override individual style fields in code, applied to every inflation of the matching View. Set transformers in `Application.onCreate()` before any Stream View inflates.

```kotlin
import io.getstream.chat.android.ui.helper.TransformStyle
import io.getstream.chat.android.ui.helper.StyleTransformer

TransformStyle.channelListStyleTransformer = StyleTransformer { defaultStyle ->
    defaultStyle.copy(/* fields on ChannelListViewStyle */)
}
```

Common transformers: `channelListStyleTransformer`, `messageListStyleTransformer`, `messageListItemStyleTransformer`, `messageComposerStyleTransformer`, `channelHeaderStyleTransformer`. The full set in `TransformStyle.kt` covers ~25+ surfaces — avatars, reactions, scroll button, attachments (file / media / giphy / poll / quoted), search input, mention list, typing indicator, audio recorder, thread list, etc. Each `*Style` is a `data class` — use `.copy(...)` with named parameters. Open `TransformStyle.kt` and the matching style class in the SDK source before referencing a transformer or field; do not enumerate from memory.

### 2. XML theme attributes

Stream Views read attributes off the host Activity's theme via the `streamUiTheme` attribute and the `streamUi*` namespaced attributes. To brand the entire SDK at the theme level, define a child theme in `res/values/themes.xml`:

```xml
<style name="Theme.MyApp" parent="Theme.MaterialComponents.DayNight.NoActionBar">
    <item name="colorPrimary">@color/brand_primary</item>
    <item name="colorOnSurface">@color/brand_on_surface</item>
    <!-- Stream-specific overrides go here, e.g. -->
    <!-- <item name="streamUiChannelListAvatarSize">48dp</item> -->
</style>
```

Apply the theme in `AndroidManifest.xml` on the application or activity. Use individual `streamUi*` attributes only when you've verified them against the SDK's `attrs.xml` — do not invent attribute names.

For most theming, **prefer `TransformStyle`** over per-attribute XML; it's terser, type-safe, and easier to maintain.

---

## ViewModel Patterns

Every Stream View has a matching ViewModel and a `bindView(view, lifecycleOwner)` extension that wires state and listeners in one call. **Always create ViewModels via a factory passed to `viewModels { factory }` (Activity / Fragment), or with Hilt via `by viewModels()` on a `@AndroidEntryPoint` host plus `@HiltViewModel` on the ViewModel — never inside a transient scope.** `hiltViewModel()` is a Compose-only API; do not use it from an Activity / Fragment.

### Channel list

```kotlin
import androidx.activity.viewModels
import io.getstream.chat.android.ui.feature.channels.list.ChannelListView
import io.getstream.chat.android.ui.viewmodel.channels.ChannelListViewModel
import io.getstream.chat.android.ui.viewmodel.channels.ChannelListViewModelFactory
import io.getstream.chat.android.ui.viewmodel.channels.bindView
import io.getstream.chat.android.models.Filters

class CustomChannelListActivity : AppCompatActivity(R.layout.activity_custom_channels) {

    private val factory by lazy {
        ChannelListViewModelFactory(
            filter = Filters.and(
                Filters.eq("type", "messaging"),
                Filters.`in`("members", listOf(ChatClient.instance().getCurrentUser()?.id ?: "")),
            ),
        )
    }
    private val viewModel: ChannelListViewModel by viewModels { factory }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val channelListView = findViewById<ChannelListView>(R.id.channelListView)
        viewModel.bindView(channelListView, this)
        channelListView.setChannelItemClickListener { channel -> /* navigate */ }
    }
}
```

`ChannelListViewModelFactory` parameters: `filter`, `sort` (default `ChannelListViewModel.DEFAULT_SORT`), `limit`, `messageLimit`, `memberLimit`, `isDraftMessagesEnabled`, `chatEventHandlerFactory`. `filter = null` falls back to `Filters.and(Filters.eq("type", "messaging"), Filters.in("members", listOf(currentUserId)))`.

### Channel screen (header + list + composer)

The three Views share a single factory (`ChannelViewModelFactory`) — one factory creates all three ViewModels.

```kotlin
import androidx.activity.viewModels
import io.getstream.chat.android.ui.viewmodel.messages.ChannelHeaderViewModel
import io.getstream.chat.android.ui.viewmodel.messages.ChannelViewModelFactory
import io.getstream.chat.android.ui.viewmodel.messages.MessageComposerViewModel
import io.getstream.chat.android.ui.viewmodel.messages.MessageListViewModel
import io.getstream.chat.android.ui.viewmodel.messages.bindView

class CustomChannelActivity : AppCompatActivity(R.layout.activity_custom_channel) {

    private val cid: String get() = intent.getStringExtra(EXTRA_CID) ?: "messaging:general"

    private val factory by lazy { ChannelViewModelFactory(applicationContext, cid = cid) }

    private val headerViewModel: ChannelHeaderViewModel by viewModels { factory }
    private val listViewModel: MessageListViewModel by viewModels { factory }
    private val composerViewModel: MessageComposerViewModel by viewModels { factory }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        headerViewModel.bindView(findViewById(R.id.channelHeaderView), this)
        listViewModel.bindView(findViewById(R.id.messageListView), this)
        composerViewModel.bindView(findViewById(R.id.messageComposerView), this)
    }

    companion object {
        const val EXTRA_CID = "cid"
    }
}
```

`ChannelViewModelFactory` parameters: `context`, `cid`, `messageId` (jump-to-message deep link), `parentMessageId` (open a thread), `threadLoadOlderToNewer`.

The `bindView` extensions also wire default behavior between the three Views (e.g. tapping a quoted message scrolls the list, the composer's edit/reply state syncs from the list). Don't reproduce those handlers manually unless you're replacing them.

---

## Logging

Disabled by default. Enable on the Builder, ideally only in debug builds:

```kotlin
ChatClient.Builder(apiKey, context)
    .logLevel(if ((context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0) ChatLogLevel.ALL else ChatLogLevel.NOTHING)
    .build()
```

Levels: `ChatLogLevel.ALL`, `DEBUG`, `WARN`, `ERROR`, `NOTHING`.

For finer control, pass a `ChatLoggerHandler` via `.loggerHandler(...)` and bridge to your existing logger (Timber, etc.).

---

## Gotchas

- **The host Activity must use a Material(Components) theme.** Stream Views read `colorPrimary`, `colorOnSurface`, and other Material attributes during inflation; a plain `Theme.AppCompat.*` will crash with a `MaterialAttributes` lookup failure.
- **Always wait for `disconnect()` completion before connecting another user.** The SDK uses Room for offline persistence and runs optimistic updates; connecting a new user while disconnect is in flight risks state corruption.
- **Build `ChatClient` once in `Application.onCreate()`, before any Stream View inflates.** `ChatClient.Builder(...).build()` registers a singleton (a second build orphans existing socket subscriptions); `ChatClient.instance()` throws until that first build completes.
- **`ChatUI` and `TransformStyle` must be configured before the first Stream View inflates** — typically in `Application.onCreate()`. Setting them later does not retroactively refresh visible Views.
- **Listener interfaces on `ChannelListFragment` are auto-discovered** via `findListener()` — implement them on the host Activity (or parent Fragment) instead of calling `.setOnXxxClickListener(...)` manually. Manual setters on the inner Views are overwritten when the Fragment re-binds.
- **Never instantiate Stream ViewModels in arbitrary scopes.** Use `viewModels { factory }` or `hiltViewModel()`. Creating them in a callback or local `lazy` outside the Activity scope leaks listeners and breaks state restoration.
- **`TokenProvider.loadToken()` is synchronous.** Block on your backend call inside it; the SDK runs the provider off the main thread and re-invokes it on expiry.
