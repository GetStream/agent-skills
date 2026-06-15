# Feeds - stream_feeds Setup & Integration

The Stream Feeds SDK for Flutter (`stream_feeds`) provides a social activity feed service. There are **no pre-built UI components** — all UI is built with standard Flutter widgets. The default UI style is Twitter-style unless the user specifies otherwise. For widget blueprints, see [FEEDS-FLUTTER-blueprints.md](FEEDS-FLUTTER-blueprints.md).

> **Package name:** `stream_feeds` (plural) — not `stream_feed`. The old `stream_feed` package is deprecated and fails to compile on Dart 3. Do not use it.

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

---

## Quick ref

- **Package:** `stream_feeds: ^0.5.1` via pub.dev
- **Dart SDK:** `>=3.10.0` required
- **No pre-built UI** — every feed screen is custom Flutter widgets
- **Default UI style:** Twitter-style — build it immediately, do not ask
- **First:** Feed group setup (automatic via CLI during Step 0.5) → Install → `StreamFeedsClient` init → `connect()` → get a `Feed` via `feedFromId` → `feed.getOrCreate()` → watch `feed.state`
- **Async calls return `Result<T>`** — not the value directly and they do not throw. Use `result.getOrNull()`, `result.getOrThrow()`, or `switch`/`fold`. This applies to nearly every SDK method (`addActivity`, `follow`, `getOrCreate`, `get`, …).
- **Current user:** `client.user` (non-nullable `User`) — there is no `client.currentUser`.
- **Docs:** `https://getstream.io/activity-feeds/docs/flutter/`

Full widget blueprints: [FEEDS-FLUTTER-blueprints.md](FEEDS-FLUTTER-blueprints.md) — load only the section you are implementing.

---

## Feed groups (required before first run)

Feed groups **are not created automatically**. Every group the app references must exist first or SDK calls throw "feed group doesn't exist" at runtime.

For a standard Twitter-style app the required groups are:

| Name | Type | Purpose |
|---|---|---|
| `user` | Flat | Stores activities posted by a user |
| `timeline` | Flat | Aggregates activities from people a user follows |
| `notification` | Notification | Alert-style feed — likes, new followers, mentions |

**The skill creates these automatically** during Step 0.5 via the Stream CLI. If the CLI commands fail, create them manually in the Stream Dashboard → Activity Feeds → Feed Groups. The error is always a missing group, not a code issue.

---

## Installation

```yaml
# pubspec.yaml
dependencies:
  stream_feeds: ^0.5.1   # check pub.dev for latest
```

```bash
flutter pub get
```

> **Do not add `stream_feed` or `stream_feed_flutter_core`.** These are the old, deprecated packages. `stream_feeds` is the current replacement and is the only package needed.

---

## Platform setup

No native dependencies beyond standard network access.

**Android** — add to `android/app/src/main/AndroidManifest.xml` if not already present:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
```

**iOS** — no additional `Info.plist` keys needed for basic feed functionality. If the user adds image upload, add `NSPhotoLibraryUsageDescription` and `NSCameraUsageDescription`.

---

## Client initialization

Initialize `StreamFeedsClient` once, before `runApp`. Call `connect()` before any feed operation.

```dart
import 'package:stream_feeds/stream_feeds.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final client = StreamFeedsClient(
    apiKey: 'your_api_key',
    user: User(id: 'your-user-id', name: 'Your Name'),
    tokenProvider: TokenProvider.static(UserToken('your_user_token')),
  );
  await client.connect();

  runApp(MyApp(client: client));
}
```

Never call `StreamFeedsClient(...)` or `connect()` inside a `build` method or `StatelessWidget`. Initialize once and pass the client through your widget tree or existing DI system.

The current user is available as `client.user` (a non-nullable `User`) — use `client.user.id`. There is **no** `client.currentUser` getter.

---

## Feed references

Getting a feed reference makes no network call. To **load** the feed's activities and start receiving real-time updates you must then call `feed.getOrCreate()`:

```dart
final userFeed      = client.feedFromId(FeedId.user(client.user.id));
final timelineFeed  = client.feedFromId(FeedId.timeline(client.user.id));
final notifFeed     = client.feedFromId(FeedId.notification(client.user.id));

// Equivalent long form
final userFeed = client.feed(group: 'user', id: client.user.id);

