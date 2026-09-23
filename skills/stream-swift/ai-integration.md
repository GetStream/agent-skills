# Stream Swift - AI assistants, LLM chat, and agentic experiences

Use this runbook when the iOS request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, thinking indicators, "stop generating", rendering markdown / code from the model, or letting the agent run tools on the device (MCP).

Like the rest of this skill, it is a **router, not a copy of the docs**: it picks the pages to fetch, and adds only what the docs do not say. Fetch the pages live and apply them; cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send (including the `generating` flag iOS depends on), and the CLI check are shared by every platform and live there.

---

## Step 1: Classify, then fetch

| Shape | Signals | Fetch (prefix `https://getstream.io/chat/docs/sdk/ios/guides/ai-integrations`) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation sidebar, suggestion chips, big prompt composer | `.md` (components + install), `/swiftui-integration.md` |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in the same channels | `/swiftui-integration.md` only - keep the app's own composer and styling |
| **C. Agent acts on the device** (open a screen, read calendar / location, show a form) | "the assistant should do X in the app" | A or B, plus `/client-side-tools.md` |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | `/stream-chat-ai-sdk.md` (Vercel AI SDK) or `/stream-chat-langchain-sdk.md` |

Decisions the docs leave to you:

- **Stay on the pre-built components.** An AI chat is a messenger surface - `StreamChatSwiftUI` + `StreamChatAI`, not a hand-built list on the low-level client ([`custom-ui.md`](custom-ui.md)). In shape B, keep existing custom attachments and list modifiers when you add the AI ones - overriding the slot replaces the default (composite-slot trap in [`design-matching.md`](design-matching.md)).
- **UIKit:** `StreamChatAI` is SwiftUI-only (iOS 16+). Host its views with `UIHostingController`, or build the AI screen in SwiftUI.
- **Install:** run [`setup.md`](setup.md) first (Chat v5). For `stream-chat-swift-ai`, pin the **latest release tag** (`git ls-remote --tags https://github.com/GetStream/stream-chat-swift-ai.git`) - the docs' `from:` version is only a minimum.

## Step 2: Fill the gaps from the reference app

The docs show the components; the **wiring around them** (event handling, starting the agent, the stop button, tool-event decoding) lives only in the reference app. Read the matching file instead of inventing it, and say the pattern came from the sample:

`https://raw.githubusercontent.com/GetStream/chat-ai-samples/main/ios/AIComponents/<file>`

| Need | File |
|---|---|
| App init, AI-friendly `MessageListConfig`, message resolver | `AIComponentsApp.swift` |
| `ViewFactory` + `Styles` for AI messages | `AIComponentsFactory.swift` |
| Thinking / generating state from `ai_indicator.*`, bot presence, client-tool dispatch | `TypingIndicatorHandler.swift` |
| Backend calls (start / stop agent, register tools, summarize for titles) | `AgentService.swift` |
| Decoding the client-tool invocation event | `StreamChatClientTools.swift` |
| Composer, suggestions, stop generating, new conversation | `ContentView.swift` |

Component source: `GetStream/stream-chat-swift-ai` (`Sources/StreamChatAI`). The event types (`AIIndicatorUpdateEvent`, `AIIndicatorClearEvent`, `AIIndicatorStopEvent`, `AITypingState`) are in `stream-chat-swift` `Sources/StreamChat/WebSocketClient/Events/AITypingEvents.swift`.

**Version-check before copying:** the sample README shows an older multi-argument `makeCustomAttachmentViewType`; the docs use the v5 `options:` form. Confirm against the pinned `stream-chat-swiftui` source.

## Step 3: State the contract, leave a tripwire

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer - on iOS both `ai_generated` and `generating` are required - and run its CLI check before debugging Swift code. Then leave a debug-only tripwire in the message resolver the docs already have you write, so a missing field shows in the Xcode console instead of as a silent plain bubble (match your bot's user id):

```swift
#if DEBUG
if message.extraData["ai_generated"]?.boolValue != true, message.author.id.hasPrefix("ai-bot") {
    print("[AI] Bot message \(message.id) has no `ai_generated: true` - the backend agent must set it.")
}
#endif
```

---

## Pitfalls the docs do not shout about

- **Filter `ai_indicator.*` by `cid`** in the event handler - otherwise "Thinking" shows in the wrong conversation (the contract's key-by-channel rule, iOS side).
- **Streamed chunks are edits:** skip the "Edited" label for AI messages (`MessageListConfig.skipEditedMessageLabel`, as in the sample).
- **Info.plist:** the AI composer's speech and photo / camera inputs crash on first tap without their usage descriptions (microphone, speech recognition, photo library, camera).
- **Device-side tools:** request OS permissions when the tool first runs (the rest of the client-tool rules are in the contract).
- **Local backend:** the simulator reaches `localhost`, a physical device does not (use the Mac's LAN IP or a tunnel). Keep the base URL in config.

## Verify before stopping

- a prompt gets a streamed, markdown-rendered answer from the bot in the same channel; thinking states appear and clear; stop keeps the partial answer
- the contract CLI check shows `ai_generated: true` and a final `generating: false` - and the developer was told the contract
- existing custom attachments still render; AI messages show no "Edited" label
