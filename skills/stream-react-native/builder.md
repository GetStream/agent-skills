# Stream React Native - build and integration flow

Use this module after intent classification, **product selection (Chat / Video / Chat + Video)**, and the Project signals probe from [`SKILL.md`](SKILL.md). Run [`credentials.md`](credentials.md) before writing connected Chat or Video code or creating requested demo data.

---

## 1. Detect the workspace

Start by understanding what kind of React Native project is in front of you:

- `EMPTY_CWD` -> valid Track A target; scaffold in the current directory or a named child directory
- no `package.json`, no Expo config, and non-empty directory -> ask before creating a child app
- `package.json` with `expo` or `app.json` / `app.config.*` -> Expo lane
- `package.json` with `react-native` and `ios/` + `android/` -> RN CLI lane
- `app/_layout.*` or `expo-router` -> Expo Router
- `@react-navigation/*` -> React Navigation
- `babel.config.js` -> required place for Reanimated/Worklets plugin (Chat)

Also note any installed Stream packages:

- `stream-chat-react-native` or `stream-chat-expo` -> Chat already present
- `@stream-io/video-react-native-sdk` -> Video already present
- `@stream-io/react-native-callingx`, `@stream-io/react-native-webrtc` -> Video peers already present
- both Chat and Video packages -> Chat + Video interop applies; see [`RULES.md`](RULES.md)

For Track A, default to Expo if the user did not specify Expo vs RN CLI. Keep the new-app guidance minimal: app creation, Stream package install, root providers, auth/token flow, first Chat or Video screen, and verification. Do not explain full React Native, Expo, Xcode, Android Studio, simulator, device, or account setup.

---

## 2. New app scaffold

Use this when the user asks for a brand-new Chat, Video, or Chat + Video RN app, or the workspace is empty and Track A applies.

### Pick target directory

- If the user provided an app name, use it as the directory name.
- If the current directory is empty and the user asked to use it, scaffold into `.`.
- If the current directory is non-empty, create a child directory from the requested app name.
- If no app name can be inferred in a non-empty directory, ask one short question for the app directory name.

### Scaffold the runtime (product-agnostic)

Expo default lane (replace `MyApp` with the target directory):

```bash
npx create-expo-app@latest MyApp
cd MyApp
```

RN CLI lane (only when the user asks for RN CLI or requirements point there):

```bash
npx @react-native-community/cli@latest init MyApp
cd MyApp
```

### Install Stream packages by product

Pick the product(s) confirmed in Step 0 of [`SKILL.md`](SKILL.md). For Chat + Video, install both.

**Chat - Expo:**

```bash
npm view stream-chat-expo version dist-tags --json
npx expo install stream-chat-expo@latest @react-native-community/netinfo expo-dev-client expo-image-manipulator react-native-gesture-handler react-native-reanimated react-native-svg react-native-teleport
npx expo install react-native-safe-area-context
npx expo prebuild
```

**Chat - RN CLI:**

```bash
npm view stream-chat-react-native version dist-tags --json
npm install stream-chat-react-native@latest @react-native-community/netinfo react-native-gesture-handler react-native-reanimated react-native-teleport react-native-worklets react-native-svg
npm install react-native-safe-area-context
npx pod-install
```

**Video - Expo:**

```bash
npm view @stream-io/video-react-native-sdk version dist-tags --json
npx expo install @stream-io/video-react-native-sdk \
  @stream-io/react-native-webrtc \
  @config-plugins/react-native-webrtc \
  react-native-svg \
  @react-native-community/netinfo \
  react-native-safe-area-context \
  expo-build-properties
# recommended (animated floating-participant tile; matches Stream's sample apps):
npx expo install react-native-reanimated react-native-worklets react-native-gesture-handler
```

Add `@stream-io/video-react-native-sdk` and `@config-plugins/react-native-webrtc` to `app.json` `plugins`. If you installed the animation peers, add `react-native-worklets/plugin` as the last Babel plugin. Also enable Android edge-to-edge under `android` in `app.json` (`"edgeToEdgeEnabled": true`; default-on Expo SDK 54+). Then `npx expo prebuild --clean`.

**Video - RN CLI:**

