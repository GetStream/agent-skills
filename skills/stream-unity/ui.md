# Stream Unity - building the UI (there are no components)

Run this for any "show a channel list", "render the participants", "style the bubbles", or "add call controls" request.

**Neither SDK ships reusable UI.** Say this before promising a screen. What you actually get is a *sample project* per SDK - a complete, working reference implementation you read and adapt, not a component library you drop in. Everything on screen in the user's game is code you write against the stateful models.

| | Chat | Video |
|---|---|---|
| Sample location | `Assets/Plugins/StreamChat/SampleProject/` | `Packages/StreamVideo/Samples~/VideoChat/` (import via Package Manager > In Project > Samples) |
| Scene | `SampleProject/Scenes/ChatDemo.unity` | the imported sample's scene |
| UI system | UGUI + TextMeshPro | UGUI + TextMeshPro |
| Credentials | `SampleProject/Config/DemoCredentials.asset` | fields on the sample manager |

**Match the project's existing UI system.** Both samples are UGUI, so on a UGUI project you can adapt their scripts almost directly. On a UI Toolkit project the *data* half is identical (same models, same events) and only the view half changes - with one hard exception for Video, below.

---

## Video first: the ParticipantView contract

This is the highest-risk UI in either SDK, because getting it wrong produces a call that connects perfectly and shows **nothing**, with no error and a correct participant count.

### Non-negotiable: incoming media must be bound to Unity components

```csharp
using StreamVideo.Core.StatefulModels;
using StreamVideo.Core.StatefulModels.Tracks;
using UnityEngine;
using UnityEngine.UI;

public sealed class ParticipantView : MonoBehaviour
{
    public string SessionId => _participant?.SessionId;
    public IStreamVideoCallParticipant Participant => _participant;

    [SerializeField] private RawImage _video;         // receives StreamVideoTrack
    [SerializeField] private AudioSource _audioSource; // receives StreamAudioTrack
    [SerializeField] private Text _name;

    private IStreamVideoCallParticipant _participant;

    public void Init(IStreamVideoCallParticipant participant)
    {
        _participant = participant;
        _name.text = participant.Name;

        // TrackAdded fires for every track, INCLUDING tracks the participant was already
        // publishing before we joined. Do not also iterate GetTracks() - you would bind twice.
        _participant.TrackAdded += OnTrackAdded;
    }

    private void OnTrackAdded(IStreamVideoCallParticipant participant, IStreamTrack track)
    {
        switch (track)
        {
            case StreamAudioTrack audioTrack:
                // Without this call you do not HEAR the participant.
                audioTrack.SetAudioSourceTarget(_audioSource);
                break;

            case StreamVideoTrack videoTrack:
                // Without this call you do not SEE the participant.
                videoTrack.SetRenderTarget(_video);
                break;
        }
    }

    private void OnDestroy()
    {
        if (_participant != null) { _participant.TrackAdded -= OnTrackAdded; }
    }
}
```

Four properties of this contract that are easy to get wrong:

1. **`TrackAdded` can fire more than once per participant.** A reconnect hands you *new* track instances. The handler must re-bind, not assume one-shot - the code above already does, because it just re-points the same components.
2. **`RawImage` and `AudioSource` must exist on the prefab before `Init`.** `SetRenderTarget(null)` silently does nothing.
3. **`AudioSource` needs no clip and no `Play()`** - the track drives it. Leave `Play On Awake` off. Multiple participants means multiple `AudioSource`s; do not share one.
4. **The `RawImage` needs a `RectTransform` with real size.** A zero-sized tile renders nothing and, if you follow the resolution-matching pattern below, also requests a 0x0 stream.

### UI Toolkit cannot receive a video track

`SetRenderTarget` takes a UGUI `RawImage`; `SetAudioSourceTarget` takes an `AudioSource` (engine-level, so fine either way). There is **no** UI Toolkit overload. On a UI Toolkit project you have two options, and you must tell the user which you are taking:

- Keep a small UGUI `Canvas` for the video surfaces and drive the rest of the call UI in UI Toolkit.
- Bind to a `RawImage` on an off-screen canvas and copy its `texture` into a `VisualElement` background - extra work and an extra blit, so only worth it for a design that genuinely cannot host a canvas.

The same applies to a video texture on a world-space quad or a `Renderer`: bind to a `RawImage` first, then read `_video.texture`.

### The local participant has no tracks

Your own camera is never received from the server, so the local tile is not driven by `TrackAdded` at all:

```csharp
public void SetLocalCameraSource(WebCamTexture localWebCamTexture)
{
    _video.texture = localWebCamTexture;   // may be null when no camera is selected
}

// From the manager, after selecting a device - and again whenever it changes:
_client.VideoDeviceManager.SelectedDeviceChanged += (previous, current) =>
    _localView.SetLocalCameraSource(_client.VideoDeviceManager.GetSelectedDeviceWebCamTexture());
```

`GetSelectedDeviceWebCamTexture()` returns a **new instance** on every device change - re-read it in `SelectedDeviceChanged` rather than caching it once at startup.

### Mobile video arrives rotated

Undocumented, and the sample is the only place it appears. Phones publish in device orientation, so a portrait sender looks sideways to everyone unless you correct it - and the correction source differs for local vs remote:

```csharp
private void FixVideoOrientation()
{
    // Remote: the track reports the angle.
    if (_participant?.VideoTrack is StreamVideoTrack streamVideoTrack)
    {
        _videoRectTransform.rotation =
            _baseVideoRotation * Quaternion.AngleAxis(-streamVideoTrack.VideoRotationAngle, Vector3.forward);
    }

    // Local: no track, so read the WebCamTexture.
    if (_participant != null && _participant.IsLocalParticipant && _video.texture is WebCamTexture webCamTexture)
    {
        // WebCamTexture reports width == 16 until it has actually initialized. Reading
        // videoRotationAngle before that logs a warning EVERY FRAME.
        if (!webCamTexture.isPlaying || webCamTexture.width <= 16) { return; }

        _videoRectTransform.rotation =
            _baseVideoRotation * Quaternion.AngleAxis(-webCamTexture.videoRotationAngle, Vector3.forward);
    }
}
```

`StreamVideoTrack` also raises `VideoRotationAngleChanged`, so you can react to it instead of polling in `Update` if you prefer.

### Request the resolution you actually render

The default request is 1080p **per participant**. Asking for 1080p to fill a 240x135 thumbnail spends bandwidth the server then takes back from the stream the user is watching. Match the request to the rendered rect, and only re-request when it changes:

```csharp
private void Update()
{
    var rect = _videoRectTransform.rect;
    var size = new Vector2(rect.width, rect.height);
    if (size == _lastRequestedSize || size.x < 1f || size.y < 1f) { return; }

    _lastRequestedSize = size;
    _participant.UpdateRequestedVideoResolution(new VideoResolution((int)size.x, (int)size.y));
}
```

The equality guard matters: `UpdateRequestedVideoResolution` is a signalling call, and calling it every frame renegotiates constantly. (`VideoResolution(int, int)` throws on a non-positive dimension, which is the other reason for the guard.)

### Subscribe video only for tiles that are visible

The SDK auto-subscribes video for **5** participants (audio is unlimited). Past 5, video is not requested at all and those tiles stay black. Drive it from your own layout:

```csharp
// On join, on ParticipantJoined, and whenever the layout changes (scroll, page, tab):
participant.SetIncomingVideoEnabled(IsTileVisible(participant));

// Spotlight layouts: full resolution for the big tile, thumbnails for the rest.
spotlight.UpdateRequestedVideoResolution(VideoResolution.Res_720p);
foreach (var thumb in thumbnails) { thumb.UpdateRequestedVideoResolution(VideoResolution.Res_240p); }
```

Skip the local participant in that loop - `participant.IsLocalParticipant` - it has nothing to subscribe to.

Two related bits worth wiring while you are here:

- `track.IsPausedByServer` tells you the server paused a stream for bandwidth. Show a placeholder rather than a black rectangle.
- `participant.SetIncomingAudioEnabled(false)` drops incoming audio for one participant, and `StreamAudioTrack.MuteLocally()` / `UnmuteLocally()` / `IsLocallyMuted()` mute an already-bound track locally. Both are undocumented; use them for a per-participant mute control instead of setting `AudioSource.volume = 0`, which keeps paying for the stream.

### Speaking state, dominant speaker, ordering

For an active-speaker frame, a talking indicator, or a spatial VU meter:

```csharp
participant.IsSpeakingChanged += isSpeaking => _frame.color = isSpeaking ? _active : _idle;
participant.AudioLevelChanged += level => _meter.fillAmount = level;   // 0..1, per frame-ish
call.DominantSpeakerChanged += (current, previous) => { /* re-layout spotlight */ };
```

