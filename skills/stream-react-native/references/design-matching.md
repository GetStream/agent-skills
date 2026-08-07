# Stream React Native — matching a reference design (Chat · Video · Feeds) (screenshot / Figma / "make it look like X")

Run this page **before** writing code, in addition to (not instead of) the normal `DOCS.md` lookup
in [SKILL.md](../SKILL.md). It is the *procedure* + the *routing map*; exact theme keys and component
names come from the manifest-selected docs and the installed package, not from memory.

**Banned as a resolution:** *"acceptable approximation", "minor", "difference noted", "close enough",
"keep default"*. Each region ends **Fixed** or **Impossible: \<concrete reason\>** — nothing in
between. (These hand-waves shipped ~10 real per-region defects.) **`scripts/check_analysis.py` is the
gate that enforces this** — run it on `design-analysis.md` before you call a match done (Step 3).

**Don't ship affordances the app can't back.** References and boilerplate often carry buttons the app
has no feature for — most commonly a **video-call icon** in the header or composer of a chat-only app.
A button with no wired behavior gets **removed**, not disabled and not pointed at a no-op: a dead
button reads as broken, not as scoped-out.

---

## Step 1: Decompose the reference into regions (every time)

Go region by region, screen group by screen group. For **each** region: name what the design shows,
compare it to the Stream RN default, and if it differs route it to the cheapest **Axis** that reaches
it (theming / layout / functional / already-default). Produce an explicit task list — one entry per
differing region. Never skip a region because it "looks standard"; verify it against the default.

**Front-load the thinking — planning is cheap, UI validation is not.** Step 4's build → run →
screenshot → compare loop is the most expensive part of a match; every region you spec and route now
is one you won't rediscover through a visual-validation cycle.

**Capture the spec, not just the identity.** Per region, record what you'll reproduce: bubble corner
radius, tail/shape, max width, alignment; avatar shape/size and whether it shows on own messages; font
sizes and **weights** (a name is usually heavier than the body); paddings and gaps; **sampled colors**
(bubble fills, accent, ticks, background). Right color + wrong size or spacing still fails the eye.

