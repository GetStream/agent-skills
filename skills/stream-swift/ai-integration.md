# Stream Swift - AI assistants, LLM chat, and agentic experiences

Use this runbook when the iOS request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, thinking indicators, "stop generating", rendering markdown / code from the model, or letting the agent run tools on the device (MCP).

Like the rest of this skill, it is a **router, not a copy of the docs**: it picks the pages to fetch, and adds only what the docs do not say. Fetch the pages live and apply them; cite what you used. Obey [`RULES.md`](RULES.md) ("AI and LLM integrations").

**The one idea to hold:** Stream does not host the model. A **backend agent** (a bot user) answers in the Chat channel, streaming its reply by updating one message and sending `ai_indicator.*` events. The iOS app is a **renderer and a trigger** - it never calls the LLM or holds a provider key.

---

## Step 1: Classify, then fetch

| Shape | Signals | Fetch (prefix `https://getstream.io/chat/docs/sdk/ios/guides/ai-integrations`) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation sidebar, suggestion chips, big prompt composer | `.md` (components + install), `/swiftui-integration.md` |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in the same channels | `/swiftui-integration.md` only - keep the app's own composer and styling |
| **C. Agent acts on the device** (open a screen, read calendar / location, show a form) | "the assistant should do X in the app" | A or B, plus `/client-side-tools.md` |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | `/stream-chat-ai-sdk.md` (Vercel AI SDK) or `/stream-chat-langchain-sdk.md` |

If it is unclear whether a backend exists, ask one question:

> Do you already have a backend agent that answers in the channel, or should I set one up with Stream's AI SDK (Vercel AI SDK) or LangChain SDK?

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

Backend reference: `chat-ai-samples/ai-sdk-sample` and `langchain-sample` (their READMEs cover run + `.env`). Component source: `GetStream/stream-chat-swift-ai` (`Sources/StreamChatAI`). The event types (`AIIndicatorUpdateEvent`, `AIIndicatorClearEvent`, `AIIndicatorStopEvent`, `AITypingState`) are in `stream-chat-swift` `Sources/StreamChat/WebSocketClient/Events/AITypingEvents.swift`.

**Version-check before copying:** the sample README shows an older multi-argument `makeCustomAttachmentViewType`; the docs use the v5 `options:` form. Confirm against the pinned `stream-chat-swiftui` source.

## Step 3: Tell the developer what the backend must set

The iOS side only renders what the agent writes, and it cannot tell when a field is missing - the app compiles and looks subtly wrong. **Always state this contract to the developer**, and when they bring their own backend, ask them to confirm it before wiring the app:

- `ai_generated: true` on the bot's reply when it is **created**. Missing -> the resolver never matches and the answer renders as a **plain bubble with raw markdown**; a custom agent that does not skip its own `ai_generated` messages can also **answer itself in a loop**.
- `generating: true` on every partial update while streaming. Missing -> the text **jumps** instead of animating.
- `generating: false` on the final update, **and** on stop and on error. Missing -> the message **never stops "generating"**.

Stream's server SDKs and the sample backends already do this; a custom backend must do it by hand.

**Check a real bot message** after one prompt, before debugging any Swift code:

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"messaging:<channel-id>"},"message_limit":5}' \
  --jq '.channels[0].messages[] | {user: .user.id, ai_generated, generating, text: (.text // "" | .[0:40])}'
```

`null` on either field for a bot message means the backend is not setting it - fix the agent, and tell the developer.

**Leave a debug-only tripwire** in the message resolver the docs already have you write, so a missing field shows in the Xcode console instead of as a silent plain bubble (match your bot's user id):

```swift
#if DEBUG
if message.extraData["ai_generated"]?.boolValue != true, message.author.id.hasPrefix("ai-bot") {
    print("[AI] Bot message \(message.id) has no `ai_generated: true` - the backend agent must set it.")
}
#endif
```

---

## Pitfalls the docs do not shout about

- **Plain bubble / jumping text / endless "generating" is almost always the backend** (Step 3), not iOS.
- **No LLM key, Stream secret, or admin token in the app**, and no "call the LLM from the device, then post the answer" shortcut.
- **Key everything by channel:** start the agent, register tools, and filter `ai_indicator.*` events per `cid` - otherwise "Thinking" shows in the wrong conversation. Start the agent once per opened conversation, not on every view appearance.
- **Streamed chunks are edits:** skip the "Edited" label for AI messages (`MessageListConfig.skipEditedMessageLabel`, as in the sample).
- **Info.plist:** the AI composer's speech and photo / camera inputs crash on first tap without their usage descriptions (microphone, speech recognition, photo library, camera).
- **Device-side tools:** request OS permissions when the tool first runs, confirm with the user before any tool that changes data, and validate tool arguments - they are model output.
- **Local backend:** the simulator reaches `localhost`, a physical device does not (use the Mac's LAN IP or a tunnel). Keep the base URL in config.

## Verify before stopping

- a prompt gets a streamed, markdown-rendered answer from the bot in the same channel; thinking states appear and clear; stop keeps the partial answer
- the CLI check in Step 3 shows `ai_generated: true` and a final `generating: false` - and the developer was told their backend must keep setting both
- existing custom attachments still render; AI messages show no "Edited" label
- no provider key or Stream secret in the app target
