# Sendbird -> Stream Chat React Native migration (Track S)

A repeatable procedure for migrating a **React Native app (Expo or bare RN CLI)** from the
**Sendbird Chat SDK** (`@sendbird/chat` + `@sendbird/uikit-react-native` +
`@sendbird/uikit-react-native-foundation`) to **Stream Chat** (`stream-chat` +
**`stream-chat-react-native`** for bare RN, **`stream-chat-expo`** for Expo). It works on *any*
Sendbird integration shape - UIKit fragment drop-in, custom hooks, a Context+reducer store,
`MessageCollection`-driven screens, or direct SDK calls - because it **detects the shape first** and
re-implements each touchpoint in place. This is not a scaffold track: do not enter Track A, Track B,
or any onboarding step.

This file owns the **procedure**; the cross-SDK knowledge lives in
[`references/sendbird-mapping.md`](references/sendbird-mapping.md) (symbol tables, behavioral
diffs, pagination recipes, feature-gap catalog - grounded against the installed SDK types and
`tsc`-verified recipes), with a concept-level companion
([`references/sendbird-mapping-extended.md`](references/sendbird-mapping-extended.md), domain-level
model mapping + the unmapped-symbol resolution protocol) for symbols the curated file doesn't carry.
Where a step touches a Stream RN component's *current* props/hooks, fetch the matching page via
[`references/DOCS.md`](references/DOCS.md) per [`RULES.md`](RULES.md) > Package version and docs
discipline - a future major can rename symbols (exactly as Chat RN v8 -> v9 did, see
[`migrate.md`](migrate.md)).

**Flavor first (every RN migration).** `stream-chat-react-native` (bare RN CLI) and
`stream-chat-expo` (Expo) are thin wrappers over the **same** `stream-chat-react-native-core`. The
component/hook API is identical; only the package name, native media/file services, and
install/linking differ. Detect the flavor in section 0 and import from the matching package
everywhere.

Three golden rules, learned from real migration runs:

1. **Change as little application code as possible - and migrate in place.** Preserve component
   boundaries, navigation, and public prop/hook signatures; **edit the existing files (Sendbird out,
   Stream in) - do not create parallel new files and delete the originals.** Swap what's *inside*
   the SDK touchpoints, not the touchpoints. New files are justified only for genuinely new needs
   (e.g. a token endpoint that never existed); a file whose entire content was Sendbird machinery
   with no remaining purpose (a `createTheme`/`colorSet` module, a `platformServices` factory) is
   deleted, not kept as a husk or reborn as a renamed twin.
2. **Almost nothing is codemod-safe.** In a full audit of these two SDKs, **exactly one** of 126
   mapped symbol pairs survived a mechanical 1:1 rename (`disconnect()` -> `disconnectUser()`) -
   virtually every touchpoint is a shape-shift or a behavioral difference. Plan file-by-file agent
   work from the mapping tables; never a global find-and-replace pass.
3. **Prefer idiomatic Stream over a mechanical port.** Where the Sendbird app hand-rolled machinery
   the Stream SDK owns first-class (typing timers, `MessageCollection` handlers, reconnect state
   machines, per-keystroke typing, cursor bookkeeping, send-state callbacks), **delete the
   machinery** and use the reactive primitive - mount `<Channel>`/`<MessageList>`/`<ChannelList>`
   and read context hooks. The idiomatic rewrite is smaller and less buggy than the faithful port -
   and it still happens **inside the existing file/component boundary** (golden rule 1).

**The compiler is the oracle.** Every `after` pattern in the mapping files is typechecked against
the installed Stream RN SDK. If a rewrite doesn't `tsc --noEmit`, the compiler is right and the row
is stale - fix against the real types, never emit an unverified symbol
([`references/sendbird-mapping.md`](references/sendbird-mapping.md) > Trust model).

**Provenance.** The mapping corpus was extracted from Sendbird `@sendbird/chat@4.22.7`,
`@sendbird/uikit-react-native@3.12.7` (`-foundation@3.12.7`) vs Stream `stream-chat@9.50.2`,
`stream-chat-react-native@9.7.0` / `stream-chat-expo@9.7.0`, covering the **used** surface across
four real sample apps (126 symbols; 28 hard gaps, 29 behavioral diffs). Anything outside that set is
`unmapped-known` - resolve it per section 0's tiers, never guess.

