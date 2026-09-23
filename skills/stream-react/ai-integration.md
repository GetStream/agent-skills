# Stream React (web) - AI assistants, LLM chat, and agentic experiences

Use this runbook when a React / Next.js request involves an **LLM or AI agent**: a ChatGPT-style app, an AI assistant / support bot / copilot in chat, streaming the model's answer, a "Thinking..." indicator, "stop generating", rendering markdown / code / tables / charts from the model, a model picker, or letting the agent trigger actions in the web app (client tools).

It is a **router, not a copy of the docs**: it picks the pages to fetch and adds only what the docs do not say. Fetch the pages live, apply them, and cite what you used. **Read [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) first** - where the model runs, what the agent must send, and the CLI check are shared by every platform and live there. It composes with the track: **Track A** scaffolds first, **Track E** runs E1-E2 first, then this runbook drives the integrate step.

---

## Step 1: Classify, then fetch

Pages are `.md` twins under `https://getstream.io/chat/docs/sdk/react/guides/`:

| Shape | Signals | Fetch |
|---|---|---|
| **A. AI-first app** (ChatGPT / Claude / Gemini clone) | one user + one assistant, conversation sidebar, model picker, big prompt composer | `ai-integrations.md` (the `@stream-io/chat-react-ai` components, install, AI states) + `ai-integrations/sdk-integration.md` (wiring them into `stream-chat-react`) |
| **B. Assistant inside an existing messenger** (support bot, "ask AI", copilot) | humans and a bot in the same channels | `ai-integrations/sdk-integration.md` only - keep the app's own `MessageComposer`, message UI, and styling |
| **C. Agent acts in the web app** (open a page, fill a form, show a record) | "the assistant should do X in the app" | A or B, plus the "Client Tools" section of `ai-integrations/stream-chat-ai-sdk.md` |
| **Backend** (no agent yet, "which SDK", memory, titles) | no backend exists, or the question is server-side | `ai-integrations/stream-chat-ai-sdk.md` (Vercel AI SDK) or `ai-integrations/stream-chat-langchain-sdk.md` |

Decisions the docs leave to you:

- **Stay on the prebuilt components** - `stream-chat-react` + `@stream-io/chat-react-ai`, not a hand-built list on the low-level client. In shape B the SDK does most of the work: `isMessageAIGenerated` on `<Chat>` swaps in the built-in `StreamedMessageText` (typewriter), and the default composer swaps the send button for `StopAIGenerationButton` while the AI is thinking / generating. Add `<AIStateIndicator />` inside `<Channel>`. For rich markdown / code / tables, register a **small wrapper** on the `StreamedMessageText` slot that reads `useMessageContext().message` and renders `<StreamingMessage text={message.text ?? ""} />` - do not register `StreamingMessage` itself, the slot does not pass `text`. **Add** these to the app's existing `WithComponents` overrides - do not replace them.
- **Full custom message or composer = [`references/custom-ui.md`](references/custom-ui.md) first.** Overriding `MessageUI` (the docs still show the deprecated `Message` key) or `MessageComposerUI` with `AIMessageComposer` is writing your own component for a region; its completion contract applies.
- **Install:** `@stream-io/chat-react-ai` plus its `material-symbols` peer, with the project's package manager. It is a **0.x** package - check `npm view @stream-io/chat-react-ai version` and confirm props against the installed types before copying from the sample.

## Step 2: Fill the gaps from the reference app

The docs show each component; the **wiring around them** lives only in the reference app. Read the matching file instead of inventing it, and say the pattern came from the sample:

`https://raw.githubusercontent.com/GetStream/chat-ai-samples/main/react/src/<file>`

| Need | File |
|---|---|
| `WithComponents` overrides, lazy "new conversation" channel (`client.channel(...)` + `<Channel initializeOnMount={false}>`), layout | `components/ChatContent.tsx` |
| `AIMessageComposer` on the composer controller: uploads, model select, watch on first send, start the agent once, conversation title via `summarize` | `components/Composer.tsx` |
| Full custom AI message bubble keeping the default `str-chat__message` classes | `components/MessageBubble.tsx` |
| AI indicator gated by `useAIState` (Thinking / Generating only) | `components/AIStateIndicator.tsx` |
| Backend calls (start agent, summarize) | `api/index.ts` |
| `ai_generated` / `summary` custom-data types (`tsc` fails without them) | `stream-custom-data.d.ts` |
| CSS layer order: `stream-chat-react` -> `@stream-io/chat-react-ai` -> overrides, plus `material-symbols` | `index.css` |

Component source: `GetStream/ai-components-js` (`packages/react-sdk`); SDK side: `stream-chat-react` `src/components/AIStateIndicator/` (`useAIState`, `AIStates`) and `src/components/Message/StreamedMessageText.tsx`. The sample README points at the older `nodejs-ai-assistant` backend - same endpoints, prefer the SDK-based samples.

**Do not copy the sample's auth.** It reads a static user token from `VITE_STREAM_USER_TOKEN` and calls an unauthenticated agent URL. Use this pack's server token route ([`sdk.md`](sdk.md) > Token endpoint pattern).

## Step 3: State the contract, leave a tripwire

State the backend contract from [`../stream/ai-backend-contract.md`](../stream/ai-backend-contract.md) to the developer and run its CLI check before debugging React code. Then leave a dev-only tripwire in the `isMessageAIGenerated` function the docs already have you write, so a missing `ai_generated` shows in the console instead of as a silent plain bubble (match your bot's user id; use the stack's dev flag):

```ts
const isDev = process.env.NODE_ENV !== "production"; // Vite: import.meta.env.DEV
const warned = new Set<string>();
const isMessageAIGenerated = (message: LocalMessage) => {
  const ai = !!message.ai_generated;
  if (isDev && !ai && message.user?.id?.startsWith("ai-bot") && !warned.has(message.id)) {
    warned.add(message.id);
    console.warn(`[AI] Bot message ${message.id} has no ai_generated: true - the backend agent must set it.`);
  }
  return ai;
};
```

---

## Pitfalls the docs do not shout about

- **Replacing `MessageComposerUI` with `AIMessageComposer` drops the built-in stop button** (it lives in the default composer). Render your own: show it while `useAIState(channel).aiState` is Thinking or Generating, and call `channel.stopAIResponse()`.
- **Two `AIStateIndicator`s.** `stream-chat-react` ships a channel-aware one; `@stream-io/chat-react-ai` ships an animated one that is **not** channel-aware - gate it with `useAIState` yourself and alias the import (`AIStateIndicator as StateIndicator`), as the sample does.
- **Pass `isMessageAIGenerated` on `<Chat>`**, not per list - the channel list preview uses it too.
- **Styles:** import `@stream-io/chat-react-ai/styles/index.css` **after** `stream-chat-react/css/index.css` (the docs page omits this) and install `material-symbols`, or the composer icons render as literal words ("close", "refresh").
- **Next.js:** the AI components use browser APIs - render them only from `'use client'` modules; the agent itself never runs in a route handler. `SpeechToTextButton` needs the Web Speech API; feature-detect and hide it where unsupported.
- **No provider key in the bundle** - in particular no `NEXT_PUBLIC_*` / `VITE_*` LLM keys. Start the agent once per conversation, not on every Strict Mode remount ([`RULES.md`](RULES.md)).

## Verify before stopping

- a prompt gets a streamed, markdown-rendered answer from the bot in the same channel; "Thinking..." appears and clears; stop keeps the partial answer
- the contract CLI check passes and the developer was told the contract
- existing message / composer overrides still render (shape B); `tsc --noEmit` passes with the `ai_generated` custom type
