# Chat React Native - Setup and Integration

Stream Chat React Native provides pre-built Chat UI for React Native CLI and Expo apps. This file covers packages, app setup, client/auth patterns, navigation, offline support, and gotchas. For `llms.txt` docs lookup, see [DOCS.md](DOCS.md). For screen structures, see [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md).

Rules: [../RULES.md](../RULES.md) (Chat-only, New Architecture, secrets, runtime lane ownership, provider placement, blueprint reads).

Manifest-selected docs are the authority. Use [DOCS.md](DOCS.md) before installing packages or making API-specific claims.

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
2. Use [DOCS.md](DOCS.md) to fetch the manifest-selected `Installation` page and verify npm dist-tags.
3. Install package and required peers.
4. Add Reanimated or Worklets Babel plugin last.
5. Wrap root with `GestureHandlerRootView`.
6. Place `OverlayProvider` and `Chat` high in the tree.
7. Use `useCreateChatClient` for normal auth.
8. Render `ChannelList`, `Channel`, `MessageList`, `MessageComposer`, and optional `Thread`.
9. If the user provided a target appearance (screenshot, Figma, or "look like \<app\>"), **before** building run [design-matching.md](design-matching.md): decompose the reference region by region, plan every theming/layout/functional difference, then apply the `Theming Blueprint` and `Component Override Blueprint` and verify region-by-region.

Full screen blueprints: [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md). Load only the section you are implementing.

---

## App Integration

### Installation

RN CLI:

```bash
npm view stream-chat-react-native version dist-tags --json
npm install stream-chat-react-native@latest @react-native-community/netinfo react-native-gesture-handler react-native-reanimated react-native-teleport react-native-worklets react-native-svg
npx pod-install
```

Expo:

```bash
npm view stream-chat-expo version dist-tags --json
npx expo install stream-chat-expo@latest @react-native-community/netinfo expo-dev-client expo-image-manipulator react-native-gesture-handler react-native-reanimated react-native-svg react-native-teleport
npx expo prebuild
```

Install `@latest` only after confirming the npm dist-tag matches the selected docs. If not, use the manifest-selected docs' tag or exact version.

### Optional dependency map

Optional dependencies are opt-in native capability packages, not default Chat requirements. Use this map only after the user asks for the capability or after manifest-selected docs require it.

Add optional dependencies with the runtime's normal install lane:

- RN CLI: use the project's package manager, then re-link the native app after native packages change — iOS: `npx pod-install`; **Android: rebuild with `npx react-native run-android`**. Autolinking runs at Gradle build time, so an already-installed Android app will **not** pick up a new native module (e.g. an attachment picker) until it is rebuilt.
- Expo: use `npx expo install` so versions match the Expo SDK.
- Expo Chat apps use a dev-client/native-build lane by default because the SDK includes native code. Do not target Expo Go.
- If an Expo app does not already have native projects, run `npx expo prebuild --clean`; run it again when native config changes need to be regenerated.
- Add platform permissions and config plugins from the selected package docs.

| Feature | Packages |
|---|---|
| React Navigation safe areas | RN CLI: `react-native-safe-area-context`; Expo: `npx expo install react-native-safe-area-context` |
| Native multipart upload progress | RN CLI: none beyond required Stream peers; Expo: none beyond dev-client lane |
| Attachment picker with built-in image media library | RN CLI: `@react-native-camera-roll/camera-roll`; Expo: `expo-media-library` |
| Native image picker / camera image upload | RN CLI: `react-native-image-picker`; Expo: `expo-image-picker` |
| File attachments / document picker | RN CLI: `@react-native-documents/picker`; Expo: `expo-document-picker` |
| Attachment sharing outside the app | RN CLI: `react-native-blob-util react-native-share`; Expo: `expo-sharing` |
| Video playback / video attachments | RN CLI: `react-native-video`; Expo: `expo-video` |
| Voice recording and audio attachments | RN CLI: `react-native-video react-native-audio-recorder-player react-native-blob-util`; Expo SDK 53+: `expo-audio`; Expo SDK 51/52: `expo-av` |
| Copy message | RN CLI: `@react-native-clipboard/clipboard`; Expo: `expo-clipboard` |
| Haptic feedback | RN CLI: `react-native-haptic-feedback`; Expo: `expo-haptics` |
| Offline support | RN CLI: `@op-engineering/op-sqlite`; Expo: `@op-engineering/op-sqlite` |
| High-performance message list | RN CLI: `@shopify/flash-list`; Expo: `@shopify/flash-list` |

