# Livestream review

Extra checks for an integration review of an app that livestreams: one or a
few hosts publish, an audience watches, usually with chat and reactions next
to the video. Audio rooms share the backstage lifecycle, so the same checks
apply to them. Run it from integration-review.md when the scope step finds
either; that file's procedure, evidence rules, and report format apply here.

A livestream fails in different places than a call. The audience arrives
within a minute or two, every viewer runs the same code path, and the
broadcast depends on one publishing host. A request that is harmless once per
user becomes the load, a retry loop becomes thousands of loops, and a
host-side mistake is seen by everyone. Most checks below come down to one of
those three.

The platform file's "Livestream" section uses the same group names. A
platform bullet replaces the generic bullet only where it covers the same
thing; a generic check with no platform bullet still applies. Where a
platform has no file yet, cite that SDK's livestreaming guide and its source.

Setup and settings can be read from code. What a phone does when it is
locked, overheats, or loses the network can't: mark those unverified and
carry them to the event readiness list.

## Scope

Add to the review's scope answers. Take them from the code, and ask only what
the code can't answer:

- Expected concurrent viewers at the peak, and how they arrive: a push
  notification, a scheduled start, a ticketed event, or a trickle.
- Where the audience is, by country or region.
- How the host publishes: the mobile app, a browser, or an encoder (RTMP,
  SRT, WHIP). One host device, or several.
- How viewers watch: WebRTC (they join the call), HLS, or both.
- Who may watch: anyone, signed-in users, or ticket holders. Anonymous or
  guest viewers.
- The date and start time of the next large event, if there is one.

## Locate the livestream

On top of the review's step 2, find and read:

- Where the call is created: client or server, by which user, with which
  call type, members, and per-call settings (`starts_at`, backstage).
- The viewer path: every Stream call between opening a stream and video on
  screen, and what happens when the stream is not live yet, has ended, or
  the join is refused.
- The host path: create, join, go live, stop live, end, and what happens on
  back, app background, an incoming phone call, and a lost network.
- Every timer and every retry loop that makes a Stream call.
- The call type and the channel type as configured. If the CLI is already
  set up for the app, read them with `getstream api GetCallType --name
  <type>` and `GetChannelType`; long arrays are cut in the default output,
  so select with `--jq` (for example `--jq '.grants'`, `--jq '.settings'`).
  Otherwise the settings checks are unverified, with the code that creates
  calls as the lead.
- The backend's webhook or SQS handlers for call and chat events.

Add the viewer path and the host path to the session trace, one line per
step with the Stream calls it makes. Then estimate the arrival: viewers times
requests per viewer on entry, per platform, in the minute they arrive. Viewers
who wait for the stream all join in the same few seconds at Go Live. Put the
estimate in the report next to the endpoint limits.

## Checks

### Viewer join path

- The path makes at most one read of the call before the join (to show a
  waiting or ended state) and one join. Neither runs again on a rebuild or
  a resume, and a read whose result isn't used is dropped. A retry after a
  failure may repeat them. Each extra call is one more request per viewer
  in the minute the audience arrives, against a per-app, per-platform limit
  for that endpoint.
- Viewers can't create calls: the role viewers hold has no `create-call`
  grant. Loading the call with a read that doesn't create, and joining
  with create off where the SDK has the flag, prevents creating one by
  accident, but only the grant stops it. On the default `livestream` type
  the `user` role can create calls and several host grants go to the
  call's creator, so a viewer who opens the id first owns the stream (see
  Host path). Without the grants, mark this unverified.
- A viewer who arrives before the stream is live waits on the call's state
  (the SDK's call object is watched and reports going live). No polling of
  the call and no timed re-join. A join into backstage is refused with a
  403 by design. A viewer with no event connection (an anonymous user)
  needs another signal, such as the app's backend.
- A join refused with a 403 (not live yet, no access, ended) is not tried
  again until something changes: the call goes live, or access is granted.
  Other failures, 429 included, are retried a bounded number of times with
  backoff and jitter, and then the viewer gets an error and a retry
  button. Retries stop when the viewer leaves the screen or the stream
  ends. The SDKs already retry inside join, so an app loop around it
  multiplies the attempts. Each user is limited to 60 requests a minute
  per endpoint: a client in a loop locks itself out and stays out.
- Every viewer has their own user id. A shared "viewer" account puts the
  whole audience on one user's rate limit. For unauthenticated viewing use
  the SDK's guest or anonymous users, and check that the call type grants
  that role the permissions it needs.
- Tokens expire and come from a token provider (the Initialization check).
  In a livestream a static token fails late: a viewer who keeps the app
  open past its expiry can go on watching for a while, and then loses
  events or is dropped at the next reconnect.
- The app's own backend is on the join path too (token endpoint, stream
  details, entitlement). List the backend calls a viewer makes on entry.
  Whether they hold up when the audience arrives is unverified without a
  load test that includes them.

Docs: `rate-limits.md` in `getstream docs platform` (how limits are counted,
the per-user limit) and in `getstream docs video/api` (per-endpoint
defaults); `streaming/backstage.md` in `getstream docs video/api`.

