# Stream - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Secrets

Never Read/Edit **`.env`** in chat — secrets leak into the conversation. Let the CLI own it: `stream env` writes `STREAM_API_KEY` + `STREAM_API_SECRET`, and that's all you need. Don't grep, don't cat, don't `echo >> .env`. Never hardcode secrets in code.

**Env vars are server-side only.** The client never reads `process.env` for Stream credentials — it receives `apiKey`, `userId`, and its token from the `/api/token` response (upserted once per login) and holds them in React state. No `NEXT_PUBLIC_STREAM_*` vars. This keeps secrets out of the client bundle *and* sidesteps the `.env` hook entirely.

**`.gitignore` before any `.env` write.** Before any tool writes secrets to `.env` (notably `stream env` in builder Task B), confirm a line covering `.env*` exists in `.gitignore` and add one if missing. The Next.js scaffold's default already does — this rule covers the edge case where the project's `.gitignore` was hand-edited or doesn't exist yet.

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

## Preflight & phase order

Tracks **A, B, C, E** must complete [`preflight.md`](preflight.md) once per session before any further work — project signals → CLI gate → credentials + auth check. **Track D (docs search) skips preflight entirely** and never runs shell commands except an on-demand read-only probe inside `docs-search.md` Step 1a when the SDK can't be resolved from user input.

If the CLI is missing, follow [`bootstrap.md`](bootstrap.md): explain, **ask the user once** for permission to install, then install. Do not skip installation and proceed to scaffold, API calls, or Steps 0–7. If the user declines, follow `bootstrap.md` read-only paths or hand documentation questions to Track D.

- Do not load `references/*.md` until the user names the product(s).
- Do not load `builder-ui.md` before Step 4.
- Shadcn/ui is always installed during Step 3 — never skip. Third-party **frontend skills** (`vercel-labs/*`, `anthropics/*`) require one explicit user confirmation per session before install — see `builder.md` Task A.2.

## Shell discipline

- **Never `bash -ce` or `set -e`** in probes or batched phases. `grep` (and friends) return exit 1 on "no match," which under `-e` aborts the whole script and leaves you with partial output. Tolerate specific failures explicitly (`|| echo NOT_FOUND`, `|| true`) instead.
- **One `bash -c` per phase where possible.** Chain with `&&` on a single line to minimize sandbox approval prompts. If you need to read JSON and then act on it, use one call to read and one batched call for the writes.
- **`stream auth login` stays its own invocation.** Browser PKCE needs an unwrapped call — never chain with `&&`, embed in a heredoc, or bundle with other commands. Hang recovery is in CLI safety above.

## Cross-track follow-ups

The tracks share a single skill so a result from one can naturally enable an action in another. Surface a follow-up offer when it genuinely helps the user — not as boilerplate on every turn.

- **D → B:** a docs answer that names a runnable operation can offer "want me to run that now via CLI?" (only if read-safe or clearly operational intent).
- **B → D:** a CLI result that has a relevant docs page can offer "want the page that explains this?" (link only — don't fetch unprompted).
- **A/E → D:** after scaffold or integration completes, mention that the SDK + version is preloaded and ask-anything is available.
- **D → A/E:** a docs answer that describes a setup-heavy flow can mention scaffold / integrate is available — without running it.

**Do not auto-execute a cross-track action.** Offer, then wait for the user to confirm. The track switch happens through the user's reply, which re-enters the router.

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
