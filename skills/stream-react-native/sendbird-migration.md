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

## Fidelity is the job — read this every time, it's the part every run gets wrong

Getting the app to **build, connect, and deliver messages live** is the easy 80%. The migration is
judged on the **last 20%: does each screen look and behave like the Sendbird original?** That 20% is
where **both real trial runs failed** — never on the SDK swap, always on the design match — and they
failed the *same* way: they reached design last, under wrap-up pressure, glanced at a full-screen
screenshot of *their own* app, saw a coherent chat app, and wrote "PASS" with no side-by-side
comparison behind it. **Internal coherence is not fidelity.** An app that looks like a nice chat app
*on its own* has been verified against nothing — colored-initial avatars where the original shows
**gray silhouettes is a FAIL even though colored looks nicer**, and "more idiomatic" / "more
on-brand" / "arguably better than the original" is a skip dressed up as a choice.

**Two screens are NON-NEGOTIABLE — every region on them ends `Fixed` or genuinely `Impossible`, never "good enough":**
1. **The channel list** — row anatomy: avatar shape, title / preview / timestamp placement, unread
   badge treatment.
2. **The channel screen: message list + composer** — where the gaps hide and where every run shipped
   wrong. Bubble shape/tail, incoming vs outgoing **background AND text** colour, avatar treatment,
   timestamp + read-receipt placement, reaction placement, and the **composer** (button inventory, the
   at-rest → typing send/mic swap, attach-button shape). A channel-**list** screenshot hides all of it
   — "the list looks right" is not "the app looks right."

**On these two screens, "good enough" is not enough.** "close enough", "acceptable approximation",
"minor", "keep default", "arguably better", "residual", "cosmetic", "polish", "deferred",
"nice-to-have" — and any other qualifier — are FAILs here, not resolutions — every region ends
`Fixed` or genuinely `Impossible: <reason>`. **A single region on either screen that doesn't match —
and isn't genuinely `Impossible` with a reason — is an immediate no-go for the whole migration.** Not
"mostly there", not "just one small thing": any unmatched, undiffed region blocks delivery. Surface
it, do not ship it.

**Walk this per-region checklist on both screens — each row is a Sendbird→Stream _default_ gap that a
green build and a full-screen glance hide. The "how" for each lives in
[`references/design-matching.md`](references/design-matching.md); this is the list you may not skip.**
These are the **most-missed regions — a floor, not the full set.** Do **not** treat the table as
exhaustive: `design-matching.md`'s region decomposition is authoritative and covers everything else
(quoted replies, polls, the attachment/image viewer, typing indicator, the thread screen, …).

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
| Composer states | at-rest / **typing** / **voice-recording** / **edit** never each rendered and compared |
| Composer chrome | floating vs docked (`messageInputFloating`), pill fill / border / radius, and the bar/wrapper background left at Stream's |
| Header | title / subtitle / avatar / right-side actions not matched to the source header |
| Date separators | Stream's default pill colour / style instead of the source's |
| Empty / loading / error strings | Stream's default English (`Streami18n`) instead of the source's copy |

**Reactions and the composer are where Sendbird and Stream diverge MOST — treat the Stream default as
_wrong_ for these two until a crop proves otherwise; they are structural rebuilds, not recolors.**
Sendbird commonly renders **reactions** as a box/bar **attached to the bubble** (Stream's default floats
pills *above/outside* it — `ReactionListTop`/`ReactionListBottom`), and its **composer** commonly puts
**send/mic OUTSIDE the input pill** with a **bordered/squared `+`** (Stream's default keeps send/mic
**inside** the pill via `OutputButtons` and ships a plain/circular `AttachButton`). Same-looking ≠ same:
read the exact arrangement off the section-0c baseline and rebuild to it — do not assume either SDK's
default (recipes: [`references/design-matching.md`](references/design-matching.md) → Composer / reactions rows).

**Verify each screen AS YOU BUILD IT — do not batch verification into a phase at the end.** Deferring
the compare to a terminal step reached under completion pressure is the single mechanism behind both
failures. So a screen is **not built until it is verified**: screenshot the migrated screen and diff it
region-by-region against the reference *before you move to the next one*. The exact loop lives in
[`references/design-matching.md`](references/design-matching.md) Step 3 — run that loop here, in full,
region by region. Skipping or shortcutting it is the failure both runs hit. Section 7's design gate is then a **final reconciliation** that
every screen was already verified, not the first time you look. The instant you are about to call
design "done" without a per-region baseline↔migrated comparison in hand, stop — that is the exact
moment both runs went wrong.

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

