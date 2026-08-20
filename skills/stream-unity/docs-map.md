# Stream Unity - docs routing map

Map a request to the exact docs page, then fetch its `.md` twin ([`SKILL.md`](SKILL.md) explains the convention). Live indexes that list every page:

```
https://getstream.io/cli/docs/chat-unity.md
https://getstream.io/cli/docs/video-unity.md
```

Fetch at most 3 pages per request. Cite what you used. Do not guess paths - if it is not below, use the index.

---

## Read this before using the Chat table

The Chat Unity tree is well maintained, but its pages carry code from **two different SDKs** and both fences say C#. The **Code** column below tells you which:

| Marker | Meaning | What to do |
|---|---|---|
| **Unity** | Page has ```` ```csharp label="Unity" ```` blocks. | Fetch it, use the code verbatim. |
| **mixed** | Page has both `label="Unity"` and `label="C#"` blocks. | Fetch it, take **only** the `label="Unity"` blocks. |
| **server C#** | Only ```` ```csharp label="C#" ```` - the **.NET server-side SDK** (`new StreamClient(apiKey, apiSecret)`). | Do **not** use in game code. If the feature also has no client API, see the N/A rows. |
| **prose** | No code, or only JSON/Bash (concepts, config, reference tables). | Fetch it; nothing to translate. |
| **no Unity** | Feature **is** implemented in the Unity SDK, but the page shows none of it. | Fetch for concepts, then read the interface (rung 2 in [`SKILL.md`](SKILL.md)). |
| **N/A** | Feature is **not** implemented in the Unity client SDK. | Do not fetch to write code. Tell the user ([`SKILL.md`](SKILL.md) Gate 3). |

Where a feature is missing, the Chat pages are usually honest about it - a `label="Unity"` block that reads `// This feature is not yet available in the Unity SDK.` The **N/A** and **partial** notes below pre-empt those so you do not spend a fetch to learn it.

The **Video** table needs no such column: all 22 Video Unity pages are Unity-first C# with no server-SDK or JavaScript mixing. Video's problem is absence, not wrong code - see "Video: shipped but undocumented" at the end.

---

# Chat

Prefix every path with `https://getstream.io/chat/docs/unity` unless stated otherwise.

## Start here

| Want to ... | Page (.md) | Code |
|---|---|---|
| Introduction: install, client, connect, channels, messages, events, query, reactions | `.md` (root) | **Unity** |
| Guided first integration (tutorial) | `https://getstream.io/chat/sdk/unity/tutorial.md` | **Unity** |
| What Stream's backend is and how it scales | `/architecture-and-benchmark.md` | prose |
| Feature overview | `/features-overview.md` | prose |
| Roadmap and changelog | `/roadmap-and-changelog.md` | prose |
| Upgrade 4.x -> 5.x (enums became structs) | `/migration-guide-to-5x.md` | **Unity** |

> The root page is unusually complete - client creation, `ConnectUserAsync` with both a token and an `ITokenProvider`, both channel-creation shapes, `StreamSendMessageRequest`, reading `channel.Messages`, the full event list, `QueryChannelsAsync` with `ChannelFilter`, reactions, and disconnect. For "wire up Chat", fetch this one page rather than five feature pages.

## Client, users, and auth

| Want to ... | Page (.md) | Code |
|---|---|---|
| Create the client, connect and disconnect a user | `/init-and-users.md` | **Unity** |
| Tokens, expiry, `ITokenProvider`, dev tokens | `/tokens-and-authentication.md` | **Unity** |
| Query users, filters and sorting | (root page) + `/query-members.md` | **Unity** |
| Presence: online state, last active, invisible | `/presence-format.md` | **Unity** - *partial: setting `invisible` or a status at connect time is N/A; `MarkInvisibleAsync` after connect works* |
| Guest and anonymous users | `/authless-users.md` | **N/A** - the Unity SDK has no guest/anonymous connect |
| Teams / multi-tenant isolation | `https://getstream.io/docs/platform/multi-tenancy.md` | prose - the `/chat/docs/unity/multi-tenant-chat/` path 301s here and has no `.md` twin |
| User groups | `/user-groups.md` | server-side concept; `user.Teams` is read-only on the client |
| Create / update users, custom fields | `https://getstream.io/docs/platform/users.md` | prose - `/chat/docs/unity/update-users/` 301s here. Client-side use `Client.UpsertUsersAsync` |

