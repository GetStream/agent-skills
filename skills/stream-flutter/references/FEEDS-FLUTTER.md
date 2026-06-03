# Feeds - stream_feeds Setup & Integration

The Stream Feeds SDK for Flutter (`stream_feeds`) provides a social activity feed service. There are **no pre-built UI components** — all UI is built with standard Flutter widgets. The default UI style is Twitter-style unless the user specifies otherwise. For widget blueprints, see [FEEDS-FLUTTER-blueprints.md](FEEDS-FLUTTER-blueprints.md).

> **Package name:** `stream_feeds` (plural) — not `stream_feed`. The old `stream_feed` package is deprecated and fails to compile on Dart 3. Do not use it.

Rules: [../RULES.md](../RULES.md) (secrets, no dev tokens in production, proper disconnect).

---

## Quick ref

- **Package:** `stream_feeds: ^0.5.1` via pub.dev
- **Dart SDK:** `>=3.6.2` required
- **No pre-built UI** — every feed screen is custom Flutter widgets
- **Default UI style:** Twitter-style — build it immediately, do not ask
- **First:** Feed group setup (automatic via CLI during Step 0.5) → Install → `StreamFeedsClient` init → `connect()` → get feed reference → query activities
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

---

## Feed references

Getting a feed reference makes no network call:

```dart
final userFeed      = client.feedFromId(FeedId.user(client.currentUser!.id));
final timelineFeed  = client.feedFromId(FeedId.timeline(client.currentUser!.id));
final notifFeed     = client.feedFromId(FeedId.notification(client.currentUser!.id));

// Equivalent long form
final userFeed = client.feed(group: 'user', id: client.currentUser!.id);
```

`FeedId` factory constructors for common groups:

```dart
FeedId.user(userId)           // group: 'user'
FeedId.timeline(userId)       // group: 'timeline'
FeedId.notification(userId)   // group: 'notification'
FeedId(group: 'custom', id: userId)   // any custom group
```

Feed groups must exist before use — see **Feed groups** section above. The skill creates them automatically during setup.

---

## Activities

### Add an activity

```dart
await userFeed.addActivity(
  request: FeedAddActivityRequest(
    type: 'post',          // use a consistent type per content kind
    text: 'Hello from Stream Feeds!',
  ),
);
```

`FeedAddActivityRequest` key fields: `type` (required), `text`, `attachments`, `custom` (Map for any extra data), `mentionedUserIds`, `visibility`.

### Get activities

```dart
// ActivityList is a stateful, paginated query object
final activityList = client.activityList(
  ActivitiesQuery(fid: FeedId.timeline(client.currentUser!.id), limit: 20),
);

// Fetch first page
final state = await activityList.get();
final activities = state.activities; // List<ActivityData>

// Next page
final nextState = await activityList.queryMoreActivities(limit: 20);
```

For streaming real-time updates:

```dart
activityList.stream.listen((state) {
  // state.activities reflects the latest snapshot
});
```

### Read activity data

```dart
final ActivityData activity = activities[i];

final text       = activity.text ?? '';
final authorName = activity.actor?.name ?? activity.actor?.id ?? 'Unknown';
final authorId   = activity.actor?.id ?? '';
final time       = activity.createdAt;
final likeCount  = activity.reactionCounts['like'] ?? 0;
final hasLiked   = activity.ownReactions['like']?.isNotEmpty ?? false;
```

### Delete an activity

```dart
await client.deleteActivities(ids: [activity.id]);
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
final state = await reactionList.get();
// state.reactions → List<FeedsReactionData>
```

---

## Follow / unfollow

The `timeline` feed follows `user` feeds. When user A follows user B, A's timeline ingests B's new activities automatically.

### Follow

```dart
final timelineFeed = client.feedFromId(FeedId.timeline(client.currentUser!.id));

await timelineFeed.follow(targetFid: FeedId.user(targetUserId));
```

### Unfollow

```dart
await timelineFeed.unfollow(targetFid: FeedId.user(targetUserId));
```

### Check if following

```dart
final followList = client.followList(
  FollowsQuery(sourceFid: FeedId.timeline(client.currentUser!.id), limit: 1),
);
final state = await followList.get();
final isFollowing = state.follows.any((f) => f.targetFid == FeedId.user(targetUserId));
```

