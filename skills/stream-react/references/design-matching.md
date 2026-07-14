# Stream React (web) - matching a reference design (screenshot / Figma / "make it look like X")

Run this whenever the request carries a **target appearance** - an attached screenshot, a Figma
frame, a whiteboard sketch, or "make it look like WhatsApp / Slack / Linear / <app>". A reference
design is a **checklist of regions, not a color tweak**: every rail, bar, row, tile, and card is a
thing to reproduce, and most differ from Stream's defaults *structurally*, not just by color.

**The thesis of this whole file:** a match is **claimed only from a rendered screenshot captured
this round and compared against the reference** - never from the code you wrote, never from your
classes, never from eyeballing the running app (however late or careful). "I implemented every region"
is a plan, not a match.

**Implement EVERY region - the composer is first-class.** Do not deliver a partial match with the
rest labelled "known cosmetic gap": a region left at the SDK default is a FAIL, not a footnote. Only
genuine impossibility is a reason to skip, and then you say exactly what and why (see The verify loop
> Exit honestly).

Division of labor - this file owns the *procedure*; it does not restate what it references:
- **Customize-vs-bespoke decision + the per-region completion contract:** [`custom-ui.md`](custom-ui.md).
- **Every URL / page name:** [`docs-map.md`](docs-map.md) - cite row names here, never raw URLs.
- **Non-negotiables** (no backend seeding, docs-first, palette channels, prebuilt-first, work in
  batches): [`../RULES.md`](../RULES.md) and [`../../stream/RULES.md`](../../stream/RULES.md).

**Work in batches** (the loop economics): decompose ALL regions -> ground ALL names -> build ALL
regions -> then **one capture per verify round, never one per tweak**. A full match is many regions;
batching the fixes and capturing once per round is what keeps it fast. The orchestration below
additionally overlaps the batches themselves - analysis alongside setup, workers alongside verify
infrastructure.

The pipeline is six steps - **Classify -> Design analysis -> Route -> Ground -> Build -> Verify
loop** - executed as the orchestration below when the harness can dispatch subagents, and inline
serially when it cannot.

---

## Orchestration (coordinator + subagents)

**Capability gate.** If the harness can dispatch concurrent subagents (a `Task` / Agent tool that
runs several at once), execute this file as the orchestration below - the fan-out trades tokens for
wall-clock, the right trade for a multi-region match. If it cannot, nothing else changes: **each
role's brief runs inline, by you, at its numbered step, in step order.** The numbered pipeline is
the specification; the orchestration only re-schedules it. **No step, gate, tolerance, or exit rule
is weakened - or tightened - by either mode.** (One pragmatic escape: a single-region match may run
one worker + one judge inline even on a capable harness; a multi-region match uses the fan-out.)

**The coordinator is you** - the session that read this file. Every other role is a dispatched
subagent with one goal, briefed from scratch:

| Role | Count | Dispatched | Reads | Writes | Returns |
|---|---|---|---|---|---|
| **Coordinator** | 1 | - (is the session) | everything | shared files only: page wiring, app shell / layout, theme / preset, providers, `package.json`; appends §11-§13 to `design-analysis.md` | the final report + the honest exit claim |
| **Design-analysis** | 1 - always, first | after Step 1, alongside Setup | `.design-verify/reference/*` + its Step 2 brief | `.design-verify/design-analysis.md` only | the filled Step 2 template |
| **Setup** | 0-1 (Track A only) | after the coordinator runs Step 1b + `getstream init`, alongside Design-analysis | SKILL.md Tasks A / A.1 / B / C / D + `sdk.md` | scaffold, `.env.local` (via `getstream env`), SDK installs, `/api/token`, Login Screen | scaffold report: paths created, SDK majors resolved |
| **Feature worker** | 1 per region | after the ownership manifest (Step 3), all in one batch, alongside Verify-infra | `design-analysis.md` (its named sections), its `custom-ui.md` contract rows, its self-fetched docs rows, the Appendix, installed SDK sources | ONLY its manifest-declared paths | report: files written, exports provided, contract rows (Reproduce / N/A / GAP), docs rows fetched verbatim, wiring instructions, blockers |
| **Verify-infra** | 1 | the moment the manifest declares component paths + exports | `design-analysis.md` + its 6a-6c brief | `.design-verify/*`, the fixtures view + fixture data at manifest-declared paths | the live tool-ladder rung, the runner path, the fixtures-view route, the reference-crop paths |
| **Region-judge** | 1 per region, per round | each 6d round, after the round's single capture | its reference crop + rendered crop + probe-JSON slice + its spec rows + the 6d tolerances | nothing | verdict rows for the discrepancy table |

### Role rules

- **Briefs are self-contained.** Subagents share no conversation context: every brief carries the
  file paths, image paths, viewport, tolerances, and section names it needs - nothing "from the
  conversation". The coordination artifact is **`.design-verify/design-analysis.md`**: roles read
  the file, not your memory of it (a long run compacts; the file survives).
- **Exactly one writer per path at a time.** The ownership manifest (Step 3) is the authority; two
  agents writing one path concurrently is the failure mode. The coordinator owns every shared file;
  a worker that needs a shared-file change reports it instead of making it. Two sanctioned handoffs,
  both sequential and declared - never a second concurrent writer: `design-analysis.md` is
  section-partitioned (the design-analysis agent writes §0-§10; the coordinator appends §11-§13 and
  any post-gate gap fills), and a coupled-fix round transfers the affected paths to the coordinator
  (6e).
- **Subagents never talk to the user.** Every stop-and-ask moment - Figma exports (Step 1), the
  mobile-vs-desktop framing decision (Step 1), the Step 1b app pick, a docs fetch that hard-fails, a
  reference image that exists only inline, the opt-in real-data seed (6a), the rung-3 manual compare
  (6b) - surfaces through the coordinator, the only role that can ask.
- **Persist the reference before any dispatch.** Conversation attachments are not visible to
  subagents; Step 1 writes every reference image to `.design-verify/reference/` and every brief
  cites images by path.
- **A blocked subagent reports, never improvises.** Tool availability inside subagents is
  harness-dependent; a role that cannot fetch, install, or capture returns exactly what failed and
  the coordinator escalates. A subagent that substitutes memory for a failed docs fetch has broken
  [`../RULES.md`](../RULES.md) > Docs-first.
- **Dispatch is unverified until proven - gate every return.** Subagent support has three states:
  available, unavailable, and **available-but-broken** (agents that return in seconds with no tool
  calls, echo their prompt back, or write nothing). Accept a return only if **(a)** the role's
  declared output paths exist on disk with plausible content and **(b)** it returned its structured
  report - check both before using anything. An instant / empty / prose-only return is a failed
  dispatch: re-dispatch that role once, then run its brief inline yourself. Every brief states:
  **"the written file is the deliverable; a prose-only reply is a failure."**
- **Never kill a dispatched agent that has shown tool activity or file writes.** Check its declared
  paths before assuming it failed like its siblings - three instant failures say nothing about a
  fourth agent that is actually working, and killing it destroys live progress.
- **Inline fallback is per-role, not all-or-nothing** - and correctness-equivalent (the capability
  gate above). If dispatch proves unreliable in this harness, run the affected briefs inline without
  second-guessing; only the wall-clock changes.
- **Dispatch each stage's agents together in one batch**, not one at a time.

**Never delegated** (decision points and shared-file writes stay with the coordinator): Classify
(tier / viewport / framing), routing + the ownership manifest, the Step 2 completeness gate,
shared-file writes + integration, merging judge verdicts, fix coordination, the 6d completeness
gate, and the honest exit claim.

### The setup track (Track A only)

When the app doesn't exist yet, setup runs concurrently with design analysis - the biggest
wall-clock overlap in the run. The coordinator does the interactive parts itself: the Step 1b app
question (the theme question is already skipped when a reference exists - SKILL.md Step 1b) and
`getstream init` (browser auth + org/app selection-or-creation; in a headless shell `init` emits a
`.stream/init-*.yaml` command file to uncomment instead of prompting - `builder.md` > Provisioning).
It then dispatches the setup agent
with the mechanical remainder, citing SKILL.md by section name - Tasks A, A.1, B, C, D - plus the
`/api/token` route and Login Screen per `sdk.md`. Nothing is restated here; the brief points at
those sections. Track E: the app already exists - no setup agent.

