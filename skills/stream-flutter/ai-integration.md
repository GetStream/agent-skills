# Stream Flutter - AI assistants, LLM chat, and agentic experiences

Use this runbook when a Flutter request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, thinking indicators, "stop generating", rendering markdown / code / charts from the model, showing the agent's reasoning and tool calls, asking the person before a tool runs (approvals), letting the agent run tools on the device, or showing what was said to a **voice agent** as a conversation.

Like the rest of this skill, it is a **router, not a copy of the docs**: it picks the pages to fetch, and adds only what the docs do not say. Fetch the pages live and apply them; cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send (`ai_generated`, `generating`, `ai_indicator.*`, the agent-steps format for reasoning / tool calls / approvals), and the CLI check are shared by every platform and live there. For integrate / new-app requests, run [`setup.md`](setup.md) first.

---

## Step 0: Install `stream_chat_flutter_ai` (before any code)

`stream_chat_flutter_ai` is the AI component library. It has **no dependency on Stream Chat** - it renders text and steps and collects input; the app connects it to a channel. Add it with `flutter pub add stream_chat_flutter_ai:^0.2.0`. It needs **Dart 3.11+ and Flutter 3.41+**: check `flutter --version` and the pubspec's `environment` first. An app on 0.1.x moves to `^0.2.0` and applies the breaking changes in the package `CHANGELOG.md` (`StreamingMessageView` types only while `expectMoreText` is `true`; `codeBlockTheme` replaces the code colors; a `CodeHighlighter` takes one `CodeHighlightRequest`, so a highlighter copied from older docs or samples needs updating) - tell the developer.

**Which Chat package:** `AIConversationView` takes any `AIMessage` and needs no Chat package; on Stream Chat, `stream_chat` (the client) underneath is enough. Add `stream_chat_flutter` when the app also shows Chat UI - a conversation drawer built on its channel list, or messenger screens (shape B).

**With the Chat UI kit:** `stream_chat_flutter` must resolve to **10.6.0+** (Dart 3.12+, Flutter 3.44+): raise the constraint in `pubspec.yaml`, with the app's other `stream_chat_*` packages (localizations, persistence) on the same version. Below 10.5, its `file_picker` needs `win32` 5 while the AI package's `share_plus` needs `win32` 6, so they don't resolve together; 10.6.0 is the first `stream_chat` that decodes the reference agents' `AI_STATE_EXTERNAL_SOURCES` as `AITypingState.checkingSources` (older versions read it as `idle`, so the indicator vanishes during tool calls). Import `stream_chat_flutter` with the AI widget names hidden, as `/stream-chat-integration.md` shows: `hide StreamingMessageView, AITypingIndicatorView, AnimatedDots, TypewriterState, TypewriterValue, TypewriterController, TypewriterWidgetBuilder`.

Where the docs stop, the package `README.md` and source at the resolved version are the reference ([`docs-map.md`](docs-map.md) "When the docs fall short") - say where a pattern came from.

## Step 1: Classify, then fetch

| Shape | Signals | Fetch (prefix `https://getstream.io/chat/docs/sdk/flutter/guides/ai-integrations`) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one person + one assistant, conversation drawer, suggestion chips, big prompt composer | `/conversation-view.md`, `.md` (components, install, platform requirements, and "Best practices": `ai_generated`, indicator events, stop, ephemeral updates), and `/stream-chat-integration.md` "Showing the AI indicator" |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | people and a bot in channels the app already renders with `stream_chat_flutter` | `/stream-chat-integration.md` and the `.md` "Best practices" section |
| **C. Agent that shows its work and asks first** (reasoning, tool calls, "ask before it books / shares / deletes") | approvals, tool use, sign-ins to a provider, transparency | A or B, plus `/reasoning-and-tool-calls.md` and the contract's "Agent steps". Stream's AI SDK and LangChain SDK don't write steps: the backend writes them itself |
| **D. Agent acts on the device** (read location, open a screen, copy to clipboard) | "the assistant should do X on the phone" | A or B, plus `/client-side-tools.md`: "Run tool calls from agent steps" when the tool returns a result to the model (needs a backend that writes `ai_tool_call` steps), "Run tool calls from events" for Stream's AI SDK / LangChain SDK, whose `custom_client_tool_invocation` events are fire-and-forget |
| **E. Voice agent transcript** (the person talks to an agent on a Stream Video call; the app shows what was said as a conversation) | "voice agent", OpenAI Realtime on a call, "transcript", "show what was said", history of past voice sessions | `/conversation-view.md`, the `.md` "Voice agent visualizations", and "Shape E" below |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | `/stream-chat-ai-sdk.md` (Vercel AI SDK) or `/stream-chat-langchain-sdk.md` |

A shape here takes up to four AI pages plus the setup pages; that is this runbook's page budget.

Decisions the docs leave to you:

- **Show the conversation with `AIConversationView`.** It is the primary way to show one person's conversation with an agent: shapes A and E, and C / D on top of A. Each question moves to the top while its reply writes out below it. Thinking, a message on its way, older messages, approvals and sign-ins are built in; reply actions (copy, share, regenerate, rate) show once you return an `AIReplyActionsView` from `AIComponentBuilders.replyActions`.
- **The alternative is the `stream_chat_flutter` message list with AI rows** (`/stream-chat-integration.md`). Take it when the conversation needs what a messenger has (reactions, threads, read state, several people), or the app already shows that channel with the UI kit (shape B). Keep the app's existing `messageBuilder` cases and add the AI branch to them; return `StreamMessageItem.fromProps(key: ValueKey(message.id), props: defaultProps)` for every other message (the key keeps per-message state on its message as pages load), which keeps the default row and any `messageItem` override from the component factory ([`design-matching.md`](design-matching.md) "Slot-override recursion trap"); the integration page's snippet returns `DefaultStreamMessageItem`, which skips that override. Keep the app's `StreamMessageComposer` (the people in the channel need its attachments and commands), and put the indicator and a Stop button in one status row above it (Step 2).
- **Starting the agent.** In an existing channel (shape B, a "Support" channel), start the agent and register any device tools when the channel page opens, after the channel is watched (contract "Key everything by channel").
- **New conversations and the drawer.** The app creates each conversation as a `messaging` channel (the app can't create `agent`-type channels; [`RULES.md`](RULES.md) "Permissions") with the person as a member and a custom field that marks it (for example `ai_assistant: true`), watches it, calls the backend's start endpoint (the reference backends add a bot per channel, `ai-bot-<channel id>`), then sends the first message. The drawer lists `Filter.and([Filter.in_('members', [me]), Filter.equal('ai_assistant', true)])`, and the app's other channel lists exclude that field. A backend with one fixed bot id can filter on two members instead, `Filter.and([Filter.in_('members', [me]), Filter.in_('members', [agentId])])` - one `Filter.in_('members', [me, agentId])` matches channels with *either* member.
- **Never a hand-built list** of bubbles on the low-level client ([`custom-ui.md`](custom-ui.md)), for a typed chat or a voice agent's transcript. Tell the developer which of the two you used and why.

## Step 2: Wire the components (what the docs leave out)

The docs show the message mapping, the indicator handler, paging, approvals and the tool runner. These are the gaps:

1. **Stop.** Turn it on from the indicator (thinking, checking sources, generating). Stop is `channel.stopAIResponse()`.
   - Under `AIConversationView`, keep `ChatComposerController.isGenerating` on while the latest reply `isGenerating`. The view draws its own rows and reports no end of typing, so Stop goes off when the backend finishes, while the last words may still be typing out.
   - In rows you draw yourself (shape B), the backend usually finishes before the typewriter does. Keep the indicator event's `messageId` (the docs' handler drops it), and keep the status row's Stop on until both the indicator has cleared and `StreamingMessageView.onFinished` has fired for that reply - in either order. When that reply's row isn't built (scrolled away), turn it off on clear. Also turn it off on `AITypingState.error` and when the person taps it.
2. **Approvals and tool results go to your backend's own routes** (the reference backends have none: they don't write steps). `decide` posts `{tool_call_id, decision}` (`decision` is the `AIToolApprovalDecision` string, `allowed` or `declined`), plus `client_id` when the call names an install, to an authenticated endpoint, which checks the caller and updates the step.
3. **Device tools.**
   - Read `AIClientIdentity.installId()` once per sign-in, before creating the runner and approver, and use that one value for both and as `client_id` on every message.
   - Create the runner once, outside `build`, and call `runner.handle(parts)` from `channel.state!.messagesStream` for every AI reply, including those already loaded when the conversation opens.
   - Request the OS permission inside the tool's `run`, and add its platform keys (a location tool: `NSLocationWhenInUseUsageDescription` on iOS, `ACCESS_COARSE_LOCATION` on Android). For a tool that shares personal data, such as the location, suggest an approval on it too (`/reasoning-and-tool-calls.md`).
   - In a channel with several people, every member sees a step's summary and arguments: keep personal data out of them.

