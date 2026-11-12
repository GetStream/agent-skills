# AI chat in React

Run this when the app talks to an LLM through Chat: a ChatGPT-style app, an assistant or
copilot inside an existing chat, streaming answers with a thinking indicator and stop, an
agent that acts in the app (client tools), or an agent that answers with UI (generative
UI: A2UI, OpenUI). For a support bot or help desk, follow ai-support-agent.md first - it
builds the backend; this file adds the UI. For an agent on Stream Agents
(`@stream-io/stream-agents`), follow stream-agents.md instead - it covers the session and the
UI; only this file's "Generative UI" section applies there too.

Stream doesn't host the model. A backend agent (a bot user) answers in the channel by
updating one message and sending `ai_indicator.*` events. The app renders and triggers -
it never calls the LLM or holds a provider key, Stream secret, or admin token.

## Docs

Pin the Chat major first (chat-versions.md), then find the AI pages in that major's docs
rather than at fixed paths - their names and places move between majors:

```bash
d=$(getstream docs chat-sdk/react/v<major>)
grep -niE "ai|generative|langchain|reasoning|tool" $d/INDEX.md
```

| Need | Page (by title) |
| --- | --- |
| The AI components: what they are, install and stylesheets, theming, migrating | "Quickstart" (`ai-components.md`) |
| AI replies in the regular message list and composer | "SDK integration" * |
| An agent conversation laid out by turn, reasoning, tool calls and approvals | "Conversation view", "Reasoning and tool calls" |
| The prompt composer: attachments, dictation, stop | "Composer" |
| Streaming markdown, code and tables in a reply | "Streaming messages" |
| A voice agent's glow or wave | "Voice visualizations" |
| UI in a reply: A2UI, OpenUI, your own components | "Generative UI" |
| A backend: Vercel AI SDK or LangChain, client tools | "Stream Chat AI SDK" *, "Stream Chat LangChain SDK" * |

\* Not in the CLI's docs copy (the pages are unlisted on the site). Fetch the Markdown from
the site instead: unversioned for the latest major - the one `getstream docs chat-sdk/react`
resolves to - and with `v<major>` for an older one (a versioned URL for the latest major
404s):

```bash
p=sdk-integration   # or stream-chat-ai-sdk, stream-chat-langchain-sdk
curl -fsSL https://getstream.io/chat/docs/sdk/react/ai-components/$p.md            # latest major
curl -fsSL https://getstream.io/chat/docs/sdk/react/v<major>/ai-components/$p.md   # older major
```

Use the response only if its first line starts with `# ` (the page title); anything else is
an error page, not the docs.

An AI-first app (one user + one assistant, conversation sidebar, model picker) needs the
Quickstart and SDK integration, and usually the conversation view. An assistant inside an
existing messenger needs SDK integration only - keep the app's own composer, message UI,
and styling. An agent that acts in the app adds the client tools section of the AI SDK
page.

## Backend

Two shapes work:

- **Webhook turn** - a `message.new` webhook route runs one LLM turn with the server SDK
  and returns. Fits a Next.js route; ai-support-agent.md builds it.
- **Long-lived agent** - `@stream-io/chat-ai-sdk` (Vercel AI SDK) or
  `@stream-io/chat-langchain-sdk` with `AgentManager`. It holds a WebSocket per channel,
  so it runs as its own process, not a serverless function. Reference servers:
  `GetStream/chat-ai-samples` `ai-sdk-sample` and `langchain-sample`.

If it's unclear whether a backend exists, ask which one to use. Start agents through an
authenticated route, once per conversation after the channel is watched - never on every
render or remount - and allowlist the model on the server.

The app can't tell when the agent skips a field - it builds and looks subtly wrong. Tell
the developer what the agent must send, and have them confirm it for their own backend:

- `ai_generated: true` when the reply is created. Missing: a plain bubble with no
  typewriter or markdown, no generative UI, and a custom agent can answer its own
  messages in a loop.
- One message, updated as tokens arrive: `ephemeralUpdateMessage` for throttled chunks,
  one final `partialUpdateMessage` to persist it (`$(getstream docs
  chat/node)/ai-message-streaming.md`). Posted once, complete, it appears all at once.
- `ai_indicator.update` (`AI_STATE_THINKING`, `AI_STATE_GENERATING`, ...) while working,
  `ai_indicator.clear` when done. Missing: no thinking indicator and no stop button.
- Honor `ai_indicator.stop`: abort the model call, keep the partial text. Missing: stop
  does nothing.
- `generating: true` on partials, `false` on the final update, stop, and error. React
  ignores it, but iOS needs it - set it so one backend serves every client.