### The schedule

```
Classify (coordinator, Step 1)
  -> [ design-analysis agent (Step 2)  ||  setup: coordinator's interactive part, then setup agent ]
  -> completeness gate (coordinator, Step 2)
  -> Route + ownership manifest (coordinator, Step 3)
  -> [ feature workers, one batch (Steps 4-5)  ||  verify-infra (6a-6c) ]
  -> integrate + tsc seam check (coordinator, Step 5)
  -> verify rounds (Step 6): one capture -> [ region-judges ] -> merge (coordinator)
       -> [ fix briefs to owning workers  ||  coordinator fixes shared / coupled rows ] -> recapture
  -> converged exit + cleanup (coordinator, 6e)
```

---

## Step 1: Classify the reference (coordinator - never delegated)

Before decomposing, classify what you were handed - it sets the match standard and the verify
standard.

| Tier | Input looks like | Match standard | Verify standard |
|---|---|---|---|
| **Pixel** | An app screenshot or a Figma PNG export | Measured: sampled hex values, measured dimensions, exact type | Full verify loop (every spec row measured against a this-round capture) |
| **Lo-fi** | A sketch, wireframe, or whiteboard photo | Structural: the right regions, present, in the right hierarchy | Verify loop checks presence + layout rows only; palette comes from the sanctioned theme channels, never sampled from pencil |
| **Figma link, no exports** | A `figma.com/...` URL with no attached images | **Stop and ask for PNG exports, one per frame** | n/a until you have images |

**Figma links: stop and ask.** You cannot authenticate to Figma and you must never guess a design
from a URL, a file name, or an app's name. Ask for a PNG export per frame, then classify as Pixel.

**The capture requirement is identical for Pixel and Lo-fi** - Step 6 (a browser screenshot taken this
round) is mandatory for both; only *what you measure* differs (Lo-fi drops color / type sampling, never
the capture). Presence and layout are confirmed from the this-round capture and the probe `missing`
flags, never from reading your own markup. **When unsure which tier, treat it as Pixel.**

**Multiple screenshots** = one `design-analysis.md` with a per-screen section each, but **one shared
token table**: the palette and type roles are sampled once and reused across screens (they are one
app). The verify loop then captures and diffs each screen separately.

**Persist the reference now.** Write every reference image to `.design-verify/reference/<screen>.png`
(create `.design-verify/` on first use; the whole directory is deleted at exit, 6e). Subagents see
only files, and the verify loop's reference crops are cut from these paths. If an image exists only
inline and cannot be written out losslessly, stop and ask the user to share it as a file.

**Derive the viewport** (it is a spec field - the loop captures at exactly this size):

| Reference shows | Viewport (CSS px) |
|---|---|
| Portrait ~9:19.5, a status bar / notch | Mobile `390 x 844` |
| ~3:4, no phone chrome | Tablet `820 x 1180` |
| Window chrome, multi-column rails | Desktop `1440 x 900` |
| A known Figma frame | That frame's exact declared size |

**Scale rule:** `scale = reference-image-px-width / viewport-CSS-width`. Divide every dimension you
measure off the image by `scale` before it enters the spec (a 132px avatar on a 3x mobile shot is
44 CSS px). Do not enter raw image pixels as CSS pixels.

