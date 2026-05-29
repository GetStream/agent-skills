# Video React Native - Screen and Component Blueprints

Load only the section you are implementing. For `llms.txt` manifest search, see [DOCS.md](DOCS.md). For setup, packages, and gotchas, see [VIDEO-REACT-NATIVE.md](VIDEO-REACT-NATIVE.md).

All snippets import from `@stream-io/video-react-native-sdk`. The package name is the same on RN CLI and Expo - there is no separate Expo package for Video.

---

## Request -> Blueprint section

| Request | Read section |
|---|---|
| root setup, providers, auth gate, login | App Provider and Auth Gate |
| brand new React Native or Expo app with Video | Fresh App Scaffold |
| home, lobby, join or start a call by id | Home / Join-or-Start Call |
| active call screen, in-call UI | Active Call Screen |
| ringing, incoming call, outgoing call, accept, reject | Ringing Blueprint |
| custom call controls, replace hangup row | Custom Call Controls Blueprint |
| custom participant tile, override video tile | Custom Participant Tile Blueprint |
| participant grid, layout, speaker layout | Participant Grid Blueprint |
| deep link into a call, push -> call screen | Call Deep-link Blueprint |
| React Navigation or Expo Router shell | Navigation Shell |
| host / broadcast a livestream, RTMP, watch / view a livestream | Livestream Blueprint |
| audio room, spaces, speaker / listener, request to speak, go live | Audio Room Blueprint |
| chat + video in the same app, call button inside a chat channel | Chat + Video Blueprint |
| theming, generic UI slot override | DOCS.md -> manifest lookup, then VIDEO-REACT-NATIVE.md > Customization |

If no row matches, read [DOCS.md](DOCS.md) and [VIDEO-REACT-NATIVE.md](VIDEO-REACT-NATIVE.md) first, then verify symbols in manifest-selected docs or the installed package before coding.

---

## App Provider and Auth Gate

Use this when adding Stream Video to the app root. Replace static credentials with values from the app's auth flow or [`../credentials.md`](../credentials.md).

```tsx
import React, { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Button, TextInput, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from "react-native-safe-area-context";
import { StatusBar } from "expo-status-bar";
import {
  StreamVideo,
  StreamVideoClient,
  type Theme,
  type DeepPartial,
  User,
} from "@stream-io/video-react-native-sdk";

type Session = {
  apiKey: string;
  token: string;
  userId: string;
  userName: string;
};

const Loading = () => (
  <View style={{ alignItems: "center", flex: 1, justifyContent: "center" }}>
    <ActivityIndicator size="large" />
  </View>
);

// Bridge device insets into StreamVideo's theme so CallContent / RingingCallContent
// respect notches and system bars (Android edge-to-edge + iOS safe areas).
const VideoWithInsets = ({
  children,
  client,
}: {
  children: React.ReactNode;
  client: StreamVideoClient;
}) => {
  const { top, right, bottom, left } = useSafeAreaInsets();
  const theme: DeepPartial<Theme> = {
    variants: { insets: { top, right, bottom, left } },
  };
  return (
    <StreamVideo client={client} style={theme}>
      {children}
    </StreamVideo>
  );
};

// LOCAL-DEMO ONLY. Editable API key / token / user id are convenient for
// pasted Stream CLI credentials during development. They are NOT a production
// auth flow - a real client must never choose its own Stream user id (see
// "Production auth gate" below for the safe pattern).
const LoginScreen = ({
  demoDefaults,
  onSession,
}: {
  demoDefaults?: Partial<Session>;
  onSession: (session: Session) => void;
}) => {
  const [apiKey, setApiKey] = useState(demoDefaults?.apiKey ?? "");
  const [token, setToken] = useState(demoDefaults?.token ?? "");
  const [userId, setUserId] = useState(demoDefaults?.userId ?? "");
  const [userName, setUserName] = useState(demoDefaults?.userName ?? "");

  const signIn = useCallback(() => {
    if (!apiKey || !token || !userId) return;
    onSession({ apiKey, token, userId, userName: userName || userId });
  }, [apiKey, onSession, token, userId, userName]);

  return (
    <View style={{ flex: 1, justifyContent: "center", padding: 24 }}>
      <TextInput autoCapitalize="none" onChangeText={setApiKey} placeholder="API key" value={apiKey} />
      <TextInput autoCapitalize="none" onChangeText={setToken} placeholder="User token" value={token} />
      <TextInput autoCapitalize="none" onChangeText={setUserId} placeholder="User id" value={userId} />
      <TextInput autoCapitalize="words" onChangeText={setUserName} placeholder="User name" value={userName} />
      <Button disabled={!apiKey || !token || !userId} onPress={signIn} title="Sign in (demo)" />
    </View>
  );
};

const ConnectedVideo = ({
  children,
  session,
}: {
  children: React.ReactNode;
  session: Session;
}) => {
  const [client, setClient] = useState<StreamVideoClient>();

  useEffect(() => {
    const user: User = { id: session.userId, name: session.userName };
    const tokenProvider = async () => session.token; // swap for a fetch in production
    const c = StreamVideoClient.getOrCreateInstance({
      apiKey: session.apiKey,
      user,
      tokenProvider,
      // Optional: auto-reject incoming calls while another is active.
      // Pair with `shouldRejectCallWhenBusy: true` on setPushConfig (see Ringing).
      // options: { rejectCallWhenBusy: true },
    });
    setClient(c);
    return () => {
      c.disconnectUser().catch((err) => console.error(err));
      setClient(undefined);
    };
  }, [session]);

  if (!client) return <Loading />;
  return <VideoWithInsets client={client}>{children}</VideoWithInsets>;
};

export default function App() {
  const [session, setSession] = useState<Session | null>(null);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <StatusBar style="auto" />
        {session ? (
          <ConnectedVideo session={session}>
            {/* navigation lives here */}
          </ConnectedVideo>
        ) : (
          <LoginScreen onSession={setSession} />
        )}
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
```

