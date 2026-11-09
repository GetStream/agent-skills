# Migrating from Sendbird to Stream Chat React Native: runbook

Migrates a React Native or Expo app from the Sendbird Chat SDK (`@sendbird/chat`,
usually with `@sendbird/uikit-react-native` + `@sendbird/uikit-react-native-foundation`)
to Stream Chat (`stream-chat` + `stream-chat-react-native` or `stream-chat-expo`).
These are code migration instructions. Data migration is explained in the stream
skill's sendbird-data-migration.md.

**Migrate in place.** Preserve component boundaries, navigation, and public
prop/hook signatures. Edit the existing files (Sendbird out, Stream in), and
don't create parallel new files. New files are acceptable for genuinely new
needs (e.g. a token endpoint that never existed). If a whole file was serving
Sendbird machinery (a `createTheme` / `colorSet` module, a `platformServices`
factory), delete it.

**Not codemod-safe.** Sendbird and Stream work differently. Of the mapped
symbols, only `disconnect()` -> `disconnectUser()` is a mechanical rename. Work
file-by-file from the mapping tables, never a global find-and-replace.

**Prefer idiomatic Stream over a mechanical port.** Stream has first-class
support for the features that require hand-rolled machinery with Sendbird
(typing timers, `MessageCollection` handlers, reconnect state machines, cursor
bookkeeping, send-state callbacks). Delete the machinery and use the reactive
primitive inside the existing file/hook boundary, so callers don't change. The
idiomatic rewrite is smaller and less buggy than the faithful port.

Symbol lookup: start with sendbird-mapping.md. For the symbols it doesn't have,
use local docs with `getstream docs` and the installed types.

## 1. Detect & inventory

Map the footprint before any edit:

```bash
cat package.json app.json app.config.* 2>/dev/null   # flavor, all three Sendbird versions, package manager
grep -rln "@sendbird/chat\|@sendbird/uikit-react-native" --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' --exclude-dir=node_modules .
grep -rn "SendbirdUIKitContainer\|create.*Fragment\|useSendbirdChat\|useConnection\|createMessageCollection\|GroupChannelHandler" --include='*.ts' --include='*.tsx' --exclude-dir=node_modules .
```

**Flavor:** an `expo` dependency or an `expo` key in the app config means
`stream-chat-expo`; otherwise bare RN CLI and `stream-chat-react-native`. Both
export the same symbols - import every UI symbol from the one flavor package,
never both. Note the navigator too (React Navigation or Expo Router): the chat
header moves into it.

Pin the Stream Chat major you migrate to (chat-versions.md): the installed one if
Stream is already present, otherwise the npm `latest`. Every Stream symbol you
write comes from that major's docs.

| Pattern found                                                                             | How it migrates                                                                             |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| UIKit fragments (`SendbirdUIKitContainer`, `createGroupChannelFragment`, `renderX` props) | Architectural remap, not a rename - compose Stream RN primitives (mapping section 12)       |
| Custom hook wrapping the SDK (returns `{ state, actions }`)                               | Keep the hook's public return shape; replace the body. Callers don't change                 |
| `MessageCollection` store (init policy + `setMessageCollectionHandler`)                   | Delete the collection lifecycle; mount `<Channel>` and read `channel.state` / context hooks |
| Context + reducer store                                                                   | Keep the store shape; effects do the async Stream work and re-dispatch                      |
| Direct / inline SDK calls                                                                 | Swap in place; keep surrounding layout/navigation                                           |
| Spaghetti                                                                                 | File-by-file; a thin boundary only where it cuts churn                                      |

