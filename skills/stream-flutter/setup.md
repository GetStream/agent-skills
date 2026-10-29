# Stream Flutter - setup flow (integrate / new app / migrate)

Run this once per session for integrate, new-app, and Sendbird-migration requests, before feature work. How-to / reference requests skip it and go straight to **Docs lookup** in [`SKILL.md`](SKILL.md). Obey [`RULES.md`](RULES.md) throughout.

---

## 1. Project signals (read-only probe)

Detect the project shape once:

```bash
bash -c 'echo "=== FLUTTER ==="; find . -maxdepth 2 -name "pubspec.yaml" -print 2>/dev/null; echo "=== STREAM ==="; grep -rE "stream_chat|stream_video|stream_feed" . --include="pubspec.yaml" 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Interpret and hold in context (do not re-run unless the directory or project shape changes):

- `pubspec.yaml` with a Stream dependency -> Stream already installed; inspect the existing wiring before editing, and run the version check below.
- `pubspec.yaml` with no Stream dependency -> install (step 3), then wire.
- No `pubspec.yaml` / `EMPTY_CWD` -> if the user explicitly asked for a new app, scaffold with `flutter create --org <reverse.domain> --project-name <name> --platforms android,ios <dir>`; otherwise stop and tell them to run `flutter create my_app` first ([`RULES.md`](RULES.md) "Project ownership").
- `sendbird_chat_sdk` / `sendbird_uikit` present -> this is a migration; [`sendbird-migration.md`](sendbird-migration.md) drives, and calls back into steps 2-4 here.

State a one-line status, e.g. `Flutter app detected - stream_chat_flutter 10.6.0 already in pubspec.lock`.

### Version prerequisite (Chat, existing project)

This skill targets `stream_chat_flutter` / `stream_chat_flutter_core` **v10**. If `pubspec.lock` resolves 9.x or earlier, stop before editing code:

> Your project uses `stream_chat_flutter` v<found>. These instructions cover v10, and a lot changed (widget names, controllers, theming, reaction/delete APIs). The upgrade guide is https://getstream.io/chat/docs/sdk/flutter/guides/migration-guide-10-0.md (older per-version guides: https://github.com/GetStream/stream-chat-flutter/tree/master/migrations). Once you're on v10 I can continue with the full feature set.

If the user wants help with the upgrade itself, fetch the migration guide and walk them through it.

---

## 2. Credentials, token, and seed data (ask once, then act)

Post **one** message with all questions for the products in scope, then execute every step without pausing between them (narrate one line per action).

- **Chat:** (1) fetch the API key and generate a token via the Stream CLI, or will you paste them? (2) token expiry (`1h`, `1d`, never)? (3) seed a few channels with sample users and messages so the app has data on first launch?
- **Video:** (1) and (2) only - calls are ephemeral, nothing to seed. If the app signs viewers in as **guests**, raise the guest-role grant requirement now ([`RULES.md`](RULES.md) "Video -> Auth").
- **Feeds:** (1), (2), and (3) seed a few sample posts? The built-in feed groups already exist - do not ask to create them.

If the user pastes credentials, take them and skip the CLI steps.

### CLI steps

```bash
# Onboard once in the project dir (auth + org/app selection). Required first:
# env/token/api fail with "stream project is not initialized" otherwise.
getstream init
# Run non-interactively (as an agent), init writes .stream/init-<id>.yaml listing
# your orgs/apps. Uncomment `app_id:` (or the new-app block), then rerun:
getstream init --command .stream/init-<id>.yaml

# API key -> dart_defines.json (read with String.fromEnvironment('STREAM_API_KEY');
# run with: flutter run --dart-define-from-file=dart_defines.json). The secret is never written.
getstream env --target flutter

# Token (never-expiring, or add --ttl <duration>)
getstream token <user_id>
getstream token <user_id> --ttl <duration>
```

A 401 means the CLI session expired - run `getstream login` and retry. If `getstream` is not installed, ask the user to install it from https://getstream.io and wait, or take pasted values (Dashboard -> Explorer has a token generator). Never fetch or run an install script.

Hold the token in context and use the real key and token in generated code - no placeholder strings.

### Seed channels (Chat, if requested)

```bash
# 1. Upsert the token user + a few sample users
getstream api UpdateUsers --request '{"users":{"<token_user_id>":{"id":"<token_user_id>","name":"<Display Name>"},"alice":{"id":"alice","name":"Alice"},"bob":{"id":"bob","name":"Bob"}}}'

