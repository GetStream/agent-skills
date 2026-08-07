# Stream React Native — matching a reference design (Chat · Video · Feeds) (screenshot / Figma / "make it look like X")

Run this page **before** writing code, in addition to (not instead of) the normal `DOCS.md` lookup
in [SKILL.md](../SKILL.md). It is the *procedure* + the *routing map*; the exact theme keys and
component names come from the manifest-selected docs and the installed package, not from memory.

**Banned as a resolution:** the strings *"acceptable approximation", "minor", "difference noted",
"close enough", "keep default"*. Each decomposed region ends **Fixed** or **Impossible: \<concrete
reason\>** — nothing in between. (These exact hand-waves shipped ~10 real per-region defects.)

---

## Don't ship affordances the app can't back

A reference design, a starting template, or a boilerplate example often carries buttons the app
doesn't actually have a feature for - most commonly a **video-call icon** in the header or composer
of an app that only implements chat. If a button has no wired behavior, **remove it** - don't leave
it rendered-but-disabled or wired to a no-op handler. A dead button is worse than no button: it reads
as broken, not as scoped-out.

---

## Step 1: Decompose the reference into regions (every time)

Go region by region. For **each** region: name what the design shows, compare it to the Stream RN
default, and decide **theming / layout / functional / already-default**. Produce an explicit task
list - one entry per region that differs. Do not skip a region because it "looks standard"; verify
it against the default.

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
reference (the original's real pixels) confirms it.

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
9. **No magic numbers — a size that represents a real thing anchors to that thing.** Sizes standing for
   a concrete thing (keyboard, safe area, header, tab bar) anchor to that thing (the SDK default or a
   measured reference value), never to "what feels roomy." When correcting an over/undershoot, reach for
   the simplest static approximation (e.g. an SDK default) *before* any runtime measurement hook — don't
   swing from an arbitrary number to an overwrought measured solution.

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
- **Verify a glyph's drawn ink, not its declared size.** An SVG's size prop sizes the box, not the
  paths. Paths that do not reach the viewBox edges render smaller than the box you set, so a size check
  against the reference passes while the glyph reads undersized. Worse, ink squeezed into less area is
  proportionally denser, so an ink-ratio check reads it as too heavy at the same time: one cause, two
  checks, both misleading. Measure the ink bounding box on both sides. If the declared sizes match and
  the ink boxes do not, the fix is in the path data or the viewBox, not the size prop.

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
- **When you override an accent/brand colour, override EVERY token that cascades from it — and treat any
  un-rendered state as hiding a stray default until proven otherwise.** Recolouring the common surfaces
  but leaving the SDK default in a less-common state (voice recording → `accentPrimary` /
  `chatWaveformBar`, edit, error, overlays, focus rings) is not a finished theme. Set those tokens from
  the theme even for states the reference never shows — that's a code check, not a reason to drive and
  screenshot the state.

**Light/dark carve-out - don't pin structural surfaces to a light-mode literal.** The reference is
almost always a light screenshot. **Pin** the sampled **brand/content** colors (bubble fills,
glyphs, accent, read-receipt ticks) - they're the same in both modes. But keep **structural
surfaces** (message-list background, composer/input background, borders) on the theme's semantic
values so they still adapt; pinning a surface to `white` looks right in light mode and breaks in
dark. If the app supports dark mode, verify both (§4.4).

**A pinned brand accent and an adapted brand-tinted surface are different tokens — never mix the two
inside one element.** A saturated brand fill (outgoing bubble, primary button) pins, and its foreground
pins with it. A pale brand wash used as a card, banner or sheet is not a brand colour but a *light
surface with brand character*; its dark counterpart is a dark surface with the same character, so it
adapts — hold the hue, cut saturation, drop lightness. Pinning a tint keeps the pigment and loses the
role: a pale card pinned into a dark UI becomes the brightest thing on screen (measured 18.93:1 against
a near-black screen, versus 1.76:1 adapted). The observed defect on two SDKs was pinning the surface
while leaving its contents semantic, collapsing label-on-card contrast to 1.03:1 and 1.58:1. When you
adapt a surface, adapt every nested surface and ink with it, and **preserve the light-mode elevation
direction** — an inner sheet lighter than its parent in light must stay lighter in dark, or a raised
sheet reads as a well. Verify by measuring every nested pair in dark: 4.5:1 for text, roughly 1.5:1 for
surface against surface where no shadow is doing the work.

**A knockout inside a glyph is not a colour, it is the surface behind the glyph showing through.** Set
it to the token of whatever surface that glyph actually sits on, pinned or adapted, never to a literal.
A hardcoded white knockout is correct only while the glyph sits on a light surface: when the surface
adapts and the ink lightens, the cutout disappears into the ink and the glyph reads as a solid blob.
Measured on one icon, the knockout went from 1.36:1 against its own ink in dark to 13.33:1 once
resolved, with light unchanged apart from the knockout pixels themselves. This passes every contrast
pair a theme check measures, because the surface and the ink both adapted correctly and the knockout is
not one of the pairs. Detect it by sampling the knockout in both modes; an identical hex while the
surrounding ink changed means it is a literal.

### Region checklist + routing (walk every row)

Walk **every row** below, screen group by screen group. For each region: name what the design shows,
compare it to the Stream RN default, and if it differs, route it to the cheapest **Axis** that
reaches it. Produce an explicit task list - one entry per region that differs. Don't skip a region because it "looks
standard"; verify it against the default.

The **Route to** column names the *mechanism*; **confirm the exact theme key / slot / prop name** in
the manifest-selected docs and the installed package, not from memory.

**Reasoning rules for picking the mechanism** - these catch the *class* of mistake a single fact never
does, so they generalize to regions not yet enumerated:

- **A theme-key / component-slot name is a hint, not a guarantee — confirm the target node in the
  render tree before using it.** Composer/message keys (`wrapper` vs `container` vs `inputBoxWrapper`,
  `MessageContent*` vs `MessageFooter`) do **not** map cleanly to "the thing you mean" by name. Two
  minutes reading the installed component's source beats a name-based guess that half-works.
- **A theme key that colours only *part* of a region means you hit an *inner* container.** A key that
  "kind of works" (paints a band around the controls, tints half the surface) is more dangerous than
  one that does nothing, because partial success doesn't trip the "go investigate" reflex. When styling
  looks partial, read the component's render tree and apply the value to the **outermost full-bleed
  `View`**, then verify the whole surface — sample the *margins around* a region, not just its
  foreground controls.
- **Fix the structure before the surface — never fake a structural property with a background fill.**
  If you're reaching for a hardcoded/sampled background colour to make a region "look right" (a
  translucent fill to fake a floating or blurred pill, a painted strip to fake an overlay), stop: a
  painted fill masking a structural difference is a defect, not a match. Map the difference to the
  SDK's structural mechanism first — a prop/flag/slot (e.g. `messageInputFloating` for a floating
  composer) — then theme the surface. Resolve the structural axis (floating, overlay, slot) *before*
  cosmetic polish (glass, exact colours), not after.
