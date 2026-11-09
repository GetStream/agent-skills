# AI chat in React Native

Run this when the app talks to an LLM through Chat: a ChatGPT-style app, an assistant or
copilot inside an existing chat, streaming answers with a thinking indicator and stop,
voice input into the prompt, an agent that acts on the device (client tools), or an agent
that answers with UI (generative UI). For a support bot or help desk, the backend comes
from stream-react skill's ai-support-agent.md; this file covers the app.

Stream doesn't host the model. A backend agent (a bot user) answers in the channel by
updating one message and sending `ai_indicator.*` events. The app renders and triggers -
it never calls the LLM or holds a provider key, Stream secret, or admin token.

## Docs

Pin the Chat major first (chat-versions.md), then find the AI pages in that major's docs
rather than at fixed paths - their names and places move between majors:

```bash
d=$(getstream docs chat-sdk/react-native/v<major>)
grep -niE "ai|generative|langchain|speech|dictation" $d/INDEX.md
```

| Need | Page (by title) |
| --- | --- |
| The AI components: streaming markdown, composer, typing indicator, speech-to-text, theming | "AI Integrations" overview |
| AI replies in the regular message list and composer | "SDK integration" |
| UI in a reply: A2UI, OpenUI, your own components | "Generative UI" (if the major has one) |
| A backend: Vercel AI SDK or LangChain, client tools | "Stream Chat AI SDK", "Stream Chat LangChain SDK" |

An AI-first app (one user + one assistant, conversation drawer, voice input) needs the
overview and SDK integration. An assistant inside an existing messenger needs SDK
integration only - keep the app's own composer, message UI, and theme. An agent that acts
on the device adds the client tools section of the AI SDK page.

## Backend

Two shapes work:

- **Webhook turn** - a `message.new` webhook route runs one LLM turn with the server SDK
  and returns. stream-react skill's ai-support-agent.md builds it.
- **Long-lived agent** - `@stream-io/chat-ai-sdk` (Vercel AI SDK) or
  `@stream-io/chat-langchain-sdk` with `AgentManager`. It holds a WebSocket per channel,
  so it runs as its own process, not a serverless function. Reference servers:
  `GetStream/chat-ai-samples` `ai-sdk-sample` and `langchain-sample`.

If it's unclear whether a backend exists, ask which one to use. Start agents through an
authenticated route, once per conversation after the channel is watched - never on every
render, remount, or screen focus - and allowlist the model on the server.

The app can't tell when the agent skips a field - it builds and looks subtly wrong. Tell
the developer what the agent must send, and run the CLI check before debugging app code:
both are in the stream skill's ai-backend-contract.md. In short: `ai_generated: true` on
the reply (missing: a plain bubble, and a custom agent can answer itself in a loop), one
message updated as tokens arrive, `ai_indicator.update` / `.clear` (missing: no thinking
indicator and no stop button), honoring `ai_indicator.stop` (sent by
`channel.stopAIResponse()`), and `generating` for the other platforms. A `null` field on a
real bot message means fix the agent, not the app.

A backend on the developer's machine: the iOS simulator reaches `localhost`, the Android
emulator needs `10.0.2.2`, a physical device needs the machine's LAN IP or a tunnel. Keep
the agent URL in config.

## Client

The AI components ship with the Chat SDK, behind the lane's `ai-components` entry point
(`stream-chat-react-native/ai-components`, or `stream-chat-expo/ai-components` on Expo).
The standalone `@stream-io/chat-react-native-ai` package is deprecated: don't install it.
An app that already uses it moves over with the overview page's "Migrating from
`@stream-io/chat-react-native-ai`" section. Take imports, peers, and props from the pinned
major's docs and the installed types. Defaults to keep in SKILL.md applies to every
override below.

- Pass `isMessageAIGenerated` on `<Chat>` only - on a lower component it is ignored. With
  it, the default message list streams the reply, and the default composer swaps send for
  a stop button while the AI is thinking or generating.
- For rich markdown / code / tables in the regular message list, follow SDK integration:
  a small wrapper on the message-text slot that reads the message from context and
  renders the AI components' streaming view. Registering the AI component directly on
  the slot renders nothing - the slot doesn't pass `text`. Add to the app's existing
  `WithComponents` overrides; don't replace them.
- The main entry point and `ai-components` export some of the same names
  (`StreamingMessageView`, `AITypingIndicatorView`, ...) as different components. Import
  the rich ones from `ai-components`, keep the slot names from the main entry point, and
  alias one import when a file needs both.
- Replacing `MessageComposer` with the AI composer drops the built-in stop button. Show
  one while `useAIState(channel).aiState` is thinking or generating, calling
  `channel.stopAIResponse()`.
- Install what the overview's Installation lists (its native peers and the Babel setup),
  with `npx expo install` on Expo. Optional features (media picker, clipboard) need one
  of the listed packages for the lane; without one, their buttons silently do nothing.
- Speech-to-text on iOS is compiled in only when the app turns it on (a Podfile flag on
  RN CLI, the `stream-chat-expo` config plugin on Expo, per the overview's
  Speech-to-text). Without it the microphone button doesn't render, with no error. Add
  the microphone and speech-recognition usage descriptions (Android `RECORD_AUDIO`), then
  rebuild native - `pod install`, or a new development build.
- The AI components take their theme from their own theme provider, not the Chat theme,
  and don't switch to dark by themselves: a dark mode or brand change is applied twice.
- The composer's bottom sheet sits under the navigation bar unless it gets the bottom
  safe-area inset (see its props in the overview). Keyboard offsets on `<Channel>` follow
  SKILL.md.
- Client tools arrive as `custom_client_tool_invocation` events on the channel. Ask for OS
  permissions when a tool first runs, confirm with the user before any tool that changes
  data, and validate `args` - they're model output.

## Generative UI: A2UI and OpenUI

When the agent should answer with UI - cards, a form, a map - look for a "Generative UI"
page in the pinned major's docs.

- **The page exists:** read it in full and follow it; it is the source for the host, the
  renderer entry points, peer versions, message fields, and actions. The traps the web
  SDK documents apply here too (stream-react skill's ai-integration.md, "Generative UI"):
  install renderer packages at the versions the docs name, tell the model what the app
  can show or it never writes UI, the backend moves the UI out of the reply text into the
  message's UI field, keep one host per conversation, treat the reply's UI as untrusted,
  and confirm actions that change data.
- **No such page:** the React Native SDK doesn't render generative UI in that major. Say
  so plainly - don't port the web renderers or build a format parser from memory. A
  backend that follows the format keeps each reply's text readable, so the app shows the
  text; confirm that with the developer.

## Reference implementation

The overview links the SDK's own example app for the AI components (an Expo ChatGPT-style
app in `GetStream/stream-chat-react-native`); read it on the branch the docs link for the
wiring the docs don't show - provider order, the overrides, the composer with stop,
conversation switching, the custom-data types `tsc` needs, and Babel setup. Don't copy
auth or hosts from any sample; use the token route from SKILL.md.

## Verify

On a native build (simulator-verification.md): a prompt gets a streamed,
markdown-rendered answer from the bot in the same channel; the thinking indicator appears
and clears; stop keeps the partial answer; with speech-to-text, the microphone button is
visible and dictation fills the prompt. The QueryChannels check shows `ai_generated: true`
and a final `generating: false`; existing message and composer overrides still render;
`tsc --noEmit` passes.
