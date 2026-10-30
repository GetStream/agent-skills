# Stream Flutter - AI assistants, LLM chat, and agentic experiences

Use this runbook when a Flutter request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, thinking indicators, "stop generating", rendering markdown / code / charts from the model, showing the agent's reasoning and tool calls, asking the person before a tool runs (approvals), letting the agent run tools on the device, or an app built on **Stream Agents** (Vision Agents) - a text session or a voice agent on a call.

Like the rest of this skill, it is a **router, not a copy of the docs**: it picks the pages to fetch, and adds only what the docs do not say. Fetch the pages live and apply them; cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send (`ai_generated`, `generating`, `ai_indicator.*`, the agent-steps format for reasoning / tool calls / approvals), and the CLI check are shared by every platform and live there. For integrate / new-app requests, run [`setup.md`](setup.md) first.

---

## Step 0: Which `stream_chat_flutter_ai` (decide before any code)

`stream_chat_flutter_ai` is the AI component library. It has **no dependency on Stream Chat** - it renders text and steps and collects input; the app connects it to a channel. It needs **Dart 3.11+ and Flutter 3.41+**: check `flutter --version` and the pubspec's `environment` before adding it.

**The released version is 0.1.0** (pub.dev): `StreamingMessageView`, `AITypingIndicatorView`, `ChatComposer`, `AISuggestionsView`, `SpeechToTextButton`, `ChartView`, `AIMarkdownBody`, `AIToolRegistry`. The conversation view, agent steps, approvals, the device-tool runner and the voice views (`AIConversationView`, `AIMessagePartsView`, `AIToolApprover`, `AIClientToolRunner`, `AIVoiceGlowView` / `AIVoiceWaveView`) are on the package's `main`, unreleased until 0.2.0, and so are `StreamingMessageView`'s `expectMoreText` and `onFinished` (0.1.0 has `onTypewriterStateChanged`). For those, pin the commit:

```yaml
dependencies:
  stream_chat_flutter_ai:
    git:
      url: https://github.com/GetStream/stream-chat-flutter-ai.git
      ref: e7a0d2a254a5cf9d7bc2a07321a8ebd20523e354
      path: packages/stream_chat_flutter_ai
```

Pick the row and **tell the developer which version you took and why**:

| The app needs | Do |
|---|---|
| A conversation (shape A), agent steps or approvals (C), the device-tool runner (D), or a Stream Agents session (E) | **The git pin above.** Say it is a stopgap until 0.2.0 is on pub.dev. |
| AI replies inside an existing message list (B), client tools over invocation events (D), or a how-to on a 0.1.0 component | **`stream_chat_flutter_ai: ^0.1.0`** from pub.dev. |
| An app already on 0.1.0 that now needs a pinned component | Move to the pin and apply the "Upcoming" breaking changes in the package `CHANGELOG.md` (`StreamingMessageView` types only while `expectMoreText` is `true`; `codeBlockTheme` replaces the code colors). |

**With the Chat UI kit:** `stream_chat_flutter` must resolve to **10.6.0+** (which needs Flutter 3.44+). The pin's `share_plus` needs 10.5+, and 10.6.0 is the first `stream_chat` that decodes the reference agents' `AI_STATE_EXTERNAL_SOURCES` as `AITypingState.checkingSources` (older versions read it as `idle`, so the indicator vanishes during tool calls). `stream_chat_flutter` ships older copies of some AI widgets: import it with `hide StreamingMessageView, AITypingIndicatorView, AnimatedDots, TypewriterState, TypewriterValue, TypewriterController, TypewriterWidgetBuilder` (the Stream Chat integration page).

The docs cover the 0.1.0 surface. For the pinned components, the source and `README.md` of `packages/stream_chat_flutter_ai` at the pinned commit are the reference ([`docs-map.md`](docs-map.md) "When the docs fall short") - say where a pattern came from.

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
- **An assistant screen in an app that already lists channels.** Assistant conversations are channels too: keep them out of the app's existing channel list (a `type` or custom-field filter) and open them on the assistant screen. The reference backends work on channels the app creates (`messaging`); an `agent`-type channel is created by the server ([`RULES.md`](RULES.md) "Permissions") - follow what the backend does.
- **Never a hand-built list** of bubbles on the low-level client ([`custom-ui.md`](custom-ui.md)), for a typed chat or a voice agent's transcript. Tell the developer which of the two you used and why.

## Step 2: Wire the components (what the docs leave out)

