# Sendbird -> Stream Chat React migration (Track S)

A repeatable procedure for migrating a **React / Next.js web app** from the **Sendbird Chat SDK**
(`@sendbird/chat` + `@sendbird/uikit-react`) to **Stream Chat** (`stream-chat` +
`stream-chat-react`, **v14**). It works on *any* Sendbird integration shape - UIKit drop-in,
custom hooks, a Context+reducer store, direct calls, or spaghetti - because it **detects the shape
first** and re-implements each touchpoint in place. This is not a scaffold track: do not enter
onboarding or any Track A step.

This file owns the **procedure**; the cross-SDK knowledge lives in
[`references/sendbird-mapping.md`](references/sendbird-mapping.md) (symbol tables, behavioral
diffs, pagination recipes, feature-gap catalog - verified against the installed SDK types and
compile-checked recipes), with a grep-only long-tail companion
([`references/sendbird-mapping-extended.md`](references/sendbird-mapping-extended.md), ~520
inferred rows) for symbols the curated file doesn't carry. Where a step touches a Stream component's *current* props/hooks, fetch
the matching page from [`references/docs-map.md`](references/docs-map.md) per
[`RULES.md`](RULES.md) > Docs-first - a future major can rename symbols (exactly as v13 -> v14
removed `MessageInput` for `MessageComposer`, see [`migrate.md`](migrate.md)).

Three golden rules, learned from real migration runs:

1. **Change as little application code as possible - and migrate in place.** Preserve component
   boundaries, routing, and public prop/hook signatures; **edit the existing files (Sendbird out,
   Stream in) - do not create parallel new files and delete the originals.** Swap what's *inside*
   the SDK touchpoints, not the touchpoints. New files are justified only for genuinely new needs
   (e.g. a token endpoint that never existed); a file whose entire content was Sendbird machinery
   with no remaining purpose (a `colorSet` module) is deleted, not kept as a husk or reborn as a
   renamed twin. (Exception: a GAP substitution that repurposes a feature into a different one -
   e.g. scheduled-send becoming a draft feature - may rename its file to match the new purpose;
   that's a genuine feature change recorded in the ledger, not a twin of a still-existing feature.)
2. **Almost nothing is codemod-safe.** In a full audit of these two SDKs, fewer than 2% of
   symbol pairs survived a mechanical rename - virtually every touchpoint is a shape-shift or a
   behavioral difference. Plan file-by-file agent work from the mapping tables; never a global
   find-and-replace pass.
3. **Prefer idiomatic Stream over a mechanical port.** Where the Sendbird app hand-rolled
   machinery the Stream SDK has first-class (typing timers, presence polling, cursor bookkeeping,
   poll event re-fetching, send-state callbacks), **delete the machinery** and use the reactive
   primitive. The idiomatic rewrite is smaller and less buggy than the faithful port - and it
   still happens **inside the existing file/hook boundary** (golden rule 1): the body changes,
   the file and its public API stay where the callers expect them.

---

## 0. Detect & inventory (before any edit)

Map the footprint first - no code changes until this section is done.

```bash
grep -rln "@sendbird/chat\|@sendbird/uikit-react" --include=*.{ts,tsx,js,jsx} .
grep -rn "SendbirdProvider\|GroupChannel\|OpenChannel\|useSendbirdStateContext\|sendbirdSelectors\|withSendBird" --include=*.{ts,tsx} .
cat package.json   # note BOTH Sendbird versions and the package manager (lockfile)
```

**Classify each touchpoint** and migrate it per its pattern later:

| Pattern found | How it migrates |
|---|---|
| **UIKit drop-in** (`<SendbirdProvider>`, `<GroupChannel>`, `<GroupChannelList>`, `renderX` props) | Architectural remap, not a rename - compose Stream primitives ([`references/sendbird-mapping.md`](references/sendbird-mapping.md) section 12). |
| **Custom hook wrapping the SDK** (returns `{ state, actions }`) | Keep the hook's public return shape; replace the body with Stream calls + context hooks. Callers don't change. |
| **Context + reducer store** (SDK calls as effects that re-dispatch) | Keep the store shape; effects do the async Stream work and re-dispatch. The reducer stays pure. |
| **Class component via `withSendBird`** | Stream context is hooks-only - convert to a function component or wrap in a thin hook-calling adapter. |
| **Direct / inline SDK calls** | Swap in place; keep surrounding layout/routing. |
| **Spaghetti** | Migrate file-by-file; introduce a thin boundary only where it cuts churn. |

**Build the parity ledger.** List every user-facing chat feature the app has - from the code, the
README, and the UIKit config props (`enableOgtag`, `enableSuggestedReplies`,
`enableMarkdownForUserMessage`, `replyType`, voice messages, ...). One row per feature:

| Feature | Sendbird source | Plan (port / idiomatic rewrite / GAP) | Spec rows | Status |
|---|---|---|---|---|

The **Spec rows** column is filled by the visual-baseline capture below: every feature with a
visual surface names its `design-analysis.md` rows and the captured state(s) that show it (`-`
for features with no visual surface). It is the bridge that verify gate 5 checks - a visual
feature cannot close as Ported while its look was never specced or never judged. Reactions,
receipts, typing, the composer: each is a ledger row, so each owes a spec row and a verdict.

This ledger is the migration's backbone: every row must end as **Ported**, **Rewritten**,
**`N/A - <real reason>`**, or **`GAP - <decision>`** - the user's decision where one was
obtainable, else a `provisional` default per section 2 (the same no-silent-blanks discipline
as [`references/custom-ui.md`](references/custom-ui.md)'s completion contract - "deferred" and
"later" are not valid statuses). Silent feature drops in real migrations
happened exactly where no ledger existed - UIKit one-liner toggles vanished and the README kept
advertising them.

**Capture the visual baseline (ladder - the highest rung you can reach, not the first that's
convenient).** The migrated app must look like the original, so record what "the original" looks
like before you delete it. A migration briefly holds the best reference a design match can have:
**a running web app whose DOM you can probe and whose states you can drive** - strictly better
than any screenshot. That window closes the moment section 5 starts; spend real effort on rung 1
(an `npm install` and an env file are worth resurrecting) before falling back.

1. **The original runs: execute [`references/design-matching.md`](references/design-matching.md)
   Steps 1-2 against it now** (its Step 1 > Live reference). Concretely: create `.design-verify/`;
   capture full screens **plus element crops** of the high-detail regions (composer, one message
   row, a quoted reply, a reaction pill) into `.design-verify/reference/`; run a **probe pass
   against the original's DOM** - `getComputedStyle` + `getBoundingClientRect` on the Sendbird
   UIKit selectors (`sendbird-*` class names) - so bubble radius, colors, type roles, and composer
   layout enter the spec as **measured CSS values, not pixel samples**. **Drive the states, don't
   capture only rest:** every parity-ledger row with a visual surface gets its state captured -
   reactions *and* the open reaction selector, the hover actions surface, a thread open, a long
   multi-line draft, a staged attachment, receipts, typing - in both themes if the app has them
   (design-matching 6a's menu is the checklist; if the dev data is empty, populate it through the
   original's own UI first - Sendbird's client-side flows still work at this point). Then run
   design-matching Step 2 (the design-analysis agent) over these artifacts so
   **`.design-verify/design-analysis.md` is written before the first migration edit** - deleting
   the original can no longer orphan the spec. Fill the ledger's Spec-rows column from it.
2. **User-provided screenshots** of the running app - ask if any exist; treat as the reference
   (Pixel tier).
3. **Code-derived spec** (always available): extract the palette from the `colorSet` object /
   custom CSS, the strings from `stringSet`, fonts, bubble radii, and the layout structure
   (panes, headers, which regions exist) into a written spec (Lo-fi tier). Say explicitly, in the
   plan and the final report, that this rung **cannot certify** composer / bubble / reaction
   fidelity - only structure.

Whichever rung produced it, this baseline becomes the **reference design** for step 6. The
`.design-verify/` directory is run scaffolding (never committed); it lives until design-matching's
exit cleanup at gate 5, not until the end of this section.

---

## 1. Kill list - the traps that bit real migrations

Verified behavioral differences that produce silent runtime bugs, not build errors. Check every
one against the app; the full catalog is in
[`references/sendbird-mapping.md`](references/sendbird-mapping.md).

| # | Trap | Consequence if ported 1:1 |
|---|---|---|
| 1 | **Stream echoes your own sent message** (`message.new` fires for your send, on top of the optimistic insert); Sendbird never did | Every Sendbird `onSucceeded`-append pattern **double-adds messages**. Remove manual appends; rely on optimistic state + events. |
| 2 | **The React `<Channel>` component skips its mount-time `watch()` when `channel.initialized` is already true** (it reuses in-memory state) | Sendbird's `refresh()` always hit the server; a port that relies on re-mounting `<Channel>` to refresh reads stale state. An explicit `channel.watch()` / `channel.query()` call always refetches - use one for refresh flows. |
| 3 | **`client.muteUser` is a personal notification mute**, not Sendbird's operator-enforced silencing | "Muted" users keep posting. Operator mute -> timed `channel.banUser(id, { timeout, reason })` - and **Sendbird durations are seconds, Stream `timeout` is minutes**: a 1:1 duration port makes every ban 60x longer. |
| 4 | **Blocking is DM-only in Stream**, global in Sendbird | Blocked users stay visible in group channels unless you also mute + filter. |
| 5 | **`StreamChat.getInstance` is a bare singleton, not keyed by apiKey**; and never use it client-side | Wrong app silently reused. Use `useCreateChatClient` (also strict-mode safe, [`RULES.md`](RULES.md) > Strict mode). |
| 6 | **`channel.delete()` / message delete soft-delete by default**; Sendbird deletes are permanent | Data-retention behavior silently changes - pass `hard_delete` where the app promised purging. |
| 7 | **Events arrive only for watched channels** | Handlers ported as global listeners miss events for channels nobody watched. |
| 8 | **Sibling panes must become `<Channel>` descendants** | Sendbird renders search/thread/settings panels as *siblings* of the conversation; Stream's equivalents read channel context, so they must move *inside* `<Channel>` - a layout restructure, not a rename. |
| 9 | **`<Chat theme>` is a CSS class name** (`str-chat__theme-dark`), not `'light' \| 'dark'`; the JS `colorSet` prop has no equivalent | Theme switching silently does nothing; recoloring must move to `--str-chat__*` CSS variables (step 6). |
| 10 | **CSS import path**: `stream-chat-react/dist/css/index.css`; the v2 path no longer resolves in v14 | Unstyled UI or a build error. |
| 11 | **No offline cache on web** - Sendbird UIKit enables one by default | State no longer survives reload; accept event-driven re-hydration rather than porting the cache dependency. |
| 12 | **Every stateful `.next()` query cursor dies** (~13 query types) | Each becomes a stateless offset/id-cursor call - per-query recipes in [`references/sendbird-mapping.md`](references/sendbird-mapping.md) section 7. |
| 13 | **Poll booleans invert**: `allowMultipleVotes` -> `enforce_unique_vote`, and `castPollVote` takes one option per call | Multi-vote polls flip semantics; both real trial runs hit this. |
| 14 | **Read receipts keep data only for the latest own message by default** | Per-message receipts vanish - set the `returnAllReadData` prop on `<MessageList>` for Sendbird parity. |

---

## 2. Plan & checkpoint - involve the user before the first edit

Assemble the migration plan from section 0's outputs. It is **not a new document** - it is the
parity ledger plus four strategy lines:

| Plan field | Source | Example |
|---|---|---|
| Integration shape(s) | section 0 classification | "UIKit drop-in + custom hooks" |
| Credentials & token path | section 4's precedence, resolved on paper | "user-provided key; pre-signed CLI tokens (no backend)" |
| Design bar + baseline tier | section 0 baseline rung | "measured (live capture)", "pixel (user screenshots)", or "structural + exact palette (code-derived)" |
| Gaps + proposed resolutions | ledger GAP rows + [`references/sendbird-mapping.md`](references/sendbird-mapping.md) section 15 | "scheduled messages -> drafts (substitute)" |

For the gaps row: collect every feature with **no Stream equivalent** (scheduled messages,
channel-level report, report categories, `copyMessage`, `FeedChannel`, offline cache, DND quiet
hours, suggested replies, ...) - each needs a decision: **substitute** (the mapping table names
the closest one), **rebuild app-side**, or **drop**.

**Checkpoint - pause and present the plan to the user when any of these holds:**

- the ledger has **>= 1 GAP row** (a product decision exists - it is the user's, not yours);
- the **credentials/token path is unresolved** (no key provided or found, or no way for clients
  to obtain tokens);
- the **design bar is ambiguous** (pixel fidelity implied, but no baseline screenshots exist and
  the user hasn't said how close is close enough);
- the **user asked** to review the plan first.

Ask everything in **one batched round** - gap decisions, the credentials call, the design bar -
never a drip of single questions. When no trigger holds (no gaps, credentials and design bar
settled), don't interrupt: proceed, and include the plan in the final summary.

**Non-interactive runs** (no user available to answer, or the user said "don't check in, use
defaults"): do not stall. Take the mapping table's named substitute as the default for each gap,
mark those ledger rows **`GAP - provisional: <default>`**, and surface every provisional decision
prominently in the final report - a provisional decision the report doesn't call out is a silent
feature drop with extra steps.

The plan lives **in the ledger**, not beside it: a mid-migration deviation is a ledger edit (gate
6 closes the ledger, so deviations surface at verification), never a silent change of course. A
gap discovered mid-migration is a checkpoint-grade decision the moment it appears - decide it (or
mark it provisional) then; parking it as a TODO is what this section exists to prevent.

---

## 3. Packages

**Install Stream alongside Sendbird first; remove Sendbird last.** Ripping the Sendbird packages
out now leaves the app unbuildable until every touchpoint is migrated - which makes the section 4
connection gate impossible to run. Order:

1. Add `stream-chat` + `stream-chat-react` with the project's existing package manager per
   [`RULES.md`](RULES.md) > Package manager (for npm, pass `--legacy-peer-deps`). They version
   independently - never apply one shared version string.
2. Add `import 'stream-chat-react/dist/css/index.css';` once at app entry (kill-list #10; the
   aliased `stream-chat-react/css/index.css` path also resolves - either is fine, be consistent
   with [`migrate.md`](migrate.md) if the app later upgrades).
3. Only after section 5 completes: uninstall `@sendbird/chat` + `@sendbird/uikit-react`, delete
   the Sendbird stylesheet import, and grep to confirm zero `@sendbird` imports remain.

---

## 4. Credentials & connection proof (gate: a real user connects)

The biggest conceptual shift: Sendbird connects with just a `userId` (auto-creating users
server-side, token optional); **Stream always requires a signed token** - there is no userId-only
path. Handle secrets per [`../stream/RULES.md`](../stream/RULES.md) > Secrets.

Wire it, then **prove the connection end-to-end before migrating any UI** - a real trial run
shipped a fully migrated app that had never once connected:

1. Get the Stream API key and replace the Sendbird `appId` in config - in precedence order:
   **(a)** credentials the user provided (in the request, or already present in the project's
   env/config) - use them as-is, don't run CLI setup around them; **(b)** only if none exist,
   ask the user or run `getstream init` (the one onboarding step Track S needs). Never invent
   a key.
2. Map the token path: `SessionHandler.onSessionTokenRequired(resolve, reject)` -> an async
   `tokenProvider` (`return` = resolve, `throw` = reject) passed as `tokenOrProvider`. Production
   needs a backend token endpoint; an existing Sendbird token endpoint gets re-pointed to mint
   Stream JWTs.
3. For local/dev parity, `client.devToken(userId)` works **only while "Disable Auth Checks" is
   enabled** on the Stream app - otherwise it is **rejected server-side**. If dev tokens are
   disabled and there's no backend yet: use tokens or a token endpoint the user provided if any;
   otherwise pre-sign real tokens with the CLI (`getstream token <user-id>`). Either way, store
   them in gitignored env vars - never in source. **In a backend-less SPA (Vite/CRA - no
   `/api/token` route), the client can't fetch a token at runtime**: read the pre-signed token
   for the logged-in user from an env map and pass it as the static `tokenOrProvider` string (fine
   for a demo; a real deployment still needs a backend token endpoint, since these tokens don't
   refresh - kill-list-adjacent: a static string token never refreshes).
4. Connect as a real user and confirm the WebSocket is healthy before proceeding. The Sendbird
   tree is still intact at this point (section 3), so mount the proof in a small dev-only
   route/component rather than the main flow - it exists to fail fast on auth, not to migrate UI.
   It is scaffolding, not migration: delete it once section 5 wires the real flow (in-place rule,
   golden rule 1).

```tsx
// <SendbirdProvider appId userId nickname accessToken> connected internally.
// Stream splits it: YOU build + connect the client, then <Chat> is a plain provider.
const client = useCreateChatClient({
  apiKey,                                  // was Sendbird appId
  tokenOrProvider,                         // string token, or async () => Promise<string>
  userData: { id: userId, name: nickname },
});
if (!client) return null;                  // still connecting
return <Chat client={client}>{/* ChannelList / Channel composition */}</Chat>;
```

---

## 5. Migrate the touchpoints

Work file-by-file, **in place** (golden rule 1), per the section 0 classification, pulling exact
symbol mappings from
[`references/sendbird-mapping.md`](references/sendbird-mapping.md) - the domain guide:

- **UI composition** (section 12-13): `<GroupChannel>` -> composed
  `<Channel><Window><MessageList/><MessageComposer/></Window><Thread/></Channel>`;
  `<GroupChannelList>` -> `<ChannelList>`; `renderX` props -> component swaps via
  `<WithComponents>`; `useSendbirdStateContext` -> focused context hooks. For any
  **livestream / high-message-throughput channel** (every migrated `OpenChannel`, and any
  channel expecting large message volume), render `<VirtualizedMessageList>` instead of
  `<MessageList>` - it takes the same `Message`-level props; fetch its page per
  [`references/docs-map.md`](references/docs-map.md) before wiring. Move sibling panes
  inside `<Channel>` (kill-list #8). Writing your own component for a prebuilt region - including
  porting an existing `renderX` implementation - is gated by [`RULES.md`](RULES.md) > Reference
  authority: load [`references/custom-ui.md`](references/custom-ui.md) first and fill its
  completion contract. **On a rung-1 baseline, any touchpoint that rebuilds a visual region
  (composer, message row, channel preview, header) also carries its `design-analysis.md` §3 rows:
  build to the original's measured look in this pass** - migrating to SDK defaults and deferring
  the look to a step-6 reskin is a second, avoidable rebuild of the same region. **Keep `<ChannelList>` as the query, watch, and real-time state owner.** For
  a product-grouped or bespoke rail, render the SDK-owned list with its documented
  `renderChannels` callback or `ChannelListUI` injection; do not maintain a parallel
  `client.queryChannels()` result and re-fetch it on events.
- **Channels** (sections 2, 7): three classes -> one `Channel` + type string; `OpenChannel` ->
  `livestream` type; distinct channels -> member-set channels with no id; every query cursor ->
  a stateless call.
- **Messages & attachments** (sections 3, 4): message-class hierarchy -> one shape with
  `attachments[]`; `MessageRequestHandler` callbacks -> optimistic send + `message.status`;
  atomic `sendFileMessage` -> the composer's `AttachmentManager` pipeline.
- **Events & real-time** (sections 5, 6): keyed handler objects -> per-event `on()` with retained
  `unsubscribe` in effect cleanup; `MessageCollection` -> `watch()` + reactive `channel.state` +
  events; typing/presence/read per section 6 (delete the hand-rolled timers and polls - golden
  rule 3).

```tsx
useEffect(() => {
  // new GroupChannelHandler({ onMessageReceived }) + addGroupChannelHandler(key, h)
  const { unsubscribe } = client.on('message.new', (event) => {
    if (event.user?.id === client.userID) return; // kill-list #1: ignore own echo
    // ...
  });
  return () => unsubscribe();                     // removeGroupChannelHandler(key)
}, [client]);
```

- **Membership & moderation** (section 8): operators -> moderators/roles + permission grants;
  the mute/ban/block/report semantics per the kill list. End-user actions only - never build a
  review UI ([`RULES.md`](RULES.md) > Moderation is Dashboard-only).
- **Polls, search, push** (sections 9-11) where the app uses them.

When every touchpoint is migrated, finish section 3 step 3: remove the Sendbird packages and
confirm zero `@sendbird` imports remain.

Seeding note: Sendbird apps often self-seed demo data by connecting as several users in turn.
Stream clients act only as themselves - cross-user seeding is server-side (CLI/backend) and gated
by [`../stream/RULES.md`](../stream/RULES.md) > No auto-seeding. Keep only a thin "ensure my own
channels exist" client step if the original had one.

---

## 6. Design parity - the app must look the same

Design fidelity is a deliverable, not a nicety. Sendbird's theming levers (`colorSet` prop,
numeric color ramps, `stringSet`) all die; their Stream replacements:

- **Palette:** re-author `colorSet` values as CSS custom properties in a stylesheet loaded
  **after** the SDK CSS, scoped to `.str-chat`. Alias Stream's *semantic* tokens - the accent is
  `--str-chat__accent-primary` (from the `--str-chat__brand-*` ramp) and the bubbles are
  `--str-chat__chat-bg-outgoing` / `--str-chat__chat-text-outgoing` / `--str-chat__chat-bg-incoming`
  - rather than repeating per-element rules: semantic tokens re-resolve under
  `.str-chat__theme-dark`, so dark mode works without duplicating every rule. **Confirm the exact
  names by grepping the installed `stream-chat-react/dist/css/index.css`, which outranks both this
  file and the Theming docs page** ([`references/docs-map.md`](references/docs-map.md)) - the docs
  page has been observed to print these tokens *without* the `--str-chat__` prefix, and older names
  like `--str-chat__primary-color` no longer exist in v14. App chrome outside `.str-chat` follows [`RULES.md`](RULES.md) > Theme.
- **Mode switching:** the `theme` prop is a class name - map the app's light/dark toggle to
  `str-chat__theme-light` / `str-chat__theme-dark` (kill-list #9).
- **Strings:** `stringSet` overrides -> `Streami18n` re-keyed against Stream's English source
  strings ([`references/sendbird-mapping.md`](references/sendbird-mapping.md) section 14).

Then hand the visual work to [`references/design-matching.md`](references/design-matching.md)
with the **section 0 baseline as the reference design** - the entry point depends on the rung:

- **Rung 1 (live capture):** Steps 1-2 are already done - `.design-verify/design-analysis.md`
  exists with measured values and reference crops. **Resume the pipeline at Step 3 (Route)**; do
  not re-classify or re-analyze, and never re-derive the spec from memory of the original. The
  verify loop then compares computed styles against computed styles, so color and dimension rows
  compare **exactly** (design-matching Step 1 > Live reference) - the sampling tolerances exist
  for anti-aliased pixels, which a measured reference doesn't have.
- **Rung 2 (screenshots):** Pixel tier; run the full pipeline from Step 1.
- **Rung 3 (code-derived):** Lo-fi (structural match) **with one override** - the `colorSet` /
  CSS hexes were read from code, not sampled from a sketch, so include them as exact, measured
  palette rows despite Lo-fi's no-sampling rule.

Its pipeline (Classify -> Design analysis -> Route -> Ground -> Build -> Verify)
owns the capture-and-compare loop - including screenshotting the **migrated** app, which is
mandatory regardless of which baseline rung you had. Do not declare the design matched from code
review; neither real trial run captured a single screenshot, and both shipped unverified skins.

---

## 7. Verify - gates, in order

Run all of these; each catches a failure a real migration shipped.

1. **Types:** `npx tsc --noEmit` - zero errors.
2. **Build:** the project's own build script succeeds.
3. **The bundle actually contains Stream:** check the build output for the SDK (e.g.
   `grep -rlc "str-chat" dist/assets/*.js` or equivalent for the bundler) and sanity-check the
   main chunk grew accordingly. A trial migration shipped a "successful" build whose bundle
   contained **no Stream SDK at all** - a stale artifact that step 2 alone blessed.
4. **Runtime smoke:** boot the app, log in as two users (two tabs), and have the buyer create a
   conversation **before sending its first message**. Assert the seller's channel rail gains it
   live with no page refresh or `queryChannels()` re-fetch. Then send a message each way. Assert:
   it appears exactly **once** for the sender (kill-list #1), arrives live for the receiver, unread
   badges and typing indicators move, and the console shows no errors. Use the in-session browser
   tooling per [`references/design-matching.md`](references/design-matching.md)'s tool ladder; if
   none works, say so and have the user run this check - do not skip it silently.
5. **Design verify loop** (step 6) reaches its exit condition - and closes **against the
   ledger**: every ledger row with a filled Spec-rows cell has a PASS verdict row citing a
   this-round capture of the migrated app compared to its reference crop, **driven states
   included** (the open reaction selector, hover actions, thread, long draft). A visual feature
   whose ledger row says Ported but that has no verdict row is unverified - treat it as FAIL,
   never as done.
6. **Ledger closure:** every parity-ledger row is Ported / Rewritten / N/A / GAP-with-decision.
   A `GAP - provisional` row (section 2, non-interactive default) closes the gate only if the
   final report calls it out explicitly as a decision the user still owes.
7. **Docs match reality:** rewrite README/feature lists against what the migrated app actually
   does, including a "Known gaps vs. the Sendbird original" section from the GAP rows. A trial
   run left the old README advertising features the migration dropped.

| Excuse | Reality |
|---|---|
| "tsc and the build pass, we're done" | A green build proved nothing about the bundle, the connection, or the pixels - gates 3-5 exist because each failed in a real run. |
| "The token wiring is obviously right" | A real run shipped without ever connecting; another was rejected server-side on its first real connect. Gate: section 4. |
| "The CSS was ported, it'll look the same" | Both real runs shipped unverified skins. A match is claimed from a capture, not from CSS diffs. |
| "I screenshotted the original once - baseline done" | A resting full-page shot holds no composer, bubble, or reaction detail - exactly the regions real runs shipped wrong. Rung 1 is element crops + DOM probes + driven states (section 0); that is what step 6 judges against. |
| "That feature was tiny, nobody will miss it" | Silent drops are how READMEs end up advertising ghosts. It's a ledger row: N/A or GAP, decided, in writing. |
| "I'll port it faithfully and refactor later" | The mechanical port of hand-rolled machinery IS the bug (double-adds, stale state, dead timers). Golden rule 3. |
| "The gaps were minor, I decided them myself and kept going" | Minor is the user's judgment, not yours. >= 1 GAP row = the section 2 checkpoint - or, non-interactive, a `provisional` default reported loudly. |

---

## 8. Offer the data migration (never auto-run it)

Everything above migrates the **code**. The app now points at an **empty** Stream app - no users,
channels, or history moved. Once gates 1-7 pass, ask:

> The SDK migration is done and verified. Do you also want to migrate your Sendbird **data**
> (users, channels, message history, reactions) into Stream? There are three approaches:
> **A** hard switch (simplest, needs a maintenance window), **B** uni-directional sync (zero
> downtime, the most common choice), or **C** bi-directional sync (zero downtime, no forced app
> update, Enterprise).

Data migration is server-side and SDK-independent, so it lives in the shared runbook:
[`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md). If the user says
yes, read that file and follow it. If they only wanted the SDK swap, stop here - it touches
production data and may incur attachment-transfer cost
([`../stream/RULES.md`](../stream/RULES.md) > Cross-track follow-ups).
