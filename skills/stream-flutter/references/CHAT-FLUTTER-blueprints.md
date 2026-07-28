# Chat stream_chat_flutter - Widget Blueprints

Load only the section you are implementing. For setup, client initialization, and gotchas, see [CHAT-FLUTTER.md](CHAT-FLUTTER.md).

---

## App Entry Point Blueprint

```dart
// main.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';
import 'package:stream_chat_localizations/stream_chat_localizations.dart';

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
      debugShowCheckedModeBanner: false,
      localizationsDelegates: GlobalStreamChatLocalizations.delegates,
      supportedLocales: const [Locale('en')],
      builder: (context, widget) => StreamChat(
        client: client,
        child: widget,
      ),
      home: const ChannelListPage(),
    );
  }
}
```

**Wiring:**

- `WidgetsFlutterBinding.ensureInitialized()` is required before any async work in `main`
- `await client.connectUser(...)` must complete before `runApp` so the app starts with an active session
- `StreamChat` in `builder` wraps every route in the app, not just `home`
- `GlobalStreamChatLocalizations.delegates` enables localized Stream widget strings

---

## Channel List Page Blueprint

> **Docs:** [StreamChannelListView](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/channel-list/stream-channel-list-view.md)

```dart
// channel_list_page.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

class ChannelListPage extends StatefulWidget {
  const ChannelListPage({super.key});

  @override
  State<ChannelListPage> createState() => _ChannelListPageState();
}

class _ChannelListPageState extends State<ChannelListPage> {
  late final _listController = StreamChannelListController(
    client: StreamChat.of(context).client,
    filter: Filter.in_(
      'members',
      [StreamChat.of(context).currentUser!.id],
    ),
    channelStateSort: const [SortOption.desc('last_message_at')],
    limit: 20,
  );

  @override
  void dispose() {
    _listController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Messages')),
    body: StreamChannelListView(
      controller: _listController,
      onChannelTap: (channel) => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => StreamChannel(
            channel: channel,
            child: const ChannelPage(),
          ),
        ),
      ),
    ),
  );
}
```

**Wiring:**

- `StreamChannelListController` must be `late final` on `State` - never created in `build`
- `Filter.in_('members', [userId])` restricts the list to channels the current user belongs to
- `SortOption.desc('last_message_at')` sorts by most recent activity
- `StreamChannel` wraps each destination so `ChannelPage` widgets can access channel state
- Call `_listController.dispose()` in `State.dispose()` to clean up WebSocket listeners

---

## Channel Page Blueprint

> **Docs:** [StreamMessageListView](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/stream-message-list-view.md) · [StreamChannelHeader](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-channel-header.md)

```dart
// channel_page.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

class ChannelPage extends StatefulWidget {
  const ChannelPage({super.key});

  @override
  State<ChannelPage> createState() => _ChannelPageState();
}

class _ChannelPageState extends State<ChannelPage> {
  final _composerController = StreamMessageComposerController();
  final _focusNode = FocusNode();

  @override
  void dispose() {
    _composerController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: const StreamChannelHeader(),
    body: Column(
      children: [
        Expanded(
          child: StreamMessageListView(
            config: const StreamMessageListViewConfiguration(
              swipeToReply: true,
            ),
            threadBuilder: (_, parent) => ThreadPage(parent: parent!),
            onReplyTap: _reply,
            onEditMessageTap: _edit,
          ),
        ),
        StreamMessageComposer(
          messageComposerController: _composerController,
          focusNode: _focusNode,
          onQuotedMessageCleared: _composerController.clearQuotedMessage,
        ),
      ],
    ),
  );

  void _reply(Message message) {
    _composerController.quotedMessage = message;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  void _edit(Message message) {
    _composerController.editMessage(message);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }
}
```

**Wiring:**

