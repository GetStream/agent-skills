# Chat Advanced - Flutter Production Concerns & Advanced SDK Patterns

Advanced Stream Chat concerns beyond basic messaging UI: **push notifications**,
**offline / local data persistence**, and **connection lifecycle & app backgrounding**.
These are package-agnostic — they apply equally to `stream_chat_flutter` (pre-built UI)
and `stream_chat_flutter_core` (custom UI). For full copy-pasteable wiring, see
[CHAT-ADVANCED-FLUTTER-blueprints.md](CHAT-ADVANCED-FLUTTER-blueprints.md).

Prerequisites: package install, client init, `connectUser`, and the `StreamChat`
widget from [`CHAT-FLUTTER.md`](CHAT-FLUTTER.md) (pre-built UI) or
[`CHAT-CORE.md`](CHAT-CORE.md) (custom UI). Shared client-ownership and auth patterns
live in [`../sdk.md`](../sdk.md).

Rules: [../RULES.md](../RULES.md) (secrets stay server-side, proper disconnect).

## Quick ref

- **Push:** `firebase_messaging` + `flutter_local_notifications`; register with `client.addDevice(token, PushProvider.firebase)` after `connectUser`; deregister with `client.removeDevice(token)` before `disconnectUser`
- **Offline:** attach `StreamChatPersistenceClient` **before** `connectUser`; package `stream_chat_persistence: ^10.0.0`
- **Lifecycle:** WS opens on `connectUser`, closes on background, reopens on foreground; gate lazy-connect UI on the `connectUser` future
- **Disconnect:** `await client.disconnectUser()` before switching users; force route disposal on logout so the WS actually closes

---

## Push notifications

> **Docs:** [Adding Push Notifications (V2)](https://getstream.io/chat/docs/sdk/flutter/guides/push-notifications/adding-push-notifications-v2.md)

Push is wired at the SDK level via **device registration**; the transport (FCM/APNs) is
standard FlutterFire setup. Applies to both `stream_chat_flutter` and `stream_chat_flutter_core`.

- **Packages:** `firebase_messaging` (FCM) + `flutter_local_notifications` (to render the notification on Android). Do the normal FlutterFire setup (`google-services.json` / `GoogleService-Info.plist`, APNs key). Stream ships no separate push package.
- **Register after `connectUser`, and on every token refresh:**
  ```dart
  final token = await FirebaseMessaging.instance.getToken();
  if (token != null) await client.addDevice(token, PushProvider.firebase);
  FirebaseMessaging.instance.onTokenRefresh
      .listen((t) => client.addDevice(t, PushProvider.firebase));
  ```
  `addDevice(String id, PushProvider provider, {String? pushProviderName})`. `PushProvider` values: `firebase`, `apn`, `huawei`, `xiaomi`. `pushProviderName:` selects a named provider config when you run more than one.
- **Deregister on logout:** `await client.removeDevice(token)` **before** `disconnectUser()`.
- **Server config:** upload your Firebase service-account JSON in Stream Dashboard → app → push and enable push (v2); APNs is delivered through Firebase by default.
- **Handling (per docs):** iOS gets a `notification`+`data` payload (OS shows it); Android gets `data`-only — render it yourself. Use a **top-level** `@pragma('vm:entry-point')` handler via `FirebaseMessaging.onBackgroundMessage`; in that isolate connect with `client.connectUser(user, token, connectWebSocket: false)` and fetch the message with `client.getMessage(messageId)` (payload keys `data['type']`, `data['cid']`, `data['id']`).
- **Gotchas:** push **requires channel membership** (watching isn't enough) and fires **only for new messages**. No push is sent while the user holds an active WebSocket; setting `onBackgroundEventReceived` on `StreamChat` keeps the WS alive ~`backgroundKeepAlive` (default 15s) after backgrounding. Max 25 devices/user; `skip_push`, muted channels, and `push_notifications` disabled on the channel type all suppress delivery. **Test on a physical iOS device** (simulator won't receive push).

---

## Offline & local data persistence

> **Docs:** [Offline Support / Local Data Persistence](https://getstream.io/chat/docs/sdk/flutter/guides/adding-local-data-persistence.md)

Attach the official persistence client **before** `connectUser` and the SDK caches channels/messages/users in a local SQLite DB, serves them instantly when offline, and queues writes (send/edit/delete) for automatic retry on reconnect.

- **Package** (not a default dependency — add it): `stream_chat_persistence: ^10.0.0` (built on `drift`/SQLite).
- **Wire it:**
  ```dart
  final client = StreamChatClient('api_key', logLevel: Level.OFF)
    ..chatPersistenceClient = StreamChatPersistenceClient(
      logLevel: Level.OFF,
      connectionMode: ConnectionMode.regular, // or .background (DB on an isolate, frees the UI thread)
    );
  await client.connectUser(user, token);
  ```
- The DB is keyed by `userId` — a different user uses a different DB. Flush a user's cache on logout with `await client.disconnectUser(flushChatPersistence: true)`.
- Once attached there's nothing else to call: the channel list, message lists, and search read from cache transparently when offline.

---

## Connection lifecycle & app backgrounding

> **Docs:** [Initialize Stream Chat in Part of the Widget Tree](https://getstream.io/chat/docs/sdk/flutter/guides/initialize-stream-chat-widget-tree.md)

- `StreamChat` opens a WebSocket **only once a user is connected** (`connectUser`); before that it just registers lifecycle listeners. Backgrounding closes the WS; foregrounding reopens it automatically.
- When chat is one section of a larger app (not the whole app), connect lazily and gate the UI on the connection future rather than blocking `runApp`:
  ```dart
  late final Future<OwnUser> _connection =
      client.connectUser(User(id: userId), token);
  // ...
  FutureBuilder<OwnUser>(
    future: _connection,
    builder: (context, snap) {
      if (snap.connectionState == ConnectionState.waiting) {
        return const Center(child: CircularProgressIndicator());
      }
      if (snap.hasError) return ErrorView(error: snap.error!);
      return const ChannelListPage();
    },
  )
  ```
- Call `client.disconnectUser()` when the chat section is disposed. `disconnectUser` only runs if the route is actually disposed — on logout force it with `Navigator.pushAndRemoveUntil(..., (r) => false)`, otherwise the connection lingers.

---

## Verification checklist (advanced)

- **Push:** `addDevice` is called after `connectUser` and re-registered on `onTokenRefresh`; `removeDevice` runs before `disconnectUser`; the background handler is a top-level `@pragma('vm:entry-point')` function; the connecting user is a **member** of the channel (not just watching).
- **Offline:** `chatPersistenceClient` is assigned **before** `connectUser`; the channel/message lists render from cache with the network off; logout uses `flushChatPersistence: true` to clear the user's DB.
- **Lifecycle:** lazy-connect UI is gated on the `connectUser` future; logout forces route disposal so the WebSocket actually closes (no orphaned connections).
