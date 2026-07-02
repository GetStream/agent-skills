# Migrate / upgrade an SDK version (Track M)

For upgrading an existing React / Next.js app's Stream SDK to a newer major/minor version ("upgrade `stream-chat-react` to v14", "migrate to the new SDK", "bump my Stream version"). **Docs-driven and read-only until you've fetched the guide** - never apply a migration from memory ([`RULES.md`](RULES.md) > Docs-first for cookbook / advanced features).

> **Rules:** [`RULES.md`](RULES.md) (package manager, docs-first) and the cross-cutting [`../stream/RULES.md`](../stream/RULES.md). This track does **not** scaffold, provision, or need to authenticate - it edits an existing project. Preserve the project's existing package manager + lockfile.

---

## M1: Detect what's installed

Read the target versions from `package.json` (do not guess):

```bash
cat package.json
```

Identify which Stream packages are present and their current versions:
- `stream-chat`, `stream-chat-react`
- `@stream-io/video-react-sdk`
- `@stream-io/feeds-react-sdk`
- `@stream-io/node-sdk` (server)

Establish **from version -> to version** for each package the user wants to move. If the user didn't name a target, the target is the latest published major - confirm it with `npm view <pkg> version` before proceeding.

**Also detect the package manager** from the lockfile (`package-lock.json` -> npm, `yarn.lock` -> yarn, `pnpm-lock.yaml` -> pnpm). Use it for every install/build below so you don't strand the active lockfile or create a stray `package-lock.json`.

## M2: Fetch the matching release / upgrade guide (before any edit)

**Match the upgrade to its guide and `WebFetch` it this turn.** Known entry point:

- **Chat React v13 -> v14:** https://getstream.io/chat/docs/sdk/react/release-guides/upgrade-to-v14.md (also in [`references/docs-map.md`](references/docs-map.md) > Chat Advanced Guides).

For any other package/version, discover the guide from the product index ([`references/docs-map.md`](references/docs-map.md) > The docs convention) - look for a `release-guides/` or `upgrade-*` page that matches the from/to versions. Read the guide in full before touching code; note every breaking change, rename, removed export, and codemod it lists.

**Hard gate ([`RULES.md`](RULES.md)):** if no guide loads, hand the lookup to the `stream-docs` skill. If neither the guide nor `stream-docs` confirms the migration steps, **stop and tell the user** - report that you could not confirm the upgrade path and ask how to proceed. Do not migrate from memory; a guess that happens to compile is still a guess.

## M3: Apply the documented changes

Work strictly from the fetched guide:

1. **Bump only the packages being migrated**, each to ITS OWN resolved target from M1. The Stream packages carry **independent version numbers** - never apply one target to several (e.g. `stream-chat-react` and `stream-chat` version separately; a single shared `<target>` can request a release that doesn't exist). Build the install list from the detected from->to pairs, including only the package(s) the user is actually upgrading:
   ```bash
   # npm (examples; --legacy-peer-deps is npm-only). Chat = each package at its own target:
   npm install stream-chat-react@<chatReactTarget> stream-chat@<chatTarget> --legacy-peer-deps
   npm install @stream-io/video-react-sdk@<videoTarget> --legacy-peer-deps   # Video
   npm install @stream-io/feeds-react-sdk@<feedsTarget> --legacy-peer-deps   # Feeds
   # yarn:  yarn add stream-chat-react@<target> stream-chat@<target>
   # pnpm:  pnpm add stream-chat-react@<target> stream-chat@<target>
   ```
   Use the **detected package manager** from M1 (yarn/pnpm don't need `--legacy-peer-deps`). Do not introduce a second lockfile or bump packages the migration doesn't touch.
2. **Apply each breaking change** the guide lists - renamed/removed exports (e.g. Chat v14: `MessageInput` -> `MessageComposer`; CSS path `dist/css/v2/index.css` -> `css/index.css` (the preferred aliased path; `dist/css/index.css` also resolves); overrides moved to `<WithComponents>`), changed prop/hook signatures, run any codemod the guide provides.
3. **Search the codebase** for each removed/renamed symbol so nothing is missed (`grep -rn "<oldSymbol>" app/ src/ components/`).
4. Do **not** introduce features the user didn't ask for; this track is an upgrade, not a redesign.

## M4: Verify

```bash
npx tsc --noEmit            # or: yarn dlx tsc --noEmit / pnpm exec tsc --noEmit
npm run build               # or: yarn build / pnpm build  (the project's own build script - do not assume next build)
```

Fix every error the guide's changes surfaced. `tsc --noEmit` reports all type errors at once (renamed exports, changed signatures) - use it first. Re-run until both pass.

## M5: Summarize

Report: packages bumped (from -> to), the breaking changes applied, files touched, and anything from the guide that needs manual follow-up (e.g. Dashboard config, server-side SDK bumps). Offer - do not auto-run - the natural next step (e.g. "want me to bump the server `@stream-io/node-sdk` too?").
