# Stream React - integration review

React (web) checks for a read-only integration review. Run the procedure in
stream skill's integration-review.md; this file uses the same section names,
and each bullet here replaces the generic bullet on the same topic. The
"Livestream" section does the same for stream skill's livestream-review.md,
and "Two-person calls" for stream skill's two-person-review.md.

This file covers Video: the client, calls, livestreams, and two-person
calls. For Chat and Feeds run the generic checks against the SDK's docs; a
section with no heading here has no React detail yet. React Native shares
the Video client but differs on devices, background behaviour, and
playback: use the stream-react-native skill for it.

Video pages are under `getstream docs video/react`, Chat SDK pages under
`getstream docs chat-sdk/react`. The Video checklist is
`advanced/integration-best-practices.md`: read it first.

Symbols were checked against `@stream-io/video-react-sdk` 1.46.2
(`@stream-io/video-client` 1.67.0). Review the versions the lockfile pins:
read the SDK source in `node_modules/@stream-io/video-client` and
`node_modules/@stream-io/video-react-sdk` at those versions, and adapt a
check that names a newer API.

## Measure, don't guess

A code read can't count requests: effects re-run when a dependency changes
identity, and a component that remounts runs them again. Without a running
app, list request counts as unverified. The review changes no code; these
are for a run the developer makes or agrees to:

- Browser DevTools, Network tab, filtered on `stream-io-api.com`: count the
  requests one viewer makes while opening one stream. Loading a call is a
  GET on `/call/<type>/<id>`, joining is a POST on `.../join`. Count the
  requests to the app's own backend on the same path separately. Source:
  SDK code.
- Measure a production build (`next build` and `next start`, `vite build`
  and `vite preview`). In development `StrictMode` runs effects a second
  time, so counts from a development server are too high.
- Video logs: `options: { logOptions: { default: { level: 'debug' } } }`
  on the client. Docs: `guides/client-auth.md`.
- Renders and remounts: the React DevTools Profiler, with "Record why each
  component rendered" on.

## Initialization

- One `StreamVideoClient` per signed-in user, created in an effect with
  `disconnectUser()` in its cleanup, or with
  `StreamVideoClient.getOrCreateInstance(...)`. Never in the body of a
  component, and not once per route or per call screen. Docs:
  `advanced/integration-best-practices.md`.
- The effect that creates the client depends on stable values. A `user`
  object or a `tokenProvider` function built during render and listed as a
  dependency makes a new client, and a new WebSocket, on every render.
  Source: the app code.
- Tokens come from a `tokenProvider`, not from a fixed `token`. The docs
  recommend short-lived tokens with a provider. The token route gives a
  token only for the user of the current session, never for a user id
  taken from the request. Docs: `guides/client-auth.md`.
- Nothing secret is in a `NEXT_PUBLIC_`, `VITE_`, or `REACT_APP_` variable:
  those are compiled into the bundle. The API key is not a secret.
- Next.js: the Stream client and components sit below a `'use client'`
  boundary, and nothing builds the client during server rendering: no
  `new StreamVideoClient` at module level or in a render-time initializer.

## Calls

- `client.call(type, id)` makes a new client-side object every time it
  runs. It is called in an effect or an event handler and kept in state,
  not called during render, and `call.leave()` runs in the cleanup.
  Components below `<StreamCall>` read it with `useCall()`. Docs:
  `advanced/integration-best-practices.md`.
- Every `call.join()` has its rejection handled and shown. So do
  `call.camera.enable()` and `call.microphone.enable()`.
- The UI handles every calling state from `useCallCallingState()`, not
  only `JOINED`. Docs: `guides/calling-state-and-lifecycle.md`.

## Livestream

React detail for stream skill's livestream-review.md, group by group. A
bullet here replaces the generic bullet only where it covers the same thing;
every generic check without a bullet here still applies. Docs:
`guides/livestreaming.md`, `ui-components/livestream/livestream-player.md`,
`ui-cookbook/watching-a-livestream.md`, `advanced/broadcasting.md`.

### Viewer join path

- Viewers make at most one `call.get()`, when the page needs the call's
  state before joining (waiting, ended), and then one `call.join()`.
  With a connected user `get()` also watches the call, so its state
  follows backstage, live, and ended from then on. Source: SDK code.
