# Stream React Native — matching a reference design (Chat · Video · Feeds) (screenshot / Figma / "make it look like X")

When the user gives a **target appearance** - an attached screenshot, a Figma frame, or "make the
app look like \<app\>" - the job is **not** "set a few
colors." A reference design is a **checklist of regions**, and real designs differ from Stream's
defaults in *layout* and *behavior*, not just color: the composer button set, where the timestamp
and read receipts sit, the bubble shape, the header, the date separators. Changing the bubble color
and calling it done is the classic failure - do not repeat it.

The region checklist below covers **Chat, Video, and Feeds** surfaces, grouped under a product header

Run this page **before** writing code, in addition to (not instead of) the normal `DOCS.md` lookup
in [SKILL.md](../SKILL.md). It is the *procedure* + the *routing map*; the exact theme keys and
component names come from the manifest-selected docs and the installed package, not from memory.

**Implement EVERY region - the composer is first-class, not optional.** Do not deliver a partial
match and label the rest "known cosmetic gaps." "Risky" or "more effort" is not a reason to skip a
region; only genuine impossibility is, and then you say exactly what and why. The composer is the
region most often left at its default and is exactly where users notice the mismatch.

**Banned as a resolution:** the strings *"acceptable approximation", "minor", "difference noted",
"close enough", "keep default"*. Each decomposed region ends **Fixed** or **Impossible: \<concrete
reason\>** — nothing in between. (These exact hand-waves shipped ~10 real per-region defects.)

**Screenshots verify appearance, not interaction.** `simctl` can't tap, so a screenshot diff never
exercises press/`onSelect`/navigation. Any custom slot with a tap handler (custom `ChannelPreview`,
message press, buttons) must be verified by *driving* it (temp auto-nav / device), not eyeballed — a
custom `ChannelPreview` that read `onSelect` from props (instead of `useChannelsContext`) silently
no-op'd channel-tap and was invisible to the screenshot loop.

---

## Work in batches - don't let a full match take all day

- **Decompose all regions first**, then read the theme tree and the component slots you'll need in
  **one** pass (manifest-selected theming + customization pages, plus the installed package's
  `Theme` type and component names). Pull the theme paths and slot names up front; don't drip-feed
  lookups while coding.
- **Implement all differing regions, THEN build/run once.** Don't rebuild-and-screenshot after each
  tiny edit - batch a round of fixes, run once, compare once.
- Iterate only on the regions that actually fail.

---

## Three axes of customization (internalize this first)

RN Chat gives you three mechanisms. Map each design difference to the cheapest axis that reaches it,
and preference order: Functional - Theming - Layout / structure.

