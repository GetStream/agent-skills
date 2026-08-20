# Stream Unity - setup flow (integrate / new project)

Run this once per session for integrate or new-project requests, before feature work. How-to / reference requests skip it entirely. Obey [`RULES.md`](RULES.md) throughout, and make sure [`SKILL.md`](SKILL.md) Step 0's three gates passed first - **the Unity version and the build target decide whether the Video SDK can go in at all**, so they are not optional here.

Chat and Video install completely differently. Do the product(s) the user actually asked for; do not install both "to be safe" - each one adds a Newtonsoft copy or a WebRTC fork to reason about.

---

## 1. Project signals (read-only probe)

```bash
bash -c 'echo "=== UNITY VERSION ==="; cat ProjectSettings/ProjectVersion.txt 2>/dev/null || echo NOT_A_UNITY_PROJECT; \
echo "=== UPM MANIFEST ==="; cat Packages/manifest.json 2>/dev/null; \
echo "=== CHAT SDK PRESENT ==="; find Assets -maxdepth 4 -type d -name "StreamChat" 2>/dev/null; \
find Assets -maxdepth 5 -name "Changelog.txt" -path "*StreamChat*" 2>/dev/null; \
echo "=== VIDEO SDK PRESENT ==="; grep -n "io.getstream.video" Packages/manifest.json 2>/dev/null; \
echo "=== EXISTING NEWTONSOFT ==="; grep -n "newtonsoft" Packages/manifest.json 2>/dev/null; find Assets -name "Newtonsoft.Json.dll" 2>/dev/null; \
echo "=== EXISTING WEBRTC ==="; grep -n "com.unity.webrtc" Packages/manifest.json 2>/dev/null; \
echo "=== USER ASMDEFS ==="; find Assets -name "*.asmdef" -not -path "*StreamChat*" 2>/dev/null | head -10; \
echo "=== UI SYSTEM ==="; grep -rln "UnityEngine.UIElements\|UIDocument" Assets --include=*.cs 2>/dev/null | head -3; \
echo "=== PLAYER SETTINGS ==="; grep -nE "scriptingBackend|managedStrippingLevel|AndroidTargetArchitectures|apiCompatibilityLevel" ProjectSettings/ProjectSettings.asset 2>/dev/null | head'
```

Interpret and hold in context:

- **No `ProjectSettings/ProjectVersion.txt`** -> **stop.** Tell the user to create the project in Unity Hub first, picking an editor version that clears Gate 2. Do not synthesize a Unity project tree by hand.
- **Editor version** -> re-check Gate 2 against it. Unity 6 + Chat means Chat must be **v5.4.0 or newer**.
- **SDK already present** -> this is an upgrade or a feature addition, not a fresh install. Read the installed version first: Chat from `Assets/Plugins/StreamChat/Changelog.txt` (top entry), Video from the `#tag` in `Packages/manifest.json` or `Library/PackageCache/io.getstream.video@*/package.json`.
- **Existing Newtonsoft** (a UPM entry or a loose DLL) + Chat install -> the collision in [`RULES.md`](RULES.md) will happen. Plan which copy to delete *before* importing, and tell the user which.
- **Existing `com.unity.webrtc`** + Video install -> conflict with the SDK's `io.stream.unity.webrtc` fork. Surface it and resolve it before installing; do not install on top.
- **User `.asmdef` files** -> their assembly needs an explicit reference to `StreamChat.Core` / `StreamVideo.Core` (step 2c). Note it now; this is the most common "nothing resolves" report.
- **UI system** -> match it. `UIDocument` / `UnityEngine.UIElements` in the project means UI Toolkit; otherwise assume UGUI (which is what both sample projects use).

State a one-line status, e.g. `Unity 6000.0.32f1 project, UGUI, no Stream SDK, no Newtonsoft conflict - ready for Chat v5.7.0`.

---

## 2. Install

### 2a. Chat - a `.unitypackage` imported into `Assets/`

Distribution is **GitHub Releases only**. There is no UPM package and no Asset Store listing. Resolve the tag rather than guessing it:

```bash
# What the latest release actually ships
gh release view --repo GetStream/stream-chat-unity --json tagName,assets \
  --jq '{tag: .tagName, assets: [.assets[].name]}'
# -> {"tag":"v5.7.0","assets":["Stream.Chat.Unity.SDK.5.7.0.unitypackage"]}

gh release download v5.7.0 --repo GetStream/stream-chat-unity \
  --pattern "*.unitypackage" --dir /tmp
```

Then import. **Ask the user to close the Unity Editor first** if it has the project open - a batch-mode import cannot take the project lock:

```bash
UNITY="/Applications/Unity/Hub/Editor/6000.0.32f1/Unity.app/Contents/MacOS/Unity"   # match ProjectVersion.txt
"$UNITY" -batchmode -quit -logFile /tmp/unity-import.log \
  -projectPath "$PWD" \
  -importPackage /tmp/Stream.Chat.Unity.SDK.5.7.0.unitypackage
```

(Windows: `C:\Program Files\Unity\Hub\Editor\<version>\Editor\Unity.exe`. Linux: `~/Unity/Hub/Editor/<version>/Editor/Unity`.)

If the editor cannot be driven from the shell, hand the user the two-step instead: **Assets > Import Package > Custom Package**, pick the `.unitypackage`, **Import** (leave everything checked).

After import, verify and resolve dependencies:

```bash
ls Assets/Plugins/StreamChat            # Core, Libs, EditorTools, SampleProject, Samples, Tests, link.xml
head -3 Assets/Plugins/StreamChat/Changelog.txt
grep -n "newtonsoft\|textmeshpro" Packages/manifest.json
```

- **Newtonsoft.Json**: the SDK vendors `com.unity.nuget.newtonsoft-json@3.0.2` under `Assets/Plugins/StreamChat/Libs/Serialization/`. If the project already has Newtonsoft, delete one copy - the vendored folder, or the project's existing package/DLL. Keep the one you can confirm supports IL2CPP; the vendored copy does.
- **TextMeshPro** is needed only by the bundled `SampleProject`. If the project has no TMP and does not want the sample, delete `Assets/Plugins/StreamChat/SampleProject/` rather than adding TMP.
- **`Assets/Plugins/StreamChat/link.xml` must stay inside `Assets/`.** Moving or deleting it breaks IL2CPP builds only, at runtime, with no editor warning ([`RULES.md`](RULES.md)).
- `Tests/` and `EditorTools/` can stay; they are gated behind their own assembly definitions and compiler flags.

### 2b. Video - a UPM package from a git URL

The docs tell the user to click through Package Manager. Editing the manifest does the same thing and is reviewable, so prefer it - and **pin the tag**, because an unpinned git dependency tracks `main` and will silently move under the project:

```jsonc
// Packages/manifest.json
{
  "dependencies": {
    "io.getstream.video": "https://github.com/GetStream/stream-video-unity.git?path=/Packages/StreamVideo#0.11.0",
    // ... existing entries
  }
}
```

Resolve the tag string first - the Video repo's tag naming is inconsistent (`0.11.0` has no `v`, `v0.11.0` does not exist):

```bash
gh api repos/GetStream/stream-video-unity/releases/latest --jq .tag_name
```

Two requirements the docs do not state:

- **`git` must be on PATH** for the editor process. UPM shells out to it for git dependencies; without it the resolve fails with a git error, not a Stream error.
- The SDK **vendors a WebRTC fork** (`io.stream.unity.webrtc@3.0.0-pre.8-stream.1`) inside its own package. Do **not** add `com.unity.webrtc`.

Verify after Unity reopens and resolves:

```bash
find Library/PackageCache -maxdepth 1 -name "io.getstream.video*"
cat Library/PackageCache/io.getstream.video@*/package.json | grep -E '"version"|"unity"'
```

To import the sample project: **Window > Package Manager**, switch the scope selector to **In Project**, select **Stream Video & Audio Chat SDK**, expand **Samples**, click **Import** next to *Video & Audio Chat Example Project*.

### 2c. Assembly definitions

Both `StreamChat.Core` and `StreamVideo.Core` are `autoReferenced: true`, so scripts compiled into `Assembly-CSharp` (plain scripts under `Assets/`) see them with no setup.

**If the user's scripts live under their own `.asmdef`**, add the reference or nothing resolves:

```jsonc
// Assets/Scripts/MyGame.asmdef
{
  "name": "MyGame",
  "references": [
    "StreamChat.Core",     // Chat
    "StreamVideo.Core"     // Video
  ]
}
```

`StreamChat.Libs` / `StreamVideo.Libs` do not need to be referenced - `Core` pulls them.

---

## 3. Credentials (ask once, then act)

Collect the API key, a user token, and optional seed data in **one** message, then execute without pausing between steps:

> To wire this with real data I need: (1) should I fetch your API key and mint a token via the Stream CLI, or will you paste them? (2) token expiry (`1h`, `1d`, never)? (3) seed a channel / call so there is something to show on first launch?

If the user says they will paste credentials, take them and skip the CLI.

