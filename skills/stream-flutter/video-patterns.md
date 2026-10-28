# Stream Flutter - Video patterns the docs do not cover

The docs ([`docs-map.md`](docs-map.md) "Video") cover each API. This file holds the cross-cutting patterns that have no docs page: a TikTok-style livestream feed, a 1:1 call over a live broadcast, sharing state across a call, listing live audio rooms and livestreams, and gluing Chat to Video. Obey [`RULES.md`](RULES.md) "Video" throughout. Confirm every symbol against the pinned `stream_video` source before shipping.


---

## 1. Livestream feed (TikTok-style vertical pager)

One call is joined at a time; every swipe switches calls. The failure mode is a slow, older `join()` finishing **after** a newer swipe and clobbering the state. Fix: a small manager with a **version counter** ("latest request wins") that re-checks the version after every `await`. The old call's `leave()` is intentionally not awaited so swipes stay smooth.

```dart
import 'dart:async';

enum CallManagerState { idle, connecting, connected, failure }

class CallManager extends ChangeNotifier {
  CallManagerState _state = CallManagerState.idle;
  Call? _currentCall;
  String? _currentCallId;
  int _version = 0;
  bool _disposed = false;

  CallManagerState get state => _state;
  Call? get currentCall => _currentCall;
  String? get currentCallId => _currentCallId;

  void switchToCall(String callId) {
    if (_currentCallId == callId && _state != CallManagerState.failure) return;
    _version += 1;
    final version = _version;
    final old = _currentCall;
    _currentCall = null;
    _currentCallId = callId;
    _set(CallManagerState.connecting);
    // Not awaited, so the teardown overlaps the next connect.
    if (old != null) unawaited(old.leave());
    unawaited(_connect(callId, version));
  }

  Future<void> _connect(String callId, int version) async {
    final call = StreamVideo.instance.makeCall(
        callType: StreamCallType.liveStream(), id: callId);
    _currentCall = call;
    final result = await call.join(
      connectOptions: CallConnectOptions(
        camera: TrackOption.disabled(),
        microphone: TrackOption.disabled(),
      ),
    );
    if (version != _version || _disposed) {
      // A newer swipe won, so drop this stale call.
      unawaited(call.leave());
      return;
    }
    _set(result.isSuccess ? CallManagerState.connected : CallManagerState.failure);
  }

  void _set(CallManagerState state) {
    _state = state;
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    // Invalidate any in-flight connect.
    _version += 1;
    final call = _currentCall;
    if (call != null) unawaited(call.leave());
    super.dispose();
  }
}
```

Wiring:

- `PageView.builder(scrollDirection: Axis.vertical, onPageChanged: (i) => manager.switchToCall(ids[i]))`; each page is a `ListenableBuilder` on the manager that shows a spinner while connecting and the player only when `currentCallId` matches the page.
- Render with `LivestreamPlayer(call: call, joinBehaviour: LivestreamJoinBehaviour.manualJoin, onCallDisconnected: (_) {})` - the manager owns `join()`, so the player must not join on its own; the no-op callback is required, because the default pops the route and would dismiss the whole feed.
- Derive "live" from state (`otherParticipants.any((p) => p.isVideoEnabled)` via `PartialCallStateBuilder`, or filter by the `host` role) - never keep a separate flag.
- With the default `allowMultipleActiveCalls: false`, the SDK also leaves the prior call as soon as the new `join()` starts; the explicit `leave()` starts the teardown a little earlier.
- Feed viewers never publish. Hosts are a standard livestream host ("Livestream: guide / host / watch" in [`docs-map.md`](docs-map.md)) using the feed item id as the call id. In production, list the feed from `queryCalls` or your backend.

---

## 2. Floating 1:1 call over a live broadcast (multicall)

