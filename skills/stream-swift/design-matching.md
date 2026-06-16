# Stream Swift - matching a reference design (screenshot / Figma / "make it look like X")

When the user gives a **target appearance** - an attached screenshot, a Figma frame, or "make the chat look like WhatsApp / iMessage / Telegram / Slack" - the job is **not** "set a few colors." A reference design is a **checklist of regions**, and most real designs differ from Stream's defaults in *structure*, not just color: the composer buttons, where the timestamp and read receipts sit, the bubble shape/tail, the header, the date separators. Changing the bubble color and the wallpaper and calling it done is the classic failure - do not repeat it.

**Implement EVERY region - the composer is first-class, not optional.** Do not deliver a partial match and label the rest "known cosmetic gaps" / "minor, skipped." If a region needs a relayout (moving the send/voice/camera buttons out of the field, adding an in-field sticker glyph, metadata inside the bubble), do the relayout - reuse the SDK's public views and wire the real closures rather than punting. "Risky" or "more effort" is not a reason to skip; only genuine impossibility is, and then you say exactly what and why. The composer is the region most often left at its default and is exactly where users notice the mismatch.

This page is the procedure + the routing map. Run it **before** writing code, in addition to (not instead of) the normal docs lookup in [`SKILL.md`](SKILL.md).

## Work in batches - a full match is many regions; do not let it take all day

The slow way is one grep / one read / one build per question. Batch instead:
- **Ground the version + checkout ONCE** (Step 3), then **read every canonical file you'll need in a single pass** - `ViewFactory.swift` (all slots), `DefaultViewFactory.swift` (defaults), `Styles.swift` (the modifiers + `RegularStyles`), the `Appearance`/`ColorPalette` tokens, and the **default view of each slot you intend to override**. Pull all the signatures/Options fields up front; don't drip-feed greps while coding.
- **Decompose all regions, then implement all of them, THEN build once.** Don't build-and-screenshot after each tiny edit - batch the fixes for a round, rebuild once, screenshot once.
- **Reuse a persistent `-derivedDataPath`** (e.g. `/tmp/<app>-dd`) so builds are incremental, **pin one already-booted simulator by UDID**, and take **one** screenshot after a short fixed settle (image loads/animations) - not a long loop of throwaway screenshots. Iterate only on regions that actually fail.

---

## Three axes of customization (internalize this first)

There are **three** independent axes, not two. Missing the third (`Styles`) is why "the padding is too big" looks unfixable - it lives in neither theming nor a `ViewFactory` slot.

