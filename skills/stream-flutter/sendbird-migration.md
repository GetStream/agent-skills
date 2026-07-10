# Sendbird → Stream Chat Flutter migration

A repeatable procedure for migrating a **Flutter app** from the **Sendbird Chat SDK**
(`sendbird_chat_sdk` / `sendbird_uikit`) to **Stream Chat** (`stream_chat_flutter` /
`stream_chat_flutter_core`). It works on *any* Sendbird integration regardless of how it was wired
— behind a service/repository, in a state object, directly in widgets, or as spaghetti. Do **not**
assume a specific symbol exists; **detect the shape** of the integration and re-implement it in
place.

Golden rule: **change as little application code as possible.** Preserve the app's architecture,
navigation, and state management (cross-ref [`RULES.md`](RULES.md) → "Project ownership"). Swap
what's *inside* the SDK touchpoints, not the touchpoints themselves.

---

## 0. Detect the integration shape (do this first)

```bash
grep -rn "sendbird_chat_sdk\|sendbird_uikit\|sendbird_chat_widget" pubspec.yaml
grep -rn "SendbirdChat\|SendbirdUIKit\|SBU\|GroupChannel\|OpenChannel" lib/
```

Classify each touchpoint and migrate it in place:

| Pattern found | How to migrate |
|---|---|
| **Service / repository** hiding the SDK | Keep its public API; re-implement the body against Stream. Callers don't change. |
| **State object** (`ChangeNotifier` / Provider / Riverpod / Bloc calling the SDK) | Keep the public surface (state + methods); replace the SDK calls inside. |
| **Direct-in-widget** (SDK calls/widgets straight in a `Widget`) | If the rendering widgets are the app's *own*: keep the widget tree, swap only the SDK data calls/types inside (appearance unchanged). If a **Sendbird UI widget** is embedded: replace it with a Stream widget — see the UI-strategy fork below. |
| **UIKit screens** (`SBUGroupChannel*Screen`) | Replace with composed Stream widgets (§3). Sendbird UIKit is **group-channel-only** — there are no open-channel UIKit screens. |
| **Singleton** (`X.instance`) | Keep the singleton + signatures; replace the SDK calls. |
| **Spaghetti** (calls scattered, no boundary) | Migrate file-by-file; don't refactor unrelated code. Note it. |

Also note **shared bootstrap** (SDK init, credentials/config, seeding) — that layer always changes.

### What renders each screen decides the UI strategy (the first fork, before any code changes)

The test is **per rendering widget: is it the developer's *own* Flutter widget, or a Sendbird UI
widget?** — not where the SDK happens to be called from.

- **Developer's own widgets** (plain Flutter/Material — `ListView`, `ListTile`, `TextField`, custom
  widgets — using Sendbird only for *data*: `GroupChannel`, `BaseMessage`, `MessageCollection`):
  **preserve them; replace only the low-level client behind them** (Sendbird core SDK →
  `stream_chat_flutter_core` controllers / `StreamChatClient`, wired behind the same widgets). **The
  app must look identical before and after** — appearance-wise there should be no difference. Do
  **not** re-skin with `stream_chat_flutter` pre-built widgets; re-implementing a working custom UI is
  wasteful and changes the product against the developer's intent.
- **Sendbird UI widgets** (anything a Sendbird package renders — `sendbird_uikit`'s `SBU…`
  screens/components, or any UI widget from `sendbird_chat_widget`): these **disappear when the SDK is
  removed**, so you must **replace each with a Stream widget** (§3) and match the Sendbird look
  **region-by-region** (§0.5). This holds even if they were dropped straight into an otherwise-custom
  widget tree.
- Most apps are cleanly one or the other — quick signal: `sendbird_uikit` in deps → UIKit / rebuild
  path; `sendbird_chat_sdk`-only → custom / preserve path — but a **mixed** app is possible, so decide
  **per widget**. (`sendbird_chat_widget` can supply *both* helpers, e.g. notification caching, and UI
  widgets: swap/drop the helper calls, but **replace** any of its UI widgets.)
- **Explicit override:** re-implement a custom UI on Stream's pre-built components **only if the user
  asks**.

([`SKILL.md`](SKILL.md) → "pick the UI strategy first" applies only when you are *building* UI, i.e.
the rebuild path.)

---

## 0.5 Design & functional fidelity (the part that's always wrong)

Swapping the SDK so the app *builds and connects* is the easy 80%. The migration is judged on the
**last 20%: does each screen look and behave like the Sendbird original?** Those gaps almost never show
in the channel **list** — they live **inside the chat** (bubbles, alignment, composer buttons, custom
cards). A green build and a correct channel list are **not** "done".

