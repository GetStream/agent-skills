# Video - component blueprints (prebuilt-first)

Setup, routes, and gotchas: [VIDEO.md](VIDEO.md). Rules: [`../RULES.md`](../RULES.md) (reference authority, strict mode protection) and the cross-cutting [../../stream/RULES.md](../../stream/RULES.md) (secrets, no auto-seeding).

**Build the common path with `@stream-io/video-react-sdk`'s prebuilt components and customize via `useCallStateHooks()` + `ParticipantView`.** For fully hand-built, bespoke UI on the low-level client, see [`custom-ui.md`](custom-ui.md) - and even then, fetch the matching docs page first ([`docs-map.md`](docs-map.md)).

---

## Prebuilt components (default path)

**CSS (once, in `app/layout.tsx` or the AppShell):**
```ts
import '@stream-io/video-react-sdk/dist/css/styles.css';
```

**Client + call (manual - there is NO `useCreateVideoClient` hook).** Use the **canonical snippet in [VIDEO.md](VIDEO.md) > Client Patterns** (loaded alongside this file in Step 4): strict-mode-safe `useState` + `useEffect` (never `useMemo`), `tokenProvider` defined inside the effect, call joined in its own guarded effect, rendering gated until both client and call exist ([`../RULES.md`](../RULES.md) > Strict mode protection). Keep every hook above any early return.

**Provider hierarchy (the canonical layout):**
```tsx
import { StreamVideo, StreamTheme, StreamCall, SpeakerLayout, CallControls } from '@stream-io/video-react-sdk';

<StreamVideo client={client}>
  <StreamTheme>
    <StreamCall call={call}>
      <SpeakerLayout participantsBarPosition="bottom" />
      <CallControls onLeave={() => {/* navigate away */}} />
    </StreamCall>
  </StreamTheme>
</StreamVideo>
```

| Component | Purpose | Key props |
|---|---|---|
| `StreamVideo` | Root client provider (+ i18n) | `client` (req), `i18nInstance`, `language` |
| `StreamCall` | Call provider around a `Call` object | `call` (req) |
| `SpeakerLayout` | Dominant speaker / screen-share focus + participants bar | `participantsBarPosition` (`top`/`bottom`/`left`/`right`/`null`), `excludeLocalParticipant`, `mirrorLocalParticipantVideo` |
| `PaginatedGridLayout` | Equal participants in a paginated grid | `groupSize`, `excludeLocalParticipant`, `pageArrowsVisible` |
| `LivestreamLayout` | One-to-many broadcast (used by `LivestreamPlayer`) | `muted`, `enableFullScreen`, `showParticipantCount`, `showDuration`, `showLiveBadge` |
| `ParticipantView` | One participant's video/audio (building block) | `participant` (req), `ParticipantViewUI`, `VideoPlaceholder`, `trackType` (`videoTrack`/`screenShareTrack`/`none`) |
| `CallControls` | Permission-aware control bar | `onLeave`. Building-block buttons: `ScreenShareButton`, `RecordCallButton`, `ReactionsButton`, `ToggleAudioPublishingButton`, `ToggleVideoPublishingButton`, ... |
| `CallParticipantsList` | Participant list w/ mute status, search, per-user actions | `onClose`, `activeUsersSearchFn`, `debounceSearchInterval` |
| `DeviceSettings` | Camera/mic/speaker settings panel | `visualType` (`menu`/`portal`, default `menu` - the `MenuVisualType` enum). Companions: `DeviceSelectorVideo`, `DeviceSelectorAudioInput`, `AudioVolumeIndicator` |
| `VideoPreview` | Lobby self-view before joining | `mirror`, `DisabledVideoPreview`, `NoCameraPreview` |
| `LivestreamPlayer` | Watch a WebRTC livestream by id/type (manages the call itself) | `callType` (`"livestream"`), `callId`, `joinBehavior` (`asap`/`live`), `layoutProps` |

**Custom layout (when prebuilt layouts don't fit):** read participants with `useCallStateHooks()` and render each with `ParticipantView` - do NOT reimplement `ParticipantView` (it owns dynascale + track subscription logic):
```tsx
import { useCall, useCallStateHooks, ParticipantView, hasScreenShare } from '@stream-io/video-react-sdk';
const { useParticipants } = useCallStateHooks();
const [spotlight, ...others] = useParticipants();
// spotlight: <ParticipantView participant={spotlight} trackType={hasScreenShare(spotlight) ? 'screenShareTrack' : 'videoTrack'} />
// bar: others.map(p => <ParticipantView key={p.sessionId} participant={p} />)
```

**Customization hooks:** the umbrella is `useCallStateHooks()`, which returns sub-hooks you destructure: `useParticipants`, `useLocalParticipant`, `useRemoteParticipants`, `useCallCallingState`, `useCameraState`, `useMicrophoneState`, `useScreenShareState`, `useDominantSpeaker`, `useParticipantCount`, `useOwnCapabilities`, `useIsCallRecordingInProgress`, ... Plus `useCall()` and `useStreamVideoClient()`. Usage: `const { useCameraState } = useCallStateHooks(); const { camera, isMute } = useCameraState(); camera.toggle();`

**Docs-first:** for any customization (replacing call controls, custom layouts, lobby preview, PiP, network quality, livestream watching, ringing, ...) fetch the matching page from [`docs-map.md`](docs-map.md) first. Component reference pages live at `https://getstream.io/video/docs/react/ui-components/...`.

---

## Fully custom UI (fallback)

For fully hand-built, bespoke UI on the low-level client - when the prebuilt layouts/controls can't be customized into the target - see [`custom-ui.md`](custom-ui.md): the prebuilt-vs-bespoke decision, the headless `useCallStateHooks()` map, and per-region routing to the live docs. Keep `ParticipantView` for track binding even in a bespoke layout; default to the prebuilt path above.
