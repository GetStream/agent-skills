# Matching a reference design

Run this when the request carries a target appearance - a screenshot, a Figma frame, or
"make it look like WhatsApp / Slack / <app>". A reference design is a **checklist of
regions, not a color tweak**: every rail, bar, row, tile, and card is a thing to
reproduce, and most differ from Stream's defaults structurally, not just by color.

A match is claimed only from a rendered screenshot captured after the last edit and
compared against the reference. Code that "should look right" is a guess.

The per-region work parallelizes well (spec one region per agent, build regions
concurrently) if the harness supports it - your call. Persist the reference images and
the spec to files first: attachments and conversation context don't reach subagents, and
long runs compact.

## Read the reference

- **Figma link, no exports:** you can't authenticate to Figma - ask for a PNG export per
  frame; never guess a design from a URL or an app's name.
- **Scale:** reference screenshots are usually 2-3x. `scale = image px width / CSS
  viewport width`; divide every dimension you measure off the image by it. Never enter
  raw image pixels as CSS pixels.
- **Viewport** is a spec field - derive it from the reference: portrait phone screenshot ->
  390x844, ~3:4 tablet -> 820x1180, desktop window chrome -> 1440x900, a Figma frame -> its
  declared size. Capture at exactly that size.
- **A running app as the reference** (a migration's original, "match our old app"): probe
  it instead of sampling - `getComputedStyle` / `getBoundingClientRect` on its DOM return
  exact values - and drive its states while it still runs.
- **Mobile screenshot, web deliverable** - the highest-leverage decision, settle it with
  the user: reproduce the phone layout at phone width (often inside a phone-frame
  element - note Stream's fullscreen image viewer renders to the document root and
  escapes a phone frame unless scoped), or adapt to the app's desktop layout (WhatsApp ->
  WhatsApp Web's two-pane shell).
- **Sketch / wireframe:** match structure only; colors come from the theme, never sampled
  from pencil.

## Write the spec

Convert the reference into a written spec file before building:

- **Name every region** - column, bar, rail, tile, card. An unnamed region gets silently
  dropped.
- **Sample, don't guess:** the hex of each surface; dimensions measured off the image and
  divided by scale - never invented round numbers (16/24/32). Controls almost always
  measure smaller than you'd guess.
- **Sample every fill at >=2 points** (top + bottom): one sample of a gradient returns its
  midpoint, which reads as a plausible flat color - the most common silent miss. Samples
  differing beyond ~+/-3 per channel mean a gradient: record the stops and direction. The
  same pass flags shadows and textures. Brand surfaces (bubbles, buttons, avatars) are
  the usual gradient carriers.
- **Transcribe exact strings and glyphs:** the composer placeholder verbatim ("Message",
  not the SDK's "Send a message"), button labels, empty-state copy, each control's glyph
  and left/right order, the composer's row count. Cheapest, most-dropped fidelity wins.
- **Design the states the reference doesn't show** - empty channel list, empty message
  list, loading, the hover actions surface, dialogs - extrapolated from the sampled
  tokens. An unthemed SDK default inside a matched design reads as broken, not neutral.
- **Name the Stream concept behind every signal** - a signal you can't name is a region
  you'll drop:

| Signal in the image | Stream concept |
|---|---|
| Single/double tick, "seen" | Read + delivery receipts |
| Emoji pill with a count | Reactions |
| "N replies" under a message | Thread |
| Mini-quote block above a message | Quoted reply |
| Image grid / file card / waveform | Attachments |
| Stacked same-author bubbles, one avatar | Message grouping |
| Floating "Today" pill | Date separator |
| Bold row + badge in the sidebar | Unread state |
| Dot on an avatar | Presence |
| "X is typing..." | Typing indicator |
| Hover "..." on a message | Message actions |
| Equal grid of tiles | `PaginatedGridLayout` |
| One large tile + filmstrip | `SpeakerLayout` |
| Mic-slash / colored ring on a tile | Mute indicator / dominant speaker |
| Circular buttons along the bottom | `CallControls` |
| Avatar + name + time + text card | Feeds activity card |
| Heart / speech-bubble / bookmark + count | Activity reaction / comments / bookmark |
| "Follow" button | Follow graph |

## Route each region

Pick the cheapest mechanism that reaches the design:

1. **Theming** - `str-chat` CSS variables + component props; no custom component.
2. **Injection** - your own component for one region via the documented slots
   (`Message=` / `WithComponents`, `ChannelPreviewUI`, the `<Channel>` header slot).
3. **Bespoke** - a headless build. All Feeds UI is bespoke by definition.

**Replacing a prebuilt region means inheriting everything it drew.** A custom message row
owes: attachments, reactions, quoted parent, receipts, thread indicator, grouping,
edited/deleted states. A custom channel preview: unread, presence, last message +
timestamp. A custom composer: send, attach, emoji, voice recording, submit handling. A
custom channel header: typing indicator, presence / member count, back navigation. A
custom call layout or controls: participant labels, mute state (`hasAudio`/`hasVideo`),
screenshare, dominant speaker, join/leave.
Reproduce each or mark it N/A with the design reason - never silently drop one. A custom
channel rail still renders through `<ChannelList>`'s `renderChannels` / `ChannelListUI`
injection - keep it the query/watch/event owner rather than mirroring the list into app
state. And never wrap a message bubble in `<button>` / `<a>`: attachments, link previews,
and polls render their own interactive elements, and the resulting nested-interactive
markup breaks hydration and can stop attachments rendering - use a `<div>` with `onClick`.

**Composer row-count test:** `MessageComposer` renders one row (leading buttons | input |
trailing buttons). A one-row reference is customized within that row; a 2+-row reference
(the Slack/Discord shape) can't come from restyling - inject a `MessageComposerUI` built
as a flex column, reusing the SDK's textarea/send/attachment pieces.

## Build

- Reuse SDK pieces inside custom components (`MessageText`, `Attachment`, `Avatar`,
  `ParticipantView`) rather than rebuilding them.
- **Containers are fluid.** A rail measured at 320px is a proportion at the spec
  viewport, not `width: 320px` - use flex-basis / % / `clamp()` on wrappers; bare px only
  for intrinsic details (avatar, radius, gap, padding). Stream regions must fill their
  wrappers: the SDK caps the channel list at ~288px by default, and the message list must
  fill its pane and bottom-anchor short conversations.
- **Palette through sanctioned channels:** app chrome via the closest shadcn preset
  tokens; the chat surface via `str-chat` theming variables (confirm names against the
  docs and the installed CSS). Sampled brand colors may be pinned literals; chrome
  surfaces ride the adaptive light/dark tokens - a light hex pinned on chrome breaks dark
  mode.
- **The reference is the shell.** Drop chrome the reference doesn't show (a bare phone
  chat has no sidebar) and fill the viewport - no fixed-width chat strip floating on
  empty background.

## Verify

Verify with a browser, not by reading your own code - every round, until the screenshot
and the reference read as the same screen.

1. **Populate states with local fixtures - never seed the backend.** A dev-only,
   env-guarded view reached through the normal login, rendering the **real shipped
   shell** with fixture data injected. A hand-rolled wrapper reproduces different
   geometry and passes while production is broken (a flex-column stand-in hides the
   width collapse that only appears in the shipped flex-row). One exception:
   `ChannelList` is query-driven, so render your preview component against fixture
   channel objects inside the shipped rail geometry. Include the awkward states: a
   one-word message and a nearly-full-width last line (catches overlaid in-bubble
   metadata), a long multi-line draft (the input must grow), a same-author run, an
   attachment, a reaction, a quoted reply, the empty lists. For video: multiple tiles, a
   muted participant, a screenshare, a dominant speaker. For feeds: a card with reactions,
   comments, and an image.
   Building a fixture channel: `client.channel('messaging', 'fixture-1')`; stub its
   network methods (`watch`, `query`, `markRead`, `keystroke`, `sendMessage`) to no-ops so
   nothing hits the backend; set `channel.state.own_capabilities` (the composer and
   reactions don't render without them); inject messages with
   `channel.state.addMessagesSorted(msgs)` - guarded by
   `if (channel.state.messages.length === 0)`, because `client.channel()` is cached by cid
   and strict mode double-invokes, so an unguarded inject renders every message twice.
   Thread-open throws on a stubbed channel (the reply composer needs a real channel
   context) - verify the thread panel against a real channel instead.
2. **Capture** with in-session browser tooling, or install Playwright into a
   self-contained harness so the app's lockfile is untouched whatever its package
   manager:
   ```bash
   mkdir -p .design-verify && printf '{"private":true}\n' > .design-verify/package.json
   npm install --prefix .design-verify -D playwright
   .design-verify/node_modules/.bin/playwright install chromium
   ```
   Capture at the spec viewport. Gotchas: don't wait for `networkidle` - Stream holds a
   WebSocket open, the network never idles; wait for a rendered Stream selector instead.
   Force the scroll position (`scrollTop = scrollHeight` on
   `.str-chat__message-list-scroll`) - fixture messages fire no events, so auto-scroll is
   unreliable. Use Playwright's Chromium, not a bare OS `chrome --headless` (it often
   captures the splash screen). Disable the Next.js dev indicator (`devIndicators:
   false`) - it occludes the composer. Capture element crops of the high-detail regions
   (the composer, one message row, a quoted reply) alongside the full screen - detail is
   lost at full-page scale.
3. **Drive the interaction states** - they don't exist at rest: hover a message (the
   toolbar must not shift the bubble, and must stay in-viewport on the topmost message),
   open the thread panel, the reaction selector, the actions menu; stage an attachment;
   type the multi-line draft. Capture each.
