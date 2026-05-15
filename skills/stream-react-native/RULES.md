# Stream React Native - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Target SDK version and scope

Target **Stream Chat React Native** and **Stream Video React Native**.

- Follow the official docs for the current React Native New Architecture support matrix. When migration docs are stricter than the general New Architecture guide, use the stricter requirement.
- The bundled references assume the React Native **New Architecture**. Do not claim old-architecture support unless the docs for the selected package version explicitly say it is supported.
- This skill bundles Chat and Video. Do not implement or document React Native Feeds or Moderation UI from memory.
- The skill installs **latest** of every package on invocation. Do not pin versions or reference deprecated APIs from memory; the live `llms.txt` and selected docs pages are authoritative.

Use Stream `llms.txt` manifests as the docs authority. Start from [`references/DOCS.md`](references/DOCS.md), fetch the appropriate manifest, then fetch the selected markdown page before coding. Do not maintain or rely on hardcoded individual docs URLs. If a symbol must be verified in source, inspect the installed package in the target app's `node_modules` after install.

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

Choose exactly one runtime lane from the project or request:

- **RN CLI:** Chat uses `stream-chat-react-native`; Video uses `@stream-io/video-react-native-sdk`.
- **Expo:** Chat uses `stream-chat-expo`; Video uses the same `@stream-io/video-react-native-sdk` package (no separate Expo package for Video).

Do not install both Chat packages (`stream-chat-react-native` and `stream-chat-expo`) unless the existing project already has a documented reason. Preserve the project's package manager (`npm`, `yarn`, `pnpm`) and navigation style.

For new app requests, default to Expo if the user did not choose a lane. Use RN CLI when the user asks for it or when native project constraints require it. Do not turn a non-empty unrelated directory into a new app without asking; create a child app directory instead when a name can be inferred.

---

## Package version and docs discipline

Before installing Stream Chat or Video RN packages:

1. Use [`references/DOCS.md`](references/DOCS.md) to fetch the appropriate manifest and the manifest-selected `Installation` markdown page (Chat: `https://getstream.io/chat/docs/sdk/react-native/llms.txt`; Video: `https://getstream.io/video/docs/react-native/llms.txt`).
2. Run or consult `npm view <package> version dist-tags --json` for the selected package(s): `stream-chat-react-native`, `stream-chat-expo`, `@stream-io/video-react-native-sdk`.
3. Install `@latest` when the npm dist-tag matches the selected docs. If it does not, use the manifest-selected tag or exact version.

Before changing an existing Chat or Video UI, fetch the manifest-selected markdown page that matches the requested change. Choose the implementation path from the docs and the existing app: theme for style-only changes, component overrides for UI slots, documented props/hooks for behavior, and optional native packages only for requested native capabilities.

---

## Required peer setup

For Chat RN, required setup includes:

- `react-native-gesture-handler`
- `react-native-reanimated`
- `react-native-teleport`
- `react-native-svg`
- `@react-native-community/netinfo`
- `react-native-worklets` for RN CLI when Reanimated 4+ is used
- `expo-image-manipulator` for Expo image compression
- `expo-dev-client` for Expo apps

The Reanimated or Worklets Babel plugin must be the last Babel plugin. Wrap the app entry point in `GestureHandlerRootView`.

`react-native-teleport` is required because `OverlayProvider` uses it for portal-hosted UI.

For Video RN, required setup includes:

