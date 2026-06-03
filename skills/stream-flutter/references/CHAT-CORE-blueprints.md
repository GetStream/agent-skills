# Chat stream_chat_flutter_core - Widget Blueprints

Load only the section you are implementing. For setup, controllers, and gotchas, see [CHAT-CORE.md](CHAT-CORE.md).

---

## App Entry Point Blueprint

```dart
// main.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter_core/stream_chat_flutter_core.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final client = StreamChatClient(
    'your_api_key',
    logLevel: Level.OFF,
  );

  await client.connectUser(
    User(id: 'alice', name: 'Alice'),
    'your_user_token',
  );

  runApp(MyApp(client: client));
}

class MyApp extends StatelessWidget {
  const MyApp({super.key, required this.client});

  final StreamChatClient client;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      builder: (context, widget) => StreamChatCore(
        client: client,
        child: widget,
      ),
      home: const ChannelListPage(),
    );
  }
}
```

**Wiring:**
- `stream_chat_flutter_core` exports `StreamChatClient` from `stream_chat` - import only `stream_chat_flutter_core`
- `StreamChatCore` (not `StreamChat`) is the inherited widget for the core package
- `await client.connectUser(...)` before `runApp` - same as the UI package

---

## Custom Channel List Blueprint

```dart
// channel_list_page.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter_core/stream_chat_flutter_core.dart';

class ChannelListPage extends StatefulWidget {
  const ChannelListPage({super.key});

  @override
  State<ChannelListPage> createState() => _ChannelListPageState();
}

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

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Messages')),
    body: PagedValueListenableBuilder<int, Channel>(
      valueListenable: _controller,
      builder: (context, value, child) {
        return value.when(
          (channels, nextPageKey, error) {
            if (channels.isEmpty) {
              return const Center(child: Text('No channels yet.'));
            }
            return RefreshIndicator(
              onRefresh: _controller.refresh,
              child: ListView.builder(
                itemCount: channels.length + (nextPageKey != null ? 1 : 0),
                itemBuilder: (context, index) {
                  if (index == channels.length) {
                    _controller.loadMore(nextPageKey!);
                    return const Center(child: CircularProgressIndicator());
                  }
                  final channel = channels[index];
                  return _ChannelTile(
                    channel: channel,
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => StreamChannel(
                          channel: channel,
                          child: const ChannelPage(),
                        ),
                      ),
                    ),
                  );
                },
              ),
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e) => Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('Error: ${e.message}'),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: _controller.retry,
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        );
      },
    ),
  );
}

class _ChannelTile extends StatelessWidget {
  const _ChannelTile({required this.channel, required this.onTap});

  final Channel channel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<Message?>(
      stream: channel.state?.lastMessageStream,
      initialData: channel.state?.lastMessage,
      builder: (context, snapshot) {
        return ListTile(
          title: Text(
            channel.name ?? channel.id ?? 'Channel',
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          subtitle: Text(
            snapshot.data?.text ?? 'No messages yet',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          trailing: StreamBuilder<int>(
            stream: channel.state?.unreadCountStream,
            initialData: channel.state?.unreadCount,
            builder: (context, snapshot) {
              final count = snapshot.data ?? 0;
              if (count == 0) return const SizedBox.shrink();
              return Badge(label: Text('$count'));
            },
          ),
          onTap: onTap,
        );
      },
    );
  }
}
```

**Wiring:**
- `_controller.doInitialLoad()` in `initState` triggers the first page fetch
- `PagedValueListenableBuilder.value.when(...)` covers loaded / loading / error states
- Sentinel item at `index == channels.length` triggers `loadMore` when scrolled into view
- `_controller.refresh()` on `RefreshIndicator` pulls fresh data
- `_controller.retry()` on error retries the last failed request

---

## Custom Channel Page Blueprint

