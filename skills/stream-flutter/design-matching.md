# Stream Flutter — matching a reference design (screenshot / Figma / "make it look like X")

When the user gives a **target appearance** — an attached screenshot, a Figma frame, or "make the chat look like WhatsApp / iMessage / Telegram / Slack / Discord" — the job is **not** "set a few colors." A reference design is a **checklist of regions**, and most real designs differ from Stream's defaults in *structure*, not just color: the composer buttons, where the timestamp and read receipts sit, the bubble shape/tail, the header, the date separators. Changing the bubble color and the wallpaper and calling it done is the classic failure — do not repeat it.

**Implement EVERY region — the composer is first-class, not optional.** Do not deliver a partial match and label the rest "known cosmetic gaps" / "minor, skipped." If a region needs a relayout (moving send/mic outside the field, adding a leading `+`, moving metadata inside the bubble, adding a bubble tail), do the relayout — reuse the SDK's public widgets and wire the real callbacks rather than punting. "Risky" or "more effort" is not a reason to skip; only genuine impossibility is, and then you say exactly what and why. The composer is the region most often left at its default and is exactly where users notice the mismatch.

This page is the procedure + the routing map. Run it **before** writing code, in addition to (not instead of) the normal reference lookup in [`SKILL.md`](SKILL.md).

## Work in batches — a full match is many regions; do not let it take all day

