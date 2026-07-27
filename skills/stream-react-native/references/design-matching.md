# Stream React Native - matching a reference design (Chat · Video · Feeds) (screenshot / Figma / "make it look like X")

Run this whenever the request carries a **target appearance** - an attached screenshot, a Figma
frame, a whiteboard sketch, a running Sendbird original, or "make it look like WhatsApp / Telegram /
\<app\>". A reference design is a **checklist of regions, not a color tweak**: every bar, row,
bubble, tile, and card is a thing to reproduce, and most differ from Stream's defaults
*structurally* - the composer button set, where the timestamp and read receipts sit, the bubble
shape, the header, the date separators - not just by color. Changing the bubble color and calling it
done is the classic failure; do not repeat it.

**The thesis of this whole file:** a match is **claimed only from a simulator (or device) capture
taken this round and compared against the reference** - never from the code you wrote, never from a
theme diff, never from eyeballing the running app (however late or careful). "I implemented every
region" is a plan, not a match.

**Implement EVERY region - the composer is first-class.** Do not deliver a partial match with the
rest labelled "known cosmetic gap": a region left at the SDK default is a FAIL, not a footnote. Only
genuine impossibility is a reason to skip, and then you say exactly what and why (Step 4 > Exit
honestly).

**Banned as a resolution:** the strings *"acceptable approximation", "minor", "difference noted",
"close enough", "keep default"*. Each decomposed region ends **Fixed** or **Impossible: \<concrete
reason\>** - nothing in between. (These exact hand-waves shipped ~10 real per-region defects.)

**Screenshots verify appearance, not interaction.** `simctl` can't tap, so a screenshot diff never
exercises press/`onSelect`/navigation. Any custom slot with a tap handler (custom `ChannelPreview`,
message press, buttons) must be verified by *driving* it (temp auto-nav / device), not eyeballed - a
custom `ChannelPreview` that read `onSelect` from props (instead of `useChannelsContext`) silently
no-op'd channel-tap and was invisible to the screenshot loop.

Division of labor - this file owns the *procedure*; it does not restate what it references:
- **Which axis a region routes to, the per-region routing map + deep-dives, and the completion
  contract:** [`custom-ui.md`](custom-ui.md).
- **Every docs page:** the manifest lookup in [`DOCS.md`](DOCS.md) - select pages there, never
  hard-code URLs.
- **The simulator run / screenshot / state-driving loop:** [`SIMULATOR-VERIFICATION.md`](SIMULATOR-VERIFICATION.md).
- **Non-negotiables** (docs-first, no auto-seeding, prebuilt-first, design-matching discipline):
  [`../RULES.md`](../RULES.md).

**Work in batches** (the loop economics): decompose ALL regions -> route ALL regions -> build ALL
regions -> then **one capture per verify round, never one per tweak**. A full match is many regions,
and on RN each round costs a bundle reload (sometimes a native rebuild); batching the fixes and
capturing once per round is what keeps it fast. The orchestration below additionally overlaps the
batches themselves - analysis alongside setup, workers alongside the verify harness.

The pipeline is four steps - **Design analysis -> Route -> Build -> Verify loop** - executed as the
orchestration below when the harness can dispatch subagents, and inline serially when it cannot.

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
| **Coordinator** | 1 | - (is the session) | everything | shared files only: navigation + screens, the `DeepPartial<Theme>` object, `OverlayProvider` / `Chat` / `Channel` wiring and props, `Streami18n` strings, `package.json`; appends §7-§9 to `design-analysis.md` | the final report + the honest exit claim |
| **Design-analysis** | 1 - always, first | at the start, alongside Setup | `.design-verify/reference/*` + its Step 1 brief | `.design-verify/design-analysis.md` only | the filled Step 1 skeleton |
| **Setup** | 0-1 (Track A only) | after the coordinator's interactive part, alongside Design-analysis | [`../builder.md`](../builder.md) sections named in its brief + [`../sdk.md`](../sdk.md) | scaffold, package installs, native config, provider wiring, first screens | scaffold report: paths created, lane, SDK versions resolved |
| **Feature worker** | 1 per region | after the ownership manifest (Step 2), all in one batch, alongside Verify-infra | `design-analysis.md` (its named sections), its [`custom-ui.md`](custom-ui.md) contract rows, its self-fetched [`DOCS.md`](DOCS.md) pages, the installed package source | ONLY its manifest-declared paths | report: files written, exports provided, contract rows (Reproduce / N/A / GAP), grounded names verbatim, wiring instructions, blockers |
| **Verify-infra** | 1 | the moment the manifest declares component paths + exports | `design-analysis.md` + its 4a-4c brief | `.design-verify/*`, the seed script, the temporary nav scaffold at manifest-declared paths | the seeded state inventory, the working capture + crop commands, the device/UDID and lane in use |
| **Region-judge** | 1 per composite screen-area, per round | each 4d round, after the round's single capture | its reference crop + rendered crop + the stacked pair + its spec rows + its contract rows + the 4d tolerances | nothing | verdict rows for the discrepancy table |

### Role rules

- **Briefs are self-contained.** Subagents share no conversation context: every brief carries the
  file paths, image paths, device class, scale, tolerances, and section names it needs - nothing
  "from the conversation". The coordination artifact is **`.design-verify/design-analysis.md`**:
  roles read the file, not your memory of it (a long run compacts; the file survives).
- **Exactly one writer per path at a time.** The ownership manifest (Step 2) is the authority; two
  agents writing one path concurrently is the failure mode - and these subagents *write code*, so a
  collision corrupts a file rather than merely confusing a report (a real run clobbered files
  mid-edit exactly this way). Give each worker **disjoint** files/slots, or isolate it
  (`isolation: 'worktree'`). The coordinator owns every shared file; a worker that needs a
  shared-file change reports it instead of making it. Two sanctioned handoffs, both sequential and
  declared - never a second concurrent writer: `design-analysis.md` is section-partitioned (the
  design-analysis agent writes §0-§6; the coordinator appends §7-§9 and any post-gate gap fills),
  and a coupled-fix round transfers the affected paths to the coordinator (4e).
- **Fan-out is a mechanism, not a mandate to over-delegate.** Don't hand *core implementation* to a
  subagent just to offload effort. Matching a region inline is fine; matching it *from memory at
  wrap-up* is the failure this whole file exists to prevent.
- **Subagents never talk to the user.** Every stop-and-ask moment surfaces through the coordinator,
  the only role that can ask: Figma exports, the thread-scope question, a genuinely ambiguous
  floating-vs-docked composer, the Track A lane/product pick and credentials question, a docs fetch
  that hard-fails, a physical-device check (4b rung 2), and the reference-capture path when the
  original app won't build.
- **Persist the reference before any dispatch.** Conversation attachments are not visible to
  subagents; write every reference image to `.design-verify/reference/` (create the directory on
  first use; the whole directory is deleted at exit, 4e) and cite images by path in every brief. If
  an image exists only inline and cannot be written out losslessly, stop and ask the user to share
  it as a file. **Figma link with no exports: stop and ask for a PNG export per frame** - you cannot
  authenticate to Figma and must never guess a design from a URL or an app's name.
