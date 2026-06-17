# Feeds Flutter - Widget Blueprints

Load only the section you are implementing. For client initialization, feed types, and gotchas, see [FEEDS-FLUTTER.md](FEEDS-FLUTTER.md).

**Default style:** Twitter-style — build it directly without asking. Only switch to Instagram, Reddit, or a custom layout if the user explicitly requests it; the SDK calls are identical regardless of style.

**Package:** `stream_feeds: ^0.5.1` (not the deprecated `stream_feed`). See [FEEDS-FLUTTER.md](FEEDS-FLUTTER.md) for v0.5.x breaking changes.

---

## App Entry Point Blueprint

Initializes `StreamFeedsClient`, connects the user, establishes the self-follow, and optionally seeds sample data.

```dart
// main.dart
import 'package:flutter/material.dart';
import 'package:stream_feeds/stream_feeds.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final client = StreamFeedsClient(
    apiKey: 'your_api_key',
    user: User(id: 'your-user-id', name: 'Your Name'),
    tokenProvider: TokenProvider.static(UserToken('your_user_token')),
  );
  await client.connect();

  // Required: timeline must follow the user feed or posts never appear there.
  // This is unconditional — it must run on every start, not just during seeding.
  await _setupFollows(client);

  // Optional dev seed — remove for production.
  await _seedPosts(client);

  runApp(MyApp(client: client));
}

/// Establishes the self-follow so the user's own posts appear in their timeline.
///
/// Without this, posting to the `user` feed has no effect on the `timeline`
/// feed — the two are independent until a follow relationship is created.
/// Loads the feed first so we can skip if the follow already exists (avoids
/// duplicate follow/notification activities).
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

/// Seeds sample posts for development. Skips if posts already exist.
/// Remove or gate behind a debug flag in production.
Future<void> _seedPosts(StreamFeedsClient client) async {
  final userId   = client.user.id;
  final userFeed = client.feedFromId(FeedId.user(userId));

  await userFeed.getOrCreate();
  if (userFeed.state.activities.isNotEmpty) return;

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

class MyApp extends StatelessWidget {
  const MyApp({super.key, required this.client});

  final StreamFeedsClient client;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Stream Feeds',
      home: HomePage(client: client),
    );
  }
}
```

**Wiring:**
- Import only `stream_feeds` — do not import the deprecated `stream_feed`
- `connect()` is async — always `await` before `runApp`
- Pass `client` down through the widget tree or inject via a DI system

---

## Home Feed Page Blueprint (Twitter-style timeline)

Shows the current user's timeline with a compose FAB.

```dart
// home_page.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:stream_feeds/stream_feeds.dart';

import 'activity_card.dart';
import 'compose_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.client});

  final StreamFeedsClient client;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  late final Feed _timelineFeed = widget.client.feedFromId(
    FeedId.timeline(widget.client.user.id),
  );
  List<ActivityData> _activities = [];
  bool _loading = true;
  StreamSubscription? _sub;

  @override
  void initState() {
    super.initState();
    _sub = _timelineFeed.stream.listen((state) {
      if (mounted) setState(() => _activities = state.activities);
    });
    _timelineFeed.getOrCreate().then((_) {
      if (mounted) {
        setState(() { _activities = _timelineFeed.state.activities; _loading = false; });
      }
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    _timelineFeed.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    await _timelineFeed.getOrCreate();
    setState(() => _activities = _timelineFeed.state.activities);
  }

  Future<void> _loadMore() async {
    if (_timelineFeed.state.canLoadMoreActivities) {
      await _timelineFeed.queryMoreActivities(limit: 20);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Home'), centerTitle: true),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _activities.isEmpty
              ? const Center(child: Text('Follow people to see their posts here.'))
              : RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView.separated(
                    itemCount: _activities.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, i) {
                      if (i == _activities.length - 1) _loadMore();
                      return ActivityCard(
                        activity: _activities[i],
                        feed: _timelineFeed,
                        currentUserId: widget.client.user.id,
                      );
                    },
                  ),
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: () async {
          await Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => ComposePage(client: widget.client),
            ),
          );
          _refresh();
        },
        child: const Icon(Icons.edit_outlined),
      ),
    );
  }
}
```

