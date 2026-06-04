# Feeds React Native - Setup and Integration

Stream Feeds React Native (`@stream-io/feeds-react-native-sdk`) provides a **headless** activity feed SDK - there are no pre-built UI components. You build every screen yourself against reactive contexts (`StreamFeeds`, `StreamFeed`) and state hooks (`useFeedActivities`, `useActivityComments`, `useOwnFollows`, etc.). This file covers package install, optional dependencies, client/auth, core hooks and contexts, feed identifiers, activities, attachments/file uploads, reactions, follow graph, comments, notification feeds, navigation, push notifications, and gotchas. For `llms.txt` docs lookup, see [DOCS.md](DOCS.md). For screen structure, see [FEEDS-REACT-NATIVE-blueprints.md](FEEDS-REACT-NATIVE-blueprints.md).

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

### App-side helpers for common Feeds UI

**These are not Feeds SDK peers.** The Feeds SDK has exactly one mandatory peer (`@react-native-community/netinfo`) and **zero opt-in native integrations** - none of the packages below plug into the SDK, unlike Chat where `@op-engineering/op-sqlite` powers `enableOfflineSupport`, `@shopify/flash-list` has a built-in integration, etc. This table is a quick pointer to which platform picker / push library to install in **your app code** when you build UI that calls Feeds API methods (`client.uploadImage`, `client.createDevice`, etc.). Install one only after the user asks for that capability, with the runtime's normal lane (`npx expo install` for Expo so versions match the SDK; the project's package manager + `npx pod-install` for RN CLI). Adding a native package puts an Expo app on the dev-client/native-build lane (Expo Go is not supported by this skill).

| Capability | RN CLI | Expo | Notes |
|---|---|---|---|
| Pick an image for an attachment | `react-native-image-picker` | `expo-image-picker` | Pick from library / camera; upload via `client.uploadImage` (see Attachments). Expo: add the plugin so `NSPhotoLibraryUsageDescription` is generated |
| Pick a document/file attachment | `@react-native-documents/picker` | `expo-document-picker` | Upload via `client.uploadFile` |
| Acquire an OS push token | `@react-native-firebase/messaging` | `expo-notifications` (+ `expo-device`) | Gets the APNs/FCM token you pass to `client.createDevice` (see Push notifications). The SDK does not bundle a push library |
| Display/route a push (background, banners) | `@notifee/react-native` (optional) | `expo-notifications` | App-owned display + tap handling |
| High-performance activity / comment list | `@shopify/flash-list` | `@shopify/flash-list` | Swap for `FlatList` on high-volume feeds |

There is **no Stream upload package** - image/file uploads go through the already-connected `FeedsClient` (`client.uploadImage` / `client.uploadFile`), so do not add an S3/storage SDK.

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

## Navigation rules

For the full provider tree see [sdk.md](../sdk.md) > Provider tree and navigation. The Feeds-specific rules:

- Mount `<StreamFeeds>` above any screen that reads Feeds state and keep it stable for the whole authenticated session, so transitions do not reconnect the WebSocket.
- Share the user's `user` + `timeline` feeds through an `OwnFeedsContextProvider` (see blueprints), **not** navigation params - `Feed` instances are not serializable through router state.
- Wrap each feed-scoped subtree in `<StreamFeed feed={feed}>` so descendant hooks (`useFeedActivities`, `useOwnFollows`, ...) resolve the feed from context.
- Pass **`activityId` (string)** through navigation params, never the `ActivityResponse`. On the destination screen create a live handle with `client.activityWithStateUpdates(activityId)` and call `.dispose()` on unmount.
- For a comments / activity-details screen, register a **modal** route and pass only `activityId`:
  - Expo Router: `<Stack.Screen name="comments-modal" options={{ presentation: "modal" }} />`
  - React Navigation: `<Stack.Screen name="CommentsModal" component={CommentsModal} options={{ presentation: "modal" }} />`
- `KeyboardAvoidingView` is unreliable inside native-stack modal sheets - handle the keyboard at the modal root. See [FEEDS-REACT-NATIVE-blueprints.md](FEEDS-REACT-NATIVE-blueprints.md) > Comments Modal.

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
// `foryou` is a watchable feed too - its content depends on the
// activity_selectors configured server-side on the feed group. See
// "For You feed / Explore" below.
await forYou.getOrCreate({ watch: true });
```

`feed.getOrCreate()` is idempotent. Call it again to refresh the feed state. After a WebSocket reconnect, the SDK automatically re-fetches any feed that was previously loaded with `watch: true`.

### For You feed / Explore prerequisite

The `foryou` group exists by default but ships with **no `activity_selectors` configured**, which means a freshly loaded `foryou` feed returns an empty list - the API call succeeds, the WebSocket subscription is live, the selector just matches nothing. Configure the group once per app (dashboard or CLI):

```bash
# `popular` formula: reactions + comments*2 + bookmarks*3 + shares*3.
# min_popularity: 1 means "at least one reaction-equivalent in cutoff_window".
stream api UpdateFeedGroup id=foryou \
  --body '{"activity_selectors":[{"type":"popular","min_popularity":1,"cutoff_window":"7d"}]}'