**Headless core (`@sendbird/chat` with the app's own UI, no UIKit):** keep the
custom UI and swap only the data layer onto `stream-chat` - no RN UI package, no
native peers, no `OverlayProvider`. Hold one `new StreamChat(apiKey)` at module
scope; `MessageCollection` + handlers -> `channel.watch()` +
`channel.state.messages` + `channel.on(...)`. Optimistic sends are yours (trap
1): `channel.state.addMessageSorted({ id, text, user, status: 'sending', ... })`
with a client-generated id, then `channel.sendMessage({ id, text })`; the echoed
`message.new` dedupes by id.

**Build the parity ledger.** List every user-facing chat feature - from the
code, the README, and the UIKit container/fragment config (voice messages,
mentions, reactions, `ReplyType` threads, read receipts, ...). One row per
feature. Mark the features **Ported**, **Rewritten**, **N/A - reason**, or
**GAP - decision**.

**Capture the visual baseline now**, before the first edit. The original app is
the best design reference there is, so get it running - install its
dependencies and set up its Sendbird env if you have to - and screenshot it on
the simulator (simulator-verification.md): the channel list, a chat with
incoming and outgoing messages, the composer at rest and typing, a thread, the
attachment picker, reactions, dark mode. Then write the region spec per
design-matching.md (sampled colors, radii, sizes, weights).

- A pre-migration Expo app often runs in Expo Go. Launch it tap-free against its
  own Metro with `xcrun simctl launch <udid> host.exp.Exponent --initialUrl "http://127.0.0.1:<port>"`;
  never `simctl openurl exp://...`, whose "Open in Expo Go?" alert can't be
  tapped and forces a simulator reboot. A fresh simulator may need Expo Go
  installed from `~/.expo/ios-simulator-app-cache/Expo-Go-*.tar.app`.
- Drive the states with real taps when a simulator tool can tap; with only
  `simctl`, which can't, use temporary scaffold code that calls the original app's
  own Sendbird APIs, and remove it after capture.

If the original can't run, fall back to user-provided screenshots (ask), or
build it from a `git worktree` at the pre-migration commit. With no pixels at
all, take the palette from `createTheme` / `colorSet` and strings from
`StringSet` - and say in the report that the layout was not matched.

## 2. Beware of these traps

| Trap                                                                                                                                                            | If ported 1:1                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Only the UI-context send is optimistic.** `channel.sendMessage()` inserts no pending message; `MessageComposer` / `useMessageInputContext().sendMessage()` do | A custom composer calling `channel.sendMessage` shows the message only after the server acks. Send through the UI path, or override `<Channel doSendMessageRequest>`                                                                                  |
| Stream keeps **one stable message id** for the whole lifecycle; Sendbird swaps `reqId` for `messageId` on success                                               | Id-swap code double-keys the list and breaks retry. Delete the `reqId` reconciliation                                                                                                                                                                 |
| `StreamChat.getInstance(apiKey)` is a first-call-wins process singleton, not keyed by apiKey                                                                    | Wrong app silently reused. UI flavor: `useCreateChatClient`; headless-core: one `new StreamChat(apiKey)` at module scope                                                                                                                              |
| **Stream always needs a token**, and a new Stream app has dev tokens off                                                                                        | `client.devToken(id)` is rejected server-side. Pre-mint a fixed user roster (section 5); never loosen the app's auth to get Sendbird's connect-any-userId behavior                                                                                    |
| `client.muteUser` is a personal notification mute, not Sendbird's operator silencing                                                                            | "Muted" users keep posting. Operator mute -> timed `channel.banUser(id, { timeout, reason })` - Sendbird durations are **seconds**, Stream `timeout` is **minutes**: a 1:1 port makes every ban 60x longer                                            |
| Blocking is DM-only in Stream, global in Sendbird                                                                                                               | Blocked users keep posting in shared group channels. Filter client-side or moderate                                                                                                                                                                   |
| Message and channel deletes are **soft** by default; Sendbird's are permanent                                                                                   | Data retention silently changes - hard-delete where the app promised purging                                                                                                                                                                          |
| Events arrive only for **watched** channels                                                                                                                     | Handlers ported as global listeners miss events for channels nobody watched                                                                                                                                                                           |
| `OpenChannel` -> `livestream` type, which has read events off                                                                                                   | Unread counts silently stop on migrated open channels. Pass `options: { isLocalUnreadCountEnabled: true }` to `useCreateChatClient`; `<Channel>` then marks read locally                                                                              |
| **Offline is opt-in.** Sendbird UIKit cached by default; Stream needs `<Chat enableOfflineSupport>` + `@op-engineering/op-sqlite` (native rebuild)              | State stops surviving restarts. And on sign-out, `await client.offlineDb?.resetDB()` **before** `disconnectUser()`, or the next user sees the previous user's data                                                                                    |
| Every stateful `.next()` / `.load()` query cursor dies                                                                                                          | Each becomes a stateless offset/id-cursor call - per-query recipes in mapping section 7                                                                                                                                                               |
| Distinct (DM) channels come from **omitting the id**, not a flag                                                                                                | `client.channel('messaging', { members })` with no id dedupes by member set; passing an id disables it                                                                                                                                                |
| Stream does **not** auto-create users named as members; Sendbird did                                                                                            | `channel.create()` / `addMembers()` fails ("users don't exist"). Upsert the users server-side first (`getstream api UpdateUsers`)                                                                                                                     |
| Mutations (edit, pin, react, translate) echo back as events and update `channel.state` on their own                                                             | A parallel cache of the response drifts, and the response type can mislead (`translateMessage` nests under `.message`, so `res.i18n` typechecks but is `undefined`). Read live state; never `client.dispatchEvent` it again                           |
| `useOwnCapabilitiesContext()` **throws** outside `<Channel>`                                                                                                    | Hand-built settings / members / moderation screens crash on mount (tsc passes). Use `useChannelOwnCapabilities(channel)` there                                                                                                                        |
| No `<Window>` and no `ChannelHeader` slot in RN - the header is app-owned                                                                                       | Port the header into the navigator, title from channel state. A custom header rendered as a sibling above `<Channel>` can push the composer off-screen - render it inside `<Channel>`, with the offsets from "Keyboard and picker insets" in SKILL.md |
| Voice recording is opt-in: `<Channel audioRecordingEnabled>` defaults to `false`                                                                                | Sendbird's `enableVoiceMessage` silently disappears - the composer shows no mic                                                                                                                                                                       |
| `react-native-teleport` (a Chat peer) has `react-dom` as an optional peer                                                                                       | An app that already has `react-dom` (the default Expo template) can resolve a version that doesn't match its `react` and fail strict peer resolution. Pin `react-dom` to the app's exact `react` version instead of `--legacy-peer-deps`              |

## 3. Decide the gaps with the user

Features with no Stream equivalent (mapping section 15: `FeedChannel`, scheduled
messages, channel-level report, `copyMessage`, recurring DND quiet hours,
AI-agent/Desk conversations, a free-text "type any name" login, ...) are product
decisions - the user's, not yours: **substitute** (the mapping names the closest
one), **rebuild app-side**, or **drop**. Ask once, batched with any open
credentials or design-fidelity question - never a drip of single questions. If
the user isn't available, take the mapping's named substitute, mark the ledger
row `GAP - provisional`, and call every provisional decision out in the final
report.