The slow way is one grep / one read / one hot-reload per question. Batch instead:
- **Ground the pinned versions ONCE** — resolve **both** package roots via the method in **[Step 3](#step-3-grounding-do-not-guess-widget-signatures)** (`$CHAT` = `stream_chat_flutter`, `$CORE` = `stream_core_flutter`); don't hardcode a pub-cache path or reuse the chat version for core — the two version lines are **decoupled** (`10.x` vs `0.4.x`). Then **read every canonical file you'll need in a single pass** — from **`$CHAT`**: `theme/stream_chat_theme.dart` (`StreamChatThemeData` slots), `theme/message_list_view_theme.dart` (list background/wallpaper), `theme/quoted_message_theme.dart`, `message_widget/stream_message_item.dart` (`StreamMessageItem` + `StreamMessageItemProps`), `message_input/stream_message_composer.dart` (composer props), `components/message_composer/message_composer_component_props.dart` (per-slot Props subtypes), `components/stream_chat_component_builders.dart` (all registration slots); and from **`$CORE`**: `theme/stream_theme.dart` + `theme/components/*.dart` (`StreamTheme` + per-component `*ThemeData`, including `stream_message_item_theme.dart` for the bubble/text/attachment sub-styles).
- **Decompose all regions, then implement all of them, THEN verify once.** Don't hot-reload-and-screenshot after every tiny edit — batch the fixes for a round, hot-reload once, screenshot once.
- **Reuse ONE running `flutter run` session with hot reload** on a **pinned device / simulator** for the whole match; take **one screenshot per fix-round** after a short settle (image loads / animations complete) — not a stream of throwaway screenshots per tiny edit; Step 5's verify loop still repeats rounds until every region passes. Iterate only on regions that actually fail.

---

## Two axes of customization (internalize this first)

Start every design difference with one question: **am I changing how a widget LOOKS, or WHAT is rendered / how it's arranged?**

- **Looks** — color, font, size, padding, corner radius, border, shape. The SDK widget stays; you just feed it different values. → **Axis 1: Theming.**
- **Structure** — add / remove / move / reshape a widget: the send button *outside* the field, a leading `+`, metadata *inside* the bubble, a bubble tail, a flat Slack-style row, a custom header. → **Axis 2: Widget replacement.**

**Priority — always try theming first; reach for replacement only when the change is genuinely structural, or no theme token exists for it.** Replacement costs more: overriding a composite widget makes you reproduce *every* sub-feature it drew (avatar, grouping, reactions, receipts — see Step 2.5), so a token is the safer lever whenever one reaches the region. Padding / insets / corner radius are theme **values** (mostly `messageItemTheme.*`) — never a reason to replace a widget on their own.

### Axis 1 — Theming (change how a widget looks)

One concern, but split across **two theme objects**. *Which* object is a lookup, not a judgement — route by what you're styling:

| Object | Set / read via | Owns |
|---|---|---|
| **`StreamTheme`** (from `stream_core_flutter` — the foundations package, **not** `stream_chat_flutter_core`; a Material `ThemeExtension`) | `MaterialApp.theme.extensions: [StreamTheme.light().copyWith(...)]` · `StreamTheme.of(context)` | Design foundations (`colorScheme`, `textTheme`, `typography`, `spacing`, `radius`, `icons`, `boxShadow`) **and every fine-grained / leaf component theme — including the entire message row**: `messageItemTheme` (bubble / text / attachment / metadata / replies sub-styles + `padding` / `spacing` / `avatarSize` / `*Visibility` toggles), `reactionsTheme`, `reactionPickerTheme`, `avatarTheme`, `textInputTheme`, `mediaViewerTheme`, the 7 composer-attachment themes, and ~30 more. |
| **`StreamChatThemeData`** (from `stream_chat_flutter`) | `StreamChat(themeData: ...)` · `StreamChatTheme.of(context)` | Only the **chat-specific composite widgets** (14 slots): `channelHeaderTheme` / `channelListHeaderTheme` / `threadHeaderTheme`, `messageListViewTheme` (wallpaper / list background), `channelListItemTheme`, `quotedMessageTheme`, `threadListTileTheme`, `voiceRecordingAttachmentTheme`, and 6 poll themes. |

**Routing rule:** anything on the **message row or a leaf widget** (bubble, text, reactions, avatar, ticks, text field) → `StreamTheme`. The handful of **chat composite widgets** (the three headers, list background, channel-list item, quoted message, thread tile, polls, voice attachment) → `StreamChatThemeData`. If you searched `StreamChatThemeData` and didn't find the entry, it lives on `StreamTheme`. Full field lists: "Theme tokens worth knowing" in Step 2.

### Axis 2 — Widget replacement (change what's rendered / how it's arranged)

You've decided the change is structural (or no token exists). Now pick the **narrowest** mechanism that reaches your region — replacing more than you need means reproducing more sub-features:

1. **Component factory** — one registry (`StreamComponentBuilders`) resolved by Props type: every Stream widget looks itself up in the nearest factory and renders your builder if present, else its own default. Populated **two ways in the same object**:
   - **Core named slots** (~48 leaf / low-level components, from `stream_core_flutter`): `StreamComponentBuilders(messageBubble: …, messageText: …, messageContent: …, messageMetadata: …, messageReplies: …, reactions: …, reactionPicker: …, mediaViewer: …, jumpToUnreadButton: …, onlineIndicator: …, textInput: …, avatar: …, button: …, …)` — the full list is on the `StreamComponentBuilders` factory (grep it in Step 3).
   - **Chat composite slots** (~30, from `stream_chat_flutter`) via `streamChatComponentBuilders(...) → extensions:`: `messageItem`, `messageComposer` + its sub-slots, `messageLeading` / `messageHeader` / `messageFooter`, `channelListItem`, `threadListItem`, `quotedMessage`, `mentionItem`, the 9 attachment types (`imageAttachment` / `videoAttachment` / `giphyAttachment` / `galleryAttachment` / `fileAttachment` / `linkPreviewAttachment` / `voiceRecordingAttachment` / `pollAttachment` / `unsupportedAttachment`), `mediaGallery` / `mediaGalleryPreview` — full list: grep `stream_chat_component_builders.dart` (Step 3).
   - Applied **globally** — `StreamChat(componentBuilders: StreamComponentBuilders(coreSlot: …, extensions: streamChatComponentBuilders(chatSlot: …)))` — or **scoped** to a subtree — `StreamComponentFactory(builders: StreamComponentBuilders(...), child: ...)` (nearest ancestor wins; nested factories fully override, they don't merge). Every override receives a typed `*Props` and returns a `Widget`.
2. **Per-widget builders** — direct params on one widget, *not* the factory: `StreamMessageListView.messageBuilder` `(context, message, StreamMessageItemProps defaultProps) → Widget` (whole row), `.builders` (`StreamMessageListViewBuilders` — frame slots: date dividers, empty / loading / error, header / footer, system / ephemeral / moderated, scroll-to-bottom, unread separator), `.config` (feature toggles); `StreamChannelListView.itemBuilder` + `emptyBuilder` / `loadingBuilder` / `errorBuilder` / `separatorBuilder` (top-level callbacks).
3. **Direct composition** — for screen chrome that is not a slot at all: build your own `AppBar` in `Scaffold(appBar:)` (the header is not a factory slot).

**Within replacement, prefer the narrowest slot over the whole-widget builder** — replace the `reactions` slot, not the entire `messageItem`. And note that many components expose BOTH a theme lever and a replacement slot: honour the top-of-section priority and try the theme first — `reactionPickerTheme` before the `reactionPicker` slot; `messageItemTheme.bubble` before overriding `messageItem`; `mediaViewerTheme` before the `mediaViewer` slot.

Two recurring mis-routings:
- Reaching for `StreamChatThemeData` when the region is really a **`StreamTheme`** concern. Bubble color / shape / padding / avatar size / reaction-pill styling all live under `StreamTheme` (extensions on `MaterialApp.theme`), not under `StreamChat(themeData:)`. If a search of `StreamChatThemeData` doesn't turn up the entry, it lives on `StreamTheme` instead.
- Reaching for a theme entry when the region is really **structural**. "Read receipts inside the bubble", "a `+` button in the composer pill", "a camera + mic cluster to the right of the field", "a bubble with a tail", "timestamp overlaid on the image", or "a Slack-style flat left-aligned row instead of bubbles" all need widget replacement — a `messageItem` builder, a `messageComposerLeading` builder, etc.

---

## Step 1: Decompose the reference into regions (every time)

**Scope: the chat surfaces the reference / request covers** — the screens Stream renders (channel list, message screen, thread — whatever the reference actually shows). Decompose exhaustively *within* that scope; do **not** extend the checklist to app screens outside the design-match request (no inventorying an onboarding or profile screen the reference never shows).

Go region by region. For **each** region: name what the design shows, compare to the Stream default, and decide theming vs. structure vs. already-default. Produce an explicit task list — one entry per region that differs. Do not skip a region because it "looks standard"; verify it against the default.

**Capture measurements, not just identity.** The reference is a *spec*, not a hint. For every region record the concrete attributes you will reproduce: header height + title font size/weight + subtitle; bubble corner radius, tail size, max width, alignment; icon sizes and the gaps between composer buttons; font sizes and weights; paddings; exact colors. "Looks roughly like it" is the failure mode — a placeholder that has the right color but the wrong size, spacing, or alignment fails the eye even though it passes a presence check. Match the numbers.

### First, get the reference in a form you can measure

Measuring needs a measurable source. A **Figma** frame already is one — read exact sizes, spacing, and colors via the Figma tools. A **raster screenshot pasted inline** is not: save it to a file first (ask the user for the file, or write the pasted image to disk) so the pixel method below and the Step 5 crop-and-compare have something to measure against. If a measurable source is genuinely unavailable, build to the closest visual read, state plainly that the match is approximate, and list which regions are unverified for want of measurement — so the gap is explicit rather than reported as "verified."

### How to actually get the dimensions right (do NOT eyeball round numbers)

Picking `24`, `28`, `44` by eye is the recurring failure — the composer is where it shows most (wrong field height, icon sizes, paddings). Use this method instead:

1. **Identify the source platform, find the reference's scale, then work in logical pixels.** A Flutter app ships to both iOS and Android, so a reference screenshot can come from either — identify which before dividing. **iOS**: typically `@2x` (older devices) or `@3x` (Plus / Pro devices) — pixel widths are e.g. `750`, `828`, `1080`, `1170`, `1179`, `1290`, `1320`. **Android**: density buckets are `mdpi`=1×, `hdpi`=1.5×, `xhdpi`=2×, `xxhdpi`=3× (Pixels, most modern devices), `xxxhdpi`=4× — pixel widths are e.g. `1080` (xxhdpi), `1440` (xxxhdpi). If the filename hints (`Screenshot_iPhone…`, `screenshot-pixel…`) don't tell you, infer from the pixel dimensions + platform chrome visible in the shot (status-bar shape, notch, home indicator vs. Android nav bar). Once the platform + scale are known, get the pixel size and divide by the scale factor:
   ```bash
   sips -g pixelWidth -g pixelHeight <reference.png>   # e.g. 1179 x 2556
   ```
   1179×2556 ÷ 3 = **393×852** logical pixels → the shot is `@3x`, so **1 lp = 3 px**. Every element you measure off the image: `logicalPixels = pixels / scale`. (A status-bar height of ~59 px ÷ 3 ≈ 20 lp is a quick sanity check.) **In Flutter, logical pixels = the numbers you pass to `SizedBox(width:)`, `EdgeInsets.all(...)`, `Radius.circular(...)`, `TextStyle(fontSize:)`, etc.** — no per-device conversion; the framework handles DPI.
2. **Extract element sizes AUTOMATICALLY — don't eye them off the image.** `magick`/Python+PIL are available; threshold the cropped region and read real bounding boxes. Icons are **dark glyphs on a light bar** → threshold dark, project onto columns, cluster into glyphs, measure each box. The field is the **wide near-white band** → its row-span is the field height, its white-column span is the field width. This script (adapt the crop band + thresholds per design) prints logical pixels directly:
   ```python
   from PIL import Image; import numpy as np
   im = Image.open(REF).convert("RGB"); W,H = im.size; S = 3.0      # @3x → ÷3
   g = np.asarray(im).astype(int).mean(2)
   band = g[H-380:H, :]                                              # bottom = composer
   def run(r,t=248):
       b=c=0
       for v in r:
           c = c+1 if v>t else 0; b = max(b,c)
       return b
   wr = np.array([run(g[y]) for y in range(H-380,H)]); ys = np.where(wr>W*.45)[0]+(H-380)
   ft, fb = ys.min(), ys.max(); print("field h", (fb-ft+1)/S, "lp")
   wc = np.where(g[(ft+fb)//2] > 246)[0]; print("field w", (wc.max()-wc.min())/S, "lp")
   dark = (g[ft-6:fb+6, :] < 110); cols = np.where(dark.sum(0)>2)[0]  # icon glyphs
   # cluster contiguous columns (gap>8) → each glyph's w/h in lp
   ```
   Run it on the reference, record each glyph's w/h and the field's h/w in logical pixels. **These exact numbers are your spec.**
3. **Controls are almost always SMALLER than you guess — and smaller than the SDK defaults.** Eyeballing consistently overshoots ("controls too big, composer too tall"). So: **measure the reference, then match the measured size; do not fall back to the SDK default or round numbers.** Material `IconData` inside an `IconButton` renders around `iconSize` × (icon glyph coverage inside its box); start at the measured target and calibrate. **Match stroke WEIGHT too, not just size** — a thin reference `+` needs a lighter-weight icon (`Icons.add_rounded` at a smaller `fill` / `weight` parameter — Material Symbols support `fill/weight/grade/opticalSize`), not the default weight, or it reads "too heavy/too big" even at the right height.
4. **The field width is the LEFTOVER — oversized buttons steal it.** The field gets `total − (leading + trailing cluster + gaps)`. If your buttons are too big the field is too narrow. Size buttons to the measured glyph sizes (small), keep gaps at a consistent scale (8 lp / 12 lp / 16 lp), and the field reclaims its width. In Flutter, size buttons with `IconButton(iconSize: X, padding: EdgeInsets.zero, constraints: BoxConstraints(minWidth: X+8, minHeight: X+8))` — the default `IconButton` reserves a **48-lp** hit area that will visually crowd the composer if you don't zero the padding.
   **Composer field height is padding-driven, not a fixed minimum.** The default input field (`message_composer_input_field.dart`) pads the `TextField` by `spacing.sm` on all sides plus a small vertical `contentPadding`, with `isCollapsed: true` under a `maxHeight` cap — so a single line is **taller than you'd guess, and there is no hard `minHeight` to lower.** To make the pill meaningfully shorter, tighten that padding by overriding `messageComposerInputCenter` (or lower `StreamTheme.spacing.sm`, but that token is global). Trade-off: a fully custom field loses draft/mentions/commands/voice unless you re-wire them — decide deliberately and tell the user.
5. **Centering: `IconButton` and `TextField` don't center themselves inside a `Row` unless you frame both to the same measured height.** The composer row is bottom-aligned by default (the text field grows upward as the user types); a fixed-size button stays at the bottom. To visually center a button against the collapsed single-line field:
   - Wrap the button in a `SizedBox(height: <measured field height>)` and let its natural vertical alignment (`Alignment.center`) do the work.
   - **Do NOT reach for `.expanded` / `mainAxisAlignment: MainAxisAlignment.stretch`** — the composer row is `CrossAxisAlignment.end` by default, so stretching inflates the row height. Match the field's measured single-line height instead.
   - **STOP — do not leave the composer until these two numbers pass (this is the recurring defect):** at **single-line** input, (1) field rendered height = your measured single-line target (the SDK default is taller — match your measurement, not the default), and (2) each side button's center-Y − field center-Y ≈ 0 (not bottom-sunk). No single-line screenshot = not checked = not done.

**General rule (not just the composer): center child elements within their container unless the design says otherwise.** Use the container's own centering (frame to its height + `Alignment.center`, or `Row(crossAxisAlignment: CrossAxisAlignment.center)`) rather than hand-tuned asymmetric padding; verify the measured center offset is ≈ 0.

### Weight is its own dimension — measure and match it (separately from color)

Every glyph has a **weight** (boldness) as well as a size and color, and the eye is sensitive to it ("feels too bold / too thin"). Match it from the reference, don't guess:
- **Different text ROLES usually have different weights — measure each separately, don't apply one weight to a whole block.** A title, a sender/author name, the message body, and a timestamp are typically distinct weights (e.g. name `FontWeight.w600`/`w700` while the body is `w400` or `w300`). The recurring miss is treating "text" as one weight — especially defaulting the body to `w400` when the reference body is lighter. Measure the stroke of each role; map the **stroke ÷ font-size ratio** to a `FontWeight` (≈ 0.05 → `w300`, ≈ 0.075 → `w400`, ≈ 0.09 → `w500`, ≈ 0.11 → `w600`, ≈ 0.13+ → `w700`), and set them independently. A body whose stroke is ~half the name's stroke is two steps lighter, not one.
- **Material icons:** Material Symbols support `fill / weight / grade / opticalSize` — a thin reference glyph is `Icons.<name>(weight: 300)` or a filled variant. Wrong weight reads "too bold / too thin" even at the right size.
- **Custom stroke glyphs** (`CustomPaint` with `Paint()..style = PaintingStyle.stroke..strokeWidth = X`): **measure the reference's stroke thickness in logical pixels** and set `strokeWidth` to it — don't pick `0.1 × size` by feel. Measure: take a horizontal scan line across the glyph and read the dark-run width = stroke thickness.
- **Do NOT conflate color with weight — they are independent.** A glyph that looks "wrong color / too light" has either a wrong base **color** or a sub-pixel-thin stroke that antialiases to gray → fix the **color** (and ensure the stroke is ≥ ~1 lp), do **not** over-thicken (that just makes it too bold, a separate defect). A glyph that looks "too bold" has too-wide a stroke / too-heavy a font weight → reduce to the **measured** width/weight; the color stays.
- **Verify both, by measurement:** the rendered glyph's **stroke width** ≈ the reference's, AND its **dark-core color** ≈ the reference's.

### Follow EVERY color from the reference — sample it, don't guess (and sample each sub-part)

Invented/guessed colors are a recurring miss. **Sample every color off the reference and apply the measured value** — wallpaper, bubble fills, composer bar, each glyph, borders, **and the read-receipt ticks**. Don't assume a "known" brand color: a messenger's read-receipt ticks are often a **different shade than the brand color you remember** (e.g. a vivid azure where you'd have reached for the classic cyan) — only measuring caught it. **Multi-part elements have more than one color — sample each part separately:** a two-part control such as a forward/reply affordance may be a **colored circle with a contrasting (e.g. white) glyph** rather than the inverse — guessing the wrong way round inverts it.
- **Carve-out — structural SURFACES stay adaptive; do NOT pin them to a sampled literal.** Sample-and-pin is right for **brand / content** colors — the sampled bubble fills, glyphs, wallpaper, and read-receipt ticks: those are identical in light and dark, so keep them pinned. But **structural surfaces / chrome** must bind to Material's **semantic surface tokens** (`ColorScheme.surface`, `ColorScheme.surfaceContainer`, `ColorScheme.surfaceContainerHighest`) so they adapt in dark mode. The reference is almost always a *light* screenshot, so a pinned-white surface (`Color(0xFFFFFFFF)` on the composer background) looks correct in light mode but **breaks in dark mode**: the body stays white under the adaptive (now-dark) chrome — a hard light/dark split. Pin the sampled bubble fills; keep the surface semantic. Verify by toggling the app to dark mode (change the `themeMode:` on `MaterialApp` or the system appearance) — brand/content colors hold, surfaces flip.
- **Recolor foundations via `StreamTheme`, not only Material's `ColorScheme`.** Setting `ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: ...))` on `MaterialApp` recolors Material-themed chrome, but the **message row and bubbles read `StreamTheme`'s `StreamColorScheme`** (the default outgoing bubble is `colorScheme.brand.shade100`, incoming is `colorScheme.backgroundSurface`) — they do **not** follow a Material seed. Recolor those by customizing the `StreamTheme` extension (its `colorScheme`) on `MaterialApp.theme.extensions`; for a specific surface that must not shift (e.g. a sampled bubble fill) set an explicit `Color(0xFFXXXXXX)` on the relevant `messageItemTheme.bubble` entry, with the dark-mode variant on the dark theme.
- **Sampling gotcha:** small colored UI elements get swamped by similar colors in **photo attachments** (blue ticks vs blue sky/water). Isolate the element: restrict the search to its context (e.g. tick pixels that sit on the *green bubble rows*, not the photo rows) before averaging, and sample the saturated **core**, not antialiased edges.
- Verify by sampling your render's colors and diffing against the reference.

### A background may be a TEXTURE, not a flat color — and texture can be what distinguishes two regions

Don't reduce every background to one `Color` — a chat wallpaper is often a **subtle pattern** (e.g. faint repeated doodles / motifs), and that texture — not a divider — is often what separates the chat area from the plain composer.
- **Detect:** sample many points across the background. Low variance → flat fill; faint repeated marks (std of a few units) → a pattern; reproduce it, don't flatten it.
- **Reproduce:** best is the **actual asset** — tile it via `StreamMessageListViewThemeData(backgroundImage: DecorationImage(image: AssetImage('assets/wallpaper.png'), repeat: ImageRepeat.repeat))`. If the art is proprietary, approximate with a **faint tiled motif** (low-contrast **pure-outline** glyphs over the base, offset per row so it's not a grid) and tell the user it's an approximation. Curate to pure-outline glyphs — many icons have filled sub-parts that read as ink blobs.
- **Match it by MEASUREMENT, not eye** — both **ink coverage** (% of a clean patch darker than the base) and **stroke width** (median dark-run width): the same coverage looks subtle with many hairlines or bold with few thick marks. Render glyphs thin (`weight: 100`–`200`) and re-measure your render against the reference until both coverage and stroke match.
- **Keep the distinction without a seam:** texture the message list (`messageListViewTheme.backgroundImage`) but keep the composer a **flat fill in the same base color** — the texture-vs-plain contrast is the separator.
- **API note:** `backgroundImage` is a `DecorationImage` (`ImageProvider` only) — no `CustomPaint` / widget-driven background. For a live/procedural pattern, wrap `StreamMessageListView` in a `Stack` with a `CustomPaint` behind (heavier lift).

### A "weird line" between two regions is almost always a COLOR SEAM, not a divider view

Before hunting for a stray `Divider`, check the obvious cause: a visible line where two regions meet is usually just **two adjacent backgrounds with slightly different fill colors**. **How to decide whether a separator should be there:** sample the reference's color on **both sides** of the boundary:
- Equal within a few units → there should be **no** line → make your two backgrounds the **same** color (or the **same theme token** — e.g. `colorScheme.surfaceContainer` on both). The classic case: a messenger's composer bar and its wallpaper are the **same near-neutral color** (their sampled hexes differ by only a unit or two); sampling both sides reveals the match — set both surfaces to the same value.
- Reference shows a deliberate contrasting hairline → reproduce it deliberately (e.g. a `Divider(height: 0.5, color: <measured>)` between the message list and the composer inside your `Column`).

Two Flutter-specific sources to rule out:
- (a) **A stray `Divider()` between `Expanded(StreamMessageListView())` and `StreamMessageComposer()`** in your `Column` — remove or recolor.
- (b) **The `Scaffold` background color bleeding through a 1-lp gap** between the message list and the composer if their backgrounds don't touch. Set `Scaffold.backgroundColor: colorScheme.surface` to match the composer.

### Spacing scale

Use consistent literal values for spacing and radius that match your measurements — 8, 12, 16, 24 lp are a common scale. Read the SDK's own paddings inside its widgets before adding your own, so you don't double-pad — e.g. `StreamMessageComposer` already applies its own inset around the leading/input/trailing row (read the exact value from the pinned source — don't assume a token or a round number like `8`/`16`), and factor that into your outer margins.

### Region checklist (walk all of these)

**Channel list screen** (if in scope)
- [ ] List header (title, search, buttons) · list item layout · avatar · swipe actions · empty/loading/error state · background

**Message screen — chrome**
- [ ] Navigation header: title, subtitle, back affordance, trailing avatar/buttons
- [ ] Chat background / wallpaper
- [ ] Date separators (the "Thu, Mar 12" pill) and the new-messages divider
- [ ] Scroll-to-bottom / jump-to-unread overlays

**Message screen — the message itself**

> **A one-sided reference is not a global rule — don't globalize the single frame you were given.** A messenger screenshot usually shows only the viewer's **own** (right-aligned) messages; that does **not** mean every message is right-aligned. Keep the messenger default (own = right / other = left — the SDK does this automatically; don't override it to match a one-sided reference) and **seed an incoming message to confirm both sides**. Same for content: a reference showing only image messages doesn't mean text messages lose their timestamp. For anything the reference doesn't show, follow the platform convention.

- [ ] **Layout style: bubbles (messenger) vs flat left-aligned rows (workplace/Slack).** Decides everything below — bubbles → restyle via `StreamTheme.messageItemTheme` (bubble/text/attachment sub-styles) and, when needed, replace `messageItem` via the component-builder factory; flat workplace rows (avatar-top, header line, bottom reactions, thread summary, no in/out split) → build the workplace archetype (see the section below).
- [ ] Bubble: fill color, border, corner radius, **tail/beak shape**, max width, alignment
- [ ] Bubble grouping (consecutive messages, who shows an avatar) — grouping is exposed inside a custom `messageItem` via `StreamMessageLayout.of(context)` (re-exported unprefixed by `stream_chat_flutter`; returns a `StreamMessageLayoutData`), which carries alignment + placement info the default row uses.
- [ ] **Metadata placement**: where do the timestamp and the delivery/read receipts sit — below the bubble (Stream default) or **inside it, bottom-trailing** (WhatsApp/iMessage)? This is structural.
- [ ] Read/delivery indicator glyphs (single/double tick, color)
- [ ] Avatars next to messages (shown? side? shape?)
- [ ] Reactions (style, position — overlay vs. attached)
- [ ] Quoted / inline replies, thread reply summary
- [ ] Long-press message actions menu
- [ ] Any per-message affordances (e.g. a floating forward/reply arrow beside a bubble)

**Message screen — attachments**
- [ ] Image/photo grid (1/2/3/4+ grouped collage with "+N" is **already the Stream default** — do not rebuild it, only restyle if needed)
- [ ] Video, file, giphy, link, voice-recording, poll, custom attachments — customized via the per-type attachment component slots (`videoAttachment`, `fileAttachment`, …) globally, or `attachmentBuilders` on a `messageBuilder` per-message
- [ ] The full-screen media viewer / gallery

**Composer** (almost always differs from default — inspect closely)
- [ ] Leading button(s) — e.g. a `+` attachment button on the left
- [ ] The input field container and the text input
- [ ] Icons *inside* the field, trailing edge — e.g. a sticker/emoji glyph
- [ ] Buttons to the *right* of the field — e.g. camera + microphone
- [ ] Send button glyph/placement; voice-record vs. send swap
- [ ] Attachment picker sheet (inline in Flutter — not a separate modal), command/slash suggestions, edit/quote states

**Cross-cutting**
- [ ] Fonts (`Theme.of(context).textTheme` + your custom `fontFamily` on `MaterialApp.theme`), accent color, icon set
- [ ] Light/dark behavior — toggle and verify

State the result as a task list: `Region → default vs. target → mechanism (theming token / widget builder / widget replacement / already-default / source-dive needed)`. Implement **all** differing regions, not just the cheap theming ones.

---

## Step 2: Region → mechanism map (verified against the pinned SDK source)

Slot names below are the parameter names on `StreamMessageListView`, `StreamMessageComposer`, `StreamChannelListView`, and property paths on `StreamChatThemeData`. Override only what you need; the rest fall back to defaults. **Confirm the exact signature + prop names against the source for the pinned version before using them** — this map is for routing, not verbatim API (see "Grounding" in Step 3).

> **These tables (and every list in this doc) are a curated routing map, NOT a complete inventory.** If the region, slot, theme token, or prop you need isn't listed here, that means *not documented in this skill* — it does **not** mean *unsupported*. Before concluding a customization is impossible or hand-rolling it, grep the authoritative source (Step 3): the `streamChatComponentBuilders(...)` + core `StreamComponentBuilders` factories for slots, the `*ThemeData` classes for theme tokens, the `*Builders` / `*Configuration` classes for per-widget builders. Assume the component exists until the source says otherwise.

### Header / chrome

| Design region | Slot(s) / token | Notes |
|---|---|---|
| Channel header (title, subtitle, back, trailing) | Build your own `AppBar` in your `Scaffold(appBar:)` — `StreamChannelHeader` is the pre-built default, or replace it with any `AppBar`. Theme via `channelHeaderTheme` (`StreamAppBarThemeData`). | Title MUST be model-driven — see the model-driven title trap below. |
| Header visibility | `Scaffold.extendBodyBehindAppBar` (for content that scrolls behind a transparent app bar) + `Scaffold.appBar` (null → no header). | — |
| Chat wallpaper / background | `StreamChatThemeData(messageListViewTheme: StreamMessageListViewThemeData(backgroundColor: …, backgroundImage: DecorationImage(image: AssetImage('assets/wallpaper.png'), fit: BoxFit.cover, repeat: ImageRepeat.repeat)))` | `backgroundImage` accepts `ImageProvider` only — no widget builder. For a live/procedural pattern, wrap the list in a `Stack` with a `CustomPaint` behind. |
| Date separator pill (inline) | `StreamMessageListView(builders: StreamMessageListViewBuilders(dateDivider: (dt) => …))` | — |
| Sticky floating date | `builders.floatingDateDivider: (dt) => …` | Toggle whole feature via `config: StreamMessageListViewConfiguration(showFloatingDateDivider: true/false)`. |
| New-messages divider | `builders.unreadMessagesSeparator: (context, unreadCount) => …` | Toggle via `config.showUnreadIndicator`. |
| Scroll-to-bottom / jump-to-unread | `builders.scrollToBottomButton: (unreadCount, defaultTap) => …` + `config.showScrollToBottom`, `config.showUnreadCountOnScrollToBottom` | — |
| Message list background wrapper | `messageListViewTheme.backgroundColor` for a solid fill; wrap `StreamMessageListView` in a `Container(decoration: BoxDecoration(gradient: ...))` for a gradient. | — |

**Model-driven title trap.** The channel-list screenshot is **one specific channel's** name, but your header renders for **every** channel. Never hardcode the reference's literal string. Compute the title from the channel model in one place and reuse it in both the list item and the header:

```dart
String resolveChannelName(Channel channel, String? currentUserId) {
  final name = channel.name;
  if (name != null && name.isNotEmpty) return name;
  final custom = channel.extraData['name'];   // some backends store the name here
  if (custom is String && custom.isNotEmpty) return custom;
  // DM / group fallback: member names (excluding the current user)
  final others = channel.state?.members
      .where((m) => m.userId != currentUserId)
      .map((m) => m.user?.name ?? m.userId ?? '')
      .where((s) => s.isNotEmpty)
      .toList() ?? const [];
  if (others.isEmpty) return 'Chat';
  if (others.length == 1) return others.first;
  if (others.length == 2) return '${others[0]} and ${others[1]}';
  return '${others.take(2).join(', ')} and ${others.length - 2} more';
}
```

Use it in **both** the channel-list `itemBuilder` and the header's title. There is no single SDK hook that both surfaces read, so the shared helper is the answer. **Verify on a second channel** — open a DM after seeding: the title must change to that channel's name, not stay at the seeded one.

### Message row, bubble, metadata

| Design region | Slot(s) / token | Notes |
|---|---|---|
| Whole message row (restructure: bubble tail, workplace archetype; **metadata placement is not this row's job** — core `messageContent` slot, see the Metadata placement row below) | `StreamMessageListView(messageBuilder: (context, message, defaultProps) => …)` — the **big hammer**. Return your own row widget (typically `StreamMessageItem.fromProps(props: defaultProps.copyWith(...))` or an entirely custom widget). See "Overriding composite widget" below. | The parameter is `messageBuilder`, **top-level** on `StreamMessageListView` — NOT inside `builders:` (which holds only frame slots). |
| Bubble shape / border / corner radius / padding | `StreamTheme.messageItemTheme.bubble` (a `StreamMessageBubbleStyle`) — `shape` (`OutlinedBorder` wrapped in `StreamMessageLayoutProperty` so it can vary per alignment), `side` (`StreamMessageLayoutBorderSide`), `padding` (a `StreamMessageLayoutProperty<EdgeInsetsGeometry>`, **not** a flat `EdgeInsets` — it resolves by content-kind; see the content-kind rules below this table before overriding it), `constraints` (`BoxConstraints`), `backgroundColor`. Set this via a `StreamTheme` `ThemeExtension` on `MaterialApp.theme.extensions`. For a **bubble tail / beak**, provide a custom shape (implement `OutlinedBorder`) or override the `messageItem` component builder and wrap the bubble in a `ClipPath`. | — |
| Bubble fill color (incoming vs outgoing) | `StreamTheme.messageItemTheme.bubble.backgroundColor: StreamMessageLayoutProperty.resolveWith((p) => p.alignment == StreamMessageAlignment.end ? outgoingColor : incomingColor)` — one property that resolves to the correct color per alignment. | — |
| Bubble text style | `StreamTheme.messageItemTheme.text` (a `StreamMessageTextStyle`) sets text color / font / size for the message body. | — |
| Bubble border color / width | `StreamTheme.messageItemTheme.bubble.side` (a `StreamMessageLayoutBorderSide` that resolves per alignment). | — |
| Timestamp text style | `StreamTheme.messageItemTheme.metadata` (`StreamMessageMetadataStyle`) sets the timestamp text style along with tick color. For a custom time format (12h/24h/relative), override the `messageFooter` component builder and format `message.createdAt` yourself. **To *reposition* metadata** (not just restyle it), note the `messageFooter` slot only stacks below the bubble — override the core **`messageContent`** slot instead, which stays inside the row's gesture layer so the long-press menu + reactions survive the relayout. Write that override as an inline lambda with the props type **inferred** — `StreamMessageContentProps` can't be named in app code (the chat barrel hides core's and doesn't export its own chat-specialized one), so a separately-declared typed helper fails to compile. | — |
| Read / delivery indicator | Theme via `StreamTheme.messageItemTheme.metadata` (a `StreamMessageMetadataStyle`) for tick color / text style. Toggle visibility via `StreamTheme.messageItemTheme.metadataVisibility` (a `StreamMessageLayoutVisibility`). For a fully custom indicator, override the `messageFooter` component builder. There is no per-message `readBy` field, but you needn't hand-roll the math: **send status** is `message.state` (a `MessageState` — top-level `initial` / `outgoing` / `completed` / `failed`, with sending/updating/deleting nested under `outgoing` and sent/updated/deleted under `completed`; confirm the set in the pinned LLC), while **read receipts** come from `channel.state?.readsOf(message:)` → the `List<Read>` that have read that message (live via `channel.state?.readsOfStream(message:)`; the extensions live on `ChannelClientState` and on any `Iterable<Read>`, e.g. `channel.state?.read` — not on `Channel` itself). It returns the reads whose `lastRead` is at/after `message.createdAt`, excluding the sender — each `Read` carries `user`, `lastRead`, and `lastReadMessageId`. | — |
| **Metadata placement** — timestamp / receipt / name moved relative to the bubble (beside it, name above, inside as an overlay) | Core **`messageContent`** slot — a **core** slot, registered on `StreamComponentBuilders(messageContent: …)` directly, **not** under `extensions:`. It receives the row's parts **already built**: `props.header` (the pinned/reminder header — **NOT the author name**), `props.child` (the fully-composed bubble: text, attachments, reactions), and `props.footer` (the default footer — **author name + timestamp + receipt bundled**; the message object is not exposed on these props). Pure re-arrangement is cheap and gesture-safe — beside-the-bubble = `Row[child, footer]`, inside = `Stack` the footer over `child` — and renders **inside the row's gesture layer**, so the long-press actions modal, reaction picker, and grouping all survive (device-verified). **To split what the footer bundles** — e.g. a design that puts the author name ABOVE the bubble and the time BESIDE it — shape the parts with their own chat-extension slots and keep `messageContent` as re-arrangement only: `messageHeader` ext = author name above · `messageFooter` ext = timestamp+receipt only (kills the duplicate name) · `messageContent` = `Row[child, footer]` — the device-verified three-slot combo. Branch per side via `StreamMessageLayout.messageAlignmentOf(context)` / `crossAxisAlignmentOf(context)`; write overrides as inline lambdas with the props type **inferred** (`StreamMessageContentProps` isn't nameable in app code). Do **not** reach for `messageBuilder` / `messageItem` for any of this — the full-row rebuild loses the private long-press/reaction internals (Step 2.5) that these slots keep for free. | — |
| Deleted / system / ephemeral / moderated message | Dedicated frame-level builders on `StreamMessageListView`: `builders.systemMessage: (context, message) => …`, `builders.ephemeralMessage`, `builders.moderatedMessage`. **Deleted** is rendered by `StreamMessageItem` internally when `message.isDeleted`; to customize, handle the case at the top of your `messageBuilder`. | — |
| Avatar beside message | Reuse `StreamUserAvatar(user: message.user!, size: StreamAvatarSize.lg)` inside your `messageItem` component builder or `messageBuilder`. `StreamUserAvatar` renders **circular** (its shape isn't configurable), and `size` is one of the fixed `StreamAvatarSize` buckets (`xs` 20 / `sm` 24 / `md` 32 / `lg` 40 / `xl` 48 / `xxl` 80 lp) — for a rounded-square shape or an off-bucket measured size, build a small custom avatar (a `ClipRRect` around the user's image with an initials fallback). Toggle visibility via `StreamTheme.messageItemTheme.avatarVisibility` and set the default size via `.avatarSize`. Grouping (avatar shown only for last-in-group) is exposed via `StreamMessageLayout.of(context)`. | — |
| Reactions display | Theme: `StreamTheme.reactionsTheme` (bottom pill row), `StreamTheme.reactionPickerTheme` (long-press picker). Replace via the core **`reactions`** slot (attached bottom row — the message row delegates to `StreamReactions`) or the core **`reactionPicker`** slot; both are exported (`StreamReactions` / `StreamReactionPicker`), fed items derived from `message.reactionGroups`, toggled via `channel.sendReaction` / `channel.deleteReaction`. Keep the emoji-per-reaction-type map in one shared `Map<String, String>` used by every reaction UI so row / picker / overlay stay in sync. | — |
| Quoted / inline reply | Reuse `StreamQuotedMessage(quotedMessage: message, onTap: ...)` or override the `quotedMessage` component builder. Theme via `quotedMessageTheme` (on `StreamChatThemeData`) — `shape`, `side`, `backgroundColor`, `titleTextStyle`, `subtitleTextStyle`, `indicatorColor`, `margin`, `padding`, `thumbnailShape`, `thumbnailSide`, `thumbnailSize`. | — |
| Thread reply summary | **Already multi-avatar by default** — the row renders a participant avatar **stack** (all `message.threadParticipants` via `StreamAvatarStack`, with a `maxAvatars` overflow badge) + reply count, so you don't build one. Theme via `StreamTheme.messageItemTheme.replies` (`StreamMessageRepliesStyle` — text / spacing). To restyle the widget or change how many avatars show, override the core **`messageReplies`** slot / reuse `StreamMessageReplies` (`avatars`, `maxAvatars`, `showConnector`). | — |
| Message actions menu (long-press) | Callback: `onMessageActions: (context, message) => showModalBottomSheet(...)` on `StreamMessageItemProps` — set it via a `messageItem` builder (or the top-level `messageBuilder` on `StreamMessageListView`) to open your own sheet. | — |
| Typing indicator | Widget: `StreamTypingIndicator(channel: channel)` — insert into your `Scaffold` above the composer if the design shows one. | — |

**The message row's padding/shape are content-kind-aware — read the default resolver before overriding, and prefer the leaf lever.** `messageItemTheme`'s `bubble`, `text`, and `attachment` styles are `StreamMessageLayoutProperty` values that **resolve per message (alignment, stack position, and `contentKind`)** — not flat constants. Their defaults encode real behavior across those cases (e.g. a lone-attachment message is padded differently from a text or mixed message so it can sit flush inside the bubble), so **replacing one with a single flat value silently clobbers every case you didn't think about.** Two consequences that generate the classic "padding looks wrong / image isn't clipped in the bubble" reports:

- **Horizontal insets live on the leaves, not the bubble.** By default the bubble contributes little/no horizontal padding; the inset you see around text comes from `text.padding` and around attachments from `attachment.padding`. So a uniform `bubble.padding` added to "inset the bubble" **stacks on top of** the leaf padding and over-insets text. Put a text inset on `text.padding`; reach for `bubble.padding` only when you genuinely mean the whole bubble, and keep it content-kind-resolved.
- **The bubble clips its child (`Material(clipBehavior: hardEdge, shape:)`), and some content relies on that clip.** A single-attachment (e.g. a lone image) may not round its own corners — it can depend on the bubble's clip *and* on that case's padding being zero so it reaches the clip edge. A flat non-zero `bubble.padding` insets it off the edge and its square corners show inside the rounded bubble.

General rule: before overriding any of these, ground against the **pinned default resolver** (Step 3) to see what it varies by `contentKind`/alignment, override with a `resolveWith(...)` that preserves the branches you're not changing, and reach for the narrowest leaf (`text` / `attachment`) over the bubble. If you **hand-roll** the row instead of theming (avoid this — Step 2.5), you inherit all of this manually: reproduce the per-content-kind padding, and clip attachments yourself — a `BoxDecoration(borderRadius:)` background does **not** clip its children without `clipBehavior`.

**Gate — overriding any of these adds two mandatory Step-5 checks:** a seeded **lone-image** message whose corners are rounded by the bubble clip (no square corners showing inside the bubble), and a seeded **text-only** message whose horizontal inset matches the reference (not double-padded). No crops of those two states = the override is unverified.

### Workplace / Slack message-row archetype (avatar-top, author·status·timestamp header, bottom reactions, thread summary)

Slack / Teams / Discord-style **workplace** chat is **still a components job** (channel list → message list → composer — stay on `stream_chat_flutter`, not `stream_chat_flutter_core`), but the message **row** is a structurally different shape from a messenger bubble, so you override the `messageItem` component builder (or the top-level `messageBuilder` on `StreamMessageListView`) and reproduce its sub-features (the "composite widget" rules below apply in full — read `StreamMessageItem` + `DefaultStreamMessageItem` in the pinned source and reuse its sub-widgets; the most-dropped element is the incoming avatar + grouping). The canonical workplace row, leading→trailing / top→bottom:

- **No incoming/outgoing split, no bubbles.** Every message renders **identically, left-aligned, full-width**, regardless of sender — do **not** mirror the current user's messages to the right or draw a bubble fill. This is the biggest departure from the messenger archetype: **ignore `message.user!.id == currentUser.id` for layout.**
- **Avatar: rounded-square (not a circle), top-leading**, aligned to the **first text line** — not vertically centered on the whole row. `StreamUserAvatar` renders **circular** and its size is a fixed `StreamAvatarSize` bucket, so a rounded-square avatar at a measured size needs a small custom widget — a `ClipRRect(borderRadius: BorderRadius.circular(6))` around the user's image (`CachedNetworkImage` / `NetworkImage`) with an initials fallback. Match the measured size exactly.
- **Header line (one row):** **author name** (bold) · optional **custom status** (emoji/badge, usually from `user.extraData`) · **timestamp** (compact, e.g. "9:41 AM"). Workplace shows it on the **first message of each grouped run**, inline with the name. Measure each role's weight separately (name `FontWeight.w600`/`w700`, time light/secondary) per "Weight is its own dimension."
- **Body + attachments** below the header, **indented to align under the name** (not under the avatar). Render the body with `StreamMessageText` (re-exported unprefixed by `stream_chat_flutter`) — it handles markdown, mentions, and links; it takes a raw markdown string as its positional argument — `StreamMessageText(text)` (see the reuse note in Step 2.5 for building that string), so don't hand-roll the text spans. **Attachments: render via the SDK default pipeline (see "Attachments" below), overriding only the one type the reference restyles — never hand-roll every type or drop one.**
- **Reactions row at the BOTTOM** as attached pill chips (emoji + count), left-aligned under the body → build a `Wrap` of pills reading from `message.reactionGroups`, and use `StreamTheme.reactionsTheme` for pill fill/border/text style. **Keep the emoji → reaction-type mapping in one place** — define a single app-level `Map<String, String> emojiForType = {'like': '👍', ...}` and read it from every custom reaction UI (row pill, picker, overlay) so they stay in sync.
- **Thread-reply summary** under the message (participant avatars + "N replies" [+ last-reply time]) → reuse `StreamMessageReplies`, which already renders a participant avatar stack + count; pass your own rounded-square avatar widgets as `avatars`, set `maxAvatars`, and `showConnector: false`, aligned under the body (not double-indented). `message.threadParticipants` carries all participants. Open the thread the same way the default does — Flutter's clean path is to call `Navigator.push(context, MaterialPageRoute(builder: (_) => StreamChannel(channel: channel, child: ThreadPage(parent: message))))` (matches the `threadBuilder` you wire on `StreamMessageListView`).
- **Grouping:** consecutive messages from the same author in a short window render **compact** — avatar + name + status hidden, body only. Inside a `messageItem` builder, read `StreamMessageLayout.of(context)` to get the alignment + placement info the default row uses (re-exported unprefixed by `stream_chat_flutter`). Use it to drive `showUserAvatar`/`showUsername` and to indent grouped messages.

Measure the row exactly like any other region (avatar size + corner radius, header font weights/sizes, body indent, reaction-pill size, vertical rhythm) — "a left-aligned name + text" is not the spec.

**Threads are first-class in workplace apps — wire and match them, don't leave them default-styled.** The reply summary on the row, the thread screen's chrome (`StreamThreadHeader(parent: parent)`), and, if in scope, the thread list are all part of the workplace design. Decompose and match each; shipping the SDK default thread UI while the rest is themed is the same "known gap" failure the composer usually is.

**The header is custom too** (Slack's is a workspace/channel title + member-count subtitle + trailing actions) → build your own `AppBar` in `Scaffold(appBar: …)`.

### Attachments

**Default-first.** Render attachments through the SDK's default builder pipeline and override only the one type the reference restyles. "Match every region" (Step 1) does NOT mean hand-building every type — for attachments, *the default IS the match*. Hand-rolling per-type widgets and returning nothing for the types you skipped is a silent drop that ships unnoticed unless your seed data has every type (Step 5). **Never render an unhandled type as an empty widget.**

Works for a keep-default row AND a fully custom row — prepend a custom builder for the one type you're restyling; the rest fall back to defaults:

**Delegate the tap behavior to the SDK when you can.** A keep-default row (`StreamMessageItem.fromProps` / the `attachmentBuilders:` prop) renders through `StreamMessageContent` → `StreamMessageAttachments`, which routes every tap for you — media opens the full-screen gallery, links/files open the URL. Prefer this whenever the row can stay default.

When you hand-build the row you reconstruct the pipeline (the SDK's `StreamMessageAttachments` / `AttachmentWidgetCatalog` are internal), so reconstruct its **tap routing** alongside its rendering. Route by type: `file`/`urlPreview` → `launchURL`; `image`/`video`/`giphy` → the full-screen gallery via the exported `StreamMediaGalleryPreview`:

```dart
// Route taps exactly as the default row does.
void onAttachmentTap(Message message, Attachment a) {
  if (a.type == AttachmentType.file || a.type == AttachmentType.urlPreview) {
    return launchURL(context, a.assetUrl ?? a.titleLink ?? a.ogScrapeUrl ?? '');
  }
  // image / video / giphy → full-screen media gallery.
  final media = message.toMediaGalleryAttachments(
    filter: (it) => const [AttachmentType.image, AttachmentType.video, AttachmentType.giphy].contains(it.type),
  );
  final i = media.indexWhere((it) => it.attachment.id == a.id);
  Navigator.of(context).push(MaterialPageRoute(
    builder: (_) => StreamChannel.value(
      channel: StreamChannel.of(context).channel,
      child: StreamMediaGalleryPreview(attachments: media, initialIndex: i < 0 ? 0 : i),
    ),
  ));
}

final builders = StreamAttachmentWidgetBuilder.defaultBuilders(
  message: message,
  onAttachmentTap: onAttachmentTap,
  customAttachmentBuilders: [const MyLinkBuilder()], // override ONE type; rest stay default
);
final grouped = <String, List<Attachment>>{};
for (final a in message.attachments) {
  final t = a.type; if (t != null) (grouped[t] ??= <Attachment>[]).add(a);
}
for (final b in builders) {
  if (b.canHandle(message, grouped)) return b.build(context, message, grouped) ?? const SizedBox.shrink();
}
return const SizedBox.shrink();
```

- The media builders render the media and invoke `onAttachmentTap` on tap — the gallery-open lives in the routing you supply (or, on a default row, in the SDK's wrapper). Pass the handler above to wire it, so images/videos open the gallery and links open the URL. **Confirm both by tapping: an image opens the gallery, a link opens the URL.**
- `defaultBuilders` covers **every** type (poll · mixed · gallery · file · giphy · image · video · voice · link · unsupported · fallback), so nothing drops.
- `customAttachmentBuilders` are **prepended**, so a custom `canHandle` must be **scoped** (e.g. url-only: `attachments.length == 1 && attachments.containsKey(AttachmentType.urlPreview)`) so it takes over only that one type and mixed messages keep the default media rendering. A builder is `class X extends StreamAttachmentWidgetBuilder` with `canHandle` + `build`.
- **Polls live on `message.poll`, not `message.attachments`** — gate the whole attachment block on `message.attachments.isNotEmpty || message.poll != null`. The poll still renders through the loop above even though `grouped` is built only from `message.attachments`: the `PollAttachmentBuilder`'s `canHandle` reads `message.poll` directly, so it matches on a poll-only message with an empty `grouped`.

Use the per-type slot table below only for a **global** restyle of one type.

| Design region | Entry point | Notes |
|---|---|---|
| Image/photo grid (1/2/3/4+ collage) | Handled by the default attachment rendering — this is already the correct layout for most designs. Restyle via `StreamTheme.messageItemTheme.attachment` (a `StreamMessageAttachmentStyle`) for tint/border/padding. To swap the rendering entirely: `streamChatComponentBuilders(imageAttachment: (context, props) => …, galleryAttachment: (context, props) => …)`. | — |
| Video + media viewer | In-message: `streamChatComponentBuilders(videoAttachment: …, mediaGallery: …, mediaGalleryPreview: …)`. Full-screen viewer: the core `mediaViewer` slot. Theme the viewer chrome via `StreamTheme.mediaViewerTheme`. | — |
| File / giphy / link / voice / poll / unsupported (in-message) | One override per type: `streamChatComponentBuilders(fileAttachment: …, giphyAttachment: …, linkPreviewAttachment: …, voiceRecordingAttachment: …, pollAttachment: …, unsupportedAttachment: …)`. To restyle (not replace) the rendered attachment, use `StreamTheme.messageItemTheme.attachment` (as with the image grid above); the voice-recording bubble also has its own composite theme, `StreamChatThemeData.voiceRecordingAttachmentTheme`. | **Do NOT reach for the `StreamTheme.messageComposer*AttachmentTheme` tokens here** (`messageComposerFileAttachmentTheme`, `messageComposerLinkPreviewAttachmentTheme`, `messageComposerMediaAttachmentTheme`, …) — those style the **composer-side previews** (the attachment chips shown *before* sending), not these received in-message attachments. |
| Per-message override (only some messages) | `StreamMessageListView.messageBuilder` → construct `StreamMessageItem.fromProps(props: defaultProps.copyWith(attachmentBuilders: [MyBuilder()]))`. Use this when the swap is per-message; use component builders when it's global. | — |

### Composer (inspect every sub-slot — it usually differs)

The `StreamMessageComposer` widget has this structure:

```
[ messageComposerLeading ] [ messageComposerInput ] [ messageComposerTrailing ]
                                     |
                     the input pill contains, top→bottom:
                     [ messageComposerInputHeader ]              (quoted-message preview, attachments header)
                     [ messageComposerInputLeading ] [ messageComposerInputCenter ] [ messageComposerInputTrailing ]
                                                            (text field itself)     (send / mic / confirm-edit / slow-mode)
```

Each of these slots (`messageComposer`, `messageComposerLeading`, `messageComposerTrailing`, `messageComposerInput`, `messageComposerInputHeader`, `messageComposerInputLeading`, `messageComposerInputCenter`, `messageComposerInputTrailing`) is a component-builder override registered via `StreamChat(componentBuilders: StreamComponentBuilders(extensions: streamChatComponentBuilders(...)))`. Each override receives a `*Props` object (a subclass of `MessageComposerComponentProps`) carrying: `controller: StreamMessageComposerController` (text + quoted-message state), `onSendPressed`, `voiceRecordingCallback`, `onAttachmentButtonPressed`, `isPickerOpen`, `focusNode`, `currentUserId`, `audioRecorderState`, `onQuotedMessageCleared`, `cooldownTimeOut`, and `isFloating`. The input-level Props (`MessageComposerInputProps` and its subvariants) additionally carry `placeholder`, `textInputAction`, `keyboardType`, `textCapitalization`, `autofocus`, `autocorrect`, `canAlsoSendToChannel`, `audioRecorderController`, `feedback`, and `sendVoiceRecordingAutomatically`.

The top-level `StreamMessageComposer` widget accepts direct props for feature toggles and callbacks that don't need a full component swap:
- `messageComposerController` — text + quoted-message state (create as a `late final` on `State`, dispose in `dispose()`)
- `focusNode` — keyboard focus
- Voice: `enableVoiceRecording` (defaults to **`true`** — set it `false` if the design has no mic/voice button), `sendVoiceRecordingAutomatically`, `voiceRecordingFeedback`
- Attachments: `disableAttachments`, `allowedAttachmentPickerTypes`, `attachmentPickerOptionsBuilder`, `onAttachmentPickerResult`, `useSystemAttachmentPicker`, `attachmentLimit`
- Polls: `pollConfig` — this feature also requires a **server-side dashboard flag** on the channel type; the picker option won't render until it's enabled on the channel type
- Placeholder text: `placeholderBuilder`
- Mentions: `mentionItemBuilder`, `mentionAllAppUsers`, `customAutocompleteTriggers`
- `canAlsoSendToChannelFromThread` — thread composer shows a "Also send in channel" checkbox
- Keyboard: `keyboardType`, `textInputAction`, `textCapitalization`, `autoCorrect`, `autofocus`, `sendMessageKeyPredicate`, `clearQuotedMessageKeyPredicate`
- Callbacks: `onMessageSent`, `preMessageSending`, `onError`, `onQuotedMessageCleared`, `validator`

**The composer is the highest-detail region — budget real attention to it and pass a literal pixel checklist, because users inspect it closely.** A composer that is "recognizably a messenger composer" but off on these points is a FAIL, not done:
- [ ] **Container background** of the whole composer bar — wrap the composer in `Container(color: colorScheme.surface)` in your `Scaffold` body if you need a specific bar fill outside the pill; bind it to a **semantic surface token, not a pinned literal**, so it adapts in dark mode (see the structural-surface carve-out above).
- [ ] **Input-field background, border, corner radius, height — MEASURED** (per Step 1's dimension method; the field is usually shorter and the controls smaller than you'd guess). **Background / border / corner radius** come from foundation tokens — `colorScheme.backgroundElevation1` (fill), `colorScheme.borderDefault` (border), `radius.xxxl` (corner); retint those on `StreamTheme` for a global change, or override `messageComposerInput` for a composer-only one. **Height** is padding-driven — lower `StreamTheme.spacing.sm` (global) or override `messageComposerInputCenter` to tighten the field's internal padding.
- [ ] **Match each glyph — and default to CUSTOM-PAINTING/SVG for distinctive icons, don't settle for a Material lookalike.** A sticker (peeling-square) is not `Icons.emoji_emotions`; a paper-plane send is not an up-arrow. Beyond identity, **Material's outlined icons render with heavier, rounder strokes than the thin-line icons brand apps (WhatsApp / iMessage / Telegram) use — a "close" Material icon reads as *soft / wrong-weight* even at the right size**, and that is exactly the kind of miss users flag. So for a distinctive glyph, reach for a `CustomPainter` (thin stroke, `strokeCap/join = round`) or an SVG rather than the nearest `Icons.*`. Match **size, stroke weight, and color** — and verify weight by cropping the glyph at native `@3x` and comparing stroke thickness, not just the bounding box. **Brand icons are best-effort:** when the customer supplies their own marks (or the exact glyph isn't reproducible), get as close as you can (right stroke weight + proportions) and say what's approximate — "exact" isn't always achievable, but "obviously Material instead of the brand icon" is still a fail.
- [ ] **Vertical alignment / centering of each button against the field** (frame side buttons to the measured field height — per Step 1's centering note). A `+` that looks too low/high or off-center is a classic miss.
- [ ] **Horizontal geometry — MEASURED, not eyeballed (a top-frequency miss).** The SDK composer applies its own horizontal inset around the leading/input/trailing row (read the exact value from the pinned source — don't assume a token or round number), so your leading/trailing widgets start *inside* that inset — the whole row silently shifts right unless you account for it. Don't assume your own leading padding is the whole story; measure and match, in logical px, the **cx of every glyph** (`+`, in-field sticker, camera, mic, send), the field's **left and right edges**, and the **gaps between children** (`+`↔pill, pill↔camera, camera↔mic). Narrow an over-wide leading, and remember: widening the pill↔trailing gap narrows the pill *without* moving the right-aligned camera/mic cluster. See Step 5 (paddings/spacings are first-class regions).
- [ ] **Both states render correctly** — at rest (camera/mic) and typing (send), plus edit/quote/slow-mode/voice-recording. `messageComposerInputTrailing` handles the state swap via `controller.text.isEmpty` + `audioRecorderState` + `cooldownTimeOut` — reproduce **all** states when you override it.

Decompose the composer in BOTH states — **at rest** (no text: leading, field, in-field/right-side buttons, mic) and **typing** (send replaces mic) — they render different sub-views. Then route each region:

| Design region | Entry point |
|---|---|
| Leading button(s) outside the pill (e.g. a `+` left of the field) | `streamChatComponentBuilders(messageComposerLeading: (context, props) => …)`. `props.onAttachmentButtonPressed` opens the inline attachment picker. |
| Icons inside the pill on the leading edge | `messageComposerInputLeading` |
| Input field itself (text field) | `messageComposerInputCenter` — receives placeholder / keyboard config. `StreamTheme.textInputTheme` styles the field's **text / hint / cursor**; for the pill background / border / radius, see the composer checklist above. |
| Icons inside the pill on the trailing edge — including **send / voice-record / confirm-edit / slow-mode** | `messageComposerInputTrailing` — the Props include `onSendPressed`, `voiceRecordingCallback`, `audioRecorderState`, `cooldownTimeOut`. Reproduce all four states. |
| Above-the-input area (quoted-reply preview, attachment thumbnails header) | `messageComposerInputHeader` |
| Buttons outside the pill on the trailing edge (e.g. right-of-field camera + mic cluster) | `streamChatComponentBuilders(messageComposerTrailing: (context, props) => …)` |
| Whole input pill | `messageComposerInput` |
| Whole composer (top-level layout) | `messageComposer` — the biggest hammer; only when the reference genuinely reshuffles the row |
| Voice recording UI | `enableVoiceRecording` + `sendVoiceRecordingAutomatically` + `voiceRecordingFeedback` toggles on `StreamMessageComposer`, plus the `_VoiceRecordingButton` behavior inside the default `messageComposerInputTrailing` (reproduce if you replace that slot) |
| Edit / quote states | Managed on `messageComposerController` — set `.quotedMessage = message` to enter reply state, call `clearQuotedMessage()` to exit. Quoted preview renders in `messageComposerInputHeader`. |
| Attachment pickers | `attachmentPickerOptionsBuilder`, `allowedAttachmentPickerTypes`, `useSystemAttachmentPicker` on the composer. The picker is inline (embedded), triggered by `onAttachmentButtonPressed`. To restyle inline attachment tiles: `streamChatComponentBuilders(messageComposerAttachment: …, messageComposerAttachmentList: …)`. |
| Command / mention suggestions | `customAutocompleteTriggers` on the composer + `streamChatComponentBuilders(mentionItem: (context, props) => …)` |

Wiring pattern — **global** override at the app root, affects every channel screen:

```dart
StreamChat(
  client: client,
  themeData: StreamChatThemeData(/* widget theming */),
  componentBuilders: StreamComponentBuilders(
    extensions: streamChatComponentBuilders(
      messageComposerLeading: (context, props) => MyPlusButton(
        onTap: props.onAttachmentButtonPressed,
        isPickerOpen: props.isPickerOpen,
      ),
      messageComposerInputTrailing: (context, props) => MySendOrMic(
        controller: props.controller,
        onSendPressed: props.onSendPressed,
        voiceRecordingCallback: props.voiceRecordingCallback,
        audioRecorderState: props.audioRecorderState,
        cooldownTimeOut: props.cooldownTimeOut,
      ),
      messageComposerTrailing: (context, props) => Row(children: [
        MyCameraButton(),
        MyMicButton(voiceRecordingCallback: props.voiceRecordingCallback),
      ]),
    ),
  ),
  child: widget,
)
```

**Scoped** override — wrap a specific subtree with `StreamComponentFactory` when only one channel/screen should use custom builders (e.g. a workplace channel with flat rows while other channels keep messenger bubbles). The nearest `StreamComponentFactory` ancestor wins:

```dart
Scaffold(
  appBar: StreamChannelHeader(),
  body: StreamComponentFactory(
    builders: StreamComponentBuilders(
      extensions: streamChatComponentBuilders(
        messageItem: (context, props) => MyFlatWorkplaceRow(props: props),
      ),
    ),
    child: Column(children: [
      Expanded(child: StreamMessageListView()),
      StreamMessageComposer(),
    ]),
  ),
)
```

Rule of thumb: reach for the **global** form when the override should apply everywhere (a consistent app-wide bubble style, a shared send-button glyph, etc.) — and also when the target component sits **deeply nested** (e.g. `messageComposerInputTrailing` inside the composer's input pill), because using the factory means you don't have to thread a builder argument down through the composer's intermediate input widgets just to reach a deeply-nested leaf slot. Reach for the **scoped** form when a single screen or channel needs a different composition from the rest of the app. Use the per-widget `messageBuilder` / `itemBuilder` when you're only tweaking one instance and don't want an `InheritedWidget` in the tree.

### Channel list

| Design region | Slot(s) / token | Notes |
|---|---|---|
| Header / top of channel list screen | Build your own `Scaffold(appBar: AppBar(title: ..., actions: ...))` — theme via `channelListHeaderTheme`. | — |
| Whole tile / item | `StreamChannelListView(itemBuilder: (context, channels, index, defaultWidget) => defaultWidget.copyWith(...))` — **the `copyWith` pattern preserves defaults while tweaking**. To fully replace: return your own `ListTile` / custom widget instead of `defaultWidget.copyWith(...)`. | — |
| Background of list | Wrap `StreamChannelListView` in a `Container(color: ...)` or set `Scaffold.backgroundColor`. | — |
| Divider between tiles | `separatorBuilder: (context, channels, index) => Divider(...)` on `StreamChannelListView` — the builder is `(BuildContext, List<Channel>, int index)`, **not** `(context, index)`. | — |
| Avatar | Use `StreamChannelAvatar(channel: channel)` inside your `itemBuilder` — auto-generated from members if no image is set. To restyle, wrap in a `ClipRRect(borderRadius: ...)` for a rounded-square look. | — |
| Unread-count badge | `StreamTheme.badgeNotificationTheme` (`primaryBackgroundColor`, which defaults to `colorScheme.accentPrimary`) — a `StreamTheme` foundation, **not** `StreamChatThemeData.channelListItemTheme` (that slot carries title/subtitle/timestamp text, background/border, and `attributePosition` — no badge color). | Set your brand accent on `StreamTheme.colorScheme` and the badge follows automatically. |
| Swipe actions | Not a first-class slot on `StreamChannelListView`. Wrap the returned tile from `itemBuilder` in a `Dismissible` or `Slidable` (package) if the design needs swipe. | — |
| Search results | `StreamMessageSearchListView` (separate widget) — see the search section of [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md#message-search). | — |
| Empty / loading / error | `emptyBuilder`, `loadingBuilder`, `errorBuilder` — **top-level** on `StreamChannelListView`, not inside a `builders:` group (this differs from `StreamMessageListView`, which groups them under `builders:`). | Documented in [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md) (channel-list placeholder slots) — "Unlike `StreamMessageListView` (which groups its slots under `builders:`), `StreamChannelListView` takes its placeholder slots as **top-level callbacks**." |

### Theme tokens worth knowing

The theming surface has two layers — each has its own reach. The lists below are the **worth-knowing subset, not the complete set** — for the full field list grep `stream_chat_theme.dart` (`StreamChatThemeData` slots) and `stream_theme.dart` (`StreamTheme` foundations + component themes) per Step 3. A token you don't see here may still exist.

**`StreamChatThemeData`** (passed to `StreamChat(themeData:)`, read via `StreamChatTheme.of(context)`):
- `channelHeaderTheme` / `channelListHeaderTheme` / `threadHeaderTheme` — all `StreamAppBarThemeData`
- `messageListViewTheme` — `backgroundColor`, `backgroundImage: DecorationImage`, `messageHighlightColor`
- `channelListItemTheme` — title/subtitle/timestamp text styles, background, border
- `quotedMessageTheme` — `shape`, `side`, `backgroundColor`, `titleTextStyle`, `subtitleTextStyle`, `indicatorColor`, `margin`, `padding`, `thumbnailShape`, `thumbnailSide`, `thumbnailSize`
- `threadListTileTheme`, `voiceRecordingAttachmentTheme`
- Poll themes: `pollCreatorTheme`, `pollInteractorTheme`, `pollResultsSheetTheme`, `pollOptionsSheetTheme`, `pollCommentsSheetTheme`, `pollOptionVotesSheetTheme`

**`StreamTheme`** (registered as a `ThemeExtension` on `MaterialApp.theme.extensions: [StreamTheme.light().copyWith(...)]`, read via `StreamTheme.of(context)`):
- Foundations — `colorScheme` (`StreamColorScheme`), `textTheme` (`StreamTextTheme`), `typography`, `spacing`, `radius`, `icons`, `boxShadow`, `brightness`
- **`messageItemTheme`** — `padding`, `spacing`, `backgroundColor`, `avatarSize`, `avatarVisibility` / `annotationVisibility` / `errorBadgeVisibility` / `metadataVisibility` / `repliesVisibility`, plus the sub-styles: `bubble` (`StreamMessageBubbleStyle`), `text` (`StreamMessageTextStyle`), `attachment` (`StreamMessageAttachmentStyle`), `annotation`, `metadata` (`StreamMessageMetadataStyle` — read receipts, timestamp), `replies` (`StreamMessageRepliesStyle`)
- `avatarTheme`, `reactionsTheme`, `reactionPickerTheme`, `mediaViewerTheme`, `contextMenuTheme`, `contextMenuActionTheme`, `emojiButtonTheme`, `emojiChipTheme`, `commandChipTheme`, `jumpToUnreadButtonTheme`, `progressBarTheme`, `playbackSpeedToggleTheme`, `audioWaveformTheme`, `onlineIndicatorTheme`
- Composer attachment themes: `messageComposerAttachmentTheme`, `messageComposerFileAttachmentTheme`, `messageComposerMediaAttachmentTheme`, `messageComposerLinkPreviewAttachmentTheme`, `messageComposerReplyAttachmentTheme`, `messageComposerEditMessageAttachmentTheme`, `messageComposerUnsupportedAttachmentTheme`
- Widget-shape themes: `appBarTheme`, `bottomAppBarTheme`, `buttonTheme`, `checkboxTheme`, `switchTheme`, `stepperTheme`, `snackbarTheme`, `sheetTheme`, `sheetHeaderTheme`, `skeletonLoadingTheme`, `textInputTheme`, `listTileTheme`, `badgeCountTheme`, `badgeNotificationTheme`

Rule of thumb: **content colors and structural chrome that apply to `stream_chat_flutter`'s named widgets** live on `StreamChatThemeData`; **design-system foundations** and **fine-grained per-part styling (bubble shape, message text, reactions pill, avatar chrome)** live on `StreamTheme`. Bubble color / shape / padding and message text live on `StreamTheme.messageItemTheme`; **reactions**-pill styling is on `StreamTheme.reactionsTheme` and **avatar** chrome on `StreamTheme.avatarTheme` (both separate top-level `StreamTheme` fields, not `messageItemTheme`) — but all under `StreamTheme`, not `StreamChatThemeData`.

---

## Step 2.5: Overriding a composite widget inherits ALL of its sub-features

**Guiding principle — reuse the SDK's own components and behaviors, even when you replace a parent or a related component.** Replacing one widget is a reason to plug the SDK's own sub-widgets and default handlers into your replacement, and to reproduce the behaviors the parent used to provide. Before building any picker, menu, tap handler, row, avatar, or interaction of your own, find the public SDK component or handler that already does it — check the package's barrel exports and read the default widget's source — and use it. When the exact widget you want is internal (not exported), reproduce its **behavior** from the exported pieces, not only its appearance. Hand-build only the piece the design genuinely requires, and wire the SDK's own pieces around it. Keep the default widget (restyled via theme) whenever it can reach the design, since that inherits every built-in interaction for free.

The high-level slots — `messageBuilder` (whole message row), a wholesale composer replacement, `itemBuilder` on the channel list — each render **many** sub-features internally. When you override one, every sub-feature the default drew **disappears unless you reproduce it.** A custom row that handles only the case in front of you (one outgoing image bubble) silently drops avatars, grouping, reactions, replies, and status — and a near-empty test channel hides the loss until the user spots it.

**Rule:** before overriding a composite slot, open the default widget in the pinned source — for the message row that's `~/.pub-cache/hosted/pub.dev/stream_chat_flutter-<VER>/lib/src/message_widget/stream_message_item.dart` (specifically `DefaultStreamMessageItem`) plus `message_widget/components/stream_message_content.dart` — read its `build()`, and enumerate every sub-view. For each one, decide: reproduce it (reusing the SDK's own sub-widget) or consciously drop it, and if you drop it, tell the user. Prefer the **narrowest slot** that achieves the change; reach for the big hammer only when a structural change truly needs it (metadata inside the bubble, a bubble tail).

**Reproduce the BEHAVIOR, not just the appearance — but know what is a built-in default vs. what you always wire yourself.** A default row / composer / tile is interactive, and a custom version that reproduces the LOOK but not the behavior is an inert look-alike — easy to miss because it still screenshots correctly. Keeping the behavior isn't one rule, though; each interaction falls into one of three buckets (verify the specifics against the pinned source — the shape is stable but exact names/defaults move):

- **SDK-internal defaults — wired *inside* the default widget, working out of the box, and NOT forwardable.** The message row's long-press → actions modal, tap-a-reaction → reaction detail sheet, the long-press reaction picker, link tap → open URL (`launchURL`), and quoted-message tap → scroll-to-original are all handled in **private** methods of `DefaultStreamMessageItem` / `StreamMessageListView` (the `on*` props only *override* them; leaving a prop null keeps the default). The composer's send / attachment-`+` / voice-record buttons are the same — the default composer calls `channel.sendMessage` etc. internally. Because these live in private code, **you cannot hand-forward them.** The only way to keep them is `StreamMessageItem.fromProps(props: defaultProps.copyWith(...))` (row) — which preserves every internal default while you restyle. A row **hand-built from scratch loses them and cannot cheaply rebuild them**; if you must hand-build, reproduce what you can and **tell the user which defaults (e.g. the actions modal, the reaction sheet) are gone.** This is the single strongest reason to prefer `fromProps` over a from-scratch row.
- **Callbacks you MUST forward when you replace a SLOT that receives them.** A slot override is handed the *real* working callback in its `*Props` and the control is dead unless your widget calls it. The composer sub-slots are the main case: `messageComposerInputTrailing` receives `props.onSendPressed` / `props.voiceRecordingCallback`, `messageComposerLeading` receives `props.onAttachmentButtonPressed` — build a send/mic/`+` button that ignores them and sending / recording / the attachment picker silently do nothing. Forward every such callback the slot's Props expose (the composer wiring example below does this).
- **App-provided wiring the SDK never does for you — navigation above all.** The channel list ships **no** tap-to-open-channel behavior: you set `onChannelTap` on `StreamChannelListView` (the SDK forwards it to the tile's `onTap`; null → the tap is a no-op), or wire the tile's `onTap` yourself if you fully replace the tile. Thread navigation is the same — the row's thread-summary tap only opens a thread when you pass `threadBuilder` (or `onThreadTap`) to `StreamMessageListView`; with neither it's a no-op even in the stock widget. And `onMentionTap` / `onUserAvatarTap` are null-default no-ops in the stock widget too. **None of these are "out-of-the-box behavior that breaks"** — they're wiring you owe whether you customize or not; the point is just to not forget them when you're assembling a screen.

**Wire only what would otherwise be lost — don't re-wire what's already intact.** The test is *"does this functionality disappear if I skip the wiring?"*, not *"does a callback param exist?"*. Redundant wiring is a real failure mode in the other direction:
- When you keep the default widget or go through `fromProps` / `defaultWidget.copyWith(...)`, the internal defaults **and** every callback the `defaultProps` already carry stay connected — re-passing them by hand is noise, and forwarding a `null` (or a hand-rolled reimplementation) can *break* the default you meant to keep. Only `copyWith` the specific props you're actually changing.
- Forward a callback (bucket 2) only where your override genuinely replaced the code that invoked it — a narrow slot override doesn't need the callbacks it never touches (styling `messageFooter` doesn't involve `onSendPressed`).
- *Add* an opt-in tap (`onMentionTap`, `onUserAvatarTap`, a channel/thread nav callback) only when the reference actually shows that affordance. Wiring an interaction the design doesn't have is scope creep, not fidelity.

**`DefaultStreamMessageItem` (the default row) composes these principal parts — all public widgets you can reuse directly. This is a starting summary, NOT an exhaustive inventory (the row also renders quoted-reply previews, pinned/annotation indicators, error/retry badges, upload progress, giphy actions, polls, etc., some of them internal) — enumerate the rest from its `build()` per the rule above. The deleted / system / ephemeral / moderated cases are handled via slots or `message` state, not a widget import.**
- `StreamMessageLeading` (avatar side of the row — for incoming, an avatar via `StreamUserAvatar`; hidden for grouped-run middle messages) — **public**
- `StreamMessageHeader` (pinned/reminder header) — **public**
- The **bubble** (`StreamMessageBubble`, **public**) — the styled container the message content renders inside.
- The **message text** — **public**: `StreamMessageText` (markdown with mentions and links; see the reuse note below for feeding it a string).
- The **attachment collage / gallery** (the 1/2/3/4+ layout per type) — exported: `StreamGalleryAttachment` / `StreamImageAttachment` / `StreamMediaGallery`. **These are NOT turnkey** — `StreamGalleryAttachment` requires you to supply an `itemBuilder` (and a `message` + `attachments`), so it is not a one-line drop-in. **The reliable reuse of the collage is `StreamMessageItem.fromProps(props: defaultProps.copyWith(...))`** — it renders the collage with the SDK's own orientation/grid logic intact. **Do NOT hand-roll the album unless you must**: a hand-rolled album has to re-derive the messenger orientation rules (landscape pairs stack vertically, portrait pairs sit side-by-side, 3 = 1+2, 4+ = grid with "+N"), and getting that wrong is a visible failure.
- The **bottom reactions pill row** (tapped to open the picker) — **public**: `StreamReactions`, themed via `StreamTheme.reactionsTheme`.
- `StreamMessageFooter` (author name if visible, timestamp, delivery/read indicator via `StreamTheme.messageItemTheme.metadata`, edited label, send-failure indicator) — **public**
- `StreamMessageReplies` (thread reply summary — participant avatar **stack** + "N replies") — **public**
- `onMessageTap`, `onMessageLongPress`, `onMentionTap`, `onUserAvatarTap`, `onReactionsTap`, `onReplyTap`, `onThreadTap`, `onMessageLinkTap`, `onMessageActions`, `onQuotedMessageTap`, `onViewInChannelTap`, `onEditMessageTap`, `onBouncedErrorMessageActions` — all wired from `StreamMessageItemProps`
- Deleted state: rendered internally as a deleted-message placeholder when `message.isDeleted` — customize by handling `message.isDeleted` at the top of your builder. System / ephemeral / moderated rows are customized via the `systemMessage` / `ephemeralMessage` / `moderatedMessage` slots on `StreamMessageListView.builders` (not by importing their default widgets).

**Reuse the SDK's public sub-widgets inside your custom row instead of reinventing them:** `StreamUserAvatar`, `StreamQuotedMessage`, `StreamMessageLeading` / `StreamMessageHeader` / `StreamMessageFooter`, and `StreamMessageBubble` / `StreamMessageReplies` — all available unprefixed from `package:stream_chat_flutter/stream_chat_flutter.dart` (the last two are foundation widgets re-exported by it). **For the message body text, use `StreamMessageText`**: it renders markdown, mentions, and links, but takes a **raw markdown string** as its positional argument (`StreamMessageText(text)`), so build the string first — `message.translate(langCode).replaceMentions().text?.replaceAll('\n', '\n\n').trim()` — rather than falling back to a plain `Text(message.text)` (which loses markdown, mentions, and links). **Attachments and reactions also have public drop-ins:** the collage/gallery (`StreamGalleryAttachment` / `StreamImageAttachment` / `StreamMediaGallery`) and the reactions row (`StreamReactions`, fed items built from `message.reactionGroups`) are all exported. So in a hand-built row you can drop those in directly; or keep the default row via `StreamMessageItem.fromProps(props: defaultProps.copyWith(...))` (which preserves the default attachment + reaction rendering while you tweak props). Instead of overriding `messageItem` wholesale, prefer replacing a narrower slot — `messageLeading` (avatar), `messageHeader`, `messageFooter` (metadata row), or `quotedMessage` — via `streamChatComponentBuilders(...)`. The wider `messageItem` builder is the right choice only when the reference reshuffles the row's structure (Slack-style flat layout, bubble with tail, metadata inside the bubble).

**When you do hand-build with these sub-widgets, wire their interaction params yourself — a reused sub-widget renders but stays inert until you do** (per the behavior rule above). Give each the callback that makes it act: `StreamUserAvatar(onTap:)`, `StreamQuotedMessage(onTap:)`, the reactions row's send/delete toggle (`channel.sendReaction` / `channel.deleteReaction`), the replies summary's thread-open (`Navigator.push` to your thread page). Confirm each param's exact name in the pinned source. The flip side is the reason to lean on `fromProps`: the default row's *internal* interactions (long-press → actions modal, tap-reaction → detail sheet, quoted-tap → scroll) live in **private** methods you can't call from a hand-built row — so a from-scratch row reproduces the callback-based affordances but not those, and `fromProps` is the safer choice whenever you only need to restyle.

**Decompose a message row into CONTENT vs CHROME — and implement chrome ONCE for all message types.** A row is **content** (per type: text, media collage, giphy, file, poll…) plus **chrome** that every message carries regardless of content: the reply/forward affordance, timestamp + delivery/read receipts, selection, long-press actions, reactions. The trap is branching early on content type (`if hasImage … else text …`) and building each branch's timestamp/affordance inline — that guarantees divergence (the reply circle lands on images but not text; timestamps sit in different places; a third type gets neither). Instead:
- Render **content through ONE path** — `StreamMessageItem.fromProps(...)` already handles every type (text, media, giphy, files) — and, **by default, apply chrome uniformly around it in a single `messageBuilder` wrapper.** Push per-content spacing to the **theme** (`bubble.padding` for the frame, `text.padding` for text breathing room, `attachment.padding: 0` for media) rather than into per-type branches.
- The **`IntrinsicWidth` hug pattern:** `StreamMessageItem` fills the available width and right-aligns internally, so a floating affordance placed beside it lands mid-margin unless you shrink the message to its content. Wrap it: `Row(mainAxisAlignment: end)[ replyCircle, gap, IntrinsicWidth(Stack[ StreamMessageItem, Positioned(timestamp) ]) ]` — `IntrinsicWidth` shrinks the message to the bubble so the affordance hugs it for text AND media alike.
- **But DEDUCE it from the reference — don't over-apply.** "Uniform chrome" is the sensible *default* (it kills the "affordance on images, missing on text" bug), not a law. Real designs sometimes vary chrome by type: a timestamp overlaid *on* a photo (white, with scrim) but placed *below* text; a forward affordance only on media; receipts hidden on system messages. So: (1) default to one wrapper applying chrome to all types; (2) inspect the reference **per message type present** and, where a design genuinely renders an affordance differently by type, branch that one affordance deliberately (still through the one wrapper, just a per-type variant), and say so. For a type the reference doesn't show, follow the platform's known convention rather than guessing.

Reactions data configuration — keep the reaction-type → emoji mapping in one shared `Map<String, String>` at app scope and read it from every custom reactions widget (row pill, picker, overlay). Toggle a reaction on tap via the channel controller — `channel.sendReaction(message, Reaction(type: 'like'))` / `channel.deleteReaction(message, Reaction(type: 'like'))`.

**Reactions overlay — replace only when explicitly asked.** The long-press reactions picker + actions menu is provided by the SDK and can feel messenger-ish; a workplace/Slack design may prefer a modal bottom sheet with a horizontal quick-reactions scroll + action tiles + action list. Building this replaces the SDK default, which is a sizeable change — do it only when the user explicitly asks. When you do, use `onReactionsTap: (message) => showModalBottomSheet(context, isScrollControlled: true, builder: (_) => YourSheet(message))` and, for the long-press, `onMessageLongPress: (message) => showModalBottomSheet(...)`.

### The channel header traps

Build your `AppBar` in `Scaffold(appBar: …)`; it renders where you place it. Two traps to watch for:

- **Model-driven title** — see the "Model-driven title trap" box above. Never hardcode.
- **Verify on the pushed channel screen**, not just an open-directly scaffold. A header that renders correctly when you `Navigator.push` to `ChannelPage()` from the channel list is the real test — a direct-open scaffold exercises only the body, not the push transition or the back button. See Step 5.

---

## Step 3: Grounding (do not guess widget signatures)

Per [`RULES.md`](RULES.md) "Reference discipline": confirm every builder / theme prop against the pinned SDK before use. Small releases can add or rename slots.

**First, resolve the two source roots — don't hardcode or guess a version.** You need the `lib/src` root of two *different* packages: **`stream_chat_flutter`** (the pre-built UI — widgets, themes, chat factory extensions) and **`stream_core_flutter`** (the `StreamTheme` foundations + the component factory). `stream_core_flutter` is pulled in **transitively** by `stream_chat_flutter` — integrators never add it to `pubspec.yaml`, and its version (`0.4.x`) is unrelated to the chat version (`10.x`), so never reuse one version for the other. Resolve each package's on-disk root from the project's **resolved package graph**: `.dart_tool/package_config.json` maps every package (transitive ones included) to its `rootUri` — read the entry for each package name and take its root. If `.dart_tool/` isn't there yet, run `flutter pub get` first, or fall back to the per-package `version:` in `pubspec.lock` and the matching pub-cache folder. Point `CHAT` and `CORE` at the two resulting `.../lib/src` paths. Don't confuse either with **`stream_chat_flutter_core`** — the headless controllers used only on the custom-UI path; three similarly-named packages.

```bash
# $CHAT and $CORE = the two resolved <package>/lib/src roots from the step above.

# every slot on StreamChatThemeData
grep -nE "^\s+final \w+" "$CHAT/theme/stream_chat_theme.dart"

# every prop on StreamMessageItem + StreamMessageItemProps
grep -nE "this\." "$CHAT/message_widget/stream_message_item.dart" | head -80

# every prop on StreamMessageComposer
grep -nE "this\." "$CHAT/message_input/stream_message_composer.dart" | head -80

# every per-slot MessageComposer*Props (leading / trailing / input / inputLeading / inputCenter / inputTrailing / inputHeader)
grep -nE "^class Message|^  final " "$CHAT/components/message_composer/message_composer_component_props.dart" | head -80

# CHAT composite slots — every registration slot on streamChatComponentBuilders(...)
grep -nE "StreamComponentBuilder<" "$CHAT/components/stream_chat_component_builders.dart" | head -40

# CORE leaf slots — every named slot on the StreamComponentBuilders factory (messageBubble / messageText / reactions / reactionPicker / mediaViewer / jumpToUnreadButton / textInput / avatar / …)
grep -nE "StreamComponentBuilder<" "$CORE/factory/stream_component_factory.dart"

# every builder / config field on StreamMessageListView
grep -nE "this\." "$CHAT/message_list_view/message_list_view.dart" | head -60
grep -nE "this\." "$CHAT/message_list_view/stream_message_list_view_builders.dart" | head -40
grep -nE "this\." "$CHAT/message_list_view/stream_message_list_view_configuration.dart" | head -40

# StreamTheme (foundation layer) — messageItemTheme + all component themes
grep -nE "^  final " "$CORE/theme/stream_theme.dart" | head -40
grep -nE "^  final |this\." "$CORE/theme/components/stream_message_item_theme.dart" | head -40
```

> **Do NOT conclude "no `copyWith` / no such field" from grepping the hand-written `.dart` alone — much of the theming API is CODE-GENERATED into a sibling part file.** `StreamTheme`, `StreamColorScheme`, the `*ThemeData` classes, and the `*Props` classes are typically declared `with _$ClassName` and pull their `copyWith`, `lerp`, and per-field constructor params from a generated `part` file (`*.g.theme.dart` / `*.g.dart`) — those members are **not** in the file you grepped above. Before deciding a method/field is missing, check for a `part '...g.theme.dart';` (or `part '...g.dart';`) directive at the top of the hand-written file and read that part file too (look for `mixin _$ClassName`). This is exactly how `StreamTheme.light().copyWith(...)` and `StreamColorScheme.light().copyWith(...)` are valid despite `copyWith` being absent from `stream_theme.dart` / `stream_color_scheme.dart`. **Confirm the actual member/param list against the generated part file in the pinned version rather than assuming** — the codegen convention is common here but verify it per class.

> **Verify a widget is EXPORTED, not merely present in `src/`, before you `import` and use it.** Reading the SDK source surfaces widgets that live under `lib/src/` and are used *internally* — e.g. `StreamMessageAttachments`, and the chat-level `StreamMessageText(message: ...)` — but are **not re-exported by the package barrel**, so app code can't import them. Confirm every widget **against the barrel exports**, not just the source: `grep -n "export" .../lib/stream_chat_flutter.dart`.
>
> **One caveat from reading source: ignore the `core.` prefix you'll see on foundation widgets there.** The SDK internally aliases `import 'package:stream_core_flutter/chat.dart' as core;`, so its own files write `core.StreamMessageText`, `core.StreamReactions`, etc. **App code never does this.** `stream_chat_flutter` re-exports those foundation widgets, so import only `package:stream_chat_flutter/stream_chat_flutter.dart` and use them **unprefixed** — `StreamMessageText(text)`, not `core.StreamMessageText(text)`. Copying the prefix into app code is a compile error (`Undefined name 'core'`), and adding a `stream_core_flutter` import to make it resolve trips `depend_on_referenced_packages` (it's a transitive-only dep). There's no ambiguity to prefix around: the internal chat `StreamMessageText(message: ...)` isn't exported, so the only `StreamMessageText` in app scope is the core one, which takes a raw markdown string positionally.

Read the **default widget** the slot returns before overriding — for the message row that's `DefaultStreamMessageItem` in `stream_message_item.dart` and its message-content composition (in `message_widget/components/`); for the composer, the default composer state in `stream_message_composer.dart` and each `Default*` in the `components/message_composer/*.dart` files. Then reuse the SDK's public sub-widgets, or reconstruct the whole row with `StreamMessageItem.fromProps(props: defaultProps.copyWith(...))` — that keeps grouping, deleted-state, ephemeral messaging, and read receipts intact. See **Step 2.5** for the principal composed parts and how to reuse them — but treat that list as a starting point, not an inventory: enumerate the rest from the default's `build()` as above.

**Live docs (fetch when in doubt):** `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-chat-and-theming.md`, `.../message-list/stream-message-list-view.md`, `.../message-input/stream-message-composer.md`, `.../channel-list/stream-channel-list-view.md`, `.../reactions.md`.

---

## Step 4: Build the customized widgets

Assemble the customizations in the app's existing structure — **do not restructure navigation** (per [`RULES.md`](RULES.md) "Project ownership").

**Fix at the lowest altitude that works — and match the size of the change to the size of the problem.**
- **Disambiguate an ambiguous design term BEFORE acting.** Feedback terms are ambiguous: "padding" = inner frame *or* outer margin; "start/end" = horizontal *or* which side of what. Before committing to a change, either ask which region/measurement is meant, or measure **all** candidate interpretations (inner frame per-side AND outer margin) and show which is actually off. Don't spend a structural change on an assumed reading. (Real miss: "bubble start/end padding is off" was read as outer width and led to replacing the whole media gallery — when the actual fix was a one-line inner `attachment.padding`.)
- **Exhaust theme/builder levers before replacing an SDK subsystem.** Check every relevant knob (`bubble.padding`, `attachment.padding`, `text.padding`, the component builders) and read the subsystem's source to find where a value comes from, before concluding "no lever exists" and reimplementing it.
- **Surface a subsystem-replacement tradeoff BEFORE doing it, not after.** Swapping out an SDK subsystem (media gallery, composer text field, reactions overlay) for a cosmetic gain loses real functionality (N-image layouts, video/file support, upload states, fullscreen; or drafts/mentions/commands/voice) — state the cost and the size of the gain, and get a yes first. (This is the inverse of Step 5's under-fix failure — under-delivering and labelling the rest a "known gap." Both are miscalibrated proportionality.)
- **A cosmetic complaint is a restyle, not a feature removal — as a default, not an absolute.** When a region "looks wrong" (the date pill, the reactions row, receipts), the fix is almost always to change how it *looks* (shape, color, weight, radius), not to disable or remove the underlying SDK feature. Reach for restyling first; only remove/disable a feature (e.g. the floating date divider) when the developer **explicitly** asks for it or the reference genuinely lacks it. (Real miss: "the date pill looks wrong" — actually just a too-square shape + grey text — was over-corrected by *removing the floating date divider* the user never asked to drop.)

Assemble each change at its entry point — the two axes from the top of this doc:

- **Theming (Axis 1)** → set foundation tokens and message-row/leaf styling (bubble shape/color/padding, text, reactions, avatar) on the `StreamTheme` extension, and build a `StreamChatThemeData(...)` for the chat composite-widget slots passed to `StreamChat(themeData:)`. Recolor the whole UI via `MaterialApp.theme.colorScheme` (`ColorScheme.fromSeed(seedColor: ...)`). Verify each theme entry exists in the pinned version. Padding/insets/radius are theme values here (`bubble.padding`, `text.padding`, `attachment.padding`, `quotedMessageTheme.shape`, …) — only fall back to a builder or a widget wrap where no token exists.
- **Widget replacement (Axis 2)** → register component-builder overrides through the factory: **globally** on `StreamChat(componentBuilders: StreamComponentBuilders(extensions: streamChatComponentBuilders(...)))`, or **scoped** to a subtree with `StreamComponentFactory` — and use the **per-widget** builders/configs (`messageBuilder`, `itemBuilder`, `builders`, `config`) directly on the parent widget where they're used. Pick the scope per Step 2's mechanism map. If a per-widget builder is reused in several places, hoist it to a top-level function or a `mixin`.

For custom bubbles/rows, define the `messageBuilder` in the channel page's `build`, not inline in the widget tree — hoisting keeps grouping/context-computation logic testable.

Wire the factory into the app's real entry point — do **not** ship a root that opens one channel directly (that is a verification scaffold only; see Step 5).

---

## Step 5: Verify against the reference — rigorously, region by region (mandatory)

A design match is **not done** until the app runs and the result is compared to the reference. Presence-and-color is not enough; verify **size, position, and proportion** too. The avatar that's missing, the header that collapsed, the icon that's the wrong size — these only show up here.

**Verification gate — this is where the match is actually won or lost, and it is the single most-skipped step. Treat it as ADVERSARIAL, not confirmatory. A confident PASS table built from eyeballing is the highest-frequency failure this skill has, and it is silent.**
- **Frame it as "find where they DIFFER," not "confirm it matches."** At thumbnail scale (the Read-tool image is only ~270 px tall) the eye fills in correct-looking detail — field height, stroke weight, corner radius, icon color, and exact metadata placement are all invisible there. "Looks like the reference" from a glance is not verification.
- **"Verify" means DRIVE the interaction on the device — a screenshot only proves the screen paints.** A painted screen can be behaviorally dead: a reply/edit/attachment-picker/send affordance that looks right but is wired to nothing screenshots perfectly. Drive every interactive affordance and record its observed effect (item 4's INTERACTION check); rendered-but-inert is a FAIL.
- **Every region gets a native-resolution crop of BOTH the reference AND your render, with real numbers (px → lp).** Crop MINE too, not just the reference — the recurring miss is measuring the reference and then eyeballing your own render. **A region with no crop is UNVERIFIED, not PASS.**
- **When the verification device ≠ the reference device, compare PROPORTIONS, not absolute lp.** A 411-lp-wide emulator vs a 393-lp reference yields a different absolute margin for the *same* correct layout — normalize by screen width (bubble width as % of screen, margin as % of width) before concluding something is mispositioned.
- **Measurement sanity (each of these has cost a wasted round):** screenshots are **RGBA** — `.convert("RGB")` before unpacking pixels; a "green bubble" detector also matches a **beige wallpaper** (both r≈g>b) so constrain it (`g>r`); validate any detector on a known region first, and when a number looks wrong suspect the **measurement** before the implementation. If a real code change produces a **byte-identical** screenshot, that's a RED FLAG (stale build / stray `flutter run` kept the old app installed) — not a passing "no change."
- **Numbers alone lie — stack the crops and look.** Glyph ink-boxes can "match" (±1 lp) while the field is too tall, strokes too heavy, or things off-center. Screenshot on the same device class (also `@3x` → both 3 px/lp, so no resizing), crop **both** the reference and your render at native resolution, and stack them to eyeball what the numbers miss (field height/compactness, stroke weight, vertical centering, overall balance):
  ```bash
  magick "$REF"  -crop ${W1}x210+0+${refY}  +repage ref.png    # reference region
  magick "$MINE" -crop ${W2}x210+0+${mineY} +repage mine.png   # your render (find Y via the field-band script)
  magick ref.png mine.png -background black -append compare.png # stack; view it
  ```
  Loop until the side-by-side reads as the same UI, not just until the numbers match.

**Pin the device — never invent one.** Do not let the model pick a device from memory: a guessed device+OS ("iPhone 16 Pro / iOS 18.x", or an emulator that is not actually running) makes the launch stall while the toolchain tries to create it — or silently fall back — which reads as a hung first build. Instead run `flutter devices` to see what is actually booted/connected, take that device id, and `flutter run -d <deviceId>`; reuse the same device for the whole match. Never pass a device name or OS version you have not confirmed appears in `flutter devices`. If `flutter devices` lists **no** device, boot one first — `flutter emulators` → `flutter emulators --launch <emulator_id>` (Android) or `open -a Simulator` (iOS) — then re-run `flutter devices` and continue only once the id appears (first boot takes a minute; poll `flutter devices`, don't guess).

**Drive the real UI with the platform's automation tool; fall back to a test harness only if none is available.** Both platforms can be scripted to press a login/connect button and navigate — **Android**: `adb shell input tap <x> <y>` (plus `input text`, key events; long-press = `input swipe x y x y 700`); **iOS**: `idb ui tap <x> <y>` (`facebook/idb`). Use these to get to the screen you need, then screenshot — target elements by accessibility label where you can, since raw x/y is brittle across screen sizes. **When you do use raw coordinates, convert to the device's PHYSICAL pixels first:** the tap tools take physical-pixel coords, but the screenshot you measured them on is usually viewed downscaled (the Read tool shrinks large images) — multiply measured coords by (device-pixel-width ÷ displayed-image-width) before tapping. A mis-scaled tap doesn't error, it lands on the wrong element and silently no-ops (text types nowhere, send does nothing) — check the post-tap screenshot actually changed screens before trusting the flow. If the tool isn't installed or can't reach the screen, fall back to a Flutter **integration-test harness** (`integration_test` + `WidgetTester.tap`, or `flutter drive`), which taps *inside* the engine — run it so you can watch its output and confirm the screenshot files land, never as a blind `tail`-piped job. Separately, the SDK renders nothing until a user is connected: when you only need a connected client (not a specific in-app path), the simplest route is to connect in code — `client.connectUser(User(id: …), token)` with the seeded CLI/dev-token creds at launch — and temporarily point the app's root/entry widget at the target screen (the throwaway scaffold in item 2), deleting it after.

**If the device, app, or `flutter run` session wedges mid-collection — timebox, diagnose, recover up a ladder. Never sit waiting on a stuck step, and never let a stuck environment turn into a silent PASS.** Steady-state steps (tap, screenshot, hot reload) finish in seconds; one that has produced no new output or file after ~2 minutes is stuck, not slow (only a cold first build legitimately takes minutes). Diagnose *what* is stuck first: take a fresh screenshot and send a harmless input (Android `adb shell input keyevent 82`, iOS an `idb ui tap` on empty space) — if the screenshot still changes, the app is alive and your **driver** is the problem (re-check the physical-pixel tap scaling above); if it's frozen, escalate cheapest-first, re-testing after each rung:
- **Hot restart** (`R`). An app stuck on a blank first frame is usually an awaited blocking call before connect (e.g. a permission dialog) — fix the cause rather than retrying forever.
- **Kill and relaunch that `flutter run`** on the **same device id**.
- **Reboot the device.** Android: `adb -s <id> emu kill`, relaunch the AVD (cold-boot with `-no-snapshot-load` if it hangs at boot again); if `adb devices` stops listing it, `adb kill-server && adb start-server`. iOS: `xcrun simctl shutdown <udid> && xcrun simctl boot <udid>`.
- **Only then switch hardware:** re-run `flutter devices`, pin another confirmed-booted id.

Recovery preserves evidence: screenshots on disk and comparison-table rows already backed by evidence stay valid — redo only the wedged step. A device **switch** changes resolution/scale, so re-shoot the affected reference/render pairs on the new device or fall back to the proportional comparison above; never pixel-diff crops taken on two different devices. If a step genuinely cannot be recovered, its regions are **UNVERIFIED and reported as such** (item 7) — a wedged emulator never upgrades a region to PASS.

1. **Seed data that triggers every customized region.** An empty or one-message channel proves nothing and hides exactly the elements that get dropped. Seed (or send): **both an incoming and an outgoing** message; a **run of 3+ consecutive messages from the same author** (so grouping + the avatar's last-in-group rule actually render); a **plain text-only** message (NOT just media — shared chrome like the timestamp/receipts/reply affordance must render on text too, and a reference that shows only image messages will hide this); a message **with reactions**; a **reply/quote**; a **long multi-line** text; enough history that the **date separator** appears. **Seed every attachment type your app renders — a photo album, a video, a file, a voice recording, a link preview (just put a URL in the message text — the server enriches it), and a poll.** A dropped/unhandled attachment type is invisible on a channel that never contains that type, so this is the check that catches it. Mark messages read if the design shows read receipts. **Also exercise the states the reference doesn't show** (empty composer, the typing→send swap, a text message when the reference has only media) — the design must hold across them, not just on the one seeded frame. Use the getstream CLI (see [`SKILL.md`](SKILL.md) Step 0.5) — server-side calls bypass permission checks, so seeding always succeeds.
2. **Open the real message screen — via a THROWAWAY scaffold you must DELETE.** Verifying only the channel list does not verify the message screen. The reliable way to render the message screen for a screenshot is to **temporarily** point the app's root (e.g. `MaterialApp(home:)`) at:
   ```dart
   home: Scaffold(
     appBar: <yourCustomHeader>,
     body: StreamChannel(
       channel: client.channel('messaging', id: '<seeded-id>'),
       child: Column(children: [
         Expanded(child: StreamMessageListView(messageBuilder: ..., builders: ..., config: ...)),
         <yourComposerRow>,
       ]),
     ),
   ),
   ```
   Screenshot on an iOS + Android simulator/device (or one per if the design is platform-specific), **then DELETE the scaffold entirely** so the shipped code's only path is the real entry point.
   - **This scaffold is for verification ONLY — never ship it, and "revert" means DELETE, not disable.** Do not leave a `verifyMessageScreen`-style boolean flag (even set to `false`), the dead `if/else` branch, or constants only the scaffold used (e.g. a `demoChannelId`) in the delivered code — a toggled-off debug flag is still scaffolding the user will (rightly) ask you to remove. Remove the flag, the branch, the direct-open `Scaffold`, the now-unused imports, and any helper that became dead — leaving `home: ChannelListPage()` (or the app's existing home) as the only path. Prefer a scaffold shaped so it's trivially deletable in one edit (a single replaced line), not threaded through the app. Do not change the app's entry point or navigation unless the user explicitly asks (see [`RULES.md`](RULES.md) "Project ownership").
   - **After the scaffold screenshot, also verify the real path:** restore the channel-list root and confirm the header, back button, and title render correctly on the pushed channel screen (the channel-list path is the one that exercises the header title-resolution + back-button + push transition end to end). A direct-open scaffold uses the same widgets for the *body*, but it does **not** prove the header/navigation works in production.
3. **Build a comparison table.** For each region from Step 1, record: target attribute (size/position/color/presence) → what rendered → **PASS / FAIL** → **evidence** (the crop pair for a render check; the driven action + observed result for an interaction). A PASS with no evidence is UNVERIFIED, not PASS. Walk the *whole* Step-1 checklist; do not stop at the regions that happen to look right.
4. **Re-check the elements that are silently lost** (give these explicit attention every time): the **author avatar on incoming messages** and message **grouping**; the **navigation header's height, alignment, and title size** (and title correctness on a DIFFERENT channel — open a DM); the **composer in BOTH states** — empty/at-rest and with text typed (the send vs. mic/camera swap).
   - **Small details users WILL catch — inspect each at native `@3x`, don't assume an SDK default matches:** reaction **counts** (whether the default hides "1" or shows it); reaction **pill padding/fill/border**; whether a control sits **inside vs. outside** a container (the composer `+`); the **reaction-picker contents**; the **gap** between the last message and a floating composer; the bubble **corner radius on adjacent messages** in a group (some designs round only the outer corners of a run).
   - **PADDINGS / spacings / margins are first-class regions — measure them, don't skip them.** They are the *least* visible artifact at thumbnail scale (a 14-lp header pad or 20-lp composer gap is sub-pixel in the Read-tool image), so they only get caught by cropping and measuring. For header / bubble / composer, measure **start pad, end pad, and gap-between-children** on BOTH reference and render, numerically — treat each as its own checklist row (e.g. header left pad, outgoing-bubble right margin, image→timestamp gap, composer `+`↔pill / pill↔camera / camera↔mic gaps, right pad). **Do this on the FIRST verification pass, together with heights/colors.** "Field height matches + colors match" reads as done while the whole row is silently shifted right, and that horizontal shift is a top-frequency real miss. It usually comes from the **SDK composer's own inset** — the composer applies its own horizontal padding around the leading/input/trailing row (read the exact value from the pinned source rather than assuming a token or round number), so your `+` and field start *inside* it; measure the actual on-screen position, don't assume your own leading padding is the whole story. Same for the header: the avatar landing too far left is almost always `leadingWidth` being too small.
   - **INTERACTION — tap every affordance, don't just look at it.** A reply/forward/react/tap-to-open that *looks* right but has no `onTap` (a decorative look-alike) is a **FAIL**. Wire the real callback and actually tap it during verification to confirm it does something.
   - **STATE COVERAGE — verify the adjacent states, not only the seeded frame.** Confirm a **text** message renders the same shared chrome as a media message; check a long multi-line message, the composer **typing** state (send button swap), and empty. Optimizing for the exact frame the reference shows (e.g. only outgoing images) silently drops chrome on the states it doesn't show.
5. **Iterate until every region passes — with HOT RELOAD, not kill-and-rebuild.** Keep **one** `flutter run` alive for the whole match and hot-reload after each batch of edits; do NOT `pkill flutter` → `flutter run` per iteration (a full rebuild+reinstall is ~1–2 min and was the dominant wall-clock cost in past runs). Use `r` (hot reload, <1 s) for Dart UI edits — theme tokens, builders, paddings; `R` (hot restart) only for `main()` / DI / const-theme-construction changes; a fresh `flutter run` only for native/`pubspec` changes. So the loop is **edit → `r` → screenshot → compare**. Don't declare done on the first screenshot. **Batch** the fixes for a round (say 5 regions) — don't hot-reload after each single-property edit; the settle time adds up. (Headless/background caveat: if you can't send `r` to a backgrounded `flutter run`'s stdin, drive it via the VM Service / `flutter` daemon rather than killing the process.)
6. **Toggle light/dark and verify both.** Change `themeMode:` on `MaterialApp` or the simulator's appearance. Brand/content colors (bubble fills, wallpaper, read-receipt ticks) stay pinned; structural surfaces (composer bar, list background) flip via `colorScheme.surface`. If they don't flip, you pinned a surface — go fix.
7. If you genuinely cannot run the build, say so plainly and list which regions are implemented-but-unverified — never imply a match you did not see.
8. **Do not deliver with a region left at its default and call it a "known gap."** Every region in the Step-1 checklist — the composer especially — must be implemented to match, not just the cheap theming ones. A region that "looks roughly like a messenger composer" but is the SDK default (wrong button set/placement, no in-field glyph) is a FAIL, not a footnote. Report something as unmatched only when it is genuinely impossible (and say what + why), never merely because it is risky or more effort.

