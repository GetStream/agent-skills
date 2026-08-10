# Stream React Native — matching a reference design (Chat · Video · Feeds) (screenshot / Figma / "make it look like X")

Run this page **before** writing code, in addition to the normal `DOCS.md` lookup in
[SKILL.md](../SKILL.md). It is the *procedure* + the *routing map*; the exact theme keys and component
names come from the manifest-selected docs and the installed package, not from memory.

**Banned as a resolution:** the strings *"acceptable approximation", "minor", "difference noted",
"close enough", "keep default"*. Each decomposed region ends **Fixed** or **Impossible: \<concrete
reason\>** — nothing in between.

---

## Don't ship affordances the app can't back

A reference design, template, or boilerplate example often carries buttons the app has no feature for
— most commonly a **video-call icon** in the header or composer of a chat-only app. If a button has no
wired behavior, **remove it**; don't leave it rendered-but-disabled or wired to a no-op handler.

---

## Step 1: Decompose the reference into regions (every time)

Go region by region. For **each** region: name what the design shows, compare it to the Stream RN
default, and decide **theming / layout / functional / already-default**. Produce an explicit task list
— one entry per region that differs. Do not skip a region because it "looks standard"; verify it
against the default.

**Front-load the thinking.** The build → run → screenshot → compare loop in Step 3 is by far the most
expensive part of a design match; every region you name, spec, and route now is one you won't
rediscover through a visual-validation cycle later.

**Capture the spec, not just the identity.** For each region record the concrete attributes you'll
reproduce: bubble corner radius, tail/shape, max width, alignment; avatar shape/size and whether it
shows on own messages; font sizes and **weights** (a name is usually heavier than the body); paddings
and gaps; and the **sampled colors** (bubble fills, accent, ticks, background). A region with the right
color but the wrong size or spacing still fails the eye.

