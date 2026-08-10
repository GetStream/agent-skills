# Sendbird -> Stream Chat React Native migration (Track S)

This file owns the **procedure**. The cross-SDK knowledge is split in two, and the split is a loading
rule:

- **[`references/sendbird-symbols.tsv`](references/sendbird-symbols.tsv)** — 361 symbol rows
  (`sendbird` · `stream` · `automation` · `tier` · `section` · `note`). **A lookup table, not reading
  material: `grep` it, never `Read` it** (~23k tokens to answer what a `grep` answers in a few
  hundred). Section 0 produces the app's Sendbird symbol inventory — resolve the whole thing in one
  shot:
  ```bash
  grep -F -f app-sendbird-symbols.txt references/sendbird-symbols.tsv
  grep -F 'createGroupChannelFragment' references/sendbird-symbols.tsv   # one symbol
  ```
  `tier=curated` rows are `tsc`-verified; `tier=inferred` rows are existence-checked hypotheses from
  the 806-symbol long tail. A `note` of `-> sendbird-notes.md#anchor` means the trap was too long for
  one line.
- **[`references/sendbird-notes.md`](references/sendbird-notes.md)** — the prose behind the rows: trust
  model, behavioral diffs, pagination discipline, the own-capabilities hook trap, the feature-gap
  catalog, and the unmapped-symbol resolution protocol. ~6k tokens; read this one.

Where a step touches a Stream RN component's *current* props/hooks, fetch the matching page via
[`references/DOCS.md`](references/DOCS.md) per [`RULES.md`](RULES.md) > Package version and docs
discipline — a future major can rename symbols, as Chat RN v8 -> v9 did ([`migrate.md`](migrate.md)).

**Flavor first (every RN migration).** `stream-chat-react-native` (bare RN CLI) and `stream-chat-expo`
(Expo) are thin wrappers over the **same** `stream-chat-react-native-core`; the component/hook API is
identical and only the package name, native media/file services, and install/linking differ. Detect
the flavor in section 0 and import from the matching package everywhere.

Three golden rules:

1. **Change as little application code as possible — and migrate in place.** Preserve component
   boundaries, navigation, and public prop/hook signatures; **edit the existing files (Sendbird out,
   Stream in) — do not create parallel new files and delete the originals.** Swap what's *inside* the
   SDK touchpoints, not the touchpoints. New files are justified only for genuinely new needs (e.g. a
   token endpoint that never existed); a file whose entire content was Sendbird machinery with no
   remaining purpose (a `createTheme`/`colorSet` module, a `platformServices` factory) is deleted, not
   kept as a husk or reborn as a renamed twin.
2. **Almost nothing is codemod-safe.** **Exactly one** of 126 mapped symbol pairs survived a mechanical
   1:1 rename (`disconnect()` -> `disconnectUser()`) — virtually every touchpoint is a shape-shift or a
   behavioral difference. Plan file-by-file agent work from the mapping tables; never a global
   find-and-replace pass.
3. **Prefer idiomatic Stream over a mechanical port.** Where the Sendbird app hand-rolled machinery the
   Stream SDK owns first-class (typing timers, `MessageCollection` handlers, reconnect state machines,
   per-keystroke typing, cursor bookkeeping, send-state callbacks), **delete the machinery** and use
   the reactive primitive — mount `<Channel>`/`<MessageList>`/`<ChannelList>` and read context hooks.
   The idiomatic rewrite is smaller and less buggy than the faithful port, and it still happens
   **inside the existing file/component boundary** (golden rule 1).

**The compiler is the oracle.** Every `after` pattern in the mapping files is typechecked against the
installed Stream RN SDK. If a rewrite doesn't `tsc --noEmit`, the compiler is right and the row is
stale — fix against the real types, never emit an unverified symbol
([`references/sendbird-notes.md`](references/sendbird-notes.md) > Trust model).

**Provenance.** The mapping corpus was extracted from Sendbird `@sendbird/chat@4.22.7`,
`@sendbird/uikit-react-native@3.12.7` (`-foundation@3.12.7`) vs Stream `stream-chat@9.50.2`,
`stream-chat-react-native@9.7.0` / `stream-chat-expo@9.7.0`, covering the **used** surface across four
real sample apps (126 symbols; 28 hard gaps, 29 behavioral diffs). Anything outside that set is
`unmapped-known` — resolve it per section 0's tiers, never guess.

---

## 0. Detect the integration shape (do this first)

Map the footprint first — no code changes until this section is done.

### 0a. Detect the flavor

```bash
cat package.json app.json app.config.js app.config.ts 2>/dev/null
```

- an `expo` dependency, or an `app.json` / `app.config.*` with an `expo` key -> **Expo** -> target
  `stream-chat-expo`.
- otherwise -> **bare RN CLI** -> target `stream-chat-react-native`.

Also note the **package manager** (lockfile), the **New Architecture** status, and the **navigation**
style (React Navigation vs Expo Router; Expo Router SDK 56+ forbids `@react-navigation/*` —
[`RULES.md`](RULES.md) > Expo Router SDK 56+). The **Project signals** probe in [`SKILL.md`](SKILL.md)
covers all of this at once.

### 0b. Inventory the Sendbird footprint

```bash
grep -rln "@sendbird/chat\|@sendbird/uikit-react-native" --include=*.{ts,tsx,js,jsx} .
grep -rn "SendbirdUIKitContainer\|createGroupChannel.*Fragment\|useSendbirdChat\|useConnection\|createMessageCollection\|GroupChannelHandler" --include=*.{ts,tsx} .
cat package.json   # note ALL THREE Sendbird packages (chat, uikit-react-native, -foundation)
```

**Classify each touchpoint** and migrate it per its pattern later:

| Pattern found | How it migrates |
|---|---|
| **UIKit fragment drop-in** (`SendbirdUIKitContainer`, `createGroupChannelFragment`, `createGroupChannelListFragment`, `renderMessage`/`renderX` props) | Architectural remap, not a rename — compose Stream RN primitives ([`references/sendbird-notes.md`](references/sendbird-notes.md) sections 12-13). |
| **Custom hook wrapping the SDK** (returns `{ state, actions }`, e.g. a `useConversation`) | Keep the hook's public return shape; replace the body with Stream calls + context hooks. Callers don't change. |
| **`MessageCollection` store** (init policy + `setMessageCollectionHandler`) | Delete the collection lifecycle; mount `<Channel>` + read `channel.state.messages` / context hooks (golden rule 3). |
| **Context + reducer store** (SDK handler callbacks re-dispatch) | Keep the store shape; effects do the async Stream work and re-dispatch. The reducer stays pure. |
| **Direct / inline SDK calls** | Swap in place; keep surrounding layout/navigation. |
| **Spaghetti** | Migrate file-by-file; introduce a thin boundary only where it cuts churn. |

