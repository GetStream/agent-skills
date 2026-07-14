# Chat - Setup & Integration

Stream Chat provides pre-built UI components via React, React Native, Flutter, Swift, and Kotlin SDKs. This file covers setup, server routes, client patterns, and gotchas. For the prebuilt component path (provider tree + props), see [CHAT-blueprints.md](CHAT-blueprints.md); when you write your own component for a region (even one, even via `Message=` / `WithComponents`) or go fully hand-built, see [custom-ui.md](custom-ui.md) (the completion contract).

Rules: [../RULES.md](../RULES.md) (login screen first, strict mode protection, reference authority) and the cross-cutting [../../stream/RULES.md](../../stream/RULES.md) (secrets, no auto-seeding).

- **Prebuilt path** ([CHAT-blueprints.md](CHAT-blueprints.md)) - the canonical provider tree, the prebuilt component prop table, and the `WithComponents` customization mechanism. The common path for every messenger.
- **Bespoke path** ([custom-ui.md](custom-ui.md)) - the prebuilt-vs-bespoke decision + the headless context-hook map for fully hand-built UI.
- **Live docs** ([docs-map.md](docs-map.md)) - fetch the matching component / cookbook / advanced page before building any customization. Server-side channel-type **defaults** (permissions, features) are set in the Dashboard / via the API, not enforced by the SDK.

## Quick ref

- **Packages:** `stream-chat`, `stream-chat-react`; import `stream-chat-react/css/index.css` (paths + version variants + the `EmojiPicker` stylesheet: [`../sdk.md`](../sdk.md) > CSS imports).
- **First:** **App Integration** -> **Setup** (CLI / channel types) before UI.
- **Per feature:** fetch the matching live page from [docs-map.md](docs-map.md) before implementing that screen; for fully hand-built UI on the low-level client, see [custom-ui.md](custom-ui.md).

Prebuilt component path: [CHAT-blueprints.md](CHAT-blueprints.md) - the canonical provider tree + props. Bespoke UI on the low-level client: [custom-ui.md](custom-ui.md).

---

## App Integration

Everything needed to wire the UI components above into a working Next.js application.

### Setup

**Packages:** `stream-chat` + `stream-chat-react` (client), `stream-chat` (server via `StreamChat.getInstance`)

No CLI commands are needed for basic messaging - built-in channel types (`messaging`, `team`, `livestream`) work out of the box. **But several composer / message features are gated by a channel-type config flag AND a role capability, and the React layer no-ops silently when either is missing** (no thrown error, no console warning) - see Feature enablement below.

### Feature enablement (channel-type flags + capabilities)

This is the single biggest source of "the feature does nothing" bugs. Several Chat features are **off by default** on the built-in `messaging` type, or grant only owner-scoped permissions to the base `user` role. When a composer button is filtered out or a handler silently no-ops, the cause is almost always a missing channel-type flag or a missing `own_capability` - **not** the UI code, and the live docs describe the API without surfacing that the default type ships these off. Confirm with `getstream api chat GetChannelType --name messaging` and enable via `UpdateChannelType`.

| Feature | Channel-type flag | Capability the React layer checks | Enable (CLI) |
|---|---|---|---|
| Polls (composer poll action + `AttachmentSelector` filter) | `polls` (default **false** on `messaging`) | `send-poll` | `getstream api chat UpdateChannelType --name messaging --request '{"polls": true}'` |
| Reactions - add | (on by default) | `send-reaction` (from the `create-reaction` grant) | granted to `channel_member` by default |
| Reactions - remove (tap to un-react) | - | `delete-reaction` | grant `create-reaction` + `delete-reaction` to the `user` role (grants note below) |
| File / image uploads | `uploads` (default true) | `upload-file` | `UpdateChannelType --request '{"uploads": true}'` if disabled |

Other features follow the same shape - check `GetChannelType` before assuming the UI is wrong. The React gates that no-op silently: `AttachmentSelector` filters `createPoll` on `channelCapabilities["send-poll"] && channelConfig?.polls`; `useReactionHandler` early-returns unless `channelCapabilities["send-reaction"]`.

**Diagnose first:** read the *connected user's* `own_capabilities` on the channel (`channel.data?.own_capabilities`) - not the server-side query, which runs with admin context and shows an inflated set. A quick throwaway `StreamChat` client (`new StreamChat(apiKey, { allowServerSideConnect: true })` + a token from `/api/token` + `connectUser`) prints the real client capabilities.

**Editing grants safely:** to add a capability to a role, read the full grants first (`GetChannelType --jq '.grants'`), then resubmit the **entire** grants object with only the target role's array changed - a partial `{"grants":{"user":[...]}}` risks dropping the other roles. Take the exact capability strings from the existing grants (e.g. `create-reaction`, `delete-reaction`); never guess them.

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
- Import the Chat CSS once - the path, version variants, and the separate `EmojiPicker` stylesheet all live in [`../sdk.md`](../sdk.md) > CSS imports (the canonical home).
- `MessageInput` was renamed/removed in v14 - use `MessageComposer` from `stream-chat-react` instead. Note: the React `<MessageComposer />` UI component is distinct from the `MessageComposer` *state class* in `stream-chat` (same name, different thing)
- Token endpoint as `GET /api/token?user_id=xxx`
- `upsertUsers` takes an **array** of user objects: `client.upsertUsers([{ id, name, role }])` - NOT an object keyed by ID
- `<Chat>` lives at app root; `<Channel>` is what swaps per conversation. Don't construct/destruct `StreamChat` per screen.
- **Prebuilt components carry an opinionated default look.** The native `Poll` renders large + full-width and *inherits the message bubble background* (scope your own-message colour to `.str-chat__message-text-inner`, not `.str-chat__message-bubble`, or it bleeds onto polls/attachments). The `MessageComposer` placeholder defaults to "Send a message" (`additionalTextareaProps={{ placeholder }}` to change) and its attach button sits on the left. Group avatars show a single initial (no stacking). When the goal is matching a specific/bespoke design, follow [`design-matching.md`](design-matching.md) - the Classify -> Design analysis -> Route -> Ground -> Build -> Verify pipeline, with a v14 reskin cheat-sheet appendix and a capture-based verify gate (`tsc`/`build` passing is not visual parity).
- **`useCanCreatePoll()` is NOT "can this channel create polls".** It returns whether the *in-progress poll form* is valid to submit (has a name, ≥1 option, no errors) - i.e. it drives the poll dialog's submit button, and is `false` on an empty form. Do **not** gate poll menu-item visibility on it (the row will never appear). The `AttachmentSelector` already filters the `createPoll` action by capability + config; let it.
- **Reaction `type` must match `[A-Za-z0-9_.-]`.** Stream rejects emoji characters as a reaction type (`"reaction.type is not valid. Only alphanumeric, underscore, dash and dot characters are allowed"`). A custom reaction set uses slug types (`heart_eyes`, `tada`) mapped to emojis for display - never the emoji char as the `type`.
- **Reaction display filters by supported type.** `useProcessReactions` only renders reactions whose `type` is a key in `reactionOptions.quick`/`.extended`. A custom reaction set must register every type it can send, or valid reactions silently won't display. (If the prebuilt `<MessageReactions>` doesn't appear inside a heavily-custom message layout, rendering pills directly from `message.reaction_groups` + a `type → emoji` map is a reliable fallback.)
