# Stream React Native — matching a reference design (Chat · Video · Feeds) (screenshot / Figma / "make it look like X")

Run this page **before** writing code, in addition to (not instead of) the normal `DOCS.md` lookup
in [SKILL.md](../SKILL.md). It is the *procedure* + the *routing map*; exact theme keys and component
names come from the manifest-selected docs and the installed package, not from memory.

**Banned as a resolution:** *"acceptable approximation", "minor", "difference noted", "close enough",
"keep default"*. Each region ends **Fixed** or **Impossible: \<concrete reason\>** — nothing in
between. (These hand-waves shipped ~10 real per-region defects.)

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

1. **Find the scale, then work in LOGICAL px.** Mobile screenshots are usually `@2x`/`@3x`; RN
   `StyleSheet` values are **logical px** (density-independent — what iOS calls points).
   ```bash
   sips -g pixelWidth -g pixelHeight <reference.png>   # e.g. 1179 x 2556 → ÷3 = 393x852 (@3x)
   ```
   1179 ÷ 393 = 3 → **@3x**, so `logical = pixels / 3` for everything you measure.
2. **Extract element sizes AUTOMATICALLY.** `magick`/PIL/numpy are available; threshold the cropped
   region and read real bounding boxes. Icons are **dark glyphs on a light bar** → threshold dark,
   project onto columns, cluster into glyphs, measure each box. The input field is the **wide
   near-white band** → its row-span is the field height, its white-column span the field width. Adapt
   the crop band + thresholds per design; this prints logical px directly:
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
   Each glyph's w/h and the field's h/w **are your spec**.
3. **Controls are almost always SMALLER than you guess — often smaller than the SDK default.** Match
   the measured size; don't fall back to the SDK's default input height or to round numbers. Confirm
   the SDK's actual defaults from the **installed package**, then decide whether the reference is
   smaller.
4. **The field width is the LEFTOVER** — `total − (leading cluster + trailing cluster + gaps)`.
   Oversized buttons steal it: size buttons to the measured glyph sizes, keep gaps on the theme's
   spacing scale, and the field reclaims its width.
5. **Centering: verify by MEASUREMENT.** Compare each glyph's center-Y to its container's center-Y
   (from the field's white-band row span); the offset must be ≈ 0. A consistent offset means your
   button frame height ≠ the field's rendered height — frame side buttons to the measured field height
   and center within, rather than hand-tuning one-sided padding.
6. **Grow the input pill with PADDING, not a fixed height — or the text stops centering.** The pill
   (`messageComposer.inputBoxWrapper`) lays out **top-down** and does not vertically center the text
   row, so a fixed `minHeight`/`height` on the wrapper drops all the slack **below** the text and it
   hugs the top (the classic "taller composer, input no longer centered" bug). Size the pill from
   **symmetric vertical padding on `messageComposer.inputBox`** (`paddingTop` == `paddingBottom`): a
   single line is centered by construction and still grows for multi-line. Don't zero the input's own
   vertical padding and re-add the height via `minHeight` — that guarantees the off-center result.
7. **Message bubble spacing** — if you change anything on the bubble, measure its inside padding and
   the gaps between its parts (text ↔ image etc.) and apply them.
8. **Land measured numbers in RN theme keys / style values, and reuse the SDK spacing scale** for
   gaps/radius so custom pieces align with un-overridden parts — but tokens are for spacing/radius,
   *not* a license to keep default control/field **sizes**; those come from measurement.
9. **No magic numbers.** A size standing for a concrete thing (keyboard, safe area, header, tab bar)
   anchors to that thing (the SDK default or a measured reference value), never to "what feels roomy."
   When correcting an over/undershoot, reach for the simplest static approximation (e.g. an SDK
   default) *before* any runtime measurement hook.

### Weight is its own dimension — measure and match it (separately from color)

- **Different text ROLES usually have different weights — measure each separately.** Sender name,
  message body and timestamp are typically distinct (name heavier, body regular/light); the recurring
  miss is treating "text" as one weight.
- **Map the stroke ÷ font-size ratio to an RN `fontWeight`**: ≈0.05→`'300'`, ≈0.075→`'400'`,
  ≈0.09→`'500'`, ≈0.11→`'600'`, ≈0.13+→`'700'`. Set each role independently in the theme's text keys.
  `'400'` often renders heavier than a reference's light body — re-measure your render and step down.
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

Invented colors are a recurring miss. **Sample every color and apply the measured value** —
background/wallpaper, bubble fills, composer bar, each glyph, borders, **and the read-receipt ticks**.
Never assume a "known" brand color.
- **Multi-part elements have more than one color — sample each part.** A two-tone control (gray circle,
  white arrow) is easy to invert if you guess.
- **Sampling gotcha:** small colored elements get swamped by similar colors in **photo attachments**
  (blue ticks vs. a blue sky — 200k blue pixels vs. ~800 tick pixels). Restrict the search to the
  element's context (tick pixels on the bubble rows, not the photo rows) before averaging, and sample
  the saturated **core**, not the antialiased edges.
- **A background may be a TEXTURE, not a flat color.** Sample **many** points: uniform (low std-dev) →
  flat fill → a color key; varying (faint repeated marks, small std-dev, darker mins) → a **pattern** →
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

**How to run the loop:** [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) — build + launch
tap-free (§1), stale-bundle trap (§2), reaching non-initial screens (§3), driving composer/picker states
(§4), poll-before-screenshot (§5), dark mode (§6). `simctl` cannot tap.

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

For each region from `design-analysis.md`: target attribute (size / position / colour / presence) ->
what rendered -> **PASS / FAIL**.

For the high-detail regions (the composer especially), back the numbers with a visual stack: screenshot
on the **same device class** (same `@2x`/`@3x`), crop **both** bars at **native resolution** (same scale
-> no resizing, so sizes compare 1:1), and stack them:

```bash
magick "$REF"  -crop ${W}x210+0+${refY}  +repage ref.png    # reference region
magick "$MINE" -crop ${W}x210+0+${mineY} +repage mine.png   # your render (find Y via the field-band script)
magick ref.png mine.png -background black -append compare.png  # stack; view it
```

On the stack, check what the numbers miss — field height/compactness, stroke weight, vertical centring
of each control, overall balance — then re-measure to confirm fixes.

**Crop the whole composite + its container + margins — full-width, never the sub-element you built.** A
crop framed on the pills or the button alone verifies *contents* but hides *positioning*: a real run
cropped reactions in isolation, saw "emoji + count + add-button" on both sides, and missed that the
reference renders them **inside** the bubble while it had built them **below**. Crop **full-width**
(screen-edge to screen-edge, boundary + both margins in frame) at these composite units: a **whole single
message row** (bubble + metadata + reactions + avatar; incoming *and* outgoing), the **whole composer bar**
(at-rest *and* typing — not button-by-button), a **channel-list row** (1:1 *and* group), and the
**header**. Then answer the **placement question** before any PASS — reactions *inside vs below* the
bubble, send/mic *inside vs outside* the pill (plus pill *filled vs outlined*, attach *circle vs square*),
metadata *inside/beside/below*, avatar *silhouette vs initials*.

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
