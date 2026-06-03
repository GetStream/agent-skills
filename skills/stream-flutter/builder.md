# Stream Flutter - build and integration flow

Use this module after intent classification and, when needed, the local **Project signals** probe from [`SKILL.md`](SKILL.md).

---

## 1. Detect the workspace

Start by understanding what kind of Flutter project is in front of you:

- `pubspec.yaml` with `flutter` dependency -> active Flutter project
- `pubspec.yaml` with `stream_chat_flutter` already present -> Stream already installed, check existing wiring
- `pubspec.yaml` with no Stream dependency -> add dependency, then wire
- no `pubspec.yaml` and `EMPTY_CWD` -> tell the user to run `flutter create my_app` first

Do **not** try to scaffold Flutter projects from scratch.

---

## 2. Choose the integration lane

Resolve three things before editing:

1. **Product:** Chat, Video, Livestream, Feeds, or a combination
2. **Package / tier:**
   - Chat pre-built UI: `stream_chat_flutter`
   - Chat custom UI: `stream_chat_flutter_core`
   - Video calling or livestreaming: `stream_video_flutter`
   - Activity Feeds: `stream_feeds` (the only correct package; `stream_feed` and `stream_feed_flutter_core` are deprecated)
3. **Scope:** full app bootstrap, auth, a specific screen, or a targeted feature
4. **Feeds only — UI style:** Default to Twitter-style. Only use a different style if the user explicitly says so.

If the user has not stated a Chat preference, default to `stream_chat_flutter`. For Video, `stream_video_flutter` covers both standard calls and livestreaming. For Feeds, use `stream_feeds` — it is the only current package. Do not use `stream_feed` or `stream_feed_flutter_core`.

If the user only asked for setup, stop after the shared wiring in [`sdk.md`](sdk.md) (for Chat), after client initialization in [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md) (for Video), or after `setUser` + `FeedProvider` wiring (for Feeds).

---

## 3. Install the SDK

### Chat

Add the dependency to `pubspec.yaml`:

```yaml
dependencies:
  stream_chat_flutter: ^10.0.0      # pre-built UI
  # OR
  stream_chat_flutter_core: ^10.0.0  # custom UI only
  # Optional - localized strings for SDK widgets
  stream_chat_localizations: ^10.0.0
```

Install only the packages needed for the requested scope. Do not add `stream_chat_flutter_core` when `stream_chat_flutter` was chosen - the UI package already re-exports it.

### Video

Add the dependency to `pubspec.yaml`:

```yaml
dependencies:
  stream_video_flutter: ^1.4.0   # pre-built UI + core
  # optional — video filters (blur/virtual background); separate package since v1.0.0
  stream_video_filters: ^1.4.0
  # OR for core only (no pre-built call UI)
  stream_video: ^1.4.0
```

Do not add `stream_video` separately when `stream_video_flutter` is chosen - the UI package re-exports it.

### Feeds

Add the dependency to `pubspec.yaml`:

```yaml
dependencies:
  stream_feeds: ^0.5.1   # check pub.dev for latest; requires Dart >=3.6.2
```

> **Package name is `stream_feeds` (plural).** Do not use `stream_feed` (deprecated, fails to compile on Dart 3) or `stream_feed_flutter_core` (old package, incompatible with `stream_feeds`). `stream_feeds` is the only package needed.

The Feeds SDK has **no pre-built UI widgets**; all feed screens are built with standard Flutter widgets.

Then run:

```bash
flutter pub get
```

---

## 4. Platform setup

Complete the required platform setup **before** wiring the client. Missing setup causes runtime crashes or missing permissions.

### Chat platform setup

#### Android

Add the following permissions to `android/app/src/main/AndroidManifest.xml` if not already present:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
```

`photo_manager` requires additional setup for Android 10+ (API 29+). Follow [pub.dev/packages/photo_manager#android-10-q-29](https://pub.dev/packages/photo_manager#android-10-q-29) for the manifest changes needed to access the photo library.

#### iOS

Add these keys to `ios/Runner/Info.plist` for file access and media:

```xml
<!-- file picker -->
<key>NSDocumentsFolderUsageDescription</key>
<string>This app needs access to your files to share attachments.</string>

<!-- image picker / camera -->
<key>NSCameraUsageDescription</key>
<string>This app needs camera access to capture photos and videos.</string>
<key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access to record audio messages.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>This app needs photo library access to share images.</string>
<key>NSPhotoLibraryAddUsageDescription</key>
<string>This app needs permission to save images to your photo library.</string>
```

For localization, add supported languages to `ios/Runner/Info.plist`:

```xml
<key>CFBundleLocalizations</key>
<array>
  <string>en</string>
</array>
```

#### Web

Edit `web/index.html` and add `oncontextmenu="return false;"` to the `<body>` tag to allow the SDK to override right-click behavior:

```html
<body oncontextmenu="return false;">
```

#### macOS

Add entitlements to `macos/Runner/Release.entitlements` and `macos/Runner/DebugProfile.entitlements`:

```xml
<key>com.apple.security.network.client</key>
<true/>
<key>com.apple.security.files.user-selected.read-write</key>
<true/>
```

### Feeds platform setup

No native dependencies beyond standard network access.

**Android** — add to `android/app/src/main/AndroidManifest.xml` if not already present:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
```

**iOS** — no additional `Info.plist` keys are needed for basic feed functionality. If the user adds image upload, add `NSPhotoLibraryUsageDescription` and `NSCameraUsageDescription` following the same pattern as Chat.

### Video platform setup

#### Android