- **A large custom build that parallels SDK infrastructure is a red flag — re-read the reference, don't
  proceed.** A knowledge-backed decision can still rest on a wrong premise (a misread screenshot), and
  knowing the API makes the wrong path *feel* informed so it never trips the "look this up" reflex.
  Before choosing a modal / host replacement / from-scratch surface over an SDK slot, **state the SDK's
  default structure for that region and diff it against the reference**. The SDK almost always has a
  slot; reinvention usually means you misread the reference.
- **Idiomatic ≠ matching, in both directions.** Swapping in an SDK component for correct *behaviour*
  inherits its *appearance* (e.g. the SDK `AttachButton` is a bordered `type="outline"` button) —
  re-decompose the look after the swap. Re-customizing a slot for *appearance* must **reuse the SDK
  component's behaviour logic** (read its `onPress` and replicate it, including subtle branches) rather
  than hand-roll a lossy version.

For every region note the followings: color, background color, border, border radius, padding / gap, typography (font, font weight, font and line size) - save findings to a file called `design-analysis.md`. Keep it until the Step 4 verify loop passes; unless asked otherwise, remove it after that.

#### Product region tables

The rows are split per product so a build only loads the surfaces it touches:

| Product | File | Covers |
|---|---|---|
| **Chat** | [`regions-chat.md`](regions-chat.md) | channel list, message chrome, message row, reactions, attachments, composer — plus 4 deep-dives (metadata in the bubble, long-press menu, composer render tree, Liquid Glass) |
| **Video** | [`regions-video.md`](regions-video.md) | call screen, participant tiles, controls, livestream surfaces |
| **Feeds** | [`regions-feeds.md`](regions-feeds.md) | activity card, composer, comments, follows, notification feed |

Read the ones in scope and walk every row. A Chat build never needs the Video or Feeds rows.
**Cross-cutting** rows below apply to all three — always walk them.


#### Cross-cutting

