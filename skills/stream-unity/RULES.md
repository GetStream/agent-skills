# Stream Unity - non-negotiable rules + Unity pitfalls

Every rule below is stated once. Read it before writing code. The docs cover *how* to call each API; this file covers what the docs do not say and what fails silently.

---

## Scope and honesty

- **Chat and Video only.** No Stream Feeds SDK exists for Unity. Do not route to `/activity-feeds/docs/...` and do not invent a Unity feeds API.
- **Two SDKs, not one.** Separate repos, packages, assemblies, clients, and `AuthCredentials` types. `StreamChat.Libs.Auth.AuthCredentials` and `StreamVideo.Libs.Auth.AuthCredentials` are different types - never pass one where the other is expected, and never claim connecting one client connects the other. They share only the API key and the user id.
- **The Video SDK is pre-1.0** (0.11.0). Say so when the user pins a version or plans an upgrade: minor versions can change the surface, and there is no migration guide - the `CHANGELOG.md` is it.
- **Say no before writing code.** Run the feature gate in [`SKILL.md`](SKILL.md) Gate 3 first. Emitting `channel.ArchiveAsync(...)` or `call.StartScreenShareAsync(...)` and letting the compiler explain that they do not exist is the failure mode this rule prevents.
- **Never paste a `label="C#"` docs snippet into game code.** On the Chat pages that label means the **.NET server-side SDK**: it constructs `new StreamClient(apiKey, apiSecret)` and needs the secret. Only `label="Unity"` blocks are client code. See [`SKILL.md`](SKILL.md) "the fence label".
- **Neither SDK ships UI components.** Both ship a sample project. Do not tell the user to "add the channel list prefab" - there isn't one. Run [`ui.md`](ui.md).

## Secrets and auth

- The client holds only the **API key** and a **user token**. The API **secret** never goes into a scene, a `ScriptableObject`, `ProjectSettings`, a `Resources` folder, a built player, or chat - it stays server-side / in the CLI. A Unity build is trivially unpackable; treat anything shipped in `Assets/` as public.
- Token model: backend-issued token via an `ITokenProvider` in production; a CLI token (`getstream token <user_id>`, optionally `--ttl <duration>`) for local/demo; a static pasted token only when the user insists.
- **A hardcoded token must carry a comment saying why it is wrong for production**: it ships to every device, cannot be rotated or revoked, and defeats token refresh (the SDK has nothing to call when it expires).
- `StreamChatClient.CreateDeveloperAuthToken(userId)` and `StreamVideoClient.CreateDeveloperAuthToken(userId)` are **development only** - they require the app to have auth checks disabled, which means any client can impersonate any user. Never ship them, and never enable dev tokens on an app that has real users.
- **Only Chat has a production token-refresh hook.** `IStreamChatClient.ConnectUserAsync(apiKey, userId, ITokenProvider)` lets the SDK re-fetch on connect, reconnect, and expiry. `IStreamVideoClient.ConnectUserAsync` takes `AuthCredentials` only - a Video token that expires mid-session ends the session, so mint Video tokens with a TTL that outlives the longest expected call and reconnect with fresh credentials.
- Never invent or fabricate credentials. Reference them through a `ScriptableObject` config or `[SerializeField]` fields, never as literals scattered across scripts.
- User ids may contain only `a-z`, `0-9`, `@`, `_`, and `-`. Both SDKs ship `SanitizeUserId(...)` - use it on anything derived from a display name, Steam id, or platform account.

## THE headline rule: the client outlives the scene

`CreateDefaultClient()` on either SDK spawns a hidden `GameObject` (named `Stream Chat Client Runner` / `Stream Client Runner`, flagged `HideFlags.HideAndDontSave`) that carries a `MonoBehaviour` whose `Awake` calls **`DontDestroyOnLoad(gameObject)`**. That runner drives the client's per-frame `Update()` - and for Video also the required `WebRTC.Update()` coroutine.

Two consequences, and both bite:

1. **The client survives every scene load.** Create it in `Awake`/`Start` of an object that exists in a scene you reload, and each reload opens **another** client and **another** WebSocket. The user shows up multiple times, events fire N times, and MAU is billed for a connection you forgot. There is no automatic de-duplication.
2. **You cannot see the runner in the Hierarchy** to notice, because it is hidden - unless you enable the debug flag (below).

**Rule: create the client exactly once per application run, from an object that is itself persistent.** The two correct shapes:

```csharp
// 1. A single persistent manager - the common case.
public sealed class ChatManager : MonoBehaviour
{
    public static ChatManager Instance { get; private set; }
    public IStreamChatClient Client { get; private set; }

    private void Awake()
    {
        if (Instance != null)        // a reloaded scene brought a second copy
        {
            Destroy(gameObject);     // destroy the duplicate BEFORE it creates a client
            return;
        }

        Instance = this;
        DontDestroyOnLoad(gameObject);
        Client = StreamChatClient.CreateDefaultClient();
    }
}
```

```csharp
// 2. A RuntimeInitializeOnLoadMethod / bootstrap scene that is never reloaded.
//    Same rule: one CreateDefaultClient() call for the whole process.
```

Never call `CreateDefaultClient()` in a method that can run twice - not in a UI script's `Start`, not in a button handler, not in `OnEnable`, and never per channel or per call.

## Teardown: disconnect, then dispose - `Dispose()` does not disconnect

`IStreamChatClient.Dispose()` tears down the socket plumbing and destroys the runner, but it **does not disconnect the user** (the SDK source still carries `//StreamTodo: disconnect current user` at that line). Dispose alone leaves the user's presence to time out server-side.

```csharp
private async void OnDestroy()   // or on sign-out
{
    if (_client != null)
    {
        await _client.DisconnectUserAsync();   // presence goes offline now, not on a timeout
        _client.Dispose();
    }
}
```

For Video: `await _client.DisconnectAsync()` then `Dispose()`, and **leave the active call first** - `await client.ActiveCall.LeaveAsync()` - or other participants keep seeing a frozen tile until the server reaps the session.

