# Video React Native - Setup and Integration

Stream Video React Native provides pre-built call UI, livestream, and audio-room primitives for React Native CLI and Expo apps. This file covers packages, app setup, client/auth patterns, call lifecycle, components, ringing, and gotchas. For `llms.txt` docs lookup, see [DOCS.md](DOCS.md). For screen structures, see [VIDEO-REACT-NATIVE-blueprints.md](VIDEO-REACT-NATIVE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (New Architecture, secrets, runtime lane ownership, provider placement, blueprint reads, Chat+Video interop).

Manifest-selected docs are the authority. Use [DOCS.md](DOCS.md) before installing packages or making API-specific claims.

---

## Quick ref

| Area | RN CLI | Expo |
|---|---|---|
| Video package | `@stream-io/video-react-native-sdk` | `@stream-io/video-react-native-sdk` |
| Required peers | `@stream-io/react-native-webrtc`, `react-native-svg`, `@react-native-community/netinfo` | `@stream-io/react-native-webrtc`, `@config-plugins/react-native-webrtc`, `react-native-svg`, `@react-native-community/netinfo`, `expo-build-properties` |
| Install command | package manager install | `npx expo install` |
| Native finalize | `npx pod-install` | `npx expo prebuild --clean` |
| Min Android SDK | 24 | 24 (via `expo-build-properties`) |
| Root wrapper | `GestureHandlerRootView` if using `react-native-gesture-handler` | same |

First path:

1. Pick RN CLI vs Expo.
2. Use [DOCS.md](DOCS.md) to fetch the manifest-selected `Installation` page and verify npm dist-tags.
3. Install package and required peers.
4. Add Expo config plugins (`@stream-io/video-react-native-sdk`, `@config-plugins/react-native-webrtc`) to `app.json` on Expo lane.
5. Declare camera and microphone permissions on iOS (`Info.plist`) and Android (`AndroidManifest.xml`).
6. Create a `StreamVideoClient` once per user session and pass it to `StreamVideo`.
7. Get or create a `Call` and render it inside `StreamCall` + `CallContent`.
8. For ringing or push, fetch the manifest-selected incoming-calls pages and follow them.

Full screen blueprints: [VIDEO-REACT-NATIVE-blueprints.md](VIDEO-REACT-NATIVE-blueprints.md). Load only the section you are implementing.

---

## App Integration

### Installation

RN CLI (use the project's package manager - the command below is illustrative; translate to `yarn add` or `pnpm add` without changing package names):

```bash
npm view @stream-io/video-react-native-sdk version dist-tags --json
npm install @stream-io/video-react-native-sdk
npm install @stream-io/react-native-webrtc react-native-svg @react-native-community/netinfo
npm install react-native-safe-area-context react-native-edge-to-edge
npx pod-install
```

Expo:

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

Install `@latest` only after confirming the npm dist-tag matches the selected docs. If not, use the manifest-selected docs' tag or exact version.

### Animation peers (recommended)

`react-native-reanimated`, `react-native-worklets`, and `react-native-gesture-handler` are **optional** for Video - the SDK dynamically `require`s reanimated and falls back to the React Native `Animated` API when it (and gesture-handler) are absent, so calls still work without them. But Stream's own sample apps install all three (even the video-only ones) for the smoother animated floating-participant tile, and wrap the root in `GestureHandlerRootView`. If you install them, add the Reanimated/Worklets Babel plugin as the **last** Babel plugin (`react-native-worklets/plugin` for Reanimated 4+, `react-native-reanimated/plugin` for Reanimated 3) - the same requirement as Chat. When Chat is also in scope these are already required, so install once.

### Expo config plugins

Add both plugins to `app.json` so `npx expo prebuild` wires the native side:

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

Run `npx expo prebuild --clean` after any config plugin change.

### Android native setup (RN CLI)

In `android/build.gradle` set `minSdkVersion = 24`. In `android/app/build.gradle`:

```groovy
android {
  compileOptions {
    sourceCompatibility JavaVersion.VERSION_1_8
    targetCompatibility JavaVersion.VERSION_11
  }
}
```

Optional R8/ProGuard rule in `android/app/proguard-rules.pro`:

```
-keep class org.webrtc.** { *; }
```

### Permissions

iOS `Info.plist`:

- `NSCameraUsageDescription` - "{appName} requires camera access to capture and transmit video"
- `NSMicrophoneUsageDescription` - "{appName} requires microphone access to capture and transmit audio"
- For ringing/VoIP, also `UIBackgroundModes` includes `voip` and `audio`.

Android `AndroidManifest.xml` (before `<application>`) - **base permissions for a foreground call**:

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
```

**Capability-owned foreground-service permissions** - add only for the matching capability (this is exactly how the Expo config plugin gates them in `withAndroidPermissions.ts`; over-declaring increases Android 14 / Play policy review work for no reason):

```xml
<!-- Background calls (Expo plugin: androidKeepCallAlive: true) -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CAMERA" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK" />

<!-- Screen share (Expo plugin: enableScreenshare: true) -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PROJECTION" />
```

Camera and microphone are prompted automatically when the stream is first requested. Request other permissions (Bluetooth, notifications) manually; `react-native-permissions` is the recommended runtime helper.

### Optional dependency map

Optional dependencies are opt-in capability packages, not default Video requirements. Add them only after the user asks for the capability or after manifest-selected docs require it.

Add optional dependencies with the runtime's normal install lane:

- RN CLI: use the project's package manager, then run pods after native packages change.
- Expo: use `npx expo install` so versions match the Expo SDK.
- Expo Video apps use a dev-client/native-build lane by default because the SDK includes native code. Do not target Expo Go.
- If an Expo app does not already have native projects, run `npx expo prebuild`; run it again when native config changes need to be regenerated.

| Feature | Packages |
|---|---|
| Ringing (CallKit on iOS, Android Telecom) | `@stream-io/react-native-callingx` |
| Background blur and virtual backgrounds | `@stream-io/video-filters-react-native` |
| Noise cancellation | `@stream-io/noise-cancellation-react-native` |
| Ringing push delivery (Android FCM) | `@react-native-firebase/app`, `@react-native-firebase/messaging` |
| App-owned non-ringing notifications (any combination, app's choice) | `@react-native-firebase/messaging`, `expo-notifications`, `@react-native-community/push-notification-ios`, `@notifee/react-native` |
| Gesture handler (recommended root wrapper) | RN CLI: `react-native-gesture-handler`; Expo: `npx expo install react-native-gesture-handler` |
| Permissions helper | `react-native-permissions` |

For ringing, push, broadcasting, picture-in-picture, screen sharing, and custom video filters, fetch the manifest-selected docs first; native setup details and supported props change between SDK versions.

### Client setup

Create the client with `StreamVideoClient.getOrCreateInstance(...)` inside a `useEffect` and dispose on unmount. Multiple `new StreamVideoClient(...)` instances break push notifications and state management - always use the singleton helper.

```tsx
import { useEffect, useState } from "react";
import {
  StreamVideo,
  StreamVideoClient,
  User,
} from "@stream-io/video-react-native-sdk";

export default function ConnectedVideo({ apiKey, user }: { apiKey: string; user: User }) {
  const [client, setClient] = useState<StreamVideoClient>();

  useEffect(() => {
    const tokenProvider = async () => {
      const res = await fetch(`https://your-api.example.com/stream-token?user_id=${user.id}`);
      return (await res.json()).token as string;
    };
    const c = StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider });
    setClient(c);
    return () => {
      c.disconnectUser().catch((err) => console.error(err));
      setClient(undefined);
    };
  }, [apiKey, user.id]);

  if (!client) return null;
  return <StreamVideo client={client}>{/* navigation and screens */}</StreamVideo>;
}
```

For ringing/push: pass the same options to `getOrCreateInstance` and `StreamVideoRN.setPushConfig`; the helper reuses cached instances and option mismatches break ringing. Use `~4-hour` tokens via `tokenProvider`; the SDK refreshes automatically.

Best practices source: [`/video/docs/react-native/advanced/integration-best-practices/`](https://getstream.io/video/docs/react-native/advanced/integration-best-practices.md).

### Token route pattern

Production apps should use a backend route that returns a fresh Stream user token:

```ts
// Server-side only
import { StreamClient } from "@stream-io/node-sdk";

