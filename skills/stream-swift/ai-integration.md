# Stream Swift - AI assistants, LLM chat, and agentic experiences

Use this runbook when the iOS request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, thinking indicators, "stop generating", rendering markdown / code from the model, showing the agent's reasoning and tool calls, asking the person before a tool runs (approvals), letting the agent run tools on the device, or showing what was said to a **voice agent** as a conversation.

Like the rest of this skill, it is a **router, not a copy of the docs**: it picks the pages to fetch, and adds only what the docs do not say. Fetch the pages live and apply them; cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send (including the `generating` flag iOS depends on, and the agent-steps format for reasoning / tool calls / approvals), and the CLI check are shared by every platform and live there.

---

## Step 0: Which StreamChatAI (decide before any code)

**`StreamChatAI` ships in `stream-chat-swift` from 5.13.0** (GetStream/stream-chat-swift#4306, released 2026-10-09), as a library product next to `StreamChat` and `StreamChatCommonUI`. Before that it was the standalone `stream-chat-swift-ai` package (last release 0.12.0), which is now the **fallback**. Both declare a target named `StreamChatAI`, so an app has one or the other, never both: SPM refuses the graph even when the app links only `StreamChat` from 5.13.0+ (`multiple packages ('stream-chat-swift', 'stream-chat-swift-ai') declare targets with a conflicting name: 'StreamChatAI'`).

**The latest release is 5.15.0** (2026-10-22, both Chat packages). It adds to `StreamChatAI`: `AIConversationView` (an assistant-style conversation list, with `AIMessage` and ready-made message views), `AIToolAuthorizationView` (a tool call that waits for the person to sign in at a provider), and the voice visualizations `AIVoiceGlowView` / `AIVoiceWaveView`. `StreamChatAI` now embeds Splash and swift-markdown-ui instead of depending on their packages, so an app that imports `MarkdownUI` or `Splash` itself must add those packages directly when it updates. The rest of the release is core-client additions and fixes. `stream-chat-swiftui` 5.15.0 requires `stream-chat-swift` 5.15.0+, so a fresh resolve of `from: "5.13.0"` takes both to 5.15.0.

Read the app's `Package.resolved` (or the project's package references), pick the row, and **tell the developer that `StreamChatAI` needs `stream-chat-swift` 5.13.0 or later, and `AIConversationView` 5.15.0**, and which path you took:

| The app has | Do |
|---|---|
| no Chat yet | **Default.** Link `StreamChat` + `StreamChatAI` from `stream-chat-swift` `from: "5.15.0"`. That is all `AIConversationView` needs. Add `StreamChatSwiftUI` from `stream-chat-swiftui` `from: "5.15.0"` only for the message-list alternative (Step 1) or the SDK's channel list (its 5.15.0 requires `stream-chat-swift` 5.15.0+ anyway). |
| Chat 5.13.0 or 5.14.0 | Keep it for the components those releases have. When the app needs one that is new in 5.15.0 (`AIConversationView`, `AIToolAuthorizationView`, the voice visualizations), **suggest raising both Chat packages to `from: "5.15.0"`**. The only source change to check is the `MarkdownUI` / `Splash` note above. |
| Chat 5.x below 5.13.0 | **Suggest the version update:** raise both Chat packages to `from: "5.15.0"` (Xcode: the package's Dependency Rule, then File > Packages > Update to Latest Package Versions). Per the changelogs, the source changes to check are `Device.createdAt`, now non-optional (5.13.0), and the `MarkdownUI` / `Splash` note (5.15.0). If the developer can't update now, take the fallback. |
| the standalone `stream-chat-swift-ai` | **Suggest migrating with the update:** remove the `stream-chat-swift-ai` package in the same change that raises Chat to 5.15.0, link the `StreamChatAI` product of `stream-chat-swift` instead, then follow the docs' "Migrating from stream-chat-swift-ai" (`.../guides/ai-integrations.md`: rename table, `AIAppearance` instead of `colors:`, `isGenerating` on the view model, `AIClientTool` + `AIClientToolRunner`). If they'd rather not migrate yet, the app stays on the fallback. |
| Xcode 26 or older, no move to Xcode 27 | **Fallback.** Adding `StreamChatAI` from `stream-chat-swift` with SPM needs Xcode 27 (Xcode 26 rejects the target). |

**The fallback (standalone package).** Pin `stream-chat-swift-ai` to 0.12.0 and keep `stream-chat-swift` and `stream-chat-swiftui` below 5.13.0 (`.upToNextMinor(from: "5.12.0")`), or SPM rejects the graph. 0.12.0 is iOS 16+, depends on the MCP Swift SDK (swift-nio, swift-log, ...), and has the API the docs' migration section lists as the old one: `ComposerView(viewModel:colors:isGenerating:onMessageSend:onStopGenerating:)`, per-view `colors:` arguments, an `AIClientTool` with only `name` + `run`, and tools described with MCP `Tool` through `ClientTool` / `ClientToolRegistry`. It does have the parts, approval, client-tool runner and on-device model types. The docs no longer show its API, so take its signatures from that tag's `Sources/StreamChatAI`. Tell the developer the fallback is a stopgap and updating to 5.15.0 is the way forward.

**The docs are current through 5.15.0** (install, requirements, `Info.plist` keys, migration, appearance, reasoning / tool calls / approvals, client tools, the on-device model, and `AIConversationView` on its own page). Where the docs and the code disagree, the source at the resolved version wins (`stream-chat-swift` `Sources/StreamChatAI`; the local SPM checkout, see [`docs-map.md`](docs-map.md) "When the docs fall short") - say so.

**`AIConversationView` needs 5.15.0.** On 5.13.0 or 5.14.0, suggest the update. If the developer can't update now, build the screen from the 5.13.0 parts (`StreamingMessageView` for the agent's lines, in a plain `ScrollView`) and tell them what the update replaces.

