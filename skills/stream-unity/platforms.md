# Stream Unity - platforms, build settings, and packaging

Run this for "build for Android", "package for iOS", "it works in the editor but not on device", "IL2CPP build crashes", "why is there no video on my phone", or before any device build. **An editor-only success proves nothing about a player build** - both SDKs deserialize by reflection (so stripping can break them) and the Video SDK is native code with per-platform requirements.

Do the target the user actually asked for. State up front which settings you are changing and why.

---

## 1. Platform support matrix (the gate, restated)

| Target | Chat | Video |
|---|---|---|
| Android | Yes | Yes - **ARM64 only**, IL2CPP, API 23+ |
| iOS | Yes | Yes - usage descriptions + Bitcode off |
| Windows | Yes | Yes - **x64 only** |
| macOS | Yes | Yes - Intel and Apple Silicon |
| Linux | Yes | Yes - Ubuntu 16.04 / 18.04 / 20.04 |
| **WebGL** | **Yes** | **No** - hard stop |
| **UWP** | Yes | **No** |
| Consoles | Claimed, no per-console guidance published - treat as unverified | No |

Video's constraints are Unity's `com.unity.webrtc` constraints, because the SDK vendors a fork of it. There is no flag, define, or workaround that adds WebGL or UWP support.

Editor versions: Video needs **2020.3+** (its package declares `"unity": "2020.3"`). Chat goes back to 2019.x. On **Unity 6**, Chat must be **v5.4.0 or newer** - earlier versions crash IL2CPP builds on `6000.0.x` with a `KeyNotFoundException` in IL2CPP's vtable builder.

---

## 2. Cross-platform: IL2CPP and managed stripping

Both SDKs deserialize server payloads by reflection, so types nothing references statically are strip candidates. Each ships a `link.xml` to prevent that.

**Chat** - `Assets/Plugins/StreamChat/link.xml`, preserving the `StreamChat.Core.InternalDTO.*` and `LowLevelClient.*` namespaces plus `Newtonsoft.Json.Serialization`. It works *because it sits under `Assets/`*.

**Video** - the package ships a `link.xml` plus editor-only installers (`CoreAssemblyLinkXmlInstaller`, `LibsAssemblyLinkXmlInstaller`) that copy it into the project. The imported sample ships one too.

```bash
# Both must resolve before an IL2CPP build. If the Video one is missing, the installers
# have not run - reopen the project / let the editor recompile.
find Assets -name "link.xml" | grep -iE "stream|getstream"
```

Rules:

- **Never move or delete a Stream `link.xml`,** and never move it out of `Assets/`. The failure is IL2CPP-only, at runtime, in the player: responses stop deserializing and you get a `StreamDeserializationException` or silently empty models, with no editor warning.
- **Do not raise `Managed Stripping Level`** above the project's existing setting without confirming both `link.xml` files are present. If the user needs `High`, build once, test a connect + a message/join on device, and only then keep it.
- `Api Compatibility Level` **.NET Standard 2.1** and **.NET Framework** both work. Do not change whichever the project uses.
- Video requires **IL2CPP on Android**; elsewhere Mono is fine for Video and for Chat everywhere.

## 3. Cross-platform: the Newtonsoft.Json collision

The Chat SDK **vendors** `com.unity.nuget.newtonsoft-json@3.0.2` at `Assets/Plugins/StreamChat/Libs/Serialization/`. The Video SDK instead declares it as a normal UPM **dependency**. So:

- Chat alone, in a project that already has Newtonsoft -> `Multiple precompiled assemblies with the same name Newtonsoft.Json.dll`. Delete one copy. Keep one you know supports IL2CPP; the SDK's vendored copy does.
- Chat + Video together -> fine, as long as exactly one *precompiled* Newtonsoft assembly reaches the build. If Chat's vendored folder is present and the UPM package resolved for Video, that is two - delete the vendored folder and let the UPM package serve both.

## 4. Cross-platform: do not add `com.unity.webrtc`

The Video package embeds `io.stream.unity.webrtc@3.0.0-pre.8-stream.1`, a patched fork, as source inside itself. Adding `com.unity.webrtc` to `manifest.json` yields two `Unity.WebRTC` assemblies and a duplicate-type build failure. If the project already depends on `com.unity.webrtc` for its own reasons, flag the conflict and resolve it before installing the Video SDK - do not install on top and hope.

---

## 5. Android

### Player Settings (File > Build Settings > Player Settings)

Four of these are load-bearing for Video and none of the failures points at the setting:

| Setting | Value | Why |
|---|---|---|
| Other Settings > **Scripting Backend** | **IL2CPP** | Mono cannot load the native WebRTC library. Required for Video. |
| Other Settings > **Target Architectures** | **ARM64 on, ARMv7 off** | No ARMv7 native library ships. A build with ARMv7 enabled either fails to link or installs and has no WebRTC. |
| Other Settings > **Internet Access** | **Require** | On "Auto", the `INTERNET` permission can be omitted from the manifest and every request fails on device with no clue why. |
| Other Settings > Identification > **Minimum API Level** | **23 or higher** | Below that the app will not install. |

Chat needs only **Internet Access: Require**; the other three are Video's.

Prerequisites: install the Android module in Unity Hub and switch the platform to Android. A **Keystore** is only needed to publish - skip it for local device testing.

### Runtime permissions

Camera and microphone are runtime permissions, and requesting them is **Unity's job, not Stream's**. Enabling a device without permission silently captures nothing.

```csharp
using UnityEngine.Android;

if (!Permission.HasUserAuthorizedPermission(Permission.Microphone))
{
    Permission.RequestUserPermission(Permission.Microphone);
}
if (!Permission.HasUserAuthorizedPermission(Permission.Camera))
{
    Permission.RequestUserPermission(Permission.Camera);
}
```

`RequestUserPermission` does not block - the dialog is asynchronous. **Do not call `EnumerateDevices()` / `SelectDevice(...)` on the next line.** Request permission on a lobby screen, or use the `PermissionCallbacks` overload and enable devices from the granted callback. The imported Video sample's `Scripts/UI/PermissionsManager.cs` is the reference implementation.

### Audio routing

`client.SetAndroidAudioUsageMode(AndroidAudioUsageMode.VoiceCommunication)` routes call audio through the voice-communication stream (earpiece/speakerphone behaviour, hardware echo cancellation on many devices) instead of the media stream. Use it for a call; leave `Media` for a livestream you only listen to. `client.PauseMobileAudioPlayback()` / `ResumeMobileAudioPlayback()` exist for handing audio focus to another app. All three are undocumented - cite the interface.

### Push notifications

Neither SDK obtains a device token. That is Firebase Unity SDK's job on Android.

- **Chat** can register the token it is given: `client.LowLevelClient.DeviceApi.AddDeviceAsync(new CreateDeviceRequest { ... })`, plus `ListDevicesAsync` / `RemoveDeviceAsync`. Undocumented for Unity - see [`docs-map.md`](docs-map.md).
- **Video has no public device-registration API at all** (`CreateDeviceAsync` is `internal`). Register the device from your backend, and remember there is no incoming-call event either, so ringing on Unity is a native-push + deep-link problem you own end to end ([`SKILL.md`](SKILL.md) Gate 3).
- Provider config (FCM credentials), templates, and payloads are Dashboard/server-side either way.

---

## 6. iOS

### Player Settings

**Switch the build target to iOS first** - the camera/microphone description fields do not exist until you do, which is why they get missed.

| Setting | Value | Why |
|---|---|---|
| Other Settings > **Camera Usage Description** | a real sentence | iOS terminates the app on first camera access without it |
| Other Settings > **Microphone Usage Description** | a real sentence | same for the microphone |
| Other Settings > **Target minimum iOS Version** | 12+ is safe | matches the WebRTC fork's floor |
| (Xcode, after export) **Enable Bitcode** | **NO** | the native WebRTC library is not bitcode-compiled; the archive fails otherwise |

`Enable Bitcode` lives in the **generated Xcode project**, so it resets on a fresh export. Either set it every export or script it in a `PBXProject` post-process build step - and say which you did, because a rebuild that skips it fails confusingly.

### The audio setting that is only in the changelog

Set **Project Settings > Audio > DSP Buffer Size** to **Best Latency** (or **Good Latency**). From the Video SDK's 0.10.0 changelog, not from any docs page: from 0.10.0 the SDK configures the iOS audio session for voice calls itself, but if Unity has already locked a large audio buffer its configuration conflicts and **echo cancellation degrades**. On a call app this presents as the far end hearing themselves, which reads like a Stream bug and is a Unity project setting.

### Permissions

```csharp
Application.RequestUserAuthorization(UserAuthorization.Microphone);
Application.RequestUserAuthorization(UserAuthorization.WebCam);

if (!Application.HasUserAuthorization(UserAuthorization.WebCam)) { /* tell the user */ }
```

