# Stream Flutter - AI assistants, LLM chat, and agentic experiences

Use this runbook when a Flutter request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, thinking indicators, "stop generating", rendering markdown / code / charts from the model, showing the agent's reasoning and tool calls, asking the person before a tool runs (approvals), letting the agent run tools on the device, replies that are interactive UI (generative UI, A2UI), a **voice agent** and what was said to it, or an app built on **Stream Agents**.

Like the rest of this skill, it is a **router, not a copy of the docs**: it picks the pages to fetch, and adds only what the docs do not say. Fetch the pages live and apply them; cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send, the agent-steps format, and the CLI check are shared by every platform and live there. For integrate / new-app requests, run [`setup.md`](setup.md) first.

The Flutter AI docs live under `https://getstream.io/chat/docs/sdk/flutter/ai-components` (index: `https://getstream.io/chat/docs/sdk/flutter/ai-components.md`). The old `.../guides/ai-integrations/...` pages moved there, and their `.md` URLs return 404.

---

## Step 0: Which agent, which packages (decide before any code)

| The agent | The app uses | Read |
|---|---|---|
| **Stream Agents**: an `agents/<name>/` folder synced with `getstream agents`, run on Stream's hosted router (any request that says Stream Agents, "agent folder", `getstream agents`, or builds a new agent with no backend of its own) | `stream_agents_core` + `stream_agents_chat` to sign in, open sessions, ask, stop, approve and run device tools (`stream_agents_rtc` for voice), plus `stream_chat` 10.6.0+ (the client the transport imports) and `stream_chat_flutter_ai` for the views. No backend agent to write | `https://getstream.io/chat/docs/sdk/flutter/ai-components.md` (the quickstart builds exactly this), then "On Stream Agents" below and `getstream docs agents` (`quickstart.md`, `sessions.md`, `responses-create.md`, `auth.md`, `tool-calling-and-dispatch.md`, `generative-ui.md`); the stream skill covers the CLI |
| **An agent of your own** that writes into a Chat channel: Stream's server SDKs (`@stream-io/chat-ai-sdk` for the Vercel AI SDK, `@stream-io/chat-langchain-sdk`) or a custom backend | `stream_chat` + `stream_chat_flutter_ai`, with the docs' channel transport | `.../conversation-state.md` "A transport over a Stream Chat channel", and the shared contract |

When the request doesn't say, and nothing in the project shows a backend agent, take Stream Agents and say so.

**Packages.** Add them with `flutter pub add`, which resolves the current release; the versions below are the minimum. The AI components (and so the app) need **Dart 3.12+ and Flutter 3.44+**: check `flutter --version` and the pubspec's `environment` first.