```

For a showcase / demo where you have just seeded activities but no engagement, you also have to seed **at least one reaction per activity** - otherwise the popular score stays at 0 and the activity does not clear `min_popularity`. See [`../credentials.md`](../credentials.md) > Step C7. Once configured, you can layer additional selectors (`following`, `current_feed`, ...) - each picks the latest 1000 activities it matches, and the union is what foryou returns.

### Querying activities for one-shot lookups

`client.queryActivities(...)` is the right tool for **search, exports, and any other one-shot lookup** - cases where you do not need the result to react to live events.

```ts
// Search: find recent posts mentioning a keyword.
const res = await client.queryActivities({
  filter: { activity_type: "post", text: { $q: "stream" } },
  sort: [{ field: "created_at", direction: -1 }],
  limit: 20,
});
```

> **Rule of thumb: never use `queryActivities` to back a live-reactive screen.** It is a one-shot HTTP call with no WebSocket subscription. The SDK applies incoming `feeds.activity.added` / `feeds.activity.reaction.added` / `feeds.follow.created` events to feeds you have called `getOrCreate({ watch: true })` on - never to a `queryActivities` result. For an Explore / For You tab that should re-render when other parts of the app change activity state, use a **watched feed group**, not `queryActivities`. See [FEEDS-REACT-NATIVE-blueprints.md](FEEDS-REACT-NATIVE-blueprints.md) > Explore Screen.

Filter notes when you do use `queryActivities`:

- Filter field is `activity_type` (not `type`). A `filter: { type: "post" }` clause silently matches zero rows.
- Default sort is newest-first if you do not pass `sort`.
- Pagination is cursor-based: `res.next` -> pass back as `{ next }`. There is no offset.

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

## Attachments and file uploads

Activities (and comments) can carry image / video / file attachments. Uploads go through the **connected `FeedsClient`** (Stream CDN by default) - there is no upload method on `Feed` and no separate storage SDK. Pick the file with a platform picker (see [App-side helpers for common Feeds UI](#app-side-helpers-for-common-feeds-ui)), then upload and attach:

```ts
// `file` is a StreamFile. In React Native, build it as { uri, name, type }.
// expo-image-picker assets expose `uri`, `fileName`, `mimeType` - map them across.
const img = await client.uploadImage({
  file: {
    uri: asset.uri,
    name: asset.fileName ?? "photo.jpg",
    type: asset.mimeType ?? "image/jpeg",
  },
  // optional server-side resize variants:
  // upload_sizes: [{ width: 100, height: 100, resize: "scale", crop: "center" }],
});

const doc = await client.uploadFile({ file: { uri, name, type } });

// The resulting URL is on `.file`. Images use `image_url`; non-images use `asset_url`.
await feed.addActivity({
  type: "post",
  text,
  attachments: [
    { type: "image", image_url: img.file, custom: {} },
    { type: "file", asset_url: doc.file, custom: {} },
  ],
});
```

Key facts (verify against the manifest-selected [File Uploads](https://getstream.io/activity-feeds/docs/react-native/file-uploads.md) page for the installed SDK version):

- The response URL is on **`response.file`** - not `.url` or `.image_url`.
- Image attachments use **`image_url`**; non-image (`type: "file"`) attachments use **`asset_url`**.
- Max upload size is **100MB**. Supported image types: bmp, gif, jpeg, png, webp, heic/heif, svg+xml. An image can be server-resized only when the source is <= 16.8M pixels.
- Defaults to the Stream CDN; swap your own CDN if needed.
- Read attachments back from `activity.attachments` on any `ActivityResponse`.
- For posting an image from the composer, see [FEEDS-REACT-NATIVE-blueprints.md](FEEDS-REACT-NATIVE-blueprints.md) > Activity Composer with Image.

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

## Push notifications

Feeds push is **opt-in** and mostly dashboard/backend-driven. Do not confuse it with the in-app notification feed: `useAggregatedActivities` / `useNotificationStatus` render notifications **inside a running app** over the WebSocket, while OS push is a separate channel (device token -> Stream -> APNs/FCM -> OS) that wakes a backgrounded or killed app. The same events feed both layers; a push tap typically deep-links into the notification screen.

**Triggering events:** new follower, comment, reaction, comment reaction, and mention. There are two delivery modes, chosen server-side per call: **direct push** (default, `skip_push: false`) and **notification-feed push** (`create_notification_activity: true` + `skip_push: true`), which writes to the notification feed and pushes from there. Pass `skip_push: true` on a comment/reaction/follow call to suppress its push.

### Dashboard

Create a push provider under your app's **Push Notifications** settings (FCM for Android, APNs for iOS) and note each provider's **name** - you reference it from the client. Customize payloads with push templates. Fetch the manifest-selected [Push Overview](https://getstream.io/activity-feeds/docs/react-native/push-introduction.md) and [Push Providers & Multi Bundle](https://getstream.io/activity-feeds/docs/react-native/push-providers-and-multi-bundle.md) pages.

### Client - register the device

Register **after** the user is connected. Feeds uses `createDevice` / `deleteDevice` - note this is **`createDevice`, not the Video SDK's `addDevice`**:

```ts
// token = the native APNs / FCM device token (e.g. expo-notifications
// getDevicePushTokenAsync(), or @react-native-firebase/messaging getToken()).
await client.createDevice({
  id: token,
  push_provider: "apn",                  // "apn" (iOS) | "firebase" (Android)
  push_provider_name: "production-ios",  // the name configured on the dashboard
});