---

## Activity Card Blueprint (Tweet card)

Renders a single activity in Twitter style: avatar, name, time, text, and action buttons.

```dart
// activity_card.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:stream_feeds/stream_feeds.dart';

class ActivityCard extends StatefulWidget {
  const ActivityCard({
    super.key,
    required this.activity,
    required this.feed,
    required this.currentUserId,
  });

  final ActivityData activity;
  final Feed feed;
  final String currentUserId;

  @override
  State<ActivityCard> createState() => _ActivityCardState();
}

class _ActivityCardState extends State<ActivityCard> {
  late bool _liked;
  late int _likeCount;

  @override
  void initState() {
    super.initState();
    _liked     = widget.activity.ownReactions.any((r) => r.type == 'like');
    _likeCount = widget.activity.reactionGroups['like']?.count ?? 0;
  }

  Future<void> _toggleLike() async {
    if (_liked) {
      await widget.feed.deleteActivityReaction(
        activityId: widget.activity.id,
        type: 'like',
      );
      setState(() { _liked = false; _likeCount--; });
    } else {
      await widget.feed.addActivityReaction(
        activityId: widget.activity.id,
        request: const AddReactionRequest(type: 'like', enforceUnique: true),
      );
      setState(() { _liked = true; _likeCount++; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final activity = widget.activity;
    final name     = activity.user.name ?? activity.user.id;
    final handle   = '@${activity.user.id}';
    final text     = activity.text ?? '';
    final time     = activity.createdAt;
    final commentCount = activity.commentCount;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          CircleAvatar(
            radius: 20,
            backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            child: Text(name[0].toUpperCase()),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(width: 4),
                    Text(handle, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                    const SizedBox(width: 4),
                    Text('·', style: TextStyle(color: Colors.grey[600])),
                    const SizedBox(width: 4),
                    Text(_formatTime(time), style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                  ],
                ),
                const SizedBox(height: 4),
                Text(text),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _ActionButton(
                      icon: Icons.chat_bubble_outline,
                      count: commentCount,
                      onTap: () {},
                    ),
                    const SizedBox(width: 32),
                    _ActionButton(
                      icon: _liked ? Icons.favorite : Icons.favorite_border,
                      count: _likeCount,
                      color: _liked ? Colors.red : null,
                      onTap: _toggleLike,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 60) return '${diff.inMinutes}m';
    if (diff.inHours < 24)   return '${diff.inHours}h';
    return '${diff.inDays}d';
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.count,
    required this.onTap,
    this.color,
  });

  final IconData icon;
  final int count;
  final VoidCallback onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Row(
        children: [
          Icon(icon, size: 18, color: color ?? Colors.grey[600]),
          const SizedBox(width: 4),
          if (count > 0)
            Text('$count', style: TextStyle(color: Colors.grey[600], fontSize: 13)),
        ],
      ),
    );
  }
}
```

---

## Compose Page Blueprint

Lets the user write and post a tweet.

```dart
// compose_page.dart
import 'package:flutter/material.dart';
import 'package:stream_feeds/stream_feeds.dart';

class ComposePage extends StatefulWidget {
  const ComposePage({super.key, required this.client});

  final StreamFeedsClient client;

  @override
  State<ComposePage> createState() => _ComposePageState();
}

class _ComposePageState extends State<ComposePage> {
  final _controller = TextEditingController();
  bool _posting = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _post() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() => _posting = true);
    try {
      final userFeed = widget.client.feedFromId(
        FeedId.user(widget.client.user.id),
      );
      await userFeed.addActivity(
        request: FeedAddActivityRequest(
          type: 'post',
          feeds: [userFeed.fid.rawValue],
          text: text,
        ),
      );
      if (mounted) Navigator.pop(context);
    } finally {
      if (mounted) setState(() => _posting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
            child: FilledButton(
              onPressed: _posting ? null : _post,
              child: _posting
                  ? const SizedBox(
                      width: 16, height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Post'),
            ),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: TextField(
          controller: _controller,
          maxLines: null,
          maxLength: 280,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: "What's happening?",
            border: InputBorder.none,
          ),
          style: const TextStyle(fontSize: 18),
        ),
      ),
    );
  }
}
```