What the common entries mean:

- Media library packages let the SDK or app read existing photos/videos from the device library.
- Native multipart upload progress uses `useNativeMultipartUpload={true}` on `Chat`; Expo already uses the dev-client/native-build lane.
- Image picker packages let the app open native picker and camera capture flows.
- Document picker packages let the app choose arbitrary files outside the media library.
- Sharing packages let the app hand an attachment to another app.
- Audio packages add recording or playback primitives and usually need microphone permissions.
- Offline storage packages add a local database and require native code.
- List virtualization packages are performance helpers, not required for basic Chat screens.

If the user request is ambiguous, inspect the selected docs and existing app behavior before installing. For example, image library access, camera capture, document picking, and sharing are separate native capabilities and should not all be installed for one vague request.

After dependencies are installed, keep optional UI inside the normal `Channel` and `MessageComposer` flow unless manifest-selected docs require a different placement.

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
| `MessageComposer` | Current message input; use instead of old message input patterns |
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
- Use `keyboardVerticalOffset={headerHeight}` on `Channel`, and pair it with `topInset={headerHeight}` so the attachment picker bottom sheet reaches its full snap point when a native navigation header is present.
- `bottomInset` stays opt-in. Add it only when a specific layout requires it (e.g. a tab bar that owns the bottom safe-area).
- For threads, pass the active `thread` to the main `Channel` while the thread screen is open and render the thread screen with `threadList`.

---

## Customization

Use [DOCS.md](DOCS.md) to fetch the manifest-selected theming/customization page first. Prefer these in order:

1. Channel props for behavior changes.
2. Theme via `OverlayProvider value={{ style }}` and `Chat style={style}`.
3. `WithComponents` overrides for the documented slot that matches the requested customization.
4. Full core component replacement only when the smaller slots cannot satisfy the request.

`WithComponents` can wrap any subtree. Inner overrides merge over outer overrides.

### Component override model (v9+) — `WithComponents` only

- **ALL component overrides go through one `WithComponents overrides={{ … }}` provider** placed above navigation so they apply on every screen. **Passing a component as a `<Channel>` prop is silently ignored** — no error, no effect; it reads exactly like a stale bundle during verification. If an override "isn't taking," first confirm it's in `WithComponents`, not a `<Channel>` prop.
- **The full overridable slot set is the compiled `components` map** in the installed package (`node_modules/stream-chat-react-native-core/.../contexts/componentsContext/defaultComponents.js`) — grep that for real slot names, don't work from memory.
- **Nullable extension slots live in `OptionalComponentOverrides`, not `DEFAULT_COMPONENTS`.** The in-bubble content slots (`MessageContentTopView` / `MessageContentBottomView` / `MessageContentLeading` / `MessageContentTrailing`, `MessageText`, `Input`, …) are in `OptionalComponentOverrides`, so they **won't appear if you only grep the `DEFAULT_COMPONENTS` keys** — "that slot doesn't exist" is usually "I grepped the wrong map." Check both.

### Composer, attach button, and message-metadata facts