- A plain `call.join()` never creates a call. `call.join({ create: true })`
  and `call.getOrCreate()` create it when it doesn't exist: flag those two
  in a viewer path. The grant check in the generic file still applies.
  Source: SDK code.
- `LivestreamPlayer` does this by itself: one `get()`, then one `join()`
  when the call is live (`joinBehavior="live"`), or as soon as the viewer
  may enter (`"asap"`, the default: live, inside the join-ahead window, or
  holding `join-backstage`). An unloaded call counts as backstage, so it
  never joins early by accident. It leaves the call when it unmounts. That
  passes the request-count check; don't wrap it in the app's own `get()`
  or `join()`. The next bullet, blocked audio, and the end of the stream
  are checked separately. Source: SDK code.
- `LivestreamPlayer` reports a failed `get()` or `join()` only to the
  console unless `onError` is passed. Without it, a viewer whose call
  doesn't exist or who has no access sees the waiting screen forever. Pass
  `onError` and show the failure. Source: SDK code.
- A custom viewer waits on `useIsCallLive()` and joins from an effect when
  it becomes true. It is false until the call is loaded. Nothing polls
  `get()` and nothing re-joins on a timer.
- The effect that creates the call object and leaves it in its cleanup
  depends only on the client, the call type, and the call id. Any other
  dependency that changes identity (an options object built during
  render) leaves and joins again for every viewer. The effect that
  triggers the join may also depend on the live state. A changing `key`,
  or a conditional wrapper around the player, remounts it with the same
  result. Source: the app code.
- `join()` retries by itself: 3 attempts (`maxJoinRetries`) with a random
  wait of up to 5 seconds, except for a refusal the API marks
  unrecoverable (a permission refusal is one), which is sent once. After a
  failed join the call is back in its earlier state and can be joined
  again, so an unbounded loop or interval around `join()` is a request
  loop of up to 3 requests per turn: FAIL. The bounded retry the generic
  check allows counts the SDK's attempts in its total. Source: SDK code.
- From 1.42.0 `join()` calls that overlap share the one in flight, and a
  `join()` on a call that is already joined throws. Before 1.42.0 the
  screen guards against double joins itself. Source: SDK code.
- A viewer must not be asked for the camera or the microphone. On `get()`
  and `join()` the SDK applies the call type's device defaults: when the
  viewer's role may publish and `camera_default_on` or `mic_default_on`
  is set, it turns the device on, which can bring up the browser's
  permission prompt and publish the viewer. PASS when the viewer role has
  no `send-video` and `send-audio` grant and the viewer page mounts no
  lobby or device component and calls no `camera.enable()` or
  `microphone.enable()`. If the review can't read the grants, that half
  is unverified. Source: SDK code.
- Anonymous viewers (`{ type: 'anonymous' }`) open no WebSocket and
  receive no events: `useIsCallLive()` never changes after the first
  `get()`, so they can't wait for Go Live on the call's state. Their token
  needs the `call_cids` claim. Guest viewers (`{ type: 'guest' }`) get
  their id from the server, and have no grants on the default `livestream`
  type until the `guest` role is given them. Docs: `guides/client-auth.md`.

### Host path

A host either publishes from the browser or from an encoder; check the one
the app uses.

- Browser host: `call.getOrCreate({ data: { members: [{ user_id: <own id>,
  role: 'host' }] } })`, then `call.join()`, both awaited with errors
  shown. As the creator the host can join backstage and publish. A call
  created by the backend also passes when it meets the generic check.
- `goLive()` is awaited and a rejection is shown. The host UI shows
  backstage or live from `useIsCallLive()`, not from a flag set when the
  button was clicked. `goLive({ start_hls: true, start_recording: true })`
  starts those with it.
- `stopLive()` (back to backstage) and `endCall()` (final) are separate
  controls, and `endCall()` is behind a confirmation.
- Nothing in the SDK ends or stops a stream when the page goes away.
  When the only publisher closes the tab, reloads, or crashes, the call
  stays live with nobody publishing. The host page warns on `beforeunload`
  while live, which covers a mistaken close but not a crash, and after a
  reload or a crash the host can open the same call and join again.
  Source: SDK code.
