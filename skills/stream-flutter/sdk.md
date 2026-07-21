# Stream Flutter - shared SDK patterns

This file holds the shared Flutter/Dart patterns that cut across different Stream packages. Load it before product-specific references when you need lifecycle, auth, or architecture guidance.

---

## Package tiers

### Chat

Three tiers with increasing control:

| Package                    | Use when                                                                                                                         |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `stream_chat_flutter`      | Fastest integration - pre-built `StreamChannelListView`, `StreamMessageListView`, `StreamMessageComposer`, `StreamChannelHeader` |
| `stream_chat_flutter_core` | Custom UI - use `StreamChannelListController`, `PagedValueListenableBuilder`, and your own widgets                               |
| `stream_chat`              | Low-level API access - direct `StreamChatClient` calls, no UI helpers                                                            |

Default to `stream_chat_flutter` unless the user explicitly needs custom UI or low-level control.

**One import, several packages — and where symbols actually live (grounding method).** The chat
stack is split across packages, but `stream_chat_flutter` **re-exports** the ones you use for UI +
data, so a single `import 'package:stream_chat_flutter/stream_chat_flutter.dart'` transitively
exposes all of them:

- `stream_chat_flutter` (pre-built widgets) → re-exports `stream_chat_flutter_core` (headless
  controllers: `StreamChannelListController`, `StreamUserListController`, `PagedValueListenableBuilder`,
  the `StreamChannel` widget) → re-exports `stream_chat` (LLC: `StreamChatClient`, models, `Filter`).
- `stream_chat_flutter` **also** re-exports `stream_core_flutter` (imported as `core` inside the SDK):
  the **theming + low-level UI components** — `StreamTheme` (a `ThemeExtension`), `messageItemTheme`
  / `StreamMessageItemThemeData` (`.bubble`, `.text`, …), the component factory
  (`StreamComponentBuilders` / `StreamComponentFactory`), `StreamMessageLayout`, `StreamColorScheme`.

**Imported separately (NOT re-exported):** `stream_chat_persistence` (offline) and
`stream_chat_localizations` (localized strings) — add these imports explicitly.

**Grounding method — don't declare an API missing from a scoped grep.** Because a symbol you use
may be *defined* in any of these transitive packages (e.g. `StreamTheme` lives in
`stream_core_flutter`, not `stream_chat_flutter/lib/src`), a `grep 'class X' stream_chat_flutter/lib`
that comes back empty means **you looked in the wrong package, not that the API is gone**. To
confirm a symbol exists/its signature: grep the **whole resolved set** (all `stream_chat*` **and**
`stream_core_flutter` under `~/.pub-cache`), or just write the code against the documented symbol
and let the analyzer/compiler confirm. The API surface these skills describe is real; find it before
concluding it drifted.

**Gate — a "missing API" claim requires cited evidence of absence.** Never report a symbol as
missing / renamed / unsupported — to the user, or implicitly by hand-rolling a workaround — unless
you can point to the check that failed: the whole-resolved-set grep above, or a compile error
against the pinned version. A scoped grep is not evidence of absence.

### Feeds

One package — no pre-built UI:

| Package                | Notes                                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------------ |
| `stream_feeds: ^0.5.1` | Current package. Requires Dart >=3.10.0. Client, models, reactions, follow/unfollow, pagination. No UI. |

> **Do not use `stream_feed` or `stream_feed_flutter_core`.** Both are deprecated and incompatible with Dart 3. `stream_feeds` is the only correct choice.

