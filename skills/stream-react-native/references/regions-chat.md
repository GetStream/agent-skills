# Chat — region checklist + routing

Channel list, message row, reactions, attachments and the composer — plus the deep-dives most often shipped wrong (dead theme keys, bubble radius, metadata inside the bubble, the long-press menu, the composer render tree, the attachment picker, Liquid Glass).

Tier 2 of the design-match decomposition. The method that drives it — measuring sizes, sampling
colours, the reasoning rules for picking a mechanism, and the Step 4 verify loop — lives in
[`design-matching.md`](design-matching.md); read that first, then walk **every row** below.

The **Route to** column names the *mechanism*. Confirm the exact theme key / slot / prop name in the
manifest-selected docs and the installed package, never from memory
([`design-matching.md`](design-matching.md#step-3-commit-the-plan-and-verify-every-name-against-the-installed-package)
> verify every name) — and check [dead theme keys](#dead-theme-keys) first.

## Three axes of customization (internalize this first)

RN Chat gives you three mechanisms. Map each design difference to the cheapest axis that reaches it,
and preference order: Functional - Theming - Layout / structure.

| Axis | Mechanism | What it changes | What it CANNOT change |
|---|---|---|---|
| **Functional** | Documented component props, channel config, and SDK context hooks (`useMessageContext`...) | Which actions/behaviors are enabled, what's interactive, send/edit/reaction/thread behavior. | Pure appearance (that's theming). |
| **Theming** | The `DeepPartial<Theme>` object passed to **both** `<OverlayProvider value={{ style }}>` **and** `<Chat style={…}>` (see [Theming Blueprint](./CHAT-REACT-NATIVE-blueprints.md#theming-blueprint)) | Colors, fonts, spacing, padding, border-radius, and dimensions - *within the existing layout*. In RN the theme object carries **both** color **and** padding/dimension, so most reskins are theme-only. | The structure - which views render, their arrangement, whether metadata sits inside or below the bubble, which buttons the composer has. |
| **Layout / structure** | Component overrides via `WithComponents overrides={{ … }}` - see the [Component Override Blueprint](./CHAT-REACT-NATIVE-blueprints.md#component-override-blueprint) | The actual views: extend or override parts of the UI | Colors/fonts/spacing that a theme key already reaches (don't replace a component to change a padding). |

**Two recurring mis-routings:**
- A **structural** difference solved with a **theming** token. "Read receipts inside the bubble", "a
  camera button in the composer", "the timestamp overlaid on the image", "an avatar on my own messages"
  are **structural** -> a component override, not a color key.
- A **spacing / padding / radius** difference solved by **overriding a component**. In RN those live in
  the **theme object** — reach for the theme key first; override only when the *arrangement* must change.

**RN-specific: the channel header is app-owned.** Unlike other Stream SDKs, RN Chat has no
`ChannelHeader` slot inside `Channel` — the nav header is **your** React Navigation `Stack.Screen
options` / Expo Router header (or a custom view above `MessageList`). Header differences route to the
**navigation layer**, not the theme. Match its height, title, subtitle and trailing affordances there,
and drive the title from channel state, never a hardcoded literal (every channel would show the same
wrong title).

---

**Channel list screen** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| List header | app-owned nav: title, actions, height | **App-owned** | React Navigation `Stack.Screen options` / Expo Router header - not a theme key |
| How many channel lists? | Group vs 1:1 messages? | Layout | Create multiple `ChannelList` with proper filter and sort options |
| Preview row | layout, avatar, unread badge, timestamp, empty/loading state, background | Theming (+ Layout) | `theme.channelPreview.*`; `ChannelList` `ChannelPreview*` props/slots if structural |
| Preview text + timestamp detail | **truncation** (where the line clips), which **side** each sits on, and the **time format** — Stream's default is relative ("2 hours ago"); many designs use a clock time or a date. A 1:1 row must show the **other member's single** avatar, not Stream's member cluster | Theming (+ Layout) | `theme.channelPreview.*` for placement; the `ChannelPreviewMessenger` / `ChannelPreviewTitle` / `ChannelPreviewStatus` slots to change the format or the avatar source |

**Message screen - chrome**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Nav header | **app-owned** RN / Expo: title, subtitle, back affordance, trailing avatar/buttons, height | **App-owned** | Always put header inside `Channel`. React Navigation `Stack.Screen options` / Expo Router header - not a theme key; drive the title from channel state. **Liquid Glass:** frosted/translucent floating pills (iOS 26 — frosted back/title/avatar pills) need `expo-glass-effect` `GlassView` ([Liquid Glass](#liquid-glass-glassview--gotchas-when-a-design-uses-frostedtranslucent-chrome)); a flat semi-transparent color is not a match. |
| Chat background / wallpaper | flat color vs. texture | Theming (+ Layout) | `Channel` / message-list background theme key; a custom background view if it's a texture |
| Date separators + new-messages divider | present? shape | Theming (+ Layout) | date-separator theme keys; slot override if the shape differs |
| Scroll-to-bottom / jump-to-latest | present? style | Theming (+ Layout) | scroll-to-bottom affordance slot - confirm exact name in docs |

**Message screen - the message itself**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Layout style | bubbles (messaging-style) vs. flat left-aligned rows (workplace-style) - **decides everything below** | Functional (+ Theming) | `forceAlignMessages` prop on `Channel` |
| Content layout | Message content order; typical variations: text first or last (default layout is text last) | Functional | `messageContentOrder` prop on `Channel` |
| Bubble | fill color, border, corner radius (**all four, per grouping variant**), max width, **tail** | Theming (+ Layout) | Fills/text are **semantic tokens** — `theme.semantics.chatBgOutgoing`/`chatBgIncoming`/`chatTextOutgoing`/`chatTextIncoming` (set literal hex) — plus `messageItemView` theme keys. Radii + the group tail: [Bubble corner radius](#bubble-corner-radius-and-the-group-tail). Text-only bubble height: [below](#text-only-bubble-height-set-markdownparagraph-not-contentcontainer). |
| Grouping | consecutive same-author messages, who shows an avatar | Layout | `useMessageContext()` group flags |
| Sender name placement | shown at all (1:1 often hides it, groups show it)? **inside** the bubble as a first line vs. **above/outside** as a separate row? incoming only or own too? first-of-group or every message? | Layout | inside → `MessageContentTopView` / `MessageContentBottomView` — **apply proper padding to custom sections too**, and ensure the rounded border doesn't hide content; above → `MessageHeader` / `MessageFooter` (remove the default `MessageFooter` if you add a custom one); `useMessageContext()` group flags. **Per-sender name colour:** map it **explicitly** to the seeded users (an id→colour map); do **not** hash `userId`→palette, which assigns the wrong colour per person — and don't ship a hash "for now". |
| Timestamp + delivery/read receipts placement | **below/outside** the bubble (Stream default) vs. **inside it** (trailing corner) | **Structural (Layout)** when moved inside; Theming only if just recolouring in place | Default via `MessageFooter`; outside → `MessageFooter` / `MessageHeader`. Moving metadata **inside** the bubble is a structural relayout, not a theme key — see [Message metadata inside the bubble](#message-metadata-inside-the-bubble-bottom-trailing-corner--a-worked-relayout). |
| Pinned / sent-to-channel / saved / reminder status | present? | Layout | default `MessageHeader` |
| Read/delivery indicator glyphs | single/double tick, color | Theming (+ Layout if repositioned) | Theming for recoloring, `MessageStatus` if ticks/indicator need to be different |
| Avatar shape | circle? square? online indicator? | Theming | `avatar` |
| Avatars beside messages | shown? on own messages? | Layout | `MessageAuthor` and `useMessageContext()` group flags |
| Quoted / inline replies | present? author-name colour? | Theming | Restyle, don't rebuild — the quoted block is the SDK `Reply` component. Its **author-name colour defaults to the SDK gray**, so a reference that tints the quoted author (e.g. per-sender colour) needs that colour pushed into the reply header via theming; restyling the surrounding block doesn't reach it. |

**Message screen - reactions**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Reactions placement | inside or outside bubble? top or bottom of bubble? reactions overlap? reaction list has add button? | Theming (+ Layout) | `Channel` props; custom reaction list components - must have if list has add button. **`ReactionListTop`/`ReactionListBottom` render OUTSIDE the bubble (above/below it) — "bottom" ≠ inside.** For reactions **inside** the bubble background (sharing the bottom row with the timestamp), render them in `MessageContentBottomView` (an in-bubble slot) and set both `ReactionListTop` and `ReactionListBottom` to `() => null` so the external list is suppressed. |
| Custom add reaction button | is there an add button inside the message reaction list? | Structural | default implementation is `EmojiViewerButton` reuse or create a custom component and display at correct spot; don't mix up with `showReactionsOverlay` - it DOESN'T add reactions |
| **Own (selected) reaction styling** | is YOUR OWN reaction tinted differently | Theming or Layout | Theming or a `ReactionListItem` override; own state is `reaction.own` from `useMessageContext()`. |
| **Custom reaction set / emoji** (`supportedReactions`) | does the reference use different reaction emoji, or an extra type (e.g. 😃 `smile`)? | Functional | **EXTEND the SDK default `reactionData` (a public export), don't rebuild the array.** The defaults are already emoji (`👍 😂 ❤️ 😮 😢`, each `isMain: true`) — there is nothing to "swap to emoji." Spread and append/replace only what differs: `[{ type: 'smile', Icon, isMain: true }, ...reactionData]`. **`isMain: true` is mandatory on any custom entry** — the context-menu picker filters to `supportedReactions.filter(r => r.isMain)`, so an entry without it never appears there (the row collapses to just the "more emojis" `+` toggle) even though already-applied chips still render. Rebuilding from scratch also silently drops the default's extra-emoji list (the `...emojis.map(...)` spread that fills the "more" sheet) — [Step 3's completion contract](design-matching.md#step-3-commit-the-plan-and-verify-every-name-against-the-installed-package) applied to a data array. |

**Message screen - attachments**

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Image/photo grid | the grouped collage is largely the RN default - **restyle, don't rebuild** | Theming (+ Layout) | attachment theme keys |
| Video / file / giphy / link / voice-recording / poll / custom | present? style | Theming (+ Layout) | attachment theme keys; `Attachment` override only if structural |

**Composer** (almost always differs - inspect closely, in BOTH states; mental model in the [composer deep-dive](#composer-deep-dive--the-render-tree-the-surfaces-and-the-two-facet-buttons))

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Floating vs. docked | inset / rounded / above content vs. flush at the bottom edge | Layout | `messageInputFloating` flag |
| Layout style | Colors, backgrounds, borders | Theming | `messageComposer.wrapper` outer wrapper; `messageComposer.container` inner part. **Liquid Glass:** frosted/translucent buttons or pill (iOS 26) need `GlassView` around the button slots + a translucent pill — a solid fill is not a match ([Liquid Glass](#liquid-glass-glassview--gotchas-when-a-design-uses-frostedtranslucent-chrome)). |
| Send/mic button | Colors, location | Theming + Layout | Use theming to recolor; Use `OutputButtons` for send/mic button, don't create custom. Inside input? `MessageInputTrailingView` (default slot). Outside input? `MessageComposerTrailingView` |
| Attach buttons | How many? Colors, location | Theming + Layout | Use theming to recolor; Default is + in `MessageComposerLeadingView`. Reuse `Attachbutton` for repositioning only (`MessageInputTrailingView`/`MessageComposerTrailingView`). For custom attach button, use `useMessageInputContext` (implement open and close picker). |
| Typing | send button appears / swaps in | Layout | `MessageComposer` slot (send/mic swap) |
| Audio recording | check if there is a standalone button (not shared send/mic button) | Layout | Reuse `AudioRecordingButton`, don't create custom; add it to proper slot |
| Location sharing | present? | Functional | Location sharing guide from docs |

**Thread surfaces** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Thread reply screen | Does it exist? Not all apps have threads; parent message + replies | Layout / **App-owned nav** | separate nav screen: `Channel` with `threadList` + `Thread` (**Thread Screen** blueprint in [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md)) - reuses your row + composer overrides |
| Thread inbox / list | row layout | Theming (+ Layout) | `ThreadList` inside `Chat` (**Thread List Screen** blueprint); thread-list theme keys + `ThreadList` item props if the row differs |
| Message replies indicators (message component) | Layout and styling | Theming + Layout | `MessageReplies`; default is connector + avatars |

> The RN slot/mechanism details behind these rows (which slot to override for metadata beside/inside the
> bubble, ungrouping + spacing, uniform bubble corners, in-bubble reactions, appending content below a
> message, `ChannelPreview` `onSelect`, composer button shape/position, the v9 no-cascade token model)
> live in [CHAT-REACT-NATIVE.md](CHAT-REACT-NATIVE.md#composer-attach-button-and-message-metadata-facts)
> — confirm names against the pinned package.

<a id="dead-theme-keys"></a>
## Theme keys that type-check but don't render — confirmed dead / deceptive

A `Theme` key compiling is no proof it paints; the principle and what to do about it are in
[design-matching.md Step 3](design-matching.md#step-3-commit-the-plan-and-verify-every-name-against-the-installed-package).
Each row was read out of the installed **`stream-chat-react-native-core@9.7.1`** source after a real run
lost time to it; **re-confirm against your pinned version**. When a key you expect to work does nothing,
suspect this class before you suspect a stale bundle.

| Key / prop | Why it doesn't do what the name implies | Reach it instead by |
|---|---|---|
| `theme.avatar` `height` / `width` | `Avatar` composes `[styles.container, avatarSizes[size], {backgroundColor}, border, style]` — no theme size is in the list at all. Setting it squares/ignores avatars rather than resizing them. | the `style` prop (last in the array, so it wins) on `Avatar`/`UserAvatar`, plus the `size` prop |
| `messageComposer.micButtonContainer.backgroundColor` | `AudioRecordingButton`'s `useAnimatedStyle` writes `backgroundColor: … : 'transparent'` on every frame; a Reanimated animated style is applied natively and beats the static entry regardless of array order. | put the fill on a **wrapper** around the button |
| `icons.Mic` size | rendered as `<icons.Mic height={20} width={20} …>` — hardcoded; neither `micButtonContainer` nor `audioRecordingButtonContainer` reaches it. | override the icon through the `icons` map |
| `messageComposer.wrapper` **in floating mode** | with `messageInputFloating`, the inner view's style is `[styles.wrapper]` only — the theme's `wrapper` is dropped from that branch (it's applied in the docked branch). | `messageComposer.floatingWrapper` |
| `semantics.*` inherited into `myMessageTheme` | `mergeThemes` builds `{...baseTheme, semantics}` — it **replaces the entire `semantics` object** with freshly resolved SDK defaults *before* merging your `myMessageTheme`, so your base theme's semantic tokens are discarded for own messages. Defining one token silently reverts the others (a real run's own-bubble fill snapped back to SDK brand blue). | restate **every** `semantics` token own-messages need inside `myMessageTheme` |
| `messageList.contentContainer` for row gutters | row horizontal padding comes from the **top-level** `theme.screenPadding` (default `16`). | set `theme.screenPadding` |

Two `<Channel>` **prop** defaults in the same family — they make a region look unimplementable when it is
only unset: `audioRecordingEnabled` defaults to **`false`** (so `OutputButtons` never shows the at-rest
mic, only send), and `reactionListPosition` defaults to **`'top'`** (a design with reactions below the
bubble needs `'bottom'`, or the in-bubble route in the reactions table above).

## Bubble corner radius and the group tail

**The last-of-group tail is usually free.** `messageBubbleRadiusTail`'s default already sharpens the near
corner and produces the "tail" look — confirm it in the installed theme before building a custom tail,
and **confirm the reference actually has a sharpened corner** (many designs keep all four corners rounded
and protrude the tail outward instead — *measure EVERY corner*).

**`components.messageBubbleRadius*` are NOT theme-overridable — set radii on
`messageItemView.content.container`.** The `components` tokens are a module-level static import
(`theme/index.ts` -> `generated/light/StreamTokens`) and there is **no `components` key on the `Theme`
type**, so nothing passed to `<Chat style>` / `<OverlayProvider value={{ style }}>` can change them.

How the SDK computes it: `MessageContent` defaults both bottom corners to
`messageBubbleRadiusGroupBottom`, swaps `messageBubbleRadiusTail` into the **near** corner (right for
outgoing, left for incoming) only for group position `single`/`bottom`, then applies
`borderBottomLeftRadius ?? computed`, reading those radii out of `content.container`.
(`messageBubbleRadiusGroupTop`/`GroupMiddle` exist as tokens but are **never read** in the SDK source.)

Consequence: a per-corner radius in **either** `content.container` (via that `??`) or
`content.containerInner` (applied *after* the computed style, so it wins by style-array order) is a
**static override that wins for every group position** — collapsing "sharp on the last bubble of a group"
into "sharp on all of them".

Want a uniform bubble? Set **`borderBottomLeftRadius` AND `borderBottomRightRadius`** (plus the top two,
or use them alongside `borderRadius`) on `content.container` to the measured radius. `borderRadius`
**alone is not enough**: the two bottom corners are always emitted explicitly and RN's per-corner props
beat it, so the tail survives. Confirm all of this in the installed package
(`Message/MessageItemView/MessageContent.tsx`).

## Text-only bubble height: set markdown.paragraph, not contentContainer

For a text-only message the SDK zeroes `contentContainer`'s vertical padding (`MessageContent` sets
`hidePaddingTop`/`hidePaddingBottom` when the message has only text). The bubble's entire vertical
padding is then `markdown.paragraph`'s `marginTop` + `marginBottom`, 8 pt each, so a single-line bubble
is 8 + lineHeight + 8.

A theme value on `contentContainer` is **not** inert: it sits later in the style array than those zeros,
so it overrides them and stays live — which is why reaching for it to size the bubble *adds* padding on
top of the 16 pt already there and the bubble overshoots by whatever you set.

Fix: set the target padding on `messageItemView.content.markdown.paragraph` (`marginTop`/`marginBottom`)
and don't set `contentContainer`'s vertical padding at all. Target the value you need, don't zero it:
with `lineHeight: 20`, a 42.7 pt reference bubble wants roughly 11 pt each. The consumer value is spread
last in `renderText`, so it lands exactly — a clean replacement, not a merge.

Set `paragraphCenter` to the same values: a paragraph with fewer than three nodes containing bold renders
with that key instead, so a short all-bold message otherwise silently keeps the 8/8 default.

Keep `fontSize` and `lineHeight` on `markdown.text`, **not** on `paragraph`. `onlyEmojiMarkdown`
shallow-replaces only the `text` key, so anything on `paragraph` survives into the emoji-only path: a
`fontSize` there caps the jumbo glyph (observed 44.3 pt shrinking to 25.0 pt) and a `lineHeight` crushes
it into a 20 pt line box. (The SDK deliberately omits `lineHeight` when `onlyEmojis`, but the consumer
spread lands after that check.)

Do **not** pre-compensate for the `marginTop: -8` caption offset on `textContainer`. It fires only when
text is NOT the first item in `messageContentOrder`, so on a text-only message it never applies; adding
8 pt to cancel it over-pads every bubble.

Verify: a single-line text bubble's height should equal paddingTop + marginTop + lineHeight +
marginBottom + paddingBottom, and that sum should close to the pixel against the reference. If not, one
of the five is contributing a value you did not set.

## Message metadata inside the bubble (bottom-trailing corner) — a worked relayout

Timestamp + delivery/read ticks *inside* the bubble (bottom-trailing corner, sharing the last row with
the text) is one of the two most-missed message details (the other is the composer). It is
**structural** — no theme key moves metadata inside; routing it to a colour key is the classic failure.
**Read the default `MessageContent` / `MessageSimple` in the installed package first** (verified against
**stream-chat-expo 9.7.0**; confirm slot names against the pinned version), then:

1. **Render the metadata in an in-bubble slot** — `MessageContentBottomView` (below the text, inside the
   bubble) or `MessageContentTrailingView` (same row as the text, trailing edge). These are *inside* the
   bubble background; `MessageFooter`/`MessageHeader` are *outside* it. **Some designs use
   inline-when-fits behaviour:** the timestamp sits *inline on the last text line* when it fits and only
   wraps below when the line is too long. That float-if-fits behaviour is fiddly; metadata on its own
   line below the text (the simpler `MessageContentBottomView` route) is a common, acceptable
   approximation — but it IS a visible difference, so choose it deliberately and note it.
2. **Suppress the default outside footer** so it isn't duplicated below the bubble: set `MessageFooter`
   to `() => null` via `WithComponents`.
3. **Reproduce the bubble's own padding** — these content slots have **no padding of their own**, so the
   metadata otherwise touches/clips the bubble's right and bottom edge. Match the content body's
   `paddingHorizontal`/`paddingBottom`, set **`alignSelf: 'flex-end'`** so it hugs the trailing corner,
   and make sure the bubble's rounded border/`overflow` doesn't clip it.
4. **Reuse `MessageStatus` for the ticks** — hand-rolling single/double-tick logic desyncs read vs
   delivered. Recolour via theming: the read-tick colour is the status check-icon's **`stroke`** (e.g.
   `theme.messageItemView.status.checkAllIcon.stroke`; **not** `pathFill` — confirm in the installed
   theme), and **sample the tick colour off the reference** rather than assuming a brand hue
   ([Follow EVERY color](design-matching.md#follow-every-color-from-the-reference--sample-it-dont-guess-and-sample-each-sub-part)).
5. **Reactions share this bottom row in some designs** — if so, render them in the same in-bubble slot
   and set both `ReactionListTop`/`ReactionListBottom` to `() => null` (reactions table above).
6. **Do both senders + verify:** incoming *and* outgoing; metadata **inside** the bubble background, not
   clipping the right/bottom edge, default outside footer gone (not duplicated). This is a composite-slot
   change, so [Step 3's completion contract](design-matching.md#step-3-commit-the-plan-and-verify-every-name-against-the-installed-package)
   applies (grouping, edited/deleted state, quoted parent still render).

## Long-press message menu — the default is an in-place overlay; a bottom sheet is a structural change

Easy to leave un-decomposed — a silent FAIL if the reference uses a different presentation. Stream RN's
default long-press menu is an **in-place floating overlay** (`Message` → `showMessageOverlay` →
`MessageOverlayWrapper`: the message floats with the reaction picker + `MessageActionList` anchored to
it). A **docked bottom sheet** (or any non-overlay menu) is a **layout+functional** difference, not
theming:

> Handler names and the `actionHandlers` shape below were read out of the installed **stream-chat-expo 9.7.2** source; re-confirm against your pinned version (the installed package outranks this file).

- Pass **`onLongPressMessage` to `<Channel>`** — providing the prop short-circuits the default overlay
  (verified in `Message.tsx`: if the prop is set it returns without calling the default handler) — and
  render your own menu. A plain RN `Modal` + bottom-anchored panel is enough; no `@gorhom/bottom-sheet`.
- **Reuse the payload's `actionHandlers`** (`{ copyMessage, deleteMessage, deleteForMeMessage,
  quotedReply, markUnread, pinMessage, resendMessage, toggleReaction, toggleBanUser, toggleMuteUser, ...
  }`) so each item keeps **exact SDK behavior** (delete confirmation, quoted-reply wiring, reaction
  toggle). Do NOT re-implement via raw `client`/`channel` calls. **Two entries are NOT usable as-is —
  `editMessage` and `threadReply`** (below).
- **Read the `actionHandlers` object in the installed source — its members are not homogeneous.** Most
  keys map to a real internal handler (`copyMessage: handleCopyMessage`, `deleteMessage:
  handleDeleteMessage`, `quotedReply: handleQuotedReplyMessage`, …), but at least one is a **pass-through
  of an optional `<Channel>` customization prop**, so it is `undefined` unless the integrator supplied
  it. Two cheap tells: `MessagesContextValue` marks it **optional** (`handleThreadReply?:`), and you find
  yourself writing `handlers.x?.(…)` — an optional-call on a handler you were told always works. Grep the
  object literal; don't pattern-match off this list.
- **Exception — do NOT call `editMessage` verbatim from inside a `Modal`/sheet; it silently no-ops.** It's
  the one keyboard-gated handler (`useWithPortalKeyboardSafety` → `useAfterKeyboardOpenCallback`):
  `setEditingState` fires only *after* the keyboard opens, which the handler triggers by focusing the
  composer and waiting for `keyboardWillShow`. From the default overlay that works; from a presented
  `Modal` the composer is occluded, `focus()` can't raise the keyboard, the event never fires, and **Edit
  appears to do nothing**. Every *other* handler uses `useStableCallback` (runs immediately), so **only
  Edit breaks** — easy to miss. Drive it yourself: `setEditingState(message)` from
  `useMessageComposerAPIContext` (the exact setter the SDK ends up calling — the composer prefills), then
  focus `useMessageInputContext().inputBoxRef.current` **after your container has dismissed**. General
  form: any payload handler needing the composer focused / keyboard up won't work while your presentation
  occludes the composer — verify each item **by actually firing it**.
- **Exception — `actionHandlers.threadReply` is `undefined` by default; calling it does NOTHING.**
  `Message.tsx` sets `threadReply: handleThreadReply`, i.e. the raw **optional `<Channel
  handleThreadReply>` prop** (`MessagesContext`: `handleThreadReply?: (message) => Promise<void>`). The
  function that actually opens a thread is `onThreadReply` in `useMessageActions` — `if
  (handleThreadReply) handleThreadReply(message); onOpenThread();` — reachable only as the `action` of the
  SDK's `threadReply` message action, i.e. from the overlay `onLongPressMessage` just short-circuited. So
  the sheet row silently closes with no error, while the *other* thread entry point (the reply-count
  indicator) keeps working — which is what makes this pass a careless check. **Replicate `onOpenThread`
  instead**; your sheet renders inside `<Channel>`, so `ThreadContext` is available:
  ```tsx
  const { openThread } = useThreadContext();                 // SDK thread state
  // onThreadReply is your own nav callback — the SAME one <MessageList onThreadSelect> uses
  onPress: () => { onClose(); if (message.reply_count) openThread(message); onThreadReply(message); }
  ```
  **Guard `openThread` on `reply_count`.** `Channel.openThread` fires `channel.markRead({ thread_id:
  message.id })` unconditionally and **unguarded**, so on a parent with **zero replies** (no server-side
  thread yet) it throws an *unhandled* rejection — `ErrorFromResponse: StreamChat error code 16: MarkRead
  failed with error: "Can't find thread with id …"`, a red LogBox toast in dev. Skipping it when
  `reply_count` is 0 loses nothing: `Thread` also only calls `loadMoreThread()` when `reply_count` is
  truthy.
- **Threads have TWO entry points and the [Thread Screen blueprint](CHAT-REACT-NATIVE-blueprints.md) only
  wires one.** The blueprint's `<MessageList onThreadSelect>` covers the reply-count indicator; a custom
  long-press menu is a **second, independent** path wired separately. Driving one and crediting the other
  is a verification hole — fire the sheet row itself.
- The `messageActions` prop only customizes the overlay's **contents**, not its **presentation**. Use
  `onLongPressMessage` for presentation.
- Gate the item set by ownership/type to match the reference (Edit/Delete for own text messages,
  Mark-as-unread for others', Resend/Delete for failed).

## Composer deep-dive — the render tree, the surfaces, and the two-facet buttons

The composer is the region users inspect most closely and the one most often left half-matched. The table
above routes each piece; this section is the **mental model** so you don't pick a theme key by name and
get a half-styled result. **Read `MessageComposer`'s source in the installed package**
(`node_modules/stream-chat-react-native-core/.../MessageComposer`) before overriding — the tree and key
names below are verified against **stream-chat-expo 9.7.0**; confirm against the pinned version
([design-matching.md](design-matching.md#step-3-commit-the-plan-and-verify-every-name-against-the-installed-package)
> verify every name).

**First check — FLOATING or docked? (structural; decide it from the reference every time.)** **The one
question: does the actual wallpaper/content appear *continuously behind and around* the composer — its
pill AND its buttons — or is there a separate fill in front of it?** Content showing through (plus a
pill/button **shadow**) = **floating**; a distinct surface with a visible "cut"/seam where the message
list ends and the composer's bar begins = **docked**.
- **Don't use "inset side margins" as the test.** A composer can be full-width, buttons reaching the
  screen edges, and still float, as long as content flows behind it.
- **A flat fill that merely *resembles* the wallpaper colour is docked.** A similar — even identical —
  colour is not the same as the real texture and messages continuing *through and behind* the composer.
- Floating is a **first-class prop — set `messageInputFloating` on `<Channel>`.** **Anti-pattern (a
  defect, not a match): painting a translucent/rounded background onto `inputBoxWrapper` to *simulate* a
  floating pill while the composer stays docked.** Map the structure to the SDK mechanism first, then
  theme the surface, and resolve this axis *before* cosmetic polish (Liquid Glass, exact colours) —
  [`design-matching.md`](design-matching.md#region-checklist--routing-walk-every-row) > *fix the structure
  before the surface*.
- Re-derive floating-vs-docked from the reference's cues on **every** build; don't let an early yes/no
  answer lock it in against what the image shows.

**The container/theme-key map (`messageComposer.*`) — names do NOT map to "the bar" by intuition.** The
composer nests roughly `wrapper → container → contentContainer → inputBoxWrapper (the pill) → inputBox`:
- **`wrapper` (and `floatingWrapper` for the floating variant) is the full-bleed SURFACE** — edge-to-edge
  and down through the bottom safe area. Its default is **padding only, no background**. **This is the
  composer *bar* colour.**
- **`container` / `contentContainer` are inner layout ROWS** (`flexDirection: 'row'`, sized to their
  children `[+][input][camera][mic]`). Colouring `container` paints only a **band hugging the controls**
  while the wrapper's padding + the safe-area strip stay transparent and show the wallpaper — the "slim
  wrap" bug, and it *looks* like it worked, which is why it slips past verification. If your composer
  colour is a band, move it to `wrapper` (+ `floatingWrapper`).
- **`inputBoxWrapper` is the input pill**; **`inputBox` is its inner content.** Grow the pill with
  symmetric vertical padding on `inputBox`, never a fixed height on the wrapper —
  [`design-matching.md`](design-matching.md#getting-sizes-right--measure-do-not-eyeball-round-numbers)
  item 6.

**The render tree (verified in source — confirm for the pinned version):**
`MessageComposerLeadingView` (→ `InputButtons` → `AttachButton`) · the **pill** [`InputView` +
`MessageInputTrailingView` (→ `OutputButtons`, the send/mic swap)] · `MessageComposerTrailingView`
(default empty). So **send/mic lives INSIDE the pill by default** (`OutputButtons`) and is **stateful**:
mic/audio at rest, **swapping to send when the input has text** — hence at least **two screenshots**
(at-rest, typing) from the same slot. **Reuse `OutputButtons` / `StartAudioRecordingButton`; do not
hand-roll the send button, the swap, or the record gesture.** To move send/mic *outside* the pill (right
of the field): render `OutputButtons` in `MessageComposerTrailingView` and override `SendButton` — a slot
override, not just theming. **To confirm `OutputButtons` (or any symbol) is exported, do NOT grep the
package's source `index.ts`: it's an `export *` barrel, so the literal name isn't there and you get a
false negative.** Verify with a throwaway `import { OutputButtons } from 'stream-chat-react-native'` (or
`-expo`) + `tsc --noEmit`, or grep the compiled `node_modules/**/lib/typescript/**/*.d.ts`. **Never leave
send/mic inside the pill — or call moving it out _Impossible_ — on a grep-based "not exported"
assumption** (a real run did, and shipped the mic in the wrong place). An `Impossible` verdict resting on
an API limitation must be proven by *attempting* it, not asserted.

**The attach (`+`) button is TWO things — verify both facets in both states.** It is (1) a **trigger**
that opens/closes the picker and (2) a **stateful icon**: `+` when closed, a **keyboard glyph when the
picker is open**. Three recurring misses:
- **Don't drop in the raw SDK `<AttachButton />` and assume it matches.** It renders as a `Button
  variant="secondary" type="outline"` — **bordered/ringed**, with `icons.Plus`. If the reference wants a
  **borderless** glyph, using it inherits the SDK look and discards the styling you matched (*idiomatic ≠
  matching* — [`../RULES.md`](../RULES.md)).
- **Its `onPress` is `toggleAttachmentPicker`, a private helper *inside* the SDK `AttachButton`** — built
  from `openAttachmentPicker` / `closeAttachmentPicker` / `focusInputOnPickerClose` / `inputBoxRef` +
  `attachmentPickerStore`, and **not on any context or hook**. A custom `+` must **replicate it verbatim,
  including the refocus-input-on-close branch**; a hand-rolled `open ? close() : open()` loses the
  refocus. Read the current source and copy the logic.
- **The open-state glyph change is a 45° ROTATION applied by the PARENT, not an icon swap — so your icon
  must survive being rotated.** `InputButtons` wraps whatever `AttachButton` resolves to in a Reanimated
  `useAnimatedStyle` animating `rotate` to `45deg` while `selectedPicker !== undefined`. A bare `+`
  rotated 45° reads as a close **✕**, which is why the SDK default looks intentional. **Any icon with a
  visible frame or non-radial symmetry breaks:** a plus-in-a-rounded-**square** (Sendbird's `icon-add`)
  rotates the square too and renders as a diamond-with-an-✕ — visible only in the picker-open state,
  never in an at-rest screenshot. If the reference keeps its `+` upright while open, you can't fix it
  inside the icon: either replace the picker presentation (the modal-action-list shape below) so
  `selectedPicker` stays `undefined`, or override `MessageComposerLeadingView` to drop the rotating
  wrapper.

**Verifying the composer:** walk the **composer gate** in
[design-matching.md](design-matching.md#42-screenshot-every-screen-then-check-it) — structure, the three
mandatory states, edge-to-edge background, pill centring, both attach-button facets. Do not leave the
composer until all of it passes; this is the recurring defect.

## Composer - attachment picker

Opened when the attach button is clicked.

| Region | What to check | Axis / Route to |
|---|---|---|
| Attachment bar | Layout (one row or multiple rows?) and position (above or under selected attachment type content) of the bar? Custom attachment bar icons (gallery, polls, files, etc.)? Or fully custom layout (for example list)? | Theming for recolor; Override for custom icons; `AttachmentPickerSelectionBar` for the bar; `AttachmentPicker` for a fully custom picker; verify the default layout/behavior from SDK source and decide the override scope. **Don't just re-render the default picker buttons and call it customized** — reproduce the reference's item layout (icon + label), selected-tab tint, and bar background. Build labeled items as `Pressable`s calling the SAME context actions the SDK buttons use (`attachmentPickerStore.setSelectedPicker(...)`, `useMessageInputContext().pickFile()` / `openPollCreationDialog({ sendMessage })`), and read the active tab from `useAttachmentPickerState().selectedPicker`. Only show tabs the app backs (Gallery/File/Poll); drop unbacked ones (Location/Checklist) rather than shipping dead tabs. |

**Mixed camera+library picker:** if the reference shows a single combined picker (live camera preview
inline with the photo grid, as in iOS's own sheet), RN Chat has no combined picker — split it into
**separate library and camera tabs** (`MediaPickerButton` → `images`, `CameraPickerButton` →
`camera-photo`/`camera-video`); don't fake one merged surface. Check whether the picker is open with
`attachmentPickerStore.state.getLatestValue().selectedPicker`.

**A chat app's attach sheet IS Stream's `AttachmentPicker` — override the bar, don't rebuild the
surface.** Most chat-app attach sheets share one shape: an **action-tile selection bar on top + a media
gallery below** — exactly `AttachmentPicker`'s default layout. So the default move is: **override only
`AttachmentPickerSelectionBar`** (via `WithComponents`) to match the tiles, and **keep the SDK gallery,
the `AttachButton`/`openPicker` lifecycle, the attachment-preview and the permission flow.** Do **NOT**
build a standalone `Modal` with your own sheet state — that bypasses all of it and re-implements
infrastructure the SDK already has.

**The one reference shape that is NOT `AttachmentPicker`: a modal action-list sheet with NO gallery.**
Some apps (Sendbird's UIKit among them) open a **dimmed-backdrop bottom sheet of labelled rows** — "Take
a photo / Take a video / Photo library / Files" — each launching the platform's **native** picker, with
no in-sheet grid at all. Overriding `AttachmentPickerContent` cannot reach that, because the difference is
the **presentation**: `AttachmentPicker` is a *keyboard-replacement* sheet docked under a still-lit
composer, so you get no dimmed backdrop, no rounded top over the whole screen, the composer shifted up by
`attachmentPickerBottomSheetHeight`, and the 45° attach-glyph rotation. **The measurable tell: sample the
backdrop luminance just above the sheet — an overlay sheet dims it (e.g. ~191 over a light app), a docked
picker leaves it untouched (255).** For that shape, bypass the host from `<Channel>`:
```tsx
<Channel
  disableAttachmentPicker                              // the SDK sheet never opens →
  handleAttachButtonPress={() => setSheetOpen(true)}   // no keyboard reservation, no
>                                                      // composer shift, no rotation
```
`handleAttachButtonPress` is checked **before** `toggleAttachmentPicker` inside `AttachButton`, and
`selectedPicker` stays `undefined` so `InputButtons` never rotates the glyph. Then render your own `Modal`
sheet whose rows call the SDK's **own upload entry points** from `useMessageInputContext()` —
`takeAndUploadImage('image' | 'video')`, `pickAndUploadImageFromNativePicker()`, `pickFile()` — the same
functions the SDK's tile buttons call, so compression, previews, permissions and error handling stay
SDK-owned. This is **not** the "standalone Modal" anti-pattern above: nothing is re-implemented, only the
presentation is replaced, and the SDK's gallery is genuinely absent from the reference.
`AttachmentPickerContent` / `AttachmentPickerSelectionBar` overrides become dead code — delete them.

**Bar position — a bottom bar does NOT require replacing the host.** The default host renders
`AttachmentPickerSelectionBar` at the TOP, but `AttachmentPicker` resolves **both**
`AttachmentPickerSelectionBar` **and** `AttachmentPickerContent` from `useComponentsContext` (verified in
the installed source — confirm for the pinned version), so **both are `WithComponents`-overridable.**
Recipe: set `AttachmentPickerSelectionBar` → `() => null` and override `AttachmentPickerContent` to render
the **default gallery** plus your bar — then match the reference's bar type. **Bar floating over the
gallery** (hovers, gallery visible behind it): gallery at **full sheet height**, bar as an
**absolutely-positioned overlay** (`position: 'absolute', bottom: 0`), and do **NOT** subtract the bar's
height from the gallery. **Bar flush** (gallery ends where the bar begins, no overlap): a **stacked**
bottom section with the gallery height reduced by the bar height. One trap regardless of type: do **NOT**
conclude the layout is locked because the `<AttachmentPicker>` host is a direct import in `Channel` — the
host being imported directly doesn't lock its children, which are context slots
([`../RULES.md`](../RULES.md) > *enumerate every context slot*).

- **Match the bar's SHAPE and MATERIAL, not just its tiles.** It may be a **flush flat bar** (its own
  surface, often only the top corners rounded) **or** a **floating inset capsule** (all corners rounded,
  side/bottom margins so it hovers, often frosted/`GlassView`, horizontally scrollable, a tinted pill on
  the selected tab). Decide from the image; don't default to either. Correct tiles in the wrong container
  is still a miss.
- **Reference-reading rule (this caused a from-scratch modal once):** the photos in a picker gallery are
  frequently **screenshots of other apps** (other chats, home screens, a settings page). Do **not**
  mistake that screenshot *content* for chrome — a strip of app-like thumbnails with selection circles /
  duration badges / a grid **is the photo gallery**, not "chat cards" or an app switcher. Re-crop at full
  resolution and confirm its identity before concluding the SDK picker can't match it
  ([design-matching.md](design-matching.md#region-checklist--routing-walk-every-row) > *reinvention is a
  red flag*).
- **Picker height — anchor to the keyboard, no magic number.** It's a **keyboard-replacement** sheet, so
  its height should ≈ the keyboard: anchor to the SDK default **`attachmentPickerBottomSheetHeight`
  (333)**. If you enlarge the selection bar, keep the **total** near keyboard height — a static
  approximation like `default_sheet + default_bar` (~`405`) is right. Do **not** invent a "roomy gallery"
  number (e.g. `+340`, which balloons the sheet far past a keyboard — obvious only on a physical device),
  and do **not** swing into a runtime keyboard-measuring hook (overreach). Simplest static approximation
  first ([design-matching.md](design-matching.md#getting-sizes-right--measure-do-not-eyeball-round-numbers)
  > *no magic numbers*).

### `keyboardVerticalOffset` / `topInset` on `Channel` — and the composer↔picker gap

> **Default to `0`; they offset for chrome ABOVE the Channel, not for a header inside it.** (This
> reconciles with [`../RULES.md`](../RULES.md) > Navigation and overlay discipline, which is
> authoritative if they ever seem to disagree.) The two props exist so the keyboard-avoiding view and the
> attachment-picker bottom sheet know how far down the Channel's top edge starts. Route by **where the
> header is rendered**, not by "native vs custom":
> - **Native nav header, or a custom header as a *sibling above* `<Channel>`:** the Channel's top is
>   pushed down by that header, so set **both** `topInset` **and** `keyboardVerticalOffset` to its height
>   (equal values). Native: `useHeaderHeight()` (RN CLI / Expo Router ≤ 55) or the `Platform.OS +
>   insets.top` swap on Expo Router 56+. Sibling header: `insets.top + <your header content height>`.
>   **But prefer the header INSIDE `<Channel>` (below): a sibling header in a plain flex column can push
>   the composer *entirely off-screen* — a whole-region disappearance, not a keyboard mis-offset — a
>   recurring migration break the in-Channel variant avoids. If a chat screen shows no composer, suspect
>   this first.**
> - **Custom header *inside* `<Channel>`** (`headerShown: false` + your own header `View` above
>   `MessageList`): the Channel already fills the screen from `y=0`, so there is **nothing above it to
>   offset** → pass both **explicitly as `0`**: `keyboardVerticalOffset={0} topInset={0}`. **Do not just
>   omit them** — the installed `Channel` defaults `topInset` to `0` but destructures
>   `keyboardVerticalOffset` with **no default**, so omitting it passes `undefined` (which is *not* `0`)
>   and leaves keyboard-avoidance unverified (confirm in the pinned source — assumed behaviour ≠ the SDK
>   default, [`../RULES.md`](../RULES.md) > Package version and docs discipline). A non-zero value here is
>   the bug, not the fix: it over-compensates the keyboard-avoiding view and mis-computes the picker snap.
>   Don't leave a dead `insets.top + HEADER_HEIGHT` value in place. **Verify by focusing the input so the
>   real keyboard rises** ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §4) — not by `setText`,
>   which raises no keyboard.
>
> **The composer↔picker gap symptom.** When the picker opens, the docked composer shifts up by the
> picker's reserved height (`attachmentPickerBottomSheetHeight`, default `333`) and the sheet's snap is
> computed from `topInset`. A gap ("picker detached from the input") means `topInset` is **wrong for the
> layout**: with a native/sibling-above header it's missing/too small → raise it to the header height;
> with an inside-`Channel` header it's non-zero when it should be `0`. **Try `0` first** and only add an
> offset if a native header is present or the picker demonstrably misbehaves.
>
> **Do NOT try to close the gap with `bottomInset`.** It shrinks the composer's upward shift
> (`attachmentPickerBottomSheetHeight - bottomInset`); dialing it up moves the input *down, under* the
> sheet and hides it. `bottomInset` is only for a bottom tab bar that owns the safe area.
>
> **Exception — a persistent app-owned bottom tab bar on the message screen (floating-composer apps like
> Slack / Telegram).** Everything above assumes a docked composer and **no** bottom tab bar. With an
> **app-owned bottom tab bar** AND a floating composer (`messageInputFloating`), `topInset`/`bottomInset`
> alone **cannot** close the gap — recognise this layout before you start tuning numbers. Why: the
> composer lives inside the **tab-navigator-inset scene** while the picker is a **root-anchored
> bottom-sheet portal** (snapped to `attachmentPickerBottomSheetHeight`, lifted off the screen bottom by
> `bottomInset`) — two coordinate spaces, and the composer's picker-open shift (`sheetHeight −
> bottomInset`) and the sheet's lift (`bottomInset`) move in **opposite** directions. Raise it and the
> composer rides *over* the input while the sheet's lower half hides *behind* the tab bar (its centred
> empty-state then reads as a tabs↔content gap); lower it and the composer detaches upward. **Don't chase
> the number** — fix it the way the keyboard already coexists: **hide the tab bar while the picker is
> open.** Mirror the picker state out of `<Channel>` to the tab layer with a tiny cross-tree store written
> by a bridge that reads `useAttachmentPickerState().selectedPicker`; set the tab bar to
> `display:'none'` (or return `null`) while open so the scene reflows full-height; keep `bottomInset={0}`.
> Read `AttachmentPicker.tsx` (snap points + root anchoring) **before** tuning any inset here — the
> structure is the answer, not the number ([`../RULES.md`](../RULES.md) > *fix the structure before the
> surface*).
>
> **Don't mistake the picker's empty / not-granted placeholder for a tabs↔content gap.** The selection bar
> and the content render inside **one** sheet, contiguous (content height =
> `attachmentPickerBottomSheetHeight − selectionBarHeight`), so a populated gallery starts right below the
> tabs. But the **not-granted / empty-state panel is centre-aligned** in the content area, so it floats in
> the middle with a large gap above it — looking exactly like a broken "tabs detached from content"
> layout. On the simulator the not-granted state is the **expected** one
> ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §1 has you revoke photo access on purpose). Do
> **not** diagnose that centred placeholder as a layout bug, and do **not** declare the picker layout
> verified from the not-granted state alone — confirm a populated grid on a device before judging
> tabs↔content spacing.

## Liquid Glass (`GlassView`) — gotchas when a design uses frosted/translucent chrome

`expo-glass-effect` ships in the Expo SDK 57 template; guard with `isLiquidGlassAvailable()` (true on iOS
26 + a matching Xcode toolchain) and provide a translucent `View` fallback otherwise. Three things make
hand-built glass render *flat*:
- **Corner radius is a NATIVE prop** on `GlassView` (`borderRadius` / `borderTopLeftRadius` …), **not** a
  clipped style — passing only `style={{ borderRadius }}` yields 0-radius glass. Set it as a prop (and
  mirror it in `style`).
- **`overflow: 'hidden'` on the `GlassView` suppresses the effect** — remove it; let the native corner
  config round it.
- **The SDK input pill (`messageComposer.inputBoxWrapper`) can't be a `GlassView` via theme** — it's a
  plain `View` that only accepts a `backgroundColor`, so the pill stays a translucent fill. The *real*
  glass goes on the **custom components you wrap in `GlassView` yourself** — composer buttons, header
  pills, the picker capsule. Don't set a flat fill and call it glass.

**Verify glass by proving the code path, not by eyeballing the simulator.** The effect renders only subtle
vibrancy on the sim and is far more pronounced on a device, so a sim screenshot can't confirm it. Prove
which branch rendered instead — temporarily give the non-glass fallback a loud colour and confirm the
element does NOT take it — then remove the probe.
