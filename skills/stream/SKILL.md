---
name: stream
description: "The fastest and easiest way to build with Stream: Chat, Video, Feeds and Moderation."
license: See LICENSE in repository root
compatibility: Requires Node.js, npm, and the stream CLI binary (see bootstrap.md)
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(stream *),
  Bash(npx *), Bash(npm install *),
  Bash(node -e *), Bash(openssl rand *),
  Bash(mv .scaffold*), Bash(rm -rf .scaffold),
  Bash(ls *)
---

# Stream - skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session - every non-negotiable rule is stated there, nowhere else.

This file is the **single entrypoint**: context detection, intent routing, and module pointers.

---

## Step 0a: `stream` CLI gate (mandatory first - never skip)

**Before** any routing, answering, reading modules, or running the rest of the context probe: verify the **`stream` executable** is installed and runnable.

1. Run:
   ```bash
   bash -ce 'command -v stream >/dev/null 2>&1 && stream --version || echo "NOT_FOUND"'
   ```
2. **If the output is `NOT_FOUND` or either command fails:** **stop here.** Do **not** proceed to Step 0b, builder, `stream api`, credential checks, or SDK wiring. Follow **[`bootstrap.md`](bootstrap.md)** (explain what the CLI is, **ask the user once** for permission to install, then run the install - needs network approval). **Do not** suggest continuing scaffold/CLI work without the binary; only after the user **declines** install may you offer read-only help from **`sdk.md`** per bootstrap.
3. **If `stream --version` succeeds:** continue to Step 0b.

This gate applies to **every** Stream-related request (including docs-only or SDK questions): check first, install if missing, then continue.

---

## Step 0b: Context probe (after CLI is available)

Run this **single** probe to understand where you are. Do not show the output as a heading - just use it internally for routing:

```bash
bash -ce 'echo "=== CLI ===" && command -v stream 2>/dev/null && stream --version 2>/dev/null || echo "NOT_FOUND"; echo "=== ENV ===" && grep -s STREAM_API_KEY .env 2>/dev/null | head -1 && echo "ENV_FOUND" || echo "NO_ENV"; echo "=== CONFIG ===" && stream config list 2>/dev/null || echo "NO_CONFIG"; echo "=== PROJECT ===" && (test -f package.json && grep -l "next" package.json >/dev/null 2>&1 && echo "NEXTJS") || echo "NO_PROJECT"'
```

This gives you:
- **CLI state:** installed or not (should already be OK after Step 0a)
- **Credential state:** `.env` in cwd (`env-local`), CLI configured (`cli-configured`), or neither (`none`)
- **Project state:** Next.js project, other project, or empty directory

Show a **one-line status** after the probe:

- `✓ Stream CLI v0.1.0 · app-a3f7b201 (Feeds + Chat) · ~/stream-tv`
- `✓ Stream CLI v0.1.0 · configured via CLI · no local project`
- `✓ Stream CLI v0.1.0 · no credentials found`
- `✗ Stream CLI not found - see bootstrap.md to install` (only if Step 0a was skipped in error - **do not** route onward; go back to Step 0a)

---

## Install