// Load + watch (makes the network call, populates feed.state, subscribes to updates)
await timelineFeed.getOrCreate();
```

`FeedId` factory constructors for common groups:

```dart
FeedId.user(userId)           // group: 'user'
FeedId.timeline(userId)       // group: 'timeline'
FeedId.notification(userId)   // group: 'notification'
FeedId.stories(userId)        // group: 'stories'
FeedId.story(userId)          // group: 'story'
FeedId(group: 'custom', id: userId)   // any custom group
```

A `Feed` exposes its loaded data via `feed.state` (a `FeedState` with `activities`, `following`, `followers`, `canLoadMoreActivities`, …) and a `feed.stream` of `FeedState` for real-time updates. Call `feed.dispose()` when you no longer need it.

Feed groups must exist before use — see **Feed groups** section above. The skill creates them automatically during setup.

---

## Activities

### Add an activity

The `feeds` field is **required** — it lists the feed(s) the activity is posted to, as raw `group:id` strings. `addActivity` does not infer it from the `Feed` you call it on.

```dart
final result = await userFeed.addActivity(
  request: FeedAddActivityRequest(
    type: 'post',                       // use a consistent type per content kind
    feeds: [userFeed.fid.rawValue],     // e.g. 'user:alice'
    text: 'Hello from Stream Feeds!',
  ),
);
final activity = result.getOrThrow();   // returns ActivityData on success
```

`FeedAddActivityRequest` key fields: `type` (required), `feeds` (required `List<String>` of feed raw values), `text`, `attachments`, `attachmentUploads`, `custom` (`Map<String, Object>`), `mentionedUserIds`, `visibility`, `expiresAt`, `createNotificationActivity`, `skipPush`.

### Get / display activities

Use the `Feed` object — it loads, caches, and live-updates a feed's activities. (`ActivitiesQuery` is a low-level cross-feed query with `filter`/`sort`/`limit` and has **no** `fid` parameter; prefer the `Feed` object to show one feed.)

```dart
final timelineFeed = client.feedFromId(FeedId.timeline(client.user.id));

// Loads the first page, populates state, and subscribes to real-time updates.
await timelineFeed.getOrCreate();

// Current snapshot
final List<ActivityData> activities = timelineFeed.state.activities;

// Load the next page (returns Result<List<ActivityData>>)
await timelineFeed.queryMoreActivities(limit: 20);
```

For streaming real-time updates, listen to the feed's `stream` (each event is a `FeedState`):

```dart
timelineFeed.stream.listen((state) {
  // state.activities reflects the latest snapshot
  // state.canLoadMoreActivities tells you whether more pages exist
});
```

### Read activity data

```dart
final ActivityData activity = activities[i];

final text       = activity.text ?? '';
final authorName = activity.user.name ?? activity.user.id; // user is non-null UserData
final authorId   = activity.user.id;
final time       = activity.createdAt;
final likeCount  = activity.reactionGroups['like']?.count ?? 0; // per-type counts
final totalReacts = activity.reactionCount;                     // total across all types
final commentCount = activity.commentCount;
final hasLiked   = activity.ownReactions.any((r) => r.type == 'like'); // ownReactions is a List
```

### Delete an activity

```dart
// Batch delete via the client
await client.deleteActivities(ids: [activity.id]);

// Or a single activity via its feed
await userFeed.deleteActivity(id: activity.id);
```

---

## Reactions

Reactions are managed on the `Feed` object, not on a separate `client.reactions` client.

### Add a reaction

```dart
// Like
await userFeed.addActivityReaction(
  activityId: activity.id,
  request: const AddReactionRequest(type: 'like', enforceUnique: true),
);

// Comment
await userFeed.addActivityReaction(
  activityId: activity.id,
  request: AddReactionRequest(
    type: 'comment',
    custom: const {'text': 'Great post!'},
  ),
);
```

### Delete a reaction

```dart
await userFeed.deleteActivityReaction(
  activityId: activity.id,
  type: 'like',
);
```

### Query reactions

```dart
final reactionList = client.activityReactionList(
  ActivityReactionsQuery(activityId: activity.id, limit: 10),
);
final result = await reactionList.get();          // Result<List<FeedsReactionData>>
final reactions = result.getOrNull() ?? [];       // List<FeedsReactionData>
// Or watch reactionList.state.reactions / reactionList.stream
```

Each `FeedsReactionData` has `type`, `user` (`UserData`), `activityId`, and optional `custom`.

---

## Follow / unfollow

The `timeline` feed follows `user` feeds. When user A follows user B, A's timeline ingests B's new activities automatically.

### Follow

```dart
final timelineFeed = client.feedFromId(FeedId.timeline(client.user.id));