1. **The conversation (`AIConversationView`).** Mix `AIMessage` into a wrapper over `stream_chat`'s `Message`: `id`, `role` (`AIMessageRole.assistant` when `extraData['ai_generated'] == true`, else `.user`), `text`, `isGenerating` (`extraData['generating'] == true`) and `parts`. `channel.state.messages` is already oldest first - pass it in that order. Build `parts` with `AIMessagePart.parseAll` over each attachment's `rawType` and `{'id': attachment.id, ...attachment.extraData}` (the README's "Using with Stream Chat": `type` can be rewritten, and the step id must win). Drive `isThinking` from the indicator state, pass what was just sent as `pendingMessage` (`AIPendingMessage`) until its copy arrives, and page with `loadOlderMessages` (`channel.query(messagesPagination: PaginationParams(lessThan: firstId, limit: n))`). On a failed reply, stop passing `isThinking` and show the error in `footer`.
2. **Create once, outside `build`:** the `AIComponentBuilders` (in a `late final` field, wrapped around the view with `AIComponentFactory`), the `AIToolApprover`, the `AIClientToolRunner` and `onAttachmentTap`. New instances rebuild every row on each streamed chunk. Builders that show your own state (a rating) read it through a `Listenable`.
3. **Indicator and stop.** Listen on the `Channel` (`channel.on(EventType.aiIndicatorUpdate, ...)`), which is already scoped to the conversation. Drive `ChatComposerController.isGenerating` (or your Stop button) from the events and the latest reply's `generating`, and keep it on until the reply is on screen - the backend usually finishes before the typewriter does. Under `AIConversationView`, which draws its own rows, keep it on while the latest reply `isGenerating`. In rows you draw yourself, turn it off when the typewriter is done: `StreamingMessageView.onFinished` on the pin, `onTypewriterStateChanged` reaching `idle` on 0.1.0. Stop is `channel.stopAIResponse()`.
4. **Approvals.** One `AIToolApprover(identity: AIClientIdentity(userId: ...), decide: ...)` per signed-in user, created once; add `clientId: installId` when the app also runs device tools. `decide` posts `{tool_call_id, client_id, allowed}` to an authenticated backend endpoint, which checks the caller and updates the step. `dispose` it with the screen.
5. **Device tools (`ai_tool_call` steps).** Register `runner.registrations` with the backend and send a stable install id as `client_id` in the custom data of every message: with the UI kit, `StreamMessageComposer(preMessageSending: (m) => m.copyWith(extraData: {...m.extraData, 'client_id': installId}))`; with `ChatComposer`, in the `Message` you send from `onSendPressed`. Call `runner.handle(parts)` from `channel.state!.messagesStream` - for every AI reply, including those already loaded when the conversation opens - never from `build`; it runs each call id once. Keep one runner per conversation and make the result endpoint idempotent on `tool_call_id`. For `custom_client_tool_invocation` events, merge `cid` and `message_id` into the map you pass `AIToolInvocation.tryParse` (the README shows it).

## Step 3: State the contract, leave a tripwire

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer - `ai_generated` picks the AI row, `generating` drives `isGenerating` (and `expectMoreText` on the pin), and the agent-steps attachments are what `AIMessagePartsView` renders - and run its CLI check before debugging Dart code. Then leave a debug-only tripwire where you decide whether a message is AI-generated, so a missing `ai_generated` shows in the console instead of as a plain bubble (match your agent's user id):

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

The agent runs on Stream (configured from its `agents/<name>/` folder with `getstream agents`), and the app talks to it through the Vision Agents Dart SDK. The SDK has no views: show the session with `stream_chat_flutter_ai`. Until the packages are on pub.dev, add them from the `accelerate` branch of `GetStream/Vision-Agents`, and name the core in your own `dependency_overrides` (pub ignores a dependency's `pubspec_overrides.yaml`):

```yaml
dependencies:
  vision_agents_core:
    git: {url: https://github.com/GetStream/Vision-Agents, ref: accelerate, path: sdks/dart/core}
  vision_agents_chat: # a text session's Stream Chat channel
    git: {url: https://github.com/GetStream/Vision-Agents, ref: accelerate, path: sdks/dart/chat}
  vision_agents_rtc: # a voice session's Stream Video call
    git: {url: https://github.com/GetStream/Vision-Agents, ref: accelerate, path: sdks/dart/rtc}
dependency_overrides:
  vision_agents_core:
    git: {url: https://github.com/GetStream/Vision-Agents, ref: accelerate, path: sdks/dart/core}
```

Tell the developer the branch is a stopgap. Use these three packages only: the SDK's own views package (`vision_agents_ui`) is being removed in favor of `stream_chat_flutter_ai` (Vision-Agents#1327), even where the branch README still shows it. List `stream_chat` / `stream_video_flutter` in your own pubspec as `any` when you import them (`depend_on_referenced_packages`); the Vision Agents packages pin their versions. Read `sdks/dart/README.md` on `accelerate` for setup (`VisionAgents(apiKey:, userId:, token:)`, regions, a local router). The Flutter demo with the wiring - `examples/voice_agents/flutter_demo` (`lib/agent_chat.dart`, `chat_view.dart`, `voice_view.dart`) - is on the `claude/flutter-demo-parity-b6ccd3` branch until #1327 merges.

**In an app already on the Chat UI kit,** add `vision_agents_core` (and `_rtc` for voice) without `vision_agents_chat`: it pins `stream_chat` 10.4.0 exactly, while the pinned AI package needs `stream_chat_flutter` 10.5+, so the two do not resolve together. Open the session's channel on the app's own client instead - that is all `session.chat()` does:

```dart
final cid = session.session.conversationId; // "type:id"
final colon = cid.indexOf(':');
final channel = client.channel(cid.substring(0, colon), id: cid.substring(colon + 1));
```

- **Text session.** `agents.agent(name).chat(SessionOptions(tools: ...))` opens an `AgentSession`; `session.chat()` gives its `stream_chat` `Channel` - watch it and wrap its messages as in Step 2 (the agent's replies carry `ai_generated`; in a one-person session the tripwire's agent is any sender other than the signed-in user). **Ask through the session** (`session.responses.create(text)`), not `channel.sendMessage`: the agent answers the session. Stop is `session.interrupt()`. Approvals: `AIToolApprover(decide: (call, d) => session.decide(call.id, allowed: d == AIToolApprovalDecision.allowed))`. Device tools are `AgentTool`s in `SessionOptions(tools:)`, run over the session's socket - no `AIClientToolRunner` here. `session.state` (`Responding`, `Working(skills)`) drives `isThinking` and a "Working on ..." `AITypingIndicatorView` in the `footer`.
- **Voice session.** `VoiceSession.start(agents, agent: name, options: ...)` then `join()`; `leave()` on hang-up. Map `voice.session.state` (`Listening`, `Responding`, `Working`) to `AIVoiceAgentState` for `AIVoiceGlowView` / `AIVoiceWaveView`, and take `audioLevel` / `isSpeaking` from the call's participants (`voice.call?.state.value.callParticipants`). These are SFU-reported levels, so the glow trails the voice slightly. An approval during a call is an `AIToolApprovalCard` over the controls for each request in `session.approvals`, answered with `session.decide`. Ask for the microphone before `join()` on Android.
- **A voice agent that is not on Stream Agents** (OpenAI Realtime, your own agent): when the app shows what was said as a conversation, accumulate the call's closed captions ([`docs-map.md`](docs-map.md) "Closed captions / transcription") into your own `AIMessage` type and render it with `AIConversationView`. Subtitles over the call stay a caption band.

---

## Pitfalls the docs do not shout about

- **`extraData` values are whatever JSON delivered.** Compare with `== true`; do not cast blind, and do not assume the key exists on older messages.
- **Streamed chunks are message updates.** Use `rawType` for step attachments (`type` can turn into a link preview), and require the backend to set `id` on every step - otherwise each update gets a new random attachment id and the step starts over.
- **`ChatComposer` is not `StreamMessageComposer`.** It is a standalone AI composer with its own controller; attachments, commands and slow mode from the Chat composer are not in it.
- **Permissions:** speech-to-text needs `NSMicrophoneUsageDescription` + `NSSpeechRecognitionUsageDescription` (iOS) and `RECORD_AUDIO` (Android); the photo / camera inputs need their usage descriptions too (the overview page's "Platform requirements"). A location tool needs its own.
- **Local backend:** the iOS simulator reaches `localhost`, the Android emulator reaches the host as `10.0.2.2`, a physical device needs the machine's LAN IP or a tunnel. Keep the agent URL in config.
- **No provider key in the app.** The agent runs on a backend; the app starts and stops it through an authenticated endpoint ([`RULES.md`](RULES.md) "Secrets and auth"). The reference backends' start / stop routes accept anyone: tell the developer to add the check (the user's Stream token as a Bearer header works) before shipping.

## Verify before stopping

- the developer was told which `stream_chat_flutter_ai` was taken (pin or `^0.1.0`) and why; `pubspec.lock` shows it, and `stream_chat_flutter` (if present) at 10.6.0+
- a prompt gets a streamed, markdown-rendered answer from the agent; "Thinking" shows until the first token; the stop button shows while the reply types and stop keeps the partial answer
- with agent steps: reasoning folds into "Thought for Ns"; each tool call shows its title and status; an approval shows on the person's device only, allow continues the call and decline shows declined; a device tool call runs once
- the contract CLI check shows `ai_generated: true`, a final `generating: false`, and any `ai_reasoning` / `ai_tool_call` attachments - and the developer was told the contract
- shape B: the app's existing `messageBuilder` cases still render, and non-AI messages use the default row
- shape E: only `vision_agents_core` / `_chat` / `_rtc` are added (no `_chat` next to the UI kit); questions go through the session; on a call the glow follows the agent and stop / hang-up work
- `flutter analyze` is clean and no Stream secret or LLM provider key is in the app
