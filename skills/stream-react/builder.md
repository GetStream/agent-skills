# Provisioning, Use Case Matching, and Page Flow

The pieces the React builder relies on that are not React-specific: **provisioning** (onboarding via `getstream init`, Step 1 of [`SKILL.md`](SKILL.md)), **use-case matching** (which products a request needs), and **page flow** (hub-first navigation every app follows).

> **CLI execution:** CLI usage and posture live in the root `stream` skill - its [`SKILL.md`](../stream/SKILL.md) (Stream CLI section) and [`../stream/RULES.md`](../stream/RULES.md) (CLI safety: no guessing endpoints, read the CLI's output).
> **Shell discipline:** one `bash -c` per phase, no `bash -ce`/`set -e` in probes, and browser sign-in (`getstream init` / `getstream login`) always as its own unwrapped invocation ([`../stream/RULES.md`](../stream/RULES.md) > Shell discipline).

---

## Provisioning

Run `getstream init`. It authenticates (opening a browser as its own invocation), then lets you select or create the org and app and writes the project credentials - follow its prompts and output. If the use case includes **Feeds**, choose a **Feeds v3** region when `getstream init` offers the region list (other regions default to legacy v2, where v3 feed groups are unavailable). If `getstream` isn't installed, ask the user to install it from https://getstream.io and wait - never fetch or run an install script.

`getstream init` is the single onboarding step - it replaces any manual auth / org-create / app-create / config-set sequence. Don't provision orgs or apps with raw `getstream api` calls; let `init` drive the selection (interactively, or via its command file in non-interactive runs).

**Command-file flow (what actually happens in an agent / non-interactive run).** When there's no TTY, `getstream init` does **not** prompt - it writes a template to `.stream/init-*.yaml` listing every org/app (commented out) and prints `Uncomment one option, then run: getstream init --command .stream/init-<id>.yaml`. So the real sequence is: run `getstream init` (once, to generate the template) -> `Read` the YAML -> pick the app with the user (an existing `app_id`, `new_app` in an existing org, or `new_org` + `new_app`) -> uncomment exactly that block with `Edit` -> run `getstream init --command .stream/init-<id>.yaml`. It writes credentials to `.stream/creds.yaml` (add `/.stream/` to `.gitignore` - it holds secrets). Then `getstream env` writes `.env.local`. The bundled skill assumes the interactive prompt; in headless runs, drive the command file instead.

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

**Video apps - decide the `video_primary_use_case` here.** When this table selects Video, also decide the `video_primary_use_case` value using the table + precedence in [`references/VIDEO.md`](references/VIDEO.md) > Primary use case. Do not confuse it with call types - e.g. a Whatnot-style live-shopping app uses the `livestream` call type but sets `video_primary_use_case: live-shopping`, not `livestreaming`. This is pure metadata and does not change which products you build or which blueprints you load.

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