```bash
npm view @stream-io/video-react-native-sdk version dist-tags --json
npm install @stream-io/video-react-native-sdk
npm install @stream-io/react-native-webrtc react-native-svg @react-native-community/netinfo
npm install react-native-safe-area-context
# recommended (animated floating-participant tile; matches Stream's sample apps):
npm install react-native-reanimated react-native-worklets react-native-gesture-handler
npx pod-install
```

**Android edge-to-edge** (pick the branch that matches the host RN version):

- **RN 0.81+**: set `edgeToEdgeEnabled=true` in `android/gradle.properties`. The RN Gradle plugin handles the rest - **no `react-native-edge-to-edge` install, no `styles.xml` edit**.
- **Older RN CLI**: `npm install react-native-edge-to-edge` and inherit a `Theme.EdgeToEdge` variant (e.g. `Theme.EdgeToEdge.Material3`) in `android/app/src/main/res/values/styles.xml`. Add `<item name="enforceNavigationBarContrast">false</item>` for a fully transparent nav bar.

If you installed the animation peers, add `react-native-worklets/plugin` as the last Babel plugin. Set `minSdkVersion = 24` in `android/build.gradle` and add Java 8 source compatibility in `android/app/build.gradle`. Add camera/microphone usage descriptions to `Info.plist` and camera/audio permissions to `AndroidManifest.xml`. In `android/app/src/main/res/values/styles.xml`, set the app theme parent to a `Theme.EdgeToEdge` variant (e.g. `Theme.EdgeToEdge.Material3`) so Android draws under the system bars.

If the new app uses yarn or pnpm, translate package-manager commands without changing package names. Run pods after native dependency changes in RN CLI apps. Use `npx expo install` for Expo dependencies so versions match the Expo SDK.

### Navigation setup (required - blueprints assume it)

The bundled blueprints (App Provider, Navigation Shell, Channel List, Channel Screen, Home/Join-or-Start, Active Call, Ringing) import from `@react-navigation/*` or `expo-router`. Install the matching stack **before** generating screens or imports will break the first build:

- **RN CLI (no navigation by default)** - install React Navigation explicitly:

```bash
npm install @react-navigation/native @react-navigation/native-stack @react-navigation/elements react-native-screens
# react-native-safe-area-context is already installed above; reuse it
npx pod-install
```

- **Expo, default template (recommended)** - `npx create-expo-app@latest` already scaffolds **Expo Router** under `app/`. Skip the React Navigation install and use the Expo Router branch of the Navigation Shell blueprint (and `app/*.tsx` files for routes). Both React Navigation and Expo Router branches are documented in the blueprints - pick the one that matches the chosen template.

- **Expo Router on SDK 56+ — never install `@react-navigation/*`.** Expo Router ships its own navigation runtime from SDK 56 onward and Metro fails to bundle if any `@react-navigation/*` package is present (see [`RULES.md`](RULES.md) > Expo Router SDK 56+ — no React Navigation). The Chat blueprints' `useHeaderHeight()` pattern from `@react-navigation/elements` does not apply on this lane — use the Expo-Router-SDK-56 swap documented in [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) > Channel Screen.

- **Expo opting into React Navigation instead (SDK ≤ 55 only)** - `npx expo install @react-navigation/native @react-navigation/native-stack @react-navigation/elements react-native-screens` and follow the React Navigation branch. Not applicable on Expo Router SDK 56+.

On RN CLI and Expo Router SDK ≤ 55, Chat blueprints read `useHeaderHeight()` from `@react-navigation/elements`; that's why `elements` is in the React Navigation install line above. On Expo Router SDK 56+, do **not** install or import it — see the Channel Screen blueprint for the Platform-based swap.

### New app continuation

After scaffold and packages:

1. Use [`references/DOCS.md`](references/DOCS.md) to fetch the appropriate manifest (Chat or Video) and selected `Installation` markdown page.
2. Confirm the installed Stream package matches the selected docs and npm dist-tag.
3. Run [`credentials.md`](credentials.md) or wire the app's token provider plan.
4. Configure Babel (Chat: Reanimated/Worklets plugin) and root providers.
5. Implement the first screen set:
   - **Chat:** [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) -> App Provider and Auth Gate, Navigation Shell, Channel List Screen, Channel Screen.
   - **Video:** [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md) -> App Provider and Auth Gate, Navigation Shell, Home / Join-or-Start Call, Active Call Screen.