`RequestUserAuthorization` returns an `AsyncOperation` - `yield return` it in a coroutine, or await the flag, before enabling devices. Same non-blocking caveat as Android.

### Push / VoIP

Same story as Android, and worse for ringing: PushKit / CallKit have no Stream Unity integration. A Unity iOS app that must ring needs a native plugin, and the Unity Video SDK gives you only `AcceptAsync` / `RejectAsync` to call once your own native layer has woken the app. Do not promise CallKit-style ringing as a Stream feature here.

---

## 7. Desktop (Windows, macOS, Linux)

The easiest targets, and the right place to test a call from two clients on one machine.

- Windows: **x64 only**. Mono or IL2CPP both work.
- macOS: Intel and Apple Silicon both supported. An unsigned local build is fine; distribution needs the usual notarization, which is not Stream-specific.
- Linux: the WebRTC fork targets Ubuntu 16.04/18.04/20.04. Newer distros usually work; treat it as unverified if the user hits a loader error.
- Camera and microphone need no runtime permission API, but **macOS still shows a system prompt on first access** - the app must be foreground when devices are first enabled, or the prompt is missed and capture silently fails.

**Testing two participants locally:** build a standalone player and run it alongside the editor, with a **different user id and token in each**, joining the same call id. Two clients with the same user id is not a valid two-participant call. Note that `HideFlags` keeps the client runner invisible, so use `STREAM_DEBUG_ENABLED` if you need to confirm each process has exactly one.

---

## 8. WebGL (Chat only)

Chat works: it swaps in a browser WebSocket under `UNITY_WEBGL` via `Libs/NativeWebSocket/WebSocket.jslib`. Notes:

- **No threads.** Everything runs on the browser's single thread; a long synchronous block stalls the socket and looks like a disconnect.
- **No `File.ReadAllBytes`.** Uploads need bytes from a browser file input via a jslib bridge, or from a `Texture2D.EncodeToPNG`.
- **Managed stripping still applies** - the `link.xml` requirement is identical.
- **Video will not work.** If the user wants calls on WebGL, the honest answers are: Chat in Unity plus Stream's web Video SDK in surrounding page JavaScript, or a non-WebGL build. Do not attempt a Unity WebGL video build.

---

## 9. Verify a device build

Editor success is not evidence. On the target device, in this order:

1. **It connects.** Chat logs a connected user; Video's `ConnectUserAsync` returns. A failure here is usually the token (expired, or minted for a different app) or Android's missing `INTERNET` permission.
2. **Data deserializes.** Chat: `QueryChannelsAsync` returns channels whose `Messages` are populated. Video: `JoinCallAsync` returns a call with a participant list. Empty models with a successful HTTP call is the **stripping** symptom - go back to section 2.
3. **Realtime works.** Send a message from the Dashboard's Chat Explorer and watch it arrive without a re-query. That exercises the WebSocket, which the REST path does not.
4. **Media flows** (Video). Join from a second client. You need moving video *and* audible audio - a black tile with the right participant count means the tracks were never bound ([`ui.md`](ui.md)), while no tile at all means the join or the permission failed.
5. **Permissions were actually granted,** not just requested. Check `HasUserAuthorizedPermission` / `HasUserAuthorization` on screen rather than assuming the dialog was accepted.

Reading device logs:

```bash
# Android - Unity's own log tag plus the SDK's
adb logcat -s Unity:V ActivityManager:W CRASH:V

# iOS - stream the device console (Xcode > Window > Devices and Simulators, or)
xcrun devicectl device console --device <udid>
```

Turn on **Tools > Stream > Toggle STREAM_DEBUG_ENABLED compiler flag** and `StreamLogLevel.Debug` for a diagnostic build, and turn both **off** before shipping - debug logging is chatty and unhides the client runner object.

---

## 10. What to tell the user before they ship

- The API **secret** is not in the build (it never should be), and the **token** in the build is a demo token that cannot be rotated - move to backend-issued tokens ([`setup.md`](setup.md) 4c). For Video, note the extra constraint: there is no `ITokenProvider`, so a token must outlive the longest expected call.
- Log level is back to `FailureOnly` and `STREAM_DEBUG_ENABLED` is off.
- Managed stripping is whatever was actually tested on device, not whatever looked tidy.
- The Video SDK is **pre-1.0**; pin the exact tag in `Packages/manifest.json` rather than tracking `main`, and read `CHANGELOG.md` before bumping.
- Moderation review happens in the Stream Dashboard, not in the game. The game ships end-user actions only (flag, mute, ban if the user is a moderator).