The host is live; a viewer rings them; the host accepts into a small floating window while the broadcast stays connected, then everything resumes when the 1:1 ends. Requires `StreamVideoOptions(allowMultipleActiveCalls: true)`; the default `MultiCallAudioPolicy.suspendExisting` hands audio focus over automatically. Docs: "Multiple simultaneous calls" in [`docs-map.md`](docs-map.md).

Host side:

1. Listen to `StreamVideo.instance.state.incomingCall` (foreground only - add [`push.md`](push.md) for background). Ignore the livestream's own `callCid` and any call that arrives while already in a 1:1.
2. On accept: turn the broadcast's mic and camera **off** (viewers see a "host is away" state - the livestream is **not** left), then `call.accept()` and `call.join(connectOptions: <camera + mic enabled>)`. Joining suspends the livestream's audio.
3. Render the 1:1 in a `Stack` over the broadcast view: a `Positioned` `ClipRRect` (about 160x220) holding `StreamCallParticipants(call: call, layoutMode: ParticipantLayoutMode.grid)` plus a mic toggle and a hang-up button.
4. Watch the 1:1's `call.state.valueStream`; when `status.isDisconnected || endedAt != null` (either side hung up), `leave()` it - `suspendExisting` resumes the livestream's audio - then turn the broadcast's mic and camera back on. If the join fails, resume the broadcast immediately.

Viewer side: `makeCall(callType: StreamCallType.defaultType(), id: '<unique>', preferences: DefaultCallPreferences(audioConfigurationPolicy: AudioConfigurationPolicy.broadcaster()))`, then `getOrCreate(memberIds: [hostId], ringing: true, video: true)` and `join(...)`. Ringing must be enabled on the `default` call type. An unanswered ring is cancelled after the call type's `auto_cancel_timeout_ms`, and `join()` returns a failure `Result`. `dropIfAloneInRingingFlow` (default `true`) ends the call when the host leaves and you are alone - detect it through `status.isDisconnected`.

Multicall API differences: `StreamVideo.instance.activeCall` **throws** - use `activeCalls` / `listenActiveCalls`. On Android each call runs its own foreground service: `StreamVideoFlutterBackground.stopService(ServiceType.call, callCid: cid)` (import `package:stream_video_flutter/stream_video_flutter_background.dart`). Under `suspendIncoming`, nothing auto-resumes - call `resumeAudio()` on the surviving call yourself.

---

## 3. Sharing app state with everyone in a call

Decision rule: **must a client that joins later still see it?**