## Channels

| Want to ... | Page (.md) | Code |
|---|---|---|
| Create a channel by id or by member set | `/creating-channels.md` | **Unity** |
| Query channels: `ChannelFilter`, `ChannelSort`, paging | `/query-channels.md` | **mixed** |
| Filter operator reference (`$in`, `$autocomplete`, ...) | `https://getstream.io/docs/platform/query-syntax-operators.md` | prose - `/chat/docs/unity/query-syntax-operators/` 301s here |
| Update a channel (overwrite and partial) | `/channel-update.md` | **Unity** |
| Paginate channels, messages, members | `/channel-pagination.md` | **Unity** - *partial: paginating watchers is N/A* |
| Members: add, remove, query | `/channel-members.md` | **mixed** |
| Query members with filters | `/query-members.md` | **Unity** |
| Channel management overview | `/channel-management.md` | prose |
| Hide / show a channel | `/hiding-channels.md` | **Unity** |
| Mute / unmute a channel | `/muting-channels.md` | **Unity** |
| Delete a channel | `/channel-delete.md` | **Unity** |
| Truncate a channel | `/truncate-channel.md` | **Unity** |
| Invites: send, accept, reject | `/channel-invites.md` | **Unity** |
| Freeze / unfreeze | `/freezing-channels.md` | **Unity** |
| Disable a channel | `/disabling-channels.md` | **Unity** |
| Channel types and their default config (`Messaging`, `Team`, `Gaming`, `Livestream`, `Commerce`) | `/channel-features.md` | prose |
| Archive a channel | `/archiving-channels.md` | **N/A** - server C# only; archived is a per-member field with no client API |
| Pin a channel | `/pinning-channels.md` | **N/A** - same shape as archiving |

## Messages

| Want to ... | Page (.md) | Code |
|---|---|---|
| Send, edit, soft/hard delete, custom data, mentions, quotes | `/send-message.md` | **mixed** |
| Threads and replies, thread read state, `QueryThreadsAsync` | `/threads.md` | **Unity** |
| Pinned messages | `/pinned-messages.md` | **Unity** - *partial: paginating via the pinned-messages endpoint is N/A; `channel.PinnedMessages` works* |
| Silent and system messages | `/silent-messages.md` | **Unity** |
| Reactions: score, enforce-unique, delete | `/send-reaction.md` | **Unity** - *partial: paginating reactions is N/A* |
| Full-text message search | `/search.md` | **Unity** |
| Files and images | `/file-uploads.md` | **Unity** - *partial: client-level standalone upload is N/A; `channel.UploadFileAsync` / `UploadImageAsync` work* |
| Auto-translation on a channel | `/translation.md` | **Unity** - *partial: on-demand translation of a single message is N/A* |
| Typing indicators | `/typing-indicators.md` | **Unity** |
| Unread counts and read state | `/unread.md` | **Unity** - *partial: unread-mentions-per-channel is N/A* |
| Delivered / read receipts, mark read | `/message-delivery-and-read-status.md` | **no Unity** - see the note below |
| Polls | `/polls-api.md` | **Unity** - *partial: poll answers (text comments) and querying votes are N/A* |
| Slow mode | `/slow-mode.md` | **Unity** - no dedicated method; set `cooldown` via `UpdatePartialAsync` |
| Draft messages | `/drafts.md` | **N/A** - JavaScript only |
| Reminders and bookmarks | `/message-reminders.md` | **N/A** - every Unity block says "not yet available" |
| Location sharing | `/location-sharing.md` | **N/A** - server C#, JS, Kotlin only |
| Pending messages | `/pending-messages.md` | server-side feature; `channel.PendingMessages` is read-only on the client |

