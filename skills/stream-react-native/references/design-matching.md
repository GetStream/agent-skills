# Stream React Native — matching a reference design (Chat · Video · Feeds) (screenshot / Figma / "make it look like X")

When the user gives a **target appearance** - an attached screenshot, a Figma frame, or "make the
app look like WhatsApp / iMessage / Telegram / Slack / \<app\>" - the job is **not** "set a few
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

For every region note the followings: color, background color, border, border radius, padding / gap, typography (font, font weight, font and line size) - save findings to a file called `design-analisys.md`. Unless asked otherwise, remove the `design-analisys.md` after the verification step.

#### Chat

**Channel list screen** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| List header | app-owned nav: title, actions, height | **App-owned** | React Navigation `Stack.Screen options` / Expo Router header - not a theme key |
| How many channel lists? | Group vs 1:1 messages? | Layout | Create multiple `ChannelList` with proper filter and sort options |
| Preview row | layout, avatar, unread badge, timestamp, empty/loading state, background | Theming (+ Layout) | `theme.channelPreview.*`; `ChannelList` `ChannelPreview*` props/slots if structural |

**Message screen - chrome**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Nav header | **app-owned** RN / Expo: title, subtitle, back affordance, trailing avatar/buttons, height | **App-owned** | Always put header inside `Channel`. React Navigation `Stack.Screen options` / Expo Router header - not a theme key; drive the title from channel state, never a hardcoded literal. **Liquid Glass:** if the design shows frosted/translucent floating pills (iOS 26, e.g. Telegram's back/title/avatar), render them with `expo-glass-effect` `GlassView` (guard `isLiquidGlassAvailable()`, translucent fallback) — a flat semi-transparent color is not a match. |
| Chat background / wallpaper | flat color vs. texture | Theming (+ Layout) | `Channel` / message-list background theme key; a custom background view if it's a texture |
| Date separators + new-messages divider | present? shape | Theming (+ Layout) | date-separator theme keys; slot override if the shape differs |
| Scroll-to-bottom / jump-to-latest | present? style | Theming (+ Layout) | scroll-to-bottom affordance slot - confirm exact name in docs |

**Message screen - the message itself**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Layout style | bubbles (messenger) vs. flat left-aligned rows (workplace/Slack) - **decides everything below** | Functional (+ Theming) | `forceAlignMessages` prop on `Channel` |
| Content layout | Message content order; typical variations: text first or last (default layout is text last) | Functional | `messageContentOrder` prop on `Channel` |
| Bubble | fill color, border, corner radius, max width | Theming (+ Layout) | `chatBg*` and `chatBorder*` semantic variables, `messageItemView` theme keys |
| Grouping | consecutive same-author messages, who shows an avatar | Layout | `useMessageContext()` group flags |
| Sender name placement | shown at all (1:1 often hides it, groups show it)? **inside** the bubble as a first line vs. **above/outside** as a separate row? incoming only or own too? first-of-group or every message? | Layout | inside → `MessageContentTopView` / `MessageContentBottomView` - **ensure proper padding is applied to custom sections too**; ensure rounded border doesn't hide content; above → `MessageHeader` / `MessageFooter` (default `MessageFooter` - remove it if you add a custom one); `useMessageContext()` group flags |
| Timestamp + delivery/read receipts placement | **below/outside** the bubble (Stream default) vs. **inside it** (trailing corner, WhatsApp/iMessage) | Theming (+ Layout if repositioned) | default via `MessageFooter`; inside → `MessageContentBottomView` / `MessageContentTrailingView` (always set `alignSelf`; **reproduce the content body's `paddingHorizontal`/`paddingBottom` — these slots have no padding of their own, so the timestamp will otherwise touch/clip at the bubble's right & bottom edge; see the Spacing row**; remove `MessageFooter` if you add a custom one); outside → `MessageFooter` and `MessageHeader` |
| Pinned / sent-to-channel / saved / reminder status | present? | Layout | default `MessageHeader` |
| Read/delivery indicator glyphs | single/double tick, color | Theming (+ Layout if repositioned) | Theming for recoloring, `MessageStatus` if ticks/indicator need to be different |
| Avatar shape | circle? square? online indicator? | Theming | `avatar` |
| Avatars beside messages | shown? on own messages? | Layout | `MessageAuthor` and `useMessageContext()` group flags |
| Quoted / inline replies | present? | Theming | Restyle, don't rebuild |

**Message screen - reactions**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Reactions placement | inside or outside bubble? top or bottom of bubble? reactions overlap? reaction list has add button? | Theming (+ Layout) | `Channel` props; custom reaction list components - must have if list has add button. **`ReactionListTop`/`ReactionListBottom` render OUTSIDE the bubble (above/below it) — "bottom" ≠ inside.** For reactions **inside** the bubble background (Telegram-style, sharing the bottom row with the timestamp), render them in `MessageContentBottomView` (an in-bubble slot) and set both `ReactionListTop` and `ReactionListBottom` overrides to `() => null` so the external list is suppressed. |
| Custom add reaction button | is there an add button inside the message reaction list? | Structural | default implementation is `EmojiViewerButton` reuse or create a custom component and display at correct spot; don't mix up with `showReactionsOverlay` - it DOESN'T add reactions |
| **Own (selected) reaction styling** | is YOUR OWN reaction tinted differently | Theming or Layout | Theming or `ReactionListItem` override; use `useMessageContext()` to `showReactionsOverlay()` |

**Message screen - attachments**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Image/photo grid | the grouped collage is largely the RN default - **restyle, don't rebuild** | Theming (+ Layout) | attachment theme keys |
| Video / file / giphy / link / voice-recording / poll / custom | present? style | Theming (+ Layout) | attachment theme keys; `Attachment` override only if structural |

**Composer** (almost always differs - inspect closely, in BOTH states)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Floating vs. docked | inset / rounded / above content vs. flush at the bottom edge | Layout | `messageInputFloating` flag |
| Layout style | Colors, backgrounds, borders | Theming | `messageComposer.wrapper` outer wrapper; `messageComposer.container` inner part. **Liquid Glass:** if the design's attach/send/mic buttons (and input pill) are frosted/translucent (iOS 26), wrap the button slots in `expo-glass-effect` `GlassView` (guard `isLiquidGlassAvailable()`) and make the input pill translucent — a solid fill is not a match. |
| Send/mic button | Colors, location | Theming + Layout | Use theming to recolor; Use `OutputButtons` for send/mic button, don't create custom. Inside input? `MessageInputTrailingView` (default slot). Outside input? `MessageComposerTrailingView` |
| Attach buttons | How many? Colors, location | Theming + Layout | Use theming to recolor; Default is + in `MessageComposerLeadingView`. Reuse `Attachbutton` for repositioning only (`MessageInputTrailingView`/`MessageComposerTrailingView`). For custom attach button, use `useMessageInputContext` (implement open and close picker).  |
| Typing | send button appears / swaps in | Layout | `MessageComposer` slot (send/mic swap) |
| Audio recording | check if there is a standalone button (not shared send/mic button) | Layout | Reuse `AudioRecordingButton`, don't create custom; add it to proper slot |
| Location sharing | present? | Functional | Location sharing guide from docs |

**Composer - attachment picker**

Opened when the attach button is clicked

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Attachment bar | Layout (one row or multiple rows?) and position (above or under selected attachment type content) of the bar? Custom attachment bar icons (gallery, polls, files, etc.)?  Or fully custom layout (for example list)?  | Theming for recolor; Override for custom icons; `AttachmentPickerSelectionBar` for the bar; `AttachmentPicker` for a fully custom picker; verify from SDK source code default layout and behavior and decide the override scope; **Don't just re-render the default picker buttons and call it customized** — reproduce the reference's item layout (icon + label), selected-tab tint, and bar background. Build labeled items as `Pressable`s that call the SAME context actions the SDK buttons use (`attachmentPickerStore.setSelectedPicker(...)`, `useMessageInputContext().pickFile()` / `openPollCreationDialog({ sendMessage })`), and read the active tab from `useAttachmentPickerState().selectedPicker`. **Bar position:** the default host renders `AttachmentPickerSelectionBar` at the TOP of the sheet (above the grid); a bottom bar requires replacing the whole `AttachmentPicker` host via `OverlayProvider`'s `AttachmentPickerComponent` (internal bottom-sheet wiring) — call that out if you keep it on top. Only show tabs the app backs (e.g. Gallery/File/Poll); drop unbacked ones (Location/Checklist) rather than shipping dead tabs. |

**Mixed camera+library picker:** if the reference shows a single combined picker (live camera preview inline with the photo grid, as in iOS's own sheet), RN Chat has no combined picker — split it into **separate library and camera tabs** (`MediaPickerButton` → `images` tab, `CameraPickerButton` → `camera-photo`/`camera-video`), don't try to fake one merged surface. Check if picker is open or not with `attachmentPickerStore.state.getLatestValue().selectedPicker`

> **Gap between the composer and the attachment picker → you forgot `topInset` on `Channel`.** When the picker opens, the docked composer shifts up by the picker's full reserved height (`attachmentPickerBottomSheetHeight`, default `333`), but the bottom sheet's snap position is computed from `Channel`'s **`topInset`**. If `topInset` is missing/too small, the sheet is clamped short and opens *low* while the composer has already shifted its full amount → a large empty band between them (looks like the picker "detached" from the input).
>
> **Rule:** set `topInset` on `Channel` to the **exact top offset the message list starts at**, and pass the **same value** as `keyboardVerticalOffset`. Compute it from whatever occupies the top:
> - **Native nav header:** `useHeaderHeight()` (RN CLI / Expo Router ≤ 55) — this is the case the CHAT-REACT-NATIVE docs already cover.
> - **Custom in-screen header** (`headerShown: false` + your own header `View`, common for a WhatsApp/Telegram-style floating header): there is *no* `useHeaderHeight()` to remind you — compute it yourself as `insets.top + <your header content height>` and pass it as **both** `topInset` and `keyboardVerticalOffset`. This is the easy-to-miss case: the composer looks fine until someone opens the picker.
>
> **Do NOT try to close the gap with `bottomInset`.** `bottomInset` shrinks the composer's upward shift (`attachmentPickerBottomSheetHeight - bottomInset`); dialing it up moves the input *down, under* the sheet and hides it. `bottomInset` is only for a bottom tab bar that owns the safe area — not a lever for picker spacing.
>
> **Verify with the picker OPEN, and wait for the image grid to load.** A picker screenshot taken before the device photo library / remote thumbnails finish loading shows a short, half-empty grid that *also* looks like a gap — re-screenshot after the grid settles before diagnosing (and open to the **Files** tab per SIMULATOR-VERIFICATION to avoid the un-dismissable photo-permission prompt).

**Thread surfaces** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Thread reply screen | Does it exist? Not all apps have threads; parent message + replies | Layout / **App-owned nav** | separate nav screen: `Channel` with `threadList` + `Thread` (**Thread Screen** blueprint in [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md)) - reuses your row + composer overrides; see the RN-specific thread notes in Step 2 |
| Thread inbox / list | row layout | Theming (+ Layout) | `ThreadList` inside `Chat` (**Thread List Screen** blueprint); thread-list theme keys + `ThreadList` item props if the row differs |
| Message replies indicators (message component) | Layout and styling | Theming + Layout | `MessageReplies`; default is connector + avatars |

#### Video

Video ships a **prebuilt component UI** (unlike Feeds) driven by a **global theme** +
**component-injection slots** (unlike Chat's per-`Channel` theme + `WithComponents`). Route each
difference to the cheapest mechanism, preference order **Theming → Layout → Component slot →
Functional**:

- **Theming** — a `DeepPartial<Theme>` passed to `<StreamVideo style={…}>` (global; there is no
  per-`CallContent` theme prop and no `OverlayProvider`/`Channel` split). Deep-merged over
  `defaultTheme`; carries `colors`, `typefaces`, `variants` (size scales), and one style slot per
  component (`callControls`, `participantView`, `participantLabel`, `liveIndicator`, …). Colors,
  fonts, and spacing live here.
- **Layout** — `CallContent`'s `layout` prop (`'grid' | 'spotlight'`) + `landscape`, and
  `CallParticipantsList` `numberOfColumns` / `horizontal`.
- **Component slot** — pass a custom `React.ComponentType` (or `null` to hide) to a slot prop on
  `CallContent` / `ParticipantView` / `HostLivestream` / `ViewerLivestream`. This is Video's
  structural axis — Chat's component override, but as direct props, not a `WithComponents` wrapper.
- **Functional** — call methods + `useCallStateHooks()` state hooks (`call.camera` /
  `call.microphone` / `call.screenShare`, `useCameraState`, `useHasOngoingScreenShare`) for behavior
  no slot reaches.

Confirm exact prop / slot / theme-key names against the installed `@stream-io/video-react-native-sdk`
and the RN Video docs — names below are verified against current source but drift across versions.

**Video call surfaces** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Call layout | equal grid of tiles vs. one large tile + filmstrip (speaker view); paginated? — decides the tile arrangement below | Layout | `CallContent` `layout` prop: `'grid'` (`CallParticipantsGrid`, equal tiles) vs. `'spotlight'` (`CallParticipantsSpotlight` — one large tile + a `CallParticipantsList` filmstrip); default `grid`. **An active screen share forces `spotlight` regardless** of the prop. No page-count prop — the filmstrip/grid is a scrollable `FlatList` with visibility-based track subscription; tune `numberOfColumns` / `horizontal`. For runtime grid⇄spotlight switching build a switcher (runtime-layout-switching cookbook) or render `CallParticipantsGrid` / `CallParticipantsSpotlight` directly. |
| Participant tile | name label, mute (mic-slash) indicator, video-off/avatar fallback, dominant-speaker ring/highlight, network-quality (signal) bars | Theming (+ Component slot) | `ParticipantView` slots (all also injectable on `CallContent`): name + mic-off/video-off/pin + dominant-speaker `SpeechIndicator` → `ParticipantLabel`; video-off avatar → `ParticipantVideoFallback` (`participant.image`); signal bars → `ParticipantNetworkQualityIndicator` (from `participant.connectionQuality`); video → `VideoRenderer`. Recolor via `participantLabel.*` / `participantNetworkQualityIndicator.container` theme keys. **Dominant-speaker ring is NOT a slot** — a 2px border recolored to `colors.buttonPrimary` when speaking; restyle via theme `participantView.highlightedContainer` (+ `colors.buttonPrimary`). Pass `null` to a slot to hide it. |
| Local participant / self-view | small self-view thumbnail present? position, size, draggable? | Component slot (+ Theming) | `FloatingParticipantView` (`CallContent`'s `FloatingParticipantView` prop; `null` to remove). Draggable, snaps to 4 corners; `alignment` (`'top-left'|'top-right'|'bottom-left'|'bottom-right'`, default `'top-right'`). **Only in grid layout, not PiP, and only with 1–2 remote participants** — a 3+ grid folds the local tile in. Size is auto from the track aspect ratio (not a prop); tap swaps local⇄remote in 1:1. Theme `floatingParticipantsView.*`. |
| Screenshare | a shared screen/window inside a tile — present? layout when active (spotlight vs. tile) | Functional (+ Layout) | Renders automatically: an ongoing share flips `CallContent` to `spotlight` (`useHasOngoingScreenShare()`), puts the `screenShareTrack` in the spotlight tile (`objectFit='contain'`), and shows the local sharer a `ScreenShareOverlay` ("Stop Screen Sharing"; injectable / `null`). Start/stop via `ScreenShareToggleButton` added to a custom `CallControls` (`screenShareOptions`: `type` `'broadcast'|'inApp'`, `includeAudio`). Screen-share label branch lives in `ParticipantLabel`. iOS needs a Broadcast Extension (screensharing guide). |
| Call controls | circular control bar (usually bottom): camera toggle, mic toggle, leave/hang-up, plus extras (flip camera, speaker, reactions, screenshare); position, glyphs | Component slot (+ Theming) | Default `CallControls` is a **fixed** row: `ToggleVideoPublishingButton`, `ToggleAudioPublishingButton`, `ToggleCameraFaceButton` (flip), `HangUpCallButton`. **No per-button order/add/remove prop** — to add `ReactionsButton`/`ScreenShareToggleButton`, reorder, or drop one, replace the whole component via `CallContent`'s `CallControls` prop (reuse the exported buttons; build custom ones from `call.microphone.toggle()` / `call.camera.toggle()` / `call.camera.flip()` / `call.leave()` — replacing-call-controls cookbook). Recolor via theme `callControls.container` / per-button slots (`hangupCallButton`, `toggleAudioPublishingButton`, …) or `colors.button*`; shared `CallControlsButton` takes `color` / `size`. |
| Device selectors | camera / mic picker affordances shown? | Functional (custom UI) | **RN ships no camera/mic device-picker component** (unlike React web's `DeviceSelector*`). Only camera **flip** (`ToggleCameraFaceButton` → `call.camera.flip()`) and on/off toggles exist. Enumerate/select devices programmatically via `useCameraState` / `useMicrophoneState` (`call.camera` / `call.microphone`); audio-output routing is native/programmatic (`callManager.ios.showDeviceSelector()` opens the iOS route picker; Android via `callManager.android.*`) — `useSpeakerState()` is **not** supported on RN. If the design shows a device dropdown, **build it custom** (or flag it). |
| Livestream surface | "LIVE" badge + viewer count; host vs. viewer controls; watching state | Component slot (+ Theming) | `HostLivestream` / `ViewerLivestream` (or `LivestreamPlayer`, which wraps `ViewerLivestream` for HLS viewers) — separate from `CallContent`. LIVE badge → `LiveIndicator` (shown while live / HLS broadcasting); viewer count → `FollowerCount` (`useParticipantCount()`, `humanizeParticipantCount`); elapsed time → `DurationBadge`; all injectable slot props on the top-view. **Host vs. viewer controls differ**: `HostLivestreamControls` (start/end + media toggles) vs. `ViewerLivestreamControls` (volume / maximize / play-pause / leave). Watching state via `joinBehavior` (`'asap' | 'live'`) → `ViewerLobby`. Theme keys `liveIndicator.*`, `followerCount.*`, `durationBadge.*`, `hostLivestream*` / `viewerLivestream*`. |

#### Feeds

Ported from the web skill's Feeds taxonomy + activity-card / comment-row / feed-composer contracts.
Feeds has **no prebuilt RN UI** — every region is a **fully custom component** you build yourself on
**state hooks** (from `@stream-io/feeds-react-native-sdk`) plus `client` / `feed` methods. Chat's
Theming / Layout / Functional axis taxonomy therefore doesn't apply; the **Axis** column below uses a
Feeds-specific vocabulary and the **Route to** column names the exact hook + method:

- **Custom · read** — render-only from a state hook
- **Custom · action** — read + a `client` / `feed` mutation
- **Custom · structure** — feed instantiation / navigation / server-side config

There is no theme object and no component-override slot to reach for here — matching a reference means
reproducing the design's layout, spacing, and colors in your own components. **Confirm every exact
hook / method / field name against the installed package** (`@stream-io/feeds-react-native-sdk`, which
re-exports `@stream-io/feeds-client`) **and the RN Feeds docs** before coding — names below are
verified against the current source but can drift across versions.

**Feed surfaces** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Activity card | avatar + author name + relative timestamp + text; attachments (image / link preview); long-text handling | Custom · read | `useFeedActivities(feed)` → `{ activities, is_loading, has_next_page, loadNextPage }` (feed optional inside `StreamFeed`). Render each `ActivityResponse` yourself: `user` (author), `created_at`, `text`, `attachments` (`image_url`/`asset_url` by `type`). No prebuilt card — you own the layout, avatar shape, and long-text truncation. |
| Activity reactions | heart/like glyph + count; own-reaction (selected) state toggle | Custom · action | Own/counts from `activity.own_reactions` / `activity.reaction_groups` (+ `latest_reactions`); toggle with `client.addActivityReaction({ activity_id, type, enforce_unique })` / `client.deleteActivityReaction({ activity_id, type })`. Gate the button on `useOwnCapabilities(feed)` (`ADD_ACTIVITY_REACTION` / `DELETE_OWN_ACTIVITY_REACTION`). |
| Comments | speech-bubble + count, open-comments affordance; comment row (avatar, author, timestamp, text); nested replies; post-a-comment input | Custom · action | Count from `activity.comment_count`; list with `useActivityComments({ feed, activity })` (or `useComments({ parent: activity })`) → `{ comments, has_next_page, is_loading_next_page, loadNextPage }`; add via `client.addComment({ object_id: activity.id, object_type: 'activity', comment, mentioned_user_ids })`. **Nested replies:** pass a comment as the parent (`useComments({ parent: comment })` / `useActivityComments({ parentComment })`), read `comment.reply_count`. Comment reactions: `client.addCommentReaction` / `deleteCommentReaction` (no dedicated hook — reuse the same reaction UI). |
| Repost | two circular arrows + count — present? | Custom · action | **No dedicated repost method.** Share by `feed.addActivity({ type, text, parent_id: original.id })`, which increments `original.share_count`; read the shared parent via `activity.parent`, and the count via `activity.share_count`. |
| Bookmark | bookmark/save flag toggle — present? | Custom · action | Own/count from `activity.own_bookmarks` / `activity.bookmark_count`; toggle with `client.addBookmark({ activity_id, folder_id? })` / `client.deleteBookmark({ activity_id })`. Folders (if the design groups saves): `client.queryBookmarkFolders` / `updateBookmarkFolder`. No dedicated hook — read off the activity. |
| Follow button | follow / unfollow affordance (profiles, suggestions); follower / following counts | Custom · action | Follow state via `useOwnFollows(feed)` → `own_follows` (match `source_feed.group_id === 'timeline'`, read `.status`: `accepted` / `pending` / `rejected` → Following / Requested / Follow); toggle `timelineFeed.follow(targetFeed, { create_notification_activity, push_preference })` / `timelineFeed.unfollow(targetFeed)`. Counts/lists: `useFeedMetadata(feed)` (`follower_count` / `following_count`) or `useFollowers(feed)` / `useFollowing(feed)`. Suggestions: `client.getFollowSuggestions`. |
| Feed composer | "What's on your mind" post box: text input + submit, attachment upload / preview, mentions, poll creation; position; posts appear without reload | Custom · action | Create with `feed.addActivity({ type, text, attachments, mentioned_user_ids, poll_id })` (or `client.addActivity({ feeds: [...] })` to post to multiple feeds at once). Uploads: `client.uploadImage({ file })` / `client.uploadFile({ file })` (helpers `isImageFile` / `isVideoFile`, type `StreamFile`) → map results into `attachments` (`image_url` vs `asset_url`). Mentions: `mentioned_user_ids` (find candidates via `client.queryUsers`; the app renders the @-text itself). Poll: `client.createPoll(...)` then attach `poll_id`. Posts appear live when the feed is watched (`getOrCreate({ watch: true })`). |
| Notification feed | aggregated "X and N others…" rows + bell; unread / unseen treatment | Custom · action | Feed group `notification` (`client.feed('notification', userId)`); rows via `useAggregatedActivities(feed)` → `aggregated_activities` (each `AggregatedActivityResponse`: `is_read` / `is_seen`, `activity_count`, `user_count`, `.activities`, `.group`). Bell/badge counts: `useNotificationStatus(feed)` → `{ unread, unseen }`; per-row read/seen from `aggregatedActivity.is_read` / `.is_seen` directly (`useIsAggregatedActivityRead` / `…Seen` are deprecated). Mark: `feed.markActivity({ mark_read: [group] })` / `{ mark_all_seen: true }`. |
| Multiple / For You feeds | tab switcher over the feed (e.g. Timeline vs. For You) — present? | Custom · structure | Each feed is a separate `client.feed(group, id)` + `feed.getOrCreate({ watch: true })`, wrapped in its own `<StreamFeed feed={…}>`; the tab switcher renders one feed at a time (e.g. `timeline` vs `user` vs a For-You group). For-You ranking is server-side (feed-group `activity_selectors` + `ranking`); RN just reads it like any feed (optionally `getOrCreate({ interest_weights })`), and `activity.selector_source` (`following`/`popular`/`interest`) tells you why an item ranked. Instantiate feeds with a query-hook pattern (see the sample's `useCreateAndQueryFeed`). |
| Poll activity | poll inside a post (options, vote bars, counts) — present? | Custom · action | Poll data on `activity.poll` (`PollResponseData`: `options`, `vote_count`, `vote_counts_by_option`, `own_votes`); for live vote updates use `client.pollFromState(pollId)` + `useStateStore(poll.state, selector)` (**no `usePoll` hook**). Vote: `client.castPollVote({ activity_id, poll_id, vote: { option_id } })`; remove: `client.deletePollVote(...)`; manage: `client.closePoll` / `createPollOption`. Create in the composer via `client.createPoll(...)` → `poll_id`. |
| Loading / empty / pagination | empty-feed state, loading skeleton, load-more / infinite scroll | Custom · read | Loading from the hook's `is_loading` / `is_loading_next_page`; infinite scroll = wire `loadNextPage()` to `FlatList` `onEndReached`, gated on `has_next_page` (start narrow with `getOrCreate({ limit })`). Empty state: check `activities.length === 0 && !is_loading` (no dedicated empty-state API). Connection-lost banner: `useWsConnectionState()`; `useClientConnectedUser()` returns `null` until connected — render a placeholder until then. |

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

**Composer placement decision.** A screenshot can likewise be inconclusive about whether the composer
is a **floating** input - a pill/bar inset from the screen edges with visible margin, corner radius,
and often a shadow, sitting *above* the content (common in iMessage/Telegram-style designs) - or a
**fixed/docked** bar flush with the screen's bottom edge and safe area. This is a structural
difference (container margin, corner radius, background, and possibly a layout override), not a
theming tweak, and getting it wrong changes the composer's relationship to the keyboard and the
message list both. If the reference doesn't make this clear, ask:

> This design doesn't clearly show whether the message input should float above the content (inset, rounded corners) or dock flush at the bottom edge. Which do you want?

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
2. **Open the real message screen on its actual navigation path** - channel list -> tap -> message
   screen - not a one-channel shortcut that never exercises the header/navigation. If you add any
   throwaway scaffold to reach a screen for a screenshot, **DELETE it before delivery** (remove the
   branch/flag/import - don't merely disable it) and re-verify on the real path. On the iOS simulator
   `simctl` can't tap, so reach non-initial screens with temporary in-code navigation and drive
   composer/picker states via SDK hooks - see the fast loop, stale-bundle trap, and cleanup steps in
   [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md).
3. **Build a comparison table.** For each region from `design-analisys.md` target attribute (size / position /
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
   vs. typing - the send/mic swap); **metadata placement**; reaction display; attachment rendering.
5. **Iterate until every region passes.** Fix, re-run, re-compare. Don't declare done on the first
   render.
6. If you genuinely cannot run the app, say so plainly and list which regions are
   implemented-but-unverified - never imply a match you did not see.
7. **Do not deliver with a region left at its default and call it a "known gap."** Every region in
   the Step-1 checklist - the composer especially - must be implemented to match. Report something as
   unmatched only when it is genuinely impossible (and say what + why), never merely because it's
   risky or more effort.
