# Stream Flutter - AI assistants, LLM chat, and agentic experiences

Use this runbook when a Flutter request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, thinking indicators, "stop generating", rendering markdown / code / charts from the model, showing the agent's reasoning and tool calls, asking the person before a tool runs (approvals), letting the agent run tools on the device, or an app built on **Stream Agents** (Vision Agents) - a text session or a voice agent on a call.

Like the rest of this skill, it is a **router, not a copy of the docs**: it picks the pages to fetch, and adds only what the docs do not say. Fetch the pages live and apply them; cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send (`ai_generated`, `generating`, `ai_indicator.*`, the agent-steps format for reasoning / tool calls / approvals), and the CLI check are shared by every platform and live there. For integrate / new-app requests, run [`setup.md`](setup.md) first.

---

## Step 0: Install `stream_chat_flutter_ai` (before any code)

`stream_chat_flutter_ai` is the AI component library. It has **no dependency on Stream Chat** - it renders text and steps and collects input; the app connects it to a channel. Add `stream_chat_flutter_ai: ^0.2.0` with `flutter pub add`. It needs **Dart 3.11+ and Flutter 3.41+**: check `flutter --version` and the pubspec's `environment` first. An app on 0.1.x moves to `^0.2.0` and applies the breaking changes in the package `CHANGELOG.md` (`StreamingMessageView` types only while `expectMoreText` is `true`; `codeBlockTheme` replaces the code colors; a `CodeHighlighter` takes one `CodeHighlightRequest`, so a highlighter copied from older docs or samples needs updating) - tell the developer.

**Which Chat package:** `AIConversationView` needs only `stream_chat` (the client) underneath. Add `stream_chat_flutter` when the app also shows Chat UI - a conversation drawer built on its channel list, or messenger screens (shape B).

**With the Chat UI kit:** `stream_chat_flutter` must resolve to **10.6.0+** (which needs Flutter 3.44+). The AI package's `share_plus` needs 10.5+, and 10.6.0 is the first `stream_chat` that decodes the reference agents' `AI_STATE_EXTERNAL_SOURCES` as `AITypingState.checkingSources` (older versions read it as `idle`, so the indicator vanishes during tool calls). `stream_chat_flutter` ships older copies of some AI widgets: import it with `hide StreamingMessageView, AITypingIndicatorView, AnimatedDots, TypewriterState, TypewriterValue, TypewriterController, TypewriterWidgetBuilder` (the Stream Chat integration page).

Where the docs stop, the package `README.md` and source at the resolved version are the reference ([`docs-map.md`](docs-map.md) "When the docs fall short") - say where a pattern came from.

## Step 1: Classify, then fetch

