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
  expo-build-properties
```

Install `@latest` only after confirming the npm dist-tag matches the selected docs. If not, use the manifest-selected docs' tag or exact version.

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

Android `AndroidManifest.xml` (before `<application>`):

```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.MODIFY_AUDIO_SETTINGS" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CAMERA" />
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
| Android push (FCM) | `@react-native-firebase/app`, `@react-native-firebase/messaging` |
| iOS local notifications | `@react-native-community/push-notification-ios` |
| Non-ringing Android notifications | `@notifee/react-native` |
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
stream token <user_id>
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

A `Call` represents one logical call (a `(type, id)` pair). Create the call inside a `useEffect` after the client is ready and **always call `call.leave()` on cleanup** - dangling calls keep publishing audio/video and leak memory.

```tsx
import { useEffect, useState } from "react";
import { useStreamVideoClient, Call } from "@stream-io/video-react-native-sdk";

const client = useStreamVideoClient();
const [call, setCall] = useState<Call>();

useEffect(() => {
  if (!client) return;
  const c = client.call(type, id);
  setCall(c);
  c.join().catch((err) => console.error("Failed to join", err));
  return () => {
    c.leave().catch((err) => console.error(err));
    setCall(undefined);
  };
}, [client, type, id]);
```

A call is initialized after any of `await call.get()`, `await call.create()`, `await call.getOrCreate()`, or `await call.join()`.

### Lifecycle methods

- `getOrCreate(data?)` - server-side reserve/create
- `join(options?)` - connect to the SFU and start sending/receiving media. Retries with exponential backoff; tune with `{ maxJoinRetries }`.
- `leave()` - disconnect locally, keep call alive for others. **Always call on unmount.**
- `endCall()` - end the call for everyone
- `accept()` / `reject()` - ringing-call handling
- `getOrCreate({ ring: true, data: { members } })` - start an outgoing ringing call
- `setDisconnectionTimeout(seconds)` - reconnection window before the SDK gives up

### Audio routing

`callManager` controls speaker/earpiece/Bluetooth routing. Start it when joining and stop when leaving:

```ts
import { callManager } from "@stream-io/video-react-native-sdk";

callManager.start({ audioRole: "communicator", deviceEndpointType: "speaker" });
// later, when leaving:
callManager.stop();
```

### Call types

`default`, `livestream`, `audio_room`, `development`. Configure per-type policies (permissions, settings, recording defaults) in the Stream dashboard or via `client.callTypes.update(...)`. See manifest-selected "Configuring Call Types".

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

`useCallStateHooks().useCallRingingState()` exposes the ringing phase for incoming/outgoing ringing calls. Pair with `client.on("call.ring", ...)` at the app shell so an incoming call can surface UI even when no screen has the call mounted yet.

### Participants

```ts
const { useParticipants, useLocalParticipant, useRemoteParticipants } = useCallStateHooks();
const participants = useParticipants();
const local = useLocalParticipant();
```

`ParticipantState` exposes `userId`, `name`, `image`, `audioStream`, `videoStream`, `isSpeaking`, `audioLevel`, `connectionQuality`, `pinned`, `roles`, and reaction state.

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
| `CallContent` | Default in-call UI; slot props for `CallTopView`, `ParticipantsInfoBadge`, `CallControls`, `CallParticipantsList` |
| `CallControls` | Mic / camera / screenshare / reactions / hangup row |
| `IncomingCall` | Built-in incoming-call screen UI |
| `OutgoingCall` | Built-in outgoing-call screen UI |
| `ParticipantView` | Renders one participant's video tile |
| `LivestreamPlayer` | Viewer-only livestream player |
| `HostLivestream` | Host-side livestream UI |
| `useStreamVideoClient` | Reads the provided client inside `StreamVideo` |
| `useCall` | Reads the current `Call` inside `StreamCall` |
| `useCallStateHooks` | Returns sub-hooks for call/participant state |
| `StreamVideoRN` | Static config surface (push, theme overrides, i18n) |

---

## Navigation rules

