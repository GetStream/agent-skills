# Stream - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Peer skills

The Stream pack ships a router (this skill) plus a set of peer skills declared in [`peers.yaml`](peers.yaml) (schema: [`peers.schema.json`](peers.schema.json)). To check whether a peer is installed, **Glob** the entry's `glob` path. To install a missing peer per its `install_policy`, run its `install` command. To use it after install, **Skill tool if listed in the system reminder's available-skills, otherwise Read the file inline** (available-skills doesn't refresh mid-session).

When adding a new peer pack, edit `peers.yaml` only.

---

## Secrets

Never Read/Edit **`.env`** / **`.env.local`** in chat - the secret leaks into the conversation. Let the CLI own it: `getstream env` writes the platform's API key var (and the secret, for server targets) into the right file, and that's all you need. Don't grep, don't cat, don't `echo >>` a file holding the secret. Never hardcode the secret in code.

**The secret is server-side only** - never in the client bundle, never `NEXT_PUBLIC`. The **public API key** may be client-exposed: `getstream env` writes it with the framework's client prefix (e.g. `NEXT_PUBLIC_STREAM_API_KEY`, `EXPO_PUBLIC_STREAM_API_KEY`). The client may read that var directly or receive `apiKey` from the `/api/token` response; either way the **token** is minted server-side (with the secret) and returned by `/api/token`.

**`.gitignore` before any `.env` write.** Before any tool writes secrets to `.env` (notably `getstream env` in builder Task B), confirm a line covering `.env*` exists in `.gitignore` and add one if missing. The Next.js scaffold's default already does - this rule covers the edge case where the project's `.gitignore` was hand-edited or doesn't exist yet.

## No auto-seeding

Never auto-create demo users (alex, maya, jake, sarah) or sample posts/channels/content. The `/api/token` route upserts **only** the requesting user and returns their token(s). Seed functions are **opt-in only** when the user explicitly asks for sample data.

## Login Screen first

Every app opens with a **Login Screen** as its root page (`app/page.tsx`). The app never auto-connects or hardcodes a user. Credentials (token, apiKey, userId) live in **React state** - not localStorage - so each browser tab can operate as an independent user. Layout and behavior details: the active builder pack's `builder-ui.md` > Login Screen ([`stream-react`](../stream-react/builder-ui.md) for web React; [`stream-builder`](../stream-builder/builder-ui.md) when explicitly invoked).

## Strict mode protection

**React packs only** (`stream-react`, `stream-react-native`, and `stream-builder`'s web flow) - not applicable to the Swift/Android/Flutter packs. Protection is **per-SDK**, not one blanket pattern:

- **Chat (client-side):** use the official `useCreateChatClient()` hook - it handles strict mode internally. Never `getInstance()` on the client (singletons break strict mode).
- **Feeds (client-side):** `useCreateFeedsClient()` handles the connection internally. Only `feed.getOrCreate()` needs the manual `setTimeout(50ms)` + `mounted` guard + cleanup in `useEffect`.
- **Video (client-side):** the `StreamVideoClient` constructor is synchronous - plain `useState` + `useEffect` with `disconnectUser()` cleanup; no timer, no mounted flag, never `useMemo`.
- **Server-side:** `StreamChat.getInstance(apiKey, apiSecret)` is fine (singleton OK).
- **Never use `useRef` as a "run once" guard** in setup effects with cleanup - the ref survives strict mode's unmount->remount cycle, so the second mount skips initialization entirely.

Authoritative detail and canonical snippets live in the React pack's own rules: [`stream-react/RULES.md`](../stream-react/RULES.md) > Strict mode protection (web; includes the carve-outs and the canonical video snippet). `stream-react-native` carries its own RULES.md.

## Base UI (not Radix)

Shadcn components use `@base-ui/react`, NOT `@radix-ui`. Key differences:
- **Never use `asChild`** - it does not exist in Base UI. Trigger components render children directly.
- Style triggers by passing `className` directly to `<DropdownMenuTrigger>`, `<PopoverTrigger>`, etc.
- Do NOT wrap triggers with `<Button>` - style the trigger element itself.

## CLI safety

The `getstream` CLI owns onboarding, auth, and credentials. Drive it from the **Stream CLI** section of [`SKILL.md`](SKILL.md) and **read the CLI's output to understand what happened** - it explains failures and next steps the same way for an agent as for a person. There are no exit-code conventions to memorize.

- **No guessing.** Endpoint names, parameters, and body shapes come from `getstream api -h` (or `stream -h`), never from training-data recall. If you're about to type a `getstream api <Endpoint>` you haven't confirmed this turn, stop and look it up first. This applies to **every** sub-skill, including `stream-builder` follow-ups and one-off "let me just check" queries.
- **Confirm before writing.** Default to read-only. Before any operation that creates, changes, or deletes - or any outward-facing action - describe it and get the user's confirmation. When the CLI refuses an operation and asks for an explicit flag or confirmation, it is flagging a dangerous action: surface it, confirm, then re-run with the flag the CLI named.
- **Nested-object updates replace, not merge.** For an update that takes a nested collection (e.g. `UpdateChannelType --request '{"grants": {...}}'`), read the current value first and resubmit the **whole** object with only your target changed - sending a partial `{"grants":{"user":[...]}}` can drop the other roles. Take exact member strings (capabilities, permissions) from the read, never guess them. Top-level scalar flags (e.g. `{"polls": true}`) do merge and are safe to send alone.
- **Sign-in opens a browser.** `getstream init` / `getstream login` launch a browser flow - run them as their own invocation (never chained with `&&` or wrapped in a heredoc). If sign-in hangs, ask the user to run it themselves with `! <command>`.

## Onboarding & phase order

Onboarding is owned by the CLI: `getstream init` authenticates, selects or creates the org + app, and writes project credentials; `getstream env` provisions the app's server-side secret without exposing it. If `getstream` isn't installed, ask the user to install it from https://getstream.io and wait - never fetch or run an install script. **The `stream-docs` skill skips onboarding entirely** and never runs the CLI except an on-demand read-only probe when the SDK can't be resolved from user input.

- Do not load `references/*.md` (in the `stream-builder` skill) until the user names the product(s).
- Do not load `builder-ui.md` (in the `stream-builder` skill) before Step 4.
- Shadcn/ui is always installed during Step 3 - never skip. Third-party **frontend skills** (`vercel-labs/*`, `anthropics/*`) require one explicit user confirmation per session before install - see the `stream-builder` skill's `SKILL.md` Task A.2.

## Shell discipline

- **Never `bash -ce` or `set -e`** in probes or batched phases. `grep` (and friends) return exit 1 on "no match," which under `-e` aborts the whole script and leaves you with partial output. Tolerate specific failures explicitly (`|| echo NOT_FOUND`, `|| true`) instead.
- **One `bash -c` per phase where possible.** Chain with `&&` on a single line to minimize sandbox approval prompts. If you need to read JSON and then act on it, use one call to read and one batched call for the writes.
- **Browser sign-in stays its own invocation.** `getstream init` / `getstream login` open a browser - never chain with `&&`, embed in a heredoc, or bundle with other commands. Hang recovery is in CLI safety above.

## Cross-track follow-ups

A result from one sub-skill can naturally enable an action in another. Surface a follow-up offer when it genuinely helps the user - not as boilerplate on every turn.

- **`stream-docs` -> CLI:** a docs answer that names a runnable operation can offer "want me to run that now via CLI?" (only if read-safe or clearly operational intent).
- **CLI -> `stream-docs`:** a CLI result that has a relevant docs page can offer "want the page that explains this?" (link only - don't fetch unprompted).
- **`stream-builder` -> `stream-docs`:** after scaffold or integration completes, mention that the SDK + version is preloaded and ask-anything is available.
- **`stream-docs` -> `stream-builder`:** a docs answer that describes a setup-heavy flow can mention scaffold / integrate is available - without running it.

**Do not auto-execute a cross-skill action.** Offer, then wait for the user to confirm. The skill switch happens through the user's reply, which re-enters the `stream` router or jumps straight to the named sub-skill.

## Theme

Use whatever theme Shadcn generates. Do not modify `globals.css` after init - no dark mode overrides, no custom variable blocks. The scaffold includes `next-themes` with a `ThemeProvider` (system default, class-based toggle) - use it as-is.

## Reference authority

**Reference files are the only source of truth** for HTML structure, SDK wiring, and property paths. Do not generate Stream SDK code from training data. Before writing each component, map it to the relevant references sections (Blueprint -> JSX structure, Wiring table -> data fetching/mutations, Requirements -> setup, App Integration -> routes and patterns).

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