Applies across all products.

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Fonts, accent color | — | Theming | theme font / color keys |
| Light/dark behavior | pin brand colors, keep structural surfaces semantic | Theming | Build **two palettes** and select on `useColorScheme()` (from `react-native`); pin brand/content, keep surfaces semantic (light/dark carve-out above). |
| Spacing | component overrides | Theming | Ensure that overriden components have proper spacing; especially inside a rounded message bubble. |
| Icons | shape, color, size | Theming or structural | Only create custom icons if the shape is truly different (for example paperclip instead of plus); don't change a mic icon with another, slightly different mic icon |

### Common decision points

**Thread scope decision.** A static screenshot usually does **not** decisively show whether threads
are in scope: the thread-reply indicator only renders on messages that already *have* replies, and
the reply screen + thread inbox are **separate screens** a message-list shot never captures. So
absence of a thread indicator is not evidence threads are unwanted. If the reference doesn't clearly
show threads and the user hasn't stated it, **ask one short question and wait** before building or
dropping them:

> This design doesn't clearly show message threads. Should the app support threads (reply-in-thread + a thread screen), or keep conversations flat?

- **Threads in scope** -> implement the Thread Screen (and the Thread List / inbox if the design
  shows one) as routed in the Step 1 region table.
- **No threads wanted** -> don't merely omit the UI. **Disable thread replies on the `messaging`
  channel type** so the SDK never surfaces a reply-in-thread affordance the design lacks - see
  [credentials.md > disable threads](../credentials.md#disable-threads). With threads disabled at the
  source, the message-row override doesn't have to reproduce a thread indicator, and Step 3's completion
  contract can legitimately mark it `N/A - threads disabled on channel type`.

**Composer placement decision — derive it from the reference, don't lead with a yes/no question.** Whether the composer **floats** (a pill inset from the screen edges with visible side margin, corner radius, often a shadow, message content visible behind/around it) or **docks** (flush with the bottom edge and safe area) is **structural**: it maps to `messageInputFloating` on `<Channel>`, not a theming tweak, and getting it wrong changes the composer's relationship to the keyboard and the list. **Read the floating cues off the image first** (inset margins, rounded corners, shadow, content behind) and decide from them — do **not** open with a bare "floating or docked?" question, because a one-time answer given wrong short-circuits the region analysis and is hard to unwind (you end up faking the look instead of re-deriving it). Only ask if the cues are genuinely ambiguous *after* you've examined them, and re-verify against the image on every build:

> The floating-vs-docked cues in this reference are ambiguous (I can't tell if the input floats inset above the content or docks flush at the bottom). Which is it?

State the result as a task list: `Region -> default vs. target -> mechanism (theme key / component
override / prop-or-hook / already-default)`. Implement **all** differing regions, not just the cheap
theming ones.

---

## Step 2: Install the dependencies the design implies

A screenshot signals a *capability*, not just a look, and some Step-1 regions aren't reachable by
theming or a component override alone. Voice-recording UI or an audio waveform, inline video with a
play button, a composer camera button, a device photo grid or attachment sheet, file/document rows, a
share affordance - each needs a **native capability package** installed first. Style the slot
perfectly without it and the region still fails, at the behavior level rather than the pixel level.

Walk the Step-1 task list, flag every region whose **capability** the design requires, and install
from the matrix for the product - each lists packages per runtime lane plus permission and re-link
notes:

- **Chat** -> [`../builder.md`](../builder.md#chat---optional-packages-by-capability)
- **Video** -> [`../builder.md`](../builder.md#video---optional-capabilities)

Install only what the design actually implies - do NOT bulk-install the whole matrix for one vague
signal. If a region needs a package the app doesn't have, install it (or flag it if you can't)
**before implementing that region** - otherwise it is a `GAP`, not a match.

**Kick off the native build NOW - as soon as the Stream packages + peers are installed - don't wait
for the implementation to finish.** The native build (`npx expo prebuild --clean` + `expo run:ios`, or
the RN CLI equivalent) is the single most expensive step (minutes, not seconds) and it is where the
**native peers actually get exercised**, so starting it early buys two things: (a) the build runs in
the background *while* you implement touchpoints, overlapping the two slow phases
instead of serialising them; and (b) it surfaces native/peer failures immediately.

---

## Step 3: Commit the plan, and verify every name against the installed package

Step 1 said *what the reference looks like*; this step commits *how you will build it* and proves each
mechanism exists before you rely on it. Both halves are cheap here and expensive after the build.

**Give `design-analysis.md` a `Plan` column: the exact SDK feature/mechanism each region will use.**
The region spec captures *what the reference looks like*; the `Plan` column commits *how you will
reproduce it* before you write any UI - one entry per region naming the concrete mechanism: the theme
key (`semantics.chatBgOutgoing`, `channelPreview.unreadContainer`, …), the `WithComponents` slot
(`MessageAuthor`, `ChannelPreviewAvatar`, `MessageContentBottomView`, `MessageComposerLeadingView`, …),
the `<Channel>` prop (`messageInputFloating`, `audioRecordingEnabled`, …), or a documented hook/config -
plus the axis (theming / layout / functional) and whether it's an SDK default that already matches.
Table shape: `Region | Spec (measured) | Plan (SDK feature) | Axis | Status`. This turns the design
match into a resolved build plan, and pre-empts the *reinvention red flag* above - if the Plan is
"custom component from scratch", re-check whether an SDK slot already covers it. Confirm each named
key/slot/prop against the installed package before relying on it.

**Verify every name you just wrote against the installed package.** A theme key, slot or prop that
type-checks is not evidence that it renders (`Theme` is a wide type and several keys are dead or partly
dead at runtime), and a prop's default in guidance is not its default in the pinned source. For each row
of the `Plan` column, open the component in `node_modules` for the pinned version and confirm the value
reaches the rendered style. A `Plan` full of unverified names is the single largest defect class in real
runs — `tsc` is green, the app builds, the pixel doesn't move, and it reads like a stale bundle.

**Completion contract — a custom component for a prebuilt region must reproduce every sub-feature the
default drew.** Overriding a composite slot silently drops what you don't re-render. Before writing one,
list what the default draws in that region and mark each entry **Reproduced** or **`N/A - <reason>`**:
avatar, grouping, sender name, reactions, quoted/inline reply, delivery/read receipts, timestamp,
edited/deleted state, attachments, pinned/saved status. A dropped sub-feature is a FAIL found at Step 4,
not a design choice — and "the region looks right" is exactly how one gets missed.

## Step 4: Verify against the reference - region by region (mandatory)

**Rules - all of them, every run:**

- A match is **not done** until the app runs and the render is compared to the reference.
  Presence-and-colour is not enough: verify **size, position, proportion, and structure**.
- Walk the **whole** Step-1 checklist. Don't stop at the regions that happen to look right.
- **Numbers alone lie.** A glyph box can match (±1 logical px) while the field is too tall, a stroke
  too heavy, filled instead of outlined, or a control off-centre. Always compare visually too.
- Any throwaway scaffold added to reach a
  screen must be **DELETED before delivery** (remove the branch/flag/import - don't merely disable
  it), then the real path re-verified.
- **Regression adjacency — re-verify *every* facet of a region after *any* change.** Fixing one facet
  (structure / appearance / behaviour) routinely breaks a neighbour one layer down (rebuilding the
  picker breaks the attach button's look; restyling the button breaks its toggle behaviour). After each
  fix, re-check the region's other facets **and both of its states** before moving on - don't re-verify
  only the facet you just touched.
- **Iterate until every region passes.** Fix, re-run, re-compare; never declare done on the first render.
- If you genuinely cannot run the app, say so plainly and list which regions are
  implemented-but-unverified - never imply a match you did not see.
- **Never deliver a region left at its default and call it a "known gap."** Report a region unmatched
  only when it is genuinely impossible (say what + why), never because it is risky or more effort -
  and prove impossibility by *attempting* it, not by assumption.

**How to run the loop:** [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) - build + launch
tap-free (§1), stale-bundle trap (§2), reaching non-initial screens (§3), driving composer/picker
states (§4), poll-before-screenshot (§5), dark mode (§6). `simctl` cannot tap.

### 4.1 Seed data that triggers every region

An empty or one-message channel proves nothing and hides exactly the elements that get dropped. The
test channel needs: **an incoming and an outgoing** message; a **run of 3+ consecutive messages from
the same author** (grouping + the avatar rule); a **photo album**; a message **with reactions**; a
**reply / thread**; a **long multi-line** message. Mark messages read if the design shows read
receipts. Seed via the Stream CLI / [`../credentials.md`](../credentials.md).

**Multi-day date separators ("Yesterday", "May 29") can't be fresh-seeded** - the seed API stamps
everything today, so only a "Today" separator appears.

### 4.2 Screenshot every screen, then check it

Screenshot the **channel list**, the **message screen**, and the **thread screen**. Each region's own
target attributes live in the Step-1 checklist and the per-product region file; on top of those, check
the ones that get silently lost - every time:

**All screens**
- [ ] **Nav header** - height, title, back affordance (app-owned, not the SDK's).

**Channel list**
- [ ] Preview row: avatar, name, preview text, timestamp, unread badge, row background.

**Message screen**
- [ ] **Incoming-message avatar** and **grouping** across the 3+ same-author run.
- [ ] **Metadata placement** - inside the bubble, not clipped, default footer not duplicated.
- [ ] Reaction display and attachment/album rendering.
- [ ] Wallpaper/background, date separator.

**Thread screen**
- [ ] Parent message + reply list render, and the thread's own header/composer match the main screen.

**Composer gate - do NOT leave the composer until all pass (the recurring defect).** Verify
**structure**, not just presence/colour; a region can render the right pixels and still be
structurally wrong:
- [ ] **Floating vs docked matches the reference.** If it floats, `messageInputFloating` is set on
  `<Channel>` - and the pill is NOT a docked bar with a painted translucent fill faking the float. If
  it docks, it sits flush to the bottom edge.
- [ ] **Three states are MANDATORY - at-rest, typing, picker-open**
  ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §4). At-rest and typing share one slot
  (`OutputButtons`), and typing is the **only** state that renders the send button - drive it with
  `useMessageComposer().textComposer.setText('hello')`. Picker-open is where the composer<->sheet
  spacing and the `+`<->keyboard swap are visible.
- [ ] **Every OTHER state - keyboard-up, voice-recording, edit mode - only if a reference screenshot
  shows it** (§4). Don't drive them speculatively: the defects they would catch (unset
  `audioRecordingEnabled`, a composer pushed off-screen) all show up at rest. If a reference does show
  one, check its own tokens - the recorder tints from `semantics.accentPrimary` +
  `semantics.chatWaveformBar`, so overriding `accentPrimary` alone can leave a waveform on the default.
- [ ] **Background fills EDGE-TO-EDGE and through the bottom safe area** - sample pixels in the
  *margin around* the controls, not just the controls. A band hugging the buttons = you coloured
  `container`, not `wrapper`.
- [ ] **Single-line input is vertically centred** in the pill (grown via `inputBox` padding, not
  wrapper height).
- [ ] **Attach button:** correct look (borderless vs bordered) **and** the `+`<->keyboard swap when the
  picker opens, wired to a `toggleAttachmentPicker` replica.
- [ ] Each glyph matches the reference's size, weight, fill-vs-outline character (compare ink ratio,
  not just the box), and colour.

### 4.3 Build the comparison table

For each region from `design-analysis.md`: target attribute (size / position / colour / presence) ->
what rendered -> **PASS / FAIL**.

For the high-detail regions (the composer especially), back the numbers with a visual stack:
screenshot on the **same device class** (same `@2x`/`@3x`), crop **both** bars at **native
resolution** (same scale -> no resizing, so sizes compare 1:1), and stack them:

```bash
magick "$REF"  -crop ${W}x210+0+${refY}  +repage ref.png    # reference region
magick "$MINE" -crop ${W}x210+0+${mineY} +repage mine.png   # your render (find Y via the field-band script)
magick ref.png mine.png -background black -append compare.png  # stack; view it
```

On the stack, check what the numbers miss - field height/compactness, stroke weight, vertical centring
of each control, overall balance - then re-measure to confirm fixes.

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

If the app supports dark mode, **both modes are verified on the same build** - no rebuild. Flip the OS
appearance at runtime and re-screenshot per
[SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §6 (shoot light first, then poll until the frame
changes *and* settles - the re-render is not instant).

Then confirm the **light/dark carve-out** from Step 1 held:

- [ ] **Structural surfaces** (message-list background, composer/input background, borders) flipped to
  their dark values. One that stayed light is a pinned-to-literal bug.
- [ ] **Pinned brand/content** colours (bubble fills, glyphs, accent, read-receipt ticks) look identical
  to light mode. One that washed out was pinned wrong.
- [ ] Text and glyphs still have contrast against the flipped surfaces - sample both modes, don't eyeball.
- [ ] No element mixes a pinned brand accent with an adapted brand-tinted surface (Step 1) - and every
  nested pair measures 4.5:1 for text, ~1.5:1 surface-on-surface, with the light-mode elevation
  direction preserved.
- [ ] No glyph **knockout** is a literal - sample it in both modes; an identical hex while the
  surrounding ink changed means it never resolved (Step 1).
- [ ] Any colour reaching the screen through a `WithComponents` slot override was verified on a
  **cold launch**, not a runtime flip ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §6).