**A *code-derived* reference (a migration's palette-only rung) is *intended*, not *verified* — and
verification is not optional at any tier.** A theme-file colour says what the source *meant* to paint,
not what the SDK renders, and a theme file carries **no layout at all**: it can seed colours, never
structure. Confirm colours against the running app's render, and treat every structural region as
unmatched until an **independent** reference (the original's real pixels) confirms it.

### Getting sizes right — MEASURE, do not eyeball round numbers

Picking `24`, `28`, `44` by eye is the recurring failure, worst in the composer (wrong input height,
oversized icons, wrong paddings). "Match by proportion" is not enough when an exact dimension matters.

1. **Run `scripts/measure_region.py` — do not hand-roll the thresholding.** Every number it prints is
   **logical px** (screenshots are `@2x`/`@3x`; `StyleSheet` takes logical px), so no device pixel can
   leak into a style. **Its output is your spec.** Needs Pillow + numpy — install before you start
   capturing (`scripts/README.md`).
   ```bash
   python3 scripts/measure_region.py scale  <ref.png>                     # pixels → scale → logical
   python3 scripts/measure_region.py band   <ref.png> [--from-bottom 380] # pill h/w/inset + icon glyphs
   python3 scripts/measure_region.py colors <ref.png> --box X,Y,W,H       # mean/core hex, flat vs texture
   python3 scripts/measure_region.py weight <ref.png> --box X,Y,W,H --font-size 15
   ```
   **`scale` first, and act on both things it tells you** — they set up the whole run:
   - **`logical_width`** is the simulator you must pin, *before* the native build:
     `bash scripts/sim.sh boot --logical-width 393`. A 402pt render cannot be compared 1:1 to a 393pt
     reference; `compare_regions.py` refuses the pair, and a run that discovered this after building
     hand-measured everything instead.
   - **`source_profile`** is usually **Display P3** for a real-device screenshot, while simulator
     captures are sRGB. The same paint reads as different numbers (`#E0FCD6` P3 = `#D9FDD3` sRGB), so
     colour verdicts flip on colour space alone. The tools convert to sRGB on load and say so — take
     **their** hex values, and never sample a P3 reference by hand into a theme file.
2. **Controls are almost always SMALLER than you guess — often smaller than the SDK default.** Match
   the measured size; don't fall back to the SDK's default input height or to round numbers. Confirm
   the SDK's actual defaults from the **installed package**, then decide whether the reference is
   smaller.
3. **The field width is the LEFTOVER** — `total − (leading cluster + trailing cluster + gaps)`.
   Oversized buttons steal it: size buttons to the measured glyph sizes, keep gaps on the theme's
   spacing scale, and the field reclaims its width.
4. **Centering: verify by MEASUREMENT.** Compare each glyph's center-Y to its container's center-Y
   (from the field's white-band row span); the offset must be ≈ 0. A consistent offset means your
   button frame height ≠ the field's rendered height — frame side buttons to the measured field height
   and center within, rather than hand-tuning one-sided padding.
5. **Grow the input pill with PADDING, not a fixed height — or the text stops centering.** The pill
   (`messageComposer.inputBoxWrapper`) lays out **top-down** and does not vertically center the text
   row, so a fixed `minHeight`/`height` on the wrapper drops all the slack **below** the text and it
   hugs the top (the classic "taller composer, input no longer centered" bug). Size the pill from
   **symmetric vertical padding on `messageComposer.inputBox`** (`paddingTop` == `paddingBottom`): a
   single line is centered by construction and still grows for multi-line. Don't zero the input's own
   vertical padding and re-add the height via `minHeight` — that guarantees the off-center result.
6. **Message bubble spacing** — if you change anything on the bubble, measure its inside padding and
   the gaps between its parts (text ↔ image etc.) and apply them.
7. **Land measured numbers in RN theme keys / style values, and reuse the SDK spacing scale** for
   gaps/radius so custom pieces align with un-overridden parts — but tokens are for spacing/radius,
   *not* a license to keep default control/field **sizes**; those come from measurement.
8. **No magic numbers.** A size standing for a concrete thing (keyboard, safe area, header, tab bar)
   anchors to that thing (the SDK default or a measured reference value), never to "what feels roomy."
   When correcting an over/undershoot, reach for the simplest static approximation (e.g. an SDK
   default) *before* any runtime measurement hook.

### Weight is its own dimension — measure and match it (separately from color)

- **Different text ROLES usually have different weights — measure each separately.** Sender name,
  message body and timestamp are typically distinct (name heavier, body regular/light); the recurring
  miss is treating "text" as one weight.
- **`measure_region.py weight <img> --box X,Y,W,H --font-size N` does the mapping** — it measures the
  median stroke width, divides by the font size, and prints the RN `fontWeight` string plus the
  glyph's dark-core colour. (The ratios it applies: ≈0.05→`'300'`, ≈0.075→`'400'`, ≈0.09→`'500'`,
  ≈0.11→`'600'`, ≈0.13+→`'700'`.) Set each role independently in the theme's text keys. `'400'` often
  renders heavier than a reference's light body — re-measure **your own render** and step down if so.
- **Don't conflate color with weight.** "Too light" may be a wrong base **color** (or a sub-pixel
  stroke antialiasing to gray) rather than a thin weight; "too bold" is weight. Fix the one that's
  actually wrong, and **verify both by measurement**: rendered stroke width ≈ reference's, AND
  dark-core color ≈ reference's. Two separate checks.
- **Verify a glyph's drawn ink, not its declared size.** An SVG's size prop sizes the box, not the
  paths: paths that don't reach the viewBox edges render smaller than the box, so a size check passes
  while the glyph reads undersized — and the same squeezed ink is proportionally denser, so an
  ink-ratio check simultaneously reads it as too heavy. One cause, two misleading checks. Measure the
  ink bounding box on both sides; if declared sizes match and ink boxes don't, fix the path data or
  the viewBox, not the size prop.

### Follow EVERY color from the reference — sample it, don't guess (and sample each sub-part)

Invented colors are a recurring miss. **Sample every color with
`python3 scripts/measure_region.py colors <img> --box X,Y,W,H` and apply the measured value** —
background/wallpaper, bubble fills, composer bar, each glyph, borders, **and the read-receipt ticks**.
Never assume a "known" brand color. It returns the mean and the saturated **core** hex, the per-channel
std-dev, and a flat-vs-texture verdict.
- **Multi-part elements have more than one color — sample each part** with its own `--box`. A two-tone
  control (gray circle, white arrow) is easy to invert if you guess.
- **Sampling gotcha:** small colored elements get swamped by similar colors in **photo attachments**
  (blue ticks vs. a blue sky — 200k blue pixels vs. ~800 tick pixels). Restrict `--box` to the
  element's context (tick pixels on the bubble rows, not the photo rows); the tool already reports the
  saturated **core** rather than the antialiased edges.
- **A background may be a TEXTURE, not a flat color** — that is the `verdict` field. Uniform (low
  std-dev) → flat fill → a color key; varying (faint repeated marks, darker mins) → a **pattern** →
  reproduce it as a tiled background component. The texture is often what separates the chat area from
  a plain composer, so don't flatten it: bundle the asset or a cropped patch and tile it, or
  approximate a faint motif and tell the user it's an approximation.
- **Verify by re-sampling YOUR render and diffing against the reference**, per sub-part.
- **Override EVERY token that cascades from an accent/brand colour, and treat any un-rendered state as
  hiding a stray default.** Recolouring common surfaces while a less-common state keeps the SDK default
  (voice recording → `accentPrimary` / `chatWaveformBar`, edit, error, overlays, focus rings) is not a
  finished theme. Set those tokens even for states the reference never shows — a code check, not a
  reason to drive and screenshot the state.

**Light/dark carve-out — don't pin structural surfaces to a light-mode literal.** The reference is
almost always a light screenshot. **Pin** the sampled **brand/content** colors (bubble fills, glyphs,
accent, read-receipt ticks) — identical in both modes. Keep **structural surfaces** (message-list
background, composer/input background, borders) on the theme's semantic values so they adapt; pinning a
surface to `white` looks right in light and breaks in dark. Verify both (§4.4).

**A pinned brand accent and an adapted brand-tinted surface are different tokens — never mix them
inside one element.** A saturated brand fill (outgoing bubble, primary button) pins, and its foreground
pins with it. A pale brand wash used as a card, banner or sheet is not a brand colour but a *light
surface with brand character*, so it adapts: hold the hue, cut saturation, drop lightness. Pinning a
tint keeps the pigment and loses the role — a pale card pinned into a dark UI becomes the brightest
thing on screen (18.93:1 against a near-black screen, vs 1.76:1 adapted). The observed defect on two
SDKs was pinning the surface while leaving its contents semantic, collapsing label-on-card contrast to
1.03:1 and 1.58:1. When you adapt a surface, adapt every nested surface and ink with it and **preserve
the light-mode elevation direction** (an inner sheet lighter than its parent in light must stay lighter
in dark, or a raised sheet reads as a well). Verify every nested pair in dark: 4.5:1 for text, ~1.5:1
surface-on-surface where no shadow is doing the work.

**A knockout inside a glyph is not a colour — it is the surface behind the glyph showing through.** Set
it to the token of whatever surface the glyph sits on, pinned or adapted, never a literal. A hardcoded
white knockout is correct only while the glyph sits on a light surface: once the surface adapts and the
ink lightens, the cutout vanishes into the ink and the glyph reads as a solid blob (measured on one
icon: 1.36:1 against its own ink in dark, 13.33:1 once resolved, light unchanged apart from the knockout
pixels). It passes every pair a theme check measures — surface and ink both adapted, and the knockout is
not one of the pairs. Detect it by sampling the knockout in both modes: an identical hex while the
surrounding ink changed means it's a literal.

### Region checklist + routing (walk every row)

The per-product tables below carry the rows. The **Route to** column names the *mechanism*; **confirm
the exact theme key / slot / prop name** in the manifest-selected docs and the installed package.

**Reasoning rules for picking the mechanism** — these catch a *class* of mistake, so they generalize to
regions not yet enumerated:

- **A theme-key / slot name is a hint, not a guarantee — confirm the target node in the render tree.**
  Composer/message keys (`wrapper` vs `container` vs `inputBoxWrapper`, `MessageContent*` vs
  `MessageFooter`) do **not** map to "the thing you mean" by name. Two minutes in the installed
  component's source beats a name-based guess that half-works.
- **A theme key that colours only *part* of a region means you hit an *inner* container.** Partial
  success (a band around the controls, half a surface tinted) is more dangerous than no effect, because
  it doesn't trip the "go investigate" reflex. Read the render tree, apply the value to the **outermost
  full-bleed `View`**, and verify by sampling the *margins around* the region, not just its controls.
- **Fix the structure before the surface — never fake a structural property with a background fill.** A
  translucent fill faking a floating/blurred pill, or a painted strip faking an overlay, is a defect,
  not a match. Map the difference to the SDK's structural mechanism first (a prop/flag/slot, e.g.
  `messageInputFloating`), then theme the surface — structural axis before cosmetic polish.
