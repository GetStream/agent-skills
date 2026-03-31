# Feeds - Setup & Integration

Setup, server routes, client patterns, and gotchas for Feeds v3. For full component structure and wiring, see [FEEDS-blueprints.md](FEEDS-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, no auto-seeding, login screen first, strict mode protection).

- **Blueprint** - HTML with BEM classes defining structure and conditional rendering
- **Wiring** - API calls to read/write each element, exact property paths
- **Requirements** - Dashboard settings, API params, and prerequisites

## Quick ref

- **Packages:** Feeds + Stream client per Wiring; server often `@stream-io/node-sdk`.
- **First:** **App Integration** → **Setup** for feeds CLI and app config.
- **Per feature:** Activity, Composer, Feed, … - open the matching section only.
- **Below the next rule:** full blueprints - **do not load past it** until you implement that component.

Full component blueprints: [FEEDS-blueprints.md](FEEDS-blueprints.md) - load only the section you are implementing.

---

## App Integration

Everything needed to wire the UI components above into a working Next.js application.

### Setup

**Package:** `@stream-io/node-sdk` (server-side only)

**Feeds v3 has no client-side SDK.** All feed operations go through your own API routes using the server-side `@stream-io/node-sdk`. The client uses `fetch()` to call these routes. Do NOT install `getstream` - it targets legacy v1/v2.

**CLI commands:**
```bash
stream api GetOrCreateFeedGroup id=user
stream api GetOrCreateFeedGroup id=timeline
stream api GetOrCreateFeedGroup id=notification
stream api ListFeedGroups  # verify
```

### Server Helper - `lib/feeds.ts`

Singleton `StreamClient` wrapper. Does NOT include seed data by default - the app starts clean.

```ts
import { StreamClient } from "@stream-io/node-sdk";
const client = new StreamClient(process.env.STREAM_API_KEY!, process.env.STREAM_API_SECRET!);
```

See RULES.md › No auto-seeding.

### API Routes

| Route | Method | Params | Action | Response |
|---|---|---|---|---|
| `/api/token` | GET | `?user_id=xxx` | Upsert the requesting user only (`client.upsertUsers([{ id, name }])`), generate token via `client.generateUserToken({ user_id })`. Do NOT seed demo users or content. | `{ feedToken, apiKey }` |
| `/api/feed/get` | GET | `?user_id=xxx` | `client.feeds.getOrCreateFeed({ feed_group_id: "user", feed_id: "community", user_id, limit: 25 })` | `{ activities: [...] }` |
| `/api/feed/post` | POST | `{ userId, text }` | `client.feeds.addActivity({ feeds: ["user:community"], type: "post", text, user_id })` | `{ activity }` |
| `/api/feed/react` | POST | `{ activityId, userId, remove? }` | If `remove`: `deleteActivityReaction({ activity_id, type: "like", user_id })`. Else: `addActivityReaction(...)` | `{ reaction }` or `{ removed: true }` |
| `/api/feed/comment` | GET | `?activityId=xxx` | `client.feeds.getComments({ object_id, object_type: "activity" })` | `{ comments: [...] }` |
| `/api/feed/comment` | POST | `{ activityId, userId, text }` | `client.feeds.addComment({ object_id, object_type: "activity", comment: text, user_id })` | `{ comment }` |

### Client Patterns

- **Login Screen first:** See RULES.md › Login Screen first + [builder-ui.md](../builder-ui.md) > Login Screen.
- **App Header:** Show the current username + avatar (initial letter) + "Switch User" in a persistent header above the feed. See [`builder-ui.md`](../builder-ui.md) → App Header.
- **Polling:** Fetch feed every 5 seconds via `setInterval`, refresh after posting
- **Optimistic UI:** Toggle like state + count immediately, rollback on API error
- **Strict mode:** See RULES.md › Strict mode protection.

### Gotchas

- Feed response shape: `data.activities` array (NOT `data.content.results`)
- `created_at` is ISO 8601 string (e.g. `"2026-03-06T15:27:41.610Z"`) - use `new Date(ts).getTime()`
- Like count: `activity.reaction_groups.like.count` (NOT `reaction_counts`)
- Own like check: `activity.own_reactions` array, look for `type === "like"`
- Comment body in **response**: `comment.text` (NOT `comment.comment`)
- Comment body in **request**: `comment` param (NOT `text`)
- **`addComment` response is nested**: returns `{ comment: { id, text, user, ... }, duration, metadata }` - unwrap with `result.comment` to get the actual comment object
- **`client.feeds.deleteActivity({ id })` exists at runtime but TypeScript types don't expose it** - use `(client.feeds as any).deleteActivity({ id })` to bypass
- Author: `activity.user.name` / `activity.user.id` (enriched automatically in v3)
- Users must exist (via `client.upsertUsers([...])`) before adding activities
- `upsertUsers` takes an **array** of user objects (NOT an object keyed by ID)
