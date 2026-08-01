# Chat — region checklist + routing

Channel list, message row, reactions, attachments and the composer — plus the four deep-dives that are most often shipped wrong (metadata inside the bubble, the long-press menu, the composer render tree, Liquid Glass).

Tier 2 of the design-match decomposition. The method that drives it — the three axes, how to
measure sizes, how to sample colours, and the Step 3 verify loop — lives in
[`design-matching.md`](design-matching.md); read that first, then walk **every row** below.

The **Route to** column names the *mechanism*. Confirm the exact theme key / slot / prop name in
the manifest-selected docs and the installed package, never from memory.

---

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
| Bubble | fill color, border, corner radius (**all four, per grouping variant**), max width, **tail** | Theming (+ Layout) | Fills/text are **semantic tokens** — `theme.semantics.chatBgOutgoing`/`chatBgIncoming`/`chatTextOutgoing`/`chatTextIncoming` (set literal hex) — plus `messageItemView` theme keys. **The last-of-group bubble tail is usually free:** the tail-corner-radius token (`messageBubbleRadiusTail`, whose default sharpens the near corner) already produces the "tail" look — confirm it in the installed theme before building a custom tail, and **confirm the reference actually has a sharpened corner** (many designs keep all four corners rounded and protrude the tail outward instead — *Measure EVERY corner*). **Set radii via the `components.messageBubbleRadius*` tokens, NOT via `messageItemView.content.containerInner`.** `MessageContent` computes the per-corner radius from the message's group position (`messageBubbleRadiusGroupTop`/`GroupMiddle`/`GroupBottom`, with `messageBubbleRadiusTail` swapped into the near corner only for `single`/`bottom`) and then applies it as `borderBottomLeftRadius ?? computed` — so a radius set in `containerInner` is a **static override that wins for every group position**, collapsing "sharp on the last bubble of a group" into "sharp on all of them". Want a uniform bubble? Set the group tokens (and the tail token) to the measured radius and leave `containerInner` radii unset. |
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
| **Custom reaction set / emoji** (`supportedReactions`) | does the reference use different reaction emoji, or an extra type (e.g. 😃 `smile`)? | Functional | **EXTEND the SDK default `reactionData` (a public export), don't rebuild the array.** The defaults are already emoji (`👍 😂 ❤️ 😮 😢`, each `isMain: true`) — there is nothing to "swap to emoji." Spread `reactionData` and append/replace only what differs: `[{ type: 'smile', Icon, isMain: true }, ...reactionData]`. **`isMain: true` is mandatory on any custom entry** — the context-menu reaction picker filters to `supportedReactions.filter(r => r.isMain)`, so an entry without it never appears in the picker (the row collapses to just the "more emojis" `+` toggle) even though already-applied chips still render. Rebuilding from scratch also silently drops the default's extra-emoji list (the `...emojis.map(...)` spread that fills the "more" sheet). See [Step 2.5](design-matching.md#step-25-overriding-a-slot-inherits-all-of-its-sub-features) — this is that trap applied to a data array, not a component. |

<a id="dead-theme-keys"></a>
## Theme keys that type-check but don't render — confirmed dead / deceptive

A `Theme` key compiling is no proof it paints (see the principle in
[design-matching.md](design-matching.md#three-axes-of-customization-internalize-this-first)). Each row
below was read out of the installed **`stream-chat-react-native-core@9.7.1`** source after a real run
lost time to it; **re-confirm against your pinned version** before relying on a row. When a key you
expect to work does nothing, suspect this class before you suspect a stale bundle.

| Key / prop | Why it doesn't do what the name implies | Reach it instead by |
|---|---|---|
| `theme.avatar` `height` / `width` | `Avatar` composes `[styles.container, avatarSizes[size], {backgroundColor}, border, style]` — no theme size is in the list at all. Setting it squares/ignores avatars rather than resizing them. | the `style` prop (last in the array, so it wins) on `Avatar`/`UserAvatar`, plus the `size` prop |
| `messageComposer.micButtonContainer.backgroundColor` | `AudioRecordingButton`'s `useAnimatedStyle` writes `backgroundColor: … : 'transparent'` on every frame; a Reanimated animated style is applied natively and beats the static entry regardless of array order. | put the fill on a **wrapper** around the button |
| `icons.Mic` size | rendered as `<icons.Mic height={20} width={20} …>` — hardcoded; neither `micButtonContainer` nor `audioRecordingButtonContainer` reaches it. | override the icon through the `icons` map |
| `messageComposer.wrapper` **in floating mode** | with `messageInputFloating`, the inner view's style is `[styles.wrapper]` only — the theme's `wrapper` is dropped from that branch (it's applied in the docked branch). | `messageComposer.floatingWrapper` |
| `semantics.*` inherited into `myMessageTheme` | `mergeThemes` builds `{...baseTheme, semantics}` — it **replaces the entire `semantics` object** with freshly resolved SDK defaults *before* merging your `myMessageTheme`, so your base theme's semantic tokens are discarded for own messages. Defining one token silently reverts the others (a real run's own-bubble fill snapped back to SDK brand blue). | restate **every** `semantics` token own-messages need inside `myMessageTheme` |
| `messageList.contentContainer` for row gutters | row horizontal padding comes from the **top-level** `theme.screenPadding` (default `16`). | set `theme.screenPadding` |

Two `<Channel>` **prop** defaults in the same family — they make a region look unimplementable when it
is only unset: `audioRecordingEnabled` defaults to **`false`** (so `OutputButtons` never shows the
at-rest mic, only send), and `reactionListPosition` defaults to **`'top'`** (a design with reactions
below the bubble needs `'bottom'`, or the in-bubble route in the reactions table above).

## Text-only bubble height: set markdown.paragraph, not contentContainer

For a text-only message the SDK zeroes `contentContainer`'s vertical padding
(`MessageContent` sets `hidePaddingTop` and `hidePaddingBottom` when the message
has only text). By default the bubble's entire vertical padding is then
`markdown.paragraph`'s `marginTop` and `marginBottom`, 8 pt each, so a
single-line bubble is 8 + lineHeight + 8.

A theme value on `contentContainer` is not inert: it sits later in the style
array than those zeros, so it overrides them and stays live. That is exactly why
reaching for it to size the bubble adds padding on top of the 16 pt already
there rather than replacing it, and the bubble overshoots by whatever you set.

Fix: set the target padding on `messageItemView.content.markdown.paragraph`
(`marginTop` / `marginBottom`) and do not set `contentContainer`'s vertical
padding at all. Target the value you need, do not zero it: with `lineHeight: 20`,
a 42.7 pt reference bubble wants roughly 11 pt each. The consumer value is
spread last in `renderText`, so it takes effect exactly, verified as a clean
replacement rather than a merge.

Set `paragraphCenter` to the same values. A paragraph with fewer than three
nodes containing bold renders with that key instead, so a short all-bold message
silently keeps the 8/8 default otherwise.

Keep `fontSize` and `lineHeight` on `markdown.text`, not on `paragraph`.
`onlyEmojiMarkdown` shallow-replaces only the `text` key, so anything set on
`paragraph` survives into the emoji-only path: a `fontSize` there caps the jumbo
glyph (observed 44.3 pt shrinking to 25.0 pt), and a `lineHeight` there crushes
it into a 20 pt line box. The SDK deliberately omits `lineHeight` when
`onlyEmojis`, but the consumer spread lands after that check.

Do not pre-compensate for the `marginTop: -8` caption offset on `textContainer`.
It fires only when text is NOT the first item in `messageContentOrder`, so on a
text-only message it never applies. Adding 8 pt to cancel it over-pads every
bubble.

Verify: measure a single-line text bubble. Its height should equal
paddingTop + marginTop + lineHeight + marginBottom + paddingBottom, and that sum
should close to the pixel against the reference. If it does not, one of the five
is contributing a value you did not set.

## Message metadata inside the bubble (bottom-trailing corner) — a worked relayout

Putting the **timestamp + delivery/read ticks *inside* the bubble** (bottom-trailing corner, sharing the last row with the text) is one of the two most-missed message-design details (the other is the composer). It is **structural** — no theme key moves metadata inside; routing it to a colour key is the classic failure. **Read the default `MessageContent` / `MessageSimple` in the installed package first** (verified against **stream-chat-expo 9.7.0**; confirm the slot names against the pinned version), then:

1. **Render the metadata in an in-bubble slot** — `MessageContentBottomView` (below the text, inside the bubble) or `MessageContentTrailingView` (same row as the text, trailing edge). These are *inside* the bubble background; `MessageFooter`/`MessageHeader` are *outside* it. **Note the inline-when-fits behaviour some designs use:** the timestamp sits *inline on the last text line* when it fits and only *wraps below* when the last line is too long. Reproducing that float-if-fits behaviour is fiddly; putting metadata on its own line below the text (the simpler `MessageContentBottomView` approach) is a common, acceptable approximation — but it IS a visible difference from the reference, so choose it deliberately and note it, rather than assuming it matches.
2. **Suppress the default outside footer** so it isn't duplicated below the bubble: set `MessageFooter` to `() => null` via `WithComponents` when you add a custom in-bubble one.
3. **Reproduce the bubble's own padding** — these content slots have **no padding of their own**, so the metadata otherwise touches/clips the bubble's right and bottom edge. Match the content body's `paddingHorizontal`/`paddingBottom`, and set **`alignSelf: 'flex-end'`** so it hugs the trailing corner. Make sure the bubble's rounded border/`overflow` doesn't clip it.
4. **Reuse `MessageStatus` for the ticks** — don't hand-roll single/double-tick logic (you'll desync read vs delivered). Recolour via theming — the read-tick colour is the status check-icon's **`stroke`** (e.g. `theme.messageItemView.status.checkAllIcon.stroke`; it uses `stroke`, **not** `pathFill` — confirm in the installed theme) — and **sample the tick colour off the reference** rather than assuming a "known" brand hue ([Follow EVERY color](design-matching.md#follow-every-color-from-the-reference--sample-it-dont-guess-and-sample-each-sub-part)).
5. **Reactions share this bottom row in some designs** — if so, render them in the same in-bubble slot and set both `ReactionListTop`/`ReactionListBottom` to `() => null` (see the reactions table above); "bottom" reaction lists render *outside* the bubble.
6. **Do both senders + verify:** incoming *and* outgoing; confirm the metadata sits **inside** the bubble background, does not clip the right/bottom edge, and the default outside footer is gone (not duplicated). This is a composite-slot change — [Step 2.5](design-matching.md#step-25-overriding-a-slot-inherits-all-of-its-sub-features)'s "reproduce every sub-feature" contract applies (grouping, edited/deleted state, quoted parent still render).

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

## Long-press message menu — the default is an in-place overlay; a bottom sheet is a structural change

Easy to leave un-decomposed — a silent FAIL if the reference uses a different presentation (region left at the SDK default). Stream RN's default long-press menu is an **in-place floating overlay** (`Message` → `showMessageOverlay` → `MessageOverlayWrapper`: the message floats with the reaction picker + `MessageActionList` anchored to it). If the reference instead uses a **docked bottom sheet** (or any non-overlay menu), that's a **layout+functional** difference, not theming:
- Pass **`onLongPressMessage` to `<Channel>`** — providing the prop short-circuits the default overlay (verified in `Message.tsx`: if the prop is set it returns without calling the default handler) — and render your own menu (a plain RN `Modal` + bottom-anchored panel is enough for a sheet; no `@gorhom/bottom-sheet` dependency needed).
- **Reuse the payload's `actionHandlers`** (`{ copyMessage, editMessage, deleteMessage, quotedReply, markUnread, resendMessage, toggleReaction, threadReply, ... }`) so each item keeps **exact SDK behavior** (delete confirmation, edit composer state, quoted-reply wiring, reaction toggle). Do NOT re-implement via raw `client`/`channel` calls.
- **Exception — do NOT call `editMessage` verbatim from inside a `Modal`/sheet; it silently no-ops.** It's the one handler the SDK keyboard-gates (`useWithPortalKeyboardSafety` → `useAfterKeyboardOpenCallback`): `setEditingState` fires only *after* the keyboard opens, which the handler triggers by focusing the composer and waiting for `keyboardWillShow`. From the default overlay that works; from a **presented `Modal`** the composer is occluded, so the `focus()` can't raise the keyboard, the event never fires, and **Edit appears to do nothing**. And because every *other* handler uses `useStableCallback` (runs immediately), **only Edit breaks** — easy to miss (green launch ≠ correct). Drive edit yourself: call `setEditingState(message)` from `useMessageComposerAPIContext` (the exact setter the SDK ends up calling — the composer prefills with the message), then focus `useMessageInputContext().inputBoxRef.current` **after your container has dismissed** so the keyboard rises. General form: any payload handler that needs the composer focused / keyboard up (`editMessage` today) won't work while your own presentation is occluding the composer — verify each item **by actually firing it**, don't assume "reused SDK handler ⇒ correct."
- The `messageActions` prop only customizes the overlay's **contents**, not its **presentation** — it does NOT change the overlay into a sheet. Use `onLongPressMessage` for presentation.
- Gate the item set by ownership/type to match the reference (e.g. Edit/Delete for own text messages, Mark-as-unread for others', Resend/Delete for failed).

## Composer deep-dive — the render tree, the surfaces, and the two-facet buttons

The composer is the region users inspect most closely and the one most often left half-matched. The table above routes each piece; this section gives you the **mental model** so you don't pick a theme key by name and get a half-styled result. **Read `MessageComposer`'s source in the installed package** (`node_modules/stream-chat-react-native-core/.../MessageComposer`) before overriding — the tree and key names below are verified against **stream-chat-expo 9.7.0**; confirm them against the pinned version (the "confirm in the installed package" rule, [Three axes](design-matching.md#three-axes-of-customization-internalize-this-first)).

**First check — is the composer FLOATING or docked? (structural; decide it from the reference every time.)** **The decisive cue: can you see the wallpaper/content *continuously behind and around* the composer — its pill AND its buttons? → floating.** Is there a distinct surface or a visible "cut"/seam where the message list ends and the composer's own bar begins? → docked. A composer can be **full-width with its buttons reaching the screen edges and still float** as long as content flows behind it — so don't rely on "inset side margins" as the test; *content visible behind* + a pill/button *shadow* are the reliable floating signals, and a distinct opaque bar with a seam is the docked signal. **Reason it out from the evidence, don't pattern-match a look:** if the composer's background is *exactly* the wallpaper/content with **no border or seam** — the wallpaper's texture and the messages actually continue *through and behind* it — that's **floating**. If it's a **flat fill that merely resembles the wallpaper colour** (a solid colour close to it, but the real texture/content does NOT show through), that's a **distinct surface → docked** — a similar, or even identical, colour is not the same as content showing through. The one concrete question to answer: *does the actual content appear behind the composer, or is there a separate fill in front of it?* Floating is a **first-class prop — set `messageInputFloating` on `<Channel>`** — it is NOT something you fake. **Anti-pattern (a defect, not a match): painting a translucent/rounded background onto `inputBoxWrapper` to *simulate* a floating pill while the composer stays docked.** Map the structure to the SDK mechanism first (`messageInputFloating`), then theme the surface — and resolve this structural axis *before* any cosmetic polish (Liquid Glass, exact colours). Re-derive floating-vs-docked from the reference's cues on every build; don't let an early yes/no answer lock it in against what the image actually shows.

**The container/theme-key map (`messageComposer.*`) — names do NOT map to "the bar" by intuition.** The composer nests roughly `wrapper → container → contentContainer → inputBoxWrapper (the pill) → inputBox`:
- **`wrapper` (and `floatingWrapper` for the floating variant) is the full-bleed SURFACE** — edge-to-edge and down through the bottom safe area. Its default is **padding only, no background**. **This is the composer *bar* colour.**
- **`container` / `contentContainer` are inner layout ROWS** (`flexDirection: 'row'`, sized to their children `[+][input][camera][mic]`). Colouring `container` paints only a **band hugging the controls** while the wrapper's padding + the safe-area strip stay transparent and show the wallpaper — the "slim wrap" bug. It *looks* like it worked (partial success), which is exactly why it slips past verification. If your composer colour is a band, you coloured `container`; move it to `wrapper` (+ `floatingWrapper`).
- **`inputBoxWrapper` is the input pill**; **`inputBox` is its inner content.** Grow the pill with **symmetric vertical padding on `inputBox` (`paddingTop == paddingBottom`)**, never a fixed `minHeight`/`height` on the wrapper — the pill lays out top-down and doesn't vertically centre a single line, so a fixed height drops all the slack below the text and it hugs the top (the common "taller composer, single line no longer centred" failure; see [Getting sizes right](design-matching.md#getting-sizes-right--measure-do-not-eyeball-round-numbers) item 6).

**The composer render tree (verified in source — confirm for the pinned version):** `MessageComposerLeadingView` (→ `InputButtons` → `AttachButton`) · the **pill** [`InputView` + `MessageInputTrailingView` (→ `OutputButtons`, the send/mic swap)] · `MessageComposerTrailingView` (default empty). So **send / mic lives INSIDE the pill by default** (`OutputButtons`) and is **stateful**: mic/audio at rest, **swapping to send when the input has text** — the composer is therefore at least **two screenshots** (at-rest and typing) from the same slot. **Reuse `OutputButtons` / `StartAudioRecordingButton`; do not hand-roll the send button, the swap, or the record gesture.** To move send/mic to the *right of the field* (outside the pill): render `OutputButtons` in `MessageComposerTrailingView` (empty by default) and override `SendButton` — a slot override, not just theming. **Confirming `OutputButtons` (or any symbol) is exported — do NOT grep the package's source `index.ts`: it's an `export *` barrel, so the literal name isn't there and you get a false negative.** Verify with a throwaway `import { OutputButtons } from 'stream-chat-react-native'` (or `-expo`) + `tsc --noEmit`, or grep the compiled `node_modules/**/lib/typescript/**/*.d.ts`. **Never leave send/mic inside the pill — or call moving it out _Impossible_ — on a grep-based "not exported" assumption**; a real run did exactly that and shipped the mic in the wrong place. An `Impossible` verdict resting on an API limitation must be proven by *attempting* it (resolve the symbol / try the prop), not asserted.

**The attach (`+`) button is TWO things — verify both facets in both states.** It is (1) a **trigger** that opens/closes the picker AND (2) a **stateful icon**: `+` when closed, a **keyboard glyph when the picker is open** (the "return to the keyboard" affordance common in chat apps). Two recurring misses:
- **Do not drop in the raw SDK `<AttachButton />` and assume it matches.** It renders as a `Button variant="secondary" type="outline"` — a **bordered/ringed** button with `icons.Plus`. If the reference wants a **borderless** glyph (e.g. a plain `+`), using it inherits the SDK look and discards the styling you matched (an *idiomatic ≠ matching* regression — [`../RULES.md`](../RULES.md)).
- **Its `onPress` is `toggleAttachmentPicker`, a private helper *inside* the SDK `AttachButton`** — built from `openAttachmentPicker` / `closeAttachmentPicker` / `focusInputOnPickerClose` / `inputBoxRef` + `attachmentPickerStore`. It is **not on any context or hook.** A custom `+` must **replicate it verbatim, including the refocus-input-on-close branch** — do not hand-roll `open ? close() : open()` (a lossy toggle that loses the refocus). Read the current source and copy the logic (also noted in [CHAT-REACT-NATIVE.md](CHAT-REACT-NATIVE.md)).

**Composer verification gate (do NOT leave the composer until all pass — the recurring defect). Verify STRUCTURE, not just presence/colour — a region can render the right pixels and still be structurally wrong:**
- [ ] **Structure: floating vs docked matches the reference.** If it floats, `messageInputFloating` is set on `<Channel>` — and the pill is NOT a docked bar with a painted translucent fill faking the float. If it docks, it sits flush to the bottom edge.
- [ ] **Three states are MANDATORY — at-rest, typing, picker-open** ([SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §4). At-rest and typing share one slot (`OutputButtons`), and typing is the **only** state that renders the send button — drive it with `useMessageComposer().textComposer.setText('hello')`. Picker-open is where the composer↔sheet spacing and the `+`↔keyboard swap are visible.
- [ ] **Every OTHER state — keyboard-up, voice-recording, edit mode — only if a reference screenshot shows it** (how to drive each: [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) §4). Don't drive them speculatively: the defects they would catch (unset `audioRecordingEnabled`, a composer pushed off-screen) all show up **at rest**. If a reference does show one, drive it and check its own tokens — the recorder tints from `semantics.accentPrimary` + `semantics.chatWaveformBar`, so overriding `accentPrimary` alone can leave a waveform on the Stream default.
- [ ] **Background fills EDGE-TO-EDGE and through the bottom safe area** — sample pixels in the *margin around* the controls, not just the controls. A colour band hugging the buttons = you coloured `container`, not `wrapper`.
- [ ] **Single-line input is vertically centred** in the pill (grew via `inputBox` padding, not wrapper height).
- [ ] **Attach button:** correct look (borderless vs bordered) **and** the `+`↔keyboard swap when the picker opens, wired to a `toggleAttachmentPicker` replica.
- [ ] Each glyph matches the reference's size, weight, fill-vs-outline character (compare ink ratio, not just the box), and colour.

## Liquid Glass (`GlassView`) — gotchas when a design uses frosted/translucent chrome

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
> - **Native nav header, or a custom header rendered as a *sibling above* `<Channel>`:** the Channel's top is pushed down by that header, so set **both** `topInset` **and** `keyboardVerticalOffset` to its height (equal values). Native: `useHeaderHeight()` (RN CLI / Expo Router ≤ 55) or the `Platform.OS + insets.top` swap on Expo Router 56+. Sibling header: `insets.top + <your header content height>`. **But prefer the header INSIDE `<Channel>` (below): a sibling header in a plain flex column can push the composer *entirely off-screen* — a whole-region disappearance, not a keyboard mis-offset — which is a recurring migration break; the in-Channel variant avoids it. If a chat screen shows no composer, suspect this first.**
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
> **Don't mistake the picker's empty / not-granted placeholder for a tabs↔content gap.** The selection bar and the content render inside **one** sheet, contiguous (content height = `attachmentPickerBottomSheetHeight − selectionBarHeight`), so a populated gallery starts right below the tabs. But the **not-granted / empty-state panel is centre-aligned** in the content area, so it floats in the middle with a large gap above it — which looks exactly like a broken "tabs detached from content" layout. On the simulator this is the **expected** state — [SIMULATOR-VERIFICATION.md](SIMULATOR-VERIFICATION.md) has you *revoke* photo access on purpose, because granting it does not reliably suppress the un-dismissable SpringBoard prompt. Do **not** diagnose that centred placeholder as a layout bug, and do **not** declare the picker layout verified from the not-granted state alone — confirm a populated grid on a device before judging tabs↔content spacing.

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