**Mobile reference, web deliverable - decide the framing up front.** The reference is almost always a
mobile-app screenshot, but you are shipping a web app - the single highest-leverage decision in these
builds. Settle it with the user before building: either **(a) reproduce the mobile layout at phone
width** (often inside a phone-frame element on the page), or **(b) adapt to the app's desktop-web
layout** (e.g. WhatsApp Web's two-pane shell). Pick per the request; when it is genuinely ambiguous,
ask. If you choose the phone-frame approach, also decide **modal containment**: Stream's fullscreen
image / gallery viewer renders to the document root and will **escape a phone frame** (fill the whole
browser window) unless you scope it - a common web-porting artifact.

---

## Step 2: Design analysis (the design-analysis agent - always dispatched, always first)

The single most important step, and the one that must be done right: convert the reference into a
fine-grained textual specification that every other agent can act on without seeing the
conversation. Dispatch **one design-analysis agent** for all screens (it is the single writer of the
file), briefed with: the image paths under `.design-verify/reference/`, the tier + viewport + scale
+ framing decision from Step 1, and this Step's text. It writes **`.design-verify/design-analysis.md`**
per the template below and returns when every section is filled. (Many-screen escape hatch: for 4+
screens the coordinator MAY fan out one analysis agent per screen returning section *text* - not
file writes - and merge them itself; the default is one agent.)

`design-analysis.md` **is the spec** - "spec row" anywhere in this file means a row of it. Do not
code from an impression and do not hold it in a head that compaction can empty. The spec has two
halves: the **attributes** (what to measure) and the **taxonomy** (naming the Stream concept behind
every visual signal). The taxonomy is where regions get silently dropped, so it is the centerpiece.

### Attributes to record per region

- **Regions / layout:** name every column, bar, rail, tile, and card. A region you do not name is a
  region you will silently drop.
- **Colors - sample, do not guess:** the hex of each sub-part (chrome, list bg, incoming vs outgoing
  bubble, text, muted text, accent, unread badge, presence dot). A "weird line" between two regions is
  usually a **color seam** (two backgrounds meeting), not a divider element. A background may be a
  **texture / gradient / image**, not a flat fill.
- **Type - per text role:** family, size, **weight** (its own axis - match it separately), line
  height, for author / body / timestamp / unread each.
- **Dimensions - measure, do not eyeball:** rail width, avatar size, bubble radius + padding, row
  gap, header height. Read pixels off the image and divide by `scale`; never invent round numbers
  (16 / 24 / 32).
- **Exact text & glyphs (not just layout):** transcribe verbatim the text the design shows - the
  composer **placeholder string** (e.g. `Message`, not the SDK default `Send a message`), button
  labels, empty-state copy - and match the **exact glyph** for each control (a paperclip attach vs a
  `+`, camera, mic) and its **left/right order** in the row. These are the cheapest, highest-visibility
  fidelity wins and, across builds, the most commonly dropped - the composer especially.
- **State + population:** every visible state (incoming + outgoing, reactions, attachments, threads,
  typing, receipts, empty). Each must be reproducible with a local fixture (Step 6).
- **Viewport + scale:** carried from Step 1.

**Measuring the reference (the web's edge over native).** The *rendered* side never needs pixel
sampling - `getComputedStyle` returns exact values in the verify loop - so only the *reference* side
is sampled here. Sample it with `magick` or Python+PIL if present; if neither is available, load the
reference image into a browser (`file://`) and read pixels with a canvas `getImageData` (the
`--sample` mode of the capture script in Step 6). **That same reference pass measures DIMENSIONS,
not just color - do not eyeball glyph and control sizes:** threshold the cropped region (dark glyphs
on a light bar), project the dark mask onto columns, cluster contiguous runs into glyphs, and read
each bounding box in image px, then divide by `scale`. Controls (composer icons, avatars, badges)
almost always measure **smaller** than you would guess - record the measured value, never a round
number. Lo-fi tier: skip sampling entirely, palette comes from the preset / brand.

### Name the Stream concept behind every signal

For every glyph, badge, pill, and label in the image, name the Stream concept it implies and where it
routes. A signal you cannot name is a region you will silently drop; if it truly matches nothing here,
fetch the product index ([`docs-map.md`](docs-map.md)) before declaring it custom chrome. "Routes to"
cites [`custom-ui.md`](custom-ui.md) contract rows and [`docs-map.md`](docs-map.md) page names - no URLs.

**Chat signals:**

| Visual signal in the image | Stream concept | Routes to |
|---|---|---|
| Single / double tick, "seen" | Read + delivery receipts | contract: message row (receipts); docs Channel Read State |
| Emoji pill with a count | Reactions | contract: message row (reactions); docs Reactions Customization |
| "N replies" under a message | Thread reply summary | contract: message row (thread indicator); docs Thread |
| Mini-quote block above a message | Quoted / replied-to parent | contract: message row (quoted parent); docs Message UI |
| Image grid / file card / audio waveform | Attachments | contract: message row (attachments); docs Voice Recording Attachment |
| Stacked same-author bubbles, one avatar | Message grouping | contract: message row (grouping); docs Message UI |
| "(edited)" / "This message was deleted" | Edited / deleted state | contract: message row (edited/deleted); docs Message UI |
| Floating "Today" / date pill | Date separator | docs Message List |
| Bold row + badge in the sidebar | Unread state | contract: channel preview (unread); docs Channel List UI |
| Dot on an avatar | Online presence | contract: channel preview / header (presence); docs Online Status |
| "X is typing..." | Typing indicator | contract: header (typing); docs Typing Indicator |
| Plus / smiley / mic inside the input | Composer attach / emoji / voice | contract: composer; docs Message Composer UI, Audio Recorder |
| Metadata inside vs below the bubble | Structural message row | contract: message row (injection - `MessageUI`); docs Message UI |
| Hover "..." on a message | Message actions menu | contract: message row (actions); docs Message Actions |
| "No chats yet" / "No messages yet" screen, or a loading skeleton | Empty / loading state | custom `EmptyStateIndicator` / `LoadingIndicator`; docs Channel List UI, MessageList |

**Video signals:**

| Visual signal in the image | Stream concept | Routes to |
|---|---|---|
| Equal grid of tiles | `PaginatedGridLayout` | docs Call layout |
| One large tile + a filmstrip | `SpeakerLayout` | docs Call layout |
| Name label on a tile | Participant label | contract: call layout (each participant); docs ParticipantView |
| Mic-slash on a tile | Mute indicator (`hasAudio`) | contract: call layout (mute indicator); docs ParticipantView |
| Colored ring around a tile | Dominant speaker | contract: call layout (dominant speaker); docs Call layout |
| A desktop / window inside a tile | Screenshare | contract: call layout (screenshare); docs ParticipantView |
| Circular buttons along the bottom | Call controls | contract: call controls; docs Call Control Actions |
| Small self-view thumbnail | Local participant | contract: call layout (each participant); docs ParticipantView |
| Signal / reception bars on a tile | Network quality | docs Network Quality Indicator |
| "LIVE" badge + viewer count | Livestream surface | docs Watching a livestream |

**Feeds signals** (Feeds is headless - every feeds region is bespoke, so the contract always applies):

| Visual signal in the image | Stream concept | Routes to |
|---|---|---|
| Avatar + name + time + text card | Activity card | contract: activity card; docs Feeds, Activities |
| Heart + count | Activity reaction + own-state | contract: activity card (reaction); docs Reactions |
| Speech-bubble + count | Comments | contract: activity card (comments) + comment row; docs Comments |
| Two circular arrows + count | Repost | contract: activity card (repost); docs Activities |
| Bookmark flag | Bookmark | contract: activity card (bookmark); docs Bookmarks |
| "Follow" button | Follow graph | docs Follow and Unfollow |
| "What's on your mind" box | Feed composer | contract: feed composer; docs Activities |
| "X and 2 others..." + a bell | Notification feed | contract: activity card (base) + docs Notification Feeds |
| A tab switcher over the feed | Multiple / For You feeds | docs For You Feed |
| Horizontal bars in a post | Poll activity | docs Polls |

### Derived designs - the reference never shows everything

A real app renders states the reference does not define: an empty channel list, an empty message
list, loading, errors, the hover message-actions surface, dialogs. Left unspecified they ship as SDK
defaults - and an unthemed default inside a matched design reads as broken, not neutral. So the
design-analysis agent **designs** them (§7): extrapolate from the §1 global tokens - the same
palette roles, type scale, radius, spacing, and glyph style as the sampled regions - and write each
as concretely as a measured region, so a judge can verdict it like any other row. Keep them quiet
(an empty state is a muted icon + a title + a hint line in token colors, not a new design language).
**The SDK default is never a design.**

### The design-analysis.md template

The agent fills exactly this skeleton. Terseness is a feature - tables over prose; the file is every
other agent's input.

```markdown
# Design analysis - <reference name>
## 0. Reference inventory <!-- per image: path under .design-verify/reference/, tier,
   viewport (CSS px), scale, framing decision - from Step 1 -->
## 1. Global tokens <!-- ONE table for all screens. Palette: sampled hex per role (chrome
   bg, list bg, incoming / outgoing bubble bg + text, muted text,
   accent, unread badge, presence dot). Type: family; per text role
   (author / body / timestamp / unread): size, WEIGHT, line-height.
   Spacing / radius scale; layout grid: rail widths recorded BOTH as
   CSS px AND as a fraction of the viewport (containers are authored
   fluid - Step 5), header height. -->
## 2. Screens <!-- one subsection per screenshot: region list + per-region bounds
   (image-px box - the verify loop cuts reference crops from these) -->
## 3. Chat regions <!-- every subsection MANDATORY: filled, or exactly "N/A - not in reference" -->
### 3.1 MessageBubble <!-- shape (pill / rounded / flat), incoming vs outgoing bg + text
   (sampled hex), radius (measured), sender name / avatar display,
   grouping behavior -->
### 3.2 Message actions <!-- reactions / reply / more-actions: positioning relative to the
   bubble (hover toolbar? beside? below?), reaction pills' position
   relative to the bubble, style -->
### 3.3 Read / Delivered indicators <!-- inside or outside the bubble, glyph style,
   avatar-next-to-receipt or not -->
### 3.4 Message composer <!-- position, style, send-button look, audio recording present?,
   attachment handling, emoji, polls; the placeholder string
   VERBATIM; each control's exact glyph + left/right order;
   ROW COUNT (drives Step 3's composer row-count test);
   input growth: how a 3+ line draft behaves (grow to a max? scroll?) -->
### 3.5 Channel header <!-- what the title area holds: title, participants, channel avatar,
   options / extra controls -->
### 3.6 Channel list / ChannelPreview <!-- row shape: title (member name for 1:1 channels), last
   message, its timestamp, unread treatment, avatar size -->
## 4. Video regions <!-- if present: layout kind, tiles, labels, controls - use the Video
   taxonomy vocabulary above -->
## 5. Feeds regions <!-- if present: cards, reactions, comments - use the Feeds taxonomy
   vocabulary above -->
## 6. Taxonomy <!-- signal -> Stream concept -> routes-to, FILLED for this design:
   every visible glyph, badge, pill, and label has a row -->
## 7. Derived designs <!-- MANDATORY. Every state / surface the app will render that the
   reference does NOT define - empty channel list, empty message list, loading, error,
   the hover message-actions surface, dialogs and menus - gets a DESIGNED spec here,
   extrapolated from the §1 tokens and as concrete as a sampled region (colors, type,
   layout, placement). The SDK default is never a design. -->
## 8. Fixture states <!-- the 6a enumeration this design needs: content states including
   the extreme-width message pair and a long multi-line composer draft, plus every
   driven / open state -->
## 9. Probe-selector seeds <!-- per region: selector + the computed-style props to probe
   (seeds verify-infra's probe list, 6c) -->
## 10. Exact strings & glyphs <!-- every verbatim string and glyph the design shows, beyond the composer -->
<!-- appended by the COORDINATOR as the run progresses: -->
## 11. Routes + mechanisms (Step 3)
## 12. File-ownership manifest (Step 3)
## 13. Running discrepancy table (6d, per round)
```

### The completeness gate (coordinator - never delegated)

Before anything is routed or built, check the returned file:

1. Sections 0-10 all present; every §3 subsection filled or exactly `N/A - not in reference` (a
   missing subsection is a FAIL; an N/A is a decision).
2. Every color is a sampled hex and every dimension is CSS px with the scale shown - no round-number
   guesses, no color names.
3. Viewport + scale stated and consistent with Step 1.
4. Every visible signal in every screen has a §6 taxonomy row, and every §6 row has at least one §9
   probe seed.
5. §8 covers every state §3-§5 and §7 mention - including the extreme-width message pair, the long
   multi-line composer draft, and the driven / open states (6a).
6. The composer section has the verbatim placeholder, the glyph identities + order, the row count,
   and the input-growth behavior.
7. **Every state / surface the app will render has a design** - a reference-anchored row (§3-§5) or
   a §7 derived-design row. Empty channel list, empty message list, loading, and the message-actions
   surface at minimum. The SDK default is never a design.

On any failure: re-dispatch the design-analysis agent ONCE with the named gaps; residual gaps after
that, the coordinator measures and fills itself. Only then proceed to Step 3.

---

## Step 3: Route every region + declare ownership (coordinator)

For each region, name the Stream component, then the cheapest mechanism that reaches the design. The
three axes: **theming** (props + CSS vars, no custom component), **injection** (your own component for
one region -> completion contract), **bespoke** (a headless tree -> completion contract). This table
maps screenshot region -> component + mechanism; [`custom-ui.md`](custom-ui.md)'s table maps a bespoke
region -> its docs page (no duplication). Record the routes in `design-analysis.md` §11.

| Region in the screenshot | Stream component | Cheapest mechanism |
|---|---|---|
| Channel-list rail | `<ChannelList>` + preview | Structural preview -> injection (`ChannelPreviewUI`) -> contract |
| Message row / bubble | `<MessageList>` + row | Almost always structural -> injection (`MessageUI` via `Message=` / `WithComponents`) -> contract |
| Composer / input bar | `<MessageComposer>` | injection (`MessageComposerUI`); **1 row = rearrange, 2+ rows = rebuild as a flex column** -> contract |
| Channel header | `<Channel>` header slot | Injection -> contract; or props only (no contract) |
| Participant tile / call layout | `<StreamCall>` + layout | Prebuilt layout, or injection -> contract |
| Call-controls bar | `CallControls` | Prebuilt, or injection (custom controls) -> contract |
| Feed of cards | `useFeedActivities` + your card | Bespoke -> contract (always) |
| Comment list | `useActivityComments` + your row | Bespoke -> contract (always) |
| Post box | `feed.addActivity` + your form | Bespoke -> contract (always) |
| Colors / fonts / spacing only | any | Theming (preset + `str-chat` vars) - no contract |

Rules:
- **Any region where you render your own component fills its [`custom-ui.md`](custom-ui.md) contract**
  (it inherits every sub-feature the prebuilt drew). A theming-only region skips the contract.
- **Injection over headless.** Keep the prebuilt tree; swap only the regions you must.
- **Feeds has no prebuilt UI: every feeds region is bespoke by definition, so the contract always
  applies** - there is no theming-only escape for any feeds region (card, composer, comment row, or
  notification list).
- **Composer row-count test.** Count the rows in the reference composer (§3.4 records it). Stream's
  `MessageComposer` renders as **one row** (leading buttons | input | trailing buttons); a 1-row
  reference is matched by customizing *within* that row (glyphs, placement, the input pill). A
  **2+ row** composer (an input row with a separate toolbar / actions row below - the Slack / Discord
  shape) cannot come from restyling the one-row default: the injected `MessageComposerUI` must be
  built as a flex **column** (input row + actions row), reusing the SDK's textarea / send / attachment
  pieces. Match row count AND per-row placement, not just the icon set.

### File-ownership manifest

Append to `design-analysis.md` (§12) the ownership table for the whole run - it is the authority
every brief quotes, and it never changes mid-run:

| Region | Worker | Owned paths | Required exports (name + prop signature) |
|---|---|---|---|
| Message row | worker-message | `components/chat/CustomMessage.tsx` | `export function CustomMessage()` - `MessageUI`-compatible |
| ... one row per routed non-theming region ... | | | |

Plus two fixed entries:
- **Coordinator-owned:** pages / app shell / layout, theme + shadcn preset, provider wiring,
  `package.json`, and anything two regions would both need (a shared avatar stack, a
  `resolveChannelName` util) - workers keep helpers inside their owned files until the coordinator
  hoists them at integration.
- **Verify-infra-owned:** `.design-verify/**` - except `reference/` and `design-analysis.md`, which
  the coordinator side wrote before verify-infra exists - plus the fixtures view + fixture data
  paths (declare the exact paths here).

Manifest completion is the dispatch trigger for verify-infra: the declared component paths + export
signatures are what it codes the fixtures view against while the workers build (Step 5).

---

## Step 4: Ground the names (inside each worker)

Docs-first, unchanged in force, relocated in place: **each feature worker grounds its own region**
before writing code. The worker batch-fetches the [`docs-map.md`](docs-map.md) rows its route names
(Step 3 / its `custom-ui.md` contract), confirms the current component / prop / hook names against
the **installed SDK major** (Chat React v14 vs v13 differ) using the runnable installed-export check
in [`custom-ui.md`](custom-ui.md), and reports the grounded names **verbatim, never paraphrased** - a
reworded prop name defeats grounding. The capability list is durable; the names come from the fetch. On fetch failure the worker stops and reports blocked; the
coordinator escalates to the `stream-docs` skill, and if that fails too, stops and asks the user
([`../RULES.md`](../RULES.md) > Docs-first). Never build from memory. The coordinator grounds the one
shared concern itself: the Stream Theming page (variable names for Step 5's palette work).

---

## Step 5: Build, fan-out (feature workers || verify-infra; coordinator integrates)

Dispatch **all feature workers in one batch** - one per manifest row - and **verify-infra alongside
them** (its brief is 6a-6c). Announce the rung-2 Playwright install (6b) yourself at dispatch time
if it may run: subagent output is not shown to the user, so the announcement is the coordinator's.

**Each worker's brief contains:** its manifest row ("you own exactly these paths; create or edit
nothing else; provide exactly these exports - a renamed export is a reported change, never a silent
one"), the `design-analysis.md` sections to read by name (its region's §3/§4/§5 subsection + §1
global tokens + its §7 derived-design rows + its §6 taxonomy rows + §10 strings), its
[`custom-ui.md`](custom-ui.md) contract rows, Step 4 (grounding), and these build rules:

- **Reuse SDK pieces inside your components** (`<MessageText/>`, `<Attachment/>`, `<Avatar/>`,
  `<ParticipantView/>`) rather than rebuilding them.
- **Fluid sizing - no fixed container dimensions.** Your region fills its wrapper (`w-full h-full`)
  and its background paints the full pane - the chat background, the channel-list background,
  everything. A reference-measured container width (a rail, a pane) enters the CSS as a flex-basis /
  percentage / `clamp()` on the wrapper, **never a bare `width: <n>px`**; bare px is only for
  intrinsic details the spec measured (avatar, icon, radius, gap, padding). Full rule:
  [`builder-ui.md`](builder-ui.md) > Layout / sizing.
- **BEM / class names on a docs page are a structural spec, not shippable CSS** - implement with
  Shadcn + Tailwind.
- **Deep-dive into the installed sources when the docs run out:** `node_modules/stream-chat-react`
  (grep `dist/css/index.css` for selectors, the `.d.ts` under `dist/types/` for props) and
  `node_modules/stream-chat` - and start from the **Appendix: Chat React v14 reskin cheat-sheet**
  below for the common chat regions.
- **Fill your contract rows as you go:** every row Reproduce / `N/A - <real design reason>` /
  `GAP - not implemented`, returned in the report.

**The coordinator builds the shared surfaces itself, in parallel with the workers:** the app shell /
page layout per the framing decision, the provider tree (`<Chat>` / `<Channel>`,
`<StreamVideo>` / `<StreamCall>`, `<StreamFeeds>` / `<StreamFeed>` - keep the providers mounted;
injection over headless), and the theme:

### Palette through the sanctioned channels

Match the reference's colors **without** hand-editing `globals.css` (which [`../RULES.md`](../RULES.md)
> Theme forbids):
- **App chrome** (your shell, buttons, sidebar): the **shadcn preset** closest to the sampled palette
  - do not accept a random preset when a screenshot dictates the colors. *(Track E / existing app: the
  preset is already set; match chrome via the app's existing theme system, and if the chrome must
  change color with no theme lever, surface that to the user. The Stream surface is matched
  regardless.)*
- **Stream chat surface** (bubbles, list, composer): Stream's **`str-chat` theming** - the
  `str-chat__theme-light/dark` class, the SDK's documented CSS custom properties, and `<Channel>`
  theming. **Confirm the current variable names on the Theming page** ([`docs-map.md`](docs-map.md)) -
  do not hard-code variable names from memory. A v14 starting map for the common chat regions
  (bubble scoping, poll containment, composer, theme classes) is in the **Appendix: Chat React v14
  reskin cheat-sheet** below - the installed CSS still outranks it.
- **Pinned vs adaptive - the reference is almost always a *light* screenshot.** Sampled **brand /
  content** colors that read identically in both themes (bubble fills, accent, presence dot, unread
  badge) may be pinned literals. But **chrome surfaces** (app shell, channel-list bg, composer bar,
  header) must ride the adaptive channels - the shadcn preset's light/dark tokens, the
  `str-chat__theme-dark` variables, and Tailwind `dark:` - never a hard-coded `#fff`. A surface pinned to
  a sampled light value looks right in light mode and **breaks in dark**. When the app supports dark mode
  this is a verify requirement, not a nicety (Step 6c captures both themes).
- **Lo-fi tier:** palette from the preset / brand, never sampled from a pencil sketch.

### The reference frame wins over the generic shell

Apply [`builder-ui.md`](builder-ui.md) > Reference-design override: **drop chrome the reference does
not show** (a bare phone-chat reference has no app top-bar and no channel-list sidebar) and **fill the
viewport** (no fixed-width chat strip beside empty background). The reference is the shell, not a
widget inside the generic shell. The Stream regions themselves must **grow to fill their container** -
the SDK default can cap the channel list at a fixed ~288px and leave the message list / header not
filling; size via the wrapper (flex + `min-w-0`, a height chain) per [`builder-ui.md`](builder-ui.md) >
Layout / sizing.

### Integration (coordinator)

When the workers return: wire their exports per their wiring instructions into the coordinator-owned
pages / shell (`Message=` / `<WithComponents>` / header slots / preview props), hoist any helper two
regions duplicated, then run `npx tsc --noEmit` as the **seam check**. A seam error in a shared file
is the coordinator's to fix; a seam error inside a worker's file goes back to that worker with the
compiler output. Collect every contract row from the worker reports - they feed the 6d completeness
gate.

---

## Step 6: The verify loop (coordinator-run)

**"Verified" = a screenshot of the rendered app, captured THIS round, compared region-by-region
against the reference, with every spec row measured.** Reading the code, trusting your class names,
trusting a worker's report, or eyeballing the running app (however late or careful) does not count. A
match claimed any other way is not a match; it is a guess that happened to compile.

Roles in this step: **verify-infra** builds everything under 6a-6c (the fixtures, the fixtures view,
the tool ladder, the capture runner) the moment the Step 3 manifest declares the component paths;
**the coordinator** runs the loop itself - triggers each round's single capture, dispatches the
**region-judges** (6d), merges their verdict rows into `design-analysis.md` §13, coordinates the
fixes (6e), and owns the exit.

**Verify-vs-ship, said once:** you verify the populated design through the dev-only fixtures view;
the shipped app starts empty and fills through real use. Both are correct - state this in the final
summary so the user does not read an empty first-run screen as a defect.

### 6a. Populate every state - fixtures by default (verify-infra)

Every state the reference shows must be **visibly present in the capture**. Default to **local
fixtures** (no backend writes - the no-seeding invariant, [`../../stream/RULES.md`](../../stream/RULES.md)
> No auto-seeding, holds). `design-analysis.md` §8 enumerates the states this design needs; the full
menu by product:
- **Chat — content states:** incoming + outgoing, a same-author run (grouping), an attachment, a
  reaction, a quoted reply, long text, **a one-word message and a message whose last line is nearly
  full-width**, a typing event, read receipts, **an empty channel list, an empty message list, and (if
  the design shows one) a loading skeleton**. *(The two extreme-width messages are the check for
  **in-bubble metadata**: if the timestamp + receipts are **overlaid** (`position: absolute`) instead of
  **laid out in flow**, they overlap the text on the wide last line and overflow / half-empty the bubble
  on the one-word message. Lay them out so the bubble sizes to `max(text, metadata)`.)*
- **Chat — interaction / open states (drive them; they do NOT appear at rest):** the hover message
  toolbar (does it shift the bubble? drive it on the **topmost visible message** too — a toolbar
  placed above the bubble clips at the viewport top there), the **thread panel OPEN** — its own
  layout, sidebar vs full-pane, not just the "N replies" entry point — the reaction selector open,
  the message-actions menu open, the composer with a staged attachment, in edit mode, **and with a
  long multi-line draft typed** (does the input keep filling its row and grow in height?), and the
  details / right pane open. Each has a distinct layout and is a common regression site a resting
  capture never reaches.
- **Video:** multiple tiles, a muted participant, a screenshare, a dominant speaker.
- **Feeds:** a card with reactions + comments + an image, long text, a notification entry.

**Render fixtures through the standard flow - never a login-bypassing route.** Mount the real
components against your fixtures in a **dev-only view reached AFTER the normal username login and
sitting inside the real AppShell / providers**, so the real layout, providers, and authenticated state
are exercised. **Guard it with an env flag that is code-checked absent in production** (the view
early-returns / 404s when the flag is unset), so a missed cleanup can never ship a live test surface. A
bare route that skips login renders components in a fake context and passes while production differs -
do not use one.

**Reuse the SHIPPED layout - do not hand-roll a wrapper for the fixtures view.** The fixtures view must
render the *same* layout component the app ships (import the real `AppShell` / shell layout and inject
the fixture channel as the active channel); it must **not** re-create its own `<main>` / column
structure. Layout bugs live in the wrapper geometry (flex direction, which node carries `flex-1`,
`min-width:0`, intermediate `str-chat` nodes) - a hand-rolled fixtures wrapper reproduces *different*
geometry and passes while production is broken. The classic trap: a fixtures wrapper that is a flex
**column** (children stretch to full width automatically) hides a width-collapse that only appears in the
shipped flex **row**. If injecting a fixture channel into the real shell is awkward, that awkwardness is
a signal the shell isn't structured for testability - report it to the coordinator to fix the shell,
don't fork the layout.

**Fixturing the channel list - the one sanctioned deviation.** The conversation pane fixtures
cleanly: inject a fixture channel as the active channel of the real `<Channel>`. The channel-list
rail does not: `<ChannelList>` is **query-driven** - it renders what the backend returns, so it
cannot show fixture rows without seeding (forbidden). Render your `ChannelPreviewUI` component
directly against fixture channel objects **inside the shipped rail geometry** - the same list-column
wrapper the app ships, same widths and flex. The shipped-layout rule is satisfied by reusing the
geometry; only the query is bypassed. Do not relax any other part of the rule for this.

**Opt-in real-data check (coordinator decision, never verify-infra's).** If the user prefers a
real-backend pass over fixtures, seed the states into a **throwaway app provisioned solely for this
check and deleted after** - **not** the app the project connects to (its `.env.local` key), and
**not** any app holding other users' data - with explicit confirmation + tracked teardown, then
capture the actual screen. "Dev" is not "disposable": if the only app available is the project's own,
you may **not** seed it; fall back to fixtures. Fixtures stay the default; when in doubt, use fixtures.

This step is **required**: a claim that a region "would render" / "is wired so it will look right" -
without a this-round capture that actually shows it populated - is not verification, and an unpopulated
fixture is `GAP - not matched`, not an inference.

### 6b. Tool ladder (verify-infra runs it; use the first rung that works; never skip to a lower rung while a higher one works)

A render comes from a browser, not from markup: `curl`-ing the page HTML or reading the served CSS
is **not** a capture (no layout, no computed styles, no fonts resolved). Use the first rung that works
and do not substitute a static read for it.

1. **In-session browser tooling, if present.** Anything that loads a URL at a set viewport,
   screenshots it, and reads computed styles / the DOM. Examples: a Preview MCP
   (`preview_start` / `preview_screenshot` / `preview_inspect` / `preview_resize`) or a connected
   Chrome - *examples of a capability*, use whatever the session exposes. (If such tooling exists
   only in the coordinator's session and not inside subagents, the coordinator runs the captures on
   verify-infra's harness - the rung is about the capability, not about who holds it.) Before
   concluding it is absent, **state which capture tools you checked for**; an unstated "no tooling
   here" is not a reason to descend.
2. **Playwright fallback - mandatory whenever `node` / `npm` are available.** The coordinator
   announces first (published by Microsoft, `microsoft/playwright`; ~120MB of Chromium to the shared
   Playwright cache), then verify-infra **actually runs** it - installed into a **self-contained
   `.design-verify/` harness with its own `package.json`, so the app's `package.json` / lockfile are
   never touched** (Track E may be a yarn / pnpm project - **never add playwright to the app root
   with any manager** - no `npm install`, `pnpm add`, or `yarn add` there; the harness install below
   is npm-only whatever the app uses):
   ```bash
   mkdir -p .design-verify && printf '{"private":true}\n' > .design-verify/package.json
   npm install --prefix .design-verify -D playwright
   .design-verify/node_modules/.bin/playwright install chromium   # add --with-deps on Linux CI
   ```
   Descend to rung 3 **only if that command actually errors** - paste the failure. Predicting "this
   looks sandboxed / offline, it would fail" and skipping the install is **not** permitted; run it and
   observe. Never fake a capture and never claim rung 2 ran when it did not. *(If the project has **no runnable app at all** - nothing to serve -
   that is a prerequisite failure: report UNVERIFIED per 6e and do not install a browser to screenshot
   nothing. Not having **built the fixtures view yet** is not this case - build it, then capture; in a
   design-matching task the app exists by definition, so this rarely applies.)*
3. **Last resort - manual with the user (coordinator only).** Only after rung 1 was checked and rung
   2 was *run and errored* (show both). Give the user the dev-server URL, the viewport, and the spec
   table, and ask them to compare. Until the user confirms, **every region is implemented but
   UNVERIFIED** - say exactly that, and never imply a match you did not see.

### 6c. Capture recipe (verify-infra builds it; one capture per round)

1. Start the dev server in the background (SKILL.md port convention: a random 5-digit port).
2. Log in through the standard Login Screen and open the env-guarded fixtures view (or, on the opt-in
   real-data path, navigate to the seeded screen).
3. Set the **Step 1 viewport** and `deviceScaleFactor: 2`.
4. **Do not wait for `networkidle`** - Stream holds a WebSocket open for the whole session, so the
   network never goes idle and a `networkidle` wait blocks until timeout. Wait for `domcontentloaded`,
   then wait for a rendered Stream selector to actually appear (e.g. `.str-chat__message-list`
   containing at least one message row / `.str-chat__li`), then ~500ms for images / animations to settle.
   Finally **force the scroll position** (`scrollTop = scrollHeight` on the message-list scroll
   container, `.str-chat__message-list-scroll` in v14) - fixture-injected messages fire no events, so
   the SDK's auto-scroll-to-bottom is unreliable and unforced captures land at random offsets
   round-to-round.
5. Produce, per screen: **(a)** a full-screen screenshot; **(b)** **element crops** of the high-detail
   regions (the composer, one message row, one quoted-reply message, one tile / card) - detail is lost
   in a full-page shot;
   **(c)** a **probe pass** that, for each selector in the probe list (seeded from
   `design-analysis.md` §9), returns its `getBoundingClientRect` + the `getComputedStyle` values you
   need and a `missing: true` flag when the selector matches nothing (that flag IS the
   structural-presence check in 6d); **(d)** **reference crops**, cut once from
   `.design-verify/reference/` using the §2 region bounds - each judge gets its region's pair;
   **(e)** optionally, sample the reference image for the color rows (`magick` / PIL, or a canvas
   `getImageData` over a `file://` load).
6. **Then drive and re-capture the interaction / open states (6a).** They don't render at rest, so
   after the resting capture: `hover()` a message row and assert its bubble `getBoundingClientRect`
   is unchanged (a shift means an in-flow hover toolbar — move it out of flow); repeat on the
   **topmost visible message** and assert the opened toolbar / menu rect sits **fully inside the
   viewport** and does not cover the hovered bubble's text; `click()` a "N
   replies" button to open the thread and capture the open panel (sidebar vs full-pane is decided
   here); open the reaction selector, actions menu, and details pane the same way; type a long
   multi-line draft into the composer and probe the input's rect against its 1-line rect (it must
   keep filling its row and grow in height). Each opened state
   is its own screenshot + probe. A capture with zero driven states is incomplete.
7. **If the app supports light/dark, capture BOTH themes.** Toggle the theme the way the app does (the
   `str-chat__theme-dark` class, the app's theme switch, or emulate `prefers-color-scheme` in the capture
   browser) and re-capture. Probe the **chrome surfaces** (app shell, channel-list bg, composer bar,
   header) in each theme: a surface still showing the same **light** hex in dark mode is a FAIL (it should
   have flipped to the adaptive dark token); brand / content colors (bubble fills, accent) should hold
   across both. No rebuild needed - it is one extra capture, not another round.

**Two capture gotchas that waste a round if missed:**
- **Capture with a real Chromium build, not the OS headless binary.** A bare system `chrome --headless`
  frequently screenshots only the app splash / loading state; use Playwright's bundled Chromium (rung 2
  installs it) or launch with `--channel=chrome`.
