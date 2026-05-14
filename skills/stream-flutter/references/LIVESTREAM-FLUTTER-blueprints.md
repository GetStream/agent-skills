# Livestream Flutter - Widget Blueprints

Load only the section you are implementing. For SDK setup, call type details, and gotchas, see [LIVESTREAM-FLUTTER.md](LIVESTREAM-FLUTTER.md). For standard call initialization patterns, see [VIDEO-FLUTTER-blueprints.md](VIDEO-FLUTTER-blueprints.md).

---

## App Entry Point Blueprint

Use the same initialization pattern as a standard video app. The `livestream` call type does not require a different client setup.

```dart
// main.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  StreamVideo(
    'your_api_key',
    user: User.regular(
      userId: 'your-user-id',
      name: 'Your Name',
    ),
    userToken: UserToken.jwt('your_user_token'),
  );

  runApp(const LivestreamApp());
}

class LivestreamApp extends StatelessWidget {
  const LivestreamApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Livestream',
      home: const LivestreamModeSelectionPage(),
    );
  }
}
```

---

## Mode Selection Page Blueprint

Lets the user enter a stream ID and choose between hosting (creator) or watching (viewer).

> **Do NOT use `StreamCallContainer` for livestreaming.** `StreamCallContainer` is designed for standard calls and will render a participant grid that replaces your custom host/viewer UI. Livestream pages manage their own layout entirely.

```dart
// livestream_mode_selection_page.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

import 'creator_livestream_page.dart';
import 'viewer_livestream_page.dart';

class LivestreamModeSelectionPage extends StatefulWidget {
  const LivestreamModeSelectionPage({super.key});

  @override
  State<LivestreamModeSelectionPage> createState() =>
      _LivestreamModeSelectionPageState();
}

class _LivestreamModeSelectionPageState
    extends State<LivestreamModeSelectionPage> {
  final _callIdController = TextEditingController();

  @override
  void dispose() {
    _callIdController.dispose();
    super.dispose();
  }

  void _navigateTo(Widget page) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => page));
  }

  @override
  Widget build(BuildContext context) {
    final callId = _callIdController.text.trim();

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: const Text('Livestream', style: TextStyle(color: Colors.white)),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: _callIdController,
              style: const TextStyle(color: Colors.white),
              decoration: const InputDecoration(
                labelText: 'Stream ID',
                labelStyle: TextStyle(color: Colors.white70),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: Colors.white30),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: Colors.white),
                ),
              ),
              autocorrect: false,
              textCapitalization: TextCapitalization.none,
              onChanged: (_) => setState(() {}),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: callId.isEmpty
                    ? null
                    : () => _navigateTo(CreatorLivestreamPage(callId: callId)),
                icon: const Icon(Icons.videocam),
                label: const Text('Go Live (Creator)'),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: callId.isEmpty
                    ? null
                    : () => _navigateTo(ViewerLivestreamPage(callId: callId)),
                icon: const Icon(Icons.play_circle_outline,
                    color: Colors.white70),
                label: const Text('Watch Stream (Viewer)',
                    style: TextStyle(color: Colors.white70)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## Creator View Blueprint

The creator view manages the full host lifecycle: join in backstage, preview camera, go live, monitor viewer count, and end the stream.

```dart
// creator_livestream_page.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

class CreatorLivestreamPage extends StatefulWidget {
  const CreatorLivestreamPage({super.key, required this.callId});

  final String callId;

  @override
  State<CreatorLivestreamPage> createState() => _CreatorLivestreamPageState();
}