All feed UI is built with standard Flutter widgets (`StatefulWidget` + `setState` or the user's existing state management). Default UI style is Twitter-style.

---

## App shapes

Match the project that already exists:

- **Standard Flutter app:** `StreamChatClient` initialized before `runApp`, `StreamChat` wrapping `MaterialApp` via `builder` or `home`
- **Existing app with state management (Riverpod, Bloc, Provider):** inject `StreamChatClient` through the existing DI pattern - do not add a second one
- **Multi-screen app with custom navigation:** use `StreamChannel` inherited widget to scope channel context per screen

Do not rewrite the app's navigation or state layer unless the user asks.

---

## Client ownership

Create `StreamChatClient` once, before `runApp`. Store it in a top-level variable or a singleton service.

**Good ownership:**

```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final client = StreamChatClient('your_api_key', logLevel: Level.OFF);
  await client.connectUser(
    User(id: 'user-id'),
    'your_user_token',
  );

  runApp(MyApp(client: client));
}
```

**Bad ownership:**

```dart
// Wrong - new client on every build
class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final client = StreamChatClient('key'); // never do this
    ...
  }
}
```

---

## StreamChat widget placement

`StreamChat` must appear in the widget tree before any Stream SDK widget renders. Two valid placements:

**Option A - builder wrapper (recommended, works with any MaterialApp setup):**

```dart
MaterialApp(
  builder: (context, widget) => StreamChat(
    client: client,
    child: widget,
  ),
  home: const ChannelListPage(),
)
```

**Option B - direct home wrapper:**

```dart
MaterialApp(
  home: StreamChat(
    client: client,
    child: const ChannelListPage(),
  ),
)
```

Use Option A when you also need to pass `themeData` or `localizationsDelegates`. Use Option B only for the simplest single-screen demos.

---

## Auth model

Use the simplest token shape that matches the user's environment:

- **Backend exists:** prefer a backend-issued Stream token fetched at login time.
- **No backend / demo flow:** generate a token with the Stream CLI (see Step 0.5 in `SKILL.md`). Never-expiring: `getstream token <user_id>`. Expiring: `getstream token <user_id> --ttl <duration>`.
- **User pastes their own:** accept it and move on.

Keep the split clear:

- **client:** API key, user id, user token
- **server:** API secret and token minting (the CLI handles this automatically)

`connectUser` is `async` - always `await` it before `runApp` so the app starts with an active session.

---

## Channel context

`StreamChannel` is an inherited widget that scopes a channel instance to a subtree. Wrap each channel screen with it.

```dart
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (_) => StreamChannel(
      channel: channel,
      child: const ChannelPage(),
    ),
  ),
);
```

Inside any widget under `StreamChannel`, retrieve the channel with:

```dart
final channel = StreamChannel.of(context).channel;
```

---

## State and controllers

Stateful SDK controllers must have explicit ownership:

- `StreamChannelListController` -> stored as a `late final` field on a `State` object, disposed in `dispose()`
- `StreamMessageComposerController` -> stored as a `late final` field on a `State` object, disposed in `dispose()`
- Never create controllers inside `build` methods

```dart
class _MyPageState extends State<MyPage> {
  late final _listController = StreamChannelListController(
    client: StreamChat.of(context).client,
    filter: Filter.in_('members', [StreamChat.of(context).currentUser!.id]),
    channelStateSort: const [SortOption.desc('last_message_at')],
  );

  @override
  void dispose() {
    _listController.dispose();
    super.dispose();
  }
}
```

---

## Reactive patterns

Use `StreamBuilder` for channel-level state (messages, members, typing indicators):

```dart
StreamBuilder<List<Message>>(
  stream: channel.state!.messagesStream,
  initialData: channel.state!.messages,
  builder: (context, snapshot) {
    final messages = snapshot.data ?? [];
    // build UI
  },
)
```

Use `ValueListenableBuilder` / `PagedValueListenableBuilder` for paginated list controllers:

```dart
PagedValueListenableBuilder<int, Channel>(
  valueListenable: _listController,
  builder: (context, value, child) {
    return value.when(
      (channels, nextPageKey, error) => ListView.builder(...),
      loading: () => const CircularProgressIndicator(),
      error: (e) => Text('Error: $e'),
    );
  },
)
```

---

## Localization

Add `GlobalStreamChatLocalizations.delegates` to `MaterialApp` to enable Stream's localized strings.

```dart
MaterialApp(
  localizationsDelegates: GlobalStreamChatLocalizations.delegates,
  supportedLocales: const [Locale('en'), Locale('fr'), Locale('es')],
  ...
)
```

Requires the `stream_chat_localizations` package.

---

## Disconnect and user switching

```dart
// Disconnect before switching users or on logout
await client.disconnectUser();

// Reconnect as a new user
await client.connectUser(
  User(id: 'new-user-id'),
  'new_user_token',
);
```

Never connect a second user while the first is still connected - this leaves orphaned WebSocket connections.

---

## Advanced chat features — push, offline, lifecycle

Production concerns beyond basic wiring — **push notifications**, **offline / local
data persistence**, and **connection lifecycle & app backgrounding** — now live in their
own pair so this file stays focused on shared setup:

- **Reference:** [`references/CHAT-ADVANCED-FLUTTER.md`](references/CHAT-ADVANCED-FLUTTER.md) — SDK patterns, gotchas, and device/persistence APIs.
- **Blueprints:** [`references/CHAT-ADVANCED-FLUTTER-blueprints.md`](references/CHAT-ADVANCED-FLUTTER-blueprints.md) — copy-pasteable FCM wiring, persistence init, and lazy-connect gate.

Both apply equally to `stream_chat_flutter` and `stream_chat_flutter_core`.

---

## Verification checklist

Before calling the work done, confirm:

- `flutter pub get` succeeds with the added Stream dependencies
- `StreamChatClient` is initialized before `runApp`
- `StreamChat` widget appears in the tree before any Stream widget renders
- the requested user connects without exposing the API secret
- the requested channel list, message list, or input surface appears where expected
- `StreamChannelListController` and `StreamMessageComposerController` are disposed in `dispose()`
- switching users tears down the previous session cleanly