- Put `StreamVideo` above any screen that needs a call. With React Navigation, prefer it above `NavigationContainer` so deep links land inside the provider.
- Keep one `StreamVideo` mounted for the whole authenticated session. Tearing it down restarts the WebSocket.
- Pass `call.cid` (string) through navigation params, not the `Call` object itself.
- Recreate the call from `client.call(type, id)` in the destination screen, then `StreamCall call={call}`.
- For ringing, register `client.on("call.ring", ...)` at the app shell, push the incoming-call screen, and let the user accept/reject before mounting `CallContent`.

---

## Customization

Use [DOCS.md](DOCS.md) to fetch the manifest-selected UI Cookbook page first. Prefer these in order:

1. Props on `CallContent` for behavior changes (e.g., `layout`, `disablePictureInPicture`).
2. Slot props on `CallContent` for swapping a section (`CallControls`, `CallTopView`, `CallParticipantsList`).
3. Theme via `StreamVideoRN.setTheme(...)` and individual component style props.
4. Custom `ParticipantView` only when the smaller slots cannot satisfy the request.

---

## Ringing, push, and notifications

Ringing is opt-in. Install `@stream-io/react-native-callingx` and follow the manifest-selected "Incoming calls" pages. The SDK wires CallKit (iOS) and Android Telecom for system-level incoming-call UI; configuration runs through `StreamVideoRN.setPushConfig({ ... })` at app start.

For push providers (Firebase Cloud Messaging on Android, APNs/PushKit on iOS), fetch the matching push-provider page from the manifest before changing setup. Do not assume background WebSocket behavior or default prop values from memory.

---

## Chat + Video interop

A single RN app can run both `stream-chat-react-native` (or `stream-chat-expo`) and `@stream-io/video-react-native-sdk` together. Build both clients with the same API key and user token; mount providers in any order, but nest them rather than placing them as siblings, and keep both above your navigator. See manifest-selected "Chat Integration" (`/advanced/chat-with-video`) for combined-product gotchas.

---

## Single-call concurrency

Prevent multiple concurrent calls by enabling auto-reject for busy users. Configure on both the client and `StreamVideoRN.setPushConfig`:

```ts
const client = StreamVideoClient.getOrCreateInstance({
  apiKey,
  user,
  tokenProvider,
  options: { rejectCallWhenBusy: true },
});

StreamVideoRN.setPushConfig({
  shouldRejectCallWhenBusy: true,
});
```

This stops a second incoming call from registering in CallKit/Telecom while another call is active.

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

## Gotchas

- The SDK includes native code; Expo apps must use a development build (not Expo Go).
- iOS Simulator does not support audio/video; test camera/mic on a real device.
- Android emulator support is limited; treat first-class testing as a real device.
- `react-native-gesture-handler` is recommended at the app root if any feature uses gestures; wrap with `GestureHandlerRootView`.
- Re-run `npx expo prebuild --clean` after any change to `app.json` plugins, package versions, or native config.
- Use `StreamVideoClient.getOrCreateInstance` only - never `new StreamVideoClient(...)`. Multiple instances break push and state.
- Always `call.leave()` on cleanup. Dangling calls keep publishing audio/video.
- Pass `call.cid`, not `Call` objects, through navigation params.
- Permissions are prompted on first media access by default; request them explicitly with `react-native-permissions` if you need them before the call screen mounts.
- For ringing on iOS, declare `UIBackgroundModes` includes `voip` and `audio` in `Info.plist`; on Android, declare the foreground service permissions above.
- If using push notifications, fetch the manifest-selected push pages before changing setup. Push wiring varies by provider and SDK version.
- Network reconnects: the SDK auto-reconnects on network changes; use `call.setDisconnectionTimeout(seconds)` to tune the window. Show low-bandwidth indicators per the manifest-selected `/ui-cookbook/low-bandwidth/` page.
- Audio/video filters (noise cancellation, background blur) add CPU overhead; the SDK auto-disables under pressure, but expose a manual toggle for low-end devices.
- Role-based UI hiding is insufficient on its own; configure permissions in the Stream dashboard (see `/guides/permissions-and-moderation/`).

TODO: Troubleshooting deep-dive (connection errors, ringing-on-push, logs) - fill from manifest-selected `/advanced/troubleshooting/` and provider-specific incoming-calls pages.