**Skill pack:** `npx skills add GetStream/agent-skills` ([skills.sh](https://skills.sh/docs/cli)) - markdown only, does **not** install the `stream` binary.

**`stream` CLI:** See **[`bootstrap.md`](bootstrap.md)** for binary install from `latest.json` / `install.sh`.

---

## Route by intent + context

| User intent | Context | Route |
|-------------|---------|-------|
| **"Build me a … app"** / scaffold | Empty dir or new dir | **Track A** → [`builder.md`](builder.md) + [`builder-ui.md`](builder-ui.md) |
| **"Add Chat/Video/Feeds to this app"** | Existing Next.js project | **Track E** → [`builder.md`](builder.md) (skip scaffold, add product only) |
| **"Any live calls?"** / **"anything flagged?"** / data queries | Any (with credentials) | **Track B** → [`cli.md`](cli.md) (auto-resolve credentials) |
| **"Any live calls?"** / data queries | No credentials | **Guide** → tell user to run `stream auth login` or `cd` into a project with `.env` |
| **`stream api`** / config / operational CLI | Any | **Track B** → [`cli.md`](cli.md). Tricky bodies/queries → [`cli-cookbook.md`](cli-cookbook.md) |
| **Install `stream` CLI or skill pack** | CLI not found | **Track C** → [`bootstrap.md`](bootstrap.md) |
| **SDK / React / Node questions** | Any | **Track D** → [`sdk.md`](sdk.md); add **one** [`references/<Product>.md`](references/) only if wiring UI |
| **Product/docs questions only** | Any | [`docs.md`](docs.md) |

**Natural language queries** (Track B - "anything flagged?", "any live calls?", "show my channels", etc.): resolve credentials, then look up the right endpoint in `~/.stream/cache/API.md` (run `stream api --refresh` if missing) and execute via [`cli.md`](cli.md) workflow. Do not hardcode endpoint names - they come from the OpenAPI spec.

**Reference blueprints** (load only after the user names the product):

| Product | Header (setup + gotchas) | Full blueprints (load per component) |
|---------|--------------------------|--------------------------------------|
| Chat | [`references/CHAT.md`](references/CHAT.md) | [`references/CHAT-blueprints.md`](references/CHAT-blueprints.md) |
| Feeds | [`references/FEEDS.md`](references/FEEDS.md) | [`references/FEEDS-blueprints.md`](references/FEEDS-blueprints.md) |
| Video | [`references/VIDEO.md`](references/VIDEO.md) | [`references/VIDEO-blueprints.md`](references/VIDEO-blueprints.md) |
| Moderation | [`references/MODERATION.md`](references/MODERATION.md) | [`references/MODERATION-blueprints.md`](references/MODERATION-blueprints.md) |

---

## Track A - Build new app (empty directory)

**Full detail:** Steps 0–7 in **[`builder.md`](builder.md)**; Step 4 UI in **[`builder-ui.md`](builder-ui.md)**.

| Phase | Name | What you do |
|-------|------|-------------|
| **A1** | CLI gate + context probe | Run **Step 0a** then **Step 0b**. Show one-line status. If CLI missing, install via **`bootstrap.md`** before A2 - never skip. |
| **A2** | Execute | **Immediately start** `builder.md` Steps 0–7. Frontend skills + Shadcn/ui are always installed during Step 3 - no prompt needed. |

**Anti-patterns:** running skills install before scaffold; building a moderation review queue in the app.

---

## Track B - CLI / data queries

**Module:** **[`cli.md`](cli.md)**.

**Prerequisite:** Complete **Step 0a** - the `stream` CLI must be installed before running queries or credential resolution.

**Credential resolution** (do this before any `stream api` call):

1. **`.env` in cwd** has `STREAM_API_KEY` → credentials are local. Mention which app you're querying if you can determine it.
2. **No `.env`** → check `stream config list` for configured org/app → use those. Mention: "Querying configured app: `<app-name>`."
3. **Nothing** → tell the user: "No Stream credentials found. Run `stream auth login` to connect, or `cd` into a project with a `.env`."

| Phase | Name | What you do | WAIT? |
|-------|------|-------------|-------|
| **B1** | Resolve credentials | Run credential resolution above - silently if `.env` or config exists | Only if no credentials found |
| **B2** | Execute | `stream --safe api …` first; exit 5 → explain, confirm, retry without `--safe` | - |

---

## Track C - Bootstrap (install CLI / skill)

**Module:** **[`bootstrap.md`](bootstrap.md)**.

| Phase | Name | What you do | WAIT? |
|-------|------|-------------|-------|
| **C1** | Explain | What `stream` is; one confirmation to install | User confirms |
| **C2** | Install | Follow bootstrap (binary + `npx skills add GetStream/agent-skills`) | As needed |

---

## Track D - SDK / Docs (no full scaffold)

**Modules:** **[`sdk.md`](sdk.md)**, **[`docs.md`](docs.md)**.

**Prerequisite:** Complete **Step 0a** first. If the user declined CLI install, limit to read-only **`sdk.md`** / **`docs.md`** per **`bootstrap.md`**.

| Phase | Name | What you do |
|-------|------|-------------|
| **D1** | Scope | Which product (Chat / Video / Feeds / Moderation) and whether references files are needed |
| **D2** | Answer | Load `references/<Product>.md` header when wiring code; load blueprints only if implementing components |

---

## Track E - Enhance existing app

For adding Stream products to an **existing Next.js project**. Uses references files and SDK patterns but skips scaffold entirely.

**Prerequisite:** Complete **Step 0a** - install the `stream` CLI before npm installs, `stream api` setup, or token routes that depend on CLI-backed config.

### E1: Audit the existing project

Before writing any code, understand what's already in place:

1. **Packages:** Check `package.json` for `stream-chat`, `stream-chat-react`, `@stream-io/video-react-sdk`, `@stream-io/node-sdk`.
2. **Auth:** Does the app already have a `/api/token` route? If so, extend it with the new product's token - don't create a second token route.
3. **Credentials:** Check for `.env` with `STREAM_API_KEY` / `STREAM_API_SECRET`. If missing, run credential resolution (Track B).
4. **UI framework:** Confirm Tailwind, Shadcn, or whatever the project uses. Do **not** install Shadcn or change the styling setup unless the user asks.
5. **Directory structure:** Note whether the project uses `app/` or `src/app/` - match the existing convention.

### E2: Install + configure

1. **Install** only the new SDKs: `npm install <new-packages> --legacy-peer-deps` (RULES.md › Package manager).
2. **Configure** via CLI: run setup commands from the relevant `references/<Product>.md` (App Integration → Setup). For example, Feeds needs feed groups created; Moderation needs blocklist + config.
3. **Import CSS** if the product needs it (Chat: `stream-chat-react/dist/css/v2/index.css`, Video: `@stream-io/video-react-sdk/dist/css/styles.css`).

### E3: Integrate

1. **Token route:** Extend the existing `/api/token` to return the new product's token alongside existing ones. Follow `sdk.md` for server-side instantiation patterns.
2. **API routes:** Add product-specific routes from the relevant `references/<Product>.md` (App Integration → API Routes). Feeds needs several (`/api/feed/get`, `/api/feed/post`, etc.); Chat and Video typically only need the token route.
3. **Components:** Load the relevant `references/<Product>-blueprints.md` sections and build components using the existing project's patterns and styling conventions - not the builder-ui.md defaults.
4. **State:** If the app already manages user state (auth context, session), wire Stream tokens into that - don't add a separate Login Screen unless the app has no auth.

### E4: Verify

Run `npx next build` and fix any errors.

### Key constraints

- Do **not** re-scaffold, re-initialize Shadcn, install frontend skills, or modify `globals.css` / `layout.tsx`.
- Do **not** overwrite or restructure existing files - add new files alongside them.
- Do **not** change the existing auth flow. Adapt Stream's token generation to fit the app's existing auth, not the other way around.
- If the project uses a different package manager (yarn, pnpm), match what it already uses - the npm-only rule applies to new scaffolds, not existing projects.

---

## Paths (portable)

| What | Where |
|------|--------|
| Reference headers | `agent-skills/skills/stream/references/*.md` |
| Reference blueprints | `agent-skills/skills/stream/references/*-blueprints.md` |
| CLI endpoint index | `~/.stream/cache/API.md` after `stream api --refresh` |
| Skill modules | `agent-skills/skills/stream/` |

---

## Tooling (all hosts)

**Loading:** This file (`SKILL.md`) + `RULES.md` + files **named by the routing table** for the task.

**Batching:** One `bash -ce` per builder phase where possible; `stream auth login` stays its own invocation for browser PKCE.

**Support:** If the user asks for support or how to contact someone, direct them to [getstream.io/contact](https://getstream.io/contact/).