const serverClient = new StreamClient(apiKey, apiSecret);
const token = serverClient.generateUserToken({ user_id: userId });
```

Client response shape:

```ts
{ apiKey: string, token: string, userId: string, userName?: string }
```

Local demo tokens can come from [`../credentials.md`](../credentials.md).

---

## User Authentication

### Static token (no expiry)

Demo/local only. Generate via the Stream CLI:

```bash
getstream token <user_id>
```

Pass the literal token to `StreamVideoClient`. Never use a no-expiry token in production builds.

### Token provider (expiring tokens)

```ts
const tokenProvider = async () => {
  const res = await fetch(`https://your-api.example.com/stream-token?user_id=${userId}`);
  const body = await res.json();
  return body.token as string;
};
const client = StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider });
```

The SDK calls `tokenProvider` again automatically when the current token nears expiry or reconnects. Always use `getOrCreateInstance` (see Client setup above) - never `new StreamVideoClient(...)`.

### Disconnecting and switching users

```ts
await client.disconnectUser();
// then call StreamVideoClient.getOrCreateInstance(...) again with the next user
```

Do not reuse a client across users. Tear it down on sign-out.

---

## Call object

A `Call` represents one logical call (a `(type, id)` pair). Create the call inside a `useEffect` after the client is ready and **call `call.leave()` on cleanup, guarded by `callingState !== CallingState.LEFT`** - dangling calls keep publishing audio/video and leak memory, but leaving twice (hangup button + unmount, React 18 strict-mode double-effect) throws `Cannot leave call that has already been left`.

```tsx
import { useEffect, useState } from "react";
import { useStreamVideoClient, Call, CallingState } from "@stream-io/video-react-native-sdk";

