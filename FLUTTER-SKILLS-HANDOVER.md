# Flutter skills — handover: fidelity-failure investigation & the read-budget root cause

**Date:** 2026-07-22 · **Branch (agent-skills):** `feature/flutter-skills-fine-tuning` — HEAD `17d3bd5`, unpushed; this handover now tracked. **Migration work:** repo `social-aspect`, branch `sendbird_to_stream_v5`.
**Scope:** `skills/stream-flutter/` (`sendbird-migration.md`, `design-matching.md`) · test target: `StudioProjects/social-aspect`

---

## Update — 2026-07-22 (session 4): first sendbird-migration isolation test (social-aspect) — passed + harvested

First isolation test of **`sendbird-migration.md`** (sessions 1–3 exercised design-matching only). Target: **`~/StudioProjects/social-aspect`** — a Sendbird demo covering **both** paths (messenger on **UIKit** group channels + a **core-SDK open-channel** live chat, dark+purple), Sendbird backend **App B `B8CD6147`** (still live/seeded). Protocol = the fixtures' clean neutral prompt: fresh blind `claude` agent, only `/stream-flutter` + Stream creds + "match the current app" + the booted **iPhone 16** sim; **blind** to prior `migrate-to-stream*` branches, the stashed v4 leftover, `sendbird-migration-fixtures`, all HANDOVER/LEDGER/GAPS docs, and my baseline shots. Orchestrator setup: stashed the v4 leftover (`git stash`), branched **`sendbird_to_stream_v5`** off pristine `ed29a5f`, and captured **first-party baseline grading keys** by running the Sendbird source via its `DEMO_LOGIN/DEMO_TAB/DEMO_CHANNEL` flags (tapping still blocked; `simctl` screenshots work) → `scratchpad/social-baseline/` (list · conversation+attachment · live). No Stream secret exposed → client-side seeding only.

**Migration (blind agent):** in-place, committed **`9bab600`** on `sendbird_to_stream_v5`; Sendbird fully removed; `flutter analyze` clean (re-run first-party). Integrity greps: **0** branch/stash/fenced-doc/baseline peeks, **0** sub-agents; skill invoked 21×. **First-party audit** (my shots on iPhone 16, region-by-region vs baseline): channel list **close**, conversation **strong** (author-name-above-bubble matched), live chat **essentially identical** (preserve path; realtime verified). Validated **both** migration strategies in one app (UIKit-shell-rebuild + preserve-custom-widgets).

**Findings → harvest (user-reviewed, landed in `sendbird-migration.md`, commit `17d3bd5`):** (1) §4 **DM single-avatar rendering** — detection ≠ rendering; Stream's channel avatar draws a member cluster, so a migrated non-distinct 1:1 shows a 2-avatar cluster → override to the other member's single avatar for `memberCount<=2`. (2) §3 **channel-list row** — match group member-count + sender-less preview (list-row gaps DO happen, contra "gaps live inside the chat"). (3) §0.5 **composer-parity forcing** — the checklist row now covers the send button (accent tint vs default blue; rest⇄typing presence) + the skipped-pass signature (blue send / filled-circle `+` / outlined field).

**The notable miss: the messenger composer shipped at Stream defaults** (filled-circle `+`, gray-bordered field, persistent **blue** send — corrects my initial "cosmetic/minor" call; a high-touch region). Fixed in-app (commit **`d7de883`** on `sendbird_to_stream_v5`): square-outline `+`, navy no-border field, send hidden-at-rest → **purple** when typing. The `crossAxisAlignment: end` **vertical-alignment trap recurred twice** — I fixed the trailing send, then the user caught the leading `+` still riding low (the exact "fix one slot, forget the other" case the design-matching alignment note warns about) → **both** side slots now field-height+Center (`+` −2px from text center, verified). Good dogfood of that note.

**Assessment (calibrated):** productive — **N=1 for migration**, but 3 real skill improvements + both migration paths validated. The throwaway `social-aspect` app still shows the DM 2-avatar cluster + missing group member-count (**skill-only** harvests, deliberately not in-app-fixed). Baseline grading keys live in tmp (`scratchpad/social-baseline/`) — won't survive a reboot.

**Operational:** agent-skills HEAD **`17d3bd5`** (unpushed): `…7905829` → `6660088` (composer-alignment note) → `17d3bd5` (migration harvest). social-aspect `sendbird_to_stream_v5`: `ed29a5f`(pristine Sendbird) → `9bab600`(migration) → `d7de883`(composer fix); v4 leftover parked in `git stash`; prior `migrate-to-stream*` branches untouched. Memory still live-but-empty; `memory.bak` still parked.

