---
name: stream-react
description: "Build, enhance, audit, or migrate a React / Next.js web app with Stream (Chat, Video, Feeds, Moderation) - the default for all web React work. Scaffold Next.js + Tailwind + Shadcn + Stream React SDKs end-to-end with Steps 0-7. Add Chat/Video/Feeds/Moderation to an existing React project (enhance). Audit an existing Stream Video integration against best practices. Migrate/upgrade an SDK version (e.g. v13 -> v14). Triggers on 'build me a ... app', 'scaffold', 'create a new ...', 'add Chat to this app', 'integrate Video', 'drop Feeds into ...', 'upgrade'/'migrate'/'bump ... version', and React / Next.js tokens: stream-chat-react, @stream-io/video-react-sdk, @stream-io/feeds-react-sdk, useCreateChatClient, useCreateFeedsClient, StreamVideo, Channel, MessageList. Covers livestreaming, video conferencing, team messaging, direct messaging, social feed. Web React only - not React Native (use stream-react-native)."
license: See LICENSE in repository root
metadata:
  author: GetStream
  requires:
    bins: ["getstream", "node", "npm"]
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(getstream *),
  Bash(npx *), Bash(npm install *), Bash(npm run *),
  Bash(yarn *), Bash(pnpm *),
  Bash(node -e *), Bash(node --version), Bash(openssl rand *),
  Bash(mv .scaffold*), Bash(rm -rf .scaffold),
  Bash(ls *), Bash(test *),
  Bash(grep *),
  Bash(cat package.json), Bash(cat go.mod), Bash(cat requirements.txt), Bash(cat pyproject.toml),
  WebFetch(domain:getstream.io),
  WebFetch(domain:www.npmjs.com),
  WebFetch(domain:github.com)
---

# Stream React (web) - scaffold + enhance + audit + migrate

> **Read first (every session):** Read [`RULES.md`](RULES.md) (React/Next.js non-negotiables) and the cross-cutting [`../stream/RULES.md`](../stream/RULES.md). Where the two files state the same rule differently (e.g. Strict mode protection, Package manager), **this pack's [`RULES.md`](RULES.md) wins for React work**. Glob `../stream/SKILL.md`; if empty, install with `getstream skills stream`.
>
> **CLI:** CLI usage (onboarding, credentials, auth, every `getstream api` call) lives in the root skill - its "Stream CLI" section in [`../stream/SKILL.md`](../stream/SKILL.md), with CLI safety in [`../stream/RULES.md`](../stream/RULES.md). Glob `../stream/SKILL.md`; install silently if missing (`getstream skills stream`).

This skill builds, enhances, audits, and migrates Stream Chat, Video, and Feeds in **React / Next.js web** apps - the default pack for all web React work. It covers **four tracks**:

- **Track A - Scaffold a new app:** Steps 0-7 below. Use when the cwd is empty / new and the user said "build me a ... app".
- **Track E - Enhance an existing app:** see [`enhance.md`](enhance.md). Skips scaffold + theme; reuses the same SDK wiring and component blueprints.
- **Track F - Audit an existing integration (read-only):** for "audit/review my video integration", "check my app against best practices", "is my video app production-ready?", "what am I missing before launch?". **Video only:** load the **Integration best-practices audit** section in [`references/VIDEO.md`](references/VIDEO.md) and follow its protocol - it has a Video-specific checklist + output contract. **If the user asks to audit Chat or Feeds**, say up front there is no dedicated best-practices checklist for those yet, then do a general docs-based review (fetch the relevant pages from [`references/DOCS.md`](references/DOCS.md) and check the app against them) rather than applying the Video checklist. **Skip onboarding, auth, the CLI, and all build steps** - this track only reads the app and reports findings. Fix issues only if the user then asks.
- **Track M - Migrate / upgrade an SDK version:** see [`migrate.md`](migrate.md). For "upgrade stream-chat-react to v14", "migrate to the new SDK", "bump my Stream version". Docs-driven: detect the installed version, fetch the matching release guide, apply it. Never migrate from memory.

### Flow dispatch - choose exactly one

- **Track A:** run `getstream init` to onboard (authenticate + select/create org + app + write credentials), then continue to **Start** and execute Steps 0-7.
- **Track E:** run `getstream init` to onboard (authenticate + select/create org + app + write credentials), then Read and execute [`enhance.md`](enhance.md). **Do not enter Start or any scaffold task.**
- **Track F:** skip onboarding and go directly to the audit in [`references/VIDEO.md`](references/VIDEO.md). **Do not enter Start or any build step.**
- **Track M:** skip onboarding and Read [`migrate.md`](migrate.md) first; it fetches the live release guide before any edit. **Do not enter Start or any scaffold task.**