> **`/message-delivery-and-read-status.md` is the sharpest trap in this tree.** Read state is fully implemented - `channel.MarkChannelReadAsync()`, `channel.MarkChannelAsUnreadAsync(messageId)`, `channel.Read` (a list of `StreamRead` with `User` / `UnreadMessages` / `LastRead`), `message.MarkMessageAsLastReadAsync()`, `message.MarkThreadAsReadAsync()` - and the page shows **server C#, JavaScript, Node, and Kotlin, with no Unity block at all**. Take the API from `Core/StatefulModels/IStreamChannel.cs` and `IStreamMessage.cs`, and from `/unread.md`, which does have Unity code.

## Events and real-time

| Want to ... | Page (.md) | Code |
|---|---|---|
| Event catalog, subscribing, payloads | `/event-object.md` | **Unity** |

Client-level events live on `IStreamChatClient` (`Connected`, `Disconnected`, `ConnectionStateChanged`, `ChannelDeleted`, `ChannelInviteReceived/Accepted/Rejected`, `AddedToChannelAsMember`, `RemovedFromChannelAsMember`, `ThreadTracked`, `ThreadUntracked`). Channel-level events live on `IStreamChannel` (messages, reactions, members, watchers, typing, mute, truncate, visibility, custom). Presence is on `IStreamUser.PresenceChanged`. Reaction events also surface on `IStreamMessage`. The shipped `Samples/EventsSamples.cs` compiles all of them.

## Moderation

| Want to ... | Page (.md) | Code |
|---|---|---|
| Flag, ban, shadow ban, mute, query bans | `/moderation.md` | **mixed** - only the flagging block is Unity |
| Permission policies and roles | `https://getstream.io/chat/docs/node/chat-permission-policies.md` | prose - `/chat/docs/unity/chat-permission-policies/` 301s here |
| Permission / action reference | `/permissions-reference.md` | prose |

> `/moderation.md` carries 22+ code blocks and exactly **one** is Unity (flagging), even though the client-side surface is substantial: `channel.BanUserAsync` / `BanMemberAsync` / `ShadowBanUserAsync` / `ShadowBanMemberAsync` / `UnbanUserAsync`, `Client.QueryBannedUsersAsync`, `user.MuteAsync` / `UnmuteAsync`, `user.FlagAsync`, `message.FlagAsync`, `channel.MuteChannelAsync`. Read `Core/StatefulModels/IStreamChannel.cs` + `IStreamUser.cs` + `Samples/ModerationCodeSamples.cs`. Note there is **no** user blocking in this SDK.

## Push notifications

`/chat/docs/unity/push-*` paths all **301 to the platform docs** and have no Unity `.md` twin. Fetch the redirect target:

| Want to ... | Page (.md) |
|---|---|
| Push overview and provider setup | `https://getstream.io/docs/platform/push-notifications.md` |
| Register a device | `https://getstream.io/docs/platform/push-devices.md` |

Client side, device registration is on the **low-level client**, not the stateful one, and it is undocumented for Unity:

```csharp
// The only client-side push API in the Chat Unity SDK.
await client.LowLevelClient.DeviceApi.AddDeviceAsync(new CreateDeviceRequest { /* Id, PushProvider, ... */ });
await client.LowLevelClient.DeviceApi.ListDevicesAsync(userId);
await client.LowLevelClient.DeviceApi.RemoveDeviceAsync(deviceId, userId);
```

Getting the token itself is Unity's job, not Stream's - Firebase Unity SDK for Android, `UnityEngine.iOS.NotificationServices` / a native plugin for APNs. See [`platforms.md`](platforms.md).

## Errors, limits, and operations

Read before scaling a vertical ([`RULES.md`](RULES.md) "Mindful API usage").