## Step 1: Classify, then fetch

| Shape | Signals | Fetch (prefix `https://getstream.io/chat/docs/sdk/ios/guides/ai-integrations`) |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation sidebar, suggestion chips, big prompt composer | `/conversation-view.md`, and `.md` (components, install, appearance, and "Best practices": `ai_generated`, indicator events, stop, ephemeral updates). `/swiftui-integration.md` only for the message-list alternative |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in the same channels | `/swiftui-integration.md` and the `.md` "Best practices" section - this is the message-list path: keep the app's own message list, composer and styling |
| **C. Agent that shows its work and asks first** (reasoning, tool calls, "ask before it books / shares / deletes") | approvals, tool use, "search for tools", transparency | A or B, plus `/reasoning-and-tool-calls.md` and the contract's "Agent steps" section |
| **D. Agent acts on the device** (read location, device settings, copy to clipboard, open a screen) | "the assistant should do X on the phone" | A or B, plus `/client-side-tools.md`: "Run tool calls from agent steps" for an agent that writes `ai_tool_call` steps, "Run tool calls from events" for Stream's AI SDK / LangChain SDK (they send `custom_client_tool_invocation` instead) |
| **E. Voice agent transcript** (the person talks to an agent on a Stream Video call; the app shows what was said as a conversation) | "voice agent", Vision Agents, OpenAI Realtime on a call, "transcript", "show what was said", "chat view of the voice session", history of past voice sessions | `/conversation-view.md` and "Shape E" below; `https://getstream.io/video/docs/ios/ui-cookbook/closed-captions.md` when captions are the source |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | `/stream-chat-ai-sdk.md` (Vercel AI SDK) or `/stream-chat-langchain-sdk.md` - and check whether it writes agent steps (contract) |

Decisions the docs leave to you:

- **Show the conversation with `AIConversationView`.** It is the primary way to show one person's conversation with an agent: shapes A and E, and C / D on top of A. Each question moves to the top while its reply writes out below it. Thinking, a message on its way, older messages, approvals, sign-ins and reply actions are built in (`/conversation-view.md`).
- **The alternative is the `StreamChatSwiftUI` message list with the AI components plugged in** (`/swiftui-integration.md`). Take it when the conversation needs what a messenger has and `AIConversationView` doesn't (reactions, threads, read state, several people in the channel), or when the app already shows that channel with `StreamChatSwiftUI` (shape B). In shape B, keep existing custom attachments and list modifiers when you add the AI ones - overriding the slot replaces the default (composite-slot trap in [`design-matching.md`](design-matching.md)).
- **Never a hand-built list** on the low-level client ([`custom-ui.md`](custom-ui.md)), for a typed chat or a voice agent's transcript (shape E). Tell the developer which of the two you used and why.
- **Install:** run [`setup.md`](setup.md) first (Chat v5), then add the products from Step 0.
- **UIKit:** `StreamChatAI` is SwiftUI-only. Host its views with `UIHostingController`, or build the AI screen in SwiftUI.

## Step 2: Wire the components (what the docs leave out)

The docs show each component, the conversation view and the StreamChatSwiftUI wiring. These are the gaps found building working apps:

1. **The conversation (`AIConversationView`).** Wrap the channel's messages as the docs' `ChatAIMessage` (the controller lists newest first, so reverse them). Drive `isThinking` from the indicator handler and pass `approver` and `loadOlderMessages`. Put `AIComposerView` below the list, or over it with `safeAreaInset(edge: .bottom)`. Pass what was just sent as `pendingMessage` until its reply starts, so the question shows at once even while the channel is created or photos upload. This path needs no `StreamChatSwiftUI`: no `StreamChat` wrapper object and no `ViewFactory`. Theme it with `AIAppearance`, and change rows through `AIConversationViewFactory`.
2. **The message-list alternative.** Conform to `MessageTypeResolving` as the SwiftUI integration page does - `MessageTypeResolver` is `public`, not `open`, so it can't be subclassed. The `makeCustomAttachmentViewType(options:)` slot renders bare (no bubble), so the reply is full width. For an AI-first app on this path, set `MessageListConfig(shouldMessagesStartAtTheTop: true)` so a new conversation reads from the top like a document instead of hugging the composer; `MessageListView` applies it itself and still anchors to the newest message once the list fills the screen.
3. **Approvals.** Hold one `AIToolApprover` per signed-in user and install, and pass it to `AIConversationView(approver:)` (on the message-list path, the view factory is a good owner). Its `decide` closure posts `{tool_call_id, client_id, allowed}` to an authenticated backend endpoint, which checks the caller and updates the step.
4. **Device tools.** The registration has no display title or approval spec: if the backend should ask before a device tool runs, send those alongside (an `Encodable` wrapper that encodes the SDK registration and then its own keys into the same keyed container). Hand `runner.run(parts)` every agent `MessageNewEvent` / `MessageUpdatedEvent` (a `chatClient.eventsController()` delegate) as well as the replies already loaded when the conversation opens - a view alone runs only while the reply is on screen. Request OS permissions inside `run`.
5. **Stop.** Set `composerViewModel.isGenerating` from the indicator events as the docs show. Send `AIIndicatorStopEvent(cid:)` through a channel events controller (the client-wide `EventsController` has no `sendEvent`), and keep that controller alive until the completion fires.
6. **Session.** If the backend issues expiring tokens, connect with `connectUser(userInfo:tokenProvider:)`: `connectUser(userInfo:token:)` rejects a token that has an expiry.

The reference app (`https://raw.githubusercontent.com/GetStream/chat-ai-samples/main/ios/AIComponents/<file>`: `AIComponentsApp.swift` init + message resolver, `AIComponentsFactory.swift`, `TypingIndicatorHandler.swift`, `AgentService.swift`, `ContentView.swift`) shows the message-list path. It still imports `MCP` and the standalone package: apply the docs' migration steps when you copy from it.

## Step 3: State the contract, leave a tripwire

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer - on iOS both `ai_generated` and `generating` are required, and the agent-steps attachments are what the parts views render - and run its CLI check before debugging Swift code. Then leave a debug-only tripwire where messages are mapped (your `AIMessage` wrapper, or the message resolver on the message-list path), so a missing field shows in the Xcode console. On the message-list path a missing `ai_generated` is a silent plain bubble. The docs' `ChatAIMessage` takes the role from the sender, so there it shows nothing at all, yet the contract still needs it, for other clients and so the agent can tell its own replies apart (match your agent's user id):

```swift
#if DEBUG
if message.extraData["ai_generated"]?.boolValue != true, message.author.id == agentUserID {
    print("[AI] Agent message \(message.id) has no `ai_generated: true` - the backend agent must set it.")
}
#endif
```

## Shape E: a voice agent's transcript as a conversation

