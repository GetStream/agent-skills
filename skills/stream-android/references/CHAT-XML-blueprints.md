# Chat XML — Screen Blueprints

Load only the section you are implementing. For setup, client initialization, and gotchas, see [CHAT-XML.md](CHAT-XML.md).

Per [`RULES.md`](../RULES.md) → *Blueprints are mandatory, on every turn*: any Stream Chat XML View, Fragment, Activity, navigation handler, deep-link route, or UI customization must be preceded by reading the matching section below — including on follow-up turns inside an existing session.

---

## Request → Blueprint section

| User request signal | Section(s) to read |
|---|---|
| "set up Stream", "initialize ChatClient", `Application` class, manifest wiring | [Application Class Blueprint](#application-class-blueprint) |
| "root host", "skip login if connected", "auto-reconnect", entry Activity | [Root Host Activity Blueprint](#root-host-activity-blueprint) |
| "login screen", "connect user", `connectUser`, token wiring | [Login Activity Blueprint](#login-activity-blueprint) |
| "channel list", `ChannelListFragment`, `ChannelListView`, channel filters/sort | [Channel List Blueprint](#channel-list-blueprint) |
| "channel screen", "message list", "open a channel", `ChannelFragment`, `MessageListView` + `MessageComposerView` | [Channel Screen Blueprint](#channel-screen-blueprint) |
| "navigate to channel", "open channel on tap", "tap a channel", channel click handler | [Channel Tap Handling / Deep-link Blueprint](#channel-tap-handling--deep-link-blueprint) + [Channel Screen Blueprint](#channel-screen-blueprint) |
| "deep link", push notification → channel, intent extras for `cid` | [Channel Tap Handling / Deep-link Blueprint](#channel-tap-handling--deep-link-blueprint) |
| "theme", colors, custom row layout, branding via `TransformStyle` | [Custom Theming Blueprint](#custom-theming-blueprint) |
| "custom channel item", channel row layout, custom view holder | [Custom Channel Item Blueprint](#custom-channel-item-blueprint) |
| "logout", switch users, tear down session | [Logout Blueprint](#logout-blueprint) |

If the request is something not covered (Video, Feeds, Compose, or an XML surface not listed above), do not fabricate APIs — say the blueprint is not bundled and fall back per [`RULES.md`](../RULES.md).

---

## Application Class Blueprint

Build `ChatClient` and configure global SDK state (`ChatUI`, `TransformStyle`) once in `Application.onCreate()`, before any Stream View inflates.

```kotlin
package com.example.streamchat

import android.app.Application
import android.content.pm.ApplicationInfo
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.client.logger.ChatLogLevel

class App : Application() {
    override fun onCreate() {
        super.onCreate()

        configureChatUi()

        val logLevel = if ((applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0) ChatLogLevel.ALL else ChatLogLevel.NOTHING

        ChatClient.Builder("your_api_key", applicationContext)
            .logLevel(logLevel)
            .build()
    }

    private fun configureChatUi() {
        // Optional: ChatUI / TransformStyle configuration goes here.
        // See the Custom Theming Blueprint.
    }
}
```

Register the `Application` in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    android:theme="@style/Theme.MyApp"
    android:label="@string/app_name">
    <!-- activities ... -->
</application>
```

**Wiring:**
- `Application.onCreate()` runs before any Activity, so `ChatClient.instance()` is safe to call from any Activity / Fragment lifecycle method.
- The host application theme **must** descend from `Theme.MaterialComponents.*` or `Theme.Material3.*` — Stream Views read Material attributes at inflation time.
- The XML SDK artifact transitively pulls in offline + state plugins; no extra Builder calls are required for default behavior.

---

## Root Host Activity Blueprint

Gate the app on connection state. Skips login if a previous session is still connected.

```kotlin
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import io.getstream.chat.android.client.ChatClient

class StartupActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val next = if (ChatClient.instance().getCurrentUser() != null) {
            Intent(this, ChannelsActivity::class.java)
        } else {
            Intent(this, LoginActivity::class.java)
        }
        startActivity(next)
        finish()
    }
}
```

Mark `StartupActivity` as the launcher in `AndroidManifest.xml`:

```xml
<activity android:name=".StartupActivity"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>
```

**Wiring:**
- `ChatClient.instance().getCurrentUser()` is non-null while a user is connected and survives process restarts when offline persistence is enabled (default).
- For a single-Activity app with Navigation Component, replace this Activity with a start destination that branches the same way before inflating any Stream View.

---

## Login Activity Blueprint

Show a login Activity before connecting. Invoke `connectUser` once per session, not on every Activity entry.

```kotlin
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.models.User
import io.getstream.result.Result

class LoginActivity : AppCompatActivity(R.layout.activity_login) {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val userIdField = findViewById<EditText>(R.id.userIdField)
        val nameField = findViewById<EditText>(R.id.nameField)
        val errorLabel = findViewById<TextView>(R.id.errorLabel)
        val progress = findViewById<ProgressBar>(R.id.progress)
        val connect = findViewById<Button>(R.id.connectButton)

        connect.setOnClickListener {
            val userId = userIdField.text.toString().trim()
            if (userId.isEmpty()) return@setOnClickListener

            connect.isEnabled = false
            progress.visibility = ProgressBar.VISIBLE
            errorLabel.text = ""

            val user = User(
                id = userId,
                name = nameField.text.toString().ifBlank { userId },
            )

            // Demo wiring only. In production, fetch the token from your backend
            // and pass a TokenProvider to connectUser instead of a static string.
            ChatClient.instance()
                .connectUser(user, token = "your_static_token_here")
                .enqueue { result ->
                    progress.visibility = ProgressBar.GONE
                    connect.isEnabled = true
                    when (result) {
                        is Result.Success -> {
                            startActivity(Intent(this, ChannelsActivity::class.java))
                            finish()
                        }
                        is Result.Failure -> errorLabel.text = result.value.message
                    }
                }
        }
    }
}
```

`activity_login.xml` is a vertical `LinearLayout` (or `ConstraintLayout`) with `R.id.userIdField`, `R.id.nameField`, `R.id.errorLabel`, `R.id.progress`, `R.id.connectButton`.

**Wiring:**
- `connectUser(...).enqueue { ... }` already hops back to the main thread for the callback — Activity state updates are safe to write directly.
- For an expiring token, swap the `token = "..."` argument for a `TokenProvider` (see [CHAT-XML.md — User Authentication](CHAT-XML.md#user-authentication)).

---

## Channel List Blueprint

### Drop-in `ChannelListFragment`

The Fragment supplies the header, search, and list. The host Activity implements the listener interfaces and the SDK auto-discovers them via `findListener()`. **Do not** call `.setOnXxxClickListener(...)` on the inner Views from the host — they are reset whenever the Fragment re-binds.

```kotlin
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import io.getstream.chat.android.models.Channel
import io.getstream.chat.android.models.Message
import io.getstream.chat.android.ui.feature.channels.ChannelListFragment

class ChannelsActivity :
    AppCompatActivity(R.layout.activity_channels),
    ChannelListFragment.ChannelListItemClickListener,
    ChannelListFragment.HeaderActionButtonClickListener,
    ChannelListFragment.HeaderUserAvatarClickListener,
    ChannelListFragment.SearchResultClickListener {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) {
            supportFragmentManager.beginTransaction()
                .replace(
                    R.id.container,
                    ChannelListFragment.newInstance {
                        showHeader(true)
                        showSearch(true)
                        headerTitle("Messages")
                    },
                )
                .commit()
        }
    }

    override fun onChannelClick(channel: Channel) {
        startActivity(ChannelActivity.createIntent(this, cid = channel.cid))
    }

    override fun onActionButtonClick() { /* open new-channel sheet */ }
    override fun onUserAvatarClick() { /* open profile / logout */ }
    override fun onSearchResultClick(message: Message) {
        startActivity(ChannelActivity.createIntent(this, cid = message.cid, messageId = message.id))
    }
}
```

`activity_channels.xml`:

```xml
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/container"
    android:layout_width="match_parent"
    android:layout_height="match_parent" />
```

### Bound `ChannelListView` (custom shell)

Drop down to the View when you want a custom Activity layout (e.g. tabs, a master-detail pane).

```kotlin
import androidx.activity.viewModels
import io.getstream.chat.android.client.ChatClient
import io.getstream.chat.android.models.Filters
import io.getstream.chat.android.models.querysort.QuerySortByField
import io.getstream.chat.android.ui.feature.channels.list.ChannelListView
import io.getstream.chat.android.ui.viewmodel.channels.ChannelListViewModel
import io.getstream.chat.android.ui.viewmodel.channels.ChannelListViewModelFactory
import io.getstream.chat.android.ui.viewmodel.channels.bindView

class CustomChannelsShellActivity : AppCompatActivity(R.layout.activity_custom_channels) {

    private val factory by lazy {
        ChannelListViewModelFactory(
            filter = Filters.and(
                Filters.eq("type", "messaging"),
                Filters.`in`("members", listOf(ChatClient.instance().getCurrentUser()?.id ?: "")),
            ),
            sort = QuerySortByField.descByName("last_updated"),
            limit = 30,
        )
    }
    private val viewModel: ChannelListViewModel by viewModels { factory }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val channelListView = findViewById<ChannelListView>(R.id.channelListView)
        viewModel.bindView(channelListView, this)
        channelListView.setChannelItemClickListener { channel ->
            startActivity(ChannelActivity.createIntent(this, cid = channel.cid))
        }
    }
}
```

**Wiring:**
- `ChannelListFragment.newInstance { ... }` exposes only `customTheme(themeResId)`, `showHeader(...)`, `showSearch(...)`, `headerTitle(...)`. Filter / sort customization is done by overriding `getFilter()` / `getSort()` in a `ChannelListFragment` subclass — `newInstance` does not accept those.
- Bound `ChannelListView` listeners (`setChannelItemClickListener`, `setChannelLongClickListener`, `setChannelDeleteClickListener`, `setChannelLeaveClickListener`) **are** wired directly on the View — they are overwritten by `bindView` only for state, not for clicks.
- Always call `bindView` from the host's `onCreate` (or `onViewCreated`), not from a callback — the binding subscribes to the lifecycle owner you pass in.

---

## Channel Screen Blueprint

### Drop-in `ChannelFragment`

The SDK ships a self-contained Fragment that stacks `ChannelHeaderView`, `MessageListView`, and `MessageComposerView` and wires all three ViewModels.

```kotlin
import android.content.Context
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import io.getstream.chat.android.ui.feature.messages.ChannelFragment

class ChannelActivity :
    AppCompatActivity(R.layout.activity_channel),
    ChannelFragment.BackPressListener {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val cid = intent.getStringExtra(EXTRA_CID) ?: error("cid required")
        val messageId = intent.getStringExtra(EXTRA_MESSAGE_ID)

        if (savedInstanceState == null) {
            supportFragmentManager.beginTransaction()
                .replace(
                    R.id.container,
                    ChannelFragment.newInstance(cid) {
                        showHeader(true)
                        messageId(messageId)
                    },
                )
                .commit()
        }
    }

    override fun onBackPress() {
        finish()
    }

    companion object {
        const val EXTRA_CID = "cid"
        const val EXTRA_MESSAGE_ID = "messageId"

        fun createIntent(context: Context, cid: String, messageId: String? = null) =
            Intent(context, ChannelActivity::class.java)
                .putExtra(EXTRA_CID, cid)
                .putExtra(EXTRA_MESSAGE_ID, messageId)
    }
}
```

`activity_channel.xml`:

```xml
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/container"
    android:layout_width="match_parent"
    android:layout_height="match_parent" />
```

### Custom screen layout (bound trio)

When the drop-in Fragment doesn't fit (custom toolbar, a side pane, extra Views around the composer), inflate the three Views yourself and wire them with the shared `ChannelViewModelFactory`:

`activity_custom_channel.xml`:

```xml
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent">

    <io.getstream.chat.android.ui.feature.messages.header.ChannelHeaderView
        android:id="@+id/channelHeaderView"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <io.getstream.chat.android.ui.feature.messages.list.MessageListView
        android:id="@+id/messageListView"
        android:layout_width="0dp"
        android:layout_height="0dp"
        app:layout_constraintTop_toBottomOf="@id/channelHeaderView"
        app:layout_constraintBottom_toTopOf="@id/messageComposerView"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <io.getstream.chat.android.ui.feature.messages.composer.MessageComposerView
        android:id="@+id/messageComposerView"
        android:layout_width="0dp"
        android:layout_height="wrap_content"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

</androidx.constraintlayout.widget.ConstraintLayout>
```

```kotlin
import androidx.activity.viewModels
import io.getstream.chat.android.ui.viewmodel.messages.ChannelHeaderViewModel
import io.getstream.chat.android.ui.viewmodel.messages.ChannelViewModelFactory
import io.getstream.chat.android.ui.viewmodel.messages.MessageComposerViewModel
import io.getstream.chat.android.ui.viewmodel.messages.MessageListViewModel
import io.getstream.chat.android.ui.viewmodel.messages.bindView

class CustomChannelActivity : AppCompatActivity(R.layout.activity_custom_channel) {

    private val cid: String get() = intent.getStringExtra(EXTRA_CID) ?: error("cid required")
    private val factory by lazy { ChannelViewModelFactory(applicationContext, cid = cid) }

    private val headerViewModel: ChannelHeaderViewModel by viewModels { factory }
    private val listViewModel: MessageListViewModel by viewModels { factory }
    private val composerViewModel: MessageComposerViewModel by viewModels { factory }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        headerViewModel.bindView(findViewById(R.id.channelHeaderView), this)
        listViewModel.bindView(findViewById(R.id.messageListView), this)
        composerViewModel.bindView(findViewById(R.id.messageComposerView), this)

        findViewById<io.getstream.chat.android.ui.feature.messages.header.ChannelHeaderView>(R.id.channelHeaderView)
            .setBackButtonClickListener { finish() }
    }

    companion object { const val EXTRA_CID = "cid" }
}
```

**Wiring:**
- `ChannelFragment.newInstance(cid) { ... }` exposes `customTheme(themeResId)`, `showHeader(...)`, `messageId(...)`, `threadLoadOlderToNewer(...)`. Anything beyond that requires either subclassing `ChannelFragment` or building the trio yourself.
- `ChannelViewModelFactory(applicationContext, cid)` resolves all three ViewModels (`ChannelHeaderViewModel`, `MessageListViewModel`, `MessageComposerViewModel`) from a single factory instance — that's what makes `viewModels { factory }` reuse the same factory cleanly.
- The `bindView` extensions wire cross-View defaults (composer edit/reply state, jump-to-quoted-message). Don't re-implement those handlers unless you're replacing them.
- `MessageListView`, `MessageComposerView`, and `ChannelHeaderView` each expose their own listener setters (`setBackButtonClickListener`, `setMessageEditHandler`, etc.) — use them for navigation hooks; do not try to drive them through ViewModels.

---

## Channel Tap Handling / Deep-link Blueprint

### Route a tap into your channel destination

```kotlin
override fun onChannelClick(channel: Channel) {
    startActivity(ChannelActivity.createIntent(this, cid = channel.cid))
}
```

`onChannelClick` is the listener method on `ChannelListFragment.ChannelListItemClickListener` — implement it on the host Activity (or parent Fragment) and the SDK auto-discovers it. For the bound `ChannelListView`, use `setChannelItemClickListener { channel -> ... }`.

### Intercept a tap without navigating

For analytics, an action sheet, or a side-effect-only tap, return without launching a destination:

```kotlin
override fun onChannelClick(channel: Channel) {
    analytics.track("channel_tapped", mapOf("cid" to channel.cid))
    // no navigation
}
```

### Deep-link from a push notification

Stream's `NotificationHandlerFactory.createNotificationHandler(...)` calls a `newMessageIntent` lambda when the user taps a chat push. Build an Intent that launches your channel destination directly with the `cid` and optional `messageId`:

```kotlin
// In your Application's ChatClient.Builder(...) chain:
val notificationConfig = NotificationConfig(
    pushDeviceGenerators = listOf(/* FirebasePushDeviceGenerator(...) */),
)
val notificationHandler = NotificationHandlerFactory.createNotificationHandler(
    context = applicationContext,
    notificationConfig = notificationConfig,
    newMessageIntent = { message, channel ->
        ChannelActivity.createIntent(
            context = applicationContext,
            cid = channel.cid,
            messageId = message.id,
        )
    },
)

ChatClient.Builder(apiKey, applicationContext)
    .notifications(notificationConfig, notificationHandler)
    .build()
```

In `ChannelActivity`, read the extras into the `ChannelFragment.Builder`:

```kotlin
ChannelFragment.newInstance(cid) {
    messageId(intent.getStringExtra(EXTRA_MESSAGE_ID))
}
```

**Wiring:**
- `Channel.cid` is the canonical `"<type>:<id>"` string — pass it as a single intent extra instead of two separate fields.
- `messageId(...)` jumps the message list to that message on first display (used by push deep-links).
- The pre-built `ChannelListFragment` does not select a channel by id on its own — for a master-detail layout that highlights the current channel, drop down to bound `ChannelListView` + your own selection state.

---

## Custom Theming Blueprint

The XML SDK has two paths. Use whichever is shorter for the change you need; reach for `TransformStyle` first.

### `TransformStyle` (runtime, code-only)

Set transformers in `Application.onCreate()` before any Stream View inflates. Each `*Style` is a `data class` — use `.copy(...)` with named parameters. Open the matching style class in the SDK source before referencing a field; do not enumerate fields from memory.

```kotlin
import io.getstream.chat.android.ui.helper.StyleTransformer
import io.getstream.chat.android.ui.helper.TransformStyle

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        configureStyleTransformers()
        ChatClient.Builder("your_api_key", applicationContext).build()
    }

    private fun configureStyleTransformers() {
        TransformStyle.channelListStyleTransformer = StyleTransformer { defaultStyle ->
            defaultStyle.copy(/* fields on ChannelListViewStyle */)
        }
        // Same pattern for messageListStyleTransformer, messageListItemStyleTransformer,
        // messageComposerStyleTransformer, channelHeaderStyleTransformer, and the
        // many specialized transformers (avatars, reactions, attachments, search,
        // audio recorder, thread list, …) declared in TransformStyle.kt.
    }
}
```

### XML theme attribute overlay

Brand the entire SDK at the theme level by inheriting from a Material theme and overriding the relevant attributes. Apply the theme on `<application>` (or on the host Activity).

```xml
<!-- res/values/themes.xml -->
<style name="Theme.MyApp" parent="Theme.MaterialComponents.DayNight.NoActionBar">
    <item name="colorPrimary">@color/brand_primary</item>
    <item name="colorOnSurface">@color/brand_on_surface</item>
    <!-- Stream-specific attribute overrides go here. Verify any
         streamUi* attribute against the SDK's attrs.xml before using it. -->
