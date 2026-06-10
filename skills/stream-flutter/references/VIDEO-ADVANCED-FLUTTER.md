# Video Advanced - Flutter Use Cases & Advanced SDK Patterns

Advanced Stream Video use cases beyond basic calling and livestreaming: audio rooms,
multiple simultaneous calls, combining Chat with Video, and the advanced call-management
surface (querying, events, preferences, moderation, network handling).
For full widget blueprints, see [VIDEO-ADVANCED-FLUTTER-blueprints.md](VIDEO-ADVANCED-FLUTTER-blueprints.md).

Prerequisites: package install, client init, and call basics from
[`VIDEO-FLUTTER.md`](VIDEO-FLUTTER.md); livestream host/viewer flows from
[`LIVESTREAM-FLUTTER.md`](LIVESTREAM-FLUTTER.md).

Rules: [../RULES.md](../RULES.md).

## Quick ref

- **Audio rooms:** `StreamCallType.audioRoom()` + backstage + request-to-speak permission loop
- **Multicall:** `StreamVideoOptions(allowMultipleActiveCalls: true)` + `MultiCallAudioPolicy`
- **Chat + Video:** one API key, one user token, two clients; call id doubles as chat channel id
- **Livestream feed (TikTok-style):** single-call CallManager with version-guarded switching -> blueprint
- **Query calls:** `StreamVideo.instance.queryCalls(filterConditions: {...})`
- **Per-call tuning:** `makeCall(preferences: DefaultCallPreferences(...))`

---

## Audio Rooms

