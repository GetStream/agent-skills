# Video — region checklist + routing

Call screen, participant tiles, controls, livestream surfaces.

Tier 2 of the design-match decomposition. The method that drives it — the three axes, how to
measure sizes, how to sample colours, and the Step 3 verify loop — lives in
[`design-matching.md`](design-matching.md); read that first, then walk **every row** below.

The **Route to** column names the *mechanism*. Confirm the exact theme key / slot / prop name in
the manifest-selected docs and the installed package, never from memory.

---

Video ships a **prebuilt component UI** (unlike Feeds) driven by a **global theme** +
**component-injection slots** (unlike Chat's per-`Channel` theme + `WithComponents`). Route each
difference to the cheapest mechanism, preference order **Theming → Layout → Component slot →
Functional**:

- **Theming** — a `DeepPartial<Theme>` passed to `<StreamVideo style={…}>` (global; there is no
  per-`CallContent` theme prop and no `OverlayProvider`/`Channel` split). Deep-merged over
  `defaultTheme`; carries `colors`, `typefaces`, `variants` (size scales), and one style slot per
  component (`callControls`, `participantView`, `participantLabel`, `liveIndicator`, …). Colors,
  fonts, and spacing live here.
- **Layout** — `CallContent`'s `layout` prop (`'grid' | 'spotlight'`) + `landscape`, and
  `CallParticipantsList` `numberOfColumns` / `horizontal`.
- **Component slot** — pass a custom `React.ComponentType` (or `null` to hide) to a slot prop on
  `CallContent` / `ParticipantView` / `HostLivestream` / `ViewerLivestream`. This is Video's
  structural axis — Chat's component override, but as direct props, not a `WithComponents` wrapper.
- **Functional** — call methods + `useCallStateHooks()` state hooks (`call.camera` /
  `call.microphone` / `call.screenShare`, `useCameraState`, `useHasOngoingScreenShare`) for behavior
  no slot reaches.

Confirm exact prop / slot / theme-key names against the installed `@stream-io/video-react-native-sdk`
and the RN Video docs — names below are verified against current source but drift across versions.

**Video call surfaces** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Call layout | equal grid of tiles vs. one large tile + filmstrip (speaker view); paginated? — decides the tile arrangement below | Layout | `CallContent` `layout` prop: `'grid'` (`CallParticipantsGrid`, equal tiles) vs. `'spotlight'` (`CallParticipantsSpotlight` — one large tile + a `CallParticipantsList` filmstrip); default `grid`. **An active screen share forces `spotlight` regardless** of the prop. No page-count prop — the filmstrip/grid is a scrollable `FlatList` with visibility-based track subscription; tune `numberOfColumns` / `horizontal`. For runtime grid⇄spotlight switching build a switcher (runtime-layout-switching cookbook) or render `CallParticipantsGrid` / `CallParticipantsSpotlight` directly. |
| Participant tile | name label, mute (mic-slash) indicator, video-off/avatar fallback, dominant-speaker ring/highlight, network-quality (signal) bars | Theming (+ Component slot) | `ParticipantView` slots (all also injectable on `CallContent`): name + mic-off/video-off/pin + dominant-speaker `SpeechIndicator` → `ParticipantLabel`; video-off avatar → `ParticipantVideoFallback` (`participant.image`); signal bars → `ParticipantNetworkQualityIndicator` (from `participant.connectionQuality`); video → `VideoRenderer`. Recolor via `participantLabel.*` / `participantNetworkQualityIndicator.container` theme keys. **Dominant-speaker ring is NOT a slot** — a 2px border recolored to `colors.buttonPrimary` when speaking; restyle via theme `participantView.highlightedContainer` (+ `colors.buttonPrimary`). Pass `null` to a slot to hide it. |
| Local participant / self-view | small self-view thumbnail present? position, size, draggable? | Component slot (+ Theming) | `FloatingParticipantView` (`CallContent`'s `FloatingParticipantView` prop; `null` to remove). Draggable, snaps to 4 corners; `alignment` (`'top-left'|'top-right'|'bottom-left'|'bottom-right'`, default `'top-right'`). **Only in grid layout, not PiP, and only with 1–2 remote participants** — a 3+ grid folds the local tile in. Size is auto from the track aspect ratio (not a prop); tap swaps local⇄remote in 1:1. Theme `floatingParticipantsView.*`. |
| Screenshare | a shared screen/window inside a tile — present? layout when active (spotlight vs. tile) | Functional (+ Layout) | Renders automatically: an ongoing share flips `CallContent` to `spotlight` (`useHasOngoingScreenShare()`), puts the `screenShareTrack` in the spotlight tile (`objectFit='contain'`), and shows the local sharer a `ScreenShareOverlay` ("Stop Screen Sharing"; injectable / `null`). Start/stop via `ScreenShareToggleButton` added to a custom `CallControls` (`screenShareOptions`: `type` `'broadcast'|'inApp'`, `includeAudio`). Screen-share label branch lives in `ParticipantLabel`. iOS needs a Broadcast Extension (screensharing guide). |
| Call controls | circular control bar (usually bottom): camera toggle, mic toggle, leave/hang-up, plus extras (flip camera, speaker, reactions, screenshare); position, glyphs | Component slot (+ Theming) | Default `CallControls` is a **fixed** row: `ToggleVideoPublishingButton`, `ToggleAudioPublishingButton`, `ToggleCameraFaceButton` (flip), `HangUpCallButton`. **No per-button order/add/remove prop** — to add `ReactionsButton`/`ScreenShareToggleButton`, reorder, or drop one, replace the whole component via `CallContent`'s `CallControls` prop (reuse the exported buttons; build custom ones from `call.microphone.toggle()` / `call.camera.toggle()` / `call.camera.flip()` / `call.leave()` — replacing-call-controls cookbook). Recolor via theme `callControls.container` / per-button slots (`hangupCallButton`, `toggleAudioPublishingButton`, …) or `colors.button*`; shared `CallControlsButton` takes `color` / `size`. |
| Device selectors | camera / mic picker affordances shown? | Functional (custom UI) | **RN ships no camera/mic device-picker component** (unlike React web's `DeviceSelector*`). Only camera **flip** (`ToggleCameraFaceButton` → `call.camera.flip()`) and on/off toggles exist. Enumerate/select devices programmatically via `useCameraState` / `useMicrophoneState` (`call.camera` / `call.microphone`); audio-output routing is native/programmatic (`callManager.ios.showDeviceSelector()` opens the iOS route picker; Android via `callManager.android.*`) — `useSpeakerState()` is **not** supported on RN. If the design shows a device dropdown, **build it custom** (or flag it). |
| Livestream surface | "LIVE" badge + viewer count; host vs. viewer controls; watching state | Component slot (+ Theming) | `HostLivestream` / `ViewerLivestream` (or `LivestreamPlayer`, which wraps `ViewerLivestream` for HLS viewers) — separate from `CallContent`. LIVE badge → `LiveIndicator` (shown while live / HLS broadcasting); viewer count → `FollowerCount` (`useParticipantCount()`, `humanizeParticipantCount`); elapsed time → `DurationBadge`; all injectable slot props on the top-view. **Host vs. viewer controls differ**: `HostLivestreamControls` (start/end + media toggles) vs. `ViewerLivestreamControls` (volume / maximize / play-pause / leave). Watching state via `joinBehavior` (`'asap' | 'live'`) → `ViewerLobby`. Theme keys `liveIndicator.*`, `followerCount.*`, `durationBadge.*`, `hostLivestream*` / `viewerLivestream*`. |
