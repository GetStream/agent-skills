# Builder - scaffold execution (Track A)

Phase table: [`SKILL.md`](SKILL.md) Track A. Rules: [`RULES.md`](RULES.md) (secrets, no auto-seeding, login screen first, phase order, package manager).

---

## A1: CLI probe

Run the probe, then report the result as a **single line** with a checkmark. Do **not** use a heading, section number, or bullet list - just one line:

- **Found → output exactly:** `✓ Stream CLI v0.1.0` (substitute actual version)
- **Not found → output exactly:** `✗ Stream CLI not found - see bootstrap.md to install, or I can continue without it.`

```bash
bash -ce 'command -v stream >/dev/null 2>&1 && stream --version || echo "STREAM_CLI_NOT_FOUND"'
```

If the sandbox blocks the probe, say so and ask the user to confirm `stream` is installed.

## A2: Immediate execution

After the CLI probe, **immediately start executing Steps 0–7**. No prompts, no checklist, no confirmation. Just build it step by step.

Frontend skills (`vercel-react-best-practices` + `web-design-guidelines`) and Shadcn/ui are **always installed** during Step 3 - never ask, never skip. Load them before Step 4 alongside `references/*.md`. **Precedence:** Stream referencess win for SDK wiring; frontend skills guide generic React / UI polish.

---

## Builder Steps (A3 execution)

Execute phases **in order** (later steps depend on earlier ones). Do **not** run independent phases in parallel.

### Sandboxed agents / fewer "Run" prompts

**Rule - one invocation per phase:** Wrap everything in `bash -ce 'set -euo pipefail; …'` (or `&&` on one line).

**When you need two calls:** If you must Read JSON (e.g. `OrganizationRead`) and then choose IDs, use one call for the read, one batched call for all creates + `stream config set`.

**Exception - browser auth:** `stream auth login` stays its own invocation so the browser can open.

### Step 0: Package manager
Always use `npm`. Never use bun.

### Step 1: Auth
If the user is not logged in, run `stream auth login` in a **normal terminal** so the browser opens (PKCE).

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

`npx shadcn@latest init -t next` requires the target directory to not yet exist - it creates the project directory. Order:

1. **Steps 1–2:** Auth + org/app.
2. **Task A:** Scaffold with Shadcn + Next.js in one command.
3. **Task A.1:** Add base Shadcn components.
4. **Task A.2:** Install frontend skills.
5. Continue with Task B (.env), Task C (SDKs), Task D (CLI config).

**Task A: Scaffold** - creates the project directory with Next.js + Tailwind + Shadcn/ui (Base UI) in one step. Pick the preset based on use case (see **Preset Matching** below) - never use `mira` (no border radius):

```bash
npx shadcn@latest init -t next -b base -n <project-name> --no-monorepo -p <preset>
```

**Task A.1: Add base Shadcn components:**

```bash
npx shadcn@latest add button input textarea card avatar badge separator
```

Add more components as the use case requires (e.g. `dialog`, `dropdown-menu`, `tabs`, `popover`).

**Task A.2: Frontend skills** - always install after scaffold (do NOT construct your own command variant):

```bash
npx skills add https://github.com/vercel-labs/agent-skills --skill vercel-react-best-practices -y && npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines -y && npx skills add https://github.com/anthropics/skills --skill frontend-design -y
```

If install fails, continue with Stream referencess only - mention the failure briefly.

Do **not** modify `layout.tsx` or `globals.css` after scaffold - use Shadcn's defaults as-is (RULES.md › Theme).

**Task B: .env** - Run AFTER scaffold so the .env lands inside the project directory.

```bash
stream env 2>/dev/null
ENV_EXIT=$?
if [ $ENV_EXIT -eq 2 ]; then
  stream auth login && stream env 2>/dev/null
elif [ $ENV_EXIT -ne 0 ]; then
  echo "stream env failed (exit $ENV_EXIT)" >&2; exit 1
fi
API_KEY=$(grep STREAM_API_KEY .env | head -1 | cut -d= -f2)
echo "STREAM_APP_ID=<app_id>" >> .env
echo "NEXT_PUBLIC_STREAM_API_KEY=$API_KEY" >> .env
echo "NEXT_PUBLIC_STREAM_APP_ID=<app_id>" >> .env
```

**Task C: Install Stream SDKs** - Only what the use case needs:

```bash
# Chat:     stream-chat stream-chat-react
# Video:    @stream-io/video-react-sdk
# Server:   @stream-io/node-sdk
npm install <packages> --legacy-peer-deps
```

**Task D: Configure Stream** - Run the CLI commands from each relevant references's App Integration → Setup section.

### Step 4: Generate code and UI

**Load [`builder-ui.md`](builder-ui.md)** and **only** the relevant `references/<Product>.md` header + `references/<Product>-blueprints.md` for the sections you are implementing - not every references file.

### Step 5: Verify
`npx next build`. Fix any errors.

### Step 6: Start dev server
Pick a random 5-digit port (10000–65535):

```bash
PORT=$((RANDOM % 55536 + 10000))
npx next dev -p $PORT &
```

### Step 7: Summary
Show what was created: org, app, resources, files. Include the local URL. Do NOT say "you can now start the dev server" - it's already running.

End with:

> Open `http://localhost:<PORT>`, enter a username, and start testing. Open a second tab with a different username to test multi-user interactions.

---

## Preset Matching

Presets control font, icon library, and component shape - **not** colors (all presets use neutral). Pick based on the use case vibe:

| Preset | Font | Icons | Style | Best for |
|---|---|---|---|---|
| **nova** | Geist | lucide-react | Rounded-lg, compact | Productivity, messaging |
| **vega** | Inter | lucide-react | Rounded-md, shadows | Professional, business |
| **maia** | Figtree | hugeicons | Rounded-4xl, spacious | Consumer, social, entertainment |
| **lyra** | Geist + JetBrains Mono | phosphor | Rounded-none, sharp | Technical, developer tools |

If the use case doesn't match any row below, pick a **random** preset from nova, vega, maia, lyra. **Never use mira** (no border radius).

---

## Use Case Matching

**Only build with the products the user explicitly mentions.** If unclear, ask.

| User says | Use case | Products | Preset |
|---|---|---|---|
| "Twitch", "YouTube Live", "Kick", "livestream" | Livestreaming | Video + Chat + Feeds | **maia** (soft, playful - consumer/entertainment) |
| "Zoom", "Google Meet", "video call", "meeting" | Video Conferencing | Video [+ Chat] | **vega** (professional, structured - business tool) |
| "Slack", "Discord", "team chat", "channels" | Team Messaging | Chat | **nova** (clean, modern - productivity) |
| "WhatsApp", "iMessage", "DM", "messaging" | Direct Messaging | Chat [+ Video] | **nova** (minimal, fast - messaging focus) |
| "Instagram", "Twitter", "social feed", "Reddit" | Social Feed | Feeds + Chat | **maia** (friendly, rounded - social feel) |

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
Login → Feed (posts + composer) → Comments → User profiles
```

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
