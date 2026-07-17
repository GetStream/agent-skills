# Stream Android - matching a reference design (screenshot / Figma / "make it look like X")

When the user gives a **target appearance** - a screenshot, a Figma frame, or "make the chat look
like WhatsApp / Telegram / Slack / a livestream" - the job is **not** "set a few colors." A reference
is a **checklist of regions**, and most real designs differ from Stream's Compose defaults in
*structure* - the bubble shape, where the timestamp and read receipts sit, the composer button set,
the wallpaper, the header - not just color. Changing the accent and the wallpaper and calling it done
is the classic failure; do not repeat it.

**Implement EVERY region - the composer is first-class, not optional.** Do not deliver a partial match
with the rest labelled "known cosmetic gaps." If a region needs a relayout (a bubble tail, metadata
inside the bubble, moving send/voice), do the relayout by overriding the right `ChatComponentFactory`
slot and reproducing the default's sub-parts. "Risky / more effort" is not a reason to skip; only
genuine impossibility is, and then say exactly what and why.

Run this **before** writing code, in addition to the normal `stream-android` build flow.

## The method: derive, do not clone

This skill does **not** encode any specific app's design, and it is not a "clone WhatsApp" tool. It is a
repeatable method for reproducing **any** reference. A reference may be **one or more screenshots**
covering different screens (channel list, message screen, thread, ...). **First classify each screenshot
and map it to its Stream surface (Step 0); then, for EACH screen:**

1. **Derive the design concepts** the reference expresses - surface/background, bubble style, metadata
   placement, header composition, composer inventory, density, typography, accent.
2. **Diff each concept against the Stream default** - what actually differs is the work; what already
   matches, leave alone.
3. **Decompose** the differences into concrete regions/components.
4. **Route** each difference to its mechanism - theming token, `ChatComponentFactory` slot, or config
   (Step 2).
5. **Build**, then **verify** region-by-region against the reference and iterate (Step 5).

Match **every** screen the reference covers - matching the message screen and leaving the channel list
at its default is a common, visible miss.

App names used below (WhatsApp, Telegram, Slack, a livestream, ...) are **illustrations of a concept**,
never a template to reproduce from memory. **Derive every value - color, size, position, weight - from
the reference in front of you**, not from what you recall about that app. A different reference yields
different regions and different mechanisms; the method is the same.

## Work in batches - a full match is many regions; do not let it take all day

- **Ground the pinned SDK version ONCE** (Step 3), then read every slot signature, `*Params` class,
  and default composable body you will need **in a single pass** - do not drip-feed greps while coding.
- **Decompose all regions, implement all of them, THEN build once.** Do not rebuild-and-screenshot
  after each tiny edit; batch a round, rebuild once, screenshot once.
- **Reuse one running emulator** (or device) and a persistent Gradle build; take **one** screenshot
  after a short settle. Iterate only on regions that actually fail.

---

## Two axes of customization (internalize this first)

Stream's Android Compose SDK has **TWO** customization axes, not three. (iOS and some platforms have a
third "Styles" axis for padding/inset/radius - **Android does not**; the SDK exposes no public
`StreamShapes`/`StreamDimens` types - radii/spacing live in an `internal` token object you cannot set.
Confirm this against the version the app pins - Step 3.)

| Axis | Mechanism | Changes | Cannot change |
|---|---|---|---|
| **Theming** | `ChatTheme(colors = StreamDesign.Colors(...), typography = StreamDesign.Typography(...))` | Colors, fonts | Layout/structure; and **padding / corner-radius / bubble shape** (no token) |
| **Structure** | `ChatTheme(componentFactory = object : ChatComponentFactory { ... })` - ~196 slots, each takes one `params: <Name>Params`; override the **narrowest** slot | The composables that render, their arrangement, padding, radius, chrome | Colors/fonts (that is theming) |
| *(cross-cutting)* **Config + hooks** | `ChatTheme(config = ChatUiConfig(...), channelNameFormatter =, messageAlignmentProvider =, dateFormatter =, reactionResolver =, ...)` | Behavior flags, message alignment, formatting, feature toggles | Visual structure |

Two recurring mis-routings (each is why a screen "looks close" but is still wrong):
- Solving a **padding / corner-radius / bubble-shape** difference with a **theme color**. On Android
  there is no radius/inset token - "the bubble corners are too round", "the composer is too tall",
  "the bubble has too much padding" are all **structure** (override the slot), not theming.
- Solving a **structural** difference (metadata inside the bubble, a bubble tail, a `+` moved outside
  the field) with a **color token**. Structure -> `ChatComponentFactory`, not `StreamDesign.Colors`.

### The bubble-color trap - read before touching bubbles