---

## User Profile Page Blueprint

Shows a user's posts with a follow/unfollow button.

```dart
// profile_page.dart
import 'package:flutter/material.dart';
import 'package:stream_feeds/stream_feeds.dart';

import 'activity_card.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key, required this.client, required this.userId});

  final StreamFeedsClient client;
  final String userId;

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  late final Feed _userFeed = widget.client.feedFromId(
    FeedId.user(widget.userId),
  );
  late final Feed _timelineFeed = widget.client.feedFromId(
    FeedId.timeline(widget.client.user.id),
  );

  bool? _isFollowing;
  bool _loadingFollow = false;
  List<ActivityData> _activities = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _userFeed.dispose();
    _timelineFeed.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    // Load the target user's posts and the current user's timeline (for follow state).
    await Future.wait([_userFeed.getOrCreate(), _timelineFeed.getOrCreate()]);

    setState(() {
      _activities = _userFeed.state.activities;
      _isFollowing = _timelineFeed.state.following
          .any((f) => f.targetFeed.fid == FeedId.user(widget.userId));
      _loading = false;
    });
  }

  Future<void> _toggleFollow() async {
    setState(() => _loadingFollow = true);
    if (_isFollowing!) {
      await _timelineFeed.unfollow(targetFid: FeedId.user(widget.userId));
    } else {
      await _timelineFeed.follow(targetFid: FeedId.user(widget.userId));
    }
    setState(() { _isFollowing = !_isFollowing!; _loadingFollow = false; });
  }

  @override
  Widget build(BuildContext context) {
    final isOwnProfile = widget.userId == widget.client.user.id;

    return Scaffold(
      appBar: AppBar(title: Text('@${widget.userId}')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : CustomScrollView(
              slivers: [
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 32,
                          backgroundColor:
                              Theme.of(context).colorScheme.primaryContainer,
                          child: Text(
                            widget.userId[0].toUpperCase(),
                            style: const TextStyle(fontSize: 24),
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(widget.userId,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.bold, fontSize: 18)),
                              Text('@${widget.userId}',
                                  style: TextStyle(color: Colors.grey[600])),
                            ],
                          ),
                        ),
                        if (!isOwnProfile && _isFollowing != null)
                          FilledButton(
                            onPressed: _loadingFollow ? null : _toggleFollow,
                            style: _isFollowing!
                                ? FilledButton.styleFrom(
                                    backgroundColor: Colors.grey[200],
                                    foregroundColor: Colors.black87)
                                : null,
                            child: Text(_isFollowing! ? 'Following' : 'Follow'),
                          ),
                      ],
                    ),
                  ),
                ),
                const SliverToBoxAdapter(child: Divider(height: 1)),
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, i) => Column(
                      children: [
                        ActivityCard(
                          activity: _activities[i],
                          feed: _userFeed,
                          currentUserId: widget.client.user.id,
                        ),
                        const Divider(height: 1),
                      ],
                    ),
                    childCount: _activities.length,
                  ),
                ),
              ],
            ),
    );
  }
}
```

---

## UI Style Variants

If the user explicitly asks for a style other than Twitter, adapt the following:

| Style | Change from Twitter default |
|---|---|
| **Instagram** | Replace ListView with a staggered grid; make images primary; full-width cards with bottom action bar |
| **Reddit** | Add upvote/downvote reactions; show score prominently; group by feed-group-style sections |
| **Custom** | Ask the user what the feed card and action buttons should look like before writing widget code |

The SDK calls (activities, reactions, follow/unfollow) are identical across all styles — only the widget layer changes.
