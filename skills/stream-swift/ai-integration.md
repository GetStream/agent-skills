# Stream Swift - AI assistants, LLM chat, and agentic experiences

Use this runbook when the iOS request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, thinking indicators, "stop generating", rendering markdown / code from the model, showing the agent's reasoning and tool calls, asking the person before a tool runs (approvals), or letting the agent run tools on the device.

Like the rest of this skill, it is a **router, not a copy of the docs**: it picks the pages to fetch, and adds only what the docs do not say. Fetch the pages live and apply them; cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send (including the `generating` flag iOS depends on, and the agent-steps format for reasoning / tool calls / approvals), and the CLI check are shared by every platform and live there.

---

## Step 0: Which StreamChatAI (decide before any code)

**`StreamChatAI` ships in `stream-chat-swift` from 5.13.0** (GetStream/stream-chat-swift#4306, released 2026-10-09), as a library product next to `StreamChat` and `StreamChatCommonUI`. Before that it was the standalone `stream-chat-swift-ai` package (last release 0.12.0), which is now the **fallback**. Both declare a target named `StreamChatAI`, so an app has one or the other, never both: SPM refuses the graph even when the app links only `StreamChat` from 5.13.0+ (`multiple packages ('stream-chat-swift', 'stream-chat-swift-ai') declare targets with a conflicting name: 'StreamChatAI'`).

**The latest release is 5.14.0** (2026-10-15, both Chat packages). It changes nothing in `StreamChatAI`: its notes are core-client additions and fixes, and nothing in them is source-breaking. `stream-chat-swiftui` 5.14.0 requires `stream-chat-swift` 5.14.0+, so a fresh resolve of `from: "5.13.0"` takes both to 5.14.0. That's expected and needs no AI changes.

Read the app's `Package.resolved` (or the project's package references), pick the row, and **tell the developer that `StreamChatAI` needs `stream-chat-swift` 5.13.0 or later**, and which path you took:

| The app has | Do |
|---|---|
| no Chat yet, or Chat 5.13.0+ | **Default.** Link `StreamChat` + `StreamChatAI` from `stream-chat-swift` `from: "5.13.0"`, and `StreamChatSwiftUI` from `stream-chat-swiftui` `from: "5.13.0"` (its 5.13.0 requires `stream-chat-swift` 5.13.0+ anyway). |
| Chat 5.x below 5.13.0 | **Suggest the version update:** raise both Chat packages to `from: "5.13.0"` (Xcode: the package's Dependency Rule, then File > Packages > Update to Latest Package Versions). Per the 5.13.0 and 5.14.0 changelogs, the only source change to check is `Device.createdAt`, now non-optional (5.13.0). If the developer can't update now, take the fallback. |
| the standalone `stream-chat-swift-ai` | **Suggest migrating with the update:** remove the `stream-chat-swift-ai` package in the same change that raises Chat to 5.13.0, link the `StreamChatAI` product of `stream-chat-swift` instead, then follow the docs' "Migrating from stream-chat-swift-ai" (`.../guides/ai-integrations.md`: rename table, `AIAppearance` instead of `colors:`, `isGenerating` on the view model, `AIClientTool` + `AIClientToolRunner`). If they'd rather not migrate yet, the app stays on the fallback. |
| Xcode 26 or older, no move to Xcode 27 | **Fallback.** Adding `StreamChatAI` from `stream-chat-swift` with SPM needs Xcode 27 (Xcode 26 rejects the target). |

**The fallback (standalone package).** Pin `stream-chat-swift-ai` to 0.12.0 and keep `stream-chat-swift` and `stream-chat-swiftui` below 5.13.0 (`.upToNextMinor(from: "5.12.0")`), or SPM rejects the graph. 0.12.0 is iOS 16+, depends on the MCP Swift SDK (swift-nio, swift-log, ...), and has the API the docs' migration section lists as the old one: `ComposerView(viewModel:colors:isGenerating:onMessageSend:onStopGenerating:)`, per-view `colors:` arguments, an `AIClientTool` with only `name` + `run`, and tools described with MCP `Tool` through `ClientTool` / `ClientToolRegistry`. It does have the parts, approval, client-tool runner and on-device model types. The docs no longer show its API, so take its signatures from that tag's `Sources/StreamChatAI`. Tell the developer the fallback is a stopgap and updating to 5.13.0 is the way forward.

**The docs are current for 5.13.0 and 5.14.0** (install, requirements, `Info.plist` keys, migration, appearance, reasoning / tool calls / approvals, client tools, the on-device model). Where the docs and the code disagree, the source at the resolved version wins (`stream-chat-swift` `Sources/StreamChatAI`; the local SPM checkout, see [`docs-map.md`](docs-map.md) "When the docs fall short") - say so. The thinking-indicator events the docs rely on now arrive, after a server-side fix, but keep the fallback (pitfalls).

## Step 1: Classify, then fetch

| Shape | Signals | Fetch (prefix `https://getstream.io/chat/docs/sdk/ios/guides/ai-integrations`) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation sidebar, suggestion chips, big prompt composer | `.md` (components, install, appearance, and "Best practices": `ai_generated`, indicator events, stop, ephemeral updates), `/swiftui-integration.md` |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in the same channels | `/swiftui-integration.md` and the `.md` "Best practices" section - keep the app's own composer and styling |
| **C. Agent that shows its work and asks first** (reasoning, tool calls, "ask before it books / shares / deletes") | approvals, tool use, "search for tools", transparency | A or B, plus `/reasoning-and-tool-calls.md` and the contract's "Agent steps" section |
| **D. Agent acts on the device** (read location, device settings, copy to clipboard, open a screen) | "the assistant should do X on the phone" | A or B, plus `/client-side-tools.md`: "Run tool calls from agent steps" for an agent that writes `ai_tool_call` steps, "Run tool calls from events" for Stream's AI SDK / LangChain SDK (they send `custom_client_tool_invocation` instead) |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | `/stream-chat-ai-sdk.md` (Vercel AI SDK) or `/stream-chat-langchain-sdk.md` - and check whether it writes agent steps (contract) |

Decisions the docs leave to you:

- **Stay on the pre-built components.** An AI chat is a messenger surface - `StreamChatSwiftUI` + `StreamChatAI`, not a hand-built list on the low-level client ([`custom-ui.md`](custom-ui.md)). In shape B, keep existing custom attachments and list modifiers when you add the AI ones - overriding the slot replaces the default (composite-slot trap in [`design-matching.md`](design-matching.md)).
- **Install:** run [`setup.md`](setup.md) first (Chat v5), then add the products from Step 0.
- **UIKit:** `StreamChatAI` is SwiftUI-only. Host its views with `UIHostingController`, or build the AI screen in SwiftUI.

## Step 2: Wire the components (what the docs leave out)

The docs show each component and the StreamChatSwiftUI wiring. These are the gaps found building a working app on 5.13.0 + StreamChatSwiftUI:

1. **The reply view.** Conform to `MessageTypeResolving` as the SwiftUI integration page does - `MessageTypeResolver` is `public`, not `open`, so it can't be subclassed. In `makeCustomAttachmentViewType(options:)`, while the reply is generating with no text and no parts, show `AITypingIndicatorView(text: "Thinking")` in the slot. That shows the agent is working even without the indicator events, which aren't replayed to someone who opens the channel mid-reply and didn't arrive on Chat v5 before the server fix (pitfalls). Add the docs' event-driven indicator on top of it for the other states ("Checking external sources"). The slot renders bare (no bubble), so the reply is full width. For an AI-first app, set `MessageListConfig(shouldMessagesStartAtTheTop: true)` so a new conversation reads from the top like a document instead of hugging the composer; `MessageListView` applies it itself and still anchors to the newest message once the list fills the screen.
2. **Approvals.** Hold one `AIToolApprover` per signed-in user and install (the view factory is a good owner); its `decide` closure posts `{tool_call_id, client_id, allowed}` to an authenticated backend endpoint, which checks the caller and updates the step.
3. **Device tools.** The registration has no display title or approval spec: if the backend should ask before a device tool runs, send those alongside (an `Encodable` wrapper that encodes the SDK registration and then its own keys into the same keyed container). Hand `runner.run(parts)` every agent `MessageNewEvent` / `MessageUpdatedEvent` (a `chatClient.eventsController()` delegate) as well as the reply view's `onAppear` - the view alone runs only while the reply is on screen. Request OS permissions inside `run`.
4. **Thinking and stop.** The docs' recipe sets `isGenerating` only from `AIIndicatorUpdateEvent(.generating)`. That event isn't replayed, so someone who opens the channel mid-reply never sees the stop button, and where the server fix hasn't landed the event never arrives (pitfalls). Set `composerViewModel.isGenerating` from two signals per `cid`: the indicator events (as the docs show, with `chatClient.eventsController()` - a `ChannelEventsController` drops them, their `cid` is optional), **or** an agent message in the channel whose `extraData["generating"]` is still `true` (track it from `MessageNewEvent` / `MessageUpdatedEvent`). Send `AIIndicatorStopEvent(cid:)` through a channel events controller (the client-wide `EventsController` has no `sendEvent`), and keep that controller alive until the completion fires.
5. **Session.** If the backend issues expiring tokens, connect with `connectUser(userInfo:tokenProvider:)`: `connectUser(userInfo:token:)` rejects a token that has an expiry.

The reference app (`https://raw.githubusercontent.com/GetStream/chat-ai-samples/main/ios/AIComponents/<file>`: `AIComponentsApp.swift` init + message resolver, `AIComponentsFactory.swift`, `TypingIndicatorHandler.swift`, `AgentService.swift`, `ContentView.swift`) still imports `MCP` and the standalone package: apply the docs' migration steps when you copy from it.

## Step 3: State the contract, leave a tripwire

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer - on iOS both `ai_generated` and `generating` are required, and the agent-steps attachments are what the parts views render - and run its CLI check before debugging Swift code. Then leave a debug-only tripwire in the message resolver, so a missing field shows in the Xcode console instead of as a silent plain bubble (match your agent's user id):

```swift
#if DEBUG
if message.extraData["ai_generated"]?.boolValue != true, message.author.id == agentUserID {
    print("[AI] Agent message \(message.id) has no `ai_generated: true` - the backend agent must set it.")
}
#endif
```

---

## Pitfalls the docs do not shout about

- **`ai_indicator.update` was dropped on Chat v5, and the fix is on the server, not in the SDK.** Backends send it as a custom event (`sendEvent`, as Stream's AI SDK and the server docs do). The v5 WebSocket (`/api/v2/connect`) delivered the custom data nested under `custom` (`{"type": "ai_indicator.update", "cid": ..., "custom": {"ai_state": ..., "message_id": ...}}`), but the generated `AIIndicatorUpdateEventDTO` requires `ai_state` and `message_id` at the top level. Decoding failed and `EventDecoder` dropped the event, without surfacing it as an `UnknownChannelEvent`; `ai_indicator.clear` needs only `cid`, so it kept arriving. The backend fix was deployed on 2026-10-13 (the SDK-side fallback, GetStream/stream-chat-swift#4324, was closed in favor of it), so 5.13.0 and 5.14.0 apps now receive `AIIndicatorUpdateEvent` and the docs' event recipes work. The DTO in 5.13.0 and 5.14.0 is unchanged, so a backend that still sends the nested shape fails the same silent way. **To check:** log every `AIIndicatorUpdateEvent` / `AIIndicatorClearEvent` in the `chatClient.eventsController()` delegate. If the clears arrive but no updates do, this is the cause. Report it, and rely on the fallbacks in Step 2.1 and 2.4. Keep those fallbacks even when the events arrive, because the events aren't replayed to someone who opens the channel mid-reply.
- **A channel the backend created must be synchronized before the first message.** `createNewMessage` on a fresh `ChatChannelController` for a channel that isn't in the local DB yet is dropped; `synchronize()` it first (wrap the completion in a continuation - there is no async variant), and pass a completion to `createNewMessage` to surface errors.
- **"Conversations with the agent" needs two member filters.** `.containMembers(userIds: [me, agent])` is `members $in [...]` - it matches channels with *either* member and leaks other people's conversations with the agent. Use `.and([.containMembers(userIds: [me]), .containMembers(userIds: [agent])])`.
- **`ChannelType(rawValue:)` is internal.** Map a channel type string from the backend to `.messaging` / `.team` / ... / `.custom(value)` yourself.
- **If you clear the composer yourself** (a custom input slot), use `clearAfterSending()`, not `cleanUpData()`: `cleanUpData()` deletes the photos the composer took, which the sent message uploads later.
- **Xcode 27 app templates turn on `MemberImportVisibility`** (and default MainActor isolation): a file using `localizedDescription` or a `CGFloat` literal needs `import Foundation` even when Stream modules are imported.
- **Info.plist:** the composer's speech and photo / camera inputs crash on first tap without the usage descriptions the docs list; a location device tool also needs `NSLocationWhenInUseUsageDescription`.
- **Local backend:** the simulator reaches `localhost`, a physical device does not (use the Mac's LAN IP or a tunnel). Keep the base URL in config. For a location tool in the simulator, set one (`xcrun simctl location booted set <lat>,<lon>`).

## Verify before stopping

- `Package.resolved` has `stream-chat-swift` 5.13.0+ and no `stream-chat-swift-ai` (on the fallback: the standalone 0.12.0, with both Chat packages below 5.13.0), and the developer was told that `StreamChatAI` needs 5.13.0 and which path was taken
- a prompt gets a streamed, markdown-rendered answer from the agent in the same channel; "Thinking" shows until the first token; the stop button shows while the reply generates, and stop keeps the partial answer
- with agent steps: reasoning folds into "Thought for Ns"; each tool call shows its title, status and duration; an approval card shows on the person's device only, allow continues the call and decline shows "Declined"; a device tool call runs once and its step completes
- the contract CLI check shows `ai_generated: true`, a final `generating: false`, and the `ai_reasoning` / `ai_tool_call` attachments - and the developer was told the contract
- existing custom attachments still render; AI messages show no "Edited" label; the conversation list shows only this person's conversations
- the debug log shows `AIIndicatorUpdateEvent`s (thinking, then generating) for a prompt, not only the clear