The chat bubble tokens - `chatBgIncoming` / `chatBgOutgoing`, `chatTextIncoming` / `chatTextOutgoing`,
`chatBorderIncoming` / `chatBorderOutgoing`, `chatBgAttachmentIncoming/Outgoing` - are **derived
`internal val`s** on `StreamDesign.Colors`, computed from `brand` (a `ColorScale`), `accentPrimary`,
and `chrome`. **They are NOT constructor parameters.** You cannot set the outgoing bubble to an
arbitrary color (e.g. WhatsApp green) via `ChatTheme(colors = StreamDesign.Colors(...))`.

Two real paths to recolor a bubble:
1. **Move the `brand` scale / `accentPrimary`** the bubbles derive from - but this cascades to buttons,
   links, and every accent surface, so only when the whole app accent matches the reference.
2. **Override the `MessageBubble` slot** (fill/shape/border) and `MessageContent` / `MessageTextContent`
   (text) - the reliable path for a specific bubble color independent of the app accent.

Set the **fill AND the text** color - a solid outgoing bubble needs its text set too, or the text stays
the default (often dark/illegible on a colored fill).

**Sample the brand/accent color EXACTLY, and set the full `brand` scale - not just `accentPrimary`.**
The accent drives many derived tokens (bubbles, buttons, links, ticks), so a *guessed* or slightly-off
accent makes the whole theme read wrong, and setting **only** `accentPrimary` (leaving the `brand`
`ColorScale` at its default) produces a flat, **washed-out** look. Pixel-sample the reference's brand
color (do not eyeball a "green"/"blue") and build a full `StreamDesign.Colors` with a matching `brand =
ColorScale(...)` (s50..s900 stepped around the sampled hue) plus `accentPrimary`, so accented surfaces
are vivid and consistent. Verify the rendered accent hex matches the sampled reference hex.

---

## Step 0: Identify the screens (one or more screenshots)

A design reference is usually **several screenshots** of different app screens. Before decomposing,
**classify each screenshot** by its telltale content, map it to the Stream surface + the slot family
that drives it, then run Steps 1-5 for EACH screen. Classify by structure, not by the app's name.

| The screenshot shows... | Screen | Stream surface | Slot family (where the design lives) |
|---|---|---|---|
| A vertical list of conversations (per row: avatar + name + last-message preview + time), a top/workspace bar, a new-chat affordance | **Channel list** | `ChannelsScreen` (e.g. a ChannelsActivity) | `ChannelListHeader` + `ChannelListHeaderLeading/Center/TrailingContent`; `ChannelListItemContent` + `ChannelItemLeading/Center/TrailingContent` |
| One conversation: message rows/bubbles + a header + a composer at the bottom | **Message screen** | `ChannelScreen` (e.g. a ChannelActivity) | `ChannelHeader` + `ChannelHeaderLeading/Center/TrailingContent`; `MessageContainer` / `MessageBubble` / `MessageContent`; `MessageComposer*` |
| A list of threads / "N replies" entries | **Thread list** | `ThreadsScreen` | `ThreadList*` |
| Member/channel details, shared media grid | **Channel info** | channel-info screens | `ChannelInfo*` / `GroupChannelInfo*` |

**The channel-list screen and the message screen have DIFFERENT headers** - the list header is
`ChannelListHeader*` (a workspace/title bar with its own actions), the message header is `ChannelHeader*`
(channel title + presence + actions). They are separate slots on separate screens - decompose and match
each on its own screen; never carry one screen's header to the other. **Match every screen the reference
covers**; if only one screenshot is given, match that one - but never leave a screen the reference shows
sitting at its Stream default.

**Non-chat components: ignore them structurally, but harvest the design language.** A reference may
include screens/components a chat SDK cannot and should not reproduce - a bottom tab/nav bar, a home
feed, a profile or settings screen, onboarding, marketing chrome. Do **not** try to build those into the
Stream chat surfaces; they are the host app's responsibility and out of scope for this skill. But **do
extract the cross-cutting design principles** from them - color palette, typography scale, corner-radius
/ shape language, spacing and density, icon style, elevation/shadows - and apply that language to the
chat screens so Chat looks native to the surrounding app. In short: **reproduce structure only for the
chat screens; derive the design *system* from the whole reference.**

---

## Step 1: Decompose the reference into regions (every time)

Go region by region. For **each** region: name what the design shows, compare to the Stream default,
and decide theming vs. structure vs. config vs. already-default. Produce an explicit task list - one
entry per region that differs. Do not skip a region because it "looks standard"; verify it against the
default.

**The recurring failure is under-decomposition.** The message bubble tends to get careful treatment
while the **composer, the header, and the channel-list row** get dismissed as "a field and some icons"
or "glyph + name" - and each turns out to be a multi-part composite that needs the same rigor (rows,
alignment, field shape; three header slots; leading-type + preview + trailing). Decompose those three
with the same care as the bubble. And keep every difference framed as an **SDK mechanism** (a derived
token, a bottom-aligned row, a shape that is structure-not-token), never as "app X does Y" - the method
derives from the reference in front of you, it does not encode any app.

