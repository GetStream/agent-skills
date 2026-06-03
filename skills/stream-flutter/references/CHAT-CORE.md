# Chat - stream_chat_flutter_core Setup & Integration

`stream_chat_flutter_core` provides business logic and data controllers without any pre-built UI. Use it when you need full control over your widget layer. This file covers setup, controllers, reactive state, and gotchas. For widget blueprints, see [CHAT-CORE-blueprints.md](CHAT-CORE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

## Quick ref

- **Package:** `stream_chat_flutter_core` via pub.dev
- **Version:** `^10.0.0`
- **Dart SDK:** `^3.10.0` | **Flutter:** `>=3.38.1`
- **Use when:** `stream_chat_flutter` pre-built widgets don't fit your design system
- **First:** Install -> client init -> `StreamChatCore` widget -> `connectUser` -> controllers -> custom widgets
- **Docs:** `https://getstream.io/chat/docs/sdk/flutter/stream_chat_flutter_core/`

For shared client setup patterns, see [`../sdk.md`](../sdk.md).

---

## Installation

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

**v10 behavioural changes in `StreamChatCore`:**
- Sets `client.recoverStateOnReconnect = false` on mount — apps watching channels outside list controllers must manually subscribe to `connectionRecovered` events to re-query.
- Default `backgroundKeepAlive` reduced from 1 minute to **15 seconds**.

---

## StreamChannelListController

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

In v10, `sendReaction` accepts a full `Reaction` object instead of individual string parameters.

```dart
// Add a reaction (v10)
await channel.sendReaction(messageId, Reaction(type: 'like'));

// Remove a reaction (unchanged)
await channel.deleteReaction(messageId, 'like');
```

Reaction counts and scores are now accessed via `message.reactionGroups` (a `Map<String, ReactionGroup>`). The old `reactionCounts` and `reactionScores` getters were removed in v10.

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

`StreamMessageInputController` was renamed to `StreamMessageComposerController` in v10. Available in `stream_chat_flutter_core` for managing compose state independently of any UI.

```dart
final composerController = StreamMessageComposerController();

// Set quoted message for reply
composerController.quotedMessage = message;

// Clear quote
composerController.clearQuotedMessage();

// Enter edit mode (v10: constructor no longer accepts non-initial messages)
composerController.editMessage(existingMessage);

// Check if in edit mode
final editing = composerController.isEditing;

// Access the message being edited (was editingOriginalMessage in v9)
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

**v10 behavioral changes:**
- Constructor no longer accepts non-initial messages; call `editMessage()` to enter edit mode
- `clear()` no longer exits edit mode; call `cancelEditMessage()` instead
- `cancelEditMessage()` is a no-op when no edit is active (safe to call unconditionally)

---

## Deleting Messages

```dart
// Delete for everyone (hard delete)
await channel.deleteMessage(message);

// Delete only for the current user (v10 new)
await channel.deleteMessageForMe(message.id);
```

`deleteMessageForMe` hides the message only for the calling user; other participants still see it. The `Message.deletedOnlyForMe` field reflects this state.

## Channel helpers (v10 new)

```dart
// True if distinct channel with exactly 2 members
final isDm = channel.isOneToOne;

// Stricter than before: memberCount > 2 || !isDistinct
final isGroup = channel.isGroup;
```

---

## ChannelsBloc (legacy BLoC pattern)

The older `ChannelsBloc` / `MessageSearchBloc` / `UsersBloc` pattern still exists but `StreamChannelListController` is preferred for new code.

```dart
// Wrap the subtree
ChannelsBloc(
  child: ChannelListCore(
    filter: Filter.in_('members', [userId]),
    sort: const [SortOption('last_message_at', direction: -1)],
    emptyBuilder: (_) => const Center(child: Text('No channels')),
    loadingBuilder: (_) => const Center(child: CircularProgressIndicator()),
    errorBuilder: (_, error) => Center(child: Text(error.toString())),
    listBuilder: (_, channels) => ListView.builder(
      itemCount: channels.length,
      itemBuilder: (_, index) => ChannelListTile(channel: channels[index]),
    ),
  ),
)
```

Use `StreamChannelListController` + `PagedValueListenableBuilder` for new code - it is more explicit and easier to test.

---

## Gotchas

- **`doInitialLoad()` must be called manually.** Unlike `stream_chat_flutter`'s `StreamChannelListView`, the core controller does not auto-fetch. Call it in `initState`.
- **Dispose all controllers.** `StreamChannelListController`, `StreamMessageComposerController` (was `StreamMessageInputController` in v9), and any manual stream subscriptions must be disposed in `State.dispose()`.
- **`channel.state` can be null before watch.** Call `await channel.watch()` or `await channel.query(...)` before reading `channel.state`.
- **`StreamChatCore` vs `StreamChat`.** `stream_chat_flutter_core` uses `StreamChatCore`; `stream_chat_flutter` uses `StreamChat`. Don't mix them in the same tree - pick one.
- **Message pagination is manual.** Call `channel.query(messagesPagination: ...)` when the user scrolls to the top - `StreamMessageListView` handles this automatically but your custom list does not.
- **Never create channels in `build`.** Channel objects should be stable references held in state, not recreated on every rebuild.
- **`sendReaction` signature changed in v10.** Pass a `Reaction` object: `channel.sendReaction(id, Reaction(type: 'like'))`. The old `(id, 'like')` string shorthand is removed.
- **`reactionCounts`/`reactionScores` removed in v10.** Use `message.reactionGroups` (`Map<String, ReactionGroup>`) instead.
- **`StreamChatCore` sets `recoverStateOnReconnect = false` in v10.** If your app manually watches channels outside a list controller, subscribe to `client.on(EventType.connectionRecovered)` to re-query them on reconnect.
- **`StreamMessageComposerController` edit mode changed in v10.** Do not pass a non-initial message to the constructor; call `controller.editMessage(msg)` instead. `clear()` no longer exits edit mode — call `cancelEditMessage()`.
- **`ClientState` collection getters are unmodifiable in v10.** Use `addChannels()`, `removeChannel()`, etc. instead of mutating the list directly.
