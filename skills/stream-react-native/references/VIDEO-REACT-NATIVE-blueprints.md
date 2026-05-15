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
| livestream viewer | Livestream Player Blueprint |
| audio room, voice-only call | Audio Room Blueprint |
| React Navigation or Expo Router shell | Navigation Shell |
| theme, dark mode, colors | Theming Blueprint |
| UI slot, component, or behavior customization | DOCS.md -> primary manifest lookup, then Component Override Blueprint |
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
  StreamVideo,
  StreamVideoClient,
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
  return <StreamVideo client={client}>{children}</StreamVideo>;
};

export default function App() {
  const [session, setSession] = useState<Session | null>(null);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      {session ? (
        <ConnectedVideo session={session}>
          {/* navigation lives here */}
        </ConnectedVideo>
      ) : (
        <LoginScreen onSession={setSession} />
      )}
    </GestureHandlerRootView>
  );
}
```

Always use `StreamVideoClient.getOrCreateInstance(...)` (not `new StreamVideoClient(...)`); the SDK relies on the singleton for push notifications and call state. Pair with a `tokenProvider` (~4-hour tokens) in production so the SDK refreshes automatically. See [VIDEO-REACT-NATIVE.md > Client setup](VIDEO-REACT-NATIVE.md#client-setup) and the live [Integration Best Practices](https://getstream.io/video/docs/react-native/advanced/integration-best-practices.md) page.

---

## Home / Join-or-Start Call

Use this for a lobby screen where the user enters a call id, runs device checks, and joins (or creates) the call. Reads the client from `StreamVideo` and hands `cid` to the next screen via navigation params.

```tsx
import { useCallback, useState } from "react";
import { Button, TextInput, View } from "react-native";
import { useStreamVideoClient } from "@stream-io/video-react-native-sdk";
import { useNavigation } from "@react-navigation/native";

export const HomeScreen = () => {
  const client = useStreamVideoClient();
  const navigation = useNavigation<any>();
  const [callId, setCallId] = useState("");
  const [joining, setJoining] = useState(false);

  const onJoin = useCallback(async () => {
    if (!client || !callId) return;
    setJoining(true);
    try {
      const call = client.call("default", callId);
      await call.getOrCreate();
      navigation.navigate("ActiveCall", { cid: call.cid });
    } catch (err) {
      console.error("Failed to create call", err);
    } finally {
      setJoining(false);
    }
  }, [client, callId, navigation]);

  return (
    <View style={{ flex: 1, justifyContent: "center", padding: 24 }}>
      <TextInput
        autoCapitalize="none"
        onChangeText={setCallId}
        placeholder="Call id"
        value={callId}
      />
      <Button disabled={!callId || joining} onPress={onJoin} title="Join call" />
    </View>
  );
};
```

Pass `call.cid` (the string `"<type>:<id>"`), not the `Call` instance, through navigation params. Defer `call.join()` to the destination screen so its lifecycle (`useEffect` cleanup -> `call.leave()`) owns the live connection. For pre-join device checks, see the **Lobby Preview** pattern in the manifest-selected `/ui-cookbook/lobby-preview/` page.

---

## Active Call Screen

The default in-call experience. Creates a `Call`, joins it inside `useEffect`, mounts `StreamCall`, and renders `CallContent`. Always `call.leave()` on unmount.

```tsx
import { useEffect, useState } from "react";
import {
  useStreamVideoClient,
  StreamCall,
  CallContent,
  Call,
  callManager,
} from "@stream-io/video-react-native-sdk";
import { useNavigation, useRoute } from "@react-navigation/native";