**Capture measurements, not just identity.** The reference is a *spec*. For every region record the
concrete attributes you will reproduce: header height + title size/weight + subtitle; bubble corner
radius, tail, max width, alignment; icon sizes and gaps between composer buttons; font sizes/weights;
paddings; exact colors. "Looks roughly like it" is the failure mode.

### Get the dimensions right (do NOT eyeball round numbers)

Work in **dp**, not raw pixels. An `adb exec-out screencap` is in device pixels; convert:

```
dp = px * 160 / densityDpi          # densityDpi from: adb shell wm density
# e.g. Pixel 7 = 1080x2400 @ 420dpi -> 1 dp = 2.625 px -> width = 411 dp
```

Extract element sizes **automatically** - do not eye them off the image. `python3` + PIL + numpy:
threshold a cropped region and read real bounding boxes (dark glyphs on a light bar -> project onto
columns, cluster into glyphs, measure each box in px, divide by scale for dp). Controls are almost
always **smaller** than you guess. Match the measured dp, not a round number.

**Match stroke WEIGHT too** - a title, author name, message body, and timestamp are usually different
weights; map each to the closest `FontWeight` and set them independently (Stream typography tokens:
`bodyDefault`, `bodyEmphasis`, `headingSmall`, `metadataDefault`, `numeric*` - see Step 2).

### Sample every color from the reference - do not guess

Sample-and-match wallpaper, bubble fills, composer bar, each glyph, borders, and read-receipt ticks.
Sample the saturated **core**, not antialiased edges; isolate small colored elements from similar
colors in photo attachments before averaging.

- **Structural surfaces stay adaptive.** Pin sampled *brand/content* colors (bubble fills, wallpaper,
  ticks). But bind *chrome surfaces* (list background, composer bar) to the SDK's semantic tokens
  (`backgroundCoreApp`, `backgroundCoreElevation1`) so light/dark still works - a reference is usually
  a light screenshot; a pinned-white surface breaks in dark mode. Verify by toggling dark mode.

### A background may be a TEXTURE, not a flat color

WhatsApp/Telegram wallpapers are subtle **patterns**, and that texture is what separates the chat area
from the composer. Detect it (sample many points - varying = pattern), reproduce it via
`MessageListBackground` (tile the asset, or a faint tiled motif if the art is proprietary; say it is an
approximation), and match its **ink coverage** and **stroke width** by measurement, not by eye.

### Region checklist (walk all of these)

**Channel list screen** (if in scope) - decompose the ROW as thoroughly as a message row; it is not
just "glyph + name":
- [ ] List header (`ChannelListHeader*`): workspace/title, search bar, avatar, actions - a DIFFERENT
      slot from the message header
- [ ] **Row leading depends on channel TYPE** - a public channel (`#`), a private channel (lock), and a
      **DM (a person's avatar + presence dot)** look different. Do NOT prefix a DM with `#` (see the
      channel-vs-DM rule in Step 2.5)
- [ ] Row name: weight/color, and **read state** (unread rows are usually **bold**)
- [ ] Last-message **preview** line (present? one line? sender prefix? muted style?)
- [ ] Row trailing cluster: timestamp, unread **badge/count**, member **facepile**, muted/pin icon
- [ ] **Sections**: is the list grouped under named headers (favorites, unreads, categories)? (See the
      sectioning note in Step 2.5 - grouping is a data/query concern, not a slot.)
- [ ] Row density/height, dividers, background

**Message screen - chrome**
- [ ] Header: title, subtitle/member count, back affordance, trailing avatar/action
- [ ] Chat background / wallpaper
- [ ] Date separators and the unread separator
- [ ] Scroll-to-bottom / scroll-to-unread overlays

**Message screen - the message**
- [ ] Layout style: **bubbles** (messenger) vs **flat left-aligned rows** (workplace/Slack: avatar-top,
      author-status-time header, bottom reactions, thread summary, no in/out split)
- [ ] Bubble: fill, border, corner radius, **tail/beak**, max width, alignment
- [ ] Grouping (consecutive same-author messages; who shows an avatar)
- [ ] **Metadata placement**: timestamp + delivery/read ticks - below the bubble (Stream default) or
      **inside it** (WhatsApp/iMessage)? Inside = structural.
- [ ] Read/delivery glyphs (single/double tick, color)
- [ ] Avatars beside messages (shown? side? shape?)
- [ ] Reactions (style, position), quoted replies, thread-reply summary
- [ ] System / deleted / moderated messages

**Message screen - attachments**
- [ ] Image/photo grid (the grouped collage is already the Stream default - restyle, do not rebuild)
- [ ] Video, file, giphy, link, audio-recording, poll, custom attachments

