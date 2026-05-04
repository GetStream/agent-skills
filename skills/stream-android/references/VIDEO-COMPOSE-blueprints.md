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
| "custom controls", mic/camera/leave bar, replace control buttons | [Custom Call Controls Blueprint](#custom-call-controls-blueprint) |
| "custom participant tile", custom video renderer, participant overlay | [Custom Participant Tile Blueprint](#custom-participant-tile-blueprint) |
| "participant grid", custom layout, local PiP | [Participant Grid Blueprint](#participant-grid-blueprint) |
| "theme", colors, dark mode, `VideoTheme` | [VIDEO-COMPOSE.md → Customization → VideoTheme](VIDEO-COMPOSE.md#videotheme) |
| "Chat + Video", combined app, in-call chat | [VIDEO-COMPOSE.md → Gotchas](VIDEO-COMPOSE.md#gotchas) (the "Chat + Video coexist" bullet) |
| "deep link", push notification → call, intent extras for `cid` / call id | [Call Deep-link Blueprint](#call-deep-link-blueprint) |

If the request is something not covered, do not fabricate APIs — say the blueprint is not bundled and fall back per [`RULES.md`](../RULES.md).

---

## Application Class Blueprint

Build `StreamVideo` once in `Application.onCreate()`. The builder registers a process-wide singleton; retrieve it elsewhere via `StreamVideo.instance()`.

```kotlin
package com.example.streamvideo

import android.app.Application
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
                priority = if (BuildConfig.DEBUG) Priority.DEBUG else Priority.NONE,
            ),
        ).build()
    }
}
```

Register it in `AndroidManifest.xml`:

```xml
<application
    android:name=".App"
    android:label="@string/app_name"
    android:theme="@style/Theme.StreamVideo">
    <!-- activities ... -->
</application>

<uses-permission android:name="android.permission.INTERNET" />
```

**Wiring:**
- `Application.onCreate()` runs before any Activity, so `StreamVideo.instance()` is safe to call from any Composable lifecycle.
- `CAMERA`, `RECORD_AUDIO`, `BLUETOOTH_CONNECT`, `MODIFY_AUDIO_SETTINGS`, and `FOREGROUND_SERVICE` are merged in from the SDK manifest — do not redeclare them.
- For combined Chat + Video apps, build both clients here in the same `onCreate` (see [Combined Chat + Video Blueprint](#combined-chat--video-blueprint)).

---

## Login / Connect User Blueprint

Stream Video's "connect user" is `StreamVideoBuilder(... user = ..., token = ...).build()` — there is no separate `connectUser` call like Chat. To support a login screen, defer the `build()` until after the user picks an identity.

```kotlin
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
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
                    StreamVideoBuilder(
                        context = applicationContext,
                        apiKey = "your_api_key",
                        user = User(id = userId, name = name.ifBlank { userId }),
                        token = "your_static_token_here",
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
- Auto-reconnect across app launches: check `StreamVideo.instanceOrNull() != null` before showing the login screen.
- To switch users, call `StreamVideo.instance().logOut()` then `StreamVideo.removeClient()` before the new `build()`.

---

## Root Navigation Blueprint

Gate the app on whether the video client has been built. Skips login if a previous session is still alive.

```kotlin
@Composable
fun RootScreen() {
    var isConnected by remember { mutableStateOf(StreamVideo.instanceOrNull() != null) }

    if (isConnected) {
        VideoTheme {
            HomeScreen(
                onLogout = {
                    StreamVideo.instance().logOut()
                    StreamVideo.removeClient()
                    isConnected = false
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
