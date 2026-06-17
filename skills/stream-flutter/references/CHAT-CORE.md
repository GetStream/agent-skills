# Chat - stream_chat_flutter_core Setup & Integration

`stream_chat_flutter_core` provides business logic and data controllers without any pre-built UI. Use it when you need full control over your widget layer. This file covers setup, controllers, reactive state, and gotchas. For widget blueprints, see [CHAT-CORE-blueprints.md](CHAT-CORE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

## Quick ref

- **Package:** `stream_chat_flutter_core` via pub.dev
- **Version:** `^10.0.0`
- **Dart SDK:** `^3.11.0` | **Flutter:** `>=3.41.0`
- **Use when:** `stream_chat_flutter` pre-built widgets don't fit your design system
- **First:** Install -> client init -> `StreamChatCore` widget -> `connectUser` -> controllers -> custom widgets
- **Docs:** `https://getstream.io/chat/docs/sdk/flutter/stream_chat_flutter_core/`

For shared client setup patterns see [`../sdk.md`](../sdk.md). **Push notifications, offline/local persistence, and connection-lifecycle/backgrounding** (all package-agnostic, apply equally to core) are in [`CHAT-ADVANCED-FLUTTER.md`](CHAT-ADVANCED-FLUTTER.md) + [`CHAT-ADVANCED-FLUTTER-blueprints.md`](CHAT-ADVANCED-FLUTTER-blueprints.md). Filter operators and permissions are in [`CHAT-FLUTTER.md`](CHAT-FLUTTER.md).

> **Prerequisite — the existing project must already be on `stream_chat_flutter_core` v10.** This skill targets the v10 API exclusively. If the integrator's `pubspec.yaml` / `pubspec.lock` pins a 9.x or earlier version, **stop and tell the user they must migrate to v10 first** — controllers, the reaction/delete APIs, and `ClientState` immutability all changed and this skill does not cover the migration path. Resume only once the project resolves `stream_chat_flutter_core: ^10.0.0`.

---

## Installation

> **Docs:** [Installation](https://getstream.io/chat/docs/sdk/flutter/basics/installation.md) · [Core Setup](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/setup.md)

```yaml
# pubspec.yaml
dependencies:
  stream_chat_flutter_core: ^10.0.0
```

```bash
flutter pub get
```

No platform-specific setup is required for `stream_chat_flutter_core` itself - it has no native dependencies. If you add `image_picker`, `file_picker`, or other media plugins for your custom attachment UI, follow their individual platform guides.

---

## StreamChatCore Widget

> **Docs:** [Chat Client / StreamChatCore](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-chat-core.md)

`stream_chat_flutter_core` has its own inherited widget, `StreamChatCore`, that is separate from `StreamChat`. Place it in the widget tree before any core widget or controller accesses it.

```dart
MaterialApp(
  builder: (context, widget) => StreamChatCore(
    client: client,
    child: widget,
  ),
  home: const ChannelListPage(),
)
```

Access the client anywhere below `StreamChatCore`:

```dart
final client = StreamChatCore.of(context).client;
final currentUser = StreamChatCore.of(context).currentUser;
```

**`StreamChatCore` behaviour to be aware of:**

- It sets `client.recoverStateOnReconnect = false` on mount. If you watch channels outside a list controller, subscribe to `client.on(EventType.connectionRecovered)` and call `channel.watch()` to refresh on reconnect.
- Default `backgroundKeepAlive` is **15 seconds**.

---

## StreamChannelListController

> **Docs:** [StreamChannelListController](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-channel-list-controller.md) · [User list](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-user-list-controller.md) · [Member list](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-member-list-controller.md) · [Message search](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-message-search-list-controller.md)

The primary controller for a paginated, filtered channel list.

```dart
class _ChannelListPageState extends State<ChannelListPage> {
  late final _controller = StreamChannelListController(
    client: StreamChatCore.of(context).client,
    filter: Filter.and([
      Filter.equal('type', 'messaging'),
      Filter.in_(
        'members',
        [StreamChatCore.of(context).currentUser!.id],
      ),
    ]),
    channelStateSort: const [SortOption.desc('last_message_at')],
    limit: 20,
  );

  @override
  void initState() {
    super.initState();
    _controller.doInitialLoad();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}
```

`doInitialLoad()` triggers the first page fetch. Do not call it in `build`. Dispose the controller in `dispose()`.

---

## PagedValueListenableBuilder

> **Docs:** [PagedValueListenableBuilder](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/paged-value-listenable-builder.md)

`StreamChannelListController` extends `PagedValueNotifier`. Build reactive UI with `PagedValueListenableBuilder`:

```dart
PagedValueListenableBuilder<int, Channel>(
  valueListenable: _controller,
  builder: (context, value, child) {
    return value.when(
      (channels, nextPageKey, error) {
        if (channels.isEmpty) {
          return const Center(child: Text('No channels yet.'));
        }
        return ListView.builder(
          itemCount: channels.length + (nextPageKey != null ? 1 : 0),
          itemBuilder: (context, index) {
            if (index == channels.length) {
              // Trigger next page when the sentinel item becomes visible
              _controller.loadMore(nextPageKey!);
              return const Center(child: CircularProgressIndicator());
            }
            return ChannelListTile(channel: channels[index]);
          },
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Error: ${e.message}'),
            TextButton(
              onPressed: _controller.retry,
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  },
)
```

`value.when(...)` covers three states: loaded data (with optional `nextPageKey` for pagination), loading, and error.

---

## StreamChannel (inherited widget)

Wrap each channel screen with `StreamChannel` so descendant widgets can call `StreamChannel.of(context).channel`:

```dart
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (_) => StreamChannel(
      channel: channel,
      child: const CustomChannelPage(),
    ),
  ),
);
```

Inside any descendant widget:

```dart
final channel = StreamChannel.of(context).channel;
```

---

## Channel state streams

All channel-level reactive state is available as streams on `channel.state`:

```dart
final channel = StreamChannel.of(context).channel;

// Messages
channel.state!.messagesStream          // Stream<List<Message>>
channel.state!.messages                // List<Message> (current value)

// Members and typing
channel.state!.membersStream           // Stream<List<Member>>
channel.state!.typingEventsStream      // Stream<Map<User, TypingStartEvent>>

// Reads and unread
channel.state!.readStream             // Stream<List<Read>>
channel.state!.unreadCountStream      // Stream<int>
channel.state!.lastMessageStream      // Stream<Message?>
```

Use `StreamBuilder` to subscribe:

```dart
StreamBuilder<List<Message>>(
  stream: channel.state!.messagesStream,
  initialData: channel.state!.messages,
  builder: (context, snapshot) {
    final messages = snapshot.data ?? [];
    return CustomMessageList(messages: messages);
  },
)
```

---

## Sending messages

```dart
// Send a plain text message
await channel.sendMessage(Message(text: 'Hello!'));

// Reply in thread
await channel.sendMessage(Message(
  text: 'Got it!',
  parentId: parentMessageId,
  showInChannel: true,
));

// Send with attachment
await channel.sendMessage(Message(
  text: 'Check this out',
  attachments: [
    Attachment(
      type: 'image',
      imageUrl: 'https://example.com/photo.jpg',
    ),
  ],
));
```

---

## Reactions

> **Docs:** [Message Reactions](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/reactions.md)

`sendReaction` and `deleteReaction` take the `Message` object and a `Reaction`:

```dart
// Add a reaction
await channel.sendReaction(message, Reaction(type: 'like'));

// Remove a reaction
await channel.deleteReaction(message, Reaction(type: 'like'));
```

Reaction counts and scores are accessed via `message.reactionGroups` (a `Map<String, ReactionGroup>`).

---

## Pagination (messages)

```dart
// Load older messages (call when user scrolls to top)
await channel.query(
  messagesPagination: PaginationParams(lessThan: oldestMessageId, limit: 20),
);
```

---

## StreamMessageComposerController

`StreamMessageComposerController` manages compose state independently of any UI. It is available in `stream_chat_flutter_core`.

```dart
final composerController = StreamMessageComposerController();

// Set quoted message for reply
composerController.quotedMessage = message;

// Clear quote
composerController.clearQuotedMessage();

// Enter edit mode
composerController.editMessage(existingMessage);

// Check if in edit mode
final editing = composerController.isEditing;

// Access the message being edited
final original = composerController.messageBeingEdited;

// Cancel edit
composerController.cancelEditMessage();

// Clear a set command
composerController.clearCommand();

// Current text
final text = composerController.text;

// Always dispose
composerController.dispose();
```

**Edit-mode semantics:**

- To enter edit mode call `editMessage(msg)` — do not pass a non-initial message to the constructor (the constructor's `message:` is for pre-filling a draft, e.g. a thread reply with `parentId`)
- `clear()` does not exit edit mode; call `cancelEditMessage()` to exit
- `cancelEditMessage()` is a no-op when no edit is active (safe to call unconditionally)

---

## Deleting Messages

```dart
// Delete for everyone
await channel.deleteMessage(message);

// Delete only for the current user
await channel.deleteMessageForMe(message);
```

Both take the `Message` object. `deleteMessageForMe` hides the message only for the calling user; other participants still see it. Delete-for-me state is reflected on the message's `state` — `message.state.isDeletedForMe`, `isDeletingForMe`, `isDeletingForMeFailed`.

## Channel helpers

```dart
// True if distinct channel with exactly 2 members — use for "DM" checks
final isDm = channel.isOneToOne;

// True for non-distinct channels (including two-member non-distinct) or larger groups
final isGroup = channel.isGroup;
```

---

## Channel permissions & roles

Permissions are enforced **per role, per scope**, and apply identically whether you build UI with `stream_chat_flutter` or `stream_chat_flutter_core` — the core package just means _you_ trigger the queries (`StreamChannelListController.doInitialLoad()`, `client.queryChannels(...)`, `channel.addMembers(...)`), so the same grants gate them.

Key point: **client-side calls are permission-checked; server-side calls (CLI / backend using the API _secret_) bypass all checks.** So seeding works but the same action from the app can 403. The two grants that most often block an open "discover & join groups" UI on the default `messaging` type:

- **`Read Channel` (`ReadChannel`)** — required to `queryChannels` for / open channels the user is **not** a member of. Often **not** granted to `user`/`guest` by default.
- **`Add Own Channel Membership` (`AddOwnChannelMembership`)** — required for `channel.addMembers([myId])` to self-join. Often **not** granted by default. (Leaving needs `RemoveOwnChannelMembership`.)

Fix in Dashboard → Chat → **Roles & Permissions** (permissions **v2**) for the `user` and/or `guest` role on the `messaging` type, or via `UpdateChannelType` / per-channel `UpdateChannelPartial` `config_overrides.grants`. Guests are stricter than `user` — grant the `guest` role too if you sign people in by name. Full table and symptoms: [CHAT-FLUTTER.md → Channel permissions & roles](CHAT-FLUTTER.md#channel-permissions--roles). Reference: <https://getstream.io/chat/docs/flutter-dart/chat-permission-policies.md>

---

## Gotchas

- **Discover/join features depend on channel-type permissions.** Querying non-member channels needs `Read Channel` and self-join needs `Add Own Channel Membership` on the channel type; the default `messaging` grants for `user`/`guest` often omit both. Works when seeded server-side, 403s from the app. See [Channel permissions & roles](#channel-permissions--roles).
- **`doInitialLoad()` must be called manually.** Unlike `stream_chat_flutter`'s `StreamChannelListView`, the core controller does not auto-fetch. Call it in `initState`.
- **Dispose all controllers.** `StreamChannelListController`, `StreamMessageComposerController`, and any manual stream subscriptions must be disposed in `State.dispose()`.
- **`channel.state` can be null before watch.** Call `await channel.watch()` or `await channel.query(...)` before reading `channel.state`.
- **`StreamChatCore` vs `StreamChat`.** `stream_chat_flutter_core` uses `StreamChatCore`; `stream_chat_flutter` uses `StreamChat`. Don't mix them in the same tree - pick one.
- **Message pagination is manual.** Call `channel.query(messagesPagination: ...)` when the user scrolls to the top - `StreamMessageListView` handles this automatically but your custom list does not.
- **Never create channels in `build`.** Channel objects should be stable references held in state, not recreated on every rebuild.
- **`sendReaction`/`deleteReaction` take a `Message` and a `Reaction`.** Use `channel.sendReaction(message, Reaction(type: 'like'))` — there is no `(id, 'like')` string shorthand.
- **Reaction counts live on `message.reactionGroups`** (`Map<String, ReactionGroup>`).
- **`StreamChatCore` sets `recoverStateOnReconnect = false`.** If your app manually watches channels outside a list controller, subscribe to `client.on(EventType.connectionRecovered)` to re-query them on reconnect.
- **`StreamMessageComposerController` edit mode is explicit.** Call `controller.editMessage(msg)` to enter edit mode; `clear()` does not exit it — call `cancelEditMessage()`.
- **`ClientState` collections are immutable.** `client.state.channels` / `users` / `activeLiveLocations` throw on mutation, and `addChannels()` / `removeChannel()` are `@internal`. Let the SDK manage state via `queryChannels()` / `channel.watch()`.
