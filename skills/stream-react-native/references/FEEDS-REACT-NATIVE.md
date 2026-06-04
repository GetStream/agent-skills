# Feeds React Native - Setup and Integration

Stream Feeds React Native (`@stream-io/feeds-react-native-sdk`) provides a **headless** activity feed SDK - there are no pre-built UI components. You build every screen yourself against reactive contexts (`StreamFeeds`, `StreamFeed`) and state hooks (`useFeedActivities`, `useActivityComments`, `useOwnFollows`, etc.). This file covers package install, client/auth, core hooks and contexts, follow graph, comments, notification feeds, and gotchas. For `llms.txt` docs lookup, see [DOCS.md](DOCS.md). For screen structure, see [FEEDS-REACT-NATIVE-blueprints.md](FEEDS-REACT-NATIVE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (Feeds is bundled alongside Chat and Video; New Architecture; secrets; runtime lane; provider placement; blueprint reads on every turn).

Manifest-selected docs are the authority. Use [DOCS.md](DOCS.md) before installing packages or making API-specific claims.

---

## Quick ref

| Area | Value |
|---|---|
| Package | `@stream-io/feeds-react-native-sdk` (same package for RN CLI and Expo) |
| Required peer | `@react-native-community/netinfo` |
| RN version | >= 0.73 |
| Expo SDK | >= 51 |
| React | >= 17 |
| Pre-built UI | None - SDK is headless |
| Live docs | `https://getstream.io/activity-feeds/docs/react-native/` |

First path:

1. Use [DOCS.md](DOCS.md) to fetch the manifest-selected `Installation` page and verify npm dist-tags.
2. Install `@stream-io/feeds-react-native-sdk` and `@react-native-community/netinfo`.
3. Wire `useCreateFeedsClient(...)` and mount `<StreamFeeds client={client}>` near the app root.
4. Create `Feed` instances with `client.feed(group, id)` and load them with `feed.getOrCreate({ watch: true })`.
5. Render UI from state hooks (`useFeedActivities`, `useActivityComments`, `useOwnFollows`, ...).

Full screen blueprints: [FEEDS-REACT-NATIVE-blueprints.md](FEEDS-REACT-NATIVE-blueprints.md). Load only the section you are implementing.

---

## App Integration

### Installation

RN CLI:

```bash
npm view @stream-io/feeds-react-native-sdk version dist-tags --json
npm install @stream-io/feeds-react-native-sdk @react-native-community/netinfo
npx pod-install
```

Expo:

```bash
npm view @stream-io/feeds-react-native-sdk version dist-tags --json
npx expo install @stream-io/feeds-react-native-sdk @react-native-community/netinfo
```

Use `@latest` only after confirming the npm dist-tag matches the selected docs. The Feeds package is the same across RN CLI and Expo - there is no separate `-expo` package as Chat has.

Feeds has no Reanimated, gesture-handler, or SVG requirement of its own. If you also wire Chat or Video, those products bring their own peer set.

### Client setup

Use `useCreateFeedsClient` for client creation and connection. It returns `undefined` while connecting and an instance of `FeedsClient` once the user is connected. Disconnection happens on cleanup.

```tsx
import {
  StreamFeeds,
  useCreateFeedsClient,
} from "@stream-io/feeds-react-native-sdk";

const client = useCreateFeedsClient({
  apiKey,
  tokenOrProvider,
  userData: { id: userId, name: userName, image: userImage },
});

if (!client) return null;

return <StreamFeeds client={client}>{children}</StreamFeeds>;
```

`tokenOrProvider` can be a string user token or a function that returns `Promise<string>` (the SDK calls it again on reconnect when the cached token nears expiry).

### Token route pattern

Production apps should fetch tokens from a backend route that authenticates the request and derives the Stream `user_id` from the server's own session (cookie, JWT subject, OAuth identity). The client never sends `user_id` to the token endpoint:

```ts
// Server-side only
import { FeedsClient as ServerFeedsClient } from "@stream-io/node-sdk";

const serverClient = new ServerFeedsClient(apiKey, apiSecret);
await serverClient.upsertUsers({ users: { [userId]: { id: userId, name: userName } } });
const token = serverClient.createToken(userId, /* exp */ undefined, /* iat */ undefined);
```

Client `tokenOrProvider` shape:

```ts
const tokenOrProvider = async () => {
  const res = await fetch("https://your-api.example.com/feeds-token");
  const body = await res.json();
  return body.token as string;
};
```

Local demo tokens can come from [`../credentials.md`](../credentials.md) (`stream token <user_id>`).

---

## Core contexts, components, and hooks

| Symbol | Use |
|---|---|
| `useCreateFeedsClient` | Creates client, connects user, returns `FeedsClient | undefined`, disconnects on cleanup |
| `StreamFeeds` | Top-level context provider; pass `client` prop |
| `StreamFeed` | Per-feed context provider; pass `feed` prop so descendant hooks resolve the feed from context |
| `StreamActivityWithStateUpdates` | Per-activity context provider; pass `activityWithStateUpdates` prop |
| `StreamSearch` | Search controller context |
| `StreamSearchResults` | Single search source context |
| `useFeedsClient` | Reads the `FeedsClient` from `StreamFeeds` |
| `useFeedContext` | Reads the `Feed` from `StreamFeed` |
| `useClientConnectedUser` | Returns the connected user (or `null` while connecting) |
| `useWsConnectionState` | Returns `{ is_healthy }` for the WebSocket |
| `useFeedActivities` | Reactive activity list + pagination for a feed |
| `useActivityComments` | Reactive comments + pagination for an activity (or a parent comment for nested replies) |
| `useFollowers` | Reactive followers + pagination |
| `useFollowing` | Reactive following + pagination |
| `useOwnFollows` | `FollowResponse`s from feeds the current user owns toward a given feed |
| `useOwnFollowings` | Inverse - follows from the feed owner toward the current user's feeds |
| `useMembers` | Reactive member list + pagination for group feeds |
| `useAggregatedActivities` | Reactive grouped activities for notification feeds |
| `useNotificationStatus` | Reactive unread/unseen counts + read/seen activity ids |
| `useOwnCapabilities` | Permissions the current user has on a feed |
| `useSearchQuery` / `useSearchSources` / `useSearchResult` | Reactive search state |
| `useStateStore` | Generic selector hook over a state store (escape hatch when no dedicated hook fits) |

State hooks accept an optional argument (`feed`, `activity`, `searchController`, `source`). When omitted, the hook resolves it from the nearest matching context provider.

---

## Feeds and feed identifiers

A feed is identified by a `(group, id)` pair. Standard built-in groups:

| Group | Purpose |
|---|---|
| `user` | A user's own posts |
| `timeline` | Aggregates activities from feeds the timeline follows |
| `notification` | Aggregated notifications (likes, follows, comments, mentions) |
| `foryou` | Algorithmic "popular" feed - no real-time updates |

Create a `Feed` handle (no network call):

```ts
const userFeed = client.feed("user", userId);
const timeline = client.feed("timeline", userId);
const notificationFeed = client.feed("notification", userId);
const forYou = client.feed("foryou", userId);
```

Load and watch a feed:

```ts
// Required for real-time updates on regular feeds
await userFeed.getOrCreate({ watch: true });
await timeline.getOrCreate({ watch: true });

// `foryou` uses selector-driven content (following + popular + interest).
// It does NOT support watch (passing watch: true is a silent no-op) AND it
// returns empty in a fresh single-user app because there is no follow /
// popularity / interest signal yet. For a general "Explore / Discover" tab
// you almost certainly want `client.queryActivities(...)` instead - see
// below. Only use `foryou` once the app has real follow/popularity signal.
await forYou.getOrCreate({ limit: 10 });
```

`feed.getOrCreate()` is idempotent. Call it again to refresh the feed state. After a WebSocket reconnect, the SDK automatically re-fetches any feed that was previously loaded with `watch: true`.

### Exploring across feeds (`queryActivities`)

For an "Explore" / "Discover" / "newest posts across the app" view, use `client.queryActivities(...)` instead of any feed group. It is purpose-built for "exploratory search and filtering across all activities" (per the live docs) and respects activity visibility rules.

```ts
const res = await client.queryActivities({
  sort: [{ field: "created_at", direction: -1 }], // newest first
  limit: 20,
  // Optional filter. Field is `activity_type` (NOT `type` - that is a different
  // field used internally; a filter on `type` silently matches zero rows).
  // filter: { activity_type: "post" },
});
const activities = res.activities; // ActivityResponse[]
const nextCursor = res.next;       // pass back as { next } for the next page
```

Unlike a feed, `queryActivities` returns a one-shot response. Manage state locally (a `useState<ActivityResponse[]>` plus a `next` cursor) rather than relying on `<StreamFeed>` and `useFeedActivities`. Pagination passes the prior response's `next`; pull-to-refresh re-issues the query without `next`.

### Self-follow

A user's own posts only appear on their own timeline when the timeline follows the user feed. Set this up once after both feeds load:

```ts
const alreadyFollows = userFeed.currentState.own_follows?.find(
  (follow) => follow.source_feed.feed === timeline.feed,
);
if (!alreadyFollows) {
  await timeline.follow(userFeed.feed);
}
```

This is typically done from the backend, but doing it client-side is acceptable for demos. The call is idempotent.

---

## Activities

### Post an activity

```ts
await feed.addActivity({
  text: "Hello world",
  type: "post",
});
```

Useful fields on the `addActivity` request: `text`, `type` (required string), `attachments`, `custom`, `mentioned_user_ids`, `visibility`, `expires_at` (ISO timestamp - turns the activity into a story).

### Read activity data

`ActivityResponse` key fields (read from `useFeedActivities` or any reactive list):

| Field | Use |
|---|---|
| `id` | Stable id |
| `text` | Optional post text |
| `type` | Activity type |
| `user` | Author |
| `created_at` / `updated_at` | Timestamps |
| `attachments` | Image / video / file attachments |
| `reaction_groups` | `{ [type]: { count, ... } }` |
| `own_reactions` | Reactions the current user added |
| `comment_count` | Total comments |
| `current_feed` | The feed this activity was posted to (useful in Reddit-style apps with separate feed and user identities) |
| `parent` | Original activity for reposts |
| `expires_at` | ISO string - set for stories |
| `custom` | Custom JSON |

### Update and delete

```ts
await feed.updateActivity({ id: activity.id, text: "Updated text" });
await client.deleteActivities({ ids: [activity.id] });
```

---

## Reactions

Reactions live on the **client**, not on the `Feed` (unlike Flutter / Swift Feeds).

```ts
// Add a reaction
await client.addActivityReaction({
  activity_id: activity.id,
  type: "like",
  // optional: enforce_unique replaces any previous reaction by this user
  enforce_unique: true,
});

// Remove a reaction
await client.deleteActivityReaction({
  activity_id: activity.id,
  type: "like",
});

// Read
const hasLiked = (activity.own_reactions?.length ?? 0) > 0;
const likeCount = activity.reaction_groups?.like?.count ?? 0;
```

The `type` is any string you choose (`"like"`, `"heart"`, `"clap"`, ...). Comment reactions use `client.addCommentReaction` / `client.deleteCommentReaction` with the same shape but a `comment_id` field.

State updates are reactive: the UI re-renders automatically when an activity's reactions change as long as the rendering hook (e.g. `useFeedActivities`) is mounted under the right context.

---

## Follow graph

Follow and unfollow are called on the source `Feed` (typically the user's `timeline`):

```ts
// Follow (string form - "group:id")
await timeline.follow("user:tom");

// Follow with extra fields
await timeline.follow("user:tom", {
  push_preference: "all",
  custom: { reason: "investment" },
});

// Unfollow
await timeline.unfollow("user:tom");

// Update an existing follow without an instance
await client.updateFollow({
  source: `timeline:${currentUserId}`,
  target: "user:tom",
  push_preference: "none",
});
```

After follow / unfollow, reload the timeline to pull or remove activities:

```ts
await timeline.getOrCreate({ watch: true });
```

Read follow state with `useOwnFollows` (own feeds -> target feed) or `useOwnFollowings` (target feed owner -> own feeds). A `FollowResponse` has `source_feed`, `target_feed`, and `status` (`"accepted"`, `"pending"`, `"rejected"`).

### Follow requests

For feeds with `data.visibility: "followers"`, `follow()` returns a `pending` status until the target accepts:

```ts
await targetClient.acceptFollow({ source: sourceFeed.feed, target: targetFeed.feed });
await targetClient.rejectFollow({ source: sourceFeed.feed, target: targetFeed.feed });
```

### Follow suggestions

```ts
const suggestions = await client.getFollowSuggestions({
  feed_group_id: "user",
  limit: 10,
});
```

---

## Comments

Comments live on activities (and can be threaded under a parent comment).

```ts
// Add a comment
await client.addComment({
  object_id: activity.id,
  object_type: "activity",
  comment: "Nice post!",
  // For a reply, set parent_id to the parent comment's id
  parent_id: parentCommentId,
});

// Update / delete
await client.updateComment({ id: commentId, comment: "Edited" });
await client.deleteComment({ id: commentId });

// React to a comment
await client.addCommentReaction({ comment_id: commentId, type: "like" });
await client.deleteCommentReaction({ comment_id: commentId, type: "like" });
```

Read comments with `useActivityComments`:

```tsx
const {
  comments,
  comments_pagination,
  has_next_page,
  is_loading_next_page,
  loadNextPage,
} = useActivityComments({ feed, activity, parentComment });
```

When you are inside `<StreamFeed>` and `<StreamActivityWithStateUpdates>` providers, both `feed` and `activity` resolve from context and can be omitted.

### Activity details (e.g. comments modal)

When you navigate to a screen that needs to show comments for an activity that may not be in the current feed (an explore tap, a deep link), use `client.activityWithStateUpdates(id)`. This returns an `ActivityWithStateUpdates` handle that subscribes to live state for that activity and can be disposed on unmount.

**Critical:** pass a `comments` request to `get(...)`. Without it, `get()` fetches the activity itself but does **not** hydrate `state.comments_by_entity_id[activityId]`, which is the state slice `useActivityComments` reads from. The `comments` array on the raw activity response is a different field that the comment-rendering path does not consult - so calling bare `get()` results in an empty comment list even when the activity has comments.

```tsx
const activity = client.activityWithStateUpdates(activityId);
await activity.get({
  comments: {
    limit: 25,       // initial page size
    sort: "last",   // "first" | "last" | "top" | "controversial"
    depth: 2,        // how many reply levels to pre-hydrate
  },
});
// ... render with useActivityComments({ activity }) and useStateStore(activity.state, selector)
activity.dispose(); // on unmount - prevents the SDK from refetching after WS reconnect
```

Pass `activityId` (string) through navigation params - never serialize the full `ActivityResponse`.

### Sort options

`useActivityComments` accepts a `sort` argument on `loadNextPage`: `"first"`, `"last"`, `"top"`, `"controversial"`. See [Comments docs](https://getstream.io/activity-feeds/docs/react-native/comments.md) for details.

---

## Notification feed

The notification feed exposes aggregated activities (`aggregated_activities`) instead of individual ones, plus a `notification_status` with unread/unseen counts.

```tsx
const notificationFeed = client.feed("notification", currentUserId);

useEffect(() => {
  notificationFeed.getOrCreate({ watch: true });
}, [notificationFeed]);

const { aggregated_activities, is_loading, has_next_page, loadNextPage } =
  useAggregatedActivities(notificationFeed) ?? {};

const { unread, unseen, last_read_at, last_seen_at } =
  useNotificationStatus(notificationFeed) ?? {};
```

Mark as read / seen (note the snake_case parameter names - this is the JS SDK):

```ts
// Mark all read or seen
await notificationFeed.markActivity({ mark_all_read: true });
await notificationFeed.markActivity({ mark_all_seen: true });

// Mark specific activity groups
await notificationFeed.markActivity({ mark_read: [groupId] });
await notificationFeed.markActivity({ mark_seen: [groupId] });
```

---

## Search

The SDK exposes a `SearchController` plus three search sources:

```tsx
import {
  ActivitySearchSource,
  FeedSearchSource,
  SearchController,
  StreamSearch,
  UserSearchSource,
} from "@stream-io/feeds-react-native-sdk";

const client = useFeedsClient();
const searchController = useMemo(() => {
  if (!client) return undefined;
  return new SearchController({
    sources: [
      new ActivitySearchSource(client),
      new FeedSearchSource(client),
      new UserSearchSource(client),
    ],
    config: { keepSingleActiveSource: true },
  });
}, [client]);

return (
  <StreamSearch searchController={searchController}>
    {/* search UI; sources read via useSearchSources / useSearchResult */}
  </StreamSearch>
);
```

Inside `<StreamSearch>`, use `useSearchQuery`, `useSearchSources`, and `useSearchResult` to wire the UI.

---

## Real-time updates

The SDK opens a WebSocket as part of `connectUser`. State hooks observe state stores that are updated by incoming events, so well-wired UI updates without manual handling.

- Use `getOrCreate({ watch: true })` for any feed where you want to receive activity / reaction / comment events.
- `foryou` does not support `watch` (the popular selector is non-real-time).
- After a WebSocket reconnect, previously watched feeds and activities (`activityWithStateUpdates`) are re-fetched automatically. Always call `activity.dispose()` on screen unmount so the SDK does not keep refetching the activity after the page is closed.
- For explicit event subscriptions, use `feed.on(eventType, handler)` or `client.on(eventType, handler)` and return the unsubscribe function. See [Events docs](https://getstream.io/activity-feeds/docs/react-native/events.md).

---

## Error handling

Wrap promise-returning SDK calls in `try/catch`. The SDK does not log them or retry on its own.

For background SDK-initiated calls (refetching after reconnect, fetching `own_*` fields on a new activity), the SDK emits an `errors.unhandled` event after retries are exhausted:

```ts
client.on("errors.unhandled", (event) => {
  switch (event.error_type) {
    case UnhandledErrorType.ReconnectionReconciliation:
    case UnhandledErrorType.FetchingOwnFieldsOnNewActivity:
      // surface a connection-lost UI, optionally reconnect:
      reconnect();
      break;
    default:
      console.warn(`Unrecognized error ${event.error_type}`);
  }
});

const reconnect = async () => {
  await client.disconnectUser();
  await client.connectUser(currentUser, tokenOrProvider);
};
```

Hooks (including `useCreateFeedsClient`) rethrow connect errors during render so a React `ErrorBoundary` can catch them.

See [Error handling docs](https://getstream.io/activity-feeds/docs/react-native/error-handling.md) for the full event types and patterns.

---

## Selector rules (when using `useStateStore`)

When no dedicated hook fits, drop down to `useStateStore(stateStore, selector)`:

- **Keep selectors stable.** Define them at module scope or memoize with `useCallback` / `useMemo`. An unstable selector re-runs on every render and defeats the state store's diffing.
- **Return primitives or stable references at the top level.** Selectors are compared with `Object.is` per top-level key. Don't build new objects / arrays inside the selector. Do transformations (`reduce`, `map`, ...) in a separate `useMemo` outside.
- **Keep the keys constant between selections.** Don't add or remove top-level keys based on input.

See [Contexts and hooks docs](https://getstream.io/activity-feeds/docs/react-native/contexts-and-hooks.md) for the full selector rules.

---

## Gotchas

- **The SDK is headless.** There are no `FeedView`, `ActivityCard`, or `CommentList` components. Build every screen yourself against the state hooks - see [FEEDS-REACT-NATIVE-blueprints.md](FEEDS-REACT-NATIVE-blueprints.md).
- **Same package across RN CLI and Expo.** `@stream-io/feeds-react-native-sdk` works on both runtimes - there is no `-expo` variant.
- **`useCreateFeedsClient` returns `undefined` while connecting.** Always render `null` (or a spinner) until the client resolves; never pass `undefined` to `<StreamFeeds client={...}>`.
- **Built-in feed groups must exist in the dashboard.** `user`, `timeline`, `notification`, and `foryou` are pre-created on most apps, but custom groups need to exist before `feed.getOrCreate(...)` can use them.
- **`foryou` is selector-driven and renders empty for a fresh single-user app.** Its selectors are following + popular + interest; with no follows, no popularity signal, and no interest tags, the API succeeds but the activity list is empty by design. For a general Explore / Discover tab, use `client.queryActivities({ sort: [{ field: "created_at", direction: -1 }] })` instead. Reserve `foryou` for apps that already have real follow / popularity signal.
- **`queryActivities` filter field is `activity_type`, not `type`.** A `filter: { type: "post" }` clause silently matches zero rows because `type` here means a different internal field. Use `filter: { activity_type: "post" }` if you want only one activity type - or leave `filter` off entirely if you want every post.
- **`foryou` does not support real-time `watch: true`.** Passing `watch: true` is not an error but does nothing. Reload with `getOrCreate({ limit })` to refresh.
- **Self-follow is required.** A user's own posts go to their `user` feed and do not appear on their own `timeline` without a `timeline.follow("user:<id>")` relationship. Make this call idempotently on first run.
- **Reactions live on the client.** Use `client.addActivityReaction` / `client.deleteActivityReaction` (not `feed.addReaction` like Flutter / Swift).
- **For activity-details pages, use `client.activityWithStateUpdates(id)`.** Pass `activityId` (string) through navigation params, not the `ActivityResponse`. Call `activity.dispose()` on unmount so the SDK does not keep refetching after the screen closes.
- **`activityWithStateUpdates.get()` must be called with a `comments` request to populate the comment list.** Bare `get()` fetches the activity but does NOT hydrate `state.comments_by_entity_id[activityId]`, which is what `useActivityComments` reads from. The `comments` array on the raw activity response is a separate field that the rendering path does not consult. Always call `get({ comments: { limit, sort, depth } })` on a screen that renders comments.
- **`react-native-safe-area-context@5.7` `SafeAreaView` no-ops on RN 0.85 + Expo 56 + new architecture.** The JS render returns but the native inset never lands - content sits under the notch / home indicator. The `useSafeAreaInsets()` hook works because it reads via a different code path. Prefer `View` + `useSafeAreaInsets()` + explicit `paddingTop` / `paddingBottom` over `<SafeAreaView edges={...}>` on this toolchain, and add `paddingBottom: insets.bottom + N` to `FlatList` `contentContainerStyle` that sits under a native iOS tab bar.
- **JS uses snake_case for `markActivity` parameters.** `mark_all_read`, `mark_all_seen`, `mark_read`, `mark_seen` - not the camelCase shown in other SDKs.
- **Keep selectors stable in `useStateStore`.** Unstable selectors run on every render. Use module-scope selectors or memoize.
- **Never put the API secret in client code.** Token generation must happen server-side.
- **Never use dev tokens in production.** They disable token auth and let any client impersonate any user.
- **Imports come from `@stream-io/feeds-react-native-sdk`.** Don't import from `@stream-io/feeds-react-sdk` (the web variant) or `stream-feeds-js` (the lower-level package) by mistake.