**Composer** (almost always differs - inspect closely, in BOTH states: at rest and while typing)
- [ ] Leading button(s) - e.g. WhatsApp `+`
- [ ] Input field container + text input
- [ ] Icons inside the field, trailing (sticker/emoji) - and **send / voice-record live here**
- [ ] Buttons right of the field (camera + mic) - Stream's slot here is **empty by default**
- [ ] Send button glyph/placement; voice-record vs send swap

**Cross-cutting**
- [ ] Fonts, accent color, icon set
- [ ] Light/dark behavior

State the result as a task list: `Region -> default vs target -> mechanism (theme token / factory slot /
config / already-default)`. Implement **all** differing regions, not just the cheap theming ones.

---

## Step 2: Region -> mechanism map (verified against the SDK source)

Slot names are `ChatComponentFactory` methods; tokens are `StreamDesign.Colors` / `Typography`;
config is `ChatUiConfig` + `ChatTheme` hook params. Confirm every signature in the pinned source
before use (Step 3) - this table routes, it is not verbatim API.

| Design region | Axis | mechanism |
|---|---|---|
| Chat wallpaper / background | Structure | `MessageListBackground` slot |
| App bar / channel header | Structure + hook | `ChannelHeader` + `ChannelHeaderLeading/Center/TrailingContent`; title via `channelNameFormatter` |
| Accent color | Theming | `accentPrimary` (+ `brand` scale) |
| Fonts | Theming | `StreamDesign.Typography` (`bodyDefault`, `bodyEmphasis`, `headingSmall`, `metadataDefault`, `numeric*`) |
| List / surface background | Theming | `backgroundCoreApp`, `backgroundCoreElevation0..3` |
| Outgoing/incoming bubble FILL | Structure* | `MessageBubble` slot (derived tokens not settable - see trap) |
| Bubble TEXT color | Structure* | `MessageContent` / `MessageTextContent` |
| Bubble shape / tail / radius | Structure | `MessageBubble` slot (no radius token) |
| Metadata (timestamp/ticks) placement | Structure | `MessageBottom` / `MessageFooterContent`; in-bubble -> `MessageContent` + `MessageBubble` |
| Message alignment (left-align livestream/open) | Hook | `messageAlignmentProvider` |
| Full row relayout (flat workplace rows) | Structure | `MessageContainer` / `MessageItem` (composite - reproduce sub-parts) |
| Avatars (shape/size/style) | Structure | `Avatar` / `UserAvatar` / `ChannelAvatar` slots - **override these to change avatar SHAPE** (e.g. rounded-square vs circle); clipping around the default avatar does NOT reshape it. `MessageAuthor` positions the in-row avatar |
| Reactions | Structure + config | `MessageReactions` slot; `reactionResolver`; `ChatUiConfig.messageActions.reactionsEnabled` |
| Thread-reply summary | Structure | `MessageFooterContent`; thread screens via `ThreadList*` slots |
| Date / unread separators | Structure | `MessageListDateSeparatorItemContent`, `MessageListUnreadSeparatorItemContent` |
| Composer leading `+` | Structure | `MessageComposerLeadingContent` |
| Composer input field | Structure | `MessageComposerInputCenterContent` (+ `MessageComposerInput`) |
| Composer send / voice (in field) | Structure | `MessageComposerInputTrailingContent`, `MessageComposerSendButton`, `MessageComposerAudioRecordingButton` |
| Composer buttons right of field | Structure | `MessageComposerTrailingContent` (empty by default - add here) |
| Floating vs docked composer | Config | `ChatUiConfig.composer.floatingStyleEnabled` |
| Voice recording enabled | Config | `ChatUiConfig.composer.audioRecordingEnabled` |
| Channel list row | Structure | `ChannelListItemContent` + `ChannelItemLeading/Center/TrailingContent` |
| Unread badge / read state | Structure | `ChannelItemUnreadCountIndicator`, `ChannelItemReadStatusIndicator` |
| Live video pane (livestream) | N/A | Not a Stream chat component - the host app renders video; chat is composed beside/over it |

\* Structure because the underlying color tokens are derived and not directly settable (see the trap).

**The message slots carry the full state - use it (do not assume data is missing).** `MessageContent`,
`MessageContainer`, `MessageBottom`, and `MessageFooterContent` all receive
`params.messageItem: MessageItemState`, which exposes `message` (hence `message.createdAt` and
`message.syncStatus`), `isMine`, **`isMessageRead`**, and `messageReadBy`. So **metadata that belongs
INSIDE the bubble** (WhatsApp/iMessage timestamp + read tick, bottom-trailing) is done in
`MessageContent` reading `messageItem` - the timestamp/read state is **not** confined to the
below-bubble `MessageFooterStatusIndicator` slot. Derive the tick from `message.syncStatus`
(sent / pending / failed) plus `isMessageRead`. Before concluding "the SDK can't do X", read the slot's
`*Params` in source (Step 3) - the state is usually there.