4. **Probe computed styles** for the spec's color/type/dimension rows. Color probes must
   read `background-image` and `box-shadow` too - a CSS gradient lives in
   `background-image` with an empty `background-color`, so a color-only probe is blind to
   flat-vs-gradient. Check regions fill their parents (rect vs parent rect): a region
   collapsed to its default width passes every color check and is still wrong. If the app
   has dark mode, capture both themes - chrome still showing the light hex in dark is a
   miss.
5. **Fix everything found, re-capture once per round** - not once per tweak - and stop
   when a round stops finding differences.
6. **Exit honestly.** Report what didn't match with both values (spec vs rendered). If no
   capture was possible, the work is UNVERIFIED - say so; never claim a match you didn't
   see. Delete `.design-verify/` and the fixtures view when done.

## Appendix: Chat React v14 reskin cheat-sheet

Concrete starting points for the most common chat regions, so a reskin isn't
reverse-engineered from compiled CSS every time. Scope: `stream-chat-react` v14. The
installed `node_modules/stream-chat-react/dist/css/index.css` and the `.d.ts` under
`dist/types/` outrank this table and the docs - grep them to confirm any selector or
variable before relying on it.

**Global accent + sizing** - set once on `.str-chat` (or your app root):
```css
.str-chat {
  --str-chat__accent-primary: #0084ff;          /* buttons, links, read ticks, poll fills, checkboxes */
  --str-chat__message-max-width: 480px;          /* text bubbles */
  --str-chat__message-with-attachment-max-width: 340px;  /* attachments + POLLS */
  --str-chat__attachment-max-width: 340px;
}
```