**"Done" means every source capability is accounted for — not that it builds.** Functional parity
(builds, connects, renders) is the floor, not the finish. Before you may call a migration done, produce an
explicit **parity account**: walk the source screen by screen and list every screen, control, and
interaction it has, and mark each **matched**, **deferred (and told to the user)**, or **not reproducible
(and told to the user, with what + why)**. A capability in none of those three states is a **silent drop**
— the failure this gate exists to prevent; never silently omit anything the source did. If you cannot run
the source to build this account (no backend, headless), you **cannot** claim fidelity — say the fidelity
pass is unverified and list what is therefore unchecked. Enumerating forces the confrontation that scanning
the source does not: real drops — a channel-row long-press, a dark theme, a simplified settings screen —
are capabilities that were never *listed*, not ones that were judged and cut. This account is the
checklist's exit criterion (§9).

**The source app IS the benchmark — build it first if it's missing.** Never design a migrated screen
from scratch or against Stream's defaults. Run the Sendbird app and screenshot every screen/variant
(list **and** chat, an incoming **and** an outgoing message); those shots are the spec. If you're adding
a *new* use-case that has no Sendbird original yet, **build the Sendbird version first** (in the source
SDK) and screenshot it — going straight to Stream invents a design with nothing to check against, and it
will be wrong. A git worktree at the Sendbird baseline lets you build the reference without disturbing
the Stream work.

**When this pass applies.** Design fidelity is the default when migrating an existing app. If the user
instead accepts Stream's defaults, this pass — and [`design-matching.md`](design-matching.md) — is out
of scope; run the functional verification only.