export const ActiveCallScreen = () => {
  const client = useStreamVideoClient();
  const navigation = useNavigation<any>();
  const { cid } = useRoute().params as { cid: string };
  const [type, id] = cid.split(":");
  const [call, setCall] = useState<Call>();

  useEffect(() => {
    if (!client) return;
    const c = client.call(type, id);
    setCall(c);
    callManager.start({ audioRole: "communicator", deviceEndpointType: "speaker" });
    c.join({ create: true }).catch((err) => console.error("Failed to join", err));
    return () => {
      callManager.stop();
      c.leave().catch((err) => console.error(err));
      setCall(undefined);
    };
  }, [client, type, id]);

  if (!call) return null;

  return (
    <StreamCall call={call}>
      <CallContent onHangupCallHandler={() => navigation.goBack()} />
    </StreamCall>
  );
};
```

`CallContent` provides the full default UI - top bar, participant grid, and call controls. Replace any slot via its props; see Custom Call Controls and Custom Participant Tile blueprints below. `callManager.start/stop` keeps the speaker/earpiece/Bluetooth routing aligned with the call lifecycle.

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

TODO: Fill from manifest-selected `/incoming-calls/overview.md` and `/incoming-calls/ringing-setup/react-native.md`.

Sections to cover:

- Surfacing an incoming call from the app shell (`client.on("call.ring", ...)`)
- Starting an outgoing ringing call (`call.getOrCreate({ ring: true, data: { members } })`)
- Accepting / rejecting an incoming call manually (`call.accept()`, `call.reject()`)
- Using built-in `IncomingCall` and `OutgoingCall` screen components
- Wiring `StreamVideoRN.setPushConfig(...)` for CallKit (iOS) + Android Telecom integration via `@stream-io/react-native-callingx`

---

## Custom Call Controls Blueprint

TODO: Fill from manifest-selected `/ui-cookbook/replacing-call-controls.md`.

Sections to cover:

- Replacing the `CallControls` slot on `CallContent` with a custom component
- Reading toggle state from `useCallStateHooks().useMicrophoneState()` / `useCameraState()`
- Wiring a custom hangup button via `call.leave()` or `call.endCall()`

---

## Custom Participant Tile Blueprint

TODO: Fill from manifest-selected `/ui-components/participants/participant-view.md` and `/ui-cookbook/participant-label.md`.

Sections to cover:

- Wrapping `ParticipantView` with custom badges / labels
- Reading speaking state, connection quality, audio level
- Overriding the video / audio renderer

---

## Participant Grid Blueprint

TODO: Fill from manifest-selected `/ui-cookbook/runtime-layout-switching.md`.

Sections to cover:

- Switching between grid and spotlight layouts
- Custom grid component receiving `useParticipants()` output
- Pinning participants

---

## Call Deep-link Blueprint

TODO: Fill from manifest-selected `/incoming-calls/overview.md` plus the platform's deep-link docs.

Sections to cover:

- Handling a notification payload at cold start
- Resolving `(type, id)` from a push payload and navigating to `ActiveCall`
- Restoring an in-progress call after the app returns from background

---

## Livestream Player Blueprint

TODO: Fill from manifest-selected `/ui-components/livestream/livestream-player.md` and `/streaming/mobile-livestreaming.md`.

Sections to cover:

- Viewer-only setup using `LivestreamPlayer`
- Connecting to an existing livestream call via `client.call("livestream", id)`
- Handling start, pause, viewer count

---

## Audio Room Blueprint

TODO: Fill from manifest-selected `audio_room` call-type pages.

Sections to cover:

- Creating an `audio_room` call type
- Speaker vs listener roles
- Built-in audio-only UI components

---

## Theming Blueprint

TODO: Fill from manifest-selected theming pages.

Sections to cover:

- `StreamVideoRN.setTheme(...)` global theme overrides
- Per-component style props
- Dark mode toggle via React Native `Appearance`

---

## Fresh App Scaffold

Use this when there is no existing app. Otherwise prefer the App Provider blueprint inside the existing root.

```bash
# RN CLI
npx @react-native-community/cli@latest init MyApp
cd MyApp
yarn add @stream-io/video-react-native-sdk
yarn add @stream-io/react-native-webrtc react-native-svg @react-native-community/netinfo
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
  expo-build-properties
```

After install:

- RN CLI: declare iOS permissions in `Info.plist`, Android permissions in `AndroidManifest.xml`, bump Android `minSdkVersion` to 24, enable Java 8 source.
- Expo: add `@stream-io/video-react-native-sdk` and `@config-plugins/react-native-webrtc` to `app.json` plugins, then `npx expo prebuild --clean`.

Then drop in the App Provider and Auth Gate blueprint above, hook up the Navigation Shell, and add Home + Active Call screens.

---

## Component Override Blueprint

TODO: Generic pattern for any `CallContent` slot or component override. Fill once the specific override is identified via manifest lookup.

Sections to cover:

- Pass a component reference via the matching slot prop on `CallContent`
- Read context via `useCall`, `useStreamVideoClient`, `useCallStateHooks()`
- Keep the override outside the `CallContent` subtree if it needs to live in the navigator shell
