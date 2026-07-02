# Stream React (web) - custom / bespoke UI on the low-level client

Read this **only** when the user explicitly wants fully hand-built UI - a bespoke surface that the
prebuilt components can't be customized into. The default is the opposite: **prebuilt-component-first**
([`../RULES.md`](../RULES.md) > Reference authority). This file is the *decision* (prebuilt vs bespoke)
plus the *headless path* (how to build on the low-level client + the SDK's context hooks). It does
**not** mirror element markup - for every region you build, fetch the matching live page from
[`docs-map.md`](docs-map.md) first.

---

## Step 0: prebuilt vs bespoke - lean hard toward prebuilt

Stream's React SDKs ship rich prebuilt components built to be *customized*. Choosing to hand-build
instead is an architecture decision that usually costs a day and throws away typing indicators, read
receipts, reactions, threads, attachments, uploads, presence, optimistic send, and i18n - all of
which the prebuilt path gives you for free. So decide deliberately, and **default to prebuilt.**

There are **three levels of customization** - exhaust the cheaper ones before going bespoke:

| Level | Mechanism | Changes |
|---|---|---|
| **Theming** | CSS variables + the theme class (`str-chat__theme-light/dark`), `<Channel>` theming, Tailwind around the components | Colors, fonts, spacing, radius - *within the existing layout* |
| **Component injection** | `<WithComponents overrides={{ MessageUI, MessageComposerUI, Avatar, ... }}>` (writes `ComponentContext`), or a per-list `<MessageList Message={Custom} />` | Swap *one* region's UI while the SDK still drives data, events, and the rest of the tree |
| **Bespoke (this file)** | Your own React tree consuming the SDK's context hooks (or the raw `stream-chat` client) | Everything - but you own every dropped sub-feature |

**Litmus test:** if theming + a few `WithComponents` overrides + hooks could reach the design, it's a
**prebuilt** job - even a strong reskin (WhatsApp/Slack/Linear). Pick **bespoke only** when you'd be
replacing the message row, composer, channel list, **and** header all at once - i.e. using the SDK
purely as a data source for a non-messenger surface (a flat ticker, an overlay, a livestream chat
rail). Over-choosing bespoke is the common, expensive mistake. **When unsure, build the prebuilt
version first** - it's faster to confirm-or-reject than to rebuild a worse messenger by hand.

If it's genuinely unclear, ask one question:

> Is this a standard messenger (channel list + message list + composer) we can customize, or a
> bespoke surface where you want fully hand-built UI on the Stream client?

---

## The headless path - Chat

**Stay inside the providers.** The cheap, correct way to go bespoke is to keep `<Chat>` / `<Channel>`
mounted (so client lifecycle, the WebSocket, pagination, read state, and optimistic updates keep
working) and render **your own children that consume the SDK's context hooks**. Only drive the raw
`stream-chat` client directly (no providers) for a surface that isn't a channel view at all.

Entry-point hooks (confirm the current surface on the page before using - the API evolves):

| Hook | Gives you |
|---|---|
| `useChatContext()` | `client`, active `channel`, `setActiveChannel` |
| `useChannelStateContext()` | `messages`, `members`, `read`, `watcher_count`, `loadingMore`, `hasMore`, `thread` |
| `useChannelActionContext()` | `sendMessage`, `editMessage`, `removeMessage`, `loadMore`, `openThread`, `jumpToMessage` |
| `useMessageContext()` | `message`, `isMyMessage()`, `handleReaction`, `handleDelete`, `handleOpenThread`, ... |
| `useComponentContext()`, `useTypingContext()` | injected components; who is typing |

Provider-less fallback (non-channel surfaces only): drive the client directly - `client.queryChannels(filter, sort, { watch: true, state: true })`, `channel.watch()`, `channel.on(event => ...)` (keep the returned `unsubscribe` for cleanup), `channel.sendMessage(...)`, `channel.countUnread()` / `channel.markRead()`. Read the **low-level client / API reference** index in [`docs-map.md`](docs-map.md) for the current surface.

**Strict mode:** still create the client with `useCreateChatClient()` ([`../RULES.md`](../RULES.md) >
Strict mode protection) - never `getInstance()` on the client. Any `channel.on(...)` subscription in
an effect must be torn down in cleanup.

## The headless path - Video

Build custom layouts from `useCallStateHooks()` (`useParticipants`, `useCameraState`,
`useMicrophoneState`, `useCallCallingState`, `useParticipantViewContext`, ... - confirm on the page).
**Keep `ParticipantView` even in a bespoke layout** - it binds the media track for you; only hand-bind
`participant.videoStream` / `audioStream` when you must. Keep `<StreamVideo>` / `<StreamCall>` mounted.

---

## Route each region to its live page (do not mirror)

For every region you hand-build, **fetch the matching page from [`docs-map.md`](docs-map.md) first** -
it carries the current props, hook names, and the canonical customization pattern. The bespoke build
is then "consume the hook above + render your own markup to match the target."

| Bespoke region | Fetch first (row in `docs-map.md`) |
|---|---|
| Custom message row | Chat cookbook -> **Message UI** |
| Custom composer / input | Chat cookbook -> **Message Composer UI** |
| Reactions set / selector | Chat cookbook -> **Reactions Customization** |
| Channel list item / preview | Chat cookbook -> **Channel List UI** |
| Channel header | Chat cookbook -> **Channel Header** |
| Message actions / context menu | Chat cookbook -> **Message Actions** |
| Search | Chat cookbook -> **Search Customization** |
| Custom call controls | Video cookbook -> **Replacing Call Controls** |
| Custom call layout | Video index -> `ui-cookbook/<slug>.md` (fetch the index) |

---

## Completion contract - fill before you ship (do NOT skip rows)

Replacing a prebuilt region means you inherit **every** sub-feature it rendered. This is not a
reminder, it's a checklist: for the region you're building, **every row below is REQUIRED**. For each
row, do exactly one of:

- **Reproduce it** - reuse the named SDK piece; don't hand-roll.
- **`N/A - <why the design genuinely doesn't need it>`** - a real *design* reason (e.g. read receipts
  in anonymous livestream chat, threads in a flat ticker). **"Deferred", "later", "moving fast", and
  "out of scope for now" are NOT design reasons and are NOT valid `N/A`.**
- **`GAP - not implemented`** - if you are skipping a genuinely-needed capability for time, label it in
  exactly those words so it stays visible. Never relabel a time-skip as `N/A`.

A blank row - or an `N/A` whose real reason is "deferred" - = incomplete. Confirm the exact current
component/prop names on the live page first ([`docs-map.md`](docs-map.md)) - the *capability list* here
is the durable part, the *names* come from the fetch.

**Custom message row (`MessageUI`):**

| Sub-feature | Reuse (don't hand-roll) | Status |
|---|---|---|
| Text: markdown, links, mentions, emoji | `<MessageText/>` - never raw `{message.text}` | [ ] |
| Attachments: image / file / video / voice / giphy | `<Attachment attachments={message.attachments}/>` | [ ] |
| Reactions: display + add | `<MessageReactions/>` + `handleReaction` | [ ] |
| Quoted / replied-to parent | render `message.quoted_message` preview | [ ] |
| Thread reply indicator | `<MessageRepliesCountButton/>` + `handleOpenThread` | [ ] |
| Read / delivery receipts (own messages) | `<MessageStatus/>` | [ ] |
| Edited / deleted state | `message.message_text_updated_at` / `message.deleted_at` | [ ] |
| Actions menu: reply / edit / delete / pin / flag | `<MessageActions/>` - not a dead `...` button | [ ] |
| Same-author grouping | `firstOfGroup` / `groupedByUser` from `useMessageContext()` | [ ] |
| Error / optimistic-send state | `message.status` / `message.error` | [ ] |

**Custom composer:** text input; attachments + upload (and removal); mentions / slash-commands
autocomplete; send (+ enter-to-send); voice recording (if enabled); edit-message mode.

**Custom call layout / controls:** each participant via `<ParticipantView/>` (don't hand-bind tracks);
screenshare track; dominant-speaker / active state; camera + mic toggle (`useCameraState` /
`useMicrophoneState`); join / leave; device selectors (if shown).

Then **verify on seeded data** that triggers every ticked row (see Verify below) - a near-empty channel
hides every gap. Baseline testing showed that without this contract, agents drop attachments, quoted
replies, threads, and receipts almost every time, and each run drops a *different* set - so fill the
rows; don't trust recall.

---

## Implementation discipline (the curated gotchas)

- **Any BEM/class names in a docs example are a structural spec, not shippable CSS.** They tell you
  the elements + conditional states (`--active`, `--unread`, online presence, sent/delivered/read).
  Implement them with **Shadcn components + Tailwind utilities**; do not ship the BEM classes or
  hand-written CSS.
- **Reuse SDK pieces inside bespoke UI** (`Attachment`, `Avatar`, `ParticipantView`) instead of
  rebuilding them.
- **Keep the providers** (`<Chat>`/`<Channel>`, `<StreamVideo>`/`<StreamCall>`) unless the surface is
  genuinely not a channel/call view - that's what keeps the WebSocket, pagination, read state, and
  client lifecycle working.
- **Still docs-first, still no guessing.** Fetch the page this turn; never wire a hook/prop from
  memory ([`docs-map.md`](docs-map.md) > URL grounding).

## Verify

A bespoke surface isn't done until you run it and check it against the target. Seed data that triggers
**every** region (incoming + outgoing, a run of same-author messages so grouping shows, an attachment,
a reaction, a reply/thread, long text, a typing event), open the real screen on its actual navigation
path, compare region-by-region, and iterate. Match the target, don't approximate it.
