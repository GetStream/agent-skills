# Stream React Native - AI assistants, LLM chat, and agentic experiences

Use this runbook when a React Native / Expo request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, a thinking indicator, "stop generating", rendering markdown / code / tables / charts from the model, voice dictation into the prompt, or letting the agent trigger actions on the device (client tools).

It is a **router, not a copy of the docs**: it picks the pages to fetch and adds only what the docs do not say. Fetch the pages live, apply them, and cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send, and the CLI check are shared by every platform and live there. It composes with the track: run Track A / B first (project signals, [`credentials.md`](credentials.md), Chat setup), then this runbook drives the integration.

---

## Step 1: Classify, then fetch

Pages come from the Chat primary manifest ([`references/DOCS.md`](references/DOCS.md)) - search it for `ai-integrations` and fetch by title:

| Shape | Signals | Fetch (manifest title) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation drawer, bottom-sheet options, voice input | **AI Integrations** (the `@stream-io/chat-react-native-ai` components, install + peers, Babel, permissions, `StreamTheme`) + **SDK Integration** (wiring them into `stream-chat-react-native`) |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in the same channels | **SDK Integration** only - keep the app's own `MessageComposer`, message UI, and theme |
| **C. Agent acts on the device** (open a screen, read location, show a form) | "the assistant should do X in the app" | A or B, plus the "Client Tools" section of **Stream Chat AI SDK** |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | **Stream Chat AI SDK** (Vercel AI SDK) or **Stream Chat LangChain SDK** |

Decisions the docs leave to you:

- **Stay on the prebuilt components** - the lane's Chat package + `@stream-io/chat-react-native-ai`, not a hand-built `FlatList` on the low-level client. In shape B the core SDK does most of the work: `isMessageAIGenerated` on `<Chat>` renders its built-in `StreamingMessageView` (typewriter), and the default composer swaps the send button for `StopMessageStreamingButton` while the AI is thinking / generating. Add a thinking indicator under `MessageList`. For rich markdown / code / tables / charts, register a **small wrapper** on the `StreamingMessageView` slot that reads `useMessageContext().message` and renders the AI package's `<StreamingMessageView text={message.text ?? ""} />` - do not register the AI component itself, the slot does not pass `text`. **Add** these to the app's existing `WithComponents` overrides - do not replace them.
- **Install for the lane** ([`RULES.md`](RULES.md) > Runtime lane ownership, Required peer setup): the package, its native peers (`react-native-svg`, `victory-native`, `@shopify/react-native-skia`, plus the Reanimated / Worklets / Gesture Handler the Chat SDK already needs), and `@babel/plugin-proposal-export-namespace-from` - Expo: `npx expo install`; RN CLI: the project's package manager. Optional features pick **one** lane variant: `expo-image-picker` vs `react-native-image-picker`, `expo-clipboard` vs `@react-native-clipboard/clipboard`. The package ships **native code** (dictation), so rebuild: `pod install` on RN CLI, a dev build / `npx expo prebuild` on Expo - not Expo Go. It is a **0.x** package - check `npm view @stream-io/chat-react-native-ai version` and confirm props against the installed types before copying from the sample.

## Step 2: Fill the gaps from the reference app

The docs show each component; the **wiring around them** lives only in the reference app (RN CLI). Read the matching file instead of inventing it, and say the pattern came from the sample:

`https://raw.githubusercontent.com/GetStream/chat-ai-samples/main/react-native/<file>`