**In-bubble metadata must be LAID OUT, not overlaid (the recurring bug).** The tempting shortcut is to
absolutely-position the timestamp + tick at the bubble's `BottomEnd` (a `Box` overlay) and reserve a
`bottom` padding on the text. It looks fine on a medium message and breaks two ways: (1) on a message
whose **last line is wide**, the overlay sits **on top of the text** (time/tick overlap the words);
(2) on a **short** message ("hello?") the bubble sizes to the short text, so the wider metadata
**overflows the bubble edge** and the reserved bottom padding reads as a too-tall, half-empty bubble.
Root cause: an overlay does not contribute to the bubble's measured size, so the bubble never reserves
room for it. **Fix: make the metadata part of the bubble's layout so the bubble sizes to
`max(textWidth, metadataWidth)` and nothing overlaps.** Two options:
- **Faithful WhatsApp/iMessage:** a custom `Layout`/`SubcomposeLayout` that places the metadata inline
  after the last word when it fits on the last line, and wraps it to its own trailing line when it does
  not. This reproduces the exact "time tucks into the last line" behavior.
- **Robust approximation:** `Column { messageContent(); Row(Modifier.align(Alignment.End)) { Timestamp(); Tick() } }`
  so the metadata always sits on its own bottom-trailing line **inside** the bubble - width becomes
  `max(text, metadata)`, no overlap, no manual bottom-padding hack. Give the time->tick `Row` real
  spacing (>= 4dp) so they do not crowd each other.
Measure the reference to choose: is the metadata **inline** with the last text line, or on **its own
line**? And test both a **short** ("ok") and a **long/wide** message - the short one is where overlay
bugs show.

**Reproduce the bubble's internal content padding (or text touches the edge).** The default bubble pads
its content away from the bubble border; a custom `MessageBubble`/`MessageContent` that wraps
`super.MessageContent(...)` in a bare `Box(clip + background)` **drops that padding**, so the text hugs
the bubble edge. Re-apply content padding **explicitly** - there is no dimens token, so measure it from
the reference (typically ~8-12dp horizontal, ~6-8dp vertical) and set it in the override. Likewise keep
the bubble's outer margin from the screen edge and its max-width. This is the composite-slot rule again:
padding is one of the things the default drew that silently disappears when you take over the slot -
reproduce it.

**Reactions default to a floating pill overlapping the bubble - reposition if the reference differs.**
The SDK renders reactions as a small pill **overlapping the top corner** of the message. Many designs
instead show reactions as **chips laid out below the message content** (Slack/Telegram). That is a
*position* change, not a recolor: move them via `MessageReactions` (and, for a below-content row, the
`MessageFooterContent` / row layout), the same way in-bubble metadata is a layout change. Verify a
message that actually has reactions - an unreacted seed hides this entirely (see "data-limited" below).

---

## Step 2.5: Overriding a composite slot inherits ALL of its sub-features

The high-level slots render **many** children internally. Override one and every sub-feature it drew
**disappears unless you reproduce it**. A custom row that handles only the case in front of you (one
outgoing bubble) silently drops avatars, grouping, reactions, replies, and status - and a near-empty
test channel hides the loss.