For grid ordering use `call.SortedParticipants` rather than `call.Participants` - it already puts pinned participants first (remote pins before local ones, most recent first) and raises `SortedParticipantsUpdated`. Pinning is `call.PinLocally` / `UnpinLocally`; to query use `call.IsPinned(p)` for either kind and `IsPinnedLocally` / `IsPinnedRemotely` for the specific one.

### Call controls

Wire the local mic/camera buttons to the **device managers**, not to `call.MuteSelf` - the device managers stop capture locally and immediately, with no server round-trip ([`RULES.md`](RULES.md)):

```csharp
_micButton.onClick.AddListener(() => _client.AudioDeviceManager.SetEnabled(!_client.AudioDeviceManager.IsEnabled));
_camButton.onClick.AddListener(() => _client.VideoDeviceManager.SetEnabled(!_client.VideoDeviceManager.IsEnabled));

// Drive the button visuals from the SDK's state, not from your own bool - the SDK is
// the source of truth and can change it (device lost, permission revoked).
_client.AudioDeviceManager.IsEnabledChanged += on => _micIcon.sprite = on ? _micOn : _micOff;
_client.VideoDeviceManager.IsEnabledChanged += on => _camIcon.sprite = on ? _camOn : _camOff;

_leaveButton.onClick.AddListener(async () => await _client.ActiveCall.LeaveAsync());
```

**Gate every capability-dependent control on the capability**, or you ship a button that throws:

```csharp
_goLiveButton.gameObject.SetActive(call.HasPermissions(OwnCapability.StartBroadcastCall));
_recordButton.gameObject.SetActive(call.HasPermissions(OwnCapability.StartRecordCall));
_muteOthersButton.gameObject.SetActive(call.HasPermissions(OwnCapability.MuteUsers));
```

A device dropdown is `EnumerateDevices()` + `SelectDevice(...)`; remember the info types are structs (never null, check `MicrophoneDeviceInfo.IsValid` or - for cameras, whose `IsValid` is `internal` - `string.IsNullOrEmpty(device.Name)`), and that the list can be empty.

The sample's `Scripts/UI/Devices/MediaDevicePanelBase.cs` and `Scripts/UI/PermissionsManager.cs` are the reference implementations for the dropdown and the mobile permission prompt.

---

## Chat UI

The Chat SDK is **stateful**: `channel.Messages`, `channel.Members`, `channel.TypingUsers`, and `channel.Read` are live collections that the WebSocket patches. So the UI is a projection of those collections plus event subscriptions - never a cache of your own, and never a polling loop.

### Channel list

```csharp
var filters = new IFieldFilterRule[] { ChannelFilter.Members.In(client.LocalUserData.UserId) };
var sort = ChannelSort.OrderByDescending(ChannelSortFieldName.LastMessageAt);
var channels = await client.QueryChannelsAsync(filters, sort, limit: 30);

foreach (var channel in channels) { SpawnRow(channel); }

// Rows update themselves - no re-query.
channel.Updated += ch => row.Refresh(ch);
channel.MessageReceived += (ch, msg) => row.SetPreview(msg.Text, msg.CreatedAt);
client.AddedToChannelAsMember += (ch, member) => SpawnRow(ch);
client.RemovedFromChannelAsMember += (ch, member) => DespawnRow(ch);
client.ChannelDeleted += (cid, id, type) => DespawnRow(cid);
```

Unread badges come from `client.LocalUserData.TotalUnreadCount` / `UnreadChannels` / `UnreadThreads`, and per-channel from `channel.Read` (a list of `StreamRead` with `User`, `UnreadMessages`, `LastRead`).

`QueryChannelsAsync`'s limit maxes at 30. For more, page with `offset`; do not ask for a bigger limit.

### Message list

Render from `channel.Messages` and subscribe. Two things the sample does that a naive implementation misses:

**1. Pool the row views.** Instantiating and destroying a `MessageView` per message thrashes GC in a scrolling list, which is very visible on mobile. `SampleProject/Scripts/Views/MessageListView.cs` keeps a `List<MessageView>` and rebuilds against it.

**2. Load older messages from the scroll position, not on a timer.**

```csharp
private void Update()
{
    // Guard 1: if the content does not fill the viewport, verticalNormalizedPosition is
    // already 1 and you would page instantly on an empty list.
    if (_scrollRect.content.rect.height < _scrollRect.viewport.rect.height) { return; }

    // Guard 2: an idle ScrollRect can sit slightly above 1f, hence the threshold.
    if (_scrollRect.verticalNormalizedPosition >= 1.05f && !_isLoading)
    {
        _ = LoadOlderAsync();   // awaits channel.LoadOlderMessagesAsync()
    }
}
```

