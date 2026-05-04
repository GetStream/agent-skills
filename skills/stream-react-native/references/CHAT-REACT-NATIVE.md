# Chat React Native v9 - Setup & Integration

Stream Chat React Native v9 provides pre-built Chat UI for React Native CLI and Expo apps. This file covers packages, app setup, client/auth patterns, navigation, offline support, and gotchas. For screen structures, see [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (Chat-only v9, New Architecture, secrets, runtime lane ownership, provider placement, blueprint reads).

Local source authority:

- Docs: `~/Projects/docs/data/docs/chat-sdk/react-native/v9-latest`
- SDK source: `~/Projects/stream-chat-react-native/package/src`

---

## Quick ref

| Area | RN CLI | Expo |
|---|---|---|
| Chat package | `stream-chat-react-native` | `stream-chat-expo` |
| Required peers | `@react-native-community/netinfo`, `react-native-gesture-handler`, `react-native-reanimated`, `react-native-teleport`, `react-native-worklets`, `react-native-svg` | `@react-native-community/netinfo`, `expo-image-manipulator`, `react-native-gesture-handler`, `react-native-reanimated`, `react-native-svg`, `react-native-teleport` |
| Install command | package manager install | `npx expo install` |
| Root wrapper | `GestureHandlerRootView` | `GestureHandlerRootView` in `App.tsx` or `app/_layout.tsx` |

First path:

1. Pick RN CLI vs Expo.
2. Install package and required peers.
3. Add Reanimated or Worklets Babel plugin last.
4. Wrap root with `GestureHandlerRootView`.
5. Place `OverlayProvider` and `Chat` high in the tree.
6. Use `useCreateChatClient` for normal auth.
7. Render `ChannelList`, `Channel`, `MessageList`, `MessageComposer`, and optional `Thread`.

Full screen blueprints: [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md). Load only the section you are implementing.

---

## App Integration

### Installation

RN CLI:

```bash
npm install stream-chat-react-native @react-native-community/netinfo react-native-gesture-handler react-native-reanimated react-native-teleport react-native-worklets react-native-svg
npx pod-install
```

Expo:

```bash
npx expo install stream-chat-expo @react-native-community/netinfo expo-image-manipulator react-native-gesture-handler react-native-reanimated react-native-svg react-native-teleport
```

Optional packages:

| Feature | Packages |
|---|---|
| React Navigation safe areas | `react-native-safe-area-context` |
| Offline support | `@op-engineering/op-sqlite` |
| High-performance message list | `@shopify/flash-list` |
| RN CLI media/audio/files | `@react-native-camera-roll/camera-roll`, `react-native-video`, `react-native-blob-util`, `react-native-share`, `@react-native-clipboard/clipboard`, `@react-native-documents/picker`, `react-native-image-picker` |
| Expo media/audio/files | `expo-av`, `expo-video`, `expo-file-system`, `expo-media-library`, `expo-sharing`, `expo-haptics`, `expo-clipboard`, `expo-document-picker`, `expo-image-picker` |

### Babel and entry point

The Reanimated or Worklets plugin must be last:

```js
module.exports = {
  presets: ["module:@react-native/babel-preset"],
  plugins: [
    // other plugins
    "react-native-worklets/plugin",
  ],
};
```

Use `react-native-reanimated/plugin` when the app is on Reanimated 3. Use `react-native-worklets/plugin` for Reanimated 4+.

Wrap the entry point:

```tsx
import { GestureHandlerRootView } from "react-native-gesture-handler";

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      {/* app */}
    </GestureHandlerRootView>
  );
}
```

### Client setup

Use `useCreateChatClient` for normal connection and cleanup:

```tsx
import {
  Chat,
  OverlayProvider,
  useCreateChatClient,
} from "stream-chat-react-native";

const chatClient = useCreateChatClient({
  apiKey,
  tokenOrProvider,
  userData: { id: userId, name: userName },
});

if (!chatClient) return null;

return (
  <OverlayProvider>
    <Chat client={chatClient}>{children}</Chat>
  </OverlayProvider>
);
```

For Expo, import from `stream-chat-expo`.

### Token route pattern

Production apps should use a backend route that upserts the current user and returns a Stream user token:

```ts
// Server-side only
import { StreamChat } from "stream-chat";

const serverClient = StreamChat.getInstance(apiKey, apiSecret);
await serverClient.upsertUsers([{ id: userId, name: userName }]);
const token = serverClient.createToken(userId);
```

Client response shape can be:

```ts
{ apiKey: string, token: string, userId: string, userName: string }
```

Local demo tokens can come from [`../credentials.md`](../credentials.md).

---

## Core components

| Component/hook | Use |
|---|---|
| `useCreateChatClient` | Creates, connects, returns `StreamChat | null`, disconnects on cleanup |
| `OverlayProvider` | Top-level overlay/image gallery/attachment picker provider |
| `Chat` | Provides client, theme, translations, online state |
| `ChannelList` | Queries and renders channels |
| `Channel` | Provides channel, keyboard, messages, composer, attachment picker, and thread contexts |
| `MessageList` | Renders messages inside `Channel` |
| `MessageComposer` | v9 message input; use instead of old message input patterns |
| `Thread` | Renders replies for a selected parent message |
| `ThreadList` | Renders an inbox of threads inside `Chat` |
| `WithComponents` | Replaces component slots and subcomponents |
| `useChatContext` | Reads the provided client inside `Chat` |
| `useMessageContext` | Reads current message state in custom message subcomponents |

---

## Navigation rules

- Put `OverlayProvider` above navigation screens; with React Navigation, prefer it above `NavigationContainer`.
- Keep `Chat` high and stable so screen transitions do not reconnect the socket.
- Pass `channel.cid` through navigation params. Do not pass `Channel` objects.
- Recreate a channel from `client.channel(type, id)` in the destination screen.
- Use `keyboardVerticalOffset={headerHeight}` on `Channel`.
- Use `topInset={headerHeight}` and `bottomInset={safeArea.bottom}` for attachment picker alignment.
- For threads, pass the active `thread` to the main `Channel` while the thread screen is open and render the thread screen with `threadList`.

---

## Customization

Prefer these in order:

1. Channel props for behavior changes.
2. Theme via `OverlayProvider value={{ style }}` and `Chat style={style}`.
3. `WithComponents` overrides for slots such as `MessageAuthor`, `MessageText`, `SendButton`, `ThreadListItem`.
4. Full core component replacement only when the smaller slots cannot satisfy the request.

`WithComponents` can wrap any subtree. Inner overrides merge over outer overrides.

---

## Offline support

Offline support is opt-in:

```bash
npm install @op-engineering/op-sqlite
```

Expo:

```bash
npx expo install @op-engineering/op-sqlite
```

Enable it:

```tsx
<Chat client={chatClient} enableOfflineSupport>
  {children}
</Chat>
```

Caveats from the local docs:

- Expo Go cannot use offline support; use Expo dev client or prebuild.
- Threads are not available in offline mode.
- Reset the DB on sign-out before disconnecting:

```tsx
await chatClient.offlineDb?.resetDB();
await chatClient.disconnectUser();
```

---

## Gotchas

- v9 requires React Native New Architecture.
- `react-native-teleport` is required for v9 overlays.
- `useCreateChatClient` returns `null` while connecting.
- Never pass `null` to `Chat`.
- Do not create multiple connected `StreamChat` clients.
- Do not pass `Channel` instances through navigation params.
- A channel created with only a members list gets a generated id and cannot later add/remove members in the usual channel-id flow; use explicit ids when membership editing matters.
- Use `MessageComposer` for v9 message input.
- Use `WithComponents` for component overrides instead of old prop-heavy override patterns.
- Do not wrap `MessageComposer` in extra `SafeAreaView` to fix spacing; use `Channel` insets.
- Remove old Android negative `keyboardVerticalOffset` hacks during v9 migration.
- Keep theme objects stable with `useMemo`.
- If using push notifications, keep background WebSocket behavior aligned with push delivery. `Chat` defaults `closeConnectionOnBackground` to `true`.
