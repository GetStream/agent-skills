# AI support agent

For "support bot", "help desk", "RAG chat", "AI customer support" requests. An additive
layer on top of Chat, not a separate product: a support ticket is a `messaging` channel, a
bot user is a member, and when the customer writes, the bot answers with an LLM. Build the
Chat scaffold per SKILL.md first; this file adds the agent.

The Stream-native wiring is documented - read before building:

```bash
cat $(getstream docs chat/node)/ai-message-streaming.md  # bot user, ai_indicator states, ai_generated, ephemeral/partial streaming
cat $(getstream docs platform)/webhooks.md               # event_hooks registration, signature verification
```

## Ask first - these are real decisions, don't silently default

1. **LLM provider + model.** Default: Gemini `gemini-2.5-flash` - one key covers chat and
   embeddings. Claude (`claude-sonnet-4-6`) and OpenAI equally supported; Anthropic has no
   embeddings model, so pair Claude with Gemini/Voyage/OpenAI embeddings.
2. **Knowledge source** - `none` (facts in the prompt), `local` (embed a docs folder), or
   `external` (TurboPuffer/Pinecone + an ingestion script). Steer by size: tiny/static ->
   none or local; large/changing -> external.
3. **Trigger** - server-side **webhook** (production; needs a public tunnel in dev) or
   **client-triggered** (demo-only: fires from the browser, silent when no tab is open).
4. **Capabilities** - plain Q&A, or a tool-using agent (`searchKnowledge`,
   `updateTicketState`, a stubbed `mockApiCall`). Add `escalateToHuman` only when a real
   destination exists (a queue, inbox, or ticket state) - never promise a handoff the
   build can't deliver.
5. **Add-ons** - a multi-select, none checked by default: persistence (Postgres +
   drizzle), operator dashboard + live rules (needs persistence), real human escalation
   (needs persistence + email), OpenAPI lookup tools, real auth (Clerk - keep the
   name-based login as a dev fallback so chat works before Clerk keys exist), and
   voice + screenshare. Auto-include persistence when the dashboard or escalation is
   checked. Voice is a **separate Vision Agents service** - never scaffold it into the web
   app; if ticked, say "not built here - separate service" in the final summary and point
   at the vision-agents skill.

## The loop

```
customer message -> message.new webhook -> verify, drop bot echoes, return 200 in <3s,
fire-and-forget the turn -> load channel history -> LLM call (with tools) ->
ai_indicator THINKING -> GENERATING -> send message (ai_generated: true) -> clear
```

## The webhook route - what the docs don't say

- **Verify over the exact raw bytes, decompressed.** Read `arrayBuffer()` and decompress
  by `content-encoding` before verifying - a tunnel/proxy can gzip/brotli in transit. The
  #1 "401 / bot silent behind a tunnel" cause.
- **The HMAC signature is the authentication.** Don't also gate on `x-api-key` - it's
  redundant with the signature and breaks behind some proxies (the docs' header table
  suggests otherwise; the signature check is what counts).
- **Return in <3s.** Fire-and-forget the turn; `export const maxDuration = 300` keeps the
  function alive to finish it.
- **Bot-loop guard.** Drop events whose sender is the bot or whose message has
  `ai_generated` - or the bot answers itself forever.
- **Streaming persists once.** `ephemeralUpdateMessage` broadcasts partials (no DB write);
  exactly one `partialUpdateMessage` persists the final text - and make that final persist
  unconditional: gating it on "text changed" truncates the saved message to the first chunk.

## Connect the webhook in dev - required, or the bot stays silent

Stream can't reach `localhost`: until a public tunnel is registered, the bot receives
messages and never replies - the most common "built it but nothing happens" cause. Treat
it as the final build step: start the dev server, expose it (`cloudflared tunnel --url
http://localhost:<port>` or ngrok), register `<tunnel>/api/stream/webhook` via
`updateAppSettings({ event_hooks: [...] })`, and ship it as one `npm run tunnel` command
that parses the tunnel URL and registers it. Re-register whenever the tunnel or dev server
restarts - quick tunnels mint a new hostname each time, and a stale URL breaks replies
silently. Tell the user: a silent bot in dev = check the tunnel first.

## Tickets

One channel per conversation, with the **URL as the source of truth** for its id
(`/chat/[id]` or `?c=<id>`); create the channel server-side on first open with the
customer and the bot as members. Two anti-patterns: minting an id in `useState`/mount
starts a new channel on every reload; hard-coding one `support-<userId>` channel makes one
ever-growing thread instead of fresh tickets.

## Providers and keys

| Provider | Packages | Env var |
|---|---|---|
| Gemini (default) | `@ai-sdk/google` + `ai` | `GOOGLE_GENERATIVE_AI_API_KEY` (accept `GEMINI_API_KEY` / `GOOGLE_API_KEY` aliases) |
| Claude | `@ai-sdk/anthropic` + `ai` | `ANTHROPIC_API_KEY` |
| OpenAI | `@ai-sdk/openai` + `ai` | `OPENAI_API_KEY` |

Resolve keys with aliases in one `lib/config.ts` that both the app and the scripts import
- a key present under the "wrong" name is the biggest setup-friction source, invisible
until runtime.

**A missing key is a visible warning, never a silent failure.** If the selected provider's
key is absent at request time, post a normal in-channel bot message naming the exact env
var and return - no 500, no dead conversation. The same principle for every optional
integration: a tool running unconfigured must announce it (a `console.warn`, a status
view, a dev-only "RAG: off" badge) - otherwise the model reports "I don't have that",
indistinguishable from a real content gap. And surface the underlying API error, not the
SDK wrapper: `AI_NoOutputGeneratedError` usually hides a real `models/<id> not found`.

## Knowledge layer

Expose retrieval as a **tool the model calls** (`searchKnowledge`) - not always-on prompt
stuffing past a page or two. Ground it: retrieve before asserting product facts, cite
`source_url`, and if two queries return nothing, say so and ask. Retrieval shape: embed
the query, run vector ANN and BM25 in parallel, fuse with Reciprocal Rank Fusion; ingest
by chunking on headings (~800 tokens).

Live-API facts that fail silently until runtime: embed documents with `RETRIEVAL_DOCUMENT`
and queries with `RETRIEVAL_QUERY` - mixing them halves recall; `gemini-embedding-001`
defaults to 3072 dims - pin `outputDimensionality` to the vector schema;
`text-embedding-004` does **not** resolve on the public API; TurboPuffer regions are
cloud-prefixed (`gcp-us-central1` - a bare `us-east-1` fails with `ENOTFOUND`).

## Client

`@stream-io/chat-react-ai` renders the streaming message and consumes the `ai_indicator`
events. Show bot identity as a non-interactive header: name, an "AI agent" badge (a chip,
not a button), one-line description. Vercel AI SDK v5/v6 tools use
`tool({ inputSchema })` - not `parameters`; v4 examples compile but never register the tool.

## Reference implementation

`GetStream/nova-support-oneshot` is the proven build: webhook + verify + loop guard
(`app/api/stream/webhook`), turn loop (`agent/run.ts`), Stream bridge
(`agent/stream-bridge.ts`), tools (`agent/tools.ts`), hybrid RAG (`lib/turbopuffer.ts`),
ingestion and webhook-registration scripts. Prefer distilling from it over inventing.