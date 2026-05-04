# Video - Compose SDK Setup & Integration

Stream Video Compose provides pre-built Jetpack Compose components for building video and audio calling experiences. This file covers package installation, client setup, authentication, call flows, customization, and gotchas. For screen blueprints, see [VIDEO-COMPOSE-blueprints.md](VIDEO-COMPOSE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no fake credentials, client lifetime).

- **Blueprint** - Compose call-screen structure and initialization
- **Wiring** - SDK calls for each component, exact property paths
- **Requirements** - `INTERNET` in app manifest (CAMERA / RECORD_AUDIO / BLUETOOTH_CONNECT are merged in from the SDK manifest), runtime permission grant before joining a call, `minSdk` 24+, Kotlin + Jetpack Compose enabled in the app module.

## Quick ref

- **Artifact (Compose):** `io.getstream:stream-video-android-ui-compose` via Maven Central
- **Artifact (core only):** `io.getstream:stream-video-android-core` (pulled in transitively by the Compose artifact)
- **First:** Installation -> Manifest -> `StreamVideoBuilder(...).build()` -> `streamVideo.call(...)` -> `VideoTheme { CallContent(call) }`
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/video/docs/android/`

Full screen blueprints: [VIDEO-COMPOSE-blueprints.md](VIDEO-COMPOSE-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation (Gradle)

Check if the SDK is already installed in the project. If not:

**With version catalog (`gradle/libs.versions.toml`):**

```toml
[versions]
stream-video-compose = "<latest>"

[libraries]
stream-video-compose = { module = "io.getstream:stream-video-android-ui-compose", version.ref = "stream-video-compose" }
```

```kotlin
// app/build.gradle.kts
dependencies {
    implementation(libs.stream.video.compose)
}
```

**Without version catalog:**

```kotlin
// app/build.gradle.kts
dependencies {
    implementation("io.getstream:stream-video-android-ui-compose:<latest>")
}
```

If you don't know the latest version, look it up via the sources listed in [`RULES.md` -> Version lookup](../RULES.md#version-lookup) (Maven Central / GitHub releases). Never use `search.maven.org`.

Add the `INTERNET` permission to `AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET" />
```

`CAMERA`, `RECORD_AUDIO`, `BLUETOOTH_CONNECT`, `MODIFY_AUDIO_SETTINGS`, and `FOREGROUND_SERVICE` are declared in the SDK's library manifest and merged automatically — you do **not** need to add them again. You **do** need to request `CAMERA` / `RECORD_AUDIO` at runtime before joining a call (see [Permissions](#permissions)).

### Client Initialization

Build the `StreamVideo` client **once** at app launch via `StreamVideoBuilder(...).build()`. **Never** create it in a `@Composable` body, in a `remember { ... }` factory, or in an `Activity.onCreate` that re-runs - the builder registers a process-wide singleton.

```kotlin
import android.app.Application
import io.getstream.video.android.core.StreamVideo
import io.getstream.video.android.core.StreamVideoBuilder
import io.getstream.video.android.core.logging.LoggingLevel
import io.getstream.video.android.model.User

class App : Application() {
    override fun onCreate() {
        super.onCreate()

        val user = User(
            id = "user-id",
            name = "User Name",
            image = "https://example.com/avatar.png",
        )

        StreamVideoBuilder(
            context = applicationContext,
            apiKey = "your_api_key",
            user = user,
            token = "your_static_token_here",
            loggingLevel = LoggingLevel(if (BuildConfig.DEBUG) Priority.DEBUG else Priority.NONE),
        ).build()
    }
}
```

Register the `Application` subclass in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    ...>
```

After build time, retrieve the client anywhere via `StreamVideo.instance()` (throws if the builder has not run) or `StreamVideo.instanceOrNull()` (returns `null`). The builder registers the singleton automatically — do **not** store your own copy as a top-level `lateinit var`.