- `call.leave()` in an unmount cleanup is the documented pattern, and it
  also means that a route change inside the app takes the host out while
  the stream stays live. In-app navigation away from the host screen is
  guarded by a prompt that offers End, Stop Live, or stay. Source: the app
  code.
- Before going live the host has a lobby: `VideoPreview`, a device
  selector, and microphone and camera state from `useMicrophoneState()`
  and `useCameraState()` (`isMute`, `hasBrowserPermission`). A denied
  permission is explained with how to allow it in the browser, because
  the browser may not ask again. Docs:
  `advanced/integration-best-practices.md`, `ui-cookbook/lobby-preview.md`.
- Reconnecting: the host UI shows `CallingState.RECONNECTING`, `MIGRATING`,
  and `OFFLINE` as states and calls neither `endCall()` nor `leave()` on
  them. `RECONNECTING_FAILED` is shown with a way to join again. If
  `call.setDisconnectionTimeout(seconds)` is set, it is long enough for a
  network switch. Docs: `ui-cookbook/network-disruption.md`.
- A phone or tablet browser as the host device: the SDK's core components
  hold no screen wake lock, so the host page requests one
  (`navigator.wakeLock`, where the browser has it) and requests it again
  when the page becomes visible. Source: SDK code. Mobile browsers
  commonly pause the camera when the tab is hidden or the screen locks;
  what the host's device really does is unverified without a test, so
  list it under event readiness.
- Encoder host (RTMP): the address comes from `useCallIngress()`, and the
  stream key is a user token. The backend mints it for the encoder's own
  user (the generic one-publisher-per-identity check), with an expiry
  past the end of the event, so that an encoder that reconnects is still
  accepted. The key is not written to logs or shown to anyone but the
  host. Docs: `advanced/broadcasting.md`.
- Resolution: the SDK applies the call type's target resolution to the
  camera. The generic 720p check is about phones. For a desktop browser
  host record the setting; whether the host's computer holds it for the
  length of the event, with screen sharing if used, is a rehearsal item
  for event readiness.

### Call-type settings

- `camera_default_on` and `mic_default_on` together with publish grants on
  the viewer's role turn every viewer's devices on. See Viewer join path.
- `starts_at` with `join_ahead_time_seconds`: `LivestreamPlayer` with
  `joinBehavior="asap"` lets viewers in when the window opens, from a
  local timer that makes no requests. With `"live"` they wait for Go Live
  whatever the window says. Check that the behaviour chosen matches the
  setting. Source: SDK code.

### Audience-scale behaviour

- The viewer count is `useParticipantCount()`, with
  `useAnonymousParticipantCount()` next to it, not
  `useParticipants().length`: that list is truncated to 250 on large
  calls. `LivestreamLayout` shows the right number. The livestreaming
  guide's sample adds the list's length to the anonymous count, which is
  fine for a small room only. Docs: `guides/call-and-participant-state.md`.
- No `setInterval` around `call.get()`, `client.queryCalls()`, or
  `call.queryMembers()` in the viewer app. `queryCalls({ watch: true })`
  keeps the calls it returned current. Docs: `guides/querying-calls.md`.
- `call.sendReaction` and `call.sendCustomEvent` send one request per
  call; the SDK doesn't throttle them. The reaction button animates every
  click locally and sends on a timer (see the generic check for how
  often), and a rejection is not retried. Source: SDK code.
- The viewer page doesn't render the audience: no `useParticipants()`
  mapped to a list of everyone, no `CallParticipantsList` for viewers.
- A chat message or a reaction doesn't remount the player or re-run its
  effects: the player keeps its component type, `key`, and position in
  the tree, and no value that changes with a message is a dependency of
  the call's effects. Incoming reactions and custom events are batched
  before they reach React state, not one state update per event. Source:
  the app code.
- The end of the stream: on `call.ended` the SDK leaves the call by
  itself, `useCallEndedAt()` gets a value, and the calling state becomes
  `LEFT`. The viewer page stops there and shows a state for it. An effect
  that joins whenever the state is not `JOINED` starts a loop here: FAIL.
  Source: SDK code.
- Stop Live looks the same to a viewer without `join-backstage`: the SDK
  takes them out of the call and sets `endedAt` locally, although the
  call has not ended. `useCallEndedAt()` alone can't tell the two apart.
  Where the host can go live again, the page makes one new call object
  and one `get()` after the calling state becomes `LEFT`: the server's
  answer says ended or backstage, and the new object waits for Go Live.
  One read, not a loop. What viewers see when the host goes live a
  second time is unverified without a test. Source: SDK code.
