---
name: stream
description: "The fastest and easiest way to build with Stream: Chat, Video, Feeds and Moderation — including live SDK docs search."
license: See LICENSE in repository root
compatibility: Requires Node.js, npm, and the stream CLI binary (see bootstrap.md). Track D (docs search) only requires WebFetch — no CLI binary needed.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(stream *),
  Bash(npx *), Bash(npm install *),
  Bash(node -e *), Bash(openssl rand *),
  Bash(mv .scaffold*), Bash(rm -rf .scaffold),
  Bash(ls *),
  Bash(grep *),
  Bash(cat package.json), Bash(cat pubspec.yaml),
  Bash(cat go.mod), Bash(cat requirements.txt), Bash(cat pyproject.toml),
  WebFetch(domain:getstream.io)
---

# Stream — skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session — every non-negotiable rule is stated there, nowhere else.

This file is the **single entrypoint**: intent classification, conditional context detection, and module pointers.

---

## Step 0: Intent classifier (mandatory first — never skip)

Before any tool call, decide the **track** from the user's input alone — no probes, no fetches, no CLI checks. The classifier is deterministic: scan the input for the signals below in order.

### Signals → track

| Signal in user input | Track | Skip CLI gate? |
|---|---|---|
| Explicit SDK/framework token: `Chat React`, `Video iOS`, `Feeds Node`, `Moderation`, etc. (with or without version) | **D — Docs search** | **Yes** |
| Words "docs" or "documentation" | **D** | **Yes** |
| "How do I {X} in {framework}?", "How does {hook/component/method} work?", "What does {SDK thing} do?" | **D** | **Yes** |
| Operational verbs + Stream noun: "list calls", "show channels", "any flagged", "find users", "check {anything}" | **B — CLI / data query** | No |
| `stream api`, `stream config`, `stream auth` (literal CLI invocation) | **B** | No |
| "Build me a … app", "scaffold", "create a new …" + Stream product, in an empty/new directory | **A — Builder (new app)** | No |
| "Add Chat/Video/Feeds to this app", "integrate Stream into" — existing project | **E — Builder (enhance)** | No |
| "Install the CLI", "set up stream" with no project context | **C — Bootstrap** | n/a |
| Operational verb wrapped in how-to phrasing (e.g. "how do I list my calls?" — docs *or* CLI) | **Ask one disambiguator** | Defer |

### Disambiguation flow

If the input fits more than one row (typically operational verb + how-to phrasing), ask **one** short question and wait. Do not probe, fetch, or gate before the answer.

> Want me to look up the SDK method (docs) or run it now via CLI?

After the answer arrives, route as if the user had given that signal directly.

### After classification

- **Tracks A, B, C, E** → run **Project signals** (local probe), then the **CLI gate**, then **CLI + credentials**, then the track. Project signals inform the one-line status and routing.
- **Track D** → **skip Project signals by default.** Track D only runs the probe on demand, inside `docs-search.md`'s inference step, and only when the SDK can't be resolved from explicit user input. Pure docs questions with an explicit SDK (e.g. `/stream Chat React v14 …`) reach `WebFetch` without any shell execution. Also skip the **CLI gate** and **CLI + credentials** probes.
- **Bare `/stream` with no args** → list the available tracks briefly and wait for input. No shell execution.

---

## Project signals (tracks A/B/C/E — once per session; Track D on demand only)

A local-only probe. **No CLI binary, no network, no gate.** Tracks A/B/C/E run it once on first invocation because scaffold, credentials, and routing depend on it. **Track D does not run it up front** — docs answers shouldn't require inspecting the user's filesystem. If Track D's SDK inference reaches the "need project context" tier (see `docs-search.md` § Inference tiers), it runs the probe at that point and only at that point.

