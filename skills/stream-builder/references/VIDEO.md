# Video - Setup & Integration

Stream Video provides pre-built UI components via React, React Native, Flutter, Swift, and Kotlin SDKs. This file covers setup, server routes, client patterns, and gotchas. For full component structure and wiring, see [VIDEO-blueprints.md](VIDEO-blueprints.md).

Rules: [../../stream/RULES.md](../../stream/RULES.md) (secrets, login screen first, strict mode protection).

- **Blueprint** - HTML with BEM classes defining structure and conditional rendering
- **Wiring** - API calls to read/write each element, exact property paths
- **Requirements** - Dashboard settings, API params, and prerequisites

## Quick ref

- **Packages:** `@stream-io/video-react-sdk`; import SDK CSS from package `dist/css/styles.css`.
- **First:** **App Integration** -> **Setup** for call types / credentials.
- **Per feature:** Lobby, Call Layout, Controls, ... - one section at a time.
- **Below the next rule:** full blueprints - **do not load past it** until you implement that component.

Full component blueprints: [VIDEO-blueprints.md](VIDEO-blueprints.md) - load only the section you are implementing.

---

## App Integration

Everything needed to wire the UI components above into a working Next.js application.

### Setup

**Packages:** `@stream-io/video-react-sdk` (client), `@stream-io/node-sdk` (server)

**Step 1 - set the app's primary use case.** Before touching call types, run the one-time `UpdateApp` write described in the Primary use case subsection below, choosing the value with that subsection's table and precedence rule. Do not confuse call types with `video_primary_use_case`: a shopping app (e.g. Whatnot) uses the `livestream` call type,m but the `video_primary_use_case` is `live-shopping`.

**Step 2 - call types & permissions.** No CLI commands needed for `default` call type. For `livestream` call type, you must update **all three** publishing roles - `user`, `call_member`, and `host`. Stream evaluates capabilities against the role applied at join-time (`call_member` / `host`), not the user-level role, and the `host` defaults restrict `send-video` to call owners only:

```bash
# 1. Disable backstage so users can join without goLive()
getstream api UpdateCallType --name livestream --request '{"settings":{"backstage":{"enabled":false}}}'

# 2. Grant unrestricted send-video / send-audio to user role
getstream api UpdateCallType --name livestream --request '{"grants":{"user":["block-user-owner","create-call","create-call-reaction","enable-noise-cancellation-any-team","end-call-owner","join-backstage-owner","join-call","join-ended-call-owner","kick-user-owner","mute-users-owner","pin-call-track-owner","read-call","remove-call-member-owner","screenshare-owner","send-audio","send-event","send-video","start-broadcasting-owner","start-frame-recording","start-recording-owner","stop-broadcasting-owner","stop-frame-recording","stop-recording-owner","update-call-member-owner","update-call-member-role-owner","update-call-owner","update-call-permissions-owner"]}}'

# 3. Grant unrestricted send-video / send-audio to call_member role (REQUIRED - without this, even owners get "No permission to publish VIDEO")
getstream api UpdateCallType --name livestream --request '{"grants":{"call_member":["block-user-owner","create-call","create-call-reaction","enable-noise-cancellation-any-team","end-call-owner","join-backstage-owner","join-call","join-call-any-team","join-ended-call-owner","kick-user-owner","mute-users-owner","pin-call-track-owner","read-call","remove-call-member-owner","screenshare-owner","send-audio","send-event","send-video","start-broadcasting-owner","start-frame-recording","start-recording-owner","stop-broadcasting-owner","stop-frame-recording","stop-recording-owner","update-call-member-owner","update-call-member-role-owner","update-call-owner","update-call-permissions-owner"]}}'

# 4. Grant unrestricted send-video / send-audio to host role
getstream api UpdateCallType --name livestream --request '{"grants":{"host":["block-user","create-call","create-call-reaction","enable-noise-cancellation-any-team","end-call","join-backstage-owner","join-call","join-ended-call-owner","kick-user-owner","mute-users","pin-call-track","read-call","read-call-stats-owner","remove-call-member-owner","screenshare","send-audio","send-event","send-video","start-broadcasting","start-frame-recording","start-recording","stop-broadcasting","stop-frame-recording","stop-recording","update-call-member-owner","update-call-member-role-owner","update-call-owner","update-call-permissions-owner"]}}'
```