- **A blocked subagent reports, never improvises.** Tool availability inside subagents is
  harness-dependent; a role that cannot fetch, install, build, or capture returns exactly what
  failed and the coordinator escalates. A subagent that substitutes memory for a failed docs fetch
  has broken [`../RULES.md`](../RULES.md) > docs discipline.
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
- **Treat a judge's crop pair as the evidence, never a subagent's words.** Do not relay a region as
  matched when you have not seen its reference↔rendered pair.
- **Inline fallback is per-role, not all-or-nothing** - and correctness-equivalent (the capability
  gate above). If dispatch proves unreliable in this harness, run the affected briefs inline without
  second-guessing; only the wall-clock changes.
- **Dispatch each stage's agents together in one batch**, not one at a time.

**Never delegated** (decision points, user contact, and shared-file writes stay with the
coordinator): routing + the ownership manifest, the Step 1 completeness gate, package installs and
the native build, shared-file writes + integration, merging judge verdicts, fix coordination, the 4d
completeness gate, and the honest exit claim.

### The setup track (Track A only)

When the app doesn't exist yet, setup runs concurrently with design analysis - the biggest
wall-clock overlap in the run. The coordinator does the interactive parts itself: the lane + product
pick ([`../SKILL.md`](../SKILL.md) Step 0 - default to Expo when unspecified) and the single upfront
credentials question ([`../credentials.md`](../credentials.md); it also resolves the token path and
any requested demo data). It then dispatches the setup agent with the mechanical remainder - i.e.
SKILL.md phases **A3-A5** - citing [`../builder.md`](../builder.md) by section name: **2. New app
scaffold**, **4. Install packages**, **5. Configure native/runtime requirements**, **6. Wire shared
setup**, plus the provider/auth patterns in [`../sdk.md`](../sdk.md). Nothing is restated here; the
brief points at those sections. **Track B / Track S: the app already exists - no setup agent**, and
Track S enters this file with its captured original as the reference
([`../sendbird-migration.md`](../sendbird-migration.md) §0.5).

### The schedule

```
Persist the reference + derive device class / scale (coordinator)
  -> [ design-analysis agent (Step 1)  ||  setup: coordinator's interactive part, then setup agent ]
  -> completeness gate (coordinator, Step 1)
  -> native-capability packages installed + native build kicked off (coordinator, Step 2)
  -> Route + Plan column + ownership manifest (coordinator, Step 2)
  -> [ feature workers, one batch (Step 3)  ||  verify-infra (4a-4c) ]
  -> integrate + tsc seam check + native rebuild (coordinator, Step 3)
  -> verify rounds (Step 4): one capture -> [ region-judges ] -> merge (coordinator)
       -> [ fix briefs to owning workers  ||  coordinator fixes shared / coupled rows ] -> recapture
  -> converged exit + cleanup (coordinator, 4e)
```

**Deriving the device class + scale (coordinator, before dispatch).** Mobile screenshots are usually
`@2x`/`@3x` and RN `StyleSheet` values are **logical px**, so the scale is a spec field every other
role depends on: `sips -g pixelWidth -g pixelHeight <reference.png>`, then
`scale = image-px-width / logical-width` (1179 ÷ 393 = 3 → `@3x`). Capture and compare on the **same
device class** as the reference so crops compare 1:1. Record both in `design-analysis.md` §0.

---

## Step 1: Design analysis (the design-analysis agent - always dispatched, always first)

The single most important step, and the one that must be done right: convert the reference into a
fine-grained textual specification that every other agent can act on without seeing the
conversation. Dispatch **one design-analysis agent** for all screens (it is the single writer of the
file), briefed with: the image paths under `.design-verify/reference/`, the device class + scale +
screens in scope, and this Step's text. It writes **`.design-verify/design-analysis.md`** per the
skeleton below and returns when every section is filled. **The written file is the deliverable; a
prose-only reply is a failure.**

`design-analysis.md` **is the spec** - "spec row" anywhere in this file means a row of it. Do not
code from an impression and do not hold it in a head that compaction can empty.

### Decompose the reference into regions (every time)

Go region by region, walking **every row** of the region checklist in
[`custom-ui.md`](custom-ui.md) - it is the authoritative region inventory for Chat, Video, Feeds,
and the cross-cutting concerns. For **each** region: name what the design shows and compare it to
the Stream RN default. Do not skip a region because it "looks standard"; verify it against the
default, and record it either way - a region you do not name is a region you will silently ship at
the SDK default. **Record what the reference shows; do not pick the mechanism here** - routing to
theming / layout / functional happens in Step 2, once the packages are installed and the names can
be confirmed.

**Front-load the thinking - planning is cheap, UI validation is not.** The build -> run -> screenshot
-> compare loop in Step 4 is by far the most expensive part of a design match. Every region you name,
spec, and route now is one you won't rediscover through a costly visual-validation cycle later. Time
spent decomposing thoroughly up front is repaid many times over in iterations you never have to run.

**Capture the spec, not just the identity.** For each region record the concrete attributes you'll
reproduce: bubble corner radius, tail/shape, max width, alignment; avatar shape/size and whether it
shows on own messages; font sizes and **weights** (a name is usually heavier than the body);
paddings and gaps; and the **sampled colors** (bubble fills, accent, ticks, background). "Looks
roughly like it" is the failure mode - a region with the right color but the wrong size or spacing
still fails the eye.

