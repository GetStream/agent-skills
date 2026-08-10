# Chat — region checklist + routing

Tier 2 of the design-match decomposition: channel list, message chrome, message row, reactions,
attachments, composer, plus deep-dives on the bubble radius, metadata inside the bubble, the
long-press menu, the composer render tree, Liquid Glass, and the attachment picker. The method — the
three axes, measuring sizes, sampling colours, the Step 3 verify loop — is in
[`design-matching.md`](design-matching.md); read that first, then walk **every row** below.

The **Route to** column names the *mechanism*. Confirm the exact theme key / slot / prop name in the
manifest-selected docs and the installed package, never from memory.

## Three axes of customization

Map each design difference to the cheapest axis that reaches it. Preference order: **Functional →
Theming → Layout / structure**.

| Axis | Mechanism | What it changes | What it CANNOT change |
|---|---|---|---|
| **Functional** | documented component props, channel config, SDK context hooks (`useMessageContext`…) | which actions/behaviors are enabled, what's interactive, send/edit/reaction/thread behavior | pure appearance (that's theming) |
| **Theming** | the `DeepPartial<Theme>` object passed to **both** `<OverlayProvider value={{ style }}>` **and** `<Chat style={…}>` ([Theming Blueprint](./CHAT-REACT-NATIVE-blueprints.md#theming-blueprint)) | colors, fonts, spacing, padding, border-radius, dimensions — *within the existing layout*. The RN theme object carries **both** colour **and** padding/dimension, so most reskins are theme-only | the structure: which views render, their arrangement, metadata inside vs below the bubble, which buttons the composer has |
| **Layout / structure** | component overrides via `WithComponents overrides={{ … }}` ([Component Override Blueprint](./CHAT-REACT-NATIVE-blueprints.md#component-override-blueprint)) | the actual views: extend or override parts of the UI | colours/fonts/spacing a theme key already reaches — don't replace a component to change a padding |

**A theme key that type-checks is NOT evidence that it renders.** `Theme` is a wide type and several
of its keys are dead or partly dead at runtime — the component overwrites them after the theme is
applied, drops them in one of its branches, or never reads them at all. The symptom reads as a stale
bundle. Before trusting any theme key for a region that matters, open the component in the installed
package and confirm the key reaches the rendered style, and check the
[confirmed-dead list](#dead-theme-keys) first.

**Two recurring mis-routings:**
- A **structural** difference solved with a **theming** token. Read receipts inside the bubble, a
  camera button in the composer, a timestamp overlaid on an image, an avatar on own messages → a
  component override, not a colour key.
- A **spacing / padding / radius** difference solved by **overriding a component**. In RN those live
  in the theme object; only override the component when the *arrangement* itself must change.

**RN-specific: the channel header is app-owned.** RN Chat has no `ChannelHeader` slot baked into
`Channel` — the nav header is **your** React Navigation `Stack.Screen options` / Expo Router header
(or a custom view above `MessageList`). Header differences route to the **navigation layer**, not the
theme: match its height, title, subtitle and trailing affordances there, and drive the title from
channel state, never a hardcoded literal.

---

**Channel list screen** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| List header | app-owned nav: title, actions, height | **App-owned** | React Navigation `Stack.Screen options` / Expo Router header — not a theme key |
| How many channel lists? | group vs 1:1 messages? | Layout | multiple `ChannelList`s with their own filter/sort options |
| Preview row | layout, avatar, unread badge, timestamp, empty/loading state, background | Theming (+ Layout) | `theme.channelPreview.*`; `ChannelList` `ChannelPreview*` props/slots if structural |

**Message screen — chrome**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Nav header | **app-owned**: title, subtitle, back affordance, trailing avatar/buttons, height | **App-owned** | Render the header inside `Channel`. React Navigation `Stack.Screen options` / Expo Router header — not a theme key; drive the title from channel state. **Liquid Glass:** frosted/translucent floating pills (iOS 26 — e.g. frosted back/title/avatar pills) need `expo-glass-effect` `GlassView` (guard `isLiquidGlassAvailable()`, translucent fallback); a flat semi-transparent colour is not a match. |
| Chat background / wallpaper | flat color vs. texture | Theming (+ Layout) | `Channel` / message-list background theme key; a custom background view for a texture |
| Date separators + new-messages divider | present? shape | Theming (+ Layout) | date-separator theme keys; slot override if the shape differs |
| Scroll-to-bottom / jump-to-latest | present? style | Theming (+ Layout) | scroll-to-bottom affordance slot — confirm the exact name in docs |

**Message screen — the message itself**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Layout style | bubbles (messaging-style) vs. flat left-aligned rows (workplace-style) — **decides everything below** | Functional (+ Theming) | `forceAlignMessages` prop on `Channel` |
| Content layout | message content order; text first or last (default is text last) | Functional | `messageContentOrder` prop on `Channel` |
| Bubble | fill color, border, corner radius (**all four, per grouping variant**), max width, **tail** | Theming (+ Layout) | Fills/text are **semantic tokens** — `theme.semantics.chatBgOutgoing` / `chatBgIncoming` / `chatTextOutgoing` / `chatTextIncoming` (set literal hex) — plus `messageItemView` theme keys. Radii and the tail: see [Bubble radius and tail](#bubble-radius-and-tail). |
| Grouping | consecutive same-author messages, who shows an avatar | Layout | `useMessageContext()` group flags |
| Sender name placement | shown at all (1:1 often hides it, groups show it)? **inside** the bubble as a first line vs. **above/outside** as a separate row? incoming only or own too? first-of-group or every message? | Layout | inside → `MessageContentTopView` / `MessageContentBottomView` — apply padding to custom sections too, and ensure the rounded border doesn't hide content; above → `MessageHeader` / `MessageFooter` (remove the default `MessageFooter` if you add a custom one); `useMessageContext()` group flags. **Per-sender name colour:** map it **explicitly** to the seeded users (an id→colour map); never hash `userId`→palette, which assigns the wrong colour per person. |
| Timestamp + delivery/read receipts placement | **below/outside** the bubble (Stream default) vs. **inside it** (trailing corner) | **Structural (Layout)** when moved inside; Theming if only recoloured in place | No theme key moves metadata inside — see [metadata inside the bubble](#message-metadata-inside-the-bubble-bottom-trailing-corner). Default via `MessageFooter`; inside → `MessageContentBottomView` / `MessageContentTrailingView` (always set `alignSelf`, reproduce the content body's `paddingHorizontal`/`paddingBottom`, remove `MessageFooter`); outside → `MessageFooter` / `MessageHeader` |
| Pinned / sent-to-channel / saved / reminder status | present? | Layout | default `MessageHeader` |
| Read/delivery indicator glyphs | single/double tick, color | Theming (+ Layout if repositioned) | theming to recolour; `MessageStatus` if the ticks/indicator must differ |
| Avatar shape | circle? square? online indicator? | Theming | `avatar` |
| Avatars beside messages | shown? on own messages? | Layout | `MessageAuthor` and `useMessageContext()` group flags |
| Quoted / inline replies | present? author-name colour? | Theming | Restyle, don't rebuild — the quoted block is the SDK `Reply` component. Its **author-name colour defaults to the SDK gray**, so a tinted quoted author (e.g. per-sender colour) must be pushed into the reply header via theming; restyling the surrounding block doesn't reach it. |

**Message screen — reactions**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Reactions placement | inside or outside bubble? top or bottom? overlapping? add button in the list? | Theming (+ Layout) | `Channel` props; custom reaction list components (required if the list has an add button). **`ReactionListTop`/`ReactionListBottom` render OUTSIDE the bubble (above/below it) — "bottom" ≠ inside.** For reactions **inside** the bubble background (sharing the bottom row with the timestamp), render them in `MessageContentBottomView` and set both `ReactionListTop` and `ReactionListBottom` to `() => null`. |
| Custom add-reaction button | is there an add button inside the message reaction list? | Structural | reuse the default `EmojiViewerButton` or create a custom component at the correct spot; not to be confused with `showReactionsOverlay`, which does NOT add reactions |
| **Own (selected) reaction styling** | is YOUR OWN reaction tinted differently? | Theming or Layout | theming or a `ReactionListItem` override; own state is `reaction.own` from `useMessageContext()` |
| **Custom reaction set / emoji** (`supportedReactions`) | different reaction emoji, or an extra type (e.g. 😃 `smile`)? | Functional | **EXTEND the SDK default `reactionData` (a public export), don't rebuild the array.** The defaults are already emoji (`👍 😂 ❤️ 😮 😢`, each `isMain: true`). Spread and append/replace only what differs: `[{ type: 'smile', Icon, isMain: true }, ...reactionData]`. **`isMain: true` is mandatory on any custom entry** — the context-menu picker filters to `supportedReactions.filter(r => r.isMain)`, so an entry without it never appears there (the row collapses to the "more emojis" `+` toggle) even though already-applied chips still render. Rebuilding from scratch also drops the default's extra-emoji list (the `...emojis.map(...)` spread that fills the "more" sheet). |

<a id="dead-theme-keys"></a>
## Theme keys that type-check but don't render — confirmed dead / deceptive

Each row was read out of the installed **`stream-chat-react-native-core@9.7.1`** source;
**re-confirm against your pinned version** before relying on one. When a key you expect to work does
nothing, suspect this class before a stale bundle.

| Key / prop | Why it doesn't do what the name implies | Reach it instead by |
|---|---|---|
| `theme.avatar` `height` / `width` | `Avatar` composes `[styles.container, avatarSizes[size], {backgroundColor}, border, style]` — no theme size is in the list. Setting it squares/ignores avatars rather than resizing them. | the `style` prop (last in the array, so it wins) on `Avatar`/`UserAvatar`, plus the `size` prop |
| `messageComposer.micButtonContainer.backgroundColor` | `AudioRecordingButton`'s `useAnimatedStyle` writes `backgroundColor: … : 'transparent'` every frame; a Reanimated animated style is applied natively and beats the static entry regardless of array order. | put the fill on a **wrapper** around the button |
| `icons.Mic` size | rendered as `<icons.Mic height={20} width={20} …>` — hardcoded; neither `micButtonContainer` nor `audioRecordingButtonContainer` reaches it. | override the icon through the `icons` map |
| `messageComposer.wrapper` **in floating mode** | with `messageInputFloating` the inner view's style is `[styles.wrapper]` only — the theme's `wrapper` is dropped from that branch. | `messageComposer.floatingWrapper` |
| `semantics.*` inherited into `myMessageTheme` | `mergeThemes` builds `{...baseTheme, semantics}` — it **replaces the entire `semantics` object** with freshly resolved SDK defaults *before* merging your `myMessageTheme`, so base-theme semantic tokens are discarded for own messages. Defining one token silently reverts the others. | restate **every** `semantics` token own messages need inside `myMessageTheme` |
| `messageList.contentContainer` for row gutters | row horizontal padding comes from the **top-level** `theme.screenPadding` (default `16`). | set `theme.screenPadding` |

Two `<Channel>` **prop** defaults in the same family, which make a region look unimplementable when
it is only unset: `audioRecordingEnabled` defaults to **`false`** (so `OutputButtons` never shows the
at-rest mic, only send), and `reactionListPosition` defaults to **`'top'`** (reactions below the
bubble need `'bottom'`, or the in-bubble route above).

## Bubble radius and tail

**The last-of-group tail is usually free:** `messageBubbleRadiusTail`'s default sharpens the near
corner, which already produces the tail look. Confirm it in the installed theme before building a
custom tail, and confirm the reference actually *has* a sharpened corner — many designs keep all four
corners rounded and protrude the tail outward instead. Measure EVERY corner.

**`components.messageBubbleRadius*` are NOT theme-overridable.** They are a module-level static
import (`theme/index.ts` → `generated/light/StreamTokens`) and there is **no `components` key on the
`Theme` type**, so nothing passed to `<Chat style>` / `<OverlayProvider value={{ style }}>` changes
them. Set radii on `messageItemView.content.container` instead.

`MessageContent` defaults both bottom corners to `messageBubbleRadiusGroupBottom`, swapping
`messageBubbleRadiusTail` into the **near** corner (right for outgoing, left for incoming) only for
group position `single`/`bottom`, then applies `borderBottomLeftRadius ?? computed`, reading those
radii out of `content.container`. (`messageBubbleRadiusGroupTop`/`GroupMiddle` exist as tokens but are
**never read** in the SDK source.) So a per-corner radius in **either** `content.container` (via that
`??`) or `content.containerInner` (applied *after* the computed style, so it wins by style-array
order) is a **static override that wins for every group position**, collapsing "sharp on the last
bubble of a group" into "sharp on all of them".

For a uniform bubble, set **`borderBottomLeftRadius` AND `borderBottomRightRadius`** (plus the top
two, or alongside `borderRadius`) on `content.container` to the measured radius. `borderRadius`
**alone is not enough**: the two bottom corners are always emitted explicitly and RN's per-corner
props beat it, so the tail survives. Confirm all of this in
`Message/MessageItemView/MessageContent.tsx` in the installed package.

## Text-only bubble height: set `markdown.paragraph`, not `contentContainer`

For a text-only message the SDK zeroes `contentContainer`'s vertical padding (`MessageContent` sets
`hidePaddingTop`/`hidePaddingBottom` when the message has only text), so the bubble's entire vertical
padding is `markdown.paragraph`'s `marginTop`/`marginBottom` — 8 pt each, making a single-line bubble
8 + lineHeight + 8. A theme value on `contentContainer` is not inert: it sits later in the style array
than those zeros, so it **adds** to the 16 pt already there and the bubble overshoots.

- Set the target padding on `messageItemView.content.markdown.paragraph`
  (`marginTop`/`marginBottom`) and don't set `contentContainer`'s vertical padding at all. Target the
  value you need, don't zero it: with `lineHeight: 20`, a 42.7 pt reference bubble wants ≈11 pt each.
  The consumer value is spread last in `renderText`, so it replaces cleanly.
- Set `paragraphCenter` to the same values — a paragraph with fewer than three nodes containing bold
  renders with that key, so a short all-bold message otherwise keeps the 8/8 default.
- Keep `fontSize`/`lineHeight` on `markdown.text`, not on `paragraph`. `onlyEmojiMarkdown`
  shallow-replaces only the `text` key, so anything on `paragraph` survives into the emoji-only path:
  a `fontSize` there caps the jumbo glyph (observed 44.3 pt → 25.0 pt) and a `lineHeight` there
  crushes it into a 20 pt line box (the SDK omits `lineHeight` when `onlyEmojis`, but the consumer
  spread lands after that check).
- Don't pre-compensate for the `marginTop: -8` caption offset on `textContainer`. It fires only when
  text is NOT the first item in `messageContentOrder`, so it never applies to a text-only message;
  adding 8 pt to cancel it over-pads every bubble.
- Verify: a single-line text bubble's height should equal
  paddingTop + marginTop + lineHeight + marginBottom + paddingBottom, and that sum should close to the
  pixel against the reference. If not, one of the five is contributing a value you did not set.

<a id="message-metadata-inside-the-bubble-bottom-trailing-corner"></a>
## Message metadata inside the bubble (bottom-trailing corner)

Putting the **timestamp + delivery/read ticks *inside* the bubble** (bottom-trailing corner, sharing
the last row with the text) is **structural** — no theme key moves metadata inside. **Read the default
`MessageContent` / `MessageSimple` in the installed package first** (slot names below verified against
**stream-chat-expo 9.7.0**), then:

1. **Render the metadata in an in-bubble slot** — `MessageContentBottomView` (below the text) or
   `MessageContentTrailingView` (same row as the text, trailing edge). These are *inside* the bubble
   background; `MessageFooter`/`MessageHeader` are *outside* it. Some designs float the timestamp
   *inline on the last text line* when it fits and wrap it below only when the line is too long;
   reproducing that is fiddly, and metadata on its own line below the text
   (`MessageContentBottomView`) is an acceptable approximation — but it IS a visible difference, so
   choose it deliberately and note it.
2. **Suppress the default outside footer** so it isn't duplicated below the bubble: set
   `MessageFooter` to `() => null` via `WithComponents`.
3. **Reproduce the bubble's own padding** — these content slots have **no padding of their own**, so
   the metadata otherwise touches/clips the bubble's right and bottom edge. Match the content body's
   `paddingHorizontal`/`paddingBottom`, set **`alignSelf: 'flex-end'`**, and make sure the bubble's
   rounded border / `overflow` doesn't clip it.
4. **Reuse `MessageStatus` for the ticks** — hand-rolled single/double-tick logic desyncs read vs
   delivered. Recolour via theming: the read-tick colour is the status check-icon's **`stroke`** (e.g.
   `theme.messageItemView.status.checkAllIcon.stroke` — `stroke`, **not** `pathFill`; confirm in the
   installed theme), and **sample the tick colour off the reference** rather than assuming a brand hue
   ([Follow EVERY color](design-matching.md#follow-every-color-from-the-reference--sample-it-dont-guess-and-sample-each-sub-part)).
5. **Reactions share this bottom row in some designs** — if so, render them in the same in-bubble slot
   and set both `ReactionListTop`/`ReactionListBottom` to `() => null`.
6. **Do both senders + verify:** incoming *and* outgoing; the metadata sits **inside** the bubble
   background, doesn't clip the right/bottom edge, and the default outside footer is gone. Overriding
   a composite slot inherits all of its sub-features — grouping, edited/deleted state and the quoted
   parent must still render.

**Message screen — attachments**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Image/photo grid | the grouped collage is largely the RN default — **restyle, don't rebuild** | Theming (+ Layout) | attachment theme keys |
| Video / file / giphy / link / voice-recording / poll / custom | present? style | Theming (+ Layout) | attachment theme keys; `Attachment` override only if structural |

**Composer** (almost always differs — inspect closely, in BOTH states)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Floating vs. docked | inset / rounded / above content vs. flush at the bottom edge | Layout | `messageInputFloating` flag |
| Layout style | colors, backgrounds, borders | Theming | `messageComposer.wrapper` (outer) and `messageComposer.container` (inner). **Liquid Glass:** frosted/translucent attach/send/mic buttons or input pill (iOS 26) need the button slots wrapped in `expo-glass-effect` `GlassView` (guard `isLiquidGlassAvailable()`) and a translucent pill — a solid fill is not a match. |
| Send/mic button | colors, location | Theming + Layout | theming to recolour; use `OutputButtons`, don't create a custom one. Inside the input → `MessageInputTrailingView` (default slot); outside → `MessageComposerTrailingView` |
| Attach buttons | how many? colors, location | Theming + Layout | theming to recolour; the default `+` is in `MessageComposerLeadingView`. Reuse `AttachButton` for repositioning only (`MessageInputTrailingView`/`MessageComposerTrailingView`). A custom attach button uses `useMessageInputContext` (implement open and close picker). |
| Typing | send button appears / swaps in | Layout | `MessageComposer` slot (send/mic swap) |
| Audio recording | is there a standalone button (not the shared send/mic)? | Layout | reuse `AudioRecordingButton` in the proper slot, don't create a custom one |
| Location sharing | present? | Functional | location sharing guide from docs |

## Long-press message menu — the default is an in-place overlay

Stream RN's default long-press menu is an **in-place floating overlay** (`Message` →
`showMessageOverlay` → `MessageOverlayWrapper`: the message floats with the reaction picker +
`MessageActionList` anchored to it). A reference using a **docked bottom sheet** (or any non-overlay
menu) is a **layout+functional** difference, not theming — and a silent FAIL if left un-decomposed.

> Handler names and the `actionHandlers` shape below were read out of the installed
> **stream-chat-expo 9.7.2** source; re-confirm against your pinned version — the installed package
> outranks this file.

- Pass **`onLongPressMessage` to `<Channel>`** — providing the prop short-circuits the default overlay
  (verified in `Message.tsx`) — and render your own menu (a plain RN `Modal` + bottom-anchored panel is
  enough for a sheet; no `@gorhom/bottom-sheet` needed).
- **Reuse the payload's `actionHandlers`** (`{ copyMessage, deleteMessage, deleteForMeMessage,
  quotedReply, markUnread, pinMessage, resendMessage, toggleReaction, toggleBanUser, toggleMuteUser,
  … }`) so each item keeps **exact SDK behavior** (delete confirmation, quoted-reply wiring, reaction
  toggle). Do NOT re-implement via raw `client`/`channel` calls. **Two entries in that object are NOT
  usable as-is — `editMessage` and `threadReply`; both are covered below.**
- **Read the `actionHandlers` object in the installed source before trusting any entry — its members
  are not homogeneous.** In `Message.tsx` most keys map to a real internal handler
  (`copyMessage: handleCopyMessage`, `deleteMessage: handleDeleteMessage`,
  `quotedReply: handleQuotedReplyMessage`, …), but at least one is a **straight pass-through of an
  optional `<Channel>` customization prop**, so it is `undefined` unless the integrator supplied it.
  Two cheap tells: `MessagesContextValue` marks it **optional** (`handleThreadReply?:`), and you find
  yourself writing `handlers.x?.(…)` — an optional-call on a handler you were told always works is the
  smell. Grep the object literal; don't pattern-match off this list.
- **Exception — do NOT call `editMessage` verbatim from inside a `Modal`/sheet; it silently no-ops.**
  It is the one keyboard-gated handler (`useWithPortalKeyboardSafety` →
  `useAfterKeyboardOpenCallback`): `setEditingState` fires only *after* the keyboard opens, which the
  handler triggers by focusing the composer and waiting for `keyboardWillShow`. From a presented
  `Modal` the composer is occluded, so `focus()` can't raise the keyboard and Edit appears to do
  nothing; every *other* handler uses `useStableCallback` and runs immediately, so **only Edit
  breaks**. Drive edit yourself: call `setEditingState(message)` from `useMessageComposerAPIContext`,
  then focus `useMessageInputContext().inputBoxRef.current` **after your container has dismissed**.
  Generally: any payload handler needing the composer focused / keyboard up won't work while your own
  presentation occludes the composer — verify each item **by actually firing it**.
- **Exception — `actionHandlers.threadReply` is `undefined` by default; calling it does NOTHING.** It is
  not an internal handler: `Message.tsx` sets `threadReply: handleThreadReply`, the raw **optional
  `<Channel handleThreadReply>` customization prop** (`MessagesContext`:
  `handleThreadReply?: (message) => Promise<void>`). The function that actually opens a thread is
  `onThreadReply` in `useMessageActions` — `if (handleThreadReply) handleThreadReply(message);
  onOpenThread();` — reachable only as the `action` of the SDK's `threadReply` **message action**, i.e.
  from the default overlay `onLongPressMessage` just short-circuited. So the sheet row silently closes
  with no error, while the *other* thread entry point (tapping the reply-count indicator) keeps working.
  **Replicate `onOpenThread` instead** — your sheet renders inside `<Channel>`, so `ThreadContext` is
  available:
  ```tsx
  const { openThread } = useThreadContext();                 // SDK thread state
  // onThreadReply is your own nav callback — the SAME one <MessageList onThreadSelect> uses
  onPress: () => { onClose(); if (message.reply_count) openThread(message); onThreadReply(message); }
  ```
  **Guard `openThread` on `reply_count`.** `Channel.openThread` fires
  `channel.markRead({ thread_id: message.id })` unconditionally and **unguarded**, so on a parent with
  **zero replies** (the thread doesn't exist server-side yet) it throws an *unhandled* rejection:
  `ErrorFromResponse: StreamChat error code 16: MarkRead failed with error: "Can't find thread with id
  …"` — a red LogBox toast in dev. Skipping `openThread` when `reply_count` is 0 loses nothing, because
  `Thread` also only calls `loadMoreThread()` when `reply_count` is truthy.
- **Threads have TWO entry points and the
  [Thread Screen blueprint](CHAT-REACT-NATIVE-blueprints.md) only wires one.** The blueprint's
  `<MessageList onThreadSelect>` covers the reply-count indicator; a custom long-press menu is a
  **second, independent** path that must be wired separately. Driving one and crediting the other is a
  verification hole — fire the sheet row itself.
- The `messageActions` prop only customizes the overlay's **contents**, not its **presentation**. Use
  `onLongPressMessage` for presentation.
- Gate the item set by ownership/type to match the reference (e.g. Edit/Delete for own text messages,
  Mark-as-unread for others', Resend/Delete for failed).

<a id="composer-deep-dive--the-render-tree-the-surfaces-and-the-two-facet-buttons"></a>
## Composer deep-dive — the render tree, the surfaces, and the two-facet buttons

**Read `MessageComposer`'s source in the installed package**
(`node_modules/stream-chat-react-native-core/.../MessageComposer`) before overriding — the tree and
key names below are verified against **stream-chat-expo 9.7.0**; confirm them against the pinned
version ([Three axes](#three-axes-of-customization)).

**First check — is the composer FLOATING or docked? (structural; re-derive it from the reference on
every build.)** The one question to answer: *does the actual content appear behind the composer, or is
there a separate fill in front of it?* **Wallpaper/content visible *continuously behind and around* the
composer — its pill AND its buttons — plus a pill/button shadow → floating.** A distinct surface, or a
visible "cut"/seam where the message list ends and the composer's bar begins → docked; so is a **flat
fill that merely resembles the wallpaper colour** without the real texture/content showing through.
Inset side margins are **not** the test — a composer can be full-width with its buttons reaching the
screen edges and still float.

Floating is a **first-class prop — set `messageInputFloating` on `<Channel>`.** **Anti-pattern:
painting a translucent/rounded background onto `inputBoxWrapper` to *simulate* a floating pill while
the composer stays docked.** Map the structure to the SDK mechanism first, then theme the surface;
resolve this structural axis *before* cosmetic polish (Liquid Glass, exact colours).

**The container/theme-key map (`messageComposer.*`).** The composer nests
`wrapper → container → contentContainer → inputBoxWrapper (the pill) → inputBox`:
- **`wrapper` (and `floatingWrapper` for the floating variant) is the full-bleed SURFACE** —
  edge-to-edge and down through the bottom safe area. Its default is **padding only, no background**.
  **This is the composer *bar* colour.**
- **`container` / `contentContainer` are inner layout ROWS** (`flexDirection: 'row'`, sized to their
  children `[+][input][camera][mic]`). Colouring `container` paints only a **band hugging the
  controls** while the wrapper's padding + the safe-area strip stay transparent and show the wallpaper
  — the "slim wrap" bug, which looks like partial success and slips past verification. If your
  composer colour is a band, move it to `wrapper` (+ `floatingWrapper`).
- **`inputBoxWrapper` is the input pill**; **`inputBox` is its inner content.** Grow the pill with
  **symmetric vertical padding on `inputBox` (`paddingTop == paddingBottom`)**, never a fixed
  `minHeight`/`height` on the wrapper: the pill lays out top-down and doesn't vertically centre a
  single line, so a fixed height drops all the slack below the text and it hugs the top (see
  [Getting sizes right](design-matching.md#getting-sizes-right--measure-do-not-eyeball-round-numbers)
  item 6).

**The composer render tree (verified in source — confirm for the pinned version):**
`MessageComposerLeadingView` (→ `InputButtons` → `AttachButton`) · the **pill** [`InputView` +
`MessageInputTrailingView` (→ `OutputButtons`, the send/mic swap)] · `MessageComposerTrailingView`
(default empty). So **send / mic lives INSIDE the pill by default** (`OutputButtons`) and is
**stateful** — mic/audio at rest, **swapping to send when the input has text** — so the composer is at
least **two screenshots** from the same slot. **Reuse `OutputButtons` / `StartAudioRecordingButton`;
do not hand-roll the send button, the swap, or the record gesture.** To move send/mic to the *right of
the field* (outside the pill): render `OutputButtons` in `MessageComposerTrailingView` and override
`SendButton` — a slot override, not just theming.

**Confirming `OutputButtons` (or any symbol) is exported — do NOT grep the package's source
`index.ts`:** it's an `export *` barrel, so the literal name isn't there and you get a false negative.
Verify with a throwaway `import { OutputButtons } from 'stream-chat-react-native'` (or `-expo`) +
`tsc --noEmit`, or grep the compiled `node_modules/**/lib/typescript/**/*.d.ts`. **Never leave
send/mic inside the pill — or call moving it out _Impossible_ — on a grep-based "not exported"
assumption**; an `Impossible` verdict resting on an API limitation must be proven by *attempting* it
(resolve the symbol / try the prop), not asserted.

**The attach (`+`) button is TWO things — verify both facets in both states.** It is (1) a **trigger**
that opens/closes the picker and (2) a **stateful icon**: `+` when closed, a **keyboard glyph when the
picker is open**. Two recurring misses:
- **Don't drop in the raw SDK `<AttachButton />` and assume it matches.** It renders as a
  `Button variant="secondary" type="outline"` — a **bordered/ringed** button with `icons.Plus`. A
  reference wanting a **borderless** glyph inherits the SDK look instead (idiomatic ≠ matching —
  [`../RULES.md`](../RULES.md)).
- **Its `onPress` is `toggleAttachmentPicker`, a private helper *inside* the SDK `AttachButton`** —
  built from `openAttachmentPicker` / `closeAttachmentPicker` / `focusInputOnPickerClose` /
  `inputBoxRef` + `attachmentPickerStore`, and **not on any context or hook.** A custom `+` must
  **replicate it verbatim, including the refocus-input-on-close branch** — a hand-rolled
  `open ? close() : open()` loses the refocus. Read the current source and copy the logic (also in
  [CHAT-REACT-NATIVE.md](CHAT-REACT-NATIVE.md)).
- **The open-state glyph change is a 45° ROTATION applied by the PARENT, not an icon swap — so the icon
  you supply must survive being rotated.** `InputButtons` wraps whatever `AttachButton` resolves to in a
  Reanimated `useAnimatedStyle` that animates `rotate` to `45deg` while `selectedPicker !== undefined`.
  A bare `+` rotated 45° reads as a close **✕**, which is why the SDK default looks intentional. **Any
  icon with a visible frame or non-radial symmetry breaks:** a plus-in-a-rounded-**square** (Sendbird's
  `icon-add`) rotates the square too and renders as a diamond-with-an-✕ — a defect visible only in the
  picker-open state, never in an at-rest screenshot. If the reference keeps its `+` upright while open,
  you cannot fix it inside the icon: either replace the picker presentation (see
  [the modal action-list shape](#the-one-reference-shape-that-is-not-attachmentpicker)) so
  `selectedPicker` stays `undefined`, or override `MessageComposerLeadingView` to drop the rotating
  wrapper.

**Verifying the composer:** walk the **composer gate** in
[design-matching.md](design-matching.md#32-screenshot-every-screen-then-check-it) — structure
(floating vs docked), the three mandatory states, edge-to-edge background, pill centring, and both
attach-button facets. Don't leave the composer until all of it passes.

## Liquid Glass (`GlassView`) — frosted/translucent chrome

`expo-glass-effect` ships in the Expo SDK 57 template; guard with `isLiquidGlassAvailable()` (true on
iOS 26 + a matching Xcode toolchain) and provide a translucent `View` fallback. Three things make
hand-built glass render *flat*:
- **Corner radius is a NATIVE prop** on `GlassView` (`borderRadius` / `borderTopLeftRadius` …), **not**
  a clipped style — `style={{ borderRadius }}` alone yields 0-radius glass. Set it as a prop (and
  mirror it in `style`).
- **`overflow: 'hidden'` on the `GlassView` suppresses the effect** — remove it and let the native
  corner config round it.
- **The SDK input pill (`messageComposer.inputBoxWrapper`) can't be a `GlassView` via theme** — it's a
  plain `View` accepting only a `backgroundColor`, so the pill stays a translucent fill. The real glass
  goes on the **custom components you wrap in `GlassView` yourself** — composer buttons, header pills,
  the picker capsule.

**Verify glass by proving the code path, not by eyeballing the simulator** — the effect renders only
subtle vibrancy on the sim. Temporarily give the non-glass fallback a loud colour, confirm the element
does NOT take it, then remove the probe.

**Composer — attachment picker** (opened by the attach button)

| Region | What to check | Route to |
|---|---|---|
| Attachment bar | rows and position of the bar (above or under the selected type's content); custom bar icons (gallery, polls, files…); or a fully custom layout (e.g. a list) | theming to recolour; overrides for custom icons; `AttachmentPickerSelectionBar` for the bar; `AttachmentPicker` for a fully custom picker. Verify the default layout/behavior in the SDK source and decide the override scope. **Don't just re-render the default picker buttons and call it customized** — reproduce the reference's item layout (icon + label), selected-tab tint and bar background. Build labeled items as `Pressable`s calling the SAME context actions the SDK buttons use (`attachmentPickerStore.setSelectedPicker(...)`, `useMessageInputContext().pickFile()`, `openPollCreationDialog({ sendMessage })`), and read the active tab from `useAttachmentPickerState().selectedPicker`. Only show tabs the app backs (e.g. Gallery/File/Poll); drop unbacked ones (Location/Checklist) rather than shipping dead tabs. |

**A chat app's attach sheet IS Stream's `AttachmentPicker` — override the bar, don't rebuild the
surface.** Most attach sheets are an **action-tile selection bar on top + a media gallery below**,
which is `AttachmentPicker`'s default layout. So: **override only `AttachmentPickerSelectionBar`** (via
`WithComponents`) and **keep the SDK gallery + the `AttachButton`/`openPicker` lifecycle + the
attachment preview + permission flow.** Do **NOT** build a standalone `Modal` with your own sheet
state — that bypasses all of it.

<a id="the-one-reference-shape-that-is-not-attachmentpicker"></a>
**The one reference shape that is NOT `AttachmentPicker`: a modal action-list sheet with NO gallery.**
Some apps (Sendbird's UIKit among them) open a **dimmed-backdrop bottom sheet of labelled rows** — "Take
a photo / Take a video / Photo library / Files" — that each launch the platform's **native** picker, with
no in-sheet grid at all. Overriding `AttachmentPickerContent` cannot reach that, because the difference is
the **presentation**, not the contents: `AttachmentPicker` is a *keyboard-replacement* sheet docked under
a still-lit composer, so you get no dimmed backdrop, no rounded top over the whole screen, the composer
shifted up by `attachmentPickerBottomSheetHeight`, and the 45° attach-glyph rotation. **The measurable
tell: sample the backdrop luminance just above the sheet — an overlay sheet dims it (e.g. ~191 over a
light app), a docked picker leaves it untouched (255).** For that shape, bypass the host from
`<Channel>`:

```tsx
<Channel
  disableAttachmentPicker                              // the SDK sheet never opens →
  handleAttachButtonPress={() => setSheetOpen(true)}   // no keyboard reservation, no
>                                                      // composer shift, no rotation
```

`handleAttachButtonPress` is checked **before** `toggleAttachmentPicker` inside `AttachButton`, and
`selectedPicker` stays `undefined` so `InputButtons` never rotates the glyph. Then render your own
`Modal` sheet whose rows call the SDK's **own upload entry points** from `useMessageInputContext()` —
`takeAndUploadImage('image' | 'video')`, `pickAndUploadImageFromNativePicker()`, `pickFile()` — the same
functions the SDK's tile buttons call, so compression, previews, permissions and error handling all stay
SDK-owned. This is **not** the "standalone Modal" anti-pattern above: nothing is re-implemented, only the
presentation is replaced, and the SDK's gallery is genuinely absent from the reference.
`AttachmentPickerContent` / `AttachmentPickerSelectionBar` overrides become dead code — delete them.

Moving the bar to the **bottom** also does not require replacing the host: `AttachmentPicker` resolves
**both** `AttachmentPickerSelectionBar` **and** `AttachmentPickerContent` from `useComponentsContext`
(verified in the installed source — confirm for the pinned version), so both are
`WithComponents`-overridable. Recipe: set `AttachmentPickerSelectionBar` → `() => null` and override
`AttachmentPickerContent` to render the **default gallery** plus your bar, then match the reference's
bar type:
- **Bar floats over the gallery** (hovers, gallery visible behind it): render the gallery at **full
  sheet height** and the bar as an **absolutely-positioned overlay** (`position: 'absolute', bottom:
  0`); do **NOT** subtract the bar's height from the gallery.
- **Bar is flush** (gallery ends where the bar begins): a **stacked** bottom section with the gallery
  height reduced by the bar height.

The `<AttachmentPicker>` host being a direct import in `Channel` does **not** lock its children — they
are context slots ([`../RULES.md`](../RULES.md) > *enumerate every context slot*).

- **Mixed camera+library picker:** RN Chat has no combined picker (live camera preview inline with the
  photo grid). Split it into **separate library and camera tabs** (`MediaPickerButton` → `images`,
  `CameraPickerButton` → `camera-photo`/`camera-video`); don't fake one merged surface. Read whether
  the picker is open from `attachmentPickerStore.state.getLatestValue().selectedPicker`.
- **Match the bar's SHAPE and MATERIAL, not just its tiles.** It may be a **flush flat bar** (its own
  surface, often only the top corners rounded) **or** a **floating inset capsule** (all corners
  rounded, side/bottom margins, often frosted/`GlassView`, horizontally scrollable, a tinted pill on
  the selected tab). Decide from the image; correct tiles in the wrong container is still a miss.
- **Reference-reading rule:** the photos in a picker gallery are frequently **screenshots of other
  apps** (other chats, home screens, a settings page). A strip of app-like thumbnails with selection
  circles / duration badges / a grid **is the photo gallery**, not "chat cards" or an app switcher.
  Re-crop the region at full resolution and confirm its identity before concluding the SDK picker
  can't match it. A decision that leads to reinventing a whole surface is the signal to re-check the
  reference read ([design-matching.md](design-matching.md#region-checklist--routing-walk-every-row) >
  *reinvention is a red flag*).
- **Picker height — anchor to the keyboard, no magic number.** The picker is a
  **keyboard-replacement** sheet, so its height should ≈ the keyboard: anchor to the SDK default
  **`attachmentPickerBottomSheetHeight` (333)**. If you enlarge the selection bar, keep the **total**
  near keyboard height — `default_sheet + default_bar` (~`405`) is right. Do **not** invent a "roomy
  gallery" number (e.g. `+340`, which balloons the sheet far past a keyboard — only visible on a
  physical device), and do **not** swing into a runtime keyboard-measuring hook
  ([design-matching.md](design-matching.md#getting-sizes-right--measure-do-not-eyeball-round-numbers)
  > *no magic numbers*).

> **`keyboardVerticalOffset`/`topInset` on `Channel` — default to `0`; they offset for chrome ABOVE
> the Channel, not for a header inside it.** ([`../RULES.md`](../RULES.md) > Navigation and overlay
> discipline is authoritative if this note ever seems to disagree.) They exist so the keyboard-avoiding
> view and the attachment-picker bottom sheet know how far down the Channel's top edge starts. Route
> by **where the header is rendered**, not by "native vs custom":
> - **Native nav header, or a custom header rendered as a *sibling above* `<Channel>`:** set **both**
>   `topInset` **and** `keyboardVerticalOffset` to its height. Native: `useHeaderHeight()` (RN CLI /
>   Expo Router ≤ 55) or the `Platform.OS + insets.top` swap on Expo Router 56+. Sibling header:
>   `insets.top + <your header content height>`. **But prefer the header INSIDE `<Channel>`: a sibling
>   header in a plain flex column can push the composer *entirely off-screen*. If a chat screen shows
>   no composer, suspect this first.**
> - **Custom header rendered *inside* `<Channel>`** (`headerShown: false` + your own header `View`
>   above `MessageList`): the Channel already fills the screen from `y=0`, so pass both **explicitly as
>   `0`**: `keyboardVerticalOffset={0} topInset={0}`. **Do not just omit them** — `Channel` defaults
>   `topInset` to `0` but destructures `keyboardVerticalOffset` with **no default**, so omitting it
>   passes `undefined` (not `0`) and leaves keyboard-avoidance unverified (confirm in the pinned
>   `Channel` source). A non-zero value over-compensates the keyboard-avoiding view and mis-computes
>   the picker snap; don't leave a dead `insets.top + HEADER_HEIGHT` value in place. **Verify by
>   focusing the input so the real keyboard rises** — not by `setText`, which raises no keyboard.
>
> **The composer↔picker gap symptom.** When the picker opens, the docked composer shifts up by the
> picker's reserved height (`attachmentPickerBottomSheetHeight`, default `333`), and the sheet's snap is
> computed from `topInset`. A gap ("picker detached from the input") means `topInset` is wrong for the
> layout: with a native/sibling-above header it's missing/too small → raise it to the header height;
> with an inside-`Channel` header it's non-zero when it should be `0`. **Try `0` first.**
>
> **Do NOT try to close the gap with `bottomInset`.** It shrinks the composer's upward shift
> (`attachmentPickerBottomSheetHeight - bottomInset`); dialing it up moves the input *down, under* the
> sheet and hides it. `bottomInset` is only for a bottom tab bar that owns the safe area.
>
> **Exception — a persistent app-owned bottom tab bar on the message screen (floating-composer apps
> like Slack / Telegram).** When the message screen keeps an **app-owned bottom tab bar** AND the
> composer floats (`messageInputFloating`), `topInset`/`bottomInset` alone **cannot** close the gap —
> recognise it before tuning numbers. The composer lives inside the **tab-navigator-inset scene**
> while the picker is a **root-anchored bottom-sheet portal** (snapped to
> `attachmentPickerBottomSheetHeight`, lifted off the screen bottom by `bottomInset`), and the two
> move in **opposite** directions: raise `bottomInset` and the composer rides *over* the input while
> the sheet's lower half hides *behind* the tab bar (its centred empty state then reads as a
> tabs↔content gap); lower it and the composer detaches upward. Fix it the way the keyboard already
> coexists: **hide the tab bar while the picker is open.** Mirror the picker state out of `<Channel>`
> to the tab layer with a tiny cross-tree store written by a bridge that reads
> `useAttachmentPickerState().selectedPicker`; set the tab bar to `display:'none'` (or return `null`)
> while open so the scene reflows full-height; keep `bottomInset={0}`. Read `AttachmentPicker.tsx`
> (snap points + root anchoring) **before** tuning any inset here.
>
> **Verify with the picker OPEN, and wait for the image grid to load.** A shot taken before the photo
> library / remote thumbnails finish loading shows a short, half-empty grid that also looks like a gap
> — re-screenshot after the grid settles (and open to the **Files** tab per SIMULATOR-VERIFICATION to
> avoid the un-dismissable photo-permission prompt).
>
> **Don't mistake the picker's empty / not-granted placeholder for a tabs↔content gap.** The selection
> bar and the content render inside **one** contiguous sheet (content height =
> `attachmentPickerBottomSheetHeight − selectionBarHeight`), so a populated gallery starts right below
> the tabs — but the **not-granted / empty-state panel is centre-aligned**, so it floats in the middle
> with a large gap above it. On the simulator this is the **expected** state
> ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) revokes photo access on purpose). Don't
> diagnose it as a layout bug, and don't declare the picker layout verified from the not-granted state
> alone — confirm a populated grid on a device before judging tabs↔content spacing.

**Thread surfaces** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Thread reply screen | does it exist? parent message + replies | Layout / **App-owned nav** | separate nav screen: `Channel` with `threadList` + `Thread` (**Thread Screen** blueprint in [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md)) — reuses your row + composer overrides |
| Thread inbox / list | row layout | Theming (+ Layout) | `ThreadList` inside `Chat` (**Thread List Screen** blueprint); thread-list theme keys + `ThreadList` item props if the row differs |
| Message replies indicators | layout and styling | Theming + Layout | `MessageReplies`; default is connector + avatars |

> The RN slot/mechanism details behind these Chat rows (metadata beside/inside the bubble, ungrouping
> + spacing, uniform bubble corners, in-bubble reactions, appending content below a message,
> `ChannelPreview` `onSelect`, composer button shape/position, the v9 no-cascade token model) live in
> [CHAT-REACT-NATIVE.md](CHAT-REACT-NATIVE.md#composer-attach-button-and-message-metadata-facts) —
> confirm names against the pinned package.
