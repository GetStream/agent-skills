# Migrating from Sendbird to Stream Chat React: runbook

Migrates a React / Next.js app from the Sendbird Chat SDK (`@sendbird/chat` +
`@sendbird/uikit-react`) to Stream Chat (`stream-chat` + `stream-chat-react`).
These are code migration instructions. Data migration is explained in the
stream skill's sendbird-data-migration.md.

**Migrate in place.** Preserve component boundaries, routing, and public
prop/hook signatures. Edit the existing files (Sendbird out, Stream in), and
don't create parallel new files. New files are acceptable for genuinely new
needs (e.g. a token endpoint that never existed). If a whole file was serving
Sendbird machinery (e.g. a `colorSet` module), clean it up.

**Not codemod-safe.** Sendbird and Stream work differently. Almost nothing in
the migration is a mechanical rename. Work file-by-file from the mapping tables,
never a global find-and-replace.

**Prefer idiomatic Stream over a mechanical port.** Stream has first-class
support for the features that require hand-rolled machinery with Sendbird
(typing timers, presence polling, cursor bookkeeping, send-state callbacks).
Delete the machinery and use the reactive primitive inside the existing
file/hook boundary, so callers don't change. The idiomatic rewrite is smaller
and less buggy than the faithful port.

Symbol lookup: start with sendbird-mapping.md. For the symbols it doesn't have,
grep sendbird-mapping-extended.md for the exact symbol (don't read this big
table). Additional sources are local docs with `getstream docs` and the
installed types.

## 1. Detect & inventory

Map the footprint before any edit:

```bash
grep -rln "@sendbird/chat\|@sendbird/uikit-react" --include=*.{ts,tsx,js,jsx} .
grep -rn "SendbirdProvider\|GroupChannel\|OpenChannel\|useSendbirdStateContext\|sendbirdSelectors\|withSendBird" --include=*.{ts,tsx} .
cat package.json   # both Sendbird versions and the package manager
```

| Pattern found                                                           | How it migrates                                                                          |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| UIKit drop-in (`<SendbirdProvider>`, `<GroupChannel>`, `renderX` props) | Architectural remap, not a rename - compose Stream primitives (mapping section 12)       |
| Custom hook wrapping the SDK (returns `{ state, actions }`)             | Keep the hook's public return shape; replace the body. Callers don't change              |
| Context + reducer store                                                 | Keep the store shape; effects do the async Stream work and re-dispatch                   |
| Class component via `withSendBird`                                      | Stream context is hooks-only - convert to a function component or wrap in a thin adapter |
| Direct / inline SDK calls                                               | Swap in place; keep surrounding layout/routing                                           |
| Spaghetti                                                               | File-by-file; a thin boundary only where it cuts churn                                   |

**Build the parity ledger.** List every user-facing chat feature - from the
code, the README, and the UIKit config flags (`enableOgtag`,
`enableSuggestedReplies`, `replyType`, voice messages, ...). One row per
feature. Mark the features **Ported**, **Rewritten**, **N/A - reason**, or
**GAP - decision**.

**Capture the visual baseline now**, before the first edit. The original app is
the best design reference there is, so get it running - install its dependencies
and set up its Sendbird env if you have to. Capture full screens plus element
crops (composer, a message row, a quoted reply, a reaction pill), probe computed
styles on the `sendbird-*` selectors, and drive the states - open reaction
picker, hover actions, thread, a long draft, both themes. The capture guidance
in design-matching.md applies.

If the original can't run, fall back to user-provided screenshots (ask) and the
code (palette from `colorSet`, strings from `stringSet`, layout structure) - and
say so in the report, since code alone certifies structure, not the look.

## 2. Beware of these traps

