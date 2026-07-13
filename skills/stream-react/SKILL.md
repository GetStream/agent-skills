---
name: stream-react
description: "Build, enhance, audit, or migrate a React / Next.js web app with Stream (Chat, Video, Feeds, Moderation) - the default for all web React work. Scaffold Next.js + Tailwind + Shadcn + Stream React SDKs end-to-end with Steps 0-7. Add Chat/Video/Feeds/Moderation to an existing React project (enhance). Audit an existing Stream Video integration against best practices. Migrate/upgrade an SDK version (e.g. v13 -> v14). Triggers on 'build me a ... app', 'scaffold', 'create a new ...', 'add Chat to this app', 'integrate Video', 'drop Feeds into ...', 'upgrade'/'migrate'/'bump ... version', and React / Next.js tokens: stream-chat-react, @stream-io/video-react-sdk, @stream-io/feeds-react-sdk, useCreateChatClient, useCreateFeedsClient, StreamVideo, Channel, MessageList. Covers livestreaming, video conferencing, team messaging, direct messaging, social feed. Web React only - not React Native (use stream-react-native)."
license: See LICENSE in repository root
metadata:
  author: GetStream
  requires:
    bins: ["getstream", "node", "npm"]
allowed-tools: >-
  Read, Write, Edit, Glob, Grep, Task,
  Bash(getstream *),
  Bash(npx *), Bash(npm install *), Bash(npm run *),
  Bash(yarn *), Bash(pnpm *),
  Bash(node -e *), Bash(node --version), Bash(node .design-verify/*), Bash(openssl rand *),
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
- **Track F - Audit an existing integration (read-only):** for "audit/review my video integration", "check my app against best practices", "is my video app production-ready?", "what am I missing before launch?". **Video only:** load the **Integration best-practices audit** section in [`references/VIDEO.md`](references/VIDEO.md) and follow its protocol - it has a Video-specific checklist + output contract. **If the user asks to audit Chat or Feeds**, say up front there is no dedicated best-practices checklist for those yet, then do a general docs-based review (fetch the relevant pages from [`references/docs-map.md`](references/docs-map.md) and check the app against them) rather than applying the Video checklist. **Skip onboarding, auth, the CLI, and all build steps** - this track only reads the app and reports findings. Fix issues only if the user then asks.
- **Track M - Migrate / upgrade an SDK version:** see [`migrate.md`](migrate.md). For "upgrade stream-chat-react to v14", "migrate to the new SDK", "bump my Stream version". Docs-driven: detect the installed version, fetch the matching release guide, apply it. Never migrate from memory.

### Flow dispatch - choose exactly one

- **Track A:** run `getstream init` to onboard (authenticate + select/create org + app + write credentials), then continue to **Start** and execute Steps 0-7.
- **Track E:** run `getstream init` to onboard (authenticate + select/create org + app + write credentials), then Read and execute [`enhance.md`](enhance.md). **Do not enter Start or any scaffold task.**
- **Track F:** skip onboarding and go directly to the audit in [`references/VIDEO.md`](references/VIDEO.md). **Do not enter Start or any build step.**
- **Track M:** skip onboarding and Read [`migrate.md`](migrate.md) first; it fetches the live release guide before any edit. **Do not enter Start or any scaffold task.**

**Styling-depth flag (orthogonal to the track).** If the request carries a **target appearance** - an attached screenshot, a Figma frame, or "make it look like WhatsApp / Slack / <app>" - route through [`references/design-matching.md`](references/design-matching.md): a reference design is a **checklist of regions, not a color tweak**. Its pipeline is **Classify -> Design analysis -> Route -> Ground -> Build -> Verify**, run as a coordinator-agent orchestration (parallel subagents where the harness dispatches them; inline serially where not): classify the fidelity tier + viewport, produce a fine-grained design analysis at `.design-verify/design-analysis.md` that **names the Stream concept behind every visual signal** via per-product identification checklists (chat / video / feeds), route each region to a component + mechanism (theming / injection -> the [`references/custom-ui.md`](references/custom-ui.md) completion contract / bespoke), ground the names against the live docs, build batched, and close with **an empirical verify loop - screenshot + computed-style checks via session browser tooling or a Playwright fallback - iterated until the spec table passes**. This composes with the track: **Track A** scaffolds first, then matches before Step 4's build; **Track E** matches within E3. Load it **before** writing UI.

---

## Docs-first triggers (consult docs before building)

**For any feature that matches a UI component, cookbook, or advanced-guide topic, fetch the matching Stream docs page BEFORE writing code.** The live docs are the source of truth for the current API and the recommended pattern; the bundled `references/*-blueprints.md` cover the prebuilt common path only. Full keyword -> page map with exact URLs: [`references/docs-map.md`](references/docs-map.md) - it opens with the **docs convention** (the `.md`-twin rule + per-product live index) so any unmapped page is still reachable: never guess a path, fetch the index. Enforced by [`RULES.md`](RULES.md) > Docs-first for cookbook / advanced features.

This skill is **prebuilt-component-first**: build the common path with the SDK's prebuilt React components and customize via the documented hooks/props - see [`RULES.md`](RULES.md) > Reference authority. The docs-first protocol covers both the **component reference pages** and the **cookbook / advanced** recipes:

- **UI Cookbook (customization / theming):** typing indicator, custom message UI, message actions, reactions customization, message composer / input UI, channel header, channel list preview, emoji picker, autocomplete / suggestion list, link previews, pin indicator, thread header, search, collapsible sidebar, system message / banner, mentions actions, attachment actions, hide channel history, localization / i18n; Video: replacing call controls, custom layouts, lobby preview, PiP, network quality, livestream watching, ringing.
- **Advanced Guides:** AI integrations (LangChain, AI SDK), advanced search, multiple lists, infinite scroll, read state, online status, location sharing, blocking, message reminders, notifications / web push, attachment previews, audio playback, date formatting, SDK state management, dialog management, TypeScript custom data, chat + video integration, recording, broadcasting, video filters.

When a request hits one of these: **match -> `WebFetch` the page's `.md` URL from [`references/docs-map.md`](references/docs-map.md) -> implement to match.** On fetch failure, hand to the `stream-docs` skill; if neither resolves the API, **stop and ask the user** - never build from memory.

---

## Start

> **Track A only.** Tracks E, F, and M branch in **Flow dispatch** above and never enter this section.

Once `getstream init` has onboarded (authenticated + selected/created org + app + written credentials), announce the network plan once, then **immediately start executing Steps 0-7** - do not ask permission to begin (the user has authorized the build by asking for it). The only pause for input is the theme + app pick (Step 1b).

### Trust readout (announce, then continue on the same turn - do not wait)

Before the first network command, print this verbatim to the user, then proceed straight into Step 0 without stopping for a reply:

> Scaffolding now. Network calls you'll see:
> - `npx shadcn@latest ...` (Vercel) - scaffold + UI components from npm.
> - `npm install <stream-packages> --legacy-peer-deps` - Stream SDKs from npm (`stream-chat-react`, `@stream-io/video-react-sdk`, etc.).
> - `getstream env` - local CLI, no network; writes `.env.local` (gitignored by the Next.js scaffold's default; Task B verifies).
>
> Interrupt me at any point if something looks wrong. I'll pause once for your input: the theme + Stream-app pick (Step 1b).

Full per-command audit (publisher, why unpinned, what each writes): section Install trust & integrity below. The user's continued silence after the readout is implicit consent for this scaffold; an objection or stop instruction aborts the run.

Shadcn/ui is always installed during Step 3. **stream-react does not install third-party frontend skills** - the build uses Stream references + Shadcn. **If** frontend skill packs (`frontend-design`, `vercel-react-best-practices`, `web-design-guidelines`) are already available in the session, use them for generic React / UI polish only; Stream references remain authoritative for SDK wiring.

---

## Install trust & integrity

This builder runs three classes of network-touching commands. Each is listed here so a reviewer can audit before approving. CLI install instructions live in the root skill's "Stream CLI" section in [`../stream/SKILL.md`](../stream/SKILL.md).

| Command | Publisher | Why unpinned | What it writes |
|---|---|---|---|
| `npx shadcn@latest init ...` (Task A) | Vercel - [`shadcn-ui/ui`](https://github.com/shadcn-ui/ui) | Scaffolder; `@latest` is the maintainer's documented usage. Pinning ships outdated scaffolds. | Project files in cwd. Next.js scaffold's `.gitignore` ignores `.env*` by default. |
| `npx shadcn@latest add ...` (Task A.1) | Vercel - same source as above | Same scaffolder; component sync depends on registry parity. | Component files under `components/ui/`. |
| `npm install <stream-packages> --legacy-peer-deps` (Task C) | GetStream (npm) for `@stream-io/*` and `stream-chat-react`; transitive deps via standard npm trust | Latest published versions of GetStream's own SDKs - same trust model as the CLI itself. | Modules under `node_modules/`. Runtime SDKs + transitive deps. |
| `getstream env` (Task B) | GetStream - install instructions in the root skill's "Stream CLI" section in [`../stream/SKILL.md`](../stream/SKILL.md) | n/a (local CLI, no network at this step) | `.env.local` in the project root with `NEXT_PUBLIC_STREAM_API_KEY` + `STREAM_API_SECRET`. Task B verifies `.gitignore` covers `.env*` before writing (Next.js scaffold's default already does). The agent never reads `.env.local` (RULES.md > Secrets). |
| Playwright into a self-contained `.design-verify/` harness (`npm install --prefix .design-verify -D playwright` + browser install) - design-matching verify-loop fallback only | Microsoft - [`microsoft/playwright`](https://github.com/microsoft/playwright) | Latest published; runs **only** when a design match needs a capture and no in-session browser tooling exists (may never run), announced inline at point of use. | Everything under `.design-verify/` (its own `package.json` + `node_modules`, gitignored) - **the app's `package.json` / lockfile are untouched** - plus ~120MB Chromium in the shared Playwright cache. Deleted wholesale at loop exit; nothing lands in the app manifest. |

**Reviewer checklist:**

- All `npx` invocations resolve to the publishers listed above; substitute a different publisher and the install fails.
- `.env.local` is written by the Stream CLI directly, not by the agent, and is not transmitted into the conversation.
- If the user wants to pin a specific shadcn version, replace `@latest` with `@<version>` in Tasks A and A.1.
- The Playwright row is a **design-matching verify-loop fallback**, not part of the scaffold: it is announced inline if and when it runs (it may never run), installs only into a self-contained `.design-verify/` harness (never the app root), and does **not** appear in the Start trust readout above.

---

## Builder Steps

Execute phases **in order** (later steps depend on earlier ones). Do **not** run independent phases in parallel. **One exception:** when [`references/design-matching.md`](references/design-matching.md) is active, its Orchestration section governs scheduling - the design-analysis agent runs concurrently with the Steps 0-3 setup work, and builds / verifies fan out per its role table; everything else here stays sequential. Shell discipline (one `bash -c` per phase, no `bash -ce`, `getstream login` standalone) lives in [`../stream/RULES.md`](../stream/RULES.md) > Shell discipline.

**Two-call exception:** If you must Read JSON from a `getstream api` call and then choose IDs, use one call for the read, one batched call for all creates.

### Step 0: Package manager
Always use `npm`. Never use bun. ([`RULES.md`](RULES.md) > Package manager.)

### Step 1: Auth
Authentication is handled by `getstream init` (Step 2) - it opens the browser as its **own invocation** if you're not signed in ([`builder.md`](builder.md) > Provisioning; [`../stream/RULES.md`](../stream/RULES.md) > Shell discipline). There is **no separate `getstream api` auth probe** - CLI v1.0.0 removed the pre-1.0 `OrganizationRead` probe, and `getstream api` subcommands are now product-namespaced (e.g. `getstream api chat ...`). Continue to Step 1b.

### Step 1b: Theme + app pick

Ask both setup questions in **one message** before doing anything else - a single pause, the same "ask exactly once, then act" pattern the other platform packs use for credentials. Build the app options from what is already in context: the org/app already configured in this project by a prior `getstream init`, if any. If none is configured yet, `getstream init` lists your orgs/apps when it runs (Step 2) - interactively with a TTY; in a non-interactive shell it writes a `.stream/init-*.yaml` command file to uncomment instead ([`builder.md`](builder.md) > Provisioning documents the exact headless sequence). Don't try to enumerate them with a raw `getstream api` call.

> **Quick setup - two questions:**
> 1. **Theme:** I can use a random shadcn theme, or you can design your own at [ui.shadcn.com/create](https://ui.shadcn.com/create) and share the `--preset` value (e.g. `--preset b1Gdi7z7r`). Random, or do you have a preset? *(If you already shared a screenshot or Figma, I'll match that instead - skip this.)*
> 2. **Stream app:** *(an app is already configured)* Use the currently configured app **`<name>`** (default), or pick/create a different one? / *(no app configured yet)* `getstream init` will list your orgs and apps when it runs - use an existing one, or create a fresh org + app?

**STOP here and wait for the user's answer.** Do not continue with any other step until the user responds. Asking a question and continuing to work in parallel is confusing - the user misses the question as output scrolls past.

- **Theme - preset provided** -> store it for Task A scaffold command. **Random / doesn't care** -> pick a random preset from `nova`, `vega`, `maia`, `lyra`, `mira`, `luma`.
- **Theme - a reference design (screenshot / Figma) was provided** -> the design dictates the theme: **skip question 1**, pick the shadcn preset closest to the sampled palette, ask only question 2 (the Stream app), and match the design via [`references/design-matching.md`](references/design-matching.md).
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
5. Continue with Task B (.env), Task C (SDKs), Task D (CLI config).

**Task A: Scaffold** - scaffolds Next.js + Tailwind + Shadcn/ui (Base UI) into the current directory. Use the theme preset chosen in **Step 1b**.

The scaffold command creates a new directory, so we scaffold into a temporary `.scaffold` subdirectory and move everything up. The `-n .scaffold` flag also lands in the generated `package.json` as `"name": ".scaffold"`, which npm/pnpm/yarn reject (a package name can't start with `.`), so the final step rewrites `name` to a valid slug derived from the project directory:

```bash
npx shadcn@latest init -t next -b base -n .scaffold --no-monorepo -p <random-preset> && mv .scaffold/* .scaffold/.* . 2>/dev/null; rm -rf .scaffold && node -e "const fs=require('fs'),path=require('path'),j=require('./package.json');j.name=path.basename(process.cwd()).toLowerCase().replace(/[^a-z0-9._-]+/g,'-').replace(/^[._-]+/,'')||'app';fs.writeFileSync('package.json',JSON.stringify(j,null,2)+'\n')"
```

**Task A.1: Add base Shadcn components:**

```bash
npx shadcn@latest add button input textarea card avatar badge separator
```

Add more components as the use case requires (e.g. `dialog`, `dropdown-menu`, `tabs`, `popover`).

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

After installing SDKs, note the resolved **Stream Chat React major**: the bundled blueprints assume **v14** (`MessageComposer`, `stream-chat-react/css/index.css`). `@latest` is v14 today; if a future install resolves a **newer major**, fetch that major's component reference from [`references/docs-map.md`](references/docs-map.md) (Version note) before writing the provider tree - don't apply v14 names from memory.

Also verify an icon package is available. Some Shadcn presets bundle one, others don't:

```bash
node -e "const p=['lucide-react','@phosphor-icons/react','@hugeicons/react'];console.log(p.some(m=>{try{require.resolve(m);return true}catch{return false}})?'ICONS_OK':'NO_ICONS')"
```

If `NO_ICONS`, install `lucide-react`: `npm install lucide-react --legacy-peer-deps`. If an icon package is already present, use that one throughout the app - do not install a second.

**Task D: Configure Stream** - run the CLI commands from the relevant [`references/<Product>.md`](references/) (App Integration -> Setup) for each product the use case needs.

### Step 4: Generate code and UI

**Prebuilt-component-first.** Build the common path with the SDK's prebuilt React components and customize via the documented hooks/props ([`RULES.md`](RULES.md) > Reference authority). Writing your own component for a region (custom message row, composer, channel preview/header, call layout) - not just passing props - loads [`references/custom-ui.md`](references/custom-ui.md) (the completion contract) first; see [`RULES.md`](RULES.md) > Reference authority.

**Docs-first:** before implementing any component, cookbook, or advanced feature (typing indicator, custom message UI, reactions, AI integrations, read state, notifications, call layouts, ...), follow the **Docs-first triggers** section above - `WebFetch` the matching [`references/docs-map.md`](references/docs-map.md) page first, then build to match.

**Load [`builder-ui.md`](builder-ui.md) and [`sdk.md`](sdk.md)** (cross-cutting SDK wiring: token route, instantiation, CSS imports), plus **only** the relevant [`references/<Product>.md`](references/) header + `references/<Product>-blueprints.md` (the prebuilt provider tree + props) for the product(s) you are implementing - not every reference file. For any customization, fetch the matching live page from [`references/docs-map.md`](references/docs-map.md) first (and if you are writing your own component for a region, load [`references/custom-ui.md`](references/custom-ui.md) first per Step 4's rule above / [`RULES.md`](RULES.md) > Reference authority). Pull **Use Case Matching** and **Page Flow** from [`builder.md`](builder.md) to choose products and navigation structure. **For multi-product apps (Chat + Video, Chat + Feeds, Video + Feeds, etc.), also load [`references/CROSS-PRODUCT.md`](references/CROSS-PRODUCT.md) before writing AppShell** - it has the canonical multi-client provider hierarchy and an error -> cause -> fix table.

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

### Step 6b: Smoke-check the render (required)

A green `tsc` + `next build` (Step 5) says nothing about what the user sees - it compiles, it does not render. Before the summary, **capture at least one screenshot of the logged-in main screen and actually look at it**, using the tool ladder in [`references/design-matching.md`](references/design-matching.md) > 6b (in-session browser tooling first, else the Playwright fallback; the `networkidle` and capture gotchas in 6c apply). You are checking for gross breakage the build cannot catch: a blank / splash-stuck screen, unstyled or collapsed layout, a region not filling its pane, or console errors. Fix what you see and re-capture.

**If the request carried any target appearance** - an attached screenshot, a Figma frame, or "make it look like <app>" - this smoke check is **not** enough: you must run the full [`references/design-matching.md`](references/design-matching.md) Step 6 verify loop (a per-region spec table diffed against a this-round capture). A referenced build that skipped that loop is unfinished, not merely unpolished - catching it here is the backstop if the styling-depth flag was missed at Start.

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
