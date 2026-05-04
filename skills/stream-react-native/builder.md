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

Do **not** scaffold React Native or Expo apps from this skill. If no project exists, stop with a concise instruction such as:

```bash
npx create-expo-app MyChatApp
# or
npx @react-native-community/cli init MyChatApp
```

Then ask the user to open that project directory and re-run the request.

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

### Optional packages

Install only when requested:

- Navigation safe area: `react-native-safe-area-context`
- Offline storage: `@op-engineering/op-sqlite`
- High-performance messages: `@shopify/flash-list`
- Media/audio/file features: follow the optional dependency list in [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md)

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