| Axis | Mechanism | What it can change | What it CANNOT change |
|---|---|---|---|
| **Theming** | `Appearance` (`ColorPalette`, `Fonts`/`FontsSwiftUI`, `Images`) injected into the `StreamChat` wrapper | Colors, fonts, icon **glyphs** (`Appearance.images`), some radii/spacing tokens - *within the existing layout* | The structure; and **insets/padding/corner-radius of bubbles & composer** (that's `Styles`) |
| **Styles** | The `Styles` protocol on `factory.styles` (default `RegularStyles()`); override the `make…ViewModifier` methods | **Insets, padding, corner radius, border, chrome** of: the message bubble (`makeMessageViewModifier`), the **attachment bubble + its insets** (`makeMessageAttachmentsViewModifier` - *this is the green frame thickness around a photo collage*), each attachment **cell** (`makeMessageAttachmentItemViewModifier`), the composer container (`makeComposerViewModifier`), the input field container (`makeComposerInputViewModifier`), composer buttons (`makeComposerButtonViewModifier`) | Which views exist / their arrangement (that's `ViewFactory`) |
| **Structure** | `ViewFactory` slots (override only the `make…` methods you need; defaults come from the `extension ViewFactory`) | The actual views: composer button set, message row layout, metadata position, bubble shape, header contents, date separators, attachment rendering | Colors/fonts (theming); padding/insets (`Styles`) |

Two recurring mis-routings:
- Solving a **structural** difference with a **theming** token. "Read receipts inside the bubble", "a + button on the left of the composer", "a camera and mic button", "a bubble tail", "timestamp overlaid on the image" are all **structural** -> `ViewFactory`, not `ColorPalette`.
- Solving a **padding / inset / corner-radius** difference with `ViewFactory` or theming. "The green frame around the photos is too thick", "the bubble has too much padding", "the composer field is too tall" are all **`Styles`** -> conform a class to `Styles`, implement the relevant `make…ViewModifier` (plus re-supply RegularStyles' non-defaulted chrome - see the ⚠️ box under "Styles modifiers worth knowing", since `RegularStyles` is not subclassable), and assign it to your factory's `var styles`. The default attachment bubble inset is `spacingXs` on all sides - WhatsApp-style frames are far tighter, so this almost always needs tuning for a photo-grid design.

---

## Step 1: Decompose the reference into regions (every time)

Go region by region. For **each** region: name what the design shows, compare to the Stream default, and decide theming vs. structure vs. already-default. Produce an explicit task list - one entry per region that differs. Do not skip a region because it "looks standard"; verify it against the default.

**Capture measurements, not just identity.** The reference is a *spec*, not a hint. For every region record the concrete attributes you will reproduce: header height + title font size/weight + subtitle; bubble corner radius, tail size, max width, alignment; icon sizes and the gaps between composer buttons; font sizes and weights; paddings; exact colors. "Looks roughly like it" is the failure mode - a placeholder that has the right color but the wrong size, spacing, or alignment fails the eye even though it passes a presence check. Match the numbers.

### How to actually get the dimensions right (do NOT eyeball round numbers)

Picking `25`, `28`, `44` by eye is the recurring failure - the composer is where it shows most (wrong field height, icon sizes, paddings). Use this method instead:

1. **Find the reference's scale, then work in points.** iOS screenshots are `@2x`/`@3x`. Get the pixel size and divide:
   ```bash
   sips -g pixelWidth -g pixelHeight <reference.png>   # e.g. 1179 x 2556
   ```
   1179×2556 ÷ 3 = **393×852 pt** → the shot is **@3x**, so **1 pt = 3 px**. Every element you measure off the image: `points = pixels / scale`. (A status-bar height of ~59px ÷3 ≈ 20pt is a quick sanity check of the scale.)
2. **Extract element sizes AUTOMATICALLY - don't eye them off the image.** `magick`/Python+PIL/numpy are available; use them to threshold the cropped region and read real bounding boxes. Icons are **dark glyphs on a light bar** → threshold dark, project onto columns, cluster into glyphs, measure each box. The field is the **wide near-white band** → its row-span is the field height, its white-column span is the field width. This script (adapt the crop band + thresholds per design) prints points directly:
   ```python
   from PIL import Image; import numpy as np
   im = Image.open(REF).convert("RGB"); W,H = im.size; S = 3.0      # @3x → ÷3
   g = np.asarray(im).astype(int).mean(2)
   band = g[H-380:H, :]                                              # bottom = composer
   # field = rows whose longest near-white run spans >45% of width
   def run(r,t=248):
       b=c=0
       for v in r:
           c=c+1 if v>t else 0; b=max(b,c)
       return b
   wr = np.array([run(g[y]) for y in range(H-380,H)]); ys=np.where(wr>W*.45)[0]+(H-380)
   ft,fb = ys.min(),ys.max(); print("field h", (fb-ft+1)/S, "pt")
   wc = np.where(g[(ft+fb)//2] > 246)[0]; print("field w", (wc.max()-wc.min())/S, "pt")
   dark = (g[ft-6:fb+6,:] < 110); cols=np.where(dark.sum(0)>2)[0]      # icon glyphs
   # cluster contiguous columns (gap>8) → each glyph's w/h in pt
   ```
   Run it on the reference, record each glyph's w/h and the field's h/w in points. **These exact numbers are your spec.**
3. **Controls are almost always SMALLER than you guess - and smaller than the SDK defaults.** A real measurement (WhatsApp @3x reference): leading `+` ≈ **20pt**, in-field sticker ≈ **18pt**, camera ≈ **20pt**, mic ≈ **22pt**, and the **input field ≈ 29pt tall - NOT the SDK's 40pt `defaultInputViewHeight`**. Eyeballing gave 27-44pt every time = "controls too big, composer too tall". So: **measure, then match the measured size; do not fall back to the SDK default field height or round numbers.** SF Symbol `font(.system(size: F))` renders a glyph ≈ `0.8-1.0 × F` pt tall (varies per glyph - the `plus` renders ~0.8×F, so a 20pt plus needs `F≈25`) - start near the measured target and calibrate in step 7. **Match stroke WEIGHT too, not just size** - a thin reference `+` needs `.font(.system(size:F, weight: .light))`, not the default weight, or it reads "too heavy/too big" even at the right height.
4. **The field width is the LEFTOVER - oversized buttons steal it.** The field gets `total − (leading + trailing cluster + gaps)`. If your buttons are too big the field is too narrow (a reported symptom). Size buttons to the measured glyph sizes (small), keep gaps at the token scale (`spacingXs=8`/`spacingMd=16`), and the field reclaims its width (~251pt / ~64% in the reference).
   **Composer field height - `composerConfig.inputViewMinHeight` only NUDGES it; there is an effective ~36-40pt floor.** Set it on the `Utils` you pass to the wrapper, but measure the result - the SDK's `UITextView` (`textContainerInset` + line height + the input view's own padding) floors the *rendered* field around ~40pt regardless: measured 44.7pt at `inputViewMinHeight=32`, only 40.7pt at `18`. So `inputViewMinHeight` + a smaller `inputFont` buys a few points, not a 29pt field.
   ```swift
   var utils = Utils()
   utils.composerConfig.inputViewMinHeight = 18
   utils.composerConfig.inputViewCornerRadius = 16
   utils.composerConfig.inputFont = .systemFont(ofSize: 15)   // needs `import UIKit`
   StreamChat(chatClient: client, appearance: appearance, utils: utils)
   ```
   **To go meaningfully below ~40pt (e.g. a 29pt WhatsApp pill) you must replace the input** - override `makeComposerTextInputView` (or the whole composer via `makeMessageComposerViewType`) with your own fixed-height field, which trades away the SDK text view's auto-grow/mentions/commands. Decide deliberately; tell the user the trade.
5. **Centering: the composer `HStack` is `.bottom`-aligned, so a custom side button centers on the field ONLY if its frame height EQUALS the field's MEASURED RENDERED height.** This is *how you decide centering* - not by eye:
   - A button frame **shorter** than the field sinks to the bottom (glyphs sit low - the "not centered" symptom). Frame each side button (`+`, camera/mic, send) to the **measured rendered field height** (e.g. `.frame(height: 41)` when the field renders 40.7) so the centered glyph lands on the field's centerline.
   - **Do NOT use `.frame(maxHeight: .infinity)` to "fill and center"** - the composer container allows vertical growth, so it **inflates the whole composer** into a giant box (verified failure). Use the fixed measured height.
   - **Default to centering inside the container; do not stack one-sided padding on a slot the SDK already pads.** The in-field trailing slot is wrapped by the SDK with `.padding(.bottom/.trailing, spacingXs)`, which alone ≈ centers an ~18pt glyph in the text. Adding your *own* `.padding(.bottom, n)` on top **compounds** and shoves it up (the "button is a bit up / not centered" bug). Return the bare centered glyph; if a measured offset remains, correct it with a **tiny** nudge (±2pt), not a large guessed pad. Never `maxHeight: .infinity` inside a growable container (inflates it).
   - **Verify centering by measurement, not eye:** find each glyph's center-Y and the field's center-Y (from the field's white-pill row span) and confirm the offset is ≈0. In the WhatsApp reference every glyph offset is ~0; a +5-7pt offset means your frames are too short, and stacked padding shows up as a several-pt offset the other way.

**General rule (not just the composer): center child elements within their container unless the design says otherwise.** Use the container's own centering (frame to its height + `.center`, or a center-aligned stack) rather than hand-tuned asymmetric padding; verify the measured center offset is ≈0.

### Weight is its own dimension - measure and match it (separately from color)
Every glyph has a **weight** (boldness) as well as a size and color, and the eye is sensitive to it ("feels too bold / too thin"). Match it from the reference, don't guess:
- **SF Symbols:** pick the `Font.Weight` that matches the reference - `.font(.system(size: F, weight: .light/.regular/.medium/...))`. A thin reference `+` is `.light`; a heavier glyph `.medium`/`.semibold`. Wrong weight reads "too bold/too thin" even at the right size.
- **Custom stroke glyphs** (`Path().stroke`): **measure the reference's stroke thickness in points** and set `lineWidth` to it - don't pick `0.1×size` by feel. Measure: take a horizontal scan line across the glyph and read the dark-run width = stroke thickness (the WhatsApp sticker stroke is ~1.5pt; rendering it at 2.0pt looks "too bold").
- **Do NOT conflate color with weight - they are independent.** A glyph that looks "wrong color / too light" has either a wrong base **color** or a sub-pixel-thin stroke that antialiases to gray → fix the **color** (and ensure the stroke is ≥~1pt), do **not** over-thicken (that just makes it too bold, a separate defect). A glyph that looks "too bold" has too-wide a stroke / too-heavy a font weight → reduce to the **measured** width/weight; the color stays.
- **Verify both, by measurement:** the rendered glyph's **stroke width** ≈ the reference's, AND its **dark-core color** ≈ the reference's. Two separate checks.

### Follow EVERY color from the reference - sample it, don't guess (and sample each sub-part)
Invented/guessed colors are a recurring miss. **Sample every color off the reference and apply the measured value** - wallpaper, bubble fills, composer bar, each glyph, borders, **and the read-receipt ticks**. Don't assume a "known" brand color: this WhatsApp's read ticks are a **vivid azure `≈#3479F2`**, not the classic cyan `#53BDEB` - only measuring caught it. **Multi-part elements have more than one color - sample each part separately:** the WhatsApp **forward button is a gray circle (`#BDBDBD`) with a WHITE arrow**, not a white circle with a gray arrow - guessing inverted it.
- **Sampling gotcha:** small colored UI elements get swamped by similar colors in **photo attachments** (e.g. blue ticks vs blue sky/water - the photos had 200k blue pixels vs ~800 tick pixels). Isolate the element: restrict the search to its context (e.g. tick pixels that sit on the *green bubble rows*, not the photo rows) before averaging, and sample the saturated **core**, not antialiased edges.
- Verify by sampling your render's colors and diffing against the reference.

### A background may be a TEXTURE, not a flat color - and texture can be what distinguishes two regions
Don't reduce every background to one `Color` - the reference's chat wallpaper is often a **subtle pattern** (WhatsApp's faint doodle icons), and **that texture is what visually separates the chat area from the plain composer** (not a divider line).
- **Detect it:** sample **many** points across the background region. Uniform (low std) → flat fill. Varying (faint repeated marks, std of a few units, darker mins) → a **pattern**; reproduce the pattern, don't flatten it (flattening loses the design's character and erases the chat-vs-composer distinction).
- **Reproduce it:** best is the **actual asset** - bundle the pattern image (or crop a clean patch from the reference) and tile it (`Image(...).resizable(resizingMode: .tile)`). If the art is **proprietary/unavailable**, approximate with a **faint tiled motif** - low-contrast repeated glyphs/shapes (e.g. SF Symbols) over the base color, offset per row for an organic (non-grid) layout - and tell the user it's an approximation, not the exact art. Match the faintness (the WhatsApp doodles are only ~10-15 brightness units off the base).
- **Match the DENSITY, by measurement - a sparse motif reads as "not detailed enough".** Quantify the texture's **ink coverage** = % of pixels in a clean reference patch darker than the base (`(patch < base-6).mean()`), then tune your motif's **cell size + glyph size** and RE-MEASURE your render's coverage until they match (the WhatsApp wallpaper is ~**15.6%** coverage; a first sparse attempt at 70pt cells / 24pt glyphs was only ~5.6% → far too thin; ~40pt cells with varied glyphs hit ~15%). Don't eyeball "looks textured" - measure coverage on both sides.
- **STROKE WIDTH is its own dimension - measure it separately from coverage, or the texture looks "too intrusive / line width too big".** The same coverage % can come from **many hairline marks** (subtle, WhatsApp) or **few thick marks** (bold, wrong) - they look completely different. Measure the reference's stroke width: threshold a clean patch and take the median horizontal **dark-run width** (px → pt at the scale), filtering out large blobs. WhatsApp doodles are **~1.3pt** hairlines; a `.regular`-weight SF-Symbol motif rendered **~3pt** (2.25× too thick) and read as intrusive. Fix: render glyphs at **`.ultraLight`/`.thin`** weight (≈1.0-1.4pt stroke at ~28-34pt) and re-measure your render's stroke until it matches. **Counter-intuitive:** thick strokes also HURT density (fewer/larger glyphs leave big gaps → *lower* coverage), so "dense AND subtle" both come from **many thin marks**, never from bolder strokes - matching coverage by thickening strokes is impossible.
- **Use only PURE-STROKE glyphs for a line-art texture - "no `*.fill`" is NOT enough; many outline symbols have filled SUB-PARTS.** Beyond solid silhouettes (`bolt`, `flame`, `pawprint`, `airplane`, `*.fill`), ordinary "outline" SF Symbols hide filled regions that read as annoying ink blobs/squares/specks even at `.ultraLight` weight (weight thins a stroke but can't hollow a fill): `scissors` (solid blades), `house`/`gift` (a filled box/door square), `camera`/`bell`/`gamecontroller` (solid button dots), `music.note` (notehead), `hurricane`/`tornado` (dense spiral centre that reads as a dot). Curate to glyphs that are PURE outline everywhere - `heart`, `star`, `leaf`, `moon`, `cloud`, `sun.max`, `snowflake`, `bicycle`, `paperplane`, `circle` - and **when unsure, DROP the glyph.**
- **VERIFY fills over the WHOLE texture, not a sample patch - and locate them.** Filled sub-parts are easy to miss by eye and a single clean strip won't contain every glyph (sampling one strip is exactly how `scissors`/`house` slipped through once). Erode the dark mask of the *entire* wallpaper (`m &= shift(m)` 4-neighbour, ~3×): hairline strokes vanish, solid interiors survive. Then **connected-component the survivors** (BFS, no scipy needed), filter out content (photos/bubbles/text/UI by size + position), and **crop+view each remaining wallpaper blob to identify the culprit glyph**, then drop it and re-verify. Iterate until the only survivors are real UI/content - a count alone isn't enough, you must see what each blob is.
- **Reproduce the reference's FULL motif vocabulary, including its fillers - but match what it ACTUALLY uses.** WhatsApp's wallpaper isn't only the big objects; it scatters **small hollow circle RINGS into the gaps** (varied sizes), so add them as a second offset layer or the texture looks emptier/more uniform than the reference. But its circles are *rings, not solid dots* - don't invent filled dots the reference doesn't have (they read as specks the user will call out). Confirm the filler shape against the reference before adding it.
- **Keep the distinction WITHOUT a hard seam:** texture the chat background but keep the composer **plain** (`makeMessageListBackground` textured, `makeComposerViewModifier` a flat fill). Use the **same base color** for both so there's no seam line (see the seam section), while the texture-vs-plain difference provides the visual separation. Over-flattening *both* to one identical flat fill (to kill a seam) erases the intended distinction - the goal is *same base color, different texture*.

### A "weird line" between two regions is almost always a COLOR SEAM, not a divider view
Before hunting for a stray `Divider`, check the obvious cause: a visible line where two regions meet is usually just **two adjacent backgrounds with slightly different fill colors**. (In Stream the message-list↔composer `Divider()` is `.opacity(0)` - it is *not* the culprit; don't chase it.) **How to decide whether a separator should be there:** sample the reference's color on **both sides** of the boundary:
- Equal within a few units → there should be **no** line → make your two backgrounds the **same** color. The classic case: WhatsApp's composer bar (`≈#F3F1EB`) equals its wallpaper (`≈#F2EEE8`), so a distinct composer-bar color (`makeComposerViewModifier`) produces an unwanted seam - set the bar to the wallpaper color (or don't paint a bar).
- Reference shows a deliberate contrasting hairline → reproduce it deliberately (e.g. a 0.5pt separator in the reference's measured color).

   **There are THREE separate line sources at the composer top - rule out all three:**
   - (a) the **color seam** above (composer-bar color ≠ wallpaper);
   - (b) a **real 1pt divider view** - `MessageComposerView.composerDivider`, a `Rectangle` in `colors.borderCoreDefault`, rendered whenever `composerPlacement == .docked` (the `Divider()` in `ChatChannelView` is `.opacity(0)` and is NOT it). A grayish hairline.
   - (c) the **view's base background bleeding through the seam** - `ChatChannelView`'s root `.background(Color(colors.backgroundCoreElevation1))` (≈ white) shows as a faint **white** line where the message-list bg and composer bg meet with a 1px gap. (Tell them apart by color: (b) is gray `borderCoreDefault`, (c) is near-white `backgroundCoreElevation1`.)

   **Decide from the reference** (sample the composer's top-edge row): no hairline there → neutralize whichever sources show, all to the bar/wallpaper color — none have dedicated slots, so set the tokens:
   ```swift
   appearance.colorPalette.borderCoreDefault = wallpaperColor        // kills (b)
   appearance.colorPalette.backgroundCoreElevation1 = wallpaperColor // kills (c) — the WHITE line
   ```
   (Both are otherwise used only by transient overlays / the themed bubble on the message screen, so this is safe.) Verify by scanning **every row** across the **full width** of the composer-top band for a bright/white spike — a center-column probe can miss a 1px line by a few pixels. WhatsApp has no composer divider → neutralize; an app that *does* (e.g. iMessage-ish) → leave/recolor it.
6. **Reuse SDK design tokens for spacing/radius** (`@Injected(\.tokens)`: `spacingXs=8, spacingSm=12, spacingMd=16`; `radiusLg=12, radius2xl=20, radius3xl=24`) so custom views align with the un-overridden parts - but tokens are for **spacing/radius**, not a license to keep the default control/field **sizes**; those come from measurement (step 2-3). Read the container's existing paddings (`MessageComposerView` pads `spacingMd` around the row, `spacingXs` between items) so you don't double-pad.
7. **Verify with a SAME-SCALE SIDE-BY-SIDE CROP - this is the real check; numbers alone lie.** Glyph ink-boxes can "match" (±1pt) while the field is too tall, the strokes too heavy, or things off-center - i.e. it still "doesn't look like the screenshot". So, screenshot on the same device class (also `@3x`), crop **both** composer bars at **native resolution** (both are 3px/pt, so no resizing - sizes compare 1:1), and stack them to eyeball the real differences:
   ```bash
   magick "$REF" -crop ${W1}x210+0+${refY} +repage ref.png      # reference composer bar
   magick "$MINE" -crop ${W2}x210+0+${mineY} +repage mine.png   # your composer bar (find Y via the field-band script)
   magick ref.png mine.png -background black -append compare.png # stack; view it
   ```
   On the stack, check what numbers miss: **field height/compactness, stroke WEIGHT, vertical centering of each control against the field, overall balance.** Then re-measure to confirm the fixes. Loop until the side-by-side reads as the same composer, not just until the numbers match.

Checklist (walk all of these):

**Channel list screen** (if in scope)
- [ ] List header (title, search, buttons) · list item layout · avatar · swipe actions · empty/loading state · background

**Message screen - chrome**
- [ ] Navigation header: title, subtitle, back affordance, trailing avatar/buttons
- [ ] Chat background / wallpaper
- [ ] Date separators (the "Thu, Mar 12" pill) and the new-messages divider
- [ ] Scroll-to-bottom / jump-to-unread overlays

**Message screen - the message itself**
- [ ] Bubble: fill color, border, corner radius, **tail/beak shape**, max width, alignment
- [ ] Bubble grouping (consecutive messages, who shows an avatar)
- [ ] **Metadata placement**: where do the timestamp and the delivery/read receipts sit - below the bubble (Stream default) or **inside it, bottom-trailing** (WhatsApp/iMessage)? This is structural.
- [ ] Read/delivery indicator glyphs (single/double tick, color)
- [ ] Avatars next to messages (shown? side? shape?)
- [ ] Reactions (style, position - overlay vs. attached)
- [ ] Quoted / inline replies, thread reply summary
- [ ] Long-press message actions menu
- [ ] Any per-message affordances (e.g. WhatsApp's floating forward arrow beside a bubble)

**Message screen - attachments**
- [ ] Image/photo grid (NOTE: the 1/2/3/4+ grouped collage with "+N" is **already the Stream default** - `MessageMediaAttachmentsContainerView`; do not rebuild it, only restyle if needed)
- [ ] Video, file, giphy, link, voice-recording, poll, custom attachments
- [ ] The full-screen media viewer

**Composer** (almost always differs from default - inspect closely)
- [ ] Leading button(s) - e.g. WhatsApp's `+` attachment button on the left
- [ ] The input field container and the text input
- [ ] Icons *inside* the field, trailing edge - e.g. a sticker/emoji glyph
- [ ] Buttons to the *right* of the field - e.g. camera + microphone (Stream's default here is empty)
- [ ] Send button glyph/placement; voice-record vs. send swap
- [ ] Attachment picker sheet, command/slash suggestions, edit/quote states

**Cross-cutting**
- [ ] Fonts, accent color, icon set
- [ ] Light/dark behavior

State the result as a task list: `Region -> default vs. target -> mechanism (theming token / ViewFactory slot / already-default / source-dive needed)`. Implement **all** differing regions, not just the cheap theming ones.

---

## Step 2: Region -> mechanism map (verified against the SDK source)

Slot names below are the `ViewFactory` methods in `Sources/StreamChatSwiftUI/ViewFactory/ViewFactory.swift`. Each takes a single `<Name>Options` value (fields are in `ViewFactory/Options/*.swift`). Override only what you need; the rest fall back to defaults. **Confirm the exact signature + options fields in the source for the pinned version before using them** - this map is for routing, not verbatim API (see "Grounding" below).

### Header / chrome
| Design region | Slot(s) / token | Docs page (`…/sdk/ios/swiftui`) |
|---|---|---|
| Channel header (title, subtitle, back, trailing) | `makeChannelHeaderViewModifier` | `chat-channel-components/channel-header.md` |
| Bars visibility | `makeChannelBarsVisibilityViewModifier` | overview |
| Chat wallpaper / background | `makeMessageListBackground` | `chat-channel-components/message-list.md` |
| Date separator pill | `makeMessageListDateIndicator`, `makeDateIndicatorView` | `message-components/message-display-options.md` |
| New-messages divider | `makeNewMessagesDividerView` | message-list |
| Scroll-to-bottom / jump-to-unread | `makeScrollToBottomButton`, `makeJumpToUnreadButtonOverlay` | message-list |

### Message row, bubble, metadata
| Design region | Slot(s) / token | Docs page |
|---|---|---|
| Whole message row (restructure layout, e.g. metadata INSIDE bubble, bubble tail) | `makeMessageItemView` (the big hammer) | `swiftui-cookbook/custom-message-list.md` |
| Text bubble content | `makeMessageTextView`, `makeStreamTextView`, `makeEmojiTextView` | message-list |
| Top/author/date row | `makeMessageTopView`, `makeMessageAuthorAndDateView`, `makeLastInGroupHeaderView` | `message-components/message-display-options.md` |
| Timestamp | `makeMessageDateView` | message-display-options |
| **Read / delivery receipts** | `makeMessageReadIndicatorView` | `message-components/read-indicators.md` |
| Deleted / system message | `makeDeletedMessageView`, `makeSystemMessageView` | message-display-options |
| Bubble fill / border colors | theming: `chatBackgroundOutgoing`/`Incoming`, `chatBorderOutgoing`/`Incoming`, `chatBorderOnChatOutgoing`/`Incoming` | `theming.md` |
| Bubble **shape / tail / radius** | structural - override `makeMessageItemView` (no token for a WhatsApp/iMessage tail) | custom-message-list |
| Avatar beside message | `makeUserAvatarView`; toggle via message display options | `message-components/custom-avatar.md` |
| Reactions | `makeMessageReactionView`, `makeBottomReactionsView`, `makeReactionsContentView`, `makeReactionsOverlayView`, `makeReactionsDetailView`, `makeMoreReactionsView` | `message-components/message-reactions.md` |
| Quoted / inline reply, thread summary | `makeQuotedMessageView`, `makeChatQuotedMessageView`, `makeMessageRepliesView`, `makeThreadRepliesDividerView` | `message-components/inline-replies.md`, `message-threads.md` |
| Message actions menu | `makeMessageActionsView`, `makeMoreChannelActionsView` | `message-components/message-display-options.md` |
| Typing indicator | `makeInlineTypingIndicatorView`, `makeSubtitleTypingIndicatorView` | `message-components/typing-indicators.md` |

### Attachments
| Design region | Slot(s) / token | Docs page |
|---|---|---|
| Image/photo grid (collage is **already default**) | `makeImageAttachmentView` (default `MessageMediaAttachmentsContainerView`) | `message-components/attachments.md` |
| Video + media viewer | `makeVideoAttachmentView`, `makeMediaViewer`, `makeMediaViewerFooterView`, `makeMediaViewerToolbarModifier` | attachments |
| File / giphy / link / custom | `makeFileAttachmentView`, `makeGiphyAttachmentView`+`makeGiphyBadgeViewType`, `makeLinkAttachmentView`, `makeCustomAttachmentViewType` | attachments |
| Attachment tint | theming: `chatBackgroundAttachmentOutgoing`/`Incoming` | theming |

### Composer (inspect every sub-slot - it usually differs)

**Know the actual structure before picking slots (verified in `MessageComposerView.swift`).** The composer is a single `HStack`:

```
[ makeLeadingComposerView ] [ makeComposerInputView ] [ makeTrailingComposerView ]
                                      |
                          rounded field, and INSIDE it on the trailing edge:
                          makeComposerInputTrailingView  ->  TrailingInputComposerView
                          which IS the send / voice-record / confirm-edit / slow-mode button
                          (it switches by state: .creating(hasContent)->send, .allowAudioRecording->mic,
                           .editing->confirm, .slowMode->cooldown)
```

Two facts this implies, and the mistakes they cause:
- **The send button and the voice-record mic live *inside* the field** (`makeComposerInputTrailingView`), **not** in `makeTrailingComposerView` (which is `EmptyView` by default). So if the target puts the mic/camera/send to the **right of the field** (WhatsApp/iMessage), overriding only `makeTrailingComposerView` leaves the real send/mic in the wrong place (in-field) - you get a duplicate or a misplaced control. To move them, **either** override `makeComposerInputTrailingView` (replace the in-field control) **or** override `makeMessageComposerViewType` and lay out `leading | input | trailing` yourself. **Whichever you override, reproduce ALL of `TrailingInputComposerView`'s states** (send / voice / confirm-edit / slow-mode) - dropping them silently breaks sending, voice notes, editing, or slow mode.
- **Defaults are NOT automatically the target's design.** The leading `+` is the SDK's `composerAdd` glyph and the in-field mic is the SDK voice button - compare each glyph, size, and **placement** against the screenshot. Restyle glyphs via `Appearance.images` (e.g. `composerSendButton`, `composerAdd`), button chrome via `styles.makeComposerButtonViewModifier`, the field container via `styles.makeComposerInputViewModifier`, and rearrange via the slots above. An **emoji/sticker button inside the field** (common in WhatsApp/Telegram) is *not* a default - add it by overriding the input view (`makeComposerInputView`) so the text field, the sticker glyph, and the in-field send/voice all coexist.
- **The closures you need to move send/voice are not in every slot - check the Options first, then reuse the public input view.** A recurring trap: `makeTrailingComposerView` (right of the field) often receives only `enabled`/`cooldownDuration`/`onTap` - it has **no** `startRecording`/`stopRecording`/recording-state bindings, and the view-model's record/send methods are not public - so you **cannot** build a functional voice/camera button there. The send/voice closures (`sendMessage`, `startRecording`, `stopRecording`, `hasContent`, recording state) live on **`makeComposerInputView`'s Options** (and `makeComposerInputTrailingView`'s). So the clean recipe to put a functional camera/mic/send cluster to the **right of the field on the background** (not inside it):
  1. Override `makeComposerInputView` and return `HStack { ComposerInputView(factory: self, <all options fields>); YourRightCluster(...) }` - **reuse the public `ComposerInputView` verbatim** so text entry, quoted/edited banners, attachment + voice-recording previews and drafts keep working; you only add the cluster beside it.
  2. Override `makeComposerInputTrailingView` to return just the in-field glyph the design shows there (e.g. a sticker), which removes the default in-field send/voice so it isn't duplicated.
  3. Build `YourRightCluster` from the options' closures: `hasContent ? sendButton(onTap: sendMessage) : (camera + holdToRecordMic(startRecording/stopRecording))`. Reproduce **all** the states the default carried (send / voice / confirm-edit / slow-mode) - confirm them against `TrailingInputComposerView` in the pinned source.
  Verify the exact slot→closure mapping in the source for the pinned version (the Options structs move between versions); the principle - *find which slot actually carries the send/record closures, then host your custom layout there and reuse the SDK input view* - is what generalizes.

**The composer is the highest-detail region - budget real attention to it and pass a literal pixel checklist, because users inspect it closely.** A composer that is "recognizably a messenger composer" but off on these points is a FAIL, not done:
- [ ] **Container background** of the whole composer bar - did you actually apply it? If you wrote a custom `Styles` and skipped `makeComposerViewModifier`, the bar is **white** (the #1 composer miss). Set it to match the reference.
- [ ] **Input-field background, border, corner radius, height - MEASURED, set via config.** Extract the field's real height + glyph sizes from the reference (script above) - the field is usually **shorter than the default `inputViewMinHeight = 40`** (≈30-34pt for WhatsApp; leaving it 40 makes the composer too tall and the controls look oversized), and the controls are **smaller** than you'd guess (≈18-22pt) and often **thinner-stroked**. Set the height via `utils.composerConfig.inputViewMinHeight`/`inputViewCornerRadius` (see the dimensions section), keep the field border **subtle** (the reference's is barely visible), size buttons to the measured glyph sizes + match their weight, and frame buttons to the field height so they vertically center.
- [ ] **Every glyph is the EXACT one in the reference - do not substitute a lookalike.** A sticker (peeling-square) is **not** `face.smiling`; a paper-plane send is not an up-arrow. If no SF Symbol matches, use `Appearance.images` or a bundled asset. Match each glyph's **size, weight, and color** too.
- [ ] **Vertical alignment / centering of each button against the field.** The composer HStack is `alignment: .bottom`, so fixed-size glyphs sit on the field's baseline unless you align them - a `+` that looks too low/high or off-center is a classic miss. Center each button to the field (match the reference's optical alignment), not just `.padding(.bottom, n)`.
- [ ] **Horizontal spacing/order** of `+`, field, in-field glyph, and the right-side cluster.
- [ ] **Both states render correctly** - at rest (camera/mic) and typing (send), plus edit/quote/slow-mode/voice-recording.

Decompose the composer in BOTH states - **at rest** (no text: leading `+`, field, any in-field/right-side buttons, mic) and **typing** (send replaces mic) - they render different sub-views. Then route each region:

| Design region | Slot | Default behavior | Docs page |
|---|---|---|---|
| Leading button(s) (e.g. WhatsApp `+`) | `makeLeadingComposerView` | attachment picker trigger | `chat-channel-components/message-composer-overview.md` |
| Input field container | `makeComposerInputView`, `makeComposerTextInputView` | rounded input + inline attachments | message-composer-overview |
| Icons inside field, trailing (e.g. sticker) + **send/voice/edit/slow-mode** | `makeComposerInputTrailingView` | **carries send + voice-record + confirm-edit + slow-mode** (composite - reproduce all states) | message-composer-overview |
| Buttons right of field (e.g. camera + mic) | `makeTrailingComposerView` | **empty by default** | message-composer-overview |
| Send button | `makeSendMessageButton` | send arrow | message-composer-overview |
| Whole composer (relayout: mic outside field, etc.) | `makeMessageComposerViewType` | full composer | `swiftui-cookbook/custom-composer.md` |
| Voice recording | `makeComposerVoiceRecordingInputView`, `makeVoiceRecordingView` | voice UI | `voice-recording.md` |
| Edit / quote states | `makeComposerEditedMessageView`, `makeConfirmEditButton`, `makeComposerQuotedMessageView` | edit/quote banners | message-composer-overview |
| Attachment pickers | `makeAttachmentPickerView`, `makeAttachmentTypePickerView`, `makeAttachmentMediaPickerView`, `makeAttachmentFilePickerView`, `makeAttachmentCameraPickerView`, `makeAttachmentCommandsPickerView`, `makeAttachmentPollPickerView`, `makeCustomAttachmentPickerView`, `makeCustomAttachmentPreviewView` | system pickers | `chat-channel-components/message-composer.md`, `composer-commands.md` |
| Command suggestions | `makeSuggestionsContainerView` | slash-command list | composer-commands |

### Channel list
| Design region | Slot | Docs page (`…/swiftui/channel-list-components`) |
|---|---|---|
| Header / top | `makeChannelListHeaderViewModifier`, `makeChannelListTopView` | `channel-list-header.md` |
| Item / background / divider | `makeChannelListItem`, `makeChannelListItemBackground`, `makeChannelListDividerItem` | `channel-list-item.md` |
| Avatar | `makeChannelAvatarView` | `channel-list-item.md` |
| Swipe actions | `makeLeadingSwipeActionsView`, `makeTrailingSwipeActionsView` | `swipe-actions-channels.md` |
| Search results | `makeChannelListSearchResultItem`, `makeSearchResultsView` | `channel-list-search.md` |
| Footer / empty / loading | `makeChannelListFooterView`, `makeChannelListStickyFooterView`, `makeEmptyChannelsView`, `makeChannelLoadingView` | `helper-views.md` |

### Theming tokens worth knowing (Appearance.ColorPalette, "Chat" section)
`chatBackgroundIncoming/Outgoing`, `chatBackgroundAttachmentIncoming/Outgoing`, `chatBorderIncoming/Outgoing`, `chatBorderOnChatIncoming/Outgoing`, `chatTextIncoming/Outgoing`, `chatTextLink`, `chatTextSystem`, `chatTextTimestamp`, `chatTextUsername`. Plus `Appearance.Fonts`/`FontsSwiftUI` and `Appearance.Images` (icon glyphs - e.g. `composerAdd`, `composerSendButton`). Apply via `StreamChat(chatClient:appearance:)`.

### Styles modifiers worth knowing (the `Styles` protocol on `factory.styles`)
For **padding, insets, corner radius, border, and container chrome** - which theming and `ViewFactory` cannot touch:
`makeMessageViewModifier` (the message bubble: bg/corners), `makeMessageAttachmentsViewModifier` (**the bubble + insets around an attachment/photo-collage - the green-frame thickness; default inset `spacingXs`**), `makeMessageAttachmentItemViewModifier` (each attachment cell's corners/border), `makeComposerViewModifier` (**whole composer container background - default `ComposerBackgroundRegularViewModifier` = `.background(backgroundCoreElevation1)`**), `makeComposerInputViewModifier` (rounded input field container - default `RegularInputViewModifier` = bg + border), `makeComposerButtonViewModifier` (composer buttons). Each takes an `…Options`/`…ModifierOptions` value - confirm fields in `Styles.swift` for the pinned version.

> **⚠️ How to supply a custom `Styles` (read before writing it - this is a common silent-failure).** `RegularStyles` is `public` but **not `open`**, so you **cannot subclass it** from your module (`error: cannot inherit from non-open class`). Conform a fresh class to `Styles` directly. But beware: the `extension Styles` defaults for the **non-defaulted** members are mostly `EmptyViewModifier` (no-op), so conforming directly and implementing only `makeMessageViewModifier` **silently drops RegularStyles' chrome** - most visibly the **composer container background and input-field background go white/unstyled**. You must **re-supply every member RegularStyles itself implements**, reusing the **public** `Regular*` modifiers:
> ```swift
> final class MyStyles: Styles {
>     var composerPlacement: ComposerPlacement = .docked
>     // your override(s):
>     func makeMessageViewModifier(for i: MessageModifierInfo) -> some ViewModifier { MyBubbleModifier(...) }
>     // re-supply RegularStyles' non-defaulted chrome (else white/unstyled defaults):
>     func makeComposerViewModifier(options: ComposerViewModifierOptions) -> some ViewModifier { ComposerBackgroundRegularViewModifier() }
>     func makeComposerInputViewModifier(options: ComposerInputModifierOptions) -> some ViewModifier { RegularInputViewModifier() }
>     func makeComposerButtonViewModifier(options: ComposerButtonModifierOptions) -> some ViewModifier { RegularButtonViewModifier() }
>     func makeScrollToBottomButtonModifier(options: ScrollToBottomButtonModifierOptions) -> some ViewModifier { RegularScrollToBottomButtonModifier() }
>     func makeSuggestionsContainerModifier(options: SuggestionsContainerModifierOptions) -> some ViewModifier { SuggestionsRegularContainerModifier() }
> }
> ```
> Confirm the exact non-defaulted set in `Styles.swift` for the pinned version (diff the protocol body against the `extension Styles` defaults; whatever `RegularStyles` implements but the extension does not is what you must re-supply). To **match** a design you may replace any of these with your own (e.g. a beige composer-bar background) - the point is **supply them, don't drop them**.

---

## Step 2.5: Overriding a composite slot inherits ALL of its sub-features

The high-level slots - `makeMessageItemView`, `makeChannelHeaderViewModifier`, `makeMessageComposerViewType`, `makeChannelListItem` - each render **many** sub-features internally. When you override one, every sub-feature the default drew **disappears unless you reproduce it.** A custom view that handles only the case in front of you (one outgoing image bubble) silently drops avatars, grouping, reactions, replies, and status - and a near-empty test channel hides the loss until the user spots it.

**Rule:** before overriding a composite slot, open the default view it returns in the pinned source, read its `body`, and **enumerate every sub-view and every conditional branch**. For each one, decide: reproduce it (reusing the SDK's own sub-view) or consciously drop it - and if you drop it, say so to the user. Prefer the **narrowest slot** that achieves the change; reach for the big hammer only when a structural change truly needs it (metadata inside the bubble, a bubble tail), and even then compose the SDK's sub-views rather than rebuild them from scratch.

**`makeMessageItemView` (default `MessageContainerView`) carries the following - verify each against the pinned source, do not assume this list is complete:**
- Author **avatar** beside incoming messages, including the grouping opacity (only the last-in-group / first message shows it) - *the most commonly dropped element*
- **Message grouping**: consecutive messages from the same author are spaced tighter; `showsAllInfo` drives whether the avatar + metadata + date show
- Reactions (top overlay **and** bottom), the long-press → **message-actions** menu, the reactions-overlay preview
- Quoted / inline reply view, thread-reply summary
- Delivery/read status + timestamp (or author+date row), the **send-failure indicator**
- **System** and **deleted** message rendering (don't draw these as normal bubbles)
- Text + attachments (reuse `factory.makeMessageAttachmentsView` or `MessageView` for the photo collage - it is already correct)

Reuse the SDK sub-views inside your custom row instead of reinventing them: `factory.makeUserAvatarView`, `factory.makeMessageAttachmentsView`, `factory.makeMessageReactionView` / `makeBottomReactionsView`, `factory.makeMessageRepliesView`, `factory.makeMessageReadIndicatorView`.

**The navigation header (`makeChannelHeaderViewModifier`) is finicky - and the obvious fix is a trap. Budget for it.**

**First, the trap (verified in source - do not repeat this mistake).** `ChatChannelView` applies your header modifier to a **zero-height `Divider().opacity(0)` placed *between* the message list and the composer** - not to the whole screen (read `ChatChannelView.swift`: the modifier sits on that divider inside the `VStack { messageList; Divider().modifier(headerModifier); composer }`). Consequences:
- Rendering your header inside the modifier via `.safeAreaInset(edge: .top)` or a `VStack { header; content }` puts it **at the bottom, just above the composer** - because "top of that divider" is near the bottom of the screen. This is the #1 header failure.
- The reason the **default** header works is that it uses `.toolbar { ToolbarItem(.principal/.navigationBarTrailing) { … } }`. **Toolbar content attaches to the navigation bar at the top of the screen regardless of where the modifier sits.** That is the *only* in-modifier mechanism that reaches the top.

**So, to customize the header, do ONE of these - never a `safeAreaInset`/`VStack` inside the modifier:**
1. **Preferred - `.toolbar` inside the modifier.** Provide your own `ToolbarItem`s plus `.toolbarBackground(<color>, for: .navigationBar)` + `.toolbarBackground(.visible, for: .navigationBar)`, and `.navigationBarBackButtonHidden(true)` if you supply your own back button. **Layout that actually works for an avatar + two-line title (verified):** put the **back button alone** in `.navigationBarLeading`, and the **avatar + title/subtitle VStack in `.principal`** with `.frame(maxWidth: .infinity, alignment: .leading)` + a trailing `Spacer`. Do **not** cram back + avatar + title into one `.navigationBarLeading`/`.topBarLeading` item - that region is width-constrained, so the flexible title Text gets compressed to **zero width and renders blank** (a real trap; the back+avatar show but the name vanishes). The default `ChannelTitleView` is the fidelity baseline for fonts/sizes.
2. **Only if the target header is genuinely taller than a nav bar can hold** (large avatar + multi-line + extra rows): hide the bar (`.toolbar(.hidden, for: .navigationBar)`) **and provide the header through a custom channel destination** so it works on the real navigation path - i.e. override `makeChannelDestination` (or wrap `ChatChannelView` in your own container that draws a top header and hides the bar). Do **not** fake it by rendering a header in the app's root view for one hard-coded channel - that only covers a directly-opened channel and leaves the normal *channel-list → push* flow with **no header at all** (a real regression that an open-channel-directly scaffold hides).

Either way, match the target's header **height, title font size/weight, subtitle, and avatar size**, and **verify on the real push path** (open the channel list and navigate in), not only on a direct-open scaffold - the header is exactly what a direct-open scaffold fails to exercise.

**Header content MUST be model-driven - never hardcode the reference's literal title/subtitle.** The title is **one specific channel's** name in the screenshot, but your header renders for **every** channel; if you hardcode it (or fall back to a fixed string like the current user's name / the demo title), **every channel shows that same wrong title** (the exact bug a user will catch by opening a different chat). Drive it from the model:
- **Title:** `utils.channelNameFormatter.format(channel: channel, forCurrentUserId: chatClient.currentUserId)` - the SAME formatter the SDK's default header AND channel list use. Don't hand-roll the title in your header alone; if it's wrong, it's wrong in both places, so fix it at the formatter. **Never** fall back to a hardcoded literal.
- **The blank-name trap (`DefaultChatChannelNamer` returns `nil`).** The default namer resolves a name ONLY from the **top-level `channel.name`** OR, for **DM channels** (auto-generated id), the member names; for a channel with a **custom id that is not a DM and whose name lives in `custom`/extra data**, it returns `nil` → **blank in BOTH the list and the header**. Many backends store the channel name under `custom` (top-level `channel.name` stays nil), so this hits often. **Fix via the SDK's hook, once, for both surfaces:** set `utils.channelNameFormatter` to a custom `ChannelNameFormatter` that reads the custom name then defers to the default, and pass that `Utils` to `StreamChat(...)`:
  ```swift
  final class CustomNameFormatter: ChannelNameFormatter {
      private let def = DefaultChannelNameFormatter()
      func format(channel: ChatChannel, forCurrentUserId currentUserId: UserId?) -> String? {
          if let n = channel.name, !n.isEmpty { return n }
          if case let .string(n)? = channel.extraData["name"], !n.isEmpty { return n }   // name stored in custom
          if let n = def.format(channel: channel, forCurrentUserId: currentUserId), !n.isEmpty { return n }
          // The default returns nil for a NON-DM channel (custom id) with no name even
          // when it has members → derive member names so it doesn't render blank:
          let others = channel.lastActiveMembers.filter { $0.id != currentUserId }
              .compactMap { $0.name ?? $0.id }.sorted()
          guard !others.isEmpty else { return channel.lastActiveMembers.first { $0.id == currentUserId }?.name }
          switch others.count {
          case 1:  return others[0]
          case 2:  return "\(others[0]) and \(others[1])"
          default: return others.prefix(2).joined(separator: ", ") + " and \(others.count - 2) more"
          }
      }
  }
  // utils.channelNameFormatter = CustomNameFormatter()
  ```
  **Do NOT just defer to `DefaultChannelNameFormatter` for the no-name case** - its member-derivation only runs for **DM channels** (`isDirectMessageChannel` = auto-generated id); a no-name channel with a **custom id** + members returns `nil` → blank, so reproduce the member-name derivation yourself (above). Then the header just calls `utils.channelNameFormatter.format(...)` - no per-header fallback - and the channel list shows the same names. (Setting top-level `channel.name` from the CLI may not work - this app keeps `name` under `custom` - so the formatter hook is the reliable fix.)
- **Subtitle:** `channel.onlineInfoText(currentUserId:)` for the general case; only special-case a label like "Message yourself" via a **model condition** (e.g. `channel.name == currentUser.name`), never an unconditional constant.
- **Verify on a second, different channel** (open a DM in the scaffold): the title must change to that channel's name. A note on scaffolds: a raw `channelController(for:)` may not have member names loaded immediately, so the derived name can be briefly blank - the member fallback above and the real list→push path (channel already loaded) both resolve it.

---

## Step 3: Grounding (do not guess slot signatures)

Per [`RULES.md`](RULES.md) "Docs discipline": most of these ~100 slots are **not** individually documented. The authoritative reference is the SDK source for the pinned version - one file lists every slot, another shows every default:

**⚠️ Pick the checkout that matches the project's pinned version - never blind `head -1`.** Multiple Xcode projects on the machine each have their own DerivedData, and a *sibling* project can hold a **different version** of the same Stream package. `find … | head -1` routinely returns the wrong one, and the API differs across versions (e.g. 5.5.x splits styling into a `Styles` protocol with Options-based slots and an Appearance/ColorPalette in `StreamChatCommonUI`; older trees put `ViewFactory.swift`/`ColorPalette.swift` at the package root with non-Options slots and `makeMessageViewModifier` on the factory). Reading the wrong tree wastes a build cycle and produces code that will not compile. So: read `Package.resolved` for the pinned version, then **verify every candidate checkout with `git describe` and use the matching one** - and prefer the checkout under *this* project's own DerivedData (or a custom `-derivedDataPath` you control).

```bash
# pinned version (source of truth)
VER=$(grep -A4 stream-chat-swiftui */*.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved \
      Package.resolved 2>/dev/null | grep -m1 version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'); echo "pinned: $VER"
# every candidate checkout, with its actual tag - pick the one whose tag == $VER
for d in $(find ~/Library/Developer/Xcode/DerivedData /tmp -type d -path "*checkouts/stream-chat-swiftui" 2>/dev/null); do
  echo "$(git -C "$d" describe --tags 2>/dev/null)  ->  $d"
done
CO="<the matching checkout>/Sources/StreamChatSwiftUI"   # then verify it has the expected layout:
ls "$CO/ViewFactory" 2>/dev/null && echo "Options-based (5.5.x+ style)" || echo "older root-level layout"
grep -nE "func make[A-Za-z]+\(" "$CO/ViewFactory/ViewFactory.swift"          # every slot
sed -n '1,60p' "$CO/ViewFactory/Options/MessageViewFactoryOptions.swift"     # an Options struct's fields
grep -rn "func makeMessageReadIndicatorView" "$CO/ViewFactory/DefaultViewFactory.swift"  # what a slot renders by default
```

If the source you are reading disagrees with the live docs about whether a slot/token exists (`chatBackgroundOutgoing` vs `messageCurrentUserBackground`, `Styles`/`RegularStyles` present or not, slots taking `options:` vs positional args), that is the tell you are on the **wrong version** - re-check `git describe` before writing code, and remember the **build's own checkout is authoritative** over any other tree you happened to read.

Read the **default view** a slot returns (e.g. `LeadingComposerView`, `MessageReadIndicatorView`, the message container) before overriding - it shows what you are replacing and what its options carry. For placement changes (metadata inside the bubble, a bubble tail), the per-element slots are not enough; override `makeMessageItemView` and rebuild the row, reusing the SDK's sub-views where you can. Cross-check the version against `Package.resolved`; say where you found anything source-derived rather than presenting it as documented.

## Step 4: Build the factory

Conform one class to `ViewFactory` (`@Injected(\.chatClient) var chatClient`; `var styles = …`), override every slot the decomposition flagged, and pass it to `ChatChannelListView(viewFactory:)` so it propagates to the pushed message screen. Wire all three axes:
- **theming** -> build an `Appearance` (recent versions: `Appearance().colorPalette.<token>` from `StreamChatCommonUI`, re-exported by `StreamChatSwiftUI`) and pass it to `StreamChat(chatClient:appearance:)`.
- **`Styles`** -> if any region flagged a padding/inset/corner-radius/container-chrome difference, conform a class to `Styles` (you cannot subclass `RegularStyles` - it is not `open`), implement the relevant `make…ViewModifier`, **re-supply RegularStyles' non-defaulted chrome** (composer background, input/button/scroll/suggestions modifiers - see the ⚠️ box; skipping this is what leaves the composer white), and set `var styles = MyStyles()` on the factory.
- **structure** -> the overridden `ViewFactory` slots.

Pass the factory to `ChatChannelListView(viewFactory:)` for the real entry point - do **not** ship a root that opens one channel directly (that is a verification scaffold only; see Step 5).

## Step 5: Verify against the reference - rigorously, region by region (mandatory)

A design match is **not done** until the build runs and the result is compared to the reference. Presence-and-color is not enough; verify **size, position, and proportion** too. The avatar that's missing, the header that collapsed, the icon that's the wrong size - these only show up here.

1. **Seed data that triggers every customized region.** An empty or one-message channel proves nothing and hides exactly the elements that get dropped. Seed (or send): **both an incoming and an outgoing** message; a **run of 3+ consecutive messages from the same author** (so grouping + the avatar's last-in-group rule actually render); a **photo album**; a message **with reactions**; a **reply/quote**; a **long multi-line** text; enough history that the **date separator** appears. Mark messages read if the design shows read receipts.
2. **Open the real message screen - via a THROWAWAY scaffold you must DELETE.** Verifying only the channel list does not verify the message screen. Scripting a tap inside the simulator is usually not possible (no `cliclick`/Quartz, no accessibility permission) and `selectedChannelId:` only *pre-selects* on iPad - it does not push on iPhone. The reliable way to render the message screen for a screenshot is to **temporarily** point the root view at `ChatChannelView(viewFactory: <yourFactory>, channelController: chatClient.channelController(for: ChannelId(type: .messaging, id: "<seeded-id>")))` inside a `NavigationStack`, screenshot, **then DELETE the scaffold entirely** so the shipped code's only path is the real entry point.
   - **This scaffold is for verification ONLY - never ship it, and "revert" means DELETE, not disable.** Do not leave a `verifyMessageScreen`-style boolean flag (even set to `false`), the dead `if/else` branch, or constants only the scaffold used (e.g. a `demoChannelId`) in the delivered code - a toggled-off debug flag is still scaffolding the user will (rightly) ask you to remove. Remove the flag, the branch, the direct-open `ChatChannelView`/`ChannelId` code, the now-unused imports, and any helper that became dead - leaving `case .connected: ChatChannelListView(...)` as the only connected path. Prefer a scaffold shaped so it's trivially deletable in one edit (a single replaced line/branch), not threaded through the view. Opening one hard-coded channel directly is not the app the user asked for; the default integration is **channel list → tap → pushed message screen**, and leaving the direct-open root **hides header/navigation bugs** (a header rendered only in the direct-open root is absent on the real push path). Do not change the app's entry point or navigation unless the user explicitly asks (see [`RULES.md`](RULES.md) "Project ownership").
   - **After the scaffold screenshot, also verify the real path:** restore the channel-list root and confirm the header, back button, and title render correctly on the *pushed* `ChatChannelView` (the channel-list path is the one that exercises `makeChannelHeaderViewModifier`/`makeChannelDestination` end to end). A direct-open scaffold uses the same factory for the *body*, but it does **not** prove the header/navigation works in production.
3. **Build a comparison table.** For each region from Step 1, record: target attribute (size/position/color/presence) → what rendered → **PASS / FAIL**. Walk the *whole* Step-1 checklist; do not stop at the regions that happen to look right.
4. **Re-check the elements that are silently lost** (give these explicit attention every time): the **author avatar on incoming messages** and message **grouping**; the **navigation header's height, alignment, and title size** (the classic collapse); the **composer in BOTH states** - empty/at-rest and with text typed (the send vs. mic/camera swap lives in different slots).
5. **Iterate until every region passes.** Fix, rebuild, re-screenshot. Don't declare done on the first screenshot.
6. If you genuinely cannot run the build, say so plainly and list which regions are implemented-but-unverified - never imply a match you did not see.
7. **Do not deliver with a region left at its default and call it a "known gap."** Every region in the Step-1 checklist - the composer especially - must be implemented to match, not just the cheap theming ones. A region that "looks roughly like a messenger composer" but is the SDK default (wrong button set/placement, no in-field glyph) is a FAIL, not a footnote. Report something as unmatched only when it is genuinely impossible (and say what + why), never merely because it is risky or more effort.