- **Disable the Next.js dev indicator first** (`devIndicators: false` in `next.config`, or dismiss the
  overlay). It parks in a screen corner and can occlude the composer or a bottom message row in the shot.

With in-session tooling, use its screenshot + computed-style calls directly. With the Playwright
harness, verify-infra writes a small runner **in `.design-verify/`** (its own `package.json` means
CommonJS `require` and ESM both work; use a `.cjs` extension to force CommonJS if you prefer) - the
`npx playwright screenshot` CLI cannot run probes, so a script is needed. **The runner is written
ONCE and re-run every round** (`node .design-verify/<runner>`) - never re-authored per round; the
probe's actual stdout is the artifact cited in 6d. A runner authored but not executed produces no
Rendered values. Probe shape:

```
// probe list: [{ selector: '.str-chat__message-text', props: ['color','font-size','font-weight'] }, ...]
// each probe -> { selector, rect, styles: { ... } }   OR   { selector, missing: true }
```

### 6d. Compare protocol (region-judge fan-out; every check per region, in order)

Each round, after the round's **single** capture:

1. **The coordinator reads the full-screen pair side by side** - reference vs this-round capture.
   Numbers can pass while the screen reads wrong (font fallback, seams, weight, overall balance).
   Name the specific things checked - a bare "reads the same" with nothing named is not a completed
   check. **Loop until the side-by-side reads as the same screen, not just until the numbers match.**
