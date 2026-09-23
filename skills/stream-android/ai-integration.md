# Stream Android - AI assistants, LLM chat, and agentic experiences

Use this runbook when an Android request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, a thinking indicator, "stop generating", rendering markdown / code / tables / charts from the model, or voice dictation into the prompt.

It is a **router, not a copy of the docs**: it picks the pages to fetch and adds only what the docs do not say. Fetch the pages live via [`references/DOCS.md`](references/DOCS.md), apply them, and cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send, and the CLI check are shared by every platform and live there. It composes with the track: run Track A / B first (Step 0.5 credentials, project signals, Chat setup), then this runbook drives the integration.

---

## Step 1: Pick the library

Android has two AI component artifacts. Only one is current:

| Artifact | Status | Use it? |
|---|---|---|
| `io.getstream:stream-chat-android-ai-compose` | Separate repo (`GetStream/stream-chat-android-ai`), versioned independently, **0.x** | **Yes - this is the library.** |
| `io.getstream:stream-chat-android-ai-assistant` | Lived in the main Chat repo, versioned with the SDK, last release **6.44.1**, **removed in v7** | **No.** It does not exist for the v7+ SDK this pack targets. If an existing project already depends on it, say it is a dead end before its next SDK upgrade. |

`stream-chat-android-ai-compose` is a **Compose UI toolkit with no dependency on the Chat SDK at all** - it never sees a `ChatClient`, a `Channel`, or a `Message`. That is the fact that shapes everything below: the components render text and collect input; **you** own every line that connects them to Stream.

Components: `StreamingText` (word-by-word reveal, markdown / code / tables / Chart.js), `ChatComposer` (prompt field, attachments, voice, send/stop), `AITypingIndicator`, `SpeechToTextButton` (+ `rememberSpeechToTextButtonState`).

Install with the project's dependency strategy (version catalog if it has one), after checking the current version - [`references/DOCS.md`](references/DOCS.md) "Version lookup before installing". It is a **0.x** artifact: confirm every parameter against the resolved artifact before copying a snippet, and expect renames between versions (`isStreaming` became `isGenerating` after the last release). Snapshots live in the Central snapshot repository and are newer than the release.

## Step 2: Classify the shape, then fetch

Pages come from the Chat primary manifest ([`references/DOCS.md`](references/DOCS.md)) - search it for `ai-integrations` and fetch by title:

| Shape | Signals | Fetch (manifest title) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation drawer, new-chat action, voice input | **AI Integrations** (components + install) + **Compose Integration** (wiring them to a channel) |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in channels the app already renders with the Chat Compose SDK | **Compose Integration**, then the slot work below - the docs do not cover this case |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | **Stream Chat AI SDK** (Vercel AI SDK) or **Stream Chat LangChain SDK** |

**XML / View-based apps get nothing.** `stream-chat-android-ai-compose` is Compose-only. In an XML app, host the AI surface in a `ComposeView` (or build the screen in Compose) and say so plainly - do not improvise View equivalents.

### Shape A - the AI-first app

Follow the reference app (Step 3). The screen is built on the **low-level client plus the state layer** (`watchChannelAsState`), not on the Chat Compose SDK's `MessagesScreen` / `MessageList`. That is a deliberate choice, not an oversight: an AI conversation has one bot and one human, no reactions, threads, or read state, so the bundled messenger screens carry weight you then have to remove. Borrow from the Compose SDK only what you need (the sample uses `StorageHelperWrapper` for attachment URIs).

### Shape B - a bot inside an existing Stream messenger

