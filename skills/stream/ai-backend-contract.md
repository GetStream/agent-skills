# Stream AI integrations - the backend agent contract (all platforms)

Shared by the platform AI runbooks ([`../stream-react/ai-integration.md`](../stream-react/ai-integration.md), [`../stream-react-native/ai-integration.md`](../stream-react-native/ai-integration.md), [`../stream-swift/ai-integration.md`](../stream-swift/ai-integration.md)). It covers what is the same on every platform: where the model runs, what the agent must send, and how to check it. The platform runbook covers the UI.

**The one idea to hold:** Stream does not host the model. A **backend agent** (a bot user) answers in the Chat channel, streaming its reply by updating one message and sending `ai_indicator.*` events. The app is a **renderer and a trigger** - it never calls the LLM or holds a provider key, Stream secret, or admin token, and never "calls the LLM from the client, then posts the answer".

## Where the agent runs

- Stream's server SDKs: `@stream-io/chat-ai-sdk` (Vercel AI SDK) or `@stream-io/chat-langchain-sdk` - docs pages "Stream Chat AI SDK" / "Stream Chat LangChain SDK" in the platform's Chat docs. Or the user's own agent that follows the contract below.
- The agent holds a long-lived WebSocket to the channel, so it runs as **its own long-lived process** (the reference server, or `AgentManager` in a long-lived service) - **not** a serverless function or a Next.js route handler.
- The app calls its start / stop endpoints through an **authenticated** route, so anonymous callers cannot start agents on the LLM bill. Allowlist the model / platform on the server - a model picker's value is only a hint.
- Reference backends: `GetStream/chat-ai-samples` `ai-sdk-sample` and `langchain-sample` (both expose `/start-ai-agent`, `/stop-ai-agent`, `/summarize`; READMEs cover run + `.env`).

If it is unclear whether a backend exists, ask one question:

> Do you already have a backend agent that answers in the channel, or should I set one up with Stream's AI SDK (Vercel AI SDK) or LangChain SDK?

## What the agent must send

The app only renders what the agent writes and emits, and it cannot tell when something is missing - it builds and looks subtly wrong. **Always state this contract to the developer**, and when they bring their own backend, ask them to confirm it before wiring the app:

- `ai_generated: true` on the bot's reply when it is **created**. The app's AI-message check (`isMessageAIGenerated` on React / RN, the message resolver on iOS) keys on it; missing -> the answer renders as an **ordinary bubble with no typewriter and no AI markdown** (raw markdown on iOS), and a custom agent that does not skip its own `ai_generated` messages can **answer itself in a loop**.
- **One message, partially updated** as tokens arrive (throttled - batch chunks, do not update per token). A reply posted once, complete, **appears all at once**; one message per chunk floods the list.
- `generating: true` on every partial update, and `generating: false` on the final update **and** on stop and error. iOS (`StreamChatAI`) reads it: missing `true` -> the text **jumps** instead of animating; missing `false` -> the message **never stops "generating"**. The React and React Native SDKs ignore it (their UI keys on `ai_indicator.*`), but set it anyway so one backend serves every client.
- `ai_indicator.update` with `ai_state` (`AI_STATE_THINKING`, `AI_STATE_GENERATING`, `AI_STATE_EXTERNAL_SOURCES`, `AI_STATE_ERROR`) while working, and `ai_indicator.clear` when done. Missing -> **no thinking indicator and no stop button** (both key on these states).
- Honor `ai_indicator.stop` (sent by the app's stop button - `channel.stopAIResponse()` on React / RN, `AIIndicatorStopEvent` on iOS): abort the model call and keep the partial text. Missing -> **stop does nothing**.

Stream's server SDKs and the sample backends already do all of this; a custom backend must do it by hand. **Plain bubbles, text that appears all at once or jumps, a missing stop button, or a message stuck "generating" are almost always this contract, not the app.**

## Check it before debugging app code

After one prompt, read a real bot message:

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"messaging:<channel-id>"},"message_limit":5}' \
  --jq '.channels[0].messages[] | {user: .user.id, ai_generated: (if has("ai_generated") then .ai_generated else .custom.ai_generated end), generating: (if has("generating") then .generating else .custom.generating end), text: (.text // "" | .[0:40])}'
```

`null` for a bot message means the backend is not setting it - fix the agent, and tell the developer. The `ai_indicator.*` events are ephemeral; log them in the app rather than the CLI.

## Rules for every platform

- **Key everything by channel:** start the agent and register tools once per conversation, after the channel is watched (the samples skip it when a watcher's id starts with `ai-bot`) - never on every render, remount, or screen focus. Filter `ai_indicator.*` per channel.
- **Client tools** (the agent asks the app to act - open a screen, fill a form): the server SDK sends a `custom_client_tool_invocation` event on the channel. Listen for it, confirm with the user before any tool that changes data, and validate `args` - they are model output.