- **A large custom build that parallels SDK infrastructure is a red flag — re-read the reference.** A
  knowledge-backed decision can rest on a misread screenshot, and knowing the API makes the wrong path
  *feel* informed, so it never trips the "look this up" reflex. Before choosing a modal / host
  replacement / from-scratch surface over an SDK slot, **state the SDK's default structure for that
  region and diff it against the reference.** The SDK almost always has a slot; reinvention usually
  means you misread the reference.
- **Idiomatic ≠ matching, in both directions.** Swapping in an SDK component for its *behaviour*
  inherits its *appearance* (the SDK `AttachButton` is a bordered `type="outline"` button) —
  re-decompose the look after the swap. Re-customizing a slot for *appearance* must **reuse the SDK
  component's behaviour logic** (read its `onPress` and replicate it, subtle branches included), not
  hand-roll a lossy version.

Per region note: color, background color, border, border radius, padding / gap, typography (font, font
weight, font and line size) — save to `design-analysis.md`. Keep it until the Step 4 verify loop passes;
unless asked otherwise, remove it after.

#### Product region tables

Split per product so a build only loads the surfaces it touches:

| Product | File | Covers |
|---|---|---|
| **Chat** | [`regions-chat.md`](regions-chat.md) | the three axes of RN Chat customization, channel list, message chrome, message row, reactions, attachments, composer — plus deep-dives (dead theme keys, bubble radius, metadata in the bubble, long-press menu, composer render tree, attachment picker, Liquid Glass) |
| **Video** | [`regions-video.md`](regions-video.md) | call screen, participant tiles, controls, livestream surfaces |
| **Feeds** | [`regions-feeds.md`](regions-feeds.md) | activity card, composer, comments, follows, notification feed |