| Trap                                                                                                                                 | If ported 1:1                                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Stream echoes your own sent message** (`message.new` fires for your own send, on top of the optimistic insert); Sendbird never did | Every `onSucceeded`-append pattern double-adds messages. Remove manual appends                                                                                                                                 |
| React `<Channel>` skips its mount-time `watch()` when `channel.initialized` is true                                                  | Re-mounting `<Channel>` is not a refresh - call `channel.watch()` / `query()` explicitly                                                                                                                       |
| `client.muteUser` is a personal notification mute, not Sendbird's operator silencing                                                 | "Muted" users keep posting. Operator mute -> timed `channel.banUser(id, { timeout, reason })` - and Sendbird durations are **seconds**, Stream `timeout` is **minutes**: a 1:1 port makes every ban 60x longer |
| Blocking is DM-only in Stream, global in Sendbird                                                                                    | Blocked users stay visible in group channels unless you also mute + filter                                                                                                                                     |
| `StreamChat.getInstance` is a bare singleton not keyed by apiKey; never use it client-side                                           | Wrong app silently reused. Use `useCreateChatClient`                                                                                                                                                           |
| `channel.delete()` / message deletes are **soft** by default; Sendbird's are permanent                                               | Data retention silently changes - pass `hard_delete` where the app promised purging                                                                                                                            |
| Events arrive only for **watched** channels                                                                                          | Handlers ported as global listeners miss events for channels nobody watched                                                                                                                                    |
| Sibling panes must become `<Channel>` descendants                                                                                    | Sendbird renders search/thread/settings as siblings of the conversation; Stream's equivalents read channel context - a restructure, not a rename                                                               |
| `<Chat theme>` is a CSS class name (`str-chat__theme-dark`), not `'light' \| 'dark'`; no `colorSet` prop exists                      | Theme switching silently does nothing; recoloring moves to `--str-chat__*` CSS variables                                                                                                                       |
| CSS import is `stream-chat-react/dist/css/index.css`                                                                                 | The old v2 path doesn't resolve - unstyled UI or a build error                                                                                                                                                 |
| No offline cache on web - Sendbird UIKit enabled one by default                                                                      | State no longer survives reload; accept event-driven re-hydration                                                                                                                                              |
| Every stateful `.next()` query cursor dies (~13 query types)                                                                         | Each becomes a stateless offset/id-cursor call - per-query recipes in mapping section 7                                                                                                                        |
| Poll booleans invert: `allowMultipleVotes` -> `enforce_unique_vote`; `castPollVote` takes one option per call                        | Multi-vote semantics flip. Both trial runs hit this                                                                                                                                                            |
| Read receipts keep data only for the latest own message by default                                                                   | Per-message receipts vanish - set `returnAllReadData` on `<MessageList>`                                                                                                                                       |

## 3. Decide the gaps with the user

Features with no Stream equivalent (mapping section 15: scheduled messages,
channel-level report, `copyMessage`, `FeedChannel`, offline cache, DND quiet
hours, ...) are product decisions - the user's, not yours: **substitute** (the
mapping names the closest one), **rebuild app-side**, or **drop**. Ask once,
batched with any open credentials or design-fidelity question - never a drip of
single questions. If the user isn't available, take the mapping's named
substitute, mark the ledger row `GAP - provisional`, and call every provisional
decision out in the final report.

## 4. Packages

Install Stream alongside Sendbird first. Keep Sendbird until the migration is
complete.

1. Add `stream-chat` + `stream-chat-react`.
2. Add `import 'stream-chat-react/dist/css/index.css';` once at app entry.

## 5. Credentials & connection

Sendbird connects with just a `userId` (token optional); Stream always requires
a signed JWT - there is no userId-only path. Check the connection end-to-end
before migrating any UI:

1. **Key:** use Stream app credentials the user provided or that exist in the
   project. If none exist, run `getstream init`.
2. **Token path:** `SessionHandler.onSessionTokenRequired(resolve, reject)`
   becomes an async `tokenProvider` passed as `tokenOrProvider`. An existing
   token endpoint gets re-pointed to mint Stream JWTs.
3. **Dev:** `client.devToken(userId)` works only while "Disable Auth Checks" is
   on for the Stream app - otherwise it's rejected server-side. Without a
   backend, pre-sign real tokens (`getstream token`) into gitignored env - never
   source. In a backend-less SPA a static token string is fine for a demo, but
   it never refreshes. A real deployment needs a token endpoint.
4. Connect as a real user in a small debug-only component and confirm the
   WebSocket is healthy. Delete the debug component after migration is done.

```tsx
// <SendbirdProvider appId userId nickname accessToken> connected internally.
// Stream splits it: you build + connect the client; <Chat> is a plain provider.
const client = useCreateChatClient({
  apiKey, // was Sendbird appId
  tokenOrProvider, // string token, or async () => Promise<string>
  userData: { id: userId, name: nickname },
});
if (!client) return null; // still connecting
return <Chat client={client}>{/* ChannelList / Channel composition */}</Chat>;
```