### Primary use case (app-level onboarding hint)

`video_primary_use_case` is an optional, app-level setting on the Stream app (one per app, nullable). It is a soft hint what the app is for. It is pure metadata, and does not affect configuration on runtime behavior.

**This is not product selection.** The [Use Case Matching](../builder.md) table decides what to build. This setting only labels the app you already decided to build.

**Allowed values** - hard-code these, do not try to discover it with `--help` or `--schema`:

| Value | Signals in the request | Maps to Use Case Matching |
|---|---|---|
| `video-calling` | "Zoom", "Google Meet", "video call", "video conferencing", "meeting", 1:1 / group video | Video Conferencing |
| `voice-calling` | "voice call", "audio call", phone-style / Discord-style voice (no video) | - |
| `livestreaming` | "Twitch", "YouTube Live", "Kick", "livestream", "go live", "broadcast to viewers" | Livestreaming |
| `audio-rooms` | "Clubhouse", "Twitter/X Spaces", "audio room", "drop-in audio", "stage with speakers/listeners" | - |
| `ai-agents` | "AI agent", "voice agent", "vision agent", an AI avatar that joins the call | - |
| `live-shopping` | "Whatnot", "QVC", "TikTok Shop", "live shopping", "live commerce", "shoppable livestream", "sell products during a stream", "auction" | Livestreaming variant |
| `other` | Video is in scope but none of the above fit | - |

**`live-shopping` vs `livestreaming` - check shopping first.** Live shopping is a livestreaming variant, so their signals overlap. If the request mentions shopping, commerce, selling, products, a marketplace, or auctions (e.g. Whatnot, QVC, TikTok Shop) - pick `live-shopping`. Only fall back to `livestreaming` when there is no commerce signal at all.

If signals are ambiguous, fold the choice into the same product question you already ask to decide the build. Do not add a separate prompt just for this hint. When still unsure, set `other` (or leave it unset) rather than guessing; the value is changeable later.

**Set it once during Setup (Task D), after `getstream init`:**

```bash
getstream api UpdateApp --request '{"video_primary_use_case":"livestreaming"}'
```

- `--app-id` is optional inside an initialized project; both read and write require a current login (`getstream login`).
- Constrain input to the allowed set **yourself** before writing - server-side enum rejection of unknown values is not relied upon.
- Setting is non-destructive and changeable, and never touches call types. Only ever set it to an allowed value; clearing it back to `null` via the API is not supported in this flow.

**Read it** (e.g. to confirm what an existing app is configured for):

```bash
getstream api GetApp --jq '.app.video_primary_use_case'   # -> "livestreaming", or null if never set
```

**By track:**
- **Scaffold (Track A):** set the hint during Task D, mapped from the detected use case, when Video is part of the build.
- **Enhance (Track E):** when you add Video to an existing app, set it the same way during Video setup if it is unset.
- **Audit (Track F):** the audit is code-only and **does not run the CLI**. Do not read or write this value yourself. But if the user tells you the app's `video_primary_use_case` (or has already read it), use it to scope which use-case-specific checklist rows apply (e.g. livestream-only rows).

### Server Routes

| Route | Method | Params | Action | Response |
|---|---|---|---|---|
| `/api/token` | GET | `?user_id=xxx` | `client.upsertUsers([{ id, name }])`, `client.generateUserToken({ user_id })` | `{ videoToken, apiKey }` |

```ts
import { StreamClient } from '@stream-io/node-sdk';
const client = new StreamClient(process.env.STREAM_API_KEY!, process.env.STREAM_API_SECRET!);
```

### Client Patterns