Read the ones in scope and walk every row — a Chat build never needs the Video or Feeds rows. The
**cross-cutting** rows below apply to all three; always walk them.

#### Cross-cutting

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Fonts, accent color | — | Theming | theme font / color keys |
| Light/dark behavior | pin brand colors, keep structural surfaces semantic | Theming | Build **two palettes** and select on `useColorScheme()` (from `react-native`); pin brand/content, keep surfaces semantic (light/dark carve-out above). |
| Spacing | component overrides | Theming | Ensure overridden components have proper spacing, especially inside a rounded message bubble. |
| Icons | shape, color, size | Theming or structural | Only create a custom icon if the shape is truly different (paperclip instead of plus); don't replace a mic icon with a slightly different mic icon. |

### Common decision points

**Thread scope.** A static screenshot usually does **not** settle whether threads are in scope: the
reply indicator only renders on messages that already *have* replies, and the reply screen + thread
inbox are separate screens a message-list shot never captures — so a missing indicator is not evidence
threads are unwanted. If the reference doesn't clearly show threads and the user hasn't said, **ask one
short question and wait**:

> This design doesn't clearly show message threads. Should the app support threads (reply-in-thread + a thread screen), or keep conversations flat?

- **In scope** -> implement the Thread Screen (and the Thread List / inbox if the design shows one) as
  routed in the region table.
