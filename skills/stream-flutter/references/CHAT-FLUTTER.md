# Chat - stream_chat_flutter Setup & Integration

`stream_chat_flutter` provides pre-built Flutter widgets for building rich messaging UIs. This file covers package installation, client setup, authentication, theming, customization, and gotchas. For widget blueprints, see [CHAT-FLUTTER-blueprints.md](CHAT-FLUTTER-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

- **Blueprint** - Widget structure and initialization
- **Wiring** - SDK calls for each component, exact property paths
- **Requirements** - Platform setup, SDK version, Flutter version

## Quick ref

- **Package:** `stream_chat_flutter` via pub.dev
- **Version:** `^10.0.0` (v10 branch: https://github.com/GetStream/stream-chat-flutter/tree/v10.0.0)
- **Dart SDK:** `^3.10.0` | **Flutter:** `>=3.38.1`
- **First:** Install -> platform setup -> client init -> `StreamChat` widget -> `connectUser` -> show widgets
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/chat/docs/sdk/flutter/`

Full widget blueprints: [CHAT-FLUTTER-blueprints.md](CHAT-FLUTTER-blueprints.md) - load only the section you are implementing.

---

## App Integration

### Installation

```yaml
# pubspec.yaml
dependencies:
  stream_chat_flutter: ^10.0.0
  stream_chat_localizations: ^10.0.0  # optional - localized UI strings
```

```bash
flutter pub get
```

For platform-specific setup (Android permissions, iOS Info.plist keys, Web index.html, macOS entitlements) see [`builder.md`](../builder.md).

### Client Initialization

Initialize once before `runApp`. **Never** create `StreamChatClient` inside a `build` method or `StatelessWidget`.

```dart
import 'package:flutter/material.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final client = StreamChatClient(
    'your_api_key',
    logLevel: Level.OFF,
  );

  await client.connectUser(
    User(id: 'user-id', name: 'User Name'),
    'your_user_token',
  );

  runApp(MyApp(client: client));
}
```

### StreamChat Widget

`StreamChat` must wrap the widget tree before any Stream SDK widget renders. Place it in `MaterialApp`'s `builder`:

```dart
class MyApp extends StatelessWidget {
  const MyApp({super.key, required this.client});

  final StreamChatClient client;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      builder: (context, widget) => StreamChat(
        client: client,
        child: widget,
      ),
      home: const ChannelListPage(),
    );
  }
}
```

To add localization and theming at the same entry point:

```dart
MaterialApp(
  localizationsDelegates: GlobalStreamChatLocalizations.delegates,
  supportedLocales: const [Locale('en'), Locale('fr'), Locale('es')],
  builder: (context, widget) => StreamChat(
    client: client,
    streamChatThemeData: StreamChatThemeData(
      colorTheme: StreamColorTheme.light(
        accentPrimary: const Color(0xFF005FFF),
      ),
    ),
    child: widget,
  ),
  home: const ChannelListPage(),
)
```

### User Authentication

**Static token (dev / demo):**

```dart
await client.connectUser(
  User(id: 'alice', name: 'Alice'),
  'your_static_token',
);
```

**Token from backend (production):**

```dart
final response = await http.get(
  Uri.parse('https://your-backend.com/stream-token?user_id=alice'),
);
final token = response.body.trim();

await client.connectUser(
  User(id: 'alice', name: 'Alice'),
  token,
);
```

**Disconnect on logout:**

```dart
await client.disconnectUser();
```

Always `await` disconnect before connecting the next user.

---

## Core Widgets

### StreamChannelListView

Displays a scrollable list of channels the user is a member of. Requires a `StreamChannelListController`.

```dart
class ChannelListPage extends StatefulWidget {
  const ChannelListPage({super.key});

  @override
  State<ChannelListPage> createState() => _ChannelListPageState();
}

