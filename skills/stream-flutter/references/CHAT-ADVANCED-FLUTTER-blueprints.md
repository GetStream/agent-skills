# Chat Advanced - Wiring Blueprints

Load only the section you are implementing. For the SDK patterns and gotchas behind these
blueprints, see [CHAT-ADVANCED-FLUTTER.md](CHAT-ADVANCED-FLUTTER.md). For client
initialization, `connectUser`, and the `StreamChat` widget, see
[CHAT-FLUTTER.md](CHAT-FLUTTER.md) / [CHAT-FLUTTER-blueprints.md](CHAT-FLUTTER-blueprints.md)
(pre-built UI) or [CHAT-CORE.md](CHAT-CORE.md) (custom UI).

These blueprints are package-agnostic — `client` is a `StreamChatClient` regardless of which
UI tier you use.

---

## Push Notifications Blueprint

> **Docs:** [Adding Push Notifications (V2)](https://getstream.io/chat/docs/sdk/flutter/guides/push-notifications/adding-push-notifications-v2.md)

End-to-end FCM wiring: a top-level background handler, device registration after connect,
token-refresh re-registration, and deregistration on logout. Assumes FlutterFire is already
set up (`google-services.json` / `GoogleService-Info.plist`, APNs key) and push (v2) is
enabled in the Stream Dashboard. If it's not setup correctly let the integrator know and ask to do it.
You can create a template/placehodler files.

```dart
// main.dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

// Top-level — required by FCM. Runs in its own isolate with no app state, so
// connect WITHOUT a WebSocket and fetch the message by id from the payload.
@pragma('vm:entry-point')
Future<void> _onBackgroundMessage(RemoteMessage message) async {
  await Firebase.initializeApp();

  final client = StreamChatClient('api_key', logLevel: Level.OFF);
  await client.connectUser(
    User(id: 'user-id'),
    'user-token',
    connectWebSocket: false, // no live socket in the background isolate
  );

  final messageId = message.data['id'];
  if (messageId != null) {
    final response = await client.getMessage(messageId);
    // Render with flutter_local_notifications using response.message.* and
    // message.data['type'] / message.data['cid'].
  }
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  FirebaseMessaging.onBackgroundMessage(_onBackgroundMessage);

  final client = StreamChatClient('api_key', logLevel: Level.OFF);
  await client.connectUser(User(id: 'user-id', name: 'User'), 'user-token');

  await _registerDevice(client); // see helper below

  runApp(MyApp(client: client));
}
```

```dart
// push_registration.dart — register/deregister helpers
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

Future<void> _registerDevice(StreamChatClient client) async {
  final settings = await FirebaseMessaging.instance.requestPermission();
  if (settings.authorizationStatus == AuthorizationStatus.denied) return;

  final token = await FirebaseMessaging.instance.getToken();
  if (token != null) {
    await client.addDevice(token, PushProvider.firebase);
  }

  // Re-register whenever FCM rotates the token.
  FirebaseMessaging.instance.onTokenRefresh
      .listen((t) => client.addDevice(t, PushProvider.firebase));
}

// On logout: deregister BEFORE disconnecting.
Future<void> logout(StreamChatClient client) async {
  final token = await FirebaseMessaging.instance.getToken();
  if (token != null) await client.removeDevice(token);
  await client.disconnectUser();
}
```

**Wiring:**

- `_onBackgroundMessage` is **top-level** and annotated `@pragma('vm:entry-point')` — a method or closure won't survive the background isolate.
- In that isolate use `connectUser(..., connectWebSocket: false)` and `getMessage(id)`; the live app keeps its normal WebSocket connection.
- `addDevice` runs **after** `connectUser`; `onTokenRefresh` keeps the registration current.
- `removeDevice` runs **before** `disconnectUser` so the server stops targeting a logged-out device.
- Push **requires channel membership** and fires only for **new** messages; no push arrives while the app holds an active WebSocket.

---

## Offline Persistence Blueprint

> **Docs:** [Offline Support / Local Data Persistence](https://getstream.io/chat/docs/sdk/flutter/guides/adding-local-data-persistence.md)

Attach the persistence client **before** `connectUser`. Nothing else changes — the channel
list, message lists, and search read from the local SQLite cache transparently when offline,
and queued writes retry on reconnect.

```dart
// main.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';
import 'package:stream_chat_persistence/stream_chat_persistence.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final client = StreamChatClient('api_key', logLevel: Level.OFF)
    ..chatPersistenceClient = StreamChatPersistenceClient(
      logLevel: Level.OFF,
      // .background runs the DB on an isolate, keeping heavy reads/writes
      // off the UI thread. Use .regular for the simplest setup.
      connectionMode: ConnectionMode.background,
    );

  await client.connectUser(
    User(id: 'user-id', name: 'User'),
    'user-token',
  );

  runApp(MyApp(client: client));
}

// On logout, flush this user's local DB:
Future<void> logout(StreamChatClient client) async {
  await client.disconnectUser(flushChatPersistence: true);
}
```

**Wiring:**

- Add `stream_chat_persistence: ^10.0.0` to `pubspec.yaml` (not a default dependency).
- Assign `chatPersistenceClient` with the cascade (`..`) **before** `connectUser` — attaching it after connect does nothing for the current session.
- The DB is keyed by `userId`; switching users uses a separate DB. `flushChatPersistence: true` clears the cache on logout.

---

## Lazy-Connect / Backgrounding Blueprint

> **Docs:** [Initialize Stream Chat in Part of the Widget Tree](https://getstream.io/chat/docs/sdk/flutter/guides/initialize-stream-chat-widget-tree.md)

When chat is one section of a larger app, don't block `runApp` on `connectUser`. Kick off the
connection once, store the future, and gate the chat UI on it. Force route disposal on logout
so the WebSocket actually closes.

```dart
// chat_section.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

class ChatSection extends StatefulWidget {
  const ChatSection({super.key, required this.client, required this.userId, required this.token});

  final StreamChatClient client;
  final String userId;
  final String token;

  @override
  State<ChatSection> createState() => _ChatSectionState();
}

class _ChatSectionState extends State<ChatSection> {
  // Started once — NOT in build, so it doesn't re-fire on rebuild.
  late final Future<OwnUser> _connection =
      widget.client.connectUser(User(id: widget.userId), widget.token);

  @override
  void dispose() {
    // Closes the WebSocket when the chat section leaves the tree.
    widget.client.disconnectUser();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<OwnUser>(
      future: _connection,
      builder: (context, snap) {
        if (snap.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snap.hasError) {
          return Center(child: Text('Connection failed: ${snap.error}'));
        }
        return const ChannelListPage();
      },
    );
  }
}

// On logout, force the whole stack to dispose so disconnectUser runs:
void logout(BuildContext context) {
  Navigator.of(context).pushAndRemoveUntil(
    MaterialPageRoute(builder: (_) => const LoginPage()),
    (route) => false,
  );
}
```

**Wiring:**

- `_connection` is a `late final` field — created once, never inside `build`.
- The `FutureBuilder` shows a spinner while connecting, an error view on failure, and the channel list on success.
- `disconnectUser()` in `dispose()` closes the socket when the section unmounts; `pushAndRemoveUntil(..., (r) => false)` guarantees the section is actually disposed on logout so the connection doesn't linger.
- Backgrounding/foregrounding is automatic — the SDK closes and reopens the WebSocket with app lifecycle; no manual handling needed.
