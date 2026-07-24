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
| Nav header | **app-owned** RN / Expo: title, subtitle, back affordance, trailing avatar/buttons, height | **App-owned** | Always put header inside `Channel`. React Navigation `Stack.Screen options` / Expo Router header - not a theme key; drive the title from channel state, never a hardcoded literal. **Liquid Glass:** if the design shows frosted/translucent floating pills (iOS 26, e.g. frosted back/title/avatar pills), render them with `expo-glass-effect` `GlassView` (guard `isLiquidGlassAvailable()`, translucent fallback) — a flat semi-transparent color is not a match. |
| Chat background / wallpaper | flat color vs. texture | Theming (+ Layout) | `Channel` / message-list background theme key; a custom background view if it's a texture |
| Date separators + new-messages divider | present? shape | Theming (+ Layout) | date-separator theme keys; slot override if the shape differs |
| Scroll-to-bottom / jump-to-latest | present? style | Theming (+ Layout) | scroll-to-bottom affordance slot - confirm exact name in docs |

**Message screen - the message itself**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Layout style | bubbles (messaging-style) vs. flat left-aligned rows (workplace-style) - **decides everything below** | Functional (+ Theming) | `forceAlignMessages` prop on `Channel` |
| Content layout | Message content order; typical variations: text first or last (default layout is text last) | Functional | `messageContentOrder` prop on `Channel` |
| Bubble | fill color, border, corner radius, max width, **tail** | Theming (+ Layout) | Fills/text are **semantic tokens** — `theme.semantics.chatBgOutgoing`/`chatBgIncoming`/`chatTextOutgoing`/`chatTextIncoming` (set literal hex) — plus `messageItemView` theme keys. **The last-of-group bubble tail is usually free:** the tail-corner-radius token (`messageBubbleRadiusTail`, whose default sharpens the near corner) already produces the "tail" look — confirm it in the installed theme before building a custom tail. |
| Grouping | consecutive same-author messages, who shows an avatar | Layout | `useMessageContext()` group flags |
| Sender name placement | shown at all (1:1 often hides it, groups show it)? **inside** the bubble as a first line vs. **above/outside** as a separate row? incoming only or own too? first-of-group or every message? | Layout | inside → `MessageContentTopView` / `MessageContentBottomView` - **ensure proper padding is applied to custom sections too**; ensure rounded border doesn't hide content; above → `MessageHeader` / `MessageFooter` (default `MessageFooter` - remove it if you add a custom one); `useMessageContext()` group flags. **Per-sender name colour:** if the reference gives each sender a distinct name colour, map it **explicitly** to the seeded users (an id→colour map) — do **not** hash `userId`→palette, which assigns the wrong colour per person. Don't defer the explicit map and ship a hash "for now." |
| Timestamp + delivery/read receipts placement | **below/outside** the bubble (Stream default) vs. **inside it** (trailing corner) | **Structural (Layout)** when moved inside; Theming only if just recolouring in place | Moving metadata **inside** the bubble is a structural relayout, not a theme key — see the *metadata-inside-the-bubble deep-dive* below. Default via `MessageFooter`; inside → `MessageContentBottomView` / `MessageContentTrailingView` (always set `alignSelf`; **reproduce the content body's `paddingHorizontal`/`paddingBottom` — these slots have no padding of their own, so the timestamp will otherwise touch/clip at the bubble's right & bottom edge; see the Spacing row**; remove `MessageFooter` if you add a custom one); outside → `MessageFooter` and `MessageHeader` |
| Pinned / sent-to-channel / saved / reminder status | present? | Layout | default `MessageHeader` |
| Read/delivery indicator glyphs | single/double tick, color | Theming (+ Layout if repositioned) | Theming for recoloring, `MessageStatus` if ticks/indicator need to be different |
| Avatar shape | circle? square? online indicator? | Theming | `avatar` |
| Avatars beside messages | shown? on own messages? | Layout | `MessageAuthor` and `useMessageContext()` group flags |
| Quoted / inline replies | present? author-name colour? | Theming | Restyle, don't rebuild. The quoted block is the SDK `Reply` component; its **author-name colour defaults to the SDK gray**, so if the reference tints the quoted author (e.g. per-sender colour), push that colour into the reply header via theming — restyling the surrounding block doesn't reach it. |

