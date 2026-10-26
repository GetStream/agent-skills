# Video Compose - Screen Blueprints

Load only the section you are implementing. For setup, client initialization, permissions, and gotchas, see [VIDEO-COMPOSE.md](VIDEO-COMPOSE.md).

Per [`RULES.md`](../RULES.md) → *Blueprints are mandatory, on every turn*: any Stream Video screen, Composable, ringing handler, deep-link route, or UI customization must be preceded by reading the matching section below — including on follow-up turns inside an existing session.

---

## Request → Blueprint section

Use this table to resolve a user request to the section(s) you must read before writing code. If multiple rows match, read all of them. If none match, say so explicitly instead of improvising.

| User request signal | Section(s) to read |
|---|---|
| "set up Stream Video", "initialize StreamVideo", `Application` class, manifest wiring | [Application Class Blueprint](#application-class-blueprint) |
| "login screen", "sign in to call", connect user before joining a call | [Login / Connect User Blueprint](#login--connect-user-blueprint) |
| "navigate between screens", "skip login if already logged in", root host, app entry | [Root Navigation Blueprint](#root-navigation-blueprint) |
| "join a call", "call lobby", "enter call ID", join-or-create flow | [Home / Join-or-Start Call Blueprint](#home--join-or-start-call-blueprint) |
| "active call screen", `CallContent`, in-call UI, layout switcher | [Active Call Blueprint (CallContent)](#active-call-blueprint-callcontent) |
| "ringing", incoming call, outgoing call, accept/decline, `RingingCallContent` | [Ringing Call Blueprint](#ringing-call-blueprint) |
| ring when the app is closed or in the background, call push notifications, "phone doesn't ring", Firebase for calls | [Ringing with Push Blueprint](#ringing-with-push-blueprint) |
| "custom controls", mic/camera/leave bar, replace control buttons | [Custom Call Controls Blueprint](#custom-call-controls-blueprint) |
| "custom participant tile", custom video renderer, participant overlay | [Custom Participant Tile Blueprint](#custom-participant-tile-blueprint) |
| "participant grid", custom layout, local PiP | [Participant Grid Blueprint](#participant-grid-blueprint) |
| "theme", colors, dark mode, `VideoTheme` | [VIDEO-COMPOSE.md → Customization → VideoTheme](VIDEO-COMPOSE.md#videotheme) |
| "Chat + Video", combined app, in-call chat | [VIDEO-COMPOSE.md → Gotchas](VIDEO-COMPOSE.md#gotchas) (the "Chat + Video coexist" bullet) |
| "deep link", push notification → call, intent extras for `cid` / call id | [Call Deep-link Blueprint](#call-deep-link-blueprint) |
| "watch a livestream", "livestream viewer", `LivestreamPlayer`, RTMP/OBS stream, viewer count | [Livestream Viewer Blueprint](#livestream-viewer-blueprint) |
| "broadcast a livestream", "go live from the device", `livestream` call, backstage, `goLive` / `stopLive`, host/broadcaster screen | [Livestream Broadcaster Blueprint](#livestream-broadcaster-blueprint) |
| "voice agent", "AI voice assistant", audio-only call, audio visualization / speaking indicator, mic-only, fetch credentials from a backend at runtime | [Audio-Only Voice-Agent Blueprint](#audio-only-voice-agent-blueprint) |

If the request is something not covered, do not fabricate APIs — say the blueprint is not bundled and fall back per [`RULES.md`](../RULES.md).

---

## Application Class Blueprint

Build `StreamVideo` once in `Application.onCreate()`. The builder registers a process-wide singleton; retrieve it elsewhere via `StreamVideo.instance()`.

```kotlin
package com.example.streamvideo

import android.app.Application
import android.content.pm.ApplicationInfo
import io.getstream.log.Priority
import io.getstream.video.android.core.StreamVideoBuilder
import io.getstream.video.android.core.logging.LoggingLevel
import io.getstream.video.android.model.User

class App : Application() {
    override fun onCreate() {
        super.onCreate()

        val user = User(
            id = "your-user-id",
            name = "Your Name",
            image = "https://example.com/avatar.png",
        )

        StreamVideoBuilder(
            context = applicationContext,
            apiKey = "your_api_key",
            user = user,
            token = "your_static_token_here",
            loggingLevel = LoggingLevel(
                priority = if ((applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0) Priority.DEBUG else Priority.ERROR,
            ),
        ).build()
    }
}
```

Register it in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    android:label="@string/app_name">
    <!-- activities ... -->
</application>
```

**Wiring:**
- `Application.onCreate()` runs before any Activity, so `StreamVideo.instance()` is safe to call from any Composable lifecycle.
- `CAMERA`, `RECORD_AUDIO`, `BLUETOOTH_CONNECT`, `MODIFY_AUDIO_SETTINGS`, and `FOREGROUND_SERVICE` are merged in from the SDK manifest — do not redeclare them.
- For combined Chat + Video apps, build both clients here in the same `onCreate`.

---

## Login / Connect User Blueprint

Stream Video's "connect user" is `StreamVideoBuilder(... user = ..., token = ...).build()` — there is no separate `connectUser` call like Chat. To support a login screen, defer the `build()` until after the user picks an identity.

```kotlin
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import io.getstream.video.android.compose.theme.VideoTheme
import io.getstream.video.android.core.StreamVideo
import io.getstream.video.android.core.StreamVideoBuilder
import io.getstream.video.android.model.User

class LoginActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            VideoTheme {
                LoginScreen(
                    onConnected = {
                        startActivity(Intent(this, HomeActivity::class.java))
                        finish()
                    },
                )
            }
        }
    }
}

@Composable
fun LoginScreen(onConnected: () -> Unit) {
    val context = LocalContext.current.applicationContext
    var userId by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
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
            enabled = userId.isNotBlank(),
            onClick = {
                error = null
                runCatching {
                    // Demo wiring only. In production, fetch the token from your backend and pass
                    // a tokenProvider into StreamVideoBuilder instead of a static string.
                    // Ringing apps: StreamSession.connect(...), then SessionStore(context).save(...)
                    // from the Ringing with Push Blueprint instead.
                    StreamVideoBuilder(
                        context = context,
                        apiKey = BuildConfig.STREAM_API_KEY,
                        user = User(id = userId, name = name.ifBlank { userId }),
                        token = Config.USER_TOKEN,
                    ).build()
                    onConnected()
                }.onFailure { error = it.message }
            },
        ) { Text("Connect") }
    }
}
```

**Wiring:**
- For an expiring token, swap the `token` argument for both an initial token and a `tokenProvider` (see [VIDEO-COMPOSE.md - User Authentication](VIDEO-COMPOSE.md#user-authentication)).
- Skipping login on the next launch needs a saved session that `Application.onCreate` builds the client from: in a new process `StreamVideo.instanceOrNull()` is `null` until something calls `build()`. If the app rings with push, it needs this anyway - save the session and connect through `StreamSession.connect` from the [Ringing with Push Blueprint](#ringing-with-push-blueprint) instead of calling the builder here.
- To switch users, delete the push device (`getDevice().first()?.let { deleteDevice(it) }`), then call `StreamVideo.removeClient()` before the new `build()`. `logOut()` only clears the local token cache and leaves the device registered.

---

## Root Navigation Blueprint

Gate the app on whether the video client has been built. Skips login if a previous session is still alive.

```kotlin
import androidx.compose.runtime.rememberCoroutineScope
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@Composable
fun RootScreen() {
    var isConnected by remember { mutableStateOf(StreamVideo.instanceOrNull() != null) }
    val scope = rememberCoroutineScope()

    if (isConnected) {
        VideoTheme {
            HomeScreen(
                onLogout = {
                    scope.launch {
                        val streamVideo = StreamVideo.instance()
                        streamVideo.getDevice().first()?.let { streamVideo.deleteDevice(it) }
                        StreamVideo.removeClient()
                        isConnected = false
                    }
                },
            )
        }
    } else {
        VideoTheme {
            LoginScreen(onConnected = { isConnected = true })
        }
    }
}
```

**Wiring:**
- `StreamVideo.instanceOrNull()` returns `null` until `StreamVideoBuilder(...).build()` has run; check it instead of caching a bool yourself.
- For multi-Activity apps, route `LoginActivity` → `HomeActivity` → `CallActivity` instead of toggling Composables.

---

## Home / Join-or-Start Call Blueprint

Lets the user enter a call ID to join an existing call, or start a new one. Permissions are requested up front so `call.join(...)` does not silently start with disabled tracks.

```kotlin
import androidx.compose.runtime.*
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.getstream.result.Result
import io.getstream.video.android.compose.permission.LaunchCallPermissions
import io.getstream.video.android.compose.theme.VideoTheme
import io.getstream.video.android.core.Call
import io.getstream.video.android.core.StreamVideo
import kotlinx.coroutines.launch
import java.util.UUID

@Composable
fun HomeScreen(
    onJoined: (Call) -> Unit,
    onLogout: () -> Unit,
) {
    val streamVideo = StreamVideo.instance()
    val scope = rememberCoroutineScope()
    var callId by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var pendingCall by remember { mutableStateOf<Call?>(null) }

    pendingCall?.let { LaunchCallPermissions(call = it) }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text("Video Call", style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        OutlinedTextField(
            value = callId,
            onValueChange = { callId = it },
            label = { Text("Call ID") },
        )
        Spacer(Modifier.height(8.dp))
        Button(
            enabled = callId.isNotBlank(),
            onClick = {
                val call = streamVideo.call(type = "default", id = callId)
                pendingCall = call
                scope.launch {
                    when (val result = call.join(create = true)) {
                        is Result.Success -> onJoined(call)
                        is Result.Failure -> error = result.value.message
                    }
                }
            },
        ) { Text("Join Call") }
        Spacer(Modifier.height(8.dp))
        Button(
            onClick = {
                val call = streamVideo.call(type = "default", id = UUID.randomUUID().toString())
                pendingCall = call
                scope.launch {
                    when (val result = call.join(create = true)) {
                        is Result.Success -> onJoined(call)
                        is Result.Failure -> error = result.value.message
                    }
                }
            },
        ) { Text("New Call") }
        error?.let {
            Spacer(Modifier.height(16.dp))
            Text(it, color = MaterialTheme.colorScheme.error)
        }
        Spacer(Modifier.height(24.dp))
        TextButton(onClick = onLogout) { Text("Sign out") }
    }
}
```

**Wiring:**
- `streamVideo.call("default", id)` returns the same `Call` instance for the same `(type, id)` pair — safe to call repeatedly.
- `call.join(create = true)` joins an existing call or creates one if it does not exist (no ringing).
- `LaunchCallPermissions(call)` requests `CAMERA` / `RECORD_AUDIO` (and `BLUETOOTH_CONNECT` on Android 12+) — wire it as soon as you have a `Call` so permissions are granted before `join` resolves.
- `runCatching` is not enough here — `call.join` returns `Result.Failure` on protocol errors; surface its `.value.message` instead of waiting for an exception.

---

## Active Call Blueprint (CallContent)

`CallContent` is the complete in-call screen with participant grid, app bar, and controls. Use it unless you are building a fully custom layout. Pass the same `Call` instance you obtained for `join(...)` — never construct a second one.

```kotlin
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import io.getstream.video.android.compose.theme.VideoTheme
import io.getstream.video.android.compose.ui.components.call.activecall.CallContent
import io.getstream.video.android.compose.ui.components.call.renderer.LayoutType
import io.getstream.video.android.core.StreamVideo

class CallActivity : ComponentActivity() {

    private val callId: String
        get() = intent.getStringExtra(KEY_CALL_ID) ?: error("Missing call id")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val call = StreamVideo.instance().call(type = "default", id = callId)

        setContent {
            VideoTheme {
                CallContent(
                    call = call,
                    layout = LayoutType.DYNAMIC,
                    onBackPressed = { finish() },
                )
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        // Use leave() — end() terminates the call for everyone.
        StreamVideo.instanceOrNull()?.call("default", callId)?.leave()
    }

    companion object {
        private const val KEY_CALL_ID = "callId"
        fun createIntent(context: Context, callId: String) =
            Intent(context, CallActivity::class.java).putExtra(KEY_CALL_ID, callId)
    }
}
```

**Wiring:**
- `LayoutType` lives in `io.getstream.video.android.compose.ui.components.call.renderer` — values: `DYNAMIC`, `SPOTLIGHT`, `GRID`.
- `CallContent` already wires `appBarContent`, `controlsContent`, a default `videoRenderer`, and a permission handler from `permissions = rememberCallPermissionsState(call)`. Override slots only when you need to.
- Do **not** wrap `CallContent` in a `Scaffold` — it ships its own Scaffold internally. Use the `appBarContent` / `controlsContent` slots instead.
- `onCallAction` defaults to `DefaultOnCallActionHandler.onCallAction(call, action)` which already handles mic/camera/speaker toggles and `LeaveCall`. Override only to add side effects (analytics, custom navigation on leave).

---

## Ringing Call Blueprint

`RingingCallContent` reads `call.state.ringingState` and routes between `IncomingCallContent`, `OutgoingCallContent`, and your accepted / rejected / no-answer slots. Pair it with the client-level `ringingCall` flow to surface incoming calls from anywhere in the app.

### Surfacing an incoming call from the app shell

```kotlin
@Composable
fun AppShell(content: @Composable () -> Unit) {
    val streamVideo = StreamVideo.instance()
    val ringingCall by streamVideo.state.ringingCall.collectAsStateWithLifecycle()

    VideoTheme {
        Box(Modifier.fillMaxSize()) {
            content()

            ringingCall?.let { call ->
                RingingCallContent(
                    call = call,
                    isVideoType = true,
                    onAcceptedContent = {
                        // Route into the active-call screen
                        ActiveCallScreen(call = call)
                    },
                    onRejectedContent = { /* dismiss */ },
                    onNoAnswerContent = { /* show "no answer" */ },
                    onBackPressed = { call.leave() },
                )
            }
        }
    }
}
```

### Starting an outgoing ringing call

```kotlin
@Composable
fun RingPeerButton(peerId: String) {
    val streamVideo = StreamVideo.instance()
    val scope = rememberCoroutineScope()

    Button(onClick = {
        val call = streamVideo.call(type = "default", id = UUID.randomUUID().toString())
        scope.launch {
            // create + ring in one shot
            call.create(
                memberIds = listOf(streamVideo.userId, peerId),
                ring = true,
            )
        }
    }) { Text("Call $peerId") }
}
```

`Call.create(...)` accepts both `memberIds` and `ring` named args (plus optional `members`, `custom`, `settings`, `team`, `notify`, `video`); the same effect can be achieved with `call.create(memberIds = ...)` followed by `call.ring()` if you need to defer ringing.

### Accepting / rejecting an incoming call manually

```kotlin
val scope = rememberCoroutineScope()

Button(onClick = { scope.launch { call.accept(); call.join() } }) { Text("Accept") }
Button(onClick = { scope.launch { call.reject(); call.leave() } }) { Text("Reject") }
```

**Wiring:**
- `call.accept()` records acceptance with the backend; you still need to call `join()` to actually enter the media session.
- `call.reject()` rejects the call for the current user; pair with `leave()` to drop any local references.
- `RingingCallContent` exposes `onIncomingContent` and `onOutgoingContent` slots if you want to fully replace the default ringing UIs — match the lambda signatures defined in the SDK source.
- `onAcceptedContent` is **required** (no default).
- This section rings only while the app is open and connected. For calls that ring with the app in the background or killed, also follow the [Ringing with Push Blueprint](#ringing-with-push-blueprint).

---

## Ringing with Push Blueprint

Calls that ring when the app is in the background or killed. Four pieces must all be in place, and a missing one fails silently - the phone just doesn't ring:

1. a Firebase push provider in the Stream dashboard
2. the Firebase push artifact and a `FirebasePushDeviceGenerator` on the builder
3. a saved session, so `Application.onCreate` can build the client before the push is handled
4. an incoming-call screen that can open over the lock screen

**1. Dashboard push provider.** It needs the Firebase service-account JSON (Firebase console -> Project settings -> Service accounts). Create a Firebase provider named `firebase` in the dashboard (Push Notifications -> New Configuration), or with `getstream api UpsertPushProvider` (`--schema` prints the body). The JSON and the app's `google-services.json` come from the user - never invent them.

**2. Gradle.** Add the Firebase push artifact and the Google services plugin:

```kotlin
// app/build.gradle.kts
plugins {
    id("com.google.gms.google-services")
}

dependencies {
    implementation("io.getstream:stream-video-android-ui-compose:<video-version>")
    implementation("io.getstream:stream-android-push-firebase:<push-version>")
}
```

- `<push-version>`: the `stream-android-push` version the Video SDK already pulls in (`./gradlew :app:dependencies --configuration debugRuntimeClasspath | grep stream-android-push`), so the push modules stay on one version. Versions newer than Maven Central's are only on Stream's Maven repository (`maven("https://stream-io-repo.com")` under `dependencyResolutionManagement.repositories`).
- Google services plugin: declare it in the root `plugins` block with `apply false`; the current version is the `<release>` in `https://dl.google.com/dl/android/maven2/com/google/gms/google-services/maven-metadata.xml`.
- `google-services.json` goes in the app module. The build fails without it: until the user adds theirs, leave the plugin unapplied and tell them the app won't ring until it's there.

**3. Session and client.** Save the user and last token at login, and build the client from them in `Application.onCreate` - no network call there. A push that arrives before `build()` is dropped ("StreamVideo is not initialised"). The token is a credential: keep it in app-private storage, as below.

```kotlin
package com.example.streamvideo

import android.app.Application
import android.content.Context
import io.getstream.android.push.firebase.FirebasePushDeviceGenerator
import io.getstream.video.android.core.StreamVideo
import io.getstream.video.android.core.StreamVideoBuilder
import io.getstream.video.android.core.notifications.NotificationConfig
import io.getstream.video.android.core.socket.common.token.TokenProvider
import io.getstream.video.android.model.User

// BuildConfig.STREAM_API_KEY comes from `getstream env` (see credentials.md).

data class Session(val userId: String, val name: String, val token: String)

class SessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("stream_session", Context.MODE_PRIVATE)

    fun load(): Session? {
        val userId = prefs.getString("user_id", null) ?: return null
        val token = prefs.getString("token", null) ?: return null
        return Session(userId, prefs.getString("name", userId) ?: userId, token)
    }

    fun save(session: Session) {
        prefs.edit()
            .putString("user_id", session.userId)
            .putString("name", session.name)
            .putString("token", session.token)
            .apply()
    }

    fun saveToken(token: String) = prefs.edit().putString("token", token).apply()

    fun clear() = prefs.edit().clear().apply()
}

object StreamSession {
    // Must match the provider name in the Stream dashboard.
    private const val PUSH_PROVIDER_NAME = "firebase"

    fun connect(context: Context, session: Session) {
        // Already built for this process. Logout (below) removes the client
        // before a different user connects.
        if (StreamVideo.isInstalled) return
        val store = SessionStore(context)
        StreamVideoBuilder(
            context = context.applicationContext,
            apiKey = BuildConfig.STREAM_API_KEY,
            user = User(id = session.userId, name = session.name),
            token = session.token,
            // With expiring tokens from your backend: called when the token
            // expires. Omit it for a never-expiring `getstream token`.
            tokenProvider = object : TokenProvider {
                override suspend fun loadToken(): String =
                    yourAuthService.fetchVideoToken(session.userId).also(store::saveToken)
            },
            notificationConfig = NotificationConfig(
                pushDeviceGenerators = listOf(
                    FirebasePushDeviceGenerator(
                        providerName = PUSH_PROVIDER_NAME,
                        context = context.applicationContext,
                    ),
                ),
            ),
        ).build()
    }
}

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        val store = SessionStore(this)
        val session = store.load() ?: return
        // build() throws on a blank key or token; don't crash every launch on a bad session.
        runCatching { StreamSession.connect(this, session) }.onFailure { store.clear() }
    }
}
```

At login, connect first and save the session only once `build()` returned: `StreamSession.connect(context, session)` then `SessionStore(context).save(session)` (see [Login / Connect User Blueprint](#login--connect-user-blueprint)).

`build()` connects in the background and only logs a failure, so watch the connection and send the user back to login when it fails (for example an invalid or revoked token):

```kotlin
import io.getstream.video.android.core.ConnectionState

// inside a coroutine scoped to the signed-in UI
StreamVideo.instance().state.connection.collect { state ->
    if (state is ConnectionState.Failed) {
        logout(context) // below
        showLogin(state.error.message)
    }
}
```

At logout, delete the device, remove the client, and clear the session. Don't tear down on a failed delete: the device would stay registered to this user and keep ringing for them.

```kotlin
import io.getstream.result.Result
import kotlinx.coroutines.flow.first

suspend fun logout(context: Context): Boolean {
    val streamVideo = StreamVideo.instanceOrNull() ?: return true
    val device = streamVideo.getDevice().first()
    if (device != null && streamVideo.deleteDevice(device) is Result.Failure) return false
    StreamVideo.removeClient()
    SessionStore(context).clear()
    return true
}
```

**4. Incoming-call screen.** The Compose SDK registers `ComposeStreamCallActivity` for the incoming, accept, and outgoing call actions, with `showWhenLocked` and `turnScreenOn`, so a push opens it with no manifest changes. It handles accept, reject, permissions, and leaving. Use it as the only incoming UI: don't also render `RingingCallContent` from `state.ringingCall` in an app shell, or the app shows two incoming screens while it's open. Start outgoing calls through it too:

```kotlin
import android.content.Context
import io.getstream.video.android.compose.ui.ComposeStreamCallActivity
import io.getstream.video.android.core.notifications.NotificationHandler
import io.getstream.video.android.model.StreamCallId
import io.getstream.video.android.ui.common.StreamCallActivity
import java.util.UUID

fun startOutgoingCall(context: Context, calleeIds: List<String>) {
    context.startActivity(
        StreamCallActivity.callIntent(
            context = context,
            // A new ID per ringing call: a call ID rings only once.
            cid = StreamCallId(type = "default", id = UUID.randomUUID().toString()),
            members = calleeIds,
            leaveWhenLastInCall = true,
            action = NotificationHandler.ACTION_OUTGOING_CALL,
            clazz = ComposeStreamCallActivity::class.java,
        ),
    )
}
```

**Wiring:**
- The SDK asks for `POST_NOTIFICATIONS` on launch (`NotificationConfig.requestPermissionOnAppLaunch`); without it no ringing notification shows on Android 13+.
- Don't remove `USE_FULL_SCREEN_INTENT`, `FOREGROUND_SERVICE_PHONE_CALL`, or `POST_NOTIFICATIONS` from the merged manifest with `tools:node="remove"`.
- A custom `FirebaseMessagingService` must forward to `FirebaseMessagingDelegate.handleRemoteMessage` and register new tokens with `FirebaseMessagingDelegate.registerFirebaseToken` - see `getstream docs video/android`, `advanced/incoming-calls/push-providers/firebase.md`.
- To replace the SDK call screen, subclass `ComposeStreamCallActivity` and give the subclass the same intent actions, `showWhenLocked`, and `turnScreenOn` - see `advanced/incoming-calls/push-notifications.md`.
- Test on two physical devices. Both users log in once first, which registers their devices; a user who never logged in has nothing to ring. Then swipe the app away on one and ring it from the other.

---

## Custom Call Controls Blueprint

Replace the SDK's default controls bar with your own. Drive call state through `call.camera`, `call.microphone`, `call.speaker`, and `call.leave()`.

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.getstream.video.android.core.Call
import kotlinx.coroutines.launch

@Composable
fun CustomCallControls(call: Call) {
    val isCameraOn by call.camera.isEnabled.collectAsStateWithLifecycle()
    val isMicOn by call.microphone.isEnabled.collectAsStateWithLifecycle()

    Row(
        Modifier.fillMaxWidth().padding(16.dp),
        horizontalArrangement = Arrangement.SpaceEvenly,
    ) {
        IconButton(onClick = { call.microphone.setEnabled(!isMicOn) }) {
            Icon(
                imageVector = if (isMicOn) Icons.Default.Mic else Icons.Default.MicOff,
                contentDescription = "Mic",
            )
        }
        IconButton(onClick = { call.camera.setEnabled(!isCameraOn) }) {
            Icon(
                imageVector = if (isCameraOn) Icons.Default.Videocam else Icons.Default.VideocamOff,
                contentDescription = "Camera",
            )
        }
        IconButton(onClick = { call.camera.flip() }) {
            Icon(Icons.Default.Cameraswitch, contentDescription = "Flip camera")
        }
        IconButton(onClick = { call.leave() }) {
            Icon(Icons.Default.CallEnd, contentDescription = "Leave", tint = MaterialTheme.colorScheme.error)
        }
    }
}
```

Wire the custom bar via `CallContent(controlsContent = { CustomCallControls(it) })`.

**Wiring:**
- `call.camera.setEnabled(...)` / `call.microphone.setEnabled(...)` accept a `Boolean`. The internal `StateFlow<Boolean>` flips automatically — collect it for UI.
- `call.camera.flip()` is synchronous — call it directly from the click handler. (The internal `flipInternal()` it delegates to is suspend, but the public API is not.)
- `call.leave()` is synchronous; the rest of teardown happens internally.

---

## Custom Participant Tile Blueprint

Render a single participant's video track with a name overlay and a speaking border.

```kotlin
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.getstream.video.android.compose.ui.components.call.renderer.ParticipantVideo
import io.getstream.video.android.compose.ui.components.call.renderer.RegularVideoRendererStyle
import io.getstream.video.android.core.Call
import io.getstream.video.android.core.ParticipantState

@Composable
fun ParticipantTile(
    call: Call,
    participant: ParticipantState,
    modifier: Modifier = Modifier,
) {
    val name by participant.name.collectAsStateWithLifecycle()
    val isSpeaking by participant.speaking.collectAsStateWithLifecycle()

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .border(
                width = if (isSpeaking) 2.dp else 0.dp,
                color = if (isSpeaking) Color.Green else Color.Transparent,
                shape = RoundedCornerShape(12.dp),
            ),
    ) {
        ParticipantVideo(
            call = call,
            participant = participant,
            style = RegularVideoRendererStyle(),
            modifier = Modifier.fillMaxSize(),
        )

        Text(
            text = name,
            color = Color.White,
            style = MaterialTheme.typography.labelSmall,
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(8.dp)
                .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(4.dp))
                .padding(horizontal = 6.dp, vertical = 2.dp),
        )
    }
}
```

**Wiring:**
- `ParticipantVideo` handles track attach/detach, mirroring for the local participant, and avatar fallback when the camera is off.
- `RegularVideoRendererStyle()` is the default style; subclasses (`ScreenSharingVideoRendererStyle`, etc.) live alongside it — verify against `stream-video-android-ui-compose/.../renderer/VideoRendererStyle.kt` before instantiating.
- Plug the tile into `CallContent` via the `videoRenderer` slot, or call it directly from a custom `ParticipantsLayout`.

---

## Participant Grid Blueprint

Custom layout: remote participants in a 2-column grid, local participant pinned as a floating tile.

```kotlin
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.getstream.video.android.core.Call

@Composable
fun ParticipantGrid(call: Call) {
    val remote by call.state.remoteParticipants.collectAsStateWithLifecycle()
    val me by call.state.localParticipant.collectAsStateWithLifecycle()

    Box(Modifier.fillMaxSize()) {
        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(remote, key = { it.sessionId }) { participant ->
                ParticipantTile(
                    call = call,
                    participant = participant,
                    modifier = Modifier.aspectRatio(1f),
                )
            }
        }

        me?.let { local ->
            ParticipantTile(
                call = call,
                participant = local,
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(16.dp)
                    .size(width = 120.dp, height = 160.dp),
            )
        }
    }
}
```

**Wiring:**
- `remoteParticipants` excludes the local user — avoids showing your own video twice.
- Use `sessionId` as the `LazyVerticalGrid` `key` — `userId` can repeat across multi-device joins.
- For a layout that reacts to pinning and dominant speaker, prefer `ParticipantsLayout(call, layoutType = LayoutType.DYNAMIC)` from the SDK over rolling your own.

---

## Call Deep-link Blueprint

Push notifications and external deep links typically deliver `(callType, callId)`. Launch the call destination directly from the intent — skip the home screen.

```kotlin
class CallDeepLinkActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val callType = intent.getStringExtra(EXTRA_CALL_TYPE) ?: "default"
        val callId = intent.getStringExtra(EXTRA_CALL_ID) ?: run { finish(); return }

        val call = StreamVideo.instance().call(type = callType, id = callId)

        setContent {
            VideoTheme {
                LaunchCallPermissions(call = call)
                LaunchedEffect(call) { call.join(create = true) }

                CallContent(
                    call = call,
                    onBackPressed = { finish() },
                )
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        StreamVideo.instanceOrNull()
            ?.call(intent.getStringExtra(EXTRA_CALL_TYPE) ?: "default",
                   intent.getStringExtra(EXTRA_CALL_ID) ?: "")
            ?.leave()
    }

    companion object {
        const val EXTRA_CALL_TYPE = "callType"
        const val EXTRA_CALL_ID = "callId"

        fun createIntent(context: Context, callType: String, callId: String) =
            Intent(context, CallDeepLinkActivity::class.java)
                .putExtra(EXTRA_CALL_TYPE, callType)
                .putExtra(EXTRA_CALL_ID, callId)
    }
}
```

**Wiring:**
- `LaunchCallPermissions(call)` runs once when the Composable enters the composition; the permission dialog appears before `call.join` resolves.
- `LaunchedEffect(call)` ties the join coroutine to the Composable's lifecycle — leaving the screen cancels in-flight join.
- For incoming-call deep links delivered via push, prefer the SDK's `RingingCallContent` flow instead of jumping straight into `CallContent` — that keeps accept/reject UX consistent.

---

## Livestream Viewer Blueprint

Watch a livestream (e.g. one published via RTMP/OBS or from another device) with the drop-in `LivestreamPlayer`. The call type is `livestream`. A viewer can be anonymous.

```kotlin
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import io.getstream.video.android.compose.permission.LaunchCallPermissions
import io.getstream.video.android.compose.theme.VideoTheme
import io.getstream.video.android.compose.ui.components.livestream.LivestreamPlayer
import io.getstream.video.android.core.Call
import io.getstream.video.android.core.StreamVideoBuilder
import io.getstream.video.android.model.User

class ViewerActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val client = StreamVideoBuilder(
            context = applicationContext,
            user = User.anonymous(),          // a viewer needs no named identity
            apiKey = "your_api_key",
            token = "your_viewer_token",
        ).build()

        val call = client.call("livestream", "your_call_id")
        setContent {
            VideoTheme {
                LaunchCallPermissions(call = call, onAllPermissionsGranted = { call.join() })
                LivestreamPlayer(call = call)
            }
        }
    }
}
```

**Wiring:**
- `LivestreamPlayer(call)` renders the host video plus a default overlay (live badge, viewer count, duration, pause/play). Customize with `overlayContent = { ... }` and/or `rendererContent = { ... }`; drop to `VideoRenderer` for a fully custom player.
- Viewer state lives on `call.state`: `totalParticipants` (viewer count), `duration`, `backstage` (true until the host goes live — viewers can't join a backstage call), `livestream` (the host video track as `StateFlow<ParticipantState.Media?>`).
- Publishing the source (RTMP push from OBS, or a broadcaster device) is a separate concern — see the broadcaster blueprint below.

---

## Livestream Broadcaster Blueprint

Broadcast a livestream **from the device camera** over WebRTC, using backstage → go-live. The broadcaster's user needs a broadcast-capable role (`host` or `admin`). There is **no** drop-in broadcaster component — build the host screen from `call.state`.

Create the user with a broadcast role and get the `livestream` call (build the client once in `Application` per the [Application Class Blueprint](#application-class-blueprint)):

```kotlin
val user = User(id = "broadcaster_id", name = "Broadcaster", role = "host")
// ...StreamVideoBuilder(... user = user ...).build()
val call = StreamVideo.instance().call("livestream", "your_call_id")
```

Gate on camera + mic, then join in backstage and render the host screen:

```kotlin
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import io.getstream.video.android.compose.permission.LaunchPermissionRequest
import io.getstream.video.android.compose.theme.VideoTheme
import io.getstream.video.android.core.Call

@Composable
fun LiveHost(call: Call) {
    LaunchPermissionRequest(
        permissions = listOf(
            android.Manifest.permission.RECORD_AUDIO,
            android.Manifest.permission.CAMERA,
        ),
    ) {
        AllPermissionsGranted {
            LaunchedEffect(call) { call.join(create = true) }  // joins in backstage; goLive() opens it to viewers
            LiveHostContent(call = call)
        }
        NoneGranted { /* explain why camera + mic are required */ }
    }
}
```

`LiveHostContent` — camera preview via `VideoRenderer`, a backstage/live status header, and a start/stop button driven by `call.state.backstage`:

```kotlin
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import io.getstream.video.android.compose.ui.components.video.VideoRenderer
import io.getstream.video.android.core.Call
import io.getstream.video.android.core.RealtimeConnection
import kotlinx.coroutines.launch

@Composable
fun LiveHostContent(call: Call) {
    val connection by call.state.connection.collectAsState()
    val backstage by call.state.backstage.collectAsState()
    val totalParticipants by call.state.totalParticipants.collectAsState()
    val duration by call.state.duration.collectAsState()
    val localParticipant by call.state.localParticipant.collectAsState()
    val video by (localParticipant?.video ?: return).collectAsState()
    val scope = rememberCoroutineScope()

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        topBar = {
            when {
                connection == RealtimeConnection.Connected && !backstage ->
                    Text("Live - $totalParticipants watching - $duration")
                connection == RealtimeConnection.Connected ->
                    Text("The livestream is not started yet")
                connection is RealtimeConnection.Failed ->
                    Text("Connection failed")
            }
        },
        bottomBar = {
            Button(onClick = { scope.launch { if (backstage) call.goLive() else call.stopLive() } }) {
                Text(if (backstage) "Start Broadcast" else "Stop Broadcast")
            }
        },
    ) { padding ->
        VideoRenderer(
            modifier = Modifier.fillMaxSize().padding(padding),
            call = call,
            video = video,               // ParticipantState.Media? — the current overload; do NOT pass videoFallbackContent = {} (deprecated)
        )
    }
}
```

**Wiring:**
- **`call.goLive()` / `call.stopLive()`** flip `call.state.backstage`. Backstage is on by default for the `livestream` call type (configurable in the dashboard) — only after `goLive()` can regular viewers join. `goLive()` returns a `Result`; call it from a coroutine (`rememberCoroutineScope().launch { }`).
- **Role matters:** a plain `user` role can join but not broadcast/go-live. Build the broadcaster `User` with `role = "host"` (or `"admin"`).
- **`VideoRenderer` API (v1.29.x):** the current overload takes `video: ParticipantState.Media?` and a `videoRendererConfig`; the older `videoFallbackContent = { }` lambda overload is **deprecated** — prefer configuring the fallback via `rememberVideoRendererConfig(...)` rather than the deprecated slot.
- **Manifest:** `CAMERA` and `RECORD_AUDIO` are declared by the SDK library manifest and merge in automatically; you only add them if you want them as explicitly-required features. `INTERNET` likewise merges from the SDK.
- **Leaving:** call `call.leave()` when the host exits (stops the foreground service). `call.stopLive()` only ends the broadcast for viewers — it does **not** disconnect the host. Never call `end()` unless you intend to end the call for everyone.
- **Emulator caveat:** the emulator has no real camera (renders the virtual scene) and may hit ICE STUN/TURN errors reaching the SFU — verify broadcast on a physical device.

---

## Audio-Only Voice-Agent Blueprint

Build a mic-only voice experience (e.g. an AI voice assistant, or joining an audio room programmatically) where **there is no camera and no bundled call screen** — you visualize audio from `call.state`. Two things make this different from a normal video call:

1. **Runtime credentials.** The `apiKey` / `token` / `userId` often arrive from a backend at runtime (not baked in, not typed on a login screen), so `StreamVideoBuilder(...).build()` must be **deferred until the async fetch resolves** — do it in an owned scope (a ViewModel), not in `Application.onCreate()`.
2. **Mic-only permissions.** Request `RECORD_AUDIO` only; do not use `LaunchCallPermissions` (it also asks for `CAMERA`).

### Build the client after a runtime fetch (ViewModel-owned)

```kotlin
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import io.getstream.video.android.core.StreamVideo
import io.getstream.video.android.core.StreamVideoBuilder
import io.getstream.video.android.model.User
import kotlinx.coroutines.launch

class VoiceAgentViewModel : ViewModel() {

    fun connect(creds: Credentials) {                 // creds came from GET /credentials
        viewModelScope.launch {
            // Build once. StreamVideoBuilder registers a process singleton, so guard against
            // a rebuild on config-change/retry — reuse the existing client if present.
            val client = StreamVideo.instanceOrNull() ?: StreamVideoBuilder(
                context = appContext,
                apiKey = creds.apiKey,
                user = User(id = creds.userId, name = creds.userId),
                token = creds.token,
            ).build()

            val call = client.call(creds.callType, creds.callId)
            call.join(create = true)                   // create=true: call exists before the agent attaches
            call.camera.setEnabled(false)              // audio-only: no camera track
            call.microphone.setEnabled(true)
            call.speaker.setEnabled(true)
            // ...expose `call` as state for the UI, then POST /{callType}/{callId}/connect to your backend...
        }
    }

    override fun onCleared() {
        StreamVideo.instanceOrNull()?.let { viewModelScope.launch { it.call(/*type*/, /*id*/).leave() } }
    }
}
```

### Request mic-only permission (no camera prompt)

```kotlin
import io.getstream.video.android.compose.permission.LaunchPermissionRequest

@Composable
fun VoiceAgentGate(onGranted: () -> Unit) {
    LaunchPermissionRequest(permissions = listOf(android.Manifest.permission.RECORD_AUDIO)) {
        AllPermissionsGranted { onGranted() }
        NoneGranted { /* explain why the mic is required */ }
    }
}
// Or the platform API: rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { ... }
```

### Visualize who's talking (the audio flows)

```kotlin
@Composable
fun AudioVisualizer(call: Call) {
    val activeSpeakers by call.state.activeSpeakers.collectAsStateWithLifecycle()
    val speaker = activeSpeakers.firstOrNull()
    val level by (speaker?.audioLevel ?: MutableStateFlow(0f)).collectAsStateWithLifecycle()
    val name by (speaker?.userNameOrId ?: MutableStateFlow("")).collectAsStateWithLifecycle()

    // Scale/pulse a circle by `level` (0f..1f); label it with `name`.
    Box(
        modifier = Modifier
            .size((80 + level * 120).dp)
            .clip(CircleShape)
            .background(VideoTheme.colors.brandPrimary),
        contentAlignment = Alignment.Center,
    ) { Text(if (name.isBlank()) "Listening..." else "$name speaking") }
}
```

**Wiring:**
- **`call.state.activeSpeakers`** (`StateFlow<List<ParticipantState>>`, loudest first) is the primary input; for an agent UI the agent is usually the first active speaker. Per participant, **`audioLevel`** (`StateFlow<Float>` 0f..1f) drives a single pulsing shape and **`audioLevels`** (`StateFlow<List<Float>>`, a 5-sample window) drives a smooth waveform/equalizer. **`userNameOrId`** gives a label without a null dance.
- **Never** collect a nullable flow with `by` directly — fall back to a `MutableStateFlow(default)` (as above) or guard with `?.let`, so recomposition stays stable when there's no active speaker.
- Build the client in the **ViewModel**, not `Application`, precisely because credentials are async here — this is the one sanctioned exception to the "build in Application" rule. Still build **once** (`instanceOrNull()` guard) and `leave()` on `onCleared()`.
- The backend contract (`GET /credentials`, `POST /{callType}/{callId}/connect`) and any HTTP client (Retrofit, Ktor) are ordinary app code — not part of this skill. For a localhost dev backend on the emulator, use `http://10.0.2.2:3000/` and add a `network_security_config.xml` permitting cleartext to that host.