`async void OnDestroy` is the one place `async void` is acceptable in this pack (Unity's message signature is `void`); wrap the body in try/catch so a failed disconnect during shutdown cannot throw into the engine.

## The runner does not run in Edit mode

If `Application.isPlaying` is false, the runner logs a warning, `DestroyImmediate`s itself, and **the client never ticks** - no events, no reconnect, nothing completes. So:

- **Never create a client from an editor script, an `[InitializeOnLoad]` hook, `OnValidate`, or a custom inspector.** If the user genuinely needs chat in an editor tool, they must call `IStreamChatClientEventsListener.Update()` and `Destroy()` themselves every editor tick.
- The same applies to tests that are not run in Play mode.

## Async in Unity: `await` continues on the main thread, and exceptions vanish

Both SDKs are `async Task`-based and their awaits resume on Unity's main thread, so touching `GameObject`s after an `await` is safe. Two rules still apply:

- **Never `async void` except for Unity message methods** (`Start`, `OnDestroy`, a button callback). An unobserved exception in an `async void` is swallowed - the call silently does nothing and no error appears. Return `Task` from your own methods and `await` them.
- **Always try/catch around Stream calls, and inspect `StreamApiException`.** Connect and join failures are normal (bad token, no permission, channel type missing, call not found), and the API throws rather than returning null. Use the `StreamApiExceptionExtensions.Is*` helpers to branch instead of string-matching messages.
- **Guard object lifetime after an await.** The `MonoBehaviour` you started from may have been destroyed while the request was in flight. Check `this == null` (Unity's fake-null works for destroyed objects) or a `_isDestroyed` flag before assigning to a UI field.

```csharp
private async Task ConnectAsync()
{
    try
    {
        var localUserData = await _client.ConnectUserAsync(_apiKey, _userId, _userToken);
        if (this == null) { return; }             // destroyed while connecting
        _label.text = $"Connected as {localUserData.User.Name}";
    }
    catch (StreamApiException e)
    {
        Debug.LogError($"Stream connect failed: {e.Message}");
    }
}
```

`GetCallAsync` is a specific trap: **the Video docs say it "will return null if the call was not found", and it does not.** The implementation awaits the coordinator API, which throws `StreamApiException` on a 404. `StreamCallNotFoundException` is declared in the SDK but never thrown anywhere. Handle not-found in `catch`, not with a null check.

## Video: you must bind tracks, or there is no audio and no video

This is the single most common Video integration failure, and it fails **silently** - the call connects, participants appear, `ParticipantCount` is right, and the screen is black.

Incoming media arrives as tracks that you attach to Unity components yourself:

```csharp
private void OnParticipantTrackAdded(IStreamVideoCallParticipant participant, IStreamTrack track)
{
    switch (track)
    {
        case StreamAudioTrack audioTrack:
            audioTrack.SetAudioSourceTarget(_audioSource);   // no call = no sound
            break;
        case StreamVideoTrack videoTrack:
            videoTrack.SetRenderTarget(_rawImage);           // no call = black tile
            break;
    }
}
```

- **Subscribe to `participant.TrackAdded` and bind there.** It fires for tracks published before you joined too.
- **Do not also iterate `participant.GetTracks()`** to bind - you would handle every track twice.
- **`TrackAdded` can fire more than once for the same participant.** A reconnect hands you new track instances. Update the existing binding; do not assume one-shot.
- **The local participant has no tracks.** Your own camera is never received from the server. Self-preview comes from `client.VideoDeviceManager.GetSelectedDeviceWebCamTexture()` assigned to `RawImage.texture`, and it changes when the selected device changes - re-read it in `SelectedDeviceChanged`. See [`ui.md`](ui.md).

## Video: incoming video is capped at 5 participants by default

The SDK auto-subscribes video for up to **5** participants; audio is auto-subscribed with no limit. Past 5, video is simply not requested and those tiles stay black with no error.

- Call `participant.SetIncomingVideoEnabled(true/false)` from your own visibility logic - on join and whenever a tile scrolls in or out of view.
- Call `participant.UpdateRequestedVideoResolution(new VideoResolution(w, h))` to match the rendered size. The default request is 1080p; asking for 1080p to fill a 240x135 thumbnail burns bandwidth that the server then takes back from the streams the user is actually watching.
- Lower the fleet-wide default with `StreamClientConfig.Video.DefaultParticipantVideoResolution` for larger calls.

Enabling video for every participant regardless of visibility is not a harmless default - the server downgrades resolution, framerate, or pauses video for **everyone** when total demand exceeds the link.

## Video: `MuteSelf` is a server round-trip, and it is fire-and-forget

`IStreamCall.MuteSelf(bool audio, bool video, bool screenShare)` returns `void` but internally calls `MuteUsersAsync` **without awaiting it** - failures are unobserved and there is nothing to await for UI feedback. It also throws if the local participant is not yet in `Participants`.

- To toggle the local user's own mic/camera, use the device managers: `client.AudioDeviceManager.SetEnabled(false)` / `client.VideoDeviceManager.SetEnabled(false)`. That stops capture locally, immediately, with no round-trip.
- Use `MuteUsersAsync(...)` directly (and await it) when you genuinely mean the server-side mute of *other* users, which needs the `MuteUsers` capability.

## Device info structs are never null - and `CameraDeviceInfo.IsValid` is not public

`MicrophoneDeviceInfo` and `CameraDeviceInfo` are `readonly struct`s, so `SelectedDevice` is never `null`; with nothing selected you get `default`.

- `MicrophoneDeviceInfo.IsValid` is **public** - use it.
- **`CameraDeviceInfo.IsValid` is `internal`**, despite the docs telling you to check it. From game code check `string.IsNullOrEmpty(device.Name)` or compare against `default(CameraDeviceInfo)` instead.
- `EnumerateDevices()` can return an empty sequence (no webcam, permission denied, headless CI). Never `.First()` it unguarded; `TryFindFirstWorkingDeviceAsync()` exists for exactly this.

## Chat: query once, then let the WebSocket do the work

The Chat SDK is **stateful** - `IStreamChannel`, `IStreamMessage`, and `IStreamUser` patch themselves as events arrive. Code that re-queries is code fighting the SDK.

- One `QueryChannelsAsync(filters, sort)` per view, then render from `channel.Messages` / `channel.Members` and subscribe to `MessageReceived`, `MessageUpdated`, `MessageDeleted`, `ReactionAdded`, `MemberAdded`, `UserStartedTyping`. Do not poll and do not re-query on every event.
- **Never call a Stream API from `Update`, `FixedUpdate`, `OnGUI`, or a per-frame coroutine.** `OnGUI` in particular runs several times per frame.
- Channels from `GetOrCreateChannel*` and `QueryChannelsAsync` are **watched** automatically, which is what makes events arrive. If you took a channel from `SearchMessagesAsync(WatchResultChannels = false)` or `QueryThreadsAsync(Watch = false)`, it is **not** watched - call `channel.WatchAsync()` or its events never fire. Check `channel.IsWatched` when messages mysteriously do not update.
- `QueryChannelsAsync` limit maxes at 30; `QueryUsersAsync` at 30 with offset capped at 1000. Paginate with `channel.LoadOlderMessagesAsync()` (typically on scroll-to-top) instead of asking for huge pages.
- **Unsubscribe in `OnDestroy`.** Stateful models outlive your views; a `+=` without a matching `-=` keeps a destroyed `MonoBehaviour` alive and reachable, and the handler will then touch destroyed components.
- Back off on errors instead of retrying tightly. There is a per-app query-channels budget on top of global rate limits.

## Mindful API usage (both SDKs)

The SDKs talk to a rate-limited, billed backend.

- **Connect once per session.** One `ConnectUserAsync` per client; never poll, never reconnect on a timer, never connect/disconnect in a loop. Both SDKs reconnect automatically when the network returns.
- **Do not open a call per player in a multiplayer scene.** The video client is client-side and per local player, exactly like the chat client - one per process, on a persistent object, never on a networked/replicated prefab.
- For a high-volume in-game or livestream chat surface, read the livestream best-practices page ([`docs-map.md`](docs-map.md)) before scaling: use the `livestream` channel type, turn off read events / typing indicators / connect events, and enable slow mode.
- Slow mode has **no dedicated Chat Unity method** - set the channel's `cooldown` in seconds via `channel.UpdatePartialAsync(new Dictionary<string, object> { { "cooldown", 30 } })`, and compute the remaining cooldown yourself from the local user's last message (`channel.Cooldown` is the configured value, not a countdown).

## No wrapper or bridge abstractions

Do not introduce `StreamChatService`, `IChatProvider`, `VideoManagerWrapper`, or an interface layer over the SDK. Use the SDK types directly: `IStreamChatClient` on a persistent manager, `IStreamChannel` / `IStreamMessage` handles, `ChannelFilter` for queries, `IStreamCall` / `IStreamVideoCallParticipant` for calls. A thin `MonoBehaviour` that owns the client and exposes it as a property is right; re-exporting its API is not.

Do not add a message cache, an offline store, or an event bus in front of the Chat SDK either - the stateful models already are the cache, and a second copy goes stale.

## Permissions: match the channel type / call type to the vertical

Stream ships types with sensible default policies. Start from the one that fits instead of hand-rolling permissions.

**Chat** (`ChannelType.Messaging` / `Team` / `Gaming` / `Livestream` / `Commerce`, or a custom type from the Dashboard):

| Vertical | Channel type |
|---|---|
| Party / squad / DM chat | `Messaging` - membership-gated |
| Guild / clan / team spaces | `Team` |
| Global in-game chat, zone chat | `Gaming` |
| Livestream / watch-party chat | `Livestream` - public read/write without membership |
| Commerce / live shopping | `Commerce` |

Note the gap: `Livestream` normally pairs with anonymous or guest viewers, and **the Unity SDK cannot connect a guest or anonymous user** ([`SKILL.md`](SKILL.md) Gate 3). Read-only spectators in Unity need a real per-user token, so plan for the MAU cost or gate spectators behind an account.

**Video** (`StreamCallType.Default` / `AudioRoom` / `Livestream` / `Development`, or `StreamCallType.Custom("key")`):

- `Development` has permissive defaults and is for prototyping only - never ship it.
- Check capabilities before offering an action: `call.HasPermissions(OwnCapability.SendVideo)`, and request with `RequestPermissionAsync`. Rendering a "go live" button the user cannot use is a bug.

For both: moderate with a moderator role, never by giving a client the `admin` role. **Permission checks apply to client-side calls only** - server-side calls with the secret bypass them all. Customize policies in the Dashboard or via the server API, never from game code.

## Project ownership

Preserve the project's existing shape. Do not switch the render pipeline, the input system, or the UI system (UGUI vs UI Toolkit) - match what the project already uses. Do not restructure `Assets/`, do not change the active scene list, do not reformat unrelated files, and do not "upgrade" the Unity version to satisfy a Stream requirement without saying so and asking. If there is no Unity project at all, tell the user to create it in Unity Hub first.

Do not commit `Library/`, and never edit files under `Library/PackageCache/` - they are regenerated. A change the user needs to keep goes in their own scripts or in `Packages/manifest.json`.

## Docs discipline

The live Unity docs are the source of truth *where they have Unity code*; the SDK source in the project is the source of truth everywhere else. Do not answer SDK specifics from training data. Cite the page or the file path. Never guess a class, method, or property name - `ChannelFilter`, `ChannelSortFieldName`, `StreamSendMessageRequest`, `IStreamLocalUserData`, `OwnCapability` all look guessable and the near-misses are routinely wrong.

---

## Unity pitfalls (the ones that fail silently)

Full procedures live in the runbooks; these are the traps, stated once.

### Newtonsoft.Json collides, and the fix depends on which copy you keep

The Chat SDK **vendors** `com.unity.nuget.newtonsoft-json@3.0.2` under `Assets/Plugins/StreamChat/Libs/Serialization/`. A project that already has Newtonsoft (as a UPM package or a loose DLL) fails to compile with `Multiple precompiled assemblies with the same name Newtonsoft.Json.dll`. Delete **one** copy - either the SDK's vendored folder or the project's existing one. If you delete the SDK's, verify the surviving copy supports IL2CPP; the vendored one is known to.

The Video SDK instead declares `com.unity.nuget.newtonsoft-json` as a real UPM **dependency**, so it resolves normally. Installing both SDKs is fine as long as only one *precompiled* Newtonsoft assembly ends up in the build.

### The Video SDK vendors a forked WebRTC package - do not install Unity's

`Packages/StreamVideo/Runtime/Libs/io.stream.unity.webrtc` is `io.stream.unity.webrtc@3.0.0-pre.8-stream.1`, described as a modified `com.unity.webrtc` with custom patches, embedded as source inside the Stream package. Adding `com.unity.webrtc` to `manifest.json` alongside it produces two `Unity.WebRTC` assemblies and a duplicate-type build failure. If the project already depends on `com.unity.webrtc` for its own reasons, that conflict has to be resolved before the Video SDK can go in - flag it, do not paper over it.

### IL2CPP strips the SDK's serialization types unless `link.xml` survives

Both SDKs deserialize server payloads by reflection, so managed stripping can remove types nothing references statically. Each ships a `link.xml` to prevent it:

- **Chat**: `Assets/Plugins/StreamChat/link.xml` - preserves the `InternalDTO.*` namespaces and `Newtonsoft.Json.Serialization`. It works because it sits in `Assets/`; **deleting or moving it out of `Assets/` breaks IL2CPP builds only**, and the symptom is a runtime deserialization failure in the player with no editor warning.
- **Video**: the package ships its `link.xml` plus `CoreAssemblyLinkXmlInstaller` / `LibsAssemblyLinkXmlInstaller`, editor-only installers that copy it into the project. If a Video IL2CPP player fails to parse responses, check the installers ran (the `link.xml` landed in `Assets/`) before touching anything else.

Raising `Managed Stripping Level` above the project default without confirming the `link.xml` is in place is how this bug ships.

### Assembly definitions: `Assembly-CSharp` just works, your own `.asmdef` does not

`StreamChat.Core` and `StreamVideo.Core` are both `autoReferenced: true`, so plain scripts in `Assets/` see them with no setup. **If the user's scripts live under their own `.asmdef`, that assembly must add an explicit reference** (`StreamChat.Core` / `StreamVideo.Core`) or every Stream type is "not found" - a compile error that reads like a broken install. This is the single most common "the package imported but nothing resolves" report.

### Chat's WebGL support is real, Video's is not

Chat swaps in a JS-backed WebSocket under `UNITY_WEBGL` and works. Video is built on Unity's WebRTC package, which does not support WebGL - the build will not produce a working call. There is no flag to enable it. ([`SKILL.md`](SKILL.md) Gate 2.)

### Android Video needs IL2CPP + ARM64 + API 23 + Internet "Require"

Four player settings, all of them load-bearing, and the failures do not point at them: Mono or ARMv7 means no native WebRTC, an Internet-access setting of "Auto" can omit the permission, and a Minimum API below 23 fails at install. Details in [`platforms.md`](platforms.md).

### iOS Video needs usage descriptions, Bitcode off, and a small audio buffer

Camera and Microphone usage descriptions must be set in Player Settings *after* switching the target to iOS (the fields do not exist before that), or the OS kills the app on first capture. `Enable Bitcode` must be `NO` in the generated Xcode project. And - documented only in the Video `CHANGELOG.md` for 0.10.0, not on the iOS page - set **Project Settings > Audio > DSP Buffer Size** to **Best Latency**: if Unity locks a large audio buffer before the call starts, its session config fights the SDK's and echo cancellation degrades.

### Tags are not named consistently - resolve them, never guess

The Video repo has `0.11.0` (no `v`), `0.10.0` **and** `v0.10.0`, `v0.9.0`, and a typo'd `v.0.8.19`. `v0.11.0` does not exist. Chat is consistent (`v5.7.0`) except `v5.2` (no patch). So a URL built from a guessed tag 404s. Resolve the real string first:

```bash
gh api repos/GetStream/stream-video-unity/releases/latest --jq .tag_name
gh api repos/GetStream/stream-chat-unity/releases/latest --jq .tag_name
```

### The Chat repo's default branch is `develop`, and the docs link to `main`

`main` does not exist in `stream-chat-unity`, so the introduction page's sample-project link 404s. Use `develop` or a tag when reading source or pointing the user at a file. The Video repo does use `main`.

### `STREAM_DEBUG_ENABLED` is the diagnostic switch nobody mentions

Toggle it from **Tools > Stream > Toggle STREAM_DEBUG_ENABLED compiler flag** in the editor menu (both SDKs ship the menu item). It unhides the client runner `GameObject` so you can see it in the Hierarchy - which is how you catch a duplicate client - and turns on verbose SDK tracing. Pair it with `StreamLogLevel.Debug` in the client config while diagnosing, and turn both off before shipping.

### Signs of a healthy first run

- **Chat:** `ConnectUserAsync` returns and `localUserData.User.Name` is populated; `QueryChannelsAsync` returns a non-zero count (zero means the token user is a member of no channels - seed one); a message sent from the Dashboard's Chat Explorer arrives on `channel.MessageReceived` without a re-query.
- **Video:** `ConnectUserAsync` returns; `JoinCallAsync` returns a call whose `Participants` includes the local participant; **exactly one** `Stream Client Runner` object exists with `STREAM_DEBUG_ENABLED` on; a second client (a build, or the web demo app on the same call id) shows a tile that is not black - which is the only real proof the tracks were bound.