const client = useStreamVideoClient();
const [call, setCall] = useState<Call>();

useEffect(() => {
  if (!client) return;
  // `{ reuseInstance: true }` is required on every destination call screen:
  // the same (type, id) may already be live in the SDK (outgoing ring, ringing
  // watcher, deep link, push), and without it the SDK constructs a duplicate
  // that leaks SFU connections and breaks state.
  const c = client.call(type, id, { reuseInstance: true });
  setCall(c);
  // `{ create: true }` lets a "join by id" lobby flow work even when the
  // (type, id) doesn't exist server-side yet. Drop it for ringing, livestream
  // host, audio room, and other flows that join an upstream-created call.
  c.join({ create: true }).catch((err) => console.error("Failed to join", err));
  return () => {
    if (c.state.callingState !== CallingState.LEFT) {
      c.leave().catch((err) => console.error(err));
    }
    setCall(undefined);
  };
}, [client, type, id]);
```

A call is initialized after any of `await call.get()`, `await call.create()`, `await call.getOrCreate()`, or `await call.join()`.

### Lifecycle methods

- `getOrCreate(data?)` - server-side reserve/create
- `join(options?)` - connect to the SFU and start sending/receiving media. Retries with exponential backoff; tune with `{ maxJoinRetries }`.
- `leave()` - disconnect locally, keep call alive for others. **Call on unmount, guarded by `call.state.callingState !== CallingState.LEFT`**; calling twice throws `Cannot leave call that has already been left`.
- `endCall()` - end the call for everyone
- `accept()` / `reject()` - ringing-call handling
- `getOrCreate({ ring: true, data: { members } })` - start an outgoing ringing call
- `setDisconnectionTimeout(seconds)` - reconnection window before the SDK gives up

### Audio routing

`callManager` is started and stopped **automatically** by `call.join()` and `call.leave()` with `audioRole: "communicator"` as the default. Do not call `callManager.start()` / `callManager.stop()` from your code for the standard call flow - the SDK already does it on the right boundaries.

The only reason to invoke `callManager` directly is to override the default role. The only two roles are `audioRole: "communicator"` (the default - full-duplex routing for anyone who publishes audio, including an audio-room host) and `audioRole: "listener"` (playback-optimized output for a view-only experience such as a livestream viewer or audio-room audience member). You may also set a custom initial output device. When you do override, still rely on the SDK's automatic teardown on `call.leave()` rather than calling `stop()` yourself.

### Call types

`default`, `livestream`, `audio_room`, `development`. Configure per-type policies (permissions, settings, recording defaults) in the Stream dashboard, or server-side via the Node SDK (the React Native client does not expose call-type configuration). See manifest-selected "Configuring Call Types".

---

## Call State

Subscribe to call state via the React hooks exported by the SDK; values come from RxJS observables under the hood and update automatically.

### Calling state and connection

```ts
import { useCallStateHooks } from "@stream-io/video-react-native-sdk";

