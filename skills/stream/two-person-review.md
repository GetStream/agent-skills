# Two-person call review

Extra checks for an integration review of an app whose calls have two
people in them. Two kinds of app are built on such calls:

- Scheduled calls: appointments, consultations, tutoring, coaching,
  interviews. The app's backend matches a provider and a client, and both
  open the call at an agreed time.
- Calls that ring. A user-to-user call: one user rings another from a
  chat, a match, an order, a ride, or a listing. Or an app-placed call:
  the app rings the next available expert, or rings a user when it is
  their turn.

The names are the docs' own: `call-types/builtin.md` in `getstream docs
video/api`, under "How a call starts". Its other two, the agent call (a
person and an AI agent) and the always-on link between two fixed devices,
are not what this module is for.

Run it from integration-review.md when the scope step finds either; that
file's procedure, evidence rules, and report format apply here. The first
five groups of checks apply to every two-person call. The sixth,
"Scheduled calls", applies only to the first kind: skip it for an app
that rings, with one line in the report saying so. What makes a call ring
(push, the incoming-call screen, accept and reject) is covered by the
Calls and Push checks in integration-review.md; this module adds nothing
for it, and the report says that too.

A two-person call is not a small group call. Three things differ:

- The call is private to two known people. Who can join it, who can read
  it, and what its data says about them matter more than in an open room.
- With two participants the video is sent differently: one stream that
  adapts, not three layers to choose from. Settings and code written with
  group calls in mind behave differently, and the difference reads as a
  bug.
- When one side goes away the conversation stops for both, so a hang-up, a
  dropped connection, a removal, and the end of the call each need their
  own state.

The platform file's "Two-person calls" section uses the same group names.
Its bullets add SDK detail to the checks here; they don't replace them.
Every requirement in a generic bullet still applies, and each topic is
recorded once. Where a platform has no section yet, cite that SDK's docs
and its source.

Some checks rest on how the server behaves today and the docs have no page
for it yet. They are marked "Source: server behaviour". Cite this file for
them, say that the docs don't state it, and list the missing page under
"Ask Stream". Don't claim to have inspected the server.

## Scope

Add to the review's scope answers. Take them from the code, and ask only
what the code can't answer:

- How a call starts: both sides open a scheduled call (a link, an
  appointment page), or one side rings the other. This decides whether
  the "Scheduled calls" group runs. An app can have both.
- What entitles two people to be in a call together: a booking, a match,
  an open order, a friendship. And what ends it.
- For scheduled calls: one call per appointment, or a standing room
  (one per clinician, tutor, or agent) that successive clients enter, and
  whether one side waits to be let in by the other (a waiting room).
- What kind of data the conversation and the user records carry: health,
  legal, financial, minors, or nothing regulated.
- Recording, transcription, and captions: on or off, who starts them, who
  can read the results.
- Whether anyone or anything else can be in the call: a supervisor, an
  interpreter, a parent, a bot.
- What each side joins from: a desktop browser, a phone browser, a native
  app.

## Locate the two-person flow

On top of the review's step 2, find and read:

- Where the call is created: client or server, by which user, with which
  call type, how the id is made, the members, and any per-call settings.
- What the backend writes about people: user objects (name, image, custom
  data), member custom data, call custom data.
- The call type as configured. If the CLI is already set up for the app,
  read it with `getstream api GetCallType --name <type>`; long arrays are
  cut in the default output, so select with `--jq` (for example `--jq
  '.grants.user'`, `--jq '.settings.video'`, `--jq '.settings.limits'`).
  Otherwise the settings and grants checks are unverified, with the code
  that creates call types and calls as the lead.
- Each side's path into the call, and what each sees while the other has
  not arrived, drops, reloads, leaves, or is removed.
- Every listener on call events: participant joined and left, call ended,
  member removed, kicked or blocked, custom events.
- The layout code: how many participants it expects, the sizes it renders,
  and anything that asks for a resolution or changes what is sent.
- The device code: mute, noise cancellation, device selection,
  picture-in-picture.

Add both sides' paths to the session trace, one line per step with the
Stream calls it makes.

## Checks

### Access and membership

- Who may join is decided by the call type's grants and the call's
  members, on the server. The role ordinary users hold (`user`, and
  `guest` if the app has guests) has no `join-call`; the backend creates
  the call with the two people as members; the member role has
  `join-call`. That is one layout; another that the server enforces just
  as well, with other role names, passes too. On the built-in `default`
  call type the `user` and `guest` roles have `join-call`, so with those
  defaults any signed-in user who learns a call id can walk into the
  call. FAIL, Fix now, when the data is sensitive. Without the grants,
  mark it unverified. Docs: `calls.md` (restrict call access) and
  `call-types/permissions.md`.
- `limits.max_participants: 2` is not access control. FAIL when it is the
  only thing that keeps a third person out: it caps how many are in at
  once, not who, so the first two to arrive are in. It also counts
  sessions, not people. A session that dropped without leaving stays
  counted until the server stops waiting for it to reconnect (tens of
  seconds), and the same person coming back after a page reload, an app
  restart, or on a second device is a new session: they are refused while
  the old one is counted. A reconnect the SDK makes by itself continues
  its own session and is not refused. With membership as the control,
  leave the limit unset or above 2. If the product wants a hard cap
  anyway, the app shows the refused join and offers a retry. Source:
  server behaviour; `call-types/settings.md` lists the field.
- Who may read the call. `read-call` lets a user load the call, its custom
  data, and its members with their user objects, and receive member
  events, without joining. On the built-in types `user` and `guest` have
  it. In a private two-person call only the member role needs it. Docs:
  `call-types/permissions.md`.
- Personal data in what the app writes to Stream: `user.name`,
  `user.image`, user `custom`, member `custom`, call `custom`. Everyone
  who can read the call reads them, and they travel in events and
  webhooks. List what is stored there and who can read it. FAIL for data
  the call does not need: an email address, a phone number, a date of
  birth, a record number, the reason for an appointment. With regulated
  data that is Fix now, and the fix is an opaque user id, a display name
  the policy allows, and the mapping to the real person kept in the app's
  backend. A name or a picture the product decided to show is not a
  finding; say who can read it. Source: the app code.
- The routes that create a call, hand out its id, or change its members
  take the two people from the app's own records (the booking, the match,
  the order), not from the request, and check that the signed-in user is
  one of them or staff. Where the browser or the app creates the call
  itself, the role's `create-call` grant lets a user make a call with any
  member they name: check what stops a user calling someone they have no
  such tie to, and what happens to the right to call when the tie ends
  (a block, an unmatch, a delivered order). A block in the app is also
  made in Stream: a user who has blocked another no longer gets ringing
  calls or call notifications from them. The token check under
  Initialization still applies. Source: the app code; user blocking is in
  `moderation/overview.md`.
- What each side's role may do matches the product. On the built-in
  `default` type the `user` role may end the call for both, start a
  recording or a transcription, and remove or update members. Decide who
  may end the call, who may record, and who may remove the other person,
  and grant only that. Hiding a button is not enforcement. Docs:
  `call-types/permissions.md`.
- Taking someone out during a call. Removing a member, or changing their
  role, disconnects their live session only when they can no longer join
  without it: membership is what grants `join-call` (the first check), or
  the call is in backstage and they may not join backstage. Where the
  `user` role can join anyway, a removed member stays connected. No timing
  is promised for the disconnect, so no flow depends on it being
  immediate. To take someone out for certain, kick or block them, or end
  the call. Source: server behaviour; kick and block are in
  `moderation/overview.md`.

Docs: `call-types/permissions.md`, `call-types/settings.md`, `calls.md`
(members), and `moderation/overview.md` in `getstream docs video/api`.

### Call-type settings

Read the call type the launch build uses, on the app it points at.

- `settings.video.target_resolution.bitrate` is in bits per second and is
  an upper bound for the best video a publisher sends, not a target. The
  encoder goes below it when the network or the device needs that, and
  never above. The maximum is 6,000,000. 0 means the server default,
  1,500,000; a call type created through the API without a bitrate reads
  back 0, and that is fine. Don't flag 0.
- The same bitrate applies to every codec. FAIL when the value looks taken
  from a per-codec bandwidth table for an efficient codec (the AV1 or VP9
  column): a publisher that ends up on H.264 or VP8 is held to the same
  number and looks worse. The evidence is a comment or a document that
  says where the number came from, or a value well below the H.264 figure
  for the target resolution in `quality/introduction.md`. Take the H.264
  figure for the target resolution and motion, or keep the default. The
  built-in types use 1280x720 at 1,500,000 (`default`) and 1920x1080 at
  3,000,000 (`livestream`). A low cap chosen on purpose to save bandwidth
  is a product decision: report what it costs, not a FAIL.
- A cap far above what the target resolution needs (6,000,000 at 720p)
  lets the encoder use bandwidth a talking-head call gains little from,
  and a target above 1080p between two webcams or phones is rarely held by
  the camera, the encoder, and the uplink together. Worth doing, as a
  question about why it was set.
- `limits.max_participants`: see Access and membership.
  `limits.max_duration_seconds`, if set, is longer than the longest call
  the product expects. When it passes the call ends for both.
- Recording, transcription, and captions are in the mode the product and
  its consent flow need. Trace what starts them: `auto-on` starts them for
  every call of the type from the first join, so a product that records
  only after consent can't use it, and every other start path waits for
  the consent too. Check who can list and read the results
  (`list-recordings` and `list-transcriptions` are on the `user` role of
  the built-in `default` type), the app's own routes that list or
  download them, where they are stored, and what deletes them.
- `audio.noise_cancellation.mode` is `available` or `auto-on` when the app
  uses noise cancellation. With `disabled` the SDK refuses to turn it on.
- Backstage is off, unless the product uses it on purpose. With backstage
  on, nobody without `join-backstage` gets in before Go Live.
- Compare the call type on the app that was tested with the one on the
  production app. Differences in grants, limits, the bitrate, and the
  recording modes are findings.
- Per-call overrides in the code that creates calls don't contradict the
  type.

Docs: `call-types/settings.md`, `call-types/builtin.md`,
`call-types/permissions.md`, and `quality/introduction.md` (bandwidth by
resolution and codec) in `getstream docs video/api`. Where those pages
don't state the unit, the maximum, or the meaning of 0 for `bitrate`, the
source is server behaviour.

### Two-person media behaviour

How it works, so the checks below make sense. While a call has two
participants, each publishes one video stream that adapts, not the three
simulcast layers a group call uses. The receiver's bandwidth estimate is
passed to the sender, whose encoder lowers the bitrate when the receiver's
network can't take more. The resolution goes down when the sender's device
can't keep up with encoding. Nothing in the app turns this on or off. Two
exceptions publish layers even with two participants: a publisher on
Firefox, and any call of the `livestream` type. When a third participant
joins and subscribes, the publishers switch to three layers during the
call, and back to one stream when it is two again. Source: server
behaviour, and the October 2024 entry in `roadmap-and-changelog.md`.

- Receiver-requested resolution. In a two-person call the size the
  receiver asks for (the size of the video element, or an explicit
  preferred-resolution call) does not change what the sender encodes:
  there is one stream and the receiver gets it, at the bitrate the link
  allows. Code that asks for a smaller incoming video to save the
  receiver's bandwidth or CPU does nothing while the call has two
  participants. Report it as "no effect in a two-person call", Worth
  doing, and say that it works once a third participant is there. The
  two exceptions above still publish layers, so on the `livestream` type,
  or with the other person on Firefox, the request does take effect:
  don't report it there. Going from a small tile to full screen needs no
  call at all: the full stream is already arriving. Source: server
  behaviour.
- Nothing changes the sent video through internal SDK calls. An app that
  shrinks what its own camera sends when the other side shows it small
  (often on a message from the other side) usually reaches for calls the
  SDK marks internal: they can change without notice, and some do nothing
  after the join. FAIL. The platform file names them, and says whether
  that SDK version has a public call for it. The public control is the
  call type's target resolution.
- The layout does not assume exactly two. It has a state for one (the
  other person has not arrived, or has left), and it survives a third
  entry in the participant list: the list holds sessions, so the same
  person joined from a second tab or device is another participant.
  Source: the app code.
- Video is drawn with the SDK's renderer, not by attaching a track to an
  element by hand. The platform file says why.
- A two-person product is not built on the `livestream` call type. It has
  backstage on and publishes layers even with two participants, so neither
  the join flow nor the media behaviour above applies. Worth doing, with a
  question about why it was chosen.
- Code that reads the publisher's encodings or layer stats (a quality
  indicator, a debug panel) handles one encoding and three. Source: the
  app code.

### Leave and end handling

- No branching on the `reason` string of `call.session_participant_left`.
  The values are not a documented contract: some are set by the server,
  clients can send their own text, the SDKs differ, and they change
  between versions. FAIL when the UI's states or the backend's records
  depend on matching it. Use it as a hint in logs. To show "left on
  purpose", the leaving side sends a custom event and then leaves, without
  holding the hang-up on it for long. That is a hint for the other
  person's screen, not a record: the send can fail, and a closed tab or a
  crash sends nothing. A participant who goes without one is "gone, reason
  unknown", not "connection lost". Billing and the app's own records come
  from the server (below). Docs: `webhooks/events.md` (the field is a free
  string); the SDK's custom-events page.
- The end of the call is handled on both sides: on `call.ended` each side
  shows an ended state and nothing tries to join again. Hanging up
  (leaving) and ending the call for both are different actions in the
  API. Where the product offers both, the second is behind a confirmation
  and a grant; where a hang-up by either side should end the call, as in
  a phone call, something does end it, and the other side isn't left
  alone in a live call.
- Being removed, kicked, or blocked has its own state. The person sees
  that the call was closed for them, not a network error, and nothing
  joins again by itself: a kicked user is allowed back in, so an automatic
  rejoin undoes the kick. FAIL for a rejoin loop.
- Call length for billing or records comes from the server (session and
  participant events over webhooks, or the call's session data), not from
  a timer in one client. Source: the app code; `webhooks/events.md`.

Docs: `call-lifecycle.md`, `webhooks/events.md`, and
`moderation/overview.md` in `getstream docs video/api`; the SDK's
calling-state and events pages.

### Devices and audio

- Mute and the recording indicator. With the microphone muted the SDK may
  keep listening so that it can tell users they are speaking while muted,
  and the browser or OS goes on showing that the microphone is in use. If
  the product needs capture to stop on mute, turn that detection off with
  the SDK's public call. Changing the SDK's internal mute mode is a FAIL.
  The platform file names both.
- Noise cancellation is turned on only once the call's settings are
  loaded: it depends on the call type's setting and on the user's
  permissions, and before that the SDK refuses. The app also reacts when
  the filter turns itself off because the device is overloaded, at least
  with a notice. The platform file names the API and the first version
  that has it.
- Web and WebView: a blocked-audio prompt. A person who lands in the call
  without a click on the page may hear nothing until they make one. N/A
  on native.
- Picture-in-picture, where the product offers it: the control is shown only
  where the browser or platform supports the API in use (any equivalent
  feature check counts), a refused request doesn't break the call, and the
  app follows the window being closed. What a phone browser does with the
  camera when the page is in the background or the screen locks can't be
  read from code: unverified, test it on a device.
- A device that disappears during the call (a headset unplugged) is shown,
  and the app doesn't end the call over it.

Docs: the SDK's camera-and-microphone, noise-cancellation, blocked-audio,
and picture-in-picture pages.

### Scheduled calls

Only for apps where both sides open a call at a booked time. Skip the
group for calls that ring.

- One call per appointment, with a new id each time, not a standing room
  that one client after another enters. In a standing room the next client
  can arrive while the last one is still there, everyone who was ever
  added stays a member until removed, and the recordings, transcripts, and
  state of every session hang on one call. A call per appointment keeps
  each client's session apart by construction; its members and grants are
  still checked under Access and membership. Where the product keeps a
  standing room, check that earlier clients are removed and can then
  neither join nor read it, and that two clients can't overlap. Source:
  the app code.
- Waiting to be let in: a person who waits can't see who else is waiting,
  and can't join or receive media before they are admitted. A shared room
  where every waiting client is a member with `read-call` shows each of
  them the others' member rows, and a Join button that is only hidden is
  not a waiting room: find the grant or membership change that admits a
  person, and who may make it. With a call per appointment the only other
  member is the person they came to see. Source: the app code;
  `call-types/permissions.md`.
- `limits.max_duration_seconds`, if set, is longer than the longest
  appointment plus an overrun, unless the product wants a hard stop, and
  then both sides are warned before it.
- The other side dropping is not the end. A person whose connection broke
  can stay in the participant list for a while as their SDK reconnects,
  and can come back as a new session after they have left it. The person
  who remains sees a state for it and is not thrown out of the call at
  once. How long to wait before treating the other side as gone is a
  product decision made in the app, with a timer. Source: the app code.
- A reload, a crash, or a closed tab does not end the appointment for that
  person. The page they come back to knows which appointment it was, and
  offers the way back in while the appointment is open and the person may
  still enter. An appointment that has ended, or one they were removed
  from, shows that state. The SDKs don't carry a call across a reload: it
  is a new session (see the participant limit under Access and
  membership).
- After the appointment the backend ends the call, so an old link doesn't
  open a live room, and the roles in use have no `join-ended-call`. A call
  that is only left stays joinable. Source: the app code;
  `call-lifecycle.md`.
- A person who never arrives: the one who waits gets a state and a way
  out, from the app's own timer. Source: the app code.
- Before the appointment each person can check camera, microphone, and
  speaker, and a denied permission is explained (the generic Calls check).
  A lobby is Worth doing where one failed start costs a paid session.

Docs: `call-types/permissions.md`, `call-types/settings.md`, and
`call-lifecycle.md` in `getstream docs video/api`.

### Ask Stream

These can't be checked in code. Print them in the report every time, with
whatever the code or the developer says about each:

- With health or other regulated data: confirm that the agreement covering
  it (a BAA, a DPA) names Video, not only Chat.
- Ask how long Stream keeps participants' IP addresses and per-session
  call statistics. There is no app setting for it today.
- Tell Stream the launch date, the expected number of calls a day, and
  where the users are.
- Every check above whose source was "server behaviour": name the docs
  page that should say it.

## Report

Two-person findings go into the review's urgency groups, under the group
names above. As a guide:

- **Fix now:** anyone signed in can join or read a private call, personal
  or regulated data in user, member, or call data, a participant limit
  used as the lock, internal SDK calls on the media path, an automatic
  rejoin after a kick.
- **Fix before scaling:** states or records that depend on leave-reason
  strings, a bitrate cap taken from the wrong codec column, and for
  scheduled calls a standing room shared by successive clients and no
  way back in after a reload.
- **Worth doing:** requests for a smaller incoming video that do nothing
  with two participants, an oversized bitrate or resolution, a missing
  lobby, picture-in-picture, the mute indicator.
- **Ask Stream:** the list above, docs gaps, anything the settings checks
  could not read.

After the scale answers, add the "Ask Stream" list. Never drop it, even
when every check passes. When the app rings, add one line saying that the
"Scheduled calls" group was skipped and that ringing was checked with
the Calls and Push sections of integration-review.md only.