### Host path

- The call is created by the host's user, or server-side with the host as
  its creator (`created_by_id`), before any viewer can reach it. On the
  default `livestream` type, joining backstage and sending video are
  granted to the creator (the `-owner` grants) and to `admin`; a `host`
  member who did not create the call can't do either. If something else
  creates the call (a service user, a bot, a viewer), the call type has to
  grant `join-backstage`, `send-video`, and `send-audio` to the host's
  role. Check the grants; don't assume them.
- Each broadcast uses a new call id. A reused id carries the previous
  session's state, members, and recordings into the next event.
- One publisher per identity. An encoder (RTMP, SRT, WHIP) publishes as its
  own user, not as the user who is also joined from the app.
- Go Live is its own step and its failure is shown. Starting a recording or
  HLS doesn't take a call out of backstage, so in a host flow that skips
  Go Live the host publishes and viewers are refused. The host UI shows
  backstage or live from the call's state.
- The host sees what is being published before going live: own preview,
  and microphone and camera state from the call's state. Going live with
  the microphone or camera off warns. Worth doing.
- End is behind a confirmation, and leaving the screen (back, swipe, a
  route change) doesn't end the stream by accident or leave it live with
  nobody publishing. Stop Live (back to backstage) and End (final) are
  different actions in the UI.
- After a crash, a kill, or an accidental leave, the host can get back in:
  the app knows which call is theirs and joins it again as host.
- The setup for publishing in the background, with the screen locked, and
  through an incoming phone call is in place. The platform file names it.
  If it is missing, ask what the product wants to happen. What the device
  really does is unverified without a test.
- A lost network is shown as reconnecting and doesn't end the stream. The
  host UI follows the call's connection state.
- Record the resolution a phone host publishes at. The mobile livestreaming
  guide recommends 720p; the default `livestream` type targets 1080p.
  Higher resolutions heat the phone, and a hot phone drops frames. Worth
  doing unless the higher setting was tested on the host's device for the
  length of the event.
- A second host device, or the plan when the host's phone fails, is written
  down. One device is a single point of failure. Report it under event
  readiness, not as a FAIL.

Docs: `streaming/backstage.md`, `streaming/mobile-livestreaming.md`,
`call-types/permissions.md`, and `call-lifecycle.md` in `getstream docs
video/api`; the SDK's livestreaming guide.

### Call-type settings

Read the call type the launch build uses, on the app it points at.

- Backstage with `join_ahead_time_seconds` at 0 (the default), or calls
  created without `starts_at`: every viewer who opens the stream before Go
  Live is refused. That is fine when the app holds them in a waiting state
  (Viewer join path). If viewers should be let in early, set `starts_at`
  and a join-ahead window, and remember they then receive the host's audio
  and video before Go Live.
- An announcement (push, email, in-app) goes out after Go Live, for example
  from the `call.live_started` event, or the waiting state above exists.
  An audience sent to a stream that is still in backstage arrives as a
  burst of refused joins.
- `limits.max_duration_seconds`, if set, is longer than the longest event.
  When it passes the session ends for everyone. `limits.max_participants`,
  if set, covers the expected peak.
- Viewers can't publish: the viewer role has no `send-audio`, `send-video`,
  or `screenshare` grant. Hiding the buttons is not enforcement.
- Access matches the product and is enforced by the server, not by the
  app's UI. For ticketed or paid streams one way is: the plain `user` role
  has no `join-call`, and the backend adds ticket holders as call members.
  The member role has `join-backstage` or `join-ended-call` only if ticket
  holders are meant to get in early or after the end. A refund removes the
  membership, and removes a viewer who is already watching.
- Recording, HLS, transcription, and frame recording are in the mode the
  product needs. `auto-on` starts them for every call of the type.
- Compare the call type on the app the rehearsals ran on with the one on
  the production app. Differences that change launch behaviour (backstage,
  limits, grants, recording modes) are findings: a rehearsal on staging
  proves the staging settings.
- Per-call overrides in the code that creates calls don't contradict the
  type.

Docs: `streaming/backstage.md`, `call-types/settings.md`,
`call-types/permissions.md`, and `call-types/builtin.md` in `getstream docs
video/api`.

### Audience-scale behaviour

- The viewer count comes from the session's participant count in the call
  state, not from the length of the participant list (the list is truncated
  on large calls) and not from a tally the app keeps.
- No viewer client polls the API on a timer (the call, a call query, the
  viewer count). A poll every 10 seconds from each viewer uses up a
  1,000-a-minute endpoint limit at about 170 viewers. A list of live
  streams comes from the app's backend or from one query; watching keeps
  the calls it returned current, but doesn't add new ones. A single poller
  on the backend, shared by all viewers, is fine.
- Reactions and other per-tap events are throttled on the client: taps are
  coalesced, and a 429 is dropped, not retried. At a large audience one
  request a second per viewer is still too many: send a count every few
  seconds, or sample. Compare viewers times expected sends with the
  endpoint's limit and ask Stream about it before the event. A raise of
  the app's limit doesn't change the limit per user.