const { useCallCallingState, useCallEgress } = useCallStateHooks();
const callingState = useCallCallingState(); // idle, joining, joined, reconnecting, left, offline
```

### Ringing state

Surface ringing calls with the client-level `useCalls()` hook and filter by the `call.ringing` flag: `useCalls().filter((c) => c.ringing)`. Read the phase from `useCallStateHooks().useCallCallingState()` (`CallingState.RINGING`, `JOINING`, `JOINED`, ...). Pair with `client.on("call.ring", ...)` at the app shell so an incoming call can surface UI even when no screen has the call mounted yet. (There is no `useCallRingingState` hook - the ringing list comes from `useCalls()` and the phase from `useCallCallingState()`.)

### Participants

```ts
const { useParticipants, useLocalParticipant, useRemoteParticipants } = useCallStateHooks();
const participants = useParticipants();
const local = useLocalParticipant();
```

Each participant is a `StreamVideoParticipant` and exposes `userId`, `name`, `image`, `audioStream`, `videoStream`, `isSpeaking`, `isDominantSpeaker`, `audioLevel`, `connectionQuality`, `pinned`, `roles`, and reaction state.

### Client-level call routing

```ts
client.on("call.ring", (event) => {
  // navigate to the incoming-call screen with event.call.cid
});
client.on("call.ended", ...);
```

---

## React Native Components

| Component / hook | Use |
|---|---|
| `StreamVideo` | App-root provider; supplies the `StreamVideoClient` to descendants |
| `StreamCall` | Scopes a single `Call` to its children; required by every call screen |
| `CallContent` | Default in-call UI; slot props `CallControls`, `CallParticipantsList`, `FloatingParticipantView`, `ParticipantView` (plus `layout` and `onHangupCallHandler`) |
| `CallControls` | Mic / camera / screenshare / reactions / hangup row |
| `RingingCallContent` | Routes between `IncomingCall`, `OutgoingCall`, and the accepted `CallContent` (all three are overridable slot props) |
| `IncomingCall` | Built-in incoming-call screen UI |
| `OutgoingCall` | Built-in outgoing-call screen UI |
| `ParticipantView` | Renders one participant's video tile |
| `LivestreamPlayer` | Low-level viewer-only livestream player (HLS / WebRTC playback) |
| `ViewerLivestream` | Full viewer-side livestream UI (live badge, duration, participant count) |
| `HostLivestream` | Host-side livestream UI |
| `useStreamVideoClient` | Reads the provided client inside `StreamVideo` |
| `useCall` | Reads the current `Call` inside `StreamCall` |
| `useCallStateHooks` | Returns sub-hooks for call/participant state |
| `StreamVideoRN` | Static config surface (push, theme overrides, i18n) |

---

## Navigation rules

- Put `StreamVideo` above any screen that needs a call. With React Navigation, prefer it above `NavigationContainer` so deep links land inside the provider.
- Keep one `StreamVideo` mounted for the whole authenticated session. Tearing it down restarts the WebSocket.
- Pass only the call id (string) through navigation params, not the `Call` object itself.
- **Create the `Call` instance exactly once** in the destination call screen via `client.call(type, id, { reuseInstance: true })`, join inside `useEffect` (pass `join({ create: true })` only for create-on-join lobby flows - ringing, livestream host, and audio-room flows join calls created upstream), and mount `<StreamCall call={call}>`. The `{ reuseInstance: true }` flag is required because the same `(type, id)` may already be in the SDK's managed state (outgoing ring, ringing watcher, deep link, push); without it the SDK constructs a duplicate `Call`. Descendants of `<StreamCall>` read the call via `useCall()` - they must **not** call `client.call(...)` again. Upstream screens (lobby, home) hand off the id without pre-creating the Call.
- For ringing, register `client.on("call.ring", ...)` at the app shell, push the incoming-call screen, and let the user accept/reject before mounting `CallContent`.

---

## Safe areas and edge-to-edge

`CallContent`, `RingingCallContent`, `HostLivestream`, `ViewerLivestream`, and the participant views do **not** infer device insets on their own. The app must:

1. Wrap the root with `SafeAreaProvider` from `react-native-safe-area-context`.
2. Read insets via `useSafeAreaInsets()` and pass them through `<StreamVideo>`'s theme:

```tsx
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StreamVideo, type Theme, type DeepPartial } from "@stream-io/video-react-native-sdk";