- **Login Screen first:** See RULES.md > Login Screen first + [builder-ui.md](../builder-ui.md) > Login Screen.
- **App Header:** Show the current username + avatar (initial letter) + "Switch User" in a persistent header above the video layout. See [`builder-ui.md`](../builder-ui.md) -> App Header.
- **Instantiate at AppShell root** using the canonical docs pattern (do NOT `useMemo`):
  ```ts
  const [videoClient, setVideoClient] = useState<StreamVideoClient>();
  useEffect(() => {
    const c = new StreamVideoClient({ apiKey, user: { id, name }, token });
    setVideoClient(c);
    return () => {
      c.disconnectUser().catch(console.error);
      setVideoClient(undefined);
    };
  }, [apiKey, userId, token]);
  ```
  `useMemo` + a separate cleanup-effect disconnects the client during strict-mode unmount, leaving a dead instance for the second mount and producing *"User token is not set. Either client.connectUser wasn't called or client.disconnect was called"*.
- **One client per session, not per screen.** Hoist `<StreamVideo client={videoClient}>` to AppShell. See [`CROSS-PRODUCT.md`](CROSS-PRODUCT.md) for the multi-product skeleton.
- **Call:** `client.call('default', callId)` or `client.call('livestream', callId)`
- **Join:** `call.join({ create: true })` - NOT `getOrCreate()` (doesn't connect WebRTC)
- **Strict mode:** See RULES.md > Strict mode protection. Do NOT use `useRef` locks like `initRan.current = true` - they short-circuit the second strict-mode mount and strand the UI on a "Setting up your camera..." loading state. Use a `mounted` flag in cleanup instead.
- **Custom controls only** - never use `<CallControls />`, use `useCallStateHooks()` instead
- **Livestream:** Camera/mic off by default - enable only on explicit "Go Live"

### Streamer (Go Live)

When the streamer joins their own livestream call, pass themselves as a `host` member explicitly. Call ownership alone isn't enough - Stream evaluates the call-member role at publish time:

```ts
await call.join({
  create: true,
  data: { members: [{ user_id: streamerUserId, role: "host" }] },
});
```

Otherwise `call.camera.enable()` / `call.microphone.enable()` will throw `No permission to publish VIDEO` / `No permission to publish AUDIO`.

After `join()` succeeds, `setCall(c)` immediately and **then** enable camera/mic in independent try/catch blocks. A permission failure on `enable()` should not strand the UI - render the call surface and surface the error in a banner; the user can retry via the on-screen toggles.

### Watcher (viewer)

Use the SDK's official `<LivestreamPlayer>` component for the viewer experience - it handles join, host detection, viewer count, live badge, fullscreen, and CSS sizing:

```tsx
import { LivestreamPlayer } from "@stream-io/video-react-sdk";
<LivestreamPlayer callType="livestream" callId={id} joinBehavior="asap" />
```

Do NOT roll your own host detection via `participants.find(p => p.roles.includes("host"))` - the streamer's video-level role may be `user`/`call_member`, not `host`. `LivestreamPlayer` and `LivestreamLayout` resolve this correctly.

### Gotchas

- Backstage mode is on by default for `livestream` call type - disable it via CLI setup
- `livestream` restricts video/audio publishing - grant `send-video` + `send-audio` to **all three** roles (`user`, `call_member`, `host`). Granting only `user` is **not enough** because the SDK evaluates against `call_member`/`host` at publish time. Symptom of a missed grant: `No permission to publish VIDEO`.
- **Streamers must join with `data: { members: [{ user_id, role: "host" }] }`** - call ownership alone doesn't grant publish rights for `livestream`.
- After changing call type settings, existing calls keep old settings - delete stale calls or mint a fresh `callId` to test
- **No `useMemo` for `StreamVideoClient`.** Strict-mode cleanup will disconnect the same instance reused on remount -> "User token is not set / disconnect was called". Use the `useState` + `useEffect` pattern shown above.
- **No `useRef` locks in setup effects** (e.g. `initRan.current = true`). They short-circuit the second strict-mode mount and the call never gets set, stranding the UI on "Setting up your camera...". Use a `mounted` flag in cleanup instead.
- **Camera/mic enable is independent of join().** Wrap each in its own try/catch and still `setCall(c)` after `join()` succeeds - otherwise a permission failure strands the UI on the loading state.
- No auto-recording unless explicitly asked (paid feature)
- Import `@stream-io/video-react-sdk/dist/css/styles.css` for default styles
- Call vs session: a **call** is the persistent entity; a **session** is one continuous period where participants are connected
- `upsertUsers` takes an **array** of user objects: `client.upsertUsers([{ id, name }])` - NOT an object keyed by ID
- **`ParticipantView` does not fill its container by default** - the SDK applies its own sizing/border-radius. For edge-to-edge video (e.g. livestream player), add CSS overrides: `.str-video__participant-view { width: 100% !important; height: 100% !important; border-radius: 0 !important; }` and `.str-video__participant-view video { width: 100% !important; height: 100% !important; object-fit: cover !important; border-radius: 0 !important; }`. Or use `<LivestreamPlayer>` for viewers - it handles sizing automatically.

---

## Integration best-practices audit (existing apps)

Use this when the user wants to **review, audit, or check** an existing React (web) Stream Video integration against Stream's best practices - e.g. *"is my video integration production-ready?"*, *"check my app against Stream's best practices"*, *"what am I missing before launch?"*. This is a **read-only review**: produce findings first; only edit code if the user then asks you to fix them. (For *adding* Video to an existing app, use [`../enhance.md`](../enhance.md) instead.)

Source of truth: [`/video/docs/react/advanced/integration-best-practices.md`](https://getstream.io/video/docs/react/advanced/integration-best-practices.md). The checklist below folds that page together with the strict-mode rules in [`../../stream/RULES.md`](../../stream/RULES.md).

### How to run it

1. **Locate the integration surface.** Grep the app source (`app/`, `src/`, `components/`, the AppShell / call screens, and any `/api/token` route) for the anchor symbols in the checklist. Confirm `@stream-io/video-react-sdk` is installed before auditing.
2. **Walk every row.** Most checks are **absence checks** - the failure is a *missing* hook, prop, or cleanup, not visibly wrong code. If the anchor symbol is not found, the row is **FAIL** (or **NEEDS-REVIEW** if it could live in a file you cannot see, e.g. a backend token route or dashboard config).
3. **Mark `N/A` only when the feature genuinely does not apply** (e.g. livestream-only or filter-only rows) - and say *why*.
4. **Report with the output contract below. Never silently skip a row.**

### Output contract

One line per check: **Verdict** (PASS / FAIL / N/A / NEEDS-REVIEW) | **Severity** (Blocker / High / Medium / Low) | **Evidence** (`file:line`, or "not found") | **Fix** (one line). Close with a prioritized remediation list, Blockers first.

Severity guide: **Blocker** = call won't reliably connect, leaks/keeps publishing media, or breaks security; **High** = real production stability or UX gap; **Medium/Low** = polish and hardening.

### Carve-out (do not raise as a finding)

- **`<CallControls />` is not a best-practices violation.** "Custom controls only" is a *builder scaffold convention* for apps this skill generates, not an integration best practice. Stream officially ships `<CallControls />`; do not FAIL an existing app for using it. (You may note it as a Low builder-style preference only if the user asked for builder-convention conformance.)

### Checklist

**Client & call lifecycle**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| Single client, created in `useEffect`/`useState`, disposed on cleanup | `new StreamVideoClient(`/`getOrCreateInstance(`, `disconnectUser(`, `useMemo` | One client; `disconnectUser()` runs in cleanup; **not** built with `useMemo` | Blocker |
| Strict-mode safe setup | `useMemo` for the client, `useRef` locks (`initRan`), a `mounted` flag in cleanup | No `useMemo` client, no `useRef` setup locks; uses a `mounted` flag | High |
| `tokenProvider` with ~4h tokens; token from a backend route, not committed | `tokenProvider`, `/api/token`, literal `token:` | Short-lived token fetched from `/api/token`; no static prod token in client code | Blocker |
| One `<StreamVideo>` per session, hoisted to AppShell (not per screen) | `<StreamVideo`, its placement | Single provider at the app root | High |
| Join with `call.join({ create: true })`, not `getOrCreate()` | `call.join(`, `getOrCreate(` | `join()` is what connects WebRTC; `getOrCreate()` alone never connects media | Blocker |
| `call.leave()` when the call is no longer needed | `.leave(` | Call disposed on unmount/leave; not left dangling and publishing | High |
| All calling states handled in UI | `useCallCallingState` | UI reacts to joining/reconnecting/offline/left states | High |

**Device management & UX**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| Browser permission state surfaced (one-shot prompt) | `hasBrowserPermission`, `isPromptingPermission` | UI explains denied/pending permissions (the user gets only one prompt) | High |
| Device switcher (camera / mic / speaker) | device-settings components, `useCameraState`/`useMicrophoneState` device lists | Users can pick a non-default device | Medium |
| Device verification before joining | `AudioVolumeIndicator`, `SpeakerTest`, `MicCaptureErrorNotification` | Devices are *verified working*, not just selected | Medium |
| Persist device selection | `usePersistedDevicePreferences` | Selection persists across sessions | Low |
| Lobby / preview before joining | a lobby screen | Users check devices/frame before connecting | Medium |
| Audio connecting indicator | audio-connecting UI | Distinguishes "connecting" from "muted"/"broken" | Low |
| Speaking-while-muted handled or disabled | `useMicrophoneState().isSpeakingWhileMuted`, `disableSpeakingWhileMutedNotification` | Surfaced to the user or explicitly disabled | Medium |
| Autoplay-blocked audio handled | `useIsAutoplayBlocked`, `call.resumeAudio(` | A user-gesture element calls `resumeAudio()` when audio is blocked | High |
| Filters expose a manual toggle on low-end devices | noise-cancellation / background-blur usage | If filters are used, a user toggle exists (blur isn't auto-disabled) | Medium (N/A if no filters) |

**Error handling & network**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| `call.join()` in try/catch | `call.join(` | Awaited and wrapped; errors surfaced | Blocker |
| `camera.enable()`/`microphone.enable()` in try/catch (or `onError` on control components) | `.enable(`, `onError` | Device failures caught; UI not stranded | High |
| `connectUser` errors handled | `connectUser` | Rejections caught and surfaced | High |
| Reconnection handled via state, not by ending the call; `setDisconnectionTimeout` tuned | `setDisconnectionTimeout`, calling-state usage | Waits ~60s for SDK reconnect on transient drops; doesn't end the call immediately | Medium |
| Low-bandwidth indicator on custom layouts | custom layout + low-bandwidth UI | Built-in layouts pass automatically; custom layouts notify the user | Medium |
| Firewall/proxy guidance for restrictive networks | n/a | Networking settings applied, or users advised to switch networks | Low |

**Security & ops**

| Check | Detect (anchor) | Pass condition | Severity |
|---|---|---|---|
| Role permissions enforced in the dashboard, not just hidden in the UI | n/a (server-side) | Confirm with the user that dashboard roles are configured (hiding UI is bypassable via the API) | High (NEEDS-REVIEW) |
| SDK CSS imported | `@stream-io/video-react-sdk/dist/css/styles.css` | Default styles imported once | Low |
| User feedback / rating collected | rating/feedback UI | Some quality-feedback path exists | Low |
| Supported-browser detection/advice | supported-platforms utility | Users on unsupported browsers are advised | Low |
| SDK dependencies reasonably current | `package.json` versions vs `npm view` dist-tags | Not far behind latest; review [GitHub Releases](https://github.com/GetStream/stream-video-js/releases) | Low |