```dart
// channel_page.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter_core/stream_chat_flutter_core.dart';

class ChannelPage extends StatefulWidget {
  const ChannelPage({super.key});

  @override
  State<ChannelPage> createState() => _ChannelPageState();
}

class _ChannelPageState extends State<ChannelPage> {
  final _textController = TextEditingController();
  final _scrollController = ScrollController();
  bool _isLoadingMore = false;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    // Watch the channel to load initial messages and subscribe to events
    WidgetsBinding.instance.addPostFrameCallback((_) {
      StreamChannel.of(context).channel.watch();
    });
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      _loadMore();
    }
  }

  Future<void> _loadMore() async {
    if (_isLoadingMore) return;
    final channel = StreamChannel.of(context).channel;
    final messages = channel.state!.messages;
    if (messages.isEmpty) return;
    setState(() => _isLoadingMore = true);
    await channel.query(
      messagesPagination: PaginationParams(
        lessThan: messages.first.id,
        limit: 20,
      ),
    );
    if (mounted) setState(() => _isLoadingMore = false);
  }

  Future<void> _sendMessage() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    final channel = StreamChannel.of(context).channel;
    await channel.sendMessage(Message(text: text));
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final channel = StreamChannel.of(context).channel;

    return Scaffold(
      appBar: AppBar(
        title: Text(channel.name ?? channel.id ?? 'Channel'),
      ),
      body: Column(
        children: [
          if (_isLoadingMore)
            const LinearProgressIndicator(),
          Expanded(
            child: StreamBuilder<List<Message>>(
              stream: channel.state!.messagesStream,
              initialData: channel.state!.messages,
              builder: (context, snapshot) {
                final messages = (snapshot.data ?? []).reversed.toList();
                return ListView.builder(
                  controller: _scrollController,
                  reverse: true,
                  itemCount: messages.length,
                  itemBuilder: (context, index) {
                    final message = messages[index];
                    final isOwn = message.user?.id ==
                        StreamChatCore.of(context).currentUser?.id;
                    return _MessageBubble(message: message, isOwn: isOwn);
                  },
                );
              },
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      decoration: const InputDecoration(
                        hintText: 'Write a message...',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(
                          horizontal: 12, vertical: 8,
                        ),
                      ),
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    icon: const Icon(Icons.send),
                    onPressed: _sendMessage,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message, required this.isOwn});

  final Message message;
  final bool isOwn;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isOwn ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.7,
        ),
        decoration: BoxDecoration(
          color: isOwn
              ? Theme.of(context).colorScheme.primary
              : Theme.of(context).colorScheme.surfaceContainerHigh,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!isOwn)
              Text(
                message.user?.name ?? message.user?.id ?? '',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: Theme.of(context).colorScheme.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            Text(
              message.text ?? '',
              style: TextStyle(
                color: isOwn
                    ? Theme.of(context).colorScheme.onPrimary
                    : Theme.of(context).colorScheme.onSurface,
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
- `channel.watch()` in `addPostFrameCallback` loads initial messages and subscribes to real-time events
- `StreamBuilder<List<Message>>` re-renders the list on every new message
- `messages.reversed.toList()` + `reverse: true` on `ListView.builder` shows newest messages at the bottom
- Scroll listener triggers `loadMore` when the user reaches the top (index 0 in reversed order)
- `channel.query(messagesPagination: PaginationParams(lessThan: oldestId, limit: 20))` fetches older messages

---

## Typing Indicator Blueprint

```dart
StreamBuilder<Map<User, Event>>(
  stream: StreamChannel.of(context).channel.state?.typingEventsStream,
  initialData: StreamChannel.of(context).channel.state?.typingEvents,
  builder: (context, snapshot) {
    final typingUsers = snapshot.data?.keys.toList() ?? [];
    if (typingUsers.isEmpty) return const SizedBox.shrink();
    final names = typingUsers.map((u) => u.name ?? u.id).join(', ');
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Text(
        '$names ${typingUsers.length == 1 ? 'is' : 'are'} typing...',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: Theme.of(context).colorScheme.outline,
          fontStyle: FontStyle.italic,
        ),
      ),
    );
  },
)
```

**Send typing events from the input field:**

```dart
TextField(
  controller: _textController,
  onChanged: (text) {
    if (text.isNotEmpty) {
      StreamChannel.of(context).channel.keyStroke();
    } else {
      StreamChannel.of(context).channel.stopTyping();
    }
  },
)
```

---

## Unread Count Badge Blueprint

Display unread channel counts using the current user's unread state:

```dart
StreamBuilder<OwnUser?>(
  stream: StreamChatCore.of(context).client.state.currentUserStream,
  initialData: StreamChatCore.of(context).client.state.currentUser,
  builder: (context, snapshot) {
    final totalUnread = snapshot.data?.totalUnreadCount ?? 0;
    if (totalUnread == 0) return const Icon(Icons.chat_bubble_outline);
    return Badge(
      label: Text('$totalUnread'),
      child: const Icon(Icons.chat_bubble),
    );
  },
)
```

---

## Message Search Blueprint

```dart
class _MessageSearchPageState extends State<MessageSearchPage> {
  late final _controller = StreamMessageSearchListController(
    client: StreamChatCore.of(context).client,
    filter: Filter.in_('members', [StreamChatCore.of(context).currentUser!.id]),
    searchQuery: '',
    sort: const [SortOption.desc('created_at')],
    messageFilter: Filter.equal('type', 'regular'),
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

  void _search(String query) {
    _controller.searchQuery = query;
    _controller.doInitialLoad();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: TextField(
        decoration: const InputDecoration(
          hintText: 'Search messages...',
          border: InputBorder.none,
        ),
        onChanged: _search,
      ),
    ),
    body: PagedValueListenableBuilder<int, GetMessageResponse>(
      valueListenable: _controller,
      builder: (context, value, child) {
        return value.when(
          (results, nextPageKey, error) => ListView.builder(
            itemCount: results.length,
            itemBuilder: (context, index) {
              final result = results[index];
              return ListTile(
                title: Text(result.message.text ?? ''),
                subtitle: Text(result.channel?.name ?? ''),
              );
            },
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e) => Center(child: Text('Search error: ${e.message}')),
        );
      },
    ),
  );
}
```

**Wiring:**
- `StreamMessageSearchListController` mirrors `StreamChannelListController` in structure
- Update `searchQuery` and call `doInitialLoad()` on each new search term
- Results are `GetMessageResponse` objects with `.message` and `.channel` fields