---

## 0. Detect & inventory (before any edit)

Map the footprint first - no code changes until this section is done.

### 0a. Detect the flavor

```bash
cat package.json app.json app.config.js app.config.ts 2>/dev/null
```

- an `expo` dependency, or an `app.json` / `app.config.*` with an `expo` key -> **Expo** -> target
  `stream-chat-expo`.
- otherwise -> **bare RN CLI** -> target `stream-chat-react-native`.

Also note the **package manager** (lockfile), the **New Architecture** status, and the
**navigation** style (React Navigation vs Expo Router; Expo Router SDK 56+ forbids
`@react-navigation/*` - [`RULES.md`](RULES.md) > Expo Router SDK 56+). Run the **Project signals**
probe in [`SKILL.md`](SKILL.md) for all of this at once.

### 0b. Inventory the Sendbird footprint

```bash
grep -rln "@sendbird/chat\|@sendbird/uikit-react-native" --include=*.{ts,tsx,js,jsx} .
grep -rn "SendbirdUIKitContainer\|createGroupChannel.*Fragment\|useSendbirdChat\|useConnection\|createMessageCollection\|GroupChannelHandler" --include=*.{ts,tsx} .
cat package.json   # note ALL THREE Sendbird packages (chat, uikit-react-native, -foundation)
```

**Classify each touchpoint** and migrate it per its pattern later:

| Pattern found | How it migrates |
|---|---|
| **UIKit fragment drop-in** (`SendbirdUIKitContainer`, `createGroupChannelFragment`, `createGroupChannelListFragment`, `renderMessage`/`renderX` props) | Architectural remap, not a rename - compose Stream RN primitives ([`references/sendbird-mapping.md`](references/sendbird-mapping.md) sections 12-13). |
| **Custom hook wrapping the SDK** (returns `{ state, actions }`, e.g. a `useConversation`) | Keep the hook's public return shape; replace the body with Stream calls + context hooks. Callers don't change. |
| **`MessageCollection` store** (init policy + `setMessageCollectionHandler`) | Delete the collection lifecycle; mount `<Channel>` + read `channel.state.messages` / context hooks (golden rule 3). |
| **Context + reducer store** (SDK handler callbacks re-dispatch) | Keep the store shape; effects do the async Stream work and re-dispatch. The reducer stays pure. |
| **Direct / inline SDK calls** | Swap in place; keep surrounding layout/navigation. |
| **Spaghetti** | Migrate file-by-file; introduce a thin boundary only where it cuts churn. |

**Classify every `@sendbird/*` symbol into three tiers** (the anti-hallucination discipline -
nothing is invisible):

- **`mapped`** - has a row in [`references/sendbird-mapping.md`](references/sendbird-mapping.md):
  apply it (agent-guided rewrite, or a `manual` gap -> `TODO(migration)`).
- **`unmapped-known`** - a real Sendbird API with **no prebuilt row** (no sampled app used it).
  **Do not skip it.** Resolve it: find the concept in
  [`references/sendbird-mapping-extended.md`](references/sendbird-mapping-extended.md) (domain-level
  direction), pick the Stream symbol, confirm it exists in the installed Stream RN types, and verify
  with `tsc`. Never emit an unverified symbol.
- **`unknown`** - imported from `@sendbird` but not in the indexed SDK surface. Likely a version
  difference; check against the Sendbird version the target actually has installed.

**Build the parity ledger.** List every user-facing chat feature the app has - from the code, the
README, and the UIKit fragment/container config props (voice messages, mentions, reactions,
reply/threads via `ReplyType`, typing, read receipts, ...). One row per feature:

| Feature | Sendbird source | Plan (port / idiomatic rewrite / GAP) | Spec rows | Status |
|---|---|---|---|---|

The **Spec rows** column is filled by the visual-baseline capture below: every feature with a
visual surface names its [`references/design-matching.md`](references/design-matching.md) Step 1
region(s) and the captured state(s) that show it (`-` for features with no visual surface). It is
the bridge verify gate 5 checks - a visual feature cannot close as Ported while its look was never
specced or never judged.

This ledger is the migration's backbone: every row must end as **Ported**, **Rewritten**,
**`N/A - <real reason>`**, or **`GAP - <decision>`** - the user's decision where one was obtainable,
else a `provisional` default per section 2. "Deferred" and "later" are not valid statuses. Silent
feature drops in real migrations happened exactly where no ledger existed - UIKit fragment features
vanished and the README kept advertising them.