2. **Dispatch one region-judge per region, all in one batch.** Each judge's brief carries: its
   reference crop + rendered crop (6c), its probe-JSON slice, its `design-analysis.md` spec rows, and
   the tolerances below. Judges return **verdict rows only, never edits** - a judge that did not
   write the code has no reason to soften a FAIL. **Never overrule a judge's FAIL without a
   this-round measurement of your own.** Each judge runs, for its region:
   - **Side-by-side crop read** (the check-1 discipline at region scale: seams, font shape, weight,
     alignment).
   - **Computed-style diff**, mapping each spec field explicitly: color -> `color` /
     `background-color`; type -> `font-family` / `font-size` / `font-weight` / `line-height`;
     dimensions -> the rect + `border-radius` / `padding` / `gap`. Tolerances: dimensions within
     `+/-2` CSS px; colors within a small band of the sampled value (about `+/-3` per 8-bit channel,
     to absorb anti-aliasing - a visible hue / shade change is a FAIL), stating both hex values on
     every color row; **`font-family` must resolve to the intended family - a fallback to serif/sans
     is a FAIL, not a rounding error.**
   - **Region-fills-container check (mandatory).** Probe the region's
     `getBoundingClientRect().width`/`height` against its parent's, and the main message list against
     the available viewport (viewport minus any sidebar). A region collapsed to a narrow/default size
     when it should fill - the message list stuck at a "mobile" width, a channel list at the ~288px
     default - is a FAIL, even when every color/type/radius value passes. This is the check that
     catches a sizing bug the eyeball misses when the content happens to be short; it is not
     optional. **Vertical counts too:** the
     message list must fill its pane height and **bottom-anchor** short content (a conversation pins
     to the composer; it must not float at the top with a blank band below), and any wallpaper /
     background must cover the **full pane height** - a background that stops where the messages stop
     is a FAIL even when every width passes. Example probe: emit
     `{ selector, rect, parentWidth, parentHeight }` for `.str-chat__channel`,
     `.str-chat__main-panel(-inner)`, the message list, and the background element, and assert both
     `width >= parentWidth - scrollbar` and `height >= parentHeight - scrollbar`. The composer's
     input is part of this check: it must fill its row width, and its multi-line-draft rect (6c)
     must be taller than its 1-line rect - an unchanged height or a clipped, scrolling single row
     is a FAIL when the reference or its §7 row shows an expanding input. **Resize robustness
     (final round only):** re-capture once at a second viewport width (spec width +25%) and re-run
     just these fills probes - a container authored at a bare fixed px passes at the spec viewport
     and betrays itself here (a pane, list, or background that no longer tracks its parent is a
     FAIL; layout containers are fluid, per Step 5 > Fluid sizing).
   - **Structural presence** via the probe `missing` flags: every taxonomy signal routed to this
     region must exist in the DOM. A `missing:true` is a dropped region.
   - **Default-leak check.** States specced by a §7 derived-design row (empty states, loading, the
     actions surface) are judged against that row like any other. A captured state showing
     recognizably unthemed SDK-default chrome - Stream's stock accent, type, or spacing inside an
     otherwise themed app - is a FAIL against its derived row; "the reference doesn't show it" does
     not exempt it.