## Step 3: State the contract, leave a tripwire (shapes A-D)

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer - `ai_generated` picks the AI row, `generating` drives `isGenerating` and `expectMoreText`, and the agent-steps attachments are what `AIMessagePartsView` renders - and run its CLI check before debugging Dart code. Then leave a debug-only tripwire where you decide whether a message is AI-generated (the `AIMessage` wrapper's constructor, or the AI branch of `messageBuilder` in shape B), so a missing `ai_generated` shows in the console instead of as a plain bubble. It logs each message once and matches your bots' user ids (the reference backends use `ai-bot-<channel id>`):

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

## Shape E: a voice agent's transcript as a conversation

The person talks to an agent on a Stream Video call (OpenAI Realtime, or the developer's own agent), and the app shows what was said as a chat: a transcript panel during the call, or the history after it. Show it with `AIConversationView` over your own `AIMessage` type. **Check the fit first**, and tell the developer which way you went:

| The request | Use |
|---|---|
| One person and one agent, shown as a running conversation | `AIConversationView` |
| Subtitles over the call: a line or two that follow the voice and fade | A caption band from the closed-captions page ([`docs-map.md`](docs-map.md) "Closed captions / transcription") |
| A meeting with several people, with or without an agent | Not this view: it starts a turn at each `AIMessageRole.user` message and draws every other role as the agent. Use the `stream_chat_flutter` message list when the transcript is in a Chat channel |
| People and a bot chatting in the same channels | Shape B |

Where the lines come from - pick by where the transcript must live, and tell the developer:

- **A Chat channel the agent writes** - the history stays after the call and on other devices; it needs an agent backend that writes the channel. Watch it and wrap its messages as `/conversation-view.md` shows, with one change: take `role` from the sender (the signed-in user's id -> `AIMessageRole.user`, anyone else -> `.assistant`), since a transcript writer may not set `ai_generated`. The person must be a member of the channel, or reading it fails with a permission error. Page with `loadOlderMessages`.
- **Closed captions** (no Chat needed) - the transcript lives in the app's memory for the screen's lifetime; for a stored copy after the call, use call transcription (the transcriptions page, [`docs-map.md`](docs-map.md) "Closed captions / transcription") or the Chat path. `call.closedCaptions` keeps only the latest captions for a moment (2 captions, 2.7 s by default in `CallPreferences`): right for subtitles, lossy for a transcript. Instead, listen with `call.callEvents.on<StreamCallClosedCaptionsEvent>(...)` for as long as the call runs and turn each into `StreamClosedCaption.fromEvent(event)`. Skip repeats (same `speakerId` and `startTime`), join consecutive captions from the same speaker into one message, map the person's own `user.id` to `AIMessageRole.user` and any other to `.assistant`. Captions must be enabled on the call type and started (`auto-on` on the call type, or `call.startClosedCaptions()`, which needs the `start-closed-captions-call` call permission; otherwise the agent's backend starts them). They arrive as finished segments, so the agent's lines show whole rather than typed out. The backend contract (`ai_generated`, `generating`, the CLI check) does not apply to this path.

The agent's backend puts the agent on the call: the app gets the call id (and the agent's user id) from that backend's authenticated start route, joins with the microphone only, and asks the backend to end the agent on hang-up. Keep each line's `id` stable across updates (a message id, or the speaker plus the first caption's start time): a changing id rebuilds the row and loses the scroll position. Put the call controls and the agent's `AIVoiceGlowView` / `AIVoiceWaveView` below the list. Find the agent's participant by its user id and map it to `AIVoiceAgentState`: not in the call yet -> `connecting`, agent `isSpeaking` -> `speaking`, the person speaking -> `listening`, otherwise `idle`; pass the agent's `audioLevel`. The captions path needs only `stream_video_flutter` and `stream_chat_flutter_ai`; with Chat in the same app too, alias the imports ([`video-patterns.md`](video-patterns.md) "Chat + Video in one app").

---

## Pitfalls the docs do not shout about

- **`extraData` values are whatever JSON delivered.** Compare with `== true`; do not cast blind, and do not assume the key exists on older messages.
- **Watch a channel before sending to it.** `channel.sendMessage` throws a `StateError` until the channel is watched (or queried) - for a channel the backend created, `await channel.watch()` first.
- **`ChatComposer` is not `StreamMessageComposer`.** It is a standalone AI composer with its own controller; attachments upload, commands and slow mode from the Chat composer are not in it.
- **Permissions:** the composer's speech, photo and camera inputs need the keys in the overview's "Platform requirements"; a device tool needs its own (Step 2).
- **Local backend:** the iOS simulator reaches `localhost`, the Android emulator reaches the host as `10.0.2.2`, a physical device needs the machine's LAN IP or a tunnel. Keep the agent URL in config.
- **No provider key in the app.** The agent runs on a backend; the app starts and stops it through an authenticated endpoint ([`RULES.md`](RULES.md) "Secrets and auth"). The reference backends' start / stop routes accept anyone: tell the developer to add the check (the user's Stream token as a Bearer header works) before shipping.

## Verify before stopping

- `pubspec.lock` shows `stream_chat_flutter_ai` 0.2.x, and `stream_chat_flutter` (if present) at 10.6.0+
- the developer was told the conversation renders with `AIConversationView`, or why the message-list alternative was taken
- shapes A-D: a prompt gets a streamed, markdown-rendered answer from the agent; "Thinking" shows until the first token; the stop button shows while the reply generates and stop keeps the partial answer
- with agent steps: reasoning folds into "Thought for Ns"; each tool call shows its title and status; an approval shows on the person's device only, allow continues the call and decline shows declined; a device tool call runs once
- shapes A-D: the contract CLI check shows `ai_generated: true`, a final `generating: false`, and any `ai_reasoning` / `ai_tool_call` attachments - and the developer was told the contract
- shape B: the app's existing `messageBuilder` cases still render, and non-AI messages use the default row
- shape E: the person's lines are their bubbles and the agent's are full-width Markdown (a line on the wrong side means the role check uses the wrong field); every line stays after the captions fade; the orb follows the agent's voice; the developer was told where the transcript lives
- `flutter analyze` is clean and no Stream secret or LLM provider key is in the app
