# Provisioning, Use Case Matching, and Page Flow

The pieces the React builder relies on that are not React-specific: **provisioning** (auth + org/app selection or creation, Steps 1-2 of [`SKILL.md`](SKILL.md)), **use-case matching** (which products a request needs), and **page flow** (hub-first navigation every app follows).

> **CLI execution:** every `stream ...` command here is run through the `stream-cli` peer - complete its [`preflight.md`](../stream-cli/preflight.md) first. No guessing endpoint names ([`../stream/RULES.md`](../stream/RULES.md) > CLI safety).
> **Shell discipline:** one `bash -c` per phase, no `bash -ce`/`set -e` in probes, and `stream auth login` always as its own unwrapped invocation ([`../stream/RULES.md`](../stream/RULES.md) > Shell discipline).

---

## Provisioning

### Step 1: Auth

**Test auth first, then act - don't skip this and don't wait until Step 2 surfaces an error.** Run `stream api OrganizationRead` as a probe:

- **Exit 0** -> already authenticated. **Keep the `OrganizationRead` output in context** - Step 1b presents the org list from it. Continue to Step 1b (theme + app pick) in [`SKILL.md`](SKILL.md).
- **Exit 2 / "not authenticated"** -> **immediately** run `stream auth login` as its **own** Bash invocation. This is a hard constraint:
  - Browser PKCE requires an unwrapped `stream auth login` call - **never** chain with `&&`, embed in a heredoc, or bundle with other commands.
  - Do not ask the user first; just run it. Give it up to ~3 minutes for the browser flow.
- **Login hangs past ~60s, or the user reports the browser is stuck** -> run `stream auth logout` to clear any stale session state, then retry `stream auth login` **once**. If the second attempt also hangs, stop and ask the user to run `! stream auth login` themselves (the `!` prefix runs it in-session so you see the result).

**No account?** Open `https://getstream.io/try-for-free/`, then `stream auth login` after signup.

### Step 2: Pick org + app

**Never create an org or app unprompted.** The user chooses in the combined Step 1b prompt ([`SKILL.md`](SKILL.md)); this step only executes that choice, with no further prompting. The inputs are already in hand: preflight's `stream config list` (currently configured org/app) and Step 1's `OrganizationRead` output (org list).

- **Use the configured app** - the default whenever one is configured and the user didn't pick otherwise. Nothing to set; echo it once before continuing: `Using Stream app "<name>" (org <org>)`.
- **Pick another existing app:** enumerate the chosen org's apps first - discover the app-list endpoint via the `stream-cli` cache (`~/.stream/cache/API.md`, [`../stream/RULES.md`](../stream/RULES.md) > CLI safety - never guess) - then set defaults:
  ```bash
  stream config set org <org_id> && stream config set app <app_id>
  ```
- **Feeds caveat for any existing app:** if the use case includes Feeds, confirm the selected app is **Feeds v3** (`stream --safe api GetApp`). If it is not, tell the user and recommend creating a new app - v3 feed groups are not available on v2 apps.
- **Create new** - only when the user chose it, or when the account has no orgs at all (announce that case). **App names are globally unique** - always `app-<hash>` where hash = `openssl rand -hex 4`. If there are already 10 orgs, do NOT create a new org - pick an existing `builder-*` org and create the app inside it.

  ```bash
  HASH=$(openssl rand -hex 4)
  stream api OrganizationCreate name=builder-$HASH slug=builder-$HASH

  # Create app with Feeds v3 + US East (region_id=1):
  stream api AppCreate name=app-$HASH org_id=<org_id> is_development=true region_id=1 feeds_version=v3

  # Set defaults:
  stream config set org <org_id> && stream config set app <app_id>
  ```

  **Never use the auto-created app** from OrganizationCreate - it uses Feeds v2 and US Ohio.
  **Fallback (org limit / 429):** pick an existing `builder-*` org from the `OrganizationRead` output, create the new app in it.

**Two-call exception:** if you must Read JSON (e.g. `OrganizationRead`) and then choose IDs, use one call for the read, one batched call for all creates + `stream config set`.

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

**Moderation** is configured via CLI during setup only. **Never build moderation review UI in the app** ([`RULES.md`](RULES.md) > Moderation is Dashboard-only) - review happens in the [Stream Dashboard](https://beta.dashboard.getstream.io).

---

## Page Flow

Every app needs a clear navigation structure. Users should always understand where they are and what they can do. **Never drop a user into a camera/mic prompt, an empty state, or a feature-heavy screen without context.**

### Principle: Hub-first

After login, land on a **hub** - a home screen that shows what's happening and lets the user choose their path. The hub is the anchor; everything else is a destination the user navigates to intentionally.

### Flow by use case

**Livestreaming (Twitch, YouTube Live, Kick):**
```
Login -> Feed hub (live streams + posts) -> Watch a stream (viewer: video + chat, no camera)
                                        -> Go Live (explicit action -> then camera/mic setup -> streaming)
```
- The feed hub shows live streams (if any) as prominent cards, plus regular posts below.
- Clicking a live card opens the **watch** view - video player + chat as a viewer. No camera permissions.
- "Go Live" is a deliberate action (button in header or dedicated screen). Only THEN prompt for camera/mic. The streamer sees a setup/preview before going live.
- Viewers and streamers are the same user type - the difference is the action they take, not the page they land on.

**Video Conferencing (Zoom, Google Meet):**
```
Login -> Lobby (list of calls or "start a call") -> Join call (camera/mic preview -> join)
```
- Land on a lobby or call list - not directly in a call.
- Joining a call shows a **preview screen** (camera/mic toggles) before connecting. The user opts in.

**Team Messaging (Slack, Discord):**
```
Login -> Channel list + active channel -> Browse/search channels
```
- Land on the channel list with the most recent channel open (or a welcome state if no channels).

**Direct Messaging (WhatsApp, iMessage):**
```
Login -> Conversation list -> Open a conversation -> Start new conversation
```

**Social Feed (Instagram, Twitter):**
```
Login -> Feed hub (follow users + composer + tabs: Timeline | My Posts) -> Comments -> User profiles
```
- The user posts to their own `user:<userId>` feed and reads from `timeline:<userId>` (aggregates followed users' posts).
- **Feed hub tabs:** Use a `Tabs` component with two views:
  - **Timeline** (default) - shows `timeline:<userId>` (posts from followed users)
  - **My Posts** - shows `user:<userId>` (the current user's own posts)
- **Refresh button:** Place a refresh/reload button next to the tabs. On click, re-call `feed.getOrCreate({ watch: true })` on the active feed to re-fetch the latest activities. This gives users an explicit way to refresh after follows or if real-time events are missed.
- A **Follow User** input (username + follow button) must be visible so users can populate their timeline.
- Without following, the timeline is permanently empty - this component is not optional.
- **Follow wiring:** The Follow component must receive the **timeline feed instance** and call `timelineFeed.follow('user:targetId')` - not `client.follow()`. Using the feed instance keeps `useFeedActivities()` in sync so the timeline updates immediately after following.

### Key rules

- **Camera/mic: opt-in only.** Never request permissions on page load. Only when the user takes an explicit action (Go Live, Join Call).
- **No empty ambiguity.** If there's no content yet, show a clear empty state that tells the user what to do ("No live streams yet - be the first to Go Live").
- **Navigation is visible.** The user should always be able to get back to the hub. Use the App Header or a sidebar for navigation.
- **One primary action per screen.** The hub's primary action is browsing/discovering. The watch screen's primary action is viewing. The Go Live screen's primary action is streaming. Don't mix them.