Add permissions to `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS"/>
<uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30"/>
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT"/>
```

Set minimum SDK in `android/app/build.gradle`:

```groovy
android {
    defaultConfig {
        minSdkVersion 24
    }
}
```

On Android 6+ (API 23+), also request runtime permissions before joining a call. Add `permission_handler` to `pubspec.yaml` and call:

```dart
await [Permission.camera, Permission.microphone].request();
```

#### iOS

Add to `ios/Runner/Info.plist`:

```xml
<key>NSCameraUsageDescription</key>
<string>Video calls require camera access.</string>
<key>NSMicrophoneUsageDescription</key>
<string>Video calls require microphone access.</string>
```

Set minimum deployment target to iOS 14.0+ in `ios/Podfile`:

```ruby
platform :ios, '14.0'
```

---

## 5. Wire the shared app setup

**Before writing any code**, confirm that Step 0.5 in [`SKILL.md`](SKILL.md) has completed - API key, token, and optional seed channels should already be in context. If not, run that step now before continuing.

### Chat

Follow [`sdk.md`](sdk.md) for:

- client lifetime - initialize `StreamChatClient` before `runApp`
- `StreamChat` widget placement in the tree
- auth and token transport - use the real API key and token from Step 0.5, never placeholder strings
- localization setup if `stream_chat_localizations` was added
- disconnect/reconnect rules when changing users

If seed channels were created in Step 0.5, the app should render them on first launch without any extra setup.

### Video

Follow [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md) for:

- `StreamVideo` initialization before `runApp` - no wrapper widget needed
- user and token wiring - use the real API key and token from Step 0.5, never placeholder strings
- `call.getOrCreate()` + `call.join()` sequence before showing the call UI
- platform runtime permission requests on Android before joining

Keep the existing app shell intact. Add only the minimum composition points needed for Stream.

### Feeds

Follow [`references/FEEDS-FLUTTER.md`](references/FEEDS-FLUTTER.md) for:

- `StreamFeedClient('apiKey')` initialization before `runApp`
- `client.setUser(user, token)` — always `await` before `runApp`; use real credentials from Step 0.5
- `FeedProvider(bloc: FeedBloc(client: client), child: MaterialApp(...))` wrapping the app
- feed group references: `client.flatFeed('user', userId)`, `client.flatFeed('timeline', userId)`
- activity queries with `getEnrichedActivities` and reactions via `client.reactions`

**UI style:** Twitter-style by default. Load `FEEDS-FLUTTER-blueprints.md` and use those blueprints directly. Only adapt to Instagram/Reddit/custom layout if the user explicitly asks for it.

---

## 6. Load only the needed reference files

Use the product and package tier to choose the smallest relevant reference set.

Available extracted modules:

- Chat pre-built UI: [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md)
- Chat pre-built UI widget blueprints: [`references/CHAT-FLUTTER-blueprints.md`](references/CHAT-FLUTTER-blueprints.md)
- Chat custom UI (core): [`references/CHAT-CORE.md`](references/CHAT-CORE.md)
- Chat custom UI blueprints: [`references/CHAT-CORE-blueprints.md`](references/CHAT-CORE-blueprints.md)
- Video setup, call types, controls, state: [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md)
- Video widget blueprints: [`references/VIDEO-FLUTTER-blueprints.md`](references/VIDEO-FLUTTER-blueprints.md)
- Livestream SDK patterns: [`references/LIVESTREAM-FLUTTER.md`](references/LIVESTREAM-FLUTTER.md)
- Livestream widget blueprints: [`references/LIVESTREAM-FLUTTER-blueprints.md`](references/LIVESTREAM-FLUTTER-blueprints.md)
- Feeds SDK setup, activities, reactions, follow/unfollow, realtime: [`references/FEEDS-FLUTTER.md`](references/FEEDS-FLUTTER.md)
- Feeds widget blueprints (Twitter-style default; Instagram/Reddit variants): [`references/FEEDS-FLUTTER-blueprints.md`](references/FEEDS-FLUTTER-blueprints.md)

If the exact file is not present yet, say so directly instead of faking a reference.

---

## 7. Verify before you stop

Check the smallest set of outcomes that proves the integration works:

- `flutter pub get` succeeds with no version conflicts
- the app compiles without errors (`flutter build` or hot reload)

**Chat:**
- `StreamChatClient` is initialized before `runApp`
- `StreamChat` widget appears in the tree before any Stream Chat widget renders
- the requested screen (channel list, channel view, thread) appears where expected
- controllers are disposed properly - no "setState after dispose" warnings
- switching users or logging out does not leave orphaned WebSocket connections

**Video:**
- `StreamVideo` is initialized before `runApp` and accessed via `StreamVideo.instance`
- `call.getOrCreate()` is called before `call.join()`
- the result of `call.join()` is checked - not silently discarded
- `call.leave()` is called in `dispose()` as a safety net
- Android runtime camera and microphone permissions are requested before joining
- the `StreamCallContainer` or custom call UI appears after a successful join

**Feeds:**
- `StreamFeedClient` is initialized before `runApp` and `setUser` is awaited
- `FeedProvider` wraps the widget tree before any `FlatFeedCore` or `FeedBloc` access
- `client.flatFeed('timeline', userId)` returns activities from followed users
- `client.flatFeed('user', userId)` stores activities posted by the user
- reactions are added/removed via `client.reactions.add` / `client.reactions.delete`
- feed subscriptions created in `initState` are cancelled in `dispose()`
- the requested feed screen (home timeline, profile, notifications) renders with real data