- `@stream-io/react-native-webrtc`
- `react-native-svg`
- `@react-native-community/netinfo`
- Expo only: `@config-plugins/react-native-webrtc`, `expo-build-properties`
- Android minSdk 24 (RN CLI: `android/build.gradle`; Expo: `expo-build-properties` plugin)
- iOS Java 8 source / Java 11 target compatibility for the WebRTC module (RN CLI: `android/app/build.gradle` compileOptions)
- `NSCameraUsageDescription` and `NSMicrophoneUsageDescription` in `Info.plist`
- `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, foreground-service permissions in `AndroidManifest.xml`
- Expo only: add `@stream-io/video-react-native-sdk` and `@config-plugins/react-native-webrtc` to `app.json` plugins, then `npx expo prebuild --clean`

Both Chat and Video Expo apps use a dev-client/native-build lane by default because both SDKs include native code. Do not target Expo Go.

Optional native dependencies are capability-owned. Install them only for requested capabilities or when manifest-selected docs require them. The package matrices live in [`builder.md`](builder.md), [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md), and [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md).

---

## Client lifetime and providers

**Chat:** Use `useCreateChatClient` for the normal Chat connection path. It creates a client, connects the user, returns `null` while connecting, and disconnects during cleanup. Never pass `null` to `<Chat client={...}>`.

Keep one stable `Chat` provider near the app root unless there is a strong reason to isolate contexts. Keep `OverlayProvider` stable and above navigation screens so long-press overlays, attachment picker, and image gallery can render above the active screen.

Do not create a `StreamChat` client:

- in a screen body
- in a component that remounts on every navigation
- per channel screen
- inside render-time factories or unstable callbacks

On sign-out, unmount or change the `useCreateChatClient` inputs. If offline support is enabled, reset the offline database before disconnecting.

**Video:** Always use `StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider, options? })` - never `new StreamVideoClient(...)`. Multiple instances break push notifications and call state. Create inside a `useEffect` keyed on `apiKey` and `user.id`, call `client.disconnectUser()` and clear state on cleanup. Pass the resulting client to `<StreamVideo client={...}>` mounted once near the app root; tearing it down restarts the WebSocket.

Use a `tokenProvider` (~4-hour tokens) for production. For ringing/push, pass the same options to `getOrCreateInstance` and `StreamVideoRN.setPushConfig` because the helper reuses cached instances and option mismatches break ringing.

Do not create a `StreamVideoClient`:

- with `new StreamVideoClient(...)` - always `getOrCreateInstance`
- in a screen body
- in a `useEffect` with empty deps inside a leaf component that remounts on navigation
- per call screen
- inside render-time factories or unstable callbacks

For `Call` lifetime: create inside a `useEffect`, `await call.join()` (or `getOrCreate()`), and **always `await call.leave()` on cleanup**. Dangling `Call` instances keep publishing audio/video and leak memory. Pair with `callManager.start({...})` / `callManager.stop()` to keep audio routing aligned with the lifecycle.

Pass `call.cid` through navigation params, not the `Call` object itself. Recreate the call from `client.call(type, id)` in the destination screen, then mount `<StreamCall call={call}>`.

For single-call concurrency, set `options: { rejectCallWhenBusy: true }` on `getOrCreateInstance` and `StreamVideoRN.setPushConfig({ shouldRejectCallWhenBusy: true })`.

---

## Navigation and overlay discipline

When using React Navigation or Expo Router:

- **Chat:** Place `OverlayProvider` above the navigation screens. With React Navigation, prefer `OverlayProvider` above `NavigationContainer`. Keep `Chat` high enough that screen transitions do not reconnect the client. Pass channel CIDs or ids through navigation params, not `Channel` instances. Recreate the `Channel` instance from `useChatContext().client` on the destination screen. Set `keyboardVerticalOffset` to the header height. Do not add `topInset` or `bottomInset` by default; add them only when a specific layout or attachment-picker issue proves they are needed.
- **Video:** Place `StreamVideo` above `NavigationContainer` (or above the Expo Router root layout) so the client survives screen transitions. Pass `call.cid` through navigation params, not `Call` instances. Recreate the call from `useStreamVideoClient().call(type, id)` in the destination screen.

For Chat threads, keep thread state explicit. When a thread screen is open, pass the same `thread` value to the main `Channel` and render the thread screen with `threadList`.

---

## Offline support

Offline support is opt-in.

- Install `@op-engineering/op-sqlite` only when requested.
- Pass `enableOfflineSupport` to `Chat`.
- Expo apps already use a dev-client/native-build lane. Expo Go is not a supported target for this skill.
- Access to threads in offline mode is not implemented in the referenced docs.
- On sign-out, run `chatClient.offlineDb.resetDB()` before `disconnectUser()` to avoid cross-user data leaks.

For offline-first boot, read the offline section in [`sdk.md`](sdk.md) before coding. The docs require starting `connectUser` before rendering Chat components but not blocking the UI on the promise.

---

## Chat + Video interop

A single RN app may run both `stream-chat-react-native` (or `stream-chat-expo`) and `@stream-io/video-react-native-sdk` together.

- Build both clients with the same API key.
- Both products can share the same user token if both are enabled for the API key.
- Mount providers in any nesting order, but **nest** them rather than placing them as siblings, and keep both above the navigator. `OverlayProvider` + `<Chat>` (Chat) and `<StreamVideo>` (Video) operate on independent contexts and do not collide.
- Disconnect both clients on sign-out before creating new ones for a different user.
- For interop-specific guidance (calling from inside a chat channel, attaching a chat thread to a call), fetch the manifest-selected Chat Integration page: `https://getstream.io/video/docs/react-native/advanced/chat-with-video.md`.

---

## Reference discipline

Load only the React Native files that match the request and product:

- [`references/DOCS.md`](references/DOCS.md) for `llms.txt` manifests and docs lookup routing (both Chat and Video)
- [`sdk.md`](sdk.md) for shared RN/Expo, auth, provider, navigation, offline, and sign-out patterns
- Chat: [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md) (setup, gotchas) and [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) (screen/component structure)
- Video: [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md) (setup, gotchas) and [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md) (screen/component structure)

### Blueprints are mandatory, on every turn

Before writing or editing **any** Stream Chat or Stream Video React Native screen, Composable provider, hook usage, navigation handler, thread flow, theming override, offline flow, ringing handler, call control, participant tile, or component customization, you **must** open the matching section of the corresponding blueprints file:

- Chat work -> [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md)
- Video work -> [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md)

This applies on **every turn**, not just the first time the skill is invoked in a session. Follow-up requests like *"add navigation to the channel screen"*, *"open a channel on tap"*, *"add a button to start a call"*, *"customize the call controls"*, *"theme the call screen"*, or *"add a ringing screen"* count as new screen work and require a fresh blueprint read.

Use the **Request -> Blueprint section** table at the top of each blueprints file. If no section matches, say so before improvising. Do not rely on a blueprint read earlier in the session; re-read the relevant section before each Stream screen edit.

---

## CLI and shell discipline

Credentials and requested demo data use the `stream` binary. If the binary is missing, follow [`../stream-cli/bootstrap.md`](../stream-cli/bootstrap.md) instead of introducing a new installer flow.

For `stream api` calls, follow [`../stream/RULES.md`](../stream/RULES.md) > CLI safety: discover endpoints before running them, use `--safe` first for read operations, and only run mutating demo-data calls after the user explicitly asks for demo data.

Do not read or print `.env` files. Do not use `bash -ce` in probes.