- `StreamChannelHeader` reads channel name and state from the `StreamChannel` ancestor
- `StreamMessageListView` handles message loading, pagination, and reactions automatically
- `threadBuilder` (top-level) receives the parent message and returns the thread screen
- `config.swipeToReply: true` enables the swipe-to-quote gesture
- `onReplyTap` sets `quotedMessage` on the composer controller and focuses the input
- `onEditMessageTap` is the edit-mode mirror of `_reply`: `_composerController.editMessage(message)` loads the message text into the composer, then focus the input
- `StreamMessageComposer` is the composer widget; its controller parameter is `messageComposerController:`
- Dispose both `_composerController` and `_focusNode` in `dispose()`

---

## Thread Page Blueprint

```dart
// thread_page.dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

class ThreadPage extends StatelessWidget {
  const ThreadPage({super.key, required this.parent});

  final Message parent;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: StreamThreadHeader(parent: parent),
    body: Column(
      children: [
        Expanded(
          child: StreamMessageListView(parentMessage: parent),
        ),
        StreamMessageComposer(
          messageComposerController: StreamMessageComposerController(
            message: Message(parentId: parent.id),
          ),
        ),
      ],
    ),
  );
}
```

**Wiring:**

- `StreamThreadHeader` shows the parent message context in the app bar
- `parentMessage: parent` tells `StreamMessageListView` to show thread replies only
- `StreamMessageComposerController(message: Message(parentId: parent.id))` pre-configures the composer to send replies into the thread

---

## Custom Theme Blueprint

> **Docs:** [StreamChat & Theming](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-chat-and-theming.md)

Base colors come from your app's Material 3 `ColorScheme`. Set that on `MaterialApp`, then pass `StreamChatThemeData` to `StreamChat` (via `themeData:`) only to override specific components.

```dart
MaterialApp(
  theme: ThemeData(
    colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF005FFF)),
    useMaterial3: true,
  ),
  builder: (context, widget) => StreamChat(
    client: client,
    themeData: StreamChatThemeData(
      messageListViewTheme: const StreamMessageListViewThemeData(
        backgroundColor: Color(0xFFF7F7F8),
      ),
      channelListItemTheme: const StreamChannelListItemThemeData(
        titleStyle: TextStyle(
          fontWeight: FontWeight.w600,
          fontSize: 14,
        ),
      ),
    ),
    child: widget,
  ),
  home: const ChannelListPage(),
)
```

**Wiring:**

- The whole UI's palette derives from the ambient Material `ColorScheme` — recolor by customizing `ThemeData` on `MaterialApp`
- `StreamChatThemeData` is passed via `themeData:` and overrides individual component themes
- Component slots: `channelHeaderTheme` / `channelListHeaderTheme` / `threadHeaderTheme` (`StreamAppBarThemeData`), `messageListViewTheme` (`StreamMessageListViewThemeData`), `channelListItemTheme` (`StreamChannelListItemThemeData`), `quotedMessageTheme`, plus thread/voice/poll themes
- Unset properties fall back to SDK defaults
- Read the resolved theme with `StreamChatTheme.of(context)`

---

## Custom Channel List Item Blueprint

Replace individual tiles using `itemBuilder` while keeping the default tap handling:

```dart
StreamChannelListView(
  controller: _listController,
  onChannelTap: _onChannelTap,
  itemBuilder: (context, channels, index, defaultWidget) {
    final channel = channels[index];
    final lastMessage = channel.state?.lastMessage;

    return ListTile(
      leading: StreamChannelAvatar(channel: channel),
      title: StreamChannelName(channel: channel),
      subtitle: lastMessage != null
          ? Text(
              lastMessage.text ?? '',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.grey),
            )
          : null,
      trailing: channel.state?.unreadCount != null &&
              channel.state!.unreadCount > 0
          ? Badge(
              label: Text('${channel.state!.unreadCount}'),
            )
          : null,
      onTap: () => _onChannelTap(channel),
    );
  },
)
```

**Wiring:**