- **Not wanted** -> don't merely omit the UI. **Disable thread replies on the `messaging` channel
  type** so the SDK never surfaces the affordance —
  [credentials.md > disable threads](../credentials.md#disable-threads). The message-row override then
  doesn't have to reproduce a thread indicator, and Step 3's completion contract can legitimately mark
  it `N/A - threads disabled on channel type`.

**Composer placement — derive it from the reference, don't lead with a yes/no question.** Floating vs
docked is **structural**: it maps to `messageInputFloating` on `<Channel>`, and getting it wrong changes
the composer's relationship to the keyboard and the list. Read the cues off the image and decide from
them (cues, anti-patterns and mechanism:
[`regions-chat.md`](regions-chat.md#composer-deep-dive--the-render-tree-the-surfaces-and-the-two-facet-buttons)).
Do **not** open with a bare "floating or docked?" — a wrong one-time answer short-circuits the region
analysis and is hard to unwind (you end up faking the look instead of re-deriving it). Ask only if the
cues are genuinely ambiguous *after* you've examined them, and re-verify against the image every build:

> The floating-vs-docked cues in this reference are ambiguous (I can't tell if the input floats inset above the content or docks flush at the bottom). Which is it?

State the result as a task list: `Region -> default vs. target -> mechanism (theme key / component
override / prop-or-hook / already-default)`. Implement **all** differing regions, not just the cheap
theming ones.

---

## Step 2: Install the dependencies the design implies

A screenshot signals a *capability*, not just a look, and some Step-1 regions aren't reachable by
theming or an override alone. Voice-recording UI or an audio waveform, inline video with a play button,
a composer camera button, a device photo grid or attachment sheet, file/document rows, a share
affordance — each needs a **native capability package** first. Style the slot perfectly without it and
the region still fails, at the behavior level rather than the pixel level.

Walk the Step-1 task list, flag every region whose **capability** the design requires, and install from
the matrix for the product (packages per runtime lane, plus permission and re-link notes):

- **Chat** -> [`../builder.md`](../builder.md#chat---optional-packages-by-capability)
- **Video** -> [`../builder.md`](../builder.md#video---optional-capabilities)

Install only what the design implies — do NOT bulk-install the matrix for one vague signal. A region
needing a package the app lacks must have it installed (or flagged if you can't) **before** you
implement that region; otherwise it is a `GAP`, not a match.

**Kick off the native build NOW — as soon as the Stream packages + peers are installed.** The native
build (`npx expo prebuild --clean` + `expo run:ios`, or the RN CLI equivalent) is the single most
expensive step and the only place the **native peers actually get exercised**. Starting early (a) runs
it in the background *while* you implement, overlapping the two slow phases instead of serialising
them, and (b) surfaces native/peer failures immediately.

---

## Step 3: Commit the plan, and verify every name against the installed package

Step 1 said *what the reference looks like*; this step commits *how you will build it* and proves each
mechanism exists. Both halves are cheap here and expensive after the build.

**Give `design-analysis.md` a `Plan` column: the exact SDK feature/mechanism per region** — the theme
key (`semantics.chatBgOutgoing`, `channelPreview.unreadContainer`, …), the `WithComponents` slot
(`MessageAuthor`, `ChannelPreviewAvatar`, `MessageContentBottomView`, `MessageComposerLeadingView`, …),
the `<Channel>` prop (`messageInputFloating`, `audioRecordingEnabled`, …), or a documented hook/config —
plus the axis and whether it's an SDK default that already matches. Table shape: `Region | Spec
(measured) | Plan (SDK feature) | Axis | Status`. This turns the match into a resolved build plan and
pre-empts the *reinvention red flag*: if the Plan is "custom component from scratch", re-check whether
an SDK slot already covers it.

**Verify every name you just wrote against the installed package.** A theme key, slot or prop that
type-checks is **not** evidence that it renders — `Theme` is a wide type and several keys are dead or
partly dead at runtime (the component overwrites them after the theme is applied, drops them in one
branch, or never reads them) — and a prop's default in guidance is not its default in the pinned source.
For each `Plan` row, open the component in `node_modules` for the pinned version and confirm the value
reaches the rendered style. An unverified `Plan` is the single largest defect class in real runs: `tsc`
green, app builds, pixel doesn't move, reads like a stale bundle. For Chat, check the confirmed-dead
list in [`regions-chat.md`](regions-chat.md#dead-theme-keys) first.

**Completion contract — a custom component for a prebuilt region must reproduce every sub-feature the
default drew.** Overriding a composite slot silently drops whatever you don't re-render, and "the region
looks right" is exactly how one gets missed. Before writing one, list what the default draws and mark
each **Reproduced** or **`N/A - <reason>`**: avatar, grouping, sender name, reactions, quoted/inline
reply, delivery/read receipts, timestamp, edited/deleted state, attachments, pinned/saved status. A
dropped sub-feature is a FAIL found at Step 4, not a design choice.

**Validate the file itself — don't re-read it hunting for hand-waves:**
`python3 scripts/check_analysis.py <project>/design-analysis.md --require-evidence`.
**Exit 1** = a region with no terminal verdict, a synonym for "good enough", a status opening with a
deferral, or an `N/A` whose reason is a schedule excuse. Everything else (unmeasured Spec, empty Plan,
unknown Axis, missing evidence file) warns without blocking, so it converges in one run; `--strict`
makes warnings fail too. A verdict may carry its evidence — `Fixed - 40.0pt vs 40.3pt, compare-composer.png`.

## Step 4: Verify against the reference - region by region (mandatory)

**Rules - all of them, every run:**

- **Not done** until the app runs and the render is compared to the reference. Presence-and-colour is
  not enough: verify **size, position, proportion, and structure**.
- Walk the **whole** Step-1 checklist. Don't stop at the regions that happen to look right.
- **Numbers alone lie.** A glyph box can match (±1 logical px) while the field is too tall, a stroke too
  heavy, filled instead of outlined, or a control off-centre. Always compare visually too.
- Any throwaway scaffold added to reach a screen is **DELETED before delivery** (remove the
  branch/flag/import, don't merely disable it), then the real path re-verified.
- **Regression adjacency — re-verify *every* facet of a region after *any* change.** Fixing one facet
  (structure / appearance / behaviour) routinely breaks a neighbour one layer down: rebuilding the
  picker breaks the attach button's look, restyling the button breaks its toggle behaviour. After each
  fix re-check the region's other facets **and both of its states**.
- **Iterate until every region passes.** Never declare done on the first render.
- If you genuinely cannot run the app, say so plainly and list which regions are
  implemented-but-unverified — never imply a match you did not see.
- **Never deliver a region left at its default and call it a "known gap."** Report a region unmatched
  only when it is genuinely impossible (say what + why), never because it is risky or more effort — and
  prove impossibility by *attempting* it.

**How to run the loop — the scripts ARE the loop; don't re-derive them:**

```bash
# Pin the simulator to the REFERENCE's device class first — Step 1's `scale` printed it.
bash scripts/gate.sh "$P" npx expo run:ios --device "$(bash scripts/sim.sh boot --logical-width 393)"

# implement ALL differing regions of a screen, THEN capture once per screen STATE
bash scripts/sim.sh capture "$BUNDLE" chat-atrest-1.png --project "$P" --lane expo --logical-width 393

# every region of that state in ONE call — numeric verdicts + one labelled contact sheet
python3 scripts/compare_regions.py ref-atrest.png chat-atrest-1.png \
    --r composer --r header --r row-out:1180 --r row-in:1320

python3 scripts/check_analysis.py "$P/design-analysis.md" --require-evidence
bash scripts/cleanup.sh "$P" --yes          # at the very end — artifacts live in the USER'S project
```

**Batch or the scripts cost more than they save.** Turn count, not file size, drives cost: a measured
pair of runs regressed 30–42% in turns mostly by calling these one region and one step at a time. One
`capture` per screen *state*, one `compare_regions.py` for **all** its regions, one `check_analysis.py`.

Background for the cases the scripts can't automate:
[SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) — reaching non-initial screens (§3), driving
composer/picker states (§4), dark-mode caveats (§6). **`simctl` cannot tap**, so any screen behind the
first one is reached with temporary in-code scaffold that you delete afterwards.

### 4.1 Seed data that triggers every region

An empty or one-message channel proves nothing and hides exactly the elements that get dropped. The
test channel needs: **an incoming and an outgoing** message; a **run of 3+ consecutive messages from the
same author** (grouping + the avatar rule); a **photo album**; a message **with reactions**; a **reply /
thread**; a **long multi-line** message. Mark messages read if the design shows read receipts. Seed via
the Stream CLI / [`../credentials.md`](../credentials.md).

**Multi-day date separators ("Yesterday", "May 29") can't be fresh-seeded** — the seed API stamps
everything today, so only a "Today" separator appears.

### 4.2 Screenshot every screen, then check it

Screenshot the **channel list**, the **message screen**, and the **thread screen**. Each region's target
attributes live in the Step-1 checklist and the per-product region file; on top of those, check the ones
that get silently lost — every time:

**All screens**
- [ ] **Nav header** — height, title, back affordance (app-owned, not the SDK's).

**Channel list**
- [ ] Preview row: avatar, name, preview text, timestamp, unread badge, row background.

**Message screen**
- [ ] **Incoming-message avatar** and **grouping** across the 3+ same-author run.
- [ ] **Metadata placement** — inside the bubble, not clipped, default footer not duplicated.
- [ ] Reaction display and attachment/album rendering.
- [ ] Wallpaper/background, date separator.

**Thread screen**
- [ ] Parent message + reply list render, and the thread's own header/composer match the main screen.

**Composer gate — do NOT leave the composer until all pass (the recurring defect).** Verify
**structure**, not just presence/colour:
- [ ] **Floating vs docked matches the reference.** If it floats, `messageInputFloating` is set on
  `<Channel>` — and the pill is NOT a docked bar with a painted translucent fill faking the float. If it
  docks, it sits flush to the bottom edge.
- [ ] **Three states are MANDATORY — at-rest, typing, picker-open**
  ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §4). At-rest and typing share one slot
  (`OutputButtons`), and typing is the **only** state that renders the send button. Picker-open is where
  the composer<->sheet spacing and the `+`<->keyboard swap are visible.
- [ ] **Every OTHER state — keyboard-up, voice-recording, edit mode — only if a reference screenshot
  shows it** (§4). Driving them speculatively catches nothing: the defects they'd find (unset
  `audioRecordingEnabled`, a composer pushed off-screen) all show up at rest. If a reference does show
  one, check its own tokens — the recorder tints from `semantics.accentPrimary` +
  `semantics.chatWaveformBar`, so overriding `accentPrimary` alone can leave a waveform on the default.
- [ ] **Background fills EDGE-TO-EDGE and through the bottom safe area** — sample pixels in the *margin
  around* the controls. A band hugging the buttons = you coloured `container`, not `wrapper`.
- [ ] **Single-line input is vertically centred** in the pill (grown via `inputBox` padding, not wrapper
  height).
- [ ] **Attach button:** correct look (borderless vs bordered) **and** the `+`<->keyboard swap when the
  picker opens, wired to a `toggleAttachmentPicker` replica.
- [ ] Each glyph matches the reference's size, weight, fill-vs-outline character (compare ink ratio, not
  just the box), and colour.

### 4.3 Build the comparison table

**`scripts/compare_regions.py` builds it** — every region of the state in ONE call:

```bash
python3 scripts/compare_regions.py <ref.png> <mine.png> \
    --r composer --r header --r row-out:1180 --r row-in:1320
```

`--r` is `name`, `name:refY`, `name:refY:mineY`, or `name:refY:mineY:height`. `composer` and `header`
self-locate in both images; anything else needs only a **reference** y. It prints a numeric verdict
table per region, **the edit that closes each failing metric**, and one labelled contact sheet; exit
non-zero = a region failed. Read the numbers and `fix:` lines first, then open the sheet **once** for
what numbers can't judge (balance, glyph identity, texture, material). A metric shown `-`/`n/a` was
**not measured** — treat it as unmeasured, never as passing.

What you still have to get right:

- **When it says `AUTO-LOCATION FAILED`, hand it the y — don't work around it.** It refuses when the
  two images' located bands disagree, or when the geometry is absurd (a pill inset a third of the
  screen, glyphs under 8pt). Both mean the crops aren't the same region: a real run published a "10pt
  input pill" that direct measurement put at 30pt, because a mic FAB near the screen edge stopped the
  *reference* scan 37pt early while the render's ran on. Re-run with `--r 'composer:<refY>'`, or
  `'composer:<refY>:<mineY>'` for a translucent composer floating over a wallpaper (Telegram-style),
  where no colour-step anchor exists at all.
- **Different device classes need `--allow-scale-mismatch`, and then only some rows mean anything.**
  Heights and sizes in pt stay comparable; absolute x-offsets do not, so insets and widths are judged
  on the `%W` rows. Prefer fixing the device class instead — this flag is the fallback.
- **Give it full-width crops of the same device class.** A region framed on the sub-element you built
  verifies its *contents* and hides its *position*: a real run cropped reactions in isolation, saw
  "emoji + count + add-button" on both sides, and missed that the reference renders them **inside** the
  bubble while it had built them **below**. Use composite units — a whole message row (incoming *and*
  outgoing), the whole composer bar (at-rest *and* typing), a channel-list row (1:1 *and* group), the header.
- **A differing control count suppresses the per-glyph rows.** Glyph N is a different button on each
  side once the counts differ, so the tool reports the mismatch and stops there. Fix the count (or
  compare a state where they match) before reading glyph sizes.
- **Answer the placement question before any PASS.** The tool reports band counts as a note, not a
  failure: reactions *inside vs below* the bubble, send/mic *inside vs outside* the pill (pill *filled vs
  outlined*, attach *circle vs square*), metadata *inside/beside/below*, avatar *silhouette vs initials*.

### 4.4 Check dark mode

If the app supports dark mode, **both modes are verified on the same build** — no rebuild. Capture each
mode per [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §6, then confirm the **light/dark
carve-out** from Step 1 held:

- [ ] **Structural surfaces** (message-list background, composer/input background, borders) flipped to
  their dark values. One that stayed light is a pinned-to-literal bug.
- [ ] **Pinned brand/content** colours (bubble fills, glyphs, accent, read-receipt ticks) look identical
  to light mode. One that washed out was pinned wrong.
- [ ] Text and glyphs still have contrast against the flipped surfaces — sample both modes.
- [ ] No element mixes a pinned brand accent with an adapted brand-tinted surface (Step 1) — every
  nested pair measures 4.5:1 for text, ~1.5:1 surface-on-surface, light-mode elevation direction
  preserved.
- [ ] No glyph **knockout** is a literal — sample it in both modes; an identical hex while the
  surrounding ink changed means it never resolved (Step 1).