Stream's server SDKs already do all of this. Check a real bot message after one prompt,
before debugging React code:

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"messaging:<channel-id>"},"message_limit":5}' \
  --jq '.channels[0].messages[] | {user: .user.id, ai_generated: (if has("ai_generated") then .ai_generated else .custom.ai_generated end), generating: (if has("generating") then .generating else .custom.generating end), text: (.text // "" | .[0:40])}'
```

`null` on a bot message means the agent isn't setting it - fix the agent, not the app.

## Client

The AI components are part of `stream-chat-react`, behind the
`stream-chat-react/ai-components` entry point, with their own stylesheet. The standalone
`@stream-io/chat-react-ai` package is deprecated: don't install it. An app that already
uses it moves over with the Quickstart page's "Migrating from `@stream-io/chat-react-ai`"
section (imports, stylesheet path, class-name prefix, a few renamed props). Take import
paths and props from the pinned major's docs and the installed types. Defaults to keep in
SKILL.md applies to every override below.

- Pass `isMessageAIGenerated` on `<Chat>`, not per list - the channel list preview uses
  it too.
- For rich markdown / code / tables in the regular message list, follow SDK integration's
  "Using StreamingMessage instead": a small wrapper on the `StreamedMessageText` slot that
  reads the message from context. Registering `StreamingMessage` directly on the slot
  renders nothing - the slot doesn't pass `text`. Add to the app's existing
  `WithComponents` overrides; don't replace them.
- Load the AI components' stylesheet after the SDK's, as the Quickstart's "Step 2: Install
  the SDKs" shows.
  Without it the composer and indicators render unstyled.
- Replacing the composer with `AIMessageComposer` drops the built-in stop button. Render
  one while `useAIState(channel).aiState` is thinking or generating, calling
  `channel.stopAIResponse()`.
- Both the main entry point and `ai-components` export an `AIStateIndicator`. The main
  one is channel-aware; the `ai-components` one only renders text - gate it with
  `useAIState` and alias one of the imports.
- The AI components use browser APIs - render them from `'use client'` modules. Speech
  input needs the Web Speech API; hide it where unsupported.
- No LLM key in the bundle (`NEXT_PUBLIC_*`, `VITE_*`).
- Client tools arrive as `custom_client_tool_invocation` events on the channel. Confirm
  with the user before any tool that changes data, and validate `args` - they're model
  output.

## Generative UI: A2UI and OpenUI

Use this when the agent should answer with UI - cards, a form, a map, a plan with
choices - instead of only text. Read the pinned major's "Generative UI" page in full
first; it is the source for every name below.

The pieces, as the docs describe them:

- An `AIUIHost` from `stream-chat-react/ai-components` holds the renderers, the app's own
  components the agent may place, the app's tools, and `send` for what the user does.
  `AIConversation` shows each reply's UI in place of its text.
- One renderer per format the agent writes, each its own entry point:
  `stream-chat-react/a2ui` (A2UI) and `stream-chat-react/openui` (OpenUI). A format with
  no renderer listed shows the reply's text. A custom format gets a renderer of your own.
- The reply's UI travels in a custom field of the agent's message, the reply's text stays
  readable on its own, and what the user does comes back as the user's next message with
  the action in a custom field (or through Stream Agents' session API). The page has the
  field names and shapes; type them by augmenting `CustomMessageData` as it shows.

What the docs leave to you:

- **Install each renderer's packages at the versions the docs name.** They are optional
  peers of `stream-chat-react`, on 0.x release lines that change their API between
  minors - don't install `latest`. Check the page's React requirement for each renderer
  against the app's React.
- **Import what each format needs once**, as Installation shows (OpenUI has its own
  stylesheet). The A2UI entry point is ES module only.
- **Tell the model what the app can show.** Without instructions the agent never writes
  UI: send the host's capabilities to the backend when a conversation starts, or generate
  the instructions at build time with the helpers each renderer entry point exports (see
  "Tell the agent what the app shows").
- **The backend owns the field.** Models write UI inside the reply text (for example a
  fenced block); the backend must move it into the message's UI field as the reply
  streams - Stream Agents does this, a backend of your own must. Missing: the raw markup
  shows as text. Tell the developer, as with the fields in Backend.
- **Keep one host per conversation** (`useMemo` on what it depends on). A new host per
  render resets every reply's UI state.
- **Treat the reply's UI as untrusted.** Keep the host's default link policy (web and
  email only) unless the user asks otherwise, validate what app tools receive, and confirm
  actions that change data before they run.
- **Route errors.** Replies fall back to text when their UI can't show; pass `onError`
  to the host and renderers and forward what the agent should hear about to the backend.
- **Theme with the AI components' tokens**, not each format's own styles, unless only one
  format should change ("Theming" on the page).
- OpenUI's packages report the install to OpenUI's analytics unless disabled - mention
  the page's note on it to the user.

## Reference implementation

The docs name the SDK's own example app for the AI components (`examples/ai-chatbot` in
`GetStream/stream-chat-react`); read it for wiring the docs don't show - overrides, a lazy
"new conversation" channel, the composer, the state indicator, the custom-data types `tsc`
needs, and stylesheet order. Don't copy auth from any sample; use the token route from
SKILL.md.

## Verify

A prompt gets a streamed, markdown-rendered answer from the bot in the same channel; the
thinking indicator appears and clears; stop keeps the partial answer; the QueryChannels
check shows `ai_generated: true` and a final `generating: false`; existing message and
composer overrides still render; `tsc --noEmit` passes. With generative UI: a reply with UI
renders it as it streams, a reply in a format without a renderer shows its text, and
acting in the UI sends the user's next message with the action attached.