**Headless-core branch (`@sendbird/chat` core, no UIKit, 100% custom UI).** When the app is built
directly on the Sendbird **core SDK** with hand-rolled screens and **no `@sendbird/uikit-react-native`**,
the idiomatic target is the **headless `stream-chat` core client**, keeping the custom components — **not**
`stream-chat-react-native` / `stream-chat-expo`. Do **not** install the Stream RN UI package or its native
peers (`react-native-reanimated` / `-gesture-handler` / `-teleport` / `-svg`, `OverlayProvider`): mounting
Stream UI would replace the custom design, and the peers are dead weight. Migrate the SDK layer only:
`SendbirdChat.init` -> `StreamChat.getInstance(apiKey)`; `MessageCollection` + handlers -> `channel.watch()`
+ read `channel.state.messages` + `channel.on(...)` -> local `setState` (the reactive replacement for the
collection lifecycle). **Optimistic sends are manual here:** `channel.sendMessage` on the client is not
optimistic (kill-list #1) and there is no `MessageComposer` to insert the pending copy, so add it yourself
with a client-generated id via `channel.state.addMessageSorted({ id, text, user, status: 'sending', … })`
before the send, and let the echoed `message.new` dedupe by id. Everything else follows the mapping tables
as usual; the UIKit-fragment rows (sections 12-13) simply don't apply.

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

**The deliverable of this step is the design analysis, not a folder of screenshots.** The pixels are
only the input; the output is [`references/design-matching.md`](references/design-matching.md)
**Step 1 (Decompose the reference into regions)** run against the original - every screen broken into
regions, each region carrying its concrete spec (measured sizes, matched weights, sampled colors),
saved to `design-analysis.md`. Run Step 1 **now, while the original renders** - this is the one moment
the reference is a running app you can re-screenshot and pixel-sample, so it is also the moment its
spec is cheapest and most accurate to extract; deferring it means decomposing from memory later.

1. **The original runs (highest rung): capture it in the simulator, then decompose it.** Build and
   boot the original Sendbird app on the iOS simulator per
   [`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md), and use that page's
   simulator-driving discipline to capture **every region and every state** the design match will be
   judged on - not just the channel list:
   - **Screens & states to shoot:** the channel list; a chat with **both an incoming and an outgoing
     message** visible; the composer **at rest and while typing** (the send/mic swap); any thread
     screen; the attachment picker open; reactions; and - if the app supports it - **dark mode** (flip
     the OS appearance, [SIMULATOR-VERIFICATION.md](references/SIMULATOR-VERIFICATION.md) §6). A
     list-only screenshot hides every bubble/composer difference, which is exactly where a migration
     looks wrong.
   - **Reach them without taps the same way** - `simctl` can't tap, so drive navigation and composer
     states from **temporary code scaffold** and screenshot each
     ([SIMULATOR-VERIFICATION.md](references/SIMULATOR-VERIFICATION.md) §3-§4). **Caveat: you are
     driving the *original Sendbird* app here, so the state-driving hooks in §4 are Stream's and do
     NOT apply** - use Sendbird's own navigation and composer APIs (or seed the state server-side) to
     reach each screen/state. Only the SDK-agnostic loop carries over unchanged: pin one UDID, `simctl
     launch`, `simctl io … screenshot`, wait for the client before the shot, and the dark-mode flip.
   - **A stuck login screen is usually a slow cold connect, not a dead backend.** The original can sit
     on its login/auth screen for 30–60s on a cold start (fresh socket + offline-cache restore), and its
     console may not surface in your terminal — so absence of an error is not evidence of failure. **Wait
     45–60s and re-screenshot before concluding auth failed; do NOT probe the backend to "prove" it's
     down** (a real run burned cycles curling the Sendbird REST API and nearly asked for screenshots it
     didn't need).
   - **Tooling precheck — do it now, before you need to crop.** The region-diff crops need ImageMagick or
     PIL; if neither is installed, set it up up front (`python3 -m venv .designvenv && .designvenv/bin/pip
     install Pillow numpy`, or install `magick`). A tool missing mid-verify is a silent reason the crop
     step gets skipped.
   - **Then run design-matching Step 1 on the shots:** go region by region, and for each region record
     the concrete spec - bubble radius/shape/max-width/alignment, avatar shape/size, font sizes and
     **weights**, paddings/gaps, and the **sampled** colors (bubble fills, accent, read-receipt ticks,
     background) - **measured and pixel-sampled off the screenshots, not eyeballed** (the measure-
     don't-guess and sample-every-color methods live in that page). Write the result to
     `design-analysis.md`, and fill the parity ledger's **Spec rows** column so every visual feature
     names the region(s) and captured state(s) that spec it.
2. **The original won't build, but the user has screenshots (rung 2):** treat the user's screenshots
   as the reference and run the **same** design-matching Step 1 decomposition on them - still Pixel
   tier, measured and sampled the same way. You just can't re-shoot new states, so decompose what you
   have into `design-analysis.md` and flag any region no screenshot covers.
3. **No runnable app and no screenshots — rung 3 (palette-only recolor, last resort).** First try to
   avoid this rung: **rebuild the original** (a `git worktree` at the pre-migration Sendbird commit, or
   the source SDK if this is a brand-new screen) and boot it in the simulator — that promotes you back
   to rung 1 and hands you a real reference *and* its source to read. Only when the original genuinely
   cannot be built **and** no screenshots exist: read the Sendbird theme (`colorSet` / `SBUTheme` /
   string sets) and record its palette in `design-analysis.md`. **Be honest about what this is: a theme
   file is colours, not layout — you cannot derive structure from a palette, so this rung only
   *recolours stock Stream* and will NOT resemble the original's structure** (bubble/tail geometry,
   metadata placement, row layout, composer). It is a recolor, not a match. When you ship on this rung,
   **say so in the summary: "layout not matched to the original."** "structural" here names the fidelity
   *tier* (how little you could learn about the original), not an achieved outcome — the rung changes
   only how you obtained the *reference*; **it never lowers the region contract or the verification
   bar** (§6). And confirm even the palette against the running app: a colour read from code is the
   *intended* value, and the SDK may not repaint the element you expect.

Whichever rung you reach, the output is the same `design-analysis.md` region spec that section 6 hands
to design-matching as **the reference design**. Keep it until the section 6 verify loop passes, then
remove it (unless the user asked to keep it), per design-matching's Step 1.

> **The rung is about the *visual* reference only — it is orthogonal to the parity-ledger code
> analysis, and neither replaces the other.** Reading the Sendbird source to inventory **features,
> behaviours, and component/API mappings** — silent/ephemeral flags, custom channel/attachment/message
> types, push config, roles & permissions, and any Sendbird-only feature — is mandatory at **every**
> rung: none of it is visible in a screenshot, it feeds the **parity ledger** (not the design spec),
> and it is the only way to find *what must be ported at all*. Screenshots make the port *look* right;
> code analysis finds *what exists*. So a lower rung means a less pixel-perfect **reference** — never
> less **verification** and never less code analysis. (This is why rebuilding the original on rung 3
> helps twice: a screenshottable reference **and** its source to sweep.)

> **HARD STOP (ordering):** on a Pixel baseline, do **not** install Stream packages or edit **any**
> file until `design-analysis.md` exists and decomposes every in-scope region with a concrete,
> **sampled** spec. Capturing the baseline late — after packages/scaffold are in — is a process
> failure even if you self-correct: the window where the original is drivable is exactly when the spec
> is cheapest and most accurate. The design analysis is the **contract** the implementation and the
> section-7 verify must satisfy, not a checkbox.

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
| 4 | **A token is always required.** Sendbird's `connect(userId)` with no token has no Stream equivalent | The userId-only auto-create path is gone. Dev: `client.devToken(id)` **only while dev tokens are enabled** on the app (**check this first — if disabled, connect as one of a fixed set of test users with tokens pre-minted via the `getstream` CLI/backend**, don't auto-create arbitrary users); prod: a `tokenProvider`. See section 4. |
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
| 16 | **SDK mutations echo back as events and update `channel.state` on their own — don't parse-and-cache a mutation's return value in a parallel store.** `translateMessage` / reactions / pins / edits are broadcast back as `message.updated` (etc.) to the channel's watchers — **including the caller** — so the SDK merges the change into `channel.state.messages` and re-renders with no extra work; Sendbird UIKit's handler-driven model nudges you to capture each call's result and stash it in your own `{[msgId]: value}` store | A parallel cache duplicates state, drifts from the live message, and couples you to the response's **exact shape — which the SDK's TS type can misdescribe** (e.g. `translateMessage` nests the message under `.message`, so reading top-level `res.i18n` type-checks but is always `undefined` → the UI silently shows nothing). You don't need the response at all: just read the live `message.i18n` / `channel.state` and let the echoed event drive the re-render. **Do NOT hand-dispatch the event yourself** (`client.dispatchEvent({ type: 'message.updated', … })`) — it already arrives over the socket; dispatching it too just double-applies. Source of truth = channel state, not your cache. |

---

## 2. Plan & checkpoint - involve the user before the first edit

Assemble the migration plan from section 0's outputs. It is **not a new document** - it is the
parity ledger plus four strategy lines:

| Plan field | Source | Example |
|---|---|---|
| Flavor + integration shape(s) | section 0 classification | "Expo (`stream-chat-expo`); UIKit fragments + a `MessageCollection` hook" |
| Credentials & token path | section 4's precedence, resolved on paper | "user-provided key; backend token endpoint re-pointed to mint Stream JWTs" |
| How the reference is obtained | section 0c baseline rung | "rebuild + capture the original (default)", "user screenshots", or — last resort, no original obtainable — "palette-only recolor (layout NOT matched)". Matching the original is non-negotiable; this row is *how* you'll get the reference, never *whether* to match. |
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
- the reference is **not obtainable** the default way (the original can't be built and the user has no
  screenshots) — ask **how to get one** (rebuild? can they share screenshots?); do **not** offer lower
  fidelity as a time saving, and never frame it as cheap-vs-faithful. Matching the original is the
  target; build effort is not a reason to drop it (RULES.md: "never because it's risky or more effort");
- the **user asked** to review the plan first.

Ask everything in **one batched round** - gap decisions, the credentials call, how to obtain the
reference - never a drip of single questions. When no trigger holds, don't interrupt: proceed, and include the
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
   while dev tokens are enabled** on the Stream app - otherwise it is rejected server-side.
   **First check whether dev tokens are enabled** (Dashboard > app > Authentication, or treat a
   server-side rejection on the first `devToken` connect as the signal). **If they are disabled,
   do NOT try to reproduce Sendbird's connect-any-userId behaviour - fall back to a fixed set of
   test users whose tokens are pre-minted via the `getstream` CLI / backend** (`getstream token
   <id>`), and connect as one of those. Gate any pasted-credential/dev-token path behind `__DEV__`
   or a feature flag so it cannot ship. Never use `devToken()` for production.
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

**When you seed, put at least one message carrying reactions in EVERY channel** (not just one channel) —
plus, in the channel you'll design-verify, the rest of the region-triggering set (incoming + outgoing, a
same-author run, an attachment/album, a reply/quote, a long wrapping message, a cross-day separator; §7
gate 5). Reactions are the easiest to forget and one of the two regions that keep shipping wrong: the
reactions box can't be matched or verified if no seeded message ever renders it. Add reactions at seed
time, server-side, as part of creating the data — not as an afterthought during verification.
**Seed reactions only with types in the app's `supportedReactions`:** the SDK filters unsupported types
out of `useMessageContext`'s `reactions`, so a reaction seeded as an unsupported type (e.g. `question`)
silently never renders — and the crop then shows nothing while looking like a layout bug. Use the
default set (`like`/`love`/`haha`/`wow`/`sad`) or extend `supportedReactions` (with an `Icon`) first, and
seed a reaction on **both** an incoming and an outgoing message.

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

**Offload the design match to subagents so the main migration agent isn't the one matching pixels
under wrap-up pressure — that overload is why these regions get skimmed.** For the two non-negotiable
screens this fan-out is **required, not a recommendation** — matching them inside the main agent's
wrap-up is the exact failure to avoid. Do not treat
`design-matching.md` as documentation to consult in passing; make it dedicated work. **Fan out one
focused subagent per _composite screen-area_** — the **message row** (it owns bubble fill+text,
metadata placement, reactions, and avatar *together*), the **composer** (the whole bar), the
**channel-list row**, and the **header** — **not** one broad "do the design" subagent, and **not** one
per tiny sub-element (a reactions-only subagent crops the pills in isolation and can't see whether they
sit *inside vs below* the bubble — the exact miss from a real run). A whole-screen subagent gets trusted
blindly and glances-and-declares; a composite-area subagent owns every checklist region in its area,
rebuilds them **together**, and crops the **whole composite full-width** — so the *positioning* between
sub-elements is verified, not just each element in isolation. Give each a clean, single-purpose context
and a tight contract: **in** — the region's section-0c baseline crop + the exact recipe from
[`references/design-matching.md`](references/design-matching.md); **out** — the region built to
pixel-match **plus the baseline↔migrated crop pair it produced** as its deliverable, not a prose "PASS".
A composite-area task keeps the main agent light and gives the area full attention — that is what makes
it come out pixel-accurate. **Treat the returned crop pair as the evidence, never the subagent's words:**
do not relay a region as matched when you have not seen its baseline↔migrated crop. Hand each subagent the **section 0c baseline as the
reference design**: its **Step 1 (Decompose the reference into
regions)** was already run in section 0c - the `design-analysis.md` region spec is your entry point;
reuse it rather than re-decomposing, route each region through the three axes, and continue to Step 3.
If a region is missing a spec (a state 0c couldn't capture), decompose it now off the screenshots.
The reference for rungs 1/2 is those captured screenshots + `design-analysis.md`; on the palette-only
rung there are no original screenshots, so the visual reference is only the palette and structure is
unmatched by definition:

- **Rung 1/2 (simulator capture / user screenshots):** Pixel tier - run the full pipeline
  (Decompose -> three axes -> Step 1.5 native packages -> Step 2.5 completion contract -> Step 3
  verify). Sample colors and measure sizes off the reference screenshots.
- **Rung 3 (palette-only recolor):** you have colours but **no layout reference** — yet you still run
  the **same** pipeline and the **same Step 3 verify**; the region contract (every region ends
  **Fixed** or **Impossible**) is **not** waived. The only difference: structural regions have no
  original to match, so each is either matched to Stream's sensible default *or* logged
  **Impossible: no layout reference (palette-only rung)** — never silently left at the default, never
  marked matched. The palette rows are the *intended* colours read from code; confirm they actually
  render on the running app (a token may not repaint the element you expect — verify against the app,
  not the constant).

Its Step 3 owns the capture-and-compare loop - including screenshotting the **migrated** app on the
simulator and comparing region-by-region against the reference crops (the `magick` crop+stack
recipe). **The reference must be independent ground truth — the original's actual pixels.** A
`design-analysis.md` you authored yourself is **not** a valid baseline: comparing the migrated app
against a spec you wrote from the same palette passes *by construction* and proves nothing (a real run
did exactly this — certified its own recolor as a "match"). A code-derived spec can certify
*"recolored,"* never *"looks like the original."* Do not declare the design matched from code review;
neither real trial run captured a single screenshot, and both shipped unverified skins.

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
5. **Design verify loop — reconciliation, not the first look.** Per the fidelity preamble and §6, each
   screen was verified *as it was built* (by the dedicated per-region design-match subagents of §6 —
   **required, not optional**, for these two screens); this gate
   **confirms** it and **fails if that never happened** — a design match first attempted here, at the
   end, is the failure both runs hit. **Hard block: the two non-negotiable screens — the channel list
   and the channel screen (message list + composer) — must have _every_ region `Fixed` or genuinely
   `Impossible: <reason>`, each citing a baseline↔migrated crop. One "good enough" / "close enough" /
   un-diffed region on either screen = this gate FAILS, full stop; the migration does not close.** It
   reaches its
   [`references/design-matching.md`](references/design-matching.md) Step 3 exit - and closes
   **against the ledger**: every ledger row with a filled Spec-rows cell has a PASS verdict citing a
   this-round simulator capture of the migrated app compared to its reference, **driven states
   included** (composer typing state, reactions, thread open, attachment picker). A visual feature
   whose ledger row says Ported but has no verdict row is unverified - treat it as FAIL.
   - **Seed data so every region actually renders BEFORE you compare.** You cannot verify a region you
     never drew. Populate both directions (incoming + outgoing), a **same-author run** (so grouping +
     avatars show), an **attachment / album**, a **reaction**, a **reply/quote**, a **long message that
     wraps**, and a **cross-day date separator** — plus a **group** chat and a **1:1** (the 1:1 row +
     header must show the other member's single avatar, not a cluster). A region that never rendered is
     **unverified**, not passed.
   - **Produce the region-diff artifact, don't claim it.** A full-screen resemblance glance is NOT a
     verify. Output a table — `region | baseline crop | migrated crop | PASS/FAIL` — one row per
     filled Spec-rows cell, from actual crops (the `magick`/PIL crop+compare recipe). Whole-screen
     "looks close" is exactly how ~10 per-region defects (split avatar, receipt placement, in-bubble
     reactions, timestamp side, composer button shapes, date-pill colour, bubble tail) shipped
     unnoticed in a real run. **The `baseline crop` must be the original's real pixels** (a rung-1/2
     screenshot, or a rebuilt original) — a spec you authored from the palette is not a baseline and
     cannot certify "looks like the original," only "recolored." On the palette-only rung, where no
     original crop exists, structural regions are logged **Impossible: no layout reference**, not PASS.
   - **Crop the whole composite + its container + margins — full-width, never the sub-element you built.**
     A crop framed on the pills or the button alone verifies *contents* but hides *positioning*: a real
     run cropped reactions in isolation, saw "emoji + count + add-button" on both sides, and missed that
     the source renders them **inside** the bubble while it had built them **below**. Crop **full-width**
     (screen-edge to screen-edge, so the bubble/bar/row boundary and both margins are always in frame),
     at these composite units: a **whole single message row** (bubble + metadata + reactions + avatar in
     one frame; incoming *and* outgoing), the **whole composer bar** (at-rest *and* typing — not
     button-by-button), a **channel-list row** (a 1:1 *and* a group), and the **header**. Then answer the
     region's **placement question** from that crop before any PASS — reactions *inside vs below* the
     bubble, send/mic *inside vs outside* the pill, metadata *inside/beside/below*, avatar *silhouette vs
     initials*. A sub-element that looks right in isolation can still be mispositioned; presence + colour
     is not enough.
   - **A region you specced but never built is a FAIL, not done.** Cross-check every
     `design-analysis.md` region against an implemented+verified result (a real run specced the header
     avatar and add-reaction button, then never built them — no gate caught it).
   - **Banned as a resolution:** "acceptable approximation", "minor", "difference noted", "close
     enough", "keep default", "residual" / "cosmetic residual", "cosmetic", "polish", "deferred",
     "nice-to-have" — **and any other qualifier or adjective**. A region's only valid terminal states are
     **Fixed** or **Impossible: \<reason\>**; a synonym for "good enough" is still "good enough" (a real
     run slipped past this list by calling an unfinished region a "cosmetic residual").
   - **Screenshots don't test interaction — a screen that paints can still be behaviorally dead.**
     `simctl` can't tap, so a screenshot diff never exercises press/nav handlers. Any custom slot with
     `onPress`/`onSelect`/navigation (custom `ChannelPreview`, message press, buttons) must be verified
     by *driving* it (temp auto-nav / device), not a shot — a custom `ChannelPreview` silently broke
     channel-tap and was invisible to the screenshot loop. **Drive every interaction the source has and
     confirm its observed effect:** send text · send an attachment via the picker · **reply** → quote
     preview → send → quoted message renders · **edit** → composer prefills → save → edited state shows ·
     **long-press** → actions menu · **react** from the picker · open a **thread** and reply ·
     channel-row tap **and** long-press · **back-nav** (chat → list, thread → chat). A rendered-but-inert
     affordance is a FAIL.
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
| "Good enough on those screens, let's ship" | Not for the two non-negotiable screens. The channel list **and** the channel screen (message list + composer) end every region `Fixed` or genuinely `Impossible` — "good enough" / "close enough" is a FAIL there. And "the list matches" is not "the app matches": the list hides every bubble, avatar, metadata and composer gap on the chat screen, which is exactly where every real run shipped wrong. |
| "It's stock Sendbird + a palette, so structural match + theming is enough — no verification needed" | Sendbird's stock UI is **not** Stream's stock UI (bubble tail, metadata placement, avatar, composer buttons, spacing all differ), and a palette carries no layout — so "stock new-SDK UI + accent" is a **named failure mode**, not a valid outcome. Even the palette-only rung captures the migrated app and logs every structural region Fixed or Impossible; a self-authored spec certifies "recolored," never "matches the original." |
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
