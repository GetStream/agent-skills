# Stream - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Secrets

Never Read/Edit **`.env`** in chat - secrets leak into the conversation. Use Bash with `grep`/`echo` to inspect or append values. Never hardcode secrets in code - use environment variables:

- **Client:** `NEXT_PUBLIC_STREAM_API_KEY`, `NEXT_PUBLIC_STREAM_APP_ID`
- **Server:** `STREAM_API_KEY`, `STREAM_API_SECRET`, `STREAM_APP_ID`
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

- Client-side Chat: `new StreamChat(apiKey)` - never `getInstance()` (singletons break strict mode).
- Server-side: `StreamChat.getInstance(apiKey, apiSecret)` is fine (singleton OK).

## CLI safety

- **First attempt always:** `stream --safe api <endpoint> [params]`.
- **Exit 5** (safe mode refusal) → endpoint is mutating. Notify the user, then rerun **without** `--safe`.
- **Exit 2** (auth error) → run `stream auth login` (browser PKCE in a real terminal), then retry.
- **Exit 4** (spec stale) → run `stream api --refresh`, then retry.
- **Exit 3** (API error) → report the error to the user with the response message.
- **Endpoint discovery:** Read `~/.stream/cache/API.md` first - never `--list`. Refresh if missing.

## CLI install gate (first)

**Before anything else** in this skill (routing, probes, builder, `stream api`, SDK wiring, or docs): verify the **`stream` CLI** is installed (`command -v stream` and `stream --version`). If missing or broken, follow **`bootstrap.md`**: explain, **ask the user once** for permission to install, then install (network). **Do not** skip installation and proceed to scaffold, API calls, or Steps 0–7. If the user declines install, follow **`bootstrap.md`** read-only paths only.

## Phase order

Follow **[`SKILL.md`](SKILL.md)** phase order. **Step 0a** (CLI gate) always comes first. Builder Track A: A1 (CLI gate + probe) → A2 (execute Steps 0–7 immediately).

- Do not load `references/*.md` until the user names the product(s).
- Do not load `builder-ui.md` before Step 4.
- Frontend skills and Shadcn/ui are always installed during Step 3 - never ask, never skip.

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