> If the user already initializes Stream Chat in the same `Application.onCreate()`, build both clients in the same method. They are independent singletons; see [Combined Chat + Video](#combined-chat--video).

---

## User Authentication

The API key and secret are shared between Stream Chat and Video — one project, one key.

### Static token (no expiry)

Pass the token as a `String` directly to `StreamVideoBuilder`:

```kotlin
val user = User(
    id = "alice",
    name = "Alice Smith",
    image = "https://example.com/alice.jpg",
)

StreamVideoBuilder(
    context = applicationContext,
    apiKey = "your_api_key",
    user = user,
    token = "your_static_token_here",
).build()
```

Token generation: `stream token <user_id>` (same CLI as Chat — see [`credentials.md`](../credentials.md)).

### Token provider (expiring tokens)

`TokenProvider` has a single `suspend` method. The SDK invokes it on a background dispatcher and re-invokes it automatically when the token expires:

```kotlin
import io.getstream.video.android.core.TokenProvider

val tokenProvider = object : TokenProvider {
    override suspend fun loadToken(): String =
        yourAuthService.fetchVideoToken(userId = user.id)
}

StreamVideoBuilder(
    context = applicationContext,
    apiKey = "your_api_key",
    user = user,
    token = initialToken,
    tokenProvider = tokenProvider,
).build()
```

`loadToken()` is a `suspend` function — call your backend with coroutines or `withContext(Dispatchers.IO)` inside it.

### Disconnecting / switching users

Tear the client down explicitly before constructing a new one for a different user:

```kotlin
StreamVideo.instance().logOut()
StreamVideo.removeClient()

// Then build again with the new user/token
StreamVideoBuilder(context, apiKey, newUser, newToken).build()
```

`StreamVideo.removeClient()` clears the singleton so `StreamVideoBuilder` can register a new one. Skipping it leaves the previous instance live and ignores the new user.

---

## Call object

Calls are obtained from the client by `type` and `id`. The same `(type, id)` pair always returns the same `Call` instance for the lifetime of the client.

```kotlin
val call = StreamVideo.instance().call(type = "default", id = "my-call-id")
```

### Lifecycle methods

All of these are **`suspend`** and return `Result<T>` from `io.getstream.result.Result` — handle both `Result.Success` and `Result.Failure`. The exception is `leave()`, which is synchronous.

| Method | Shape | Purpose |
|---|---|---|
| `call.create()` | `suspend Result<GetOrCreateCallResponse>` | Create the call on the backend without joining |
| `call.join(create: Boolean = false, ring: Boolean = false)` | `suspend Result<RtcSession>` | Join the call. `create = true` creates it if missing; `ring = true` triggers ringing for invited members |
| `call.ring()` | `suspend Result<GetCallResponse>` | Start an outgoing ringing call (does **not** join) |
| `call.accept()` | `suspend Result<AcceptCallResponse>` | Accept an incoming ringing call |
| `call.reject()` | `suspend Result<RejectCallResponse>` | Reject an incoming ringing call |
| `call.end()` | `suspend Result<Unit>` | End the call for all participants (host/owner permission required) |
| `call.leave()` | synchronous | Leave the local session — internal cleanup happens asynchronously |

Call them from a coroutine scope you own (Activity / ViewModel / `LifecycleScope`) — never from a `@Composable` body. Wrap the suspend call in `LaunchedEffect(call)` or kick off via `rememberCoroutineScope().launch { ... }`.

```kotlin
val scope = rememberCoroutineScope()
Button(onClick = {
    scope.launch {
        when (val result = call.join(create = true)) {
            is Result.Success -> { /* joined */ }
            is Result.Failure -> { /* surface error */ }
        }
    }
}) { Text("Join") }
```

### Call types

| Type | Use case |
|---|---|
| `default` | Standard peer-to-peer and small-group video calls |
| `audio_room` | Audio-only group rooms |
| `livestream` | One-to-many broadcasting |

Use `default` for most calling scenarios. `audio_room` and `livestream` have different permission and layout models.

---

## Call State

`Call.state` exposes Kotlin `StateFlow`s for everything you render. Collect them with `collectAsStateWithLifecycle()` in Compose.

```kotlin
val participants by call.state.participants.collectAsStateWithLifecycle()
val me by call.state.localParticipant.collectAsStateWithLifecycle()
val others by call.state.remoteParticipants.collectAsStateWithLifecycle()
val dominant by call.state.dominantSpeaker.collectAsStateWithLifecycle()
val connection by call.state.connection.collectAsStateWithLifecycle()
val ringing by call.state.ringingState.collectAsStateWithLifecycle()
```

### `ringingState` tracks the current ringing phase

`RingingState` is a sealed interface from `io.getstream.video.android.core.RingingState`:

| State | When |
|---|---|
| `Idle` | No active or pending call |
| `Incoming(acceptedByMe)` | Remote user is calling this device |
| `Outgoing(acceptedByCallee)` | Outgoing ringing call, waiting for others to join |
| `Active` | Active call session |
| `RejectedByAll` | Every callee declined the outgoing call |
| `TimeoutNoAnswer` | No callee picked up before the ring timeout |

Use the `RingingCallContent` Composable (see [Compose Components](#compose-components)) to switch between incoming, outgoing, and active UI without authoring the `when` yourself.

### `connection` tracks the realtime socket

`RealtimeConnection` is a sealed interface — match on it to drive reconnect banners or loading spinners:

| State | When |
|---|---|
| `PreJoin` | Call object exists, no socket yet |
| `InProgress` | Joining is in flight |
| `Joined(session)` | Joined; media setup in progress |
| `Connected` | Media flowing |
| `Reconnecting` | Network drop, SDK is recovering |
| `Disconnected` | Cleanly left |
| `Failed(error)` | Terminal failure |

### `ParticipantState` key fields

Each participant is a `ParticipantState`. The renderable bits are also `StateFlow`s — read them with `collectAsStateWithLifecycle()`:

| Property | Type | Description |
|---|---|---|
| `sessionId` | `String` | Unique session id (use as `key` in lists) |
| `userId.value` | `String` | Stable user id |
| `name` | `StateFlow<String>` | Display name |
| `image` | `StateFlow<String>` | Avatar URL |
| `video` | `StateFlow<ParticipantState.Video?>` | Video track + enabled flag |
| `audio` | `StateFlow<ParticipantState.Audio?>` | Audio track + enabled flag |
| `speaking` | `StateFlow<Boolean>` | Currently speaking |
| `dominantSpeaker` | `StateFlow<Boolean>` | Loudest active speaker |
| `videoEnabled` | `StateFlow<Boolean>` | Camera on |
| `audioEnabled` | `StateFlow<Boolean>` | Microphone on |

Use `sessionId` as the stable key in `LazyColumn` / `LazyVerticalGrid` `items(...)` calls — `userId` can repeat if the same user joins twice.

### Client-level call routing

`StreamVideo.instance().state` also exposes `ringingCall: StateFlow<Call?>` and `activeCall: StateFlow<Call?>` for routing app-level UI (e.g. opening a full-screen incoming-call activity when a remote user calls):

```kotlin
val ringingCall by StreamVideo.instance().state.ringingCall.collectAsStateWithLifecycle()
val activeCall by StreamVideo.instance().state.activeCall.collectAsStateWithLifecycle()
```

---

## Compose Components

All Stream Video Composables must be hosted inside `VideoTheme { ... }` — calling them outside throws at runtime ("No colors provided!").

| Composable | Purpose |
|---|---|
| `VideoTheme(...)` | Theme + composition-locals wrapper. Wrap every Stream surface. |
| `CallContent(call)` | Drop-in active-call screen: app bar + participant layout + control bar |
| `RingingCallContent(call, onAcceptedContent = { ... })` | Auto-routes between `IncomingCallContent`, `OutgoingCallContent`, and the accepted/rejected/no-answer slots based on `ringingState` |
| `IncomingCallContent(call, isVideoType, ...)` | Incoming-ringing UI |
| `OutgoingCallContent(call, isVideoType, ...)` | Outgoing-ringing UI |
| `ParticipantsLayout(call, layoutType)` | Renders all participants in `DYNAMIC` / `SPOTLIGHT` / `GRID` layouts |
| `ParticipantVideo(call, participant, style)` | Renders a single participant's video track |
| `FloatingParticipantVideo(...)` | Picture-in-picture style local-participant tile |
| `ControlActions(call, onCallAction)` | Default mute / camera / leave / flip control bar |

### `CallContent` slots

`CallContent(call, ...)` exposes slot lambdas for the app bar, control bar, video grid, individual participant renderer, floating local-participant tile, and PiP content. The defaults already wire `ParticipantsLayout`, `ControlActions`, `CallAppBar`, and a permission handler — override only the slots you need.

> **Never guess slot names or default-content shapes.** Check the source (`stream-video-android-ui-compose/.../activecall/CallContent.kt`) before writing an override — slot lambdas evolve between versions.

### `CallAction` sealed interface

`onCallAction` receives a `CallAction` from `io.getstream.video.android.core.call.state.CallAction`. The default handler (`DefaultOnCallActionHandler`) already toggles camera/mic/speaker, flips the camera, and leaves the call. Override `onCallAction` only when you need extra behavior (analytics, custom navigation on `LeaveCall`, etc.):

| Action | Purpose |
|---|---|
| `ToggleMicrophone(isEnabled)` | Mute/unmute |
| `ToggleCamera(isEnabled)` | Camera on/off |
| `ToggleSpeakerphone(isEnabled)` | Speakerphone on/off |
| `FlipCamera` | Front/back camera flip |
| `LeaveCall` | Leave the local session |
| `AcceptCall` / `DeclineCall` / `CancelCall` | Ringing actions |
| `Reaction` / `ChooseLayout` / `ShowCallParticipantInfo` | UX helpers |

When you handle an action yourself, fall through to the default if you only want to add side effects:

```kotlin
onCallAction = { action ->
    when (action) {
        is LeaveCall -> { analytics.track("call_left"); call.leave(); finish() }
        else -> DefaultOnCallActionHandler.onCallAction(call, action)
    }
}
```

---

## Permissions

`CAMERA` and `RECORD_AUDIO` (and `BLUETOOTH_CONNECT` on Android 12+) are runtime permissions. The Compose SDK ships two helpers in `io.getstream.video.android.compose.permission`:

```kotlin
// One-shot: request permissions once when the Composable enters the composition
@Composable
fun JoinScreen(call: Call) {
    LaunchCallPermissions(call = call)
    // ... your join UI ...
}

// Stateful: control when to launch and react to results
@Composable
fun JoinScreen(call: Call) {
    val permissions = rememberCallPermissionsState(
        call = call,
        onAllPermissionsGranted = {
            call.join(create = true)
        },
    )

    Button(onClick = { permissions.launchPermissionRequest() }) {
        Text("Join")
    }
}
```

`CallContent` already invokes a `DefaultPermissionHandler` internally using the `permissions` parameter — pass a custom `VideoPermissionsState` only if you want a different request shape.

---

## Customization

### `VideoTheme`

`VideoTheme` is the entry point for colors, dimensions, typography, shapes, ripple, and reaction mapping. Build it once at the top of every Stream surface — `CallContent`, `RingingCallContent`, and friends require a hosting `VideoTheme`.

```kotlin
import io.getstream.video.android.compose.theme.VideoTheme
import io.getstream.video.android.compose.theme.base.StreamColors

@Composable
fun BrandVideoTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) {
        StreamColors.defaultColors()
    } else {
        StreamColors.defaultColors()  // override here when light/dark differ
    }
    VideoTheme(
        colors = colors,
        content = content,
    )
}
```

> **Never guess `StreamColors` token names from training data.** Inspect `stream-video-android-ui-compose/.../theme/base/StreamColors.kt` (or the [theming docs](https://getstream.io/video/docs/android/ui-cookbook/replacing-the-theme/)) before overriding individual fields. Tokens evolve across versions.

Read tokens at the call site via `VideoTheme.colors.<token>`, `VideoTheme.dimens.<token>`, etc.

### Custom participant rendering

`CallContent` accepts a `videoRenderer` lambda — replace the default `ParticipantVideo` to draw your own tile:

```kotlin
CallContent(
    call = call,
    videoRenderer = { videoModifier, videoCall, participant, videoStyle ->
        BrandedTile(
            modifier = videoModifier,
            call = videoCall,
            participant = participant,
        )
    },
)
```

Drop down to `ParticipantsLayout(call, layoutType, videoRenderer = ...)` when you want the SDK's grid/spotlight logic but a custom tile.

### Custom controls

Replace the bottom controls bar by passing your own `controlsContent`:

```kotlin
CallContent(
    call = call,
    controlsContent = { _ ->
        MyCustomControls(call = call)
    },
)
```

Inside the custom controls, drive call state with `call.camera`, `call.microphone`, `call.speaker`, and `call.leave()` — see [Call Controls](#call-controls).

---

## Call Controls

Toggle camera, microphone, and speaker during an active call. These read/write `StateFlow`s on the call's media managers:

```kotlin
val camOn by call.camera.isEnabled.collectAsStateWithLifecycle()
val micOn by call.microphone.isEnabled.collectAsStateWithLifecycle()
val speakerOn by call.speaker.isEnabled.collectAsStateWithLifecycle()

call.camera.setEnabled(!camOn)
call.microphone.setEnabled(!micOn)
call.speaker.setEnabled(!speakerOn)

// Front/back camera flip
call.camera.flip()

// Leave call (synchronous; cleanup runs internally)
call.leave()
```

`call.camera`, `call.microphone`, and `call.speaker` are stable for the lifetime of the `Call` — keep references in your ViewModel, not in `remember { ... }`.

---

## Troubleshooting

Source: [getstream.io/video/docs/android/advanced/troubleshooting/](https://getstream.io/video/docs/android/advanced/troubleshooting/)

### Connection issues

A failed WebSocket connection prevents calls from being established.

- **Expired token** — verify at [jwt.io](https://jwt.io). When using expiring tokens always supply a `tokenProvider` so the SDK can refresh automatically.
- **Wrong secret** — tokens must be signed with this app's secret. Tokens copied from docs use a demo secret and will be rejected.
- **User-token mismatch** — the token must be signed for the same user id passed to `StreamVideoBuilder(user = ...)`.
- **Missing `INTERNET` permission** — the app manifest must declare it explicitly even though the SDK manifest declares it too (manifest merger keeps both, but if your app removes the SDK's via `tools:node="remove"` the call silently fails).

### Ringing call issues

- **App in foreground:** ringing UI shows via the active socket. Fix connection issues first.
- **App in background or killed:** requires push notification + a foreground service. The SDK ships a default service config in `NotificationConfig` — don't strip it from the merged manifest.
- **Calling yourself** — caller and callee must be different users; a user cannot ring themselves.
- **Unknown member** — the callee must have connected to Stream at least once so the platform knows their device token.
- **Reused call ID** — ringing fires only once per call ID. Use a fresh `UUID().toString()` (or a server-issued id) for every ringing call.

### Logs

Pass `loggingLevel` to `StreamVideoBuilder` to surface socket and SFU events in Logcat:

```kotlin
loggingLevel = LoggingLevel(priority = if (BuildConfig.DEBUG) Priority.DEBUG else Priority.NONE)
```

Levels: `Priority.VERBOSE`, `DEBUG`, `INFO`, `WARN`, `ERROR`, `ASSERT`, `NONE`. Configure it before `build()` returns; setting it after has no effect on existing connections.

---

## Gotchas

- **`StreamVideoBuilder(...).build()` registers a singleton.** Calling it twice without `StreamVideo.removeClient()` leaks the previous instance. Build once in `Application.onCreate()`.
- **`StreamVideo.instance()` throws if the builder has not run yet.** Make sure your `Application` class is declared in the manifest (`<application android:name=".App" ... />`) before any Stream Composable renders. Use `StreamVideo.instanceOrNull()` for code paths that may run pre-init.
- **Never instantiate the client in a `@Composable` body or `remember { ... }`.** It survives recompositions; recreating it tears down the WebSocket and orphans the active call.
- **Every Stream Composable needs a hosting `VideoTheme { ... }`.** Calling `CallContent`, `RingingCallContent`, etc. outside a `VideoTheme` throws "No colors provided!" at runtime.
- **All call lifecycle methods (`create`, `join`, `accept`, `reject`, `end`, `ring`) are `suspend` and return `Result<T>`.** Call them from a coroutine scope you own; never from a `@Composable` body. Handle `Result.Failure` — silently swallowing it leaves the UI stuck mid-state.
- **`call.leave()` is synchronous; the rest are not.** `leave()` is the right way to exit the local session — kicking off `end()` on the host side ends the call for everyone.
- **Use `sessionId` as the list key for participants, not `userId`.** The same user may join twice (multi-device); `sessionId` is unique per session.
- **Do not request `CAMERA` / `RECORD_AUDIO` lazily inside the call screen.** Use `LaunchCallPermissions(call)` (or `rememberCallPermissionsState`) before `call.join(...)` runs — joining without granted permissions starts the call but with disabled tracks.
- **The API key is shared between Chat and Video.** One Stream project, one API key and one secret — token generation is identical for both products.
- **Chat + Video coexist cleanly on Android.** The two SDKs use different package names — `io.getstream.chat.android.models.User` vs `io.getstream.video.android.model.User`, separate theming, separate DI primitives — so they don't collide. Build both in the same `Application.onCreate()` with the same API key and token; no file-isolation pattern needed (unlike iOS).
- **Never use dev / unsigned tokens in production.** They disable token verification and let any client impersonate any user.
- **The SDK manifest already declares `CAMERA`, `RECORD_AUDIO`, `BLUETOOTH_CONNECT`, `MODIFY_AUDIO_SETTINGS`, `FOREGROUND_SERVICE`, etc.** Do not duplicate them in the app manifest unless you want to add extra `android:maxSdkVersion` or `tools:node` overrides.