- The viewer UI doesn't render or query the whole audience: no member or
  participant list of every viewer, no per-viewer subscription.
- The end of the stream is handled. When the call ends, viewers leave it
  and see an ended state, and nothing tries to join again. When the host
  stops live, viewers go back to the waiting state.
- Livestream chat uses the `livestream` channel type, or a custom type with
  read events, typing indicators, and connect events off. Slow mode is set
  for the expected traffic. The generic Scale and release chat bullets
  apply.
- Moderation is ready before the event: automatic moderation or block
  lists on the channel type, and someone who can delete a message and ban
  a user while the stream runs.
- The channel is opened with one call (watch), not create, query, and watch
  in turn.
- With member-only chat, ticket holders known before the event are added
  as members before it, in batches of the documented size. Later buyers
  are added in batches too, not one request per viewer on entry. Nothing
  writes live values such as a viewer count into channel data during the
  stream: every update is sent to every watcher.
- Attendance and reach come from the call attendance endpoint after the
  call, not from counting participant joined and left webhooks.
- Webhook endpoints verify the signature on the raw body, hand the work to
  a queue or store, answer 2xx quickly, and are idempotent
  (`X-Webhook-Id`). Only network errors and 5xx are retried, so an
  endpoint that answers 4xx to Stream (an IP allowlist, an auth proxy)
  loses the event. No environment delivers the same event to two URLs by
  accident, and the production app is subscribed to every event type the
  backend's handlers switch on. Participant events arrive for every viewer
  session: subscribe only if the backend uses them, or use SQS.

Docs: `rate-limits.md` in `getstream docs platform` and `getstream docs
video/api`; `livestream-best-practices.md` and `slow-mode.md` in `getstream
docs chat/<platform>`; `webhooks.md` in `getstream docs platform`;
`analytics/call-attendance.md` in `getstream docs video/api`. The truncated
participant list is in the SDK's call-state page.

### Playback and event readiness

- Web and WebView viewers: a blocked-audio prompt, because playback with
  sound needs a user gesture there. N/A on native.
- HLS, when used: something starts it (Go Live, an explicit call, or the
  call type's mode), the player takes the playlist URL from the call's
  state once broadcasting has started, and the UI doesn't present HLS
  viewers as participants (they aren't counted as such, and they are
  several seconds behind chat and reactions). For a ticketed stream,
  check who can get the playlist and recording URLs: the join permission
  doesn't cover them. N/A when viewers only use WebRTC.
- Viewers see a connection or quality indicator and a reconnecting state.
  A viewer who has joined while the host's video is missing sees a state
  for that, not a black screen. The video is rendered with the SDK's
  renderer at its on-screen size, so the server can send a matching layer.
- Picture-in-picture and background audio for viewers, where the platform
  has them and the product wants them.
- Each Stream SDK, in the app and on the backend, is on a current release,
  and the tested set is frozen before the event. Name the installed and
  the latest released versions with the date you checked, and read the
  changelog between them for join, reconnect, and livestream fixes.
- A failed join can be investigated: the app logs or shows the call id and
  the error, and SDK logs can be collected from a release build on request.

These can't be checked in code. Print them in the report every time, under
"Event readiness", with whatever the code or the developer says about each:

- Tell Stream the event's date and start time, the expected concurrent
  peak, and where the audience is, as early as possible, so capacity near
  the audience is ready before the stream opens.
- Ask Stream what the app's Video rate limits are and have them sized to
  the arrival estimate. The default for joining is 1,000 a minute per
  platform for the whole app, and all concurrent streams share it.
- Rehearse on the production app, with the launch call type and the release
  build, including the app's own backend. A load test that only exercised
  Stream leaves the token endpoint, entitlement checks, and webhook
  handlers untested.
- On the release build, try a network loss of about 10 seconds on the host
  and on a viewer, a switch between Wi-Fi and mobile data, and a session
  that outlives the token.
- Go live a few minutes before the main content starts, so the audience
  doesn't arrive all at once.
- Host kit: the tested device, a charger, Wi-Fi with mobile data as the
  backup, the second device signed in, and someone watching as a viewer.

## Report

Livestream findings go into the review's urgency groups, under the group
names above. As a guide:

- **Fix now:** the host can be locked out or can't recover, viewers can
  create or publish, a ticketed stream can be joined without a ticket, a
  retry or rejoin loop with no bound.
- **Fix before scaling:** extra requests on the join path, unthrottled
  reactions, per-viewer polling, chat settings, webhook handling. Move one
  to Fix now when the audience stated for the next event is certain to
  take it past a limit.
- **Worth doing:** host UI safeguards, indicators, picture-in-picture,
  version updates.
- **Ask Stream:** rate limits, capacity for the event, docs gaps, anything
  the settings checks could not read.

After the scale answers, add the "Event readiness" list. Never drop it,
even when every check passes.