**"Fidelity" means different things per the §0 fork:**
- **Preserve path (own widgets kept):** you didn't touch the widgets, so *looks* is satisfied for free —
  fidelity here means **zero visual change** (any before/after difference is a regression to fix), and
  verification focuses on **behavior/functional parity** (the client swap didn't drop a feature).
- **Rebuild path (Sendbird UI widgets replaced):** the region-by-region matching below applies —
  reproduce the Sendbird look on the new Stream widgets.

- **Derive every value from the source — pixel-sample, don't guess.** For each region pull the concrete
  Sendbird value: colors from the theme classes (`SBUColors` / `SBUThemeProvider`) — **read the actual
  values there** (source: `github.com/sendbird/sendbird-uikit-flutter` → `lib/src/public/resource/`); a
  per-app override or a newer default means any constant baked in here would be wrong. Note Sendbird
  encodes **emphasis tiers** in the alpha channel (high/mid/low ≈ 88/50/38% opacity) — match the tier per
  element. Also pull fonts/sizes/paddings per element. **Name the value from the theme, but let the
  rendered pixel be the source of truth** — the theme constant can lie, so confirm each color against the
  running app and sample it (method in [`design-matching.md`](design-matching.md)). When you hand-build a
  view, pull **every** element's value including **text**, and keep the source's emphasis hierarchy (a
  quieter author over a brighter message) — full-strength everything inverts it. If a rendered color
  *contradicts the app's own accent*, that's likely an SDK quirk: prefer brand consistency, and when it's
  ambiguous **ask rather than guess**.
- **Classify each difference, then reach for the matching knob — using the wrong one is why a screen
  "looks migrated" but is still off.** Route it through the two axes (don't reinvent a model here):
  - **Recolored / restyled** — same layout, different color/font/size/padding/radius → **theming**
    (`StreamTheme` for the message row/leaf widgets, `StreamChatThemeData` for the chat composite
    widgets).
  - **Restructured** — a widget moved/added/removed/reshaped (flat rows, author-on-top, no bubble), *or*
    a message **realigned** off its default side → **widget replacement** (`streamChatComponentBuilders`
    / `StreamComponentBuilders` / per-widget builders). Message side is set inside the row widget by
    sender, so *realigning* — e.g. an open-channel all-left layout with one shared message style — is a
    row override: replace the row (`messageBuilder` / the `messageItem` slot) and lay it out yourself.
    **Reaching for a theme token when the change is structural is the single most common "still looks
    like Stream, not Sendbird" miss.**
  - Full procedure: [`design-matching.md`](design-matching.md) (components) or
    [`custom-ui.md`](custom-ui.md) (bespoke/livestream). Overriding a **composite** slot drops the
    sub-features the default rendered — read its `build()` and reproduce them.
- **Rebuild path — the misses a green build hides.** Walk these inside the chat (full region list in
  [`design-matching.md`](design-matching.md)); each is a Sendbird→Stream *default* gap a list-only
  screenshot won't catch:

  | Check (inside the chat) | The gap a green build hides |
  |---|---|
  | **Outgoing bubble** | Left as Stream's pale brand shade (`colorScheme.brand.shade100`); a solid source bubble needs its fill **and** text color set (`StreamTheme.messageItemTheme`), or the text stays dark/illegible. |
  | **Incoming bubble** | Not matched to the source's incoming fill + text. |
  | **Row layout** | A restructured row (author-on-top, flat rows, no bubble) treated as a recolor — it's a **widget replacement** (the Restructured axis above), not a theme token. |
  | **Header trailing** | `StreamChannelHeader` defaults its trailing edge to the channel avatar; the source header's actual actions not reproduced. |
  | **Composer inventory** | Stream's default set (leading attachment button, picker/command affordances, mic) shipped as-is instead of matched 1:1 — inventory the source composer left→right. |
  | **Avatars** | Stream's circular avatar left as-is; source shape/size not matched, or an avatar shown where the source hides it (1:1 / bot chat). |
  | **Custom cards** | Rendered as plain text or nested in a default bubble instead of via a custom `Attachment` builder (§5). |
- **Flutter realities to expect:** avatars are **circular-only** (Slack-style rounded squares need a
  custom avatar widget); there's **no consolidated Styles axis** (insets/radii spread across theme
  objects); **no global reaction-emoji config**. A Sendbird app using any of these needs widget-level work.
- **Functional parity — confirm each feature the source enables has its Stream equivalent wired:**
  threads/replies, reactions, typing, read/delivery receipts, mentions, message search, edit/delete,
  pinned messages, moderation/frozen channels, polls, voice messages, and **push** — separate concerns the
  source often conflates:
  - **Device registration** — `client.addDevice(token, PushProvider.firebase | PushProvider.apn)` at login,
    `client.removeDevice(token)` at logout. A push-enabled source goes silently pushless if skipped. These
    are permanent device ops — not a user's on/off toggle. Setup in
    [`references/CHAT-ADVANCED-FLUTTER.md`](references/CHAT-ADVANCED-FLUTTER.md).
  - **Per-channel notifications toggle** (channel-info) → `channel.mute()` / `channel.unmute()`. A muted
    channel stops push **and** stops counting toward unread; it stays in the list (mute is a flag on the
    user's `channelMutes`, not a removal). Read state via `channel.isMuted` / `isMutedStream`.
  - **Global notifications toggle / do-not-disturb** (settings) → `client.setPushPreferences([...])`:
    `PushPreferenceInput(chatLevel: ChatLevel.all | ChatLevel.none)` for global on/off, `disabledUntil`
    (clear with `removeDisable: true`) for DND/snooze. Push preferences filter *push only* (unread is
    untouched), so a push-only per-channel override is `PushPreferenceInput.channel(channelCid: cid,
    chatLevel: ChatLevel.none | ChatLevel.defaultValue)` — use this instead of `channel.mute()` when the
    source's toggle silences notifications but keeps the unread badge.

  Where there's no clean 1:1 Stream equivalent, flag it and plan the custom work rather than assuming parity.
- **Carry the dark palette too, if the source has one.** A source with light *and* dark themes (Sendbird's
  `SBUThemeProvider`) must ship both — build both theme variants and switch on `Theme.of(context).brightness`
  (§6). How the switch is triggered (system brightness or an in-app control) follows the source; the
  requirement is that both palettes exist in the migrated app, not that a toggle does. Migrating light-only
  silently drops half the source's theming.
- **Verify on the real screen — a green build is not "done."** Open the list **and** each chat on the
  app's real navigation path and compare region-by-region against the Sendbird baseline at native scale
  (measure, don't eyeball; iterate on hot reload). **Seed the chat first so every region is populated,**
  covering both sides: send an **outgoing** message as the connected user (from the client, or
  server-side with `SendMessage … user_id=<connected user>`), and seed the cross-user **incoming**
  messages and any custom-card messages server-side (`getstream` CLI, §7). The outgoing message is the
  one to be sure of — it's where the bubble fill/text match shows. Delete any throwaway verification
  scaffold before delivery and re-verify on the real navigation path ([`RULES.md`](RULES.md) → "Project
  ownership"). Confirm Sendbird is fully removed (`grep -ri sendbird lib/` is empty).

---

## 1. Packages (pub.dev)

Remove Sendbird, add Stream. `stream_chat_flutter` re-exports the full stack.

| Remove (Sendbird) | Add (Stream) |
|---|---|
| `sendbird_chat_sdk` (core) | `stream_chat` (core, pure Dart) — transitively via the UI package |
| `sendbird_uikit` (widgets) | `stream_chat_flutter` (pre-built UI; re-exports `_flutter_core` + `stream_chat`) |
| — (custom-UI path) | `stream_chat_flutter_core` (headless controllers) instead of the UI package |
| offline (bundled in `sendbird_chat_sdk`) | `stream_chat_persistence` (**separate** package) |

Pin the Stream packages in lockstep to the same major (these skills target **v10** — see
[`SKILL.md`](SKILL.md) → "Version prerequisite"). State the lockstep rule; don't hard-code a patch.

- **Migrate to v10** — the current major these skills target; don't migrate onto an older Stream
  Flutter version. Ground your API usage against the pinned v10 source (or pub.dev).
- **Expect toolchain bumps in an existing app.** Adopting v10 often pulls newer transitive deps that
  require bumping the Android toolchain (Kotlin / Gradle / heap) before the build passes — budget for
  it; it's not migration logic but it blocks the build.
- **Offline persistence is opt-in — mirror the source.** Sendbird's local caching (`SendbirdChatOptions
  .useCollectionCaching` / the collection DB) maps to attaching a `StreamChatPersistenceClient`. If the
  source enables caching, attach it (before `connectUser`, §8); if it opts out, **don't add the
  persistence client at all**. Don't hardcode persistence on — match the source's on/off choice.

---

## 2. Initialization & authentication

The biggest conceptual shift: **App ID + optional session token → API key + always a per-user JWT.**

| Sendbird | Stream |
|---|---|
| `SendbirdChat.init(appId: 'APP_ID')` / `SendbirdUIKit.init(appId:)` | `StreamChatClient('api-key')` |
| `SendbirdChat.connect(userId, accessToken: token)` (token optional in test mode) | `client.connectUser(User(id: userId), token)` — **token always required** (`connectUserWithProvider` for prod refresh) |
| `SendbirdUIKit.provider(...)` wraps the tree | `StreamChat(client: client, child: …)` wraps `MaterialApp` (or `StreamChatCore` for headless) |
| App ID is the only credential | API **key** (client-safe) + per-user **token**; the **secret** stays server-side |

Init the client **once before `runApp`** and mount `StreamChat(client:, child:)` so the provider
**wraps the tree from the first frame**. `connectUser` is a separate step that can come later (e.g. on a
login screen) — create the client and mount the provider unconditionally rather than gating either on
being connected. Stream's pre-built widgets read the client from context via `StreamChat.of(context)`,
which **throws** when no `StreamChat` ancestor is mounted, so a channel-list or chat screen shown before
the provider is in the tree red-screens. `disconnectUser()` before switching users (cross-ref
[`RULES.md`](RULES.md) → "Client lifetime"). No wrapper layer (→ "No wrapper or bridge abstractions").
Use a CLI-minted token via `getstream token <id>` for local (see [`SKILL.md`](SKILL.md) → Step 0.5)
— it's a real secret-signed JWT, not a dev token.

> **Heads-up:** client-side **dev tokens** (`client.devToken(userId)`) work only when dev tokens are
> **enabled on the app in the dashboard** (Auth settings) — otherwise `connectUser` returns a 401.
> The CLI-minted token above needs no dashboard toggle.

---

## 3. UI components

| Sendbird (`sendbird_uikit`) | Stream (`stream_chat_flutter`) |
|---|---|
| `SBUGroupChannelListScreen` | `StreamChannelListView(controller:, onChannelTap:)` |
| `SBUGroupChannelScreen` | compose it yourself: `StreamChannel` → `Scaffold(appBar: StreamChannelHeader(), body: Column([StreamMessageListView(), StreamMessageComposer()]))` |
| `SBUGroupChannelCreateScreen` / `…SettingsScreen` / `…MembersScreen` | build with Stream controllers + widgets as needed |
| composer — the input region inside `SBUGroupChannelScreen` (an internal component, not a public widget, so nothing to swap 1:1) | `StreamMessageComposer` |

**Biggest structural difference: Stream Flutter has no built-in navigation.** Sendbird UIKit pushes
its own screens; Stream widgets don't. Add a routing layer wired to the app's existing router
(Navigator / GoRouter / auto_route) — e.g. `onChannelTap` pushes a route that wraps the chat screen
in `StreamChannel(channel: channel, child: …)`. The `StreamChat` → `StreamChannel` →
`StreamMessageListView` provider nesting is mandatory here (a hard runtime constraint — §8).

**Composing the chat screen means you own its action wiring.** UIKit shipped these behaviors inside its
screens; a composed screen connects them itself — reply/edit to the composer controller, `threadBuilder`
for threads, `onChannelLongPress` for a channel action sheet. Follow the message-list action-wiring
recipes in [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md); keep the default row/tile and
override only what differs so each keeps its built-in behavior.

**Stream ships composable widgets, not assembled screens.** Several Sendbird UIKit screens have **no
pre-built Stream equivalent** — create-channel, settings, channel-info, and invite are rebuilt from Stream
controllers + widgets (`StreamChannelListController` / `StreamUserListController` / `StreamMemberListView`),
and **moderation** (operators / muted / banned) has no Stream UI at all, only low-level moderation calls
— so build the screen or scope it out. Map a mute action to Stream's mute primitive (`channel.mute()`
channel-scoped, `client.muteUser` user-scoped), not to a ban (a ban removes access — a different, heavier
action); where the mute semantics don't line up 1:1 with the source, **state the difference explicitly**
rather than silently substituting a near-match. **Rebuilding a screen does not license dropping
its contents:** inventory every control and interaction the source screen has and reproduce each,
matching the reference's look as well as its controls (§0.5) — a rebuild silently loses whatever you don't re-add (e.g. a settings toggle, a multi-select member picker, a
channel-row long-press action sheet — illustrative, not a closed list). Anything you genuinely cannot
reproduce must be **surfaced explicitly**, never silently omitted (§0.5).

---

## 4. Channels

| Sendbird | Stream |
|---|---|
| **GroupChannel** (members) | `messaging` channel type |
| **OpenChannel** (public) | `livestream` channel type |
| `channelUrl` (opaque string) | `type + id` → `client.channel('messaging', id: '…')` then `.watch()` |
| `GroupChannel.createChannel(GroupChannelCreateParams(userIds:, name:, isDistinct:, customType:, data:))` | `client.channel('messaging', extraData: {'members': [...], 'name': ...})` then `.watch()` |
| `GroupChannelListQuery` | `StreamChannelListController(client:, filter:, channelStateSort: [SortOption.desc('last_message_at')])` with `Filter` (`Filter.in_('members', [userId])`, `Filter.equal('type', 'messaging')`). Sort goes in `channelStateSort:` (a `List<SortOption<ChannelState>>`); build entries with `SortOption.desc('field')` / `SortOption.asc('field')`. |

Trap: a `Channel` from `client.channel(...)` is uninitialized until `.watch()` is awaited.

**Detecting a 1:1 DM.** Stream ships predicates on `Channel`: `isOneToOne` (`isDistinct && memberCount == 2`),
`isDistinct` (id starts with `!members` — Stream's auto-generated distinct-channel id), and `isGroup`. Prefer
`channel.isOneToOne` for DMs created the Stream-native way (no explicit id → distinct). **Migration gotcha:**
if you preserved the Sendbird `channelUrl` as an explicit channel `id`, the channel is **not** distinct, so
`isOneToOne`/`isDistinct` return `false` — fall back to `channel.memberCount <= 2`. (Don't key off an empty
`name`; Stream DM channels usually have one.)

**Open channels → `livestream`.** Sendbird's Flutter UIKit is group-channel-only, so this applies when
the source used the core SDK's `OpenChannel` directly — the UI is the developer's own, so it's a
preserve-path swap (`livestream` is a plain channel type, no dedicated class):
- **List** via `Filter.equal('type', 'livestream')` — public, so query **without** a `members` filter
  (a membership-scoped query returns nothing for a channel the user hasn't joined).
- **Enter / leave** → `channel.watch()` to start receiving, `channel.stopWatching()` on leave; watching
  *is* the participation (there's no separate join step).
- **Participant count** → `channel.state.watcherCount` (nullable `int?`; live via `channel.state.watcherCountStream`).

**Sendbird Notifications / `FeedChannel`** (`getAppInfo()?.notificationInfo`) is a separate product
concept; the nearest Stream options are its separate Feeds product or a custom channel type. Surface
it and stub it with a note so the gap is visible.

### Membership & member selection (create / invite / member screens)

Channel-membership ops, plus the user query that a hand-built member picker needs (a pre-built picker
wouldn't surface this — a custom create/invite screen does):

| Sendbird | Stream |
|---|---|
| add / remove members | `channel.addMembers([...])` / `channel.removeMembers([...])` |
| update channel name / data | `channel.updateName(...)` / `channel.update(...)` |
| `ApplicationUserListQuery` (`.next()` / `hasNext`) — populating a member picker | `client.queryUsers(filter:, sort:, pagination: PaginationParams(offset:, limit:))` — or `StreamUserListController` (below) |
| exclude members / search | `Filter.notIn('id', [...])`; `Filter.autoComplete('name', text)` — search on `name`, the field Stream autocompletes |

Prefer the **paged controllers** for list UIs — the same `PagedValue` pattern as the channel list:
`StreamChannelListController` (channels) and `StreamUserListController` (users) both follow it with
`doInitialLoad()` / `loadMore(nextPageKey)`; `nextPageKey` lives on the **success value** — guard on
`controller.value.isSuccess` first, then read `asSuccess.nextPageKey` (or the `hasNextPage` getter),
non-null / true ⇒ more pages. (`asSuccess` **throws** off a non-success value rather than returning
null — so `asSuccess?.` is both an unnecessary null-aware and unsafe; check `isSuccess` instead.) For a
manual "load more" button, show it when more pages remain. **Gotcha — the two controllers differ on runtime filter changes.** `StreamUserListController` exposes
`filter` / `sort` **setters** (assign, then call `doInitialLoad()`). `StreamChannelListController.filter`
is **final** (no setter) — to change a channel-list filter at runtime, construct a **new** controller;
`refresh()` only reloads with the filter it already has.

---

## 5. Messages & custom attachments

| Sendbird | Stream |
|---|---|
| `channel.sendUserMessage(UserMessageCreateParams(message: 'text'))` | `channel.sendMessage(Message(text: 'text'))` |
| `channel.sendFileMessage(FileMessageCreateParams(...))` | `channel.sendMessage(Message(attachments: [Attachment(type: …, file: AttachmentFile(...))]))` — auto-uploads. Pick `type` by mime (`image`/`video`/`audio`/`file`) from `AttachmentFile.mediaType` so each renders with its proper UI. Low-level `client.sendImage/sendFile(...)` exist for an explicit upload step. |
| `params.customType` (String) + `params.data` (**JSON string**) | `Message(extraData: {…})` (structured `Map`) **or** a typed custom `Attachment` |
| read `message.customType` / `message.data` | read `message.extraData[...]` / `message.attachments` |

**Custom cards / structured payloads** — one canonical path: define a custom `Attachment(type:
'my_type', extraData: {...})`, send it in `Message.attachments`, and render it by subclassing
`StreamAttachmentWidgetBuilder` (override `canHandle` + `build`). Build the builder list with
`StreamAttachmentWidgetBuilder.defaultBuilders(message: msg, customAttachmentBuilders: [yours])` and
attach it per message through `StreamMessageListView.messageBuilder` →
`StreamMessageItem.fromProps(props: defaultProps.copyWith(attachmentBuilders: [yours]))` — copy the
builder's `defaultProps` so the row keeps its default rendering. (Unknown attachment root keys are promoted into
`extraData`; read them back as `attachment.extraData['key']`.)

### The message-list source (per-channel messages)

Sendbird's **`MessageCollection`** (channel-scoped, event-driven: `initialize()` +
`onMessagesAdded/Updated/Deleted`) has **no symmetric Stream controller** — unlike channels and users,
messages have **no `PagedValue` list controller**. Map it to a **watched `Channel`'s state streams**
(drive the existing widget) or wrap the list in `MessageListCore`:

| Sendbird `MessageCollection` | Stream (on a watched `Channel`) |
|---|---|
| `messageList` + `onMessagesAdded/Updated/Deleted` | subscribe to `channel.state.messagesStream` — or `MessageListCore(messageListBuilder:)` |
| receipt/unread updates | `channel.state.readStream` |
| "am I at the newest?" | `channel.state.isUpToDateStream` / `isUpToDate` |
| `markAsRead()` | `channel.markRead()` |

Stream subscriptions **must be cancelled in `dispose`** (Sendbird's collection handler didn't require it).

### Threads (parent message + replies)

Sendbird threads (a reply carries `parentMessageId`; the parent's `threadInfo` holds the count) map onto
Stream's `parentId` model:

| Sendbird | Stream |
|---|---|
| `params.parentMessageId = id` on the reply | `channel.sendMessage(Message(text: …, parentId: parentId))` — add `showInChannel: true` to also post it to the main channel |
| `parent.getThreadedMessagesByTimestamp(...)` → `ThreadedMessages.threadMessages` | `channel.getReplies(parentId)` → `QueryRepliesResponse.messages` (paginate with `PaginationParams`); replies also stream into `channel.state.threads[parentId]` |
| `MessageListParams..replyType = ReplyType.none` (hide replies from the main list) | Stream returns replies in the channel state, so exclude them from the channel view yourself: `where((m) => m.parentId == null)` |
| `parent.threadInfo.replyCount` | `message.replyCount` (on the parent) |
| `parent.threadInfo.lastRepliedAt` | **no field on the parent** — read the last reply's `createdAt` from `channel.state.threads[parentId]`, populated once that thread has been fetched (`getReplies`) |

The reply count sits on the parent, but the **last-reply time does not** — a "N replies · last reply <time>"
affordance renders the count immediately and fills in the time once `channel.state.threads[parentId]` is populated.

### Mentions

Sendbird's `params.mentionedUserIds` + `message.mentionedUsers` map to Stream's `User`-typed mentions:

| Sendbird | Stream |
|---|---|
| `params.mentionType = MentionType.users` + `params.mentionedUserIds = [...]` | `channel.sendMessage(Message(text: …, mentionedUsers: [User(id: …), …]))` — pass resolved `User`s, not bare ids |
| `message.mentionedUsers` (render / detect) | `message.mentionedUsers` (`List<User>`) — highlight the `@name` tokens; a mention of the current user can tint the row |
| autocomplete source | `channel.state.members` (each `Member.user`) — filter by name for the `@` picker |

The pre-built `StreamMessageComposer` handles mention autocomplete + highlighting on its own; a hand-built
composer reads `channel.state.members` and sets `Message.mentionedUsers` itself.

### Message pagination & jump-to-message

Page a watched channel in either direction, and gate whatever triggers the load — a scroll-to-edge
callback, a manual control, whatever the source used — on whether that end still has messages:

| Sendbird | Stream |
|---|---|
| `loadPrevious()` / `loadNext()`, `MessageListParams(previous/nextResultSize)` | `StreamChannel.of(context).queryMessages(direction: QueryDirection.top)` (older) / `QueryDirection.bottom` (newer). Default page 30; `MessageListCore` paginates at 20. |
| reverse + `startingPoint` (open mid-history) | `StreamChannel.of(context).loadChannelAtMessage(id)` — jump to a message (search result / push deep-link) |
| `hasNext` (newer exist) | **`hasNewer = !channel.state.isUpToDate`.** After `watch()` you're at the tail (`isUpToDate == true`); it flips false only after a jump into the past (`loadChannelAtMessage`), and back to true once you page forward to the tail. |
| `hasPrevious` (older exist) | **`hasOlder`: no public flag — derive it from the page size.** A top query returning **fewer messages than the requested limit** means older history is exhausted (the rule the SDK uses internally); until then, assume older may exist. |

Derive both from the page size / `isUpToDate` — not from "are there any messages" — so a load-older /
load-newer affordance turns off once that end is exhausted instead of triggering forever.

### Read receipts / unread counts — the model is inverted

Sendbird gives per-message `channel.getUnreadMembers(message)`. Stream exposes **channel-level read
cursors**: `channel.state.read` → `List<Read>` of `{user, lastRead}`. You don't have to hand-roll the
per-message math: the `readsOf(message:)` extension on the read list returns who has read a given
message (reads whose `lastRead >= message.createdAt`, sender excluded) — "unread by member" is the
remaining members.

### Timestamps are UTC

Server-synced Stream `DateTime`s (`message.createdAt`, `channel.createdAt`) are **UTC** —
`.toString()` renders `…ffffffZ`. (A just-sent message carries a local timestamp until the server
echo replaces it.) If a preserved widget stringifies a timestamp (Sendbird's were epoch-ms →
local), call `.toLocal()` so the rendered text matches the source.

---

## 6. Theming & view customization

| Sendbird | Stream |
|---|---|
| `SBUColors` (+ `SBUColors.setColors(...)`) | component themes on `StreamChatThemeData` (via `StreamChat(themeData:)`) + `StreamTheme` (a `ThemeExtension`) |
| `SBUThemeProvider` (`SBUTheme.light`/`.dark` toggle) | two `StreamChatThemeData` instances switched on `Theme.of(context).brightness` |
| `SendbirdUIKit.setFontFamily(...)` | text styles in the theme |
| `SBUStringProvider().setStrings(...)` (custom UI strings) | A kept Stream pre-built widget shows **default English** until overridden — its empty / loading / error states are the classic silent misses (e.g. an empty chat reverts to "Send a message to start the conversation" instead of the source's `noMessages`). Catch them all centrally: subclass `StreamChatLocalizationsEn` (from `stream_chat_localizations`), `@override` the specific getters (`sendMessageToStartConversationText` for the empty chat, `writeAMessageLabel` for the composer placeholder, …), and register it as a `LocalizationsDelegate` in `MaterialApp.localizationsDelegates` (ahead of `GlobalStreamChatLocalizations.delegates`). Per-widget builders only cover the surfaces you remember to set: `StreamMessageListView(builders: StreamMessageListViewBuilders(empty: …))` (the message list groups its placeholder slots under `builders:`), `StreamChannelListView(emptyBuilder:)` (top-level there), `StreamMessageComposer(placeholderBuilder:)`. |

The *how* of matching a specific look lives in [`design-matching.md`](design-matching.md) — this
table only maps the concepts. Sendbird's Flutter theme values live in the `sendbird_uikit` package's
`SBUColors` / `SBUThemeProvider` (source: `github.com/sendbird/sendbird-uikit-flutter` →
`lib/src/public/resource/`) — read them to name concrete colors, then confirm against the running app.

The per-region specifics — composer parity, avatars, message-bubble fill/text, custom cards — are the
"misses a green build hides" checklist in §0.5; the exact `StreamTheme` / component-builder knobs live
in [`design-matching.md`](design-matching.md).

---

## 7. Seeding / demo data

The client can act **only** as the connected user. Sendbird's test-mode multi-user creation does
**not** map. Create other users / cross-user messages **server-side** (`getstream` CLI — see
[`SKILL.md`](SKILL.md) → Step 0.5). The current user's own channels/messages can be created from
the client.

---

## 8. Pitfalls (build/runtime breakers)

- **Provider-tree order** is a hard runtime constraint (`StreamChat` → `StreamChannel` →
  `StreamMessageListView`).
- **Dispose controllers** (`StreamChannelListController` etc. are `ChangeNotifier`s) in
  `State.dispose` — Sendbird's queries had no dispose requirement.
- **`StreamChannel.value` for sub-routes:** the default `StreamChannel(...)` repositions the loaded
  message window on mount (anchors to `initialMessageId` / last-read / latest). Use
  `StreamChannel.value(...)` for a thread / modal / info route off an already-initialized channel to
  keep its window intact.
- **Attach `stream_chat_persistence` before `connectUser`** (`client.chatPersistenceClient = …`).
- **Don't `await` a blocking OS permission dialog before `connectUser`.** A preserved app that requests
  push/notification permission on the critical path (e.g. inside `login()` ahead of connecting) hangs on
  a blank screen while the system dialog is up. Connect first, then request permission off the critical path.
- **Full replace vs. per-field update — same rule for users, channels, and messages.** The `update*`
  call replaces the whole object, dropping any field you didn't include; the partial call sets/unsets
  individual fields. Reach for `update*` only when you intend a full replace:
  - **User** — `client.updateUser(user)` (full) vs `client.partialUpdateUser(id, set: {…}, unset: […])`.
  - **Channel** — `channel.update(…)` / `client.updateChannel(…)` (full) vs `channel.updatePartial(set:,
    unset:)` / `client.updateChannelPartial(…)`.
  - **Message** — `channel.updateMessage(msg)` (full) vs `channel.partialUpdateMessage(msg, set:, unset:)`.

---

## 9. Procedure checklist
1. **Detect** the integration shape (§0).
2. **Swap packages** (§1).
3. **Credentials**: API key + token via the CLI (§2, [`SKILL.md`](SKILL.md) Step 0.5).
4. **Wire one client** + provider; repoint existing bootstraps without changing their public API (§2).
5. **Migrate each touchpoint** — views + navigation (§3), channels (§4), messages/attachments (§5).
6. **Re-apply theming/customization** via the two axes (§6, [`design-matching.md`](design-matching.md)).
7. **Move seeding server-side** (§7).
8. **Complete the parity account** (§0.5) — every source screen/control/interaction marked matched /
   deferred-and-surfaced / not-reproducible-and-surfaced, backed by the source-vs-migrated screenshots
   you compared. This account, not a green build, is the exit criterion.
9. **Offer data migration** (§10).

---

## 10. Data migration (offer after the code migration)

The steps above migrate the **code/SDK**; they move no history — a migrated app talks to an
**empty** Stream app until you seed or import. Once it builds, connects, and matches the source,
**ask** whether to also migrate the Sendbird **data** (users, channels, message history, reactions).
That work is server-side and SDK-independent, so it lives in the shared runbook
[`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md) — read and follow it
if the user says yes. Do **not** start a data migration unsolicited.
