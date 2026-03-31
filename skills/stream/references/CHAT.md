# Chat - Setup & Integration

Stream Chat provides pre-built UI components via React, React Native, Flutter, Swift, and Kotlin SDKs. This file covers setup, server routes, client patterns, and gotchas. For full component structure and wiring, see [CHAT-blueprints.md](CHAT-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no auto-seeding, login screen first, strict mode protection).

- **Blueprint** - HTML with BEM classes defining structure and conditional rendering
- **Wiring** - API calls to read/write each element, exact property paths
- **Requirements** - Dashboard settings, API params, and prerequisites

## Quick ref

- **Packages:** `stream-chat`, `stream-chat-react`; import `stream-chat-react/dist/css/v2/index.css`.
- **First:** **App Integration** → **Setup** (CLI / channel types) before UI.
- **Per feature:** Jump to section (Channel List, Message List, …) when implementing that screen.
- **Below the next rule:** full blueprints - **do not load past it** until you implement that component.

Full component blueprints: [CHAT-blueprints.md](CHAT-blueprints.md) - load only the section you are implementing.

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

See RULES.md › No auto-seeding.

```ts
import { StreamChat } from 'stream-chat';
const client = StreamChat.getInstance(process.env.STREAM_API_KEY!, process.env.STREAM_API_SECRET!);
```

### Client Patterns

- **Login Screen first:** See RULES.md › Login Screen first + [builder-ui.md](../builder-ui.md) > Login Screen.
- **App Header:** Show the current username + avatar (initial letter) + "Switch User" in a persistent header above the chat layout. See [`builder-ui.md`](../builder-ui.md) → App Header.
- **Instantiate:** `new StreamChat(apiKey)` - never `getInstance()` on client (breaks strict mode)
- **Connect:** `client.connectUser({ id, name }, token)` inside `setTimeout` with `mounted` guard
- **Theme:** `useTheme()` from `next-themes` - pass `str-chat__theme-dark` or `str-chat__theme-light` to `<Chat>` based on `resolvedTheme`
- **Disconnect:** `client.disconnectUser()` in useEffect cleanup
- **Strict mode:** See RULES.md › Strict mode protection.

### Gotchas

- Always generate real tokens server-side via `client.createToken()` - never `devToken()`
- `StreamChat.getInstance(apiKey, apiSecret)` is fine server-side (singleton OK)
- `client.channel("livestream", id)` - no third arg with `{ name }` (TS error in v9+)
- Listen for `user.banned` event to show banned state in UI
- Import `stream-chat-react/dist/css/v2/index.css` for default styles
- Token endpoint as `GET /api/token?user_id=xxx`
- `upsertUsers` takes an **array** of user objects: `client.upsertUsers([{ id, name, role }])` - NOT an object keyed by ID