**Message bubbles - scope the color to the TEXT, not the container.** The single most
common mistake: styling `.str-chat__message-bubble` paints the whole message container,
so polls, images, and other attachments inherit your bubble background/gradient. Style
the text element:
```css
/* OK - own text bubble only */
.str-chat__message--me .str-chat__message-text-inner { background: <brand>; color: #fff; }
/* WRONG - NOT this - bleeds onto polls/attachments */
/* .str-chat__message--me .str-chat__message-bubble { background: <brand>; } */
```

**Poll** (`.str-chat__poll`) - the native Poll is large and full-width and renders inside
a message bubble. To make it a compact card: constrain via the attachment-width vars
above, make the bubble transparent when it holds a poll, and give the poll its own
background:
```css
.str-chat__message-bubble:has(.str-chat__poll) { background: transparent; padding: 0; }
.str-chat__poll { max-width: 300px; border-radius: 18px; padding: 12px 14px; background: <card>; }
.str-chat__message--me .str-chat__poll { background: <brand>; color: #fff; }
```
Sub-parts: `.str-chat__poll-title`, `.str-chat__poll-option`,
`.str-chat__poll-option__votes-bar`, `.str-chat__poll-actions .str-chat__poll-action`.
The control type (radio selectors) and the action labels ("End Vote") are structural, not
themable - if the reference shows something else, inject `PollOptionSelector` /
`PollActions` via `WithComponents`.

