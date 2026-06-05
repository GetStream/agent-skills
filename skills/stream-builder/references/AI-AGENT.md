# AI Support Agent - Setup & Integration

An **additive layer on top of Chat**, not a separate product. A support ticket is a Stream `messaging` channel; a **bot user** is a member; when the customer sends a message the bot answers with an LLM. Read [CHAT.md](CHAT.md) first - the agent reuses the Chat scaffold, token route, and client components. This file adds the server-side agent loop, the LLM/knowledge choices, and the Stream-native AI wiring.

Rules: [../../stream/RULES.md](../../stream/RULES.md) (secrets, no auto-seeding, login screen first, strict mode protection).

The canonical, proven implementation of everything here is **`GetStream/nova-support-oneshot`** (`apps/web/agent/*`, `app/api/stream/webhook`, `lib/turbopuffer.ts`, `scripts/ingest.ts`, `scripts/register-webhook.ts`). Prefer distilling from it over inventing.

---

## Ask the user first (these are real decisions - do not silently default)

Before scaffolding, ask and record the answers. Each maps to a section below.

1. **LLM provider + model** - Anthropic Claude, OpenAI, or Google Gemini. Pick one explicitly and wire its key. Default: Claude (`claude-sonnet-4-6` for quality, `claude-haiku-4-5` for speed/cost). See *LLM provider selection*.
2. **Knowledge source** - `none` (facts in the prompt), `local` (embed a folder of docs into a local index), or `external` (TurboPuffer / Pinecone + ingestion script). Steer by size: tiny/static -> none or local; large/changing -> external. See *Knowledge layer*.
3. **Trigger** - server-side **webhook** (production, recommended) or **client-triggered** (demo-only). Webhook needs a public tunnel in dev. See *Server Routes*.
4. **Capabilities** - plain Q&A, or a **tool-using agent** (search knowledge, escalate to human, update ticket status). See *Agent capabilities*.

The Stream-native wiring (bot user, `ai_indicator` states, `ai_generated`, streaming, HMAC + loop guard) is always built regardless of the answers.

---

## The loop (what you are building)

```
Customer message
  -> Stream delivers it + fires the message.new webhook
  -> /api/stream/webhook: verify HMAC, drop bot echoes, return 200 in <3s, fire-and-forget the turn
  -> turn handler: load channel history (+ optional rules), build the system prompt
  -> LLM call (optionally with tools: searchKnowledge / escalate / updateTicketState)
  -> stream the answer back into the SAME channel as the bot user
       ai_indicator THINKING -> GENERATING -> send message (ai_generated: true) -> ai_indicator clear
```

Swap the trigger for a client listener and it is the demo-only variant; everything after the webhook is identical.

---

## App Integration

### Setup

