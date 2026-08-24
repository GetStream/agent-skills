# Migrating from Sendbird (code)

Migrates a React / Next.js app from the Sendbird Chat SDK (`@sendbird/chat` +
`@sendbird/uikit-react`) to Stream Chat (`stream-chat` + `stream-chat-react`). Works on any
integration shape - UIKit drop-in, custom hooks, a Context+reducer store, direct calls -
because it detects the shape first and re-implements each touchpoint in place. This migrates
code only; moving the data is the `stream` skill's `sendbird-data-migration.md` (step 9).

Three rules, learned from real migration runs:

1. **Migrate in place.** Preserve component boundaries, routing, and public prop/hook
   signatures; edit the existing files (Sendbird out, Stream in) - no parallel new files.
   New files only for genuinely new needs (a token endpoint that never existed); a file
   whose entire content was Sendbird machinery (a `colorSet` module) is deleted, not kept
   as a husk.
2. **Almost nothing is codemod-safe.** In a full audit of these two SDKs, fewer than 2% of
   symbol pairs survived a mechanical rename. Work file-by-file from the mapping tables;
   never a global find-and-replace.
3. **Prefer idiomatic Stream over a mechanical port.** Where the app hand-rolled machinery
   Stream has first-class (typing timers, presence polling, cursor bookkeeping, send-state
   callbacks), delete the machinery and use the reactive primitive - inside the existing
   file/hook boundary, so callers don't change. The idiomatic rewrite is smaller and less
   buggy than the faithful port.

Symbol lookup order: [`sendbird-mapping.md`](sendbird-mapping.md) (curated, verified) ->
grep [`sendbird-mapping-extended.md`](sendbird-mapping-extended.md) for the exact symbol
(~520 machine-inferred rows; a lookup table, never read end-to-end) -> the local docs and the
installed types. If `npx tsc --noEmit` disagrees with any row, the compiler is right.

## 1. Detect & inventory

Map the footprint before any edit:

```bash
grep -rln "@sendbird/chat\|@sendbird/uikit-react" --include=*.{ts,tsx,js,jsx} .
grep -rn "SendbirdProvider\|GroupChannel\|OpenChannel\|useSendbirdStateContext\|sendbirdSelectors\|withSendBird" --include=*.{ts,tsx} .
cat package.json   # both Sendbird versions and the package manager
```

| Pattern found | How it migrates |
|---|---|
| UIKit drop-in (`<SendbirdProvider>`, `<GroupChannel>`, `renderX` props) | Architectural remap, not a rename - compose Stream primitives (mapping section 12) |
| Custom hook wrapping the SDK (returns `{ state, actions }`) | Keep the hook's public return shape; replace the body. Callers don't change |
| Context + reducer store | Keep the store shape; effects do the async Stream work and re-dispatch |
| Class component via `withSendBird` | Stream context is hooks-only - convert to a function component or wrap in a thin adapter |
| Direct / inline SDK calls | Swap in place; keep surrounding layout/routing |
| Spaghetti | File-by-file; a thin boundary only where it cuts churn |

**Build the parity ledger.** List every user-facing chat feature - from the code, the
README, and the UIKit config flags (`enableOgtag`, `enableSuggestedReplies`, `replyType`,
voice messages, ...). One row per feature; every row must end **Ported**, **Rewritten**,
**N/A - reason**, or **GAP - decision**. Real migrations dropped features exactly where no
ledger existed: UIKit one-liner toggles vanished while the README kept advertising them.

**Capture the visual baseline now.** A migration briefly holds the best design reference
there is - the original app running, whose DOM you can probe and whose states you can
drive. That window closes at the first edit. Take the highest rung you can reach:

1. **The original runs:** capture full screens plus element crops (composer, a message
   row, a quoted reply, a reaction pill), probe computed styles on the `sendbird-*`
   selectors, and drive the states - open reaction picker, hover actions, thread, a long
   draft, both themes. The capture guidance in [`design-matching.md`](design-matching.md)
   applies. An `npm install` and an env file are worth resurrecting the original for.
2. **User-provided screenshots** - ask if any exist.
3. **Code-derived** (always available): palette from `colorSet`, strings from `stringSet`,
   layout structure. Say explicitly this rung can't certify composer/bubble/reaction
   fidelity - only structure.

Whichever rung produced it, this baseline is the reference design for step 7.

## 2. Kill list - traps that bit real migrations

Behavioral differences that produce silent runtime bugs, not build errors. Check every one:

| # | Trap | If ported 1:1 |
|---|---|---|
| 1 | **Stream echoes your own sent message** (`message.new` fires for your own send, on top of the optimistic insert); Sendbird never did | Every `onSucceeded`-append pattern double-adds messages. Remove manual appends |
| 2 | React `<Channel>` skips its mount-time `watch()` when `channel.initialized` is true | Re-mounting `<Channel>` is not a refresh - call `channel.watch()` / `query()` explicitly |
| 3 | `client.muteUser` is a personal notification mute, not Sendbird's operator silencing | "Muted" users keep posting. Operator mute -> timed `channel.banUser(id, { timeout, reason })` - and Sendbird durations are **seconds**, Stream `timeout` is **minutes**: a 1:1 port makes every ban 60x longer |
| 4 | Blocking is DM-only in Stream, global in Sendbird | Blocked users stay visible in group channels unless you also mute + filter |
| 5 | `StreamChat.getInstance` is a bare singleton not keyed by apiKey; never use it client-side | Wrong app silently reused. Use `useCreateChatClient` |
| 6 | `channel.delete()` / message deletes are **soft** by default; Sendbird's are permanent | Data retention silently changes - pass `hard_delete` where the app promised purging |
| 7 | Events arrive only for **watched** channels | Handlers ported as global listeners miss events for channels nobody watched |
| 8 | Sibling panes must become `<Channel>` descendants | Sendbird renders search/thread/settings as siblings of the conversation; Stream's equivalents read channel context - a restructure, not a rename |
| 9 | `<Chat theme>` is a CSS class name (`str-chat__theme-dark`), not `'light' \| 'dark'`; no `colorSet` prop exists | Theme switching silently does nothing; recoloring moves to `--str-chat__*` CSS variables |
| 10 | CSS import is `stream-chat-react/dist/css/index.css` | The old v2 path doesn't resolve - unstyled UI or a build error |
| 11 | No offline cache on web - Sendbird UIKit enabled one by default | State no longer survives reload; accept event-driven re-hydration |
| 12 | Every stateful `.next()` query cursor dies (~13 query types) | Each becomes a stateless offset/id-cursor call - per-query recipes in mapping section 7 |
| 13 | Poll booleans invert: `allowMultipleVotes` -> `enforce_unique_vote`; `castPollVote` takes one option per call | Multi-vote semantics flip. Both trial runs hit this |
| 14 | Read receipts keep data only for the latest own message by default | Per-message receipts vanish - set `returnAllReadData` on `<MessageList>` |

## 3. Decide the gaps with the user

Features with no Stream equivalent (mapping section 15: scheduled messages, channel-level report,
`copyMessage`, `FeedChannel`, offline cache, DND quiet hours, ...) are product decisions -
the user's, not yours: **substitute** (the mapping names the closest one), **rebuild
app-side**, or **drop**. Ask once, batched with any open credentials or design-fidelity
question - never a drip of single questions. If the user isn't available, take the mapping's
named substitute, mark the ledger row `GAP - provisional`, and call every provisional
decision out in the final report.

## 4. Packages

Install Stream alongside Sendbird first; remove Sendbird last - ripping Sendbird out now
leaves the app unbuildable until every touchpoint is migrated.

1. Add `stream-chat` + `stream-chat-react` with the project's package manager (npm:
   `--legacy-peer-deps`). They version independently - never one shared version string.
