---
use_case: ai-support-agent
signals: ["ai support agent", "support bot", "help desk", "rag chat", "customer support ai", "ai customer support"]
products: [chat]
load_with: [CHAT.md]
---

# AI Support Agent - Setup & Integration

An **additive layer on top of Chat**, not a separate product. A support ticket is a Stream `messaging` channel; a **bot user** is a member; when the customer sends a message the bot answers with an LLM. Read [CHAT.md](../CHAT.md) first - the agent reuses the Chat scaffold, token route, and client components. This file adds the server-side agent loop, the LLM/knowledge choices, and the Stream-native AI wiring.

Rules: [RULES.md](../../../stream/RULES.md) (secrets, no auto-seeding, login screen first, strict mode protection).

The canonical, proven implementation of everything here is **`GetStream/nova-support-oneshot`** (`apps/web/agent/*`, `app/api/stream/webhook`, `lib/turbopuffer.ts`, `scripts/ingest.ts`, `scripts/register-webhook.ts`). Prefer distilling from it over inventing.

---

## Ask the user first (these are real decisions - do not silently default)

Before scaffolding, ask and record the answers. Each maps to a section below.

1. **LLM provider + model** - Google Gemini, Anthropic Claude, or OpenAI. Pick one explicitly and wire its key. Default: **Gemini** (`gemini-2.5-flash`, or `gemini-2.5-pro` for higher quality) - using Gemini also covers embeddings for the knowledge layer, so a single provider powers both chat and RAG. Claude (`claude-sonnet-4-6`) and OpenAI are equally supported. See *LLM provider selection*.
2. **Knowledge source** - `none` (facts in the prompt), `local` (embed a folder of docs into a local index), or `external` (TurboPuffer / Pinecone + ingestion script). Steer by size: tiny/static -> none or local; large/changing -> external. See *Knowledge layer*.
3. **Trigger** - server-side **webhook** (production, recommended) or **client-triggered** (demo-only). The webhook needs a public tunnel registered in dev or the bot never replies - treat connecting it as a required final step, not optional setup. See *Connect the webhook in dev*.
4. **Capabilities** - plain Q&A, or a **tool-using agent** (e.g. search knowledge, update ticket status). See *Agent capabilities*.
5. **Optional add-ons** - a **multi-select** of extra capabilities that bring the build closer to a full support product (persistence, operator dashboard + live rules, real human escalation, OpenAPI lookup, a transactional action, real auth, voice). Present them as **checkboxes with none checked by default**: the user can skip them all (the lean, reliable grounded agent) or tick what they want, and each is built with the stack in *Optional add-ons*. Never build an unchecked one. See *Optional add-ons*.

The Stream-native wiring (bot user, `ai_indicator` states, `ai_generated`, streaming, HMAC + loop guard) is always built regardless of the answers.

---

## The loop (what you are building)

```
Customer message
  -> Stream delivers it + fires the message.new webhook
  -> /api/stream/webhook: verify HMAC, drop bot echoes, return 200 in <3s, fire-and-forget the turn
  -> turn handler: load channel history (+ optional rules), build the system prompt
  -> LLM call (optionally with tools: searchKnowledge / updateTicketState)
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

**Centralize config and accept key aliases.** A provider's key *label* rarely matches the env var *name* the code expects - the single biggest source of setup friction, and invisible until runtime. Resolve keys in one `lib/config.ts` that both the app and the scripts import, and accept common aliases:

```ts
export const GEMINI_KEY = process.env.GOOGLE_GENERATIVE_AI_API_KEY ?? process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;
export const TURBOPUFFER_KEY = process.env.TURBOPUFFER_API_KEY ?? process.env.TURBO_PUFFER_KEY;
```

Aliasing must cover the ingestion/webhook **scripts**, not just the app - their preflight guards read the same env vars. If a key is present but misnamed, the setup check should name the exact rename.

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

### Connect the webhook in dev (required, or the bot stays silent)

**If the build uses the webhook trigger, it is not finished until the webhook is connected.** Stream only ever invokes the agent through the `message.new` webhook, and it cannot reach `localhost`, so until a public tunnel is registered the bot receives messages but never replies. This is the single most common reason a freshly built agent "does nothing." Treat it as the final build step and tell the user explicitly.

1. Start the dev server.
2. Expose it publicly: `cloudflared tunnel --url http://localhost:<port>` (or `ngrok http <port>`).
3. Register that URL: run the `register-webhook` script against `<tunnel-url>/api/stream/webhook`.
4. Tell the user plainly: the bot will not reply until this is done; the tunnel and `npm run dev` must both stay running; and the URL must be re-registered whenever the tunnel or dev server restarts (quick tunnels mint a new hostname each time). A stale URL silently breaks replies.