- The docs' ended view calls `call.listRecordings()`. Kept as it is, every
  viewer sends that request in the second the stream ends. Keep it only
  if replays are offered there and the viewer role may list them, and
  then load it on a click or from the app's backend. Docs:
  `guides/livestreaming.md`.
- Chat next to the stream: the Chat client is created once per signed-in
  user (`useCreateChatClient` or an equivalent), the `livestream`-type
  channel is watched once in an effect, the list is
  `VirtualizedMessageList` or another list that renders only what is on
  screen, and the loaded messages are capped (`maxLoadedItems`, off by
  default). Docs: `features/channels/livestream-chat.md` in `getstream
  docs chat-sdk/react`; on an older major read that major's docs.

### Playback and event readiness

- Blocked audio: a viewer who arrives by a link has made no gesture on the
  page, and the browser may block sound until they do. The blocked-audio
  overlay is part of `DefaultParticipantViewUI`; `LivestreamLayout`, and
  with it `LivestreamPlayer`, draws its own overlay without it. A viewer
  page built on either one adds its own prompt: `useIsAutoplayBlocked()`
  and a button that calls `call.resumeAudio()`. A child of
  `LivestreamPlayer` is rendered inside its `StreamCall`, so the hook
  works there. A "Watch" button before the join makes blocking less
  likely but doesn't replace the prompt. Docs:
  `ui-cookbook/blocked-audio.md`; source: SDK code.