</style>
```

```xml
<!-- AndroidManifest.xml -->
<application
    android:name=".App"
    android:theme="@style/Theme.MyApp">
    <!-- ... -->
</application>
```

**Wiring:**
- `TransformStyle.*` is set-and-leave: once configured, every subsequent inflation of the matching View applies the override. Setting it after a View is already on screen does not refresh the live View — recreate the Activity / Fragment to pick up changes.
- Prefer `TransformStyle` for code-driven branding; reach for XML attributes when you need theme variants (light/dark/branded) coordinated with the rest of your app's theming.
- The host Activity's theme **must** descend from a `Theme.MaterialComponents.*` or `Theme.Material3.*` family — Stream Views read Material attributes during inflation.

---

## Custom Channel Item Blueprint

For style-only changes (text size, avatar size, bubble drawables), use `TransformStyle.channelListStyleTransformer` instead — see [Custom Theming Blueprint](#custom-theming-blueprint). Drop down to a `ChannelListItemViewHolderFactory` only when you need a fundamentally different row layout.

```kotlin
import android.view.LayoutInflater
import android.view.ViewGroup
import io.getstream.chat.android.ui.feature.channels.list.adapter.ChannelListItem
import io.getstream.chat.android.ui.feature.channels.list.adapter.viewholder.BaseChannelListItemViewHolder
import io.getstream.chat.android.ui.feature.channels.list.adapter.viewholder.ChannelListItemViewHolderFactory