Reference facts the composer/message customizations lean on (verified against **stream-chat-expo 9.7.0**; confirm against the installed package — the full design-match procedure is in [design-matching.md](design-matching.md#composer-deep-dive--the-render-tree-the-surfaces-and-the-two-facet-buttons)):

- **Composer surface vs inner rows.** `messageComposer.wrapper` (and `floatingWrapper`) is the **full-bleed bar surface** (default: padding only, no background). `messageComposer.container` / `contentContainer` are inner `flexDirection: 'row'` layout rows sized to their children — theming `container` colours only a band around the controls, not the bar. The input pill is `inputBoxWrapper`; grow it via symmetric `inputBox` `paddingTop`/`paddingBottom`, not a fixed wrapper height (the pill doesn't vertically-centre a single line).
- **Send/mic** is the SDK's `OutputButtons`, rendered **inside** the input pill (`MessageInputTrailingView`) and **stateful** (mic/audio at rest → send when the input has text). Reuse `OutputButtons` / `AudioRecordingButton`; don't hand-roll. Move it outside the pill via `MessageComposerTrailingView`.
- **`toggleAttachmentPicker` is a private helper *inside* the SDK `AttachButton`** — composed from `openAttachmentPicker` / `closeAttachmentPicker` / `focusInputOnPickerClose` / `inputBoxRef` + `attachmentPickerStore`. It is **not on any context or hook**. A custom attach button must **replicate it, including the refocus-input-on-close branch** — not just call open/close. The SDK `AttachButton` also renders as a bordered `Button variant="secondary" type="outline"` with `icons.Plus` and swaps `+`→keyboard while the picker is open; a custom borderless `+` must reproduce that open-state swap.
- **A chat app's attach sheet (tiles on top + gallery below) is Stream's `AttachmentPicker`** — override `AttachmentPickerSelectionBar` via `WithComponents`; don't build a standalone modal.
- **Metadata inside the bubble** (timestamp/ticks bottom-trailing) is structural — render in `MessageContentBottomView`/`MessageContentTrailingView` (inside the bubble), set `alignSelf`, reproduce the body padding, and set the default outside `MessageFooter` to `() => null`. Reuse `MessageStatus` for ticks (recolour via the check-icon `stroke`).
- **Metadata BESIDE the bubble** (timestamp/ticks to the side, same row) is a different slot: override **`MessageSpacer`** (trailing child of the message row; row is `row-reverse` for outgoing, so it lands left-of-outgoing / right-of-incoming, bottom-aligned). Not `MessageContent`, not `MessageFooter`. Pair with `MessageFooter → () => null`.
- **Append content BELOW a whole message** (e.g. a translate affordance) — override the **`Message`** slot and wrap the default `Message`; don't use `MessageFooter` (renders inside the content column, collides with avatar alignment). The wrapper is above the SDK's `MessageProvider`, so read `message` from **props**, not `useMessageContext`.
- **Ungroup messages** (each standalone, avatar/name/time on every one) → `getMessageGroupStyle={() => ['single']}`, NOT `enableMessageGroupingByUser={false}` (which empties `groupStyles` and removes the per-message vertical padding → messages collapse). `['single']` also re-enables the bubble **tail** (`messageBubbleRadiusTail`); override `theme.messageItemView.content.container` corner radii for uniform bubbles. Note the incoming **avatar** hides unless a message is `lastGroupMessage` — with grouping changed, override `MessageAuthor` (mounted only for incoming rows) to always render it.
- **Attached, full-width reaction box** (vs the default external pill) → render in `MessageContentBottomView` with `alignSelf: 'stretch'`, and null both `ReactionListTop`/`ReactionListBottom`. Toggle via `useMessageContext().handleReaction(type)` (there is **no** `showMessageReactions` on that context).
- **Custom `ChannelPreview` slot** receives `{ channel, lastMessage, unread, muted, pinned }` — **`onSelect` comes from `useChannelsContext()`, not props** (reading `props.onSelect` silently no-ops the row tap). The default preview renders the sent/read tick on **line 2** with a `You:` prefix; designs that want the tick on line 1 (by the timestamp) or no prefix must reroute via the preview slots.
- **`AttachButton` `iconOnly` renders a CIRCLE** (a squircle/square reference is a shape override, not a recolor). **Send/mic default INSIDE the pill** — move outside via `OutputButtons` in `MessageComposerTrailingView` + null `MessageInputTrailingView`.
- **Theme overrides don't cascade:** user `style.semantics` merges *after* `$token` resolution, so overriding `accentPrimary` doesn't retint `$brand*`-derived tokens. Set literals for each. **Composer buttons use `button*` tokens** (`buttonSecondaryText`/`buttonSecondaryBorder` for attach/mic, `buttonPrimaryBg` for send), not `accentPrimary`.
- **Composer placeholder text** (e.g. changing "Send a message" to something shorter) is a **translation, not a prop:** build a `Streami18n` from **`stream-chat-expo`** (the RN SDK's own — not `stream-chat`) with `translationsForLanguage: { 'Send a message': '<your text>' }` and pass it as `<Chat i18nInstance={…}>`.

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

Caveats from the manifest-selected docs:

- Expo apps already use a dev-client/native-build lane. Expo Go is not a supported target for this skill.
- Threads are not available in offline mode.
- Reset the DB on sign-out before disconnecting:

```tsx
await chatClient.offlineDb?.resetDB();
await chatClient.disconnectUser();
```

---

## Expo SDK 55 → 56 changes

Expo SDK 56 changed several Chat-relevant defaults. Pick the right blueprint based on the SDK version reported by the project-signals probe in [../SKILL.md](../SKILL.md):

- **`@react-navigation/*` is no longer co-installable with `expo-router`.** Metro halts with "As of SDK 56, expo-router is no longer compatible with react-navigation." On SDK 56+ use the Platform-based header-offset swap in [CHAT-REACT-NATIVE-blueprints.md](CHAT-REACT-NATIVE-blueprints.md) > Channel Screen. See also [../RULES.md](../RULES.md) > Expo Router SDK 56+ — no React Navigation.
- **`"edgeToEdgeEnabled": true` is no longer needed in `app.json`.** Android 16 makes edge-to-edge mandatory; `expo prebuild` warns and ignores the entry. Safe to omit on SDK 56+; still required on SDK 53–55.
- **Reanimated 4 ships by default**, so the last Babel plugin should be `react-native-worklets/plugin`. Use `react-native-reanimated/plugin` only when the project pinned Reanimated 3.
- **React 19 / RN 0.85 baseline.** Most Chat blueprints work unchanged, but third-party libraries that haven't bumped their peer ranges may need `--legacy-peer-deps` during install.

When in doubt, run the probe and check the `EXPO_SDK` line before applying any blueprint.

---

## Gotchas

- The bundled references assume React Native New Architecture.
- **Expo SDK 57 pins a crash-prone `react-native-reanimated@4.5.0` + `react-native-worklets@0.10.0`.** Require ≥`4.5.1`/≥`0.10.2` (good pairing: `4.5.2`/`0.10.2`) and rebuild native — the crash is on worklet/animation paths, not at boot, so a clean launch does not clear it. `npx expo install react-native-reanimated` re-pins the bad version; the safe versions are baked into the [builder.md](../builder.md) install blocks. See [../RULES.md](../RULES.md) > Required peer setup.
- `react-native-teleport` is required for overlays.
- `useCreateChatClient` returns `null` while connecting.
- Never pass `null` to `Chat`.
- Do not create multiple connected `StreamChat` clients.
- Do not pass `Channel` instances through navigation params.
- A channel created with only a members list gets a generated id and cannot later add/remove members in the usual channel-id flow; use explicit ids when membership editing matters.
- Use `MessageComposer` for message input.
- Use `WithComponents` for component overrides instead of old prop-heavy override patterns.
- Do not wrap `MessageComposer` in extra `SafeAreaView` to fix spacing; use `Channel` insets.
- Remove old Android negative `keyboardVerticalOffset` hacks during migration.
- Keep theme objects stable with `useMemo`.
- For upload progress, use `useNativeMultipartUpload={true}` on `Chat`.
- On iOS Simulator, after fully closing and reopening the app, the first native multipart upload can fail while later uploads may proceed. Verify on a real device before treating it as a general SDK bug.
- If using push notifications, fetch the manifest-selected push notification docs before changing setup. Do not assume background WebSocket behavior or default prop values from memory.
