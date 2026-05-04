# Stream React Native - build and integration flow

Use this module after intent classification, credentials when needed, and the Project signals probe from [`SKILL.md`](SKILL.md).

---

## 1. Detect the workspace

Start by understanding what kind of React Native project is in front of you:

- `package.json` with `expo` or `app.json` / `app.config.*` -> Expo lane
- `package.json` with `react-native` and `ios/` + `android/` -> RN CLI lane
- `app/_layout.*` or `expo-router` -> Expo Router
- `@react-navigation/*` -> React Navigation
- `babel.config.js` -> required place for Reanimated/Worklets plugin
- no `package.json`, no Expo config, and `EMPTY_CWD` -> tell the user to create an RN/Expo app first

Do **not** scaffold React Native or Expo apps from this skill. If no project exists, use the fresh app handoff below and stop.

### Fresh app handoff

Give the user only the minimal creation commands and the next Stream-specific action. Do not explain full React Native, Expo, Xcode, Android Studio, simulator, device, or account setup.

Expo:

```bash
npx create-expo-app MyChatApp
cd MyChatApp
```

RN CLI:

```bash
npx @react-native-community/cli init MyChatApp
cd MyChatApp
```

Then ask the user to re-run the Stream Chat request from inside that project. After the project exists, this skill owns Stream package install, peer dependencies, provider placement, auth/token wiring, and Chat UI screens.

---

## 2. Choose the integration lane

Resolve four things before editing:

1. **Runtime:** Expo or RN CLI
2. **Navigation:** React Navigation, Expo Router, existing custom navigation, or no navigation
3. **Scope:** setup only, channel list, channel screen, threads, theming, offline, push, or customization
4. **Auth model:** backend token endpoint, CLI-generated local token, or pasted static token

If the user only asked for setup, stop after the shared wiring in [`sdk.md`](sdk.md).

---

## 3. Install packages

Preserve the project's package manager. Use `npx expo install` for Expo packages so versions match the Expo SDK.

### RN CLI lane

Install the Chat SDK and required peers:

```bash
npm install stream-chat-react-native @react-native-community/netinfo react-native-gesture-handler react-native-reanimated react-native-teleport react-native-worklets react-native-svg
```

If the project uses yarn or pnpm, translate the command without changing package names.

Run pods after native dependencies change:

```bash
npx pod-install
```

### Expo lane

Install the Expo wrapper and compatible peers:

```bash
npx expo install stream-chat-expo @react-native-community/netinfo expo-image-manipulator react-native-gesture-handler react-native-reanimated react-native-svg react-native-teleport
```

If the project uses Expo prebuild or native builds, run prebuild after adding native packages with config plugins:

```bash
npx expo prebuild
```

Do not run prebuild for a managed Expo app unless the project already uses native builds or the requested feature requires it.

### Optional packages by feature

Install optional packages only when the user asks for that feature or when an implemented blueprint needs it. Use the project's package manager for RN CLI and `npx expo install` for Expo.

| User asks for | RN CLI packages | Expo packages | Notes |
|---|---|---|---|
| React Navigation examples / safe areas | `react-native-safe-area-context` | `react-native-safe-area-context` | Needed for `SafeAreaProvider` and `useSafeAreaInsets`; navigation itself may already be installed |
| Attachment picker with built-in image media library | `@react-native-camera-roll/camera-roll` | `expo-media-library` | Enables gallery images in the SDK attachment picker |
| Native image picker / camera image upload | `react-native-image-picker` | `expo-image-picker` | Use for camera capture and native picker flows |
| File attachments / document picker | `@react-native-documents/picker` | `expo-document-picker` | Required for file picking |
| Attachment sharing outside the app | `react-native-blob-util react-native-share` | `expo-sharing` | Share downloaded attachments |
| Video playback / video attachments | `react-native-video` | `expo-video` | Optional media playback |
| Voice recording and audio attachments | `react-native-audio-recorder-player react-native-blob-util` | `expo-av` or `expo-audio` | Add microphone permissions/config plugins |
| Copy message | `@react-native-clipboard/clipboard` | `expo-clipboard` | Clipboard action support |
| Haptic feedback | `react-native-haptic-feedback` | `expo-haptics` | Optional tactile feedback |
| Offline support | `@op-engineering/op-sqlite` | `@op-engineering/op-sqlite` | Expo Go cannot use this; dev client/prebuild required |
| High-performance message list | `@shopify/flash-list` | `@shopify/flash-list` | Use when large channels need FlashList |

After adding native optional packages, follow their platform permission steps. For Expo prebuild/native builds, add the needed config plugins and run `npx expo prebuild` only when the project already uses native builds or the feature requires custom native code.

---

## 4. Configure native/runtime requirements

### Babel plugin

Ensure the Reanimated or Worklets plugin is the last Babel plugin:

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

### Entry point

Wrap the app entry point with `GestureHandlerRootView`.

For Expo Router, the entry point is usually `app/_layout.tsx`. For RN CLI, it is usually `App.tsx` or the component registered from `index.js`.

### Safe area

If navigation is used, install and place `SafeAreaProvider` near the root. Use `useSafeAreaInsets()` in channel screens for `bottomInset`.

---

## 5. Wire shared Chat setup

Before writing code, confirm [`credentials.md`](credentials.md) has resolved the API key, user id, and token or token provider plan for tracks A/B/D.

Follow [`sdk.md`](sdk.md) for:

- package import lane
- `useCreateChatClient`
- root provider hierarchy
- React Navigation / Expo Router placement
- channel selection and CID navigation
- thread state
- sign-out and offline cleanup

Use the real API key and token or the app's token provider. Do not leave placeholder strings in final code unless the user explicitly asked for a template only.

---

## 6. Load only the needed reference files

Use the requested screen/feature to choose the smallest relevant reference set.

Always load:

- [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md) for setup and gotchas

Load the matching blueprint section from:

- [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md)

Per [`RULES.md`](RULES.md), re-open the relevant blueprint section before every Stream Chat screen, navigation handler, thread flow, theming override, offline flow, or component customization edit.

For feature-specific installs such as attachment picker, camera upload, file picker, audio recording, sharing, offline support, or FlashList, read [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md) > **Optional feature dependency map** before installing packages.

---

## 7. Verify before you stop

Use the project's existing verification commands. Prefer the smallest checks that prove the integration works:

- package install completed
- iOS pods resolved for RN CLI native installs
- Babel plugin is present and last
- `GestureHandlerRootView` wraps the app
- `OverlayProvider` and `Chat` are stable near the root
- `ChannelList` renders for the connected user
- channel navigation passes a CID, not a `Channel` object
- `Channel` renders `MessageList` and `MessageComposer`
- thread navigation passes thread state correctly
- sign-out clears the connected user and, if offline is enabled, resets offline DB before disconnect

Common commands:

```bash
npm run typecheck
npm run lint
npm run ios
npm run android
npx expo start
```

Run only commands that exist in the project.
