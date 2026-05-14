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

Resolve two things before editing:

1. **Package tier:** `stream_chat_flutter` (pre-built UI) or `stream_chat_flutter_core` (custom UI)
2. **Scope:** full app bootstrap, auth, a specific screen, or a targeted feature

If the user has not stated a preference, default to `stream_chat_flutter` - it covers most cases and is the fastest path to a working app.

If the user only asked for setup, stop after the shared wiring in [`sdk.md`](sdk.md).

---

## 3. Install the SDK

Add the dependency to `pubspec.yaml`:

```yaml
dependencies:
  stream_chat_flutter: ^10.0.0-beta.13      # pre-built UI
  # OR
  stream_chat_flutter_core: ^10.0.0-beta.13  # custom UI only
  # Optional - localized strings for SDK widgets
  stream_chat_localizations: ^10.0.0-beta.13
```

Then run:

```bash
flutter pub get
```

Install only the packages needed for the requested scope. Do not add `stream_chat_flutter_core` when `stream_chat_flutter` was chosen - the UI package already re-exports it.

---

## 4. Platform setup

Complete the required platform setup **before** wiring the client. Missing setup causes runtime crashes or missing permissions.

### Android

Add the following permissions to `android/app/src/main/AndroidManifest.xml` if not already present:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
```

`photo_manager` requires additional setup for Android 10+ (API 29+). Follow [pub.dev/packages/photo_manager#android-10-q-29](https://pub.dev/packages/photo_manager#android-10-q-29) for the manifest changes needed to access the photo library.

### iOS

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

### Web

Edit `web/index.html` and add `oncontextmenu="return false;"` to the `<body>` tag to allow the SDK to override right-click behavior:

```html
<body oncontextmenu="return false;">
```

### macOS

Add entitlements to `macos/Runner/Release.entitlements` and `macos/Runner/DebugProfile.entitlements`:

```xml
<key>com.apple.security.network.client</key>
<true/>
<key>com.apple.security.files.user-selected.read-write</key>
<true/>
```

---

## 5. Wire the shared app setup

**Before writing any code**, confirm that Step 0.5 in [`SKILL.md`](SKILL.md) has completed - API key, token, and optional seed channels should already be in context. If not, run that step now before continuing.

Follow [`sdk.md`](sdk.md) for:

- client lifetime - initialize `StreamChatClient` before `runApp`
- `StreamChat` widget placement in the tree
- auth and token transport - use the real API key and token from Step 0.5, never placeholder strings
- localization setup if `stream_chat_localizations` was added
- disconnect/reconnect rules when changing users

If seed channels were created in Step 0.5, the app should render them on first launch without any extra setup.

Keep the existing app shell intact. Add only the minimum composition points needed for Stream.

---

## 6. Load only the needed reference files

Use the package tier to choose the smallest relevant reference set.

Available extracted modules:

- Chat pre-built UI: [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md)
- Chat pre-built UI widget blueprints: [`references/CHAT-FLUTTER-blueprints.md`](references/CHAT-FLUTTER-blueprints.md)
- Chat custom UI (core): [`references/CHAT-CORE.md`](references/CHAT-CORE.md)
- Chat custom UI blueprints: [`references/CHAT-CORE-blueprints.md`](references/CHAT-CORE-blueprints.md)

If the exact file is not present yet, say so directly instead of faking a reference.

---

## 7. Verify before you stop

Check the smallest set of outcomes that proves the integration works:

- `flutter pub get` succeeds with no version conflicts
- the app compiles without errors (`flutter build` or hot reload)
- `StreamChatClient` is initialized before `runApp`
- `StreamChat` widget appears in the tree before any Stream widget renders
- the requested screen (channel list, channel view, thread) appears where expected
- controllers are disposed properly - no "setState after dispose" warnings
- switching users or logging out does not leave orphaned WebSocket connections