```bash
# Onboard ONCE in the project dir: authenticate + select/create org & app + write credentials.
# REQUIRED first - token/api all fail with "stream project is not initialized" otherwise.
getstream init

# Mint a user token (never-expiring, or add --ttl <duration>)
getstream token sam
getstream token sam --ttl 2h

# Chat: seed users then a channel, so QueryChannelsAsync is not empty on first run.
# Pick --type to match the vertical (see RULES.md "Permissions").
getstream api UpdateUsers --request '{"users":{"sam":{"id":"sam","name":"Sam"},"alice":{"id":"alice","name":"Alice"}}}'
getstream api GetOrCreateChannel --type messaging --id general \
  --request '{"data":{"created_by_id":"sam","members":[{"user_id":"sam"},{"user_id":"alice"}]}}'
getstream api SendMessage --type messaging --id general \
  --request '{"message":{"user_id":"alice","text":"Hey, welcome in."}}'
```

**Video needs no seeding** - `JoinCallAsync(type, id, create: true, ...)` creates the call on first join. To test a call you need a *second* participant: either a second build, or join the same call id from Stream's web demo app with a token for a different user.

`getstream env` has targets for web/next/vite/expo/ios/android/flutter and **no Unity target**, so do not use it here - carry the API key into Unity yourself (below). Never put the API **secret** in the project. If a CLI step fails, explain briefly and ask the user to paste the missing value.

### Where credentials live in a Unity project

There is no `.env`. A `ScriptableObject` is the right home - it keeps values out of code, is editable in the Inspector, and can be excluded from source control. This is the pattern the Chat sample uses (`SampleProject/Config/DemoCredentials.asset`).

```csharp
// Assets/Scripts/Stream/StreamCredentials.cs
using UnityEngine;

[CreateAssetMenu(fileName = "StreamCredentials", menuName = "Stream/Credentials")]
public sealed class StreamCredentials : ScriptableObject
{
    [Tooltip("Public API key from the Stream dashboard. Safe to ship.")]
    public string ApiKey;

    public string UserId;

    [Tooltip("DEMO ONLY. A token baked into the build ships to every device, cannot be " +
             "rotated or revoked, and cannot be refreshed when it expires. Production " +
             "issues tokens from your backend - see setup.md 4c.")]
    public string UserToken;
}
```

Create the asset (**Assets > Create > Stream > Credentials**), fill it in, and reference it with `[SerializeField]` from the manager. Add the asset to `.gitignore` if the token is real.

**Anything shipped in `Assets/` is public** - a Unity build is trivially unpacked. The API key is fine there; the secret never is, and a long-lived user token should not be.

---

## 4. Wire the client

### 4a. Chat

One persistent manager, one client, correct teardown. This is the minimal integration that actually holds up across scene loads - see [`RULES.md`](RULES.md) "the client outlives the scene".

```csharp
using System;
using System.Threading.Tasks;
using StreamChat.Core;
using StreamChat.Core.Configs;
using StreamChat.Core.Exceptions;
using StreamChat.Core.QueryBuilders.Filters;
using StreamChat.Core.QueryBuilders.Filters.Channels;
using StreamChat.Core.QueryBuilders.Sort;
using StreamChat.Core.StatefulModels;
using UnityEngine;

public sealed class ChatManager : MonoBehaviour
{
    public static ChatManager Instance { get; private set; }

    public IStreamChatClient Client { get; private set; }
    public event Action<IStreamChannel> ChannelReady;

    [SerializeField] private StreamCredentials _credentials;

    private void Awake()
    {
        // A reloaded scene brings a second copy of this object. Destroy it BEFORE it
        // creates a client - the runner is DontDestroyOnLoad, so a duplicate means a
        // second WebSocket that nothing ever closes.
        if (Instance != null)
        {
            Destroy(gameObject);
            return;
        }

        Instance = this;
        DontDestroyOnLoad(gameObject);

        Client = StreamChatClient.CreateDefaultClient(new StreamClientConfig
        {
            LogLevel = StreamLogLevel.FailureOnly,   // StreamLogLevel.Debug while developing
        });
    }

    private async void Start()
    {
        try
        {
            await ConnectAndLoadAsync();
        }
        catch (StreamApiException e)
        {
            // Bad token, revoked token, or the user has no access. The API throws - it
            // does not return null.
            Debug.LogError($"Stream Chat connect failed [{e.Code}/{e.StatusCode}]: {e.ErrorMessage}");
        }
    }

    private async Task ConnectAndLoadAsync()
    {
        var localUserData = await Client.ConnectUserAsync(
            _credentials.ApiKey,
            StreamChatClient.SanitizeUserId(_credentials.UserId),
            _credentials.UserToken);

        if (this == null) { return; }   // destroyed while the request was in flight

        Debug.Log($"Connected as {localUserData.User.Name} ({localUserData.UserId})");

        // ONE query. Channels returned here are watched, so the WebSocket keeps their
        // Messages/Members collections current - never poll, never re-query per event.
        var filters = new IFieldFilterRule[]
        {
            ChannelFilter.Members.In(localUserData.UserId),
        };
        var sort = ChannelSort.OrderByDescending(ChannelSortFieldName.LastMessageAt);

        var channels = await Client.QueryChannelsAsync(filters, sort, limit: 30);
        if (this == null) { return; }

        foreach (var channel in channels)
        {
            Debug.Log($"{channel.Name ?? channel.Id}: {channel.Messages.Count} message(s)");
            ChannelReady?.Invoke(channel);   // hand it to the UI - see ui.md
        }
    }

    private async void OnDestroy()
    {
        if (Instance == this) { Instance = null; }
        if (Client == null) { return; }

        try
        {
            // Dispose() does NOT disconnect the user - the SDK still carries a TODO at
            // that line. Without this the user lingers online until the server reaps them.
            await Client.DisconnectUserAsync();
        }
        catch (Exception e)
        {
            Debug.LogWarning($"Stream Chat disconnect on shutdown: {e.Message}");
        }
        finally
        {
            Client.Dispose();
            Client = null;
        }
    }
}
```

