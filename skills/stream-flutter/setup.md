# Stream Flutter - setup flow (integrate / new app / migrate)

Run this once per session for integrate, new-app, and Sendbird-migration requests, before feature work. How-to / reference requests skip it and go straight to **Docs lookup** in [`SKILL.md`](SKILL.md). Obey [`RULES.md`](RULES.md) throughout.

> Docs paths written as `CS/...`, `CD/...`, `V/...`, `F/...` use the URL prefixes defined at the top of [`docs-map.md`](docs-map.md) (Chat SDK, Chat client, Video, Feeds); expand them before fetching.

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

State a one-line status, e.g. `Flutter app detected - stream_chat_flutter 10.5.0 already in pubspec.lock`.

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

The CLI has no Feeds seeding commands, so generate two separate helpers called in `main` after `await client.connect()`:

1. **`_setupFollows(client)` - always, unconditionally.** The `timeline` feed only shows feeds it follows; without `timeline:<me>` following `user:<me>` the user never sees their own posts. Never merge it into the seed helper - once data exists the seed guard returns early and the follow never runs.
2. **`_seedPosts(client)` - only if the user said yes, dev only.** Skip when the user feed already has activities.

```dart
Future<void> _setupFollows(StreamFeedsClient client) async {
  final userId = client.user.id;
  final timeline = client.feedFromId(FeedId.timeline(userId));
  await timeline.getOrCreate(); // populates state.following
  final already = timeline.state.following
      .any((f) => f.targetFeed.fid == FeedId.user(userId));
  if (!already) {
    await timeline.follow(targetFid: FeedId.user(userId), createNotificationActivity: false);
  }
}
```

If the pinned `stream_feeds` exposes the idempotent `getOrCreateFollow` (see `F/follows.md` in [`docs-map.md`](docs-map.md)), prefer it over the guard. For posting activities, follow `F/activities.md`.

---

## 3. Install the SDKs

Use `flutter pub add` so pub resolves the current release; install only what the requested products need:

| Need | Packages | Do not also add |
|---|---|---|
| Chat, pre-built UI (default) | `stream_chat_flutter` (v10) | `stream_chat_flutter_core` / `stream_chat` - re-exported |
| Chat, custom UI | `stream_chat_flutter_core` (v10) | - |
| Chat extras | `stream_chat_persistence` (offline), `stream_chat_localizations` (strings) - both imported separately | - |
| Video / livestream / audio rooms | `stream_video_flutter` | `stream_video` - re-exported |
| Video extras | `stream_video_push_notification` (ringing), `stream_video_filters`, `stream_video_noise_cancellation` - same version as `stream_video_flutter` | - |
| Feeds | `stream_feeds` | never `stream_feed` / `stream_feed_flutter_core` |

For exact constraints, SDK floors (Dart / Flutter versions) and per-platform requirements, fetch the install page from [`docs-map.md`](docs-map.md): Chat `CS/basics/installation.md`, Video `V/basics/installation.md`, Feeds `F/installation.md`.

---

## 4. Platform setup the docs do not fully cover

Fetch the install page for the standard permissions and `Info.plist` keys, then also apply:

- **Chat (`stream_chat_flutter`) on iOS:** the attachment / camera / voice-recording pickers need `NSPhotoLibraryUsageDescription`, `NSPhotoLibraryAddUsageDescription`, `NSCameraUsageDescription`, `NSMicrophoneUsageDescription` (and `NSDocumentsFolderUsageDescription` for the file picker) in `ios/Runner/Info.plist`. Missing keys crash the picker.
- **Chat on Android with AGP 9:** if the build fails with `cannot find symbol ... FilePickerPlugin` in `GeneratedPluginRegistrant.java`, the project was scaffolded with AGP 9.x and `file_picker` (a transitive dependency) does not compile under it. This is a toolchain mismatch - `flutter clean` will not help. Pin `com.android.application` to `8.9.1` and `org.jetbrains.kotlin.android` to `2.1.0` in `android/settings.gradle.kts`, and `distributionUrl` to `gradle-8.11.1-all.zip` in `android/gradle/wrapper/gradle-wrapper.properties`; bump again once the plugins support AGP 9.
- **Chat on web / macOS:** web needs `oncontextmenu="return false;"` on `<body>` in `web/index.html`; macOS needs `com.apple.security.network.client` and `com.apple.security.files.user-selected.read-write` entitlements in both `.entitlements` files.
- **Video:** the iOS SPM two-step, analyzer exclude, Kotlin-DSL `minSdk`, runtime permissions, and `StreamFlutterActivity` for PiP - all in [`RULES.md`](RULES.md) "Video -> Build blockers".
- **Feeds:** network only; add the photo-library / camera keys if posts include uploads.

---

## 5. Wire the client

Initialize once before `runApp` (or in the existing DI) and connect the user, following the getting-started page for the product ([`docs-map.md`](docs-map.md): Chat `CS/stream-chat-flutter/introduction.md` or `CS/stream-chat-flutter-core/setup.md`; Video `V/basics/quickstart.md` + `V/guides/client-auth.md`; Feeds `https://getstream.io/activity-feeds/docs/flutter.md`). Honor [`RULES.md`](RULES.md) "Client lifetime". If chat is only one section of a larger app, connect lazily per `CS/guides/initialize-stream-chat-widget-tree.md` instead of blocking `runApp`.

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
