# Stream React (web) - custom components + bespoke UI on the Stream client

**Read this whenever you write your OWN component or markup for a region a prebuilt component
normally renders - even a single region, and even when you wire it via the documented `Message=` /
`<WithComponents overrides={...}>` prop - OR when you go fully hand-built (the low-level client for a
non-messenger surface).** Passing props or theme tokens to a prebuilt component is NOT this file; just
fetch the page. (Exact predicate: [`../RULES.md`](../RULES.md) > Reference authority.)

The default is still **prebuilt-component-first**. This file carries two things: the *decision* (is
going custom even warranted? - Step 0) and, once you are writing a custom component, the **completion
contract** below (the sub-features you must reproduce so a custom region doesn't silently drop
attachments, reactions, receipts, threads). It does **not** mirror element markup - for every region
you build, fetch the matching live page from [`docs-map.md`](docs-map.md) first.

**Matching a reference design (screenshot / Figma)?** Run [`design-matching.md`](design-matching.md) for the region-by-region decompose -> map -> verify procedure; it routes back here for the completion contract on each custom region.

---

## Step 0: which level - and does the completion contract apply?

Stream's React SDKs ship rich prebuilt components built to be *customized*. There are **three
levels** - use the cheapest that reaches the design:

| Level | Mechanism | Completion contract? |
|---|---|---|
| **Theming** | CSS variables + the theme class (`str-chat__theme-light/dark`), `<Channel>` theming, Tailwind around the components | **No** - you replace no region. Fetch the page, pass props/tokens, done. |
| **Component injection** | Your OWN component for one region via `<WithComponents overrides={{ MessageUI, MessageComposerUI, Avatar, ... }}>` or `<MessageList Message={Custom} />` | **YES** - you render the region yourself, so you inherit its sub-features. Fill the contract below. |
| **Bespoke (headless)** | Your own React tree consuming the SDK's context hooks (or the raw `stream-chat` client) | **YES** - you own every region and every dropped sub-feature. |

**The gate is one question: are you writing your own component/markup for a region?** If **no**
(props + theme only) -> Theming row; you can stop reading here. If **yes** -> the **completion
contract** applies, whether it is one region via `WithComponents` or a whole bespoke tree. Do **not**
talk yourself out of it because "it's only one component" or "it's still basically the prebuilt app":
a single custom `MessageUI` is exactly the case that silently drops attachments / receipts / threads.

**Injection vs. fully-headless is an architecture choice, NOT a contract escape.** Prefer **component
injection** - keep the prebuilt tree, swap only the regions you must - over a fully-headless rebuild.
Go **fully headless** only when you'd be replacing the message row, composer, channel list, **and**
header at once, i.e. using the SDK purely as a data source for a non-messenger surface (a flat
ticker, an overlay, a livestream chat rail). Over-choosing headless is the common, expensive mistake
(you throw away typing indicators, receipts, reactions, threads, uploads, presence, optimistic send,
i18n). **When unsure, injection first** - and the contract still applies.

If it is genuinely unclear whether the user wants a custom component at all (vs. just a restyle), ask
one question:

> Do you want your own custom component(s) for specific regions, or just to restyle the prebuilt UI
> (colors / fonts / spacing) via theming?

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

### Custom channel rail: real-time contract

**Keep `<ChannelList>` as the state/event owner whenever component injection can reach the design.** It
already reconciles new membership, unloaded-message, removal, channel-update, and reconnect events.
If a bespoke rail is genuinely required (for example, product-grouped conversations), fetch the live
**ChannelList** page first and own that behavior explicitly: reconcile `notification.added_to_channel`,
`notification.message_new`, `message.new`, relevant channel add/remove/update events, and
`connection.recovered`; clean up the listener. **Do not wait for `message.new` to discover a new
channel**—a user can be added when a channel is created before anyone sends a message. Do not re-query
the full rail for read receipts alone.