### 0c. Capture the visual baseline (while the original still runs)

The migrated app must look like the original, so record what "the original" looks like before you
delete it. Unlike web, an RN app has **no DOM to probe** - the reference is captured as **simulator
screenshots** (Pixel tier), not measured computed styles. A migration briefly holds the best
reference an RN design match can have: **the original app, buildable and drivable in the simulator**.
That window closes the moment section 5 starts; spend real effort on the highest rung you can reach.

1. **The original runs (highest rung): capture it in the simulator now.** Build and boot the
   original Sendbird app on the iOS simulator per
   [`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md), and screenshot
   every parity-ledger row with a visual surface into a reference folder (e.g.
   `sendbird-reference/`). **Drive the states, don't capture only rest:** an incoming *and* outgoing
   bubble, a same-author run (grouping + avatar rule), an attachment/photo album, a message with
   reactions, a reply/thread open, a long multi-line message, typing, read receipts, the composer
   at-rest *and* typing (send/mic swap), the attachment picker open, and both light/dark if the app
   themes. If the dev data is empty, populate it through the original's own UI first (Sendbird's
   client flows still work at this point). These screenshots become the **Pixel-tier reference** for
   [`references/design-matching.md`](references/design-matching.md) Step 1. Fill the ledger's
   Spec-rows column from them.
2. **User-provided screenshots** of the running app - ask if any exist; treat as the reference
   (Pixel tier) when the original can't be built.
3. **Code-derived spec** (always available): extract the palette and type from the Sendbird theme -
   `createTheme` / `colorSet` / `LightUIKitTheme` / `DarkUIKitTheme` /`Palette` in
   `@sendbird/uikit-react-native-foundation` - plus the strings, into a written spec. Say explicitly,
   in the plan and the final report, that this rung **cannot certify** composer / bubble / reaction
   fidelity - only structure and exact colors.

Whichever rung produced it, this baseline is the **reference design** for step 6. It is run
scaffolding (never committed).

---

## 1. Kill list - the traps that bit real migrations

Verified behavioral differences that produce silent runtime bugs, not build errors. Check every one
against the app; the full catalog with workarounds is in
[`references/sendbird-mapping.md`](references/sendbird-mapping.md) > Kill list and the gaps table.

| # | Trap | Consequence if ported 1:1 |
|---|---|---|
| 1 | **Only the UI-context send produces an optimistic message.** `channel.sendMessage()` on the client inserts **no** pending/optimistic message; only `MessageComposer` / `useMessageInputContext().sendMessage()` does | A port that calls `channel.sendMessage` from a custom composer loses optimistic UI (message appears only after the server acks). Send through the UI path, or override `<Channel doSendMessageRequest>` to keep optimistic state. |
| 2 | **One stable message id, no `reqId` reconciliation.** Sendbird tracks pending sends by `reqId` (messageId `0` until acked); Stream keeps one id across the lifecycle | A port that swaps ids on success double-keys the list / breaks retry. Delete `reqId` bookkeeping; use the one id for keys, retry, edit, delete. |
| 3 | **`StreamChat.getInstance(apiKey)` is a process-wide, first-call-wins singleton** - NOT keyed by apiKey | A second `getInstance` with a different key silently returns the first client. Use `useCreateChatClient` ([`RULES.md`](RULES.md) > Client lifetime and providers); use `new StreamChat(apiKey)` only if multiple keys must coexist. |
| 4 | **A token is always required.** Sendbird's `connect(userId)` with no token has no Stream equivalent | The userId-only auto-create path is gone. Dev: `client.devToken(id)` **only while dev tokens are enabled** on the app; prod: a `tokenProvider`. See section 4. |
| 5 | **`muteUser` is a personal, caller-scoped mute**, not Sendbird's operator silencing | "Muted" users keep posting for everyone. Operator mute -> timed `channel.banUser(id, { timeout, reason })`. Reserve `client.muteUser` for an "I don't want to hear from X" feature. |
| 6 | **Ban duration units differ.** Sendbird durations are seconds/ms; Stream `timeout` is **minutes** | A 1:1 duration port makes bans wildly wrong. Convert (`timeout = Math.round(sendbirdDurationMs / 60000)`); confirm the source unit against the installed Sendbird API. |
| 7 | **Blocking is DM-only in Stream**, global in Sendbird | `client.blockUser` stops direct messages only; blocked users still post in shared group channels. Filter client-side or ban/moderate for group hiding. |
| 8 | **Delete soft-deletes by default**; Sendbird deletes are permanent | `client.deleteMessage(id)` leaves a `type: 'deleted'` tombstone. Pass `hardDelete` where the app promised purging. |
| 9 | **Events arrive only for watched channels** | Handlers ported as global listeners miss events for channels nobody watched. `watch()` the channel; `client.on`/`channel.on` return `{ unsubscribe }` - call it in effect cleanup. |
| 10 | **`OpenChannel` -> `livestream` type, and `read_events` is off there.** enter/exit -> `watch()` / `stopWatching()` | Unread counts silently stop working on migrated open channels. Enable client-side unread: `new StreamChat(apiKey, { isLocalUnreadCountEnabled: true })` + `channel.markReadLocally()` / `channel.countUnread()`. The `livestream` type must be configured server-side first. |
| 11 | **No offline cache by default** - Sendbird UIKit enables one via `localCacheEnabled` | State no longer survives reload unless you opt in: `enableOfflineSupport` on `<Chat>` + `@op-engineering/op-sqlite` (native; Expo needs a dev client). Reset on sign-out: `await client.offlineDb.resetDB()` **before** `disconnectUser()` (else cross-user leak). |
| 12 | **Every stateful `.next()` / `.load()` query cursor dies** (channel-list, message history, users, search, members, threads) | Each becomes a stateless call: `queryChannels` offset/limit, `channel.query({ messages: { id_lt, limit } })` id-cursor. Per-query recipes in [`references/sendbird-mapping.md`](references/sendbird-mapping.md) section 7. |
| 13 | **Distinct/DM channels are created by omitting the id**, not a flag | Porting `isDistinct: true` as a data field breaks dedup. `client.channel('messaging', { members })` with **no id** dedups by member set; passing an id disables it. |
| 14 | **Read receipts are a dashboard toggle + auto-marked.** Per-member read state lives on `channel.state.read`, not `getReadStatus()` | `markRead()` is a no-op unless "Read Events" is enabled on the channel type; `<Channel>` marks read automatically. Delete manual `markAsRead` timers and per-member read queries. |
| 15 | **Reconnection is automatic.** Sendbird's `ConnectionHandler` / manual `reconnect()` has no equivalent | Delete the reconnect state machine. Read `isOnline` / `connectionRecovering` from `useChatContext` (or `useIsOnline`); pass a `tokenProvider` so re-auth is silent. |

---

## 2. Plan & checkpoint - involve the user before the first edit

Assemble the migration plan from section 0's outputs. It is **not a new document** - it is the
parity ledger plus four strategy lines:

| Plan field | Source | Example |
|---|---|---|
| Flavor + integration shape(s) | section 0 classification | "Expo (`stream-chat-expo`); UIKit fragments + a `MessageCollection` hook" |
| Credentials & token path | section 4's precedence, resolved on paper | "user-provided key; backend token endpoint re-pointed to mint Stream JWTs" |
| Design bar + baseline rung | section 0c baseline rung | "pixel (simulator capture of the original)", "pixel (user screenshots)", or "structural + exact palette (code-derived)" |
| Gaps + proposed resolutions | ledger GAP rows + [`references/sendbird-mapping.md`](references/sendbird-mapping.md) section 15 | "FeedChannel -> admin-post-only channel (substitute); scheduled messages -> server-side job" |

For the gaps row: collect every feature with **no Stream equivalent** (`FeedChannel` /
notifications, scheduled messages, `ReportCategory` enum, channel-level report, offline cache
tuning, recurring DND quiet hours, per-file thumbnail sizes, CSAT/feedback, AI-agent/Desk
conversations, ...) - each needs a decision: **substitute** (the mapping table names the closest
one), **rebuild app-side**, or **drop**.

**Checkpoint - pause and present the plan to the user when any of these holds:**

- the ledger has **>= 1 GAP row** (a product decision exists - it is the user's, not yours);
- the **credentials/token path is unresolved** (no key provided or found, or no way for clients to
  obtain tokens);
- the **design bar is ambiguous** (pixel fidelity implied, but no baseline screenshots exist and the
  user hasn't said how close is close enough);
- the **user asked** to review the plan first.

Ask everything in **one batched round** - gap decisions, the credentials call, the design bar -
never a drip of single questions. When no trigger holds, don't interrupt: proceed, and include the
plan in the final summary.

**Non-interactive runs** (no user available, or "don't check in, use defaults"): do not stall. Take
the mapping table's named substitute as the default for each gap, mark those ledger rows
**`GAP - provisional: <default>`**, and surface every provisional decision prominently in the final
report - a provisional decision the report doesn't call out is a silent feature drop with extra
steps.

The plan lives **in the ledger**, not beside it: a mid-migration deviation is a ledger edit (gate 6
closes the ledger, so deviations surface at verification), never a silent change of course. A gap
discovered mid-migration is a checkpoint-grade decision the moment it appears - decide it (or mark it
provisional) then; parking it as a TODO is what this section exists to prevent.

---

## 3. Packages

**Install Stream alongside Sendbird first; remove Sendbird last.** Ripping the Sendbird packages out
now leaves the app unbuildable until every touchpoint is migrated - which makes the section 4
connection gate impossible to run. Order:

1. Add Stream with the project's existing package manager, per the **flavor** (section 0a) and
   [`RULES.md`](RULES.md) > Runtime lane ownership. Confirm current dist-tags first
   ([`RULES.md`](RULES.md) > Package version and docs discipline). `stream-chat` and the Stream RN
   UI package version **independently** - never apply one shared version string.
   - **Bare RN CLI:** `stream-chat` + `stream-chat-react-native`, then the required peers
     (`react-native-gesture-handler`, `react-native-reanimated`, `react-native-teleport`,
     `react-native-svg`, `@react-native-community/netinfo`; `react-native-worklets` for Reanimated
     4+), then `cd ios && pod install`.
   - **Expo:** `stream-chat` + `stream-chat-expo` (via `npx expo install`), the Expo peers
     (`expo-image-manipulator`, `expo-dev-client`, ...), and a dev client (Expo Go is not supported).
   Full peer matrix + native setup: [`RULES.md`](RULES.md) > Required peer setup and
   [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md).
2. Wire the mandatory RN chrome the Sendbird container used to own for you: the Reanimated/Worklets
   Babel plugin **last** in `babel.config.js`, `GestureHandlerRootView` at the app entry, and
   `<OverlayProvider>` above navigation (it uses `react-native-teleport` for portal-hosted overlays -
   long-press menu, attachment picker, image gallery). Skipping these is the RN analog of forgetting
   the stylesheet on web: broken overlays or a crash, not a clean error.
3. Only after section 5 completes: uninstall `@sendbird/chat`, `@sendbird/uikit-react-native`, and
   `@sendbird/uikit-react-native-foundation`, drop the Sendbird platform-service factories, and grep
   to confirm zero `@sendbird` imports remain.

---

## 4. Credentials & connection proof (gate: a real user connects)

The biggest conceptual shift: Sendbird connects with just a `userId` (auto-creating users
server-side, token optional); **Stream always requires a signed token** - there is no userId-only
path (kill-list #4). Handle secrets per [`RULES.md`](RULES.md) > Secrets and auth and
[`credentials.md`](credentials.md) - never put the API secret on device.

Wire it, then **prove the connection end-to-end before migrating any UI** - a real trial run shipped
a fully migrated app that had never once connected:

1. Get the Stream API key and replace the Sendbird `appId`. Precedence: **(a)** credentials the user
   provided (in the request or the project's env/config) - use as-is; **(b)** only if none exist,
   run the [`credentials.md`](credentials.md) flow (`getstream` CLI). Never invent a key.
2. Map the token path: `SendbirdChat.setSessionHandler` + `onSessionTokenRequired(resolve, reject)`
   -> an async `tokenProvider` (`() => Promise<string>`) passed as `tokenOrProvider`. `resolve(token)`
   -> `return token`; `reject(err)` -> `throw err`. Stream re-invokes it automatically on expiry -
   **do not** try to imperatively push a new token in
   ([`references/sendbird-mapping.md`](references/sendbird-mapping.md) section 1). Production needs a
   backend token endpoint; an existing Sendbird token endpoint gets re-pointed to mint Stream JWTs.
   **The backend must derive the user id from its own authenticated session, never from a
   client-supplied parameter** ([`RULES.md`](RULES.md) > Secrets and auth).
3. For local/dev parity with Sendbird's tokenless connect, `client.devToken(userId)` works **only
   while dev tokens are enabled** on the Stream app - otherwise it is rejected server-side. Gate any
   pasted-credential/dev-token path behind `__DEV__` or a feature flag so it cannot ship. Never use
   `devToken()` for production.
4. Connect as a real user and confirm the WebSocket is healthy before proceeding. The Sendbird tree
   is still intact (section 3), so mount the proof in a small dev-only screen rather than the main
   flow - it exists to fail fast on auth, not to migrate UI. It is scaffolding, not migration:
   delete it once section 5 wires the real flow (in-place rule, golden rule 1).

```tsx
// <SendbirdUIKitContainer appId userId nickname accessToken> connected internally.
// Stream splits it: build + connect the client with the hook, then providers just distribute it.
const client = useCreateChatClient({
  apiKey,                                  // was Sendbird appId
  tokenOrProvider,                         // string token, or async () => Promise<string>
  userData: { id: userId, name: nickname },// nickname -> name, profileUrl -> image
});
if (!client) return null;                  // hook returns null while connecting
return (
  <OverlayProvider>
    <Chat client={client}>{/* ChannelList / Channel composition */}</Chat>
  </OverlayProvider>
);
```

---

## 5. Migrate the touchpoints

Work file-by-file, **in place** (golden rule 1), per the section 0 classification, pulling exact
symbol mappings from [`references/sendbird-mapping.md`](references/sendbird-mapping.md) - the domain
guide. Import UI symbols from the flavor package (`stream-chat-react-native` **or**
`stream-chat-expo`); the symbol names are identical.

- **UI composition** (sections 12-13): `SendbirdUIKitContainer` -> `useCreateChatClient` +
  `<OverlayProvider><Chat>`; `createGroupChannelFragment` -> `<Channel channel={c}><MessageList/>
  <MessageComposer/></Channel>`; threads -> `<Channel channel={c} thread={t}><Thread/></Channel>`
  (**there is no `<Window>` in RN** - that is a web-only component); `createGroupChannelListFragment`
  -> `<ChannelList filters sort options onSelect />`, row overrides via the `Preview` prop;
  `renderMessage` / `renderX` -> component-swap props / `WithComponents overrides`. **The channel
  header is app-owned in RN** - there is no `ChannelHeader` slot inside `<Channel>`; the nav header
  is your React Navigation / Expo Router header (drive its title from channel state, never a
  literal). Writing your own component for a prebuilt region is gated by the completion contract in
  [`references/design-matching.md`](references/design-matching.md) Step 2.5 (RN's sub-feature
  inheritance rule - the analog of web's custom-ui contract): fill it, don't silently drop
  reactions/receipts/grouping/attachments. **On a Pixel baseline, any touchpoint that rebuilds a
  visual region (composer, message row, channel preview) also carries its Step 1 region spec: build
  to the original's captured look in this pass** - migrating to SDK defaults and deferring the look
  to a step-6 reskin is a second, avoidable rebuild. **Keep `<ChannelList>` as the query, watch, and
  real-time owner** - don't maintain a parallel `client.queryChannels()` result and re-fetch it on
  events.
- **Channels** (sections 2, 7): three Sendbird classes -> one `Channel` + type string;
  `OpenChannel` -> `livestream` type (kill-list #10); distinct channels -> member-set channels with
  no id (kill-list #13); every query cursor -> a stateless call.
- **Messages & attachments** (sections 3, 4): the message-class hierarchy
  (`UserMessage`/`FileMessage`/`MultipleFilesMessage`/`AdminMessage`) -> one `MessageResponse` shape
  discriminated by `message.type` + `message.attachments[]`; `MessageRequestHandler`
  `.onPending/.onSucceeded/.onFailed` -> optimistic send via the UI path + `message.status`
  (kill-list #1); atomic `sendFileMessage` -> upload (`channel.sendImage`/`sendFile`) then
  `channel.sendMessage({ attachments })`, or let `MessageComposer`'s `AttachmentManager` own the
  pipeline.
- **Events & real-time** (sections 5, 6): keyed handler objects
  (`add/removeGroupChannelHandler(key, h)`) -> per-event `client.on()`/`channel.on()` with retained
  `unsubscribe` in effect cleanup; `MessageCollection` + `setMessageCollectionHandler` -> `watch()` +
  reactive `channel.state` + events (golden rule 3 - delete the collection lifecycle);
  typing/presence/read per section 6 (delete the hand-rolled timers, polls, and manual `markAsRead`).

```tsx
useEffect(() => {
  // new GroupChannelHandler({ onMessageReceived }) + addGroupChannelHandler(key, h)
  const { unsubscribe } = channel.on('message.new', (event) => {
    // UI components (MessageList) already re-render from this event -
    // only subscribe by hand for side-effects the components don't own (badges, analytics, nav).
  });
  return () => unsubscribe();                     // removeGroupChannelHandler(key)
}, [channel]);
```

- **Membership & moderation** (section 8): operators -> moderators/roles + capability checks
  (`useChannelOwnCapabilities`, not a `myRole` string); mute/ban/block/report semantics per the kill
  list. End-user actions only - never build a moderation review UI ([`RULES.md`](RULES.md) - Chat,
  Video, Feeds only; no Moderation review UI).
- **Offline & sync** (section 6 / offline domain): opt in with `enableOfflineSupport` +
  `@op-engineering/op-sqlite` if the app relied on Sendbird's cache; delete `onHugeGapDetected` /
  changelog rebuild (recovery is automatic); reset the DB on sign-out (kill-list #11).

When every touchpoint is migrated, finish section 3 step 3: remove the three Sendbird packages and
confirm zero `@sendbird` imports remain.

Seeding note: Sendbird apps often self-seed demo data by connecting as several users in turn. Stream
clients act only as themselves - cross-user seeding is server-side (CLI/backend) and gated by
[`RULES.md`](RULES.md) / [`credentials.md`](credentials.md). Keep only a thin "ensure my own
channels exist" client step if the original had one.

---

## 6. Design parity - the app must look the same

Design fidelity is a deliverable, not a nicety. Sendbird's theming levers all die; their Stream RN
replacements are a **JS theme object, not CSS** (there is no DOM / stylesheet on native):

- **Palette & dimensions:** re-author `colorSet` / `createTheme` / `LightUIKitTheme` /
  `DarkUIKitTheme` / `Palette` (from `@sendbird/uikit-react-native-foundation`) as a
  `DeepPartial<Theme>` object passed to **both** `<OverlayProvider value={{ style }}>` **and**
  `<Chat style={…}>`, read via `useTheme()`. In RN the theme object carries **both color and
  spacing/dimension**, so most reskins are theme-only. Confirm exact theme keys against the installed
  package and the manifest-selected Theming page ([`references/DOCS.md`](references/DOCS.md)) - do not
  hard-code key names from memory. See the Theming Blueprint in
  [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md).
- **Light/dark:** there is no `theme="light"|"dark"` prop - build two theme objects and select on
  `useColorScheme()` (from `react-native`); pin brand/content colors, keep chrome surfaces adaptive
  ([`references/design-matching.md`](references/design-matching.md) > light/dark).
- **Strings & i18n:** `createBaseStringSet` / `StringSet` overrides -> a `Streami18n` instance
  (`registerTranslation` / `setLanguage`) passed to `<Chat i18nInstance={…}>`
  ([`references/sendbird-mapping.md`](references/sendbird-mapping.md) section 14). Stream's keys are
  the English source strings themselves - re-key, don't map 1:1.

Then hand the visual work to [`references/design-matching.md`](references/design-matching.md) with
the **section 0c baseline as the reference design**. Because RN verification is simulator-based (no
DOM to probe), enter its pipeline at **Step 1 (Decompose the reference into regions)** with the
captured screenshots as the reference, regardless of rung:

- **Rung 1/2 (simulator capture / user screenshots):** Pixel tier - run the full pipeline
  (Decompose -> three axes -> Step 1.5 native packages -> Step 2.5 completion contract -> Step 3
  verify). Sample colors and measure sizes off the reference screenshots.
- **Rung 3 (code-derived):** structural match **with one override** - the `colorSet` / theme values
  were read from code, not sampled from a sketch, so include them as exact palette rows despite the
  no-sampling rule for structural tier.

Its Step 3 owns the capture-and-compare loop - including screenshotting the **migrated** app on the
simulator and comparing region-by-region against the reference crops (the `magick` crop+stack
recipe). Do not declare the design matched from code review; neither real trial run captured a single
screenshot, and both shipped unverified skins.

---

## 7. Verify - gates, in order

Run all of these; each catches a failure a real migration shipped. The compiler is the oracle
(golden rule / trust model).

1. **Types:** `npx tsc --noEmit` - zero errors. A row that doesn't typecheck is stale; fix against
   the installed types.
2. **Bundle + native build:** Metro bundles and the app builds for the flavor
   (Expo: `npx expo run:ios` / bare: `npx react-native run-ios`). There is no `next build`; a green
   `tsc` is not a build.
3. **Sendbird is actually gone:** `grep -rn "@sendbird" --include=*.{ts,tsx,js,jsx} .` returns
   nothing, and the three Sendbird packages are uninstalled. A migration that "passed" while still
   importing `@sendbird` shipped a hybrid that only looked done.
4. **Runtime smoke (simulator/device):** boot the app per
   [`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md), log in as two
   users, and have one create a conversation **before sending its first message**. Assert the other's
   channel rail gains it live with no manual re-fetch. Then send each way. Assert: the message
   appears **optimistically once** for the sender (kill-list #1/#2), arrives live for the receiver,
   unread badges and typing indicators move, and there are no console errors. If you cannot run the
   app, say so and have the user run this check - do not skip it silently.
5. **Design verify loop** (step 6) reaches its
   [`references/design-matching.md`](references/design-matching.md) Step 3 exit - and closes
   **against the ledger**: every ledger row with a filled Spec-rows cell has a PASS verdict citing a
   this-round simulator capture of the migrated app compared to its reference, **driven states
   included** (composer typing state, reactions, thread open, attachment picker). A visual feature
   whose ledger row says Ported but has no verdict row is unverified - treat it as FAIL.
6. **Ledger closure:** every parity-ledger row is Ported / Rewritten / N/A / GAP-with-decision. A
   `GAP - provisional` row (section 2 default) closes the gate only if the final report calls it out
   explicitly as a decision the user still owes.
7. **Docs match reality:** rewrite README/feature lists against what the migrated app actually does,
   including a "Known gaps vs. the Sendbird original" section from the GAP rows.

| Excuse | Reality |
|---|---|
| "tsc and the build pass, we're done" | A green build proved nothing about the connection, the pixels, or whether `@sendbird` is really gone - gates 3-5 exist because each failed in a real run. |
| "The token wiring is obviously right" | A real run shipped without ever connecting; Stream requires a token where Sendbird did not. Gate: section 4. |
| "The theme was ported, it'll look the same" | Both real runs shipped unverified skins. A match is claimed from a simulator capture, not from theme diffs. |
| "I screenshotted the original once - baseline done" | A resting shot holds no composer-typing, reaction, or picker detail - exactly where real runs shipped wrong. Rung 1 is driven states in the simulator (section 0c). |
| "That feature was tiny, nobody will miss it" | Silent drops are how READMEs advertise ghosts. It's a ledger row: N/A or GAP, decided, in writing. |
| "I'll port the MessageCollection faithfully and refactor later" | The mechanical port of hand-rolled machinery IS the bug (lost optimistic sends, stale state, dead handlers). Golden rule 3. |
| "The gaps were minor, I decided them myself and kept going" | Minor is the user's judgment, not yours. >= 1 GAP row = the section 2 checkpoint - or, non-interactive, a `provisional` default reported loudly. |

---

## 8. Offer the data migration (never auto-run it)

Everything above migrates the **code**. The app now points at an **empty** Stream app - no users,
channels, or history moved. Once gates 1-7 pass, ask:

> The SDK migration is done and verified. Do you also want to migrate your Sendbird **data** (users,
> channels, message history, reactions) into Stream? There are three approaches: **A** hard switch
> (simplest, needs a maintenance window), **B** uni-directional sync (zero downtime, the most common
> choice), or **C** bi-directional sync (zero downtime, no forced app update, Enterprise).

Data migration is server-side and SDK-independent, so it lives in the shared runbook:
[`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md). If the user says yes,
read that file and follow it. If they only wanted the SDK swap, stop here - it touches production
data and may incur attachment-transfer cost.