## 4. Packages

Install Stream alongside Sendbird first. Keep Sendbird until the migration is
complete.

1. Add `stream-chat` + the flavor package (`npx expo install stream-chat-expo`,
   or `stream-chat-react-native`) and the required peers and app-entry wiring
   (`GestureHandlerRootView`, `<OverlayProvider>` above the navigator) from the
   Installation page of the pinned major's docs. Skipping a piece gives broken
   overlays or a crash, not a clean error.
2. Start the native build now - an Expo dev build (`npx expo prebuild --clean` +
   `npx expo run:ios`), not Expo Go, which can't load Stream's native modules; or
   `pod install` + `npx react-native run-ios`. It is the slowest step, and
   starting it early surfaces native peer failures while you migrate.

## 5. Credentials & connection

Sendbird connects with just a `userId` (token optional, users auto-created);
Stream always requires a signed JWT - there is no userId-only path. Check the
connection end-to-end before migrating any UI:

1. **Key:** use Stream app credentials the user provided or that exist in the
   project. If none exist, run `getstream init`.
2. **Token path:** `SessionHandler.onSessionTokenRequired(resolve, reject)`
   becomes an async `tokenProvider` passed as `tokenOrProvider`. An existing
   token endpoint gets re-pointed to mint Stream JWTs, deriving the user id from
   its own session, never from a client parameter.
3. **Dev:** connect as one of a fixed roster of test users. Mint each token with
   `getstream token <user_id>` (one call per user), keep them in a
   `__DEV__`-gated module so they can't ship, and upsert the roster users
   server-side once so they can be channel members.
4. Connect as a roster user from a small debug-only screen and confirm
   `useChatContext().isOnline`. Delete the debug screen after migration is done.
   A login that hangs - here or in the original Sendbird app - is usually a
   30-60s cold connect, not a dead backend: wait ~60s and re-screenshot before
   debugging auth.

```tsx
// <SendbirdUIKitContainer appId platformServices> connected internally.
// Stream splits it: you build + connect the client; platformServices are dropped.
const client = useCreateChatClient({
  apiKey, // was Sendbird appId
  tokenOrProvider, // string token, or async () => Promise<string>
  userData: { id: userId, name: nickname },
});
if (!client) return null; // still connecting
return (
  <OverlayProvider>
    <Chat client={client}>{/* navigator */}</Chat>
  </OverlayProvider>
);
```

## 6. Migrate

File-by-file, in place, referencing the mapping, and tracking progress in the
ledger:

- **UI composition** (mapping section 12-13): `createGroupChannelFragment` ->
  `<Channel channel={c}><MessageList/><MessageComposer/></Channel>`;
  `createGroupChannelListFragment` -> `<ChannelList filters sort onSelect>`
  (on another major, take the composition from that major's docs,
  chat-versions.md). The header is your navigator's. `renderX` props ->
  `<WithComponents overrides>` mounted above the navigator - `<Channel>` takes
  no component props (tsc rejects one; in JS it is silently ignored). Keep
  `<ChannelList>` as the query/watch/state owner - don't maintain a parallel
  `queryChannels()` result. Writing your own component for a prebuilt region
  owes the completion contract in design-matching.md - build it to the baseline
  look now, not to SDK defaults for a later reskin.