await timelineFeed.follow(targetFid: FeedId.user(targetUserId));
```

`follow` also accepts optional `createNotificationActivity`, `custom`, and `pushPreference`. Both `follow` and `unfollow` return a `Result`.

### Unfollow

```dart
await timelineFeed.unfollow(targetFid: FeedId.user(targetUserId));
```

### Check if following

After `getOrCreate()`, the feed's own follow relationships are in `feed.state.following` (a `List<FollowData>`). Each `FollowData` exposes `sourceFeed` and `targetFeed` (both `FeedData`) — match on `targetFeed.fid`:

```dart
await timelineFeed.getOrCreate();
final isFollowing = timelineFeed.state.following
    .any((f) => f.targetFeed.fid == FeedId.user(targetUserId));
```

---

## Realtime updates

A `Feed` (and the list objects like `ActivityReactionList`, `FollowList`) exposes a `stream` of state that emits whenever the server pushes an update. Call `getOrCreate()` once to load the first page and subscribe:

```dart
late final Feed _feed = widget.client.feedFromId(
  FeedId.timeline(widget.client.user.id),
);
StreamSubscription? _sub;
List<ActivityData> _activities = [];

@override
void initState() {
  super.initState();
  _sub = _feed.stream.listen((state) {
    if (mounted) setState(() => _activities = state.activities);
  });
  _feed.getOrCreate().then((_) {
    if (mounted) setState(() => _activities = _feed.state.activities);
  });
}

@override
void dispose() {
  _sub?.cancel();
  _feed.dispose();
  super.dispose();
}
```

Always cancel stream subscriptions and call `feed.dispose()` in `dispose()` to prevent memory leaks.

> If you use the `flutter_state_notifier` package, you can bind directly with `StateNotifierBuilder(stateNotifier: feed.notifier, builder: (context, state, _) => ...)` instead of managing a subscription manually.

---

## Self-follow (required — call on every start)

The `timeline` feed only shows activities from feeds it follows. A user's own posts go to their `user` feed, which is a separate feed. Without a follow relationship between them, posting to the `user` feed has no effect on what the `timeline` shows.

**This call must be unconditional and separate from any seed logic.** The feed must be loaded with `getOrCreate()` first so `state.following` is populated; guard on it to avoid creating duplicate follow/notification activities:

```dart
Future<void> _setupFollows(StreamFeedsClient client) async {
  final userId       = client.user.id;
  final timelineFeed = client.feedFromId(FeedId.timeline(userId));
  await timelineFeed.getOrCreate();
  final alreadyFollowing = timelineFeed.state.following
      .any((f) => f.targetFeed.fid == FeedId.user(userId));
  if (!alreadyFollowing) {
    await timelineFeed.follow(
      targetFid: FeedId.user(userId),
      createNotificationActivity: false,
    );
  }
}
```

Call it right after `connect()`, before `runApp`:

```dart
await client.connect();
await _setupFollows(client); // must always run — not just during seeding
runApp(MyApp(client: client));
```

---

## Seed data (development)

The Stream CLI does not have Feeds-specific commands. For local dev, seed activities programmatically — but keep this separate from the self-follow setup above.

```dart
Future<void> _seedPosts(StreamFeedsClient client) async {
  final userId   = client.user.id;
  final userFeed = client.feedFromId(FeedId.user(userId));

  await userFeed.getOrCreate();
  if (userFeed.state.activities.isNotEmpty) return; // already seeded

  for (final text in [
    'Just shipped a new feature! 🚀',
    'Loving the Flutter ecosystem lately.',
    'Stream Feeds makes social apps surprisingly simple.',
  ]) {
    await userFeed.addActivity(
      request: FeedAddActivityRequest(
        type: 'post',
        feeds: [userFeed.fid.rawValue],
        text: text,
      ),
    );
  }
}
```

Call order in `main`:

```dart
await client.connect();
await _setupFollows(client); // always
await _seedPosts(client);    // dev only — remove for production
runApp(MyApp(client: client));
```

---

## Partial activity updates (v0.5.1+)

Update specific fields of an existing activity without replacing it entirely. This is a `Feed` method (`updateActivityPartial`) taking an `UpdateActivityPartialRequest`:

```dart
await userFeed.updateActivityPartial(
  id: activity.id,
  request: UpdateActivityPartialRequest(
    set: {'text': 'Updated post text', 'custom_field': 'value'},
    unset: ['obsolete_field'],
  ),
);
```

## Batch follow / unfollow (v0.5.1+)

Create or remove multiple follow relationships in a single call. These are **client** methods that take batch request objects; sources and targets are raw `group:id` strings (use `FeedId(...).rawValue`):

```dart
await client.getOrCreateFollows(
  FollowBatchRequest(
    follows: [
      FollowRequest(
        source: FeedId.timeline(client.user.id).rawValue,
        target: FeedId.user('alice').rawValue,
      ),
      FollowRequest(
        source: FeedId.timeline(client.user.id).rawValue,
        target: FeedId.user('bob').rawValue,
      ),
    ],
  ),
);

