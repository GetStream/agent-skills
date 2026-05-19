# Video Flutter - Widget Blueprints

Load only the section you are implementing. For setup, client initialization, and gotchas, see [VIDEO-FLUTTER.md](VIDEO-FLUTTER.md).

---

## App Entry Point Blueprint

Initialize `StreamVideo` before `runApp`. No wrapper widget is needed - the SDK uses a singleton pattern.

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
      image: 'https://example.com/avatar.jpg',
    ),
    userToken: UserToken.jwt('your_user_token'),
  );

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Video App',
      home: const HomeScreen(),
    );
  }
}
```

**Wiring:**
- `WidgetsFlutterBinding.ensureInitialized()` is required before any async or SDK work in `main`
- The `StreamVideo(...)` constructor registers the singleton - no return value is needed in `main`
- Access the client anywhere with `StreamVideo.instance`
- Do **not** introduce a `VideoManager`, `CallService`, or wrapper class - use `StreamVideo.instance` and `Call` directly

---

## Home / Join-or-Start Call Blueprint

Lets the user enter a call ID to join an existing call, or generate a new one.

```dart
// home_screen.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';
import 'package:uuid/uuid.dart';

import 'call_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _callIdController = TextEditingController();
  bool _joining = false;

  @override
  void dispose() {
    _callIdController.dispose();
    super.dispose();
  }

  Future<void> _joinCall(String callId) async {
    setState(() => _joining = true);
    try {
      final call = StreamVideo.instance.makeCall(
        callType: StreamCallType.defaultType,
        id: callId,
      );
      await call.getOrCreate();
      final result = await call.join();
      result.fold(
        success: (_) {
          if (mounted) {
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => CallScreen(call: call)),
            );
          }
        },
        failure: (error) {
          if (mounted) _showError('Failed to join: $error');
        },
      );
    } finally {
      if (mounted) setState(() => _joining = false);
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Video Call')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: _callIdController,
              decoration: const InputDecoration(
                labelText: 'Call ID',
                border: OutlineInputBorder(),
              ),
              autocorrect: false,
              textCapitalization: TextCapitalization.none,
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _joining || _callIdController.text.isEmpty
                    ? null
                    : () => _joinCall(_callIdController.text.trim()),
                child: _joining
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Join Call'),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: _joining
                    ? null
                    : () => _joinCall(const Uuid().v4()),
                child: const Text('New Call'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

**Wiring:**
- `makeCall` is synchronous - no `await` needed
- `getOrCreate()` then `join()` is the required two-step sequence; never call `join()` alone
- The `Result` from `join()` must be checked - it does not throw on failure
- `_joining` prevents double-taps while the call is connecting

---

## Full Call View Blueprint (StreamCallContainer)

`StreamCallContainer` is the complete in-call screen with participant grid, controls, and camera feed. Use it unless you are building a fully custom layout.

```dart
// call_screen.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

class CallScreen extends StatefulWidget {
  const CallScreen({super.key, required this.call});

  final Call call;

  @override
  State<CallScreen> createState() => _CallScreenState();
}

class _CallScreenState extends State<CallScreen> {
  @override
  void dispose() {
    // leave() is idempotent - safe to call on dispose if not already left
    widget.call.leave();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: StreamCallContainer(
        call: widget.call,
        onBackPressed: () => Navigator.of(context).pop(),
        onLeaveCallTap: () async {
          await widget.call.leave();
          if (context.mounted) Navigator.of(context).pop();
        },
      ),
    );
  }
}
```

**Wiring:**
- `StreamCallContainer` manages participant layout, controls bar, and camera feed internally
- `onLeaveCallTap` is called when the user taps the hang-up control; call `leave()` and then navigate away
- `dispose()` calls `leave()` as a safety net for cases where the screen is popped without the hang-up button (e.g. OS back gesture)
- Do **not** embed `StreamCallContainer` inside a `SingleChildScrollView` - it manages its own layout

---

## Custom Call Controls Blueprint

Replace the SDK's default controls bar with your own by building controls that call directly into `call.camera`, `call.microphone`, and `call.speakerphone`.

```dart
// custom_call_controls.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

class CustomCallControls extends StatelessWidget {
  const CustomCallControls({super.key, required this.call});

  final Call call;

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<CallState>(
      stream: call.state,
      initialData: call.state.value,
      builder: (context, snapshot) {
        final state = snapshot.requireData;
        final local = state.localParticipant;
        final micOn = local?.isAudioEnabled ?? false;
        final cameraOn = local?.isVideoEnabled ?? false;

        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _ControlButton(
                  icon: micOn ? Icons.mic : Icons.mic_off,
                  active: micOn,
                  onTap: () async {
                    micOn
                        ? await call.microphone.disable()
                        : await call.microphone.enable();
                  },
                ),
                _ControlButton(
                  icon: cameraOn ? Icons.videocam : Icons.videocam_off,
                  active: cameraOn,
                  onTap: () async {
                    cameraOn
                        ? await call.camera.disable()
                        : await call.camera.enable();
                  },
                ),
                _ControlButton(
                  icon: Icons.flip_camera_ios,
                  active: true,
                  onTap: () async => call.camera.flip(),
                ),
                _ControlButton(
                  icon: Icons.call_end,
                  active: false,
                  backgroundColor: Colors.red,
                  onTap: () async {
                    await call.leave();
                    if (context.mounted) Navigator.of(context).pop();
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _ControlButton extends StatelessWidget {
  const _ControlButton({
    required this.icon,
    required this.active,
    required this.onTap,
    this.backgroundColor,
  });

  final IconData icon;
  final bool active;
  final VoidCallback onTap;
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    final bg = backgroundColor ??
        (active
            ? Colors.white.withOpacity(0.15)
            : Colors.red.withOpacity(0.8));

    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(color: bg, shape: BoxShape.circle),
        child: Icon(icon, color: Colors.white, size: 24),
      ),
    );
  }
}
```

**Wiring:**
- Use `StreamBuilder<CallState>` on `call.state` to rebuild controls when audio/video state changes
- `local?.isAudioEnabled` and `local?.isVideoEnabled` reflect current toggle state
- `call.camera.flip()` is synchronous from the widget side; errors are swallowed - add try/catch for production

---

## Participant Tile Blueprint

Renders a single participant's video with name and audio status overlaid.

```dart
// participant_tile.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

class ParticipantTile extends StatelessWidget {
  const ParticipantTile({
    super.key,
    required this.call,
    required this.participant,
  });

  final Call call;
  final CallParticipant participant;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Stack(
        fit: StackFit.expand,
        children: [
          StreamVideoRenderer(
            call: call,
            participant: participant,
            videoFit: VideoFit.cover,
          ),
          // Name + mute indicator overlay
          Positioned(
            left: 8,
            bottom: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    participant.name,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (!participant.isAudioEnabled) ...[
                    const SizedBox(width: 4),
                    const Icon(
                      Icons.mic_off,
                      color: Colors.white,
                      size: 12,
                    ),
                  ],
                ],
              ),
            ),
          ),
          // Speaking indicator
          if (participant.isSpeaking)
            Positioned.fill(
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.green, width: 2),
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
```

**Wiring:**
- `StreamVideoRenderer` requires both `call` and `participant` to resolve the correct media track
- `VideoFit.cover` fills the tile and may crop; use `VideoFit.contain` to avoid cropping
- `isSpeaking` updates automatically from call state - no extra stream subscription needed inside the tile
- Wrap the tile in `LayoutBuilder` or give it a fixed size so `StreamVideoRenderer` knows the render resolution

---

## Participant Grid Blueprint

Displays all remote participants in a grid with the local participant in a corner PiP.

```dart
// participant_grid.dart
import 'package:flutter/material.dart';
import 'package:stream_video_flutter/stream_video_flutter.dart';

class ParticipantGrid extends StatelessWidget {
  const ParticipantGrid({super.key, required this.call});

  final Call call;

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<CallState>(
      stream: call.state,
      initialData: call.state.value,
      builder: (context, snapshot) {
        final state = snapshot.requireData;
        final remote = state.remoteParticipants;
        final local = state.localParticipant;

        return Stack(
          fit: StackFit.expand,
          children: [
            // Remote participant grid
            GridView.builder(
              padding: const EdgeInsets.all(8),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 8,
                mainAxisSpacing: 8,
              ),
              itemCount: remote.length,
              itemBuilder: (context, index) {
                return ParticipantTile(
                  call: call,
                  participant: remote[index],
                );
              },
            ),
            // Local PiP
            if (local != null)
              Positioned(
                right: 16,
                bottom: 100,
                width: 100,
                height: 140,
                child: ParticipantTile(call: call, participant: local),
              ),
          ],
        );
      },
    );
  }
}
```

**Wiring:**
- `remoteParticipants` excludes the local user - avoids showing your own video in the grid
- The local PiP is positioned with `Stack`; adjust the `bottom` offset to clear your custom controls bar
- `StreamBuilder` on `call.state` rebuilds the grid when participants join or leave
