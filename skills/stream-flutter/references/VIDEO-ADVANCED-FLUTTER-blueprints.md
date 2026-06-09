# Video Advanced - Use Case Blueprints

Load only the section you are implementing. For the SDK patterns behind these blueprints,
see [VIDEO-ADVANCED-FLUTTER.md](VIDEO-ADVANCED-FLUTTER.md). For client initialization and
call basics, see [VIDEO-FLUTTER.md](VIDEO-FLUTTER.md) /
[VIDEO-FLUTTER-blueprints.md](VIDEO-FLUTTER-blueprints.md); for livestream host/viewer
basics, see [LIVESTREAM-FLUTTER-blueprints.md](LIVESTREAM-FLUTTER-blueprints.md).

---

## Audio Room Screen Blueprint

> **Docs:** [Audio Room with Chat](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/audio-room-with-chat/) · [Permissions & Moderation](https://getstream.io/video/docs/flutter/guides/permissions-and-moderation/)

Join in `initState`, render all participants in a grid with a speaking highlight, and
wire the mic button through the permission loop. The host additionally surfaces incoming
speak requests.

```dart
// audio_room_screen.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

class AudioRoomScreen extends StatefulWidget {
  const AudioRoomScreen({super.key, required this.call, required this.isHost});

  final Call call;
  final bool isHost;

  @override
  State<AudioRoomScreen> createState() => _AudioRoomScreenState();
}

class _AudioRoomScreenState extends State<AudioRoomScreen> {
  final _speakRequests = <StreamCallPermissionRequestEvent>[];

  @override
  void initState() {
    super.initState();
    _join();
    if (widget.isHost) {
      // Host: collect incoming speak requests
      widget.call.onPermissionRequest = (request) {
        setState(() => _speakRequests.add(request));
      };
    }
  }

  Future<void> _join() async {
    // CallConnectOptions defaults camera AND mic to disabled - correct for audio rooms
    final result = await widget.call.join();
    result.fold(
      success: (_) async {
        if (widget.isHost) {
          await widget.call.goLive();
          await widget.call.update(custom: {'live': true});
        }
      },
      failure: (error) => debugPrint('Join failed: $error'),
    );
  }

  Future<void> _grant(StreamCallPermissionRequestEvent request) async {
    await widget.call.grantPermissions(
      userId: request.user.id,
      permissions: request.permissions.toList(),
    );
    setState(() => _speakRequests.remove(request));
  }

  @override
  void dispose() {
    widget.call.leave();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Audio Room')),
      body: Column(
        children: [
          if (widget.isHost && _speakRequests.isNotEmpty)
            _SpeakRequestCard(
              request: _speakRequests.first,
              onAllow: () => _grant(_speakRequests.first),
              onDeny: () =>
                  setState(() => _speakRequests.removeAt(0)), // local dismiss only
            ),
          Expanded(
            child: StreamBuilder<CallState>(
              stream: widget.call.state.asStream(),
              initialData: widget.call.state.value,
              builder: (context, snapshot) {
                final participants = snapshot.requireData.callParticipants;
                return GridView.builder(
                  padding: const EdgeInsets.all(16),
                  gridDelegate:
                      const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3,
                  ),
                  itemCount: participants.length,
                  itemBuilder: (context, index) =>
                      _ParticipantAvatar(participant: participants[index]),
                );
              },
            ),
          ),
          _AudioRoomActions(call: widget.call),
        ],
      ),
    );
  }
}

class _ParticipantAvatar extends StatelessWidget {
  const _ParticipantAvatar({required this.participant});

  final CallParticipantState participant;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.all(3),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: participant.isSpeaking ? Colors.green : Colors.white24,
              width: 2,
            ),
          ),
          child: CircleAvatar(
            radius: 32,
            backgroundImage: participant.image != null
                ? NetworkImage(participant.image!)
                : null,
            child: participant.image == null
                ? Text(participant.name.isNotEmpty ? participant.name[0] : '?')
                : null,
          ),
        ),
        const SizedBox(height: 4),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(participant.name,
                style: const TextStyle(fontSize: 12),
                overflow: TextOverflow.ellipsis),
            if (!participant.isAudioEnabled) ...[
              const SizedBox(width: 2),
              const Icon(Icons.mic_off, size: 12),
            ],
          ],
        ),
      ],
    );
  }
}

class _AudioRoomActions extends StatefulWidget {
  const _AudioRoomActions({required this.call});

  final Call call;

  @override
  State<_AudioRoomActions> createState() => _AudioRoomActionsState();
}

class _AudioRoomActionsState extends State<_AudioRoomActions> {
  bool _waitingForGrant = false;

  @override
  void initState() {
    super.initState();
    // Enable the mic automatically when the host grants sendAudio
    widget.call.callEvents.on<StreamCallPermissionsUpdatedEvent>((event) {
      if (event.user.id == StreamVideo.instance.currentUser.id &&
          event.ownCapabilities.contains(CallPermission.sendAudio) &&
          _waitingForGrant) {
        setState(() => _waitingForGrant = false);
        widget.call.setMicrophoneEnabled(enabled: true);
      }
    });
  }

  Future<void> _onMicPressed(bool micOn) async {
    if (micOn) {
      await widget.call.setMicrophoneEnabled(enabled: false);
      return;
    }
    if (widget.call.hasPermission(CallPermission.sendAudio)) {
      await widget.call.setMicrophoneEnabled(enabled: true);
    } else {
      setState(() => _waitingForGrant = true);
      await widget.call.requestPermissions([CallPermission.sendAudio]);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Asked to speak - waiting for host')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return PartialCallStateBuilder<bool>(
      call: widget.call,
      selector: (state) => state.localParticipant?.isAudioEnabled ?? false,
      builder: (context, micOn) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              IconButton.filled(
                icon: Icon(micOn ? Icons.mic : Icons.mic_off),
                onPressed: _waitingForGrant ? null : () => _onMicPressed(micOn),
              ),
              IconButton.filled(
                icon: const Icon(Icons.call_end),
                style: IconButton.styleFrom(backgroundColor: Colors.red),
                onPressed: () async {
                  await widget.call.leave();
                  if (context.mounted) Navigator.of(context).pop();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SpeakRequestCard extends StatelessWidget {
  const _SpeakRequestCard({
    required this.request,
    required this.onAllow,
    required this.onDeny,
  });

  final StreamCallPermissionRequestEvent request;
  final VoidCallback onAllow;
  final VoidCallback onDeny;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(12),
      child: ListTile(
        title: Text('${request.user.name} wants to speak'),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextButton(onPressed: onDeny, child: const Text('Deny')),
            FilledButton(onPressed: onAllow, child: const Text('Allow')),
          ],
        ),
      ),
    );
  }
}
```

**Wiring:**

- Bare `join()` is correct for audio rooms - camera and mic default to disabled
- The host pairs `goLive()`/`stopLive()` with `call.update(custom: {'live': ...})` so
  lobby screens can `queryCalls(filterConditions: {'type': 'audio_room', 'live': true})`
- "Deny" only dismisses the local card; call `revokePermissions` to enforce server-side
- `onPermissionRequest` is a settable callback on `Call`; grant confirmations arrive as
  `StreamCallPermissionsUpdatedEvent` on `call.callEvents`
- The speaking highlight needs no extra subscription - `isSpeaking` updates with call state

---

## Livestream Feed Blueprint (TikTok-style vertical pager)

> **Docs:** [Livestream Feed](https://getstream.io/video/docs/flutter/ui-cookbook/livestreaming/livestream-feed/)

One call is joined at a time. A `CallManager` owns join/leave with a **version counter**
("latest request wins"): every swipe bumps the version, and any in-flight older join
aborts itself after each `await`. The old call's `leave()` is intentionally **not
awaited** so swipes stay smooth.

```dart
// call_manager.dart
import 'package:flutter/foundation.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

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

    final version = ++_version;
    final oldCall = _currentCall;
    _currentCall = null;
    _currentCallId = callId;
    _state = CallManagerState.connecting;
    _safeNotify();

    oldCall?.leave(); // NOT awaited - teardown overlaps with the next connect
    _connectCall(callId, version);
  }

  Future<void> _connectCall(String callId, int version) async {
    final call = StreamVideo.instance.makeCall(
      callType: StreamCallType.liveStream(),
      id: callId,
    );
    _currentCall = call;
    try {
      final getResult = await call.getOrCreate();
      if (_isStale(version, call)) return;
      if (getResult.isFailure) return _fail(version);

      final joinResult = await call.join(
        connectOptions: CallConnectOptions(
          camera: TrackOption.disabled(),
          microphone: TrackOption.disabled(),
        ),
      );
      if (_isStale(version, call)) return;
      if (joinResult.isFailure) return _fail(version);
    } catch (_) {
      if (_isStale(version, call)) return;
      return _fail(version);
    }
    _state = CallManagerState.connected;
    _safeNotify();
  }

  // A newer switch happened (or we were disposed): leave this stale call and bail.
  bool _isStale(int version, Call call) {
    if (version != _version || _disposed) {
      call.leave();
      return true;
    }
    return false;
  }

  void _fail(int version) {
    if (version == _version && !_disposed) {
      _state = CallManagerState.failure;
      _safeNotify();
    }
  }

  void _safeNotify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _version++; // invalidate any in-flight connect
    _currentCall?.leave();
    super.dispose();
  }
}
```

```dart
// feed_screen.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

import 'call_manager.dart';

// Replace with queryCalls or your backend in production.
const channels = ['feed-gaming', 'feed-music', 'feed-sports'];

class FeedScreen extends StatefulWidget {
  const FeedScreen({super.key});

  @override
  State<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends State<FeedScreen> {
  final _callManager = CallManager();
  final _pageController = PageController();

  @override
  void initState() {
    super.initState();
    _callManager.switchToCall(channels.first);
  }

  @override
  void dispose() {
    _callManager.dispose();
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: PageView.builder(
        controller: _pageController,
        scrollDirection: Axis.vertical,
        itemCount: channels.length,
        onPageChanged: (index) => _callManager.switchToCall(channels[index]),
        itemBuilder: (context, index) => _LivestreamPage(
          channelId: channels[index],
          callManager: _callManager,
        ),
      ),
    );
  }
}

class _LivestreamPage extends StatelessWidget {
  const _LivestreamPage({required this.channelId, required this.callManager});

  final String channelId;
  final CallManager callManager;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: callManager,
      builder: (context, _) {
        final isActive = callManager.currentCallId == channelId;
        final call = callManager.currentCall;

        if (isActive &&
            callManager.state == CallManagerState.connected &&
            call != null) {
          return _ActiveVideo(call: call);
        }
        if (isActive && callManager.state == CallManagerState.connecting) {
          return const Center(
            child: CircularProgressIndicator(color: Colors.white),
          );
        }
        return const Center(
          child: Text('No one is live',
              style: TextStyle(color: Colors.white54)),
        );
      },
    );
  }
}

class _ActiveVideo extends StatelessWidget {
  const _ActiveVideo({required this.call});

  final Call call;

  @override
  Widget build(BuildContext context) {
    return PartialCallStateBuilder<bool>(
      call: call,
      selector: (state) =>
          state.otherParticipants.any((p) => p.isVideoEnabled),
      builder: (context, hasLiveHost) => hasLiveHost
          // onCallDisconnected MUST be a no-op here: the default pops the route,
          // which would dismiss the whole feed. The CallManager owns leave().
          ? LivestreamPlayer(call: call, onCallDisconnected: (_) {})
          : const Center(
              child: Text('No one is live',
                  style: TextStyle(color: Colors.white54)),
            ),
    );
  }
}
```

**Wiring:**

- The **version guard after every `await`** is the core of the pattern - without it a
  slow earlier join can finish after a newer swipe and clobber the state
- With the default `allowMultipleActiveCalls: false`, the SDK also auto-leaves the prior
  call when the new `join()` lands; the explicit unawaited `leave()` just stops the old
  media sooner
- `LivestreamPlayer` auto-joins (`autoJoinAsap`) - safe next to the manager's `join()`
  because `join()` is idempotent for an already-connected call; use
  `joinBehaviour: LivestreamJoinBehaviour.manualJoin` to fully own join timing
- Viewer joins with camera/mic disabled - never publish from a feed viewer
- "Live" is derived (`otherParticipants.any((p) => p.isVideoEnabled)`); prefer
  `roles.contains('host')` filtering if your call type configures roles
- Host side is a standard livestream host (see LIVESTREAM-FLUTTER-blueprints.md) using
  the channel id as the call id

---

## Floating Call Panel Blueprint (1:1 call over a livestream, multicall)

> **Docs:** [Multicall cookbook](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/multicall/) · [Multiple Active Calls](https://getstream.io/video/docs/flutter/advanced/multiple-active-calls/)

The host livestreams; a viewer rings them; the host accepts into a small floating window
while the broadcast stays connected (video paused), then everything resumes when the call
ends. Requires `StreamVideoOptions(allowMultipleActiveCalls: true)` (default
`suspendExisting` policy handles audio focus automatically).

```dart
// host_livestream_screen.dart (essentials)
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

class HostLivestreamScreenState extends State<HostLivestreamScreen> {
  late final Call _livestreamCall = widget.livestreamCall;
  Call? _secondaryCall;
  Call? _incomingCall;
  StreamSubscription<Call?>? _incomingSub;
  StreamSubscription<CallState>? _secondaryStateSub;

  @override
  void initState() {
    super.initState();
    // Foreground-only incoming call detection; add push for background delivery.
    _incomingSub = StreamVideo.instance.state.incomingCall.listen((call) {
      if (call == null) return;
      if (call.callCid == _livestreamCall.callCid) return; // ignore own stream
      if (_secondaryCall != null) return;                  // already in a call
      setState(() => _incomingCall = call);
    });
  }

  Future<void> _acceptIncoming(Call call) async {
    setState(() => _incomingCall = null);

    // Pause the broadcast visually: viewers see a "host is away" placeholder.
    // The livestream call stays joined - only mic/cam are turned off.
    await _livestreamCall.setMicrophoneEnabled(enabled: false);
    await _livestreamCall.setCameraEnabled(enabled: false);

    await call.accept();
    final result = await call.join(
      connectOptions: CallConnectOptions(
        camera: TrackOption.enabled(),
        microphone: TrackOption.enabled(),
      ),
    );
    // Under suspendExisting, joining the 1:1 auto-suspends the livestream's audio.
    result.fold(
      success: (_) {
        setState(() => _secondaryCall = call);
        // Resume the broadcast when the 1:1 ends (either side hangs up).
        _secondaryStateSub = call.state.valueStream.listen((state) {
          final ended =
              state.status.isDisconnected || state.endedAt != null;
          if (ended) _endSecondaryCall();
        });
      },
      failure: (_) => _resumeLivestream(),
    );
  }

  Future<void> _endSecondaryCall() async {
    _secondaryStateSub?.cancel();
    _secondaryStateSub = null;
    final call = _secondaryCall;
    setState(() => _secondaryCall = null);
    await call?.leave(); // suspendExisting auto-resumes the livestream's audio
    await _resumeLivestream();
  }

  Future<void> _resumeLivestream() async {
    await _livestreamCall.setMicrophoneEnabled(enabled: true);
    await _livestreamCall.setCameraEnabled(enabled: true);
  }

  @override
  void dispose() {
    _incomingSub?.cancel();
    _secondaryStateSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(child: widget.broadcastView), // host StreamCallContent
        if (_secondaryCall != null)
          Positioned(
            top: MediaQuery.paddingOf(context).top + 80,
            right: 16,
            child: _FloatingCallPanel(
              call: _secondaryCall!,
              onHangUp: _endSecondaryCall,
            ),
          ),
        if (_incomingCall != null)
          _IncomingCallSheet(
            call: _incomingCall!,
            onAccept: () => _acceptIncoming(_incomingCall!),
            onDecline: () {
              _incomingCall!.reject();
              setState(() => _incomingCall = null);
            },
          ),
      ],
    );
  }
}

class _FloatingCallPanel extends StatelessWidget {
  const _FloatingCallPanel({required this.call, required this.onHangUp});

  final Call call;
  final VoidCallback onHangUp;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 160,
      height: 220,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: Stack(
          children: [
            Positioned.fill(
              child: StreamCallParticipants(
                call: call,
                layoutMode: ParticipantLayoutMode.grid,
              ),
            ),
            Positioned(
              bottom: 6,
              left: 0,
              right: 0,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  ToggleMicrophoneOption(call: call),
                  IconButton.filled(
                    icon: const Icon(Icons.call_end, size: 18),
                    style: IconButton.styleFrom(backgroundColor: Colors.red),
                    onPressed: onHangUp,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

Viewer side rings the host with a unique call id and per-call audio profile:

```dart
final call = StreamVideo.instance.makeCall(
  callType: StreamCallType.defaultType(),
  id: 'viewer-host-${DateTime.now().microsecondsSinceEpoch}',
  preferences: DefaultCallPreferences(
    audioConfigurationPolicy: AudioConfigurationPolicy.broadcaster(),
  ),
);
await call.getOrCreate(memberIds: [hostUserId], ringing: true, video: true);
await call.join(
  connectOptions: CallConnectOptions(
    camera: TrackOption.enabled(),
    microphone: TrackOption.enabled(),
  ),
);
// Detect acceptance: watch call state for the host appearing in otherParticipants.
```

**Wiring:**

- `StreamVideo.instance.state.incomingCall` only fires while the app is foregrounded -
  wire `stream_video_push_notification` for background ringing
- The livestream is never left during the 1:1 - mic/cam off + SDK audio suspension only
- The `default` call type must have ringing enabled in the dashboard
- `dropIfAloneInRingingFlow` (default true) auto-ends the viewer's outgoing call if the
  host never joins - the viewer detects this via `status.isDisconnected`

---

## Chat with Video Blueprints

> **Docs:** [Chat with Video](https://getstream.io/video/docs/flutter/ui-cookbook/utilities/chat-with-video/)

### Dual client init and login

```dart
// main.dart
final chatClient = StreamChatClient(apiKey, logLevel: Level.INFO);
runApp(MaterialApp(
  builder: (context, child) => StreamChat(client: chatClient, child: child!),
  home: const LoginScreen(),
));

// On login - same API key, SAME token for both products:
await StreamChat.of(context).client.connectUser(
  chat.User(id: user.id, name: user.name, image: user.image),
  user.token,
);
StreamVideo(
  apiKey,
  user: video.User(info: video.UserInfo(id: user.id, name: user.name, image: user.image)),
  userToken: user.token,
);

// On logout (unmount chat/video UI first):
await StreamChat.of(context).client.disconnectUser();
if (StreamVideo.isInitialized()) await StreamVideo.reset(disconnect: true);
```

### Start a call from a channel and announce it

```dart
Future<void> startCallFromChannel(BuildContext context) async {
  final channel = StreamChannel.of(context).channel;
  final currentUser = StreamChat.of(context).currentUser;

  final call = StreamVideo.instance.makeCall(
    callType: StreamCallType.defaultType(),
    id: '${channel.id}_call${Random().nextInt(10000)}', // unique per call
  );
  await call.getOrCreate();
  // Ringing variant: collect channel member ids (minus self) and use
  // getOrCreate(memberIds: members, ringing: true, video: true) instead.

  // Announce with a custom attachment the message list can render as a join card
  channel.sendMessage(Message(attachments: [
    Attachment(
      type: 'custom',
      authorName: currentUser?.name ?? '',
      uploadState: const UploadState.success(),
      extraData: {'callId': call.id, 'callType': call.type.toString()},
    ),
  ]));
}
```

### Attachment join card (StreamAttachmentWidgetBuilder)

```dart
class CallAttachmentWidgetBuilder extends StreamAttachmentWidgetBuilder {
  @override
  bool canHandle(Message message, Map<String, List<Attachment>> attachments) {
    final custom = attachments['custom'];
    return custom != null &&
        custom.length == 1 &&
        custom.first.extraData['callId'] != null &&
        custom.first.extraData['callType'] != null;
  }

  @override
  Widget build(BuildContext context, Message message,
      Map<String, List<Attachment>> attachments) {
    final attachment = attachments['custom']!.first;
    final callId = attachment.extraData['callId'] as String;
    final callType = attachment.extraData['callType'] as String;

    return Card(
      child: ListTile(
        leading: const Icon(Icons.videocam_rounded),
        title: const Text('Video call'),
        trailing: FilledButton(
          child: const Text('Join'),
          onPressed: () {
            final call = StreamVideo.instance.makeCall(
              callType: StreamCallType.fromString(callType),
              id: callId,
            );
            Navigator.of(context).push(MaterialPageRoute(
              fullscreenDialog: true,
              builder: (_) => Scaffold(body: StreamCallContainer(call: call)),
            ));
          },
        ),
      ),
    );
  }
}

// Wire into the message list - custom builder FIRST, then the defaults:
StreamMessageListView(
  messageBuilder: (context, details, messages, defaultMessage) =>
      defaultMessage.copyWith(attachmentBuilders: [
    CallAttachmentWidgetBuilder(),
    ...StreamAttachmentWidgetBuilder.defaultBuilders(
        message: defaultMessage.message),
  ]),
)
```

### In-call chat overlay (chat channel per call)

```dart
// In the call screen: a chat channel whose id IS the call id.
// Channel type 'livestream' allows all users to post by default.
final channel = StreamChat.of(context).client.channel(
  'livestream',
  id: call.id,
);
await channel.watch();

// Render as a toggleable panel stacked over StreamCallContainer:
SizedBox(
  height: 300,
  child: StreamChannel(
    channel: channel,
    child: const Column(
      children: [
        Expanded(child: StreamMessageListView()),
        StreamMessageInput(),
      ],
    ),
  ),
)

// dispose(): channel.stopWatching();
```

**Wiring:**

- Alias the imports (`as chat` / `as video`) - both SDKs declare a `User` type
- One JWT works for both products; never mint separate tokens
- `StreamCallType.fromString(...)` reconstructs the type from the attachment payload
- The `'livestream'` channel type is chosen for open posting permissions, not because the
  call is a livestream; other channel types need dashboard permission changes
- `StreamChatClient` lives in the widget tree (`StreamChat.of(context)`); `StreamVideo`
  is a singleton - do not wrap it in a provider
