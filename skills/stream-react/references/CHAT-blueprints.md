# Chat - component blueprints (prebuilt-first)

Setup, routes, and gotchas: [CHAT.md](CHAT.md). Rules: [`../RULES.md`](../RULES.md) (reference authority, strict mode protection) and the cross-cutting [../../stream/RULES.md](../../stream/RULES.md) (secrets, no auto-seeding).

**Build the common path with `stream-chat-react`'s prebuilt components and customize via the documented hooks/props.** For fully hand-built, bespoke UI on the low-level client, see [`custom-ui.md`](custom-ui.md) - and even then, fetch the matching docs page first ([`docs-map.md`](docs-map.md)).

---

## Prebuilt components (default path)

**CSS (once, in `app/layout.tsx` or the AppShell):**
```ts
import 'stream-chat-react/css/index.css'; // v14+ preferred alias (v13 used dist/css/v2/index.css)
// If you use <EmojiPicker />, also import its stylesheet:
// import 'stream-chat-react/css/emoji-picker.css';
```

**Client (strict-mode-safe hook - never `getInstance()` on the client, [`../RULES.md`](../RULES.md) > Strict mode protection):**
```tsx
import { useCreateChatClient } from 'stream-chat-react';
const client = useCreateChatClient({ apiKey, tokenOrProvider: token, userData: { id: userId } });
if (!client) return null; // null until connected - gate rendering
```

**Provider hierarchy (the canonical layout):**
```tsx
import { Chat, ChannelList, Channel, Window, ChannelHeader,
  MessageList, MessageComposer, Thread } from 'stream-chat-react';

<Chat client={client} theme={theme /* str-chat__theme-dark | str-chat__theme-light from next-themes */}>
  <ChannelList filters={filters} sort={sort} options={options} />
  <Channel>
    <Window>
      <ChannelHeader />
      <MessageList />
      <MessageComposer />
    </Window>
    <Thread />
  </Channel>
</Chat>
```
`Chat` and `Channel` are context providers; every Stream component must be a child of `<Chat>`. **If you render `<ChannelList>`, do NOT pass a `channel` prop to `<Channel>`** (the list sets the active channel); without a list, pass `channel` explicitly.

| Component | Purpose | Key props |
|---|---|---|
| `Chat` | Root provider (client, active channel, theme, i18n) | `client` (req), `theme`, `i18nInstance`, `customClasses` |
| `ChannelList` | Queries + renders channel previews; click sets active channel | `filters`, `sort`, `options`, `showChannelSearch`, `setActiveChannelOnMount`, `customActiveChannel` |
| `Channel` | State/logic/UI for one channel; provides the channel contexts | `channel` (omit when using `ChannelList`), `EmptyPlaceholder`, `markReadOnMount`, `doSendMessageRequest` |
| `Window` | Main-panel wrapper; adds the `str-chat__main-panel--thread-open` class when a `Thread` is open (it does not itself hide children) | `thread` (optional) |
| `MessageList` | Standard scrollable message list | `Message` (per-list custom UI), `messageActions`, `disableDateSeparator`, `hideDeletedMessages` |
| `VirtualizedMessageList` | Virtualized variant for high-volume channels | same message-level props + `stickToBottomScrollBehavior`, `additionalVirtuosoProps` (`defaultItemHeight` is deprecated - pass it via `additionalVirtuosoProps`) |
| `MessageComposer` | Composer + default input UI (v14 name; **not** `MessageInput`) | `audioRecordingEnabled`, `overrideSubmitHandler`, `hideSendButton`, `minRows`/`maxRows` |
| `Thread` | Parent message + replies (own list + composer) | `Message`, `virtualized`, `additionalMessageListProps` |
| `Message` | Single-message logic + `MessageContext` (rarely rendered directly) | `message`, `Message` (custom UI), `showAvatar` |
| `ChannelHeader` | Default channel header bar | `title`, `image`, `Avatar` |