- HLS: something starts it (`goLive({ start_hls: true })`,
  `call.startHLS()`, or the call type's mode), and the page reads
  `useCallEgress()?.hls.playlist_url` after one `get()`. The URL is empty
  until broadcasting has started, so the page treats that as a waiting
  state and follows the call's state for it; an anonymous viewer gets no
  updates and needs the URL from the app's backend. It is played with
  HLS.js or the browser's own player, and the player is destroyed when
  the page is left. HLS viewers don't `join()`. Docs:
  `advanced/broadcasting.md`.
- Video is rendered with `ParticipantView` (or `call.bindVideoElement` for
  an element of the app's own), not by attaching a participant's
  `videoStream` to a `<video>` by hand. The SDK subscribes to a
  participant's video only for an element it has bound, at that element's
  size, so a hand-made element gets no picture, and the size is how the
  server picks the layer to send. Source: SDK code.
- Indicators: a viewer sees `RECONNECTING` and `RECONNECTING_FAILED` from
  `useCallCallingState()`, and a state for a joined call with no host
  video. Docs: `guides/livestreaming.md`,
  `ui-cookbook/network-quality-indicator.md`,
  `ui-cookbook/low-bandwidth.md`.
- Where the link opens: a link tapped inside another app (mail, chat) may
  open in that app's built-in browser, without the viewer's session.
  Check which browsers the product supports, what an unsupported one is
  shown, and that sign-in from there leads back to the stream. Docs:
  `basics/supported-platforms.md`.
- Versions: compare the lockfile with the latest releases on npm and give
  both with the date. Below 1.42.0 (the shared in-flight join) the checks
  above behave differently; say so in the finding. Release notes are on
  the SDK's GitHub releases page.

## Two-person calls

React detail for stream skill's two-person-review.md, group by group. The
bullets here add to the generic checks and don't replace them: every
requirement in the generic bullet still applies. "Scheduled calls" at
the end is only for apps where both sides open a call at a booked time;
skip it for calls that ring. An app on the
plain JS client (`@stream-io/video-client`, no React) is covered by the
same checks: each hook named here reads `call.state` or a device manager,
which that app uses directly, and its pages are under `getstream docs
video/javascript`. Docs: `guides/joining-and-creating-calls.md`,
`guides/permissions-and-moderation.md`, `guides/events.md`,
`guides/custom-events.md`, `guides/camera-and-microphone.md`,
`guides/noise-cancellation.md`.

### Access and membership

- Where the backend creates the call with both people as members
  (`@stream-io/node-sdk`: `client.video.call(type, id).getOrCreate({ data:
  { created_by_id, members } })`), the browser only joins: a plain
  `call.join()` never creates a call. `call.getOrCreate()` or `call.join({
  create: true })` in the browser, with members taken from the page, lets
  a signed-in user make a call with members of their choosing when their
  role has `create-call`, and with `ring: true` it rings them. That is
  the usual shape of a call button in a chat: run the generic check on
  what ties the two people together. Source: SDK code.
- The `user` object given to `StreamVideoClient` is sent to Stream when
  the client connects: its `name`, `image`, and `custom` are stored on the
  user. Run the personal-data check on it, as well as on the backend's
  `upsertUsers` and on member `custom`. Source: SDK code.
- A join refused by the participant limit rejects `call.join()` with an
  `SfuJoinError`, after the SDK's own attempts. The page shows it with a
  retry button and doesn't loop. Source: SDK code.

### Call-type settings

No React detail: the generic checks apply. The client has no bitrate
setting of its own (see the internal calls under Two-person media
behaviour), and the SDK applies the call type's target resolution to the
camera.

### Two-person media behaviour

- Receiver-requested resolution: in this SDK "the size the receiver asks
  for" is the size of the element behind `ParticipantView` or
  `call.bindVideoElement`, which the SDK reports by itself, and
  `call.setPreferredIncomingVideoResolution()`. The generic check says
  what they do in a two-person call. `call.setIncomingVideoEnabled(false)`
  is not a resolution request: it drops the subscription, with any number
  of participants. Docs: `ui-cookbook/manual-video-quality-selection.md`;
  source: SDK code.
- Internal calls on the sending side: `call.updatePublishOptions()`
  (`preferredBitrate`, `preferredCodec`, `maxSimulcastLayers`) is marked
  `@internal`, logs a warning, and has no effect once the call is joined.
  `call.camera.selectTargetResolution()` is marked `@internal` too. FAIL
  for either. At 1.46.2 no public call changes the resolution or the
  bitrate that is sent during a call. `applyConstraints()` on the track
  taken from `call.camera.state.mediaStream` is not SDK API: the SDK gets
  a new track, with its own constraints, when the camera is turned off and
  on or the device changes, and the app's constraint is gone. Worth doing.
  Source: SDK code.
- Layout: `useParticipants()` and `useRemoteParticipants()` return
  sessions. A layout that draws `remoteParticipants[0]` and nothing else
  has a state for an empty list, and doesn't break or show the wrong
  person when the list holds two: the same user in a second tab is a
  remote participant with the same `userId`. Source: the app code.
- Drawing video with `ParticipantView`: see Playback and event readiness
  under Livestream.

### Leave and end handling

- Leave reasons: FAIL for a comparison of `event.reason` from
  `call.on('call.session_participant_left', ...)` with fixed strings. This
  SDK alone sends several: `call.leave()` sends "user is leaving the call"
  unless the app passes `call.leave({ message })`, and the SDK's own
  leaves send other texts. For a deliberate leave: `await
  call.sendCustomEvent({ type: ... })`, then `call.leave()`; the other
  side listens with `call.on('custom', ...)`. The sender's role needs the
  `send-event` grant. Docs: `guides/custom-events.md`; source: SDK code.
- Own connection: the page shows `CallingState.RECONNECTING`, `MIGRATING`,
  and `OFFLINE` from `useCallCallingState()` as states, and calls neither
  `leave()` nor `endCall()` on them. `RECONNECTING_FAILED` is shown with a
  way to join again. Docs: `ui-cookbook/network-disruption.md`.
- The end of the call: on `call.ended` the SDK leaves by itself,
  `useCallEndedAt()` gets a value, and the calling state becomes `LEFT`.
  The page shows an ended state. An effect that joins whenever the state
  is not `JOINED` starts a loop here: FAIL. `call.endCall()` ends it for
  both and needs `end-call`; `call.leave()` is the hang-up. Source: SDK
  code.
- Kicked, removed, or blocked: the SDK treats being taken out by the
  server like the end. It leaves, sets `endedAt` locally, and the calling
  state becomes `LEFT`, although the call goes on for the other person.
  `useCallEndedAt()` alone can't tell the two apart, and `LEFT` alone
  doesn't say why. The page remembers its own `leave()`. For a `LEFT` it
  did not ask for, a `call.kicked_user` or `call.blocked_user` event with
  its own id in `event.user` says the person was taken out, and one
  `get()` on a new call object tells a call that has ended from one that
  goes on. A failed read proves nothing. If the cause stays unknown the
  page shows a closed session, with no automatic join and no polling.
  Whether the event or the SDK's own leave reaches the page first is
  unverified without a test. Source: SDK code.

### Devices and audio

- Mute: with the microphone muted and the user joined, speaking-while-
  muted detection keeps a capture of its own open, so the browser goes on
  showing the microphone as in use. It is on by default for users who may
  send audio. Turn it off with
  `call.microphone.disableSpeakingWhileMutedNotification()` and back on
  with `enableSpeakingWhileMutedNotification()`;
  `useMicrophoneState().isSpeakingWhileMuted` is the signal for the hint.
  `call.microphone.state.disableMode` and `call.camera.state.disableMode`
  are read-only: FAIL for code that assigns to them, with a cast or
  without. Docs: `guides/camera-and-microphone.md` (speaking while muted
  detection); source: SDK code.
- Noise cancellation: `call.microphone.enableNoiseCancellation()` throws
  until the call's settings and the user's capabilities are loaded, when the
  call type's mode is `disabled`, and when the user lacks the
  `enable-noise-cancellation` capability. `NoiseCancellationProvider` below
  `StreamCall` waits for the settings by itself. FAIL for a direct call that
  can run before the call is loaded (before `call.get()`,
  `call.getOrCreate()`, or `call.join()` has resolved), and for one whose
  rejection is swallowed. Overload: from `@stream-io/video-react-sdk` 1.45.0
  (`@stream-io/video-client` 1.64.0, `@stream-io/audio-filters-web` 0.11.0)
  `useNoiseCancellation().status` is `enabled`, `disabled`, `suspended`, or
  `overloaded`, and `call.microphone.state.noiseCancellationStatus$` carries
  the same for the plain client. The page shows `suspended` and
  `overloaded`. On an older version there is no signal: report the version,
  not a FAIL. Docs: `guides/noise-cancellation.md` (handling device
  overload); source: SDK code.
- Blocked audio: the prompt is `useIsAutoplayBlocked()` with a button that
  calls `call.resumeAudio()`; `DefaultParticipantViewUI` has it built in
  (see Playback and event readiness under Livestream). From 1.44.1
  (`@stream-io/video-client` 1.63.0) the SDK also resumes blocked audio
  on the next click or key press anywhere on the page; below that only
  the app's own button does. Blocking is less likely for a person who
  clicked Join on the same page, and more likely for one who arrives
  from a link that joins without a click; the prompt is needed either
  way. Docs: `ui-cookbook/blocked-audio.md`; source: SDK code.
- Picture-in-picture: the video-element API
  (`ui-cookbook/picture-in-picture.md`) shows one video and is offered only
  when `document.pictureInPictureEnabled` is true. Document
  picture-in-picture (`ui-cookbook/document-pip.md`) carries a whole call UI
  and is offered only when `'documentPictureInPicture' in window`; the page
  lists the browsers that have it, and not all do. FAIL for a control shown
  with no feature check of any kind. With Document picture-in-picture the
  audio elements stay in the main window (`ParticipantsAudio`). On iPhone
  and iPad browsers, picture-in-picture of a call and what happens to the
  camera in the background are unverified without a device test.

### Scheduled calls

- The other side: an effect that leaves, ends the call, or navigates away
  as soon as `useRemoteParticipants()` is empty ends the appointment on a
  drop or a reload of the other person. It waits on a timer, or for the
  custom event above. Source: the app code.
- Nothing in the SDK carries a call across a reload. The page takes the
  appointment from its route, makes the call object in an effect, and
  offers the same call again, as a new session and subject to the generic
  check. Source: SDK code.
- The page doesn't call `endCall()` in an unmount cleanup or on
  `beforeunload`: that ends the appointment for the other person on every
  reload. `call.leave()` in the cleanup is the documented pattern. Docs:
  `advanced/integration-best-practices.md`.
- The lobby: `VideoPreview`, a device selector, and microphone and camera
  state from `useMicrophoneState()` and `useCameraState()`, as in Host
  path under Livestream. Docs: `ui-cookbook/lobby-preview.md`.
