# Sendbird → Stream Chat Flutter migration

A repeatable procedure for migrating a **Flutter app** from the **Sendbird Chat SDK**
(`sendbird_chat_sdk` / `sendbird_uikit`) to **Stream Chat** (`stream_chat_flutter` /
`stream_chat_flutter_core`). It works on *any* Sendbird integration regardless of how it was wired
— behind a service/repository, in a state object, directly in widgets, or as spaghetti. Do **not**
assume a specific symbol exists; **detect the shape** of the integration and re-implement it in
place.

Golden rule: **change as little application code as possible.** Preserve the app's architecture,
navigation, and state management (cross-ref [`RULES.md`](RULES.md) → "Project ownership"). Swap
what's *inside* the SDK touchpoints, not the touchpoints themselves.

Exit criterion — read before starting: **the migration is done when every Sendbird-backed screen,
region, and interaction (§0's touchpoints; not the app's unrelated screens) has been compared against
the source baseline and driven on the device (§0.5)** — matched, or reported with its specific
blocker. A green build that renders every screen is *not* done.

---

## 0. Detect the integration shape (do this first)

```bash
grep -rn "sendbird_chat_sdk\|sendbird_uikit\|sendbird_chat_widget" pubspec.yaml
grep -rn "SendbirdChat\|SendbirdUIKit\|SBU\|GroupChannel\|OpenChannel" lib/
```

Classify each touchpoint and migrate it in place:

| Pattern found | How to migrate |
|---|---|
| **Service / repository** hiding the SDK | Keep its public API; re-implement the body against Stream. Callers don't change. |
| **State object** (`ChangeNotifier` / Provider / Riverpod / Bloc calling the SDK) | Keep the public surface (state + methods); replace the SDK calls inside. |
| **Direct-in-widget** (SDK calls/widgets straight in a `Widget`) | If the rendering widgets are the app's *own*: keep the widget tree, swap only the SDK data calls/types inside (appearance unchanged). If a **Sendbird UI widget** is embedded: replace it with a Stream widget — see the UI-strategy fork below. |
| **UIKit screens** (`SBUGroupChannel*Screen`) | Replace with composed Stream widgets (§3). Sendbird UIKit is **group-channel-only** — there are no open-channel UIKit screens. |
| **Singleton** (`X.instance`) | Keep the singleton + signatures; replace the SDK calls. |
| **Spaghetti** (calls scattered, no boundary) | Migrate file-by-file; don't refactor unrelated code. Note it. |

Also note **shared bootstrap** (SDK init, credentials/config, seeding) — that layer always changes.

### What renders each screen decides the UI strategy (the first fork, before any code changes)

The test is **per rendering widget: is it the developer's *own* Flutter widget, or a Sendbird UI
widget?** — not where the SDK happens to be called from.

- **Developer's own widgets** (plain Flutter/Material — `ListView`, `ListTile`, `TextField`, custom
  widgets — using Sendbird only for *data*: `GroupChannel`, `BaseMessage`, `MessageCollection`):
  **preserve them; replace only the low-level client behind them** (Sendbird core SDK →
  `stream_chat_flutter_core` controllers / `StreamChatClient`, wired behind the same widgets). **The
  app must look identical before and after** — appearance-wise there should be no difference. Do
  **not** re-skin with `stream_chat_flutter` pre-built widgets; re-implementing a working custom UI is
  wasteful and changes the product against the developer's intent.
- **Sendbird UI widgets** (anything a Sendbird package renders — `sendbird_uikit`'s `SBU…`
  screens/components, or any UI widget from `sendbird_chat_widget`): these **disappear when the SDK is
  removed**, so you must **replace each with a Stream widget** (§3) and match the Sendbird look
  **region-by-region** (§0.5). This holds even if they were dropped straight into an otherwise-custom
  widget tree.
- Most apps are cleanly one or the other — quick signal: `sendbird_uikit` in deps → UIKit / rebuild
  path; `sendbird_chat_sdk`-only → custom / preserve path — but a **mixed** app is possible, so decide
  **per widget**. (`sendbird_chat_widget` can supply *both* helpers, e.g. notification caching, and UI
  widgets: swap/drop the helper calls, but **replace** any of its UI widgets.)
- **Explicit override:** re-implement a custom UI on Stream's pre-built components **only if the user
  asks**.

([`SKILL.md`](SKILL.md) → "pick the UI strategy first" applies only when you are *building* UI, i.e.
the rebuild path.)

---

## 0.5 Design & functional fidelity (read this every time — it's the part that's always wrong)

Swapping the SDK so the app *builds and connects* is the easy 80%. The migration is judged on the
**last 20%: does each screen look and behave like the Sendbird original?** Those gaps almost never show
in the channel **list** — they live **inside the chat** (bubbles, alignment, composer buttons, custom
cards). A green build and a correct channel list are **not** "done". Four habits prevent this:

**0. The source app IS the benchmark — build it first if it doesn't exist.** Never design a migrated
screen from scratch or against Stream's defaults. Run the Sendbird app and screenshot every **in-scope
(Sendbird-backed)** screen/variant — §0's touchpoints: the list **and** the chat, with an incoming
**and** an outgoing message visible; those shots are the spec. (A screen with no Sendbird involvement
gets no fidelity pass — the migration doesn't touch it; the one app-wide check is that a shared edit
such as `MaterialApp.theme` didn't bleed into non-chat screens.) If you're adding a *new* use-case that
has no Sendbird original yet, **build the Sendbird version first** (in the source SDK) and screenshot
it — going straight to Stream invents a design with nothing to check against, and it will be wrong; a
git worktree at the Sendbird baseline lets you build the reference without disturbing the Stream work.
To screenshot the source you must get past its login: the app gates its SDK behind
`SendbirdChat.connect(userId, accessToken: token)`, usually fired from a login screen — press the login
with the platform automation tool (Android `adb shell input tap`, iOS `idb ui tap`), drive it with an
integration-test harness, or connect the source in code at launch. Sendbird **auto-creates a user on
`connect(userId)`** unless the app enforces access tokens, so a second connect-in-code session can send
the cross-user data the baseline needs (ask for a test user/token only when tokens are enforced). The
reference is only valid once you've reached the real screens, not the login.

**1. Derive every value from the source — pixel-sample, don't guess, never accept Stream's default.**
For each region pull the concrete Sendbird value: colors from the theme classes (`SBUColors` /
`SBUThemeProvider`) — **read the actual values there** (source: `github.com/sendbird/sendbird-uikit-flutter`
→ `lib/src/public/resource/`); a per-app override or a newer default means any constant baked in here
would be wrong. Sendbird encodes **emphasis tiers** in the alpha channel (high/mid/low ≈ 88/50/38%
opacity) — match the tier per element, and pull fonts/sizes/paddings per element too. **Name the value
from the theme, but let the rendered pixel be the source of truth** — the theme constant can lie, so
confirm each color against the running app and sample it (method in
[`design-matching.md`](design-matching.md) Step 1). When you hand-build a view, pull **every** element's
value including **text**, and keep the source's emphasis hierarchy (a quieter author over a brighter
message) — full-strength everything inverts it. If a rendered color *contradicts the app's own accent*,
that's likely an SDK quirk: prefer brand consistency, and when it's ambiguous **ask rather than guess**.

Then **classify the *kind* of difference** — it tells you which knob to reach for, and using the wrong
one is why a screen "looks migrated" but is still off:
- **Recolored / restyled** (same layout, different color/font/size/padding/radius) → **theming**
  (`StreamTheme` for the message row/leaf widgets, `StreamChatThemeData` for the chat composite widgets, §6).
- **Restructured** (a widget moved/added/removed/reshaped — flat rows, author-on-top, no bubble — *or* a
  message **realigned** off its default side) → **widget replacement** (`streamChatComponentBuilders` /
  `StreamComponentBuilders` / per-widget builders). Message side is set inside the row widget by sender,
  so *realigning* — e.g. an open-channel all-left layout — is a row override (`messageBuilder` / the
  `messageItem` slot). **Reaching for a theme token when the change is structural is the single most
  common "still looks like Stream, not Sendbird" miss.**
- **Prefer the narrowest slot.** Stream v10 exposes fine-grained sub-slots (`messageHeader`,
  `messageFooter`, `messageContent`, `messageComposerLeading`, `messageComposerInputLeading`, `avatar`,
  the per-attachment builders, …) that restructure **one region while the default composite keeps
  running** — reactions, threads, status, grouping, quoted messages, and attachments all survive.
  **"Custom row = lose the sub-features" is false** — and it is the exact rationalization behind the
  most-skipped restructure: **re-ordering the message row's metadata** (author name, timestamp, avatar,
  receipts) to the source's positions. Replicate the **original's** layout and behavior, never Stream's
  default (unless the user explicitly asks for Stream defaults). Overriding a **composite** slot drops
  the sub-features the default rendered — read its `build()` and reproduce them. Full procedure:
  [`design-matching.md`](design-matching.md) (components — read its procedure half in full, one Read;
  Grep its Reference half per region) or [`custom-ui.md`](custom-ui.md) (bespoke/livestream).

**2. Inspect EVERY screen variant, and inside it walk this checklist** — each is a Sendbird→Stream
*default* gap a green build and a list-only screenshot hide:

| Check (inside the chat) | The gap a green build hides |
|---|---|
| **Outgoing bubble** | Left as Stream's pale brand shade (`colorScheme.brand.shade100`); a solid source bubble needs its fill **and** text color set (`StreamTheme.messageItemTheme`), or the text stays dark/illegible. |
| **Incoming bubble** | Not matched to the source's incoming fill + text. |
| **Row layout** | A restructured row (author-on-top, flat rows, no bubble) treated as a recolor — it's a **widget replacement** (the Restructured axis above), not a theme token. |
| **Metadata placement** | Author name / timestamp / receipts / avatar sitting at **Stream's default positions** instead of the source's — re-order via the core `messageContent` slot (+ `messageHeader` / `messageFooter` extensions); a placement miss reads "matched" at a glance, so compare native-scale crops, never thumbnails. |
| **Header trailing** | `StreamChannelHeader` defaults its trailing edge to the channel avatar; the source header's actual actions not reproduced. |
| **Composer inventory** | Stream's default set (leading attachment button, picker/command affordances, mic) shipped as-is instead of matched 1:1 — inventory the source composer left→right and match every control, the placeholder, and the field container (§6 *Composer parity*). No source mic → `enableVoiceRecording: false`; an **added** affordance is a fail exactly like a dropped one. |
| **Composer states** | The rest⇄typing swap, and the **edit** and **quote/reply** states, never compared against the source. |
| **Avatars** | Stream's circular avatar left as-is; source shape/size not matched, or an avatar shown where the source hides it (1:1 / bot chat). |
| **Custom cards** | Rendered as plain text or nested in a default bubble instead of via a custom `Attachment` builder (§5). |
| **Empty / loading / error strings** | A kept pre-built widget shows Stream's default English instead of the source's strings (§6 localization row). |
| **Dark palette** | Migrated light-only when the source ships both (`SBUThemeProvider`) — build both variants and switch on `Theme.of(context).brightness` (§6); how the switch triggers follows the source, but both palettes must exist. |