class CustomChannelListItemViewHolderFactory : ChannelListItemViewHolderFactory() {

    override fun createViewHolder(
        parentView: ViewGroup,
        viewType: Int,
    ): BaseChannelListItemViewHolder {
        if (viewType == TYPE_CUSTOM) {
            val binding = ItemCustomChannelBinding.inflate(
                LayoutInflater.from(parentView.context), parentView, false,
            )
            return CustomChannelViewHolder(
                binding,
                listenerContainer.channelClickListener,
                listenerContainer.channelLongClickListener,
            )
        }
        return super.createViewHolder(parentView, viewType)
    }

    override fun getItemViewType(item: ChannelListItem): Int {
        if (item is ChannelListItem.ChannelItem) return TYPE_CUSTOM
        return super.getItemViewType(item)
    }

    companion object {
        private const val TYPE_CUSTOM = 1
    }
}
```

The base factory exposes `listenerContainer: ChannelListListenerContainer` (with `channelClickListener`, `channelLongClickListener`, `deleteClickListener`, `moreOptionsClickListener`, `userClickListener`, `swipeListener`), `visibilityContainer`, `iconProviderContainer`, and `style` — pass through whichever your custom view holder needs.

```kotlin
// Wire on the View (bound shell):
channelListView.setViewHolderFactory(CustomChannelListItemViewHolderFactory())
```

**Wiring:**
- `ChannelListItem.ChannelItem` exposes `channel: Channel` — read name, last message, etc. off `channel`. For unread count, use the extension `channel.currentUserUnreadCount()` from `io.getstream.chat.android.client.extensions`.
- Subclass `BaseChannelListItemViewHolder` for your custom view holder; override `bind(channelItem, diff)` to update on data changes.
- Always delegate to `super.createViewHolder(...)` / `super.getItemViewType(...)` for items you don't customize, so built-in row types still render.
- For `ChannelListFragment`, override `setupChannelList(channelListView)` in a Fragment subclass and call `setViewHolderFactory(...)` there.

---

## Logout Blueprint

For full logout (no follow-up `connectUser`), `disconnect(flushPersistence = true)` to clear the Room cache. For switching to another user in one call, prefer `ChatClient.switchUser(...)` — it disconnects, deletes the push device, and connects the new user atomically.

```kotlin
import android.content.Intent
import io.getstream.chat.android.client.ChatClient
import io.getstream.result.Result