Make it one command, not four: provide a single `npm run tunnel` that starts cloudflared, parses the public URL from its output, and runs `register-webhook` automatically. Rule of thumb to tell the user: a silent bot in dev = check the tunnel + registration first.

Zero-setup alternative for a quick local check: the **client-triggered** trigger needs no tunnel (it fires from the browser), but it is demo-only and goes silent when no tab is open. Use the webhook for anything real.

### Conversations and sessions (the ticket model)

Each conversation is its own channel - a ticket. Generate a fresh id per conversation (`support-<shortid>`) and make the **URL the source of truth** for it (a `/chat/[channelId]` route, or a `?c=<id>` query param). This gives the behavior users expect, with no database required:

- **Entering a chat** opens (and, on first visit, creates) that specific channel, with the customer and the bot as members. Create it server-side in the token/agent route if it does not exist yet.
- **Refreshing** the chat page keeps the same channel, because the id is read from the URL. Do not generate a new id on mount (a `useState`/`useEffect` that mints an id on render will start a new channel on every reload).
- **Returning to the home/hub and starting again** mints a new id and navigates to it - a new session, a new channel.

Keep it light: the id can be generated client-side (a short nanoid, or a slice of `crypto.randomUUID()`) and the channel created on first open. A persistent ticket list, status, and cross-session history is the next tier (Postgres) - add it only when needed. Avoid the opposite trap too: do not hard-code a single `support-<userId>` channel for everything, or every visit reuses one ever-growing thread instead of a fresh ticket.

### Server Routes

| Route | Method | Purpose |
|---|---|---|
| `/api/token` | GET | From CHAT.md. Also `ensureBot()` and create the support channel. Returns `{ apiKey, userId, chatToken, channelId }`. |
| `/api/stream/webhook` | POST | Stream calls this on every `message.new`. Verify, filter, fire-and-forget the turn. |

**Webhook handler** - the load-bearing route. Verify over the **raw** body, guard against the bot replying to itself, return fast:

```ts
export const maxDuration = 300; // the turn runs after the 200; keep the function alive

import { gunzipSync, brotliDecompressSync, inflateSync } from "node:zlib";

export async function POST(req: Request) {
  // Verify over the EXACT bytes Stream signed. A tunnel/proxy (cloudflared) can
  // compress in transit, so decompress by content-encoding BEFORE reading text,
  // or verifyWebhook fails with signatureValid:false. This is the #1 "bot is
  // silent behind a tunnel" cause.
  const buf = Buffer.from(await req.arrayBuffer());
  const enc = req.headers.get("content-encoding");
  const raw = (enc === "gzip" ? gunzipSync(buf)
    : enc === "br" ? brotliDecompressSync(buf)
    : enc === "deflate" ? inflateSync(buf)
    : buf).toString("utf8");

  // The HMAC signature IS the authentication. Do NOT also gate on x-api-key:
  // it is redundant with the signature and breaks behind some proxies.
  if (!serverClient.verifyWebhook(raw, req.headers.get("x-signature") ?? "")) {
    return new Response("bad signature", { status: 401 });
  }

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

For **token streaming** (optional, advanced): broadcast partials with `ephemeralUpdateMessage` (no DB write, requires `stream-chat` >= 9.27) while tokens arrive, then persist once with `partialUpdateMessage`. Persisting per token hits rate limits. The final `partialUpdateMessage` with the complete text must be **unconditional** - do not gate it on `finalText !== accumulated` (it is false once the accumulator holds the whole text), or the saved message is truncated to the first chunk.

**Client-triggered variant (demo-only):** skip the webhook. In the browser, listen on the channel and POST your agent route when the customer sends a message:

```ts
channel.on("message.new", (e) => {
  if (e.user?.id === userId && !e.message?.parent_id) fetch("/api/agent", { method: "POST", body: JSON.stringify({ channelId }) });
});
```

Simpler (no tunnel, no HMAC) but the bot only replies while a tab is open and listening. State this tradeoff to the user; do not ship it as production.

### LLM provider selection

Ask, then wire exactly one. **List Gemini first and pre-select it as the default** (it is the recommended choice below); switch only if the user picks another. Add the key to `.env` (server-side only; never `NEXT_PUBLIC_*`).

| Provider | Package(s) | Env var | Default model |
|---|---|---|---|
| Google Gemini **(recommended default)** | `@ai-sdk/google` + `ai` | `GOOGLE_GENERATIVE_AI_API_KEY` (accept `GEMINI_API_KEY` / `GOOGLE_API_KEY` aliases) | `gemini-2.5-flash` (or `gemini-2.5-pro`) |
| Anthropic Claude | `@ai-sdk/anthropic` + `ai`, or `@anthropic-ai/sdk` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` (or `claude-haiku-4-5`) |
| OpenAI | `@ai-sdk/openai` + `ai` | `OPENAI_API_KEY` | `gpt-5` class |

Recommended path: the **Vercel AI SDK** (`ai` + `@ai-sdk/<provider>`) with `streamText({ model, system, messages, tools, stopWhen: stepCountIs(8) })`. It is provider-agnostic and supports the tool loop. For a no-tools, no-RAG build, a single `@anthropic-ai/sdk` `messages.create` call is fine and lighter. Use prompt caching on the static system/KB portion regardless of provider.

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

For `local`/`external`, expose retrieval as a **tool the model calls** (`searchKnowledge`), not always-on prompt stuffing - that is what makes it an agent. Ground it: instruct the model to call retrieval **before** asserting product facts and to cite `source_url`; if two queries return nothing relevant, say so and ask a clarifying question.

