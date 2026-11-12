---
name: stream-unity
description: "Build, integrate, and answer how-to questions for Stream Chat and Stream Video in Unity Engine games and apps. Use for Unity / C# / MonoBehaviour project work - the Chat .unitypackage and the Video UPM package, StreamChatClient / StreamVideoClient wiring, ConnectUserAsync and tokens, channels and messages, calls and participant tracks, camera and microphone devices, building the UI yourself on UGUI or UI Toolkit, IL2CPP, and Android / iOS / desktop / WebGL player settings. Triggers on unity, unity engine, unity 6, unity 2022, monobehaviour, .unitypackage, Packages/manifest.json, asmdef, il2cpp, ugui, rawimage, audiosource, webcamtexture, StreamChatClient, IStreamChatClient, IStreamChannel, StreamVideoClient, IStreamVideoClient, IStreamCall, StreamVideoTrack, in-game chat, unity video call. Chat and Video only - there is no Stream Feeds SDK for Unity."
license: See LICENSE in repository root
compatibility: Requires a Unity project (Unity 2020.3+ for Video, 2019.4+ for Chat) for build/integrate work. Docs lookups need only network access. The `getstream` CLI is the default path for credentials (API key + user token); optional if the user pastes them.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  WebFetch(domain:getstream.io),
  WebFetch(domain:github.com),
  WebFetch(domain:raw.githubusercontent.com),
  Bash(ls *),
  Bash(grep *),
  Bash(find * *),
  Bash(find . *),
  Bash(cat *.json), Bash(cat *.asmdef), Bash(cat *.asset),
  Bash(jq *),
  Bash(gh release *),
  Bash(gh api *),
  Bash(unzip *),
  Bash(curl -sL *),
  Bash(getstream *)
---

# Stream Unity - docs orchestrator for Unity Engine

**Chat and Video.** There is no Stream Feeds SDK for Unity (`/activity-feeds/docs/unity` and `https://getstream.io/cli/docs/activity-feeds-unity.md` both 404). If the user asks for activity feeds in Unity, say so up front and offer the alternatives (the REST/server API driven from your backend, or a platform SDK on a companion app) rather than inventing an API.

**These are two separate SDKs, and almost nothing is shared.** Different repos, different install mechanisms, different maturity, different supported platforms, different docs quality. There is no combined client, no shared `AuthCredentials` type (`StreamChat.Libs.Auth.AuthCredentials` and `StreamVideo.Libs.Auth.AuthCredentials` are distinct types in distinct assemblies), and connecting a user to one does not connect them to the other. Treat "add chat to my Unity call app" as two integrations that happen to share an API key.