The AI components are a separate artifact on every Stream platform, and the Chat Compose SDK carries the `ai_indicator.*` events but no AI rendering - same split as iOS. So the wiring is yours to write, through `ChatComponentFactory` ([`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md), [`design-matching.md`](design-matching.md)):

- **The AI bubble:** override `MessageTextContent(message, currentUser, onLongItemClick, onLinkClick, onUserMentionClick)`. When the message is AI-generated, render `StreamingText(text = message.text, animate = <generating>)`; otherwise delegate to `super`. This is the narrowest slot that works - do **not** take `MessageContainer` or `MessageContent`, which would drop avatars, grouping, reactions, replies, and status ([`RULES.md`](RULES.md) "Matching a reference design").
- **The stop button:** the default composer has no AI state. Override `MessageComposerTrailingContent` (or `MessageComposerSendButton`) to show a stop control while the indicator state is thinking or generating.
- **The thinking indicator:** place `AITypingIndicator` between the message list and the composer, driven by the events below.
- **Keep the app's other overrides.** Add to the existing factory, do not replace it.

Read the AI-generated and generating flags off `Message.extraData` (`"ai_generated"`, `"generating"`), which is what the backend contract puts there.

### Indicator events and stop

The Chat client already models the protocol - no custom transport:

- `AIIndicatorUpdatedEvent` (`aiState: String`, `messageId: String`), `AIIndicatorClearEvent`, `AIIndicatorStopEvent`
- `EventType.AI_TYPING_INDICATOR_UPDATED` / `_CLEAR` / `_STOP` (`ai_indicator.update` / `.clear` / `.stop`)

**Subscribe on the `ChannelClient`, not on `ChatClient`.** `chatClient.channel(cid).subscribeFor<...>` already filters these three events by `cid`, so the contract's key-by-channel rule costs you nothing; subscribing on the client means "Thinking" appears in the wrong conversation.

**Android has no `stopAIResponse()` helper** (React and React Native do). Stop is an event:

```kotlin
chatClient.channel(cid)
    .sendEvent(EventType.AI_TYPING_INDICATOR_STOP)
    .enqueue()
```

The states the server sends are `AI_STATE_THINKING`, `AI_STATE_GENERATING`, `AI_STATE_EXTERNAL_SOURCES`, and `AI_STATE_ERROR`. **Match on those exact strings** - the sample app and the Compose Integration docs page both map `AI_STATE_CHECKING_SOURCES`, which the server never sends, so that state silently renders nothing.

## Step 3: Fill the gaps from the reference app

The docs show each component; the **wiring around them** lives only in the reference app. Read the matching file instead of inventing it, and say the pattern came from the sample:

`https://raw.githubusercontent.com/GetStream/stream-chat-android-ai/develop/stream-chat-android-ai-compose-sample/src/main/kotlin/io/getstream/chat/android/ai/compose/sample/<file>`

| Need | File |
|---|---|
| Agent start on channel open, event handling, optimistic send, create-channel-on-first-message, stop | `presentation/chat/ChatViewModel.kt` |
| Assistant state model (thinking / generating / external sources / error) | `presentation/chat/ChatUiState.kt` |
| `StreamingText` per message, `ChatComposer`, `AITypingIndicator` placement | `ui/chat/ChatScreen.kt`, `ui/components/ChatMessageItem.kt` |
| AI-message detection off `extraData` | `domain/StreamMessageExt.kt` |
| Backend calls (`/start-ai-agent`, `/stop-ai-agent`, `/summarize`) | `data/api/ChatAiApi.kt`, `data/repository/ChatAiService.kt`, `ChatDependencies.kt` |
| Conversation drawer, new chat as a fresh channel | `ui/components/ChatDrawer.kt`, `presentation/conversations/` |
| Chart.js rendering (needs `src/main/assets/chart.umd.min.js` - the docs never mention the asset) | `ui/components/ChartDiagram.kt` |

Component source: `GetStream/stream-chat-android-ai` (`stream-chat-android-ai-compose`). Event types: `stream-chat-android` `stream-chat-android-client/.../client/events/ChatEvent.kt`.

**Do not copy the sample's auth or hosts.** `App.kt` hardcodes a static user token and points at `http://10.0.2.2:3000`. Use [`credentials.md`](credentials.md) for the token path and the user's own agent URL from config. Its `isFromAi()` fallback also matches `ai_bot-`, while the backends use `ai-bot-*` ids - rely on `ai_generated`, not the prefix.

## Step 4: State the contract, leave a tripwire

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer and run its CLI check before debugging Android code. Then leave a debug-only tripwire where you decide whether a message is AI-generated, so a missing `ai_generated` shows in Logcat instead of as a silent plain bubble (match your bot's user id):

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

---

## Pitfalls the docs do not shout about

- **`extraData` values are whatever JSON delivered.** Compare `extraData["generating"] == true`; do not cast to `Boolean` blind, and do not assume the key is present on older messages.
- **Streamed chunks are message edits.** Expect an "Edited" label on AI replies in the bundled Compose message UI, and suppress it for AI messages in shape B.
- **`ChatComposer` is not `MessageComposer`.** It is a standalone AI composer with its own state; it does not read the Chat SDK's composer controller, so attachments, commands, and slow mode are yours to wire.
- **Permissions:** `SpeechToTextButton` needs `RECORD_AUDIO` (the sample declares it in its manifest) and dictation depends on an on-device recognizer - feature-detect and hide the button where it is unavailable rather than failing at tap. Add camera / media permissions only if you enable those composer inputs.
- **Local backend:** the emulator reaches the host at `10.0.2.2`, a physical device needs the machine's LAN IP or a tunnel. Keep the agent URL in config, never hardcoded.
- **`minSdk`:** the AI artifact builds against `minSdk 23`; confirm the consuming module is not lower before adding it.
- **No provider key in the app.** The agent runs on a backend; the app starts and stops it through an authenticated endpoint ([`RULES.md`](RULES.md) "Secrets and auth").

## Verify before stopping

- on a real device or emulator, a prompt gets a streamed, markdown-rendered answer from the bot in the same channel; the thinking indicator appears and clears; stop keeps the partial answer; dictation fills the prompt
- the contract CLI check passes and the developer was told the contract
- shape B only: existing `ChatComponentFactory` overrides still render, and non-AI messages are untouched
- the project builds and no Stream secret or LLM provider key is in the app module
