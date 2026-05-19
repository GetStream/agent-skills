# Chat - stream_chat_flutter_core Setup & Integration

`stream_chat_flutter_core` provides business logic and data controllers without any pre-built UI. Use it when you need full control over your widget layer. This file covers setup, controllers, reactive state, and gotchas. For widget blueprints, see [CHAT-CORE-blueprints.md](CHAT-CORE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

## Quick ref

- **Package:** `stream_chat_flutter_core` via pub.dev
- **Version:** `^10.0.0-beta.13`
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
  stream_chat_flutter_core: ^10.0.0-beta.13
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

```dart
// Add a reaction
await channel.sendReaction(messageId, 'like');

// Remove a reaction
await channel.deleteReaction(messageId, 'like');
```

---

## Pagination (messages)

```dart
// Load older messages (call when user scrolls to top)
await channel.query(
  messagesPagination: PaginationParams(lessThan: oldestMessageId, limit: 20),
);
```

---

## StreamMessageInputController

Available in `stream_chat_flutter_core` for managing compose state independently of any UI:

```dart
final inputController = StreamMessageInputController();

// Set quoted message for reply
inputController.quotedMessage = message;

// Clear quote
inputController.clearQuotedMessage();

// Current text
final text = inputController.text;

// Always dispose
inputController.dispose();
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
- **Dispose all controllers.** `StreamChannelListController`, `StreamMessageInputController`, and any manual stream subscriptions must be disposed in `State.dispose()`.
- **`channel.state` can be null before watch.** Call `await channel.watch()` or `await channel.query(...)` before reading `channel.state`.
- **`StreamChatCore` vs `StreamChat`.** `stream_chat_flutter_core` uses `StreamChatCore`; `stream_chat_flutter` uses `StreamChat`. Don't mix them in the same tree - pick one.
- **Message pagination is manual.** Call `channel.query(messagesPagination: ...)` when the user scrolls to the top - `StreamMessageListView` handles this automatically but your custom list does not.
- **Never create channels in `build`.** Channel objects should be stable references held in state, not recreated on every rebuild.
