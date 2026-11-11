# Stream Android - AI assistants, LLM chat, and agentic experiences

Use this runbook when an Android request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, a voice agent, streaming the model's answer, a thinking indicator, "stop generating", rendering markdown / code / tables / charts from the model, showing the agent's reasoning and tool calls, asking the person before a tool runs, letting the agent run tools on the device, generative UI in a reply, or voice dictation into the prompt.

It is a **router, not a copy of the docs**: it picks the pages to fetch and adds only what the docs do not say. Fetch the pages live via [`references/DOCS.md`](references/DOCS.md), apply them, and cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send, and the CLI check are shared by every platform and live there. It composes with the track: run Track A / B first (Step 0.5 credentials, project signals, Chat setup), then this runbook drives the integration.

---

## Step 0: Pick the libraries (decide before any code)

**The AI components ship with Stream Chat Android from 7.15.0**, versioned with the rest of the SDK. Earlier, `stream-chat-android-ai-compose` was released separately from `GetStream/stream-chat-android-ai` as 0.x; that repo is no longer where the components live.

| Artifact | What it is | Needs |
|---|---|---|
| `io.getstream:stream-chat-android-ai-compose` | The components: `AIConversation`, `ChatComposer`, `StreamingText`, agent steps, approvals, voice visualizations | `minSdk` 23 |
| `io.getstream:stream-chat-android-ai-a2ui` / `-ai-openui` | Generative UI renderers for A2UI / OpenUI replies (from 7.18.0) | `minSdk` 23 |
| `io.getstream:stream-chat-android-ai-ondevice` | `AIOnDeviceModel`: Gemini Nano through ML Kit's GenAI Prompt API, the offline fallback | `minSdk` 26 |
| `io.getstream:stream-chat-android-ai-assistant` | The v6 component, **never published for v7** | Do not add it. In an existing project, say it is a dead end before the next major upgrade. |

Use the Chat version the project already resolves for every AI artifact ([`references/DOCS.md`](references/DOCS.md) "Version lookup before installing"). A project on the standalone 0.x artifact moves to the Chat one in the same change that raises Chat to 7.15.0 or later; the 0.x API differs, so recheck every call against the new version.

**`stream-chat-android-ai-compose` does not depend on the Chat SDK.** It never sees a `ChatClient`, a `Channel` or a `Message`: you hand it `AIMessage`s and callbacks. That is the fact that shapes everything below - the connection to Stream is either Stream Agents' (shape A on Stream Agents) or yours (every other shape).

**Stream Agents on Android.** When the agent runs on Stream Agents (an `agents/<name>/` folder synced with `getstream agents`, see [`../stream/SKILL.md`](../stream/SKILL.md)), the app opens its sessions with `io.getstream:stream-agents-android-core` from `https://stream-io-repo.com` (look the version up as [`references/DOCS.md`](references/DOCS.md) "Version lookup before installing" shows). The client is `StreamAgents`, the package `io.getstream.agents.android.core`. It needs `compileSdk` 37, Kotlin 2.3 or newer and `minSdk` 24, and brings Stream Chat and Stream Video with it. Its source is `sdks/kotlin` on the `accelerate` branch of `GetStream/Vision-Agents` (`https://raw.githubusercontent.com/GetStream/Vision-Agents/accelerate/sdks/kotlin/README.md`). When the docs and the SDK disagree, the SDK's source at the resolved version wins.

## Step 1: Classify the shape, then fetch

Pages come from the Chat primary manifest ([`references/DOCS.md`](references/DOCS.md)) - search it for `ai-components` and fetch by title:

