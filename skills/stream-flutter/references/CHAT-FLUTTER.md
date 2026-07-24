# Chat - stream_chat_flutter Setup & Integration

`stream_chat_flutter` provides pre-built Flutter widgets for building rich messaging UIs. This file covers package installation, client setup, authentication, theming, customization, and gotchas. For widget blueprints, see [CHAT-FLUTTER-blueprints.md](CHAT-FLUTTER-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

- **Blueprint** - Widget structure and initialization
- **Wiring** - SDK calls for each component, exact property paths
- **Requirements** - Platform setup, SDK version, Flutter version

## Quick ref

- **Package:** `stream_chat_flutter` via pub.dev
- **Version:** `^10.0.0`
- **Dart SDK:** `^3.11.0` | **Flutter:** `>=3.41.0`
- **First:** Install -> platform setup -> client init -> `StreamChat` widget -> `connectUser` -> show widgets
- **Per feature:** Jump to the relevant section or blueprint when implementing a screen. This file covers core widgets, theming, filters, **member/user lists, message search, composer flags (voice/polls/drafts)**, creating channels, reactions, and **permissions**.
- **Production concerns** — push notifications, offline/local persistence, connection lifecycle & backgrounding — live in [`CHAT-ADVANCED-FLUTTER.md`](CHAT-ADVANCED-FLUTTER.md) + [`CHAT-ADVANCED-FLUTTER-blueprints.md`](CHAT-ADVANCED-FLUTTER-blueprints.md) (package-agnostic). Shared client/auth wiring is in [`../sdk.md`](../sdk.md).
- **Docs:** If you can't find information here, check the docs: `https://getstream.io/chat/docs/sdk/flutter/`

Full widget blueprints: [CHAT-FLUTTER-blueprints.md](CHAT-FLUTTER-blueprints.md) - load only the section you are implementing.

> **Prerequisite — the existing project must already be on `stream_chat_flutter` v10.** This skill targets the v10 API exclusively. If the integrator's `pubspec.yaml` (or `pubspec.lock`) pins a 9.x or earlier version, **stop and tell the user they must migrate to v10 first** — the widget names, controllers, theming model, and reaction/delete APIs all changed and this skill does not cover the migration path. Point them at the upgrade docs and resume only once the project resolves `stream_chat_flutter: ^10.0.0`.

---

## App Integration

### Installation

> **Docs:** [Installation](https://getstream.io/chat/docs/sdk/flutter/basics/installation.md)

```yaml
# pubspec.yaml
dependencies:
  stream_chat_flutter: ^10.0.0
  stream_chat_localizations: ^10.0.0 # optional - localized UI strings
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

`logLevel` takes a `Level` from `package:logging`. It defaults to `Level.WARNING`; use `Level.OFF` in production.

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
    themeData: StreamChatThemeData(),
    child: widget,
  ),
  home: const ChannelListPage(),
)
```

The theme parameter is `themeData:` (a `StreamChatThemeData`). See [Theming](#theming).

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

> **Docs:** [StreamChannelListView](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/channel-list/stream-channel-list-view.md)

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

`StreamChannelListController` is a `late final` field - never create it in `build`. Dispose it in `dispose()`. Its sort parameter is `channelStateSort:` (a `List<SortOption<ChannelState>>`).

Unlike `StreamMessageListView` (which groups its slots under `builders:`), `StreamChannelListView` takes its placeholder slots as **top-level callbacks**: `emptyBuilder`, `loadingBuilder`, `errorBuilder`, `itemBuilder`, `separatorBuilder`, `listBuilder`. Use `emptyBuilder: (context) => ...` for the "no channels yet" state (e.g. a CTA to create/discover a group).

### StreamChannelHeader

> **Docs:** [StreamChannelHeader](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-channel-header.md)

A pre-built `AppBar`-style header for channel screens. Use it as a `Scaffold`'s `appBar`:

```dart
Scaffold(
  appBar: StreamChannelHeader(),
  body: ...,
)
```

`StreamChannelHeader` reads channel state from the nearest `StreamChannel` in the tree.

### StreamMessageListView

> **Docs:** [StreamMessageListView](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/stream-message-list-view.md)

Displays the list of messages in the current channel. Must be a descendant of `StreamChannel`.

```dart
Scaffold(
  appBar: const StreamChannelHeader(),
  body: Column(
    children: [
      Expanded(child: StreamMessageListView()),
      StreamMessageComposer(),
    ],
  ),
)
```

`StreamMessageListView` keeps a small set of top-level parameters and groups the rest into two dedicated objects:

- **Top-level:** `messageBuilder`, `parentMessage`, `threadBuilder`, `onReplyTap`, `onEditMessageTap`.
- **`config:` — `StreamMessageListViewConfiguration`** — behaviour flags such as `swipeToReply`, `markReadWhenAtTheBottom`, `showScrollToBottom`, `showUnreadCountOnScrollToBottom`, `showUnreadIndicator`, `highlightInitialMessage`, `showFloatingDateDivider`, `reverse`, `shrinkWrap`, `paginationLimit`.
- **`builders:` — `StreamMessageListViewBuilders`** — slot builders such as `empty`, `loading`, `error`, `header`, `footer`, `content`, `dateDivider`, `floatingDateDivider`, `threadSeparator`, `unreadMessagesSeparator`, `paginationLoadingIndicator`, `systemMessage`, `ephemeralMessage`, `moderatedMessage`.

```dart
StreamMessageListView(
  config: const StreamMessageListViewConfiguration(
    swipeToReply: true,
    markReadWhenAtTheBottom: true,
  ),
  builders: StreamMessageListViewBuilders(
    empty: (context) => const Center(child: Text('No messages yet')),
  ),
  threadBuilder: (context, parent) => ThreadPage(parent: parent!),
)
```

> The builder keys inside `StreamMessageListViewBuilders` are `empty` / `loading` / `error` (not `emptyBuilder` / `loadingBuilder`). `threadBuilder`, `parentMessage`, and `onReplyTap` stay at the top level.

### StreamMessageComposer

The composer widget for sending messages, attachments, and voice recordings. Must be a descendant of `StreamChannel`. The attachment picker is embedded inline inside the composer — there is no separate modal sheet to open.

Voice recording is enabled by default on the `StreamMessageComposer` **widget** (`enableVoiceRecording` defaults to `true`). **Caveat — the default flips on the props path:** on `MessageComposerProps` (the object handed to you when you override the composer through the component factory / the `.fromProps` path) the effective default is **`false`**, so a factory-overridden composer has **no** mic unless you set it. Detail: [`design-matching.md`](../design-matching.md) → Composer.

```dart
StreamMessageComposer()
```

**With `StreamMessageComposerController` for quote-reply:**

```dart
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
      StreamMessageComposer(
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

The controller parameter is `messageComposerController:`.

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

Wire the thread navigation from the channel screen via the top-level `threadBuilder`:

```dart
StreamMessageListView(
  threadBuilder: (context, parent) => ThreadPage(parent: parent!),
)
```

---

## Theming

> **Docs:** [StreamChat & Theming](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-chat-and-theming.md)

`StreamChatThemeData` customizes the appearance of all Stream widgets. Pass it to the `StreamChat` widget via `themeData:`.

`StreamChatThemeData` is a Material `ThemeExtension`. Base colors and typography are derived from the ambient Material 3 `ThemeData` (its `ColorScheme`) plus the Stream design system. To recolor the whole UI, customize your app's `ColorScheme` / `ThemeData`; to override individual components, pass the component theme objects below.

```dart
StreamChat(
  client: client,
  themeData: StreamChatThemeData(
    channelHeaderTheme: const StreamAppBarThemeData(),
    messageListViewTheme: const StreamMessageListViewThemeData(
      backgroundColor: Color(0xFFF7F7F8),
    ),
    channelListItemTheme: const StreamChannelListItemThemeData(
      titleStyle: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
    ),
  ),
  child: widget,
)
```

**Component theme slots on `StreamChatThemeData`:**

| Object                                                                                                                                                                                                                           | What it controls                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `channelHeaderTheme` / `channelListHeaderTheme` / `threadHeaderTheme` (`StreamAppBarThemeData`)                                                                                                                                  | Header app bars                                                       |
| `messageListViewTheme` (`StreamMessageListViewThemeData`)                                                                                                                                                                        | Message list background, image, highlight color                       |
| `channelListItemTheme` (`StreamChannelListItemThemeData`)                                                                                                                                                                        | Channel list tile title/subtitle/timestamp styles, background, border |
| `quotedMessageTheme` (`StreamQuotedMessageThemeData`)                                                                                                                                                                            | Quoted-message styling                                                |
| `threadListTileTheme`, `voiceRecordingAttachmentTheme`, and the poll themes (`pollCreatorTheme`, `pollInteractorTheme`, `pollOptionsSheetTheme`, `pollResultsSheetTheme`, `pollCommentsSheetTheme`, `pollOptionVotesSheetTheme`) | Their respective components                                           |

Read the resolved theme anywhere below `StreamChat` with `StreamChatTheme.of(context)`.

> **Never guess `StreamChatThemeData` property names.** Use only tokens listed above or fetched from the [theming docs](https://getstream.io/chat/docs/sdk/flutter/stream_chat_flutter/stream_chat_and_theming/). Names look guessable but are often wrong. There is no `colorTheme` / `StreamColorTheme`; colors come from the ambient Material `ColorScheme`.

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

The `itemBuilder` signature is `(context, channels, index, defaultWidget)`. `defaultWidget` is the built-in `StreamChannelListTile` - call `defaultWidget.copyWith(...)` to modify it without replacing it entirely.

---

## Filters and Sorting

> **Docs:** [Understanding Filters](https://getstream.io/chat/docs/sdk/flutter/guides/understanding-filters.md)

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

`SortOption` uses the named constructors `SortOption.desc('field')` / `SortOption.asc('field')`.

Common filters:

| Filter           | Example                             |
| ---------------- | ----------------------------------- |
| User is a member | `Filter.in_('members', [userId])`   |
| Channel type     | `Filter.equal('type', 'messaging')` |
| Combined         | `Filter.and([...])`                 |

**Full operator set** (all are `Filter.*` constructors):

| Operator                                     | Meaning                                                                                              |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `Filter.equal` / `Filter.notEqual`           | field equals / does not equal a value                                                                |
| `Filter.greater` / `Filter.greaterOrEqual`   | numeric/date `>` / `>=`                                                                              |
| `Filter.less` / `Filter.lessOrEqual`         | numeric/date `<` / `<=`                                                                              |
| `Filter.in_` / `Filter.notIn`                | field matches **any** / **none** of a list (`in_` has the underscore because `in` is a Dart keyword) |
| `Filter.query`                               | full-text search on a field                                                                          |
| `Filter.autoComplete`                        | prefix match                                                                                         |
| `Filter.exists` / `Filter.notExists`         | field is present / absent                                                                            |
| `Filter.contains`                            | a list field contains the value                                                                      |
| `Filter.and` / `Filter.or` / `Filter.nor`    | boolean combinators over `List<Filter>`                                                              |
| `Filter.empty()`                             | no-op filter (matches everything, `{}`)                                                              |
| `Filter.raw(value: {...})`                   | escape hatch for a raw filter map the constructors can't express                                     |
| `Filter.custom(operator: '\$x', value: ...)` | a custom operator your Stream backend supports                                                       |

Not every field is queryable — channels commonly filter on `members`, `type`, `name`, `last_message_at`; consult the dashboard's query options if a filter returns nothing.

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

`channel.isOneToOne` returns `true` for a distinct two-member channel (use it for "DM" checks); `channel.isGroup` returns `true` for non-distinct or larger channels.

---

## Member list & user list

> **Docs:** [StreamMemberListView](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/member-list/stream-member-list-view.md) · [StreamUserListView](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/user-list/stream-user-list-view.md)

Two pre-built paginated lists (each backed by a controller from `stream_chat_flutter_core`). Use them to show who's in a channel, or to pick people to add to one.

**Channel members — `StreamMemberListView` + `StreamMemberListController`** (scope is one channel):

```dart
late final _memberController = StreamMemberListController(
  channel: StreamChannel.of(context).channel,   // required
  filter: Filter.notEqual('id', StreamChat.of(context).currentUser!.id),
  // sort + limit have sensible defaults
);

@override
void initState() { super.initState(); _memberController.doInitialLoad(); }
@override
void dispose() { _memberController.dispose(); super.dispose(); }

// build:
StreamMemberListView(
  controller: _memberController,
  onMemberTap: (member) { /* ... */ },
)
```

**App-wide users — `StreamUserListView` + `StreamUserListController`** (queried across the app):

```dart
late final _userController = StreamUserListController(
  client: StreamChat.of(context).client,   // required (note: client, not channel)
  filter: Filter.notEqual('id', StreamChat.of(context).currentUser!.id),
  presence: true,                          // include online / last-active state
  limit: 30,
);
// doInitialLoad() in initState, dispose() in dispose:
StreamUserListView(controller: _userController, onUserTap: (user) { /* ... */ })
```

**To build "add members to a group":** query users with `StreamUserListController`, collect the tapped ids, then `await channel.addMembers([id1, id2])`. Adding members is permission-gated — see [Channel permissions & roles](#channel-permissions--roles).

- The controllers differ: member takes `channel:`, user takes `client:`.
- Both are `PagedValueNotifier`s — for fully custom UI use `PagedValueListenableBuilder` + `loadMore(nextPageKey)` instead of the pre-built view.
- Querying users app-wide is permission-gated; a restricted role may get an empty list.

---

## Message search

> **Docs:** [StreamMessageSearchListView](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/stream-message-search-list-view.md)

`StreamMessageSearchListView` + `StreamMessageSearchListController` search messages **across channels** (not tied to a `StreamChannel`).

```dart
late final _searchController = StreamMessageSearchListController(
  client: StreamChat.of(context).client,
  filter: Filter.in_('members', [StreamChat.of(context).currentUser!.id]), // channels to search
  searchQuery: '',   // OR messageFilter: — provide EXACTLY one (asserts otherwise)
  limit: 20,
);

void _onQueryChanged(String q) {
  _searchController
    ..searchQuery = q
    ..doInitialLoad();
}

// build:
StreamMessageSearchListView(controller: _searchController)
```

- The controller **requires exactly one** of `searchQuery` (a full-text term) or `messageFilter` (a `Filter`, e.g. `Filter.query('text', 'hello')`). Passing both, or neither, throws an assertion at construction.
- `filter` scopes which channels are searched (usually the current user's channels).
- **Throttle** input-driven searches — don't fire a query per keystroke (the docs recommend a rate limiter).
- Dispose the controller in `dispose()`.

---

## Composer feature flags — voice, polls, drafts

> **Docs:** [Voice Recording](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-voice-recording.md) · [Polls](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/polls.md) · [Draft Messages](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/drafts.md)

Toggles on `StreamMessageComposer` (plus one app-level config). All verified on v10.0.1:

- **Voice messages:** `StreamMessageComposer(enableVoiceRecording: true)` adds a hold-to-record mic button (long-press >1s to start). Add `sendVoiceRecordingAutomatically: true` to send on release. Recordings render automatically in the message list.
- **Polls:** pass `pollConfig: PollConfig(...)` to the composer to constrain poll creation (name/option/vote ranges). **Polls must be enabled on the channel type in the Stream Dashboard** — without that server-side flag the Polls option never appears in the picker, regardless of client code. Created polls render automatically in the message list.
- **Drafts:** auto-saving unsent composer text is **on by default** — `StreamChatConfigurationData.draftMessagesEnabled` defaults to `true`, and a draft preview shows on the channel/thread tile. To disable, pass it to the `StreamChat` widget via `configData:`:
  ```dart
  StreamChat(
    client: client,
    configData: StreamChatConfigurationData(draftMessagesEnabled: false),
    child: child,
  )
  ```
  (A `StreamDraftListController` exists in `stream_chat_flutter_core` if you want to build a custom "drafts" screen; there is no pre-built draft-list widget in 10.0.1.)

---

## Channel permissions & roles

Stream Chat enforces **per-role, per-scope permissions**. Every client-side SDK call is checked against the connected user's role; **server-side calls (the CLI or your backend using the API _secret_) bypass all permission checks**. This is the single most common source of "works when I seed it, fails from the app" confusion — seeding channels via the CLI succeeds because the secret bypasses checks, but the same query/join from the app hits the `user`/`guest` role's grants and can fail. The failure is a _permission gap_, not a code bug.

Default user-level roles: `user` (every authenticated user), `guest` (name-only / no-backend sign-in), `anonymous` (read-only), `admin`. Channel-level roles: `channel_member`, `channel_moderator`. Each channel **type** (`messaging`, `team`, `livestream`, …) carries its own grant set, and individual channels can override the type.

**The defaults are tuned for member-based DMs/groups, not open discovery.** On the default `messaging` type the `user` role can read and post in channels it is _already a member of_, but is typically **not** granted what an open "browse & join groups" feature needs. The grants that most commonly bite:

| Feature in the app                                                                                                            | Permission (grant) needed on the channel type                  | Often missing for `user`? | For `guest`? |
| ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------------------------- | ------------ |
| List/open channels the user is **not** a member of — `queryChannels` without a `members` filter, opening a discovered channel | `Read Channel` (`ReadChannel`)                                 | **yes**                   | yes          |
| Join an existing channel by adding yourself — `channel.addMembers([myId])`                                                    | `Add Own Channel Membership` (`AddOwnChannelMembership`)       | **yes**                   | yes          |
| Leave a channel — `channel.removeMembers([myId])`                                                                             | `Remove Own Channel Membership` (`RemoveOwnChannelMembership`) | varies                    | yes          |
| Create a new channel — `channel.create()` / `watch()`                                                                         | `Create Channel` (`CreateChannel`)                             | usually granted           | varies       |
| Post a message                                                                                                                | `Create Message` (`CreateMessage`)                             | granted (members)         | members only |

> Exact defaults depend on your app's permission version and any prior Dashboard edits — **verify, don't assume**. The grant names above are what to search for in Roles & Permissions.

**Symptom.** The SDK throws a `StreamChatNetworkError` like `"User '...' with role 'user' is not allowed to perform action ReadChannel in scope 'messaging'"` (error code 17 / HTTP 403). If a discovery list comes back empty or a join silently does nothing, this is almost always why.

**How to grant them.**

- **Dashboard (quickest):** Chat → **Roles & Permissions** (switch the app to permissions **v2** if prompted) → select the role (`user` and/or `guest`) → channel type `messaging` → enable the grant(s) above → Save. Changes propagate within ~a minute.
- **API / CLI (scriptable):** `UpdateChannelType` changes a channel-type's grants for a role; `UpdateChannelPartial` with `config_overrides.grants` overrides a single channel.

**Guests are stricter than `user`.** A name-only / no-backend app that signs people in as guests must grant the **`guest`** role the discover/join permissions too, or those flows fail even after they work for authenticated users.

Full reference: <https://getstream.io/chat/docs/flutter-dart/chat-permission-policies.md>

---

## Attachments — rendering & customization

> **Docs:** [Attachments](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-composer/attachments/)

The pre-built message widget renders all attachment types through an ordered builder pipeline. Reuse it and override only the type you're restyling — the pipeline handles the rest, including a fallback for unknown types, so every message renders.

- `StreamAttachmentWidgetBuilder.defaultBuilders(message:, onAttachmentTap:, customAttachmentBuilders:)` returns the ordered list: poll · mixed · gallery · file · giphy · image · video · voice-recording · link-preview · unsupported · fallback — covering every type.
- Pass your override(s) as `customAttachmentBuilders`; they are **prepended** (checked first). A custom builder is `class X extends StreamAttachmentWidgetBuilder` with `canHandle(message, groupedByType)` + `build(context, message, groupedByType)`. Scope `canHandle` tightly (e.g. url-preview-only: `attachments.length == 1 && attachments.containsKey(AttachmentType.urlPreview)`) so it takes over only that one type and mixed messages keep the default (which renders their media).
- Attachments are grouped by `attachment.type` into a `Map<String, List<Attachment>>`; the first builder whose `canHandle` returns true wins. **Polls live on `message.poll`, not `message.attachments`** — `PollAttachmentBuilder` triggers on `message.poll != null`, so run this whenever `message.attachments.isNotEmpty || message.poll != null`.
- To restyle a rendered type without replacing it, use `StreamTheme.messageItemTheme.attachment` (`StreamMessageAttachmentStyle`); for a global per-type swap in the pre-built row, use the `streamChatComponentBuilders(imageAttachment:/videoAttachment:/fileAttachment:/…)` slots.

**Inside a fully custom message row**, render attachments with the same pipeline: build `defaultBuilders(...)`, group `message.attachments` by `type` into a `Map<String, List<Attachment>>`, and return the first builder whose `canHandle` is true (give it an `onAttachmentTap` that opens the URL/file via `launchURL`). See the copy-pasteable snippet in [`design-matching.md`](../design-matching.md) → Attachments. Use `StreamMessageItem.fromProps` / the `attachmentBuilders:` prop when you keep the default (bubble) row; use this pipeline when you build the row yourself.

**Link previews** come from a URL in the message **text** — the server enriches it into a `url_preview` attachment; you don't send links as attachments. **Channel mentions** render when the message is sent with `mentionedChannel: true` (`StreamMessageText` handles `StreamMentionType.channel`).

---

## Reactions

> **Docs:** [Message Reactions](https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/reactions.md)

`sendReaction` takes the `Message` object and a `Reaction`:

```dart
await channel.sendReaction(message, Reaction(type: 'like'));

// Remove a reaction
await channel.deleteReaction(message, Reaction(type: 'like'));
```

Reaction counts and scores are exposed via `message.reactionGroups` (a `Map<String, ReactionGroup>`).

---

## Deleting Messages

```dart
// Delete for everyone
await channel.deleteMessage(message);

// Delete only for the current user
await channel.deleteMessageForMe(message);
```

Both take the `Message` object. Delete-for-me state is reflected on the message's `state` (`message.state.isDeletedForMe`, `isDeletingForMe`, `isDeletingForMeFailed`).

---

## StreamChatClient config

All config changes must happen before `StreamChatClient(...)` is called.

```dart
final client = StreamChatClient(
  'your_api_key',
  logLevel: Level.INFO,        // Level.OFF in production
);
```

---

## Gotchas

- **Never use dev tokens in production.** A development token disables token auth and allows any client to impersonate any user.
- **Never store your Stream secret in the app.** Secrets on-device can be extracted and enable destructive actions on your app instance.
- **Discover/join features depend on channel-type permissions.** `queryChannels` over channels the user isn't a member of needs `Read Channel` (`ReadChannel`), and `channel.addMembers([myId])` needs `Add Own Channel Membership` (`AddOwnChannelMembership`) — the default `messaging` grants for the `user`/`guest` role often omit both, so the feature works when seeded server-side (CLI/secret bypass checks) but throws a 403 from the app. See [Channel permissions & roles](#channel-permissions--roles).
- **Always `await client.disconnectUser()` before connecting another user.** Connecting a new user while disconnect is in progress risks state corruption.
- **`StreamChat` must appear in the widget tree before any Stream widget renders.** Rendering a widget without `StreamChat` in the ancestor tree causes a runtime error.
- **`StreamChannelListController` must be disposed.** Failing to call `dispose()` leaks WebSocket listeners.
- **Never create `StreamChannelListController` in `build`.** It must be a `late final` field on `State` - a new controller on every rebuild resets pagination and breaks the list.
- **`connectUser` is async - always `await` it before `runApp`.** Starting the app before the user is connected shows an empty or errored channel list.
- **`StreamMessageComposerController` must be disposed.** Always dispose it alongside the `FocusNode` in `State.dispose()`.
- **`StreamChannelListView` handles pagination automatically.** Do not manually call `loadMore` - the built-in infinite scroll triggers it.
- **`StreamChannel` scopes channel context.** Every channel screen must be wrapped with `StreamChannel(channel: channel, child: ...)` so descendant widgets can read channel state.
- **`StreamMessageListView` flags live in `config:` and builders in `builders:`.** Behaviour flags like `swipeToReply` go in `config: StreamMessageListViewConfiguration(...)`; slot builders like `empty`/`loading`/`error` go in `builders: StreamMessageListViewBuilders(...)`. `messageBuilder`, `parentMessage`, `threadBuilder`, and `onReplyTap` stay top-level.
- **The composer widget is `StreamMessageComposer`** with a `messageComposerController:` parameter. The attachment picker is inline — there is no separate modal sheet function to call.
- **`sendReaction`/`deleteReaction` take a `Message` object and a `Reaction`** — `channel.sendReaction(message, Reaction(type: 'like'))`.