| Axis | Mechanism | What it changes | What it CANNOT change |
|---|---|---|---|
| **Functional** | Documented component props, channel config, and SDK context hooks (`useMessageContext`...) | Which actions/behaviors are enabled, what's interactive, send/edit/reaction/thread behavior. | Pure appearance (that's theming). |
| **Theming** | The `DeepPartial<Theme>` object passed to **both** `<OverlayProvider value={{ style }}>` **and** `<Chat style={…}>` (see [Theming Blueprint](./CHAT-REACT-NATIVE-blueprints.md#theming-blueprint)) | Colors, fonts, spacing, padding, border-radius, and dimensions - *within the existing layout*. In RN the theme object carries **both** color **and** padding/dimension, so most reskins are theme-only. | The structure - which views render, their arrangement, whether metadata sits inside or below the bubble, which buttons the composer has. |
| **Layout / structure** | Component overrides via `WithComponents overrides={{ … }}` - see the [Component Override Blueprint](./CHAT-REACT-NATIVE-blueprints.md#component-override-blueprint) | The actual views: extend or override parts of the UI | Colors/fonts/spacing that a theme key already reaches (don't replace a component to change a padding). | 

**A theme key that type-checks is NOT evidence that it renders.** `Theme` is a wide type and several of
its keys are dead or partly dead at runtime — the component overwrites them after the theme is applied,
drops them in one of its branches, or never reads them at all. `tsc` is green, the app builds, the
pixel doesn't move, and the natural (wrong) conclusion is "stale bundle". Across four real runs this
was the single largest defect class. **Before trusting any theme key for a region that matters, open the
component in the installed package and confirm the key reaches the rendered style** — and check the
confirmed-dead list in [`regions-chat.md`](regions-chat.md#dead-theme-keys) first.

**Two recurring mis-routings:**
- Solving a **structural** difference with a **theming** token. "Read receipts inside the bubble", "a
  camera button in the composer", "the timestamp overlaid on the image", "an avatar on my own
  messages" are **structural** -> a component override, not a color key.
- Solving a **spacing / padding / radius** difference by **overriding a component**. In RN those live
  in the **theme object** - reach for the theme key first; only override the component when the
  *arrangement* itself must change.

**RN-specific: the channel header is app-owned.** Unlike other Stream SDKs, RN Chat has no
`ChannelHeader` slot baked into `Channel` - the nav header is **your** React Navigation
`Stack.Screen options` / Expo Router header (or a custom view above `MessageList`). Header
differences route to the **navigation layer**, not the theme. Match its height, title, subtitle, and
trailing affordances there; drive the title from channel state, never a hardcoded literal (every
channel would show the same wrong title).

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
-> compare loop in Step 3 is by far the most expensive part of a design match. Every region you name,
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
[`../sendbird-migration.md`](../sendbird-migration.md) §0c/§6.

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

### Region checklist + routing (walk every row)

Walk **every row** below, screen group by screen group. For each region: name what the design shows,
compare it to the Stream RN default, and if it differs, route it to the cheapest **Axis** that
reaches it (per [Three axes](#three-axes-of-customization-internalize-this-first)). Produce an
explicit task list - one entry per region that differs. Don't skip a region because it "looks
standard"; verify it against the default.

The **Route to** column names the *mechanism*; **confirm the exact theme key / slot / prop name** in
the manifest-selected docs and the installed package, not from memory. For the rules behind each axis
see the [Theming Blueprint](./CHAT-REACT-NATIVE-blueprints.md#theming-blueprint) and the
[Component Override Blueprint](./CHAT-REACT-NATIVE-blueprints.md#component-override-blueprint).

For every region note the followings: color, background color, border, border radius, padding / gap, typography (font, font weight, font and line size) - save findings to a file called `design-analysis.md`. Unless asked otherwise, remove the `design-analysis.md` after the verification step.

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
| Light/dark behavior | pin brand colors, keep structural surfaces semantic | Theming | Build **two palettes** and select on `useColorScheme()` (from `react-native`); pin brand/content, keep surfaces semantic (light/dark carve-out above). **Verify by flipping the OS appearance** and re-screenshotting — see the dark-mode toggle in [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md); confirm surfaces flip while pinned brand colors hold. |
| Spacing | component overrides | Theming | Ensure that overriden components have proper spacing; especially inside a rounded message bubble. |
| Icons | shape, color, size | Theming or structural | Only create custom icons if the shape is truly different (for example paperclip instead of plus); don't change a mic icon with another, slightly different mic icon |

### When the reference is inconclusive - ask, don't guess

**Thread scope decision.** A static screenshot usually does **not** decisively show whether threads
are in scope: the thread-reply indicator only renders on messages that already *have* replies, and
the reply screen + thread inbox are **separate screens** a message-list shot never captures. So
absence of a thread indicator is not evidence threads are unwanted. If the reference doesn't clearly
show threads and the user hasn't stated it, **ask one short question and wait** before building or
dropping them:

> This design doesn't clearly show message threads. Should the app support threads (reply-in-thread + a thread screen), or keep conversations flat?

- **Threads in scope** -> implement the Thread Screen (and the Thread List / inbox if the design
  shows one) as routed in the Step 1 **Thread surfaces** table (deep-dive in Step 2).
- **No threads wanted** -> don't merely omit the UI. **Disable thread replies on the `messaging`
  channel type** so the SDK never surfaces a reply-in-thread affordance the design lacks - see
  [credentials.md > disable threads](../credentials.md#disable-threads). With threads disabled at the
  source, the message-row override doesn't have to reproduce a thread indicator, and Step 2.5 can
  legitimately mark it `N/A - threads disabled on channel type`.

**Composer placement decision — derive it from the reference, don't lead with a yes/no question.** Whether the composer **floats** (a pill inset from the screen edges with visible side margin, corner radius, often a shadow, message content visible behind/around it) or **docks** (flush with the bottom edge and safe area) is **structural**: it maps to `messageInputFloating` on `<Channel>`, not a theming tweak, and getting it wrong changes the composer's relationship to the keyboard and the list. **Read the floating cues off the image first** (inset margins, rounded corners, shadow, content behind) and decide from them — do **not** open with a bare "floating or docked?" question, because a one-time answer given wrong short-circuits the region analysis and is hard to unwind (you end up faking the look instead of re-deriving it). Only ask if the cues are genuinely ambiguous *after* you've examined them, and re-verify against the image on every build:

> The floating-vs-docked cues in this reference are ambiguous (I can't tell if the input floats inset above the content or docks flush at the bottom). Which is it?

State the result as a task list: `Region -> default vs. target -> mechanism (theme key / component
override / prop-or-hook / already-default)`. Implement **all** differing regions, not just the cheap
theming ones.

---

## Step 1.5: Map design-implied features to optional native packages

Some regions from Step 1 aren't reachable by theming or a component override alone - they need a
**native capability package** installed first. A screenshot signals a *capability*, not just a look:
voice messages, video attachments, a camera button in the composer, a document/file attachment, a
device photo-library picker, or a share action each imply an optional dependency. If the package
isn't installed you can style the slot perfectly and the region still won't work - the match fails at
the behavior level, not the pixel level.

Walk the Step-1 task list and flag every region whose **capability** (not just its appearance) the
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
can't, flag it) **before** Step 2 - otherwise that region is a `GAP`, not a match.

---

## Step 2.5: Overriding a slot inherits ALL of its sub-features

The composite slots - the message row, the composer, the channel-list preview - each render **many**
sub-features. When you override one via `WithComponents`, every sub-feature the default drew
**disappears unless you reproduce it.** A custom row that handles only the case in front of you (one
outgoing text bubble) silently drops attachments, quoted replies, reactions, read receipts,
grouping, and edited/deleted state - and a near-empty test channel hides the loss until the user
spots it.

**Rule:** before overriding a composite slot, read the default component in the installed package, enumerate every sub-view and conditional branch, and for each
decide **reproduce it** (reusing the SDK's own sub-component) or **consciously drop it** (and say so).
Prefer the **narrowest** slot that achieves the change; reach for a full row/composer replacement
only when the *arrangement* truly needs it. Keep custom rows `memo`-ized and read SDK context hooks
(`useMessageContext`, `useMessagesContext`) for data and handlers - do not hand-roll business logic.

**Reusing the SDK's own sub-component is not automatically enough — pass the props its default parent injected.** "Reproduce it" often means rendering the SDK's own sub-component, but a sub-component may read only *part* of its data from context and take the rest from **props that only its default parent supplies**. Render it bare and whatever came from those props silently vanishes — the component still mounts (no error, looks fine at a glance), just missing a field. Canonical case: the default `MessageFooter` pulls `alignment`/`message`/`members`/`showMessageStatus` from `useMessageContext()`, but its **timestamp** comes *only* from a `date` prop — `MessageTimestamp` has **no `message.created_at` fallback**, so `date=undefined` → `getDateString(undefined)` → renders `null`. The SDK's parent renders `<MessageFooter date={message.created_at} />` (`MessageItemView.tsx`); a custom footer that renders `<MessageFooter />` shows read receipts + edited + name but **no timestamp**. **Rule:** before reusing an SDK sub-component, open its *default parent* in the installed source, see exactly which props it passes, and replicate them — context alone may not carry the data.

**Completion contract - fill before you ship (do NOT skip rows).** For **each** region you replace,
list every sub-feature the default rendered and mark it exactly one of:
- **Reproduce it** - reuse the named SDK piece; don't hand-roll it.
- **`N/A - <genuine design reason>`** - a real *design* reason the target doesn't need it (e.g. read
  receipts in an anonymous livestream chat). **"Deferred", "later", "moving fast", "out of scope for
  now" are NOT design reasons and are NOT valid N/A.** For the **thread-reply indicator**
  specifically, `N/A` is valid **only** when threads are actually disabled on the channel type
  (`replies:false`, per the Step 1 thread scope decision); if threads are still enabled server-side
  but you skipped the indicator, that's a `GAP`, not `N/A`.
- **`GAP - not implemented`** - if you are knowingly skipping a needed capability, label it in
  exactly those words so it stays visible. Never relabel a time-skip as `N/A`.

A blank row - or an `N/A` whose real reason is "deferred" - means incomplete.

Typical **custom message row** sub-features to account for: text (markdown/links/mentions/emoji),
attachments (image/file/video/voice/giphy), reactions (display + add), quoted/replied-to parent,
thread-reply indicator, read/delivery receipts on own messages, edited/deleted state, actions menu,
same-author grouping, and error/optimistic-send state. **Custom composer:** text input; attachments
+ upload (and removal); mentions/slash-command autocomplete; send (+ the at-rest↔typing swap); voice
recording (if enabled); edit-message mode.

---

## Step 3: Verify against the reference - region by region (mandatory)

A design match is **not done** until the app runs and the result is compared to the reference.
Presence-and-color is not enough; verify **size, position, and proportion** too.

1. **Seed data that triggers every region.** An empty or one-message channel proves nothing and
   hides exactly the elements that get dropped. Ensure the test channel has: **an incoming and an
   outgoing** message; a **run of 3+ consecutive messages from the same author** (so grouping + the
   avatar rule render); a **photo album**; a message **with reactions**; a **reply / thread**; a
   **long multi-line** message; and enough history that a **date separator** appears. Mark messages
   read if the design shows read receipts. (Use the Stream CLI / credentials flow to seed if needed.)
   **Multi-day date separators ("Yesterday", "May 29") can't be fresh-seeded** — the seed API stamps
   everything "today", so only a "Today" separator appears. To verify cross-day separators, use a
   channel that already has multi-day history or import backdated data server-side; otherwise note the
   dated separators as implemented-but-unverified rather than claiming a match.
2. **Open the real message screen on its actual navigation path** - channel list -> tap -> message
   screen - not a one-channel shortcut that never exercises the header/navigation. If you add any
   throwaway scaffold to reach a screen for a screenshot, **DELETE it before delivery** (remove the
   branch/flag/import - don't merely disable it) and re-verify on the real path. On the iOS simulator
   `simctl` can't tap, so reach non-initial screens with temporary in-code navigation and drive
   composer/picker states via SDK hooks - see the fast loop, stale-bundle trap, and cleanup steps in
   [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md).
3. **Build a comparison table.** For each region from `design-analysis.md` target attribute (size / position /
   color / presence) -> what rendered -> **PASS / FAIL**. Walk the whole checklist; don't stop at the
   regions that happen to look right. **Numbers alone lie** — a glyph box can "match" (±1 logical px)
   while the field is too tall, a stroke too heavy, or a control off-center. So for the high-detail
   regions (the composer especially), screenshot on the **same device class** (same `@2x`/`@3x`), crop
   **both** bars at **native resolution** (same scale → no resizing, so sizes compare 1:1), and stack
   them to eyeball the real differences:
   ```bash
   magick "$REF"  -crop ${W}x210+0+${refY}  +repage ref.png    # reference region
   magick "$MINE" -crop ${W}x210+0+${mineY} +repage mine.png   # your render (find Y via the field-band script)
   magick ref.png mine.png -background black -append compare.png  # stack; view it
   ```
   On the stack, check what the numbers miss — field height/compactness, stroke weight, vertical
   centering of each control, overall balance — then re-measure to confirm fixes.
4. **Re-check the silently-lost ones explicitly, every time:** the **incoming-message avatar** and
   **grouping**; the **nav header** (height, title, back); the **composer in BOTH states** (at-rest
   vs. typing - the send/mic swap) — walk the full *composer verification gate* in the composer
   deep-dive above, including that the **composer background fills edge-to-edge and through the bottom
   safe area** (sample the margin around the controls, not just the controls — a band = you coloured
   `container`, not `wrapper`); **metadata placement** (inside the bubble, not clipped, default footer
   not duplicated); reaction display; attachment rendering. After fixing any one facet of a region,
   re-verify the **other** facets of that same region ([`../RULES.md`](../RULES.md) > regression
   adjacency) — fixes routinely break a neighbour (picker → attach-button look → toggle behaviour).
5. **Iterate until every region passes.** Fix, re-run, re-compare. Don't declare done on the first
   render.
6. If you genuinely cannot run the app, say so plainly and list which regions are
   implemented-but-unverified - never imply a match you did not see.
7. **Do not deliver with a region left at its default and call it a "known gap."** Every region in
   the Step-1 checklist - the composer especially - must be implemented to match. Report something as
   unmatched only when it is genuinely impossible (and say what + why), never merely because it's
   risky or more effort.