**Composer** (`<MessageComposer>`):
- Placeholder: `additionalTextareaProps={{ placeholder: 'Enter message' }}` (default is
  "Send a message"). For a full string sweep use a `Streami18n` instance on
  `<Chat i18nInstance>`.
- Send button `.str-chat__send-button`; attachment button lives under
  `.str-chat__attachment-selector`. The attach button sits on the left by default -
  moving it is a layout override. The attach glyph swaps without rebuilding the selector:
  override `AttachmentSelectorInitiationButtonContents` (a `ComponentContext` slot, via
  `WithComponents`).
- Input sizing / rounding: the textarea wrapper is `.str-chat__textarea` (inner element:
  `.str-chat__textarea textarea`); the emoji-picker variant is
  `.str-chat__message-textarea-emoji-picker-container`.
  (`.str-chat__message-textarea-container` does not exist in v14.8 - grep the installed
  CSS.) The SDK textarea auto-grows: pass `minRows` / `maxRows` to `TextareaComposer` and
  let the wrapper flex to fill the row - a fixed-height input that clips a 3-line draft
  fails the growth check.
- Rebuilding `MessageComposerUI`? `useMessageComposerContext()` returns
  `{ handleSubmit, onPaste, recordingController, textareaRef }` - submit and voice
  recording without re-implementing either.

**Read receipts** - `readBy` from `useMessageContext()` is populated only for the
latest-read message by default; per-message ticks (WhatsApp-style blue checks on every
read row) need `returnAllReadData` on `<MessageList>` (or derive read state from
`channel.state.read`). Gray-ticks-everywhere-but-one-row is this, not CSS.

**Quoted reply** - renders inside the message bubble: `.str-chat__quoted-message-preview`
(`--own` modifier on your side) and `.str-chat__quoted-message-indicator`, with the
`--str-chat__quoted-message-bubble-background-color` variable for its fill. Style it as a
compact inset card (background + left accent bar + truncated text) - it is a repeat
offender for stray CSS; verify it with the quoted-reply fixture.

**Wallpaper / message-list background** - v14 scrolls the list inside
`.str-chat__message-list-scroll`; paint the wallpaper there (docs examples still target
`.str-chat__list`) so it covers the full scrollable pane. A wallpaper that stops where
the messages stop is a miss even when every width passes.

**Avatars** - Stream renders a single initial/image. Stacked group avatars are not
built-in - render them yourself in your custom channel-preview / header component from
`channel.state.members` (that component then owes its contract rows above).

**Theme (light/dark)** - pass `theme="str-chat__theme-light|dark"` to `<Chat>`; Stream's
variables are scoped under those classes. Keep your own app-chrome tokens on the adaptive
channels.

**Finding a selector you don't know:** grep the installed stylesheet -
`node_modules/stream-chat-react/dist/css/index.css` - for the feature name (`poll`,
`message-bubble`, `send-button`, `avatar`); it's the authority for the exact installed
version. Confirm class props from the `.d.ts` under `dist/types/`.