class _CreatorLivestreamPageState extends State<CreatorLivestreamPage> {
  Call? _call;
  bool _joined = false;
  bool _isGoingLive = false;
  bool _isEndingStream = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _joinAsHost();
  }

  Future<void> _joinAsHost() async {
    try {
      final call = StreamVideo.instance.makeCall(
        callType: StreamCallType('livestream'),
        id: widget.callId,
      );
      await call.getOrCreate();
      final result = await call.join();
      result.fold(
        success: (_) {
          if (mounted) setState(() { _call = call; _joined = true; });
        },
        failure: (error) {
          if (mounted) setState(() => _error = error.toString());
        },
      );
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _goLive() async {
    setState(() => _isGoingLive = true);
    try {
      await _call?.goLive();
    } finally {
      if (mounted) setState(() => _isGoingLive = false);
    }
  }

  Future<void> _endStream() async {
    setState(() => _isEndingStream = true);
    try {
      await _call?.stopLive();
      await _call?.end();
      await _call?.leave();
      if (mounted) Navigator.of(context).pop();
    } finally {
      if (mounted) setState(() => _isEndingStream = false);
    }
  }

  @override
  void dispose() {
    _call?.leave();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, style: const TextStyle(color: Colors.red)),
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Go back', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      );
    }

    if (!_joined || _call == null) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(color: Colors.white),
              SizedBox(height: 16),
              Text('Setting up stream...',
                  style: TextStyle(color: Colors.white)),
            ],
          ),
        ),
      );
    }

    return StreamBuilder<CallState>(
      stream: _call!.state,
      initialData: _call!.state.value,
      builder: (context, snapshot) {
        final state = snapshot.requireData;
        final isBackstage = state.backstage;
        final isLive = !isBackstage;
        final viewerCount = state.remoteParticipants.length;
        final local = state.localParticipant;

        return Scaffold(
          backgroundColor: Colors.black,
          body: Stack(
            fit: StackFit.expand,
            children: [
              // Camera preview
              if (local != null)
                StreamVideoRenderer(
                  call: _call!,
                  participant: local,
                  videoFit: VideoFit.cover,
                )
              else
                const ColoredBox(color: Colors.black),
              // Status badge
              Positioned(
                top: MediaQuery.of(context).padding.top + 16,
                left: 0,
                right: 0,
                child: Center(child: _statusBadge(isLive, viewerCount)),
              ),
              // Controls
              Positioned(
                left: 0,
                right: 0,
                bottom: MediaQuery.of(context).padding.bottom + 32,
                child: _controlBar(isLive, state),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _statusBadge(bool isLive, int viewerCount) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.6),
        borderRadius: BorderRadius.circular(20),
      ),
      child: isLive
          ? Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: Colors.red,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                const Text('LIVE',
                    style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                const SizedBox(width: 6),
                const Text('·', style: TextStyle(color: Colors.white54)),
                const SizedBox(width: 6),
                const Icon(Icons.person, color: Colors.white70, size: 14),
                const SizedBox(width: 4),
                Text('$viewerCount',
                    style: const TextStyle(color: Colors.white70, fontSize: 12)),
              ],
            )
          : const Text('BACKSTAGE',
              style: TextStyle(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 12)),
    );
  }

  Widget _controlBar(bool isLive, CallState state) {
    final micOn = state.localParticipant?.isAudioEnabled ?? false;
    final cameraOn = state.localParticipant?.isVideoEnabled ?? false;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        children: [
          _iconButton(
            icon: micOn ? Icons.mic : Icons.mic_off,
            active: micOn,
            onTap: () async {
              micOn ? await _call?.microphone.disable() : await _call?.microphone.enable();
            },
          ),
          const SizedBox(width: 16),
          _iconButton(
            icon: cameraOn ? Icons.videocam : Icons.videocam_off,
            active: cameraOn,
            onTap: () async {
              cameraOn ? await _call?.camera.disable() : await _call?.camera.enable();
            },
          ),
          const SizedBox(width: 16),
          _iconButton(
            icon: Icons.flip_camera_ios,
            active: true,
            onTap: () => _call?.camera.flip(),
          ),
          const Spacer(),
          isLive ? _endStreamButton() : _goLiveButton(),
        ],
      ),
    );
  }

  Widget _iconButton({
    required IconData icon,
    required bool active,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 52,
        height: 52,
        decoration: BoxDecoration(
          color: active ? Colors.white.withOpacity(0.15) : Colors.red.withOpacity(0.8),
          shape: BoxShape.circle,
        ),
        child: Icon(icon, color: Colors.white, size: 22),
      ),
    );
  }

  Widget _goLiveButton() {
    return GestureDetector(
      onTap: _isGoingLive ? null : _goLive,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.red,
          borderRadius: BorderRadius.circular(24),
        ),
        child: _isGoingLive
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
            : const Text('Go Live', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
    );
  }

  Widget _endStreamButton() {
    return GestureDetector(
      onTap: _isEndingStream ? null : _endStream,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: Colors.red,
          borderRadius: BorderRadius.circular(24),
        ),
        child: _isEndingStream
            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
            : const Text('End Stream', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
      ),
    );
  }
}
```

**Wiring:**
- **No `StreamCallContainer`** — `CreatorLivestreamPage` owns the call UI entirely
- `_joinAsHost()` is called from `initState`; the `_joined` flag prevents double-joining on re-render
- `isLive` is derived from `state.backstage` — no separate `bool` state
- `viewerCount` comes from `state.remoteParticipants.length` — excludes local participant
- `dispose()` calls `leave()` as a safety net for screen pops without the end-stream button
- `goLive()` / `stopLive()` / `end()` / `leave()` is the correct end-stream sequence

---

## Viewer View Blueprint (WebRTC)

The viewer view joins the call as a subscriber and watches the creator's stream in real time.

```dart
// viewer_livestream_page.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

