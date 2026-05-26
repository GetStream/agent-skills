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
| livestream viewer, audio room, theming, generic UI slot override | DOCS.md -> manifest lookup, then VIDEO-REACT-NATIVE.md > Customization |
| chat + video in the same app | DOCS.md -> manifest -> Chat Integration; then App Provider + Chat Provider |

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

  const signIn = useCallback(async () => {
    if (apiKey && token && userId) {
      onSession({ apiKey, token, userId, userName: userName || userId });
      return;
    }
    const res = await fetch(
      `https://your-api.example.com/stream-token?user_id=${encodeURIComponent(userId)}`,
    );
    const body = await res.json();
    onSession({
      apiKey: body.apiKey,
      token: body.token,
      userId,
      userName: body.userName || userName || userId,
    });
  }, [apiKey, onSession, token, userId, userName]);

  return (
    <View style={{ flex: 1, justifyContent: "center", padding: 24 }}>
      <TextInput autoCapitalize="none" onChangeText={setApiKey} placeholder="API key" value={apiKey} />
      <TextInput autoCapitalize="none" onChangeText={setToken} placeholder="User token" value={token} />
      <TextInput autoCapitalize="none" onChangeText={setUserId} placeholder="User id" value={userId} />
      <TextInput autoCapitalize="words" onChangeText={setUserName} placeholder="User name" value={userName} />
      <Button disabled={!userId} onPress={signIn} title="Sign in" />
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
    c.join({ create: true }).catch((err) => console.error("Failed to join", err));
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

`CallContent` provides the full default UI - top bar, participant grid, and call controls. Inside `<StreamCall>`, any child component (custom controls, participant tile, ringing UI, in-call toolbar) reads the current call via `useCall()` - never `client.call(...)` again. Replace any slot via its props; see Custom Call Controls and Custom Participant Tile blueprints below. Audio routing (speaker/earpiece/Bluetooth) is handled automatically by `call.join()` / `call.leave()` with `audioRole: "communicator"` as the default - do not call `callManager.start/stop` yourself unless you are overriding the role (e.g., `broadcaster` in an audio room).

Notice the screen does **not** wrap `<CallContent />` in a `SafeAreaView`. `CallContent`, `RingingCallContent`, `HostLivestream`, and `ViewerLivestream` all read insets from `<StreamVideo>`'s theme (`variants.insets`) - wire them once at the App Provider blueprint and the call screen renders edge-to-edge with the correct padding on both iOS and Android. See [VIDEO-REACT-NATIVE.md > Safe areas and edge-to-edge](VIDEO-REACT-NATIVE.md#safe-areas-and-edge-to-edge).

The destructured `callType` defaults to `"default"` for the simple join-by-id case but accepts whatever the deep-link / ringing watcher / push handler delivers (`livestream`, `audio_room`, custom call types). Always pass `{ reuseInstance: true }` so a Call already created upstream (an outgoing ring, a ringing watcher) is returned as-is rather than duplicated.

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

`RingingCallContent` reads `call.state.callingState` and routes between the default `IncomingCall`, `OutgoingCall`, `JoiningCallIndicator`, and accepted `CallContent` slots. Pair it with the client-level `useCalls()` hook to surface incoming or outgoing ringing calls from anywhere in the app. Deeper detail lives on the live [Ringing](https://getstream.io/video/docs/react-native/incoming-calls/ringing.md) and [RingingCallContent](https://getstream.io/video/docs/react-native/ui-components/call/ringing-call-content.md) pages.

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
- Replace the default ringing UIs by passing `IncomingCall`, `OutgoingCall`, `JoiningCallIndicator`, or `CallContent` component refs to `<RingingCallContent ... />`. Match the prop signatures on the live [RingingCallContent](https://getstream.io/video/docs/react-native/ui-components/call/ringing-call-content.md) page; the [Incoming & Outgoing Call cookbook](https://getstream.io/video/docs/react-native/ui-cookbook/incoming-and-outgoing-call.md) shows full custom replacements built from `useCallMembers` and the accept/reject buttons above.
- For background and terminated ringing (CallKit on iOS, Telecom + FCM on Android), call `StreamVideoRN.setPushConfig({...})` once at module load - including a `createStreamVideoClient` callback that builds the client with `StreamVideoClient.getOrCreateInstance(...)`. Full wiring (Info.plist keys, AppDelegate PushKit hooks, Firebase listeners, `@stream-io/react-native-callingx`) is documented at [Ringing Setup - React Native](https://getstream.io/video/docs/react-native/incoming-calls/ringing-setup/react-native.md).
- To let the app's own ringing UI take over when a ringing push arrives while the app is foregrounded, set `skipIncomingPushInForeground: true` on the per-platform `ios` / `android` keys of `setPushConfig`. On iOS 26.4+ this branch also requires the PushKit `didReceiveIncomingVoIPPushWith:metadata:withCompletionHandler:` delegate forwarding to `StreamVideoReactNative.didReceiveIncomingVoIPPush(...)` on RN CLI; Expo apps inject this automatically via the SDK config plugin. Full details on the same Ringing Setup pages above.
- **Non-ringing notifications** (`call.missed`, `call.notification`, `call.live_started`, `call.session_started`) are NOT handled by `setPushConfig` - they are entirely app-owned. Register the device token via `client.addDevice(token, push_provider, push_provider_name)` and display/route the push yourself using any library. See manifest-selected `/incoming-calls/non-ringing-notifications-setup/overview/`.

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

// matches stream-calls-dogfood.example.com/join/<callType>/<callId>
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
      // ActiveCallScreen creates the Call exactly once via client.call(type, id).
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

**Push payload path:** ringing calls delivered via Firebase/APNs/CallKit are handled by `StreamVideoRN.setPushConfig(...)` plus the SDK's `@stream-io/react-native-callingx` bridge - the SDK surfaces the incoming call UI for you (see Ringing Blueprint). Non-ringing pushes (`call.missed`, `call.notification`, `call.live_started`, `call.session_started`) are **app-owned**: register the device token via `client.addDevice(token, push_provider, push_provider_name)`, then have your push handler (any library) filter by `data.sender === "stream.video"`, split `data.call_cid` on `:`, and call your own navigation helper:

```ts
// inside your FCM / APN / expo-notifications tap handler:
if (data?.sender === "stream.video") {
  const [callType, callId] = String(data.call_cid).split(":");
  staticNavigate({ name: "ActiveCall", params: { callType, callId } });
}
```

Use a `createNavigationContainerRef` + interval gate (`staticNavigate`) because cold-start taps fire before `<NavigationContainer>` is ready - identical pattern to `Linking.getInitialURL()` but driven by the chosen push library. Native intent-filter / `apple-app-site-association` setup (AndroidManifest, AppDelegate `RCTLinkingManager`) is one-time per platform; see the [Deep Linking guide](https://getstream.io/video/docs/react-native/advanced/deeplinking.md). For the canonical non-ringing handling flow and the full payload schema, see manifest-selected `/incoming-calls/non-ringing-notifications-setup/overview/`, `/register-device/`, and `/handling-example/`.

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

Then drop in the App Provider and Auth Gate blueprint above, hook up the Navigation Shell, and add Home + Active Call screens.
