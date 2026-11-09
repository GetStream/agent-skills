# Matching a reference design

Run this when the request carries a target appearance - a screenshot, a Figma frame, or
"make it look like WhatsApp / Slack / <app>". A reference design is a **checklist of
regions, not a color tweak**: every header, row, bubble, bar, sheet, and tile is a thing to
reproduce, and most differ from Stream's defaults structurally, not just by color.

A match is claimed only from a simulator screenshot captured after the last edit and
compared against the reference. Code that "should look right" is a guess.

The per-region work parallelizes well (spec one region per agent, build regions
concurrently) if the harness supports it - your call. Persist the reference images and the
spec to files first: attachments and conversation context don't reach subagents, and long
runs compact.

## Read the reference

- **Figma link, no exports:** you can't authenticate to Figma - ask for a PNG export per
  frame; never guess a design from a URL or an app's name.
- **Scale:** phone screenshots are 2x or 3x, and RN style values are points.
  `scale = image px width / device point width` (`sips -g pixelWidth ref.png`: 1179 px at
  3x is 393 pt). Divide every dimension measured off the image by it; never enter raw
  pixels as style values.
- **Device** is a spec field: run the simulator whose point width matches the reference
  (`xcrun simctl list devicetypes`; a 393 pt reference is not a 402 pt device) - another
  width rewraps text and moves every measurement. A Figma frame -> its declared size.
- **A running app as the reference** (a migration's original, "match our old app"): run it
  on the same simulator and capture the states you need while it still runs - long-press
  menu, attachment sheet, keyboard up, a thread. Values read from its source are intended,
  not verified, and a theme file carries no layout: confirm structure against its pixels.
- **Sketch / wireframe:** match structure only; colors come from the theme, never sampled
  from pencil.

## Write the spec

Convert the reference into a written spec file before building:

- **Name every region** - header, list row, bubble, composer, sheet, tile, card. An
  unnamed region gets silently dropped.
- **Sample, don't guess:** the hex of each surface; dimensions measured off the image and
  divided by scale - never invented round numbers (16/24/44). Controls almost always
  measure smaller than you'd guess, often smaller than the SDK default, and the input gets
  what's left after the buttons, so oversized buttons shrink it.
- **Sample every fill at >=2 points** (top + bottom): one sample of a gradient returns its
  midpoint, which reads as a plausible flat color. Samples differing beyond ~+/-3 per
  channel mean a gradient (record stops and direction) or a texture (a wallpaper pattern
  is a tiled image). Sample small glyphs such as read ticks at their core, away from photo
  attachments of a similar hue.
- **Transcribe exact strings and glyphs:** the composer placeholder verbatim ("Message",
  not the SDK's "Send a message"), header title and subtitle, empty-state copy, each
  control's glyph, outline vs filled, and left/right order. Each text role (sender name,
  body, timestamp) has its own size and weight - record them separately.
- **Don't ship affordances the app can't back.** A control in the reference for a feature
  the app doesn't have (a call button in a chat-only header, a camera icon with no camera
  package) is either built for real or left out and reported - never a dead button.
- **Floating or docked composer, from the image:** wallpaper or messages continuously
  behind and around it (usually with a shadow) means floating; a separate bar or a seam
  where the list ends means docked. Ask only if the cues are genuinely ambiguous.
- **Design the states the reference doesn't show** - empty channel list, empty channel,
  loading, the long-press menu, the attachment picker, typing, the recorder, edit mode,
  dark mode if the app has it - extrapolated from the sampled tokens. An unthemed SDK
  default inside a matched design reads as broken, not neutral.
- **Threads not visible?** The replies indicator renders only on messages that have
  replies, so a screenshot rarely settles it. Threads stay on (Defaults to keep in
  SKILL.md) unless the user turns them off by name - then see "No threads" under Build.
- **Name the Stream concept behind every signal** - a signal you can't name is a region
  you'll drop:

| Signal in the image | Stream concept |
|---|---|
| Single/double tick, "seen" | Read + delivery receipts (`MessageStatus`) |
| Emoji pill with a count | Reactions (`ReactionListTop` / `ReactionListBottom`) |
| "N replies" under a message | Thread (`MessageReplies`) |
| Mini-quote block above a message | Quoted reply (`Reply`) |
| Image grid / file card / waveform | Attachments (`Gallery`, `FileAttachment`, `AudioAttachment`) |
| Stacked same-author bubbles, one avatar | Message grouping (`getMessageGroupStyle`) |
| Floating "Today" pill | Date separator (`StickyHeader`, `InlineDateSeparator`) |
| Bold row + badge in the list | Unread state (`ChannelPreviewUnreadCount`) |
| Dot on an avatar | Presence |
| "X is typing..." | Typing indicator (`TypingIndicator`) |
| Pill composer over the messages | `messageInputFloating` on `<Channel>` |
| Mic at rest, send while typing | `OutputButtons` |
| Tiles over a photo grid below the composer | `AttachmentPicker` |
| Equal grid of tiles | `CallContent` `layout="grid"` |
| One large tile + filmstrip | `CallContent` `layout="spotlight"` |
| Small draggable self-view | `FloatingParticipantView` |
| Mic-slash / colored ring on a tile | `ParticipantLabel` mute icon / speaking highlight |
| Circular buttons along the bottom | `CallControls` |
| "LIVE" badge + viewer count | `HostLivestream` / `ViewerLivestream` top view |
| Avatar + name + time + text card | Feeds activity (bespoke) |
| Heart / speech-bubble / bookmark + count | Activity reaction / comments / bookmark (bespoke) |
| "Follow" button | Follow graph (bespoke) |

## Route each region

Pick the cheapest mechanism that reaches the design:

1. **Theming** - one `DeepPartial<Theme>` passed to both `<OverlayProvider value={{ style }}>`
   and `<Chat style={style}>`: each builds its own theme, and the overlay (long-press menu,
   gallery, sheets) reads only the first. Colors, fonts, padding, radii, and sizes live
   here. The SDK switches its own semantics with the OS appearance, but your `semantics`
   literals apply in both modes: build two palettes and pick one with `useColorScheme()`.
   Overrides don't cascade - yours merge after the SDK resolves its token references, so
   `accentPrimary` doesn't retint tokens defined from it (`buttonPrimaryBg` - the send
   button - `chatTextMention`, `badgeBgPrimary`, `chatWaveformBarPlaying`). Set each
   token you need as a hex literal; a `$token` string in your style is never resolved.
   Video: one theme on `<StreamVideo style={...}>`.
2. **Injection** - your component for one slot through a single
   `<WithComponents overrides={{ ... }}>` above the navigator; a component passed as a
   `<Channel>` prop is silently ignored. The slots are `DEFAULT_COMPONENTS` plus
   `OptionalComponentOverrides` in the core's `contexts/componentsContext/defaultComponents.ts`.
   The optional ones (`MessageContentTopView` / `BottomView` / `LeadingView` /
   `TrailingView`, `MessageSpacer`, `MessageText`, `Input`) have no default, so grepping
   only the defaults map reports them missing. A host imported directly
   (`AttachmentPicker`) still resolves its children from context - grep its
   `useComponentsContext()` destructure before calling a region fixed. Overrides are read
   once at mount (SKILL.md, Chat), so an override's colors come from `useTheme()` inside
   it, not from a palette variable it closes over. Video: slot props on
   `CallContent` / `ParticipantView` (a component, or `null` to hide).
3. **Bespoke** - a build on SDK hooks and state. All Feeds UI is bespoke: Feeds has no
   prebuilt RN components.

**Replacing a prebuilt region means inheriting everything it drew.** Defaults to keep in
SKILL.md lists what a custom message and a custom composer owe. Beyond those:

- A custom channel preview: unread count, last message + timestamp, delivery status,
  muted/pinned state, and the tap. The slot gets `{ channel, lastMessage, unread, muted,
  pinned }`; `onSelect` comes from `useChannelsContext()` - read from props it no-ops every
  row tap and still passes every screenshot.
- A custom composer: the `AttachmentPicker` toggle and previews (see Build),
  `OutputButtons` (send, mic, edit, cooldown, and AI stop all swap there), and audio
  recording when enabled.
- The channel header is app-owned (navigation header, or a view inside `<Channel>`): title
  and avatar from channel state, presence or member count, typing, back navigation.
- Custom call controls: mic/camera toggle state, flip, hang-up. A custom participant tile:
  name, mute indicator, video-off fallback, speaking highlight, network quality,
  screenshare.

Reproduce each or mark it N/A with the design reason - never silently drop one.

**Composer structure test.** Floating is a prop - `messageInputFloating` on `<Channel>` -
never a translucent or rounded fill painted on a docked composer; settle it before any
color work. Then count rows. `MessageComposer` renders one row:
`MessageComposerLeadingView` (attach) | the pill (`InputView` + `MessageInputTrailingView`,
which holds `OutputButtons`) | `MessageComposerTrailingView` (empty). A one-row reference is
customized within that row - for send/mic outside the pill, render the SDK's
`MessageInputTrailingView` from your `MessageComposerTrailingView` override and null the
`MessageInputTrailingView` slot (keeps its recording-state handling). A 2+-row reference
(input above a toolbar) can't come from restyling: override the optional `Input` slot, which
replaces everything inside the composer wrapper, as a column reusing `InputView`,
`AttachButton`, and `OutputButtons`.

## Build

- Defaults to keep in SKILL.md applies: a feature the reference doesn't show (reactions,
  threads, read status, the attachment picker) stays on, styled to match the spec.
- **Decide every native capability package before the first native build** - each later
  one costs another rebuild. Expo: `expo-media-library` (without it `disableAttachmentPicker`
  defaults to `true` and the picker never opens), `expo-image-picker`,
  `expo-document-picker`, `expo-audio`, `expo-video`; RN CLI equivalents on the
  Installation page.
- **Composer surfaces.** Docked, the bar is `messageComposer.wrapper` (default fill
  `backgroundCoreElevation1` plus a top border, through the safe area); `container` is the
  inner row - coloring it paints a band around the controls. With `messageInputFloating`
  the theme's `wrapper` is dropped: style `floatingWrapper` (the outer absolute view),
  `inputBoxWrapper` (the pill), and `inputFloatingContainer` (floating-only pill styles).
- **Grow the pill with symmetric `messageComposer.inputBox` padding** (defaults 12 + 12
  around lineHeight 20). A `minHeight` on `inputBoxWrapper` puts the extra height below a
  single line - the pill's inner column lays out top down.
- **Send and mic are `OutputButtons`.** Send is enabled only with text or a staged
  attachment; at rest the slot shows the mic only with `audioRecordingEnabled` (default
  `false`). Send is a primary solid button (`buttonPrimaryBg`); attach a secondary outline
  button (`buttonSecondaryBorder`) - that ring is the SDK look, so a borderless `+` is a
  custom `AttachButton`.
- **A custom `+` (the `AttachButton` slot) replicates the SDK toggle**, which lives inside
  `AttachButton` and on no hook - a plain open/close loses the refocus. Honor
  `handleAttachButtonPress` first if the app sets it:
  ```tsx
  const { closeAttachmentPicker, focusInputOnPickerClose, inputBoxRef, openAttachmentPicker } =
    useMessageInputContext();
  const { attachmentPickerStore } = useAttachmentPickerContext();
  const toggle = () => {
    if (attachmentPickerStore.state.getLatestValue().selectedPicker) {
      if (focusInputOnPickerClose) inputBoxRef.current?.focus(); // keyboard replaces the sheet
      else closeAttachmentPicker();
    } else openAttachmentPicker();
  };
  ```
  The parent `InputButtons` rotates whatever `AttachButton` renders by 45 degrees while
  the picker is open: a bare `+` becomes an x, a framed icon (plus in a rounded square) a
  diamond. To keep it upright, override `MessageComposerLeadingView` instead. Picker
  customization itself is in the appendix.
