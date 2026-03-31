# SDK reference - cross-cutting patterns

Rules: [`RULES.md`](RULES.md) (secrets, strict mode protection, package manager). **CLI:** complete **[`SKILL.md`](SKILL.md) › Step 0a** before any workflow that needs the `stream` CLI.
Product-specific SDK wiring, gotchas, and client patterns: see `references/*.md` App Integration sections.

---

## Token endpoint pattern (all products)

`GET /api/token?user_id=xxx` - upsert the requesting user only (RULES.md › No auto-seeding), return per-product tokens.

**Combined token route** when multiple products are used:

```ts
// Returns whichever tokens the use case needs:
{ chatToken, videoToken, feedToken, apiKey }
```

## Server-side client instantiation

| Product | Package | Instantiation |
|---------|---------|---------------|
| Chat | `stream-chat` | `StreamChat.getInstance(apiKey, apiSecret)` - singleton OK server-side |
| Video / Feeds | `@stream-io/node-sdk` | `new StreamClient(apiKey, apiSecret)` |

**CRITICAL (Feeds v3):** Do NOT install `getstream` - it targets legacy v1/v2. Use `@stream-io/node-sdk` which has `client.feeds.*` methods. The namespace is `client.feeds` (plural), NOT `client.feed` (singular).

## Client-side instantiation

| Product | Package | Instantiation |
|---------|---------|---------------|
| Chat | `stream-chat` + `stream-chat-react` | `new StreamChat(apiKey)` - never `getInstance()` on client (RULES.md › Strict mode protection) |
| Video | `@stream-io/video-react-sdk` | `new StreamVideoClient({ apiKey, user: { id, name }, token })` |
| Feeds v3 | No client SDK | All operations via `fetch()` to your own API routes |

## CSS imports

```ts
// Chat
import 'stream-chat-react/dist/css/v2/index.css';
// Video
import '@stream-io/video-react-sdk/dist/css/styles.css';
```

## Theme hook (next-themes)

Use `useTheme()` from `next-themes` (scaffolded automatically) to read `resolvedTheme` and pass to Stream Chat:

```tsx
import { useTheme } from "next-themes";
const { resolvedTheme } = useTheme();
const theme = resolvedTheme === "dark" ? "str-chat__theme-dark" : "str-chat__theme-light";
<Chat client={client} theme={theme}>
```

## searchParams narrowing

`searchParams.get()` returns `string | null` - guard before passing to SDK methods.

## `upsertUsers` format

Both `StreamChat` and `StreamClient` take an **array** of user objects:

```ts
client.upsertUsers([{ id, name, role: 'user' }])  // NOT an object keyed by ID
```

## Moderation - CLI setup only

Moderation is configured via CLI during scaffold - NOT built as in-app UI. Review happens in the [Stream Dashboard](https://beta.dashboard.getstream.io). CLI commands: see `references/MODERATION.md` (App Integration → Setup).