# 2. Create each channel (repeat per id: general, random, team-alpha)
getstream api GetOrCreateChannel --type messaging --id <channel-id> \
  --request '{"data":{"created_by_id":"<token_user_id>","custom":{"name":"<Channel Name>"}}}'

# 3. Add members - the token user MUST be in every channel, or the app's
#    Filter.in_('members', [userId]) channel list comes back empty
getstream api UpdateChannel --type messaging --id <channel-id> \
  --request '{"add_members":[{"user_id":"<token_user_id>"},{"user_id":"alice"},{"user_id":"bob"}],"user_id":"<token_user_id>"}'

# 4. Seed messages; give a message an explicit id so a thread reply can reference it
getstream api SendMessage --type messaging --id <channel-id> \
  --request '{"message":{"id":"<channel-id>-m1","user_id":"alice","text":"Morning - anyone up for a sync today?"}}'
getstream api SendMessage --type messaging --id <channel-id> \
  --request '{"message":{"user_id":"bob","text":"I will bring the numbers","parent_id":"<channel-id>-m1"}}'
```

Pick `--type` to match the vertical (`messaging`, `team`, `livestream` - see [`RULES.md`](RULES.md) "Permissions"). Print a one-line summary, e.g. `Created channels: general (you, alice, bob), random (you, carol, dave)`. Seeding uses the secret, so it bypasses permissions - if the app will discover or join channels, name the grants now ([`RULES.md`](RULES.md) "Permissions").

### Feeds: self-follow and seed posts

1. **Self-follow - in the app, always, unconditionally.** The `timeline` feed only shows feeds it follows; without `timeline:<me>` following `user:<me>` the user never sees their own posts. Generate a `_setupFollows(client)` helper called in `main` after `await client.connect()`, separate from any seeding (real users need it too):

```dart
Future<void> _setupFollows(StreamFeedsClient client) async {
  final userId = client.user.id;
  final timeline = client.feedFromQuery(
    FeedQuery(
      fid: FeedId.timeline(userId),
      followingLimit: 100,
      watch: false,
    ),
  );

  try {
    final result = await timeline.getOrCreate();
    result.getOrThrow();

    final isFollowingSelf = timeline.state.following
        .any((f) => f.targetFeed.fid == FeedId.user(userId));
    if (isFollowingSelf) return;

    final follow = await timeline.follow(
      targetFid: FeedId.user(userId),
      createNotificationActivity: false,
    );
    follow.getOrThrow();
  } finally {
    timeline.dispose();
  }
}
```

Alternatively, `client.getOrCreateFollows(FollowBatchRequest(follows: [FollowRequest(source: FeedId.timeline(userId).rawValue, target: FeedId.user(userId).rawValue, createNotificationActivity: false)]))` is idempotent, so it can replace the guard above.

2. **Seed data - via the CLI, only if the user said yes.** `getstream api` has a Feeds group (`GetOrCreateFeed`, `GetOrCreateFollows`, `AddActivity`, `AddComment`, `AddActivityReaction`, ...):

```bash
getstream api GetOrCreateFeed --feed-group-id user --feed-id alice --request '{"user_id":"alice"}'
getstream api GetOrCreateFeed --feed-group-id timeline --feed-id <token_user_id> --request '{"user_id":"<token_user_id>"}'
getstream api GetOrCreateFollows --request '{"follows":[{"source":"timeline:<token_user_id>","target":"user:alice","create_notification_activity":false}]}'
# --jq prints the id WITH quotes - strip them before reusing it
ID=$(getstream api AddActivity --request '{"type":"post","feeds":["user:alice"],"text":"Hello from Alice","user_id":"alice"}' --jq '.activity.id' | tr -d '"')
getstream api AddComment --request "{\"object_id\":\"$ID\",\"object_type\":\"activity\",\"comment\":\"Nice!\",\"user_id\":\"bob\"}"
getstream api AddActivityReaction --activity-id "$ID" --request '{"type":"like","user_id":"<token_user_id>"}'
```

Seed authors' feeds, have the token user's timeline follow them, then post. For posting from the app, follow the "Post / update / partial-update / delete activities" docs.

---

## 3. Install the SDKs

Use `flutter pub add` so pub resolves the current release; install only what the requested products need:

| Need | Packages | Do not also add |
|---|---|---|
| Chat, pre-built UI (default) | `stream_chat_flutter` (v10) | `stream_chat_flutter_core` / `stream_chat` - re-exported |
| Chat, custom UI | `stream_chat_flutter_core` (v10) | - |
| Chat extras | `stream_chat_persistence` (offline), `stream_chat_localizations` (strings) - both imported separately | - |
| Video / livestream / audio rooms | `stream_video_flutter` | `stream_video` - re-exported |
| Video extras | `stream_video_push_notification` (ringing), `stream_video_filters`, `stream_video_noise_cancellation`, `stream_video_screen_sharing` (iOS broadcast) - same version as `stream_video_flutter` | - |
| Feeds | `stream_feeds`, plus `flutter_state_notifier` for `StateNotifierBuilder` (`stream_feeds` only depends on the pure-Dart `state_notifier`) | never `stream_feed` / `stream_feed_flutter_core` |

SDK floors (Dart / Flutter versions) are in each package's `pubspec.yaml` `environment:` (e.g. `stream_chat_flutter` 10.6 needs Flutter >= 3.44). For per-platform requirements, fetch the product's install page from [`docs-map.md`](docs-map.md) (Chat "Install packages", Video "Install packages + platform permissions", Feeds "install" in the Feeds intro).

---

## 4. Platform setup the docs do not fully cover

Fetch the install page for the standard permissions and `Info.plist` keys, then also apply:

- **Chat (`stream_chat_flutter`) on iOS:** the attachment / camera / voice-recording pickers need `NSPhotoLibraryUsageDescription`, `NSPhotoLibraryAddUsageDescription`, `NSCameraUsageDescription`, `NSMicrophoneUsageDescription` (and `NSDocumentsFolderUsageDescription` for the file picker) in `ios/Runner/Info.plist`. Missing keys crash the picker. The iOS deployment target must be 14.0+ (`file_picker`); see the 15.0 bullet in [`RULES.md`](RULES.md) "Video -> Build blockers", which applies to Chat too.
- **Chat on Android, older projects:** `share_plus` (a `stream_chat_flutter` dependency) is built with Kotlin 2.2, so the project's `org.jetbrains.kotlin.android` plugin needs 2.1 or newer.
- **Chat on Android with AGP 9 (only if you hit this error - recent templates build fine):** if the build fails with `cannot find symbol ... FilePickerPlugin` in `GeneratedPluginRegistrant.java`, the project was scaffolded with AGP 9.x and `file_picker` (a transitive dependency) does not compile under it. This is a toolchain mismatch - `flutter clean` will not help. Pin `com.android.application` to `8.9.1` and `org.jetbrains.kotlin.android` to `2.1.0` in `android/settings.gradle.kts`, and `distributionUrl` to `gradle-8.11.1-all.zip` in `android/gradle/wrapper/gradle-wrapper.properties`; bump again once the plugins support AGP 9.
- **Chat on web / macOS:** web needs `oncontextmenu="return false;"` on `<body>` in `web/index.html`; macOS needs `com.apple.security.network.client` and `com.apple.security.files.user-selected.read-write` entitlements in both `.entitlements` files.
- **Video:** the iOS 15.0 target, analyzer exclude, `minSdk` floor, runtime permissions, and PiP - all in [`RULES.md`](RULES.md) "Video -> Build blockers".
- **Feeds:** network only; add the photo-library / camera keys if posts include uploads.

---

## 5. Wire the client

Initialize once before `runApp` (or in the existing DI) and connect the user, following the getting-started page for the product ([`docs-map.md`](docs-map.md): Chat "Getting started, pre-built UI" or "Getting started, core / custom UI"; Video "First call in minutes" + "Client init, tokens, guest / anonymous users"; Feeds "quick start" in the Feeds intro). Honor [`RULES.md`](RULES.md) "Client lifetime". If chat is only one section of a larger app, connect lazily per "Chat in only part of the widget tree" in the map instead of blocking `runApp`.

If the user only asked for setup, stop here.

---

## 6. Verify before stopping

- `flutter pub get` succeeds and `flutter analyze` is clean (the app builds or hot-reloads).
- The client is created once, before any Stream widget renders; `StreamChat` (Chat) is an ancestor of every Stream Chat widget.
- The user connects without the secret in the app; seeded channels / posts render on first launch with no hard-coded ids.
- Controllers and subscriptions are disposed (no "setState after dispose" warnings).
- Switching users / logout tears down the previous session (`disconnectUser` / `StreamVideo.reset(disconnect: true)`).
- Video: Android runtime permissions are requested before joining; the `join()` result is checked.
- If the app discovers / joins channels or uses guests, the permission prerequisite was stated.

Then return to **Docs lookup** in [`SKILL.md`](SKILL.md) for each requested screen.