6. Start the dev server only when useful and feasible for the environment (`npx expo start --dev-client`, `npm run ios`, or `npm run android`).

---

## 3. Choose the integration lane

Resolve five things before editing an existing app:

1. **Runtime:** Expo or RN CLI
2. **Product:** Chat, Video, or Chat + Video (from Step 0 of [`SKILL.md`](SKILL.md))
3. **Navigation:** React Navigation, Expo Router, existing custom navigation, or no navigation
4. **Scope:** setup only, core Chat / Video screens, optional native capability, or customization
5. **Auth model:** backend token endpoint, CLI-generated local token, or pasted static token

If the user only asked for setup, stop after the shared wiring in [`sdk.md`](sdk.md).

---

## 4. Install packages

Use [`references/DOCS.md`](references/DOCS.md) first: fetch the appropriate manifest (Chat or Video), select `Installation`, then fetch that markdown page.

Preserve the project's package manager. Use `npx expo install` for Expo packages so versions match the Expo SDK.

### Chat - RN CLI lane

```bash
npm view stream-chat-react-native version dist-tags --json
npm install stream-chat-react-native@latest @react-native-community/netinfo react-native-gesture-handler react-native-reanimated react-native-teleport react-native-worklets react-native-svg
```

If the project uses yarn or pnpm, translate the command without changing package names. Run pods after native dependencies change:

```bash
npx pod-install
```

### Chat - Expo lane

```bash
npm view stream-chat-expo version dist-tags --json
npx expo install stream-chat-expo@latest @react-native-community/netinfo expo-dev-client expo-image-manipulator react-native-gesture-handler react-native-reanimated react-native-svg react-native-teleport
```

Expo Chat apps use a dev-client/native-build lane by default because the SDK includes native code. If the app does not already have native projects, generate them:

```bash
npx expo prebuild
```

Run Expo through the dev client:

```bash
npx expo start --dev-client
```

Do not target Expo Go for `stream-chat-expo`. Also set `useNativeMultipartUpload={true}` on `Chat` when upload progress is required.

### Video - RN CLI lane

```bash
npm view @stream-io/video-react-native-sdk version dist-tags --json
npm install @stream-io/video-react-native-sdk
npm install @stream-io/react-native-webrtc react-native-svg @react-native-community/netinfo
npm install react-native-safe-area-context
npx pod-install
```

For Android edge-to-edge, pick the branch matching the host RN version (see "Required Android setup" below) - on RN 0.81+ you do **not** install `react-native-edge-to-edge`. If the project uses yarn or pnpm, translate the command without changing package names. Run pods after native dependencies change.

Required Android setup in the host app:

- `android/build.gradle`: `minSdkVersion = 24`
- `android/app/build.gradle`: `compileOptions { sourceCompatibility JavaVersion.VERSION_1_8; targetCompatibility JavaVersion.VERSION_11 }`
- `AndroidManifest.xml`: declare `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS` (add `BLUETOOTH_CONNECT` for Bluetooth audio). **Foreground-service permissions are capability-owned** - declare them only for background calls (`androidKeepCallAlive`) or screenshare; see the per-capability list below
- **Android edge-to-edge** (pick the branch matching the host RN version):
  - **RN 0.81+**: set `edgeToEdgeEnabled=true` in `android/gradle.properties` - the RN Gradle plugin handles the rest. **No `react-native-edge-to-edge` install, no `styles.xml` edit.**
  - **Older RN CLI**: `npm install react-native-edge-to-edge` and inherit a `Theme.EdgeToEdge` variant (e.g. `Theme.EdgeToEdge.Material3`) in `android/app/src/main/res/values/styles.xml`. Add `<item name="enforceNavigationBarContrast">false</item>` for a fully transparent nav bar.

Required iOS setup:

- `Info.plist`: add `NSCameraUsageDescription` and `NSMicrophoneUsageDescription`
- For ringing/VoIP, also include `voip` and `audio` in `UIBackgroundModes`

### Video - Expo lane

```bash
npm view @stream-io/video-react-native-sdk version dist-tags --json
npx expo install @stream-io/video-react-native-sdk \
  @stream-io/react-native-webrtc \
  @config-plugins/react-native-webrtc \
  react-native-svg \
  @react-native-community/netinfo \
  react-native-safe-area-context \
  expo-build-properties
```