**When the reference is *code-derived* (a migration's palette-only rung), the values are *intended*,
not *verified* — and verification is not optional at any tier.** A colour read from a theme file says
what the source *meant* to paint, not what the SDK actually renders, and a theme file carries **no
layout at all**, so a code-derived spec can seed colours but never structure. Confirm colours against
the running app's render, and treat every structural region as unmatched until an **independent**
reference (the original's real pixels) confirms it — a spec you authored yourself cannot certify
"looks like the original," only "recolored." See
[`../sendbird-migration.md`](../sendbird-migration.md) §0.5.

### Getting sizes right — MEASURE, do not eyeball round numbers

Picking `24`, `28`, `44` by eye is the recurring failure, and it shows most in the composer (wrong
input height, oversized icons, wrong paddings). "Match by proportion" is not enough when an exact
dimension matters. Extract the real numbers off the reference and land them in RN style values:

1. **Find the scale, then work in LOGICAL px.** Mobile screenshots are usually `@2x`/`@3x`, and RN
   `StyleSheet` values are **logical px** (density-independent — the same unit iOS calls points). Get
   the pixel size and divide:
   ```bash
   sips -g pixelWidth -g pixelHeight <reference.png>   # e.g. 1179 x 2556 → ÷3 = 393x852 (@3x)
   ```
   1179 ÷ 393 = 3 → the shot is **@3x**, so **1 logical px = 3 device px**. For every element you
   measure off the image: `logical = pixels / scale`.
2. **Extract element sizes AUTOMATICALLY — don't eye them off the image.** `magick`/Python+PIL/numpy
   are available; threshold the cropped region and read real bounding boxes. Icons are **dark glyphs
   on a light bar** → threshold dark, project onto columns, cluster into glyphs, measure each box. The
   input field is the **wide near-white band** → its row-span is the field height, its white-column
   span is the field width. This script (adapt the crop band + thresholds per design) prints logical
   px directly:
   ```python
   from PIL import Image; import numpy as np
   im = Image.open(REF).convert("RGB"); W,H = im.size; S = 3.0      # @3x → ÷3
   g = np.asarray(im).astype(int).mean(2)
   band = g[H-380:H, :]                                              # bottom = composer
   def run(r,t=248):                                                 # longest near-white run in a row
       b=c=0
       for v in r:
           c=c+1 if v>t else 0; b=max(b,c)
       return b
   wr = np.array([run(g[y]) for y in range(H-380,H)]); ys=np.where(wr>W*.45)[0]+(H-380)
   ft,fb = ys.min(),ys.max(); print("field h", (fb-ft+1)/S)         # logical px
   wc = np.where(g[(ft+fb)//2] > 246)[0]; print("field w", (wc.max()-wc.min())/S)
   dark = (g[ft-6:fb+6,:] < 110); cols=np.where(dark.sum(0)>2)[0]    # icon glyphs
   # cluster contiguous columns (gap>8) → each glyph's w/h in logical px
   ```
   Record each glyph's w/h and the field's h/w. **These exact numbers are your spec.**
3. **Controls are almost always SMALLER than you guess — and often smaller than the SDK default.**
   Measure, then match the measured size; don't fall back to the SDK's default input height or to
   round numbers. Confirm the SDK's actual default dimensions from the **installed package**, not
   memory, then decide whether the reference is smaller.
4. **The field width is the LEFTOVER — oversized buttons steal it.** The input gets
   `total − (leading cluster + trailing cluster + gaps)`. If your buttons are too big the field is too
   narrow. Size buttons to the measured glyph sizes and keep gaps on the theme's spacing scale, and
   the field reclaims its width.
5. **Centering: verify by MEASUREMENT, not eye.** Find each glyph's center-Y and its container's
   center-Y (from the field's white-band row span) and confirm the offset ≈ 0. A consistent offset
   means your button frame height ≠ the field's rendered height (a bottom-sunk or floated control) —
   frame side buttons to the measured field height and center within, rather than hand-tuning
   one-sided padding.
6. **Grow the input pill with PADDING, not a fixed height — or the text stops centering.** the composer input pill
   (`messageComposer.inputBoxWrapper`) lays its content out **top-down** and does **not** vertically
   center the text row. If you make the pill taller with a fixed `minHeight` / `height` on the
   wrapper, the extra height all falls **below** the single line of text, which then hugs the top —
   the classic "I increased the composer size and now the input isn't centered" bug. Size the pill
   from **symmetric vertical padding on the input** instead (`messageComposer.inputBox`
   `paddingTop` == `paddingBottom`): a single line is then centered by construction and it still
   grows for multi-line. Corollary: don't zero the input's own vertical padding and then re-add the
   height via `minHeight` — that guarantees the off-center result.
7. **Message bubble spacing** - it's your task to ensure proper spacing for message bubble should you change anything on it. Measure message bubble inside padding; gap between text - image etc. and apply necessary changes
8. **Land measured numbers in RN theme keys / style values, and reuse the SDK spacing scale** for
   gaps/radius so custom pieces align with un-overridden parts — but tokens are for spacing/radius,
   *not* a license to keep default control/field **sizes**; those come from measurement.

### Weight is its own dimension — measure and match it (separately from color)

Every glyph and text role has a **weight** as well as a size and color, and the eye is sensitive to it
("feels too bold / too thin"). Match it from the reference; don't guess:
- **Different text ROLES usually have different weights — measure each separately.** A sender name, the
  message body, and a timestamp are typically distinct weights (name heavier, body regular/light). The
  recurring miss is treating "text" as one weight.
- **Map the stroke ÷ font-size ratio to an RN `fontWeight` string**: ≈0.05→`'300'`, ≈0.075→`'400'`, ≈0.09→`'500'`, ≈0.11→`'600'`, ≈0.13+→`'700'`.
  Set each role independently in the theme's text keys. Note `'400'` often renders heavier than a
  reference's light body — re-measure your own render and step down if so.
- **Don't conflate color with weight — they are independent.** A glyph that looks "too light" may be a
  wrong base **color** (or a sub-pixel stroke antialiasing to gray), not a too-thin weight; a glyph
  that looks "too bold" has too heavy a weight. Fix the one that's actually wrong.
- **Verify BOTH, by measurement:** the rendered role's **stroke width** ≈ the reference's, AND its
  **dark-core color** ≈ the reference's. Two separate checks.

### Follow EVERY color from the reference — sample it, don't guess (and sample each sub-part)

Invented/guessed colors are a recurring miss. **Sample every color off the reference and apply the
measured value** — background/wallpaper, bubble fills, composer bar, each glyph, borders, **and the
read-receipt ticks**. Don't assume a "known" brand color; only measuring catches the real one.
- **Multi-part elements have more than one color — sample each part separately.** A two-tone control
  (e.g. a gray circle with a white arrow) is easy to invert if you guess; sample the circle and the
  glyph independently.
- **Sampling gotcha:** small colored UI elements get swamped by similar colors in **photo
  attachments** (blue ticks vs. a blue sky/water — the photos can hold 200k blue pixels vs. ~800 tick
  pixels). Isolate the element — restrict the search to its context (e.g. tick pixels sitting on the
  bubble rows, not the photo rows) before averaging — and sample the saturated **core**, not the
  antialiased edges.
- **A background may be a TEXTURE, not a flat color.** Sample **many** points across the background:
  uniform (low std-dev) → flat fill → a color key; varying (faint repeated marks, small std-dev,
  darker mins) → a **pattern** → reproduce it as a tiled background component (don't flatten it — the
  texture is often what separates the chat area from a plain composer). Bundle the actual asset or a
  cropped patch and tile it; if unavailable, approximate a faint motif and tell the user it's an
  approximation.
- **Verify by re-sampling YOUR render and diffing against the reference** — run the same sampling on a
  screenshot of what you built, per sub-part, and compare the measured values; don't eyeball it.

**Light/dark carve-out - don't pin structural surfaces to a light-mode literal.** The reference is
almost always a light screenshot. **Pin** the sampled **brand/content** colors (bubble fills,
glyphs, accent, read-receipt ticks) - they're the same in both modes. But keep **structural
surfaces** (message-list background, composer/input background, borders) on the theme's semantic
values so they still adapt; pinning a surface to `white` looks right in light mode and breaks in
dark. If the app supports dark mode, verify both.


### The `design-analysis.md` skeleton

The agent fills exactly this skeleton, and every later brief cites its sections **by name**.
Terseness is a feature - tables over prose; the file is every other agent's input.

```markdown
# Design analysis - <reference name>
## 0. Reference inventory <!-- per image: path under .design-verify/reference/, what screen it is,
   device class, image px, SCALE, and (for a Live/original-app reference) how it was captured -->
## 1. Global tokens <!-- ONE table for all screens. Palette per role (nav/chrome bg, list bg,
   incoming vs outgoing bubble bg + text, muted text, accent, unread badge, presence dot,
   read-receipt tick, wallpaper): the SAMPLED hex AND the fill type - `flat #hex` /
   `gradient #stop->#stop <dir>` / `texture` - from >=2 sampled points, never one. Type: family;
   per text role (channel title, preview, author, body, timestamp, unread) size, WEIGHT,
   line-height. Spacing + radius scale. All dimensions in LOGICAL px with the scale shown. -->
## 2. Screens <!-- one subsection per screenshot: the region list + per-region bounds in image px
   (the verify loop cuts reference crops from these) -->
## 3. Regions <!-- one row per region, every in-scope region from custom-ui.md's checklist:
   Region | What the reference shows | color | background | border | radius | padding / gap |
   typography (family, weight, size, line-height) | measured dimensions (logical px).
   A region left out here is a region that ships at the SDK default. -->
## 4. States to render <!-- the 4a seed + drive list this design needs: content states (incoming +
   outgoing, a same-author run, an album, a reaction, a quote/reply, a long wrapping message, a
   cross-day separator, 1:1 AND group) and driven states (composer at-rest / typing /
   voice-recording / edit, keyboard up, picker open, long-press menu, reaction picker, thread
   open, dark mode) -->
## 5. Exact strings & glyphs <!-- verbatim copy the design shows (composer placeholder, empty-state
   text, button labels) and each control's exact glyph + left/right order -->
## 6. Derived designs <!-- MANDATORY. Every state the app renders that the reference does NOT show
   - empty channel list, empty message list, loading, error, the long-press menu surface, dialogs
   - gets a DESIGNED spec here, extrapolated from the §1 tokens and as concrete as a sampled
   region. The SDK default is never a design. -->
<!-- appended by the COORDINATOR as the run progresses: -->
## 7. Plan + routes (Step 2)
## 8. File-ownership manifest (Step 2)
## 9. Running discrepancy table (4d, per round)
```

### The completeness gate (coordinator - never delegated)

Before anything is routed or built, check the returned file:

1. Sections 0-6 all present, and every in-scope region from [`custom-ui.md`](custom-ui.md)'s
   checklist has a §3 row - filled, or exactly `N/A - not in reference`. A missing row is a FAIL; an
   N/A is a decision.
2. Every color is a **sampled** hex with a stated fill type backed by **>=2 sampled points** (a lone
   hex for a bubble or a bar is a FAIL - re-sample it; a single sample of a gradient returns its
   midpoint and reads as a plausible flat color, the most common silent miss).
3. Every dimension is **logical px** with the scale shown - no round-number guesses (16 / 24 / 32 /
   44), no color names.
4. Every text role carries its **weight** as well as its size (weight is its own axis).
5. §4 covers the driven states, not just the resting ones - composer typing / voice-recording /
   edit, keyboard up, picker open, reactions, thread, and dark mode if the app supports it.
6. The composer row has the verbatim placeholder, each glyph's identity + order, and the measured
   field height / glyph sizes.
7. §6 exists and covers, at minimum, the empty channel list, the empty message list, loading, and
   the long-press menu surface. The SDK default is never a design.

On any failure: re-dispatch the design-analysis agent ONCE with the named gaps; residual gaps after
that, the coordinator measures and fills them itself. Only then proceed to Step 2.

---

## Step 2: Route every region + declare ownership (coordinator)

**Ordering rule, RN-specific: Step 2 runs only after setup is complete and the packages are
installed.** Routing names concrete SDK mechanisms - a theme key, a `WithComponents` slot, a
`<Channel>` prop - and you cannot confirm any of them against a package that isn't on disk. On Track
A that means waiting for the setup agent; on Tracks B / S the app is already there.

### 2.1 Map design-implied features to optional native packages (then start the native build)

Some regions from Step 1 aren't reachable by theming or a component override alone - they need a
**native capability package** installed first. A screenshot signals a *capability*, not just a look:
voice messages, video attachments, a camera button in the composer, a document/file attachment, a
device photo-library picker, or a share action each imply an optional dependency. If the package
isn't installed you can style the slot perfectly and the region still won't work - the match fails at
the behavior level, not the pixel level.

Walk the §3 region rows and flag every region whose **capability** (not just its appearance) the
design requires, then map it to the package in the **Optional dependency map** in
[CHAT-REACT-NATIVE.md](CHAT-REACT-NATIVE.md#optional-dependency-map). Typical screenshot signals:

- Voice-recording UI / audio waveform, or a voice-message bubble -> voice recording + audio packages
- Inline video / a video thumbnail with a play button -> video playback packages
- A camera button in the composer or a "take photo" affordance -> native image picker / camera
- A photo grid sourced from the device library, or an attachment-picker sheet -> media library packages
- File / document attachment rows -> document picker
- A share affordance on an attachment -> sharing packages

Install only the packages the design actually implies, on the app's runtime lane (RN CLI vs. Expo),
following that map's install and permission notes - do NOT bulk-install the whole matrix for one
vague signal. If a region needs a capability package the app doesn't have, install it (or, if you
can't, flag it) **before** the workers build it in Step 3 - otherwise that region is a `GAP`, not a
match.

**Install them now, and kick off the native build in the background** before you dispatch workers,
so the expensive native build overlaps Step 3 instead of blocking Step 4. A capability package that
lands after the workers have built is a second rebuild you didn't need.

### 2.2 Route every region to the cheapest axis

For each §3 region: name the Stream mechanism, then the cheapest axis that reaches it - **functional**
(props / config / hooks), **theming** (the `Theme` object), **layout** (a `WithComponents` slot or an
app-owned nav header). The per-region routing map - what to check on each region and the exact
mechanism it routes to, with the deep-dives for the composer, in-bubble metadata, the attachment
picker, and the long-press menu - is [`custom-ui.md`](custom-ui.md); walk **every** row there rather
than re-deriving it here. Two rules that decide most rows:

- **Prefer the narrowest mechanism.** A spacing / padding / radius difference is a theme key in RN,
  not a component override. A structural difference (metadata inside the bubble, reactions inside
  the bubble, a bottom-sheet long-press menu, send/mic outside the pill, a floating composer) is
  **never** reachable by a color key - route it to the slot or the `<Channel>` prop.
- **Any region you render yourself owes its [`custom-ui.md`](custom-ui.md) contract rows.** A
  theming-only region skips the contract. Feeds has no prebuilt RN UI, so every Feeds region is
  custom and the contract always applies.

### 2.3 Give `design-analysis.md` a `Plan` column

The §3 region spec captures *what the original looks like*; the `Plan` column commits *how you will
reproduce it in Stream* before you write any UI - one entry per region naming the concrete
mechanism: the theme key (`semantics.chatBgOutgoing`, `channelPreview.unreadContainer`, …), the
`WithComponents` slot (`MessageAuthor`, `ChannelPreviewAvatar`, `MessageContentBottomView`,
`MessageComposerLeadingView`, …), the `<Channel>` prop (`messageInputFloating`,
`audioRecordingEnabled`, …), or a documented hook/config - plus the axis (theming / layout /
functional) and whether it's an SDK default that already matches. Write the result into §7:

| Region | Spec (measured) | Plan (Stream SDK feature) | Axis | Status |
|---|---|---|---|---|
| ... one row per §3 region ... | | | | |

This turns the design match into a resolved build plan - and pre-empts the **reinvention red flag**:
if the Plan is "custom component from scratch", re-check whether an SDK slot already covers it
([`../RULES.md`](../RULES.md) > *reinvention is a red flag*; a real run rebuilt a whole attachment
sheet that `AttachmentPicker` already was). **Confirm each named key / slot / prop against the
installed package before it enters this column** - see 2.4.

### 2.4 Ground the names (before they enter the Plan column)

Docs-first, unchanged in force: the routes name capabilities, the *names* come from the fetch and
the installed package - never from memory.

1. Batch-fetch the [`DOCS.md`](DOCS.md) manifest-selected pages the routes name (theming,
   customization, the specific cookbook page) - one pass, not drip-fed lookups while coding.
2. **Confirm every theme key, slot, prop, and hook against the installed package** for the pinned
   version: `node_modules/stream-chat-react-native-core` (the `Theme` type, the default component
   source), `@stream-io/video-react-native-sdk`, `@stream-io/feeds-react-native-sdk`.
3. **To check whether a symbol is exported, do NOT grep the package's source `index.ts`** - it is an
   `export *` barrel, so the literal name isn't there and you get a false negative. Grep the
   compiled `node_modules/**/lib/typescript/**/*.d.ts`, or write a throwaway
   `import { OutputButtons } from 'stream-chat-expo'` and run `tsc --noEmit`. A real run called a
   region *Impossible* on a grep-based "not exported" and shipped the mic in the wrong place.
4. Record the grounded names **verbatim, never paraphrased** - a reworded prop name defeats
   grounding.

On fetch failure, stop and report blocked; the coordinator escalates to the `stream-docs` skill, and
if that fails too, stops and asks the user ([`../RULES.md`](../RULES.md) > docs discipline). Never
build from memory. Workers re-confirm the names in their own region as they build (Step 3), but the
Plan column must already be grounded.

### 2.5 The decisions only the coordinator can make

Two routing decisions a static reference usually cannot settle. Subagents cannot ask, so they are
resolved here, before the manifest.

**Thread scope decision.** A static screenshot usually does **not** decisively show whether threads
are in scope: the thread-reply indicator only renders on messages that already *have* replies, and
the reply screen + thread inbox are **separate screens** a message-list shot never captures. So
absence of a thread indicator is not evidence threads are unwanted. If the reference doesn't clearly
show threads and the user hasn't stated it, **ask one short question and wait** before building or
dropping them:

> This design doesn't clearly show message threads. Should the app support threads (reply-in-thread + a thread screen), or keep conversations flat?

- **Threads in scope** -> implement the Thread Screen (and the Thread List / inbox if the design
  shows one) as routed in the **Thread surfaces** table in [`custom-ui.md`](custom-ui.md).
- **No threads wanted** -> don't merely omit the UI. **Disable thread replies on the `messaging`
  channel type** so the SDK never surfaces a reply-in-thread affordance the design lacks - see
  [credentials.md > disable threads](../credentials.md#disable-threads). With threads disabled at the
  source, the message-row override doesn't have to reproduce a thread indicator, and the completion contract can
  legitimately mark it `N/A - threads disabled on channel type`.

**Composer placement decision — derive it from the reference, don't lead with a yes/no question.** Whether the composer **floats** (a pill inset from the screen edges with visible side margin, corner radius, often a shadow, message content visible behind/around it) or **docks** (flush with the bottom edge and safe area) is **structural**: it maps to `messageInputFloating` on `<Channel>`, not a theming tweak, and getting it wrong changes the composer's relationship to the keyboard and the list. **Read the floating cues off the image first** (inset margins, rounded corners, shadow, content behind) and decide from them — do **not** open with a bare "floating or docked?" question, because a one-time answer given wrong short-circuits the region analysis and is hard to unwind (you end up faking the look instead of re-deriving it). The cues to read (content visible behind vs. a distinct surface with a seam) are enumerated in [`custom-ui.md`](custom-ui.md) > Composer deep-dive. Only ask if the cues are genuinely ambiguous *after* you've examined them, and re-verify against the image on every build:

> The floating-vs-docked cues in this reference are ambiguous (I can't tell if the input floats inset above the content or docks flush at the bottom). Which is it?

Record both outcomes in §7 as Plan entries (`threads: out of scope - replies:false on the messaging
type`, `composer: floating - messageInputFloating`), so no worker re-litigates them.

### 2.6 File-ownership manifest

Append to `design-analysis.md` (§8) the ownership table for the whole run - it is the authority
every brief quotes, and it never changes mid-run:

| Region | Worker | Owned paths | Required exports (name + prop signature) |
|---|---|---|---|
| Message row | worker-message | `src/chat/CustomMessageContentBottom.tsx` | `export function CustomMessageContentBottom()` - `MessageContentBottomView`-compatible |
| ... one row per routed non-theming region ... | | | |

Plus two fixed entries:

- **Coordinator-owned:** navigation + screens (the app-owned nav header lives here), the
  `DeepPartial<Theme>` object and its light/dark palettes, provider wiring
  (`OverlayProvider` / `Chat` / `Channel` and every structural `<Channel>` prop), `Streami18n`
  strings, `package.json` / native config, and anything two regions would both need (a shared avatar
  component, a `resolveChannelName` util) - workers keep helpers inside their owned files until the
  coordinator hoists them at integration.
- **Verify-infra-owned:** `.design-verify/**` - except `reference/` and `design-analysis.md`, which
  the coordinator side wrote before verify-infra exists - plus the seed script and the temporary
  in-code nav scaffold (declare the exact paths here, because 4e deletes them).

Group regions into workers by **composite screen-area**, not by sub-element: the message row (bubble
+ metadata + reactions + avatar together), the composer (the whole bar), the channel-list row, the
header. Sub-elements of one area are coupled - splitting them across workers puts two agents in one
file and hides positioning bugs between them.

Manifest completion is the dispatch trigger for verify-infra: the declared component paths + export
signatures are what it seeds and scaffolds against while the workers build (Step 3).

---

## Step 3: Build, fan-out (feature workers || verify-infra; coordinator integrates)

Dispatch **all feature workers in one batch** - one per manifest row - and **verify-infra alongside
them** (its brief is 4a-4c). Announce anything user-visible yourself at dispatch time - the native
build, a tooling install such as the Pillow/numpy venv, a device request: subagent output is not
shown to the user, so the announcement is the coordinator's.

**Each worker's brief contains:** its manifest row ("you own exactly these paths; create or edit
nothing else; provide exactly these exports - a renamed export is a reported change, never a silent
one"), the `design-analysis.md` sections to read by name (its §3 region rows + §1 global tokens +
its §6 derived-design rows + §5 strings + its §7 Plan entries), its
[`custom-ui.md`](custom-ui.md) contract rows, Step 2.4 (grounding), and these build rules:

- **Build to the Plan.** Your §7 entry names the mechanism; if it turns out to be wrong, report it -
  don't silently substitute a custom component for a slot the Plan named (or vice versa).
- **Reuse SDK pieces inside your components** (`MessageStatus` for ticks, `OutputButtons` /
  `StartAudioRecordingButton` / `AttachButton` in the composer, `Reply` for quoted parents,
  `MessageFooter`, `EmojiViewerButton`) rather than rebuilding them - and **pass the props the
  default parent injected**, not just the context (the `<MessageFooter date={message.created_at} />`
  trap in [`custom-ui.md`](custom-ui.md)).
- **Reuse the payload's `actionHandlers`** for any menu you build, so each item keeps exact SDK
  behavior - and remember the `editMessage`-from-a-`Modal` exception documented in
  [`custom-ui.md`](custom-ui.md).
- **Land the measured numbers**, in theme keys where a theme key reaches them and in style values
  otherwise. Reuse the SDK spacing / radius scale for gaps so custom pieces align with
  un-overridden parts - but tokens are **not** a license to keep default control and field *sizes*;
  those come from the §3 measurements.
- **Never fake a structure with a background fill.** Resolve the structural mechanism (prop / flag /
  slot) first; cosmetic polish (glass, exact colours) comes after.
- **Deep-dive into the installed source when the docs run out** - the default component you are
  replacing is the specification for what you must reproduce.
- **Fill your contract rows as you go:** every row `Reproduce it` / `N/A - <real design reason>` /
  `GAP - not implemented`, returned in the report.

**The coordinator builds the shared surfaces itself, in parallel with the workers:**

- **The theme object.** Two palettes selected on `useColorScheme()` (from `react-native`) - there is
  no `theme="light|dark"` prop - passed to **both** `<OverlayProvider value={{ style }}>` **and**
  `<Chat style={…}>` (Theming Blueprint in
  [`CHAT-REACT-NATIVE-blueprints.md`](CHAT-REACT-NATIVE-blueprints.md); Video's theme is instead
  global on `<StreamVideo style={…}>`). **Pin** the sampled brand / content colors (bubble fills,
  glyphs, accent, read-receipt ticks) - they are the same in both modes - and keep **structural
  surfaces** (message-list background, composer bar, borders) on semantic values so they still
  adapt. A surface pinned to a light literal looks right in light mode and breaks in dark. When you
  override a brand/accent token, **override every cascading token it feeds** (the recorder and
  waveform tint from `semantics.accentPrimary` / `semantics.chatWaveformBar`) - an un-rendered state
  hides a stray default.
- **The structural `<Channel>` props** the Plan named: `messageInputFloating`, `forceAlignMessages`,
  `messageContentOrder`, `audioRecordingEnabled`, `supportedReactions`, and
  `keyboardVerticalOffset={0} topInset={0}` for a header rendered **inside** `<Channel>` (omitting
  `keyboardVerticalOffset` passes `undefined`, not `0` - it has no SDK default).
- **The app-owned nav header** - RN has no `ChannelHeader` slot; render it **inside** `<Channel>`
  (a sibling header above `<Channel>` can push the composer entirely off-screen) and drive its title
  from channel state, never a literal.
- **Strings** - a `Streami18n` instance on `<Chat i18nInstance={…}>` for the §5 copy; Stream's keys
  are the English source strings themselves.

### Integration (coordinator)

When the workers return: wire their exports per their wiring instructions into the coordinator-owned
screens (`WithComponents overrides`, `ChannelList` `Preview`, `<Channel>` props), hoist any helper
two regions duplicated, then run `npx tsc --noEmit` as the **seam check**, and **rebuild native** if
Step 2.1 added a package. A seam error in a shared file is the coordinator's to fix; a seam error
inside a worker's file goes back to that worker with the compiler output. Collect every contract row
from the worker reports - they feed the 4d completeness gate.

---

## Step 4: The verify loop (coordinator-run)

**"Verified" = a screenshot of the running app, captured THIS round on the simulator or a device,
compared region-by-region against the reference, with every spec row measured.** Reading the code,
trusting your theme diff, trusting a worker's report, or eyeballing the running app (however late or
careful) does not count. A match claimed any other way is not a match; it is a guess that happened
to compile - and a green launch is not a correct screen.

Roles in this step: **verify-infra** builds everything under 4a-4c (the seed data, the simulator
harness, the temporary nav scaffold, the capture + crop recipe) the moment the Step 2 manifest
declares the component paths; **the coordinator** runs the loop itself - triggers each round's
single capture, dispatches the **region-judges** (4d), merges their verdict rows into
`design-analysis.md` §9, coordinates the fixes (4e), and owns the exit.

### 4a. Populate every state - seed the data (verify-infra)

Every state the reference shows must be **visibly present in the capture**. RN has no DOM and no
fixtures view: the states come from **real seeded data**, rendered on the app's real navigation
path. `design-analysis.md` §4 enumerates what this design needs; the floor for a chat match:

- **Content states:** an incoming **and** an outgoing message; a run of **3+ consecutive messages
  from the same author** (grouping + the avatar rule); a **photo album**; a message **with
  reactions**; a **reply / quote**; a **long multi-line** message; enough history for a **date
  separator**; and both a **1:1 and a group** channel (a 1:1 row and header must show the other
  member's single avatar, not a member cluster). Mark messages read if the design shows receipts.
- **Reactions in every channel you will capture, seeded server-side at creation time** - not as an
  afterthought - and **only with types in the app's `supportedReactions`**: the SDK filters
  unsupported types out of `useMessageContext`'s `reactions`, so a reaction seeded as an unsupported
  type silently never renders and the crop then looks like a layout bug. Seed one on an incoming
  **and** an outgoing message.
- **Video:** multiple participants, a muted participant, a screenshare, a dominant speaker.
- **Feeds:** an activity with reactions + comments + an image, long text, a notification entry.

Seeding is **server-side** (the Stream CLI / a backend), per [`../credentials.md`](../credentials.md)
and [`../RULES.md`](../RULES.md) - a client acts only as itself, and nothing is auto-seeded without
the user's ask. **Multi-day date separators can't be fresh-seeded** (the API stamps everything
today): use a channel with real multi-day history or backdated server-side import, otherwise record
the dated separator as implemented-but-unverified rather than claiming a match.

This step is **required**: a claim that a region "would render" - without a this-round capture that
actually shows it populated - is not verification, and an unpopulated state is `GAP - not matched`,
not an inference.

### 4b. Tool ladder (use the first rung that works; never skip to a lower rung while a higher one works)

1. **The simulator / emulator, driven per [`SIMULATOR-VERIFICATION.md`](SIMULATOR-VERIFICATION.md).**
   Boot the device, native-build **once**, then use the fast relaunch loop; reach non-initial screens
   with a **temporary in-code nav scaffold** and drive composer / picker states through SDK hooks
   (`simctl` cannot tap). **Precheck the crop tooling before round 1** - `magick`, or
   `python3 -m venv .designvenv && .designvenv/bin/pip install Pillow numpy`. A tool discovered
   missing mid-verify is the reason a crop gets silently skipped.
2. **A physical device, through the user (coordinator asks).** Only for what the simulator genuinely
   cannot show: Liquid Glass vibrancy, a populated photo library behind the attachment picker, real
   keyboard behavior. For glass specifically, **prove the code path instead** where you can -
   temporarily give the non-glass fallback a loud colour and confirm the element does not take it,
   then remove the probe.
3. **Last resort - manual with the user (coordinator only).** Only after rung 1 was *run and errored*
   (show the failure). Give the user the run command, the device class, and the spec table, and ask
   them to compare. Until they confirm, **every region is implemented but UNVERIFIED** - say exactly
   that, and never imply a match you did not see.

### 4c. Capture recipe (verify-infra builds it; one capture per round)

1. Launch tap-free onto the Metro bundle for the app's lane, and **force a clean relaunch after
   every code change** - a stale bundle is the classic "my fix did nothing" round
   (SIMULATOR-VERIFICATION §1-§2).
1b. **Reach each screen on its real navigation path** - channel list → tap → message screen - not a
   one-channel shortcut that never exercises the header or the navigation layer. The temporary
   in-code scaffold exists to *drive* that path without taps, not to bypass it; anything it adds is
   deleted at 4e and the screen re-verified on the real path.
2. **Wait for the client before you trust a shot** (SIMULATOR-VERIFICATION §5) - a screenshot of a
   still-connecting app is not a capture of your design.
3. Per screen, produce: **(a)** a full-screen `simctl` screenshot; **(b)** **composite full-width
   crops** - a whole message row (incoming *and* outgoing), the whole composer bar (at-rest *and*
   typing), a channel-list row (1:1 *and* group), and the header - screen-edge to screen-edge with
   both margins in frame. **Never crop the sub-element you built**: a crop framed on the reaction
   pills verifies their *contents* and hides their *placement* (a real run cropped reactions in
   isolation, saw "emoji + count" on both sides, and missed that the source renders them **inside**
   the bubble while it had built them below). **(c)** reference crops cut from
   `.design-verify/reference/` using the §2 bounds, at the **same device class and native
   resolution** so no resizing is needed and sizes compare 1:1; **(d)** a **stacked pair** per
   region for the eye:
   ```bash
   magick "$REF"  -crop ${W}x210+0+${refY}  +repage ref.png
   magick "$MINE" -crop ${W}x210+0+${mineY} +repage mine.png
   magick ref.png mine.png -background black -append compare.png
   ```
   **(e)** re-measured dimensions and re-sampled colors off your own render, using the same Step 1
   method (threshold + column projection for glyphs, the white-band span for the input field,
   saturated-core sampling per sub-part) - numbers on both sides, not numbers on one.
4. **Then drive and re-capture the states that don't exist at rest.** Composer **typing**
   (`useMessageComposer().textComposer.setText('hello')` - the send/mic swap), **voice-recording**,
   **edit mode**, the **keyboard actually up** (focus the input; `setText` raises no keyboard, so it
   never exercises `keyboardVerticalOffset` - enable the software keyboard on the sim), the
   **attachment picker open** (open the **Files** tab to dodge the un-dismissable photo-permission
   prompt, and wait for the grid to settle before diagnosing any gap), the **long-press menu**, the
   **reaction picker**, and a **thread open**. Each is its own screenshot + crop. A capture with zero
   driven states is incomplete.
5. **If the app supports dark mode, capture both themes** - flip the OS appearance
   (SIMULATOR-VERIFICATION §6), don't rebuild. Chrome surfaces must flip; pinned brand colors must
   hold. A structural surface still showing its light hex in dark mode is a FAIL.

**Before you compare anything: is every mandatory region actually on screen?** A chat screen with no
visible composer (or a clipped header / message list) is a **layout bug to fix**, not something to
verify around - almost always the header-rendered-as-a-sibling-above-`<Channel>` trap. First glance
at any chat-screen shot: *is the composer even there?*

### 4d. Compare protocol (region-judge fan-out; every check per region, in order)

Each round, after the round's **single** capture:

1. **The coordinator reads the full-screen pair side by side** - reference vs this-round capture.
   Numbers can pass while the screen reads wrong (font fallback, weight, seams, overall balance).
   Name the specific things checked - a bare "reads the same" with nothing named is not a completed
   check. **Loop until the side-by-side reads as the same screen, not just until the numbers match.**
2. **Dispatch one region-judge per composite screen-area, all in one batch.** Each judge's brief
   carries: its reference crop + rendered crop + the stacked pair (4c), its `design-analysis.md` §3
   rows + §1 tokens + §6 derived rows, its [`custom-ui.md`](custom-ui.md) contract rows, and the
   tolerances below. Judges return **verdict rows only, never edits** - a judge that did not write
   the code has no reason to soften a FAIL. **Never overrule a judge's FAIL without a this-round
   measurement of your own.** Each judge runs, for its area:
   - **The stacked side-by-side read.** Name the **fill type** ("flat or gradient? shadowed?"), the
     **stroke weight**, the field height / compactness, and the vertical centering of each control -
     not "looks the same"; a subtle gradient and a half-step of font weight both survive "looks the
     same".
   - **The placement question, answered explicitly before any PASS** - reactions *inside vs below*
     the bubble · send/mic *inside vs outside* the pill · metadata *inside / beside / below* ·
     avatar *silhouette vs initials* · attach *circle vs square, bordered vs borderless* · composer
     *floating vs docked* · the picker bar *flush vs floating capsule*. This is the class of miss
     that every colour and size row passes.
   - **Measured dimensions** - within **±2 logical px** of the spec, measured off the crop the same
     way §3 measured the reference, never eyeballed.
   - **Sampled colors, per sub-part** - state both hex values on every color row; a two-tone control
     is two rows. Isolate small elements from photo attachments before averaging, and sample the
     saturated core, not the antialiased edge. A visible hue / shade change is a FAIL.
   - **Structural presence** - every region routed to this area exists in the frame. A missing
     region is a dropped region, not a pass.
   - **Default-leak check** - a state specced by a §6 derived-design row is judged against that row
     like any other. Recognizably unthemed SDK chrome (Stream's stock accent, type, or spacing)
     inside an otherwise matched app is a FAIL; "the reference doesn't show it" does not exempt it.
3. **The coordinator merges the returned rows** into the discrepancy table
   (`design-analysis.md` §9). Every "Rendered" value is copied from this round's capture /
   measurement, and the Source cell names the crop file - a row with no Source is UNVERIFIED, not
   PASS:

| Region | Spec | Rendered (this round) | Source (capture + crop paths) | Verdict | Fix |
|---|---|---|---|---|---|
| ... | ... | ... | ... | PASS / FAIL | ... |

4. **Completeness gate (coordinator).** Every §3 region row and every applicable
   [`custom-ui.md`](custom-ui.md) contract row (collected from the worker reports) must have a
   judge and a table row. A region you specced and never built is a **FAIL**, not done - cross-check
   §3 against the built result explicitly (a real run specced a header avatar and an add-reaction
   button, never built them, and no gate caught it). A short table is an incomplete spec, not an
   early finish.
5. **Re-check the silently-lost regions explicitly, every round** - they pass a glance and fail a
   crop: the **incoming-message avatar** and **grouping**; the **nav header** (height, title, back
   affordance); the **composer in every state** (walk the full *composer verification gate* in
   [`custom-ui.md`](custom-ui.md), including that the composer background fills **edge-to-edge and
   through the bottom safe area** - sample the margin *around* the controls, not just the controls;
   a colour band hugging the buttons means `container` was styled instead of `wrapper`);
   **metadata placement** (inside the bubble, not clipped, the default footer not duplicated);
   **reaction placement** (in-bubble vs outside); and **attachment rendering**.
6. **The interaction gate - screenshots don't test interaction.** A screen that paints can still be
   behaviorally dead, and `simctl` never exercises a press. **Drive every interaction the design
   implies and confirm its observed effect:** send text · send an attachment through the picker ·
   **reply** → quote preview → send → the quoted message renders · **edit** → composer prefills →
   save → edited state shows · **long-press** → actions menu · **react** from the picker · open a
   **thread** and reply · channel-row **tap** and long-press · **back-nav** (chat → list, thread →
   chat). A rendered-but-inert affordance is a FAIL. Fire each handler rather than assuming "reused
   SDK handler ⇒ correct" - `editMessage` from inside a `Modal` is the documented counter-example.

### 4e. Iterate and exit honestly (coordinator)

Fix **all** failing rows, **then** recapture **once** (work in batches - not one recapture per row).

**Fix dispatch preserves ownership:** group the failing rows by owning worker (manifest §8) and
dispatch the fix briefs **in parallel, one per owner** - each brief carries its rows with BOTH
measured values (spec vs rendered), the crop paths, and the placement answer that failed. Rows in
shared files the coordinator fixes itself. **Coupled rows spanning two owners** (the oscillation case
below) transfer to the coordinator for that round: it edits those paths itself and does not dispatch
those workers that round - a declared, sequential handoff, never a second concurrent writer. Then ONE
recapture. **A round is global:** one capture, all judges, and the coordinator computes the failing
set over the merged table - never per-region loops running on their own clocks.

**After fixing any one facet of a region, re-verify the OTHER facets of that same region** -
[`../RULES.md`](../RULES.md) > regression adjacency. Fixes routinely break a neighbour (picker →
attach-button look → toggle behaviour).

**Loop until the target is met - every spec row PASS with this-round evidence - not until a fixed
round count expires.** After each recapture, compute the set of failing rows and require it to
**strictly shrink** round over round (≥1 FAIL flips to PASS and nothing regresses). Stop **before**
full PASS only when:

- **Plateau** - a round does not shrink the failing set (same rows fail with the same measured
  values). A new, specific fix is still progress - take it; otherwise stop.
- **Oscillation** - a fix **regresses** a row that was passing. The two regions are coupled: fix
  **both in one batched edit** this round instead of alternating; if they keep trading failures,
  stop and report both.
- **Genuine impossibility** - the SDK or platform cannot express the row at all, **proven by
  attempting it** (resolve the symbol against the `.d.ts`, try the prop), never asserted from a grep
  or a guess. Cite the specific limitation. Time pressure is never impossibility.
- **Runaway backstop** - a hard ceiling of **8 rounds** (or a token / wall-clock budget set up
  front) exists ONLY to catch a misjudged "still converging". Hitting it is exceptional: flag it,
  and hand the remaining rows to the user rather than GAP-ing matchable work.

Exit only when every spec row is **PASS with this-round evidence**: the final claim cites the last
capture. "This round" = the capture taken after the most recent edit to any file affecting the
captured screens - **whoever made the edit, worker or coordinator**. *Any* such edit invalidates the
prior capture; if `git status` shows changes to those paths since the cited capture, it is stale and
you re-capture (with a clean relaunch) before claiming PASS.

**If no capture happened this round on any rung** (no simulator, the build fails, the app won't
boot), the deliverable says **UNVERIFIED** and lists which regions are implemented-but-unseen. Do
not describe any region as "matched" in the delivery when you never rendered it.

At any exit short of full PASS - plateau, oscillation, impossibility, or the runaway backstop -
report each unresolved row as **`GAP - not matched`** with **both measured values** and the honest
reason. "Deferred", "minor", "close enough", "cosmetic", "residual", "polish", and "nice-to-have"
are banned relabels of a GAP.

**Cleanup at exit (finally-style - run it even on failure or interruption):** delete
`.design-verify/` (reference images, crops, captures) and `design-analysis.md` - the final report in
the transcript is the deliverable, and the coordination artifact dies with the run (keep it only if
the user asked). **Remove the temporary nav scaffold and any auto-nav flag - remove the branch, the
flag, and the import, don't merely disable it - then re-verify the affected screen on its real
navigation path.** Tear down the `.designvenv` if you created one.

### 4f. Anti-rationalization

Matching a design under time pressure breeds excuses. The discrepancy table decides, not adjectives.

| Excuse | Reality |
|---|---|
| "It's close enough / basically there" | The table decides with measured values, not an adjective. Every region ends **Fixed** or **Impossible: \<reason\>**. |
| "The theme was ported, it'll look the same" | Both real Sendbird runs shipped unverified skins. A match is claimed from a capture, not from a theme diff - and a theme carries no layout, so it can certify "recolored", never "looks like the original". |
| "I verified it by reading the code" | Code is not a render. Capture this round or it is UNVERIFIED. |
| "`tsc` and the build pass, we're done" | A green build says nothing about the pixels, and a green launch is not a correct screen. |
| "The worker's report says it matches" | Reports are claims; crops are evidence. Every PASS needs this-round capture data, whoever wrote the code. |
| "The judge is too strict - I'll overrule it" | Never overrule a judge's FAIL without a this-round measurement of your own. |
| "No subagent tool here, so the gates relax" | The capability gate changes scheduling only: serially, you run every brief inline at its step. Nothing is skipped. |
| "I'll brief the workers from memory instead of the file" | Subagents share no conversation context, and a long run compacts. `design-analysis.md` is the spec; a worker briefed from memory is ungrounded. |
| "I screenshotted it once - baseline done" | A resting shot holds no composer-typing, recording, picker, or menu detail - exactly where real runs shipped wrong. Drive the states (4c). |
| "I rendered every state in the seed data" | Rendering isn't driving. Hover/open states exist only after you drive them; a state you never render hides its defects. |
| "The measured numbers all match" | The stacked crop read is mandatory every round - numbers miss font weight, seams, centering, and *placement* (inside vs below the bubble). |
| "I cropped the reaction pills and they match" | Crop the **composite, full-width**. A sub-element crop verifies contents and hides positioning - the exact miss from a real run. |
| "The symbol isn't exported, so it's impossible" | You grepped an `export *` barrel. Check the compiled `.d.ts` or a throwaway import + `tsc`. An `Impossible` verdict must be proven by attempting it. |
| "The composer is fiddly, I'll note it as a known gap" | The composer is first-class and the single most-missed region. An unresolved row is `GAP - not matched` with both measured values, never "minor". |
| "The reference doesn't show an empty state, so the default is fine" | Every rendered state has a spec row - sampled (§3) or derived (§6). An unthemed SDK default inside a matched design is a FAIL against its derived row. |
| "It looks like a coherent chat app" | Internal coherence is not fidelity. An app verified against itself has been verified against nothing. |
| "The channel list matches, so the app matches" | The list hides every bubble, avatar, metadata, and composer gap on the chat screen - which is exactly where every real run shipped wrong. |
| "The user can just check it" | That is rung 3 only, and only after rung 1 was run and errored - and it ships labeled UNVERIFIED. |

**Red flags - stop:**
- Claiming "matches" without a capture taken **this round**.
- Claiming a region PASS from a worker report, with no crop behind it.
- Overruling a region-judge's FAIL without a this-round measurement of your own.
- Ending with failing rows left unlabeled, or a GAP relabeled "deferred" / "minor" / "cosmetic".
- Skipping the composer, the receipts, or the reactions rows because they are fiddly.
- Downgrading a measured FAIL to a soft word to close the task.
- Delivering with the temporary nav scaffold still in the tree.