Always use `StreamVideoClient.getOrCreateInstance(...)` (not `new StreamVideoClient(...)`); the SDK relies on the singleton for push notifications and call state. Pair with a `tokenProvider` (~4-hour tokens) in production so the SDK refreshes automatically. See [VIDEO-REACT-NATIVE.md > Client setup](VIDEO-REACT-NATIVE.md#client-setup) and the live [Integration Best Practices](https://getstream.io/video/docs/react-native/advanced/integration-best-practices.md) page.

### Production auth gate (replace the demo `LoginScreen` for real apps)

**The Stream user id must be derived server-side from the authenticated session, never sent by the client.** A client-supplied `user_id` query/body parameter on a token endpoint is a trust-boundary bug: any signed-in user could mint a Stream token for any other user and impersonate them in calls.

The mobile app authenticates with the customer's own auth system (cookie, bearer token, OAuth, Firebase Auth, Clerk, Auth0, etc.). The backend reads the authenticated principal from the request and returns the Stream `apiKey`, the Stream `user_id` it picked, and either a freshly minted Stream token or a refreshable token endpoint:

```ts
// Customer backend - e.g. Node + Stream server SDK:
import { StreamClient } from "@stream-io/node-sdk";
const stream = new StreamClient(STREAM_API_KEY, STREAM_API_SECRET);

app.get("/api/stream/session", requireAuth, (req, res) => {
  const user = req.user;                       // from your session/JWT middleware
  const token = stream.generateUserToken({     // ~4h TTL recommended
    user_id: user.id,
    validity_in_seconds: 60 * 60 * 4,
  });
  res.json({
    apiKey: STREAM_API_KEY,
    userId: user.id,                            // server-chosen, never client-supplied
    userName: user.displayName,
    userImage: user.avatarUrl,
    token,
  });
});
```

The mobile app then fetches that session and wires a `tokenProvider` that re-hits the same authenticated endpoint when the token nears expiry - the SDK never sees a refresh secret, and the client never names a Stream user id:

```tsx
import { useEffect, useState } from "react";
import {
  StreamVideoClient,
  type TokenProvider,
  type User,
} from "@stream-io/video-react-native-sdk";

type ServerSession = {
  apiKey: string;
  userId: string;
  userName?: string;
  userImage?: string;
  token: string;
};

// `fetchAuthed` is the app's own authenticated fetch wrapper - it forwards the
// signed-in user's cookie / bearer / OAuth header. It does NOT take a user id.
const fetchStreamSession = async (): Promise<ServerSession> => {
  const res = await fetchAuthed("/api/stream/session");
  if (!res.ok) throw new Error(`Stream session failed: ${res.status}`);
  return res.json();
};

export const useProductionStreamClient = () => {
  const [client, setClient] = useState<StreamVideoClient>();

  useEffect(() => {
    let cancelled = false;
    let current: StreamVideoClient | undefined;
    (async () => {
      const session = await fetchStreamSession();
      if (cancelled) return;
      const user: User = {
        id: session.userId,
        name: session.userName,
        image: session.userImage,
      };
      // tokenProvider re-hits the SAME authenticated endpoint - the server
      // re-derives user id from the session and mints a fresh token.
      const tokenProvider: TokenProvider = async () => {
        const fresh = await fetchStreamSession();
        return fresh.token;
      };
      current = StreamVideoClient.getOrCreateInstance({
        apiKey: session.apiKey,
        user,
        token: session.token,
        tokenProvider,
      });
      setClient(current);
    })().catch((err) => console.error("Stream auth failed", err));
    return () => {
      cancelled = true;
      current?.disconnectUser().catch((err) => console.error(err));
      setClient(undefined);
    };
  }, []);

  return client;
};
```

What this rules out:
- No client input controls which Stream user the token is minted for - the server reads it from its own session.
- The Stream **API secret** stays on the customer's backend; the SDK only ever receives short-lived user tokens.
- The same endpoint serves the initial session and the refresh, so token rotation reuses the existing auth check.

The demo `LoginScreen` above remains useful for local development with pasted Stream CLI credentials (see [`../credentials.md`](../credentials.md)) and for the Stream sample apps - keep it gated behind a build-time check (`__DEV__` or a feature flag) so it cannot ship in a production build.

`SafeAreaProvider` + `VideoWithInsets` is the canonical safe-area wiring: `SafeAreaProvider` exposes device insets, and `VideoWithInsets` bridges them into `<StreamVideo>`'s theme so `CallContent`, `RingingCallContent`, and participant views respect notches and system bars without an extra `SafeAreaView` wrap. `<StatusBar style="auto" />` handles status-bar text contrast against the app's background.

The snippet above defaults to the Expo lane: `expo-status-bar` is in every Expo template, so no extra install is needed. **RN CLI apps swap that import** to `import { SystemBars } from "react-native-edge-to-edge"` and use `<SystemBars style="auto" />` (and install `react-native-edge-to-edge` directly). Both APIs are equivalent on Expo SDK 54+; `expo-status-bar` simply delegates to `SystemBars` under the hood. For Android nav-bar styling on Expo, add `expo-navigation-bar` (also in the Expo template). On Android, edge-to-edge itself is enabled via Expo `app.json` `"edgeToEdgeEnabled": true` or the `react-native-edge-to-edge` theme on RN CLI; see [VIDEO-REACT-NATIVE.md > Safe areas and edge-to-edge](VIDEO-REACT-NATIVE.md#safe-areas-and-edge-to-edge).

---

## Home / Join-or-Start Call

Use this for a lobby screen where the user picks or enters a call id and navigates into the call screen. **The Home screen does not create the `Call` instance** - it only hands the id off through navigation. The destination Active Call screen owns the single creation. Pre-creating here and recreating downstream is a bug: it produces two `Call` objects, leaks SFU connections, and breaks state.

```tsx
import { useCallback, useState } from "react";
import { Button, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";

export const HomeScreen = () => {
  const navigation = useNavigation<any>();
  const [callId, setCallId] = useState("");

  const onJoin = useCallback(() => {
    if (!callId) return;
    navigation.navigate("ActiveCall", { callId });
  }, [callId, navigation]);

  return (
    <SafeAreaView style={{ flex: 1 }} edges={["top", "bottom"]}>
      <View style={{ flex: 1, justifyContent: "center", padding: 24 }}>
        <TextInput
          autoCapitalize="none"
          onChangeText={setCallId}
          placeholder="Call id"
          value={callId}
        />
        <Button disabled={!callId} onPress={onJoin} title="Join call" />
      </View>
    </SafeAreaView>
  );
};
```

`SafeAreaView` here comes from `react-native-safe-area-context`, not `"react-native"` (that one is deprecated and Android-blind). For finer control - e.g. an absolutely positioned floating action button that needs `bottom` inset only - reach for `useSafeAreaInsets()` from the same package and pad manually. Pass only `callId` through navigation. For pre-join device checks (camera test, mic test, output picker), see the **Lobby Preview** pattern in the manifest-selected `/ui-cookbook/lobby-preview/` page - the canonical lobby pre-creates a Call instance specifically for the preview so `useCallStateHooks()` can read camera/microphone state through a real `<StreamCall>` context.

---

## Active Call Screen

The default in-call experience. The screen calls `client.call(type, id, { reuseInstance: true })` once inside `useEffect`, joins, and mounts `<StreamCall>`. `{ reuseInstance: true }` is required because the same `(type, id)` may already be in the SDK's managed list - delivered by an outgoing ring, an incoming ringing watcher, or a deep link / push - and a second construction would produce a duplicate `Call`. With the flag, the SDK returns the cached singleton. Child components read the call via `useCall()` from `<StreamCall>` context; they must **not** call `client.call(...)` again to retrieve it.

`call.leave()` runs on unmount, **guarded by `callingState !== CallingState.LEFT`** so leaving twice (hangup button + unmount, or React 18 strict-mode double-effect) does not throw `Cannot leave call that has already been left`. Hangup handlers should only navigate; `CallContent`'s default hangup already calls `leave()`.

```tsx
import { useEffect, useState } from "react";
import {
  useStreamVideoClient,
  StreamCall,
  CallContent,
  Call,
  CallingState,
} from "@stream-io/video-react-native-sdk";
import { useNavigation, useRoute } from "@react-navigation/native";

export const ActiveCallScreen = () => {
  const client = useStreamVideoClient();
  const navigation = useNavigation<any>();
  const { callId, callType = "default" } = useRoute().params as {
    callId: string;
    callType?: string;
  };
  const [call, setCall] = useState<Call>();

  useEffect(() => {
    if (!client) return;
    const c = client.call(callType, callId, { reuseInstance: true });
    setCall(c);

    // Tune the reconnect window (seconds). The SDK keeps the call alive
    // through brief network drops instead of ending it; 120s is a good default.
    c.setDisconnectionTimeout(120);

    (async () => {
      try {
        // `create: true` lets a "join by id" flow work even when the
        // (type, id) doesn't exist server-side yet - the SDK creates it on
        // join. Drop the flag if you only want to join calls created upstream
        // (ringing, host livestream, audio room, etc.).
        await c.join({ create: true });
      } catch (err) {
        console.error("Failed to join", err);
      }
    })();

    return () => {
      if (c.state.callingState !== CallingState.LEFT) {
        c.leave().catch((err) => console.error(err));
      }
      setCall(undefined);
    };
  }, [client, callType, callId]);

  if (!call) return null;

  return (
    <StreamCall call={call}>
      <CallContent onHangupCallHandler={() => navigation.goBack()} />
    </StreamCall>
  );
};
```

**Pre-call device enable (lobby / permission gate).** When you need cameras and mics live *before* `join()` - e.g. a lobby preview where the user checks themselves on camera - `enable()` them explicitly with `try/catch` so a denied permission surfaces a meaningful error rather than a silent black tile:

```tsx
try {
  await call.camera.enable();
  await call.microphone.enable();
} catch (err) {
  console.error("Failed to enable a device", err);
}
```

For a plain join-by-id flow, you do not need this block - `call.join()` brings up devices per the call type's defaults.

`CallContent` provides the full default UI - top bar, participant grid, and call controls. Inside `<StreamCall>`, any child component (custom controls, participant tile, ringing UI, in-call toolbar) reads the current call via `useCall()` - never `client.call(...)` again. Replace any slot via its props; see Custom Call Controls and Custom Participant Tile blueprints below. Audio routing (speaker/earpiece/Bluetooth) is handled automatically by `call.join()` / `call.leave()` with `audioRole: "communicator"` as the default - do not call `callManager.start/stop` yourself unless you are overriding the role (the only other value is `"listener"`, for a view-only livestream viewer or audio-room audience member).

Notice the screen does **not** wrap `<CallContent />` in a `SafeAreaView`. `CallContent`, `RingingCallContent`, `HostLivestream`, and `ViewerLivestream` all read insets from `<StreamVideo>`'s theme (`variants.insets`) - wire them once at the App Provider blueprint and the call screen renders edge-to-edge with the correct padding on both iOS and Android. See [VIDEO-REACT-NATIVE.md > Safe areas and edge-to-edge](VIDEO-REACT-NATIVE.md#safe-areas-and-edge-to-edge).

The destructured `callType` defaults to `"default"` for the simple join-by-id case but accepts whatever the deep-link / ringing watcher / push handler delivers (`livestream`, `audio_room`, custom call types).

**Always pass `{ reuseInstance: true }` from a destination call screen.** Any screen the user can land on - via deep link, push, ringing accept, navigation from a lobby, or external linking - may find the same `(type, id)` already live in the SDK (outgoing ring, ringing watcher, push wake-up, deep link). Without the flag the SDK constructs a duplicate that leaks SFU connections and breaks state. The cost when the call is not yet known is zero - the SDK simply creates and caches it. For calls that arrive via **ringing**, the canonical pattern is still to read the existing instance from `useCalls()` (see the Ringing Blueprint) rather than reconstructing it; reach for `client.call(...)` only when you must obtain a `Call` reference yourself for an id you were handed through navigation or a payload.

---

## Navigation Shell

Minimal React Navigation shell. Place `StreamVideo` above `NavigationContainer` so the client survives screen transitions.

```tsx
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { HomeScreen } from "./HomeScreen";
import { ActiveCallScreen } from "./ActiveCallScreen";

const Stack = createNativeStackNavigator();

export const VideoNavigator = () => (
  <NavigationContainer>
    <Stack.Navigator>
      <Stack.Screen name="Home" component={HomeScreen} />
      <Stack.Screen name="ActiveCall" component={ActiveCallScreen} />
    </Stack.Navigator>
  </NavigationContainer>
);
```

For Expo Router, wrap `app/_layout.tsx` with `StreamVideo` inside `GestureHandlerRootView` and use file-based routes for `Home` and `ActiveCall`.

---

## Ringing Blueprint

`RingingCallContent` reads `call.state.callingState` and routes between the default `IncomingCall`, `OutgoingCall`, and accepted `CallContent` slots (each is an overridable prop). Pair it with the client-level `useCalls()` hook to surface incoming or outgoing ringing calls from anywhere in the app. Deeper detail lives on the live [Ringing](https://getstream.io/video/docs/react-native/incoming-calls/ringing.md) and [RingingCallContent](https://getstream.io/video/docs/react-native/ui-components/call/ringing-call-content.md) pages.

### Surfacing an incoming call from the app shell

Mount the watcher once, **inside `<StreamVideo>` but above your navigator**, so it covers every screen and also catches calls that arrive via push while the app is backgrounded. The Call instance comes from `useCalls()` - the app shell never calls `client.call(...)` itself.

```tsx
import { StyleSheet, View } from "react-native";
import {
  RingingCallContent,
  StreamCall,
  useCalls,
} from "@stream-io/video-react-native-sdk";

export const RingingCalls = () => {
  // SDK-managed ringing calls (incoming + outgoing). For simplicity, take the
  // first one - there can be multiple ringing at once if you allow it.
  const ringingCall = useCalls().filter((c) => c.ringing)[0];
  if (!ringingCall) return null;

  return (
    <StreamCall call={ringingCall}>
      <View style={StyleSheet.absoluteFill}>
        <RingingCallContent />
      </View>
    </StreamCall>
  );
};
```

Render it as a sibling of your navigator: `<StreamVideo client={client}><MyApp /><RingingCalls /></StreamVideo>`. `RingingCallContent` reads insets from `StreamVideo`'s theme (`variants.insets`) - wire those once at the App Provider level via `useSafeAreaInsets()` so this overlay respects notches and system bars without an extra `SafeAreaView` wrap. `RingingCallContent` switches to `CallContent` on accept, so the accepted call flows into the active-call UI without an explicit navigation step. If you do navigate (e.g. to surface the existing Active Call Screen blueprint), pass only `ringingCall.id` and `ringingCall.type` through navigation - the destination screen passes `{ reuseInstance: true }` to `client.call(...)` so the SDK returns the same `Call` instance the watcher was rendering, not a new one.

### Starting an outgoing ringing call

The screen that triggers the ring calls `client.call(type, id, { reuseInstance: true })` once and fires `getOrCreate({ ring: true, ... })`. The shell-level `RingingCalls` watcher then picks the call up via `useCalls()` (a read of the SDK's managed list - not another construction), and any later navigation into the Active Call screen also passes `{ reuseInstance: true }` so the same instance is reused everywhere. Always include the caller in `members`.

```tsx
import { useCallback } from "react";
import { Button } from "react-native";
import { useStreamVideoClient } from "@stream-io/video-react-native-sdk";

export const RingPeerButton = ({ peerId, myId }: { peerId: string; myId: string }) => {
  const client = useStreamVideoClient();

  const onPress = useCallback(async () => {
    if (!client) return;
    const callId = `ring-${Date.now()}`; // unique id - do not reuse
    const call = client.call("default", callId, { reuseInstance: true });
    await call.getOrCreate({
      ring: true,
      video: true,
      data: { members: [{ user_id: myId }, { user_id: peerId }] },
    });
  }, [client, myId, peerId]);

  return <Button onPress={onPress} title={`Call ${peerId}`} />;
};
```

`getOrCreate({ ring: true })` starts the signaling flow and (with `StreamVideoRN.setPushConfig` set up) delivers a VoIP / FCM notification to each member. Reuse of call ids is unsupported - generate a fresh one per ring. Use `call.ring({ members_ids: [...] })` if you need to ring into an existing call instead. The shell-level `RingingCalls` watcher renders `<StreamCall>` around the same instance via `useCalls()`; the Active Call screen later reuses the same instance via `{ reuseInstance: true }` when the user navigates in.

### Accepting / rejecting manually

Inside `<StreamCall>`, read the Call with `useCall()` and the calling state with `useCallStateHooks().useCallCallingState()`. Guard `leave()` with `callingState !== CallingState.LEFT` to survive React 18 strict-mode double-effects and hangup+unmount races.

```tsx
import { useCallback } from "react";
import { Button, View } from "react-native";
import {
  CallingState,
  useCall,
  useCallStateHooks,
} from "@stream-io/video-react-native-sdk";

export const IncomingCallButtons = () => {
  const call = useCall();
  const { useCallCallingState } = useCallStateHooks();
  const callingState = useCallCallingState();

  const accept = useCallback(async () => {
    // call.join() is the accept action - no separate accept() step
    await call?.join();
  }, [call]);

  const reject = useCallback(async () => {
    if (!call || callingState === CallingState.LEFT) return;
    await call.leave({ reject: true, reason: "decline" });
  }, [call, callingState]);

  return (
    <View>
      <Button onPress={accept} title="Accept" />
      <Button onPress={reject} title="Reject" />
    </View>
  );
};
```

**Wiring:**
- `call.join()` is the accept action on RN - it records acceptance with the backend and enters the media session in one step. Audio routing (`audioRole: "communicator"`) is auto-managed by `join()` / `leave()`; do not call `callManager.start/stop` here.
- Reject an incoming call with `call.leave({ reject: true, reason: "decline" })`. Cancel an outgoing call with `call.leave({ reject: true, reason: "cancel" })` before the first callee accepts.
- Replace the default ringing UIs by passing `IncomingCall`, `OutgoingCall`, or `CallContent` component refs to `<RingingCallContent ... />`. Match the prop signatures on the live [RingingCallContent](https://getstream.io/video/docs/react-native/ui-components/call/ringing-call-content.md) page; the [Incoming & Outgoing Call cookbook](https://getstream.io/video/docs/react-native/ui-cookbook/incoming-and-outgoing-call.md) shows full custom replacements built from `useCallMembers` and the accept/reject buttons above.
- For background and terminated ringing (CallKit on iOS, Telecom + FCM on Android), call `StreamVideoRN.setPushConfig({...})` once at module load - including a `createStreamVideoClient` callback that builds the client with `StreamVideoClient.getOrCreateInstance(...)`. To auto-reject a second incoming call while one is active, pair `options: { rejectCallWhenBusy: true }` on `getOrCreateInstance` with `shouldRejectCallWhenBusy: true` on `setPushConfig` (both keys are required - the client option covers the foreground/socket path, the push-config option covers the CallKit/Telecom path):
  ```ts
  const clientOptions = { apiKey, user, tokenProvider, options: { rejectCallWhenBusy: true } };
  StreamVideoClient.getOrCreateInstance(clientOptions);
  StreamVideoRN.setPushConfig({
    createStreamVideoClient: async () => StreamVideoClient.getOrCreateInstance(clientOptions),
    shouldRejectCallWhenBusy: true,
  });
  ```
  Full wiring (Info.plist keys, AppDelegate PushKit hooks, Firebase listeners, `@stream-io/react-native-callingx`) is documented at [Ringing Setup - React Native](https://getstream.io/video/docs/react-native/incoming-calls/ringing-setup/react-native.md).
- **Android 13+ (API 33+) runtime notification permission.** Push delivery for ringing requires the user to grant `POST_NOTIFICATIONS` at runtime - the SDK will not display incoming-call notifications without it. Request it explicitly (via `react-native-permissions`, `expo-notifications`, `PermissionsAndroid.request("android.permission.POST_NOTIFICATIONS")`, or your push library's helper) **before** the first ringing call is expected. Declare `<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />` in `AndroidManifest.xml` (Expo's notification config plugin or the SDK config plugin emit it for you).
- To let the app's own ringing UI take over when a ringing push arrives while the app is foregrounded, set `skipIncomingPushInForeground: true` on the per-platform `ios` / `android` keys of `setPushConfig`. On iOS 26.4+ this branch also requires the PushKit `didReceiveIncomingVoIPPushWith:metadata:withCompletionHandler:` delegate forwarding to `StreamVideoReactNative.didReceiveIncomingVoIPPush(...)` on RN CLI; Expo apps inject this automatically via the SDK config plugin. Full details on the same Ringing Setup pages above.
- **Non-ringing notifications** (`call.missed`, `call.notification`, `call.live_started` - the SDK's `NonRingingPushEvent` type) are NOT handled by `setPushConfig` - they are entirely app-owned. Register the device token via `client.addDevice(token, push_provider, push_provider_name)` and display/route the push yourself using any library. See manifest-selected `/incoming-calls/non-ringing-notifications-setup/overview/`.

---

## Custom Call Controls Blueprint

Replace the SDK's default controls bar with your own. Drive call state through `call.microphone`, `call.camera`, and `call.leave()`, reading toggle status via `useCallStateHooks()`.

```tsx
import { Pressable, StyleSheet, Text, View } from "react-native";
import {
  CallingState,
  useCall,
  useCallStateHooks,
} from "@stream-io/video-react-native-sdk";
import { useNavigation } from "@react-navigation/native";

export const CustomCallControls = () => {
  const call = useCall();
  const navigation = useNavigation<any>();
  const { useMicrophoneState, useCameraState } = useCallStateHooks();
  const { status: micStatus } = useMicrophoneState();
  const { status: camStatus } = useCameraState();

  const toggleMic = async () => {
    await call?.microphone.toggle();
  };
  const toggleCam = async () => {
    await call?.camera.toggle();
  };
  const flipCam = async () => {
    await call?.camera.flip();
  };
  const hangup = async () => {
    if (call && call.state.callingState !== CallingState.LEFT) {
      await call.leave().catch((err) => console.error(err));
    }
    navigation.goBack();
  };

  return (
    <View style={styles.row}>
      <Pressable onPress={toggleMic} style={styles.button}>
        <Text>{micStatus === "disabled" ? "Mic On" : "Mic Off"}</Text>
      </Pressable>
      <Pressable onPress={toggleCam} style={styles.button}>
        <Text>{camStatus === "disabled" ? "Cam On" : "Cam Off"}</Text>
      </Pressable>
      <Pressable onPress={flipCam} style={styles.button}>
        <Text>Flip</Text>
      </Pressable>
      <Pressable onPress={hangup} style={[styles.button, styles.hangup]}>
        <Text style={styles.hangupText}>Leave</Text>
      </Pressable>
    </View>
  );
};

const styles = StyleSheet.create({
  row: { flexDirection: "row", justifyContent: "space-evenly", paddingVertical: 10 },
  button: { alignItems: "center", borderRadius: 40, height: 64, justifyContent: "center", width: 64 },
  hangup: { backgroundColor: "#FF3742" },
  hangupText: { color: "white" },
});
```

Wire the custom bar via `<CallContent CallControls={CustomCallControls} />` - the prop accepts a `ComponentType` and the SDK renders it in the controls slot. The custom component must live inside `<StreamCall>` so `useCall()` and `useCallStateHooks()` resolve the active call.

If the screen also adds a **custom top bar above `CallContent`**, zero `theme.callContent.container.paddingTop` via a scoped `<StreamTheme>` so the SDK's top inset doesn't stack on top of the app bar. If the bottom controls host **absolute overlays, drawers, or subtitles**, include `theme.variants.insets.bottom` (via `useTheme()`) in the offset math, since `CallContent` already pads the bottom safe area. Both patterns and full code: live [Safe area insets cookbook page](https://getstream.io/video/docs/react-native/ui-cookbook/safe-area-insets.md).

**Wiring:**

- `call.microphone.toggle()` / `call.camera.toggle()` flip the published track; await them since they are async. Read the live state from `useMicrophoneState().status` and `useCameraState().status` (`"enabled" | "disabled"`) - the hooks re-render on change.
- `call.camera.flip()` swaps front/back; `useCameraState().direction` (`"front" | "back"`) is available if you need to label the button.
- **Speaking-while-muted hint.** `useMicrophoneState().isSpeakingWhileMuted` becomes `true` when the SDK detects voice activity but the mic track is off - surface a small "You're muted" tooltip so the user notices:
  ```tsx
  const { isSpeakingWhileMuted } = useMicrophoneState();
  // {isSpeakingWhileMuted ? <Text>You're muted</Text> : null}
  ```
- For hangup, call `call.leave()` and navigate. Guard with `callingState !== CallingState.LEFT` so the call-screen unmount effect does not double-leave. Do **not** use `call.endCall()` here unless you intend to terminate the call for every participant.

---

## Custom Participant Tile Blueprint

Wrap `ParticipantView` with a speaking border and a custom label that surfaces the dominant-speaker state.

```tsx
import { StyleSheet, Text, View } from "react-native";
import {
  ParticipantLabelProps,
  ParticipantView,
  StreamVideoParticipant,
  useCallStateHooks,
  VideoRendererProps,
  VideoRenderer,
} from "@stream-io/video-react-native-sdk";

const CustomParticipantLabel = ({ participant }: ParticipantLabelProps) => {
  const label = participant?.name || participant?.id;
  const isDominant = participant?.isDominantSpeaker;
  return (
    <View style={styles.labelWrap}>
      <Text style={styles.labelText}>
        {label}
        {isDominant ? " (speaking)" : ""}
      </Text>
    </View>
  );
};

const CustomVideoRenderer = (props: VideoRendererProps) => (
  <VideoRenderer {...props} objectFit="cover" />
);

export const ParticipantTile = ({
  participant,
}: {
  participant: StreamVideoParticipant;
}) => {
  const { useParticipants } = useCallStateHooks();
  const participants = useParticipants();
  const tracked = participants.find((p) => p.sessionId === participant.sessionId) ?? participant;
  const isSpeaking = tracked.isSpeaking;

  return (
    <View
      style={[
        styles.tile,
        { borderColor: isSpeaking ? "#00E676" : "transparent" },
      ]}
    >
      <ParticipantView
        participant={tracked}
        style={styles.view}
        ParticipantLabel={CustomParticipantLabel}
        VideoRenderer={CustomVideoRenderer}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  tile: { borderRadius: 12, borderWidth: 2, flex: 1, overflow: "hidden" },
  view: { flex: 1 },
  labelWrap: {
    backgroundColor: "rgba(0,0,0,0.5)",
    borderRadius: 4,
    bottom: 8,
    left: 8,
    paddingHorizontal: 6,
    paddingVertical: 2,
    position: "absolute",
  },
  labelText: { color: "white", fontSize: 12 },
});
```

**Wiring:**

- `ParticipantView` handles track attach/detach, mirroring for the local participant, and avatar fallback when the camera is off via its built-in `ParticipantVideoFallback`. Override the `ParticipantLabel`, `ParticipantReaction`, `ParticipantVideoFallback`, `ParticipantNetworkQualityIndicator`, or `VideoRenderer` slot props to customize sub-regions; leave the rest as default.
- Read live participant state (`isSpeaking`, `isDominantSpeaker`, `audioLevel`, `connectionQuality`) via `useCallStateHooks().useParticipants()` inside `<StreamCall>` - never call `client.call(...)` again to retrieve state.
- Plug the tile into `CallContent` via the `ParticipantView` prop, or render it directly from a custom `CallParticipantsList` layout. For a label-only swap (no border), pass `CustomParticipantLabel` straight to `CallContent`'s `ParticipantLabel` prop.

---

## Participant Grid Blueprint

Toggle the built-in grid/spotlight layouts via `CallContent`'s `layout` prop, and read participants through `useCallStateHooks().useParticipants()` when you need a fully custom grid.

```tsx
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import {
  CallContent,
  ParticipantView,
  StreamCall,
  useCallStateHooks,
  type Call,
} from "@stream-io/video-react-native-sdk";

type LayoutMode = "grid" | "spotlight";

export const ParticipantGridScreen = ({ call }: { call: Call }) => {
  const [layout, setLayout] = useState<LayoutMode>("grid");

  return (
    <StreamCall call={call}>
      <View style={styles.toolbar}>
        <Pressable onPress={() => setLayout("grid")}>
          <Text style={layout === "grid" ? styles.active : styles.inactive}>Grid</Text>
        </Pressable>
        <Pressable onPress={() => setLayout("spotlight")}>
          <Text style={layout === "spotlight" ? styles.active : styles.inactive}>Spotlight</Text>
        </Pressable>
      </View>
      <CallContent layout={layout} />
    </StreamCall>
  );
};

// Fully custom grid - render instead of <CallContent /> when defaults don't fit.
export const CustomParticipantGrid = () => {
  const { useParticipants } = useCallStateHooks();
  const participants = useParticipants();

  return (
    <View style={styles.grid}>
      {participants.map((participant) => (
        <View key={participant.sessionId} style={styles.cell}>
          <ParticipantView participant={participant} />
        </View>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  toolbar: { flexDirection: "row", gap: 16, padding: 12 },
  active: { fontWeight: "700" },
  inactive: { opacity: 0.5 },
  grid: { flex: 1, flexDirection: "row", flexWrap: "wrap" },
  cell: { width: "50%", aspectRatio: 1, padding: 4 },
});
```

**Wiring:**

- `CallContent` auto-switches to `spotlight` when a screen share starts - your stored `layout` state is overridden until the share ends, so do not fight it.
- `useParticipants()` already sorts by speaking/dominant-speaker/pinned; iterate it in order rather than re-sorting on every render.
- Use `sessionId` as the React `key` - `userId` can repeat across multi-device joins.
- For pinning, dominant-speaker focus, or a floating local tile, prefer overriding `CallContent`'s `CallParticipantsList` / `FloatingParticipantView` slot props over reimplementing the grid from scratch.

---

## Call Deep-link Blueprint

Push notifications and external deep links typically deliver `(callType, callId)`. Resolve the pair as soon as the app wakes, then navigate to the Active Call screen with just the id - the destination screen owns the single `client.call(...)` creation (see Active Call Screen). The deep-link handler must NOT pre-create a `Call` instance.

```tsx
import { useEffect } from "react";
import { Linking } from "react-native";
import { useNavigation } from "@react-navigation/native";

// matches https://your-app.example.com/join/<callType>/<callId>
// or myapp://call/<callType>/<callId>
const CALL_LINK_REGEX = /(?:\/join\/|:\/\/call\/)([^/]+)\/([^/?#]+)/;

const parseCallLink = (url: string | null) => {
  const m = url?.match(CALL_LINK_REGEX);
  if (!m) return null;
  return { callType: m[1], callId: m[2] };
};

export const useCallDeepLink = () => {
  const navigation = useNavigation<any>();

  useEffect(() => {
    const open = (url: string | null) => {
      const parsed = parseCallLink(url);
      if (!parsed) return;
      // Pass the id (and type if dynamic) through navigation only.
      // ActiveCallScreen creates the Call exactly once via
      // client.call(type, id, { reuseInstance: true }).
      navigation.navigate("ActiveCall", parsed);
    };

    // Cold start: app launched by tapping the link.
    Linking.getInitialURL().then(open);

    // Warm: app already running, link delivered as an event.
    const sub = Linking.addEventListener("url", ({ url }) => open(url));
    return () => sub.remove();
  }, [navigation]);
};
```

Mount `useCallDeepLink()` inside the `<StreamVideo>` subtree (below the auth gate) so the client is ready by the time navigation lands on `ActiveCall`. For Expo Router, swap `useNavigation()` for `router.push({ pathname: "/active-call", params: parsed })` from `expo-router`; the rest of the hook is identical.

**Push payload path:** ringing calls delivered via Firebase/APNs/CallKit are handled by `StreamVideoRN.setPushConfig(...)` plus the SDK's `@stream-io/react-native-callingx` bridge - the SDK surfaces the incoming call UI for you (see Ringing Blueprint). Non-ringing pushes (`call.missed`, `call.notification`, `call.live_started` - the SDK's `NonRingingPushEvent` type) are **app-owned**: register the device token via `client.addDevice(token, push_provider, push_provider_name)`, then have your push handler (any library) filter by `data.sender === "stream.video"`, split `data.call_cid` on `:`, and call your own navigation helper:

```ts
// inside your FCM / APN / expo-notifications tap handler:
if (data?.sender === "stream.video") {
  const [callType, callId] = String(data.call_cid).split(":");
  staticNavigate({ name: "ActiveCall", params: { callType, callId } });
}
```

Use a `createNavigationContainerRef` + interval gate (`staticNavigate`) because cold-start taps fire before `<NavigationContainer>` is ready - identical pattern to `Linking.getInitialURL()` but driven by the chosen push library. Native intent-filter / `apple-app-site-association` setup (AndroidManifest, AppDelegate `RCTLinkingManager`) is one-time per platform; see the [Deep Linking guide](https://getstream.io/video/docs/react-native/advanced/deeplinking.md). For the canonical non-ringing handling flow and the full payload schema, see manifest-selected `/incoming-calls/non-ringing-notifications-setup/overview/`, `/register-device/`, and `/handling-example/`.

---

## Livestream Blueprint

Livestreams use the `livestream` call type. The host publishes (WebRTC, or RTMP-in from OBS); viewers watch with low latency. Component names are verified in [VIDEO-REACT-NATIVE.md](VIDEO-REACT-NATIVE.md); deeper options live on the manifest-selected `/ui-components/livestream/*` and `/advanced/broadcasting/` pages.

### Host

`HostLivestream` is the full host UI. Create a `livestream` call, join with `create: true` and the host as a member, then render `HostLivestream` inside `<StreamCall>`. The SDK's built-in start/stop control drives `call.goLive()` / `call.stopLive()`.

```tsx
import { useEffect, useMemo } from "react";
import {
  Call,
  CallingState,
  HostLivestream,
  StreamCall,
  useConnectedUser,
  useStreamVideoClient,
} from "@stream-io/video-react-native-sdk";

export const HostLivestreamScreen = ({ callId }: { callId: string }) => {
  const client = useStreamVideoClient();
  const me = useConnectedUser();

  const call = useMemo<Call | undefined>(
    () => (client ? client.call("livestream", callId, { reuseInstance: true }) : undefined),
    [client, callId],
  );

  useEffect(() => {
    if (!call || !me) return;
    call
      .join({ create: true, data: { members: [{ user_id: me.id, role: "host" }] } })
      .catch((err) => console.error("Failed to start livestream", err));
    return () => {
      if (call.state.callingState !== CallingState.LEFT) {
        call.leave().catch((err) => console.error(err));
      }
    };
  }, [call, me]);

  if (!call) return null;
  return (
    <StreamCall call={call}>
      <HostLivestream />
    </StreamCall>
  );
};
```

For RTMP-in (broadcast from OBS), read the ingress address + stream key from `call.state.ingress?.rtmp` after join. See the manifest-selected `/advanced/broadcasting/` page.

### Viewer

The simplest viewer is `LivestreamPlayer`, which takes `callId` + `callType` props and manages its own call instance:

```tsx
import { useEffect } from "react";
import { callManager, LivestreamPlayer } from "@stream-io/video-react-native-sdk";

export const ViewerScreen = ({ callId }: { callId: string }) => {
  useEffect(() => {
    // A watch-only viewer is a "listener", not a "communicator".
    // This is the one place you start callManager yourself.
    callManager.start({ audioRole: "listener", enableStereoAudioOutput: true });
    return () => callManager.stop();
  }, []);

  return <LivestreamPlayer callId={callId} callType="livestream" />;
};
```

For the full viewer UI (live badge, duration, participant count, leave button), create the call yourself (`client.call("livestream", id, { reuseInstance: true })` + `join()`) and render `<ViewerLivestream />` inside `<StreamCall>` instead of `LivestreamPlayer`. Either way, a watch-only viewer uses `audioRole: "listener"`; for an ordinary call you never touch `callManager`.

---

## Audio Room Blueprint

Audio rooms use the `audio_room` call type. There is **no single `AudioRoom` component** - compose the UI from `useCallStateHooks()` plus the call's backstage and permission model. Verify the backstage/permission API on the manifest-selected `/guides/audio-rooms/` page before building - it drifts more than any other Video flow.

Verified building blocks (all confirmed in the SDK source):

- **Create / join:** `client.call("audio_room", id, { reuseInstance: true })`, then `call.join({ create: true, data: { members, custom: { title, description } } })`.
- **Go live:** hosts call `call.goLive()`; end with `call.stopLive()`. Listeners join the live room directly. Gate host-only UI on `OwnCapability.JOIN_BACKSTAGE` via `call.permissionsContext.hasPermission(...)`.
- **Request to speak:** a listener calls `call.requestPermissions({ permissions: [OwnCapability.SEND_AUDIO] })`. A host listens with `call.on("call.permission_request", (event) => { ... })` and grants via `call.updateUserPermissions({ user_id, grant_permissions: [OwnCapability.SEND_AUDIO] })`. Read your own granted capabilities with `useCallStateHooks().useHasPermissions(...)`.
- **State:** `useCallStateHooks().useParticipants()`, `useDominantSpeaker()`, and `useMicrophoneState()` for the speaking/mute UI.
- **Audio role:** an audience member can run `callManager.start({ audioRole: "listener" })`; a speaker/host stays the default `"communicator"`.
- **Cleanup:** `call.leave()` on unmount, guarded by `call.state.callingState !== CallingState.LEFT`.

```tsx
import { useEffect } from "react";
import {
  CallingState,
  OwnCapability,
  StreamCall,
  useCall,
  useCallStateHooks,
} from "@stream-io/video-react-native-sdk";

// Inside <StreamCall call={audioRoomCall}>:
export const AudioRoom = () => {
  const call = useCall();
  const { useCallCallingState, useParticipants } = useCallStateHooks();
  const callingState = useCallCallingState();
  const participants = useParticipants();

  useEffect(() => {
    return () => {
      if (call && call.state.callingState !== CallingState.LEFT) {
        call.leave().catch((err) => console.error(err));
      }
    };
  }, [call]);

  const requestToSpeak = () =>
    call?.requestPermissions({ permissions: [OwnCapability.SEND_AUDIO] });

  // host side: grant a pending request
  // call.on("call.permission_request", (e) =>
  //   call.updateUserPermissions({ user_id: e.user.id, grant_permissions: [OwnCapability.SEND_AUDIO] }));

  // ...render participant list, speaking indicators, and controls from `participants` + `callingState`
  return null;
};
```

---

## Chat + Video Blueprint

Use this when one app runs both `stream-chat-react-native` (or `stream-chat-expo`) and `@stream-io/video-react-native-sdk` - e.g. a "start a call" button inside a chat channel. Build both clients with the same API key (and they can share one user token if both products are enabled for the key). For combined-product gotchas, fetch the manifest-selected `https://getstream.io/video/docs/react-native/advanced/chat-with-video.md`.

**Provider nesting** (the full tree lives in [../sdk.md](../sdk.md) - nest, never sibling):

```tsx
<GestureHandlerRootView style={{ flex: 1 }}>
  <SafeAreaProvider>
    <StreamVideo client={videoClient} style={themeWithInsets}>
      <OverlayProvider>
        <Chat client={chatClient}>
          <NavigationContainer>{/* navigator */}</NavigationContainer>
        </Chat>
      </OverlayProvider>
    </StreamVideo>
  </SafeAreaProvider>
</GestureHandlerRootView>
```

**Start a ringing call from inside a channel.** The button reads the Video client and rings the channel's other members; the shell-level `RingingCalls` watcher (see Ringing Blueprint) surfaces the call UI - the channel screen does not mount `CallContent` itself.

```tsx
import { useCallback } from "react";
import { Button } from "react-native";
import { useChannelContext } from "stream-chat-react-native"; // or stream-chat-expo
import { useStreamVideoClient } from "@stream-io/video-react-native-sdk";

export const StartCallButton = ({ myId }: { myId: string }) => {
  const client = useStreamVideoClient();
  const { channel } = useChannelContext();

  const startCall = useCallback(async () => {
    if (!client) return;
    const memberIds = Object.keys(channel?.state.members ?? {});
    const callId = `call-${Date.now()}`; // fresh id per ring
    const call = client.call("default", callId, { reuseInstance: true });
    await call.getOrCreate({
      ring: true,
      video: true,
      data: { members: memberIds.map((user_id) => ({ user_id })) },
    });
  }, [client, channel]);

  return <Button onPress={startCall} title="Start call" />;
};
```

Disconnect **both** clients on sign-out before building new ones for a different user. Both providers stay mounted above the navigator for the whole session.

---

## Fresh App Scaffold

Use this when there is no existing app. Otherwise prefer the App Provider blueprint inside the existing root.

```bash
# RN CLI (translate the install commands to match the project's package manager)
npx @react-native-community/cli@latest init MyApp
cd MyApp
npm install @stream-io/video-react-native-sdk
npm install @stream-io/react-native-webrtc react-native-svg @react-native-community/netinfo
npm install react-native-safe-area-context react-native-edge-to-edge
npx pod-install
```

```bash
# Expo
npx create-expo-app@latest MyApp
cd MyApp
npx expo install @stream-io/video-react-native-sdk \
  @stream-io/react-native-webrtc \
  @config-plugins/react-native-webrtc \
  react-native-svg \
  @react-native-community/netinfo \
  react-native-safe-area-context \
  expo-build-properties
```

After install:

- RN CLI: declare iOS permissions in `Info.plist`, Android permissions in `AndroidManifest.xml`, bump Android `minSdkVersion` to 24, enable Java 8 source.
- Expo: add `@stream-io/video-react-native-sdk` and `@config-plugins/react-native-webrtc` to `app.json` plugins, then `npx expo prebuild --clean`.
- **Navigation (required - blueprints below assume it):** RN CLI has no navigation by default, install React Navigation: `npm install @react-navigation/native @react-navigation/native-stack @react-navigation/elements react-native-screens`. Expo apps from `create-expo-app` already have **Expo Router** under `app/` - use the Expo Router branch of the Navigation Shell blueprint instead. Skipping this step will cause `import` errors on the first build.
- Recommended: install `react-native-reanimated`, `react-native-worklets`, and `react-native-gesture-handler` (Stream's sample apps do, even video-only) for the animated floating-participant tile, and add `react-native-worklets/plugin` as the last Babel plugin. They are optional - the SDK falls back to the RN `Animated` API without them.

Then drop in the App Provider and Auth Gate blueprint above, hook up the Navigation Shell, and add Home + Active Call screens.
