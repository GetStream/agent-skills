# Stream - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Secrets

Never Read/Edit **`.env`** in chat — secrets leak into the conversation. Let the CLI own it: `stream env` writes `STREAM_API_KEY` + `STREAM_API_SECRET`, and that's all you need. Don't grep, don't cat, don't `echo >> .env`. Never hardcode secrets in code.

**Env vars are server-side only.** The client never reads `process.env` for Stream credentials — it receives `apiKey`, `userId`, and its token from the `/api/token` response (upserted once per login) and holds them in React state. No `NEXT_PUBLIC_STREAM_*` vars. This keeps secrets out of the client bundle *and* sidesteps the `.env` hook entirely.

- Narrow `searchParams.get()` (returns `string | null`) with guards before passing to SDK methods.

## No auto-seeding

Never auto-create demo users (alex, maya, jake, sarah) or sample posts/channels/content. The `/api/token` route upserts **only** the requesting user and returns their token(s). Seed functions are **opt-in only** when the user explicitly asks for sample data.

## Login Screen first

Every app opens with a **Login Screen** as its root page (`app/page.tsx`). The app never auto-connects or hardcodes a user. Credentials (token, apiKey, userId) live in **React state** - not localStorage - so each browser tab can operate as an independent user. Layout and behavior details: [`builder-ui.md`](builder-ui.md) > Login Screen.

## Strict mode protection

All SDK connections **must** use `setTimeout(50ms)` + `mounted` guard + cleanup in `useEffect`:

```tsx
useEffect(() => {
  if (!apiKey || !userId || !token) return;
  let mounted = true;
  const timer = setTimeout(async () => {
    if (!mounted) return;
    // ... connect SDK ...
    if (!mounted) { /* disconnect */ return; }
    // ... set state ...
  }, 50);
  return () => { mounted = false; clearTimeout(timer); /* disconnect */ };
}, [deps]);
```

**Do NOT use `useRef` as a "run once" guard** with this pattern (e.g. `const initRef = useRef(false); if (initRef.current) return; initRef.current = true;`). `useRef` persists across strict mode's unmount→remount cycle - if you set `ref.current = true` on the first mount, it stays `true` after cleanup, and the second mount skips initialization entirely. The `let mounted` + `setTimeout` + cleanup pattern handles strict mode correctly on its own.

- Client-side Chat: `new StreamChat(apiKey)` - never `getInstance()` (singletons break strict mode).
- Client-side Feeds: `useCreateFeedsClient()` handles strict mode internally - no manual pattern needed for connection. But `feed.getOrCreate()` must still use the `setTimeout` + `mounted` guard.
- Server-side: `StreamChat.getInstance(apiKey, apiSecret)` is fine (singleton OK).

## Base UI (not Radix)

Shadcn components use `@base-ui/react`, NOT `@radix-ui`. Key differences:
- **Never use `asChild`** - it does not exist in Base UI. Trigger components render children directly.
- Style triggers by passing `className` directly to `<DropdownMenuTrigger>`, `<PopoverTrigger>`, etc.
- Do NOT wrap triggers with `<Button>` - style the trigger element itself.

## CLI safety

- **First attempt always:** `stream --safe api <endpoint> [params]`.
- **Exit 5** (safe mode refusal) → endpoint is mutating. Notify the user, then rerun **without** `--safe`.
- **Exit 2** (auth error) → run `stream auth login` as its **own** Bash invocation (browser PKCE — never chain with `&&` or wrap in a heredoc), then retry. If `stream auth login` hangs past ~60s, run `stream auth logout` to clear stale state, then retry `stream auth login` **once**; if it hangs again, ask the user to run `! stream auth login` themselves.
- **Exit 4** (spec stale) → run `stream api --refresh`, then retry.
- **Exit 3** (API error) → report the error to the user with the response message.
- **Endpoint discovery:** Read `~/.stream/cache/API.md` first - never `--list`. Refresh if missing.

## CLI install gate (per track)

For tracks **A, B, C, E** — verify the **`stream` CLI** is installed (`command -v stream` and `stream --version`) before any further work in that track. If missing or broken, follow **`bootstrap.md`**: explain, **ask the user once** for permission to install, then install (network). **Do not** skip installation and proceed to scaffold, API calls, or Steps 0–7.

**Track D (docs search) does not require the CLI** — it only fetches from `getstream.io`. Skip the gate entirely for Track D.

If the user declines install, follow **`bootstrap.md`** read-only paths or hand documentation questions to Track D.

## Phase order

Follow **[`SKILL.md`](SKILL.md)** phase order: **Step 0** (intent classifier) → **Project signals** for tracks A/B/C/E only → **CLI gate** → **CLI + credentials** → execute. Track D skips project signals, the CLI gate, and credentials by default; it only runs a read-only probe **on demand** if SDK inference can't resolve from user input alone (see `docs-search.md` § On-demand project-signals probe). Builder Track A: Step 0 → project signals → A1 (CLI gate + credentials) → A2 (execute Steps 0–7 immediately).

- Do not load `references/*.md` until the user names the product(s).
- Do not load `builder-ui.md` before Step 4.
- Shadcn/ui is always installed during Step 3 — never skip. Third-party **frontend skills** (`vercel-labs/*`, `anthropics/*`) require one explicit user confirmation per session before install — see `builder.md` Task A.2.

## Theme

Use whatever theme Shadcn generates. Do not modify `globals.css` after init - no dark mode overrides, no custom variable blocks. The scaffold includes `next-themes` with a `ThemeProvider` (system default, class-based toggle) - use it as-is.

## Reference authority

**Reference files are the only source of truth** for HTML structure, SDK wiring, and property paths. Do not generate Stream SDK code from training data. Before writing each component, map it to the relevant references sections (Blueprint → JSX structure, Wiring table → data fetching/mutations, Requirements → setup, App Integration → routes and patterns).

## Package manager

Always use **`npm`**. Never use bun. Always **`--legacy-peer-deps`** for Stream packages.

## Moderation is Dashboard-only

**Never build a moderation review queue, review panel, or flagged-item UI in the app.** Moderation review always happens in the [Stream Dashboard](https://beta.dashboard.getstream.io). The app's role is limited to:
- **CLI setup** during scaffold (blocklists, automod config via `references/MODERATION.md` Setup)
- **End-user actions** (report, block, mute) if the product needs them
- Do **not** load Review Queue, Flagged Item, or Auto-Mod Status blueprints from `MODERATION-blueprints.md`

---

## Sandboxed / blocked shell fallback

If terminal is denied or offline: print commands for the user to run locally; continue with **Read**/file work only.