| Need | File |
|---|---|
| Provider order (`SafeAreaProvider` > `StreamTheme` > `GestureHandlerRootView` > `OverlayProvider` > `Chat isMessageAIGenerated`) | `App.tsx` |
| `<Channel preSendMessageRequest>` (watch on first send, start the agent once, title via `summarize`), `WithComponents` overrides (`StreamingMessageView`, bot-bubble theme, hidden author / footer), `ComposerView` with stop, AI typing indicator | `screens/ChatContent.tsx` |
| Conversation drawer, "new chat" = a fresh unwatched channel | `screens/MenuDrawer.tsx`, `contexts/AppContext.tsx` |
| `ComposerView` bottom-sheet options | `bottomSheetOptions.ts` |
| Backend calls (start / stop agent, summarize) | `http/requests.ts` |
| `ai_generated` custom-data type (`tsc` fails without it) | `custom-types.d.ts` |
| Babel plugin order (export-namespace-from, worklets last) | `babel.config.js` |

Component source: `GetStream/ai-components-js` (`packages/react-native-sdk`); core SDK side: `stream-chat-react-native` `package/src/components/AITypingIndicatorView/` (`useAIState`, `AIStates`) and `StopMessageStreamingButton` in `package/src/components/MessageInput/`.

**Do not copy the sample's auth or hosts.** `chatConfig.ts` hardcodes an API key and a static user token, and `http/requests.ts` points at a demo host. Use [`credentials.md`](credentials.md) for the token path and your own agent URL from config.

## Step 3: State the contract, leave a tripwire

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer and run its CLI check before debugging RN code. Then leave a dev-only tripwire in the `isMessageAIGenerated` function the docs already have you write, so a missing `ai_generated` shows in Metro instead of as a silent plain bubble (match your bot's user id):

```ts
const warned = new Set<string>();
const isMessageAIGenerated = (message: LocalMessage) => {
  const ai = !!message.ai_generated;
  if (__DEV__ && !ai && message.user?.id?.startsWith("ai-bot") && !warned.has(message.id)) {
    warned.add(message.id);
    console.warn(`[AI] Bot message ${message.id} has no ai_generated: true - the backend agent must set it.`);
  }
  return ai;
};
```

---

## Pitfalls the docs do not shout about

- **Rendering `ComposerView` instead of `MessageComposer` drops the built-in stop button.** Pass `isGenerating` (Thinking or Generating from `useAIState`) and `stopGenerating={() => channel.stopAIResponse()}`, as SDK Integration shows.
- **Same names in two packages.** `StreamingMessageView` and `AITypingIndicatorView` exist in both the core SDK and `@stream-io/chat-react-native-ai`. Import the rich ones from the AI package; the `WithComponents` slot keeps the core name.
- **Pass `isMessageAIGenerated` on `<Chat>` only.** `<Channel>` accepts the prop but the SDK overwrites it with the `<Chat>` value, so a `<Channel>`-level function is silently ignored.
- **Theme twice.** `StreamTheme` (AI components) and the Chat `theme` are separate systems - a dark mode or brand change needs both.
- **Permissions or the app crashes / dictation fails silently:** iOS `NSMicrophoneUsageDescription` + `NSSpeechRecognitionUsageDescription` (and camera / photo library with the media picker), Android `RECORD_AUDIO` (and `CAMERA`); on Expo use the package's config plugin, then rebuild.
- **`ComposerView` bottom sheet under the nav bar:** pass `bottomSheetInsets` from `useSafeAreaInsets()` (the sample pads Android extra). Keyboard offset on `<Channel>` follows [`RULES.md`](RULES.md) > Navigation and overlay discipline.
- **Local backend:** the iOS simulator reaches `localhost`, the Android emulator needs `10.0.2.2`, a physical device needs the Mac's LAN IP or a tunnel. Keep the agent URL in config.
- **Client tools on device:** request OS permissions when the tool first runs (the rest of the client-tool rules are in the contract).

## Verify before stopping

- on a real build ([`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md)), a prompt gets a streamed, markdown-rendered answer from the bot in the same channel; the thinking indicator appears and clears; stop keeps the partial answer; dictation fills the prompt
- the contract CLI check passes and the developer was told the contract
- existing message / composer overrides still render (shape B); `tsc --noEmit` passes with the `ai_generated` custom type