- **Recorder tints** come from `semantics.accentPrimary` and `chatWaveformBar`
  (`chatWaveformBarPlaying` for played audio); the accent alone leaves the waveform default.
- **Timestamp and receipts inside the bubble** are structural: render them in
  `MessageContentBottomView` (own line) or `MessageContentTrailingView` (beside the text)
  and set `MessageFooter` to `() => null`, or they show twice. These slots have no padding:
  add the body's horizontal and bottom padding and `alignSelf: 'flex-end'`. Reuse
  `MessageStatus` for the ticks. Beside the bubble, outside it, is the `MessageSpacer` slot
  (same `MessageFooter` null).
- **Keyboard and picker insets on `<Channel>`** follow "Keyboard and picker insets" in
  SKILL.md. One case no inset fixes: an app-owned tab bar under a floating composer (the
  picker is anchored to the root) - hide the tab bar while
  `useAttachmentPickerState().selectedPicker` is set.
- **No threads** (only when the user turned them off by name): hiding the UI isn't enough.
  `getstream api UpdateChannelType --name messaging --request '{"replies":false}'` (check
  `-h` for the body) - app-wide, so on an app with real data confirm with the user first.
  The custom message's replies indicator is then N/A.

## Verify

Verify on a simulator, not by reading your own code - every round, until the screenshot and
the reference read as the same screen. The run loop, polling, state scaffolds, and
appearance flips are in simulator-verification.md.

