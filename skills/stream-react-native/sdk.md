# Stream React Native - shared SDK patterns

This file holds the shared React Native and Expo patterns that cut across Stream Chat, Stream Video, and Stream Feeds. Load it before product-specific references when you need client lifecycle, auth, provider, navigation, or lifecycle/cleanup guidance.

> **Client model.** Chat uses a process-wide singleton (`StreamChat.getInstance(apiKey)`) and swaps user identity via `connectUser` / `disconnectUser`. Video uses `StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider, options? })` - **never `new StreamVideoClient(...)`** - which caches a single instance per process and breaks push/state if you create more than one. Feeds uses the `useCreateFeedsClient({ apiKey, tokenOrProvider, userData })` hook, which creates a `FeedsClient`, connects the user, returns `undefined` while connecting, and disconnects on cleanup - mount the resulting client inside `<StreamFeeds client={client}>`. All three products tear down the current user with `disconnectUser()` before building a new client for a different user.

For the canonical Video best-practices source, see [`/video/docs/react-native/advanced/integration-best-practices/`](https://getstream.io/video/docs/react-native/advanced/integration-best-practices.md).

---

## Runtime package lane

| Product | RN CLI | Expo | Import from |
|---|---|---|---|
| Chat | `stream-chat-react-native` | `stream-chat-expo` | matching package |
| Video | `@stream-io/video-react-native-sdk` | `@stream-io/video-react-native-sdk` (same package) | `"@stream-io/video-react-native-sdk"` |
| Feeds | `@stream-io/feeds-react-native-sdk` | `@stream-io/feeds-react-native-sdk` (same package) | `"@stream-io/feeds-react-native-sdk"` |

Most Chat component names are the same across CLI and Expo - swap the import package to match the project. Video and Feeds use the same package across CLI and Expo and differ only by install commands (Expo uses `npx expo install`).

Never mix `stream-chat-react-native` and `stream-chat-expo` in the same app unless the existing project already does so intentionally.

---

## App shapes

Match the project that already exists:

- **Expo Router app:** ownership starts in `app/_layout.tsx`
- **RN CLI with React Navigation:** ownership starts in `App.tsx` (or the component registered from `index.js`)
- **Mixed / non-standard navigation:** keep Stream setup at the shared boundary (`App` root) instead of duplicating it per screen

Do not rewrite the app into a different navigator unless the user asks.

---

## Client ownership

Create each Stream client once, store it in app-scoped state, and pass or hook it from there.

Good ownership points:

- the top-level `App` component (or `app/_layout.tsx`)
- a context provider that wraps the navigator
- a module-level singleton initialised in the auth flow

Bad ownership points:

- inside a screen body
- inside a `useEffect` with empty deps inside a leaf component that remounts on navigation
- per channel screen (Chat) or per call screen (Video)
- inside render-time factories or unstable callbacks

### Chat client lifecycle

`useCreateChatClient` is the supported path. It creates a client, connects the user, returns `null` while connecting, and disconnects on cleanup. Never pass `null` to `<Chat client={...}>`.

```tsx
import { Chat, OverlayProvider, useCreateChatClient } from "stream-chat-react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";

const chatClient = useCreateChatClient({
  apiKey,
  tokenOrProvider,
  userData: { id: userId, name: userName },
});

if (!chatClient) return null;

return (
  <GestureHandlerRootView style={{ flex: 1 }}>
    <OverlayProvider>
      <Chat client={chatClient}>{children}</Chat>
    </OverlayProvider>
  </GestureHandlerRootView>
);
```

For Expo, change imports from `stream-chat-react-native` to `stream-chat-expo`.

### Video client lifecycle

```tsx
import { useEffect, useState } from "react";
import {
  StreamVideo,
  StreamVideoClient,
  User,
} from "@stream-io/video-react-native-sdk";

const [client, setClient] = useState<StreamVideoClient>();

useEffect(() => {
  const user: User = { id: userId, name: userName };
  const tokenProvider = async () => api.fetchToken(userId);
  const c = StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider });
  setClient(c);
  return () => {
    c.disconnectUser().catch((err) => console.error(err));
    setClient(undefined);
  };
}, [apiKey, userId]);

if (!client) return null;
return <StreamVideo client={client}>{children}</StreamVideo>;
```

For ringing/push, pass the **same** `options` to `getOrCreateInstance` and `StreamVideoRN.setPushConfig`; the helper reuses cached instances and option mismatches break ringing.

### Feeds client lifecycle

`useCreateFeedsClient` is the supported path. It creates a `FeedsClient`, connects the user, returns `undefined` while connecting, and disconnects on cleanup. Never pass `undefined` to `<StreamFeeds client={...}>`.

```tsx
import {
  StreamFeeds,
  useCreateFeedsClient,
} from "@stream-io/feeds-react-native-sdk";

const feedsClient = useCreateFeedsClient({
  apiKey,
  tokenOrProvider,
  userData: { id: userId, name: userName, image: userImage },
});

if (!feedsClient) return null;

return <StreamFeeds client={feedsClient}>{children}</StreamFeeds>;
```

The same `@stream-io/feeds-react-native-sdk` package is used on both RN CLI and Expo.

For sharing the user's `user` and `timeline` feeds across screens, wrap the navigator in an `OwnFeedsContextProvider` that creates both feeds with `client.feed("user", userId)` / `client.feed("timeline", userId)`, loads them with `getOrCreate({ watch: true })`, and establishes the self-follow (`timeline.follow(userFeed.feed)`) on first run. See [`references/FEEDS-REACT-NATIVE-blueprints.md`](references/FEEDS-REACT-NATIVE-blueprints.md) > Own Feeds Context.

### Call lifetime (Video)

Create `Call` only after the client is ready, inside a `useEffect`, and `call.leave()` on cleanup **guarded by `callingState !== CallingState.LEFT`** - leaving twice throws `Cannot leave call that has already been left`. Dangling calls keep publishing audio/video and leak memory.

```tsx
import { useEffect, useState } from "react";
import { useStreamVideoClient, Call, CallingState } from "@stream-io/video-react-native-sdk";

const client = useStreamVideoClient();
const [call, setCall] = useState<Call>();

useEffect(() => {
  if (!client) return;
  // `{ reuseInstance: true }` returns the cached Call when the same (type, id)
  // is already live in the SDK (outgoing ring, ringing watcher, deep link, push).
  // Required on every destination call screen; without it the SDK constructs a
  // duplicate that leaks SFU connections and breaks state.
  const c = client.call(type, id, { reuseInstance: true });
  setCall(c);
  // `{ create: true }` lets a "join by id" lobby flow work even when the
  // (type, id) doesn't exist server-side yet. Drop it for flows that only
  // join calls created upstream (ringing, livestream host, audio room).
  c.join({ create: true }).catch((err) => console.error("Failed to join", err));
  return () => {
    if (c.state.callingState !== CallingState.LEFT) {
      c.leave().catch((err) => console.error(err));
    }
    setCall(undefined);
  };
}, [client, type, id]);
```

A `Call` initializes after any of `call.get()`, `call.create()`, `call.getOrCreate()`, or `call.join()`. Audio routing (speaker/earpiece/Bluetooth) is handled by the SDK automatically on `join()` / `leave()` with `audioRole: "communicator"` - do not call `callManager.start/stop` yourself unless you are overriding the default role. The only other role is `"listener"` (playback-optimized output for a view-only experience such as a livestream viewer or audio-room audience member); a host/publisher keeps `"communicator"`.

---

## Auth model

Use the simplest token shape that matches the user's environment:

- **Backend exists (production path):** the backend authenticates the request, derives the Stream `user_id` **from its own session** (cookie / JWT / OAuth subject), and mints a Stream token for that id. The client wires a `tokenProvider` callback that re-hits the same authenticated endpoint when the token nears expiry. The SDK calls it again automatically on reconnect. The client must **never** send a `user_id` query/body parameter to the token endpoint - that lets any signed-in user impersonate any other Stream user. See [`references/VIDEO-REACT-NATIVE-blueprints.md` > Production auth gate](references/VIDEO-REACT-NATIVE-blueprints.md#production-auth-gate-replace-the-demo-loginscreen-for-real-apps) for the canonical wiring.
- **No backend / demo flow:** generate a token with the Stream CLI (`stream token <user_id>`; expiring: `stream token <user_id> --ttl 1h`) and paste it into a dev-only login form. See [`credentials.md`](credentials.md). Gate any such form behind `__DEV__` or a feature flag so it never ships in a production build.
- **User pastes their own:** accept it and pass to the client. Same dev-only caveat applies.

Keep the split clear:

- **client:** API key, `User` (`id`, `name`, `image`), user token. The client never decides which Stream user the token represents.
- **server:** API secret and token minting (the CLI handles this automatically). The server is the only place that names a Stream `user_id` when minting.

If the app already has its own auth system, extend that flow instead of adding a second login model beside it. Connect / build once per user session, not on every screen entry.

Never use `devToken()` (Chat) for production. Never invent credentials. Never accept a client-supplied `user_id` on the token endpoint.

---

## Provider tree and navigation

**Chat:** `GestureHandlerRootView` -> `SafeAreaProvider` -> `OverlayProvider` -> `NavigationContainer` (or Expo Router root) -> `<Chat>` -> screens. `SafeAreaProvider` from `react-native-safe-area-context` is required for both platforms (iOS notches, Android edge-to-edge). Keep `OverlayProvider` above navigation so attachment picker / image gallery / overlays render above the active screen. Keep `<Chat>` high enough that screen transitions do not reconnect the socket.

**Video:** `GestureHandlerRootView` (recommended) -> `SafeAreaProvider` -> `<StreamVideo client={client} style={themeWithInsets}>` -> `NavigationContainer` (or Expo Router root) -> screens. Bridge insets from `useSafeAreaInsets()` into `StreamVideo`'s `style` prop as `theme.variants.insets = { top, right, bottom, left }` so `CallContent`, `RingingCallContent`, and all participant views respect notches and system bars - the SDK does not infer insets on its own. Mount `<StreamVideo>` once near the app root; tearing it down restarts the WebSocket.

**Feeds:** `SafeAreaProvider` -> `<StreamFeeds client={feedsClient}>` -> (optional `OwnFeedsContextProvider`) -> `NavigationContainer` (or Expo Router root) -> screens. Mount `<StreamFeeds>` once near the app root, above any screen that uses Feeds hooks. Wrap individual feed-scoped subtrees with `<StreamFeed feed={feed}>` so descendant hooks (`useFeedActivities`, `useOwnFollows`, ...) can resolve the feed from context. Pass `activityId` (string) through navigation params, not `ActivityResponse`; on activity-details screens, create a live handle with `client.activityWithStateUpdates(id)` and call `.dispose()` on unmount.

**Combined (any of Chat, Video, Feeds):** nest the providers. Order does not matter, but **nest** them - do not place as siblings.

```tsx
<GestureHandlerRootView style={{ flex: 1 }}>
  <StreamFeeds client={feedsClient}>
    <StreamVideo client={videoClient}>
      <OverlayProvider>
        <Chat client={chatClient}>
          <NavigationContainer>{/* navigator */}</NavigationContainer>
        </Chat>
      </OverlayProvider>
    </StreamVideo>
  </StreamFeeds>
</GestureHandlerRootView>
```

Pass references through navigation params, not live objects:

- Chat: pass `channel.cid` (string), not the `Channel` instance. Recreate from `useChatContext().client.channel(type, id)` on the destination screen.
- Video: pass only the call id through navigation, not the `Call` instance. The destination call screen is the **sole** Call owner - it calls `client.call(type, id, { reuseInstance: true })` once, joins (with `{ create: true }` only for create-on-join lobby flows), and mounts `<StreamCall>`. Descendants read via `useCall()` and must **not** call `client.call(...)` again to obtain the same instance. Upstream screens (lobby, home) hand off the id without pre-creating the Call.
- Feeds: pass `activityId` (string), not the `ActivityResponse`. For shared `Feed` instances (own user / timeline), use the `OwnFeedsContext` pattern rather than navigation params - feeds are not serializable through router state. On activity-details screens, create `client.activityWithStateUpdates(activityId)` and call `.dispose()` on unmount so the SDK does not keep refetching after the screen closes.

---

## State and React patterns

Stateful SDK helpers should have explicit ownership:

- **Chat:** use the SDK's pre-built screens (`ChannelList`, `Channel`, `MessageList`, `MessageComposer`, `Thread`) and read context via `useChatContext`, `useMessageContext`, etc. Do not instantiate `StreamChat` inside Composables/screens.
- **Video:** read call state via `useCallStateHooks()` sub-hooks (`useCallCallingState`, `useParticipants`, `useCallMembers`, `useCameraState`, `useMicrophoneState`). For incoming/outgoing ringing calls, read the ringing list from the client-level `useCalls()` hook (filter by `call.ringing`) - there is no `useCallRingingState` hook. Do not instantiate `StreamVideoClient` or `Call` inside leaf components - hoist them into `App` or a screen-owned `useEffect`.
- **Feeds:** the SDK is headless - build all UI yourself. Prefer the dedicated state hooks (`useFeedActivities`, `useActivityComments`, `useFollowers`, `useFollowing`, `useOwnFollows`, `useOwnFollowings`, `useAggregatedActivities`, `useNotificationStatus`, `useOwnCapabilities`, `useMembers`) over reading `feed.currentState` directly. For arbitrary state slices, drop down to `useStateStore(feed.state, selector)` and keep the selector stable (module scope or `useCallback` / `useMemo`). Do not instantiate `FeedsClient` inside leaf components - hoist into the `<StreamFeeds>` host via `useCreateFeedsClient`.

Avoid creating filters/sort values (Chat), `Call` instances (Video), or `Feed` instances (Feeds) inline on every render. Memoise with `useMemo` keyed on inputs that actually change.

---

## Lifecycle and cleanup

- **Chat:** unmount or change `useCreateChatClient` inputs on sign-out. If offline support is enabled, run `chatClient.offlineDb?.resetDB()` **before** `disconnectUser()` to avoid cross-user data leaks.
- **Video:** call `client.disconnectUser()` and clear the state holding the client on sign-out. For active calls, run `call.leave()` on unmount **guarded by `callingState !== CallingState.LEFT`** to avoid `Cannot leave call that has already been left` when a hangup handler or React 18 strict-mode already left.
- **Feeds:** unmount or change `useCreateFeedsClient` inputs on sign-out, or call `feedsClient.disconnectUser()` directly. For any `client.activityWithStateUpdates(id)` handles still in scope, call `activity.dispose()` first so the SDK does not keep refetching after disconnect.
- **AppState / background:** the SDK auto-reconnects on network changes. For Video, tune the reconnection window with `call.setDisconnectionTimeout(seconds)` rather than ending calls on temporary disconnects. Android requires a foreground service for background calls. For Feeds, the SDK refetches any feed that was loaded with `watch: true` and any active `activityWithStateUpdates` handle when the WebSocket reconnects.

---

## Error handling

Wrap promise-returning SDK calls in try/catch and surface meaningful errors:

```ts
try {
  await call.join({ maxJoinRetries: 1 });
} catch (err) {
  console.error("Join failed", err);
}

try {
  await call.camera.enable();
  await call.microphone.enable();
} catch (err) {
  console.error("Failed to enable a device", err);
}
```

`call.join()` retries with exponential backoff by default; cap with `maxJoinRetries` when fast-fail UI is preferred. For Chat connect failures, surface them through your auth flow before mounting Chat.

---

## Combined apps (Chat + Video + Feeds)

A single RN app can run any combination of Chat, Video, and Feeds. Build all clients with the same API key; products can share the same user token if all of them are enabled for the API key. Nest providers (do not silo); see the provider tree example above.

For interop-specific guidance (call from inside a chat channel, attach a thread to a call, ringing UX in a chat-first app), fetch the manifest-selected `https://getstream.io/video/docs/react-native/advanced/chat-with-video.md`. Feeds has no built-in cross-product integration page; the standard pattern is to render Feeds activities (e.g. an activity row that links to a chat channel) and link out from your own UI.

---

## Verification checklist

Before calling the work done, confirm:

- imports match the runtime package lane (Chat) / Expo config plugins are wired (Video)
- mandatory peer dependencies are installed for the selected lane
- optional dependencies are installed only for requested capabilities
- app entry is wrapped in `GestureHandlerRootView` (Chat required; Video recommended)
- Chat: `OverlayProvider` and `<Chat>` are stable and high in the tree; navigation passes channel CID, not channel object; `Channel` owns `MessageList` and `MessageComposer`; thread state is shared between channel and thread screens; offline sign-out resets DB before disconnect when offline is enabled
- Video: client created via `StreamVideoClient.getOrCreateInstance(...)` and disposed on cleanup; `<StreamVideo>` mounted once near the app root above the navigator; **`Call` created exactly once** with `client.call(type, id, { reuseInstance: true })` in the destination call screen, joined inside `useEffect` (use `join({ create: true })` only for create-on-join lobby flows; ringing / livestream-host / audio-room flows join without `create`), mounted via `<StreamCall>`, and descendants read via `useCall()` (never `client.call(...)` again); `call.leave()` on cleanup **guarded by `callingState !== CallingState.LEFT`**; hangup handlers only navigate (no manual `leave()` - `CallContent` already calls it); audio routing left to the SDK (no manual `callManager.start/stop` unless overriding the role); navigation passes only the call id (not `Call` instances); permissions declared (iOS `Info.plist`, Android `AndroidManifest.xml`, Expo `app.json` plugins)
- Feeds: `useCreateFeedsClient` returns a client (or `undefined` while connecting - never pass `undefined` to `<StreamFeeds>`); `<StreamFeeds>` mounted once near the app root above the navigator; shared `user` + `timeline` feeds created through an `OwnFeedsContextProvider` (not per screen); self-follow established once after both feeds load (`timeline.follow(userFeed.feed)` if not already in `userFeed.currentState.own_follows`); activities read through `useFeedActivities` and similar state hooks (not `feed.currentState`); navigation passes `activityId` strings (not `ActivityResponse` objects); activity-details pages create `client.activityWithStateUpdates(id)` and call `.dispose()` on unmount; attachments (if used) upload via `client.uploadImage` / `client.uploadFile` with the URL read from `response.file` (`image_url` for images, `asset_url` for files), never through `Feed`; push (if wired) registers devices with `client.createDevice({ id, push_provider, push_provider_name })` (**not** the Video `addDevice`) and removes them with `client.deleteDevice({ id })`; `client.disconnectUser()` on sign-out
- when combined (Chat + Video, Feeds + Chat, Feeds + Video, or all three): all providers nested (not siblings); all clients disconnect on sign-out