Enable Android edge-to-edge in `app.json` (default-on from Expo SDK 54, opt-in on SDK 53):

```json
{
  "expo": {
    "android": {
      "edgeToEdgeEnabled": true
    }
  }
}
```

Add config plugins to `app.json`:

```json
{
  "expo": {
    "plugins": [
      "@stream-io/video-react-native-sdk",
      [
        "@config-plugins/react-native-webrtc",
        {
          "cameraPermission": "$(PRODUCT_NAME) requires camera access to capture and transmit video",
          "microphonePermission": "$(PRODUCT_NAME) requires microphone access to capture and transmit audio"
        }
      ],
      [
        "expo-build-properties",
        { "android": { "minSdkVersion": 24 } }
      ]
    ]
  }
}
```

Then regenerate the native projects:

```bash
npx expo prebuild --clean
```

Do not target Expo Go for Video; the SDK includes native code.

### Video - optional capabilities

| User asks for | Packages | Notes |
|---|---|---|
| Ringing (CallKit iOS, Android Telecom) | `@stream-io/react-native-callingx` | Wires CallKit/Telecom; see manifest-selected `/incoming-calls/*` pages. `skipIncomingPushInForeground: true` on `setPushConfig` lets the app's in-foreground ringing UI take over; on iOS 26.4+ RN CLI also needs the PushKit `metadata:` delegate calling `StreamVideoReactNative.didReceiveIncomingVoIPPush(...)` (Expo auto-injects) |
| Background blur / virtual background | `@stream-io/video-filters-react-native` | Optional filter pipeline |
| Noise cancellation | `@stream-io/noise-cancellation-react-native` | Audio quality improvement |
| Ringing push delivery (Android FCM) | `@react-native-firebase/app`, `@react-native-firebase/messaging` | Required for ringing on Android; `@react-native-firebase/messaging` is also the typical library for app-owned non-ringing handling |
| App-owned non-ringing notifications | `@react-native-firebase/messaging`, `expo-notifications`, `@react-native-community/push-notification-ios`, `@notifee/react-native` (any combination) | Non-ringing pushes (`call.missed`, `call.notification`, `call.live_started` - the three values of the SDK's `NonRingingPushEvent` type) are app-owned. Register the device token with `client.addDevice(token, provider, providerName)` and handle display/taps yourself. See manifest-selected `/incoming-calls/non-ringing-notifications-setup/overview/` |
| Permissions helper | `react-native-permissions` | Pre-call permission prompts |

After adding native Video optional packages, follow their platform permission steps. For Expo, keep the app in the dev-client/native-build lane and run `npx expo prebuild --clean` when native config changes need to be regenerated.

### Chat - optional packages by capability

Optional dependencies are capability packages. They are not required for every Chat app. Install them only when the user asks for that capability, when selected manifest docs require them, or when an implemented blueprint needs native functionality beyond the core Chat UI.

How to add one:

1. Identify the requested capability from the user request and manifest-selected docs.
2. Pick the package from the matrix for the detected runtime lane.
3. Install with the project's package manager for RN CLI, or `npx expo install` for Expo.
4. Add required platform permissions or Expo config plugins from the selected package docs.
5. Run pods for RN CLI native installs. For Expo, keep the app in the dev-client/native-build lane and run prebuild when native config changes need to be regenerated.
6. Verify the capability in the existing app flow; do not leave unused optional packages installed.

| User asks for | RN CLI packages | Expo packages | Notes |
|---|---|---|---|
| React Navigation examples / safe areas | `react-native-safe-area-context` | `react-native-safe-area-context` | Needed for `SafeAreaProvider` and `useSafeAreaInsets`; navigation itself may already be installed |
| Native multipart upload progress | none beyond required Stream peers | none beyond Expo dev-client lane | Set `useNativeMultipartUpload={true}` on `Chat` |
| Attachment picker with built-in image media library | `@react-native-camera-roll/camera-roll` | `expo-media-library` | Enables gallery images in the SDK attachment picker |
| Native image picker / camera image upload | `react-native-image-picker` | `expo-image-picker` | Use for camera capture and native picker flows |
| File attachments / document picker | `@react-native-documents/picker` | `expo-document-picker` | Required for file picking |
| Attachment sharing outside the app | `react-native-blob-util react-native-share` | `expo-sharing` | Share downloaded attachments |
| Video playback / video attachments | `react-native-video` | `expo-video` | Optional media playback |
| Voice recording and audio attachments | `react-native-video react-native-audio-recorder-player react-native-blob-util` | Expo SDK 53+: `expo-audio`; Expo SDK 51/52: `expo-av` | Add microphone permissions/config plugins |
| Copy message | `@react-native-clipboard/clipboard` | `expo-clipboard` | Clipboard action support |
| Haptic feedback | `react-native-haptic-feedback` | `expo-haptics` | Optional tactile feedback |
| Offline support | `@op-engineering/op-sqlite` | `@op-engineering/op-sqlite` | Requires native code; Expo already uses the dev-client lane |
| High-performance message list | `@shopify/flash-list` | `@shopify/flash-list` | Use when large channels need FlashList |

After adding native optional packages, follow their platform permission steps. For Expo, keep the app in the dev-client/native-build lane and run `npx expo prebuild` when native config changes need to be regenerated.

---

## 5. Configure native/runtime requirements

### Babel plugin (Chat only)

If Chat is in scope, ensure the Reanimated or Worklets plugin is the last Babel plugin:

```js
module.exports = {
  presets: ["module:@react-native/babel-preset"],
  plugins: [
    // other plugins
    "react-native-worklets/plugin",
  ],
};
```

Use `react-native-reanimated/plugin` if the project is still on Reanimated 3. Use `react-native-worklets/plugin` for Reanimated 4+.

Reanimated/Worklets are optional for Video - the SDK falls back to the RN `Animated` API when they are absent. But Stream's sample apps (including the video-only ones) install `react-native-reanimated` + `react-native-worklets` + `react-native-gesture-handler` for the smoother animated floating-participant tile. If they are installed (or Chat is also in scope), add the Reanimated/Worklets plugin as the last Babel plugin.

### Entry point

Wrap the app entry point with `GestureHandlerRootView` (required for Chat; recommended for Video apps that use any gesture handling).

For Expo Router, the entry point is usually `app/_layout.tsx`. For RN CLI, it is usually `App.tsx` or the component registered from `index.js`.

### Permissions (Video only)

If Video is in scope, ensure runtime camera/microphone access is configured:

- RN CLI iOS: `NSCameraUsageDescription` and `NSMicrophoneUsageDescription` in `Info.plist`. Add `voip` and `audio` to `UIBackgroundModes` if ringing is in scope.
- RN CLI Android: declare `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS` (and `BLUETOOTH_CONNECT` if Bluetooth audio is wanted) in `AndroidManifest.xml`. Add `FOREGROUND_SERVICE` / `FOREGROUND_SERVICE_CAMERA` / `FOREGROUND_SERVICE_MICROPHONE` / `FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK` **only** for background calls (matches Expo plugin's `androidKeepCallAlive`); add `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_MEDIA_PROJECTION` **only** for screenshare. A plain foreground call needs none of those.
- Expo: handled by the `@config-plugins/react-native-webrtc` plugin entry in `app.json` plus `npx expo prebuild --clean`.

Use `react-native-permissions` if the app needs to request permissions before the first call screen mounts; otherwise the SDK prompts at the first media access.

### Safe area and Android edge-to-edge

Always wire safe areas:

- Install `react-native-safe-area-context` and mount `SafeAreaProvider` near the root (above the navigator) on every app. Use `SafeAreaView` (from `react-native-safe-area-context`, not `react-native`) for full-screen wrappers and `useSafeAreaInsets()` when you need fine-grained padding.
- **Android edge-to-edge** is required so the app draws under transparent system bars.
  - **Expo**: set `"edgeToEdgeEnabled": true` in `app.json` under `android` (default-on Expo SDK 54+).
  - **RN CLI 0.81+**: set `edgeToEdgeEnabled=true` in `android/gradle.properties`. The RN Gradle plugin enables the edge-to-edge feature flag automatically - no `react-native-edge-to-edge` install, no `styles.xml` edit.
  - **Older RN CLI**: install `react-native-edge-to-edge` and set the app theme parent to a `Theme.EdgeToEdge` variant in `android/app/src/main/res/values/styles.xml`.
- Status-bar / nav-bar styling: **Expo** uses `expo-status-bar` and (optionally) `expo-navigation-bar` - both are in every Expo template, no extra install needed. **RN CLI** uses `<SystemBars style="auto" />` from `react-native-edge-to-edge`. Both APIs are equivalent on Expo SDK 54+ (Expo's wrappers delegate to `SystemBars` under the hood). Do not call deprecated direct `StatusBar` APIs from `react-native` when edge-to-edge is on.
- For **Chat**: `<Channel>` handles its own insets. Do not pass `topInset` or `bottomInset` by default; add them only after a specific layout or attachment-picker issue proves they are needed. If navigation is used, place `SafeAreaProvider` near the root. When the chat screen sits under a native navigation header, pass that header height to `Channel` as both `keyboardVerticalOffset` and `topInset` (same value) — `topInset` is what the attachment picker uses to compute its bottom sheet top boundary, and without it the sheet clamps short of its snap point. `bottomInset` stays opt-in; add it only when a specific layout requires it (e.g. a tab bar that owns the bottom safe-area).
- For **Video**: the SDK does not infer insets. Read them with `useSafeAreaInsets()` and bridge into `<StreamVideo style={theme}>` as `theme.variants.insets = { top, right, bottom, left }` so `CallContent`, `RingingCallContent`, `HostLivestream`, `ViewerLivestream`, and participant views respect notches and system bars. Once the theme insets are wired, do **not** also wrap those components in `SafeAreaView`, and do **not** re-read `useSafeAreaInsets()` inside a custom `CallControls` to add `paddingBottom` - both produce double padding. For custom top bars rendered outside `CallContent`, custom bottom overlays / drawers / subtitles, or other layouts that fight `CallContent`'s built-in padding, follow the patterns on the live [Safe area insets cookbook page](https://getstream.io/video/docs/react-native/ui-cookbook/safe-area-insets.md) (scoped `<StreamTheme>` override of `callContent.container.paddingTop`; reuse `theme.variants.insets.bottom` in absolute offsets).

---

## 6. Wire shared setup

Before writing code, confirm [`credentials.md`](credentials.md) has resolved the API key, user id, and token or token provider plan for tracks A/B/D.

Follow [`sdk.md`](sdk.md) for shared patterns (client lifecycle, auth, provider tree, navigation, lifecycle/cleanup) and then branch by product:

**Chat:**

- package import lane (`stream-chat-react-native` or `stream-chat-expo`)
- `useCreateChatClient` for client lifecycle
- `OverlayProvider` + `<Chat>` root provider hierarchy
- channel selection and CID navigation
- thread state
- sign-out and offline cleanup

**Video:**

- `StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider, options? })` inside a `useEffect`, with `client.disconnectUser()` on cleanup
- `<StreamVideo client={client}>` mounted once near the app root, above the navigator
- `Call` created **exactly once** in the destination call screen via `client.call(type, id, { reuseInstance: true })` (the flag is mandatory - the same `(type, id)` may already be live from a ring/deep link/push, and without it the SDK constructs a duplicate); mount `<StreamCall call={call}>`; descendants read it via `useCall()` and never call `client.call(...)` again; navigation hands off only the call id, not the Call instance. Use `join({ create: true })` only for create-on-join lobby flows; ringing, livestream-host, and audio-room flows join without `create`.
- `call.leave()` on screen unmount, **guarded by `call.state.callingState !== CallingState.LEFT`** (a second `leave()` throws `Cannot leave call that has already been left`); hangup handlers only navigate
- audio routing is automatic on `call.join()` / `call.leave()` (default `audioRole: "communicator"`); only call `callManager.start/stop` to override the role - the only other value is `"listener"` (playback-optimized, for a view-only livestream viewer or audio-room audience member)
- error handling around `call.join()`, `call.camera.enable()`, `client.connectUser()`

Use the real API key and token or the app's token provider. Reference credentials via named constants (e.g., from a local `.env` file or config module) or the app's token provider. Do not embed raw credential values in final code unless the user explicitly asked for a template only.

---

## 7. Load only the needed reference files

Use the requested screen/feature **and product** to choose the smallest relevant reference set.

Always load:

- [`references/DOCS.md`](references/DOCS.md) for `llms.txt` manifest lookup

Then load the matching product references:

**Chat work:**

- [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md) for setup and gotchas
- [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) for screen/component blueprints

**Video work:**

- [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md) for setup and gotchas
- [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md) for screen/component blueprints

Per [`RULES.md`](RULES.md), re-open the relevant blueprint section before every Stream Chat or Stream Video screen, navigation handler, thread flow, ringing handler, call control, participant tile, theming override, offline flow, or component customization edit.

For requested optional native capabilities, read the **Optional dependency map** in the matching product reference file before installing packages.

---

## 8. Existing app modification flow

Use this when the request is a targeted Chat or Video change in an existing app.

1. Detect runtime, product(s), and currently installed Stream packages.
2. Use [`references/DOCS.md`](references/DOCS.md) to fetch the relevant manifest (Chat or Video) and selected markdown page for the requested area.
3. Open the matching blueprint section in the product's `*-blueprints.md`.
4. For cookbook-style requests, use [`references/DOCS.md`](references/DOCS.md) manifest search and fetch the best matching cookbook/customization markdown page.
5. Prefer the smallest change that preserves the app's architecture:
   - **Chat:** style-only -> theme object; slot-level UI -> `WithComponents`; behavior -> component prop or documented hook; native capability -> install only the optional package(s) for that capability
   - **Video:** style-only -> pass a theme via `<StreamVideo style={theme}>` (or scope it with `<StreamTheme style={theme}>`); slot-level UI -> `CallContent` slot props (`CallControls`, `CallParticipantsList`, `FloatingParticipantView`, `ParticipantView`); behavior -> documented `Call` method or `useCallStateHooks()` value; native capability -> install only the optional package(s) for that capability
6. Verify with the existing project commands.

For Chat message visual or layout changes, fetch the manifest-selected theming/customization pages, then prefer theme values before replacing core message components. For Video customization, prefer slot replacement over full `CallContent` replacement.

---

## 9. Verify before you stop

Use the project's existing verification commands. Prefer the smallest checks that prove the integration works.

**Common:**

- package install completed and selected Stream package(s) match the docs
- iOS pods resolved for RN CLI native installs
- `GestureHandlerRootView` wraps the app (Chat: required; Video: recommended when any gestures)
- optional dependencies are present only for requested optional features

**Chat:**

- Babel Reanimated/Worklets plugin is present and last
- `OverlayProvider` and `Chat` are stable near the root
- `ChannelList` renders for the connected user
- channel navigation passes a CID, not a `Channel` object
- `Channel` renders `MessageList` and `MessageComposer`
- thread navigation passes thread state correctly
- sign-out clears the connected user and, if offline is enabled, resets offline DB before disconnect

**Video:**

- camera and microphone permissions declared (iOS `Info.plist`, Android `AndroidManifest.xml`); Expo: config plugins in `app.json` and `npx expo prebuild --clean` ran
- Android `minSdkVersion = 24` set (RN CLI direct, Expo via `expo-build-properties`)
- client created via `StreamVideoClient.getOrCreateInstance(...)` (not `new StreamVideoClient(...)`) and disposed on cleanup
- `<StreamVideo>` mounted once near the app root, above the navigator
- `Call` created **exactly once** with `client.call(type, id, { reuseInstance: true })` in the destination call screen, joined inside `useEffect` (use `join({ create: true })` only for create-on-join lobby flows; ringing / livestream-host / audio-room join calls created upstream and pass no `create`), and mounted via `<StreamCall>`; descendants read it via `useCall()` and never call `client.call(...)` again; upstream screens (lobby, home) only hand off the call id, do not pre-create the Call
- `call.leave()` called on cleanup **guarded by `callingState !== CallingState.LEFT`** (avoids `Cannot leave call that has already been left`); hangup handlers only navigate
- audio routing left to the SDK (automatic on `call.join()` / `call.leave()`); no manual `callManager.start/stop` unless overriding the default `audioRole: "communicator"`
- call navigation passes only the call id, not a `Call` object
- error handling around `call.join()`, `call.camera.enable()`, `client.connectUser()`
- ringing-related setup matches manifest-selected `/incoming-calls/*` pages when ringing is in scope

Common commands:

```bash
npm run typecheck
npm run lint
npm run ios
npm run android
npx expo start
```

Run only commands that exist in the project.