**Message screen - reactions**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Reactions placement | inside or outside bubble? top or bottom of bubble? reactions overlap? reaction list has add button? | Theming (+ Layout) | `Channel` props; custom reaction list components - must have if list has add button. **`ReactionListTop`/`ReactionListBottom` render OUTSIDE the bubble (above/below it) — "bottom" ≠ inside.** For reactions **inside** the bubble background (sharing the bottom row with the timestamp), render them in `MessageContentBottomView` (an in-bubble slot) and set both `ReactionListTop` and `ReactionListBottom` overrides to `() => null` so the external list is suppressed. |
| Custom add reaction button | is there an add button inside the message reaction list? | Structural | default implementation is `EmojiViewerButton` reuse or create a custom component and display at correct spot; don't mix up with `showReactionsOverlay` - it DOESN'T add reactions |
| **Own (selected) reaction styling** | is YOUR OWN reaction tinted differently | Theming or Layout | Theming or a `ReactionListItem` override; own state is `reaction.own` from `useMessageContext()`. |
| **Custom reaction set / emoji** (`supportedReactions`) | does the reference use different reaction emoji, or an extra type (e.g. 😃 `smile`)? | Functional | **EXTEND the SDK default `reactionData` (a public export), don't rebuild the array.** The defaults are already emoji (`👍 😂 ❤️ 😮 😢`, each `isMain: true`) — there is nothing to "swap to emoji." Spread `reactionData` and append/replace only what differs: `[{ type: 'smile', Icon, isMain: true }, ...reactionData]`. **`isMain: true` is mandatory on any custom entry** — the context-menu reaction picker filters to `supportedReactions.filter(r => r.isMain)`, so an entry without it never appears in the picker (the row collapses to just the "more emojis" `+` toggle) even though already-applied chips still render. Rebuilding from scratch also silently drops the default's extra-emoji list (the `...emojis.map(...)` spread that fills the "more" sheet). See [Step 2.5](#step-25-overriding-a-slot-inherits-all-of-its-sub-features) — this is that trap applied to a data array, not a component. |

#### Message metadata inside the bubble (bottom-trailing corner) — a worked relayout

Putting the **timestamp + delivery/read ticks *inside* the bubble** (bottom-trailing corner, sharing the last row with the text) is one of the two most-missed message-design details (the other is the composer). It is **structural** — no theme key moves metadata inside; routing it to a colour key is the classic failure. **Read the default `MessageContent` / `MessageSimple` in the installed package first** (verified against **stream-chat-expo 9.7.0**; confirm the slot names against the pinned version), then:

1. **Render the metadata in an in-bubble slot** — `MessageContentBottomView` (below the text, inside the bubble) or `MessageContentTrailingView` (same row as the text, trailing edge). These are *inside* the bubble background; `MessageFooter`/`MessageHeader` are *outside* it. **Note the inline-when-fits behaviour some designs use:** the timestamp sits *inline on the last text line* when it fits and only *wraps below* when the last line is too long. Reproducing that float-if-fits behaviour is fiddly; putting metadata on its own line below the text (the simpler `MessageContentBottomView` approach) is a common, acceptable approximation — but it IS a visible difference from the reference, so choose it deliberately and note it, rather than assuming it matches.
2. **Suppress the default outside footer** so it isn't duplicated below the bubble: set `MessageFooter` to `() => null` via `WithComponents` when you add a custom in-bubble one.
3. **Reproduce the bubble's own padding** — these content slots have **no padding of their own**, so the metadata otherwise touches/clips the bubble's right and bottom edge. Match the content body's `paddingHorizontal`/`paddingBottom`, and set **`alignSelf: 'flex-end'`** so it hugs the trailing corner. Make sure the bubble's rounded border/`overflow` doesn't clip it.
4. **Reuse `MessageStatus` for the ticks** — don't hand-roll single/double-tick logic (you'll desync read vs delivered). Recolour via theming — the read-tick colour is the status check-icon's **`stroke`** (e.g. `theme.messageItemView.status.checkAllIcon.stroke`; it uses `stroke`, **not** `pathFill` — confirm in the installed theme) — and **sample the tick colour off the reference** rather than assuming a "known" brand hue ([Follow EVERY color](#follow-every-color-from-the-reference--sample-it-dont-guess-and-sample-each-sub-part)).
5. **Reactions share this bottom row in some designs** — if so, render them in the same in-bubble slot and set both `ReactionListTop`/`ReactionListBottom` to `() => null` (see the reactions table above); "bottom" reaction lists render *outside* the bubble.
6. **Do both senders + verify:** incoming *and* outgoing; confirm the metadata sits **inside** the bubble background, does not clip the right/bottom edge, and the default outside footer is gone (not duplicated). This is a composite-slot change — [Step 2.5](#step-25-overriding-a-slot-inherits-all-of-its-sub-features)'s "reproduce every sub-feature" contract applies (grouping, edited/deleted state, quoted parent still render).

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

#### Long-press message menu — the default is an in-place overlay; a bottom sheet is a structural change

Easy to leave un-decomposed — a silent FAIL if the reference uses a different presentation (region left at the SDK default). Stream RN's default long-press menu is an **in-place floating overlay** (`Message` → `showMessageOverlay` → `MessageOverlayWrapper`: the message floats with the reaction picker + `MessageActionList` anchored to it). If the reference instead uses a **docked bottom sheet** (or any non-overlay menu), that's a **layout+functional** difference, not theming:
- Pass **`onLongPressMessage` to `<Channel>`** — providing the prop short-circuits the default overlay (verified in `Message.tsx`: if the prop is set it returns without calling the default handler) — and render your own menu (a plain RN `Modal` + bottom-anchored panel is enough for a sheet; no `@gorhom/bottom-sheet` dependency needed).
- **Reuse the payload's `actionHandlers`** (`{ copyMessage, editMessage, deleteMessage, quotedReply, markUnread, resendMessage, toggleReaction, threadReply, ... }`) so each item keeps **exact SDK behavior** (delete confirmation, edit composer state, quoted-reply wiring, reaction toggle). Do NOT re-implement via raw `client`/`channel` calls.
- **Exception — do NOT call `editMessage` verbatim from inside a `Modal`/sheet; it silently no-ops.** It's the one handler the SDK keyboard-gates (`useWithPortalKeyboardSafety` → `useAfterKeyboardOpenCallback`): `setEditingState` fires only *after* the keyboard opens, which the handler triggers by focusing the composer and waiting for `keyboardWillShow`. From the default overlay that works; from a **presented `Modal`** the composer is occluded, so the `focus()` can't raise the keyboard, the event never fires, and **Edit appears to do nothing**. And because every *other* handler uses `useStableCallback` (runs immediately), **only Edit breaks** — easy to miss (green launch ≠ correct). Drive edit yourself: call `setEditingState(message)` from `useMessageComposerAPIContext` (the exact setter the SDK ends up calling — the composer prefills with the message), then focus `useMessageInputContext().inputBoxRef.current` **after your container has dismissed** so the keyboard rises. General form: any payload handler that needs the composer focused / keyboard up (`editMessage` today) won't work while your own presentation is occluding the composer — verify each item **by actually firing it**, don't assume "reused SDK handler ⇒ correct."
- The `messageActions` prop only customizes the overlay's **contents**, not its **presentation** — it does NOT change the overlay into a sheet. Use `onLongPressMessage` for presentation.
- Gate the item set by ownership/type to match the reference (e.g. Edit/Delete for own text messages, Mark-as-unread for others', Resend/Delete for failed).

#### Composer deep-dive — the render tree, the surfaces, and the two-facet buttons

The composer is the region users inspect most closely and the one most often left half-matched. The table above routes each piece; this section gives you the **mental model** so you don't pick a theme key by name and get a half-styled result. **Read `MessageComposer`'s source in the installed package** (`node_modules/stream-chat-react-native-core/.../MessageComposer`) before overriding — the tree and key names below are verified against **stream-chat-expo 9.7.0**; confirm them against the pinned version (the "confirm in the installed package" rule, [Three axes](#three-axes-of-customization-internalize-this-first)).

**First check — is the composer FLOATING or docked? (structural; decide it from the reference every time.)** **The decisive cue: can you see the wallpaper/content *continuously behind and around* the composer — its pill AND its buttons? → floating.** Is there a distinct surface or a visible "cut"/seam where the message list ends and the composer's own bar begins? → docked. A composer can be **full-width with its buttons reaching the screen edges and still float** as long as content flows behind it — so don't rely on "inset side margins" as the test; *content visible behind* + a pill/button *shadow* are the reliable floating signals, and a distinct opaque bar with a seam is the docked signal. **Reason it out from the evidence, don't pattern-match a look:** if the composer's background is *exactly* the wallpaper/content with **no border or seam** — the wallpaper's texture and the messages actually continue *through and behind* it — that's **floating**. If it's a **flat fill that merely resembles the wallpaper colour** (a solid colour close to it, but the real texture/content does NOT show through), that's a **distinct surface → docked** — a similar, or even identical, colour is not the same as content showing through. The one concrete question to answer: *does the actual content appear behind the composer, or is there a separate fill in front of it?* Floating is a **first-class prop — set `messageInputFloating` on `<Channel>`** — it is NOT something you fake. **Anti-pattern (a defect, not a match): painting a translucent/rounded background onto `inputBoxWrapper` to *simulate* a floating pill while the composer stays docked.** Map the structure to the SDK mechanism first (`messageInputFloating`), then theme the surface — and resolve this structural axis *before* any cosmetic polish (Liquid Glass, exact colours). Re-derive floating-vs-docked from the reference's cues on every build; don't let an early yes/no answer lock it in against what the image actually shows.

**The container/theme-key map (`messageComposer.*`) — names do NOT map to "the bar" by intuition.** The composer nests roughly `wrapper → container → contentContainer → inputBoxWrapper (the pill) → inputBox`:
- **`wrapper` (and `floatingWrapper` for the floating variant) is the full-bleed SURFACE** — edge-to-edge and down through the bottom safe area. Its default is **padding only, no background**. **This is the composer *bar* colour.**
- **`container` / `contentContainer` are inner layout ROWS** (`flexDirection: 'row'`, sized to their children `[+][input][camera][mic]`). Colouring `container` paints only a **band hugging the controls** while the wrapper's padding + the safe-area strip stay transparent and show the wallpaper — the "slim wrap" bug. It *looks* like it worked (partial success), which is exactly why it slips past verification. If your composer colour is a band, you coloured `container`; move it to `wrapper` (+ `floatingWrapper`).
- **`inputBoxWrapper` is the input pill**; **`inputBox` is its inner content.** Grow the pill with **symmetric vertical padding on `inputBox` (`paddingTop == paddingBottom`)**, never a fixed `minHeight`/`height` on the wrapper — the pill lays out top-down and doesn't vertically centre a single line, so a fixed height drops all the slack below the text and it hugs the top (the common "taller composer, single line no longer centred" failure; see [Getting sizes right](#getting-sizes-right--measure-do-not-eyeball-round-numbers) item 6).

**The composer render tree (verified in source — confirm for the pinned version):** `MessageComposerLeadingView` (→ `InputButtons` → `AttachButton`) · the **pill** [`InputView` + `MessageInputTrailingView` (→ `OutputButtons`, the send/mic swap)] · `MessageComposerTrailingView` (default empty). So **send / mic lives INSIDE the pill by default** (`OutputButtons`) and is **stateful**: mic/audio at rest, **swapping to send when the input has text** — the composer is therefore at least **two screenshots** (at-rest and typing) from the same slot. **Reuse `OutputButtons` / `StartAudioRecordingButton`; do not hand-roll the send button, the swap, or the record gesture.** To move send/mic to the *right of the field* (outside the pill): render `OutputButtons` in `MessageComposerTrailingView` (empty by default) and override `SendButton` — a slot override, not just theming.

**The attach (`+`) button is TWO things — verify both facets in both states.** It is (1) a **trigger** that opens/closes the picker AND (2) a **stateful icon**: `+` when closed, a **keyboard glyph when the picker is open** (the "return to the keyboard" affordance common in chat apps). Two recurring misses:
- **Do not drop in the raw SDK `<AttachButton />` and assume it matches.** It renders as a `Button variant="secondary" type="outline"` — a **bordered/ringed** button with `icons.Plus`. If the reference wants a **borderless** glyph (e.g. a plain `+`), using it inherits the SDK look and discards the styling you matched (an *idiomatic ≠ matching* regression — [`../RULES.md`](../RULES.md)).
- **Its `onPress` is `toggleAttachmentPicker`, a private helper *inside* the SDK `AttachButton`** — built from `openAttachmentPicker` / `closeAttachmentPicker` / `focusInputOnPickerClose` / `inputBoxRef` + `attachmentPickerStore`. It is **not on any context or hook.** A custom `+` must **replicate it verbatim, including the refocus-input-on-close branch** — do not hand-roll `open ? close() : open()` (a lossy toggle that loses the refocus). Read the current source and copy the logic (also noted in [CHAT-REACT-NATIVE.md](CHAT-REACT-NATIVE.md)).

**Composer verification gate (do NOT leave the composer until all pass — the recurring defect). Verify STRUCTURE, not just presence/colour — a region can render the right pixels and still be structurally wrong. Verify every STATE, not every screen — a state you never render hides its defects (a stray default colour, a broken layout):**
- [ ] **Structure: floating vs docked matches the reference.** If it floats, `messageInputFloating` is set on `<Channel>` — and the pill is NOT a docked bar with a painted translucent fill faking the float. If it docks, it sits flush to the bottom edge.
- [ ] **EVERY state captured, not just the ones that render by default** — at-rest (mic/camera), **typing** (send), **voice-recording in progress** (waveform/timer), and **edit mode**. Drive typing with `useMessageComposer().textComposer.setText('hello')`; drive the recording and edit states too ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §4).
- [ ] **Keyboard-avoidance verified with the REAL keyboard up.** `setText` does not raise the keyboard, so it never exercises `keyboardVerticalOffset`. **Focus the input** so the software keyboard actually rises (on the iOS sim, enable the software keyboard — it's hidden while a hardware keyboard is attached), then confirm the composer sits correctly above it with no gap/overlap.
- [ ] **Voice-recording UI is re-themed, not left on the SDK default.** The in-progress recorder tints from `semantics.accentPrimary` (default = Stream brand blue) and `semantics.chatWaveformBar` — overriding `accentPrimary` alone can leave a recorder/waveform element on the stray default. Render the recording state and sample it (this is the *override every cascading token* rule, [`../RULES.md`](../RULES.md); confirm the token names in the installed package).
- [ ] **Background fills EDGE-TO-EDGE and through the bottom safe area** — sample pixels in the *margin around* the controls, not just the controls. A colour band hugging the buttons = you coloured `container`, not `wrapper`.
- [ ] **Single-line input is vertically centred** in the pill (grew via `inputBox` padding, not wrapper height).
- [ ] **Attach button:** correct look (borderless vs bordered) **and** the `+`↔keyboard swap when the picker opens, wired to a `toggleAttachmentPicker` replica.
- [ ] Each glyph matches the reference's size, weight, and colour; buttons vertically centred against the field.

#### Liquid Glass (`GlassView`) — gotchas when a design uses frosted/translucent chrome

`expo-glass-effect` ships in the Expo SDK 57 template; guard with `isLiquidGlassAvailable()` (true on iOS 26 + a matching Xcode toolchain) and provide a translucent `View` fallback otherwise. Three things make hand-built glass render *flat*:
- **Corner radius is a NATIVE prop** on `GlassView` (`borderRadius` / `borderTopLeftRadius` …), **not** a clipped style — passing only `style={{ borderRadius }}` yields 0-radius glass. Set it as a prop (and mirror it in `style`).
- **`overflow: 'hidden'` on the `GlassView` suppresses the effect** — remove it; let the native corner config round it.
- **The SDK input pill (`messageComposer.inputBoxWrapper`) can't be a `GlassView` via theme** — it's a plain `View` that only accepts a `backgroundColor`, so the pill stays a translucent fill. The *real* glass goes on the **custom components you wrap in `GlassView` yourself** — composer buttons, header pills, the picker capsule. Don't set a flat fill and call it glass.

**Verify glass by proving the code path, not by eyeballing the simulator.** The glass effect renders only subtle vibrancy on the sim and is far more pronounced on a device, so a sim screenshot can't confirm it. Prove which branch rendered instead — e.g. temporarily give the non-glass fallback a loud colour and confirm the element does NOT take it — then remove the probe.

**Composer - attachment picker**

Opened when the attach button is clicked

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Attachment bar | Layout (one row or multiple rows?) and position (above or under selected attachment type content) of the bar? Custom attachment bar icons (gallery, polls, files, etc.)?  Or fully custom layout (for example list)?  | Theming for recolor; Override for custom icons; `AttachmentPickerSelectionBar` for the bar; `AttachmentPicker` for a fully custom picker; verify from SDK source code default layout and behavior and decide the override scope; **Don't just re-render the default picker buttons and call it customized** — reproduce the reference's item layout (icon + label), selected-tab tint, and bar background. Build labeled items as `Pressable`s that call the SAME context actions the SDK buttons use (`attachmentPickerStore.setSelectedPicker(...)`, `useMessageInputContext().pickFile()` / `openPollCreationDialog({ sendMessage })`), and read the active tab from `useAttachmentPickerState().selectedPicker`. **Bar position:** the default host renders `AttachmentPickerSelectionBar` at the TOP. Moving the bar to the BOTTOM does **not** require replacing the host — `AttachmentPicker` resolves **both** `AttachmentPickerSelectionBar` **and** `AttachmentPickerContent` from `useComponentsContext`, so null the bar and override `AttachmentPickerContent` (see the picker deep-dive below). Only show tabs the app backs (e.g. Gallery/File/Poll); drop unbacked ones (Location/Checklist) rather than shipping dead tabs. |

**Mixed camera+library picker:** if the reference shows a single combined picker (live camera preview inline with the photo grid, as in iOS's own sheet), RN Chat has no combined picker — split it into **separate library and camera tabs** (`MediaPickerButton` → `images` tab, `CameraPickerButton` → `camera-photo`/`camera-video`), don't try to fake one merged surface. Check if picker is open or not with `attachmentPickerStore.state.getLatestValue().selectedPicker`

**A chat app's attach sheet IS Stream's `AttachmentPicker` — override the bar, don't rebuild the surface.** Most chat-app attach sheets share one shape: an **action-tile selection bar on top + a media gallery below** — which is exactly `AttachmentPicker`'s default layout. So the default move is: **override only `AttachmentPickerSelectionBar`** (via `WithComponents`) to match the tiles, and **keep the SDK gallery + the `AttachButton`/`openPicker` lifecycle + the attachment-preview + permission flow.** Do **NOT** build a standalone `Modal` with your own sheet state — that bypasses the SDK gallery, previews, and permissions, and re-implements infrastructure the SDK already has.

For a **bottom** tab bar, you still do **not** replace the host. `AttachmentPicker` resolves **both** `AttachmentPickerSelectionBar` **and** `AttachmentPickerContent` from `useComponentsContext` (verified in the installed `AttachmentPicker` source — confirm for the pinned version), so **both are `WithComponents`-overridable.** Recipe: set `AttachmentPickerSelectionBar` → `() => null` and override `AttachmentPickerContent` to render the **default gallery** plus your bar — then match the reference's bar type. **If the bar floats over the gallery** (hovers, gallery visible behind it): render the gallery at **full sheet height** and the bar as an **absolutely-positioned overlay** (`position: 'absolute', bottom: 0`), and do **NOT** subtract the bar's height from the gallery. **If the bar is flush** (gallery ends where the bar begins, no overlap): a **stacked** bottom section with the gallery height reduced by the bar height is correct. (Match the bar's shape + material either way — see the bar-shape bullet below.) One trap regardless of type: do **NOT** conclude the layout is locked because the `<AttachmentPicker>` host is a direct import in `Channel` — the host being imported directly doesn't lock its children, which are context slots ([`../RULES.md`](../RULES.md) > *enumerate every context slot*).

- **Match the bar's SHAPE and MATERIAL, not just its tiles.** Read the reference for what the bar actually is — it may be a **flush flat bar** (sits on its own surface, often only the top corners rounded) **or** a **floating inset capsule** (all corners rounded, side/bottom margins so it hovers, often frosted/`GlassView`, horizontally scrollable, a tinted pill on the selected tab). Decide from the image; don't default to either. Reproduce that shape + material even once the tiles are right — correct tiles in the wrong container (flat when the reference floats, or floating when it's flush) is still a miss.
- **Reference-reading rule (this caused a from-scratch modal once):** the photos in a picker gallery are frequently **screenshots of other apps** (other chats, home screens, a settings page). Do **not** mistake that screenshot *content* for chrome — a strip of app-like thumbnails with selection circles / a grid **is the photo gallery**, not "chat cards" or an app switcher. Re-crop the region at full resolution and confirm its identity before concluding the SDK picker can't match it. A decision that leads to reinventing a whole surface is the signal to re-check the reference read ([`../RULES.md`](../RULES.md) > *reinvention is a red flag*).
- **Picker height — anchor to the keyboard, no magic number.** The picker is a **keyboard-replacement** sheet, so its height should ≈ the keyboard. Anchor to the SDK default **`attachmentPickerBottomSheetHeight` (333)**. If you enlarge the selection bar, keep the **total** near keyboard height — a static approximation like `default_sheet + default_bar` (~`405`) is right. Do **not** invent a "roomy gallery" number (e.g. `+340`, which balloons the sheet far past a keyboard — only obvious on a physical device, not the roomy simulator), and do **not** swing the other way into a runtime keyboard-measuring hook (overreach). Simplest static approximation first ([`../RULES.md`](../RULES.md) > *no magic numbers*).

> **`keyboardVerticalOffset`/`topInset` on `Channel` — default to `0`; they offset for chrome ABOVE the Channel, not for a header inside it.** (This reconciles with [`../RULES.md`](../RULES.md) > Navigation and overlay discipline, which is authoritative — read it if this note and any other doc ever seem to disagree.) The two props exist so the keyboard-avoiding view and the attachment-picker bottom sheet know how far down the Channel's top edge starts. Route by **where the header is rendered**, not by "native vs custom":
> - **Native nav header, or a custom header rendered as a *sibling above* `<Channel>`:** the Channel's top is pushed down by that header, so set **both** `topInset` **and** `keyboardVerticalOffset` to its height (equal values). Native: `useHeaderHeight()` (RN CLI / Expo Router ≤ 55) or the `Platform.OS + insets.top` swap on Expo Router 56+. Sibling header: `insets.top + <your header content height>`.
> - **Custom header rendered *inside* `<Channel>`** (`headerShown: false` + your own header `View` above `MessageList`, the common floating in-screen-header pattern): the Channel already fills the screen from `y=0`, so there is **nothing above it to offset** → pass both **explicitly as `0`**: `keyboardVerticalOffset={0} topInset={0}`. **Do not just omit them** — in the installed SDK, `Channel` defaults `topInset` to `0` but destructures `keyboardVerticalOffset` with **no default**, so omitting it passes `undefined` (which is *not* `0`) and leaves keyboard-avoidance unverified (confirm the default in the pinned `Channel` source — assumed behaviour ≠ the SDK default, [`../RULES.md`](../RULES.md) > Design-matching discipline). A non-zero value here is the bug, not the fix: it over-compensates the keyboard-avoiding view and mis-computes the picker snap. Don't leave a dead `insets.top + HEADER_HEIGHT` value in place. **Verify by focusing the input so the real keyboard rises** (see below) — not by `setText`, which raises no keyboard.
>
> **The composer↔picker gap symptom.** When the picker opens, the docked composer shifts up by the picker's reserved height (`attachmentPickerBottomSheetHeight`, default `333`), and the sheet's snap is computed from `topInset`. A gap ("picker detached from the input") means `topInset` is **wrong for the layout**: with a native/sibling-above header it's missing/too small → raise it to the header height; with an inside-`Channel` header it's non-zero when it should be `0` → set it to `0`. **Try `0` first** and only add an offset if a native header is present or the picker demonstrably misbehaves.
>
> **Do NOT try to close the gap with `bottomInset`.** `bottomInset` shrinks the composer's upward shift (`attachmentPickerBottomSheetHeight - bottomInset`); dialing it up moves the input *down, under* the sheet and hides it. `bottomInset` is only for a bottom tab bar that owns the safe area — not a lever for picker spacing.
>
> **Exception — a persistent app-owned bottom tab bar on the message screen (floating-composer apps like Slack / Telegram).** Everything above assumes a docked composer and **no** bottom tab bar. When the message screen keeps an **app-owned bottom tab bar** AND the composer floats (`messageInputFloating`), `topInset`/`bottomInset` alone **cannot** close the gap — this is the one layout where "just fix `topInset` / try `0` first" fails, so recognise it before you start tuning numbers. Why: the composer lives inside the **tab-navigator-inset scene**, while the picker is a **root-anchored bottom-sheet portal** (snapped to `attachmentPickerBottomSheetHeight`, lifted off the screen bottom by `bottomInset`) — two different coordinate spaces. A single `bottomInset` can't reconcile them because the composer's picker-open shift (`sheetHeight − bottomInset`) and the sheet's lift (`bottomInset`) move in **opposite** directions: raise it and the composer rides *over* the input while the sheet's lower half hides *behind* the tab bar (its centred empty-state then reads as a tabs↔content gap); lower it and the composer detaches upward. **Don't chase the number** — fix it the way the keyboard already coexists: **hide the tab bar while the picker is open.** Mirror the picker state out of `<Channel>` to the tab layer with a tiny cross-tree store written by a bridge that reads `useAttachmentPickerState().selectedPicker`; set the tab bar to `display:'none'` (or return `null`) while open so the scene reflows full-height; keep `bottomInset={0}`. Read `AttachmentPicker.tsx` (snap points + root anchoring) **before** tuning any inset here — the structure is the answer, not the number ([`../RULES.md`](../RULES.md) > *fix the structure before the surface*).
>
> **Verify with the picker OPEN, and wait for the image grid to load.** A picker screenshot taken before the device photo library / remote thumbnails finish loading shows a short, half-empty grid that *also* looks like a gap — re-screenshot after the grid settles before diagnosing (and open to the **Files** tab per SIMULATOR-VERIFICATION to avoid the un-dismissable photo-permission prompt).
>
> **Don't mistake the picker's empty / not-granted placeholder for a tabs↔content gap.** The selection bar and the content render inside **one** sheet, contiguous (content height = `attachmentPickerBottomSheetHeight − selectionBarHeight`), so a populated gallery starts right below the tabs. But the **not-granted / empty-state panel is centre-aligned** in the content area, so it floats in the middle with a large gap above it — which looks exactly like a broken "tabs detached from content" layout. On the simulator this is the *default* state: `xcrun simctl privacy grant photos` frequently does **not** satisfy `expo-media-library`, so the grid never populates. Do **not** diagnose that centred placeholder as a layout bug, and do **not** declare the picker layout verified from the not-granted state alone — confirm a populated grid on a device (or once access is genuinely granted) before judging tabs↔content spacing.

**Thread surfaces** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Thread reply screen | Does it exist? Not all apps have threads; parent message + replies | Layout / **App-owned nav** | separate nav screen: `Channel` with `threadList` + `Thread` (**Thread Screen** blueprint in [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md)) - reuses your row + composer overrides; see the RN-specific thread notes in Step 2 |
| Thread inbox / list | row layout | Theming (+ Layout) | `ThreadList` inside `Chat` (**Thread List Screen** blueprint); thread-list theme keys + `ThreadList` item props if the row differs |
| Message replies indicators (message component) | Layout and styling | Theming + Layout | `MessageReplies`; default is connector + avatars |

> The RN slot/mechanism details behind these Chat rows (which slot to override for metadata
> beside/inside the bubble, ungrouping + spacing, uniform bubble corners, in-bubble reactions,
> appending content below a message, `ChannelPreview` `onSelect`, composer button shape/position,
> the v9 no-cascade token model) live in
> [CHAT-REACT-NATIVE.md](CHAT-REACT-NATIVE.md#composer-attach-button-and-message-metadata-facts) —
> confirm names against the pinned package.

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