const VideoWithInsets = ({ client, children }) => {
  const { top, right, bottom, left } = useSafeAreaInsets();
  const theme: DeepPartial<Theme> = { variants: { insets: { top, right, bottom, left } } };
  return <StreamVideo client={client} style={theme}>{children}</StreamVideo>;
};
```

For a scoped override (single screen, landscape iPad, custom toolbar overlap), wrap that subtree in `<StreamTheme style={customTheme}>` instead of the global `<StreamVideo>` style.

**Custom top bar outside `CallContent`**: if the app renders its own top bar above `CallContent`, the SDK's built-in top padding stacks on top of the app bar. Wrap `CallContent` in a scoped `<StreamTheme>` that sets `theme.callContent.container.paddingTop = 0` so only the app bar carries the top inset.

**Custom bottom overlays, drawers, or subtitles** that sit above a custom `CallControls`: `CallContent` already pads the bottom safe area, so absolute offsets measured from the controls also need `theme.variants.insets.bottom` added in. Read `insets` via `useTheme()` inside the overlay.

Full code for both cases: live [Safe area insets cookbook page](https://getstream.io/video/docs/react-native/ui-cookbook/safe-area-insets.md).

On Android the app must also enable edge-to-edge so the call UI draws under transparent system bars before the inset bridge can give it usable padding:

- **Expo**: set `"edgeToEdgeEnabled": true` in `app.json` under `android`.
- **RN CLI 0.81+**: set `edgeToEdgeEnabled=true` in `android/gradle.properties`. The React Native Gradle plugin flips `BuildConfig.IS_EDGE_TO_EDGE_ENABLED` and the generated entry-point calls `WindowUtilKt.setEdgeToEdgeFeatureFlagOn()` for you - no separate package install.
- **Older RN CLI**: install `react-native-edge-to-edge` and inherit a `Theme.EdgeToEdge` variant in `android/app/src/main/res/values/styles.xml`.

iOS is edge-to-edge by default.

Status-bar / nav-bar styling: **Expo** apps use `expo-status-bar` (and optionally `expo-navigation-bar`), already in every Expo template - no extra install. **RN CLI** apps use `<SystemBars style="auto" />` from `react-native-edge-to-edge`. Both APIs are equivalent on Expo SDK 54+ (Expo wrappers delegate to `SystemBars`). Do not call deprecated direct `StatusBar` APIs from `react-native`.

---

## Customization

Use [DOCS.md](DOCS.md) to fetch the manifest-selected UI Cookbook page first. Prefer these in order:

1. Props on `CallContent` for behavior changes (e.g., `layout`, `disablePictureInPicture`).
2. Slot props on `CallContent` for swapping a section (`CallControls`, `CallParticipantsList`, `FloatingParticipantView`).
3. Theme via the `style` prop on `<StreamVideo style={theme}>` (global) or `<StreamTheme style={theme}>` (scoped), plus individual component style props.
4. Custom `ParticipantView` only when the smaller slots cannot satisfy the request.

---

## Ringing, push, and notifications

**Ringing** is opt-in and SDK-managed. Install `@stream-io/react-native-callingx` and follow the manifest-selected `/incoming-calls/ringing-setup/react-native/` and `/incoming-calls/ringing-setup/expo/` pages. The SDK wires CallKit (iOS) and Android Telecom for system-level incoming-call UI; configuration runs through `StreamVideoRN.setPushConfig({ ... })` at app start. On iOS, call `StreamVideoReactNative.voipRegistration()` once from `application:didFinishLaunchingWithOptions:` (Expo injects this via the SDK config plugin). An optional per-platform flag `skipIncomingPushInForeground: true` (under `ios` / `android`) suppresses the CallKit/Telecom UI when the app is already foregrounded so the in-app ringing UI can take over.

**Non-ringing notifications** (`call.missed`, `call.notification`, `call.live_started` - the three values of the SDK's `NonRingingPushEvent` type) are **entirely the app's responsibility**. The SDK does not display them, route taps, or own channel config; use any push + display library (e.g. `@react-native-firebase/messaging`, `expo-notifications`, `@react-native-community/push-notification-ios`, `@notifee/react-native`). Register the device token explicitly with `client.addDevice(token, push_provider, push_provider_name)` - on iOS this requires a **separate APN token** because the VoIP token from ringing is PushKit-only. See manifest-selected `/incoming-calls/non-ringing-notifications-setup/overview/`, `/register-device/`, and `/handling-example/`.

For ringing-provider details (Firebase Cloud Messaging on Android, APNs/PushKit on iOS), fetch the matching push-provider page from the manifest before changing setup. Do not assume background WebSocket behavior or default prop values from memory.

---

## Chat + Video interop

A single RN app can run both `stream-chat-react-native` (or `stream-chat-expo`) and `@stream-io/video-react-native-sdk` together. Build both clients with the same API key and user token; mount providers in any order, but nest them rather than placing them as siblings, and keep both above your navigator. See manifest-selected "Chat Integration" (`/advanced/chat-with-video`) for combined-product gotchas.

---

## Single-call concurrency

Prevent multiple concurrent calls by enabling auto-reject for busy users. Configure on both the client and `StreamVideoRN.setPushConfig`:

```ts
const clientOptions = {
  apiKey,
  user,
  tokenProvider,
  options: { rejectCallWhenBusy: true },
};

const client = StreamVideoClient.getOrCreateInstance(clientOptions);

StreamVideoRN.setPushConfig({
  // Must return Promise<StreamVideoClient | undefined>
  createStreamVideoClient: async () =>
    StreamVideoClient.getOrCreateInstance(clientOptions),
  shouldRejectCallWhenBusy: true,
});
```

`createStreamVideoClient` is required on `setPushConfig` - the SDK invokes it to rebuild the client when waking from a push delivered while the app was terminated. It must return `Promise<StreamVideoClient | undefined>`, so wrap the synchronous `getOrCreateInstance(...)` in an `async` arrow. Share the same `clientOptions` between the in-app client and the push config so push wake-ups reuse the singleton.

This stops a second incoming call from registering in CallKit/Telecom while another call is active. See manifest-selected `/ui-cookbook/ringing/reject-call-when-busy/`.

---

## Error handling

Wrap promise-returning SDK calls in try/catch and surface meaningful errors. Hot paths:

```ts
try {
  await client.connectUser(user, token);
} catch (err) {
  console.error("Failed to connect user", err);
}

try {
  await call.camera.enable();
  await call.microphone.enable();
} catch (err) {
  console.error("Failed to enable a device", err);
}

