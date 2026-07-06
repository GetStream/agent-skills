# Chat - Setup & Integration

Stream Chat provides pre-built UI components via React, React Native, Flutter, Swift, and Kotlin SDKs. This file covers setup, server routes, client patterns, and gotchas. For the prebuilt component path (provider tree + props), see [CHAT-blueprints.md](CHAT-blueprints.md); when you write your own component for a region (even one, even via `Message=` / `WithComponents`) or go fully hand-built, see [custom-ui.md](custom-ui.md) (the completion contract).

Rules: [../RULES.md](../RULES.md) (login screen first, strict mode protection, reference authority) and the cross-cutting [../../stream/RULES.md](../../stream/RULES.md) (secrets, no auto-seeding).

- **Prebuilt path** ([CHAT-blueprints.md](CHAT-blueprints.md)) - the canonical provider tree, the prebuilt component prop table, and the `WithComponents` customization mechanism. The common path for every messenger.
- **Bespoke path** ([custom-ui.md](custom-ui.md)) - the prebuilt-vs-bespoke decision + the headless context-hook map for fully hand-built UI.
- **Live docs** ([docs-map.md](docs-map.md)) - fetch the matching component / cookbook / advanced page before building any customization. Server-side channel-type **defaults** (permissions, features) are set in the Dashboard / via the API, not enforced by the SDK.

## Quick ref

- **Packages:** `stream-chat`, `stream-chat-react`; import `stream-chat-react/css/index.css` (v14+ preferred alias; v13 used `dist/css/v2/index.css`).
- **First:** **App Integration** -> **Setup** (CLI / channel types) before UI.
- **Per feature:** fetch the matching live page from [docs-map.md](docs-map.md) before implementing that screen; for fully hand-built UI on the low-level client, see [custom-ui.md](custom-ui.md).

Prebuilt component path: [CHAT-blueprints.md](CHAT-blueprints.md) - the canonical provider tree + props. Bespoke UI on the low-level client: [custom-ui.md](custom-ui.md).

---

## App Integration

Everything needed to wire the UI components above into a working Next.js application.

### Setup

**Packages:** `stream-chat` + `stream-chat-react` (client), `stream-chat` (server via `StreamChat.getInstance`)

No CLI commands needed - built-in channel types (`messaging`, `team`, `livestream`) work out of the box.

### Server Routes

| Route | Method | Params | Action | Response |
|---|---|---|---|---|
| `/api/token` | GET | `?user_id=xxx` | `client.upsertUsers([{ id, name, role: 'user' }])`, `client.createToken(userId)` | `{ chatToken, apiKey }` |

See RULES.md > No auto-seeding.

```ts
import { StreamChat } from 'stream-chat';
const client = StreamChat.getInstance(process.env.STREAM_API_KEY!, process.env.STREAM_API_SECRET!);
```

### Client Patterns

- **Login Screen first:** See RULES.md > Login Screen first + [builder-ui.md](../builder-ui.md) > Login Screen.
- **App Header:** Show the current username + avatar (initial letter) + "Switch User" in a persistent header above the chat layout. See [`builder-ui.md`](../builder-ui.md) -> App Header.
- **Use `useCreateChatClient`:** the SDK ships an official hook that handles strict-mode, instantiation, `connectUser`, and cleanup. Never wire `connectUser`/`disconnectUser` manually - they race with strict-mode double-mount and produce *"You can't use a channel after client.disconnect was called"*.
  ```ts
  import { useCreateChatClient } from "stream-chat-react";
  const chatClient = useCreateChatClient({
    apiKey,
    tokenOrProvider: chatToken,
    userData: { id: userId, name },
  });
  if (!chatClient) return <Loading />;
  ```
- **Hoist `<Chat>` to AppShell:** mount `<Chat client={chatClient}>` once at the app root, alongside `<StreamVideo>` / `<StreamFeeds>`. Per-screen components only render `<Channel channel={...}>` from the existing client. **Never instantiate a new `StreamChat` per screen** - the cleanup of one screen's effect will disconnect the client another screen is still using. See [`CROSS-PRODUCT.md`](CROSS-PRODUCT.md) for the full multi-product AppShell skeleton.
- **Channel switching:** the client is long-lived; only swap the `channel` prop on `<Channel>` when the conversation changes. On per-channel unmount call `channel.stopWatching()` - never `client.disconnectUser()`.
- **Theme:** `useTheme()` from `next-themes` - pass `str-chat__theme-dark` or `str-chat__theme-light` to `<Chat>` based on `resolvedTheme`.
- **Strict mode:** See RULES.md > Strict mode protection. `useCreateChatClient` already handles this for you.

### Gotchas

- Always generate real tokens server-side via `client.createToken()` - never `devToken()`
- `StreamChat.getInstance(apiKey, apiSecret)` is fine server-side (singleton OK)
- `client.channel(type, id, { name, image, members })` - the 3rd arg accepts custom channel data (`ChannelData`); Stream's own tutorial does `client.channel('livestream', 'spacex', { name, image })`.
- SDK uses module augmentation for custom data types. A custom channel field like `name` and a custom `channel.sendEvent({ type: 'bid.placed', ... })` both raise a type error by default. Declare custom fields and events using module augmentation and interface merging:
  ```ts
  import "stream-chat"
  declare module "stream-chat" {
    interface CustomChannelData {
      name?: string // add your custom channel fields here
    }
    interface CustomEventTypes {
      "bid.placed": true // your custom event type
    }
    interface CustomEventData {
      payload?: Record<string, unknown> // your custom event payload shape
    }
  }
  ```
- Listen for `user.banned` event to show banned state in UI
- Import `stream-chat-react/css/index.css` for default styles - the preferred aliased path (`dist/css/index.css` also resolves; v14+, the `/v2/` subpath was removed). If you use `EmojiPicker`, also import `stream-chat-react/css/emoji-picker.css`
- `MessageInput` was renamed/removed in v14 - use `MessageComposer` from `stream-chat-react` instead. Note: the React `<MessageComposer />` UI component is distinct from the `MessageComposer` *state class* in `stream-chat` (same name, different thing)
- Token endpoint as `GET /api/token?user_id=xxx`
- `upsertUsers` takes an **array** of user objects: `client.upsertUsers([{ id, name, role }])` - NOT an object keyed by ID
- `<Chat>` lives at app root; `<Channel>` is what swaps per conversation. Don't construct/destruct `StreamChat` per screen.