| Shape | Signals | Fetch (manifest title) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation drawer, new-chat action, voice input | On Stream Agents: **Quickstart**, then **Personal Assistant** or **Customer Support Agent**. On the developer's own backend: **Conversation State**. Both with **Conversation View** and **Composer** |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in channels the app already renders with the Chat Compose SDK | **Compose Integration** - it covers the AI bubble, agent steps, the "Edited" label, indicator events and stop; the slot work below adds the stop button and where the thinking indicator goes |
| **C. Agent that shows its work and asks first** (reasoning, tool calls, "ask before it books / shares / deletes") | approvals, tool use, transparency | A or B, plus **Reasoning and Tool Calls** and the contract's "Agent steps" section |
| **D. Agent acts on the device** (read location, calendar, open a screen) | "the assistant should do X on the phone" | A or B, plus **Reasoning and Tool Calls** "Tools on the device" |
| **E. Voice agent** (the person talks to the agent on a call) | "voice agent", "talk to the assistant", a glow or wave while it speaks | **Voice Agent** and **Voice Visualizations** |
| **F. Generative UI** (the reply is a card, a form, a map) | A2UI, OpenUI, "the agent answers with UI" | A, plus **Generative UI** |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | Stream Agents (`https://getstream.io/agents/docs/quickstart/?lang=android`), or **Stream Chat AI SDK** (Vercel AI SDK) / **Stream Chat LangChain SDK** |

**XML / View-based apps get nothing.** The AI components are Compose-only. In an XML app, host the AI surface in a `ComposeView` (or build the screen in Compose) and say so plainly - do not improvise View equivalents.

Decisions the docs leave to you:

- **Show the conversation with `AIConversation`.** It is the primary way to show one person's conversation with an agent: shapes A, C, D and F, and the transcript in E. Thinking, a message on its way, older messages, approvals, sign-ins and reply actions are built in (**Conversation View**).
- **The alternative is the Chat Compose message list with the AI components plugged in** (shape B). Take it when the conversation needs what a messenger has and `AIConversation` doesn't (reactions, threads, read state, several people in the channel), or when the app already shows that channel with the Chat Compose SDK.
- **Never a hand-built list** of `StreamingText` items for a new screen. Tell the developer which of the two you used and why.

## Step 2: Wire the components (what the docs leave out)

### Shape A on Stream Agents