**Customization (v14 mechanism):** register custom UI through the `WithComponents` provider, which writes to `ComponentContext` for its subtree - **not** via per-component `Avatar`/`Input`/`Message` props on `<Channel>`:
```tsx
import { WithComponents } from 'stream-chat-react';
<WithComponents overrides={{ Avatar: CustomAvatar, MessageComposerUI: CustomInput, MessageUI: CustomMessage }}>
  <Channel>...</Channel>
</WithComponents>
```
`MessageUI` is the canonical `ComponentContext` key for a custom message component (`Message` still works as a deprecated alias). `MessageList`, `VirtualizedMessageList`, and `Thread` still accept a per-list `Message={CustomMessage}` prop for a one-off override. Read state with the documented hooks: `useChatContext()` (`client`, `channel`, `setActiveChannel`), `useChannelStateContext()` (`messages`, ...), `useChannelActionContext()` (`sendMessage`, `openThread`), `useMessageContext()` (`message`, `isMyMessage()`, ...), `useComponentContext()`, `useTypingContext()`.

**Bonus:** `ChatView` (+ `ChatView.Selector` / `.Channels` / `.Threads`) and `ThreadList` / `ThreadListItem` for a channel/thread switcher.

**Beyond the common path (docs-first expansion points)** - features the blueprints above don't cover; fetch the matching [`docs-map.md`](docs-map.md) row before building:
- **Polls** - prebuilt `Poll` component; create / vote (needs `polls` enabled on the channel type)
- **AI assistant / streaming responses** - typewriter effect + `AIStateIndicator` (AI Integrations, LangChain, Vercel AI SDK)
- **Voice messages** - record in the composer (`audioRecordingEnabled`) and play back the voice-recording attachment
- **Shared location** - static + live location messages
- **Message reminders** - "remind me" / saved-for-later
- **Blocking users** - block / unblock a user
- **Threads manager** - `ChatView` channel/thread switcher + `ThreadList` (unread-threads inbox)
- **Moderation bounce** - let a user review / edit / retry their own message bounced by moderation (`MessageBounce`)

**Docs-first:** for any customization (custom message UI, theming, reactions, composer UI, channel header, search, AI, ...) fetch the matching page from [`docs-map.md`](docs-map.md) before writing - the prebuilt props and customization API evolve. Component reference pages live at `https://getstream.io/chat/docs/sdk/react/components/{category}/{component}.md`.

### v14 renamed / moved exports (confirm against the installed package, don't trust memory)

These moved between majors and are the common grounding-time surprises. Still run the runnable export check ([`custom-ui.md`](custom-ui.md) > Ground the symbol) - this table is a head start, not a substitute.

| You may reach for | v14 reality |
|---|---|
| `MessageInput` | Renamed -> `MessageComposer` (the React component; distinct from the `MessageComposer` state class in `stream-chat`). |
| `ChannelPreview` + `Preview=` prop | Renamed -> `ChannelListItem`; custom preview is registered via `WithComponents` key **`ChannelListItemUI`** (props: `channel`, `active`, `displayTitle`, `displayImage`, `latestMessagePreview`, `lastMessage`, `unread`, `muted`, `pinned`, `messageDeliveryStatus`, `setActiveChannel`). |
| Custom message component key | `WithComponents` key **`MessageUI`** (`Message` still works as a deprecated alias). |
| `MessageOptions` (hover toolbar) | Removed / not exported - use **`MessageActions`** (renders react + reply + dropdown; reads `MessageContext`). |
| `EmojiPicker` from `stream-chat-react` | Moved to the **`stream-chat-react/emojis`** submodule; needs the `emoji-mart` + `@emoji-mart/data` + `@emoji-mart/react` peer deps. Register via `WithComponents` `{ EmojiPicker }` and import `stream-chat-react/css/emoji-picker.css`. |
| Voice-message MP3 encoding | `encodeToMp3` from **`stream-chat-react/mp3-encoder`** (needs `@breezystack/lamejs`); pass via `<MessageComposer audioRecordingConfig={{ transcoderConfig: { encoder: encodeToMp3 } }} audioRecordingEnabled />`. Recording works without it (wav); the encoder just shrinks files. |
| Poll instance for a custom row | `message.poll` is response data, not a `Poll` instance - get the instance with `client.polls.fromState(message.poll_id)` and render `<Poll poll={...} />`. |
| `firstOfGroup` / `endOfGroup` | Set by the **virtualized** list only; `undefined` in the regular `<MessageList>` (see [`custom-ui.md`](custom-ui.md) grouping row). |

---

## Fully custom UI (fallback)

For fully hand-built, bespoke UI on the low-level client - when the prebuilt components above can't be customized into the target - see [`custom-ui.md`](custom-ui.md): the prebuilt-vs-bespoke decision, the headless context-hook map, and per-region routing to the live docs. Don't hand-build a messenger you could have themed; default to the prebuilt path above.
