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
  expo-build-properties
```

Add `@stream-io/video-react-native-sdk` and `@config-plugins/react-native-webrtc` to `app.json` `plugins`, then `npx expo prebuild --clean`.

**Video - RN CLI:**

```bash
npm view @stream-io/video-react-native-sdk version dist-tags --json
npm install @stream-io/video-react-native-sdk
npm install @stream-io/react-native-webrtc react-native-svg @react-native-community/netinfo
npx pod-install
```

Set `minSdkVersion = 24` in `android/build.gradle` and add Java 8 source compatibility in `android/app/build.gradle`. Add camera/microphone usage descriptions to `Info.plist` and camera/audio permissions to `AndroidManifest.xml`.

If the new app uses yarn or pnpm, translate package-manager commands without changing package names. Run pods after native dependency changes in RN CLI apps. Use `npx expo install` for Expo dependencies so versions match the Expo SDK.

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
npx pod-install
```

If the project uses yarn or pnpm, translate the command without changing package names. Run pods after native dependencies change.

Required Android setup in the host app:

- `android/build.gradle`: `minSdkVersion = 24`
- `android/app/build.gradle`: `compileOptions { sourceCompatibility JavaVersion.VERSION_1_8; targetCompatibility JavaVersion.VERSION_11 }`
- `AndroidManifest.xml`: declare `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, and foreground-service permissions

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
  expo-build-properties
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
| Ringing (CallKit iOS, Android Telecom) | `@stream-io/react-native-callingx` | Wires CallKit/Telecom; see manifest-selected `/incoming-calls/*` pages |
| Background blur / virtual background | `@stream-io/video-filters-react-native` | Optional filter pipeline |
| Noise cancellation | `@stream-io/noise-cancellation-react-native` | Audio quality improvement |
| Android push (FCM) | `@react-native-firebase/app`, `@react-native-firebase/messaging` | Required for ringing/Android push |
| iOS local notifications | `@react-native-community/push-notification-ios` | Local notification helpers |
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

Video does not require Reanimated/Worklets by default. Only add the plugin if Chat is also in scope or if a specific Video optional capability requires it.

### Entry point

Wrap the app entry point with `GestureHandlerRootView` (required for Chat; recommended for Video apps that use any gesture handling).

For Expo Router, the entry point is usually `app/_layout.tsx`. For RN CLI, it is usually `App.tsx` or the component registered from `index.js`.

### Permissions (Video only)

If Video is in scope, ensure runtime camera/microphone access is configured:

- RN CLI iOS: `NSCameraUsageDescription` and `NSMicrophoneUsageDescription` in `Info.plist`. Add `voip` and `audio` to `UIBackgroundModes` if ringing is in scope.
- RN CLI Android: declare `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, and foreground-service permissions in `AndroidManifest.xml`.
- Expo: handled by the `@config-plugins/react-native-webrtc` plugin entry in `app.json` plus `npx expo prebuild --clean`.

Use `react-native-permissions` if the app needs to request permissions before the first call screen mounts; otherwise the SDK prompts at the first media access.

### Safe area

If navigation is used, install and place `SafeAreaProvider` near the root. Do not pass safe-area values into `Channel` as `topInset` or `bottomInset` by default; add those props only after a specific layout or attachment-picker issue proves they are needed.

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
- `call.cid` navigation, recreate `Call` in the destination screen, `<StreamCall call={call}>`
- `call.leave()` on screen unmount (always); `callManager.start/stop` for audio routing
- error handling around `call.join()`, `call.camera.enable()`, `client.connectUser()`

Use the real API key and token or the app's token provider. Do not leave placeholder strings in final code unless the user explicitly asked for a template only.

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
   - **Video:** style-only -> `StreamVideoRN.setTheme` or per-component style; slot-level UI -> `CallContent` slot props (`CallControls`, `CallTopView`, `CallParticipantsList`, etc.); behavior -> documented `Call` method or `useCallStateHooks()` value; native capability -> install only the optional package(s) for that capability
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
- `Call` created with `client.call(type, id)` in the destination screen, joined inside `useEffect`, and `call.leave()` called on cleanup
- `callManager.start/stop` paired with the call lifecycle
- call navigation passes `call.cid`, not a `Call` object
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