// On sign-out (before disconnectUser, so the next user does not inherit pushes):
await client.deleteDevice({ id: token });
```

Acquiring the OS token (permission prompt, `expo-notifications` / Firebase, Expo dev-client requirement) is the same app-owned pipeline as any RN push app - the Feeds SDK only stores the token via `createDevice`. See [App-side helpers for common Feeds UI](#app-side-helpers-for-common-feeds-ui) for the platform-specific push token libraries.

### Push preferences

- **Per-follow:** `timeline.follow("user:alice", { push_preference: "all" })` - values `"all"` | `"none"` (default `"none"`). Change later with `client.updateFollow({ source, target, push_preference })`.
- **Per-user / global** via `updatePushNotificationPreferences`:

```ts
await client.updatePushNotificationPreferences({
  preferences: [{
    feeds_level: "all", // "all" | "none"
    feeds_preferences: { comment: "all", reaction: "all", follow: "none", mention: "all", comment_reaction: "all" },
    // custom_activity_types: { milestone: "all" },
    // disabled_until: someIsoString, // temporary mute
  }],
});
```

### Backend trigger and handling the tap

Push **emission** is owned by the backend + dashboard, not the client: follows / comments / reactions written through Stream generate pushes according to your dashboard push config and the recipient's preferences. Whether a given event pushes by default, and exactly which preference gates it (the follower's per-follow `push_preference` vs the recipient's `feeds_preferences`), is configured server-side - confirm the precise gating on the manifest-selected Push Overview / Push Preferences pages rather than assuming. Mint tokens and configure providers from your backend with `@stream-io/node-sdk`.

**Handling the notification** (foreground display, tapping a push to deep-link into the activity / notification screen) is app-owned - wire it with your push library's listeners (e.g. `expo-notifications` `addNotificationResponseReceivedListener`). The Feeds SDK only stores the device token via `createDevice`; it does not display pushes or route taps.

Confirm the device-registration and preference shapes against the manifest-selected [Registering Push Devices](https://getstream.io/activity-feeds/docs/react-native/push-devices.md) and [Push Preferences](https://getstream.io/activity-feeds/docs/react-native/push-preferences.md) pages for the installed SDK version.

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
- **For any screen that should react live to other users' activity, back it with a watched feed (`feed.getOrCreate({ watch: true })`), never with `client.queryActivities()`.** `queryActivities` is for one-shot lookups (search, exports) - it returns raw data and the SDK has no place to apply incoming WebSocket events to it. The SDK only applies `feeds.activity.added` / `feeds.activity.reaction.added` / `feeds.follow.created` events to feeds you have loaded with `watch: true`. If reactions / follows / new posts from elsewhere in the app fail to update a list, you are almost certainly looking at a `queryActivities`-backed screen that should be a `<StreamFeed>` + `useFeedActivities()` screen instead.
- **`foryou` ships with no `activity_selectors` configured and returns empty until you configure one.** This is server-side on the feed group, not a client setup step. Configure via dashboard or `stream api UpdateFeedGroup id=foryou --body '{"activity_selectors":[{"type":"popular","min_popularity":1,"cutoff_window":"7d"}]}'`. With the `popular` selector, an activity needs popularity >= `min_popularity` to appear (formula: `reactions + comments*2 + bookmarks*3 + shares*3`); seed at least one reaction per activity in demos.
- **`queryActivities` filter field is `activity_type`, not `type`.** A `filter: { type: "post" }` clause silently matches zero rows because `type` here means a different internal field. Use `filter: { activity_type: "post" }` if you want only one activity type - or leave `filter` off entirely if you want every post.
- **Self-follow is required.** A user's own posts go to their `user` feed and do not appear on their own `timeline` without a `timeline.follow("user:<id>")` relationship. Make this call idempotently on first run.
- **Reactions live on the client.** Use `client.addActivityReaction` / `client.deleteActivityReaction` (not `feed.addReaction` like Flutter / Swift).
- **For activity-details pages, use `client.activityWithStateUpdates(id)`.** Pass `activityId` (string) through navigation params, not the `ActivityResponse`. Call `activity.dispose()` on unmount so the SDK does not keep refetching after the screen closes.
- **`activityWithStateUpdates.get()` must be called with a `comments` request to populate the comment list.** Bare `get()` fetches the activity but does NOT hydrate `state.comments_by_entity_id[activityId]`, which is what `useActivityComments` reads from. The `comments` array on the raw activity response is a separate field that the rendering path does not consult. Always call `get({ comments: { limit, sort, depth } })` on a screen that renders comments. (This reflects the SDK's current state-store internals - if comments still render empty after a version bump, re-verify the slice name against the installed package.)
- **`react-native-safe-area-context@5.7` `SafeAreaView` no-ops on RN 0.85 + Expo 56 + new architecture.** The JS render returns but the native inset never lands - content sits under the notch / home indicator. The `useSafeAreaInsets()` hook works because it reads via a different code path. Prefer `View` + `useSafeAreaInsets()` + explicit `paddingTop` / `paddingBottom` over `<SafeAreaView edges={...}>` on this toolchain, and add `paddingBottom: insets.bottom + N` to `FlatList` `contentContainerStyle` that sits under a native iOS tab bar.
- **`KeyboardAvoidingView` is unreliable inside native-stack `presentation: "modal"` sheets.** RN's KAV computes `frame.y + frame.height - keyboardScreenY`, mixing parent-relative `onLayout` coordinates with screen-relative event coordinates. Inside a modal sheet the two spaces don't match, so `keyboardVerticalOffset` becomes a magic-number knob (commonly 88 / 96 / 128) that drifts by device, header style, and sheet style. On Android with `behavior={undefined}` (RN's recommended Android default), KAV does literally nothing. For modal screens with a composer / input at the bottom (comments modal, reply sheet, search prompt), handle the keyboard at the modal root with `Keyboard.addListener("keyboardWillShow"/"keyboardWillHide")` and adjust `paddingBottom` on the root `View`. iOS `endCoordinates.height` already covers the home indicator; Android (edge-to-edge) `endCoordinates.height` is just the IME and needs `insets.bottom` added back. See the Comments Modal blueprint for the full snippet.
- **Do not use `useHeaderHeight` from `@react-navigation/elements`.** It does not solve modal-sheet keyboard math, and every helper exported from that package is deprecated and scheduled for removal in expo-router 56.
- **JS uses snake_case for `markActivity` parameters.** `mark_all_read`, `mark_all_seen`, `mark_read`, `mark_seen` - not the camelCase shown in other SDKs.
- **Uploads go through the client, and the URL is on `response.file`.** `client.uploadImage({ file })` / `client.uploadFile({ file })` return an object whose URL is `response.file` (not `.url` / `.image_url`). Image attachments use `image_url`; non-image attachments use `asset_url`. There is no upload method on `Feed` and no separate storage SDK.
- **Push uses `createDevice` / `deleteDevice`, NOT `addDevice`.** The Video RN SDK registers devices with `client.addDevice(token, provider, name)`; the **Feeds** SDK uses `client.createDevice({ id, push_provider, push_provider_name })` and `client.deleteDevice({ id })`. Don't copy the Video call shape.
- **The notification feed is in-app, not OS push.** `useAggregatedActivities` / `useNotificationStatus` render over the WebSocket inside a running app. OS push (APNs/FCM) is a separate channel that needs `createDevice` + dashboard provider config. See Push notifications.
- **Keep selectors stable in `useStateStore`.** Unstable selectors run on every render. Use module-scope selectors or memoize.
- **Never put the API secret in client code.** Token generation must happen server-side.
- **Never use dev tokens in production.** They disable token auth and let any client impersonate any user.
- **Imports come from `@stream-io/feeds-react-native-sdk`.** Don't import from `@stream-io/feeds-react-sdk` (the web variant) or `stream-feeds-js` (the lower-level package) by mistake.