`_isLoading` is not optional - without it a single scroll-to-top fires `LoadOlderMessagesAsync` every frame until the response lands, which is exactly the rate-limit spam [`RULES.md`](RULES.md) warns about. This is the one legitimate per-frame check near a Stream API: it reads a `ScrollRect`, and only calls the SDK on an edge.

Events to bind: `MessageReceived`, `MessageUpdated`, `MessageDeleted` (its handler receives `isHardDelete`), `ReactionAdded` / `ReactionRemoved` / `ReactionUpdated`.

For reactions render `message.ReactionCounts` / `ReactionScores` and highlight from `message.OwnReactions`. For a soft-deleted message check `message.IsDeleted` - the text is cleared but the row should stay (that is the point of a soft delete). Threads: `message.ReplyCount` for the summary line, `message.GetThreadAsync()` / `LoadRepliesAsync()` to open one.

### Composer and typing

Throttle typing events - do not send one per keystroke. The sample's `TypingMonitor.cs` uses a **2 second** start-event throttle and a **15 second** stop timeout:

```csharp
// On text change: at most one start event every ~2s while the user keeps typing.
await channel.SendTypingStartedEventAsync();
// After ~15s of no input, or on send:
await channel.SendTypingStoppedEventAsync();
```

Render other people's typing from `channel.TypingUsers` plus `UserStartedTyping` / `UserStoppedTyping` / `TypingUsersChanged`. Filter out the local user.

Slow mode has no dedicated API: read `channel.Cooldown` (seconds, the configured value - **not** a countdown) and compute the remaining time from the local user's last message yourself, then disable the send control. Also catch `StreamApiException` with `CooldownErrorStreamCode` on send, because the server is the authority.

If sent messages appear out of order relative to other participants, that is `OptimisticMessageInsert` (default `true`): your own message is inserted locally as soon as the send returns, so a message another user sent just before yours can arrive over the socket and land ahead of it. Set `StreamClientConfig.OptimisticMessageInsert = false` when consistent cross-client ordering matters more than instant local feedback.

### Avatars and attachment images

Neither SDK loads images for you. `user.Image` and `attachment.ImageUrl` are URLs; fetch them with `UnityWebRequestTexture` and cache by URL. The sample ships `SampleProject/Scripts/Utils/UnityImageWebLoader.cs` as a working `IImageLoader`. Guard the callback against a destroyed row - a scrolling list destroys views while requests are in flight.

For file and image *upload*, `channel.UploadFileAsync(byte[], name)` / `UploadImageAsync(byte[], name)` return a URL you then attach with `StreamAttachmentRequest`. Getting the bytes is Unity's problem (`File.ReadAllBytes`, `Texture2D.EncodeToPNG`, a native gallery plugin) - and note the bundled sample's video-attachment picker only works in the Editor.

### Presence

```csharp
foreach (var member in channel.Members)
{
    member.User.PresenceChanged += (user, isOnline, lastActive) => row.SetOnline(isOnline);
}
```

`user.Online` and `user.LastActive` are the current values. `MarkInvisibleAsync()` / `MarkVisibleAsync()` toggle the local user - but note you cannot connect *as* invisible ([`SKILL.md`](SKILL.md) Gate 3).

---

## Rules that apply to both

- **Unsubscribe in `OnDestroy`.** Stateful models and the call object outlive your views. Every `+=` needs a matching `-=`, or the destroyed `MonoBehaviour` stays reachable and its handler then touches destroyed components - which surfaces as `MissingReferenceException` from a callback with no obvious owner.
- **Guard `this == null` after every `await`** before touching UI. Unity's fake-null works for destroyed objects.
- **Never call a Stream API from `Update`, `OnGUI`, or a layout callback.** Read state there; call the SDK on an edge (a click, a scroll threshold crossing, a visibility change).
- **Drive visuals from SDK state, not from a parallel bool.** `IsEnabled`, `IsSpeaking`, `channel.Messages`, `call.SortedParticipants` are already the truth, and the SDK changes them for reasons your code did not cause (reconnect, device lost, server mute).
- **Build the loading and empty states.** An `await` that takes a second on a bad connection, a channel list with zero results, a call with one participant, and a device list with no camera are all normal - and all four look like bugs if the UI has nothing to show.
- **Read the sample before inventing a pattern.** Message-list pooling, the scroll-to-page guards, the typing throttle, the device dropdown, the orientation fix, and the mobile permission prompt are all solved in the shipped samples, and none of them is in the docs.
