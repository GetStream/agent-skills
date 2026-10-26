# Integration review

A read-only review of an existing app's Stream integration, before it goes live
or before the live integration review with Stream. The output is a checklist
the developer can act on. Change code only if asked, after the report.

The check sections follow the agenda of Stream's live review, so the report
maps onto that call: initialization, a typical session, disconnecting,
fetching channels and calls, search, rendering and customization, push, unread
counts, and scale.

This file holds the procedure and the checks that apply on every platform. Each
platform skill adds its own pitfalls on top; run both. Platform files use the
same section names, and a platform bullet replaces the generic bullet on the
same topic, so check each topic once.

| Platform | Platform checks |
|---|---|
| Android | Read stream-android skill's integration-review.md |
| React, React Native | The platform skill's audit section, plus the Video "Integration best practices" page in that SDK's docs |
| iOS | No platform file yet: stream-swift skill's RULES.md pitfalls, and the best-practices pages listed in its docs-map.md |
| Flutter, Unity, Unreal | No platform file yet: use the SDK's go-live checklist page and the platform skill's RULES.md |

## 1. Scope

Find out from the code, and ask only what the code can't answer. If you can't
ask, record the answer as unknown and continue:

- Products in use: Chat, Video, Feeds, Moderation.
- UI: Stream's prebuilt components or the app's own UI on the client SDK. With
  a custom UI, read state, unread, and notification handling become the app's
  job, so more checks apply.
- Features shipped: 1:1, groups, livestream, support inbox, calls, feeds.
- Scale: channels per user, members in the largest channel, messages per day
  in the busiest channel, concurrent call participants, expected growth.
  Several findings only matter at scale, so record the answers in the report.

## 2. Locate the integration

Before judging anything, find and read:

- where the client is built, and every place that can reach it
- every connect and disconnect call site, and the logout and account-switch
  paths
- the token provider and where tokens come from
- every channel, call, or feed query, with its literal filter, sort, and limits
- the screens that render Stream data, and how each is customized
- push: the client-side registration, any custom push service, and the
  provider name per build variant
- dependency declarations for every Stream package

Then trace one typical session through the code: app start, login, the channel
or call list, starting a new conversation (user search, channel creation),
opening a channel or joining a call, sending a message, receiving a push and
opening it, backgrounding and returning, logout. For each step list the Stream
calls the app makes and where. For a prebuilt screen, name the component and
what it requests; don't walk the SDK's internals.

A call the code makes repeatedly (on every resume, keystroke, or selection) is
a finding under its section. How many requests actually go out at runtime
needs a running app; without one, list it as unverified.

Review what ships. Name the build type and flavor that go to users (a flavor
called `demo` can be the shipping one), and tag a finding that affects only
another variant with that variant's name.

## 3. Walk the checks

Run the generic checks below, then the platform file. Where the platform file
covers the same item in more detail, its version replaces the generic one.

Back every finding with its source: the docs page a check names (look it up
with `getstream docs`), the SDK source, or the app code itself for general
practice such as debouncing. Say which. Don't flag from memory. For each check
record: PASS, FAIL, or N/A, the evidence (file:line), and the fix.

A check that needs the dashboard, the CLI, or a running app you don't have is
listed as unverified, with any in-code hint (a comment, a KDoc) as the lead.

### Initialization

- The client is built once per process, at app start. Building it lazily when
  chat opens delays push registration; building it twice drops state, and
  anything that cached the old instance keeps using it.
- The API secret is nowhere in the app, its build config, or source control.
  Anyone holding it can act as any user.
- No tokens bundled in the app, development or signed: anyone unpacking it can
  act as those users. Tokens expire and come from a token provider backed by
  the app's server.
- The provider can't hang or crash on network errors. The SDKs retry it.

Docs: `tokens-and-authentication.md` in `getstream docs chat/<platform>`, and
the SDK's go-live checklist (its path is in the platform file).

### Typical session

- The user connects once per session, from the app's session or login code,
  not from a chat screen. One connection per user, guarded against races and
  repeated calls on resume.
- A failed connect (invalid or revoked token) is handled: the user is sent back
  to login and stored credentials are cleared, not left on an empty screen.
- The app doesn't manage the socket by hand on background and foreground. The
  SDKs already do, and a manual disconnect usually stops reconnection.
- The session trace from step 2 makes no call the SDK already makes, and the
  code re-fetches nothing on every screen visit.

### Disconnecting

- Logout disconnects the user and removes the push device. Otherwise the next
  person on the device gets the previous user's notifications and offline
  data: a privacy finding, Fix now.
- The app waits for the disconnect before clearing its session or showing
  login, so a quick re-login doesn't race it. A worth-doing finding when the
  device is still removed.
- App-wide services (location, sync, calls) can start again after a logout and
  login in the same process.

### Fetching channels

- Every channel list filters on membership plus type, and sorts on
  `last_message_at` or `last_updated`. Type alone is slow and pages unstably.
  Sorting on anything else, `pinned_at` included, isn't indexed.
- No custom fields, `member_count`, or `frozen` in filters; no `$or` combined
  with `$and`; no `$ne`, `$nin`, or `$autocomplete` on hot lists. `api-budget.md`
  lists what's cheap and what's expensive.
- A predefined filter is reviewed like an inline one: read its definition from
  the dashboard, or with `getstream api` if the CLI is already set up for the
  app. Otherwise it's unverified.
- Channels are created when the user commits (first message, confirm), not on
  every selection change in a picker. Throwaway channels pile up in members'
  lists and force extra filter clauses to hide them. Source: the app code.