3. **The coordinator merges the returned rows** into the discrepancy table (`design-analysis.md`
   §13). Every "Rendered" value is copied from this round's probe output / capture, and the Source
   cell names the file - a row with no Source is UNVERIFIED, not PASS:

| Region | Spec | Rendered (this round) | Source (capture file + probe) | Verdict | Fix |
|---|---|---|---|---|---|
| ... | ... | ... | ... | PASS / FAIL | ... |

4. **Completeness gate (coordinator).** Every signal named in the §6 taxonomy (Step 2) and every row
   of the applicable [`custom-ui.md`](custom-ui.md) contract (collected from the worker reports) must
   have a probe selector, a judge, and a table row. Before exit, diff the probe list against the
   taxonomy - any taxonomy entry with no probe is an unverified region (treat as FAIL), never a
   silent omission. Each high-detail region (composer, one message row, one quoted-reply message,
   one tile / card) must also
   have an element crop cited in its Source cell - a full-page shot alone does not satisfy a
   high-detail row. A short table is an incomplete spec, not an early finish.

### 6e. Iterate and exit honestly (coordinator)

Fix **all** failing rows, **then** recapture **once** (work in batches - not one recapture per row).

**Fix dispatch preserves ownership:** group the failing rows by owning worker (manifest §12) and
dispatch the fix briefs **in parallel, one per owner** - each brief carries its rows with BOTH
measured values (spec vs rendered), the crop paths, and the probe slice. Rows in shared files the
coordinator fixes itself. **Coupled rows spanning two owners** (the oscillation case below - they
must be fixed in one batched edit) transfer to the coordinator for that round: it edits those paths
itself and does not dispatch those workers that round - a declared, sequential handoff, never a
second concurrent writer. Then ONE recapture. **A round is global:** one capture,
all judges, and the coordinator computes the failing set over the merged table - never per-region
loops running on their own clocks.

