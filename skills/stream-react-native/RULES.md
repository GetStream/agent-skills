# Stream React Native - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Target SDK version and scope

Target **Stream Chat React Native v9**.

- v9 supports the React Native **New Architecture only**. The v9 migration docs require React Native 0.76+ or an Expo SDK version that defaults to the New Architecture.
- The general New Architecture guide says SDK New Architecture support starts at React Native >=0.75.4, but for v9 migrations use the stricter v9 requirement.
- This skill is Chat-only in v1. Do not implement or document React Native Video, Feeds, or Moderation UI from memory.

If training data conflicts with this skill, the local docs under `~/Projects/docs/data/docs/chat-sdk/react-native/v9-latest` and SDK source under `~/Projects/stream-chat-react-native/package/src` win.

---

## Secrets and auth

Never put a Stream API secret in React Native code, Expo config, app config, native manifests, or chat. The client may receive the **API key** and a **user token**. The **API secret** stays server-side or inside the Stream CLI.

Default token model:

- Existing backend: use a backend-issued Stream token or token provider.
- Local dev/demo: use a CLI-generated token from [`credentials.md`](credentials.md).
- User-managed: accept a pasted API key/token if the user chooses that path.

Never use `devToken()` for production. Never invent credentials.

Prefer not to commit static user tokens. If the user wants a local-only demo and accepts a static token, keep the blast radius clear and avoid putting that token in shared docs or final summaries.

---

## Runtime lane ownership

Choose exactly one lane from the project:

- **RN CLI:** use `stream-chat-react-native`.
- **Expo:** use `stream-chat-expo`.

Do not install both packages unless the existing project already has a documented reason. Preserve the project's package manager (`npm`, `yarn`, `pnpm`) and navigation style.

If there is no React Native or Expo project, do not scaffold from this skill. Tell the user to create the app first with their preferred tooling, then continue.

---

## Required peer setup

For Chat RN v9, required setup includes:

- `react-native-gesture-handler`
- `react-native-reanimated`
- `react-native-teleport`
- `react-native-svg`
- `@react-native-community/netinfo`
- `react-native-worklets` for RN CLI when Reanimated 4+ is used
- `expo-image-manipulator` for Expo image compression

The Reanimated or Worklets Babel plugin must be the last Babel plugin. Wrap the app entry point in `GestureHandlerRootView`.

`react-native-teleport` is required in v9 because `OverlayProvider` uses it for portal-hosted UI.

---

## Client lifetime and providers

Use `useCreateChatClient` for the normal Chat connection path. It creates a client, connects the user, returns `null` while connecting, and disconnects during cleanup. Never pass `null` to `<Chat client={...}>`.

Keep one stable `Chat` provider near the app root unless there is a strong reason to isolate contexts. Keep `OverlayProvider` stable and above navigation screens so long-press overlays, attachment picker, and image gallery can render above the active screen.

Do not create a `StreamChat` client:

- in a screen body
- in a component that remounts on every navigation
- per channel screen
- inside render-time factories or unstable callbacks

On sign-out, unmount or change the `useCreateChatClient` inputs. If offline support is enabled, reset the offline database before disconnecting.

---

## Navigation and overlay discipline

When using React Navigation or Expo Router:

- Place `OverlayProvider` above the navigation screens. With React Navigation, prefer `OverlayProvider` above `NavigationContainer`.
- Keep `Chat` high enough that screen transitions do not reconnect the client.
- Pass channel CIDs or ids through navigation params, not `Channel` instances.
- Recreate the `Channel` instance from `useChatContext().client` on the destination screen.
- Set `keyboardVerticalOffset` to the header height.
- Set `topInset` and `bottomInset` on `Channel` for attachment picker and safe area alignment.

For threads, keep thread state explicit. When a thread screen is open, pass the same `thread` value to the main `Channel` and render the thread screen with `threadList`.

---

## Offline support

Offline support is opt-in.

- Install `@op-engineering/op-sqlite` only when requested.
- Pass `enableOfflineSupport` to `Chat`.
- Expo Go cannot use offline support because it requires custom native code; use Expo prebuild or a dev client.
- Access to threads in offline mode is not implemented in the referenced v9 docs.
- On sign-out, run `chatClient.offlineDb.resetDB()` before `disconnectUser()` to avoid cross-user data leaks.

For offline-first boot, read the offline section in [`sdk.md`](sdk.md) before coding. The docs require starting `connectUser` before rendering Chat components but not blocking the UI on the promise.

---

## Reference discipline

Load only the React Native Chat files that match the request:

- [`sdk.md`](sdk.md) for shared RN/Expo, auth, provider, navigation, offline, and sign-out patterns
- [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md) for Chat v9 setup and gotchas
- [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) for concrete screen/component structure

### Blueprints are mandatory, on every turn

Before writing or editing any Stream Chat React Native screen, navigation handler, thread flow, theming override, offline flow, or component customization, open the matching section of [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) and follow its structure.

Use the **Request -> Blueprint section** table at the top of the blueprints file. If no section matches, say so before improvising. Do not rely on a blueprint read earlier in the session; re-read the relevant section before each Stream screen edit.

---

## Source verification

Before using a v9 symbol, prop, or export path that is not already in this skill, verify it in one of:

- `~/Projects/docs/data/docs/chat-sdk/react-native/v9-latest`
- `~/Projects/stream-chat-react-native/package/src/index.ts`
- the specific SDK source file under `~/Projects/stream-chat-react-native/package/src`

The SDK source lives in the package source, not only in wrapper package names.

---

## CLI and shell discipline

Credentials and seeding use the `stream` binary. If the binary is missing, follow [`../stream-cli/bootstrap.md`](../stream-cli/bootstrap.md) instead of introducing a new installer flow.

For `stream api` calls, follow [`../stream/RULES.md`](../stream/RULES.md) > CLI safety: discover endpoints before running them, use `--safe` first for read operations, and only run mutating seed calls after the user explicitly agrees to seeding.

Do not read or print `.env` files. Do not use `bash -ce` in probes.