**Headless-core branch (`@sendbird/chat` core, no UIKit, 100% custom UI).** When the app is built
directly on the Sendbird **core SDK** with hand-rolled screens and **no
`@sendbird/uikit-react-native`**, the idiomatic target is the **headless `stream-chat` core client**,
keeping the custom components — **not** `stream-chat-react-native` / `stream-chat-expo`. Do **not**
install the Stream RN UI package or its native peers (`react-native-reanimated` /
`-gesture-handler` / `-teleport` / `-svg`, `OverlayProvider`): Stream UI would replace the custom
design and the peers are dead weight. Migrate the SDK layer only: `SendbirdChat.init` ->
`StreamChat.getInstance(apiKey)`; `MessageCollection` + handlers -> `channel.watch()` + read
`channel.state.messages` + `channel.on(...)` -> local `setState`. **Optimistic sends are manual here:**
`channel.sendMessage` on the client is not optimistic (kill-list #1) and there is no `MessageComposer`
to insert the pending copy, so add it yourself with a client-generated id via
`channel.state.addMessageSorted({ id, text, user, status: 'sending', … })` before the send, and let the
echoed `message.new` dedupe by id. Everything else follows the mapping tables; the UIKit-fragment rows
(notes sections 11-12) don't apply.

**Classify every `@sendbird/*` symbol into three tiers** (the anti-hallucination discipline — nothing
is invisible):

- **`mapped`** — `grep` hits a row in
  [`references/sendbird-symbols.tsv`](references/sendbird-symbols.tsv): apply it (agent-guided rewrite,
  or a `manual`/`none` gap -> `TODO(migration)`). `tier=inferred` rows are strong candidates, not
  `tsc`-verified — confirm before shipping.
- **`unmapped-known`** — a real Sendbird API with **no row at all**. **Do not skip it.** Find the
  nearest concept/family among the rows you did hit, pick the Stream symbol, confirm it exists in the
  installed Stream RN types, and verify with `tsc`. Never emit an unverified symbol. Full protocol:
  [`references/sendbird-notes.md`](references/sendbird-notes.md) > Resolving a symbol not in this table.
- **`unknown`** — imported from `@sendbird` but not in the indexed SDK surface. Likely a version
  difference; check against the Sendbird version the target actually has installed.

**Build the parity ledger.** List every user-facing chat feature the app has — from the code, the
README, and the UIKit fragment/container config props (voice messages, mentions, reactions,
reply/threads via `ReplyType`, typing, read receipts, …). One row per feature:

| Feature | Sendbird source | Plan (port / idiomatic rewrite / GAP) | Spec rows | Status |
|---|---|---|---|---|

**Spec rows** is filled by the §1a visual-baseline capture: every feature with a visual surface names
its [`references/design-matching.md`](references/design-matching.md) Step 1 region(s) and the captured
state(s) that show it (`-` for features with no visual surface). It is the bridge verify gate 5
checks — a visual feature cannot close as Ported while its look was never specced or never judged.

Every row must end as **Ported**, **Rewritten**, **`N/A - <real reason>`**, or **`GAP - <decision>`** —
the user's decision where one was obtainable, else a `provisional` default per section 2. "Deferred"
and "later" are not valid statuses. Silent feature drops happened exactly where no ledger existed:
UIKit fragment features vanished and the README kept advertising them.

---

## 1. Design & functional fidelity (read this every time — it's the part that's always wrong)

Getting the app to **build, connect, and deliver messages live** is the easy 80%. The migration is
judged on the **last 20%: does each screen look and behave like the Sendbird original?** — and that is
where **every failing trial run failed**, never on the SDK swap. **Internal coherence is not
fidelity:** a full-screen screenshot of *its own* app that looks like a coherent chat app has been
verified against nothing. Colored-initial avatars where the original shows **gray silhouettes are a
FAIL even though colored looks nicer**, and "more idiomatic" / "more on-brand" / "arguably better than
the original" is a skip dressed up as a choice.

For the channel list and chat screens, **give `design-analysis.md` a `Plan` column: the exact Stream
SDK feature/mechanism each region will use.** The region spec captures *what the original looks like*;
the `Plan` column commits *how you will reproduce it in Stream* before you write any UI — the theme key
(`semantics.chatBgOutgoing`,
`channelPreview.unreadContainer`, …), the `WithComponents` slot (`MessageAuthor`,
`ChannelPreviewAvatar`, `MessageContentBottomView`, `MessageComposerLeadingView`, …), the `<Channel>`
prop (`messageInputFloating`, `audioRecordingEnabled`, …), or a documented hook/config — plus the axis
(theming / layout / functional) and whether it's an SDK default that already matches. Table shape:
`Region | Spec (measured) | Plan (Stream SDK feature) | Axis | Status`. If a Plan reads "custom
component from scratch", re-check whether an SDK slot already covers it. Confirm each named
key/slot/prop against the installed package.

### 1a. The source app IS the benchmark — capture it before you delete it

Unlike web, an RN app has **no DOM to probe** — the reference is **simulator screenshots**, and the one
moment you can re-screenshot and pixel-sample the original is *now, while it still runs*. The
deliverable is not a folder of screenshots but the **design spec**:
[`references/design-matching.md`](references/design-matching.md) **Step 1 (Decompose the reference into
regions)** run against the original, saved to `design-analysis.md`.

1. **Build and boot the original** on the iOS simulator
   ([`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md)) and capture **every
   screen and every state** the match is judged on: the channel list; a chat with **both incoming and
   outgoing** messages; the composer **at rest and typing** (the send/mic swap); any thread; the
   attachment picker open; reactions; and **dark mode** if supported. `simctl` can't tap, so drive
   navigation/composer states from temporary code scaffold (SIMULATOR-VERIFICATION §3–§4 — using the
   *original Sendbird* app's own APIs, not Stream's hooks).
   - **A stuck login screen is usually a slow cold connect (30–60s), not a dead backend** — its console
     may not reach your terminal, so no visible error ≠ failure. Wait 45–60s and re-screenshot before
     concluding auth failed; do **not** probe the backend to "prove" it's down.
   - **Tooling precheck now, before you crop:** the region-diff crops need ImageMagick or PIL; if
     neither is installed, `python3 -m venv .designvenv && .designvenv/bin/pip install Pillow numpy`
     (or install `magick`) up front.
   - **Then run design-matching Step 1 on the shots:** region by region, record the concrete spec —
     bubble radius/shape/max-width/alignment, avatar shape/size, font sizes and **weights**,
     paddings/gaps, and the **sampled** colours (bubble fills, accent, read-receipt ticks, background)
     — measured and pixel-sampled off the screenshots, not eyeballed. Write it to `design-analysis.md`
     and fill the parity ledger's **Spec rows**.
2. **If the original won't build:** use the user's screenshots and run the same Step 1 decomposition on
   them (flag any region no shot covers). **If there are none:** rebuild the original — a
   `git worktree` at the pre-migration Sendbird commit — and boot it; it is the benchmark, worth the
   build. Only if getting *any* pixels of the original is genuinely impossible, read the Sendbird theme
   (`colorSet` / `SBUTheme`) for its palette and **say plainly in the summary that the layout is NOT
   matched** — a palette gives colours, never layout, so that path is a recolor, not a match.

> **This capture path only governs how you learn the *look*. It is orthogonal to the parity-ledger code
> analysis** — reading the Sendbird source for features, behaviours, and API mappings (silent /
> ephemeral flags, custom channel/attachment/message types, push config, roles & permissions, any
> Sendbird-only feature) feeds the ledger, is invisible in a screenshot, and is mandatory regardless.
> Screenshots make the port *look* right; code analysis finds *what must be ported at all*.

> **HARD STOP (ordering):** do **not** install Stream packages or edit any file until
> `design-analysis.md` exists and decomposes every in-scope region with a concrete, **sampled** spec.
> The window where the original is drivable is exactly when the spec is cheapest and most accurate. The
> design analysis is the **contract** the implementation and the §7 verify must satisfy. Keep it until
> the §7 verify loop passes, then remove it (unless the user asked to keep it).

### 1b. Two screens are NON-NEGOTIABLE

Every region on these two ends `Fixed` or genuinely `Impossible`:

1. **The channel list** — row anatomy: avatar shape, title / preview / timestamp placement, unread
   badge treatment.
2. **The channel screen: message list + composer** — bubble shape/tail, incoming vs outgoing
   **background AND text** colour, avatar treatment, timestamp + read-receipt placement, reaction
   placement, and the **composer** (button inventory, the at-rest → typing send/mic swap, attach-button
   shape). A channel-**list** screenshot hides all of it — "the list looks right" is not "the app looks
   right."

**Banned as a resolution on these two screens** — "close enough", "acceptable approximation", "minor",
"difference noted", "keep default", "arguably better", "residual", "cosmetic", "polish", "deferred",
"nice-to-have", **and any other qualifier**. **A single region on either screen that doesn't match —
and isn't genuinely `Impossible` with a reason — is an immediate no-go for the whole migration.**
Surface it, do not ship it.

**Walk this per-region checklist on both screens — each row is a Sendbird→Stream _default_ gap a green
build and a full-screen glance hide.** The "how" for each lives in
[`references/design-matching.md`](references/design-matching.md). These are the **most-missed regions —
a floor, not the full set**; design-matching's decomposition is authoritative and covers everything
else (quoted replies, polls, the attachment/image viewer, typing indicator, the thread screen, …).

*Channel list:*
| Region | The Stream-default gap to catch |
|---|---|
| Row anatomy | avatar / title / preview / timestamp / unread-badge **positions** left at Stream's `ChannelPreview` layout instead of the source's |
| Avatar | Stream's circular avatar + generated fallback shipped where the source shows a different shape/size or a plain placeholder; a **1:1** row must show the **other member's single** avatar, not Stream's member cluster |
| Unread badge | Stream default colour / shape / position instead of the source's (often accent-tinted) |
| Preview + timestamp | wrong truncation, wrong side, or Stream's relative-time format vs the source's |

*Channel screen (message list + composer):*
| Region | The Stream-default gap to catch |
|---|---|
| Outgoing bubble | left as Stream's **pale accent tint** instead of the source's solid fill — and a solid fill needs its **text colour set too**, or the text stays dark / illegible |
| Incoming bubble | not matched to the source's incoming fill + text |
| Bubble geometry | radius / tail / **max-width** left at Stream defaults, so bubbles wrap where the source fits one line; the grouped-run tail corner not matched |
| Metadata placement | timestamp + read receipts left in Stream's **footer below** the bubble when the source puts them **inside / beside** it (structural — `MessageContent` / `MessageFooter`, not a theme key) |
| Avatar treatment | shown on own messages, or shown in a 1:1 where the source hides it, or wrong shape / size |
| Reactions | Stream's default overlay pills + emoji set/order instead of the source's **position** (in-bubble vs overlay), **set**, and **order** — read off the baseline, never assume |
| Composer inventory | Stream's default button set shipped as-is: match 1:1 — the attach/`+` **shape**, the at-rest→typing **send/mic swap**, and **no** control the source lacks (an added button is a fail like a dropped one) |
| Composer chrome | floating vs docked (`messageInputFloating`), pill fill / border / radius, and the bar/wrapper background left at Stream's |
| Header | title / subtitle / avatar / right-side actions not matched to the source header |
| Date separators | Stream's default pill colour / style instead of the source's |
| Empty / loading / error strings | Stream's default English (`Streami18n`) instead of the source's copy |

**Reactions and the composer are where Sendbird and Stream diverge MOST — treat the Stream default as
_wrong_ for these two until a crop proves otherwise; they are structural rebuilds, not recolors.**
Sendbird commonly renders **reactions** as a box/bar **attached to the bubble** (Stream's default floats
pills *above/outside* it — `ReactionListTop`/`ReactionListBottom`), and its **composer** commonly puts
**send/mic OUTSIDE the input pill** with a **bordered/squared `+`** (Stream's default keeps send/mic
**inside** the pill via `OutputButtons` and ships a plain/circular `AttachButton`). Read the exact
arrangement off the baseline and rebuild to it (recipes:
[`references/design-matching.md`](references/design-matching.md) → Composer / reactions rows).

---

## 2. Plan & checkpoint — involve the user before the first edit

### 2a. Kill list — the traps that bit real migrations

Verified behavioral differences that produce silent runtime bugs, not build errors. Check every one
against the app; the full catalog with workarounds is in
[`references/sendbird-notes.md`](references/sendbird-notes.md) > Kill list and the gaps table. **Every
trap the app actually hits is a plan line below** — a ledger row with a decision, never a
mid-migration surprise.

| # | Trap | Consequence if ported 1:1 |
|---|---|---|
| 1 | **Only the UI-context send produces an optimistic message.** `channel.sendMessage()` on the client inserts **no** pending/optimistic message; only `MessageComposer` / `useMessageInputContext().sendMessage()` does | A custom composer calling `channel.sendMessage` loses optimistic UI (message appears only after the server acks). Send through the UI path, or override `<Channel doSendMessageRequest>`. |
| 2 | **One stable message id, no `reqId` reconciliation.** Sendbird tracks pending sends by `reqId` (messageId `0` until acked); Stream keeps one id across the lifecycle | A port that swaps ids on success double-keys the list / breaks retry. Delete `reqId` bookkeeping; use the one id for keys, retry, edit, delete. |
| 3 | **`StreamChat.getInstance(apiKey)` is a process-wide, first-call-wins singleton** — NOT keyed by apiKey | A second `getInstance` with a different key silently returns the first client. Use `useCreateChatClient` ([`RULES.md`](RULES.md) > Client lifetime and providers); use `new StreamChat(apiKey)` only if multiple keys must coexist. |
| 4 | **A token is always required.** Sendbird's `connect(userId)` with no token has no Stream equivalent | The userId-only auto-create path is gone. Dev: `client.devToken(id)` **only while dev tokens are enabled** — a new app has them **off**, and the fixed decision then is a **pre-minted fixed user roster** ([`credentials.md`](credentials.md#dev-tokens-disabled)); prod: a `tokenProvider`. See section 4. |
| 5 | **`muteUser` is a personal, caller-scoped mute**, not Sendbird's operator silencing | "Muted" users keep posting for everyone. Operator mute -> timed `channel.banUser(id, { timeout, reason })`. Reserve `client.muteUser` for an "I don't want to hear from X" feature. |
| 6 | **Ban duration units differ.** Sendbird durations are seconds/ms; Stream `timeout` is **minutes** | A 1:1 duration port makes bans wildly wrong. Convert (`timeout = Math.round(sendbirdDurationMs / 60000)`); confirm the source unit against the installed Sendbird API. |
| 7 | **Blocking is DM-only in Stream**, global in Sendbird | `client.blockUser` stops direct messages only; blocked users still post in shared group channels. Filter client-side or ban/moderate for group hiding. |
| 8 | **Delete soft-deletes by default**; Sendbird deletes are permanent | `client.deleteMessage(id)` leaves a `type: 'deleted'` tombstone. Pass `hardDelete` where the app promised purging. |
| 9 | **Events arrive only for watched channels** | Handlers ported as global listeners miss events for channels nobody watched. `watch()` the channel; `client.on`/`channel.on` return `{ unsubscribe }` — call it in effect cleanup. |
| 10 | **`OpenChannel` -> `livestream` type, and `read_events` is off there.** enter/exit -> `watch()` / `stopWatching()` | Unread counts silently stop working on migrated open channels. Enable client-side unread: `new StreamChat(apiKey, { isLocalUnreadCountEnabled: true })` + `channel.markReadLocally()` / `channel.countUnread()`. The `livestream` type must be configured server-side first. |
| 11 | **No offline cache by default** — Sendbird UIKit enables one via `localCacheEnabled` | State no longer survives reload unless you opt in: `enableOfflineSupport` on `<Chat>` + `@op-engineering/op-sqlite` (native; Expo needs a dev client). Reset on sign-out: `await client.offlineDb.resetDB()` **before** `disconnectUser()` (else cross-user leak). |
| 12 | **Every stateful `.next()` / `.load()` query cursor dies** (channel-list, message history, users, search, members, threads) | Each becomes a stateless call: `queryChannels` offset/limit, `channel.query({ messages: { id_lt, limit } })` id-cursor. Per-query recipes in [`references/sendbird-notes.md`](references/sendbird-notes.md) section 7. |
| 13 | **Distinct/DM channels are created by omitting the id**, not a flag | Porting `isDistinct: true` as a data field breaks dedup. `client.channel('messaging', { members })` with **no id** dedups by member set; passing an id disables it. |
| 14 | **Read receipts are a dashboard toggle + auto-marked.** Per-member read state lives on `channel.state.read`, not `getReadStatus()` | `markRead()` is a no-op unless "Read Events" is enabled on the channel type; `<Channel>` marks read automatically. Delete manual `markAsRead` timers and per-member read queries. |
| 15 | **Reconnection is automatic.** Sendbird's `ConnectionHandler` / manual `reconnect()` has no equivalent | Delete the reconnect state machine. Read `isOnline` / `connectionRecovering` from `useChatContext` (or `useIsOnline`); pass a `tokenProvider` so re-auth is silent. |
| 16 | **SDK mutations echo back as events and update `channel.state` on their own — don't parse-and-cache a mutation's return value in a parallel store.** `translateMessage` / reactions / pins / edits are broadcast back as `message.updated` (etc.) to the channel's watchers, **including the caller**, so the SDK merges the change into `channel.state.messages` and re-renders | A parallel cache duplicates state, drifts from the live message, and couples you to the response's **exact shape — which the SDK's TS type can misdescribe** (e.g. `translateMessage` nests the message under `.message`, so reading top-level `res.i18n` type-checks but is always `undefined` → the UI silently shows nothing). Read the live `message.i18n` / `channel.state` instead. **Do NOT hand-dispatch the event yourself** (`client.dispatchEvent({ type: 'message.updated', … })`) — it already arrives over the socket, so dispatching double-applies. |

### 2b. Assemble the plan, then checkpoint

The plan is **not a new document** — it is the parity ledger plus four strategy lines:

| Plan field | Source | Example |
|---|---|---|
| Flavor + integration shape(s) | section 0 classification | "Expo (`stream-chat-expo`); UIKit fragments + a `MessageCollection` hook" |
| Credentials & token path | section 4's precedence, resolved on paper | "user-provided key; backend token endpoint re-pointed to mint Stream JWTs" |
| How the reference is obtained | §1a baseline capture | "rebuild + capture the original (default)", or "user screenshots". This row is *how* you'll get the reference, never *whether* to match. |
| Gaps + proposed resolutions | ledger GAP rows + [`references/sendbird-notes.md`](references/sendbird-notes.md) section 15 | "FeedChannel -> admin-post-only channel (substitute); scheduled messages -> server-side job" |

For the gaps row: collect every feature with **no Stream equivalent** (`FeedChannel` / notifications,
scheduled messages, `ReportCategory` enum, channel-level report, offline cache tuning, recurring DND
quiet hours, per-file thumbnail sizes, CSAT/feedback, AI-agent/Desk conversations, …) — each needs a
decision: **substitute** (the mapping table names the closest one), **rebuild app-side**, or **drop**.

**Checkpoint — pause and present the plan to the user when any of these holds:**

- the ledger has **>= 1 GAP row** (the product decision is the user's, not yours);
- the **credentials/token path is unresolved** (no key provided or found, or no way for clients to
  obtain tokens);
- the reference is **not obtainable** the default way (the original can't be built and the user has no
  screenshots) — ask **how to get one** (rebuild? can they share screenshots?); do **not** offer lower
  fidelity as a time saving ([`RULES.md`](RULES.md): "never because it's risky or more effort");
- the **user asked** to review the plan first.

Ask everything in **one batched round** — gap decisions, the credentials call, how to obtain the
reference — never a drip of single questions. When no trigger holds, don't interrupt: proceed, and
include the plan in the final summary.

**Non-interactive runs** (no user available, or "don't check in, use defaults"): take the mapping
table's named substitute as the default for each gap, mark those ledger rows
**`GAP - provisional: <default>`**, and surface every provisional decision prominently in the final
report — a provisional decision the report doesn't call out is a silent feature drop with extra steps.

The plan lives **in the ledger**, not beside it: a mid-migration deviation is a ledger edit (gate 6
closes the ledger), never a silent change of course. A gap discovered mid-migration is a
checkpoint-grade decision the moment it appears — decide it (or mark it provisional) then.

---

## 3. Packages

**Install Stream alongside Sendbird first; remove Sendbird last** — ripping the Sendbird packages out
now leaves the app unbuildable until every touchpoint is migrated. Order:

1. Add Stream with the project's existing package manager, per the **flavor** (section 0a) and
   [`RULES.md`](RULES.md) > Runtime lane ownership. Confirm current dist-tags first
   ([`RULES.md`](RULES.md) > Package version and docs discipline). `stream-chat` and the Stream RN UI
   package version **independently** — never apply one shared version string.
   - **Bare RN CLI:** `stream-chat` + `stream-chat-react-native`, then the required peers
     (`react-native-gesture-handler`, `react-native-reanimated`, `react-native-teleport`,
     `react-native-svg`, `@react-native-community/netinfo`; `react-native-worklets` for Reanimated 4+),
     then `cd ios && pod install`.
   - **Expo:** `stream-chat` + `stream-chat-expo` (via `npx expo install`), the Expo peers
     (`expo-image-manipulator`, `expo-dev-client`, …), and a dev client (Expo Go is not supported).

   Full peer matrix + native setup: [`RULES.md`](RULES.md) > Required peer setup and
   [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md). On the React-19 / RN-0.85
   baseline, a third-party peer that hasn't bumped its range may force `--legacy-peer-deps`; a partial
   install failure can leave a nested/inconsistent tree, so reconcile it cleanly rather than layering on
   top. **`react-native-teleport` is the recurring offender** — it peers on `react-dom@*`, pulls a newer
   `react-dom` than Expo's pinned `react`, and fails strict peer resolution. Prefer **pinning `react-dom`
   to the project's exact `react` version** over `--legacy-peer-deps`: both work, but the pin keeps the
   tree consistent instead of suppressing the check.
2. Wire the mandatory RN chrome the Sendbird container used to own for you: the Reanimated/Worklets
   Babel plugin **last** in `babel.config.js` — **RN CLI and Expo <54 only; on Expo SDK 54+ create no
   `babel.config.js`, `babel-preset-expo` appends the plugin itself** ([`builder.md`](builder.md) §5 >
   Babel plugin) — `GestureHandlerRootView` at the app entry, and `<OverlayProvider>` above navigation
   (it uses `react-native-teleport` for portal-hosted overlays: long-press menu, attachment picker,
   image gallery). Skipping these gives broken overlays or a crash, not a clean error.
3. **Kick off the native build NOW — as soon as the Stream packages + peers are installed.** The native
   build (`npx expo prebuild --clean` + `expo run:ios`, or the RN CLI equivalent) is the single most
   expensive step and it is where the **native peers actually get exercised**, so starting it early
   overlaps it with the touchpoint migration (sections 4-5) and surfaces native/peer failures
   immediately.
4. Only after section 5 completes: uninstall `@sendbird/chat`, `@sendbird/uikit-react-native`, and
   `@sendbird/uikit-react-native-foundation`, drop the Sendbird platform-service factories, and grep to
   confirm zero `@sendbird` imports remain.

---

## 4. Credentials

The biggest conceptual shift: Sendbird connects with just a `userId` (auto-creating users server-side,
token optional); **Stream always requires a signed token** (kill-list #4). Handle secrets per
[`RULES.md`](RULES.md) > Secrets and auth and [`credentials.md`](credentials.md) — never put the API
secret on device.

1. Get the Stream API key and replace the Sendbird `appId`. Precedence: **(a)** credentials the user
   provided (in the request or the project's env/config) — use as-is; **(b)** only if none exist, run
   the [`credentials.md`](credentials.md) flow (`getstream` CLI). Never invent a key.
2. Map the token path: `SendbirdChat.setSessionHandler` + `onSessionTokenRequired(resolve, reject)` ->
   an async `tokenProvider` (`() => Promise<string>`) passed as `tokenOrProvider`. `resolve(token)` ->
   `return token`; `reject(err)` -> `throw err`. Stream re-invokes it automatically on expiry — **do
   not** try to imperatively push a new token in
   ([`references/sendbird-notes.md`](references/sendbird-notes.md) section 1). Production needs a
   backend token endpoint; an existing Sendbird token endpoint gets re-pointed to mint Stream JWTs.
   **The backend must derive the user id from its own authenticated session, never from a
   client-supplied parameter** ([`RULES.md`](RULES.md) > Secrets and auth).
3. For local/dev parity with Sendbird's tokenless connect, `client.devToken(userId)` works **only while
   dev tokens are enabled**, and **a freshly created Stream app has them off**. Follow the single
   decision in [`credentials.md` > dev tokens disabled](credentials.md#dev-tokens-disabled): connect as
   one of a fixed set of test users with tokens pre-minted in Step B — don't reproduce Sendbird's
   connect-any-userId behaviour, and don't loosen the app's auth to get it. A free-text "type any name
   and join" login screen therefore becomes a **GAP row the user owns**. Gate any
   pasted-credential/dev-token path behind `__DEV__` or a feature flag so it cannot ship.

---

## 5. Migrate the touchpoints

Work file-by-file, **in place** (golden rule 1), per the section 0 classification, pulling exact symbol
mappings from the `grep` of [`references/sendbird-symbols.tsv`](references/sendbird-symbols.tsv) you ran
in section 0, and the behavioral prose from
[`references/sendbird-notes.md`](references/sendbird-notes.md). Import UI symbols from the flavor
package (`stream-chat-react-native` **or** `stream-chat-expo`); the symbol names are identical.

- **UI composition** (notes sections 11-12): `SendbirdUIKitContainer` -> `useCreateChatClient` +
  `<OverlayProvider><Chat>`; `createGroupChannelFragment` -> `<Channel channel={c}><MessageList/>
  <MessageComposer/></Channel>`; threads -> `<Channel channel={c} thread={t}><Thread/></Channel>`
  (**there is no `<Window>` in RN** — that is web-only); `createGroupChannelListFragment` ->
  `<ChannelList filters sort options onSelect />`, row overrides via the `Preview` prop;
  `renderMessage` / `renderX` -> component-swap props / `WithComponents overrides`. **The channel header
  is app-owned in RN** — there is no `ChannelHeader` slot inside `<Channel>`; the nav header is your
  React Navigation / Expo Router header (drive its title from channel state, never a literal). Writing
  your own component for a prebuilt region carries the sub-feature inheritance contract: fill it, don't
  silently drop reactions/receipts/grouping/attachments. **Any touchpoint that rebuilds a visual region
  (composer, message row, channel preview) also carries its §1a region spec: build to the original's
  captured look in this pass** — migrating to SDK defaults and deferring the look to a step-6 reskin is
  a second, avoidable rebuild. **Keep `<ChannelList>` as the query, watch, and real-time owner** — don't
  maintain a parallel `client.queryChannels()` result and re-fetch it on events.
- **Channels** (notes sections 2, 7): three Sendbird classes -> one `Channel` + type string;
  `OpenChannel` -> `livestream` type (kill-list #10); distinct channels -> member-set channels with no
  id (kill-list #13); every query cursor -> a stateless call.
- **Messages & attachments** (notes sections 3, 4): the message-class hierarchy
  (`UserMessage`/`FileMessage`/`MultipleFilesMessage`/`AdminMessage`) -> one `MessageResponse` shape
  discriminated by `message.type` + `message.attachments[]`; `MessageRequestHandler`
  `.onPending/.onSucceeded/.onFailed` -> optimistic send via the UI path + `message.status` (kill-list
  #1); atomic `sendFileMessage` -> upload (`channel.sendImage`/`sendFile`) then
  `channel.sendMessage({ attachments })`, or let `MessageComposer`'s `AttachmentManager` own the
  pipeline.
- **Events & real-time** (notes sections 5, 6): keyed handler objects
  (`add/removeGroupChannelHandler(key, h)`) -> per-event `client.on()`/`channel.on()` with retained
  `unsubscribe` in effect cleanup; `MessageCollection` + `setMessageCollectionHandler` -> `watch()` +
  reactive `channel.state` + events (golden rule 3); typing/presence/read per notes section 6 (delete
  the hand-rolled timers, polls, and manual `markAsRead`).

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

- **Membership & moderation** (notes section 8): operators -> moderators/roles + capability checks
  (`useChannelOwnCapabilities`, not a `myRole` string); mute/ban/block/report semantics per the kill
  list. End-user actions only — never build a moderation review UI ([`RULES.md`](RULES.md): Chat, Video,
  Feeds only).
- **Offline & sync** (notes section 14): opt in with `enableOfflineSupport` +
  `@op-engineering/op-sqlite` if the app relied on Sendbird's cache; delete `onHugeGapDetected` /
  changelog rebuild (recovery is automatic); reset the DB on sign-out (kill-list #11).

When every touchpoint is migrated, finish section 3 step 4: remove the three Sendbird packages and
confirm zero `@sendbird` imports remain.

**Seeding.** Sendbird apps often self-seed demo data by connecting as several users in turn. Stream
clients act only as themselves — cross-user seeding is server-side (CLI/backend) and gated by
[`RULES.md`](RULES.md) / [`credentials.md`](credentials.md). Keep only a thin "ensure my own channels
exist" client step if the original had one.

**Put at least one message carrying reactions in EVERY channel** — plus, in the channel you'll
design-verify, the rest of the region-triggering set listed in §7 gate 5. The
reactions box can't be matched or verified if no seeded message renders it, so add reactions at seed
time, server-side, as part of creating the data. **Seed reactions only with types in the app's
`supportedReactions`:** the SDK filters unsupported types out of `useMessageContext`'s `reactions`, so a
reaction seeded as an unsupported type (e.g. `question`) silently never renders and the crop looks like
a layout bug. Use the default set (`like`/`love`/`haha`/`wow`/`sad`) or extend `supportedReactions`
(with an `Icon`) first, and seed a reaction on **both** an incoming and an outgoing message.

---

## 6. Design parity — re-apply the look, then match it region-by-region

The framing, the two non-negotiable screens, the per-region checklist, and the baseline all live in
**§1a/§1b** — this section is the *mechanism*. Sendbird's theming levers all die; their Stream RN
replacements are a **JS theme object, not CSS**:

- **Palette & dimensions:** re-author `colorSet` / `createTheme` / `LightUIKitTheme` / `DarkUIKitTheme`
  / `Palette` (from `@sendbird/uikit-react-native-foundation`) as a `DeepPartial<Theme>` object passed
  to **both** `<OverlayProvider value={{ style }}>` **and** `<Chat style={…}>`, read via `useTheme()`.
  In RN the theme object carries **both color and spacing/dimension**, so most reskins are theme-only.
  Confirm exact theme keys against the installed package and the manifest-selected Theming page
  ([`references/DOCS.md`](references/DOCS.md)) — do not hard-code key names from memory. See the Theming
  Blueprint in
  [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md).
- **Light/dark:** there is no `theme="light"|"dark"` prop — build two theme objects and select on
  `useColorScheme()` (from `react-native`); pin brand/content colors, keep chrome surfaces adaptive
  ([`references/design-matching.md`](references/design-matching.md) > light/dark).
- **Strings & i18n:** `createBaseStringSet` / `StringSet` overrides -> a `Streami18n` instance
  (`registerTranslation` / `setLanguage`) passed to `<Chat i18nInstance={…}>`
  ([`references/sendbird-notes.md`](references/sendbird-notes.md) section 13). Stream's keys are the
  English source strings themselves — re-key, don't map 1:1.

**Run the design match as its own first-class task, not a sub-step skimmed under wrap-up pressure.**
**Fan out one focused subagent per _composite screen-area_** — the **message row** (bubble fill+text,
metadata placement, reactions and avatar *together*), the **composer** (the whole bar), the
**channel-list row**, and the **header** — **not** one broad "do the design" subagent, and **not** one
per tiny sub-element (a reactions-only subagent crops the pills in isolation and can't see whether they
sit *inside vs below* the bubble). A composite-area subagent owns every checklist region in its area,
rebuilds them **together**, and crops the **whole composite full-width**, so *positioning* between
sub-elements is verified too.

- **Contract per subagent:** **in** — the area's baseline crop + the exact recipe from
  [`references/design-matching.md`](references/design-matching.md); **out** — the area built to
  pixel-match **plus the baseline↔migrated crop pair it produced**, not a prose "PASS". **The crop pair
  is the evidence, never the subagent's words:** do not relay an area as matched when you have not seen
  its crops.
- **Fan-out is a mechanism, not a mandate to over-delegate.** These subagents *write* code, so two
  editing the same file will corrupt it — give each **disjoint** files/slots, run them sequentially, or
  isolate them (`isolation: 'worktree'`); and don't hand *core implementation* to a subagent to offload
  effort. Matching a screen inline is fine; matching it *from memory at wrap-up* is the failure.

Each subagent gets `design-analysis.md` as the reference design (its Step 1 was already run in §1a) —
reuse it rather than re-decomposing, route each region through the three axes, and run design-matching
Step 3, screenshotting the **migrated** app and comparing region by region against the reference crops.
**The baseline must be independent ground truth — the original's actual pixels.** A `design-analysis.md`
you authored yourself is not a valid baseline: comparing the app against a spec you wrote passes *by
construction*. If you only had the theme (no original pixels), you can certify *"recolored"*, never
*"looks like the original"*.

---

## 7. Verify — gates, in order

Run all of these; each catches a failure a real migration shipped. The compiler is the oracle.

**Gate 0 — the 30-second floor; do this FIRST, before the region tables and before any styling.** Take
**one channel-list shot + one channel-screen shot**. On the channel screen, confirm **all four are in
frame: the header, an incoming bubble, an outgoing bubble, and the composer.** Any one missing = a
**broken screen — stop and fix it**; do **not** let the regions that *are* visible stand in for the
screen. The composer especially: a custom header rendered as a **sibling above** `<Channel>` can push
the composer **entirely off-screen** — render the header **inside** `<Channel>` with
`keyboardVerticalOffset={0} topInset={0}`. **Presence before appearance**, and *attempted* before
*present*: a channel screen whose message-list bubbles you never tried to match is not "done" because
the channel list looked right.

**Run every gate command from an absolute `cd`, and NEVER pipe one** — a pipe reports the pipe's exit
status and a stray `npx` resolves an unrelated package, both of which read as a pass
([`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md) §7). Shape:
`cd <abs-project-path> && <cmd> > /tmp/gate.log 2>&1; echo "EXIT=$?"; tail -20 /tmp/gate.log`.

1. **Types:** `tsc --noEmit` — zero errors (`npx tsc --noEmit`, or `yarn tsc --noEmit` /
   `pnpm exec tsc --noEmit`, from the project root per the rule above). A row that doesn't typecheck is
   stale; fix against the installed types.
2. **Bundle + native build:** Metro bundles and the app builds for the flavor (Expo:
   `npx expo run:ios` / bare: `npx react-native run-ios`). There is no `next build`; a green `tsc` is
   not a build. On Expo, `run:ios` exits **non-zero on an osascript permission error after "Build
   Succeeded"** — read the log, not just the exit code.
3. **Sendbird is actually gone:** `grep -rn "@sendbird" --include=*.{ts,tsx,js,jsx} .` returns nothing,
   and the three Sendbird packages are uninstalled. A migration that "passed" while still importing
   `@sendbird` shipped a hybrid that only looked done.
4. **Runtime smoke (simulator/device) — connectivity AND interaction.** Boot the app per
   [`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md), log in as two users,
   and have one create a conversation **before sending its first message**. Assert the other's channel
   rail gains it live with no manual re-fetch. Then send each way and assert: the message appears
   **optimistically once** for the sender (kill-list #1/#2), arrives live for the receiver, unread
   badges and typing indicators move, and there are no console errors. If you cannot run the app, say
   so and have the user run this check — do not skip it silently.
   - **Then drive every interaction the source app has, and confirm its observed effect.** `simctl`
     can't tap, so nothing below is exercised by a screenshot — a screen that paints correctly can be
     entirely dead: send text · **send an attachment through the picker** · **reply** → quote preview →
     send → quoted message renders · **edit** → composer prefills → save → edited state shows ·
     **long-press** → actions menu · **react** from the picker · open a **thread** and reply ·
     channel-row tap **and** long-press · **back-nav** (chat → list, thread → chat). A
     rendered-but-inert affordance is a FAIL.
   - **This list is not a design check and does not close with the design gate.** A screenshot of an
     attach menu is identical whether the upload works or aborts with `SIGABRT` on the first real tap.
     Drive the upload, don't photograph the button.
5. **Design verify — reconciliation, not the first look.** Per §1a and §6, each screen was verified *as
   it was built* by the per-region design-match subagents; this gate **confirms** it and **fails if it
   never happened**. **Hard block: the two non-negotiable screens — the channel list and the channel
   screen (message list + composer) — must have _every_ region `Fixed` or genuinely
   `Impossible: <reason>`, each citing a baseline↔migrated crop. One "good enough" / un-diffed region on
   either screen = this gate FAILS, full stop.** It closes **against the ledger**: every ledger row with
   a filled Spec-rows cell has a PASS verdict citing a this-round capture of the migrated app compared
   to its reference, **driven states included** (composer typing, reactions, thread open, attachment
   picker). A visual feature whose ledger row says Ported but has no verdict row is unverified — treat
   it as FAIL.
   - **Seed data so every region actually renders BEFORE you compare:** incoming + outgoing, a
     same-author run (grouping + avatars), an attachment/album, a reaction, a reply/quote, a long
     wrapping message, a cross-day separator, and a **group** + a **1:1** (the 1:1 row + header must
     show the other member's single avatar). A region that never rendered is **unverified**, not passed.
   - **Confirm every mandatory region is actually ON SCREEN before you compare.** A chat screen with
     **no visible composer** (or a clipped message list / header) means a region got pushed off-screen —
     almost always the header-outside-`<Channel>` trap (gate 0 / [`RULES.md`](RULES.md)). A mandatory
     region absent from the frame = **not done**; fix the layout and re-shoot.
   - **Produce the region-diff artifact, don't claim it.** Output a
     `region | baseline crop | migrated crop | PASS/FAIL` table, one row per filled Spec-rows cell, from
     actual crops; the **baseline crop must be the original's real pixels**. Whole-screen "looks close"
     is how ~10 per-region defects (split avatar, receipt placement, in-bubble reactions, timestamp
     side, composer button shapes, date-pill colour, bubble tail) shipped unnoticed.
   - **Crop the whole composite + its container + margins — full-width, never the sub-element you
     built** (a crop framed on the pills or the button alone verifies *contents* but hides
     *positioning*). Composite units, screen-edge to screen-edge: a **whole single message row** (bubble
     + metadata + reactions + avatar; incoming *and* outgoing), the **whole composer bar** (at-rest *and*
     typing), a **channel-list row** (1:1 *and* group), and the **header**. Then answer the **placement
     question** before any PASS — reactions *inside vs below* the bubble, send/mic *inside vs outside*
     the pill (plus pill *filled vs outlined*, attach *circle vs square*), metadata
     *inside/beside/below*, avatar *silhouette vs initials*.
   - **A region you specced but never built is a FAIL.** Cross-check every `design-analysis.md` region
     against an implemented+verified result.
   - **Banned as a resolution:** the §1b list, **and any other qualifier or adjective**. A region's only
     valid terminal states are **Fixed** or **Impossible: \<reason\>**.
   - **Passing this gate says nothing about interaction** — every handler is verified in **gate 4**.
6. **Ledger closure:** every parity-ledger row is Ported / Rewritten / N/A / GAP-with-decision. A
   `GAP - provisional` row (section 2 default) closes the gate only if the final report calls it out
   explicitly as a decision the user still owes.
7. **Docs match reality:** rewrite README/feature lists against what the migrated app actually does,
   including a "Known gaps vs. the Sendbird original" section from the GAP rows.

| Excuse | Reality |
|---|---|
| "tsc and the build pass, we're done" | A green build proves nothing about the connection, the pixels, or whether `@sendbird` is gone — gates 3-5. |
| "The token wiring is obviously right" | Stream requires a token where Sendbird did not; a real run shipped without ever connecting. Section 4. |
| "The theme was ported, it'll look the same" | A match is claimed from a simulator capture, never from theme diffs. |
| "Good enough on those screens, let's ship" | Not for the two non-negotiable screens — and "the list matches" is not "the app matches": the list hides every bubble, avatar, metadata and composer gap on the chat screen. |
| "It's stock Sendbird + a palette, so a recolor is enough" | Sendbird's stock UI is **not** Stream's (bubble tail, metadata placement, avatar, composer buttons, spacing all differ) and a palette carries no layout, so "stock Stream UI + accent" is a **named failure mode**. Match the structure, then the colour. |
| "I screenshotted the original once — baseline done" | A resting shot holds no composer-typing, reaction, or picker detail. §1a wants driven states. |
| "That feature was tiny, nobody will miss it" | Silent drops are how READMEs advertise ghosts. It's a ledger row: N/A or GAP, decided, in writing. |
| "I'll port the MessageCollection faithfully and refactor later" | The mechanical port of hand-rolled machinery IS the bug (lost optimistic sends, stale state, dead handlers). Golden rule 3. |
| "The gaps were minor, I decided them myself and kept going" | Minor is the user's judgment, not yours. >= 1 GAP row = the section 2 checkpoint, or a `provisional` default reported loudly. |

---

## 8. Offer the data migration (never auto-run it)

Everything above migrates the **code**. The app now points at an **empty** Stream app — no users,
channels, or history moved. Once gates 1-7 pass, ask:

> The SDK migration is done and verified. Do you also want to migrate your Sendbird **data** (users,
> channels, message history, reactions) into Stream? There are three approaches: **A** hard switch
> (simplest, needs a maintenance window), **B** uni-directional sync (zero downtime, the most common
> choice), or **C** bi-directional sync (zero downtime, no forced app update, Enterprise).

Data migration is server-side and SDK-independent, so it lives in the shared runbook:
[`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md). If the user says yes,
read that file and follow it. If they only wanted the SDK swap, stop here — it touches production data
and may incur attachment-transfer cost.