## The headless path - Video

Build custom layouts from `useCallStateHooks()` (`useParticipants`, `useCameraState`,
`useMicrophoneState`, `useCallCallingState`, `useParticipantViewContext`, ... - confirm on the page).
**Keep `ParticipantView` even in a bespoke layout** - it binds the media track for you; only hand-bind
`participant.videoStream` / `audioStream` when you must. Keep `<StreamVideo>` / `<StreamCall>` mounted.

## The headless path - Feeds

Feeds is **always** headless - there are no prebuilt UI components, so **every** feeds region is a
custom component and the completion contract **always** applies (there is no theming-only escape). Build
from the SDK hooks; keep `<StreamFeeds>` / `<StreamFeed>` mounted and create the client with
`useCreateFeedsClient()` ([`../RULES.md`](../RULES.md) > Strict mode protection). Entry-point hooks
(confirm the current surface on the page before using - the API evolves):

| Hook | Gives you |
|---|---|
| `useFeedActivities(feed)` | `activities`, `is_loading`, `has_next_page`, `loadNextPage` |
| `useActivityComments({ feed, activity })` | `comments`, `has_next_page`, `is_loading_next_page`, `loadNextPage` |
| `useAggregatedActivities(feed)` / `useNotificationStatus(feed)` | grouped notifications; `unread` / `unseen` counts |
| `useOwnFollows(feed)` / `useFeedMetadata(feed)` | follow state; `follower_count` / `following_count` |

Writes go through the feed / client instance - `feed.addActivity(...)`, `client.addComment(...)`,
`client.addActivityReaction(...)`, `client.addBookmark(...)`, `feed.follow(...)`; confirm each on its
[`docs-map.md`](docs-map.md) Feeds row before wiring. The initial `useActivityComments` fetch needs a
one-shot `loadNextPage()` on mount (ref-guard carve-out - [`../RULES.md`](../RULES.md) > Strict mode).

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
| Empty / loading state (channel list, message list) | Chat cookbook -> **Channel List UI**; also the **MessageList** / **Channel** pages (`EmptyStateIndicator` / `LoadingIndicator`) |
| Channel header | Chat cookbook -> **Channel Header** |
| Message actions / context menu | Chat cookbook -> **Message Actions** |
| Search | Chat cookbook -> **Search Customization** |
| Custom call controls | Video cookbook -> **Replacing Call Controls** |
| Custom call layout | Video index -> `ui-cookbook/<slug>.md` (fetch the index) |
| Feed activity card | Feeds -> **Feeds**, **Activities** |
| Comment row / list | Feeds -> **Comments** |
| Feed composer / post box | Feeds -> **Activities** |
| Reaction / bookmark controls | Feeds -> **Reactions**, **Bookmarks** |
| Notification list | Feeds -> **Notification Feeds** |

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
| Poll message | `message.poll_id` → `client.polls.fromState(message.poll_id)` + `<Poll poll={poll}/>` - a custom row drops polls silently otherwise | [ ] |
| Reactions: display + add | `<MessageReactions/>` + `handleReaction`; if the prebuilt list doesn't render inside your layout, render pills from `message.reaction_groups` + a `type→emoji` map. Custom reaction types must be slugs (`[A-Za-z0-9_.-]`, **not** emoji chars) and registered in `reactionOptions` | [ ] |
| Quoted / replied-to parent | render `message.quoted_message` preview | [ ] |
| Thread reply indicator | `<MessageRepliesCountButton/>` + `handleOpenThread` | [ ] |
| Read / delivery receipts (own messages) | `<MessageStatus/>`; per-message ticks (WhatsApp-style) need `returnAllReadData` on `<MessageList>` - the default populates `readBy` **only on the latest-read message**, so every earlier row renders "delivered". Gray-ticks-everywhere-but-one is this, not CSS | [ ] |
| Edited / deleted state | `message.message_text_updated_at` / `message.deleted_at` | [ ] |
| Actions menu: reply / edit / delete / pin / flag | `<MessageActions/>` - not a dead `...` button | [ ] |
| Same-author grouping | `groupStyles` from `useMessageContext()` (regular `<MessageList>`); `firstOfGroup` / `endOfGroup` / `groupedByUser` are set by the **virtualized list only** and are `undefined` in the regular list - don't gate avatars/radii on them there. When neither is populated, compute grouping from the adjacent messages in `useChannelStateContext().messages` (same `user.id` within a short time window). | [ ] |
| Error / optimistic-send state | `message.status` / `message.error` | [ ] |