- **Channels** (section 2, 7): three channel classes -> one `Channel` + type
  string; `OpenChannel` -> `livestream`; `isDistinct` -> member-set channel with
  no id; every query cursor -> a stateless call.
- **Messages & attachments** (section 3, 4): the message class hierarchy -> one
  shape with `attachments[]`; `MessageRequestHandler` callbacks -> the UI-path
  optimistic send + `message.status`; atomic `sendFileMessage` -> the composer's
  `AttachmentManager` pipeline.
- **Events & real-time** (section 5, 6): keyed handler objects -> per-event
  `on()` with a retained `unsubscribe` in the effect cleanup;
  `MessageCollection` -> `<Channel>` + reactive `channel.state`. Delete
  hand-rolled typing timers, presence polls, reconnect machines and manual
  `markAsRead`.

```tsx
useEffect(() => {
  // new GroupChannelHandler({ onMessageReceived }) + addGroupChannelHandler(key, h)
  const { unsubscribe } = channel.on("message.new", (event) => {
    // MessageList already re-renders from this event - subscribe by hand only
    // for side effects the components don't own (badges, analytics, navigation).
  });
  return () => unsubscribe(); // removeGroupChannelHandler(key)
}, [channel]);
```

- **Membership & moderation** (section 8): gate UI on own capabilities, not a
  role string. Role changes (`addModerators`, `assignRoles`) need a server
  token, so move them to a backend and record the gap. Port end-user actions
  only - review UI stays in the Stream Dashboard.
- **Offline** (section 5): opt in only if the app relied on Sendbird's cache;
  delete `onHugeGapDetected` / changelog rebuilds - recovery is automatic.
- **Polls, search, push** (section 9-11) where the app uses them.

At this point you can remove all three Sendbird packages and the platform-service
factories, and grep for zero `@sendbird` imports.

Seeding note: Stream clients act only as themselves - cross-user seeding is
server-side. Keep only a thin "ensure my own channels exist" step if the
original had one. Seed reactions only with types in `supportedReactions`
(default `like`, `love`, `haha`, `wow`, `sad`): other types never render, which
looks like a layout bug. Put one on an incoming and an outgoing message.

## 7. Theming

Sendbird's theming levers (`createTheme`, `colorSet`, `LightUIKitTheme` /
`DarkUIKitTheme`, `StringSet`) all die - their replacements are in mapping
section 14. In RN the theme is a JS object, not CSS, and it carries dimensions as
well as colors. Then treat the captured visual baseline as the reference design
and verify per design-matching.md. Reactions and the composer diverge most:
Sendbird often attaches reactions to the bubble and puts send/mic outside the
input pill, where Stream's defaults don't - treat the Stream default there as
wrong until a crop proves otherwise.

## 8. Verify

Run every check from an absolute `cd` and never pipe it - both fake a pass
(simulator-verification.md).

1. **Types:** `npx tsc --noEmit` - zero errors.
2. **Native build:** the app builds and bundles for its flavor - read the build
   log, not just the exit code.
3. **Sendbird is gone:** zero `@sendbird` imports, all three packages
   uninstalled.
4. **Runtime smoke, two users:** two simulators/emulators, or one plus the
   second user acting server-side (`getstream api SendMessage` with its
   `user_id`). With user B logged in, have user A create a conversation with B.
   It must appear in B's channel list without a refresh, before any message is
   sent. Then send each way: each message appears exactly once for the sender,
   arrives live, unread badges and typing move. Then drive every interaction the
   original has - send an attachment through the picker, reply, edit,
   long-press, react, reply in a thread, navigate back - and confirm each
   effect; a screenshot of a button proves nothing about its handler. If you
   can't run the app, ask the user to run this check; never skip it silently.
5. **Design:** the channel screen shows the header, an incoming bubble, an
   outgoing bubble, and the composer in one frame; then the result matches the
   visual baseline region by region, in all states, on seed data that renders
   every region.
6. **Ledger:** every row Ported / Rewritten / N/A / GAP-with-decision;
   provisional gaps called out explicitly in the report.
7. **Docs match reality:** rewrite the README/feature list against what the
   migrated app actually does, with a "Known gaps vs the Sendbird original"
   section from the GAP rows.

## 9. Offer the data migration

The app now points at an empty Stream app: no users, channels, or history moved.
Ask whether to migrate the Sendbird data too; only if yes, follow the stream
skill's sendbird-data-migration.md.