try {
  await call.join({ maxJoinRetries: 1 });
} catch (err) {
  console.error("Join failed", err);
}
```

`call.join()` retries with exponential backoff by default; cap retries with `maxJoinRetries` when you want fast failure UI.

---

## Device management

- Provide a **lobby** for camera/mic checks before joining a call (see manifest-selected `/ui-cookbook/lobby-preview/`).
- Detect speaking-while-muted via `useCallStateHooks().useMicrophoneState().isSpeakingWhileMuted`.
- Flip cameras with `useCallStateHooks().useCameraState().camera.flip()`.
- Android requires a foreground service for background calls and a runtime notification permission on Android 13+ (see manifest-selected `/guides/keeping-call-alive/`).

---

## Integration best-practices audit (existing apps)

Use this when the user wants to **review, audit, or check** an existing Stream Video React Native integration against Stream's best practices - e.g. *"is my video integration production-ready?"*, *"check my app against Stream's best practices"*, *"what am I missing before launch?"*. This is a **read-only review**: produce findings first; only edit code if the user then asks you to fix them.

Source of truth: [`/video/docs/react-native/advanced/integration-best-practices.md`](https://getstream.io/video/docs/react-native/advanced/integration-best-practices.md). The checklist below folds that page together with this skill's stricter house rules in [`../RULES.md`](../RULES.md). **When the live doc and a house rule differ, the house rule wins** - it is the stricter, RN-specific guidance (e.g. `getOrCreateInstance` is mandatory here, and audio routing is auto-managed - see the carve-outs below).

### How to run it

1. **Detect the app.** Run the Project signals probe in [`SKILL.md`](../SKILL.md) to confirm RN CLI vs Expo and which Stream packages are installed. If `@stream-io/video-react-native-sdk` is absent, stop - there is nothing to audit.
2. **Locate the integration surface.** Grep the app source (`app/`, `src/`, `App.tsx`/`index.*`) and native/config files (`app.json`, `app.config.*`, `ios/**/Info.plist`, `android/**/AndroidManifest.xml`, `android/gradle.properties`) for the anchor symbols in the checklist.
3. **Walk every row.** Most checks are **absence checks** - the failure is a *missing* hook, call, permission, or provider, not visibly wrong code. If the anchor symbol is not found, the row is **FAIL** (or **NEEDS-REVIEW** if it could legitimately live in a file you cannot see, e.g. a backend token route).
4. **Mark `N/A` only when the feature genuinely does not apply** (e.g. ringing-only rows in an app with no ringing) - and say *why*.
5. **Report with the output contract below. Never silently skip a row** - silent omission reads as "covered" when it wasn't.

### Output contract

One line per check: **Verdict** (PASS / FAIL / N/A / NEEDS-REVIEW) | **Severity** (Blocker / High / Medium / Low) | **Evidence** (`file:line`, or "not found") | **Fix** (one line). Close with a prioritized remediation list, Blockers first.

Severity guide: **Blocker** = call won't reliably connect, leaks/keeps publishing media, or breaks push/security; **High** = real production stability or UX gap; **Medium/Low** = polish and hardening.

### Carve-outs (do not raise these as findings)

- **Audio routing (`callManager`).** Do **not** flag missing `callManager.start()/stop()`. The SDK starts/stops audio routing automatically on `call.join()`/`call.leave()`. Only inspect `callManager` when the app deliberately overrides `audioRole` (e.g. a livestream/audio-room *listener*); a wrong/missing role there is the only valid finding.
- **Animation peers.** `react-native-reanimated`/`-worklets`/`-gesture-handler` are optional for Video; their absence is not a failure (the SDK falls back to RN `Animated`). Only note them as a Low "nice-to-have" for smoother floating-tile animation.

### Checklist

**Client & call lifecycle**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| Singleton client | `new StreamVideoClient(` vs `StreamVideoClient.getOrCreateInstance(` | Only `getOrCreateInstance` is used; never `new` | Blocker |
| Client created in `useEffect`, disposed on unmount/sign-out | `disconnectUser(` in a cleanup; client effect keyed on `apiKey`/`user.id` | `client.disconnectUser()` runs on cleanup; client not rebuilt per screen | High |
| `tokenProvider` with ~4h tokens; no committed no-expiry token | `tokenProvider` vs a literal `token:` (static/no-expiry) or `devToken(` in client code | A `tokenProvider` fetches from a backend; no static prod token in source | Blocker |
| One `<StreamVideo>` mounted once, above the navigator | `<StreamVideo`, its position vs `NavigationContainer`/root layout | Single provider near app root, survives screen transitions | High |
| `Call` created once with `{ reuseInstance: true }` in the destination screen | `client.call(`, `reuseInstance` | Exactly one `client.call(type, id, { reuseInstance: true })`; descendants use `useCall()` | High |
| Guarded `call.leave()` on cleanup | `.leave(`, `CallingState.LEFT` | `leave()` runs on unmount, guarded by `callingState !== CallingState.LEFT` | Blocker |
| Only the call id/type passed through navigation params | nav `params`/route props | No `Call` object serialized through navigation | Medium |
| All calling states handled in UI | `useCallCallingState` | UI reacts to `JOINING`/`RECONNECTING`/`RECONNECTING_FAILED`/`OFFLINE`/`LEFT` | High |
| Ringing/push: same client options in app & `setPushConfig`, with `createStreamVideoClient` | `setPushConfig`, `createStreamVideoClient` | Identical options; `createStreamVideoClient` returns the singleton | High (N/A if no ringing/push) |
| Ringing/push: `pushProviderName` is defined in `setPushConfig` | `setPushConfig`, `pushProviderName` | `pushProviderName` value should be defined for ringing flow to function | High (N/A if no ringing/push) |

**Permissions & native config**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| iOS camera/mic usage strings | `NSCameraUsageDescription`, `NSMicrophoneUsageDescription` (Info.plist or Expo webrtc plugin params) | Both present with real copy | Blocker |
| Android base call permissions | `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS`, `BLUETOOTH_CONNECT` (AndroidManifest or Expo plugin) | All declared | Blocker |
| Expo: SDK + webrtc config plugins + `expo-build-properties` (minSdk 24) | `app.json` `plugins` array | `@stream-io/video-react-native-sdk`, `@config-plugins/react-native-webrtc`, `expo-build-properties` all present | Blocker (Expo lane) |
| Foreground-service perms only when earned | `FOREGROUND_SERVICE*` | Declared **only** if background calls (`androidKeepCallAlive`) or screenshare are enabled; not over-declared | Medium |
| Android 13+ runtime `POST_NOTIFICATIONS` (if background/ringing) | `POST_NOTIFICATIONS`, runtime request | Requested at runtime when needed | Medium (N/A if no background/ringing) |
| Permissions requested at a contextual moment, not on app launch | call sites of permission requests | Prompted when entering a call/lobby, not at cold start | Medium |

**Devices & layout**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| Lobby / device check before joining | a pre-join screen, `useCameraState`/`useMicrophoneState` preview | Users can verify devices before connecting | Medium |
| Camera flip + audio route switching available | `useCameraState().camera.flip`, audio-output route UI | Flip control present (multi-camera devices); users can switch audio output route | Low |
| Speaking-while-muted handled or intentionally disabled | `isSpeakingWhileMuted`, `disableSpeakingWhileMutedNotification` | Either surfaced to the user or explicitly disabled | Medium |
| Safe areas + Android edge-to-edge | `SafeAreaProvider`, `variants.insets`/`useSafeAreaInsets`, `edgeToEdgeEnabled` | `SafeAreaProvider` at root, insets bridged into `<StreamVideo style>`, edge-to-edge on (Android) | High |
| Filters expose a manual toggle on low-end devices | `@stream-io/video-filters-react-native`, `@stream-io/noise-cancellation-react-native` | If filters are used, a user toggle exists | Medium (N/A if no filters) |

**Error handling & network**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| `call.join()` awaited and in try/catch | `call.join(` | Awaited, wrapped, errors surfaced (not a floating promise) | Blocker |
| `camera.enable()`/`microphone.enable()` in try/catch | `.enable(` | Each wrapped; failure doesn't strand the UI | High |
| `connectUser`/token errors handled | `connectUser`, tokenProvider body | Rejections caught and surfaced | High |
| Reconnection handled via state, not by ending the call; `setDisconnectionTimeout` tuned | `setDisconnectionTimeout`, calling-state usage | App waits for SDK reconnect; doesn't end on transient drop | Medium |
| Low-bandwidth indicator on custom layouts | custom layout + low-bandwidth UI | Built-in layouts pass automatically; custom layouts notify the user | Medium |
| Firewall/proxy guidance for restrictive networks | n/a | Networking/firewall settings applied, or users advised to switch networks | Low |

**Concurrency, security & ops**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| Single-call concurrency (if concurrent calls are unwanted) | `rejectCallWhenBusy`, `shouldRejectCallWhenBusy` | Set on both `getOrCreateInstance` options and `setPushConfig` | Medium (N/A if concurrent calls are intended) |
| Role permissions enforced in the dashboard, not just hidden in the UI | n/a (server-side) | Confirm with the user that dashboard roles are configured | High (NEEDS-REVIEW) |
| User feedback / rating collected | rating/feedback UI | Some quality-feedback path exists | Low |
| Tested on real devices | n/a | iOS Simulator has no camera/mic; confirm real-device testing | Low (NEEDS-REVIEW) |
| SDK dependencies reasonably current | `package.json` versions vs `npm view` dist-tags | Not far behind latest; review [GitHub Releases](https://github.com/GetStream/stream-video-js/releases) | Low |

---

## Gotchas

- The SDK includes native code; Expo apps must use a development build (not Expo Go).
- iOS Simulator does not support audio/video; test camera/mic on a real device.
- Android emulator support is limited; treat first-class testing as a real device.
- `react-native-gesture-handler` is recommended at the app root if any feature uses gestures; wrap with `GestureHandlerRootView`.
- Re-run `npx expo prebuild --clean` after any change to `app.json` plugins, package versions, or native config.
- Use `StreamVideoClient.getOrCreateInstance` only - never `new StreamVideoClient(...)`. Multiple instances break push and state.
- Create each `Call` instance **exactly once** in the destination call screen via `client.call(type, id, { reuseInstance: true })`. `{ reuseInstance: true }` is required because the same `(type, id)` may already exist (outgoing ring, ringing watcher, deep link, push); without it the SDK constructs a duplicate. Components inside `<StreamCall>` read it with `useCall()` - never call `client.call(...)` again to "retrieve" the same call. Recreating leaks SFU connections and breaks state.
- `call.leave()` on cleanup, **guarded by `call.state.callingState !== CallingState.LEFT`** - dangling calls keep publishing audio/video, but a second `leave()` (custom hangup + unmount, or React 18 strict-mode double-effect) throws `Cannot leave call that has already been left`.
- Pass only the call id through navigation params, not `Call` objects. Upstream screens hand off the id; the destination owns single creation.
- Permissions are prompted on first media access by default; request them explicitly with `react-native-permissions` if you need them before the call screen mounts.
- For ringing on iOS, declare `UIBackgroundModes` includes `voip` and `audio` in `Info.plist`; on Android, declare the foreground service permissions above.
- If using push notifications, fetch the manifest-selected push pages before changing setup. Push wiring varies by provider and SDK version.
- Network reconnects: the SDK auto-reconnects on network changes; use `call.setDisconnectionTimeout(seconds)` to tune the window. Show low-bandwidth indicators per the manifest-selected `/ui-cookbook/low-bandwidth/` page.
- Audio/video filters (noise cancellation, background blur) add CPU overhead; the SDK auto-disables under pressure, but expose a manual toggle for low-end devices.
- Role-based UI hiding is insufficient on its own; configure permissions in the Stream dashboard (see `/guides/permissions-and-moderation/`).

## Troubleshooting

Source: [getstream.io/video/docs/react-native/advanced/troubleshooting/](https://getstream.io/video/docs/react-native/advanced/troubleshooting/)

### Connection issues

A failed WebSocket connection or rejected `call.join()` prevents calls from being established. Always `await` and handle rejection:

```ts
try {
  await call.join();
} catch (err) {
  setError(err);
}
```

- **Expired token** - verify at [jwt.io](https://jwt.io). Always pass a `tokenProvider` to `StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider })` so the SDK refreshes automatically (~4 hour tokens recommended).
- **Wrong secret** - tokens copied from docs use a demo secret and will be rejected. Generate tokens with this app's secret on a backend.
- **User-token mismatch** - the token must be signed for the same `user.id` passed to `getOrCreateInstance`.
- **Firewall/proxy** - restrictive networks may block WebRTC. UDP is preferred; the SDK falls back to TURN over TCP/443 when UDP is blocked. See the manifest-selected `/misc/networking/` page for the port matrix.
- **Retries** - `call.join()` retries up to three times with exponential backoff. Tune with `await call.join({ maxJoinRetries: 1 })`.
- **Mid-call disruptions** - the SDK auto-reconnects; show UI based on `useCallCallingState()` (`CallingState.RECONNECTING`, `CallingState.RECONNECTING_FAILED`) and tune the window with `call.setDisconnectionTimeout(seconds)`. See the [Network Disruptions](https://getstream.io/video/docs/react-native/ui-cookbook/network-disruption/) cookbook.

### Ringing call issues

- **App in foreground:** ringing UI shows over the active socket - fix connection issues first.
- **App in background or killed:** requires push (FCM on Android, APN/VoIP + CallKit on iOS). Mount `<StreamVideo>` at the app root so push-driven events are not missed during hot reload, and call `StreamVideoRN.setPushConfig(...)` with provider names that match the dashboard.
- **Singleton client** - always `StreamVideoClient.getOrCreateInstance(...)`; multiple instances break push delivery and state.
- **Calling yourself** - caller and callee must be different users.
- **Unknown member** - the callee must have connected to Stream at least once so the device token is registered.
- **Reused call id** - ringing fires only once per call id. Use a fresh UUID (or server-issued id) for each ringing call.
- **Dashboard logs** - in the [Stream dashboard](https://dashboard.getstream.io/), open **Webhook & Push Logs** for Video & Audio and filter by `error` to see delivery failures.
- **iOS** - VoIP certificate bundle id matches the app, Push Notifications capability enabled, background modes include `voip`, `audio`, `remote-notification`, `processing`. Disable Do Not Disturb when testing CallKit. A failed `mustReport` to CallKit can cause iOS to stop delivering VoIP pushes - reinstall the app to recover.
- **Android** - grant `POST_NOTIFICATIONS` at runtime on Android 13+, declare `FOREGROUND_SERVICE` permissions, and check OEM battery optimizations (OnePlus Deep Clear, etc.) that block killed-app notifications. Force-stopped apps cannot receive push until the user reopens them.
- **Dev-mode quirk** - during hot reload, global event listeners can de-register and accept/reject taps silently no-op. Fully restart the app or test a release build.

### Logs

Default SDK log level is `warn`. Raise it via `options.logLevel` on `getOrCreateInstance` (levels: `trace`, `debug`, `info`, `warn`, `error`):

```ts
import { StreamVideoClient } from "@stream-io/video-react-native-sdk";

const client = StreamVideoClient.getOrCreateInstance({
  apiKey,
  user,
  tokenProvider,
  options: { logLevel: "debug" },
});
```

For native WebRTC packet/peer-connection traces, set `WebRTCModuleOptions.loggingSeverity = .verbose` (iOS, in `AppDelegate`) or `Logging.Severity.LS_VERBOSE` (Android, in `MainApplication`) - then watch Xcode or Android Studio. Configure log level before connecting; changes after the socket is established do not retroactively rewrite existing connection state.
