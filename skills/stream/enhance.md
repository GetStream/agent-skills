# Track E — Enhance an existing app

For adding Stream products to an **existing Next.js project**. Reuses the references files and SDK patterns from Track A but skips the scaffold entirely.

**Rules:** [`RULES.md`](RULES.md) (secrets, no auto-seeding, login screen first, package manager).
**Preflight:** complete [`preflight.md`](preflight.md) — CLI must be installed, credentials resolved — before npm installs, `stream api` setup, or token routes that depend on CLI-backed config.
**SDK wiring (shared with builder):** [`sdk.md`](sdk.md) and the relevant `references/<Product>.md` — Track E uses the same wiring patterns as Track A; only the surrounding scaffold differs.

---

## E1: Audit the existing project

Before writing any code, understand what's already in place:

1. **Packages:** check `package.json` for `stream-chat`, `stream-chat-react`, `@stream-io/video-react-sdk`, `@stream-io/node-sdk`.
2. **Auth:** does the app already have a `/api/token` route? If so, **extend** it with the new product's token — don't create a second token route.
3. **Credentials:** check for `.env` with `STREAM_API_KEY` / `STREAM_API_SECRET`. If missing, run credential resolution from [`cli.md`](cli.md).
4. **UI framework:** confirm Tailwind, Shadcn, or whatever the project uses. Do **not** install Shadcn or change the styling setup unless the user asks.
5. **Directory structure:** note whether the project uses `app/` or `src/app/` — match the existing convention.

## E2: Install + configure

1. **Install** only the new SDKs: `npm install <new-packages> --legacy-peer-deps` ([`RULES.md`](RULES.md) › Package manager).
2. **Configure via CLI:** run setup commands from the relevant `references/<Product>.md` (App Integration → Setup). Feeds needs feed groups created; Moderation needs blocklist + config.
3. **Import CSS** if the product needs it (Chat: `stream-chat-react/dist/css/v2/index.css`, Video: `@stream-io/video-react-sdk/dist/css/styles.css`).

## E3: Integrate

1. **Token route:** extend the existing `/api/token` to return the new product's token alongside existing ones. Follow [`sdk.md`](sdk.md) for server-side instantiation patterns.
2. **API routes:** add product-specific routes from `references/<Product>.md` (App Integration → API Routes). Feeds needs several (`/api/feed/get`, `/api/feed/post`, etc.); Chat and Video typically only need the token route.
3. **Components:** load the relevant `references/<Product>-blueprints.md` sections and build components using the existing project's patterns and styling conventions — not the [`builder-ui.md`](builder-ui.md) defaults.
4. **State:** if the app already manages user state (auth context, session), wire Stream tokens into that — don't add a separate Login Screen unless the app has no auth.

## E4: Verify

```bash
npx tsc --noEmit
npx next build
```

Fix any errors.

---

## Key constraints

- Do **not** re-scaffold, re-initialize Shadcn, install frontend skills, or modify `globals.css` / `layout.tsx`.
- Do **not** overwrite or restructure existing files — add new files alongside them.
- Do **not** change the existing auth flow. Adapt Stream's token generation to fit the app's existing auth, not the other way around.
- If the project uses a different package manager (yarn, pnpm), match what it already uses — the npm-only rule applies to new scaffolds, not existing projects.
