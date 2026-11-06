# Stream React Native - AI assistants, LLM chat, and agentic experiences

Use this runbook when a React Native / Expo request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, a thinking indicator, "stop generating", rendering markdown / code / tables / charts from the model, voice dictation into the prompt, voice-agent visuals, letting the agent trigger actions on the device (client tools), or an agent that answers with UI (generative UI: A2UI, OpenUI).

Stream does not host the model. A **backend agent** (a bot user) answers in the Chat channel, streaming its reply by updating one message and sending `ai_indicator.*` events. The app is a **renderer and a trigger** - it never calls the LLM or holds a provider key, Stream secret, or admin token. It composes with the track: run Track A / B first (project signals, [`credentials.md`](credentials.md), Chat setup), then this runbook drives the integration.

---

## Step 1: Classify, then read the docs

Pin the Chat major first ([`references/CHAT-VERSIONS.md`](references/CHAT-VERSIONS.md)), then find the AI pages in that major's docs rather than at fixed paths - their names and places move between majors:

```bash
d=$(getstream docs chat-sdk/react-native/v<major>)
grep -niE "ai|generative|langchain|dictation|voice" $d/INDEX.md
```

(For a major the CLI doesn't list yet, search the major's `llms.txt` manifest the same way - [`references/DOCS.md`](references/DOCS.md).)

| Shape | Signals | Read (page titles) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation drawer, bottom-sheet options, voice input | **AI integrations** overview (the AI components, install, peers, Babel, dictation setup, theming) + **SDK integration** (AI replies in the regular Chat UI) |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in the same channels | **SDK integration** only - keep the app's own `MessageComposer`, message UI, and theme |
| **C. Agent acts on the device** (open a screen, read location, show a form) | "the assistant should do X in the app" | A or B, plus the "Client Tools" section of **Stream Chat AI SDK** |
| **D. Agent answers with UI** (cards, forms, A2UI, OpenUI) | "render the agent's UI", generative UI | A **Generative UI** page, if the pinned major's docs have one - see Step 4 |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | **Stream Chat AI SDK** (Vercel AI SDK) or **Stream Chat LangChain SDK** |

If it is unclear whether a backend exists, ask which one to use: the user's own agent, or one set up with Stream's AI SDK (`@stream-io/chat-ai-sdk`, Vercel AI SDK) or LangChain SDK (`@stream-io/chat-langchain-sdk`). With `AgentManager` the agent holds a WebSocket per channel, so it runs as **its own long-lived process**, not a serverless function. Reference servers: `GetStream/chat-ai-samples` `ai-sdk-sample` and `langchain-sample`. The app calls the agent's start / stop endpoints through an **authenticated** route, and the server allowlists the model - a model picker's value is only a hint.

## Step 2: Wire the components

The AI components ship with the Chat SDK, behind the `ai-components` entry point of the lane's package (`stream-chat-react-native/ai-components`, or `stream-chat-expo/ai-components` with Expo). The standalone `@stream-io/chat-react-native-ai` package is deprecated: don't install it. An app that already uses it moves over with the overview page's "Migrating from `@stream-io/chat-react-native-ai`" section. Take imports, peers, and props from the pinned major's docs and the installed types.

Decisions and traps the docs leave to you:

- **Stay on the prebuilt components** - the lane's Chat package and its AI components, not a hand-built `FlatList` on the low-level client. In shape B the main entry point does most of the work: `isMessageAIGenerated` on `<Chat>` streams the reply's text, and the default composer swaps the send button for a stop button while the AI is thinking / generating. For rich markdown / code / tables / charts, follow SDK integration's section on using the AI components' streaming view instead: a **small wrapper** on the slot that reads the message from context - the slot does not pass `text`, so registering the AI component itself renders nothing. **Add** these to the app's existing `WithComponents` overrides - do not replace them.
- **Same names in two entry points.** The main entry point and `ai-components` both export names such as `StreamingMessageView`, `AITypingIndicatorView`, and `useStreamingMessage`, as different components. Import the rich ones from `ai-components`; the `WithComponents` slot keeps the main entry point's name. Alias one import when both are in a file.
- **Install for the lane** ([`RULES.md`](RULES.md) > Runtime lane ownership, Required peer setup) exactly what the overview's Usage lists - its native chart / graphics peers and the Babel plugin it names - Expo: `npx expo install`; RN CLI: the project's package manager. Optional features (photo picker, clipboard) pick **one** lane variant; without one, those buttons silently do nothing.
- **iOS dictation is opt-in.** The speech module is compiled in only when the app turns it on (Podfile flag on RN CLI, the `stream-chat-expo` config plugin on Expo, per the overview's Speech-to-text). Without it the microphone button does not render - no error. Add the usage descriptions / Android permission it lists, then rebuild: `pod install` on RN CLI, a dev build / `npx expo prebuild` on Expo - not Expo Go.
- **Theme twice.** The AI components take their theme from their own `StreamTheme`, not from the Chat `style` / theme, and don't switch to dark by themselves - a dark mode or brand change needs both.
- **Pass `isMessageAIGenerated` on `<Chat>` only** - a value on a lower component is ignored or no longer accepted.

## Step 3: Tell the developer what the backend must send

The app only renders what the agent writes and emits, and it cannot tell when something is missing - it builds and looks subtly wrong. **Always state this to the developer**, and when they bring their own backend, ask them to confirm it before wiring the app:

- `ai_generated: true` on the bot's reply when it is **created**. `isMessageAIGenerated` keys on it; missing -> an **ordinary bubble with no typewriter and no AI markdown**, and a custom agent that does not skip its own `ai_generated` messages can **answer itself in a loop**.
- **One message, updated as tokens arrive:** throttled chunks via `ephemeralUpdateMessage`, one final `partialUpdateMessage` to persist it (`$(getstream docs chat/node)/ai-message-streaming.md`). A reply posted once, complete, **appears all at once**.
- `ai_indicator.update` with `ai_state` (`AI_STATE_THINKING`, `AI_STATE_GENERATING`, `AI_STATE_EXTERNAL_SOURCES`, `AI_STATE_ERROR`) while working, and `ai_indicator.clear` when done. Missing -> **no thinking indicator and no stop button**.
- Honor `ai_indicator.stop` (sent by `channel.stopAIResponse()`): abort the model call and keep the partial text. Missing -> **stop does nothing**.
- `generating: true` on partial updates, `false` on the final update, stop, and error. React Native ignores it, but iOS needs it - set it so one backend serves every client.

Stream's server SDKs and the sample backends already do all of this. Start the agent and register tools once per conversation, after the channel is watched - never on every render, remount, or screen focus. After one prompt, read a real bot message before debugging RN code:

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"messaging:<channel-id>"},"message_limit":5}' \
  --jq '.channels[0].messages[] | {user: .user.id, ai_generated: (if has("ai_generated") then .ai_generated else .custom.ai_generated end), generating: (if has("generating") then .generating else .custom.generating end), text: (.text // "" | .[0:40])}'
```

`null` for a bot message means the backend is not setting it - fix the agent, and tell the developer. The `ai_indicator.*` events are ephemeral; log them in the app rather than the CLI.

## Step 4: Generative UI (A2UI, OpenUI)

When the agent should answer with UI - cards, a form, a map - instead of only text, look for a "Generative UI" page (A2UI / OpenUI renderers) in the pinned major's docs.

- **The page exists:** follow it in full; it is the source for the host, renderer entry points, peer versions, message fields, and actions. The same traps apply as on web (stream-react skill's ai-integration.md, "Generative UI"): install renderer packages at the versions the docs name, tell the model what the app can show or it never writes UI, the backend moves the UI out of the reply text into the message's UI field, keep one host per conversation, treat the reply's UI as untrusted, and confirm actions that change data.
- **No such page:** the React Native SDK doesn't render generative UI in that major. Say so plainly - don't port the web renderers or build a format parser from memory. A backend that follows the format keeps each reply's text readable, so the app shows the text; confirm that with the developer, and offer the web docs only as a description of the backend contract.

---

## Reference app

The AI integrations overview links the SDK's own sample app for the AI components (an Expo ChatGPT-style app in `GetStream/stream-chat-react-native`). Read it for the wiring the docs don't show - provider order, the overrides, the composer with stop, conversation switching, the custom-data type `tsc` needs, Babel plugin order - and say the pattern came from the sample. Use the branch the docs link, which matches the pinned major. **Do not copy a sample's auth or hosts:** use [`credentials.md`](credentials.md) for the token path and your own agent URL from config.

## Pitfalls the docs do not shout about

- **Rendering the AI composer instead of `MessageComposer` drops the built-in stop button.** Wire its generating state and stop handler to `useAIState` and `channel.stopAIResponse()`, as SDK integration shows.
- **Permissions or the app crashes / dictation fails silently:** iOS microphone + speech recognition usage descriptions (and camera / photo library with the media picker), Android `RECORD_AUDIO` (and `CAMERA`); on Expo set them through the config plugins, then rebuild.
- **The composer's bottom sheet under the nav bar:** pass the bottom safe-area inset the component takes (see its props in the overview). Keyboard offset on `<Channel>` follows [`RULES.md`](RULES.md) > Navigation and overlay discipline.
- **Local backend:** the iOS simulator reaches `localhost`, the Android emulator needs `10.0.2.2`, a physical device needs the Mac's LAN IP or a tunnel. Keep the agent URL in config.
- **Client tools on device** arrive as `custom_client_tool_invocation` events on the channel. Request OS permissions when the tool first runs, confirm with the user before any tool that changes data, and validate `args` - they are model output.

## Verify before stopping

- on a real build ([`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md)), a prompt gets a streamed, markdown-rendered answer from the bot in the same channel; the thinking indicator appears and clears; stop keeps the partial answer; dictation fills the prompt (iOS: the microphone button is visible at all)
- the Step 3 CLI check shows `ai_generated: true` and a final `generating: false`, and the developer was told what the backend must send
- existing message / composer overrides still render (shape B); `tsc --noEmit` passes with the `ai_generated` custom type
