# Enhance an existing app (Track E)

For adding Stream products to an **existing React project** - Next.js or any other React stack (Vite, CRA, Remix, TanStack Start). Reuses the references files and SDK patterns from the scaffold flow but skips the scaffold entirely. **Detect the framework first (E1) and adapt the Next.js-specific bits** - the server token endpoint and the verify/build command differ on non-Next.js stacks; the Stream SDK wiring itself is identical.

> **Reviewing, not adding?** If the user wants to **audit/check an existing Stream Video integration against best practices** ("is my video app production-ready?", "what am I missing?") rather than add a feature, run the **Integration best-practices audit** section in [`references/VIDEO.md`](references/VIDEO.md). It is a read-only review with a fixed checklist + output contract - produce findings first, fix only if asked.

**Rules:** [`RULES.md`](RULES.md) (login screen first, package manager - preserve the existing project's) and the `stream` skill's [`RULES.md`](../stream/RULES.md) (secrets, no auto-seeding).
**Preflight:** hand off to the `stream-cli` skill before any npm installs, `stream api` setup, or token routes - it owns install, credentials, and auth. Wait for its `OK` readout, then continue here. Do not inline-read its files; the hand-off primes its endpoint cache + cookbook for any ad-hoc query you need later (RULES.md > CLI safety).
**SDK wiring (shared with the scaffold flow):** [`sdk.md`](sdk.md) and the relevant [`references/<Product>.md`](references/) - enhance uses the same wiring patterns as scaffold; only the surrounding setup differs.

---

## E1: Audit the existing project

Before writing any code, understand what's already in place:

1. **Packages:** check `package.json` for `stream-chat`, `stream-chat-react`, `@stream-io/video-react-sdk`, `@stream-io/node-sdk`.
2. **Framework:** detect from `package.json` - **Next.js** (has `next`; route handlers under `app/` or `pages/api`; build = `next build`) vs **another React stack** (Vite/CRA/Remix/etc.; no Next.js `/api` routes; build = the project's own `build` script). This drives where the token endpoint lives (E3) and the verify command (E4).
3. **Auth:** does the app already have a server token endpoint (Next.js `/api/token` route, or an equivalent endpoint in the app's own backend)? If so, **extend** it with the new product's token - don't create a second token endpoint.
4. **Credentials:** check for `.env` with `STREAM_API_KEY` / `STREAM_API_SECRET`. If missing, hand off to the `stream-cli` skill to resolve them (it runs `stream env` against the active app), then resume here.
5. **UI framework:** confirm Tailwind, Shadcn, or whatever the project uses. Do **not** install Shadcn or change the styling setup unless the user asks.
6. **Directory structure:** note whether the project uses `app/`, `src/app/`, `pages/`, or `src/` - match the existing convention.

## E2: Install + configure

1. **Install** only the new SDKs **with the project's detected package manager** (from E1) - never introduce a second lockfile: npm -> `npm install <new-packages> --legacy-peer-deps`; yarn -> `yarn add <new-packages>`; pnpm -> `pnpm add <new-packages>`. `--legacy-peer-deps` is **npm-only** (yarn/pnpm resolve Stream peers without it). (the `stream` skill's [`RULES.md`](../stream/RULES.md) > Package manager.)
2. **Configure via CLI:** run setup commands from the relevant `references/<Product>.md` (App Integration -> Setup). Feeds needs feed groups created; Moderation needs blocklist + config.
3. **Import CSS** if the product needs it (Chat: `stream-chat-react/css/index.css` (v14+ preferred alias; v13 used `dist/css/v2/index.css`), Video: `@stream-io/video-react-sdk/dist/css/styles.css`).

## E3: Integrate

1. **Token endpoint:** extend the existing token endpoint to return the new product's token alongside existing ones. On **Next.js** this is the `/api/token` route handler; on **other React stacks** it is the project's own server endpoint (Express/Fastify route, Remix loader/action, Vite server fn, etc.) - the server-side instantiation in [`sdk.md`](sdk.md) is identical, only the host differs. Tokens are always minted server-side ([`RULES.md`](RULES.md) > Env vars are server-side only).
2. **API routes:** add the product-specific server routes from `references/<Product>.md` (App Integration -> API Routes) - as Next.js route handlers on Next.js, or equivalent endpoints in the app's backend otherwise. Feeds needs several (`/api/feed/get`, `/api/feed/post`, etc.); Chat and Video typically only need the token endpoint.
3. **Components:** load the relevant `references/<Product>-blueprints.md` sections and build components using the existing project's patterns and styling conventions - not the [`builder-ui.md`](builder-ui.md) defaults.
4. **State:** if the app already manages user state (auth context, session), wire Stream tokens into that - don't add a separate Login Screen unless the app has no auth.

## E4: Verify

Run with the project's **detected** package manager (do not introduce a second lockfile):

```bash
npx tsc --noEmit            # or: yarn dlx tsc --noEmit / pnpm exec tsc --noEmit
npm run build               # or: yarn build / pnpm build  (runs the project's own build script)
```

Fix any errors. Use the project's existing package manager and `build` script - do not assume `npm` or `next build` on a yarn/pnpm or non-Next.js project.

---

## Key constraints

- Do **not** re-scaffold, re-initialize Shadcn, install frontend skills, or modify `globals.css` / `layout.tsx`.
- Do **not** overwrite or restructure existing files - add new files alongside them.
- Do **not** change the existing auth flow. Adapt Stream's token generation to fit the app's existing auth, not the other way around.
- If the project uses a different package manager (yarn, pnpm), match what it already uses - the npm-only rule applies to new scaffolds, not existing projects.