- **Yes -> custom data** (`call.update(custom: ...)`): durable, stored on the call, re-synced through `CallState.custom` on join. `update(custom:)` merges top-level keys into the stored map (omitted keys are kept; a sent key replaces its whole value). Every `call.update(...)` also resets `startsAt` unless you pass it - on scheduled calls always pass the current `startsAt`. Needs the `update-call` capability, which `user` typically holds only as `update-call-owner` (the call's creator) on `default`, `audio_room` and `livestream` - check with `getstream api GetCallType --name <type>`. Route writes through the creator / host, or grant `update-call` to the role on that call type. Read reactively from `call.state` (`StreamBuilder` on `asStream()`); before joining, read once from `(await call.get()).getDataOrNull()?.metadata.details.custom`.
- **No -> custom event** (`call.sendCustomEvent(eventType: 'raise-hand', custom: {...})`, received with `call.callEvents.on<StreamCallCustomEvent>(...)`): ephemeral, only clients connected at send time get it. If late joiners must know the resulting state, also mirror it into custom data.

Docs: "Custom call data" and "Call events / custom events" in [`docs-map.md`](docs-map.md).

---

## 4. Audio rooms and live listings: speak requests and the live lobby

`audio_room` starts in backstage: hosts join and `goLive()`; listeners can join once live, with mic and camera off. Docs: "Audio rooms (+ chat)" and "Roles, permissions, request-to-speak, moderation" in [`docs-map.md`](docs-map.md).

| Step | API |
|---|---|
| Listener checks | `call.hasPermission(CallPermission.sendAudio)` |
| Listener requests | `call.requestPermissions([CallPermission.sendAudio])` |
| Host receives | `call.onPermissionRequest = (StreamCallPermissionRequestEvent r) {...}` |
| Host grants / revokes | `call.grantPermissions(userId: ..., permissions: [...])` / `call.revokePermissions(...)` |
| Listener sees the grant | `call.callEvents.on<StreamCallPermissionsUpdatedEvent>(...)` -> then `setMicrophoneEnabled(enabled: true)` |

- Dismissing a request in the host UI does nothing server-side - **deny is not revoke**; call `revokePermissions` to take the mic back.
- `setMicrophoneEnabled` without `sendAudio` returns a failure `Result` rather than publishing.
- **Listing live rooms / livestreams:** filter on the documented `backstage: false` and `ended_at: {r'$exists': false}` fields - see "Finding live streams" in the livestreaming guide and "Query calls / members" in [`docs-map.md`](docs-map.md). Use the same filter with `'type': 'audio_room'`. Keep an app-managed `custom` flag only for states the server fields do not express.

---

## 5. Chat + Video in one app

Docs: "Chat app with video calls" in [`docs-map.md`](docs-map.md) - but that page still uses **v9** Chat APIs (`StreamMessageInput`, `defaultMessage.copyWith(attachmentBuilders: ...)`, `StreamChannelHeader(actions: ...)`) and never shows its attachment builder. Use the v10 equivalents below (checked against `stream_chat_flutter` 10.6.0). Same API key and **one** user JWT for both - do not mint separate tokens.

- **Alias the imports** - both SDKs export `User`: `import 'package:stream_chat_flutter/stream_chat_flutter.dart' as chat;` and `import 'package:stream_video_flutter/stream_video_flutter.dart' as video;`. Map one app user to `chat.User(id:, name:, image:)` and `video.User(info: video.UserInfo(id:, name:, image:))`.
- `StreamChatClient` lives in the `StreamChat` widget; `StreamVideo(...)` is its own singleton, typically created at login with the same token. Log out of both: `chatClient.disconnectUser()` and `StreamVideo.reset(disconnect: true)` (guard with `StreamVideo.isInitialized()`).
- **Call id derived from the channel** (e.g. `'${channel.id}_call<suffix>'`) - unique per call, traceable to the conversation.
- **Start-call button in the channel header:** `StreamChannelHeader(trailing: ...)` - v10 has no `actions` parameter, and `trailing` takes the place of the default channel avatar.
- **Announce a call in the channel** with a custom attachment (`type: 'video_call'`, `extraData: {'callId': call.id, 'callType': call.type.value}`) rendered as a join card:
  - A custom `Attachment` with no file needs `uploadState: const UploadState.success()` - the default is `UploadState.preparing()`, which renders it as still uploading.
  - The card is a class extending `StreamAttachmentWidgetBuilder`: implement `bool canHandle(Message message, Map<String, List<Attachment>> attachments)` (the map is keyed by attachment type, e.g. `attachments.containsKey('video_call')`) and `Widget? build(BuildContext context, Message message, Map<String, List<Attachment>> attachments)`.
  - Register it globally with `StreamChat(configData: StreamChatConfigurationData(attachmentBuilders: [VideoCallAttachmentBuilder()]))` - custom builders are prepended to `StreamAttachmentWidgetBuilder.defaultBuilders`, so they are checked first and every other type keeps its default rendering.
  - Rebuild the call type on join with `StreamCallType.fromString(callType)` (`StreamCallType.value` gives the string).
- **In-call chat:** a `livestream`-type channel whose id equals `call.id`, so both sides land in the same conversation with no bookkeeping.
- **Ringing variant:** instead of an attachment, ring the channel members - `call.getOrCreate(memberIds: members, ringing: true, video: true)` - and wire [`push.md`](push.md).