**Flutter realities to expect:** avatars are **circular-only** (Slack-style rounded squares need a
custom avatar widget); there's **no consolidated Styles axis** (insets/radii spread across theme
objects); **no global reaction-emoji config**. A Sendbird app using any of these needs widget-level work.

**3. Verify on the real screens — rendering AND behavior; a green build is not "done".**
**Seed the chat first so every region is populated,** covering both sides: send an **outgoing** message
as the connected user (from the client, or server-side with `SendMessage … user_id=<connected user>`),
and seed the cross-user **incoming** messages and any custom-card messages server-side (`getstream`
CLI, §7). The outgoing message is the one to be sure of — it's where the bubble fill/text match shows.
Then open the list **and** each chat on the app's **real navigation path** and compare region-by-region
against the Sendbird baseline at native scale (crop both sides and measure — don't eyeball; iterate on
hot reload). Rendering is not behavior — a screen that paints can still be behaviorally dead, so
**drive every interaction the source has** and confirm its observed effect; when present, these are the
ones that get silently dropped: **send text · send an attachment via the picker · Reply → quote preview
above the input (`onReplyTap → controller.quotedMessage`) → send → quoted message renders · Edit →
composer loads the text → save → edited message shows · long-press → actions menu · react from the
picker · open a thread and reply · channel-row long-press · mark-read.** A rendered-but-inert affordance
is a fail. Run on a device you confirmed is booted (`flutter devices` → `flutter run -d <deviceId>` —
never a device/OS you haven't confirmed); to reach gated screens, and if the device or run session
wedges mid-pass, use the driving tools and the recovery ladder in
[`design-matching.md`](design-matching.md) Step 5 — an environment failure never upgrades a region to
verified: regions you could not check are reported as **unverified**, never implied matched. Delete any
throwaway verification scaffold before delivery and re-verify on the real navigation path
([`RULES.md`](RULES.md) → "Project ownership"). Confirm Sendbird is fully removed
(`grep -ri sendbird lib/` is empty).

**When this pass applies.** Design fidelity is the default when migrating an existing app. If the user
instead accepts Stream's defaults, the *look-matching* half of this pass — and
[`design-matching.md`](design-matching.md) — is out of scope; habit 3's **interaction pass is never
waived** — functional parity still gates "done".

**"Fidelity" means different things per the §0 fork:**
- **Preserve path (own widgets kept):** you didn't touch the widgets, so *looks* is satisfied for free —
  fidelity here means **zero visual change** (any before/after difference is a regression to fix), and
  verification focuses on **behavior/functional parity** (the client swap didn't drop a feature).
- **Rebuild path (Sendbird UI widgets replaced):** the region-by-region matching above applies —
  reproduce the Sendbird look on the new Stream widgets.

**Functional parity — confirm each feature the source enables has its Stream equivalent wired:**
threads/replies, reactions, typing, read/delivery receipts, mentions, message search, edit/delete,
pinned messages, moderation/frozen channels, polls, voice messages, and **push** — separate concerns the
source often conflates:
- **Device registration** — `client.addDevice(token, PushProvider.firebase | PushProvider.apn)` at login,
  `client.removeDevice(token)` at logout. A push-enabled source goes silently pushless if skipped. These
  are permanent device ops — not a user's on/off toggle. Setup in
  [`references/CHAT-ADVANCED-FLUTTER.md`](references/CHAT-ADVANCED-FLUTTER.md).
- **Per-channel notifications toggle** (channel-info) → `channel.mute()` / `channel.unmute()`. A muted
  channel stops push **and** stops counting toward unread; it stays in the list (mute is a flag on the
  user's `channelMutes`, not a removal). Read state via `channel.isMuted` / `isMutedStream`.
- **Global notifications toggle / do-not-disturb** (settings) → `client.setPushPreferences([...])`:
  `PushPreferenceInput(chatLevel: ChatLevel.all | ChatLevel.none)` for global on/off, `disabledUntil`
  (clear with `removeDisable: true`) for DND/snooze. Push preferences filter *push only* (unread is
  untouched), so a push-only per-channel override is `PushPreferenceInput.channel(channelCid: cid,
  chatLevel: ChatLevel.none | ChatLevel.defaultValue)` — use this instead of `channel.mute()` when the
  source's toggle silences notifications but keeps the unread badge.

Where there's no clean 1:1 Stream equivalent, flag it and plan the custom work rather than assuming parity.

**No region ships at the Stream default as a "disclosed difference".** A region is matched, or it is
reported unmatched with the **specific blocker** — a named missing SDK API, verified against the pinned
source ([`sdk.md`](sdk.md) → a missing-API claim requires cited evidence of absence) — never skipped
because it is "risky" or "more effort" ([`design-matching.md`](design-matching.md) Step 5's
no-known-gaps rule). On the preserve path the widgets are yours, so UI is never the blocker — a valid
gap there names a missing **data/API capability** (e.g. the §3 moderation gaps).

---

## 1. Packages (pub.dev)

Remove Sendbird, add Stream. `stream_chat_flutter` re-exports the full stack.

| Remove (Sendbird) | Add (Stream) |
|---|---|
| `sendbird_chat_sdk` (core) | `stream_chat` (core, pure Dart) — transitively via the UI package |
| `sendbird_uikit` (widgets) | `stream_chat_flutter` (pre-built UI; re-exports `_flutter_core` + `stream_chat`) |
| — (custom-UI path) | `stream_chat_flutter_core` (headless controllers) instead of the UI package |
| offline (bundled in `sendbird_chat_sdk`) | `stream_chat_persistence` (**separate** package) |

Pin the Stream packages in lockstep to the same major (these skills target **v10** — see
[`SKILL.md`](SKILL.md) → "Version prerequisite"). State the lockstep rule; don't hard-code a patch.

- **Migrate to v10** — the current major these skills target; don't migrate onto an older Stream
  Flutter version. Ground your API usage against the pinned v10 source (or pub.dev).
- **Expect toolchain bumps in an existing app.** Adopting v10 often pulls newer transitive deps that
  require bumping the Android toolchain (Kotlin / Gradle / heap) before the build passes — budget for
  it; it's not migration logic but it blocks the build.
- **Offline persistence is opt-in — mirror the source.** Sendbird's local caching (`SendbirdChatOptions
  .useCollectionCaching` / the collection DB) maps to attaching a `StreamChatPersistenceClient`. If the
  source enables caching, attach it (before `connectUser`, §8); if it opts out, **don't add the
  persistence client at all**. Don't hardcode persistence on — match the source's on/off choice.

---

## 2. Initialization & authentication

The biggest conceptual shift: **App ID + optional session token → API key + always a per-user JWT.**

| Sendbird | Stream |
|---|---|
| `SendbirdChat.init(appId: 'APP_ID')` / `SendbirdUIKit.init(appId:)` | `StreamChatClient('api-key')` |
| `SendbirdChat.connect(userId, accessToken: token)` (token optional in test mode) | `client.connectUser(User(id: userId), token)` — **token always required** (`connectUserWithProvider` for prod refresh) |
| `SendbirdUIKit.provider(...)` wraps the tree | `StreamChat(client: client, child: …)` wraps `MaterialApp` (or `StreamChatCore` for headless) |
| App ID is the only credential | API **key** (client-safe) + per-user **token**; the **secret** stays server-side |

Init the client **once before `runApp`** and mount `StreamChat(client:, child:)` so the provider
**wraps the tree from the first frame**. `connectUser` is a separate step that can come later (e.g. on a
login screen) — create the client and mount the provider unconditionally rather than gating either on
being connected. Stream's pre-built widgets read the client from context via `StreamChat.of(context)`,
which **throws** when no `StreamChat` ancestor is mounted, so a channel-list or chat screen shown before
the provider is in the tree red-screens. `disconnectUser()` before switching users (cross-ref
[`RULES.md`](RULES.md) → "Client lifetime"). No wrapper layer (→ "No wrapper or bridge abstractions").
Use a CLI-minted token via `getstream token <id>` for local (see [`SKILL.md`](SKILL.md) → Step 0.5)
— it's a real secret-signed JWT, not a dev token.

> **Heads-up:** client-side **dev tokens** (`client.devToken(userId)`) work only when dev tokens are
> **enabled on the app in the dashboard** (Auth settings) — otherwise `connectUser` returns a 401.
> The CLI-minted token above needs no dashboard toggle.

---

## 3. UI components

| Sendbird (`sendbird_uikit`) | Stream (`stream_chat_flutter`) |
|---|---|
| `SBUGroupChannelListScreen` | `StreamChannelListView(controller:, onChannelTap:)` |
| `SBUGroupChannelScreen` | compose it yourself: `StreamChannel` → `Scaffold(appBar: StreamChannelHeader(), body: Column([StreamMessageListView(), StreamMessageComposer()]))` |
| `SBUGroupChannelCreateScreen` / `…SettingsScreen` / `…MembersScreen` | build with Stream controllers + widgets as needed |
| composer — the input region inside `SBUGroupChannelScreen` (an internal component, not a public widget, so nothing to swap 1:1) | `StreamMessageComposer` — that the Sendbird composer is not a public component is **no waiver**: replicate its original **appearance and functionality** anyway. Do it with the Stream pieces first — `StreamMessageComposer` + its props / theme / sub-slot overrides ([`design-matching.md`](design-matching.md) → Composer) — and hand-build a composer on `StreamMessageComposerController` **only as a fallback** when those can't reach the original. Matched to the baseline via §0.5's composer row set, never shipped at the Stream default. |

**Biggest structural difference: Stream Flutter has no built-in navigation.** Sendbird UIKit pushes
its own screens; Stream widgets don't. Add a routing layer wired to the app's existing router
(Navigator / GoRouter / auto_route) — e.g. `onChannelTap` pushes a route that wraps the chat screen
in `StreamChannel(channel: channel, child: …)`. The `StreamChat` → `StreamChannel` →
`StreamMessageListView` provider nesting is mandatory here (a hard runtime constraint — §8).

**Composing the chat screen means you own its action wiring — the defaults do NOT auto-wire.** A bare
`StreamMessageListView` + `StreamMessageComposer` in the same `Column` are **not connected**: Reply /
Edit / quote / thread silently do nothing until you share one `StreamMessageComposerController`
(passed as `messageComposerController:`) and wire the list view's `onReplyTap:`
(→ `controller.quotedMessage = message`), `onEditMessageTap:` (→ `controller.editMessage(message)`),
and `threadBuilder:` — the canonical recipe is
[`references/CHAT-FLUTTER-blueprints.md`](references/CHAT-FLUTTER-blueprints.md) → Channel Page
Blueprint; follow it, don't re-derive it. Assuming a Stream widget "just handles it" is the #1 silent
behavioral drop in a composed screen — these are exactly the interactions §0.5 habit 3 drives on the
device: if you didn't drive it, it doesn't work. UIKit also shipped channel-row actions inside its
screens — wire `onChannelLongPress` for a channel action sheet where the source had one. Keep the
default row/tile and override only what differs so each keeps its built-in behavior.

**Stream ships composable widgets, not assembled screens.** Several Sendbird UIKit screens have **no
pre-built Stream equivalent** — create-channel, settings, channel-info, and invite are rebuilt from Stream
controllers + widgets (`StreamChannelListController` / `StreamUserListController` / `StreamMemberListView`),
and **moderation** (operators / muted / banned) has no Stream UI at all — and the client-side API covers
only part of it, so build or scope out the screen per this capability inventory (verified against v10 — confirm against
the pinned source), not by assuming a call exists:
- **Ban / unban / shadow-ban HAVE client-side calls:** `channel.banMember(userId, opts)` /
  `channel.unbanMember(userId)` / `channel.shadowBan(userId, opts)`; list via
  `channel.queryBannedUsers()` → `.bans` (a `List<BannedUser>`).
- **Operator promotion has NO client-side call** — nothing maps to Sendbird's `addOperators`;
  `Member.channelRole` / `Member.isModerator` are read-only, server-assigned. Surface it as a gap
  (server-side role assignment), don't fake it with another call.
- **Channel-scoped member mute (Sendbird's operator mute — the member is silenced for everyone) has NO
  Stream equivalent.** Don't substitute the near-matches: `client.muteUser(id)` mutes that user *for the
  current viewer only*, and `channel.mute()` mutes the *channel's notifications for the current user* —
  both are viewer-side preferences, not moderation. A ban is the nearest enforcement primitive but is a
  heavier action (removes access); where the source's mute semantics don't line up 1:1, **state the
  difference explicitly** rather than silently substituting a near-match. **Rebuilding a screen does not license dropping
its contents:** inventory every control and interaction the source screen has and reproduce each,
matching the reference's look as well as its controls — each part of §0.5's verification pass — a
rebuild silently loses whatever you don't re-add (e.g. a settings toggle, a multi-select member picker, a
channel-row long-press action sheet — illustrative, not a closed list). Anything you genuinely cannot
reproduce must be **surfaced explicitly**, never silently omitted (§0.5).

---

## 4. Channels

| Sendbird | Stream |
|---|---|
| **GroupChannel** (members) | `messaging` channel type |
| **OpenChannel** (public) | `livestream` channel type |
| `channelUrl` (opaque string) | `type + id` → `client.channel('messaging', id: '…')` then `.watch()` |
| `GroupChannel.createChannel(GroupChannelCreateParams(userIds:, name:, isDistinct:, customType:, data:))` | `client.channel('messaging', extraData: {'members': [...], 'name': ...})` then `.watch()` |
| `GroupChannelListQuery` | `StreamChannelListController(client:, filter:, channelStateSort: [SortOption.desc('last_message_at')])` with `Filter` (`Filter.in_('members', [userId])`, `Filter.equal('type', 'messaging')`). Sort goes in `channelStateSort:` (a `List<SortOption<ChannelState>>`); build entries with `SortOption.desc('field')` / `SortOption.asc('field')`. |

Trap: a `Channel` from `client.channel(...)` is uninitialized until `.watch()` is awaited.

**Detecting a 1:1 DM.** Stream ships predicates on `Channel`: `isOneToOne` (`isDistinct && memberCount == 2`),
`isDistinct` (id starts with `!members` — Stream's auto-generated distinct-channel id), and `isGroup`. Prefer
`channel.isOneToOne` for DMs created the Stream-native way (no explicit id → distinct). **Migration gotcha:**
if you preserved the Sendbird `channelUrl` as an explicit channel `id`, the channel is **not** distinct, so
`isOneToOne`/`isDistinct` return `false` — fall back to `(channel.memberCount ?? 0) <= 2` (`memberCount`
is `int?`, so the bare comparison doesn't compile). (Don't key off an empty
`name`; Stream DM channels usually have one.)

**Open channels → `livestream`.** Sendbird's Flutter UIKit is group-channel-only, so this applies when
the source used the core SDK's `OpenChannel` directly — the UI is the developer's own, so it's a
preserve-path swap (`livestream` is a plain channel type, no dedicated class):
- **List** via `Filter.equal('type', 'livestream')` — public, so query **without** a `members` filter
  (a membership-scoped query returns nothing for a channel the user hasn't joined).
- **Enter / leave** → `channel.watch()` to start receiving, `channel.stopWatching()` on leave; watching
  *is* the participation (there's no separate join step).
- **Participant count** → `channel.state.watcherCount` (nullable `int?`; live via `channel.state.watcherCountStream`).

**Sendbird Notifications / `FeedChannel`** (`getAppInfo()?.notificationInfo`) is a separate product
concept; the nearest Stream options are its separate Feeds product or a custom channel type. Surface
it and stub it with a note so the gap is visible.

### Membership & member selection (create / invite / member screens)

Channel-membership ops, plus the user query that a hand-built member picker needs (a pre-built picker
wouldn't surface this — a custom create/invite screen does):

| Sendbird | Stream |
|---|---|
| add / remove members | `channel.addMembers([...])` / `channel.removeMembers([...])` |
| update channel name / data | `channel.updateName(...)` / `channel.update(...)` |
| `ApplicationUserListQuery` (`.next()` / `hasNext`) — populating a member picker | `client.queryUsers(filter:, sort:, pagination: PaginationParams(offset:, limit:))` — or `StreamUserListController` (below) |
| exclude members / search | `Filter.notIn('id', [...])`; `Filter.autoComplete('name', text)` — search on `name`, the field Stream autocompletes |

Prefer the **paged controllers** for list UIs — the same `PagedValue` pattern as the channel list:
`StreamChannelListController` (channels) and `StreamUserListController` (users) both follow it with
`doInitialLoad()` / `loadMore(nextPageKey)`; `nextPageKey` lives on the **success value** — guard on
`controller.value.isSuccess` first, then read `asSuccess.nextPageKey` (or the `hasNextPage` getter),
non-null / true ⇒ more pages. (`asSuccess` **throws** off a non-success value rather than returning
null — so `asSuccess?.` is both an unnecessary null-aware and unsafe; check `isSuccess` instead.) For a
manual "load more" button, show it when more pages remain. **Gotcha — the two controllers differ on runtime filter changes.** `StreamUserListController` exposes
`filter` / `sort` **setters** (assign, then call `doInitialLoad()`). `StreamChannelListController.filter`
is **final** (no setter) — to change a channel-list filter at runtime, construct a **new** controller;
`refresh()` only reloads with the filter it already has.

---

## 5. Messages & custom attachments

| Sendbird | Stream |
|---|---|
| `channel.sendUserMessage(UserMessageCreateParams(message: 'text'))` | `channel.sendMessage(Message(text: 'text'))` |
| `channel.sendFileMessage(FileMessageCreateParams(...))` | `channel.sendMessage(Message(attachments: [Attachment(type: …, file: AttachmentFile(...))]))` — auto-uploads. Pick `type` by mime (`image`/`video`/`audio`/`file`) from `AttachmentFile.mediaType` so each renders with its proper UI. Low-level `client.sendImage/sendFile(...)` exist for an explicit upload step. |
| `params.customType` (String) + `params.data` (**JSON string**) | `Message(extraData: {…})` (structured `Map`) **or** a typed custom `Attachment` |
| read `message.customType` / `message.data` | read `message.extraData[...]` / `message.attachments` |
| `channel.addReaction(message, key)` / `channel.deleteReaction(message, key)` | `channel.sendReaction(message, Reaction(type: key))` / `channel.deleteReaction(message, Reaction(type: key))` |
| read `message.reactions` (each `Reaction` carries `.userIds`) | counts per type: `message.reactionGroups` (`Map<String, ReactionGroup>`); the current user's own: `message.ownReactions`; the most recent reactors (with `user`): `message.latestReactions`. There is no full per-type `userIds` list on the message — a "who reacted" sheet needs `latestReactions` or a server-side query. |
| `AdminMessage` (announcements / system notices) | detect via `message.type == MessageType.system`; render via `StreamMessageListView`'s `builders.systemMessage`. Like Sendbird admin messages, these originate server-side — seed them via the CLI (§7), not the client. |

**Custom cards / structured payloads** — one canonical path: define a custom `Attachment(type:
'my_type', extraData: {...})`, send it in `Message.attachments`, and render it by subclassing
`StreamAttachmentWidgetBuilder` (override `canHandle` + `build`). Build the builder list with
`StreamAttachmentWidgetBuilder.defaultBuilders(message: msg, customAttachmentBuilders: [yours])` and
attach it per message through `StreamMessageListView.messageBuilder` →
`StreamMessageItem.fromProps(props: defaultProps.copyWith(attachmentBuilders: [yours]))` — copy the
builder's `defaultProps` so the row keeps its default rendering. (Unknown attachment root keys are promoted into
`extraData`; read them back as `attachment.extraData['key']`.)

### The message-list source (per-channel messages)

Sendbird's **`MessageCollection`** (channel-scoped, event-driven: `initialize()` +
`onMessagesAdded/Updated/Deleted`) has **no symmetric Stream controller** — unlike channels and users,
messages have **no `PagedValue` list controller**. Map it to a **watched `Channel`'s state streams**
(drive the existing widget) or wrap the list in `MessageListCore`:

| Sendbird `MessageCollection` | Stream (on a watched `Channel`) |
|---|---|
| `messageList` + `onMessagesAdded/Updated/Deleted` | subscribe to `channel.state.messagesStream` — or `MessageListCore(messageListBuilder:)` |
| receipt/unread updates | `channel.state.readStream` |
| "am I at the newest?" | `channel.state.isUpToDateStream` / `isUpToDate` |
| `markAsRead()` | `channel.markRead()` |

Stream subscriptions **must be cancelled in `dispose`** (Sendbird's collection handler didn't require it).

### Threads (parent message + replies)

Sendbird threads (a reply carries `parentMessageId`; the parent's `threadInfo` holds the count) map onto
Stream's `parentId` model:

| Sendbird | Stream |
|---|---|
| `params.parentMessageId = id` on the reply | `channel.sendMessage(Message(text: …, parentId: parentId))` — add `showInChannel: true` to also post it to the main channel |
| `parent.getThreadedMessagesByTimestamp(...)` → `ThreadedMessages.threadMessages` | `channel.getReplies(parentId)` → `QueryRepliesResponse.messages` (paginate with `PaginationParams`); replies also stream into `channel.state.threads[parentId]` |
| `MessageListParams..replyType = ReplyType.none` (hide replies from the main list) | Stream returns replies in the channel state, so exclude them from the channel view yourself: `where((m) => m.parentId == null)` |
| `parent.threadInfo.replyCount` | `message.replyCount` (on the parent) |
| `parent.threadInfo.lastRepliedAt` | **no field on the parent** — read the last reply's `createdAt` from `channel.state.threads[parentId]`, populated once that thread has been fetched (`getReplies`) |

The reply count sits on the parent, but the **last-reply time does not** — a "N replies · last reply <time>"
affordance renders the count immediately and fills in the time once `channel.state.threads[parentId]` is populated.

### Mentions

Sendbird's `params.mentionedUserIds` + `message.mentionedUsers` map to Stream's `User`-typed mentions:

| Sendbird | Stream |
|---|---|
| `params.mentionType = MentionType.users` + `params.mentionedUserIds = [...]` | `channel.sendMessage(Message(text: …, mentionedUsers: [User(id: …), …]))` — pass resolved `User`s, not bare ids |
| `message.mentionedUsers` (render / detect) | `message.mentionedUsers` (`List<User>`) — highlight the `@name` tokens; a mention of the current user can tint the row |
| autocomplete source | `channel.state.members` (each `Member.user`) — filter by name for the `@` picker |

The pre-built `StreamMessageComposer` handles mention autocomplete + highlighting on its own; a hand-built
composer reads `channel.state.members` and sets `Message.mentionedUsers` itself.

### Message pagination & jump-to-message

Page a watched channel in either direction, and gate whatever triggers the load — a scroll-to-edge
callback, a manual control, whatever the source used — on whether that end still has messages:

| Sendbird | Stream |
|---|---|
| `loadPrevious()` / `loadNext()`, `MessageListParams(previous/nextResultSize)` | `StreamChannel.of(context).queryMessages(direction: QueryDirection.top)` (older) / `QueryDirection.bottom` (newer). Default page 30; `MessageListCore` paginates at 20. |
| reverse + `startingPoint` (open mid-history) | `StreamChannel.of(context).loadChannelAtMessage(id)` — jump to a message (search result / push deep-link) |
| `hasNext` (newer exist) | **`hasNewer = !channel.state.isUpToDate`.** After `watch()` you're at the tail (`isUpToDate == true`); it flips false only after a jump into the past (`loadChannelAtMessage`), and back to true once you page forward to the tail. |
| `hasPrevious` (older exist) | **`hasOlder`: no public flag — derive it from the page size.** A top query returning **fewer messages than the requested limit** means older history is exhausted (the rule the SDK uses internally); until then, assume older may exist. |

Derive both from the page size / `isUpToDate` — not from "are there any messages" — so a load-older /
load-newer affordance turns off once that end is exhausted instead of triggering forever.

### Read receipts / unread counts — the model is inverted

Sendbird gives per-message `channel.getUnreadMembers(message)`. Stream exposes **channel-level read
cursors**: `channel.state.read` → `List<Read>` of `{user, lastRead}`. You don't have to hand-roll the
per-message math: the `readsOf(message:)` extension on the read list returns who has read a given
message (reads whose `lastRead >= message.createdAt`, sender excluded) — "unread by member" is the
remaining members.

The **app-total badge** (Sendbird's `SendbirdChat.getTotalUnreadMessageCount()`) is
`client.state.totalUnreadCount` (live: `client.state.totalUnreadCountStream`) — it lives on
`ClientState`, not on the client itself.

### Timestamps are UTC

Server-synced Stream `DateTime`s (`message.createdAt`, `channel.createdAt`) are **UTC** —
`.toString()` renders `…ffffffZ`. (A just-sent message carries a local timestamp until the server
echo replaces it.) If a preserved widget stringifies a timestamp (Sendbird's were epoch-ms →
local), call `.toLocal()` so the rendered text matches the source.

---

## 6. Theming & view customization

| Sendbird | Stream |
|---|---|
| `SBUColors` (+ `SBUColors.setColors(...)`) | component themes on `StreamChatThemeData` (via `StreamChat(themeData:)`) + `StreamTheme` (a `ThemeExtension`) |
| `SBUThemeProvider` (`SBUTheme.light`/`.dark` toggle) | two `StreamChatThemeData` instances switched on `Theme.of(context).brightness` |
| `SendbirdUIKit.setFontFamily(...)` | text styles in the theme |
| `SBUStringProvider().setStrings(...)` (custom UI strings) | A kept Stream pre-built widget shows **default English** until overridden — its empty / loading / error states are the classic silent misses (e.g. an empty chat reverts to "Send a message to start the conversation" instead of the source's `noMessages`). Catch them all centrally: subclass `StreamChatLocalizationsEn` (from `stream_chat_localizations`), `@override` the specific getters (`sendMessageToStartConversationText` for the empty chat, `writeAMessageLabel` for the composer placeholder, …), and register it as a `LocalizationsDelegate` in `MaterialApp.localizationsDelegates` (ahead of `GlobalStreamChatLocalizations.delegates`). Per-widget builders only cover the surfaces you remember to set: `StreamMessageListView(builders: StreamMessageListViewBuilders(empty: …))` (the message list groups its placeholder slots under `builders:`), `StreamChannelListView(emptyBuilder:)` (top-level there), `StreamMessageComposer(placeholderBuilder:)`. |

The *how* of matching a specific look lives in [`design-matching.md`](design-matching.md) — this
table only maps the concepts. Sendbird's Flutter theme values live in the `sendbird_uikit` package's
`SBUColors` / `SBUThemeProvider` (source: `github.com/sendbird/sendbird-uikit-flutter` →
`lib/src/public/resource/`) — read them to name concrete colors, then confirm against the running app.

The per-region specifics — composer parity, avatars, message-bubble fill/text, custom cards — are the
checklist in §0.5 habit 2; the exact `StreamTheme` / component-builder knobs live in
[`design-matching.md`](design-matching.md).

### Composer parity — inventory the source composer button-by-button

The composer is where Stream's defaults differ most from Sendbird's, and the gaps are obvious to anyone
comparing screens. **Don't accept Stream's default composer** — make it match the source exactly, per
integration:

- **Leading button.** Sendbird's is a **"+"** tinted with the accent (the attachment/menu trigger).
  Stream's default leading is also a `+`, but its **shape and fill differ** (an outlined chip vs the
  source's plain or filled glyph) — don't assume they match because both are a plus; crop and compare,
  and override the `messageComposerLeading` slot when they don't.
- **Remove what the source doesn't have.** Sendbird (default config) shows **no GIF/giphy** and **no
  slash-command** affordance, and the **mic is per-integration** — show Stream's voice recording only
  where the source enables it (`enableVoiceRecording: false` where it doesn't). An **added** control is
  a fail exactly like a dropped one.
- **Send button behavior at rest.** Check what each side shows with an **empty** field (send hidden,
  greyed, or swapped for a mic) and with **text typed** — the rest⇄typing swap must match the source.
- **Placeholder text.** Sendbird's default is **"Enter message"**; Stream's is **"Write a message"**
  (`writeAMessageLabel`) — override via the localization subclass (table above) or
  `StreamMessageComposer(placeholderBuilder:)`.
- **Tint + field container.** Tint the `+`/send with the integration accent, and match the input
  field's **fill, border, corner radius, and height** to the source — measured, not eyeballed.

Inventory the source composer **left→right and right→left, in both states** (at rest and with text),
and reproduce exactly that set — no more, no less. The inventory names **WHAT** to match;
[`design-matching.md`](design-matching.md) → Composer is the **HOW** (the sub-slot map, stock-default
chrome, per-part sampling and measurement).

---

## 7. Seeding / demo data

The client can act **only** as the connected user. Sendbird's test-mode multi-user creation does
**not** map. Create other users / cross-user messages **server-side** (`getstream` CLI — see
[`SKILL.md`](SKILL.md) → Step 0.5). The current user's own channels/messages can be created from
the client.

---

## 8. Pitfalls (build/runtime breakers)

- **Provider-tree order** is a hard runtime constraint (`StreamChat` → `StreamChannel` →
  `StreamMessageListView`).
- **Dispose controllers** (`StreamChannelListController` etc. are `ChangeNotifier`s) in
  `State.dispose` — Sendbird's queries had no dispose requirement.
- **`StreamChannel.value` for sub-routes:** the default `StreamChannel(...)` repositions the loaded
  message window on mount (anchors to `initialMessageId` / last-read / latest). Use
  `StreamChannel.value(...)` for a thread / modal / info route off an already-initialized channel to
  keep its window intact.
- **Attach `stream_chat_persistence` before `connectUser`** (`client.chatPersistenceClient = …`).
- **Don't `await` a blocking OS permission dialog before `connectUser`.** A preserved app that requests
  push/notification permission on the critical path (e.g. inside `login()` ahead of connecting) hangs on
  a blank screen while the system dialog is up. Connect first, then request permission off the critical path.
- **Full replace vs. per-field update — same rule for users, channels, and messages.** The `update*`
  call replaces the whole object, dropping any field you didn't include; the partial call sets/unsets
  individual fields. Reach for `update*` only when you intend a full replace:
  - **User** — `client.updateUser(user)` (full) vs `client.partialUpdateUser(id, set: {…}, unset: […])`.
  - **Channel** — `channel.update(…)` / `client.updateChannel(…)` (full) vs `channel.updatePartial(set:,
    unset:)` / `client.updateChannelPartial(…)`.
  - **Message** — `channel.updateMessage(msg)` (full) vs `channel.partialUpdateMessage(msg, set:, unset:)`.

---

## 9. Procedure checklist
1. **Detect** the integration shape + the per-widget UI strategy (§0).
2. **Capture the source baseline** (§0.5 habit 0) — run the Sendbird app and screenshot every
   **Sendbird-backed** screen/variant (§0's touchpoints — not the app's unrelated screens), list and
   chat, incoming and outgoing. Those shots are the spec the rest of the migration is judged against —
   capture them **before** writing any Stream code.
3. **Swap packages** (§1).
4. **Credentials**: API key + token via the CLI (§2, [`SKILL.md`](SKILL.md) Step 0.5).
5. **Wire one client** + provider; repoint existing bootstraps without changing their public API (§2).
6. **Migrate each touchpoint** — views + navigation + action wiring (§3), channels (§4),
   messages/attachments (§5).
7. **Re-apply theming/customization** via the two axes (§6, [`design-matching.md`](design-matching.md)).
8. **Move seeding server-side** (§7).
9. **Verify against the baseline** (§0.5 habits 2–3 + [`design-matching.md`](design-matching.md)
   Step 5) — walk the §0.5 checklist on every screen at native scale (preserve path: zero visual
   change), drive every interaction the source has, and iterate until every region passes. **The
   region-by-region comparison — not a green build, not this checklist — is the exit criterion;**
   report what was verified and name anything left unverified or unmatched, with its blocker.
10. **Offer data migration** (§10).

---

## 10. Data migration (offer after the code migration)

The steps above migrate the **code/SDK**; they move no history — a migrated app talks to an
**empty** Stream app until you seed or import. Once it builds, connects, and matches the source,
**ask** whether to also migrate the Sendbird **data** (users, channels, message history, reactions).
That work is server-side and SDK-independent, so it lives in the shared runbook
[`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md) — read and follow it
if the user says yes. Do **not** start a data migration unsolicited.