**Rule:** before overriding a composite slot, read its default `@Composable` body in the pinned source,
enumerate every sub-view and branch, and for each decide reproduce (call the SDK's own slot/composable)
or consciously drop (and say so). Prefer the **narrowest** slot; reach for the big hammer only when a
structural change truly needs it.

- `MessageContainer` (avatar + bubble + reactions + top/bottom) - override only for a full row relayout
  (flat workplace rows). Otherwise use `MessageBubble` / `MessageContent` / `MessageBottom`.
- `MessageComposer` - a large assembly with ~30 sub-slots. **Never override wholesale.** Target
  `MessageComposerLeadingContent` (the `+`), `MessageComposerInputTrailingContent` (send + voice-record -
  they live INSIDE the field, not in a right-of-field slot), `MessageComposerSendButton`,
  `MessageComposerInputCenterContent` (the field). `MessageComposerTrailingContent` (right of field) is
  **empty by default** - add a camera/mic cluster there.
  **Run the row-count test on the composer, every time (the single most-skipped relayout).** Count the
  rows in the reference composer. Stream's default is **ONE row**: `leading | input field | trailing`.
  Swapping sub-slots can only ever change what sits *within that one row* - it is **structurally
  incapable of adding a second row**. So:
  - **Reference composer is 1 row** -> sub-slot swaps are fine (`MessageComposerLeadingContent`, etc.).
  - **Reference composer is 2+ rows** (e.g. the input field spans its own row, with a toolbar of icons +
    send on a separate row below - the Slack/Discord pattern) -> you **MUST override the whole
    `MessageComposer`** and rebuild the arrangement as a `Column { inputFieldRow; toolbarRow }`. There
    is no other way to get a second row. Reuse the SDK's input + send + attachment sub-composables so
    text entry, send, and attachments keep working; only the *arrangement* is yours. Do NOT ship a
    single-row composer with the icons rearranged and call it a match - that is the recurring failure.
  Also match **where each control sits within its row** - e.g. a send button pinned to the far right of
  the toolbar row is not the same as a send button trailing the input field. Match row count AND
  per-row placement, not just the icon set.
  **Vertically align custom composer content (the ragged-icon trap).** The default `MessageComposer`
  lays its integration row out with `verticalAlignment = Bottom` (so a multi-line field grows upward
  while the buttons stay pinned to the bottom). A custom leading/trailing icon that is *shorter* than
  the input field therefore sits **low and ragged** next to it - the composer looks broken on its own,
  before any design question. Fix it by giving every composer element the **same height** and centering
  within it (e.g. wrap each icon cluster in a `Box(Modifier.height(rowHeight), contentAlignment =
  Center)` and give the input the same height) so their centers line up; keep icon sizes and inter-icon
  spacing consistent. Verify the row looks level in the screenshot.
  **The input field's SHAPE/border is structure, not a token - and the SDK ALWAYS draws a border
  stroke.** The SDK's `MessageComposerInput` wraps the text field in `MessageInput`, which bakes in a
  `.border(borderCoreDefault, RoundedCornerShape)` **plus** a background fill (a pill) - there is no
  radius/shape token to flip (same as bubbles). **Check for the border STROKE specifically, separate from
  shape/fill:** many designs have a composer with a subtle *fill* but **no stroke at all** (Slack), or a
  fully flat field (Telegram) - the SDK's stroke then reads as an extra outline the reference does not
  have. This is **easiest to miss in dark mode**, where the light-gray stroke is the only thing wrong on
  an otherwise-close screen and an agent glances past it as "there's a field, looks fine." If the
  reference field is **flat / borderless / stroke-less**, a **different radius**, or a different fill, do
  NOT try to theme it away:
  **override `MessageComposerInput`** and render the SDK's borderless center content directly
  (`MessageComposerInputCenterContent(MessageComposerInputCenterContentParams(state, onInputChanged))`)
  in your own flat container - this keeps the real text field + placeholder while dropping the pill. When
  you take over the input wrapper you also drop its built-in send/mic and any attachment/quoted/edit
  previews (composite-slot rule): re-add a **send** affordance (the wrapper's `params` carries
  `state.inputValue` and `onSendClick` - show send when `inputValue` is non-blank), and reproduce or
  consciously drop the rest per the reference (Telegram's rest state shows no mic and no send).
  **The center content already carries its own start inset, vertical inset, and min-height - your
  container must not re-add them.** Give your flat container only border, shape, fill, and width; never
  add a second start padding (the placeholder inset doubles), vertical padding, or height (the field
  compounds tall). A compounded-tall input also overshoots a compact reference and, because the
  composer's own integration row is padded and `Bottom`-aligned with no centerline hook (an SDK
  constraint, not settable), drops a shorter leading control below the field's centerline - so size any
  custom leading control to the input's height and center its glyph so their centers line up
  (ragged-icon trap above).
- `ChannelHeader` - use `ChannelHeaderLeading/Center/TrailingContent`. Drive the title from
  `channelNameFormatter` (set once; it feeds BOTH the header and the channel list - never hardcode the
  reference's literal channel name, or every channel shows that one name). **Resolve nameless DMs here
  too:** a direct message usually has no `name`, so the default title falls back to a placeholder
  ("Channel") - make `channelNameFormatter` return the **other member's name** for a nameless DM so the
  message header shows the person, not "Channel" (this is the SAME formatter that distinguishes DM vs
  channel in the list - fix it once, both surfaces benefit). **The default header rarely
  matches a reference - do NOT rubber-stamp it "already-default."** Stream's default is: back-arrow
  (leading), centered title + subtitle (center), **channel avatar / member facepile (trailing)**.
  Decompose the reference's header across ALL THREE slots and reproduce whatever it shows in each:
  - **Trailing is the silent miss.** The default trailing content is a **channel avatar / facepile**.
    If the reference shows **action icons** there (call, huddle, search, AI, overflow) or **nothing**,
    you must **override `ChannelHeaderTrailingContent`** to render those icons (or an empty box) - leave
    it default and the avatar stays, which is almost never what the reference shows.
  - **Center may be a styled container, not bare text.** Some designs wrap the title+subtitle in a
    rounded/tinted pill or a tappable search-like box (Slack). If so, reproduce that container in
    `ChannelHeaderCenterContent`, not just the text.
  - **Leading** may swap the back-arrow's glyph/weight or add an avatar beside it.
  It is one of the most visible regions and a common silent miss - and the message header
  (`ChannelHeader*`) is a DIFFERENT slot from the channel-list header (`ChannelListHeader*`); match each
  on its own screen.
- `ChannelListItemContent` (+ `ChannelItemLeading/Center/TrailingContent`) - **decompose a list row as
  thoroughly as a message row.** The default draws avatar (leading) + name & last-message preview
  (center) + timestamp & unread badge (trailing); override one and reproduce the rest (composite-slot
  rule). The recurring miss is treating every row as `# + name` and dropping the preview, the trailing
  badge/facepile, and the read-state weight.
  - **Channel vs DM (do NOT `#`-prefix a DM).** A workplace design marks **channels** with a `#` (public)
    or lock (private) glyph, but a **direct message** with the other member's **avatar + presence dot** -
    never a `#`. Decide per row from the channel's data, not by assuming: a DM is typically a channel
    with **no set `name`** / a small distinct member set (`channel.members`), whereas a named channel has
    a `name`. Branch in `ChannelItemLeadingContent` (glyph vs member avatar) and in the name shown
    (`channelNameFormatter` feeds BOTH header and list - make it fall back to the other member's name for
    a nameless DM, and do not inject a literal `#`; add the `#`/lock glyph in the leading slot, not into
    the formatted name). Verify with the seeded data, which mixes channels and people.
  - **Sections are a data/query concern, not a slot.** Stream's channel list is a single sorted query;
    it does not natively render custom named groups (favorites / unreads / categories). If the reference
    groups rows under section headers, that requires **separate filtered `queryChannels` calls** (one per
    section) or a custom list - beyond theming. Reproduce the row **style** faithfully, and if true
    sectioning is out of scope for a styling pass, **say so** rather than faking one flat list as if it
    matched.

---

## Step 3: Grounding (do not guess slot signatures)

Ground every signature against **the version the app pins** - most of the ~196 slots are not
individually documented. Find the pinned version (`io.getstream:stream-chat-android-compose:<version>`
in the app's Gradle files), then read that version's source: on GitHub at the matching tag, or a local
checkout at that **tag** (not a moving branch).

```bash
# GitHub: github.com/GetStream/stream-chat-android/tree/<version>/stream-chat-android-compose/...
# or in a local checkout, read the pinned tag:
BASE=stream-chat-android-compose/src/main/java/io/getstream/chat/android/compose/ui/theme
git -C <checkout> show <version>:$BASE/ChatComponentFactory.kt        # every slot + default @Composable body
git -C <checkout> show <version>:$BASE/ChatComponentFactoryParams.kt  # the *Params fields each slot receives
git -C <checkout> show <version>:$BASE/StreamDesign.kt                # color + typography tokens
```

Always read a slot's default `@Composable` body before overriding it (Step 2.5) and its `*Params` fields
(you usually have more state than you think - see the note under Step 2). **The SDK renames APIs across
major versions** (screens, menu/actions components, config classes, and per-slot arguments moved into
`*Params`). If the source you read disagrees with the names in this doc, you are reading a different
version than the app pins - trust the pinned version's source and follow that.

---

## Step 4: Build the customization

Wire the axes at the app's existing `ChatTheme(...)` call site (e.g. inside `ChannelActivity` /
`ChannelsActivity`) - **do not** change the app's entry point or navigation (Project ownership, below).

```kotlin
val colors = if (isSystemInDarkTheme()) StreamDesign.Colors.defaultDark() else StreamDesign.Colors.default()
    .copy(accentPrimary = brandAccent, backgroundCoreApp = sampledSurface /* semantic surfaces stay adaptive */)

val factory = object : ChatComponentFactory {
    // Override ONLY the slots the decomposition flagged; read each default body first (Step 2.5).
    @Composable
    override fun MessageBubble(params: MessageBubbleParams) { /* custom fill/shape/tail; reproduce content */ }
    @Composable
    override fun MessageListBackground(params: MessageListBackgroundParams) { /* wallpaper */ }
    @Composable
    override fun RowScope.MessageComposerLeadingContent(params: MessageComposerLeadingContentParams) { /* + button */ }
}

ChatTheme(
    colors = colors,
    typography = StreamDesign.Typography.default(fontFamily = brandFont),
    componentFactory = factory,
    config = ChatUiConfig(/* composer.floatingStyleEnabled, audioRecordingEnabled, ... */),
    channelNameFormatter = customNameFormatter,       // if the header/list title needs it
    messageAlignmentProvider = alignmentProvider,      // if left-aligning (livestream/open)
) { /* existing ChannelScreen / ChannelsScreen content */ }
```

Reproduce the sub-parts of any composite slot you override (Step 2.5). Do not ship a root that opens one
channel directly - that is a verification scaffold only (Step 5).

---

## Step 5: Verify against the reference - region by region (mandatory)

A match is **not done** until the app builds, runs, and the result is compared to the reference.
Presence-and-color is not enough; verify **size, position, and proportion** too.

1. **Seed data that triggers every customized region.** An empty/one-message channel hides exactly the
   elements that get dropped. Ensure visible: an **incoming and an outgoing** message; a run of 3+
   consecutive messages from one author (grouping + avatar rule); a photo album; reactions; a reply;
   long multi-line text; enough history for a date separator.
   **A region the data cannot populate is UNVERIFIED, not PASS ("data-limited" != matched).** If the
   reference shows member avatars but the seeded users have no photo URL, a member facepile / "N online"
   count / huddle badge / reactions the seed lacks, or a section the query doesn't return - you have NOT
   verified that region's layout. Two honest options: (a) **seed the data** so the region actually
   renders (add an image URL, a reaction, more members) and verify it, or (b) mark it **data-limited**
   in the comparison table with what's missing. Never green-tick a region you couldn't see because the
   data was thin, and never confuse a **data** gap (missing avatar image) with a **layout** gap (avatar
   in the wrong place) - say which it is.
2. **Build, install, open the real message screen, screenshot it.**
   ```bash
   ./gradlew :app:installDebug
   adb shell am start -n <pkg>/<launcher-activity>
   # navigate to a channel (adb shell input tap <x> <y> on a channel row, or a throwaway direct-open
   # scaffold you DELETE afterwards), then:
   adb exec-out screencap -p > result.png
   adb shell wm density        # for px -> dp
   ```
   Verifying only the channel list does not verify the message screen. If you add a temporary
   direct-open scaffold to reach the screen, it is **throwaway: delete it before delivery** (not
   disable - remove the code, the extra, the dead branch) and re-verify on the real navigation path.
3. **Build a comparison table.** For each Step-1 region: target attribute (size/position/color/presence)
   -> what rendered -> PASS / FAIL. Walk the whole checklist; do not stop at the regions that look right.
4. **Re-check the silently-lost elements** every time: the author **avatar on incoming messages** +
   grouping; the **header** height/alignment/title (and that a *different* channel shows its own name -
   not a hardcoded one); the **composer in BOTH states** (at rest: camera/mic; typing: send).
   High-variance regions to confirm explicitly (each has bitten a real run): (a) **header customized**,
   not left at the centered-title default; (b) **accent = the exact sampled hue** with a full `brand`
   scale (rendered hex == reference hex), not a washed-out `accentPrimary`-only guess; (c) **metadata (timestamp +
   delivery/read status) positioned as the reference shows it** - Stream defaults to BELOW the bubble,
   so if the reference places it inside the bubble, lay it out inside; (d) no metadata/text **overlap**
   and correct bubble **content padding** on a **short** message; (e) **composer matches the reference AND
   looks level on its own** - row count correct (multi-row -> rebuilt as a Column, not the default single
   row); every element **vertically centered** (no icon sitting low against the input - the bottom-align
   trap); and the input field **shape AND border** match (if the reference field has no stroke, the SDK's
   baked-in border/pill is gone - check this explicitly in **dark mode**, where a stray light stroke is
   the classic last mismatch on an otherwise-close screen); and the composer is a **single controlled
   height** with the placeholder's left inset matching the reference (the center content's insets/min-height
   not doubled by the wrapper); (f) **message header trailing** shows the
   reference's action icons
   (or nothing), NOT the default channel avatar/facepile - and the center matches (pill/container if the
   reference has one); (g) **channel-list rows fully decomposed** - preview/trailing/read-state present
   per the reference, and **DMs show a member avatar (not a `#`)** while channels show `#`/lock. Check on
   the seeded data, which mixes channels and people.
5. **Iterate until every region passes.** Fix, rebuild, re-screenshot. Do not declare done on the first
   screenshot.
6. If you genuinely cannot build/run, say so plainly and list which regions are implemented-but-unverified
   - never imply a match you did not see.
7. **Do not deliver with a region left at its default and call it a "known gap."** Every region in the
   Step-1 checklist - the composer especially - must be implemented to match. Report something as
   unmatched only when it is genuinely impossible (say what + why), never because it is more effort.

---

## Project ownership (rules)

- **Do not scaffold a new app.** If there is no Android project, tell the user to create one in Android
  Studio first. This skill customizes an **existing** Stream Compose integration
  (channel list -> message screen).
- **Do not change the app's entry point or navigation** unless asked. "Make the channel look like X" is a
  styling request. Do not make the app open one hardcoded channel directly as shipped behavior - that is
  an architecture change and it hides header/navigation bugs.
- **Preserve the app's structure** - do not convert XML to Compose or restructure navigation to match a
  design. Match the design inside the existing screens.