The person talks to an agent on a Stream Video call (Vision Agents, OpenAI Realtime, or the developer's own agent), and the app shows what was said as a chat: a transcript panel during the call, the history after it, or a voice mode next to a typed chat with the same agent. Left alone this becomes a hand-built `ScrollView` of bubbles (the closed-captions docs page shows one). When it fits, use **`AIConversationView`** instead. It shows the person's lines as bubbles and the agent's as streamed Markdown. Each new line goes to the top with the reply writing out below it, and the view has a thinking state, a scroll-to-latest button and loading of older lines. It takes any `AIMessage` (`id`, `role`, `text`, `isGenerating`) and needs no Chat client, so any transcript source maps onto it.

**Check the fit first**, and tell the developer which way you went:

| The request | Use |
|---|---|
| One person and one agent, shown as a running conversation | **`AIConversationView`** |
| Subtitles over the call: a line or two that follow the voice and fade | A caption band from the closed-captions page. This is not a conversation, and the agent's text arrives ahead of its voice |
| A meeting with several people, with or without an agent | Not this view: it starts a turn at each of the person's messages and draws every other role as the agent. Use a custom list, or the `StreamChatSwiftUI` message list when the transcript is in a Chat channel |
| People and a bot chatting in the same channels | Shape B |

**Where the lines come from.** Map each source to one `AIMessage` type:

- **A Chat channel the agent writes.** Vision Agents keeps the conversation in a Chat channel whose id is the call's id: `messaging:<call id>` in the released Python SDK (0.6.x), `agent:<call id>` on newer, unreleased builds. It posts the person's words as their messages and the agent's as the agent user's, streamed with `generating` (ephemeral updates, then a final partial update). Watch the channel with a `ChatChannelController` (synchronize it first) and wrap its messages as the docs' `ChatAIMessage` does (`/conversation-view.md`, "Messages from Stream Chat"). A few things are specific to a transcript:
  - `role`: keep the docs' `isSentByCurrentUser` rule. Don't key on `ai_generated` or `source` here: the released Python SDK doesn't set `ai_generated`, and the Go agent sets `source: "agent"` on every message, the person's included.
  - Long text: the Python edge splits anything over 1000 characters into several messages that share `extraData["chunk_group"]`, ordered by `chunk_index`. Join them into one.
  - Paging: pass `loadOlderMessages` (from `loadPreviousMessages`) while `!hasLoadedAllPreviousMessages`.
  - Membership: the person must be a member of the channel, or reading it fails with a permission error. The released Python SDK adds nobody outside `open_demo`, so with it the backend must add the person once the agent has created the channel (`channel.update(add_members=...)`). Newer builds add the people on the call. If the backend can't be changed, take the captions path instead, and tell the developer why.
- **Closed captions** (no Chat needed). `call.state.closedCaptions` keeps only the latest two, for about 2.7 s: fine for subtitles, lossy for a transcript. Instead, consume `call.subscribe(for: ClosedCaptionEvent.self)` for as long as the call runs, and append each event's `closedCaption`. A caption from the person's own user id (`closedCaption.user.id`) is `.user` and any other is `.assistant`, and consecutive captions from the same speaker join into one message. Captions must be on for the call type (`auto-on`, or `call.startClosedCaptions()` with the permission; see the closed-captions page). They arrive as finished segments, so the agent's lines show whole rather than typed out.
- **The agent framework's own events**, such as a client SDK that hands over transcript turns, or custom call events. Map its turns the same way: who spoke, the text, and whether it is still being written.

**Wiring:**

1. Build an oldest-first array of one `AIMessage` type: the docs' `ChatAIMessage` for a Chat channel (the controller lists newest first, so reverse it), or a small type of your own for captions (`struct TranscriptLine: AIMessage { let id: String; let role: AIMessageRole; var text: String; var isGenerating = false }`). Keep each line's id stable across updates (a message id, or the speaker plus the first caption's start time): a changing id rebuilds the row and loses the scroll position.
2. `AIConversationView(messages: lines, isThinking: ..., emptyContent: { ... })`. `isThinking` is optional. Set it from the agent's state when the app has one (from the person's last words until the agent's line appears). The view already shows thinking while the latest reply is `isGenerating` with no text. The default view factory needs nothing. Conform to `AIConversationViewFactory` only to change a row (the docs' "Customize the messages").
3. Put the call controls (mute, hang up, the voice visualization) below the list, or over it with `safeAreaInset(edge: .bottom)` so the list knows how much of it is covered. If the person can also type to the agent, put `AIComposerView` there too, and pass what they sent as `pendingMessage` until its copy arrives.
4. Packages: `StreamChatAI` depends only on `StreamCore`, so for the captions path a Video-only app adds just that product from `stream-chat-swift`. The Chat-channel path also needs `StreamChat`. Keep the `ChatMessage` mapping in a file that imports `StreamChat` + `StreamChatAI`, and the call screen in one that imports `StreamVideo` (+ `StreamChatAI`). Never import `StreamChat` and `StreamVideo` in the same file ([`RULES.md`](RULES.md) "Chat + Video name collisions").

---

## Pitfalls the docs do not shout about

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
- the developer was told the conversation renders with `AIConversationView`, or why the message-list alternative was taken
- on the message-list path, existing custom attachments still render and AI messages show no "Edited" label; the conversation list shows only this person's conversations
- shape E: the developer was told why `AIConversationView` fits (or why not) and that it needs 5.15.0. The person's lines are bubbles at the trailing edge and the agent's are full-width Markdown; a line on the wrong side means the role check is keyed on the wrong field. A long answer is one message, every line stays after the captions fade, and reopening shows the history (Chat path)