**Loop until the target is met - every spec row PASS with this-round evidence - not until a fixed round
count expires.** There is no 5-round cap; the termination rule is **convergence, not a counter**. After
each recapture, compute the set of failing rows and require it to **strictly shrink** round over round
(≥1 FAIL flips to PASS and nothing regresses). A monotonically shrinking finite set is guaranteed to
terminate, so full PASS is reachable without an arbitrary ceiling - and a stuck loop ends *sooner* than
a fixed count would, not later. Stop **before** full PASS only when:
- **Plateau** - a round does not shrink the failing set (same rows fail with the same measured values):
  you have spent the fixes you know. A new, specific fix is still progress - take it; otherwise stop.
- **Oscillation** - a fix **regresses** a row that was passing (the set changed but did not shrink). The
  two regions are coupled: fix **both in one batched edit** this round instead of alternating; if they
  keep trading failures, stop and report both.
- **Genuine impossibility** - the SDK / platform cannot express the row at all (see below).
- **Runaway backstop** - a hard ceiling of **8 rounds** (or a token / wall-clock budget set up front)
  exists ONLY to catch a misjudged "still converging". Hitting it is exceptional: flag it, and if you
  were genuinely still converging, hand the remaining rows to the user rather than GAP-ing matchable work.

Exit only when every spec row is **PASS with this-round evidence**: the final claim cites the last
capture. "This round" = the capture taken after the most recent edit to any file affecting the
previewed regions (components, CSS / theme, fixtures, preset) - **whoever made the edit, worker or
coordinator**. *Any* such edit - however small - invalidates the prior capture; if `git status` shows
changes to those paths since the cited capture, it is stale and you re-capture before claiming PASS.

**Dropping the round count RAISES the evidence bar, it does not lower it.** PASS is now the loop's exit
ticket, so the temptation is to *declare* one to get out. Resist it: every PASS still needs this-round
measured evidence in the 6d table; a row you cannot measure to PASS stays FAIL / GAP, never a "close
enough" invented to end the loop.

**If no capture happened this round on any rung** (tooling absent, install failed, app unreachable),
the deliverable says **UNVERIFIED** and lists which regions are implemented-but-unseen. Do not describe
any region as "matched" or "verified" in the delivery when you never rendered it - a note-to-self that
it is unverified does not license a customer-facing "it matches." UNVERIFIED still requires the fixtures
view to be **built** and its states populated - "unseen" means the capture tooling failed, not that you
skipped the fixtures work; an UNVERIFIED deliverable with no fixtures view built is an unfinished task,
not an honest exit.

At any exit short of full PASS - plateau, oscillation, impossibility, or the runaway backstop - report
each unresolved row as **`GAP - not matched`** (the [`custom-ui.md`](custom-ui.md) vocabulary), with
**both measured values** (spec vs rendered) and the honest reason. "Deferred", "minor", "close enough",
and "cosmetic" are banned relabels of a GAP.

**"Genuine impossibility"** (the only reason to drop a row from the PASS target while the loop
continues) means the SDK or platform cannot express it at all - cite the specific limitation, not "hard to fixture", "fiddly", or "low on time". A
region you skip for *any* reason is still a row in the discrepancy table marked `GAP - not matched` with
the reason (impossible regions included), never a prose footnote. Time pressure is never impossibility.

**Cleanup at exit (finally-style - run it even on failure or interruption):** delete the entire
`.design-verify/` directory - the Playwright harness (its `package.json` / `node_modules` included -
nothing landed in the app manifest, so there is no app devDependency to disclose), **and**
`design-analysis.md`, `reference/`, and every capture / crop (the final report in the transcript is
the deliverable; the coordination artifact dies with the run); remove the dev-only fixtures view + its
env flag and confirm it is gone (it is also code-guarded out of production, so a missed cleanup cannot
ship a live surface). If you used the opt-in disposable-app seed, tear down every seeded resource and
verify the deletion.

### 6f. Anti-rationalization

Matching a design under time pressure breeds excuses. The discrepancy table decides, not adjectives.