---

## Update — 2026-07-21 (session 3): isolation tests 2 & 3 passed; composer-alignment note landed (commit `6660088`)

Two more isolation tests, run under the session-2 protocol (fresh `claude` agent via the Agent tool; only the `/stream-flutter` ask + a reference screenshot + the credential/constraint brief; no handover, no explorer agents, no leaked fixes; brand-new `flutter create`; **first-party** audit by the orchestrator — own `xcrun simctl io booted screenshot` + Pillow crops at native @3x, region by region). Both were **strong region-by-region passes**, and transcript greps (counts-only, to avoid context overflow) confirmed each honored isolation: **0** handover/postmortem reads, **0** explorer/sub-agent spawns, skill genuinely invoked, fresh app.

**Test 2 — Slack `#random` (light, workplace) → `~/StudioProjects/slack_iso_test`.** Both historically-failing regions matched: composer (`+` outside-left, white pill, "Message #random" placeholder, mic at rest) and **incoming-message metadata placement** (flat row — avatar left, name·🏢·time on ONE line *above*, body below, no bubble). All three test-1 (`7905829`) defects were avoided by a fresh agent (white composer bar; metadata/text overlap; slot-recursion crash) → **regression check PASSED**. Other regions covered: header (`#`+title+"N members • 4 tabs"+sparkle/headphones), link-preview card, reaction pills, thread-reply summary, bottom nav, "Today" divider. One finish nit found on audit — the custom mic rode **~7pt low** — fixed in-app AND traced to a skill gap → **landed the composer-alignment note** (commit `6660088`): the input-**pill** row is `Row(crossAxisAlignment: end)` (SDK-verified at `message_composer_input.dart:69`), same as the outer bar row, so custom leading/trailing/inputLeading/inputTrailing glyphs bottom-anchor; wrap each in a measured-field-height box + `Center` (like the SDK `Default*` slots) and apply to **every** side slot — the agent centered the leading `+` but left the trailing mic a bare box. Read-budget re-verified safe: procedure front half **byte-for-byte unchanged** (51.5KB ≈ ~19k tok, under the ~25k Read cap); the note is +432B, entirely in the grep-accessed `# Reference` half. That channel carries leftover data cruft (the subagent's own verification sends: "Ooops", a voice msg, 2 photos); seeding is idempotent (`_seedMarker`), so curated content is intact — cruft left in place per user.

**Test 3 — Kalshi live-event chat (light, ultra-flat) → `~/StudioProjects/kalshi_iso_test`.** Structurally unlike tests 1–2, and all of it handled: inline **`**username:** text` on ONE line** (vs Slack's name-*above*); continuation lines indent to the name column; **no timestamp / no reactions / no bubbles**; **no sender-run grouping** — username repeats every message (the *inverse* of Slack, and the agent did NOT over-apply the Slack habit); minimal composer (grey pill + a *separate* circular ↑ send, no `+`, no mic); custom header (title + red ● LIVE + grey "Kalshi" wordmark + back + swap/share icons); static NYK/SAS outcome bar + multipliers. The skill correctly routed this to the **headless `stream_chat_flutter_core` / custom-ui path** (first test to exercise it). No skill changes indicated. Nits are data/finish only (photo avatars vs the reference's identicons; swap-arrow spacing; title y a hair low).

**Assessment (calibrated — see the "would you say the skill works well?" exchange).** Three consecutive clean first-party passes across three structurally-distinct references (WhatsApp bubbles → Slack name-above → Kalshi inline `name:`); the read-budget fix + current skill state are holding, and the original failure (truncation → verify loop skipped → laundered "done ✅") did **not** recur. **Do not overclaim.** Caveats: N=3; single auditor (the orchestrator, who also wrote the briefs incl. region enumeration); all runs on **Opus 4.8**; all **light-mode**, single-screen, appearance-at-rest. Untested axes: weaker models (Sonnet/Haiku), **dark mode / semantic-token adaptation** (flagged all 3×), other surfaces (channel list, threads, navigation), and behavior (live updates, edit/quote/slow-mode, gestures). To drop the qualifier: one Sonnet run + one dark-mode reference + ideally an independent auditor.

**Operational deltas since session 2.** Skill changes are now **committed** — HEAD `6660088` on `feature/flutter-skills-fine-tuning`, still **unpushed**; only this handover is untracked. Three throwaway test apps now exist (`acme_chat`=test 1, `slack_iso_test`=test 2 [has data residue + an uncommitted in-app mic fix], `kalshi_iso_test`=test 3) — the next test needs a **fresh `flutter create`**, none of these. Sim automation unchanged (screenshot works; tapping blocked → open the app straight to the target screen). Credentials unchanged (key `4r9zd3yf3qb7`; tokens in `social-aspect/lib/app/stream_tokens.dart`; users alex/sofia/marcus/priya/diego/emma/kenji/nadia/luna). Memory still **live but empty**; `memory.bak` still parked. **Next activity: a sendbird-migration flow** (starting now) — note `sendbird-migration.md` has NOT been exercised by any isolation test yet (all three tested design-matching only).

---

## Update — 2026-07-21 (session 2): split shipped + first isolation test passed

The read-budget fix below is **done**. `design-matching.md` was restructured into a one-Read **procedure** front half (≤55KB, ends at Step 5 — a fresh-agent Read now sees the whole verify loop, empirically confirmed) plus a random-access **`# Reference` back half** consulted per-region by Grep; `sendbird-migration.md` §0.5 was rewritten to the iOS skill's self-sufficient "habits + checklist" shape (fidelity-matrix machinery dropped), and the SDK-default facts were landed version-agnostically (v10, no minor pins). Six commits on `feature/flutter-skills-fine-tuning`, **all local/unpushed** (`347a7ef` split · `80924e7` §0.5 · `8ac6a74` facts · `98744ca` referrers · `08c13e4` Track-M · `7905829` isolation-test hardening). We then ran the **first isolation test**: a fresh `claude` agent, given only the `/stream-flutter` invocation + a WhatsApp "Message yourself" screenshot + credentials (no internal explorer agents, no handover, repo read limited to `skills/`), implemented the screen in a throwaway `flutter create` app (`StudioProjects/acme_chat`, iPhone 16 sim) — a **strong** region-by-region match; the historically-failing composer and metadata regions were much improved and Step 5 actually ran. I audited it **first-party** (my own `xcrun simctl io booted screenshot` + Pillow crops vs the reference at native @3x). Two finish defects surfaced (read-ticks overlapping text; composer bar rendering white) — both fixed in the app **and**, more importantly, traced to skill gaps now corrected + SDK-verified in commit `7905829`: (1) `StreamMessageComposer` paints its OWN bar (`Material(backgroundElevation1)`) so wrapping in a `Container` is not enough — set the token on `StreamTheme`, and re-whiten the pill per-subtree since bar+pill share it; (2) metadata placement is content-kind-aware — `messageContent` overlay works for media but covers TEXT, so text goes INSIDE the bubble via the `messageBubble` slot, and because neither slot sees the message (and `contentKind` conflates album vs text) the decision must be injected from the `messageItem` slot via an `InheritedWidget`; (3) returning the public widget (`StreamMessageItem.fromProps` / `StreamMessageBubble` / `StreamMessageComposerInput`) from its OWN slot stack-overflows — wrap the terminal `Default*` widget instead.

**Operational must-knows for the next test:** (a) **Isolation-test protocol** — spawn a fresh `claude` agent via the Agent tool with the verbatim `/stream-flutter` ask + reference path + the credential/constraint brief; then audit first-party. (b) **Sim automation is half-blocked on this machine** — `xcrun simctl io booted screenshot` WORKS (no perms needed), but `idb`/`cliclick`/AppleScript tapping are blocked (no accessibility/screen-recording grant); to reach a nested chat screen, temporarily add an env-gated `home:` re-route (`--dart-define=AUDIT_CHANNEL=<cid>` → `StreamChannel(channel, child: ChannelPage())`), screenshot, then revert it. (c) **Credentials** — API key `4r9zd3yf3qb7`; no API secret or `getstream` CLI on the machine; pre-minted non-expiring user tokens (`alex`/`sofia`/`marcus`/…) in `social-aspect/lib/app/stream_tokens.dart` (read-only). (d) **`acme_chat` is the finished WhatsApp test app** (fixes uncommitted, throwaway) — the next test needs a **fresh `flutter create`**, not this one. (e) The three `7905829` fixes double as a **regression check**: a fresh agent should now avoid all three by reading the skill. (f) Reference for test 2 is **pending from the user** (workplace/Slack suggested for structural contrast). (g) Session **memory is live but empty** (`…/memory/`); `memory.bak` still parked alongside — restore/merge when testing concludes and record the read-budget + isolation-test lessons.

---

## TL;DR (session 1 — original investigation; the fix it proposed is now DONE, see Update above)

Four fresh-agent migration runs kept failing on the same two regions (composer appearance, message-row
metadata placement) despite escalating skill hardening. Each hardening layer worked — the failure moved
downstream every run — until the last confession exposed the true root cause, which is **mechanical, not
behavioral**:

> **`design-matching.md` is ~119KB ≈ 44k tokens. An agent's Read call caps at ~25k tokens, so every fresh
> agent truncates at ~line 315 of 659 — and the unread half contains the ENTIRE composer section, Step 2.5,
> Step 3 (grounding), Step 4, and Step 5 (the whole verification loop).**

The v4 agent, verbatim: *"I only read lines 1–315 of 660. The file truncated at 315 and I judged I had the
methodology and moved on."*

Corollaries:
- The Swift sibling (`stream-swift/design-matching.md`, 92KB ≈ 23k tokens) **fits in one Read** — a
  mechanical explanation for why "iOS works great" with *lighter* compliance machinery.
- `sendbird-migration.md` (55KB ≈ 14k tokens) is fully readable — which is why its content (the §6
  composer-parity inventory, the §0.5 matrix mandates) demonstrably lands in every run while
  design-matching's back half never does.
- **Principle: agents execute what they read; the file decides what they read.** Content past the
  truncation point is effectively unwritten.

**Proposed fix (agreed in principle, NOT yet executed):** split `design-matching.md` by access pattern —
a one-Read **procedure** file + a random-access **reference map** file. Details in §6.

---

## 1. Evidence timeline — four runs, what each fixed and what each exposed

Skill state per run matters: runs used the working tree via the repo's `.claude/skills -> ../skills`
symlink; agent memory was parked (`memory.bak`) for fresh runs.

| Run | Session / branch | Outcome | Confession / diagnosis |
|---|---|---|---|
| 0 (pre-session) | `sendbird-uikit-sample-flutter` (postmortem) | Composer never matched (D1), metadata layout skipped (D3), self-attested ✅ | See `SENDBIRD-MIGRATION-POSTMORTEM.md`. Fixes (matrix machinery) were drafted into the working tree before this session. |
| 1 | `1dc6ddd5` / `migrate-to-stream` | Enumeration + drives good; 4 regions shipped at Stream default as **"disclosed differences"** + "done ✅" + opt-in offer | Invented `DIFFERS` status; "end-of-session effort triage… I stopped before finishing"; row-3 deferral grounded the WRONG route (searched only chat extensions, never the core factory). When directed: core `messageContent` slot closed it — long-press/reactions survive (device-verified, commits `a075a62` + `87337fe`). |
| 2 | `8426bd10` / `migrate-to-stream-v3` | Textbook matrix (decomposed per-side rows, mechanisms named) — but composer rows **false-`matched`** | "I filled the matrix from memory of the full-screen shots… citing pairs I never cropped or compared. I let 'I touched it' stand in for 'I matched it'. A matrix filled by the same person who took the shortcut, from the same glance, catches nothing." Also: partial metadata (`messageContent`-only; wrote a false "v10.1 limitation" — refuted by run 1's three-slot combo). |
| 3 | `a76450f2` / `migrate-to-stream-v4` | Composer **attempted** (knowledge density worked) but appearance wrong: `+` inverted (filled chip vs outline), **pill left at Stream default chrome** (borderDefault + backgroundElevation1 + radius.xxxl vs source's filled/no-border/compact), all constants eyeballed (34×34, icon 22, radius 10) | **"The file truncated at 315 and I judged I had the methodology"** — never read Step 5 or the composer section of design-matching; verify loop was "ad hoc"; measurement rigor "I shortcut". |

The funnel across runs: silent drop → laundered status → false-matched → executed-but-unmeasured. Every
rung was moved by a fix; the final rung is the read-budget problem.

---

## 2. What is already changed in the working tree (this session)

`skills/stream-flutter/sendbird-migration.md`:
- §3 mapping table, composer row: "not a public component" is **no waiver** — replicate appearance +
  functionality; `StreamMessageComposer` + props/theme/sub-slots first, hand-built on
  `StreamMessageComposerController` only as fallback.
- §0.5 deferral rule: names **metadata re-ordering** as the canonical "custom row = lose sub-features"
  rationalization; "replicate the original's layout/behavior, never Stream's default (unless the user
  explicitly asks)."
- §0.5 new bullet: **message row enters the matrix decomposed per side** (author name · timestamp ·
  read/delivery indicator · avatar · bubble **+ every further element the source row renders** —
  floor-not-list); rows record **position, not presence**; placement rows close on native-scale crop
  pairs; row gestures (swipe-to-reply) are `drive` rows.
- §9 step 2 mirrors: composer **and message row** decomposed before coding.
- §6 new subsection **"Composer parity — inventory the source composer button-by-button"** (ported from
  the Swift skill's pattern): leading `+` shape · remove-what-source-lacks (no mic → `enableVoiceRecording:
  false`) · send-at-rest behavior · placeholder ("Enter message" vs Stream's **"Write a message"** /
  `writeAMessageLabel`) · tint + field container; "inventory L→R and R→L in both states; the crops decide."
- §0.5 composer bullet points to §6.

`skills/stream-flutter/design-matching.md`:
- New **"Metadata placement"** row in the Step-2 message-row table: core `messageContent` slot
  (registered on `StreamComponentBuilders` directly, NOT `extensions:`); receives prebuilt
  `props.header` (pinned/reminder — NOT the author name) / `props.child` / `props.footer`; re-arrangement
  is gesture-safe (device-verified); **the three-slot combo** for name-above + time-beside
  (`messageHeader` ext + `messageFooter` ext + `messageContent`); inline-lambda compile gotcha;
  vendor-neutral wording.
- "Whole message row" big-hammer row de-routed ("metadata placement is not this row's job").

Session-level decisions (do not relitigate):
- **No baked vendor-visual diff tables** (unmaintainable). Facts are stated as *checks* anchored to named
  config keys / theme constants; "the crops decide; the list exists so you know what to crop for."
- **Refutations live at the point of decision** (the table cell / deferral rule), never in preambles.
- **General skills stay vendor-neutral** — Sendbird specifics live in the migration skill only.
- **Six queued compliance edits were consciously SKIPPED** (closed-status/evidence-decides + "NOT done — N
  rows pending" header; both-factories deferral evidence; structural-rows-first; "surfaced" tightening;
  crop-files-as-evidence; grader≠worker fresh-context audit). Direction chosen: stop adding rules, densify
  knowledge, prune on evidence. They remain drafted in the session transcript with two observed failures
  each behind them — revisit only if failures persist AFTER the read-budget fix.

---

## 3. Grounded v10.1 facts (verified via flutter-sdk-explorer against pub-cache; NOT yet landed in the skill)

Pinned: `stream_chat_flutter` 10.1.0, `stream_core_flutter` 0.4.0.

**Composer defaults:** bar = top border + `spacing.md` padding + `Row(crossAxisAlignment: end)`; pill =
`radius.xxxl` + `borderDefault` border + `backgroundElevation1` fill; picker panel slides **below** the
pill. `messageComposerLeading` default = outline `+` (`streamIcons.plus`, secondary/outline/large; rotates
45° while picker open; hidden during voice flow / active command; disabled in slow mode).
`messageComposerTrailing` default = **empty** (`SizedBox.shrink`). `messageComposerInputLeading` = empty.
`messageComposerInputCenter` = bare TextField, `maxHeight: 124`, **no min height**; placeholder =
`writeAMessageLabel` ("Write a message"). `messageComposerInputTrailing` = the **state machine**: recording
locked/stopped → nothing · slow mode → countdown · recording → voice UI · editing/command → checkmark ·
has content → send · else → mic; `voiceRecordingCallback == null` short-circuits to a **persistent,
enabled** send (validator blocks empty sends). `enableVoiceRecording` defaults **`true` on the widget but
`false` on `MessageComposerProps`** (`.fromProps` flips it). `messageComposerInputHeader` = edit banner ▸
quoted-reply ▸ voice chips ▸ attachment chips ▸ link preview; collapses when idle.

**Exports:** `DefaultStreamMessageComposerInput/InputCenter/InputTrailing/Leading` and
`StreamMessageComposerInputField` are barrel-exported and constructible; router widgets
(`StreamMessageComposerInput`, `StreamMessageComposerInputCenter`) are internal. `messageComposerTrailing`
Props **do** carry `onSendPressed` + `voiceRecordingCallback` (no iOS-style closure trap). Mentions +
drafts live on `DefaultStreamMessageComposerState` and watch `props.controller.textFieldController` — a
custom field with its own `TextEditingController` silently kills both; wrapping
`DefaultStreamMessageComposerInputCenter(props: props)` is zero-loss.

**Message row defaults:** footer bundles author name (incoming AND **group** channels only — never DMs,
never outgoing) · ticks (own messages only) · timestamp (always) · edited label; footer renders only on
the **last message of a sender run** (edited always). Header = annotations only (saved/pinned/also-sent/
reminder) — never the author name. Avatar: DMs — gone entirely · outgoing — never · incoming group
non-last — **hidden with space reserved** · last/solo — visible at `md` (32lp). Alignment decided in
`StreamMessageListView.buildMessage` (`isMyMessage → end`).

**Reactions:** counts render only when **some** type's count > 1 — then every chip shows its count (a lone
"1" appears); all-1s → no counts. **Replies summary:** `maxAvatars: 3`, connector shown (suppressed for
jumbomoji), label "N replies", **no last-reply time**. **Channel list:** trailing = last-message timestamp
+ unread badge (`colorScheme.accentPrimary` via `badgeNotificationTheme`).

**Drafted but UNAPPLIED (8 edits, target = the future reference/map file):** composer anatomy block with
the state machine + "Defaults are NOT automatically the target's design" + facts→mistakes bullets;
canonical recipe (trailing-cluster / inputLeading glyph / wrap-DefaultInputCenter / textFieldController
caveat); Default(v10.1) column on the composer table; footer/avatar/reactions/replies row annotations;
Step-1 field-note precision; §6 "inventory names WHAT — design-matching is the HOW (pill chrome, per-part
fill-vs-border sampling, measured sizes)" closing line.

---

## 4. The proposed next step (agreed in principle, taking it slowly)

**Split `design-matching.md` by access pattern:**
1. `design-matching.md` → the linear **procedure**, must fit one Read (~<23k tokens): two axes → Step 1
   (decompose + measure) → Step 4 (build) → **Step 5 (verify)** → per-region pointers into the map.
2. `design-matching-map.md` (new) → the random-access **reference**: Step 2 region→mechanism tables
   (header/chrome · message row · attachments · composer · channel list), theme-token lists, Step 2.5
   composite inventories, Step 3 grounding greps. Consulted per region while implementing.
3. Update referrers (`SKILL.md` styling flag + module map, `sendbird-migration.md` §0.5/§6/§9,
   `custom-ui.md` if it cross-references): "read `design-matching.md` IN FULL (fits one read); look up each
   region in the map while implementing."
4. Land the 8 drafted edits in the map's composer/message-row sections.
5. **Repo-wide size audit**: `wc -c skills/*/*.md skills/*/references/*.md` — flag anything over ~90KB
   (≈ the one-Read ceiling) as having the same silent-truncation problem. `stream-swift/design-matching.md`
   (92KB) is at the line; `sendbird-migration.md` (55KB) has headroom but grew all session.

**Alternative considered (weaker):** keep one file + a top-of-file "longer than one Read — you haven't
read it until line N" contract + move Step 5 forward. Rejected as primary fix: banners are skimmable and
the file keeps growing.

---

## 5. Operational state (as of writing)

- **Agent memory is PARKED**: `~/.claude/projects/-Users-pvelikov-StudioProjects-agent-skills/memory.bak`.
  Restore when testing concludes: `mv …/memory.bak …/memory` (if a fresh `memory/` appeared meanwhile,
  peek before overwriting). On restore, record the read-budget lesson in
  `skill-compliance-forcing-function.md` ("skill files must fit the ~25k-token Read budget; content past
  truncation is effectively unwritten; the Swift/Flutter outcome gap was partly this").
- **Run 3 (v4, session `a76450f2`) may still be live** on `migrate-to-stream-v4` (uncommitted working
  tree in `social-aspect`).
- **All skill changes are uncommitted** on `feature/flutter-skills-fine-tuning`. Recommend committing the
  current state before the split so the split is its own reviewable commit.
- Fidelity matrices + baseline/after screenshots for runs 1–3 live under
  `/private/tmp/claude-501/-Users-pvelikov-StudioProjects-agent-skills/<session>/scratchpad/`
  (sessions `1dc6ddd5…`, `8426bd10…`, `a76450f2…`) — tmp storage, will not survive a reboot; copy anything
  worth keeping.