**When the reference is *code-derived* (a migration's palette-only rung), the values are *intended*,
not *verified*.** A colour read from a theme file says what the source *meant* to paint, and a theme
file carries **no layout at all** — so a code-derived spec can seed colours but never structure.
Confirm colours against the running app's render, and treat every structural region as unmatched until
an **independent** reference (the original's real pixels) confirms it.

### Getting sizes right — MEASURE, do not eyeball round numbers

Picking `24`, `28`, `44` by eye is the recurring failure, and it shows most in the composer (wrong
input height, oversized icons, wrong paddings). Matching by proportion is not enough when an exact
dimension matters — extract the real numbers off the reference and land them in RN style values:

1. **Find the scale, then work in LOGICAL px.** Mobile screenshots are usually `@2x`/`@3x`, and RN
   `StyleSheet` values are **logical px** (density-independent — what iOS calls points):
   ```bash
   sips -g pixelWidth -g pixelHeight <reference.png>   # e.g. 1179 x 2556 → ÷3 = 393x852 (@3x)
   ```
   For every element you measure off the image: `logical = pixels / scale`.
2. **Extract element sizes AUTOMATICALLY.** `magick`/Python+PIL/numpy are available; threshold the
   cropped region and read real bounding boxes. Icons are **dark glyphs on a light bar** → threshold
   dark, project onto columns, cluster into glyphs, measure each box. The input field is the **wide
   near-white band** → its row-span is the field height, its white-column span the field width. This
   script (adapt the crop band + thresholds per design) prints logical px directly:
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
   Match the measured size; don't fall back to the SDK's default input height or to round numbers.
   Confirm the SDK's actual defaults from the **installed package**, then decide whether the reference
   is smaller.
4. **The field width is the LEFTOVER.** The input gets
   `total − (leading cluster + trailing cluster + gaps)`, so oversized buttons make the field too
   narrow. Size buttons to the measured glyph sizes and keep gaps on the theme's spacing scale.
5. **Centering: verify by MEASUREMENT, not eye.** Find each glyph's center-Y and its container's
   center-Y (from the field's white-band row span) and confirm the offset ≈ 0. A consistent offset
   means your button frame height ≠ the field's rendered height — frame side buttons to the measured
   field height and center within, rather than hand-tuning one-sided padding.
6. **Grow the input pill with PADDING, not a fixed height.** The pill
   (`messageComposer.inputBoxWrapper`) lays its content out **top-down** and does **not** vertically
   center the text row, so a fixed `minHeight`/`height` on the wrapper drops the extra height **below**
   the single line of text and it hugs the top. Size the pill from **symmetric vertical padding on the
   input** instead (`messageComposer.inputBox` `paddingTop` == `paddingBottom`): a single line is then
   centered by construction and it still grows for multi-line. Don't zero the input's own vertical
   padding and re-add the height via `minHeight`.
7. **Message bubble spacing** — if you change anything on the bubble, measure its inside padding and
   the gaps between its parts (text ↔ image, …) and apply them.
8. **Land measured numbers in RN theme keys / style values, and reuse the SDK spacing scale** for
   gaps/radius so custom pieces align with un-overridden parts — but tokens are for spacing/radius,
   *not* a license to keep default control/field **sizes**; those come from measurement.
9. **No magic numbers.** A size standing for a concrete thing (keyboard, safe area, header, tab bar)
   anchors to that thing (the SDK default or a measured reference value), never to "what feels roomy."
   When correcting an over/undershoot, reach for the simplest static approximation before any runtime
   measurement hook.

### Weight is its own dimension — measure and match it (separately from color)

Every glyph and text role has a **weight** as well as a size and color, and the eye is sensitive to it.
Match it from the reference:
- **Different text ROLES usually have different weights — measure each separately.** A sender name, the
  message body, and a timestamp are typically distinct (name heavier, body regular/light); the
  recurring miss is treating "text" as one weight.
- **Map the stroke ÷ font-size ratio to an RN `fontWeight` string**: ≈0.05→`'300'`, ≈0.075→`'400'`,
  ≈0.09→`'500'`, ≈0.11→`'600'`, ≈0.13+→`'700'`. Set each role independently in the theme's text keys.
  `'400'` often renders heavier than a reference's light body — re-measure your own render and step down
  if so.
- **Don't conflate color with weight.** A glyph that looks "too light" may be a wrong base **color** (or
  a sub-pixel stroke antialiasing to gray) rather than a too-thin weight.
- **Verify BOTH, by measurement:** the rendered role's **stroke width** ≈ the reference's, AND its
  **dark-core color** ≈ the reference's.
- **Verify a glyph's drawn ink, not its declared size.** An SVG's size prop sizes the box, not the
  paths: paths that don't reach the viewBox edges render smaller than the box, so a size check passes
  while the glyph reads undersized — and the squeezed ink is proportionally denser, so an ink-ratio
  check simultaneously reads it as too heavy. Measure the ink bounding box on both sides; if the
  declared sizes match and the ink boxes don't, the fix is in the path data or the viewBox, not the
  size prop.

### Follow EVERY color from the reference — sample it, don't guess (and sample each sub-part)

**Sample every color off the reference and apply the measured value** — background/wallpaper, bubble
fills, composer bar, each glyph, borders, **and the read-receipt ticks**. Don't assume a "known" brand
color.
- **Multi-part elements have more than one color — sample each part separately.** A two-tone control
  (e.g. a gray circle with a white arrow) is easy to invert if you guess.
- **Sampling gotcha:** small colored UI elements get swamped by similar colors in **photo attachments**
  (blue ticks vs. a blue sky — the photos can hold 200k blue pixels vs. ~800 tick pixels). Isolate the
  element (restrict the search to its context, e.g. tick pixels on the bubble rows, not the photo rows)
  and sample the saturated **core**, not the antialiased edges.
- **A background may be a TEXTURE, not a flat color.** Sample **many** points across it: uniform (low
  std-dev) → flat fill → a color key; varying (faint repeated marks, small std-dev, darker mins) → a
  **pattern** → reproduce it as a tiled background component. Bundle the actual asset or a cropped
  patch and tile it; if unavailable, approximate a faint motif and tell the user it's an approximation.
- **Verify by re-sampling YOUR render and diffing against the reference**, per sub-part.
- **When you override an accent/brand colour, override EVERY token that cascades from it**, and treat
  any un-rendered state as hiding a stray default until proven otherwise. Recolouring the common
  surfaces but leaving the SDK default in a less-common state (voice recording → `accentPrimary` /
  `chatWaveformBar`, edit, error, overlays, focus rings) is not a finished theme. Set those tokens even
  for states the reference never shows — that's a code check, not a reason to drive and screenshot the
  state.

**Light/dark carve-out — don't pin structural surfaces to a light-mode literal.** The reference is
almost always a light screenshot. **Pin** the sampled **brand/content** colors (bubble fills, glyphs,
accent, read-receipt ticks) — they're the same in both modes. But keep **structural surfaces**
(message-list background, composer/input background, borders) on the theme's semantic values so they
still adapt; pinning a surface to `white` looks right in light mode and breaks in dark. If the app
supports dark mode, verify both (§3.4).

**A pinned brand accent and an adapted brand-tinted surface are different tokens — never mix the two
inside one element.** A saturated brand fill (outgoing bubble, primary button) pins, and its foreground
pins with it. A pale brand wash used as a card, banner or sheet is a *light surface with brand
character*, not a brand colour, so it adapts — hold the hue, cut saturation, drop lightness. A pale
card pinned into a dark UI becomes the brightest thing on screen; pinning the surface while leaving its
contents semantic collapses label-on-card contrast. When you adapt a surface, adapt every nested
surface and ink with it, and **preserve the light-mode elevation direction** — an inner sheet lighter
than its parent in light must stay lighter in dark, or a raised sheet reads as a well. Verify by
measuring every nested pair in dark: 4.5:1 for text, roughly 1.5:1 for surface against surface where no
shadow is doing the work.

**A knockout inside a glyph is not a colour, it is the surface behind the glyph showing through.** Set
it to the token of whatever surface that glyph actually sits on, pinned or adapted, never to a literal.
A hardcoded white knockout is correct only while the glyph sits on a light surface: when the surface
adapts and the ink lightens, the cutout disappears into the ink and the glyph reads as a solid blob.
This passes every contrast pair a theme check measures, because surface and ink both adapted correctly
and the knockout is not one of the pairs. Detect it by sampling the knockout in both modes; an
identical hex while the surrounding ink changed means it is a literal.

### Region checklist + routing (walk every row)

Walk **every row** in the per-product files below, screen group by screen group. For each region: name
what the design shows, compare it to the Stream RN default, and if it differs, route it to the cheapest
**Axis** that reaches it. Produce an explicit task list — one entry per region that differs.

The **Route to** column names the *mechanism*; **confirm the exact theme key / slot / prop name** in the
manifest-selected docs and the installed package, not from memory.

**Reasoning rules for picking the mechanism** — these catch the *class* of mistake a single fact never
does, so they generalize to regions not yet enumerated:

- **A theme-key / component-slot name is a hint, not a guarantee — confirm the target node in the
  render tree before using it.** Composer/message keys (`wrapper` vs `container` vs `inputBoxWrapper`,
  `MessageContent*` vs `MessageFooter`) do **not** map cleanly to "the thing you mean" by name.
- **A theme key that colours only *part* of a region means you hit an *inner* container.** Partial
  success (a band around the controls, half a surface tinted) doesn't trip the "go investigate" reflex.
  When styling looks partial, read the component's render tree, apply the value to the **outermost
  full-bleed `View`**, and verify by sampling the *margins around* the region, not just its foreground
  controls.
- **Fix the structure before the surface — never fake a structural property with a background fill.**
  Reaching for a hardcoded/sampled background colour to make a region "look right" (a translucent fill
  to fake a floating or blurred pill, a painted strip to fake an overlay) is a defect, not a match. Map
  the difference to the SDK's structural mechanism first — a prop/flag/slot (e.g.
  `messageInputFloating`) — then theme the surface. Resolve the structural axis before cosmetic polish.
- **A large custom build that parallels SDK infrastructure is a red flag — re-read the reference, don't
  proceed.** Before choosing a modal / host replacement / from-scratch surface over an SDK slot,
  **state the SDK's default structure for that region and diff it against the reference**. The SDK
  almost always has a slot; reinvention usually means you misread the reference.
- **Idiomatic ≠ matching, in both directions.** Swapping in an SDK component for correct *behaviour*
  inherits its *appearance* (e.g. the SDK `AttachButton` is a bordered `type="outline"` button) —
  re-decompose the look after the swap. Re-customizing a slot for *appearance* must **reuse the SDK
  component's behaviour logic** (read its `onPress` and replicate it, including subtle branches) rather
  than hand-roll a lossy version.

For every region note: color, background color, border, border radius, padding / gap, typography (font,
weight, font and line size) — save findings to `design-analysis.md`. Unless asked otherwise, remove
`design-analysis.md` after the verification step.

#### Product region tables

| Product | File | Covers |
|---|---|---|
| **Chat** | [`regions-chat.md`](regions-chat.md) | channel list, message chrome, message row, reactions, attachments, composer + deep-dives (bubble radius, metadata in the bubble, long-press menu, composer render tree, Liquid Glass, attachment picker) |
| **Video** | [`regions-video.md`](regions-video.md) | call screen, participant tiles, controls, livestream surfaces |
| **Feeds** | [`regions-feeds.md`](regions-feeds.md) | activity card, composer, comments, follows, notification feed |

Read the ones in scope and walk every row; a Chat build never needs the Video or Feeds rows. The
**cross-cutting** rows below apply to all three — always walk them.

#### Cross-cutting

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Fonts, accent color | — | Theming | theme font / color keys |
| Light/dark behavior | pin brand colors, keep structural surfaces semantic | Theming | build **two palettes** and select on `useColorScheme()` (from `react-native`) |
| Spacing | component overrides | Theming | ensure overridden components have proper spacing, especially inside a rounded message bubble |
| Icons | shape, color, size | Theming or structural | only create custom icons if the shape is truly different (a paperclip instead of a plus); don't swap a mic icon for a slightly different mic icon |

### Common decision points

**Thread scope decision.** A static screenshot usually does **not** show whether threads are in scope:
the thread-reply indicator only renders on messages that already *have* replies, and the reply screen +
thread inbox are **separate screens**. If the reference doesn't clearly show threads and the user hasn't
stated it, **ask one short question and wait**:

> This design doesn't clearly show message threads. Should the app support threads (reply-in-thread + a thread screen), or keep conversations flat?

- **Threads in scope** → implement the Thread Screen (and the thread inbox if the design shows one) per
  the **Thread surfaces** rows in [`regions-chat.md`](regions-chat.md).
- **No threads wanted** → don't merely omit the UI. **Disable thread replies on the `messaging` channel
  type** so the SDK never surfaces a reply-in-thread affordance the design lacks —
  [credentials.md > disable threads](../credentials.md#disable-threads). The message-row override then
  doesn't have to reproduce a thread indicator, and it can legitimately close as
  `N/A - threads disabled on channel type`.

**Composer placement decision — derive it from the reference, don't lead with a yes/no question.**
Whether the composer **floats** (a pill inset from the screen edges, visible side margin, corner radius,
often a shadow, message content visible behind/around it) or **docks** (flush with the bottom edge and
safe area) is **structural**: it maps to `messageInputFloating` on `<Channel>`, and getting it wrong
changes the composer's relationship to the keyboard and the list. **Read the floating cues off the image
first** and decide from them; a bare "floating or docked?" question answered wrong short-circuits the
region analysis and is hard to unwind. Only ask if the cues are genuinely ambiguous *after* you've
examined them, and re-verify against the image on every build:

> The floating-vs-docked cues in this reference are ambiguous (I can't tell if the input floats inset above the content or docks flush at the bottom). Which is it?

State the result as a task list: `Region -> default vs. target -> mechanism (theme key / component
override / prop-or-hook / already-default)`. Implement **all** differing regions, not just the cheap
theming ones.

---

## Step 2: Map design-implied features to optional native packages

A screenshot signals a *capability*, not just a look, and some Step-1 regions aren't reachable by
theming or a component override alone. Voice-recording UI or an audio waveform, inline video with a play
button, a composer camera button, a device photo grid or attachment sheet, file/document rows, a share
affordance — each needs a **native capability package** installed first, or the region fails at the
behavior level however well you style the slot.

Walk the Step-1 task list, flag every region whose **capability** the design requires, and install from
the matrix for the product — each lists packages per runtime lane plus permission and re-link notes:

- **Chat** → [`../builder.md`](../builder.md#chat---optional-packages-by-capability)
- **Video** → [`../builder.md`](../builder.md#video---optional-capabilities)

Install only what the design actually implies — do NOT bulk-install the whole matrix for one vague
signal. If a region needs a package the app doesn't have, install it (or flag it if you can't) **before
implementing that region** — otherwise it is a `GAP`, not a match.

**Kick off the native build NOW — as soon as the Stream packages + peers are installed.** The native
build (`npx expo prebuild --clean` + `expo run:ios`, or the RN CLI equivalent) is the single most
expensive step and it is where the **native peers actually get exercised**, so starting it early both
overlaps it with implementation and surfaces native/peer failures immediately.

---

## Step 3: Verify against the reference — region by region (mandatory)

**Rules — all of them, every run:**

- A match is **not done** until the app runs and the render is compared to the reference. Verify
  **size, position, proportion, and structure**, not just presence and colour.
- Walk the **whole** Step-1 checklist. Don't stop at the regions that happen to look right.
- **Numbers alone lie.** A glyph box can match (±1 logical px) while the field is too tall, a stroke too
  heavy, filled instead of outlined, or a control off-centre. Always compare visually too.
- Any throwaway scaffold added to reach a screen must be **DELETED before delivery** (remove the
  branch/flag/import, don't merely disable it), then the real path re-verified.
- **Regression adjacency — re-verify *every* facet of a region after *any* change.** Fixing one facet
  (structure / appearance / behaviour) routinely breaks a neighbour one layer down (rebuilding the
  picker breaks the attach button's look; restyling the button breaks its toggle behaviour). After each
  fix, re-check the region's other facets **and both of its states**.
- **Iterate until every region passes.** Fix, re-run, re-compare; never declare done on the first render.
- If you genuinely cannot run the app, say so plainly and list which regions are
  implemented-but-unverified — never imply a match you did not see.
- **Never deliver a region left at its default and call it a "known gap."** Report a region unmatched
  only when it is genuinely impossible (say what + why), and prove impossibility by *attempting* it.

**How to run the loop:** [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) — build + launch
tap-free (§1), stale-bundle trap (§2), reaching non-initial screens (§3), driving composer/picker states
(§4), poll-before-screenshot (§5), dark mode (§6). `simctl` cannot tap.

### 3.1 Seed data that triggers every region

An empty or one-message channel hides exactly the elements that get dropped. The test channel needs:
**an incoming and an outgoing** message; a **run of 3+ consecutive messages from the same author**
(grouping + the avatar rule); a **photo album**; a message **with reactions**; a **reply / thread**; a
**long multi-line** message. Mark messages read if the design shows read receipts. Seed via the Stream
CLI / [`../credentials.md`](../credentials.md).

**Multi-day date separators ("Yesterday", "May 29") can't be fresh-seeded** — the seed API stamps
everything today, so only a "Today" separator appears.

### 3.2 Screenshot every screen, then check it

Screenshot the **channel list**, the **message screen**, and the **thread screen**. Each region's own
target attributes live in the Step-1 checklist and the per-product region file; on top of those, check
these — every time:

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

**Composer gate — do NOT leave the composer until all pass.** Verify **structure**, not just
presence/colour:
- [ ] **Floating vs docked matches the reference.** If it floats, `messageInputFloating` is set on
  `<Channel>` — and the pill is NOT a docked bar with a painted translucent fill faking the float. If it
  docks, it sits flush to the bottom edge.
- [ ] **Three states are MANDATORY — at-rest, typing, picker-open**
  ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §4). At-rest and typing share one slot
  (`OutputButtons`), and typing is the **only** state that renders the send button — drive it with
  `useMessageComposer().textComposer.setText('hello')`. Picker-open is where the composer↔sheet spacing
  and the `+`↔keyboard swap are visible.
- [ ] **Every OTHER state — keyboard-up, voice-recording, edit mode — only if a reference screenshot
  shows it** (§4). The defects they would catch (unset `audioRecordingEnabled`, a composer pushed
  off-screen) all show up at rest. If a reference does show one, check its own tokens — the recorder
  tints from `semantics.accentPrimary` + `semantics.chatWaveformBar`, so overriding `accentPrimary`
  alone can leave the waveform on the default.
- [ ] **Background fills EDGE-TO-EDGE and through the bottom safe area** — sample pixels in the *margin
  around* the controls. A band hugging the buttons = you coloured `container`, not `wrapper`.
- [ ] **Single-line input is vertically centred** in the pill (grown via `inputBox` padding, not wrapper
  height).
- [ ] **Attach button:** correct look (borderless vs bordered) **and** the `+`↔keyboard swap when the
  picker opens, wired to a `toggleAttachmentPicker` replica.
- [ ] Each glyph matches the reference's size, weight, fill-vs-outline character (compare ink ratio, not
  just the box), and colour.

### 3.3 Build the comparison table

For each region from `design-analysis.md`: target attribute (size / position / colour / presence) →
what rendered → **PASS / FAIL**.

For the high-detail regions (the composer especially), back the numbers with a visual stack: screenshot
on the **same device class** (same `@2x`/`@3x`), crop **both** bars at **native resolution** (same scale
→ no resizing, so sizes compare 1:1), and stack them:

```bash
magick "$REF"  -crop ${W}x210+0+${refY}  +repage ref.png    # reference region
magick "$MINE" -crop ${W}x210+0+${mineY} +repage mine.png   # your render (find Y via the field-band script)
magick ref.png mine.png -background black -append compare.png  # stack; view it
```

On the stack, check what the numbers miss — field height/compactness, stroke weight, vertical centring
of each control, overall balance — then re-measure to confirm fixes.

### 3.4 Check dark mode

If the app supports dark mode, **both modes are verified on the same build** — no rebuild. Flip the OS
appearance at runtime and re-screenshot per
[SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §6 (shoot light first, then poll until the frame
changes *and* settles).

Then confirm the **light/dark carve-out** from Step 1 held:

- [ ] **Structural surfaces** (message-list background, composer/input background, borders) flipped to
  their dark values. One that stayed light is a pinned-to-literal bug.
- [ ] **Pinned brand/content** colours (bubble fills, glyphs, accent, read-receipt ticks) look identical
  to light mode. One that washed out was pinned wrong.
- [ ] Text and glyphs still have contrast against the flipped surfaces — sample both modes.
- [ ] No element mixes a pinned brand accent with an adapted brand-tinted surface (Step 1) — every
  nested pair measures 4.5:1 for text, ~1.5:1 surface-on-surface, with the light-mode elevation
  direction preserved.
- [ ] No glyph **knockout** is a literal — sample it in both modes; an identical hex while the
  surrounding ink changed means it never resolved (Step 1).
- [ ] Any colour reaching the screen through a `WithComponents` slot override was verified on a **cold
  launch**, not a runtime flip ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §6).