Retrieval shape (nova's TurboPuffer pattern): embed the query, run vector ANN **and** BM25 in parallel, fuse with Reciprocal Rank Fusion. Embedding asymmetry is mandatory: ingest with `RETRIEVAL_DOCUMENT`, query with `RETRIEVAL_QUERY` (mixing them silently halves recall). One namespace per knowledge set. Ingestion (`scripts/ingest.ts`): crawl/read docs, chunk by heading (~800 tokens), embed, upsert `{ id, vector, text, source_url, title }`.

**Use defaults that resolve on the live APIs** (invalid ids fail silently until runtime). Gemini embeddings model: `gemini-embedding-001` (it defaults to 3072 dims - pin `outputDimensionality` to your vector schema, e.g. 768; cosine distance is scale-invariant, no normalization needed). `text-embedding-004` does **not** resolve on the public API. TurboPuffer regions are **cloud-prefixed** (`gcp-us-central1`, `aws-us-east-1`); a bare `us-east-1` fails with `ENOTFOUND`.

### Agent capabilities (tools)

Define tools the model can call (Vercel AI SDK `tool({ description, inputSchema, execute })` - note `inputSchema`, not `parameters`):

| Tool | Purpose |
|---|---|
| `searchKnowledge` | Retrieve grounding passages (see Knowledge layer). The anti-hallucination tool. |
| `escalateToHuman` *(optional)* | Only add if there is a real place to escalate to (a human queue, inbox, or ticket system). Hands off and notifies. Without that infrastructure, leave it out rather than promising a handoff the build cannot deliver. |
| `updateTicketState` | Move a ticket to resolved/closed, only after the user confirms. |
| `mockApiCall` | Stubbed transactional action (refund/cancel) when there is no real backend. |

Escalation needs somewhere to escalate to (a human queue, inbox, or ticket state). A basic stateless build has none of that, so omit `escalateToHuman` and any "talk to a human" affordance until that structure exists. Persistence (tickets, rules, analytics) is the next tier up.

### Optional add-ons (build only what is checked)

Present these as a multi-select checkbox list, **none checked by default**. Skipping all is the recommended, reliable path (the grounded agent above). Each checked item is a tier up: build it with the stack shown, and build nothing for the unchecked ones. These are how you get *closer to a full support product* without betting the one-shot on generating everything at once.

| Add-on | What it adds | Stack to use | Requires |
|---|---|---|---|
| Persistence | Durable tickets, transcript, and a log of every tool call + lifecycle event | Postgres + `drizzle-orm` + `postgres`; tables: `tickets`, `messages`, `actions`, `events`. For a local DB, probe for a free port (5432 → 5433 → 55432…) instead of hardcoding 5432, and surface the chosen `DATABASE_URL` (devs often already run Postgres on 5432). | - |
| Operator dashboard + live rules | A `/dashboard` to write natural-language rules that inject into the prompt (behaviour changes on the next turn, no redeploy), plus a human queue, transcripts, and analytics | Next.js dashboard routes + a `rules` table | Persistence |
| Human escalation (real) | `escalateToHuman` with an actual destination: flip the ticket to `needs_human` and notify | `resend` (+ `@react-email/components`) + a `needs_human` queue | Persistence |
| OpenAPI lookup | `listApiOperations` / `getApiOperation` tools for exact API-reference answers (operation, method+path, params, schemas, error codes) | parse an OpenAPI spec into a local index + two internal endpoints | - |
| Transactional action | `mockApiCall` - a stubbed backend action (refund/cancel) the agent can invoke | none (stub) | - |
| Real auth (Clerk) | A real sign-in/sign-up system instead of the name-based login: authenticated sessions, and the `/api/token` route gated by the signed-in user so the **Stream user id is the authenticated identity** (not a typed name), plus an optional email allowlist. Same setup nova uses to gate both the app and the dashboard. Keep the name-based login as a **dev fallback** so chat can be smoke-tested before Clerk keys exist (the `/api/token` `?user_id=` path already supports it); upgrade to Clerk when its keys are present, so auth never hard-blocks the first run. | `@clerk/nextjs` | - |
| Voice + screenshare | A voice + screenshare agent that joins a Stream Video call (real-time voice + `describe_screen`) | a separate Python Vision Agents worker - **use the `vision-agents` skill**, do not scaffold it into the Next.js app | separate service |

Rules:
- **Default is none.** If the user skips, build the lean grounded agent and stop.
- **Auto-include Persistence** when Operator dashboard or Human escalation is checked - both depend on it.
- **Voice is a separate build.** Do not generate it inline; point the user to the `vision-agents` skill. It needs its own service, keys, and deploy, and is not part of the few-minutes web one-shot.
- **If voice is selected, say so unmistakably in the final summary.** Nothing for it ships in the web app, so add a dedicated "Not built here - separate service" line and offer to kick off the `vision-agents` skill, so a ticked box is never silently dropped.

### Client Patterns

- Reuse the Chat client + components from CHAT.md (`useCreateChatClient`, `<Chat>`, `<Channel>`, `<MessageList>`, `<MessageComposer>`).
- For AI rendering, `@stream-io/chat-react-ai` provides a streaming message component + an AI state indicator that consumes the `ai_indicator` events automatically. Without it, the default typing indicator still shows while the bot "types"; the `ai_indicator` states drive the thinking/generating UI.
- Show a clear **bot identity** as a non-interactive header: the agent name, an "AI agent" **badge** (a label/chip, not a button), and a one-line description of what it does. It is informational, not clickable.

### Gotchas

- **HMAC over the EXACT raw bytes, decompressed.** Read `arrayBuffer()` and decompress by `content-encoding` (a tunnel/proxy may gzip/br in transit) before `verifyWebhook`, then `JSON.parse`. Never `req.json()` before verifying. Authenticate with the HMAC signature **only** - do not also gate on `x-api-key` (redundant, and breaks behind proxies). This is the #1 "401 / bot silent behind a tunnel" cause.
- **Bot-loop guard is mandatory.** Filter `user.id === BOT_USER_ID` and `message.ai_generated`, or the bot answers its own messages forever.
- **Webhook must return <3s.** Fire-and-forget the turn; set `export const maxDuration = 300` so the function stays alive to finish it.
- **Streaming needs the two-call split.** `ephemeralUpdateMessage` (broadcast, no DB, >= 9.27) for intra-response flushes, exactly one `partialUpdateMessage` to persist. Per-token persistence trips rate limits. The final persist is **unconditional** - gating it on "changed" truncates the saved message to the first chunk.
- **`ai_indicator` events** carry `user_id` = the bot, and use `AI_STATE_THINKING` / `AI_STATE_GENERATING` / `ai_indicator.clear`.
- **Embedding asymmetry** - `RETRIEVAL_DOCUMENT` (ingest) vs `RETRIEVAL_QUERY` (query). Wrong pairing halves recall.
- **Don't prompt-stuff a large KB** - use retrieval as a tool past a page or two.
- **Vercel AI SDK v5/v6** uses `inputSchema`, not `parameters`. v4 examples compile but never register the tool.
- **Next.js 16 middleware file is `proxy.ts`**, not `middleware.ts`.
- **Missing LLM key: warn in-channel, don't 500.** If the selected provider's key is absent at request time, post a bot message naming the missing env var and return, rather than failing silently. Keeps the chat alive and the cause obvious.
- **Every optional integration must announce its status; silent degrade is a UX trap.** A missing `TURBOPUFFER_API_KEY` (or Resend, or the OpenAPI spec) makes a tool return "not configured", which the model reports as "I don't have that" - indistinguishable from a real content gap. Pair runtime resilience with a visible signal: a one-line `console.warn` when a tool runs unconfigured, a reachable setup/status view (not only the root gate), and ideally a dev-only badge ("RAG: off") plus a dashboard Integrations row (green/grey + the env var to set).
- **Surface the underlying API error, not just the SDK wrapper.** An `AI_NoOutputGeneratedError` usually hides a real message like `models/<id> is not found` - log/show it so "model not found" / "region not found" is obvious instead of a generic failure.
- **Webhook trigger in dev: connect it or the bot is silent.** Start a tunnel, register `<tunnel>/api/stream/webhook`, keep both the tunnel and dev server running, and re-register when either restarts. The most common "built it but nothing replies" cause. See *Connect the webhook in dev*.
- **Client-triggered trigger is demo-only** - the bot is silent when no tab is connected. Webhook is the real pattern.

---

## Recommended default stack (if the user is unsure)

Next.js (Chat scaffold) + `@stream-io/node-sdk` + Vercel AI SDK with **Google Gemini** (`gemini-2.5-flash`) + a webhook trigger + a `local` knowledge index, exposed to the model as a `searchKnowledge` tool. This is a real agent with grounding, runnable on one machine (the only external dependency beyond Stream + the LLM key is the dev tunnel for the webhook). Gemini also supplies the embeddings for the knowledge layer, so one key covers chat and retrieval. Scale up to an external vector store, human escalation, and persistence when the knowledge or operator needs grow.

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
