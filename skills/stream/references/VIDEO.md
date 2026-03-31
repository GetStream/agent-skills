# Video - Setup & Integration

Stream Video provides pre-built UI components via React, React Native, Flutter, Swift, and Kotlin SDKs. This file covers setup, server routes, client patterns, and gotchas. For full component structure and wiring, see [VIDEO-blueprints.md](VIDEO-blueprints.md).

Rules: [../RULES.md](../RULES.md) (secrets, login screen first, strict mode protection).

- **Blueprint** - HTML with BEM classes defining structure and conditional rendering
- **Wiring** - API calls to read/write each element, exact property paths
- **Requirements** - Dashboard settings, API params, and prerequisites

## Quick ref

- **Packages:** `@stream-io/video-react-sdk`; import SDK CSS from package `dist/css/styles.css`.
- **First:** **App Integration** → **Setup** for call types / credentials.
- **Per feature:** Lobby, Call Layout, Controls, … - one section at a time.
- **Below the next rule:** full blueprints - **do not load past it** until you implement that component.

Full component blueprints: [VIDEO-blueprints.md](VIDEO-blueprints.md) - load only the section you are implementing.

---

## App Integration

Everything needed to wire the UI components above into a working Next.js application.

### Setup

**Packages:** `@stream-io/video-react-sdk` (client), `@stream-io/node-sdk` (server)

No CLI commands needed for `default` call type. For `livestream` call type:

```bash
stream api UpdateCallType name=livestream --body '{"settings":{"backstage":{"enabled":false}}}'
stream api UpdateCallType name=livestream --body '{"grants":{"user":["block-user-owner","create-call","create-call-reaction","enable-noise-cancellation-any-team","end-call-owner","join-backstage-owner","join-call","join-ended-call-owner","kick-user-owner","mute-users-owner","pin-call-track-owner","read-call","remove-call-member-owner","screenshare-owner","send-audio","send-event","send-video","start-broadcasting-owner","start-frame-recording","start-recording-owner","stop-broadcasting-owner","stop-frame-recording","stop-recording-owner","update-call-member-owner","update-call-member-role-owner","update-call-owner","update-call-permissions-owner"]}}'
```

### Server Routes

| Route | Method | Params | Action | Response |
|---|---|---|---|---|
| `/api/token` | GET | `?user_id=xxx` | `client.upsertUsers([{ id, name }])`, `client.generateUserToken({ user_id })` | `{ videoToken, apiKey }` |

```ts
import { StreamClient } from '@stream-io/node-sdk';
const client = new StreamClient(process.env.STREAM_API_KEY!, process.env.STREAM_API_SECRET!);
```

### Client Patterns

- **Login Screen first:** See RULES.md › Login Screen first + [builder-ui.md](../builder-ui.md) > Login Screen.
- **App Header:** Show the current username + avatar (initial letter) + "Switch User" in a persistent header above the video layout. See [`builder-ui.md`](../builder-ui.md) → App Header.
- **Instantiate:** `new StreamVideoClient({ apiKey, user: { id, name }, token })`
- **Call:** `client.call('default', callId)` or `client.call('livestream', callId)`
- **Join:** `call.join({ create: true })` - NOT `getOrCreate()` (doesn't connect WebRTC)
- **Strict mode:** See RULES.md › Strict mode protection.
- **Custom controls only** - never use `<CallControls />`, use `useCallStateHooks()` instead
- **Livestream:** Camera/mic off by default - enable only on explicit "Go Live"

### Gotchas

- Backstage mode is on by default for `livestream` call type - disable it via CLI setup
- `livestream` restricts video/audio to owners - grant `send-video` + `send-audio` to user role
- After changing call type settings, existing calls keep old settings - delete stale calls
- No auto-recording unless explicitly asked (paid feature)
- Import `@stream-io/video-react-sdk/dist/css/styles.css` for default styles
- Call vs session: a **call** is the persistent entity; a **session** is one continuous period where participants are connected
- `upsertUsers` takes an **array** of user objects: `client.upsertUsers([{ id, name }])` - NOT an object keyed by ID
- **`ParticipantView` does not fill its container by default** - the SDK applies its own sizing/border-radius. For edge-to-edge video (e.g. livestream player), add CSS overrides: `.str-video__participant-view { width: 100% !important; height: 100% !important; border-radius: 0 !important; }` and `.str-video__participant-view video { width: 100% !important; height: 100% !important; object-fit: cover !important; border-radius: 0 !important; }`