---

## Realtime updates

`ActivityList` (and other list objects) expose a `stream` that emits whenever the server pushes an update:

```dart
late StreamSubscription _sub;

@override
void initState() {
  super.initState();
  _activityList = widget.client.activityList(
    ActivitiesQuery(fid: FeedId.timeline(widget.client.currentUser!.id), limit: 20),
  );
  _sub = _activityList.stream.listen((state) {
    setState(() => _activities = state.activities);
  });
  _activityList.get().then((state) {
    setState(() => _activities = state.activities);
  });
}

@override
void dispose() {
  _sub.cancel();
  super.dispose();
}
```

Always cancel stream subscriptions in `dispose()` to prevent memory leaks.

---

## Self-follow (required — call on every start)

The `timeline` feed only shows activities from feeds it follows. A user's own posts go to their `user` feed, which is a separate feed. Without a follow relationship between them, posting to the `user` feed has no effect on what the `timeline` shows.

**This call must be unconditional and separate from any seed logic:**

```dart
Future<void> _setupFollows(StreamFeedsClient client) async {
  final userId       = client.currentUser!.id;
  final timelineFeed = client.feedFromId(FeedId.timeline(userId));
  await timelineFeed.follow(targetFid: FeedId.user(userId));
}
```

Call it right after `connect()`, before `runApp`:

```dart
await client.connect();
await _setupFollows(client); // must always run — not just during seeding
runApp(MyApp(client: client));
```

`follow` is idempotent — calling it when a follow already exists is a no-op.

---

## Seed data (development)

The Stream CLI does not have Feeds-specific commands. For local dev, seed activities programmatically — but keep this separate from the self-follow setup above.

```dart
Future<void> _seedPosts(StreamFeedsClient client) async {
  final userId   = client.currentUser!.id;
  final userFeed = client.feedFromId(FeedId.user(userId));

  final activityList = client.activityList(
    ActivitiesQuery(fid: FeedId.user(userId), limit: 1),
  );
  final state = await activityList.get();
  if (state.activities.isNotEmpty) return;

  for (final text in [
    'Just shipped a new feature! 🚀',
    'Loving the Flutter ecosystem lately.',
    'Stream Feeds makes social apps surprisingly simple.',
  ]) {
    await userFeed.addActivity(
      request: FeedAddActivityRequest(type: 'post', text: text),
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

Update specific fields of an existing activity without replacing it entirely:

```dart
await client.partialUpdateActivity(
  id: activity.id,
  set: {'text': 'Updated post text', 'custom_field': 'value'},
  unset: ['obsolete_field'],
);
```

## Batch follow / unfollow (v0.5.1+)

Follow or unfollow multiple feeds in a single call:

```dart
await timelineFeed.followMany(targets: [
  FeedId.user('alice'),
  FeedId.user('bob'),
]);

await timelineFeed.unfollowMany(targets: [
  FeedId.user('charlie'),
]);
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
- **Feed groups must be created in the Dashboard** — they are not created automatically. Missing groups produce a "feed group doesn't exist" error at runtime.
- **Posts don't appear in timeline without self-follow** — the `timeline` and `user` feeds are independent until a follow relationship is created. Call `_setupFollows` unconditionally on every app start as its own step. Do not bury it inside seed logic — once activities exist the seed guard skips early and the follow never runs.
- **`connect()` is async** — always `await client.connect()` before any feed operation.
- **`client.currentUser`** — available after `connect()`. Accessing it before connect returns null.
- **Cursor-based pagination** — use `queryMoreActivities()` on the `ActivityList`, not offset arithmetic.
- **Reactions are on the `Feed`** — use `feed.addActivityReaction(...)` / `feed.deleteActivityReaction(...)`, not a separate reactions client.
- **Token generation** — use `stream token <user_id>` (Stream CLI) for local dev. Never use the API secret in Flutter code.
- **`ActivitiesFilterField.type` removed in v0.5.0** — use `ActivitiesFilterField.activityType` instead.
- **`ThreadedCommentData` removed in v0.5.0** — use `CommentData` for both flat and threaded comments.