| | Chat | Video |
|---|---|---|
| Repo | [`GetStream/stream-chat-unity`](https://github.com/GetStream/stream-chat-unity) (default branch **`develop`**) | [`GetStream/stream-video-unity`](https://github.com/GetStream/stream-video-unity) (default branch `main`) |
| Latest | **v5.7.0** (stable, 5.x line) | **0.11.0** (pre-1.0 - the surface still moves) |
| Install | `.unitypackage` from GitHub Releases, imported into `Assets/` | UPM package from a git URL |
| Entry point | `StreamChatClient.CreateDefaultClient()` -> `IStreamChatClient` | `StreamVideoClient.CreateDefaultClient()` -> `IStreamVideoClient` |
| Namespace | `StreamChat.Core` | `StreamVideo.Core` |
| Platforms | Everything Unity targets, WebGL included | Android (ARM64), iOS, Windows x64, macOS, Linux. **No WebGL, no UWP** |
| Pre-built UI | **None** - a sample project, not components | **None** - a sample project, not components |
| Docs coverage | Good: nearly every page carries real Unity C# | Thin: 22 pages; several shipped capabilities have no page at all |

**Neither SDK ships reusable UI.** Both ship a *sample project* you import and read, not a component library you drop in. Every chat bubble, channel row, participant tile, and call button in the user's game is code you write. Say this before promising a screen, and run [`ui.md`](ui.md) when building one.

This skill **orchestrates**: it gates the request against product, platform, and feature support, routes to the exact docs page, fetches it live, and applies it - while carrying the Unity-specific knowledge the docs do not have (the client's hidden `DontDestroyOnLoad` runner, the track-binding requirement, IL2CPP stripping, and the player settings that decide whether a build works on device at all).

**Rules (read once per session):** [`RULES.md`](RULES.md) - non-negotiable rules + Unity pitfalls. Read before writing any code.

---

## Step 0: Three gates, before any code

Resolve all three from the user's words plus a read-only probe. Each one can turn "here is the code" into "that is not possible", so none is optional and none belongs in a runtime failure later.

### Gate 1: product (and whether it exists for Unity)

| Ask | Answer |
|---|---|
| Chat / messaging / in-game text chat | Supported. Chat SDK. |
| Video calls / audio calls / audio rooms / livestream broadcast | Supported. Video SDK. |
| Both | Two installs, two clients, two connect calls. Do not try to unify them. |
| Activity feeds / timelines / follow graph | **No Unity SDK.** State it immediately; offer the server API path. |
| Moderation review queue / dashboard UI | Not an app surface. Moderation review happens in the Stream Dashboard; the SDKs expose only end-user actions (flag, mute, ban). |

### Gate 2: Unity version and build target (the Video SDK is the constraint)

Probe rather than ask:

```bash
bash -c 'echo "=== UNITY VERSION ==="; cat ProjectSettings/ProjectVersion.txt 2>/dev/null; \
echo "=== UPM MANIFEST ==="; cat Packages/manifest.json 2>/dev/null; \
echo "=== STREAM CHAT PRESENT ==="; find . -maxdepth 5 -type d -name "StreamChat" -not -path "*/Library/*" 2>/dev/null; \
echo "=== STREAM VIDEO PRESENT ==="; grep -n "io.getstream.video" Packages/manifest.json 2>/dev/null; \
echo "=== SCRIPTING BACKEND / TARGET ==="; grep -nE "scriptingBackend|AndroidTargetArchitectures|apiCompatibilityLevel|managedStrippingLevel" ProjectSettings/ProjectSettings.asset 2>/dev/null | head -20'
```

| Situation | What to do |
|---|---|
| Unity **6 / 2023.1 / 2022.3 / 2021.3 / 2020.3** | Both SDKs supported. |
| Unity **2019.4 - 2020.2**, Chat only | Chat supports it (the SDK advertises 2019.x). Video does **not** - its package declares `"unity": "2020.3"` and its WebRTC fork the same. |
| Unity **2019.x - 2020.2**, Video requested | **Hard stop for Video.** Say it immediately: upgrade the editor, or ship Chat only. |
| Target is **WebGL**, Video requested | **Hard stop.** Unity's WebRTC package does not support WebGL, so neither does the Video SDK. Chat *does* work on WebGL. Offer: Chat on WebGL plus a browser-based Video client, or drop WebGL. |
| Target is **Android**, Video requested | ARM64 only. ARMv7 is unsupported and must be disabled. See [`platforms.md`](platforms.md). |
| Target is **UWP** | Video unsupported. |
| Target is a **console** | Chat only, and treat it as unverified - the SDK claims console support but publishes no per-console guidance. |

Unity **6** plus Chat carries one hard version floor: Chat **v5.4.0** fixed an IL2CPP build crash on Unity `6000.0.x` (a `KeyNotFoundException` in IL2CPP's vtable builder). Never pin Chat below v5.4.0 on Unity 6.

### Gate 3: feature support (say no in the plan, not in a compile error)

**Chat - not implemented client-side as of v5.7.0.** If the request needs one of these, say so *before* writing code:

- Guest and anonymous users (`ConnectGuestUser` / anonymous connect do not exist) - this blocks the usual read-only-spectator livestream pattern
- Channel archiving, channel pinning (both are per-member fields with no client API)
- Draft messages, message reminders and bookmarks, location sharing
- User blocking (`BlockUser` / `UnblockUser` / blocked-user list)
- On-demand message translation (auto-translation on a channel *does* work)
- Setting `invisible` or a custom status at connect time (`MarkInvisibleAsync` after connect works)
- Unread-mentions-per-channel count; pagination of reactions, watchers, and pinned messages via their dedicated endpoints
- Client-level standalone file upload (channel-level `UploadFileAsync` / `UploadImageAsync` work)
- Poll answers (text comments) and querying poll votes

**Video - not implemented client-side as of 0.11.0:**

- **Publishing your own screen share.** You can *receive* a remote participant's `ScreenShareTrack`; there is no API to start sharing from Unity. The repo README's feature list says "Screensharing" and means the receive half.
- **Any incoming-call / ringing event.** `call.ring` is handled internally and never surfaced (the source literally reads `//StreamTodo: expose CallRinging event?`). `ring: true` and `AcceptAsync` / `RejectAsync` exist, but the callee has no client-side signal that a call arrived - you need your own push handling.
- **Push device registration.** `CreateDeviceAsync` exists only on an `internal` API and the low-level client is only reachable through an `internal` interface. Register devices from your backend.
- A public calling-state machine. `CallingState` is internal; use `client.CallStarted` / `CallLeaving` / `CallEnded` plus `client.ActiveCall`.
- Video-side chat integration, deeplinking, picture-in-picture, noise cancellation, transcription control, and HLS/RTMP viewer UI have no Unity docs page. `GoLiveAsync` / `StopLiveAsync` / `StartHLS` / `StopHLS` / `StartRecordingAsync` / `StopRecordingAsync` **do** ship on `IStreamCall` - they are undocumented, not absent. Read the interface (rung 2 below) and say where you got it.

Anything server-side stays server-side for both SDKs: call types, channel types, permissions and roles, webhooks, push templates and providers, recording/transcription config, data retention, imports. The client never holds the API secret.

---

## The docs convention - and the per-product coverage reality

Every Stream docs page has a Markdown twin: **take the page URL, drop the trailing `/`, add `.md`.**

```
https://getstream.io/chat/docs/unity/query-channels/   ->   https://getstream.io/chat/docs/unity/query-channels.md
https://getstream.io/video/docs/unity/basics/quickstart/ -> https://getstream.io/video/docs/unity/basics/quickstart.md
```

Always fetch the `.md` variant - clean Markdown, verbatim code, no page chrome. Live indexes that list every page:

| Product | Live index |
|---|---|
| Chat | `https://getstream.io/cli/docs/chat-unity.md` |
| Video | `https://getstream.io/cli/docs/video-unity.md` |

The two trees fail in opposite directions, so the caveat is different per product.

### Chat: the code is real, but not every C# block is *Unity* C#

The Chat Unity tree is well maintained. Roughly 40 of its 53 pages carry a genuine Unity code tab, and where a feature is missing the page usually says so outright:

```csharp label="Unity"
// This feature is not yet available in the Unity SDK.
```

**The one trap is the fence label, and it is easy to miss because both say C#.** These pages mix two different SDKs:

| Fence | Which SDK | Use it? |
|---|---|---|
| ```` ```csharp label="Unity" ```` | The Unity client SDK | **Yes.** Copy verbatim. |
| ```` ```csharp label="C#" ```` | The **.NET server-side** SDK (`using GetStream;`, `new StreamClient(apiKey, apiSecret)`, `chat.SendMessageAsync(...)`) | **No.** It needs the API secret and cannot run in a shipped game. |

`label="C#"` snippets are `IStreamChannel`-shaped only by coincidence: `chat.SendMessageAsync("channel-type", "channel-id", request)` looks close enough to `channel.SendNewMessageAsync(request)` to paste by mistake, and then the fix is "add the API secret to the client", which is exactly wrong. Pages that are **entirely** server-side C# (`archiving-channels`, `pinning-channels`, `location-sharing`) document features the Unity SDK does not have at all - see Gate 3. Pages that are **mixed** (`send-message`, `query-channels`, `channel-members`, `moderation`, `message-delivery-and-read-status`) do have a Unity path; take the `label="Unity"` block and ignore the rest.

`message-delivery-and-read-status` is the sharpest case: read state is **fully implemented** (`channel.MarkChannelReadAsync`, `channel.Read`, `channel.MarkChannelAsUnreadAsync`, `message.MarkMessageAsLastReadAsync`) and the page carries **no Unity block at all**. Get the API from the interface, not from the page's server-side C#.

**Two more Chat-tree facts worth knowing before you fetch:**

- **The CLI index is incomplete.** 15 more paths resolve under `/chat/docs/unity/` - but they **301-redirect** to platform or Node docs (`push-devices` -> `/docs/platform/push-devices/`, `chat-permission-policies` -> `/chat/docs/node/...`, `update-users` -> `/docs/platform/users/`) and their `/chat/docs/unity/<page>.md` twins **404**. Fetch the `.md` at the *redirect target* instead, and expect no Unity code there. [`docs-map.md`](docs-map.md) lists them with their real URLs.
- **The sample-project link in the docs is broken.** The introduction page links `github.com/GetStream/stream-chat-unity/tree/main/...`; the repo has **no `main` branch**. Use `develop` (or a version tag).

### Video: the code is trustworthy, the tree is just small

All 22 Video Unity pages are Unity-first C# - there is no server-SDK mixing and no JavaScript. The problem is absence: no page covers going live, backstage, HLS, RTMP, recording control, ringing flows, or screen-share receive, even though most of those ship on `IStreamCall`. When a Video request has no page, that is normal - go to rung 2 and read the interface.

### Source-of-truth ladder

Walk it in order. Stop at the first rung that answers the question, and cite which rung you used.

| Rung | Source | Use for |
|---|---|---|
| 1 | The page's **`label="Unity"` block** (Chat) or the page's C# (Video) - [`docs-map.md`](docs-map.md) says which pages have one | Anything covered. Copy verbatim. |
| 2 | **SDK source in the project** - `Assets/.../StreamChat/Core/**` and `Library/PackageCache/io.getstream.video*/Runtime/Core/**`, else `raw.githubusercontent.com/GetStream/<repo>/<tag>/...` | Exact signatures, defaults, nullability, what is `public` vs `internal`. The final authority. |
| 3 | **Shipped docs code samples** - Chat: `Assets/Plugins/StreamChat/Samples/*.cs`; Video: `Packages/StreamVideo/DocsCodeSamples/**` | Compiling versions of the snippets behind the docs pages. Often clearer than the page. |
| 4 | **Sample projects** - Chat: `Assets/Plugins/StreamChat/SampleProject/`; Video: `Packages/StreamVideo/Samples~/VideoChat/` | Real end-to-end wiring, including message-list pooling and participant-view spawning. |
| 5 | **Changelogs** - Chat: `Assets/Plugins/StreamChat/Changelog.txt`; Video: `CHANGELOG.md` | Behaviour and config that never reached the docs (see [`RULES.md`](RULES.md)). Richer than the release notes. |

Read from **the version the project actually vendors** - Chat is copied into `Assets/`, Video is resolved into `Library/PackageCache/`, so both are already on disk. Prefer them over GitHub `develop`/`main`.

**URL grounding:** only fetch a page URL you got from [`docs-map.md`](docs-map.md) or from a live index fetch in this conversation. Do not invent doc paths from memory.

---

## Step 1: Classify the request

With the gates passed, pick the mode:

- **How-to / reference** ("how do I query channels?", "what does `SetIncomingVideoEnabled` do?") -> go straight to **Docs lookup**. No setup, no credentials.
- **Integrate** ("add chat to my game", "put a video call in this project") -> run [`setup.md`](setup.md), then **Docs lookup** per feature.
- **New project** ("build me a Unity chat app") -> [`setup.md`](setup.md) then **Docs lookup**, scoped to the requested screens. If there is **no Unity project** (no `ProjectSettings/ProjectVersion.txt`), tell the user to create it in Unity Hub first - do not try to synthesize a Unity project tree by hand.
- **UI work** ("show a channel list", "render the participants", "style the message bubbles", "add call controls") -> run [`ui.md`](ui.md). Neither SDK ships components, so this is code you write; the runbook carries the prefab/pooling patterns, the track-binding contract, and the self-preview path that has no track.
- **Build / ship / run on device** ("build for Android", "why is there no video on my phone?", "IL2CPP build crashes", "package for iOS") -> run [`platforms.md`](platforms.md). The player settings there are load-bearing, not polish: without them an Android Video build has no working WebRTC, an iOS build never gets camera permission, and an IL2CPP build can strip the SDK's serialization types.
- **Upgrade / migrate a version** ("bump Chat to 5.7", "we're on 4.x") -> Chat 4.x -> 5.x is the enum-to-struct migration; read `migration-guide-to-5x.md` from [`docs-map.md`](docs-map.md). For Video, there is no migration guide - read `CHANGELOG.md` between the two versions and say plainly that a pre-1.0 SDK can break API between minors.

---

## Step 2: Docs lookup (every request ends here)

1. Open [`docs-map.md`](docs-map.md). Find the row for the feature; it gives the exact `.md` URL **and what kind of code that page carries**.
2. If the feature is not in the map, fetch the live index for the product and pick from it.
3. **Fetch the `.md` page(s)** with WebFetch. At most 3 per request; beyond that, hand the user the index URL.
4. Use the Unity code verbatim, adapting only to the project's `MonoBehaviour` and scene shape. If the page has no Unity block, drop to rung 2 and read the interface.
5. **Cite what you used:** `Source: [Title](https://getstream.io/...)`, or `Source: Assets/Plugins/StreamChat/Core/StatefulModels/IStreamChannel.cs` for a source read. Never answer SDK specifics from training data - if you did not read it this conversation, read it now or say you could not find it.
6. **Apply best practices** - one `QueryChannelsAsync` then let the WebSocket keep state fresh; subscribe video only for participants actually on screen; connect once. See [`RULES.md`](RULES.md) "Mindful API usage".

---

## What this skill carries

The official docs cover the low-level clients well where they have Unity code, so this skill does not restate them. The curated, non-doc content is:

| File | What it is |
|---|---|
| [`RULES.md`](RULES.md) | Non-negotiable rules + the Unity pitfalls that fail silently. Every rule is stated once, here. |
| [`setup.md`](setup.md) | Version-pinned install for both SDKs (`.unitypackage` and UPM manifest), CLI credentials, and the verified minimal client wiring with correct lifecycle. |
| [`ui.md`](ui.md) | Building the UI yourself - there are no components. Chat lists and composer on UGUI, participant views, the track-binding contract, self-preview, and subscription management. |
| [`platforms.md`](platforms.md) | Per-target player settings, IL2CPP and managed stripping, the Newtonsoft conflict, WebGL, Android/iOS/desktop, and what push does and does not do. |
| [`docs-map.md`](docs-map.md) | Intent -> exact docs page for both products, annotated with what kind of code each page carries, plus the source fallback. |

---

## Support

If the user asks for support or how to contact someone, direct them to [getstream.io/contact](https://getstream.io/contact/). SDK gaps and feature requests go to the repo issues: [Chat](https://github.com/GetStream/stream-chat-unity/issues), [Video](https://github.com/GetStream/stream-video-unity/issues).