- `limit` stays within the documented maximum, and nothing pages past the
  maximum offset. For older data, add a time filter instead.
- Queries aren't re-issued on navigation, resume, or reconnect. The socket
  keeps watched channels current.
- Each list filters incoming events to its own filter before adding a channel.
  Events aren't filtered server-side, so with a default handler channels
  outside the filter appear, and with several lists they land in the wrong
  one.

Docs: `api-budget.md`, `query-channels.md` (filter best practices, pagination,
performance), and `rate-limits.md` in `getstream docs chat/<platform>`.

### Fetching calls

- Call lists are scoped to the user (`members`, `created_by_user_id`) and
  bounded in time (`starts_at`, `ended_at`), not an unfiltered query over the
  app's calls.
- Sorting uses a field the docs list as sortable, and paging uses `next` /
  `prev` with a bounded `limit`.
- The list isn't re-queried on every visit, and `watch` is on only where the
  list shows live state. Source: the app code.

Docs: `guides/querying-calls.md` in `getstream docs video/<platform>` (filter
fields, sort fields, paging).

### Search

- Message search scopes its channel filter to the user's channels, debounces
  input, and pages with `next`, not offset.
- User search (new-chat and member pickers) debounces input too, and avoids
  `$ne` and broad `$autocomplete`, which `api-budget.md` lists as expensive.
- No searching by filtering already loaded messages on the client: it misses
  everything not loaded.

Docs: `search.md` (paging) and `api-budget.md` (operators) in
`getstream docs chat/<platform>`. Debouncing is general practice: cite the
code.

### Rendering and customization

What matters is how the app customized, not how much: anything that will
break on the next SDK upgrade is a finding.

- Customization goes through the SDK's extension points: theming, component
  overrides or factories, and the documented customization hooks.
- No SDK source copied into the app. Look for Stream copyright headers, files
  named like SDK components, or packages mirroring the SDK's. Record which
  extension point was missing under "Ask Stream".
- An override of a composite component falls back to the SDK default for the
  cases it doesn't handle. Otherwise those messages or rows lose what the
  default drew.
- Message and channel actions are gated on the channel's own capabilities,
  not hardcoded roles that drift from dashboard permissions.
- Prebuilt screens get their state from the SDK's own view models or hooks.
  A custom UI watches the channel or call for updates instead of a one-off
  fetch plus polling, and releases listeners when the screen goes away.
- A call object lives as long as the call screen, not recreated on each
  render.

Docs: the platform file names the customization pages.

### Push

Check the chain in order. Every broken link looks the same to the user:

1. Push is enabled in the client config.
2. The device is registered after connect, and re-registered on token
   rotation.
3. A custom push service forwards Stream payloads to the SDK.
4. The provider name in the app matches the dashboard, for every build
   variant.
5. Push can still be shown when the app was killed and the Stream token has
   expired.

If the CLI is already set up for the app, check the user's device list with
`getstream api`: no device means the cause is in the app. Otherwise list it as
unverified.

### Unread counts

- Badges come from the server's counts over the socket, not summed from loaded
  channels.
- The app doesn't poll the REST unread endpoint on a timer while connected:
  the socket already delivers counts. One fetch at app load, or a badge
  without a connection, is what the endpoint is for.
- A custom message list marks the channel read when the user sees the newest
  message, not on every incoming message.

Docs: `unread.md` in `getstream docs chat/<platform>`.

### Scale and release

- High-volume channel types (livestreams) use a livestream channel type, and
  the app keeps them out of offline storage and caps messages held in memory.
- Large groups or livestreams were load-tested before launch. The go-live
  checklist points to the load-test tool.
- Release builds don't log at the most verbose level: it costs performance and
  logs message content. No debug-only tooling ships either.
- Calls that matter handle failure: connect, send, channel creation, uploads.
  Ignored errors there hide failed sends and rate limits. Don't list every
  fire-and-forget call.
- The SDK's own artifacts are on one version, on a current major. Helper
  libraries can have their own version lines.

Docs: `livestream-best-practices.md` in `getstream docs chat/<platform>`, and
the SDK's go-live checklist.

### Video and Feeds

For Video, also read the SDK's "Integration best practices" page when it
exists (React, React Native). Otherwise use the platform skill's Video
reference and the SDK's `guides/joining-and-creating-calls.md`, and check
device permissions and error handling against them. For Feeds, read
`getstream docs activity-feeds/<platform>` best practices.

## 4. Report

Lead with the checklist, grouped by urgency:

- **Fix now:** anything that blocks a release. Broken push, the previous
  user's data or notifications leaking, exposed secrets or bundled tokens,
  users stuck after a failed connect, release builds that allow cleartext
  traffic or can be signed with a debug key.
- **Fix before scaling:** redundant queries, oversized payloads, filters that
  won't hold.
- **Worth doing:** lifecycle leaks, release hygiene, upgrades, config tuning,
  replacing copied SDK code.
- **Ask Stream:** index or filter-performance questions, missing extension
  points, docs gaps, suspected SDK bugs.

Within each group, order findings by check section, in the agenda order
above. One line per FAIL: the check section, check, evidence, fix, docs page,
and the variant if it isn't every variant. PASS checks get a one-line list per
section with evidence, and N/A checks a one-line reason, so the reader sees
they were considered. Then the session trace from step 2, as one line per step with the
Stream calls it makes. End with the scale answers from step 1 and anything you
couldn't verify from the code.