> **Docs:** [Audio Room with Chat](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/audio-room-with-chat/) · [Permissions & Moderation](https://getstream.io/video/docs/flutter/guides/permissions-and-moderation/)

The `audio_room` call type is built for drop-in audio (Twitter Spaces / Clubhouse style):
camera off, listeners muted by default, speakers managed through call permissions.

### Create, join, go live

The `audio_room` call type starts in **backstage**: only hosts/admins can join before
`goLive()`; listeners wait until the room is live.

```dart
// Host: create and open the room
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.audioRoom(),
  id: 'audio_room_${DateTime.now().millisecondsSinceEpoch}',
);
final createResult = await call.getOrCreate(custom: {'name': 'My Room'});
await createResult.fold(
  success: (_) async {
    final joinResult = await call.join(); // host joins backstage
    await joinResult.fold(
      success: (_) => call.goLive(), // opens the room to listeners
      failure: (failure) {
        debugPrint('join failed: ${failure.error.message}');
      },
    );
  },
  failure: (failure) {
    debugPrint('getOrCreate failed: ${failure.error.message}');
  },
);

// Listener: join a live room
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.audioRoom(),
  id: roomId,
);
final createResult = await call.getOrCreate();
await createResult.fold(
  success: (_) async {
    final joinResult = await call.join(); // allowed once the host is live
    joinResult.fold(
      success: (_) {/* connected */},
      failure: (failure) {
        debugPrint('join failed: ${failure.error.message}');
      },
    );
  },
  failure: (failure) {
    debugPrint('getOrCreate failed: ${failure.error.message}');
  },
);
```

No camera/mic config is needed at join time: `CallConnectOptions` defaults both to
disabled. Listeners enable the mic only after being granted permission.

### Request-to-speak permission loop

| Step                       | API                                                                             |
| -------------------------- | ------------------------------------------------------------------------------- |
| Listener checks capability | `call.hasPermission(CallPermission.sendAudio)`                                  |
| Listener requests          | `call.requestPermissions([CallPermission.sendAudio])`                           |
| Host receives request      | `call.onPermissionRequest = (StreamCallPermissionRequestEvent r) {...}`         |
| Host grants                | `call.grantPermissions(userId: r.user.id, permissions: r.permissions.toList())` |
| Host revokes               | `call.revokePermissions(userId: id, permissions: [...])`                        |
| Listener confirms grant    | `call.callEvents.on<StreamCallPermissionsUpdatedEvent>(...)`                    |

```dart
// Listener: mic button
if (call.hasPermission(CallPermission.sendAudio)) {
  await call.setMicrophoneEnabled(enabled: true);
} else {
  await call.requestPermissions([CallPermission.sendAudio]);
}

// Listener: enable mic once granted
call.callEvents.on<StreamCallPermissionsUpdatedEvent>((event) {
  if (event.user.id == StreamVideo.instance.currentUser.id &&
      event.ownCapabilities.contains(CallPermission.sendAudio)) {
    call.setMicrophoneEnabled(enabled: true);
  }
});
```

`setMicrophoneEnabled` itself guards on `sendAudio` permission - enabling without the
capability returns a failure `Result` instead of publishing.

### Listing live rooms (queryCalls + custom flag)

The SDK's backstage state (`isBackstage`) is not directly filterable as "live" in a useful
way for lobbies; the sample pattern keeps an app-managed custom flag in sync:

```dart
// Host, on go-live / stop-live:
await call.goLive();
await call.update(custom: {'live': true});
// ...
await call.stopLive();
await call.update(custom: {'live': false});

// Lobby: list live audio rooms
final result = await StreamVideo.instance.queryCalls(
  filterConditions: {'type': 'audio_room', 'live': true},
);
final rooms = result.getDataOrNull()?.calls ?? [];
```

Full screen blueprint (speakers grid, actions bar, host request cards):
[VIDEO-ADVANCED-FLUTTER-blueprints.md](VIDEO-ADVANCED-FLUTTER-blueprints.md) > Audio Room.

---

## Multiple Simultaneous Calls (multicall)

> **Docs:** [Multiple Active Calls](https://getstream.io/video/docs/flutter/advanced/multiple-active-calls/) · [Multicall cookbook](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/multicall/) · [Background Modes](https://getstream.io/video/docs/flutter/advanced/background-modes/)

By default the SDK keeps **one** active call: joining a second call makes the SDK leave
the first (`DisconnectReason.replaced`). Opt in to multicall:

```dart
StreamVideo(
  apiKey,
  user: user,
  userToken: token,
  options: StreamVideoOptions(
    allowMultipleActiveCalls: true,
    multiCallAudioPolicy: MultiCallAudioPolicy.suspendExisting, // default
  ),
);
```

### Audio policy

Two unsuspended calls contend for the mic/speaker, so the SDK hands audio focus off
per policy when calls join/leave:

| Policy                      | On joining a new call                     | On leaving a call                              |
| --------------------------- | ----------------------------------------- | ---------------------------------------------- |
| `suspendExisting` (default) | suspends audio of every other active call | resumes the most recently added remaining call |
| `suspendIncoming`           | the new call joins with audio suspended   | nothing auto-resumed - resume manually         |
| `manual`                    | nothing                                   | nothing - you own suspend/resume entirely      |

Manual focus switch between two joined calls:

```dart
Future<void> switchFocus({required Call from, required Call to}) async {
  await from.setMicrophoneEnabled(enabled: false);
  await from.setCameraEnabled(enabled: false);
  await from.suspendAudio(); // release mic/speaker
  await to.resumeAudio();    // reclaim + restore suspended track states
  await to.setMicrophoneEnabled(enabled: true);
  await to.setCameraEnabled(enabled: true);
}
```

### API differences under multicall

- `StreamVideo.instance.activeCall` **throws** when multicall is enabled - use
  `StreamVideo.instance.activeCalls` (a `List<Call>`) and `listenActiveCalls(callback)`.
- Each call owns an isolated native `PeerConnectionFactory` + audio device module
  (v1.4.0), which is what makes clean sibling-call audio possible.
- Per-call audio profiles: pass `DefaultCallPreferences(audioConfigurationPolicy: ...)`
  to `makeCall(preferences:)` - e.g. `viewer()` for a watched livestream and
  `broadcaster()` for a simultaneous 1:1 call.

### Multicall gotchas

- **Android foreground services:** with multicall, each call runs its own service. Pass
  the cid when stopping: `StreamVideoFlutterBackground.stopService(ServiceType.call, callCid: callCid)`.
- **`suspendIncoming` does not auto-resume:** after leaving the foreground call, call
  `resumeAudio()` on the surviving call yourself.
- **`dropIfAloneInRingingFlow` (default `true`):** a ringing 1:1 auto-ends when the local
  user is the last participant - detect via the call status turning disconnected.

### Sharing custom state across ALL participants

> **Docs:** [Custom Data](https://getstream.io/video/docs/flutter/advanced/custom-data/) · [Call Events: Custom event](https://getstream.io/video/docs/flutter/guides/call-events/#custom-event)

To sync app-specific state (badges, pairings, "raise hand", scores, "X is away") to every
client in a call, choose one of two mechanisms.

**Decision rule:** must a client that joins _later_ still see it?

- **Yes -> custom data** (`call.update(custom:)`). Durable; stored on the call, re-syncs via `CallState` on join.
- **No -> custom event** (`call.sendCustomEvent`). Ephemeral broadcast; only clients connected at send time receive it.

Both carry a `Map<String, Object>` payload. Custom data also attaches to other models
(user via `User.regular(extraData: ...)`, reactions via `call.sendReaction(custom: ...)`);
for shared call state, write it on the call.

#### Option A - Custom data (durable)

Contract:

- `CallState.custom` is `Map<String, Object>` (never null - defaults to `{}`).
- `call.update(custom:)` **replaces the entire map**, so always read-merge-write.
- Requires the **`update-call`** capability. `default` call type grants it to `user`;
  restrictive types (`audio_room`, `livestream`) may not - grant it in the dashboard, or
  route writes through the call creator/host.

```dart
// WRITE: read-merge-write (update() replaces the whole map). Remove the key on hang-up.
final pairs = Map<String, Object>.from(
  (mainCall.state.value.custom['audioPairs'] as Map?) ?? {});
pairs[sideCall.id] = [selfId, partnerId];
await mainCall.update(custom: {'audioPairs': pairs});

// READ reactively on every client (custom rides on the same CallState):
StreamBuilder<CallState>(
  stream: mainCall.state.asStream(),
  initialData: mainCall.state.value,
  builder: (context, snap) {
    final pairs = snap.requireData.custom['audioPairs'] as Map? ?? {};
    return /* render badges - sort keys for stable colors/labels across clients */;
  },
);

// READ once, before joining (no live CallState yet):
final custom = (await mainCall.get()).getDataOrNull()?.metadata.details.custom;
```

#### Option B - Custom event (ephemeral)

```dart
// SEND a one-off signal to everyone currently connected:
await call.sendCustomEvent(
  eventType: 'raise-hand',
  custom: {'userId': selfId},
);

// RECEIVE on every other client:
call.callEvents.on<StreamCallCustomEvent>((event) {
  if (event.eventType == 'raise-hand') {
    final userId = event.custom['userId'];
    // show a transient indicator
  }
});
```

Not persisted - late joiners never replay it. If a late joiner must know the resulting
state, also mirror it into custom data (Option A).

Use case blueprint - host accepts a 1:1 call in a floating window while livestreaming:
[VIDEO-ADVANCED-FLUTTER-blueprints.md](VIDEO-ADVANCED-FLUTTER-blueprints.md) > Floating Call Panel.

---

## Chat + Video in One App

> **Docs:** [Chat with Video](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/chat-with-video/)

Stream Chat and Stream Video share one project: **same API key, same user JWT**. Each SDK
has its own client and its own `User` type - alias the imports.

```dart
import 'package:stream_chat_flutter/stream_chat_flutter.dart' as chat;
import 'package:stream_video_flutter/stream_video_flutter.dart' as video;

// One app user -> two SDK users
chat.User toChatUser() => chat.User(id: id, name: name, image: image);
video.User toVideoUser() =>
    video.User(info: video.UserInfo(id: id, name: name, image: image));
```

- `StreamChatClient` is created at app launch and provided via the `StreamChat` inherited
  widget (`StreamChat.of(context).client`).
- `StreamVideo(...)` registers its own singleton (`StreamVideo.instance`) - typically
  created at login with the same token.
- Disconnect both at logout: `chatClient.disconnectUser()` +
  `StreamVideo.reset(disconnect: true)` (guard with `StreamVideo.isInitialized()`).

### Conventions that tie the products together

- **Call id derived from channel id:** `'${channel.id}_call${Random().nextInt(10000)}'` -
  unique per call, traceable to the conversation.
- **Announce a call in the channel** with a custom `Attachment`
  (`extraData: {'callId': ..., 'callType': ...}`) and render a join card with a
  `StreamAttachmentWidgetBuilder`. Reconstruct with
  `StreamCallType.fromString(callType)`.
- **Chat channel per call:** for in-call chat, use channel type `'livestream'` (open
  posting) with **id == `call.id`** - both sides land in the same conversation without
  extra bookkeeping.
- **Ringing variant:** instead of an attachment, collect channel members and
  `call.getOrCreate(memberIds: members, ringing: true, video: true)` - members get
  push/CallKit via `stream_video_push_notification`.

Blueprints (dual init, start-call-from-channel, attachment join card, in-call chat
overlay): [VIDEO-ADVANCED-FLUTTER-blueprints.md](VIDEO-ADVANCED-FLUTTER-blueprints.md) > Chat with Video.

---

## Querying Calls and Members

> **Docs:** [Querying Calls](https://getstream.io/video/docs/flutter/guides/querying-calls/) · [Query Call Members](https://getstream.io/video/docs/flutter/guides/query-call-members/)

```dart
// Calls - filterConditions is required (pass {} for all)
final result = await StreamVideo.instance.queryCalls(
  filterConditions: {'type': 'livestream', 'backstage': false},
  sorts: [SortParamRequest(field: 'starts_at', direction: -1)],
  limit: 25,
  watch: true, // keep results updated via client events
);
final calls = result.getDataOrNull()?.calls ?? [];
```

Filterable fields: `type`, `id`, `cid`, `created_by_user_id`, `created_at`, `updated_at`,
`starts_at`, `ended_at`, `backstage`, `members`, `custom.<field>`.
Sortable: `starts_at`, `created_at`, `updated_at`, `ended_at`, `type`, `id`, `cid`.

```dart
// Members - join()/getOrCreate() return at most 100 members (membersLimit caps at 100).
// Use the paginated query for more:
final page = await call.queryMembers(
  filterConditions: {'role': {'eq': 'admin'}},
  sorts: [SortParamRequest(field: 'user_id', direction: 1)],
  limit: 10,
);
final next = page.getDataOrNull()?.next; // pass as next: for the following page
```

---

## Permissions and Moderation

> **Docs:** [Permissions & Moderation](https://getstream.io/video/docs/flutter/guides/permissions-and-moderation/) · [Call Moderation cookbook](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/call-moderation/)

All return `Future<Result<None>>` - check the result, do not fire-and-forget.

```dart
bool ok = call.hasPermission(CallPermission.sendAudio);
await call.requestPermissions([CallPermission.sendAudio]);
await call.grantPermissions(userId: 'alice', permissions: [CallPermission.sendAudio]);
await call.revokePermissions(userId: 'alice', permissions: [CallPermission.sendAudio]);

await call.muteUsers(userIds: ['alice']);     // audio by default (TrackType.audio)
await call.muteOthers();                       // everyone except yourself
await call.muteAllUsers();                     // EVERYONE including yourself, all tracks
await call.blockUser('alice');
await call.unblockUser('alice');
await call.kickUser('alice', block: true);     // remove + block
await call.end();                              // terminate for everyone
```

Host-side permission requests arrive via the `onPermissionRequest` callback (see Audio
Rooms above). Gotcha: use `muteOthers()` for the common "mute everyone else" action -
`muteAllUsers()` includes the caller and defaults to all tracks.

---

## Call Events and Custom Events

> **Docs:** [Call Events](https://getstream.io/video/docs/flutter/guides/call-events/) · [Custom Data](https://getstream.io/video/docs/flutter/advanced/custom-data/)

`call.callEvents` is the per-call typed event stream (distinct from the client-level
`StreamVideo.instance.events`):

```dart
final sub = call.callEvents.on<StreamCallSessionParticipantCountUpdatedEvent>((event) {
  // live participant counts without diffing call state
});
// later: sub.cancel();

// App-level realtime signaling between participants:
await call.sendCustomEvent(eventType: 'poll-started', custom: {'pollId': '42'});
call.callEvents.on<StreamCallCustomEvent>((event) {
  final data = event.custom;
});
```

Event families available on `callEvents`: lifecycle (`StreamCallCreatedEvent`,
`StreamCallEndedEvent`, `StreamCallLiveStartedEvent`), participants
(`StreamCallParticipantJoinedEvent` / `LeftEvent`, dominant speaker), quality
(connection quality, audio levels), permissions (request / updated), ringing, recording,
broadcasting (`StreamCallBroadcastingStartedEvent` with `hlsPlaylistUrl`), transcription,
closed captions, session counts, reactions, mutes, blocks, and `StreamCallCustomEvent`.

---

## Call Preferences (per-call tuning)

> **Docs:** [Call Preferences](https://getstream.io/video/docs/flutter/advanced/call-preferences/)

Pass at creation or update mid-call:

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.defaultType(),
  id: 'my-call-id',
  preferences: DefaultCallPreferences(
    connectTimeout: const Duration(seconds: 30),
    reactionAutoDismissTime: const Duration(seconds: 3),
    dropIfAloneInRingingFlow: false,
    closedCaptionsVisibleCaptions: 3,
  ),
);
call.updateCallPreferences(
  DefaultCallPreferences(reactionAutoDismissTime: const Duration(seconds: 10)),
);
```

Verified defaults (v1.4.0): `connectTimeout` 60 s; `reconnectTimeout` `Duration.zero`
(retry indefinitely); `networkAvailabilityTimeout` 5 min. Other knobs:
`callStatsReportingInterval`, `closedCaptionsVisibilityDurationMs`,
`audioConfigurationPolicy` (per-call override), `clientPublishOptions` (codec/bitrate -
leave alone unless you know exactly why).

---

## Session Timers (max call duration)

> **Docs:** [Session Timers](https://getstream.io/video/docs/flutter/advanced/session-timers/)

```dart
final createResult = await call.getOrCreate(
  limits: const StreamLimitsSettings(maxDurationSeconds: 3600),
);
await createResult.fold(
  success: (_) async {
    final joinResult = await call.join();
    joinResult.fold(
      success: (_) {/* connected */},
      failure: (failure) {
        debugPrint('join failed: ${failure.error.message}');
      },
    );
  },
  failure: (failure) {
    debugPrint('getOrCreate failed: ${failure.error.message}');
  },
);

final endsAt = call.state.value.timerEndsAt; // DateTime? - drives a countdown UI

// Extend mid-call (fires call.updated for everyone):
await call.update(
  limits: StreamLimitsSettings(
    maxDurationSeconds:
        call.state.value.settings.limits.maxDurationSeconds! + 600,
  ),
);
```

When the timer expires the call ends automatically for all participants.

---

## Network Handling and Quality

> **Docs:** [Network Disruptions](https://getstream.io/video/docs/flutter/advanced/network-disruptions/)

### Reconnection status UI

Reconnection is automatic; surface it from the call status:

```dart
call.partialState((s) => s.status).listen((status) {
  if (status is CallStatusReconnecting) { /* show banner */ }
  if (status is CallStatusReconnectionFailed) { /* offer rejoin/leave */ }
});
```

Timeouts are tuned via `DefaultCallPreferences` (see Call Preferences).

### Low bandwidth - subscriber video pause

On poor networks the SFU pauses incoming video (on by default). Pre-built widgets show an
avatar placeholder + `Icons.network_check` automatically. To opt out, do it **before**
`join()`:

```dart
call.disableClientCapabilities([SfuClientCapability.subscriberVideoPause]);
```

Detect paused tracks in custom UI: `participant.isTrackPaused(SfuTrackType.video)` /
`participant.pausedTracks`.

### Manual incoming video quality (data saver)

```dart
// Cap one participant's incoming resolution (sessionId from CallParticipantState):
await call.setPreferredIncomingVideoResolution(
  VideoDimension(width: 640, height: 480),
  sessionIds: [participant.sessionId],
);
await call.setPreferredIncomingVideoResolution(null); // clear all
await call.setIncomingVideoEnabled(false);            // audio-only mode
```

Gotcha: setting a resolution re-enables previously disabled incoming video;
`setIncomingVideoEnabled(false)` clears resolution preferences.

### Connection quality indicator

`participant.connectionQuality` -> `SfuConnectionQuality { unspecified, poor, good,
excellent }`; render with the pre-built `StreamConnectionQualityIndicator`.

---

## User Feedback (call rating)

```dart
await call.collectUserFeedback(
  rating: 4,                       // 1-5; anything else throws ArgumentError
  reason: 'choppy audio',
  custom: {'screen': 'call_end'},
);
```

Must run while the call session still exists - collect on the call screen (e.g. from a
dialog at hang-up) rather than after teardown. Ratings appear in dashboard call stats.

---

## More advanced surface (entry points)

- **Screenshots:** `final bytes = await call.takeScreenshot(participant, trackType: SfuTrackType.screenShare);`
  returns `ByteBuffer?` - await it and null-check.
- **Participant sorting:** built-in comparators (`dominantSpeaker`, `speaking`,
  `screenSharing`, `pinned`, `byRole(...)`) and presets
  (`CallParticipantSortingPresets.regular / .speaker / .livestreamOrAudioRoom`); pass a
  custom `Comparator<CallParticipantState>` to participant widgets.
- **Deep linking ("join via link"):** platform config (App Links `assetlinks.json` /
  Universal Links AASA) + a URI listener; SDK side is just `makeCall` -> `getOrCreate` ->
  `join` with the parsed id. Handle both cold start (`getInitialUri`) and warm
  (`uriLinkStream`), and wait for login before joining.
- **RTMP ingest (OBS -> call):** `call.state.value.rtmpIngress` is the server URL; the
  OBS publisher joins as a real participant - use a dedicated user for it.
- **Video compositing (burned-in overlays):** register a native video filter
  (`BitmapVideoFilter` on Android / `VideoFilter` on iOS via
  `ProcessorProvider.addProcessor`) and apply it with `stream_video_filters`'
  `StreamVideoEffectsManager.applyCustomEffect(...)`; push overlay state from Flutter over
  a `MethodChannel`. The overlay is encoded into the outgoing track, so it reaches local
  preview, all viewers, and HLS/RTMP egress. Join with mirroring off so the overlay is not
  flipped. Runnable example: `flutter-video-samples/packages/video_livestream_overlay`.

---

## Gotchas

- **Audio rooms: deny is not revoke.** Dismissing a speak request in the UI does nothing
  server-side; call `revokePermissions` to actively remove a granted capability.
- **The `'live'` query flag is app-managed.** The SDK's source of truth is
  `state.isBackstage`; keep the custom flag in sync on every goLive/stopLive if you use
  it for lobby queries.
- **Multicall changes the client API surface:** `activeCall`/`listenActiveCall` throw -
  use `activeCalls`/`listenActiveCalls`.
- **`muteAllUsers()` mutes you too.** Use `muteOthers()` for the host "mute everyone"
  button.
- **Client capability changes apply at join.** `disableClientCapabilities` after `join()`
  only takes effect on the next join/reconnect.
- **`collectUserFeedback` needs a live session.** Calling it after teardown throws.
- **One token, two SDKs.** Chat and Video accept the same user JWT - do not mint separate
  tokens per product.
- **`queryCalls` results are snapshots** unless `watch: true`; with watch on, observe
  updates via client events.
- **Moderation calls return `Result`** - surface failures (mostly missing capabilities)
  instead of assuming success.