Zero channels returned means the token user is a member of none - seed one (step 3), or create one from the client:

```csharp
// Idempotent: get-or-create. Safe to call on every launch.
var channel = await Client.GetOrCreateChannelWithIdAsync(ChannelType.Messaging, "general");
await channel.SendNewMessageAsync("Hello");
```

### 4b. Video

Same lifetime rules, plus the track binding that decides whether the call has any media at all.

```csharp
using System;
using System.Linq;
using System.Threading.Tasks;
using StreamVideo.Core;
using StreamVideo.Core.Configs;
using StreamVideo.Core.Exceptions;
using StreamVideo.Core.StatefulModels;
using StreamVideo.Libs.Auth;
using UnityEngine;

public sealed class VideoManager : MonoBehaviour
{
    public static VideoManager Instance { get; private set; }

    public IStreamVideoClient Client { get; private set; }

    [SerializeField] private StreamCredentials _credentials;
    [SerializeField] private ParticipantView _participantViewPrefab;   // see ui.md
    [SerializeField] private Transform _participantRoot;

    private void Awake()
    {
        if (Instance != null) { Destroy(gameObject); return; }

        Instance = this;
        DontDestroyOnLoad(gameObject);

        Client = StreamVideoClient.CreateDefaultClient(new StreamClientConfig
        {
            LogLevel = StreamLogLevel.FailureOnly,
            Video =
            {
                // Default request is 1080p per participant. Lower it for grid layouts.
                DefaultParticipantVideoResolution = VideoResolution.Res_720p,
            },
        });
    }

    private async void Start()
    {
        try
        {
            await Client.ConnectUserAsync(new AuthCredentials(
                _credentials.ApiKey,
                StreamVideoClient.SanitizeUserId(_credentials.UserId),
                _credentials.UserToken));

            if (this == null) { return; }

            // Pick devices before joining so the first published frame is not black.
            // Both collections can be empty - no webcam, no permission, headless CI.
            var mic = await Client.AudioDeviceManager.TryFindFirstWorkingDeviceAsync();
            if (mic.HasValue) { Client.AudioDeviceManager.SelectDevice(mic.Value, enable: true); }

            var camera = Client.VideoDeviceManager.EnumerateDevices().FirstOrDefault();
            if (!string.IsNullOrEmpty(camera.Name))
            {
                // CameraDeviceInfo.IsValid is `internal` - check Name, not IsValid.
                Client.VideoDeviceManager.SelectDevice(camera, VideoResolution.Res_720p, enable: true);
            }
        }
        catch (StreamApiException e)
        {
            Debug.LogError($"Stream Video connect failed [{e.Code}/{e.StatusCode}]: {e.ErrorMessage}");
        }
    }

    public async Task JoinAsync(string callId)
    {
        try
        {
            // ring: true notifies every member with an incoming call. Keep it false -
            // the Unity SDK exposes no incoming-call event to answer with.
            var call = await Client.JoinCallAsync(
                StreamCallType.Default, callId, create: true, ring: false, notify: false);

            if (this == null) { return; }

            call.ParticipantJoined += OnParticipantJoined;
            call.ParticipantLeft += OnParticipantLeft;

            foreach (var participant in call.Participants)
            {
                CreateParticipantView(participant);
            }
        }
        catch (StreamApiException e)
        {
            // GetCallAsync/JoinCallAsync THROW on not-found. They do not return null,
            // whatever the docs say.
            Debug.LogError($"Join failed [{e.Code}/{e.StatusCode}]: {e.ErrorMessage}");
        }
    }

    private void OnParticipantJoined(IStreamVideoCallParticipant participant)
        => CreateParticipantView(participant);

    private void OnParticipantLeft(string sessionId, string userId)
    {
        foreach (var view in _participantRoot.GetComponentsInChildren<ParticipantView>())
        {
            if (view.SessionId == sessionId) { Destroy(view.gameObject); }
        }
    }

    private void CreateParticipantView(IStreamVideoCallParticipant participant)
    {
        var view = Instantiate(_participantViewPrefab, _participantRoot);
        view.Init(participant);   // binds the tracks - ui.md
    }

    private async void OnDestroy()
    {
        if (Instance == this) { Instance = null; }
        if (Client == null) { return; }

        try
        {
            // Leave the call first, or other participants keep a frozen tile until the
            // server reaps the session.
            if (Client.ActiveCall != null) { await Client.ActiveCall.LeaveAsync(); }
            await Client.DisconnectAsync();
        }
        catch (Exception e)
        {
            Debug.LogWarning($"Stream Video disconnect on shutdown: {e.Message}");
        }
        finally
        {
            Client.Dispose();
            Client = null;
        }
    }
}
```