fun logout(onComplete: () -> Unit) {
    ChatClient.instance().disconnect(flushPersistence = true).enqueue { result ->
        when (result) {
            is Result.Success -> onComplete()
            is Result.Failure -> { /* surface error */ }
        }
    }
}

// Usage — switch to login after logout:
logout {
    startActivity(
        Intent(this, LoginActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK),
    )
}
```

User switching (replace logout + login with a single call):

```kotlin
ChatClient.instance().switchUser(nextUser, nextToken).enqueue { result ->
    when (result) {
        is Result.Success -> { /* connected as next user */ }
        is Result.Failure -> { /* surface error */ }
    }
}
```

**Wiring:**
- `disconnect(flushPersistence = true)` clears the Room cache; pass `false` when you want to keep cached channels for the same user across temporary disconnects.
- `disconnect(...).enqueue { ... }` already hops back to the main thread for the callback — Activity / navigation calls are safe to make directly.
- `switchUser(user, token)` and `switchUser(user, tokenProvider)` are both `@JvmOverloads`; use the `TokenProvider` form for expiring tokens.
- If you roll your own switch via `disconnect(...).enqueue { connectUser(...) }`, do not call `connectUser(...)` inside the disconnect callback's `Result.Failure` branch unless you've handled the underlying error first; retrying immediately can loop on the same failing token.
