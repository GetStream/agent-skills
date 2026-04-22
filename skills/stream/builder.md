# Builder - scaffold execution (Track A)

Phase table: [`SKILL.md`](SKILL.md) Track A. Rules: [`RULES.md`](RULES.md) (secrets, no auto-seeding, login screen first, phase order, package manager).

---

## A1: CLI gate + probe

Follow **[`SKILL.md`](SKILL.md) › CLI gate** first: if `stream` is missing, install via **`bootstrap.md`** after user permission - **do not** start Steps 0–7 until the CLI works.

Then run the probe and report the result as a **single line** with a checkmark. Do **not** use a heading, section number, or bullet list - just one line:

- **Found → output exactly:** `✓ Stream CLI v0.1.0` (substitute actual version)
- **Not found →** you must not reach A2; follow **`bootstrap.md`** until installed (or user declines - then stop builder work).

```bash
bash -c 'command -v stream >/dev/null 2>&1 && stream --version || echo "STREAM_CLI_NOT_FOUND"'
```

If the sandbox blocks the probe, say so and ask the user to confirm `stream` is installed.

## A2: Immediate execution

After the CLI is verified (and the **CLI gate** satisfied), **immediately start executing Steps 0–7**. No prompts, no checklist, no confirmation. Just build it step by step.

Shadcn/ui is always installed during Step 3. Third-party **frontend skills** (`vercel-react-best-practices`, `web-design-guidelines`, `frontend-design`) are installed **only with explicit user consent** — see Task A.2 for the disclosure script. If the user declines, Step 4 proceeds using Stream references only. **Precedence (when the skills are present):** Stream references win for SDK wiring; frontend skills guide generic React / UI polish.

---

## Builder Steps (A3 execution)

Execute phases **in order** (later steps depend on earlier ones). Do **not** run independent phases in parallel.

### Sandboxed agents / fewer "Run" prompts

**Rule - one invocation per phase:** Wrap everything in `bash -c '…'` and chain with `&&` on one line. **Do NOT use `bash -ce` or `set -e`** — `grep` (and friends) return exit 1 on "no match," which aborts the entire probe and leaves you with partial or no output. If you need to tolerate specific failures, handle them explicitly (`|| echo NOT_FOUND`, `|| true`) rather than relying on `-e`.

**When you need two calls:** If you must Read JSON (e.g. `OrganizationRead`) and then choose IDs, use one call for the read, one batched call for all creates + `stream config set`.

**Exception - browser auth:** `stream auth login` stays its own invocation so the browser can open.

### Step 0: Package manager
Always use `npm`. Never use bun.

### Step 1: Auth

**Test auth first, then act — don't skip this and don't wait until Step 2 surfaces an error.** Run `stream api OrganizationRead` as a probe:

- **Exit 0** → already authenticated, continue to Step 1b.
- **Exit 2 / "not authenticated"** → **immediately** run `stream auth login` as its **own** Bash invocation. This is a hard constraint:
  - Browser PKCE requires an unwrapped `stream auth login` call — **never** chain with `&&`, embed in a heredoc, or bundle with other commands.
  - Do not ask the user first; just run it. Give it up to ~3 minutes for the browser flow.
- **Login hangs past ~60s, or the user reports the browser is stuck** → run `stream auth logout` to clear any stale session state, then retry `stream auth login` **once**. If the second attempt also hangs, stop and ask the user to run `! stream auth login` themselves (the `!` prefix runs it in-session so you see the result).

### Step 1b: Theme pick

Ask the user which Shadcn theme they'd like **before doing anything else**:

> **Quick theme pick:** I can use a random shadcn theme, or you can design your own at [ui.shadcn.com/create](https://ui.shadcn.com/create) and share the `--preset` value (e.g. `--preset b1Gdi7z7r`). Want a random one or do you have a preset?

**STOP here and wait for the user's answer.** Do not continue with org/app creation or any other steps until the user responds. Asking a question and continuing to work in parallel is confusing — the user misses the question as output scrolls past.

- **User provides a preset** → store it for Task A scaffold command.
- **User says random / doesn't care / wants to move on** → pick a random preset from `nova`, `vega`, `maia`, `lyra`, `mira`, `luma`.

### Step 2: Create org + app

**First, check existing orgs** with `stream api OrganizationRead`. If there are already 10 orgs, do NOT create a new one - pick an existing `builder-*` org and create a new app inside it.

**App names are globally unique.** Always use `app-<hash>` where hash = `openssl rand -hex 4`.

```bash
# Check existing orgs first:
stream api OrganizationRead

# If under 10 orgs, create new:
HASH=$(openssl rand -hex 4)
stream api OrganizationCreate name=builder-$HASH slug=builder-$HASH

# Create app with Feeds v3 + US East (region_id=1):
stream api AppCreate name=app-$HASH org_id=<org_id> is_development=true region_id=1 feeds_version=v3

# Set defaults:
stream config set org <org_id> && stream config set app <app_id>
```

**Never use the auto-created app** from OrganizationCreate - it uses Feeds v2 and US Ohio.

**Fallback (org limit / 429):** Use `OrganizationRead` to list existing builder orgs, pick one, create a new app in it.

### Step 3: Scaffold + .env + SDKs + Configure - SEQUENTIALLY

#### Scaffold order

Order:

1. **Steps 1–1b:** Auth + theme pick (wait for answer).
2. **Step 2:** Create org/app.
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

**Task A.2: Frontend skills** — third-party skill packs. **You must disclose and ask before installing.** Do NOT construct your own command variant.

Print this disclosure verbatim, then stop and wait for the user's answer:

> I'd like to install three third-party skill packs that improve generic UI quality:
> - `vercel-react-best-practices` — from [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills)
> - `web-design-guidelines` — from [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills)
> - `frontend-design` — from [`anthropics/skills`](https://github.com/anthropics/skills)
>
> These aren't required — Stream reference files cover SDK wiring either way. Install them?

- **User agrees** → run:
  ```bash
  npx skills add https://github.com/vercel-labs/agent-skills --skill vercel-react-best-practices -y && npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines -y && npx skills add https://github.com/anthropics/skills --skill frontend-design -y
  ```
- **User declines** → skip silently and continue to Task B. Do not retry, do not bring it up again this session.
- **Install fails** → continue with Stream reference files only; mention the failure briefly.

Do **not** modify `layout.tsx` or `globals.css` after scaffold - use Shadcn's defaults as-is (RULES.md › Theme).

**Task B: .env** - Run AFTER scaffold so the .env lands inside the project directory.

```bash
stream env
```

That's it. `stream env` writes `STREAM_API_KEY` and `STREAM_API_SECRET` — both server-side. The client never reads env vars directly; it gets `apiKey`, `userId`, and its token from the `/api/token` response and holds them in React state. No `NEXT_PUBLIC_*` duplication, no `.env` gymnastics.

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

If `NO_ICONS`, install `lucide-react`: `npm install lucide-react --legacy-peer-deps`. If an icon package is already present, use that one throughout the app — do not install a second.

**Task D: Configure Stream** - Run the CLI commands from each relevant references's App Integration → Setup section.

### Step 4: Generate code and UI

**Load [`builder-ui.md`](builder-ui.md)** and **only** the relevant `references/<Product>.md` header + `references/<Product>-blueprints.md` for the sections you are implementing - not every references file.

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
Pick a random 5-digit port (10000–65535). Run the server using `run_in_background`:

```bash
PORT=$((RANDOM % 55536 + 10000))
npx next dev -p $PORT
```

**Important:** The dev server is a long-running process. When run in the background it will eventually emit a "completed" notification — this does **not** mean the server stopped. The server is still running and serving requests. **Do not** respond to the background-task completion notification by telling the user the server has stopped. If you receive that notification after Step 7, ignore it silently — do not output anything.

### Step 7: Summary
Show what was created: org, app, resources, files. Include the local URL. Do NOT say "you can now start the dev server" - it's already running.

End with:

> Open `http://localhost:<PORT>`, enter a username, and start testing. Open a second tab with a different username to test multi-user interactions.

---

## Use Case Matching

**Only build with the products the user explicitly mentions.** If unclear, ask.

| User says | Use case | Products |
|---|---|---|
| "Twitch", "YouTube Live", "Kick", "livestream" | Livestreaming | Video + Chat + Feeds |
| "Zoom", "Google Meet", "video call", "meeting" | Video Conferencing | Video [+ Chat] |
| "Slack", "Discord", "team chat", "channels" | Team Messaging | Chat |
| "WhatsApp", "iMessage", "DM", "messaging" | Direct Messaging | Chat [+ Video] |
| "Instagram", "Twitter", "social feed", "Reddit" | Social Feed | Feeds + Chat |

**Moderation** is configured via CLI during setup only. **Never build moderation review UI in the app** (RULES.md › Moderation is Dashboard-only) - review happens in the [Stream Dashboard](https://beta.dashboard.getstream.io).

---

## Page Flow

Every app needs a clear navigation structure. Users should always understand where they are and what they can do. **Never drop a user into a camera/mic prompt, an empty state, or a feature-heavy screen without context.**

### Principle: Hub-first

After login, land on a **hub** - a home screen that shows what's happening and lets the user choose their path. The hub is the anchor; everything else is a destination the user navigates to intentionally.

### Flow by use case

**Livestreaming (Twitch, YouTube Live, Kick):**
```
Login → Feed hub (live streams + posts) → Watch a stream (viewer: video + chat, no camera)
                                        → Go Live (explicit action → then camera/mic setup → streaming)
```
- The feed hub shows live streams (if any) as prominent cards, plus regular posts below
- Clicking a live card opens the **watch** view - video player + chat as a viewer. No camera permissions.
- "Go Live" is a deliberate action (button in header or dedicated screen). Only THEN prompt for camera/mic. The streamer sees a setup/preview before going live.
- Viewers and streamers are the same user type - the difference is the action they take, not the page they land on.

**Video Conferencing (Zoom, Google Meet):**
```
Login → Lobby (list of calls or "start a call") → Join call (camera/mic preview → join)
```
- Land on a lobby or call list - not directly in a call.
- Joining a call shows a **preview screen** (camera/mic toggles) before connecting. The user opts in.

**Team Messaging (Slack, Discord):**
```
Login → Channel list + active channel → Browse/search channels
```
- Land on the channel list with the most recent channel open (or a welcome state if no channels).

**Direct Messaging (WhatsApp, iMessage):**
```
Login → Conversation list → Open a conversation → Start new conversation
```

**Social Feed (Instagram, Twitter):**
```
Login → Feed hub (follow users + composer + tabs: Timeline | My Posts) → Comments → User profiles
```
- The user posts to their own `user:<userId>` feed and reads from `timeline:<userId>` (aggregates followed users' posts)
- **Feed hub tabs:** Use a `Tabs` component with two views:
  - **Timeline** (default) — shows `timeline:<userId>` (posts from followed users)
  - **My Posts** — shows `user:<userId>` (the current user's own posts)
- **Refresh button:** Place a refresh/reload button next to the tabs. On click, re-call `feed.getOrCreate({ watch: true })` on the active feed to re-fetch the latest activities. This gives users an explicit way to refresh after follows or if real-time events are missed.
- A **Follow User** input (username + follow button) must be visible so users can populate their timeline
- Without following, the timeline is permanently empty — this component is not optional
- **Follow wiring:** The Follow component must receive the **timeline feed instance** and call `timelineFeed.follow('user:targetId')` — not `client.follow()`. Using the feed instance keeps `useFeedActivities()` in sync so the timeline updates immediately after following.

### Key rules

- **Camera/mic: opt-in only.** Never request permissions on page load. Only when the user takes an explicit action (Go Live, Join Call).
- **No empty ambiguity.** If there's no content yet, show a clear empty state that tells the user what to do ("No live streams yet - be the first to Go Live").
- **Navigation is visible.** The user should always be able to get back to the hub. Use the App Header or a sidebar for navigation.
- **One primary action per screen.** The hub's primary action is browsing/discovering. The watch screen's primary action is viewing. The Go Live screen's primary action is streaming. Don't mix them.

---

## Cross-Product Integration

When building apps that combine multiple products, read each relevant references's App Integration section. Key patterns:

- **Combined token route:** `/api/token` returns tokens for each product (`{ chatToken, videoToken, feedToken, apiKey }`). Upsert only the requesting user - never seed demo users.
- **Video + Feeds (Livestreaming):** Feed hub separates `type === "live"` activities as prominent live cards. "Go Live" posts a live activity via `/api/feed/live`. "End Stream" removes it.
- **Video + Chat (Livestreaming):** Chat alongside video on the watch screen. Use `livestream` channel type - one channel per stream, keyed by call ID. Create the chat channel in the `/api/token` route.
- **Moderation (all use cases):** Run Moderation CLI setup commands from `references/MODERATION.md` (App Integration → Setup), adjusting channel type name. **Never build moderation review UI** (RULES.md › Moderation is Dashboard-only) - review happens in the [Stream Dashboard](https://beta.dashboard.getstream.io).

---

## Authentication

If not authenticated:
- **Has account** → `stream auth login`
- **No account** → Open `https://getstream.io/try-for-free/`, then `stream auth login` after signup

---

## Reference file paths

Blueprint files live under `agent-skills/skills/stream/references/` inside the Stream skill. Reference them as `agent-skills/skills/stream/references/FEEDS.md` from the **root of this repository**. Do not use machine-specific absolute paths.
