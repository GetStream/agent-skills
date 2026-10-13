# Stream Flutter - Video patterns the docs do not cover

The docs ([`docs-map.md`](docs-map.md) "Video") cover each API. This file holds the cross-cutting patterns that have no docs page: a TikTok-style livestream feed, a 1:1 call over a live broadcast, sharing state across a call, audio-room "live" listing, and gluing Chat to Video. Obey [`RULES.md`](RULES.md) "Video" throughout. Confirm every symbol against the pinned `stream_video` source before shipping.


---

## 1. Livestream feed (TikTok-style vertical pager)

One call is joined at a time; every swipe switches calls. The failure mode is a slow, older `join()` finishing **after** a newer swipe and clobbering the state. Fix: a small manager with a **version counter** ("latest request wins") that re-checks the version after every `await`. The old call's `leave()` is intentionally not awaited so swipes stay smooth.

```dart
enum CallManagerState { idle, connecting, connected, failure }

class CallManager extends ChangeNotifier {
  CallManagerState state = CallManagerState.idle;
  Call? currentCall;
  String? currentCallId;
  int _version = 0;
  bool _disposed = false;

  void switchToCall(String callId) {
    if (currentCallId == callId && state != CallManagerState.failure) return;
    final version = ++_version;
    final old = currentCall;
    currentCall = null;
    currentCallId = callId;
    _set(CallManagerState.connecting);
    old?.leave(); // not awaited: teardown overlaps the next connect
    _connect(callId, version);
  }

  Future<void> _connect(String callId, int version) async {
    final call = StreamVideo.instance.makeCall(
        callType: StreamCallType.liveStream(), id: callId);
    currentCall = call;
    final result = await call.join(
      connectOptions: CallConnectOptions(
        camera: TrackOption.disabled(),
        microphone: TrackOption.disabled(),
      ),
    );
    if (version != _version || _disposed) {
      call.leave(); // a newer swipe won - drop this stale call
      return;
    }
    _set(result.isSuccess ? CallManagerState.connected : CallManagerState.failure);
  }

  void _set(CallManagerState s) {
    state = s;
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _version++; // invalidate any in-flight connect
    currentCall?.leave();
    super.dispose();
  }
}
```

Wiring:

- `PageView.builder(scrollDirection: Axis.vertical, onPageChanged: (i) => manager.switchToCall(ids[i]))`; each page is a `ListenableBuilder` on the manager that shows a spinner while connecting and the player only when `currentCallId` matches the page.
- Render with `LivestreamPlayer(call: call, onCallDisconnected: (_) {})` - the no-op callback is required, because the default pops the route and would dismiss the whole feed. Use `joinBehaviour: LivestreamJoinBehaviour.manualJoin` if the manager must fully own join timing.
- Derive "live" from state (`otherParticipants.any((p) => p.isVideoEnabled)` via `PartialCallStateBuilder`, or filter by the `host` role) - never keep a separate flag.
- With the default `allowMultipleActiveCalls: false`, the SDK also leaves the prior call when the new `join()` lands; the explicit `leave()` just stops old media sooner.
- Feed viewers never publish. Hosts are a standard livestream host ("Livestream: guide / host / watch" in [`docs-map.md`](docs-map.md)) using the feed item id as the call id. In production, list the feed from `queryCalls` or your backend.

---

## 2. Floating 1:1 call over a live broadcast (multicall)

The host is live; a viewer rings them; the host accepts into a small floating window while the broadcast stays connected, then everything resumes when the 1:1 ends. Requires `StreamVideoOptions(allowMultipleActiveCalls: true)`; the default `MultiCallAudioPolicy.suspendExisting` hands audio focus over automatically. Docs: "Multiple simultaneous calls" in [`docs-map.md`](docs-map.md).

Host side:

1. Listen to `StreamVideo.instance.state.incomingCall` (foreground only - add [`push.md`](push.md) for background). Ignore the livestream's own `callCid` and any call that arrives while already in a 1:1.
2. On accept: turn the broadcast's mic and camera **off** (viewers see a "host is away" state - the livestream is **not** left), then `call.accept()` and `call.join(connectOptions: <camera + mic enabled>)`. Joining suspends the livestream's audio.
3. Render the 1:1 in a `Stack` over the broadcast view: a `Positioned` `ClipRRect` (about 160x220) holding `StreamCallParticipants(call: call, layoutMode: ParticipantLayoutMode.grid)` plus a mic toggle and a hang-up button.
4. Watch the 1:1's `call.state.valueStream`; when `status.isDisconnected || endedAt != null` (either side hung up), `leave()` it - `suspendExisting` resumes the livestream's audio - then turn the broadcast's mic and camera back on. If the join fails, resume the broadcast immediately.

Viewer side: `makeCall(callType: StreamCallType.defaultType(), id: '<unique>', preferences: DefaultCallPreferences(audioConfigurationPolicy: AudioConfigurationPolicy.broadcaster()))`, then `getOrCreate(memberIds: [hostId], ringing: true, video: true)` and `join(...)`. Ringing must be enabled on the `default` call type. `dropIfAloneInRingingFlow` (default `true`) auto-ends the outgoing call if the host never joins - detect it through `status.isDisconnected`.

Multicall API differences: `StreamVideo.instance.activeCall` **throws** - use `activeCalls` / `listenActiveCalls`. On Android each call runs its own foreground service: `StreamVideoFlutterBackground.stopService(ServiceType.call, callCid: cid)`. Under `suspendIncoming`, nothing auto-resumes - call `resumeAudio()` on the surviving call yourself.

---

## 3. Sharing app state with everyone in a call

Decision rule: **must a client that joins later still see it?**

- **Yes -> custom data** (`call.update(custom: ...)`): durable, stored on the call, re-synced through `CallState.custom` on join. `update(custom:)` **replaces the whole map** - always read, merge, write. Needs the `update-call` capability (granted to `user` on `default`; often not on `audio_room` / `livestream` - grant it or route writes through the host). Read reactively from `call.state` (`StreamBuilder` on `asStream()`); before joining, read once from `(await call.get()).getDataOrNull()?.metadata.details.custom`.
- **No -> custom event** (`call.sendCustomEvent(eventType: 'raise-hand', custom: {...})`, received with `call.callEvents.on<StreamCallCustomEvent>(...)`): ephemeral, only clients connected at send time get it. If late joiners must know the resulting state, also mirror it into custom data.

Docs: "Custom call data" and "Call events / custom events" in [`docs-map.md`](docs-map.md).

---

## 4. Audio rooms: speak requests and the live lobby

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
- **Listing live rooms:** `isBackstage` is not a useful lobby filter, so keep an app-managed flag in sync: `call.update(custom: {'live': true})` right after `goLive()` and `{'live': false}` after `stopLive()`, then `queryCalls(filterConditions: {'type': 'audio_room', 'live': true})`. The flag is app-managed - the SDK's source of truth stays `isBackstage`.

---

## 5. Chat + Video in one app

Docs: "Chat app with video calls" in [`docs-map.md`](docs-map.md). Same API key and **one** user JWT for both - do not mint separate tokens.

- **Alias the imports** - both SDKs export `User`: `import 'package:stream_chat_flutter/stream_chat_flutter.dart' as chat;` and `import 'package:stream_video_flutter/stream_video_flutter.dart' as video;`. Map one app user to `chat.User(id:, name:, image:)` and `video.User(info: video.UserInfo(id:, name:, image:))`.
- `StreamChatClient` lives in the `StreamChat` widget; `StreamVideo(...)` is its own singleton, typically created at login with the same token. Log out of both: `chatClient.disconnectUser()` and `StreamVideo.reset(disconnect: true)` (guard with `StreamVideo.isInitialized()`).
- **Call id derived from the channel** (e.g. `'${channel.id}_call<suffix>'`) - unique per call, traceable to the conversation.
- **Announce a call in the channel** with a custom attachment (`extraData: {'callId': ..., 'callType': ...}`) rendered as a join card by a custom `StreamAttachmentWidgetBuilder`; rebuild the type with `StreamCallType.fromString(callType)`.
- **In-call chat:** a `livestream`-type channel whose id equals `call.id`, so both sides land in the same conversation with no bookkeeping.
- **Ringing variant:** instead of an attachment, ring the channel members - `call.getOrCreate(memberIds: members, ringing: true, video: true)` - and wire [`push.md`](push.md).