- `stream_chat_flutter_ai` `^0.2.0` for the views; `stream_chat_flutter_ai_a2ui` `^0.2.0` when the agent writes A2UI (shape F). They depend on no Stream Chat package; the app connects them to the agent.
- `stream_chat_flutter` (10.6.0+, with the app's other `stream_chat_*` packages on the same version) only for the message-list path (Step 1) or its channel list. Import it with the hide list on `/stream-chat-integration.md`. 10.6.0 is the first `stream_chat` that reads both "checking sources" spellings.
- **From 0.1.x:** the move to 0.2.0 breaks code. Defaults come from `StreamTheme`; a `CodeHighlighter` takes one `CodeHighlightRequest`, and `codeBlockTheme` / `CodeBlockView.theme` replace the code colors; the composer's slot builders (`streamAIComponentBuilders`) replace `ChatComposerFactory`; `AnimatedDots` and `dotCount` are gone; `StreamingMessageView` types only while `expectMoreText` is `true`. Apply the rest from the package `CHANGELOG.md` "Breaking" section and tell the developer. An app on `stream_chat_flutter`'s own AI widgets follows the migration note in `/streaming-messages.md` "Type the reply out".

Where the docs and the code disagree, the source at the resolved version wins (`stream-chat-flutter-ai` `packages/stream_chat_flutter_ai` and `_a2ui`; `Vision-Agents` `sdks/dart/core`, `chat`, `rtc`; the pub-cache checkout, see [`docs-map.md`](docs-map.md) "When the docs fall short") - say so.

## Step 1: Classify, then fetch

| Shape | Signals | Fetch (prefix `https://getstream.io/chat/docs/sdk/flutter/ai-components`) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one person + one assistant, conversation drawer, suggestion chips, big prompt composer | `https://getstream.io/chat/docs/sdk/flutter/ai-components.md` (quickstart), `/conversation-view.md`, `/conversation-state.md`; `/use-cases/personal-assistant.md` for a conversation list, device tools and a voice mode |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | people and a bot in channels the app already renders with `stream_chat_flutter` | `/stream-chat-integration.md` and `/conversation-state.md` "What your backend sends"; `/use-cases/customer-support-agent.md` for a support agent on Stream Agents |
| **C. Agent that shows its work and asks first** (reasoning, tool calls, "ask before it books / shares / deletes") | approvals, tool use, sign-ins to a provider, transparency | A or B, plus `/reasoning-and-tool-calls.md` and the contract's "Agent steps" |
| **D. Agent acts on the device** (read location, the calendar, open a screen, copy to clipboard) | "the assistant should do X on the phone" | A or B, plus `/reasoning-and-tool-calls.md` "Tools on the device" (`AIClientToolRunner`; on Stream Agents, `AgentTool`) |
| **E. Voice agent** (the person talks to an agent on a call; the app shows its state and what was said) | "voice agent", "talk to the assistant", a glow or wave while it speaks, "transcript", history of voice sessions | `/use-cases/voice-agent.md`, `/voice-visualizations.md`, `/conversation-view.md`, and "Shape E" below; on Stream Agents also `sessions.md` "Voice" in `getstream docs agents` |
| **F. Replies that are UI** (generative UI, A2UI, "the agent shows cards / a form") | interactive replies, components the agent places | `/generative-ui.md`, `generative-ui.md` in `getstream docs agents` on Stream Agents, and "Generative UI" below |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | Stream Agents (Step 0), or `/stream-chat-ai-sdk.md` (Vercel AI SDK) / `/stream-chat-langchain-sdk.md` - and check whether it writes agent steps (contract) |

A shape here takes up to five Flutter AI pages, plus the setup pages and, on Stream Agents, the Agents docs pages Step 0 names; that is this runbook's page budget.

Decisions the docs leave to you:

- **Show the conversation with `AIConversationView`, driven by one `AIConversation`.** It is the primary way to show one person's conversation with an agent: shapes A, E and F, and C / D on top of A. Thinking, a message on its way, older messages, approvals, sign-ins, stop and reply actions are built in; errors are yours to show, in the `footer` with a retry (`/conversation-state.md` "Show what the agent is doing and errors").
- **The alternative is the `stream_chat_flutter` message list with AI rows** (`/stream-chat-integration.md`). Take it when the conversation needs what a messenger has (reactions, threads, read state, several people), or the app already shows that channel with the UI kit (shape B).
- **Never a hand-built list** of bubbles on the low-level client ([`custom-ui.md`](custom-ui.md)), for a typed chat or a voice agent's transcript. Tell the developer which of the two you used and why.
- **The list of conversations.** On Stream Agents each conversation is a session: list them with `sessions.query` / `search` (`/use-cases/personal-assistant.md`). With an agent of your own, the app creates each conversation as a `messaging` channel (the app can't create `agent`-type channels; [`RULES.md`](RULES.md) "Permissions") with the person as a member and a custom field that marks it (for example `ai_assistant: true`), watches it, starts the agent, then sends the first message. List `Filter.and([Filter.in_('members', [me]), Filter.equal('ai_assistant', true)])`, and leave them out of the app's other channel lists with `Filter.notExists('ai_assistant')` (`Filter.notEqual` on a custom field the channel doesn't have fails). With one fixed bot id, filter on two members instead: `Filter.and([Filter.in_('members', [me]), Filter.in_('members', [agentId])])` - one `Filter.in_('members', [me, agentId])` matches channels with *either* member.

## Step 2: Wire the components (what the docs leave out)

1. **The conversation.** Keep one `AIConversation` per open conversation, made outside `build` (a `late final` field of the screen's `State`) and disposed with it; give it to `AIConversationView.conversation` and `ChatComposer.conversation`. Its transport is the quickstart's `AgentTransport` on Stream Agents (below), or the channel transport from `/conversation-state.md` for an agent of your own.
2. **The message-list path.** Keep the app's existing `messageBuilder` cases and add the AI branch. For every other message return `StreamMessageItem.fromProps(key: ValueKey(message.id), props: defaultProps)`: it keeps the default row and any `messageItem` override from the component factory ([`design-matching.md`](design-matching.md) "Slot-override recursion trap"), where the page's `DefaultStreamMessageItem` skips that override. Keep the app's `StreamMessageComposer` (the people in the channel need its attachments and commands), with the indicator and a Stop button in a status row above it. Register the AI builders in the same `StreamChat(componentBuilders:)` as the Chat ones, as the page shows.
3. **Approvals.** Pass an `AIToolApprover` as `AIConversation(approver:)` and dispose it with the conversation. With an agent of your own, `decide` posts `{tool_call_id, decision}` (plus `client_id` when the call names an install) to an authenticated backend route, which checks the caller and updates the step.
4. **Device tools with an agent of your own.** Pick by what the tool returns. A tool whose result the model needs runs from agent steps: the backend writes an `ai_tool_call` step for it (Stream's AI SDK and LangChain SDK don't; the backend adds that), and the app runs it with `AIClientToolRunner`. A fire-and-forget action (open a screen, fill a form) can take the SDKs' `custom_client_tool_invocation` event instead: handle it with the package's `AIToolRegistry` (in the source, not the docs), and confirm with the person before anything that changes data. For the runner: read `AIClientIdentity.installId()` once per sign-in, before the runner and approver, and use that value for both and as `client_id` on every message. Create the runner once, outside `build`, and call `runner.handle(parts)` for every agent reply from `channel.state!.messagesStream`, including the replies loaded when the conversation opens. Request the OS permission inside the tool and add its platform keys (a location tool: `NSLocationWhenInUseUsageDescription`, `ACCESS_COARSE_LOCATION`). In a channel with several people, every member sees a step's summary and arguments: keep personal data out of them.
5. **Stop.** With `AIConversation`, the composer's stop button calls the transport's `stop()`. On the message-list path, follow `/stream-chat-integration.md` "Stopping generation" (Stop stays on until `onFinished`), and also turn it off on `ai_indicator.clear` when the reply's row isn't built (scrolled away), or it stays on.

## On Stream Agents

The router runs the agent, writes the conversation into the session's channel, and writes every field of the contract. The app opens sessions and renders them.

- **Client.** One `StreamAgents(apiKey:, userId:, token:)` per signed-in user, created once. `token` is a function the SDK calls before every request and socket handshake: cache in it, and fetch from the developer's backend in production. For development, return a CLI token (`getstream token <user_id> --ttl 2h`). The same token signs in Chat and Video. When the app already has a connected `StreamChatClient` or `StreamVideo` for that user, hand them over with `agents.useChat(client)` / `agents.useVideo(video)` before the first session, or the SDK opens second connections. `withUser` switches the user; `disconnect()` and `close()` tear down.
- **Ask the session, never the channel.** `session.responses.create(text)` asks; the agent doesn't answer a message sent with `channel.sendMessage`. One response runs at a time: a second one fails with "a response is already running" - queue and retry it. Photos go as data URIs in `images:` (`/use-cases/personal-assistant.md` "Send photos").
- **The transport.** Use the quickstart's `AgentTransport` and add what it leaves out:
  - **Reasoning:** a stored reasoning step keeps only its opening. Keep one `LiveReasoning` (`stream_agents_chat`) per conversation, `read` the message of every `message.updated` event from the client into it (not the channel's message list, which folds updates together), and return `reasoning[(message: message.id, step: step.id)]` from the message's `reasoningText`, so reasoning shows in full.
  - **Older messages:** implement `loadOlderMessages` as the channel transport on `/conversation-state.md` does, on the session's channel.
- **Opening.** `agents.agent(name).chat(options)` creates and starts a new session. For a new conversation, open it in the transport's first `send` (then `session.chat()`, `watch()` and `responses.create`) rather than when the screen opens, or the list fills with empty conversations; the docs open it eagerly, which is fine for a single-conversation screen. `agents.attach(id, tools:)` carries an old one on: pass the tools again, since a reopened session has none. `session.close()` ends it and keeps its history - close the previous one when another opens. A new session whose first question fails stays listed as an empty conversation: delete it with `session.delete()`.
- **Approvals.** `decide` is `session.decide(call.id, allowed: decision == AIToolApprovalDecision.allowed)` (the quickstart's `approver()`). A sign-in to a connector needs an `AIToolAuthorizer`, `returnUrl` on the app's own scheme, and `session.declineLogin` (`/reasoning-and-tool-calls.md` "Tool sign-ins").
- **Device tools.** `AgentTool`s in `SessionOptions(tools:)`, run over the session socket. Give each a `displayTitle`. A tool that asks first (`approval: ToolApproval(...)`) keeps the default executor: its question writes the step, and the router can ask a client tool only once it knows the install. Declare every other device tool `executor: ToolExecutor.client`, or it runs with no step on the reply. `run` gets only the arguments. In a typed chat only the app's own session tools can ask first: a tool registered on the server (`agent.tools`) runs where a dispatch worker hosts it, and its approval is never answered.
- **Check the channel.** The conversation is in an `agent:<session id>` channel: run the contract's `agent` channel check after one prompt. A missing field there is a router problem to report, not app code to add.

## Step 3: State the contract, leave a tripwire (an agent of your own)

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer - `ai_generated` picks the AI row, `generating` drives `isGenerating` and `expectMoreText`, and the agent-steps attachments are what `AIMessagePartsView` renders - and run its CLI check before debugging Dart code. Then leave a debug-only tripwire where you decide whether a message is AI-generated (your `AIMessage` type, or the AI branch of `messageBuilder`), so a missing `ai_generated` shows in the console instead of as a plain bubble or a reply drawn as the person's. It logs each message once and matches your bot's user id (the default prefix is the reference backends' `ai-bot-<channel id>`; pass your own):

```dart
import 'package:flutter/foundation.dart';

final _warned = <String>{};

bool isAIReply(Message message, {String agentIdPrefix = 'ai-bot-'}) {
  final ai = message.extraData['ai_generated'] == true;
  if (kDebugMode && !ai && (message.user?.id.startsWith(agentIdPrefix) ?? false) && _warned.add(message.id)) {
    debugPrint('[AI] Agent message ${message.id} has no ai_generated: true - the backend agent must set it.');
  }
  return ai;
}
```

## Generative UI (shape F)

The agent writes a reply's UI (A2UI), the backend moves it into the message's `ai_ui` custom field, and `AIConversationView.conversation(conversation:, ui:)` shows it in place of the text. Fetch `/generative-ui.md` (and the Agents `generative-ui.md` on Stream Agents). What they leave out:

- **One `AIUIHost` per conversation**, kept as long as the conversation shows (next to its `AIConversation`), so a form keeps what the person typed. Your `AIMessage` returns `uiDocument` (`AIUIDocument.fromCustomData(message.extraData)`), or no reply shows UI. Pass `onError` to the renderer and check one real reply: invalid A2UI (an unknown component, a missing argument) shows as an empty reply. If the agent's replies come out that way, give it a stronger model in `agent.yaml`.
- **On Stream Agents, the host's `send` asks the session:** `session.responses.create(action.label, uiAction: action.toJson())`. The Flutter page's `channel.sendMessage(... action.toCustomData())` is for an agent of your own. Catch the error in `send` to tell the person asking failed.
- **Tell the agent what the app shows.** The model writes only the UI the agent's instructions describe. On Stream Agents they are files synced with the CLI: generate them from the host's `ui.capabilities` in a `flutter test` that writes them between two marker lines in the agent's `instructions.md` (so a re-run replaces only that block), run `getstream agents sync <name>`, and re-run it whenever a component changes. Give the renderer only the components the agent uses (`A2UICatalog.basic.removing(...)`): the model reads the whole catalog every turn.
- **A2UI ships; other formats need a renderer of your own.** There is no OpenUI renderer for Flutter: a reply in a format with no renderer shows its text. Say so, and suggest the agent write A2UI; write an `AIUIRenderer` (`/generative-ui.md` "Write a renderer") only when the developer asks for one.
- **No generative UI on a call.** While voice is on, show the conversation without `ui`, and say in `instructions.md` that the agent answers in words on a call.

## Shape E: a voice agent

The person talks to an agent on a Stream Video call, and the app shows the agent's state (a glow or a wave) and what was said, during the call or after it. Show what was said with `AIConversationView`. **Check the fit first**, and tell the developer which way you went:

| The request | Use |
|---|---|
| One person and one agent, shown as a running conversation | `AIConversationView` |
| Subtitles over the call: a line or two that follow the voice and fade | A caption band from the closed-captions page ([`docs-map.md`](docs-map.md) "Closed captions / transcription") |
| A meeting with several people, with or without an agent | Not this view: it starts a turn at each `AIMessageRole.user` message and draws every other role as the agent. Use the `stream_chat_flutter` message list when the transcript is in a Chat channel |
| People and a bot chatting in the same channels | Shape B |

**On Stream Agents** (`stream_agents_rtc`): fetch `/use-cases/voice-agent.md`. `VoiceSession.start(agents, agent:)` starts the agent on a call and `voice.join()` joins from the phone; `join()` doesn't throw, its failure is in `voice.state.value.failure`. The transcript is the session's channel, through the `AgentTransport` and an `AIConversation`: it keeps the greeting and `say()` lines, which the use case's `voice.session.conversation` turns (`TurnMessage`) leave out, and stays as history. An approval on a call is `session.approvals` with `AIToolApprovalCard`. `stream_agents_rtc` brings `stream_video_flutter`, so [`RULES.md`](RULES.md) "Video -> Build blockers" and the call permissions on the use-case page apply. A **voice mode inside a chat** (`/use-cases/personal-assistant.md` "Talk instead of typing"):

- Keep the chat's session started for the whole call: its socket runs the phone's tools. `session.startVoice()`, then `VoiceSession.attach(agents, session.id)`; on hang-up `leave()`, then `session.stopVoice()`. `voice.end()` ends the whole session, chat included.
- One `AIConversation` per conversation, shared by the chat and the call screen. The use case's `VoiceCallScreen` takes the session's turns, so the call screen here is your own, given the chat's conversation; what was said then stays in the chat's history. A second conversation made for the call can leave one of the two screens empty.
- No composer and no generative UI while voice is on: a typed turn in a voice session isn't marked finished, so the next question is refused.

**With a voice agent of your own** (OpenAI Realtime, or the developer's own agent on the call), map each source to one `AIMessage` type, and tell the developer where the transcript lives:

- **A Chat channel the agent writes** - the history stays after the call and on other devices. Wrap its messages as `/conversation-view.md` "Messages from Stream Chat" shows, with `role` from the sender (the signed-in user's id -> `AIMessageRole.user`, anyone else -> `.assistant`): a transcript writer may not set `ai_generated`. The person must be a member of the channel, or reading it fails with a permission error.
- **Closed captions** (no Chat needed) - the transcript lives in the screen's memory. `call.closedCaptions` keeps only the latest few captions for a moment: right for subtitles, lossy for a transcript. Listen with `call.callEvents.on<StreamCallClosedCaptionsEvent>(...)` for as long as the call runs, turn each into `StreamClosedCaption.fromEvent(event)`, skip repeats (same `speakerId` and `startTime`), and join consecutive captions from the same speaker into one message. Captions must be on for the call type (`auto-on`, or `call.startClosedCaptions()` with the `start-closed-captions-call` permission). They arrive as finished segments, so the agent's lines show whole. The backend contract does not apply to this path.

Either way: keep each line's `id` stable across updates (a message id, or the speaker plus the first caption's start time), or the row rebuilds and the list loses its place. Put the call controls and the agent's `AIVoiceGlowView` / `AIVoiceWaveView` below the list, mapped from the agent's participant: not in the call yet -> `connecting`, agent `isSpeaking` -> `speaking`, the person speaking -> `listening`, otherwise `idle`, with the agent's `audioLevel`. On Stream Agents, map as `/use-cases/voice-agent.md` "Show what the agent is doing" does instead, which takes `thinking` from the session's state. With Chat in the same app too, alias the imports ([`video-patterns.md`](video-patterns.md) "Chat + Video in one app").

---

## Pitfalls the docs do not shout about

- **`extraData` values are whatever JSON delivered.** Compare with `== true`; do not cast blind, and do not assume the key exists on older messages.
- **Watch a channel before sending to it.** `channel.sendMessage` throws a `StateError` until the channel is watched (or queried) - for a channel the backend created, `await channel.watch()` first.
- **`ChatComposer` is not `StreamMessageComposer`.** It is a standalone AI composer with its own controller; the Chat composer's attachment upload, commands and slow mode are not in it.
- **`LiveValue`s start with a value.** Give each `StreamBuilder` over one `initialData: value.value`, or the first frame has no data.
- **Permissions:** the composer's dictation and photos need the keys on `/composer.md` "Permissions"; a call and a device tool need their own.
- **Local backend:** the iOS simulator reaches `localhost`; the Android emulator reaches the host as `10.0.2.2` (or `adb reverse tcp:<port> tcp:<port>`); a physical device needs the machine's LAN IP or a tunnel. Android 9+ refuses plain `http://`, so allow it for debug builds only with `android:usesCleartextTraffic="true"` on `<application>` in `android/app/src/debug/AndroidManifest.xml`. Keep the URLs in config.
- **No provider key in the app.** The agent runs on a backend or on Stream; the app starts and stops it through an authenticated route, or opens a Stream Agents session with the user's token ([`RULES.md`](RULES.md) "Secrets and auth"). The reference backends' start / stop routes accept anyone: tell the developer to add the check before shipping.

## Verify before stopping

- `pubspec.lock` shows `stream_chat_flutter_ai` 0.2.x (and `_a2ui` for generative UI), `stream_chat_flutter` at 10.6.0+ if present, and on Stream Agents the `stream_agents_*` packages; the developer was told which versions and which path were taken
- a prompt gets a streamed, markdown-rendered answer; "Thinking" shows until the first token; the stop button shows while the reply generates, and stop keeps the partial answer
- with agent steps: reasoning folds into "Thought for Ns" (in full on Stream Agents); each tool call shows its title and status; an approval shows on the person's device only, allow continues the call and decline shows declined; a device tool call runs once and its step completes (on Stream Agents, no step on a tool without an approval means it isn't `ToolExecutor.client`)
- the contract CLI check (the `agent` channel on Stream Agents) shows `ai_generated: true`, a final `generating: false`, and any `ai_reasoning` / `ai_tool_call` attachments - and, with an agent of your own, the developer was told the contract
- the developer was told the conversation renders with `AIConversationView`, or why the message-list path was taken; on that path the app's existing `messageBuilder` cases still render
- generative UI: the agent's instructions were generated from the app's components (and synced), a reply shows its UI in place of its text, a tap asks the agent and gets an answer, and on a call replies show their words
- shape E: the person's lines are their bubbles and the agent's are full-width Markdown (a line on the wrong side means the role check uses the wrong field); every line stays after the captions fade; the glow follows the agent's voice; the developer was told where the transcript lives
- `flutter analyze` is clean and no Stream secret or LLM provider key is in the app