class ViewerLivestreamPage extends StatefulWidget {
  const ViewerLivestreamPage({super.key, required this.callId});

  final String callId;

  @override
  State<ViewerLivestreamPage> createState() => _ViewerLivestreamPageState();
}

class _ViewerLivestreamPageState extends State<ViewerLivestreamPage> {
  Call? _call;
  bool _joined = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _joinAsViewer();
  }

  Future<void> _joinAsViewer() async {
    try {
      final call = StreamVideo.instance.makeCall(
        callType: StreamCallType('livestream'),
        id: widget.callId,
      );
      await call.getOrCreate();
      // Disable camera and mic before joining - viewers do not publish
      final result = await call.join();
      result.fold(
        success: (_) async {
          await call.camera.disable();
          await call.microphone.disable();
          if (mounted) setState(() { _call = call; _joined = true; });
        },
        failure: (error) {
          if (mounted) setState(() => _error = error.toString());
        },
      );
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  void dispose() {
    _call?.leave();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, style: const TextStyle(color: Colors.red)),
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Go back', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      );
    }

    if (!_joined || _call == null) {
      return const Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(color: Colors.white),
              SizedBox(height: 16),
              Text('Connecting...', style: TextStyle(color: Colors.white)),
            ],
          ),
        ),
      );
    }

    return StreamBuilder<CallState>(
      stream: _call!.state,
      initialData: _call!.state.value,
      builder: (context, snapshot) {
        final state = snapshot.requireData;
        final isBackstage = state.backstage;
        final host = state.remoteParticipants.firstOrNull;

        return Scaffold(
          backgroundColor: Colors.black,
          body: Stack(
            fit: StackFit.expand,
            children: [
              // Host video or waiting overlay
              if (!isBackstage && host != null)
                StreamVideoRenderer(
                  call: _call!,
                  participant: host,
                  videoFit: VideoFit.cover,
                )
              else
                const _WaitingForHostOverlay(),
              // LIVE badge
              if (!isBackstage)
                Positioned(
                  top: MediaQuery.of(context).padding.top + 16,
                  left: 16,
                  child: _liveBadge(),
                ),
              // Leave button
              Positioned(
                top: MediaQuery.of(context).padding.top + 8,
                right: 16,
                child: TextButton(
                  onPressed: () async {
                    await _call?.leave();
                    if (context.mounted) Navigator.of(context).pop();
                  },
                  child: const Text('Leave', style: TextStyle(color: Colors.white)),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _liveBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.6),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          const Text('LIVE',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
        ],
      ),
    );
  }
}

class _WaitingForHostOverlay extends StatelessWidget {
  const _WaitingForHostOverlay();

  @override
  Widget build(BuildContext context) {
    return const ColoredBox(
      color: Colors.black,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.podcasts, size: 64, color: Colors.white30),
            SizedBox(height: 16),
            Text(
              'Waiting for host to go live...',
              style: TextStyle(color: Colors.white70, fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}
```

**Wiring:**
- **No `StreamCallContainer`** — same reason as `CreatorLivestreamPage`
- Disable camera/mic immediately after a successful join — the `livestream` call type also enforces this server-side, but disabling locally avoids spurious track creation
- `state.backstage` is the source of truth for whether the stream is live
- `state.remoteParticipants.firstOrNull` is the host's participant — null if backstage or not yet live
- `dispose()` calls `leave()` as a safety net for OS back gestures

---

## HLS Viewer Blueprint

Use the HLS path for large-scale audiences where per-viewer WebRTC connections are impractical. HLS viewers do not call `join()`.

```dart
// hls_viewer_page.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';
import 'package:video_player/video_player.dart';

class HLSViewerPage extends StatefulWidget {
  const HLSViewerPage({super.key, required this.callId});

  final String callId;

  @override
  State<HLSViewerPage> createState() => _HLSViewerPageState();
}

class _HLSViewerPageState extends State<HLSViewerPage> {
  VideoPlayerController? _controller;
  bool _ready = false;
  bool _waiting = true;
  String? _error;
  StreamSubscription<CallState>? _stateSub;
  Call? _call;

  @override
  void initState() {
    super.initState();
    _watchForHLSUrl();
  }

  Future<void> _watchForHLSUrl() async {
    try {
      final call = StreamVideo.instance.makeCall(
        callType: StreamCallType('livestream'),
        id: widget.callId,
      );
      await call.getOrCreate();
      _call = call;

      // Observe call state - start playback when HLS URL appears
      _stateSub = call.state.listen((state) async {
        final hlsUrl = state.egress?.hls?.playlistUrl;
        if (hlsUrl != null && _controller == null) {
          await _startPlayback(hlsUrl);
        }
      });

      // Check current state immediately in case stream is already live
      final hlsUrl = call.state.value.egress?.hls?.playlistUrl;
      if (hlsUrl != null) await _startPlayback(hlsUrl);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _startPlayback(String hlsUrl) async {
    final controller = VideoPlayerController.networkUrl(Uri.parse(hlsUrl));
    await controller.initialize();
    controller.play();
    controller.setLooping(true);
    if (mounted) {
      setState(() {
        _controller = controller;
        _ready = true;
        _waiting = false;
      });
    }
  }

  @override
  void dispose() {
    _stateSub?.cancel();
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        backgroundColor: Colors.black,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!, style: const TextStyle(color: Colors.red)),
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Go back', style: TextStyle(color: Colors.white)),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          if (_ready && _controller != null)
            AspectRatio(
              aspectRatio: _controller!.value.aspectRatio,
              child: VideoPlayer(_controller!),
            )
          else if (_waiting)
            const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  CircularProgressIndicator(color: Colors.white),
                  SizedBox(height: 16),
                  Text('Waiting for stream...', style: TextStyle(color: Colors.white)),
                ],
              ),
            ),
          // LIVE badge
          if (_ready)
            Positioned(
              top: MediaQuery.of(context).padding.top + 16,
              left: 16,
              child: _liveBadge(),
            ),
          // Leave button
          Positioned(
            top: MediaQuery.of(context).padding.top + 8,
            right: 16,
            child: TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Leave', style: TextStyle(color: Colors.white)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _liveBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.6),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          const Text('LIVE',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
        ],
      ),
    );
  }
}
```

**Wiring:**
- HLS viewers do **not** call `call.join()` — they observe `call.state` for the HLS URL only
- `VideoPlayerController` is created in `_startPlayback`, not in `build` — recreating it in `build` resets playback every frame
- The `StreamSubscription` is cancelled in `dispose()` to prevent state-after-dispose errors
- `egress?.hls?.playlistUrl` — the HLS URL appears a few seconds after the host calls `goLive()`; the subscription handles the delay automatically
- HLS latency is 10–30 s by design — do not try to synchronize with WebRTC viewers
- `video_player` must be added to `pubspec.yaml` separately (`video_player: ^2.9.1`)

---

## Complete Sample: Wiring the Pages Together

```
LivestreamApp
  └── LivestreamModeSelectionPage   (enter stream ID, choose mode)
        ├── CreatorLivestreamPage   (join + backstage + goLive + controls)
        └── ViewerLivestreamPage    (join as subscriber + watch host)
              OR
        └── HLSViewerPage           (observe HLS URL + video_player playback)
```

Each page creates its own `Call` object via `StreamVideo.instance.makeCall(...)`. For the creator and WebRTC viewer, this is the same call ID joining the same stream from different roles.