| Want to ... | Page (.md) | Code |
|---|---|---|
| Handle 429s and API errors with `StreamApiException` | `/rate-limits.md` | **Unity** - a full try/catch + error-code switch and the `Is*` extensions |
| Best practices overview | `/best-practices.md` | prose |
| Livestream and live-shopping (disable read/typing/connect events, slow mode) | `/livestream-best-practices.md` | prose |
| Query-channels budget | `/api-budget.md` | prose + JSON |
| API error codes | `https://getstream.io/docs/platform/api-error-codes.md` | prose - `/chat/docs/unity/api-errors-response/` 301s here |
| Error-handling concepts | `https://getstream.io/docs/platform/error-handling.md` | prose |
| Fair-usage limits | `https://getstream.io/chat/docs/node/fair-usage-limits.md` | prose |
| Marketplace best practices | `https://getstream.io/chat/docs/node/marketplace-best-practices.md` | prose |
| Server-side overview | `/server-side.md` | prose |
| Stream CLI | `/cli-introduction.md` | Bash |

---

# Video

Prefix every path with `https://getstream.io/video/docs/unity` unless stated otherwise. All 22 pages are Unity C#.

## Start here

| Want to ... | Page (.md) | Notes |
|---|---|---|
| Introduction | `.md` (root) | prose |
| Install (UPM git URL, assembly-definition reference) | `/basics/installation.md` | the URL to paste; [`setup.md`](setup.md) has the `manifest.json` edit instead |
| **Quickstart** | `/basics/quickstart.md` | the single most useful Video page - client, join, devices, tracks, and a complete `VideoManager` + `ParticipantView` pair |
| Tutorials index | `/basics/tutorials.md` | links out |
| Video calling tutorial | `https://getstream.io/video/sdk/unity/tutorial/video-calling.md` | end-to-end |
| Audio room tutorial | `https://getstream.io/video/sdk/unity/tutorial/audio-room.md` | end-to-end |
| Import the sample project | `/basics/example-project.md` | Package Manager > Samples > Import |
| Supported Unity versions and platforms | `/platforms/overview.md` | the WebGL / ARM64 / UWP constraints |
| Architecture and benchmarks | `/architecture-and-benchmark.md` | prose |
| Pricing model | `/pricing-guide.md` | prose |
| Changelog | `/roadmap-and-changelog.md` | prose - the repo `CHANGELOG.md` is more detailed |

> **Fetch `/basics/quickstart.md` for any "add a call" request.** It carries the `TrackAdded` contract, the "you must bind tracks or you get nothing" warning, the 5-participant subscription cap, and both complete scripts. Skipping it is how a black-screen integration happens.

## Client and calls

| Want to ... | Page (.md) |
|---|---|
| Create the client, connect, `StreamClientConfig` (log level, RED, DTX, default resolution) | `/guides/client-auth.md` |
| Join / create / get a call; `ring` and `notify`; query members | `/guides/joining-and-creating-calls.md` |
| `IStreamCall` and `IStreamVideoCallParticipant` reference: events, properties, methods | `/guides/call-and-participant-state.md` |
| Query calls: `CallFilter`, `CallSort`, watching results | `/guides/querying-calls.md` |
| Call types and every call-type setting (audio, video, backstage, recording, HLS, ringing, geofencing, transcription, push) | `/guides/configuring-call-types.md` |
| Permissions and moderation: request/grant/revoke, block, remove, mute users, mute all | `/guides/permissions-and-moderation.md` |
| Reactions and custom events | `/guides/reactions-and-custom-events.md` |
| Custom data on a call and on a participant | `/advanced/custom-data.md` |

## Media and rendering

| Want to ... | Page (.md) |
|---|---|
| Camera and microphone: enumerate, select, enable, events, mobile permissions, **self-preview via `WebCamTexture`** | `/guides/camera-and-microphone.md` |
| Bandwidth: the 5-participant cap, `SetIncomingVideoEnabled`, `UpdateRequestedVideoResolution`, FPS guidance | `/guides/video-optimization.md` |
| Pin participants locally and remotely, `SortedParticipants` | `/ui-cookbook/pin-participants.md` |

> Two corrections to apply while reading these pages:
> - `/guides/camera-and-microphone.md` says to check `MicrophoneDeviceInfo.IsValid` / `CameraDeviceInfo.IsValid`. `CameraDeviceInfo.IsValid` is **`internal`** and unreachable from game code - check `string.IsNullOrEmpty(device.Name)` instead. The microphone one is public.
> - `/ui-cookbook/pin-participants.md` offers `IsPinnedLocally(participant)` as the way to check "pinned either locally or remotely". The either/or check is `call.IsPinned(participant)`; `IsPinnedLocally` / `IsPinnedRemotely` are the specific ones.