class _ChannelListPageState extends State<ChannelListPage> {
  late final _controller = StreamChannelListController(
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
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: StreamChannelListView(
      controller: _controller,
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

`StreamChannelListController` is a `late final` field - never create it in `build`. Dispose it in `dispose()`.

### StreamChannelHeader

A pre-built `AppBar`-style header for channel screens. Use it as a `Scaffold`'s `appBar`:

```dart
Scaffold(
  appBar: StreamChannelHeader(),
  body: ...,
)
```

`StreamChannelHeader` reads channel state from the nearest `StreamChannel` in the tree.

### StreamMessageListView

Displays the list of messages in the current channel. Must be a descendant of `StreamChannel`.

```dart
Scaffold(
  appBar: const StreamChannelHeader(),
  body: Column(
    children: [
      Expanded(child: StreamMessageListView()),
      const StreamMessageInput(),
    ],
  ),
)
```

In v10, many `StreamMessageListView` parameters were moved into two dedicated objects:

- **`StreamMessageListViewConfiguration`** (passed as `config:`) — boolean flags like `swipeToReply`, `markReadWhenAtTheBottom`, `enableDraftMessages`, etc.
- **`StreamMessageListViewBuilders`** (passed as `builders:`) — builder callbacks like `messageBuilder`, `threadBuilder`, `loadingBuilder`, `emptyBuilder`, etc.

```dart
StreamMessageListView(
  config: const StreamMessageListViewConfiguration(
    swipeToReply: true,
    markReadWhenAtTheBottom: true,
  ),
  builders: StreamMessageListViewBuilders(
    threadBuilder: (context, parent) => ThreadPage(parent: parent!),
  ),
)
```

> Simple flags like `onReplyTap` may still be top-level parameters — check the widget signature for the version you're on. When in doubt, use the `config:` / `builders:` path for any flag that is no longer accepted at the top level.

### StreamMessageInput

The composer widget for sending messages, attachments, and voice recordings. Must be a descendant of `StreamChannel`.

Voice recording is **enabled by default** in v10 — no need to pass `enableVoiceRecording: true`.

```dart
StreamMessageInput()
```

**With `StreamMessageComposerController` for quote-reply:**

`StreamMessageInputController` was renamed to `StreamMessageComposerController` in v10. The parameter on `StreamMessageInput` changed from `messageInputController` to `messageComposerController`.

```dart
class _ChannelPageState extends State<ChannelPage> {
  late final _composerController = StreamMessageComposerController();
  final _focusNode = FocusNode();

  @override
  void dispose() {
    _composerController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Expanded(
        child: StreamMessageListView(
          config: const StreamMessageListViewConfiguration(
            swipeToReply: true,
          ),
          onReplyTap: _reply,
        ),
      ),
      StreamMessageInput(
        messageComposerController: _composerController,
        focusNode: _focusNode,
        onQuotedMessageCleared: _composerController.clearQuotedMessage,
      ),
    ],
  );

  void _reply(Message message) {
    _composerController.quotedMessage = message;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }
}
```

### StreamThreadHeader and Thread View

For threading, use `StreamThreadHeader` in the thread screen's `appBar` and pass `parentMessage` to `StreamMessageListView`:

```dart
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
        StreamMessageInput(
          messageComposerController: StreamMessageComposerController(
            message: Message(parentId: parent.id),
          ),
        ),
      ],
    ),
  );
}
```

Wire the thread navigation in `StreamMessageListView` via `builders.threadBuilder` (v10):

```dart
StreamMessageListView(
  builders: StreamMessageListViewBuilders(
    threadBuilder: (context, parent) => ThreadPage(parent: parent!),
  ),
)
```

---

## Theming

`StreamChatThemeData` customizes the appearance of all Stream widgets. Pass it to the `StreamChat` widget.

```dart
StreamChat(
  client: client,
  streamChatThemeData: StreamChatThemeData(
    colorTheme: StreamColorTheme.light(
      accentPrimary: const Color(0xFF005FFF),
    ),
    channelHeaderTheme: const StreamChannelHeaderThemeData(
      color: Color(0xFF005FFF),
      titleStyle: TextStyle(
        color: Colors.white,
        fontWeight: FontWeight.bold,
      ),
    ),
    channelPreviewTheme: StreamChannelPreviewThemeData(
      unreadCounterColor: Theme.of(context).colorScheme.error,
    ),
  ),
  child: widget,
)
```

**Key theme objects:**

| Object | What it controls |
|---|---|
| `StreamColorTheme` | Accent colors, backgrounds, borders across all widgets |
| `StreamChannelHeaderThemeData` | Channel screen header colors and typography |
| `StreamMessageListViewThemeData` | Message list background and spacing |

> **v10 breaking change:** `StreamMessageThemeData`, `StreamMessageInputThemeData`, and `StreamChannelPreviewThemeData` were **removed** in v10. Do not use them — check the [theming docs](https://getstream.io/chat/docs/sdk/flutter/stream_chat_flutter/stream_chat_and_theming/) for the replacement tokens.

> **Never guess `StreamChatThemeData` property names.** Use only tokens listed above or fetched from the [theming docs](https://getstream.io/chat/docs/sdk/flutter/stream_chat_flutter/stream_chat_and_theming/). Names look guessable but are often wrong.

---

## Customizing the Channel List Item

Override individual tiles via `itemBuilder` on `StreamChannelListView`:

```dart
StreamChannelListView(
  controller: _controller,
  itemBuilder: (context, channels, index, defaultWidget) {
    final channel = channels[index];
    return ListTile(
      title: Text(channel.name ?? 'Channel'),
      subtitle: Text(
        channel.state?.lastMessage?.text ?? '',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      onTap: () { /* navigate */ },
    );
  },
)
```

`defaultWidget` is the built-in `StreamChannelListTile` - call `defaultWidget.copyWith(...)` to modify it without replacing it entirely.

---

## Filters and Sorting

Pass `Filter` and `SortOption` to `StreamChannelListController`:

```dart
StreamChannelListController(
  client: client,
  filter: Filter.and([
    Filter.equal('type', 'messaging'),
    Filter.in_('members', [currentUserId]),
  ]),
  channelStateSort: const [
    SortOption.desc('last_message_at'),
  ],
  limit: 20,
)
```

Common filters:

| Filter | Example |
|---|---|
| User is a member | `Filter.in_('members', [userId])` |
| Channel type | `Filter.equal('type', 'messaging')` |
| Combined | `Filter.and([...])` |

---

## Creating Channels

```dart
final channel = client.channel(
  'messaging',
  id: 'general',
  extraData: {
    'name': 'General',
    'members': ['alice', 'bob'],
  },
);
await channel.create();
```

Or use `watch()` to create-and-subscribe in one call:

```dart
await channel.watch();
```

---

## ChatClientConfig options

All config changes must happen before `StreamChatClient(...)` is called.

```dart
// Logging (disable in production)
final client = StreamChatClient(
  'your_api_key',
  logLevel: Level.INFO,        // Level.OFF in production
);
```

---

---

## v10 Breaking Changes Summary

| v9 | v10 |
|---|---|
| `StreamMessageInputController` | `StreamMessageComposerController` |
| `messageInputController:` param | `messageComposerController:` param |
| `StreamMessageWidget` | `StreamMessageItem` |
| `StreamMessageAnnotations` | `StreamMessageHeader` |
| `StreamMessageMetadata` | `StreamMessageFooter` |
| `StreamMessageComposerInput` | `StreamMessageComposerInputCenter` |
| `StreamAttachmentPackage` | `StreamMediaGalleryAttachment` |
| `StreamFullScreenMedia` | `StreamMediaGalleryPreview` |
| `StreamGalleryHeader`/`Footer` | `StreamMediaGalleryPreviewHeader`/`Footer` |
| `StreamPollOptionsDialog` | `StreamPollOptionsSheet` |
| `StreamPollResultsDialog` | `StreamPollResultsSheet` |
| `StreamPollCreatorDialog` | `StreamPollCreatorSheet` |
| `threadBuilder:` top-level | `builders: StreamMessageListViewBuilders(threadBuilder:)` |
| `StreamMessageThemeData` | **Removed** |
| `StreamMessageInputThemeData` | **Removed** |
| `StreamChannelPreviewThemeData` | **Removed** |
| `StreamDraftListView`/`Tile` | **Removed** (draft messages managed internally) |
| `enableVoiceRecording: true` | **Default true** - no longer required |
| `enforceUniqueReactions: true` | **Default false** in v10 |
| `draftMessagesEnabled: false` | **Default true** in v10 |

**New in v10:**
- `messageLeading`, `messageHeader`, `messageFooter` factory slots on `StreamMessageListView` builders for granular widget overrides
- `BlockUser`/`UnblockUser` default message actions
- `StreamMediaGalleryPreview` — cross-platform media gallery with thumbnail grid and video player
- Slow-mode UI: input disabled with countdown during slow mode periods

---

## Gotchas

- **Never use dev tokens in production.** A development token disables token auth and allows any client to impersonate any user.
- **Never store your Stream secret in the app.** Secrets on-device can be extracted and enable destructive actions on your app instance.
- **Always `await client.disconnectUser()` before connecting another user.** Connecting a new user while disconnect is in progress risks state corruption.
- **`StreamChat` must appear in the widget tree before any Stream widget renders.** Rendering a widget without `StreamChat` in the ancestor tree causes a runtime error.
- **`StreamChannelListController` must be disposed.** Failing to call `dispose()` leaks WebSocket listeners.
- **Never create `StreamChannelListController` in `build`.** It must be a `late final` field on `State` - a new controller on every rebuild resets pagination and breaks the list.
- **`connectUser` is async - always `await` it before `runApp`.** Starting the app before the user is connected shows an empty or errored channel list.
- **`StreamMessageComposerController` must be disposed** (renamed from `StreamMessageInputController` in v10). Always dispose it alongside the `FocusNode` in `State.dispose()`.
- **`StreamChannelListView` handles pagination automatically.** Do not manually call `loadMore` - the built-in infinite scroll triggers it.
- **`StreamChannel` scopes channel context.** Every channel screen must be wrapped with `StreamChannel(channel: channel, child: ...)` so descendant widgets can read channel state.
- **`StreamMessageListView` config split in v10.** Flags like `swipeToReply` moved to `config: StreamMessageListViewConfiguration(...)` and builders moved to `builders: StreamMessageListViewBuilders(...)`. Passing them at the top level is a compile error in v10.