| Shape | Signals | Fetch (prefix `https://getstream.io/chat/docs/sdk/flutter/guides/ai-integrations`) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one person + one assistant, conversation drawer, suggestion chips, big prompt composer | `.md` (components, install, permissions, "Best practices": `ai_generated`, indicator events, stop, ephemeral updates), then the package README "Conversations: `AIConversationView`" and "Using with Stream Chat" |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | people and a bot in channels the app already renders with `stream_chat_flutter` | `/stream-chat-integration.md` and the `.md` "Best practices" section |
| **C. Agent that shows its work and asks first** (reasoning, tool calls, "ask before it books / shares / deletes") | approvals, tool use, transparency | A or B, plus the README "Agent steps", "Tool approvals" and "Tool sign-ins" sections, and the contract's "Agent steps" |
| **D. Agent acts on the device** (read location, open a screen, copy to clipboard) | "the assistant should do X on the phone" | A or B, plus `/client-side-tools.md` for agents that send `custom_client_tool_invocation` events (Stream's AI SDK / LangChain SDK), or the README "`AIClientToolRunner`" for agents that write `ai_tool_call` steps |
| **E. Stream Agents app** (Vision Agents: a text session, or a voice agent on a Stream Video call) | "Stream Agents", "Vision Agents", `getstream agents`, voice agent, "talk to the agent" | `getstream docs agents/flutter` (agent folder, sessions, voice, tools), then "Shape E" below |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | `/stream-chat-ai-sdk.md` (Vercel AI SDK) or `/stream-chat-langchain-sdk.md` - and check whether it writes agent steps (contract) |

Decisions the docs leave to you:

- **Show the conversation with `AIConversationView`.** It is the primary way to show one person's conversation with an agent: shapes A and E, and C / D on top of A. Each question moves to the top while its reply writes out below it; thinking, a message on its way, older messages, approvals and reply actions are built in.
- **The alternative is the `stream_chat_flutter` message list with AI rows** (`/stream-chat-integration.md`): `messageBuilder` returns the AI row for messages with `ai_generated` and `DefaultStreamMessageItem(props: defaultProps)` for every other message, so the default rows keep their avatars, reactions, threads and status ([`RULES.md`](RULES.md) "Design fidelity"). Take it when the conversation needs what a messenger has (reactions, threads, read state, several people), or the app already shows that channel with the UI kit (shape B). Keep the app's existing `messageBuilder` logic and add the AI branch to it, keep its `StreamMessageComposer` (the people in the channel need its attachments and commands), and put a Stop button next to the indicator.
- **An assistant screen in an app that already lists channels.** Assistant conversations are channels too: keep them out of the app's existing channel list (a `type` or custom-field filter) and open them on the assistant screen. The reference backends work on channels the app creates (`messaging`); an `agent`-type channel is created by the server ([`RULES.md`](RULES.md) "Permissions"), as Stream Agents does - follow what the backend does.
- **Never a hand-built list** of bubbles on the low-level client ([`custom-ui.md`](custom-ui.md)), for a typed chat or a voice agent's transcript. Tell the developer which of the two you used and why.

## Step 2: Wire the components (what the docs leave out)

1. **The conversation (`AIConversationView`).** Mix `AIMessage` into a wrapper over `stream_chat`'s `Message`: `id`, `role` (`AIMessageRole.assistant` when `extraData['ai_generated'] == true`, else `.user`), `text`, `isGenerating` (`extraData['generating'] == true`) and `parts`. `channel.state.messages` is already oldest first - pass it in that order. Build `parts` with `AIMessagePart.parseAll` over each attachment's `rawType` and `{'id': attachment.id, ...attachment.extraData}` (the README's "Using with Stream Chat": `type` can be rewritten, and the step id must win). Drive `isThinking` from the indicator state, pass what was just sent as `pendingMessage` (`AIPendingMessage`) until its copy arrives, and page with `loadOlderMessages` (`channel.query(messagesPagination: PaginationParams(lessThan: firstId, limit: n))`). On a failed reply, stop passing `isThinking` and show the error in `footer`.
2. **Create once, outside `build`:** the `AIComponentBuilders` (in a `late final` field, wrapped around the view with `AIComponentFactory`), the `AIToolApprover`, the `AIClientToolRunner` and `onAttachmentTap`. New instances rebuild every row on each streamed chunk. Builders that show your own state (a rating) read it through a `Listenable`.
3. **Indicator and stop.** Listen on the `Channel` (`channel.on(EventType.aiIndicatorUpdate, ...)`), which is already scoped to the conversation. Drive `ChatComposerController.isGenerating` (or your Stop button) from the events and the latest reply's `generating`, and keep it on until the reply is on screen - the backend usually finishes before the typewriter does. Under `AIConversationView`, which draws its own rows, keep it on while the latest reply `isGenerating`. In rows you draw yourself, turn it off from `StreamingMessageView.onFinished`. Stop is `channel.stopAIResponse()`.
4. **Approvals.** One `AIToolApprover(identity: AIClientIdentity(userId: ...), decide: ...)` per signed-in user, created once; add `clientId: installId` when the app also runs device tools. `decide` posts `{tool_call_id, client_id, allowed}` to an authenticated backend endpoint, which checks the caller and updates the step. `dispose` it with the screen.
5. **Device tools (`ai_tool_call` steps).** Register `runner.registrations` with the backend and send a stable install id as `client_id` in the custom data of every message: with the UI kit, `StreamMessageComposer(preMessageSending: (m) => m.copyWith(extraData: {...m.extraData, 'client_id': installId}))`; with `ChatComposer`, in the `Message` you send from `onSendPressed`. Call `runner.handle(parts)` from `channel.state!.messagesStream` - for every AI reply, including those already loaded when the conversation opens - never from `build`; it runs each call id once. Keep one runner per conversation and make the result endpoint idempotent on `tool_call_id`. For `custom_client_tool_invocation` events, merge `cid` and `message_id` into the map you pass `AIToolInvocation.tryParse` (the README shows it).

## Step 3: State the contract, leave a tripwire

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer - `ai_generated` picks the AI row, `generating` drives `isGenerating` and `expectMoreText`, and the agent-steps attachments are what `AIMessagePartsView` renders - and run its CLI check before debugging Dart code. Then leave a debug-only tripwire where you decide whether a message is AI-generated, so a missing `ai_generated` shows in the console instead of as a plain bubble (match your agent's user id):

```dart
bool isAIReply(Message message, {required String agentUserId}) {
  final ai = message.extraData['ai_generated'] == true;
  if (kDebugMode && !ai && message.user?.id == agentUserId) {
    debugPrint('[AI] Agent message ${message.id} has no ai_generated: true - the backend agent must set it.');
  }
  return ai;
}
```

## Shape E: a Stream Agents app (text session or voice agent)

The agent runs on Stream (configured from its `agents/<name>/` folder with `getstream agents`), and the app talks to it through the Stream Agents Dart SDK: `vision_agents_core` (the client and its sessions), `vision_agents_chat` (a session's Stream Chat channel) and `vision_agents_rtc` (its Stream Video call). Install and set them up from `getstream docs agents/flutter` (sessions, voice, tools, auth), and add only these three. The conversation and the agent's voice state always render with `stream_chat_flutter_ai` - also when the request names another conversation widget; tell the developer why (streamed markdown, steps, approvals, stop, history). From `vision_agents_rtc`, `AgentVideoView` renders a video session's camera and the agent's track, and `VoiceCallView` is ready-made call controls (mute, camera, hang up) that join the call when first built - request the microphone before showing it. The backend contract's message fields (`ai_generated`, `generating`, agent steps) apply; its backend-side parts (where the agent runs, start / stop routes) do not - Stream runs the agent. Wire it through the session, not the channel:

- **Client.** Create one `VisionAgents(apiKey:, userId:, token:)` next to the app's `StreamChatClient`. When the app already has a connected client, hand it over once with `agents.useChat(client)` (connected as the same user) so sessions open on it instead of a second connection.
- **Text session.** `agents.agent(name).chat(...)` starts the session; `session.chat()` (from `vision_agents_chat`) opens its channel, the transcript: watch it and wrap its messages as in Step 2 (the agent's replies carry `ai_generated`). **Ask through the session** (`session.responses.create(text)`), not `channel.sendMessage` - the agent does not answer messages sent to the channel. Stop is `session.interrupt()`, approvals answer with `session.decide(...)` from the `AIToolApprover`, and device tools are `AgentTool`s in the session's options rather than an `AIClientToolRunner`. The session's state drives `isThinking`. The channel stores only the opening of each reasoning step: feed the client's `message.updated` events for this channel into `vision_agents_chat`'s `LiveReasoning` and return its text from `AIMessage.reasoningText`, so reasoning shows in full.
- **Voice session.** The agent joins a Stream Video call with the person, and the session's channel is the transcript for voice too: render it with `AIConversationView` (not a transcript built from session events), with no composer while the call is on - a typed turn during a call is refused. Show the agent with `AIVoiceGlowView` / `AIVoiceWaveView`: speaking and `audioLevel` come from the call's participants (`isSpeaking`, `audioLevel`), listening and thinking from the session's state, mapped to `AIVoiceAgentState`; the session's state drives `isThinking` here too. Ask for the microphone before joining on Android. `vision_agents_rtc` brings in `stream_video_flutter`, so [`RULES.md`](RULES.md) "Video -> Build blockers" applies.
- **Tokens and channels.** Stream Agents refuses a user token without an expiry: `getstream token <user> --ttl <duration>` for development, the backend in production. The SDK calls the `token:` function again when the token expires, so a static development token must outlast the session; the app's own Chat connection then needs a token provider too ([`RULES.md`](RULES.md) "Authenticate once"). Session channels are `agent`-type (the router creates them): keep them out of the app's other channel lists (`Filter.notEqual('type', 'agent')`), and run the contract's CLI check on the session's own cid.

### A voice agent's transcript as a conversation (not on Stream Agents)

For another voice agent on a Stream Video call (OpenAI Realtime, your own agent), check the fit first and tell the developer which way you went:

| The request | Use |
|---|---|
| One person and one agent, shown as a running conversation | `AIConversationView` over your own `AIMessage` type |
| Subtitles over the call: a line or two that follow the voice and fade | A caption band from the closed-captions page ([`docs-map.md`](docs-map.md) "Closed captions / transcription") |
| A meeting with several people, with or without an agent | Not this view: it starts a turn at each `AIMessageRole.user` message and draws every other role as the agent. Use the `stream_chat_flutter` message list when the transcript is in a Chat channel |
| People and a bot chatting in the same channels | Shape B |

`call.closedCaptions` keeps only the latest captions for a moment (2 captions, 2.7 s by default in `CallPreferences`): right for subtitles, lossy for a transcript. Instead, listen to `call.callEvents` for `StreamCallClosedCaptionsEvent` for as long as the call runs and turn each into `StreamClosedCaption.fromEvent(event)`. Skip repeats (same `speakerId` and `startTime`), join consecutive captions from the same speaker into one message, map the person's own `user.id` to `AIMessageRole.user` and any other to `.assistant`, and keep each line's `id` stable across updates. Captions must be on for the call (`call.startClosedCaptions()`, or `auto-on` on the call type); they arrive as finished segments, so the agent's lines show whole rather than typed out.

---

## Pitfalls the docs do not shout about

- **`extraData` values are whatever JSON delivered.** Compare with `== true`; do not cast blind, and do not assume the key exists on older messages.
- **Streamed chunks are message updates.** Use `rawType` for step attachments (`type` can turn into a link preview), and require the backend to set `id` on every step - otherwise each update gets a new random attachment id and the step starts over.
- **Watch a channel before sending to it.** `channel.sendMessage` throws a `StateError` until the channel is watched (or queried) - for a channel the backend created, `await channel.watch()` first.
- **`ChatComposer` is not `StreamMessageComposer`.** It is a standalone AI composer with its own controller; attachments, commands and slow mode from the Chat composer are not in it.
- **Permissions:** speech-to-text needs `NSMicrophoneUsageDescription` + `NSSpeechRecognitionUsageDescription` (iOS) and `RECORD_AUDIO` (Android); the photo / camera inputs need their usage descriptions too (the overview page's "Platform requirements"). A location tool needs its own.
- **Local backend:** the iOS simulator reaches `localhost`, the Android emulator reaches the host as `10.0.2.2`, a physical device needs the machine's LAN IP or a tunnel. Keep the agent URL in config.
- **No provider key in the app.** The agent runs on a backend; the app starts and stops it through an authenticated endpoint ([`RULES.md`](RULES.md) "Secrets and auth"). The reference backends' start / stop routes accept anyone: tell the developer to add the check (the user's Stream token as a Bearer header works) before shipping.

## Verify before stopping

- `pubspec.lock` shows `stream_chat_flutter_ai` 0.2.x, and `stream_chat_flutter` (if present) at 10.6.0+
- a prompt gets a streamed, markdown-rendered answer from the agent; "Thinking" shows until the first token; the stop button shows while the reply types and stop keeps the partial answer
- with agent steps: reasoning folds into "Thought for Ns"; each tool call shows its title and status; an approval shows on the person's device only, allow continues the call and decline shows declined; a device tool call runs once
- the contract CLI check shows `ai_generated: true`, a final `generating: false`, and any `ai_reasoning` / `ai_tool_call` attachments - and the developer was told the contract
- shape B: the app's existing `messageBuilder` cases still render, and non-AI messages use the default row
- shape E: questions, stop and approvals go through the session; reasoning shows in full; on a call the transcript renders from the session channel with no composer, the glow follows the agent, and stop / hang-up work
- `flutter analyze` is clean and no Stream secret or LLM provider key is in the app