## Platforms

| Want to ... | Page (.md) |
|---|---|
| Supported versions, platforms, and the WebGL/UWP exclusions | `/platforms/overview.md` |
| Android: IL2CPP, ARM64, API 23, Internet Require | `/platforms/android.md` |
| iOS: camera/microphone usage descriptions, Bitcode off | `/platforms/ios.md` |

[`platforms.md`](platforms.md) in this skill carries these plus what the pages omit (managed stripping, the DSP-buffer setting, desktop, WebGL, and push).

## Video: shipped but undocumented

These are on `IStreamCall` / `IStreamVideoClient` in 0.11.0 with **no Unity docs page anywhere**. Read the interface before generating code, and say that is where it came from:

| Capability | API |
|---|---|
| Livestream backstage: go live / stop live | `call.GoLiveAsync()`, `call.StopLiveAsync()`, `call.Backstage` |
| HLS broadcast | `call.StartHLS()`, `call.StopHLS()`, `call.Egress` |
| Recording | `call.StartRecordingAsync()`, `call.StopRecordingAsync()`, `call.Recording`, `RecordingStarted` / `RecordingStopped` events |
| RTMP ingress | `call.Ingress` |
| Ringing accept/decline | `call.AcceptAsync()`, `call.RejectAsync()` - **but there is no incoming-call event**; see [`SKILL.md`](SKILL.md) Gate 3 |
| Ending a call for everyone | `call.EndAsync()` vs `call.LeaveAsync()` |
| Receiving a screen share | `participant.ScreenShareTrack`, `participant.IsScreenSharing` - **receive only**, no publish API |
| Dominant speaker / speaking state | `call.DominantSpeaker`, `participant.IsSpeaking`, `participant.AudioLevel`, `AudioLevelChanged` |
| Connection quality per participant | `participant.ConnectionQuality` |
| Audio processing module (echo cancellation, AGC, noise suppression) | `client.SetAudioProcessingModule(...)`, `client.GetAudioProcessingModuleConfig(...)` |
| Mobile audio session control | `client.PauseMobileAudioPlayback()`, `client.ResumeMobileAudioPlayback()`, `client.SetAndroidAudioUsageMode(...)` |
| Per-participant incoming audio toggle | `participant.SetIncomingAudioEnabled(bool)` |

Files: `Runtime/Core/StatefulModels/IStreamCall.cs`, `IStreamVideoCallParticipant.cs`, `Runtime/Core/IStreamVideoClient.cs`.

---

## When the docs fall short: source + samples

For Chat this is the exception (moderation, read state, push). For Video it is routine. Both SDKs are already on disk in the project.

### Where to look