```bash
bash -c 'echo "=== PKG ==="; grep -oE "\"(stream-chat[^\"]*|@stream-io/[^\"]*)\": *\"[^\"]*\"" package.json 2>/dev/null; echo "=== NEXT ==="; test -f package.json && grep -q "\"next\"" package.json && echo "NEXTJS" || echo "NO_NEXT"; echo "=== NATIVE ==="; ls pubspec.yaml go.mod requirements.txt pyproject.toml Podfile build.gradle 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

**Do NOT use `bash -ce`** (`-e` = exit-on-error): `grep` returns exit 1 when it finds no matches, which aborts the entire probe and leaves you with partial output. Same applies to every other probe in this file.

This gives you:
- **PKG:** Stream npm packages with versions (e.g. `"stream-chat-react": "^14.2.0"`) — empty if none
- **NEXT:** `NEXTJS` if `next` is in `package.json`, else `NO_NEXT`
- **NATIVE:** Names of non-npm project files present (Flutter, Go, Python, iOS, Android)
- **EMPTY:** `EMPTY_CWD` if cwd is empty, else `NON_EMPTY`

**Hold the result in conversation context.** Don't re-run unless:
- A scaffold (Track A) or install (Track E) completed and added new packages
- The user changed directory mid-conversation
- A signal you need is missing (e.g., Track D needs a version and `PKG` was empty earlier — re-probe one specific file)

**Don't print this result as a heading.** Use it internally; surface a signal only when it changes what you say to the user (e.g., "I see Chat React v14 — looking up v14 docs.").

---

## CLI gate (tracks A, B, C, E only)

**Track D skips this step.** For all other tracks: verify the **`stream` executable** is installed and runnable before any further work.

1. Run:
   ```bash
   bash -c 'command -v stream >/dev/null 2>&1 && stream --version || echo "NOT_FOUND"'
   ```
2. **If the output is `NOT_FOUND` or either command fails:** **stop here.** Do **not** proceed to the credentials probe, builder, `stream api`, credential checks, or SDK wiring. Follow **[`bootstrap.md`](bootstrap.md)** (explain what the CLI is, **ask the user once** for permission to install, then run the install — needs network approval). **Do not** suggest continuing scaffold/CLI work without the binary; only after the user **declines** install may you offer read-only help from **`sdk.md`** per bootstrap, or hand the user back to Track D for documentation questions.
3. **If `stream --version` succeeds:** continue to the credentials probe.

---

## CLI + credentials probe (tracks A, B, C, E only)

Run this **single** probe to confirm the CLI works and credentials are available. Project signals are already in context from the earlier local probe — don't repeat them here.

```bash
bash -c 'echo "=== CLI ==="; command -v stream 2>/dev/null; stream --version 2>/dev/null || echo "NOT_FOUND"; echo "=== CONFIG ==="; stream config list 2>/dev/null || echo "NO_CONFIG"'
```

This gives you:
- **CLI state:** installed or not (should already be OK after the CLI gate)
- **Config state:** CLI configured (`cli-configured`) or not (`NO_CONFIG`)

**`.env` is intentionally NOT checked here.** Many sandbox configs install a `PreToolUse` hook that blocks any bash command referencing `.env` — including inside a `bash -c` wrapper — which would silently fail this whole probe. For tracks A (new app) and E (enhance), you'll either create a fresh `.env` via `stream env` (Task B) or work in a project that already has one; the project-signals probe tells you whether you're in an existing project.

**Auth check (run only on tracks A/B/E that need to make `stream api` calls):**

The probe above does NOT verify you're logged in — `stream config list` succeeds even when unauthenticated. Run one auth-requiring call, **unpiped** so the exit code surfaces:

```bash
stream api OrganizationRead
```

Do not pipe through `head`/`tail`/`jq` on this probe — the pipeline exit code is the last command's, which masks the auth failure. If output volume is a concern, redirect: `stream api OrganizationRead >/dev/null 2>&1; echo "exit=$?"`.

- Exit 0 → authenticated, continue. (Bonus: the output is reusable for Step 2's "check existing orgs".)
- Exit 2 / "not authenticated" → **immediately** run `stream auth login` as its own Bash invocation (required for browser PKCE — never chain with `&&` or wrap inside a heredoc). Do not ask the user first.
- If `stream auth login` hangs past ~60s or the user reports a stuck browser state → run `stream auth logout` to clear stale state, then retry `stream auth login` once. If the second attempt also hangs, stop and ask the user to complete login manually (they can type `! stream auth login` to run it in-session).

Show a **one-line status** combining project signals and CLI + credentials:

- `✓ Stream CLI v0.1.0 · app-a3f7b201 (Feeds + Chat) · Next.js + Chat React v14 · ~/stream-tv`
- `✓ Stream CLI v0.1.0 · configured via CLI · no local project`
- `✓ Stream CLI v0.1.0 · no credentials · empty dir (ready to scaffold)`
- `✗ Stream CLI not found — see bootstrap.md to install` (only if the CLI gate was skipped in error — **do not** route onward; go back and run it)

---

## Install

**Skill pack:** `npx skills add GetStream/agent-skills` ([skills.sh](https://skills.sh/docs/cli)) — markdown only, does **not** install the `stream` binary. A git-clone alternative that bypasses `skills.sh` is documented in the [README](../../README.md#install--direct-from-github-no-third-party-cli).

**`stream` CLI:** See **[`bootstrap.md`](bootstrap.md)** for binary install. That file also includes **§ What the installer does** — a line-by-line description of `install.sh`, checksum verification, TTY confirmation, and an audit recipe for reviewers who want to inspect before running.

---

## Module map

Step 0 picks the track. Each Track section below has the full prerequisites and phase table — this is just the at-a-glance map.

| Track | Module(s) |
|---|---|
| A — Build new app | [`builder.md`](builder.md) + [`builder-ui.md`](builder-ui.md) |
| B — CLI / data query | [`cli.md`](cli.md); tricky bodies → [`cli-cookbook.md`](cli-cookbook.md) |
| C — Bootstrap | [`bootstrap.md`](bootstrap.md) |
| D — Docs search (no CLI gate) | [`docs-search.md`](docs-search.md) |
| E — Enhance existing app | [`builder.md`](builder.md) (skip scaffold) + [`references/<Product>.md`](references/) |
| SDK wiring inside A/E | [`sdk.md`](sdk.md) + relevant [`references/<Product>.md`](references/) |

**Reference blueprints** (load only after the user names the product, used by Tracks A and E):

| Product | Header (setup + gotchas) | Full blueprints (load per component) |
|---------|--------------------------|--------------------------------------|
| Chat | [`references/CHAT.md`](references/CHAT.md) | [`references/CHAT-blueprints.md`](references/CHAT-blueprints.md) |
| Feeds | [`references/FEEDS.md`](references/FEEDS.md) | [`references/FEEDS-blueprints.md`](references/FEEDS-blueprints.md) |
| Video | [`references/VIDEO.md`](references/VIDEO.md) | [`references/VIDEO-blueprints.md`](references/VIDEO-blueprints.md) |
| Moderation | [`references/MODERATION.md`](references/MODERATION.md) | [`references/MODERATION-blueprints.md`](references/MODERATION-blueprints.md) |

---

## Cross-track follow-ups (use judgment)

The tracks share a single skill so a result from one can naturally enable an action in another. Surface a follow-up offer when it genuinely helps the user — not as boilerplate on every turn.

- **D → B:** A docs answer that names a runnable operation can offer "want me to run that now via CLI?" (only if read-safe or clearly operational intent).
- **B → D:** A CLI result that has a relevant docs page can offer "want the page that explains this?" (link only — don't fetch unprompted).
- **A/E → D:** After scaffold or integration completes, mention that the SDK + version is preloaded and ask-anything is available.
- **D → A/E:** A docs answer that describes a setup-heavy flow can mention scaffold / integrate is available — without running it.

**Do not** auto-execute a cross-track action. Offer, then wait for the user to confirm. The track switch happens through the user's reply, which re-enters Step 0.

---

## Track A — Build new app (empty directory)

**Full detail:** Steps 0–7 in **[`builder.md`](builder.md)**; Step 4 UI in **[`builder-ui.md`](builder-ui.md)**.

| Phase | Name | What you do |
|-------|------|-------------|
| **A1** | CLI gate + context probe | Run the **CLI gate** then **CLI + credentials**. Show one-line status. If CLI missing, install via **`bootstrap.md`** before A2 — never skip. |
| **A2** | Execute | **Immediately start** `builder.md` Steps 0–7. Shadcn/ui installs silently; third-party **frontend skills** require one explicit user confirmation during Step 3 Task A.2 (third-party provenance). |

**Anti-patterns:** running skills install before scaffold; building a moderation review queue in the app.

---

## Track B — CLI / data queries

**Module:** **[`cli.md`](cli.md)**.

**Prerequisite:** Complete the **CLI gate** — the `stream` CLI must be installed before running queries or credential resolution.

**Credential resolution** (do this before any `stream api` call):

1. **`.env` in cwd** has `STREAM_API_KEY` → credentials are local. Mention which app you're querying if you can determine it.
2. **No `.env`** → check `stream config list` for configured org/app → use those. Mention: "Querying configured app: `<app-name>`."
3. **Nothing** → tell the user: "No Stream credentials found. Run `stream auth login` to connect, or `cd` into a project with a `.env`."

| Phase | Name | What you do | WAIT? |
|-------|------|-------------|-------|
| **B1** | Resolve credentials | Run credential resolution above — silently if `.env` or config exists | Only if no credentials found |
| **B2** | Execute | `stream --safe api …` first; exit 5 → explain, confirm, retry without `--safe` | — |

---

## Track C — Bootstrap (install CLI / skill)

**Module:** **[`bootstrap.md`](bootstrap.md)**.

| Phase | Name | What you do | WAIT? |
|-------|------|-------------|-------|
| **C1** | Explain | What `stream` is; one confirmation to install | User confirms |
| **C2** | Install | Follow bootstrap (binary + `npx skills add GetStream/agent-skills`) | As needed |

---

## Track D — Docs search (no CLI gate)

**Module:** **[`docs-search.md`](docs-search.md)**.

The full docs-search engine: SDK identification (explicit input → project signals → keyword inference), `llms.txt` slug resolution, framework-index fetch, page fetch, cited answer. All honesty rules and URL-grounding rules live in `docs-search.md` — read it before answering.

| Phase | Name | What you do |
|-------|------|-------------|
| **D1** | Identify SDK | Explicit input wins — no probe. Only if SDK remains ambiguous, run the **project signals probe on demand** (inside `docs-search.md` § Inference tiers), then fall back to keyword tiers. |
| **D2** | Resolve slug | Fetch `llms.txt` once per conversation, find slug for product + framework |
| **D3** | Fetch + answer | Fetch the framework index (verbatim URLs), pick the right page, fetch it, quote and cite |

Track D never invokes Write, Edit, npm, scaffold tools, or `Bash(stream *)`. If the user asks for action mid-conversation, offer to switch tracks (D → B/A/E) and re-enter Step 0.

---

## Track E — Enhance existing app

For adding Stream products to an **existing Next.js project**. Uses references files and SDK patterns but skips scaffold entirely.

**Prerequisite:** Complete the **CLI gate** — install the `stream` CLI before npm installs, `stream api` setup, or token routes that depend on CLI-backed config.

### E1: Audit the existing project

Before writing any code, understand what's already in place:

1. **Packages:** Check `package.json` for `stream-chat`, `stream-chat-react`, `@stream-io/video-react-sdk`, `@stream-io/node-sdk`.
2. **Auth:** Does the app already have a `/api/token` route? If so, extend it with the new product's token — don't create a second token route.
3. **Credentials:** Check for `.env` with `STREAM_API_KEY` / `STREAM_API_SECRET`. If missing, run credential resolution (Track B).
4. **UI framework:** Confirm Tailwind, Shadcn, or whatever the project uses. Do **not** install Shadcn or change the styling setup unless the user asks.
5. **Directory structure:** Note whether the project uses `app/` or `src/app/` — match the existing convention.

### E2: Install + configure

1. **Install** only the new SDKs: `npm install <new-packages> --legacy-peer-deps` (RULES.md › Package manager).
2. **Configure** via CLI: run setup commands from the relevant `references/<Product>.md` (App Integration → Setup). For example, Feeds needs feed groups created; Moderation needs blocklist + config.
3. **Import CSS** if the product needs it (Chat: `stream-chat-react/dist/css/v2/index.css`, Video: `@stream-io/video-react-sdk/dist/css/styles.css`).

### E3: Integrate

1. **Token route:** Extend the existing `/api/token` to return the new product's token alongside existing ones. Follow `sdk.md` for server-side instantiation patterns.
2. **API routes:** Add product-specific routes from the relevant `references/<Product>.md` (App Integration → API Routes). Feeds needs several (`/api/feed/get`, `/api/feed/post`, etc.); Chat and Video typically only need the token route.
3. **Components:** Load the relevant `references/<Product>-blueprints.md` sections and build components using the existing project's patterns and styling conventions — not the builder-ui.md defaults.
4. **State:** If the app already manages user state (auth context, session), wire Stream tokens into that — don't add a separate Login Screen unless the app has no auth.

### E4: Verify

Run `npx next build` and fix any errors.

### Key constraints

- Do **not** re-scaffold, re-initialize Shadcn, install frontend skills, or modify `globals.css` / `layout.tsx`.
- Do **not** overwrite or restructure existing files — add new files alongside them.
- Do **not** change the existing auth flow. Adapt Stream's token generation to fit the app's existing auth, not the other way around.
- If the project uses a different package manager (yarn, pnpm), match what it already uses — the npm-only rule applies to new scaffolds, not existing projects.

---

## Paths (portable)

| What | Where |
|------|--------|
| Reference headers | `agent-skills/skills/stream/references/*.md` |
| Reference blueprints | `agent-skills/skills/stream/references/*-blueprints.md` |
| Docs search engine | `agent-skills/skills/stream/docs-search.md` |
| CLI endpoint index | `~/.stream/cache/API.md` after `stream api --refresh` |
| Skill modules | `agent-skills/skills/stream/` |

---

## Tooling (all hosts)

**Loading:** This file (`SKILL.md`) + `RULES.md` + files **named by the routing table** for the task. Track D loads `docs-search.md` only; tracks A/B/C/E load their respective modules.

**Batching:** One `bash -c` per builder phase where possible (never `-ce` — `-e` aborts on any non-zero exit, including `grep` finding nothing). `stream auth login` stays its own invocation for browser PKCE — never chain with `&&` or wrap in a heredoc.

**Support:** If the user asks for support or how to contact someone, direct them to [getstream.io/contact](https://getstream.io/contact/).