`ParticipantView` - the script that actually binds audio and video - is in [`ui.md`](ui.md). Without it the call connects and the screen stays black.

On Android and iOS, request camera/microphone permission before enabling devices; the calls are Unity's, not Stream's. See [`platforms.md`](platforms.md).

### 4c. Production auth

**Chat** has a refresh hook. Implement `ITokenProvider` and the SDK re-fetches on connect, reconnect, and expiry with no extra work:

```csharp
using System.Threading.Tasks;
using StreamChat.Libs.Auth;

public sealed class BackendTokenProvider : ITokenProvider
{
    public Task<string> GetTokenAsync(string userId)
    {
        // Call your own authenticated endpoint and return the JWT it issues.
        // Your backend must authenticate the caller first - never expose an endpoint
        // that returns a Stream token for any userId a client asks for.
    }
}

await Client.ConnectUserAsync(apiKey, userId, new BackendTokenProvider());
```

**Video has no equivalent** - `ConnectUserAsync` takes `AuthCredentials` only. So: fetch a fresh token from your backend immediately before connecting, mint it with a TTL that outlives the longest expected call, and on an auth failure re-fetch and reconnect rather than expecting the SDK to recover. Say this plainly rather than implying parity with Chat.

---

## 5. UI

The client is connected and data is loading. Neither SDK ships components, so putting anything on screen is code you write - run [`ui.md`](ui.md). Do not improvise the Video participant view in particular: the failure mode is a call that connects perfectly and shows nothing, with no error.

---

## 6. Verify before stopping

Enter Play mode and check, do not assume. Turn on diagnostics first: **Tools > Stream > Toggle STREAM_DEBUG_ENABLED compiler flag**, and set `LogLevel = StreamLogLevel.Debug` in the config.

**Chat:**

- Console shows `Connected as <name>` and a non-zero channel count (zero means the token user is a member of no channels - seed one).
- Send a message from the Dashboard's **Chat Explorer** to the seeded channel; `channel.MessageReceived` fires **without a re-query**. That is the proof the WebSocket and the stateful models are working, not just the REST call.
- Exit Play mode: the user goes offline in the Dashboard promptly, not minutes later. If not, `DisconnectUserAsync` is not being awaited.
- With `STREAM_DEBUG_ENABLED` on, exactly **one** `Stream Chat Client Runner` object in the Hierarchy. Two means a duplicate client.

**Video:**

- `ConnectUserAsync` returns and `JoinCallAsync` returns a call whose `Participants` contains the local participant.
- Join the same call id from a second client (another build, or Stream's web demo app with a different user token). The remote tile shows **moving video and audible audio** - that is the only real proof `SetRenderTarget` and `SetAudioSourceTarget` were called. A black tile with a correct participant count is the classic unbound-track bug.
- Self-preview shows the local camera (that comes from `WebCamTexture`, not from a track).
- Exactly one `Stream Client Runner` object.

Then go to [`platforms.md`](platforms.md) before any device build - an editor-only success proves nothing about Android or iOS - and return to **Docs lookup** in [`SKILL.md`](SKILL.md) for each remaining feature.