await client.getOrCreateUnfollows(
  UnfollowBatchRequest(
    follows: [
      UnfollowPair(
        source: FeedId.timeline(client.user.id).rawValue,
        target: FeedId.user('charlie').rawValue,
      ),
    ],
  ),
);
```

---

## v0.5.x Changes

- **`ActivitiesFilterField.type` renamed to `ActivitiesFilterField.activityType`** (v0.5.0 breaking) — update any `filter` calls that used `.type`.
- **`ThreadedCommentData` unified into `CommentData`** (v0.5.0) — `ThreadedCommentData` no longer exists as a separate class.
- **Activities from other users now ignored by default** in `ActivityList` queries (v0.5.0) — if you previously relied on cross-user activity visibility without explicit follows, you must now use follows or adjust the query.
- **`FeedData.activityCount` and `FeedData.ownFollowings`** — new fields available on feed metadata (v0.5.1).

---

## Gotchas

- **Package is `stream_feeds` (plural)** — `stream_feed` is deprecated and fails to compile on Dart 3. Never recommend or use the old package.
- **Async methods return `Result<T>`, they do not throw or return the value directly** — unwrap with `getOrNull()` / `getOrThrow()` / `fold`. This includes `getOrCreate`, `addActivity`, `follow`, `addActivityReaction`, `get`, etc.
- **Current user is `client.user`** (non-nullable `User`) — there is **no** `client.currentUser`. Available after the client is constructed; `connect()` establishes the WebSocket.
- **Read a feed via the `Feed` object, not `ActivitiesQuery(fid:)`** — `ActivitiesQuery` has no `fid` field. Use `client.feedFromId(fid)` → `feed.getOrCreate()` → `feed.state.activities` / `feed.stream`.
- **`addActivity` requires `feeds`** — set `feeds: [feed.fid.rawValue]` (raw `group:id` strings). It is not inferred from the `Feed` you call it on.
- **`ActivityData` shape** — author is `activity.user` (non-null `UserData`), not `activity.actor`. `ownReactions` is a `List<FeedsReactionData>` (use `.any((r) => r.type == 'like')`, not map indexing). Per-type counts are in `reactionGroups['like']?.count`; total in `reactionCount`; comments in `commentCount`. There is no `reactionCounts` map.
- **Feed groups must be created in the Dashboard** — they are not created automatically. Missing groups produce a "feed group doesn't exist" error at runtime.
- **Posts don't appear in timeline without self-follow** — the `timeline` and `user` feeds are independent until a follow relationship is created. Call `_setupFollows` unconditionally on every app start as its own step. Do not bury it inside seed logic — once activities exist the seed guard skips early and the follow never runs.
- **`connect()` is async** — always `await client.connect()` before any feed operation.
- **Cursor-based pagination** — use `feed.queryMoreActivities()` (or `.queryMore…()` on a list object), not offset arithmetic. Check `feed.state.canLoadMoreActivities` first.
- **Reactions are on the `Feed`** — use `feed.addActivityReaction(...)` / `feed.deleteActivityReaction(...)`, not a separate reactions client.
- **Partial update / batch follow live in different places** — `feed.updateActivityPartial(id:, request:)` is on the `Feed`; `client.getOrCreateFollows(...)` / `client.getOrCreateUnfollows(...)` are on the client. There is no `client.partialUpdateActivity`, `feed.followMany`, or `feed.unfollowMany`.
- **Dispose feeds and subscriptions** — call `feed.dispose()` and cancel any `feed.stream` subscription in `dispose()`.
- **Token generation** — use `stream token <user_id>` (Stream CLI) for local dev. Never use the API secret in Flutter code.
- **`ActivitiesFilterField.type` removed in v0.5.0** — use `ActivitiesFilterField.activityType` instead.
- **`ThreadedCommentData` removed in v0.5.0** — use `CommentData` for both flat and threaded comments.