---

## Docs-first triggers (consult docs before building)

**For any feature that matches a UI component, cookbook, or advanced-guide topic, fetch the matching Stream docs page BEFORE writing code.** The live docs are the source of truth for the current API and the recommended pattern; the bundled `references/*-blueprints.md` cover the common path only. Full keyword -> page map with exact URLs: [`references/DOCS.md`](references/DOCS.md). Enforced by [`RULES.md`](RULES.md) > Docs-first for cookbook / advanced features.

This skill is **prebuilt-component-first**: build the common path with the SDK's prebuilt React components and customize via the documented hooks/props - see [`RULES.md`](RULES.md) > Reference authority. The docs-first protocol covers both the **component reference pages** and the **cookbook / advanced** recipes:

- **UI Cookbook (customization / theming):** typing indicator, custom message UI, message actions, reactions customization, message composer / input UI, channel header, channel list preview, emoji picker, autocomplete / suggestion list, link previews, pin indicator, thread header, search, collapsible sidebar, system message / banner, mentions actions, attachment actions, hide channel history, localization / i18n; Video: replacing call controls, custom layouts, lobby preview, PiP, network quality, livestream watching, ringing.
- **Advanced Guides:** AI integrations (LangChain, AI SDK), advanced search, multiple lists, infinite scroll, read state, online status, location sharing, blocking, message reminders, notifications / web push, attachment previews, audio playback, date formatting, SDK state management, dialog management, TypeScript custom data, chat + video integration, recording, broadcasting, video filters.

When a request hits one of these: **match -> `WebFetch` the page's `.md` URL from [`references/DOCS.md`](references/DOCS.md) -> implement to match.** On fetch failure, hand to the `stream-docs` skill; if neither resolves the API, **stop and ask the user** - never build from memory.

---

## Start

> **Track A only.** Tracks E, F, and M branch in **Flow dispatch** above and never enter this section.

Once `getstream init` has onboarded (authenticated + selected/created org + app + written credentials), announce the network plan once, then **immediately start executing Steps 0-7** - do not ask permission to begin (the user has authorized the build by asking for it). The only pauses for input are the theme + app pick (Step 1b) and the skill-pack consent (Task A.2).

### Trust readout (announce, then continue on the same turn - do not wait)

Before the first network command, print this verbatim to the user, then proceed straight into Step 0 without stopping for a reply:

> Scaffolding now. Network calls you'll see:
> - `npx shadcn@latest ...` (Vercel) - scaffold + UI components from npm.
> - `npm install <stream-packages> --legacy-peer-deps` - Stream SDKs from npm (`stream-chat-react`, `@stream-io/video-react-sdk`, etc.).
> - `getstream env` - local CLI, no network; writes `.env.local` (gitignored by the Next.js scaffold's default; Task B verifies).
>
> Interrupt me at any point if something looks wrong. I'll pause twice for your input: the theme + Stream-app pick (Step 1b) and the optional third-party skill packs (Task A.2).

Full per-command audit (publisher, why unpinned, what each writes): section Install trust & integrity below. The user's continued silence after the readout is implicit consent for this scaffold; an objection or stop instruction aborts the run.

Shadcn/ui is always installed during Step 3. Third-party **frontend skills** (`vercel-react-best-practices`, `web-design-guidelines`, `frontend-design`) are installed **only with explicit user consent** - see Task A.2 for the disclosure script. If the user declines, Step 4 proceeds using Stream references only. **Precedence (when the skills are present):** Stream references win for SDK wiring; frontend skills guide generic React / UI polish.

---

## Install trust & integrity

This builder runs three classes of network-touching commands. Each is listed here so a reviewer can audit before approving. CLI install instructions live in the root skill's "Stream CLI" section in [`../stream/SKILL.md`](../stream/SKILL.md).

| Command | Publisher | Why unpinned | What it writes |
|---|---|---|---|
| `npx shadcn@latest init ...` (Task A) | Vercel - [`shadcn-ui/ui`](https://github.com/shadcn-ui/ui) | Scaffolder; `@latest` is the maintainer's documented usage. Pinning ships outdated scaffolds. | Project files in cwd. Next.js scaffold's `.gitignore` ignores `.env*` by default. |
| `npx shadcn@latest add ...` (Task A.1) | Vercel - same source as above | Same scaffolder; component sync depends on registry parity. | Component files under `components/ui/`. |
| `npm install <stream-packages> --legacy-peer-deps` (Task C) | GetStream (npm) for `@stream-io/*` and `stream-chat-react`; transitive deps via standard npm trust | Latest published versions of GetStream's own SDKs - same trust model as the CLI itself. | Modules under `node_modules/`. Runtime SDKs + transitive deps. |
| `npx skills add <github>` (Task A.2) | `vercel-labs/agent-skills` and `anthropics/skills` | Optional. Markdown-only skill packs; `npx skills add` is the published install path. | Markdown files in the user's skills directory. **Gated by explicit user consent in Task A.2** - never runs without an affirmative answer. |
| `getstream env` (Task B) | GetStream - install instructions in the root skill's "Stream CLI" section in [`../stream/SKILL.md`](../stream/SKILL.md) | n/a (local CLI, no network at this step) | `.env.local` in the project root with `NEXT_PUBLIC_STREAM_API_KEY` + `STREAM_API_SECRET`. Task B verifies `.gitignore` covers `.env*` before writing (Next.js scaffold's default already does). The agent never reads `.env.local` (RULES.md > Secrets). |

**Reviewer checklist:**

- All `npx` invocations resolve to the publishers listed above; substitute a different publisher and the install fails.
- `npx skills add` runs **only after** the disclosure prompt in Task A.2 and an explicit user "yes."
- `.env.local` is written by the Stream CLI directly, not by the agent, and is not transmitted into the conversation.
- If the user wants to pin a specific shadcn version, replace `@latest` with `@<version>` in Tasks A and A.1.

---

## Builder Steps

Execute phases **in order** (later steps depend on earlier ones). Do **not** run independent phases in parallel. Shell discipline (one `bash -c` per phase, no `bash -ce`, `getstream login` standalone) lives in [`../stream/RULES.md`](../stream/RULES.md) > Shell discipline.

**Two-call exception:** If you must Read JSON (e.g. `OrganizationRead`) and then choose IDs, use one call for the read, one batched call for all creates.

### Step 0: Package manager
Always use `npm`. Never use bun. ([`RULES.md`](RULES.md) > Package manager.)

### Step 1: Auth
Run the **Provisioning > Step 1: Auth** flow in [`builder.md`](builder.md) (auth probe via `getstream api OrganizationRead`; `getstream login` as its own invocation on exit 2; hang recovery). On **exit 0**, continue to Step 1b.

### Step 1b: Theme + app pick

Ask both setup questions in **one message** before doing anything else - a single pause, the same "ask exactly once, then act" pattern the other platform packs use for credentials. Build the app options from what is already in context: the configured org/app from `getstream init` and the org list from Step 1's `OrganizationRead` output.

> **Quick setup - two questions:**
> 1. **Theme:** I can use a random shadcn theme, or you can design your own at [ui.shadcn.com/create](https://ui.shadcn.com/create) and share the `--preset` value (e.g. `--preset b1Gdi7z7r`). Random, or do you have a preset?
> 2. **Stream app:** *(an app is configured)* Use the currently configured app **`<name>`** (default), pick another existing org/app, or create a fresh one? / *(no app configured)* You have these orgs: `<list>`. Pick one to use - I'll list its apps - or create a fresh org + app?

**STOP here and wait for the user's answer.** Do not continue with any other step until the user responds. Asking a question and continuing to work in parallel is confusing - the user misses the question as output scrolls past.

- **Theme - preset provided** -> store it for Task A scaffold command. **Random / doesn't care** -> pick a random preset from `nova`, `vega`, `maia`, `lyra`, `mira`, `luma`.
- **App - named choice, "default", or "don't care"** -> Step 2 applies it (the configured app wins whenever one exists). **Create new** -> Step 2 runs the create flow.
- **Account has no orgs at all** -> drop question 2, announce that a fresh org + app will be created, and ask only the theme.

### Step 2: Pick org + app
Run **Provisioning** in [`builder.md`](builder.md): `getstream init` handles auth and org/app selection-or-creation (including the Feeds v3 region choice). Let `init` drive it - interactively or via its command file; don't provision with raw `getstream api` calls.

### Step 3: Scaffold + .env + SDKs + Configure - SEQUENTIALLY

#### Scaffold order

Order:

1. **Steps 1-1b:** Auth + theme/app pick (wait for answer).
2. **Step 2:** Apply the org/app choice (select existing or create).
3. **Task A:** Scaffold with Shadcn + Next.js using the chosen preset.
4. **Task A.1:** Add base Shadcn components.
5. **Task A.2:** Disclose + ask about third-party frontend skill installs; install only with user consent.
6. Continue with Task B (.env), Task C (SDKs), Task D (CLI config).

**Task A: Scaffold** - scaffolds Next.js + Tailwind + Shadcn/ui (Base UI) into the current directory. Use the theme preset chosen in **Step 1b**.

The scaffold command creates a new directory, so we scaffold into a temporary `.scaffold` subdirectory and move everything up:

```bash
npx shadcn@latest init -t next -b base -n .scaffold --no-monorepo -p <random-preset> && mv .scaffold/* .scaffold/.* . 2>/dev/null; rm -rf .scaffold
```

**Task A.1: Add base Shadcn components:**

```bash
npx shadcn@latest add button input textarea card avatar badge separator
```

Add more components as the use case requires (e.g. `dialog`, `dropdown-menu`, `tabs`, `popover`).

**Task A.2: Frontend skills** - third-party skill packs. **You must disclose and ask before installing.** Do NOT construct your own command variant.

Print this disclosure verbatim, then stop and wait for the user's answer:

> I'd like to install three third-party skill packs that improve generic UI quality:
> - `vercel-react-best-practices` - from [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills)
> - `web-design-guidelines` - from [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills)
> - `frontend-design` - from [`anthropics/skills`](https://github.com/anthropics/skills)
>
> The packs are markdown only - no scripts execute. If you say yes, I'll run `npx skills add ... -y` once per pack from those GitHub repos at their current `main` branch (`-y` skips the installer's own confirmation since you've consented here). These aren't required - Stream reference files cover SDK wiring either way. Install them?

- **User agrees** -> run:
  ```bash
  npx skills add https://github.com/vercel-labs/agent-skills --skill vercel-react-best-practices -y && npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines -y && npx skills add https://github.com/anthropics/skills --skill frontend-design -y
  ```
- **User declines** -> skip silently and continue to Task B. Do not retry, do not bring it up again this session.
- **Install fails** -> continue with Stream reference files only; mention the failure briefly.

Do **not** modify `layout.tsx` or `globals.css` after scaffold - use Shadcn's defaults as-is (RULES.md > Theme).

**Task B: .env** - run AFTER scaffold so the `.env` lands inside the project directory.

**First, verify `.env*` is gitignored** ([`../stream/RULES.md`](../stream/RULES.md) > Secrets). The Next.js scaffold's default already includes it; this is a safety net for projects whose `.gitignore` was hand-edited or doesn't yet exist. Use the **file tools** (no shell) so no broad `bash -c` permission is needed:

- `Grep` for `^\.env` in `.gitignore` (or `Read` it). If it already ignores `.env*`, do nothing.
- If `.gitignore` exists but has no `.env` entry, **`Edit`** it to append a line `.env*`.
- If `.gitignore` does not exist, **`Write`** a new `.gitignore` containing `.env*`.

(Inspecting/editing `.gitignore` is fine; **never** Read or Edit `.env` itself - [`../stream/RULES.md`](../stream/RULES.md) > Secrets.)

Then write secrets:

```bash
getstream env
```

`getstream env` detects the Next.js project and writes `NEXT_PUBLIC_STREAM_API_KEY` + `STREAM_API_SECRET` to `.env.local`. The secret is server-side only - used by `/api/token` to mint tokens, never in the client bundle. The public API key may be read client-side from `NEXT_PUBLIC_STREAM_API_KEY` or returned via `/api/token`. The agent never reads `.env.local` ([`RULES.md`](RULES.md) > Env vars).

**Task C: Install Stream SDKs + verify icons** - Only what the use case needs:

```bash
# Chat:     stream-chat stream-chat-react
# Video:    @stream-io/video-react-sdk
# Feeds:    @stream-io/feeds-react-sdk
# Server:   @stream-io/node-sdk
npm install <packages> --legacy-peer-deps
```

After installing SDKs, verify an icon package is available. Some Shadcn presets bundle one, others don't:

```bash
node -e "try{require.resolve('lucide-react');console.log('ICONS_OK')}catch{try{require.resolve('@phosphor-icons/react');console.log('ICONS_OK')}catch{console.log('NO_ICONS')}}"
```

If `NO_ICONS`, install `lucide-react`: `npm install lucide-react --legacy-peer-deps`. If an icon package is already present, use that one throughout the app - do not install a second.

**Task D: Configure Stream** - run the CLI commands from the relevant [`references/<Product>.md`](references/) (App Integration -> Setup) for each product the use case needs.

### Step 4: Generate code and UI

**Prebuilt-component-first.** Build the common path with the SDK's prebuilt React components and customize via the documented hooks/props ([`RULES.md`](RULES.md) > Reference authority). Hand-build markup only when the user explicitly wants fully bespoke UI.

**Docs-first:** before implementing any component, cookbook, or advanced feature (typing indicator, custom message UI, reactions, AI integrations, read state, notifications, call layouts, ...), follow the **Docs-first triggers** section above - `WebFetch` the matching [`references/DOCS.md`](references/DOCS.md) page first, then build to match.

**Load [`builder-ui.md`](builder-ui.md) and [`sdk.md`](sdk.md)** (cross-cutting SDK wiring: token route, instantiation, CSS imports), plus **only** the relevant [`references/<Product>.md`](references/) header + `references/<Product>-blueprints.md` for the sections you are implementing - not every reference file. Pull **Use Case Matching** and **Page Flow** from [`builder.md`](builder.md) to choose products and navigation structure. **For multi-product apps (Chat + Video, Chat + Feeds, Video + Feeds, etc.), also load [`references/CROSS-PRODUCT.md`](references/CROSS-PRODUCT.md) before writing AppShell** - it has the canonical multi-client provider hierarchy and an error -> cause -> fix table.

### Step 5: Verify

**Type-check first** (reports ALL errors at once, ~3s):
```bash
npx tsc --noEmit
```
Fix all type errors. Then run the full build:
```bash
npx next build
```
Fix any remaining errors. Do NOT skip `tsc --noEmit` - it catches every type error in one pass, while `next build` stops at the first error per file and requires multiple rebuild cycles.

### Step 6: Start dev server
Pick a random 5-digit port (10000-65535). Run the server using `run_in_background`:

```bash
PORT=$((RANDOM % 55536 + 10000))
npx next dev -p $PORT
```

**Important:** The dev server is a long-running process. When run in the background it will eventually emit a "completed" notification - this does **not** mean the server stopped. The server is still running and serving requests. **Do not** respond to the background-task completion notification by telling the user the server has stopped. If you receive that notification after Step 7, ignore it silently - do not output anything.

### Step 7: Summary
Show the org/app used (created or selected), plus resources and files created. Include the local URL. Do NOT say "you can now start the dev server" - it's already running.

End with:

> Open `http://localhost:<PORT>`, enter a username, and start testing. Open a second tab with a different username to test multi-user interactions.

---

## Use Case Matching and Page Flow

Both live in [`builder.md`](builder.md) (Use Case Matching, Page Flow). Match the user's words to a use case there, then build only the products that use case needs and follow the hub-first navigation it describes. **Moderation** is configured via CLI during setup only - **never build moderation review UI** ([`RULES.md`](RULES.md) > Moderation is Dashboard-only).

---

## Cross-Product Integration

When building apps that combine multiple products, read each relevant [`references/<Product>.md`](references/) App Integration section. Key patterns:

- **Combined token route:** `/api/token` returns tokens for each product (`{ chatToken, videoToken, feedToken, apiKey }`). Upsert only the requesting user - never seed demo users ([`../stream/RULES.md`](../stream/RULES.md) > No auto-seeding).
- **Video + Feeds (Livestreaming):** Feed hub separates `type === "live"` activities as prominent live cards. "Go Live" posts a live activity via `/api/feed/live`. "End Stream" removes it.
- **Video + Chat (Livestreaming):** Chat alongside video on the watch screen. Use `livestream` channel type - one channel per stream, keyed by call ID. Create the chat channel in the `/api/token` route.
- **Moderation (all use cases):** Run Moderation CLI setup commands from [`references/MODERATION.md`](references/MODERATION.md) (App Integration -> Setup), adjusting channel type name. **Never build moderation review UI** ([`RULES.md`](RULES.md) > Moderation is Dashboard-only).

For multi-product provider nesting, load [`references/CROSS-PRODUCT.md`](references/CROSS-PRODUCT.md).

---

## Reference file paths

Blueprint files live in the `references/` directory **next to this SKILL.md**. Resolve them relative to this skill's own directory, wherever the pack is installed (e.g. `<skill-dir>/references/FEEDS.md`). Do not hardcode machine-specific absolute paths or assume a repo-checkout layout.
