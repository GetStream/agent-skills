# AI chat in React

Run this when the app talks to an LLM through Chat: a ChatGPT-style app, an assistant or
copilot inside an existing chat, streaming answers with a thinking indicator and stop, or
an agent that acts in the app (client tools). For a support bot or help desk, follow
ai-support-agent.md first - it builds the backend; this file adds the UI.

Stream doesn't host the model. A backend agent (a bot user) answers in the channel by
updating one message and sending `ai_indicator.*` events. The app renders and triggers -
it never calls the LLM or holds a provider key, Stream secret, or admin token.

## Docs

```bash
d=$(getstream docs chat-sdk/react)
cat $d/guides/ai-integrations.md                         # @stream-io/chat-react-ai components, AI states
cat $d/guides/ai-integrations/sdk-integration.md         # wiring them into stream-chat-react
cat $d/guides/ai-integrations/stream-chat-ai-sdk.md      # Vercel AI SDK backend, client tools
cat $d/guides/ai-integrations/stream-chat-langchain-sdk.md
cat $d/components/ai/hooks.md
```

An AI-first app (one user + one assistant, conversation sidebar, model picker) needs
ai-integrations.md and sdk-integration.md. An assistant inside an existing messenger needs
sdk-integration.md only - keep the app's own composer, message UI, and styling. An agent
that acts in the app adds the "Client Tools" section of stream-chat-ai-sdk.md.

## Backend

Two shapes work:

- **Webhook turn** - a `message.new` webhook route runs one LLM turn with the server SDK
  and returns. Fits a Next.js route; ai-support-agent.md builds it.
- **Long-lived agent** - `@stream-io/chat-ai-sdk` (Vercel AI SDK) or
  `@stream-io/chat-langchain-sdk` with `AgentManager`. It holds a WebSocket per channel,
  so it runs as its own process, not a serverless function. Reference servers:
  `GetStream/chat-ai-samples` `ai-sdk-sample` and `langchain-sample`.

If it's unclear whether a backend exists, ask which one to use. Start agents through an
authenticated route, once per conversation after the channel is watched - never on every
render or remount - and allowlist the model on the server.

The app can't tell when the agent skips a field - it builds and looks subtly wrong. Tell
the developer what the agent must send, and have them confirm it for their own backend:

- `ai_generated: true` when the reply is created. Missing: a plain bubble with no
  typewriter or markdown, and a custom agent can answer its own messages in a loop.
- One message, updated as tokens arrive: `ephemeralUpdateMessage` for throttled chunks,
  one final `partialUpdateMessage` to persist it (`$(getstream docs
  chat/node)/ai-message-streaming.md`). Posted once, complete, it appears all at once.
- `ai_indicator.update` (`AI_STATE_THINKING`, `AI_STATE_GENERATING`, ...) while working,
  `ai_indicator.clear` when done. Missing: no thinking indicator and no stop button.
- Honor `ai_indicator.stop`: abort the model call, keep the partial text. Missing: stop
  does nothing.
- `generating: true` on partials, `false` on the final update, stop, and error. React
  ignores it, but iOS needs it - set it so one backend serves every client.

Stream's server SDKs already do all of this. Check a real bot message after one prompt,
before debugging React code:

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"messaging:<channel-id>"},"message_limit":5}' \
  --jq '.channels[0].messages[] | {user: .user.id, ai_generated: (if has("ai_generated") then .ai_generated else .custom.ai_generated end), generating: (if has("generating") then .generating else .custom.generating end), text: (.text // "" | .[0:40])}'
```

`null` on a bot message means the agent isn't setting it - fix the agent, not the app.

## Client

Stay on `stream-chat-react` + `@stream-io/chat-react-ai`. It's a 0.x package - check
props against the installed types. Install `material-symbols` with it.

- Pass `isMessageAIGenerated` on `<Chat>`, not per list - the channel list preview uses
  it too.
- For rich markdown / code / tables, register a small wrapper on the `StreamedMessageText`
  slot that reads `useMessageContext().message` and renders
  `<StreamingMessage text={message.text ?? ""} />`. Registering `StreamingMessage`
  directly renders nothing - the slot doesn't pass `text`. Add to the app's existing
  `WithComponents` overrides; don't replace them.
- Import `@stream-io/chat-react-ai/styles/index.css` after `stream-chat-react`'s CSS. The
  docs omit it; without it (and `material-symbols`) the composer icons render as words
  ("close", "refresh").
- Replacing the composer with `AIMessageComposer` drops the built-in stop button. Render
  one while `useAIState(channel).aiState` is thinking or generating, calling
  `channel.stopAIResponse()`.
- Both packages export an `AIStateIndicator`. The `stream-chat-react` one is
  channel-aware; the `chat-react-ai` one isn't - gate it with `useAIState` and alias the
  import.
- The AI components use browser APIs - render them from `'use client'` modules.
  `SpeechToTextButton` needs the Web Speech API; hide it where unsupported.
- No LLM key in the bundle (`NEXT_PUBLIC_*`, `VITE_*`).
- Client tools arrive as `custom_client_tool_invocation` events on the channel. Confirm
  with the user before any tool that changes data, and validate `args` - they're model
  output.

## Reference implementation

`GetStream/chat-ai-samples` `react/src/` has the wiring the docs don't show:
`components/ChatContent.tsx` (overrides, lazy "new conversation" channel),
`components/Composer.tsx` (`AIMessageComposer`, start the agent once, title via
`summarize`), `components/AIStateIndicator.tsx`, `stream-custom-data.d.ts` (the
`ai_generated` type `tsc` needs), and `index.css` (layer order). Don't copy its auth - it
uses a static user token and an unauthenticated agent URL; use the token route from
SKILL.md.

## Verify

A prompt gets a streamed, markdown-rendered answer from the bot in the same channel; the
thinking indicator appears and clears; stop keeps the partial answer; the QueryChannels
check shows `ai_generated: true` and a final `generating: false`; existing message and
composer overrides still render; `tsc --noEmit` passes.