| Excuse | Reality |
|---|---|
| "It's close enough / basically there" | The table decides with measured values, not an adjective. |
| "I verified it by reading the code" | Code is not a render. Capture this round or it is UNVERIFIED. |
| "The worker's report says it matches" | Reports are claims; captures are evidence. Every PASS needs this-round probe / capture data, whoever wrote the code. |
| "The judge is too strict - I'll overrule it" | Never overrule a judge's FAIL without a this-round measurement of your own. |
| "No subagent tool here, so the gates relax" | The capability gate changes scheduling only: serially, you run every brief inline at its step. Nothing is skipped. |
| "I'll brief the workers from memory instead of the file" | Subagents share no conversation context, and a long run compacts. `design-analysis.md` is the spec; a worker briefed from memory is ungrounded. |
| "There's no browser tooling here" | The ladder has three rungs. Rung 2 (Playwright) installs; rung 3 is labeled UNVERIFIED. |
| "Screenshots are too slow to loop" | The loop is batched: decompose/build all, one capture per round, and it stops when a round stops shrinking the failing set - not one capture per tweak. |
| "No cap now, so I'll loop until it's perfect" | The loop is convergence-gated, not infinite: it ends when a round fails to shrink the failing set (plateau / oscillation) or at the 8-round runaway backstop. Then GAP the rest with measured values - looping past convergence just burns the run. |
| "The computed styles all match" | The side-by-side Read is mandatory every round - numbers miss font fallback, seams, weight. |
| "Colors/type all match, so the region's fine" | Run the region-fills-container check (6d). A region collapsed to a mobile/default width passes every color/type row and is still a FAIL. |
| "I built a quick wrapper for the fixtures view" | Verify in the SHIPPED layout component, not a hand-rolled wrapper. A flex-column stand-in hides a width-collapse that only appears in the shipped flex-row - you verified a different screen than you ship. |
| "I rendered every state in the fixtures" | Rendering isn't driving. Hover/open states (thread panel, hover toolbar, reaction picker, actions menu) only exist after you `hover()`/`click()` - a resting capture misses them (6a/6c). |
| "`next build` passed" | Compiling is not matching. A green build says nothing about the pixels. |
| "The user can just check it" | That is rung 3 only, and only after rungs 1-2 fail - and it ships labeled UNVERIFIED. |
| "I'll curl the HTML / read the served CSS instead" | Static markup is not a render - no layout, no computed styles, no resolved fonts. Use a browser rung (1 or 2). |
| "The font won't install, so I'll note it as minor" | An unresolved row is `GAP - not matched` with both measured values, never "minor". |
| "I'll `pnpm add` / `yarn add` playwright instead" | Any add in the app root corrupts its lockfile. Install only into the `.design-verify/` harness (`npm install --prefix`), whatever the app uses. |
| "I wrote the probe / capture script" | Writing it is not running it. Run it this round; its real stdout is the evidence - an authored-but-unrun script proves nothing. |
| "The reference doesn't show an empty state, so the default is fine" | Every rendered state has a spec row - sampled or derived (§7). An unthemed SDK default inside a matched design is a FAIL against its derived row. |
| "The rail measures 320px in the reference, so `width: 320px` is correct" | The measured value is the *proportion at the spec viewport*, not a CSS literal. Containers are fluid (flex-basis / % / `clamp()`); bare fixed px on a container fails the resize-robustness probe (6d). |

**Red flags - stop:**
- Claiming "matches" without a capture taken **this round**.
- Claiming a region PASS from a worker report, with no capture behind it.
- Overruling a region-judge's FAIL without a this-round measurement of your own.
- Ending with failing rows left unlabeled, or a GAP relabeled "deferred" / "minor" / "cosmetic".
- Skipping the composer or the receipts rows because they are fiddly.
- Downgrading a measured FAIL to a soft word to close the task.

---

## Appendix: Chat React v14 reskin cheat-sheet

Concrete starting points for the most common chat regions, so a reskin isn't reverse-engineered
from compiled CSS every time. Scope: `stream-chat-react` **v14**. The authority order of Step 4
still applies: the installed `node_modules/stream-chat-react/dist/css/index.css` and the `.d.ts`
under `dist/types/` outrank this table and the docs page - grep them to confirm any selector or
variable before relying on it, and every value here still gets measured in the Step 6 loop.

**Global accent + sizing** - set once on `.str-chat` (or your app root):
```css
.str-chat {
  --str-chat__accent-primary: #0084ff;          /* buttons, links, read ticks, poll fills, checkboxes */
  --str-chat__message-max-width: 480px;          /* text bubbles */
  --str-chat__message-with-attachment-max-width: 340px;  /* attachments + POLLS */
  --str-chat__attachment-max-width: 340px;
}
```

**Message bubbles - scope the colour to the TEXT, not the container.** The single most common
mistake: styling `.str-chat__message-bubble` paints the whole message container, so **polls,
images, and other attachments inherit your bubble background/gradient**. Style the text element:
```css
/* ✅ own text bubble only */
.str-chat__message--me .str-chat__message-text-inner { background: <brand>; color: #fff; }
/* ❌ NOT this - bleeds onto polls/attachments */
/* .str-chat__message--me .str-chat__message-bubble { background: <brand>; } */
```

**Poll** (`.str-chat__poll`) - the native Poll is **large and full-width** and renders *inside* a
message bubble. To make it a compact card: constrain via the attachment-width vars above, make the
bubble transparent when it holds a poll, and give the poll its own background:
```css
.str-chat__message-bubble:has(.str-chat__poll) { background: transparent; padding: 0; }
.str-chat__poll { max-width: 300px; border-radius: 18px; padding: 12px 14px; background: <card>; }
.str-chat__message--me .str-chat__poll { background: <brand>; color: #fff; }
```
Sub-parts: `.str-chat__poll-title`, `.str-chat__poll-option`, `.str-chat__poll-option__votes-bar`,
`.str-chat__poll-actions .str-chat__poll-action`. The control *type* (radio selectors) and the
action labels ("End Vote") are **structural, not themable** - if the reference shows something
else, that region routes to injection (`PollOptionSelector` / `PollActions` via `WithComponents`,
Step 3); an unrouted mismatch is a `GAP - not matched` row, never a silent ship.

**Composer** (`<MessageComposer>`):
- Placeholder: `additionalTextareaProps={{ placeholder: 'Enter message' }}` (default is "Send a
  message"). For a full string sweep use a `Streami18n` instance on `<Chat i18nInstance>`.
- Send button `.str-chat__send-button`; attachment button lives under `.str-chat__attachment-selector`.
  The attach button sits on the **left** by default - moving it is a layout override. The attach
  **glyph** swaps without rebuilding the selector: override
  `AttachmentSelectorInitiationButtonContents` (a `ComponentContext` slot, via `WithComponents`).
- Input sizing / rounding: the textarea wrapper is `.str-chat__textarea` (inner element:
  `.str-chat__textarea textarea`); the emoji-picker variant is
  `.str-chat__message-textarea-emoji-picker-container`. (`.str-chat__message-textarea-container`
  does **not** exist in v14.8 - grep the installed CSS.) The SDK textarea **auto-grows**: pass
  `minRows` / `maxRows` to `TextareaComposer` and let the wrapper flex to fill the row - a
  fixed-height input that clips a 3-line draft fails the verify loop's growth probe (6c/6d).
- Rebuilding `MessageComposerUI`? `useMessageComposerContext()` returns
  `{ handleSubmit, onPaste, recordingController, textareaRef }` - submit and voice recording
  (`recordingController`) without re-implementing either; the recorder swap pattern is in the
  [`custom-ui.md`](custom-ui.md) composer contract.

**Read receipts** - `readBy` from `useMessageContext()` is populated **only for the latest-read
message** by default; per-message ticks (WhatsApp-style blue checks on every read row) need
`returnAllReadData` on `<MessageList>` (or derive read state from `channel.state.read`).
Gray-ticks-everywhere-but-one-row is this, not CSS.

**Quoted reply** - renders *inside* the message bubble: `.str-chat__quoted-message-preview`
(`--own` modifier on your side) and `.str-chat__quoted-message-indicator`, with the
`--str-chat__quoted-message-bubble-background-color` variable for its fill. Style it as a compact
inset card (background + left accent bar + truncated text) and verify it with the quoted-reply
fixture + element crop (6c) - it is a repeat offender for stray CSS.

**Wallpaper / message-list background** - v14 scrolls the list inside
`.str-chat__message-list-scroll`; paint the wallpaper there (docs examples still target
`.str-chat__list`) so it covers the full scrollable pane, and remember 6d's full-height background
check - a wallpaper that stops where the messages stop is a FAIL.

**Avatars** - Stream renders a single initial/image. **Stacked group avatars are not built-in** -
render them yourself in your custom channel-preview / header component from `channel.state.members`
(that component then owes its [`custom-ui.md`](custom-ui.md) contract rows as usual).

**Theme (light/dark)** - pass `theme="str-chat__theme-light|dark"` to `<Chat>`; Stream's variables
are scoped under those classes. Keep your own app-chrome tokens on the adaptive channels (Step 5 >
Palette through the sanctioned channels).

**Finding a selector you don't know:** grep the installed stylesheet -
`node_modules/stream-chat-react/dist/css/index.css` - for the feature name (`poll`, `message-bubble`,
`send-button`, `avatar`); it's the authority for the exact installed version. Confirm class props
from the `.d.ts` under `dist/types/`.