2. Add `import 'stream-chat-react/dist/css/index.css';` once at app entry (kill #10).
3. Only after step 6 completes: uninstall the Sendbird packages, delete their stylesheet
   import, and grep to confirm zero `@sendbird` imports remain.

## 5. Credentials & connection proof

The biggest conceptual shift: Sendbird connects with just a `userId` (token optional);
**Stream always requires a signed JWT** - there is no userId-only path. Prove the
connection end-to-end before migrating any UI - a real run shipped a fully migrated app
that had never once connected.

1. **Key:** use credentials the user provided or that exist in the project's env/config
   as-is; only if none exist, run `getstream init` (the one onboarding step this migration
   needs). Never invent a key.
2. **Token path:** `SessionHandler.onSessionTokenRequired(resolve, reject)` -> an async
   `tokenProvider` (`return` = resolve, `throw` = reject) passed as `tokenOrProvider`. An
   existing Sendbird token endpoint gets re-pointed to mint Stream JWTs.
3. **Dev:** `client.devToken(userId)` works only while "Disable Auth Checks" is on for the
   Stream app - otherwise it's rejected server-side. Without a backend, pre-sign real
   tokens (`getstream token <user-id>`) into gitignored env vars - never source. In a
   backend-less SPA a static token string is fine for a demo, but it never refreshes - a
   real deployment needs a token endpoint.
4. Connect as a real user in a small dev-only proof component (the Sendbird tree is still
   intact) and confirm the WebSocket is healthy. Delete the proof once step 6 wires the
   real flow.

```tsx
// <SendbirdProvider appId userId nickname accessToken> connected internally.
// Stream splits it: you build + connect the client; <Chat> is a plain provider.
const client = useCreateChatClient({
  apiKey,                          // was Sendbird appId
  tokenOrProvider,                 // string token, or async () => Promise<string>
  userData: { id: userId, name: nickname },
});
if (!client) return null;          // still connecting
return <Chat client={client}>{/* ChannelList / Channel composition */}</Chat>;
```

## 6. Migrate the touchpoints

File-by-file, in place, per the step-1 classification, pulling exact symbols from the
mapping:

- **UI composition** (mapping section 12-13): `<GroupChannel>` -> composed
  `<Channel><Window><MessageList/><MessageComposer/></Window><Thread/></Channel>`;
  `<GroupChannelList>` -> `<ChannelList>`; `renderX` props -> component swaps via
  `<WithComponents>`; `useSendbirdStateContext` -> focused context hooks. Keep
  `<ChannelList>` as the query/watch/state owner - don't maintain a parallel
  `queryChannels()` result. Every migrated `OpenChannel` (and any high-throughput channel)
  renders `<VirtualizedMessageList>`, not `<MessageList>`. Move sibling panes inside
  `<Channel>` (kill #8). Writing your own component for a prebuilt region owes the
  completion contract in [`design-matching.md`](design-matching.md) - and on a live-capture
  baseline, build it to the measured look now; migrating to SDK defaults and reskinning
  later rebuilds the same region twice.
- **Channels** (section 2, 7): three channel classes -> one `Channel` + type string; `OpenChannel`
  -> `livestream` type; `isDistinct` -> member-set channel with no id; every query cursor ->
  a stateless call.
- **Messages & attachments** (section 3, 4): the message class hierarchy -> one shape with
  `attachments[]`; `MessageRequestHandler` callbacks -> optimistic send + `message.status`;
  atomic `sendFileMessage` -> the composer's `AttachmentManager` pipeline.
- **Events & real-time** (section 5, 6): keyed handler objects -> per-event `on()` with a retained
  `unsubscribe` in the effect cleanup; `MessageCollection` -> `watch()` + reactive
  `channel.state` + events. Delete hand-rolled typing timers and presence polls (rule 3).

```tsx
useEffect(() => {
  // new GroupChannelHandler({ onMessageReceived }) + addGroupChannelHandler(key, h)
  const { unsubscribe } = client.on('message.new', (event) => {
    if (event.user?.id === client.userID) return; // kill #1: ignore own echo
    // ...
  });
  return () => unsubscribe();                     // removeGroupChannelHandler(key)
}, [client]);
```

- **Membership & moderation** (section 8): operators -> moderators/roles + permission grants; the
  mute/ban/block/report semantics per the kill list. Port end-user actions only - review
  UI stays in the Stream Dashboard.
- **Polls, search, push** (section 9-11) where the app uses them.

Then finish step 4.3: remove the Sendbird packages, grep for zero `@sendbird` imports.

Seeding note: Sendbird apps often self-seed by connecting as several users in turn. Stream
clients act only as themselves - cross-user seeding is server-side. Keep only a thin
"ensure my own channels exist" step if the original had one.

## 7. Re-theme & verify the look

Sendbird's theming levers (`colorSet`, `stringSet`, mode-string themes) all die - their
replacements are in mapping section 14. Then treat the step-1 baseline as the reference design and
verify per [`design-matching.md`](design-matching.md). Both real trial runs shipped
unverified skins - a match comes from a capture of the migrated app, not from ported CSS.

## 8. Verify - gates, in order

Each gate caught a failure a real migration shipped:

1. **Types:** `npx tsc --noEmit` - zero errors.
2. **Build:** the project's own build script succeeds.
3. **The bundle actually contains Stream:** grep the build output (e.g.
   `grep -rlc "str-chat" dist/assets/*.js`) and sanity-check the main chunk grew. A trial
   migration shipped a "successful" build whose bundle contained no Stream SDK at all.
4. **Runtime smoke, two tabs:** have user A create a conversation *before sending its
   first message* - user B's channel rail must gain it live, with no refresh. Then message
   each way: it appears exactly once for the sender (kill #1), arrives live, unread badges
   and typing move, console clean. No browser tooling -> ask the user to run this check;
   never skip it silently.
5. **Design:** the step-7 loop reaches its exit against the baseline, driven states
   included.
6. **Ledger closure:** every row Ported / Rewritten / N/A / GAP-with-decision; provisional
   gaps called out explicitly in the report.
7. **Docs match reality:** rewrite the README/feature list against what the migrated app
   actually does, with a "Known gaps vs the Sendbird original" section from the GAP rows.

## 9. Offer the data migration - never auto-run it

The app now points at an empty Stream app: no users, channels, or history moved. Once the
gates pass, ask whether to migrate the Sendbird data too; if yes, follow the `stream`
skill's `sendbird-data-migration.md`. It touches production data and may incur
attachment-transfer cost - offer, don't start.