1. **Populate states without polluting the user's data:** two test users upserted first
   (`getstream api UpdateUsers` - Stream doesn't create members on the fly), then one
   channel created for the check (`GetOrCreateChannel` with both as members), never the
   user's real channels; ask before writing to an app with real data. As each user,
   `SendMessage` (`user_id`) and `SendReaction`: incoming and outgoing, a 3+ same-author
   run, a one-word message and a nearly-full-width last line (catches clipped in-bubble metadata), a long
   multi-line message, an image album, a reaction, a quoted reply, a thread reply, and
   `MarkRead` for receipts. All of it is stamped now: only a "Today" separator appears.
2. **Capture each screen** at rest - channel list, channel, thread - then **drive the
   interaction states**, which don't exist at rest: long-press menu, reaction picker,
   thread, attachment picker open, recorder, typing (send visible), a multi-line draft (the
   pill must grow), edit mode. `setText` doesn't raise the keyboard: focus the input to
   check keyboard avoidance.
3. **Check structure before color.** Floating vs docked matches; the composer fill runs
   edge to edge and through the safe area (sample the margin around the buttons); a single
   line sits centered in the pill; in-bubble metadata isn't clipped and the outside footer
   is gone; the open picker sits flush under the composer.
4. **Dark mode**, if the app has it: `WithComponents` overrides don't follow a runtime
   appearance flip - cold-launch each mode. Pinned brand colors (bubbles, accent, ticks)
   stay identical; structural surfaces (list background, composer, borders) flip.
5. **Screenshots don't test taps.** Drive every custom handler: the preview row tap, the
   custom `+` open and close, each custom menu row - fire the thread and edit rows
   themselves.
6. **Fix everything found, re-capture once per round** - not once per tweak - and stop
   when a round stops finding differences.
7. **Exit honestly.** Report what didn't match with both values (spec vs rendered). If no
   capture was possible, the work is UNVERIFIED - say so; never claim a match you didn't
   see. Delete the test channel (`DeleteChannel`, `hard_delete`), the test users, and every
   scaffold.

## Appendix: Chat RN v9 reskin cheat-sheet

Written for stream-chat-react-native v9 (checked against `stream-chat-react-native-core`
9.12.1 and `@stream-io/video-react-native-sdk` 1.47.1). On another major, check each name
against that major's theming docs and the migration guide for the pair (chat-versions.md)
before reusing it. The installed core source (`contexts/themeContext/utils/theme.ts`,
`contexts/componentsContext/defaultComponents.ts`, the component files) outranks this
table and the docs.

**Theme keys that matter**

| Region | Key |
|---|---|
| Bubble fill / text | `semantics.chatBgOutgoing`, `chatBgIncoming`, `chatTextOutgoing`, `chatTextIncoming` |
| Read tick / delivered and sent ticks | `semantics.accentPrimary` / `chatTextTimestamp`; `messageItemView.status.checkAllIcon` styles read AND delivered alike |
| Send / attach / mic buttons | `semantics.buttonPrimaryBg`, `buttonPrimaryTextOnAccent` / `buttonSecondaryBorder`, `buttonSecondaryText` |
| Row side gutter | top-level `screenPadding` (default 16), not `messageList.contentContainer` |
| Bubble corners | `messageItemView.content.container` corner keys (below) |
| Text-only bubble height | `messageItemView.content.markdown.paragraph` and `paragraphCenter` `marginTop` / `marginBottom` (default 8 each) - the SDK zeroes the content padding for text-only messages, so padding added on `content.contentContainer` stacks on top and overshoots |
| Body font | `content.markdown.text`; `fontSize` / `lineHeight` on `paragraph` also reach emoji-only messages and shrink the jumbo emoji |
| Composer | `messageComposer.wrapper`, `floatingWrapper`, `container`, `inputBoxWrapper`, `inputBox`, `inputFloatingContainer`, `focusedInputBoxContainer` |
| Picker selection bar | top-level `attachmentSelectionBar.container` |
| Avatar shape / border | `avatar.container`, `avatar.border`; size is the component's `size` prop |
| Own messages beyond colors | `myMessageTheme` on `<Channel>` |

**Keys and slots that type-check but don't render**

| Key / slot | Why | Instead |
|---|---|---|
| `avatar.container` `width` / `height` | the `size` prop's dimensions are applied after it | `size` prop, or `style` on the avatar |
| `messageComposer.micButtonContainer.backgroundColor` | the button's Reanimated animated style writes `backgroundColor` and wins | fill a wrapper around the button |
| Mic icon size | `icons.Mic` renders at a fixed 20x20 | override `icons.Mic` through `WithComponents` |
| `messageComposer.wrapper` with `messageInputFloating` | the floating branch uses the default wrapper style only | `floatingWrapper`, `inputBoxWrapper` |
| `messageComposer.attachButton`, `sendButton`, `editButton`, `attachmentSelectionBar` | never read | `attachButtonContainer`, `sendButtonContainer`, `editButtonContainer`, top-level `attachmentSelectionBar`, `button*` semantics |
| `content.container.borderRadius` alone | both bottom corners are emitted per corner, which beats it | set all four corner keys |
| `components.messageBubbleRadius*` | a static import, not on the `Theme` type | corner keys on `content.container` |
| `MessageInputLeadingView`, `MessageInputFooterView` slots | in `DEFAULT_COMPONENTS`, never rendered by `MessageComposer` | `MessageComposerLeadingView`, `MessageInputHeaderView`, or `Input` |

**Bubble radius and tail.** The near bottom corner (right for own, left for others) gets
`messageBubbleRadiusTail` on `single` / `bottom` group positions - the default tail. A
corner key on `content.container` (or `containerInner`, which wins by order) applies to
every group position, so it also removes the tail. Measure every corner of the reference:
many designs round all four and protrude a tail instead.

**Slots and props**

| Need | Mechanism |
|---|---|
| All rows on one side (workplace style) | `forceAlignMessages` on `<Channel>` (`'left'` / `'right'`) |
| Text before attachments | `messageContentOrder` on `<Channel>` (default ends with `'text'`) |
| Reactions below the bubble | `reactionListPosition='bottom'` (default `'top'`); both lists render outside the bubble |
| Reactions inside the bubble | render them in `MessageContentBottomView`; set `ReactionListTop` and `ReactionListBottom` to `() => null` |
| Mic at rest | `audioRecordingEnabled` on `<Channel>` (default `false`) |
| Ungrouped messages | `getMessageGroupStyle={() => ['single']}`, not `enableMessageGroupingByUser={false}` (that empties the group styles and drops the per-message spacing); `'single'` also puts the tail on every bubble |
| Avatar on every incoming message | override `MessageAuthor` (mounted for incoming rows only) |
| Composer placeholder | `additionalTextInputProps={{ placeholder: 'Message' }}` on `<Channel>`; a `Streami18n` on `<Chat i18nInstance>` for a full string sweep |
| Custom reaction set | extend the exported `reactionData`; picker entries need `isMain: true` |

**Long-press menu wiring.** Another presentation than the in-place overlay (a bottom
sheet) is `onLongPressMessage` on `<Channel>`; `messageActions` changes only the overlay's
contents. Reuse the payload's `actionHandlers` (copy, delete, quoted reply, mark unread,
pin, resend, toggle reaction) for exact SDK behavior, except two:

- `threadReply` is the optional `<Channel handleThreadReply>` prop, `undefined` by default.
  Call `openThread(message)` from `useThreadContext()`, then navigate to your thread
  screen. On a parent with no replies yet, its fire-and-forget `markRead` rejects ("Can't
  find thread") - a harmless warning, not a reason to block starting a thread.
- `editMessage` waits for the keyboard, which a presented Modal blocks, so it no-ops.
  Close the Modal, call `setEditingState(message)` from `useMessageComposerAPIContext()`,
  then focus `useMessageInputContext().inputBoxRef`.

**Attachment picker.**

- Height stands in for the keyboard: keep `attachmentPickerBottomSheetHeight` near its
  default 333 - the simulator window hides an oversized sheet.
- Bar at the bottom: null `AttachmentPickerSelectionBar` and render the gallery plus your
  bar from an `AttachmentPickerContent` override (absolutely positioned if it floats over
  the gallery). Custom tabs call `attachmentPickerStore.setSelectedPicker(...)` or
  `useMessageInputContext().pickFile()`; show only tabs the app backs.
- The one shape that isn't `AttachmentPicker`: a dimmed modal list of rows ("Take a photo",
  "Files") with no gallery. Set `disableAttachmentPicker` and `handleAttachButtonPress` on
  `<Channel>` (no sheet, lift, or rotation); each row calls `takeAndUploadImage()`,
  `pickAndUploadImageFromNativePicker()`, or `pickFile()` from `useMessageInputContext()`,
  so uploads, previews, and permissions stay SDK-owned.

**Video.** The theme is global (`<StreamVideo style>`: `callControls`, `participantView`,
`participantLabel`, `floatingParticipantsView`, ...). `CallContent` `layout` is `'grid'`
(default) or `'spotlight'`; an ongoing screenshare forces spotlight.
`FloatingParticipantView` shows only in grid, outside PiP, with 1-2 remote participants.
The default `CallControls` row is fixed (video, audio, flip, hang-up): to add or reorder
buttons, replace it through the `CallControls` prop with the exported buttons. The speaking
ring is a theme key, not a slot: a 2 pt border tinted `colors.buttonPrimary` on any
participant while `isSpeaking` (not only the dominant speaker; never on a screenshare
tile), restyled via `participantView.highlightedContainer`. RN ships no camera/mic
device-picker component: a device dropdown is a custom build on `call.camera` /
`call.microphone`, or a flagged gap.

**Feeds.** No theme and no slots: every region is your component on the Feeds state hooks
and `client` / `feed` methods. Take hook and method names from the Feeds RN docs and the
installed `@stream-io/feeds-react-native-sdk`.