**Packages** (add to a Chat scaffold):
- Server: `@stream-io/node-sdk` and/or `stream-chat` (server client via `getInstance`).
- LLM: pick ONE - `@ai-sdk/anthropic` + `ai` (recommended, provider-agnostic tool loop), or `@anthropic-ai/sdk` (simple single-call, no tools), or `@ai-sdk/openai`, `@ai-sdk/google`.
- Knowledge (only if `external`/`local`): a vector store client (`@turbopuffer/turbopuffer`, `@pinecone-database/pinecone`, or `pgvector`) + an embeddings provider (`@google/genai`, or the provider's embeddings). Anthropic has no embeddings model; pair Claude with Voyage/Gemini/OpenAI embeddings.

Install with `--legacy-peer-deps` (RULES.md > Package manager).

**Bot user** - upsert once per process, server-side, and add as a channel member:

```ts
import { StreamChat } from "stream-chat";
export const serverClient = StreamChat.getInstance(process.env.STREAM_API_KEY!, process.env.STREAM_API_SECRET!);
export const BOT_USER_ID = process.env.STREAM_BOT_USER_ID ?? "ai-bot";

let botEnsured: Promise<void> | null = null;
export function ensureBot() {
  if (!botEnsured) {
    botEnsured = serverClient.upsertUser({ id: BOT_USER_ID, name: "Support AI", role: "user" }).then(() => undefined)
      .catch((e) => { botEnsured = null; throw e; });
  }
  return botEnsured;
}
```

**Channel** - one `messaging` channel per ticket, with the customer and the bot as members, created server-side:

```ts
const channel = serverClient.channel("messaging", `support-${id}`, {
  members: [userId, BOT_USER_ID],
  created_by_id: BOT_USER_ID,
} as Record<string, unknown>);
await channel.create();
```

**Webhook registration** (only for the webhook trigger) - Stream's v2 hooks. Generate a `scripts/register-webhook.ts` and run it against the dev tunnel URL (and later the prod URL):

```ts
await serverClient.updateAppSettings({
  event_hooks: [{ hook_type: "webhook", enabled: true, webhook_url: url, event_types: ["message.new"] }],
} as Parameters<typeof serverClient.updateAppSettings>[0]);
```

In dev the URL must be public: `cloudflared tunnel --url http://localhost:<port>` (or ngrok), then register the tunnel URL. The `event_hooks` list is app-wide; re-point it when switching between local and prod (a stale tunnel URL silently breaks the agent).

### Server Routes

| Route | Method | Purpose |
|---|---|---|
| `/api/token` | GET | From CHAT.md. Also `ensureBot()` and create the support channel. Returns `{ apiKey, userId, chatToken, channelId }`. |
| `/api/stream/webhook` | POST | Stream calls this on every `message.new`. Verify, filter, fire-and-forget the turn. |

**Webhook handler** - the load-bearing route. Verify over the **raw** body, guard against the bot replying to itself, return fast:

```ts
export const maxDuration = 300; // the turn runs after the 200; keep the function alive

export async function POST(req: Request) {
  const raw = await req.text();                       // raw body BEFORE JSON.parse - HMAC needs it
  if (req.headers.get("x-api-key") !== process.env.STREAM_API_KEY) return new Response("bad key", { status: 401 });
  if (!serverClient.verifyWebhook(raw, req.headers.get("x-signature") ?? "")) return new Response("bad sig", { status: 401 });

  const evt = JSON.parse(raw);
  if (evt.type !== "message.new") return Response.json({ ok: true });
  // Bot-loop guard: ignore the bot's own messages, or it answers itself forever.
  if (evt.user?.id === BOT_USER_ID || evt.message?.user?.id === BOT_USER_ID || evt.message?.ai_generated) {
    return Response.json({ ok: true, skipped: true });
  }
  const channelId = evt.channel_id ?? evt.cid?.split(":")[1];
  processTurn(channelId).catch(console.error);        // fire-and-forget so we return in <3s
  return Response.json({ ok: true });
}
```

**Turn handler** - load history from the channel, map it to the LLM's message shape (bot -> `assistant`, everyone else -> `user`), build the system prompt, then call the agent. Read history from Stream (`channel.query({ messages: { limit: 40 } })`), not a database, for a stateless build.

**Stream bridge** - run the model and post the answer with AI state events:

```ts
const channel = serverClient.channel("messaging", channelId);
await channel.sendEvent({ type: "ai_indicator.update", ai_state: "AI_STATE_THINKING", user_id: BOT_USER_ID });
// ... start the model ...
await channel.sendEvent({ type: "ai_indicator.update", ai_state: "AI_STATE_GENERATING", user_id: BOT_USER_ID });
const text = await runModel(...);
await channel.sendMessage({ text, user_id: BOT_USER_ID, ai_generated: true });
await channel.sendEvent({ type: "ai_indicator.clear", user_id: BOT_USER_ID });
```

For **token streaming** (optional, advanced): broadcast partials with `ephemeralUpdateMessage` (no DB write, requires `stream-chat` >= 9.27) while tokens arrive, then persist once with `partialUpdateMessage`. Persisting per token hits rate limits.

**Client-triggered variant (demo-only):** skip the webhook. In the browser, listen on the channel and POST your agent route when the customer sends a message:

```ts
channel.on("message.new", (e) => {
  if (e.user?.id === userId && !e.message?.parent_id) fetch("/api/agent", { method: "POST", body: JSON.stringify({ channelId }) });
});
```

Simpler (no tunnel, no HMAC) but the bot only replies while a tab is open and listening. State this tradeoff to the user; do not ship it as production.

### LLM provider selection

Ask, then wire exactly one. Add the key to `.env` (server-side only; never `NEXT_PUBLIC_*`).

| Provider | Package(s) | Env var | Default model |
|---|---|---|---|
| Anthropic Claude | `@ai-sdk/anthropic` + `ai`, or `@anthropic-ai/sdk` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` (or `claude-haiku-4-5`) |
| OpenAI | `@ai-sdk/openai` + `ai` | `OPENAI_API_KEY` | `gpt-5` class |
| Google Gemini | `@ai-sdk/google` + `ai` | `GOOGLE_GENERATIVE_AI_API_KEY` | `gemini-3-pro` class |

Recommended path: the **Vercel AI SDK** (`ai` + `@ai-sdk/<provider>`) with `streamText({ model, system, messages, tools, stopWhen: [stepCountIs(8), hasToolCall("escalateToHuman")] })`. It is provider-agnostic and supports the tool loop. For a no-tools, no-RAG build, a single `@anthropic-ai/sdk` `messages.create` call is fine and lighter. Use prompt caching on the static system/KB portion regardless of provider.

**A missing key is a visible warning, never a silent failure.** The user may select a provider whose key is not set yet (they pick Claude but `ANTHROPIC_API_KEY` is absent, etc.). Check for the selected provider's key at request time, BEFORE calling the model. If it is missing, do not throw or return a 500 - post a normal channel message as the bot saying it is not configured, naming the exact env var, then return. The chat stays alive and the developer (or end user) sees precisely what to fix instead of a dead, silent conversation.

```ts
if (!process.env.ANTHROPIC_API_KEY) {
  await channel.sendMessage({
    text: "I'm not fully configured yet (missing ANTHROPIC_API_KEY). Add it to .env and restart to enable AI answers.",
    user_id: BOT_USER_ID,
    ai_generated: true,
  });
  return; // also clear the ai_indicator if one was already sent
}
```

### Knowledge layer

Choose per the user's answer.

- **none** - put a short, static fact sheet directly in the system prompt (use prompt caching). Good for a handful of policies. Does not scale and cannot cite.
- **local** - embed a folder of docs into a local index (`pgvector`, LanceDB, or an in-memory cosine index for small sets). No external account. Good for a self-contained demo with real retrieval.
- **external** - a managed vector store (TurboPuffer, Pinecone) plus an ingestion script. Good for large or frequently-changing knowledge.

For `local`/`external`, expose retrieval as a **tool the model calls** (`searchKnowledge`), not always-on prompt stuffing - that is what makes it an agent. Ground it: instruct the model to call retrieval **before** asserting product facts and to cite `source_url`; if two queries return nothing relevant, say so or escalate.

Retrieval shape (nova's TurboPuffer pattern): embed the query, run vector ANN **and** BM25 in parallel, fuse with Reciprocal Rank Fusion. Embedding asymmetry is mandatory: ingest with `RETRIEVAL_DOCUMENT`, query with `RETRIEVAL_QUERY` (mixing them silently halves recall). One namespace per knowledge set. Ingestion (`scripts/ingest.ts`): crawl/read docs, chunk by heading (~800 tokens), embed, upsert `{ id, vector, text, source_url, title }`.

### Agent capabilities (tools)

Define tools the model can call (Vercel AI SDK `tool({ description, inputSchema, execute })` - note `inputSchema`, not `parameters`):

| Tool | Purpose |
|---|---|
| `searchKnowledge` | Retrieve grounding passages (see Knowledge layer). The anti-hallucination tool. |
| `escalateToHuman` | Hand off: mark the channel/ticket, optionally notify (email, dashboard queue). Fire on distress, legal threats, or "I want a human". |
| `updateTicketState` | Move a ticket to resolved/closed, only after the user confirms. |
| `mockApiCall` | Stubbed transactional action (refund/cancel) when there is no real backend. |

For a stateless build with no database, `escalateToHuman` can simply post a system message and stop the bot; persistence (tickets, rules, analytics) is the next tier up.

### Client Patterns

- Reuse the Chat client + components from CHAT.md (`useCreateChatClient`, `<Chat>`, `<Channel>`, `<MessageList>`, `<MessageComposer>`).
- For AI rendering, `@stream-io/chat-react-ai` provides a streaming message component + an AI state indicator that consumes the `ai_indicator` events automatically. Without it, the default typing indicator still shows while the bot "types"; the `ai_indicator` states drive the thinking/generating UI.
- Show a clear **bot identity** (name + "AI agent" badge) so the customer knows they are talking to an AI, and surface escalation ("talk to a human").

### Gotchas

- **HMAC over the raw body.** `await req.text()` first, verify, then `JSON.parse`. Never `req.json()` before verifying.
- **Bot-loop guard is mandatory.** Filter `user.id === BOT_USER_ID` and `message.ai_generated`, or the bot answers its own messages forever.
- **Webhook must return <3s.** Fire-and-forget the turn; set `export const maxDuration = 300` so the function stays alive to finish it.
- **Streaming needs the two-call split.** `ephemeralUpdateMessage` (broadcast, no DB, >= 9.27) for intra-response flushes, exactly one `partialUpdateMessage` to persist. Per-token persistence trips rate limits.
- **`ai_indicator` events** carry `user_id` = the bot, and use `AI_STATE_THINKING` / `AI_STATE_GENERATING` / `ai_indicator.clear`.
- **Embedding asymmetry** - `RETRIEVAL_DOCUMENT` (ingest) vs `RETRIEVAL_QUERY` (query). Wrong pairing halves recall.
- **Don't prompt-stuff a large KB** - use retrieval as a tool past a page or two.
- **Vercel AI SDK v5/v6** uses `inputSchema`, not `parameters`. v4 examples compile but never register the tool.
- **Next.js 16 middleware file is `proxy.ts`**, not `middleware.ts`.
- **Missing LLM key: warn in-channel, don't 500.** If the selected provider's key is absent at request time, post a bot message naming the missing env var and return, rather than failing silently. Keeps the chat alive and the cause obvious.
- **Client-triggered trigger is demo-only** - the bot is silent when no tab is connected. Webhook is the real pattern.

---

## Recommended default stack (if the user is unsure)

Next.js (Chat scaffold) + `@stream-io/node-sdk` + Vercel AI SDK with Anthropic (`claude-sonnet-4-6`) + a webhook trigger + a `local` knowledge index, exposed to the model as a `searchKnowledge` tool, plus `escalateToHuman`. This is a real agent with grounding and a human handoff, runnable on one machine (the only external dependency beyond Stream + the LLM key is the dev tunnel for the webhook). Scale up to an external vector store and persistence when the knowledge or operator needs grow.

## Reference implementation map (nova-support-oneshot)

- Webhook + verify + loop guard: `apps/web/app/api/stream/webhook/route.ts`
- Turn loader (history -> messages, rules, prompt): `apps/web/agent/run.ts`
- Stream bridge (ai_indicator + streaming + send): `apps/web/agent/stream-bridge.ts`
- Tools (searchKnowledge, escalate, updateTicketState, mockApiCall): `apps/web/agent/tools.ts`
- System prompt + grounding contract: `apps/web/agent/prompt.ts`
- RAG (hybrid search + RRF, embeddings): `apps/web/lib/turbopuffer.ts`
- Ingestion (crawl, chunk, embed, upsert): `apps/web/scripts/ingest.ts`
- Webhook registration: `apps/web/scripts/register-webhook.ts`
- Gotchas, expanded: `nova-spec.md` section 9