**Custom composer (`MessageComposerUI`):**

| Sub-feature | Reuse (don't hand-roll) | Status |
|---|---|---|
| Text input + send (+ enter-to-send) | composer input + submit handler; when matching a reference, use its **exact placeholder string** (e.g. `Message`, not the SDK default `Send a message`) | [ ] |
| Attachments: attach + upload + remove | upload handler + attachment previews | [ ] |
| Mentions / slash-command autocomplete | the SDK suggestion list | [ ] |
| Voice recording (if enabled) | enable `<MessageComposer audioRecordingEnabled/>`; a custom `MessageComposerUI` must render the swap itself - `recordingController.recordingState ? <AudioRecorder/> : <normal composer>` (from `useMessageComposerContext()`), start recording via `recordingController.recorder?.start()`. Optional mp3: `@breezystack/lamejs` + `encodeToMp3` from `stream-chat-react/mp3-encoder` | [ ] |
| Edit-message mode | composer edit state | [ ] |
| Typing events | `channel.keystroke()` / `channel.stopTyping()` | [ ] |

**Custom channel preview (`ChannelPreviewUI`):**

| Sub-feature | Reuse (don't hand-roll) | Status |
|---|---|---|
| Display name | channel display-name helper | [ ] |
| Last message: text + sender (attachment / deleted fallbacks) | latest of `channel.state.messages` / `lastMessage` | [ ] |
| Last-message timestamp | latest message `created_at` | [ ] |
| Unread count / badge | `unread` preview prop / `channel.countUnread()` | [ ] |
| Active / selected state | compare to `channel` from `useChatContext()`; `setActiveChannel` | [ ] |
| Avatar + online presence (DMs) | `<Avatar/>` + member `user.online` | [ ] |
| Muted / pinned / archived indicator | `channel.muteStatus()` / channel state | [ ] |

**Custom channel header:**

| Sub-feature | Reuse (don't hand-roll) | Status |
|---|---|---|
| Channel name / title | channel display name | [ ] |
| Member / online count or subtitle | `channel.state.members` / watcher count | [ ] |
| Typing indicator | `useTypingContext()` | [ ] |
| Avatar | `<Avatar/>` | [ ] |
| Back / close nav (mobile) | your router + `setActiveChannel(undefined)` | [ ] |
| Header actions (info / search / call) | as the design shows | [ ] |

**Custom call layout / controls:**

| Sub-feature | Reuse (don't hand-roll) | Status |
|---|---|---|
| Each participant | `<ParticipantView/>` - don't hand-bind tracks | [ ] |
| Screenshare track | the screen-share participant / track type | [ ] |
| Dominant-speaker / active state | participant state from `useCallStateHooks()` | [ ] |
| Mute / camera-off indicator (per participant) | `hasAudio(p)` / `hasVideo(p)` from `@stream-io/video-react-sdk` | [ ] |
| Camera + mic toggle | `useCameraState` / `useMicrophoneState` | [ ] |
| Join / leave | `call.join()` / `call.leave()` | [ ] |
| Device selectors (if shown) | `useCameraState().devices` (Observable-backed - subscribe, don't `.map` an array) | [ ] |

**Feeds contracts** (Feeds is headless, so one of these applies to **every** feeds surface you build -
same reproduce / `N/A` / `GAP` semantics; names come from the [`docs-map.md`](docs-map.md) Feeds rows):

**Custom feed activity card:**

| Sub-feature | Reuse (don't hand-roll) | Status |
|---|---|---|
| Author + avatar | `activity.user` (`.name ?? .id`, `.image`) | [ ] |
| Relative timestamp | `activity.created_at` | [ ] |
| Text + mentions / links | `activity.text` (docs User Mentions / URL Previews) | [ ] |
| Attachments | `activity.attachments` (`.type`, `.image_url`, `.asset_url`) | [ ] |
| Reaction count + own-state toggle | `activity.reaction_groups`, `activity.own_reactions`; `client.addActivityReaction` / `deleteActivityReaction` | [ ] |
| Comment count + open comments | `activity.comment_count`; `useActivityComments` | [ ] |
| Bookmark toggle | `activity.own_bookmarks`; `client.addBookmark` / `deleteBookmark` | [ ] |
| Repost (if shown) | per docs Activities - confirm the API before wiring | [ ] |
| Poll (if shown) | fetch docs Polls before building (no bundled blueprint) | [ ] |
| Pagination | `has_next_page` + `loadNextPage()` (wrap for onClick) | [ ] |
| Loading / empty state | `is_loading`; guard optional fields (`activities?`) | [ ] |

**Custom comment row:**

| Sub-feature | Reuse (don't hand-roll) | Status |
|---|---|---|
| Author / avatar / timestamp | `comment.user`, `comment.created_at` | [ ] |
| Text | `comment.text` | [ ] |
| Nested replies | `client.addComment({ parent_id })` (inherits `object_id` / `object_type`) | [ ] |
| Comment reactions (if shown) | per docs Reactions - confirm the API | [ ] |
| Initial fetch | `loadNextPage()` once on mount (ref-guard carve-out - [`../RULES.md`](../RULES.md) > Strict mode) | [ ] |
| Post a comment | `client.addComment({ object_id: activity.id, object_type: 'activity', comment })` - field is `comment`, NOT `text` | [ ] |

**Custom feed composer:**

| Sub-feature | Reuse (don't hand-roll) | Status |
|---|---|---|
| Text input + submit | `feed.addActivity({ type: 'post', text })` - note `feed.`, not `client.` | [ ] |
| Attachment upload / preview (if shown) | `client.uploadImage()` / `uploadFile()` -> URL in `attachments` | [ ] |
| Mentions (if shown) | per docs User Mentions | [ ] |
| Poll creation (if shown) | per docs Polls | [ ] |
| Post appears without reload | watched feed (`getOrCreate({ watch: true })`) | [ ] |
| Error / disabled state | `useFeedsClient` null-guard; disable submit when text empty | [ ] |

Then **verify against local fixtures** that trigger every ticked row (see Verify below) - a near-empty channel
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
- **Don't wrap the message bubble in a `<button>` or `<a>`.** The pieces you render inside it
  (`<Attachment/>` image gallery, link previews, poll actions) render their **own** interactive
  elements, so an outer button/anchor produces nested-interactive invalid HTML that breaks hydration
  and can stop attachments from rendering. Use a `<div>`; if the bubble itself needs a click (e.g.
  retry on a failed send), attach `onClick` to the div.
- **Keep the providers** (`<Chat>`/`<Channel>`, `<StreamVideo>`/`<StreamCall>`) unless the surface is
  genuinely not a channel/call view - that's what keeps the WebSocket, pagination, read state, and
  client lifecycle working.
- **Empty + loading states are their own regions.** `<ChannelList>` and `<MessageList>` / `<Channel>`
  render an `EmptyStateIndicator` (no channels / no messages) and a `LoadingIndicator` (while fetching);
  if the design shows a specific empty or loading screen, pass custom ones and reproduce them - a seeded
  or near-full channel hides both, so trigger them with fixtures (Verify below).
- **Still docs-first, still no guessing.** Fetch the page this turn; never wire a hook/prop from
  memory ([`docs-map.md`](docs-map.md) > URL grounding).
- **Ground the symbol before wiring it (runnable check).** Export names move between majors, so
  confirm the component / hook / prop actually exists in the *installed* package - not just in memory
  or a docs page for another version:
  ```bash
  # does the export exist in the installed SDK? (v14 vs v13 differ)
  node -e "console.log(Object.keys(require('stream-chat-react')).filter(k => /MessageComposer|MessageStatus|WithComponents/.test(k)))"
  # or grep the shipped type defs:
  grep -rl 'MessageComposer' node_modules/stream-chat-react/dist/*.d.ts
  ```
  If the name isn't there, you're on a different major - re-fetch the docs for the installed version
  ([`docs-map.md`](docs-map.md) Version note) before wiring.

## Verify

A bespoke surface isn't done until you run it and check it against the target. **Populate every region
with local mock / fixture data** (chat: incoming + outgoing, a run of same-author messages so grouping
shows, an attachment, a reaction, a reply/thread, long text, a typing event, an empty channel list, an empty message list, a
loading state; feeds: a card with
reactions + comments + an image, long text, a notification entry) - render your components against
hand-authored message / channel / activity objects, **not** by seeding the configured Stream app. The
no-auto-seeding rule ([`../../stream/RULES.md`](../../stream/RULES.md)) still holds: backend seeding to verify
needs the user's explicit confirmation **and** a disposable / dev app (see [`design-matching.md`](design-matching.md)
> The verify loop). Open the real screen on its actual navigation path, compare region-by-region, and
iterate. Match the target, don't approximate it.

**Drive the open / interaction states too** - the hover toolbar, the **thread panel opened** (its own
layout), the reaction selector, the actions menu, the composer with a staged attachment / in edit
mode. These don't render at rest; `hover()` / `click()` to reach them, and check the message bubble
doesn't move when its hover toolbar appears. Caveat: the **thread's own reply composer needs a real
channel context**, so a neutralized fixture channel throws when the thread opens - verify thread-open
against a real channel, or with a stand-in element carrying the real thread-container class for the
container-layout check.

**Chat fixture-channel recipe (local, no backend writes).** `client.channel(type, id)` returns a
client-side instance; populate its state and stub its network methods, then pass it to the *shipped*
layout (mount the real `AppShell` / shell layout - not a hand-rolled wrapper - see
[`design-matching.md`](design-matching.md) > Reuse the SHIPPED layout):

```ts
function neutralize(channel) { // stop it from hitting the backend
  const noop = async () => ({});
  Object.assign(channel, {
    watch: noop, query: noop, markRead: noop, keystroke: noop, stopTyping: noop,
    sendReaction: noop, sendMessage: async (m) => ({ message: m }), initialized: true,
  });
}
const ch = client.channel("messaging", "fixtures-dm");
ch.data = { ...ch.data, own_capabilities: ["send-message","upload-file","send-reaction","send-reply","read-events","typing-events"] };
ch.state.members = { [me]: { user: meUser }, sarah: { user: sarahUser } };
if (ch.state.messages.length === 0)                  // idempotency guard (see below)
  ch.state.addMessagesSorted([ /* incoming, outgoing, run-of-same-author, attachment, reaction, quoted, voice, long text */ ]);
neutralize(ch);
```

Two traps this recipe avoids:
- **Duplicate messages.** `client.channel(type, id)` is **cached by cid**, and React StrictMode
  double-invokes render/`useMemo`, so `addMessagesSorted` can run twice on the same instance -> every
  message renders twice. Guard with `if (ch.state.messages.length === 0)` (or build outside `useMemo`);
  don't rely on the factory running once.
- **Nested interactive elements** (see gotchas above) - don't wrap a fixture bubble in a `<button>`.