## 6. Migrate

File-by-file, in place, referencing the mapping, and tracking progress in the
ledger:

- **UI composition** (mapping section 12-13): `<GroupChannel>` -> composed
  `<Channel><Window><MessageList/><MessageComposer/></Window><Thread/></Channel>`;
  `<GroupChannelList>` -> `<ChannelList>`; `renderX` props -> component swaps
  via `<WithComponents>`; `useSendbirdStateContext` -> focused context hooks.
  Keep `<ChannelList>` as the query/watch/state owner - don't maintain a
  parallel `queryChannels()` result. Every migrated `OpenChannel` (and any
  high-throughput channel) renders `<VirtualizedMessageList>`, not
  `<MessageList>`. Move sibling panes inside `<Channel>`. Writing your own
  component for a prebuilt region owes the completion contract in
  design-matching.md - and on a live-capture baseline, build it to the measured
  look now; migrating to SDK defaults and reskinning later rebuilds the same
  region twice.
- **Channels** (section 2, 7): three channel classes -> one `Channel` + type
  string; `OpenChannel` -> `livestream` type; `isDistinct` -> member-set channel
  with no id; every query cursor -> a stateless call.
- **Messages & attachments** (section 3, 4): the message class hierarchy -> one
  shape with `attachments[]`; `MessageRequestHandler` callbacks -> optimistic
  send + `message.status`; atomic `sendFileMessage` -> the composer's
  `AttachmentManager` pipeline.
- **Events & real-time** (section 5, 6): keyed handler objects -> per-event
  `on()` with a retained `unsubscribe` in the effect cleanup;
  `MessageCollection` -> `watch()` + reactive `channel.state` + events. Delete
  hand-rolled typing timers and presence polls.

```tsx
useEffect(() => {
  // new GroupChannelHandler({ onMessageReceived }) + addGroupChannelHandler(key, h)
  const { unsubscribe } = client.on("message.new", (event) => {
    if (event.user?.id === client.userID) return; // Stream echoes your own send - ignore it
    // ...
  });
  return () => unsubscribe(); // removeGroupChannelHandler(key)
}, [client]);
```

- **Membership & moderation** (section 8): operators -> moderators/roles +
  permission grants; the mute/ban/block/report semantics per the traps in
  section 2. Port end-user actions only - review UI stays in the Stream
  Dashboard.
- **Polls, search, push** (section 9-11) where the app uses them.

At this point you can remove the Sendbird packages, grep for zero `@sendbird`
imports.

Seeding note: Sendbird apps often self-seed by connecting as several users in
turn. Stream clients act only as themselves - cross-user seeding is server-side.
Keep only a thin "ensure my own channels exist" step if the original had one.

## 7. Theming

Sendbird's theming levers (`colorSet`, `stringSet`, mode-string themes) all
die - their replacements are in mapping section 14. Then treat the captured
visual baseline as the reference design and verify per design-matching.md.

## 8. Verify

1. **Types:** `npx tsc --noEmit` - zero errors.
2. **Build:** the project's own build script succeeds.
3. **The bundle actually contains Stream:** grep the build output (e.g.
   `grep -rlc "str-chat" dist/assets/*.js`) and check that the main chunk grew.
4. **Runtime smoke, two tabs:** log in as user B in one tab, then have user A
   create a conversation with B in another. The conversation must appear in B's
   channel list without a refresh, before any message is sent. Only then send
   messages each way: each appears exactly once for the sender, arrives live,
   unread badges and typing move, console clean. No browser tooling -> ask the
   user to run this check; never skip it silently.
5. **Design:** the result matches the visual baseline, in all states.
6. **Ledger:** every row Ported / Rewritten / N/A / GAP-with-decision;
   provisional gaps called out explicitly in the report.
7. **Docs match reality:** rewrite the README/feature list against what the
   migrated app actually does, with a "Known gaps vs the Sendbird original"
   section from the GAP rows.

## 9. Offer the data migration

The app now points at an empty Stream app: no users, channels, or history moved.
Ask whether to migrate the Sendbird data too; only if yes, follow the stream
skill's sendbird-data-migration.md.