- **Ask the session, never the channel.** The agent doesn't answer a message sent to the session's channel; the router writes the person's message into the channel itself. Sending through `ChatClient` produces a message nobody answers.
- **The conversation is an `AIConversationState` (Chat 7.19.0 or later) over the session's channel.** The app writes the `AIConversationTransport` (the Quickstart's `AgentTransport`): it feeds the state from `session.channelState(context, scope)`, wrapping each message as an `AIMessage` (the Quickstart's `AgentMessage`), sends with `session.responses.create(text)`, and stops with `session.interrupt()`. Keep the state in a `ViewModel` and pass it to both `AIConversation` and `ChatComposer`. Keep one `StreamAgents` client per app, created once, and set the user when they sign in.
- **One `AIToolApprover` per signed-in user**, built with that user's id, passed to `AIConversation`.
- **Errors:** session calls throw `AgentsException`; catch it where the person can see what failed.

### Shape A on the developer's own backend

Follow **Conversation State**: the screen is an `AIConversationState` (Chat 7.19.0 or later) kept in a `ViewModel` and passed to `AIConversation` and `ChatComposer`. The app writes its `AIConversationTransport` on the **low-level client plus the state layer**: it watches the channel with `watchChannelAsState` and wraps the messages as `AIMessage`s, follows the `ai_indicator.*` events, sends what the user asks as a channel message, and stops the reply with the stop event. Not the Chat Compose SDK's `MessagesScreen` / `MessageList`: an AI conversation has one bot and one human, no reactions, threads, or read state, so the bundled messenger screens carry weight you then have to remove.

### Shape B - a bot inside an existing Stream messenger

The Chat Compose SDK carries the `ai_indicator.*` events but no AI rendering - same split as iOS. So the wiring is yours to write, through `ChatComponentFactory` ([`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md), [`design-matching.md`](design-matching.md)):

- **The AI bubble:** override `MessageTextContent(params: MessageTextContentParams)`. When `params.message` is AI-generated, render `StreamingText(text = params.message.text, animate = <generating>)`; otherwise delegate to `super`. This is the narrowest slot that works - do **not** take `MessageContainer` or `MessageContent`, which would drop avatars, grouping, reactions, replies, and status ([`RULES.md`](RULES.md) "Matching a reference design").
- **The stop button:** the default composer has no AI state. Override `MessageComposerTrailingContent(params)` (or `MessageComposerSendButton(params)`) to show a stop control while the indicator state is thinking or generating.
- **The thinking indicator:** there is no slot between the message list and the composer - `ChannelScreen`'s `DefaultBottomBarContent` is `internal`. The way in is to override `ChatComponentFactory.MessageComposer(params)`, emit `AITypingIndicator` above it, and call `super.MessageComposer(params)` for the real composer. Additive, and nothing internal gets reimplemented.
- **Keep the app's other overrides.** Add to the existing factory, do not replace it.

**Every `ChatComponentFactory` slot takes a single `params` object in v7** (`MessageTextContentParams`, `MessageComposerTrailingContentParams`, ...), not positional arguments - that changed from v6. Confirm the fields against `ChatComponentFactoryParams.kt` at the version the project resolves.

Read the AI-generated and generating flags off `Message.extraData` (`"ai_generated"`, `"generating"`), which is what the backend contract puts there.

### Indicator events and stop (own backend, shapes A and B)

The Chat client already models the protocol - no custom wire format (on shape A these events feed your `AIConversationTransport`):

- `AIIndicatorUpdatedEvent` (`aiState: String`, `messageId: String`), `AIIndicatorClearEvent`, `AIIndicatorStopEvent`
- `EventType.AI_TYPING_INDICATOR_UPDATED` / `_CLEAR` / `_STOP` (`ai_indicator.update` / `.clear` / `.stop`)

**Subscribe on the `ChannelClient`, not on `ChatClient`.** `chatClient.channel(cid).subscribeFor<...>` already filters these three events by `cid`, so the contract's key-by-channel rule costs you nothing; subscribing on the client means "Thinking" appears in the wrong conversation.

**Android has no `stopAIResponse()` helper** (React and React Native do). Stop is an event:

```kotlin
chatClient.channel(cid)
    .sendEvent(EventType.AI_TYPING_INDICATOR_STOP)
    .enqueue()
```

The states are `AI_STATE_THINKING`, `AI_STATE_GENERATING`, `AI_STATE_ERROR`, and a fourth for "consulting tools / sources" whose spelling **is not consistent across Stream**: the reference Node agents emit `AI_STATE_EXTERNAL_SOURCES` (so do React, React Native and iOS), while the backend's own constant, `stream-chat-js` and Flutter use `AI_STATE_CHECKING_SOURCES`. `ai_state` arrives as a raw `String` with no SDK enum, so **match both spellings** and map them to one state.

**Every `ai_indicator.update` must carry a `message_id` on Android.** The event model declares `message_id` as a required `String`, so an event without it fails to parse and is dropped. Stream's reference agents always set it - they create the bot's empty placeholder message first and then send the indicator with **that message's** id - so this only bites a hand-rolled backend. iOS declares the same field optional, so a custom agent that omits it works on iOS and not on Android - check this first when a customer reports that thinking indicators never appear on Android only.

## Step 3: Fill the gaps from the reference apps

Read the matching file instead of inventing it, and say the pattern came from the sample:

- **Stream Agents:** `examples/voice_agents/android_assistant` on the `accelerate` branch of `GetStream/Vision-Agents` - a text and voice assistant on `stream-agents-android-core` and the AI components.
- **Own backend:** `stream-chat-android-ai-compose-sample` in `GetStream/stream-chat-android` (`develop`). It predates `AIConversation`: take its wiring around the channel, not its message list.

`https://raw.githubusercontent.com/GetStream/stream-chat-android/develop/stream-chat-android-ai-compose-sample/src/main/kotlin/io/getstream/chat/android/ai/compose/sample/<file>`

| Need | File |
|---|---|
| Agent start on channel open, event handling, optimistic send, create-channel-on-first-message, stop | `presentation/chat/ChatViewModel.kt` |
| Assistant state model (thinking / generating / external sources / error) | `presentation/chat/ChatUiState.kt` |
| AI-message detection off `extraData` | `domain/StreamMessageExt.kt` |
| Backend calls (`/start-ai-agent`, `/stop-ai-agent`, `/summarize`) | `data/api/ChatAiApi.kt`, `data/repository/ChatAiService.kt`, `ChatDependencies.kt` |
| Conversation drawer, new chat as a fresh channel | `ui/components/ChatDrawer.kt`, `presentation/conversations/` |

Component source: `GetStream/stream-chat-android` (`stream-chat-android-ai-compose`). Event types: `stream-chat-android-client/.../client/events/ChatEvent.kt`.

**Do not copy the samples' auth or hosts.** The Chat sample's `App.kt` hardcodes a static user token and points at `http://10.0.2.2:3000`. Use [`credentials.md`](credentials.md) for the token path and the user's own agent URL from config. Its `isFromAi()` fallback also matches `ai_bot-`, while the backends use `ai-bot-*` ids - rely on `ai_generated`, not the prefix.

## Step 4: State the contract, leave a tripwire

On the developer's own backend, state the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) and run its CLI check before debugging Android code. If the `getstream` CLI is not set up for this project, read the same fields back over the REST API instead - the point is to inspect a real bot message, not to run that exact command. Then leave a debug-only tripwire where you decide whether a message is AI-generated, so a missing `ai_generated` shows in Logcat instead of as a silent plain bubble (match your bot's user id):

```kotlin
private val warned = mutableSetOf<String>()

internal fun Message.isFromAi(): Boolean {
    val ai = extraData["ai_generated"] == true
    if (BuildConfig.DEBUG && !ai && user.id.startsWith("ai-bot") && warned.add(id)) {
        Log.w("AI", "Bot message $id has no ai_generated: true - the backend agent must set it.")
    }
    return ai
}
```

On Stream Agents the router writes the messages, so skip the tripwire and check the agent with `getstream agents` instead.

---

## Pitfalls the docs do not shout about

- **`extraData` values are whatever JSON delivered.** Compare `extraData["generating"] == true`; do not cast to `Boolean` blind, and do not assume the key is present on older messages.
- **Streamed chunks are message edits.** Expect an "Edited" label on AI replies in the bundled Compose message UI (shape B). It is driven by `message.messageTextUpdatedAt` inside the message footer, so suppressing it for AI messages means overriding `MessageFooterContent` - there is no flag for it.
- **`ChatComposer` is not `MessageComposer`.** It is a standalone AI composer with its own state; it does not read the Chat SDK's composer controller, so attachments, commands, and slow mode are yours to wire.
- **Charts load Chart.js from a CDN** unless the app ships `chart.umd.min.js` in `src/main/assets`. Ship the asset for offline use or a strict network policy.
- **Permissions:** `SpeechToTextButton` needs `RECORD_AUDIO` and an on-device recognizer - feature-detect and hide the button where it is unavailable rather than failing at tap. A voice agent needs `RECORD_AUDIO` too, and `CAMERA` only if it sees the camera.
- **`AIOnDeviceModel` runs only where AICore offers Gemini Nano** (recent flagship phones, never emulators), and may need downloading first. Check `status()` and keep the backend agent as the default; the device model is the fallback.
- **Local backend:** the emulator reaches the host at `10.0.2.2`, a physical device needs the machine's LAN IP or a tunnel. Keep the agent URL in config, never hardcoded.
- **No provider key in the app.** The agent runs on a backend; the app starts and stops it through an authenticated endpoint, or opens a Stream Agents session with the user's token ([`RULES.md`](RULES.md) "Secrets and auth").

## Verify before stopping

- on a real device or emulator, a prompt gets a streamed, markdown-rendered answer from the agent; the thinking indicator appears and clears; stop keeps the partial answer; dictation fills the prompt
- own backend: the contract CLI check passes and the developer was told the contract
- shape B only: existing `ChatComponentFactory` overrides still render, and non-AI messages are untouched
- the project builds and no Stream secret or LLM provider key is in the app module