- `StreamChannelAvatar` renders the channel's avatar (auto-generated from members if no image is set)
- `StreamChannelName` renders the channel display name, falling back to member names for DMs
- `defaultWidget.copyWith(selected: true)` preserves the default layout with a selection highlight (useful for split-view)
- `onChannelTap` at the controller level and `onTap` inside `itemBuilder` should call the same handler

---

## Split View Blueprint (tablet / desktop)

```dart
class SplitView extends StatefulWidget {
  const SplitView({super.key});

  @override
  State<SplitView> createState() => _SplitViewState();
}

class _SplitViewState extends State<SplitView> {
  Channel? _selectedChannel;

  @override
  Widget build(BuildContext context) => Row(
    children: [
      Expanded(
        child: ChannelListPage(
          onChannelTap: (channel) => setState(() => _selectedChannel = channel),
          selectedChannel: _selectedChannel,
        ),
      ),
      Expanded(
        flex: 2,
        child: _selectedChannel != null
            ? StreamChannel(
                key: ValueKey(_selectedChannel!.cid),
                channel: _selectedChannel!,
                child: const ChannelPage(),
              )
            : const Center(child: Text('Select a channel')),
      ),
    ],
  );
}
```

**Wiring:**

- `ValueKey(_selectedChannel!.cid)` forces `StreamChannel` to rebuild when the selected channel changes, preventing stale message lists
- `ChannelListPage` receives `selectedChannel` to highlight the active item (passed to `defaultWidget.copyWith(selected: ...)` in `itemBuilder`)
- Use `Expanded(flex: 2, ...)` to give the message list 2/3 of the available width

---

## Login / Connect User Blueprint

Show a login screen before connecting. Call `connectUser` once per session - not on every screen appear.

```dart
class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.onLogin});

  final VoidCallback onLogin;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _userIdController = TextEditingController();
  bool _isLoading = false;
  String? _error;

  @override
  void dispose() {
    _userIdController.dispose();
    super.dispose();
  }

  Future<void> _connect() async {
    if (_userIdController.text.trim().isEmpty) return;
    setState(() { _isLoading = true; _error = null; });

    try {
      final client = StreamChat.of(context).client;
      final userId = _userIdController.text.trim();

      // Fetch token from your backend
      final response = await http.get(
        Uri.parse('https://your-backend.com/stream-token?user_id=$userId'),
      );
      final token = response.body.trim();

      await client.connectUser(User(id: userId), token);
      widget.onLogin();
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          TextField(
            controller: _userIdController,
            decoration: const InputDecoration(labelText: 'User ID'),
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _connect(),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_error!, style: const TextStyle(color: Colors.red)),
            ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isLoading ? null : _connect,
            child: _isLoading
                ? const CircularProgressIndicator()
                : const Text('Connect'),
          ),
        ],
      ),
    ),
  );
}
```

**Wiring:**

- `StreamChat.of(context).client` accesses the already-created client from the widget tree
- `connectUser` is async - always `await` it
- Check `mounted` before calling `setState` after an async gap to avoid "setState after dispose"

---

## State Layer - StreamBuilder Blueprint

Use `StreamBuilder` for reactive channel state without the full message list widget:

```dart
StreamBuilder<List<Member>>(
  stream: StreamChannel.of(context).channel.state!.membersStream,
  initialData: StreamChannel.of(context).channel.state!.members,
  builder: (context, snapshot) {
    final members = snapshot.data ?? [];
    return ListView.builder(
      itemCount: members.length,
      itemBuilder: (context, index) => ListTile(
        title: Text(members[index].user?.name ?? members[index].userId),
      ),
    );
  },
)
```

Common streams on `channel.state`:

| Stream               | Data type                     |
| -------------------- | ----------------------------- |
| `messagesStream`     | `List<Message>`               |
| `membersStream`      | `List<Member>`                |
| `lastMessageStream`  | `Message?`                    |
| `typingEventsStream` | `Map<User, Event>` |
| `unreadCountStream`  | `int`                         |
| `readStream`         | `List<Read>`                  |