| What you need | Chat | Video |
|---|---|---|
| Client API | `Assets/Plugins/StreamChat/Core/IStreamChatClient.cs`, `StreamChatClient.cs` | `Library/PackageCache/io.getstream.video*/Runtime/Core/IStreamVideoClient.cs` |
| Stateful models | `Core/StatefulModels/IStreamChannel.cs`, `IStreamMessage.cs`, `IStreamUser.cs`, `IStreamChannelMember.cs`, `IStreamLocalUserData.cs`, `IStreamThread.cs`, `IStreamPoll.cs` | `Runtime/Core/StatefulModels/IStreamCall.cs`, `IStreamVideoCallParticipant.cs`, `IStreamVideoUser.cs` |
| Tracks | - | `Runtime/Core/StatefulModels/Tracks/StreamVideoTrack.cs`, `StreamAudioTrack.cs`, `IStreamTrack.cs` |
| Devices | - | `Runtime/Core/DeviceManagers/*.cs` |
| Filters and sorting | `Core/QueryBuilders/Filters/**` (`ChannelFilter`, `MessageFilter`, `UserFilter`, `PollFilter`), `Core/QueryBuilders/Sort/**` | `Runtime/Core/QueryBuilders/Filters/**` (`CallFilter`, `CallMemberFilter`), `.../Sort/**` |
| Requests and responses | `Core/Requests/**`, `Core/Responses/**` | `Runtime/Core/Models/**` |
| Config | `Core/Configs/StreamClientConfig.cs` (`LogLevel`, `OptimisticMessageInsert`) | `Runtime/Core/Configs/StreamClientConfig.cs` (`LogLevel`, `Audio`, `Video`) |
| Enums / enumerated structs | `Core/ChannelType.cs`, `ConnectionState.cs`, `StreamLogLevel.cs` | `Runtime/Core/StreamCallType.cs`, `VideoResolution.cs`, `Models/OwnCapability.cs`, `Models/Sfu/ConnectionQuality.cs` |
| Exceptions | `Core/Exceptions/StreamApiException.cs` | `Runtime/Core/Exceptions/*.cs` |
| Low-level client (push devices, raw endpoints) | `Core/LowLevelClient/IStreamChatLowLevelClient.cs`, `LowLevelClient/API/**` | `internal` - not reachable from game code |
| Docs code samples (compiling) | `Assets/Plugins/StreamChat/Samples/*.cs` | `Packages/StreamVideo/DocsCodeSamples/**` |
| Sample project | `Assets/Plugins/StreamChat/SampleProject/Scripts/` | `Packages/StreamVideo/Samples~/VideoChat/` |
| Changelog | `Assets/Plugins/StreamChat/Changelog.txt` | repo `CHANGELOG.md` |

```bash
# Prefer the vendored/cached copy - it is the exact version the project compiles.
grep -rn "SendReactionAsync" Assets/Plugins/StreamChat/Core/StatefulModels/
find Library/PackageCache -maxdepth 1 -name "io.getstream.video*"
grep -rn "GoLiveAsync" Library/PackageCache/io.getstream.video*/Runtime/Core/
```

If the project has no copy yet, read from GitHub at the **tag matching the release** - and resolve the tag string rather than guessing it, because the Video repo's tag naming is inconsistent ([`RULES.md`](RULES.md)):

```bash
CHAT_TAG=$(gh api repos/GetStream/stream-chat-unity/releases/latest --jq .tag_name)
VIDEO_TAG=$(gh api repos/GetStream/stream-video-unity/releases/latest --jq .tag_name)

curl -sL "https://raw.githubusercontent.com/GetStream/stream-chat-unity/$CHAT_TAG/Assets/Plugins/StreamChat/Core/StatefulModels/IStreamChannel.cs"
curl -sL "https://raw.githubusercontent.com/GetStream/stream-video-unity/$VIDEO_TAG/Packages/StreamVideo/Runtime/Core/StatefulModels/IStreamCall.cs"
```

The Chat repo's default branch is **`develop`** and it has no `main` - a `tree/main/...` URL 404s even though the docs use one.

### The changelogs carry things the docs never got

Worth reading before an upgrade or when behaviour looks wrong:

- Chat **v5.6.0** added `IStreamClientConfig.OptimisticMessageInsert` (default `true`). Your own sent message is inserted locally as soon as the send call returns, before the `message.new` echo - so it can briefly appear ahead of a message another user sent just before yours. Set it to `false` when consistent cross-client ordering matters more than instant local feedback.
- Chat **v5.4.0** fixed an IL2CPP build crash on Unity `6000.0.x`. Never pin below it on Unity 6.
- Chat **v5.5.0** added `SearchMessagesAsync`, `channel.WatchAsync()`, `channel.IsWatched`, and fixed `WatchedChannels` listing unwatched channels.
- Video **0.10.0** added `client.CallLeaving` (fires while the call is still live, before state is cleared - `CallEnded` fires after the reset) and the iOS audio-session work, including the **DSP Buffer Size = Best Latency** recommendation that appears nowhere in the docs.
- Video **0.9.0 / 0.11.0** rewrote reconnection and remote-video subscription. If a user reports video that never appears for late joiners, check their version before debugging their code.

Never present a source-derived API as if it were documented - say where you found it (`Source: Runtime/Core/StatefulModels/IStreamCall.cs`).
