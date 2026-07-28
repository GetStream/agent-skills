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

**0. The source SDK IS the spec — running the source only *confirms* it.** Never design a migrated
screen from scratch or against Stream's defaults. The spec exists **without running anything**: the
app's Sendbird theme/config (`SBUColors` / `SBUThemeProvider` overrides) applied through the **Sendbird
UIKit's default rendering** — both open source (`github.com/sendbird/sendbird-uikit-flutter`; theme
under `lib/src/public/resource/`, layout in the `SBU…` widgets' `build()`) — so you can read what
*would* render for every in-scope screen: the list **and** the chat, incoming **and** outgoing. **If the
source is runnable, run it and screenshot to confirm** — the render is the tiebreaker when a theme
constant and the SDK's actual output disagree (habit 1). **If it isn't** (no creds, dead backend, won't
build — the common production case), derive the spec from the source read and **mark every value you
couldn't confirm against a render as unverified**, never as matched. Either way you verify your *Stream*
render against this spec (habit 3) — the target is usually runnable even when the source isn't. (A
screen with no Sendbird involvement gets no fidelity pass — the migration doesn't touch it; the one
app-wide check is that a shared edit such as `MaterialApp.theme` didn't bleed into non-chat screens. For
a *new* use-case with no Sendbird original, read the same source defaults, or build a throwaway Sendbird
reference in a git worktree if you need to see it.) To run the source when you can, get past its login
(`SendbirdChat.connect(userId, accessToken: token)`) via the platform automation tool (`adb shell input
tap`), an integration-test harness, or connecting in code at launch — Sendbird auto-creates the user on
`connect(userId)` unless access tokens are enforced.

**1. Derive every value from the source — never guess, never accept Stream's default.** Each region's
value comes from the app's Sendbird theme (`SBUColors` / `SBUThemeProvider` — read the actual values in
`lib/src/public/resource/` of `github.com/sendbird/sendbird-uikit-flutter`; a per-app override or a
newer default makes any constant baked in here wrong) applied through the SDK's default rendering.
Sendbird encodes **emphasis tiers** in the alpha channel (high/mid/low ≈ 88/50/38% opacity) — match the
tier per element, and pull fonts/sizes/paddings per element too, **text included**, keeping the source's
hierarchy (a quieter author over a brighter message; full-strength everything inverts it). **Read the
SDK's *rendering*, not just the theme constant — the constant can lie** (a value set in the theme may
never reach the widget). **When the source is runnable, pixel-sample it to settle disagreements** (method
in [`design-matching.md`](design-matching.md) Step 1); **when it isn't, the source read is the spec —
flag any value a render would have confirmed as unverified.** If a value *contradicts the app's own
accent*, that's likely an SDK quirk: prefer brand consistency, and when ambiguous **ask rather than
guess**.

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
  [`design-matching.md`](design-matching.md) (components — read its procedure half in full: everything
  above the `# Reference` divider, which may span two Reads; Grep its Reference half per region) or [`custom-ui.md`](custom-ui.md) (bespoke/livestream).

**2. Inspect EVERY screen variant, and inside it walk this checklist** — each is a Sendbird→Stream
*default* gap a green build and a list-only screenshot hide:

| Check (inside the chat) | The gap a green build hides |
|---|---|
| **Outgoing bubble** | Left as Stream's pale brand shade (`colorScheme.brand.shade100`); a solid source bubble needs its fill **and** text color set (`StreamTheme.messageItemTheme`; §6 → *Message bubble fill & text*), or the text stays dark/illegible. |
| **Incoming bubble** | Not matched to the source's incoming fill + text. |
| **Row layout** | A restructured row (author-on-top, flat rows, no bubble) treated as a recolor — it's a **widget replacement** (the Restructured axis above), not a theme token. |
| **Bubble geometry & text scale** | Fill matched but geometry left at Stream defaults: the **tail corner squares** on the last message of a run (Sendbird rounds every corner uniformly, 16), the **body text is larger** (Sendbird body is 14) and the **item width caps at 264/272** — so migrated bubbles wrap lines Sendbird fits on one. Fix via `messageItemTheme.bubble.shape` / `.text.textStyle` / `messageItem → DefaultStreamMessageItem(props.copyWith(maxWidth:))` ([`design-matching.md`](design-matching.md) → Message row, bubble, metadata). |
| **Status bar** | Sendbird tints the status strip with the accent (white glyphs); a migration keeps the white-glyph style without the tinted strip → **invisible clock**, or drops the tint entirely. Paint the inset + set `AnnotatedRegion` brightness ([`design-matching.md`](design-matching.md) → Header / chrome, incl. the `removePadding` trap). |
| **Metadata placement** | Author name / timestamp / receipts / avatar sitting at **Stream's default positions** instead of the source's — match the source's arrangement (wherever it puts them) per §6 → *Message-row metadata* (the `messageHeader` / `messageContent` slots **plus** a `messageItem` hand-off, because those slots can't see the message); a placement miss reads "matched" at a glance, so compare native-scale crops, never thumbnails. |
| **Header trailing** | `StreamChannelHeader` defaults its trailing edge to the channel avatar; the source header's actual actions not reproduced. |
| **Composer inventory** | Stream's default set shipped as-is instead of matched 1:1. Inventory the source composer left→right in **both** states and match every control, the placeholder, and the field container (§6 *Composer parity*) — **including the send button**: its accent **tint** (not Stream's default **blue**) and its **rest⇄typing presence** (Sendbird hides send on an empty field; Stream's default rests on a **mic**, becoming a persistent send when voice recording isn't wired — `voiceRecordingCallback == null`). No source mic → `enableVoiceRecording: false`; an **added** affordance is a fail exactly like a dropped one. The signature of a skipped pass — **a stock trailing control (mic, or persistent blue send), the outlined `+` chip, the gray-bordered field** — is a FAIL even when sending works. |
| **Composer states** | The rest⇄typing swap, and the **edit** and **quote/reply** states, never compared against the source. |
| **Composer chrome (bar + pill)** | **Behavior parity ≠ chrome parity.** A pass that matches the placeholder and send-presence can still ship Stream's chrome — the bar top hairline, bar height, pill fill/border/radius, and the `+` glyph shape are all separate from behavior, and each reads as "unmigrated". Close each on a native-scale crop pair — a code comment naming the source shape is not evidence. Mechanisms + the exact tokens: §6 → *Composer parity*; full checklist: [`design-matching.md`](design-matching.md) → Composer. |
| **Composer-area extras** | Suggestion / quick-reply chips, banners, or any auxiliary UI the source renders around the input **dropped, or re-homed** away from the source's placement (inside vs above the field). Rebuild them at the source's exact position — e.g. via the composer's `inputHeader` / header sub-slots ([`design-matching.md`](design-matching.md) → Composer). |
| **Avatars** | Stream's circular avatar left as-is; source shape/size not matched; an avatar shown where the source hides it (1:1 / bot chat); or an **invented** colorful/initials avatar where the source renders its default grey placeholder (§6 → *Avatars*). |
| **Reactions** | Left at Stream's default — overlay pills on the bubble's top edge, Stream's own emoji set and order — instead of the source's. Match what the **source actually renders**: **position** (in-bubble vs. overlay — read it off the baseline shot, don't assume), the **emoji set**, and the **order**. Sendbird's reaction set and ordering are app-configurable, so the running source is the only benchmark — never assume either SDK's default. Relocate via the `reactions` slot / `reactionsTheme`, with one shared type→emoji map ([`design-matching.md`](design-matching.md) → Message row, bubble, metadata — the reactions rows; [`RULES.md`](RULES.md)). |
| **Custom cards** | Rendered as plain text or nested in a default bubble instead of via a custom `Attachment` builder (§5). |
| **Empty / loading / error strings** | A kept pre-built widget shows Stream's default English instead of the source's strings (§6 localization row). |
| **Dark palette** | Migrated light-only when the source ships both (`SBUThemeProvider`) — build both variants and switch on `Theme.of(context).brightness` (§6); how the switch triggers follows the source, but both palettes must exist. Toggle and verify **both** on the device — a built-but-unverified palette is unverified, not done. |

**Flutter realities to expect:** avatars are **circular-only** (Slack-style rounded squares need a
custom avatar widget); there's **no consolidated Styles axis** (insets/radii spread across theme
objects); **no global reaction-emoji config**. A Sendbird app using any of these needs widget-level work.

**3. Verify on the real screens — rendering AND behavior; a green build is not "done".**
**Seed the chat first so every region is populated,** covering both sides: send an **outgoing** message
as the connected user (from the client, or server-side with `SendMessage … user_id=<connected user>`),
and seed the cross-user **incoming** messages and any custom-card messages server-side (`getstream`
CLI, §7). The outgoing message is the one to be sure of — it's where the bubble fill/text match shows.
Cover the channel shapes too: a **group** chat AND a **1:1** (the §4 DM render check needs one), plus
extra members/watchers on any open/livestream surface so participant counts render.
Then open the list **and** each chat — including the 1:1: its list row and header must show the
**other member's single avatar and name**, not a two-avatar cluster (§4) — on the app's **real
navigation path** and compare region-by-region
against the Sendbird baseline at native scale (crop both sides and measure — don't eyeball; iterate on
hot reload). Rendering is not behavior — a screen that paints can still be behaviorally dead, so
**drive every interaction the source has** and confirm its observed effect; when present, these are the
ones that get silently dropped: **send text · send an attachment via the picker · Reply → quote preview
above the input (`onReplyTap → controller.quotedMessage`) → send → quoted message renders · Edit →
composer loads the text → save → edited message shows · long-press → actions menu · react from the
picker · open a thread and reply · channel-row long-press · mark-read · navigate back (chat → list,
thread → chat).** The routing layer is migration-owned (§3), so a broken pop — or a header with no
wired back affordance — is a migration defect. A rendered-but-inert affordance
is a fail. Run on a device you confirmed is booted (`flutter devices` → `flutter run -d <deviceId>` —
never a device/OS you haven't confirmed). To reach a gated chat screen where tapping isn't available,
use a temporary env-gated re-route: launch with `--dart-define=AUDIT_CHANNEL=<cid>`, read it via
`String.fromEnvironment`, and when set point `home:` at the target screen wrapped in
`StreamChannel(channel: client.channel('messaging', id: cid))` — delete it after (same rules as the
throwaway scaffold), and beware the stale-define trap: an incremental build can reuse the previous
run's define values, so force the rebuild with a changing nonce define. If the device or run session
wedges mid-pass, recover via the ladder in [`design-matching.md`](design-matching.md) Step 5 — an
environment failure never upgrades a region to
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

**Match the channel-list row, not just the list.** The default channel-list row differs from
Sendbird's group-channel row in ways that read as "unmigrated": it **drops the member-count** the
source shows next to a group name, and its subtitle **prefixes the sender** ("Alex: …") where Sendbird
shows the bare last message. Match both via `StreamChannelListView(itemBuilder:)` → construct a
`StreamChannelListTile`, supplying **every part**: `avatar:` (required — `StreamChannelAvatar(channel: channel)`),
`title:` (append `channel.memberCount`), `subtitle:` (bare last-message text), **plus `timestamp:` and
`unreadCount:`** — the tile renders those two right-aligned at the row edge, exactly Sendbird's trailing
cluster (timestamp + delivery check on your own last message); omit them and the trailing silently
disappears. (The `defaultWidget` handed to `itemBuilder` is a `StreamChannelListItem`; its `copyWith`
covers only `channel`/`onTap`/`onLongPress`/`selected`, so it can't reach title/subtitle. A fully
hand-rolled row needs a `Spacer()` to push the trailing cluster to the edge.) Also crop the **unread
badge**: Stream tints it `colorScheme.accentPrimary` (via
`StreamTheme.badgeNotificationTheme`) — set the source's accent on `StreamTheme.colorScheme` so the
badge follows ([`design-matching.md`](design-matching.md) → Channel list). These are the rare fidelity gaps that DO surface on the
list — the habit-0 note that "gaps live inside the chat" is the common case, not a guarantee, so
still crop the list row.

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

**Detecting a DM is only half of it — render it like one.** Stream's channel **avatar**
(`StreamChannelAvatar`, used by the default `StreamChannelListTile` leading and by the chat header)
builds a **member cluster** from `channel.state.members`, so a migrated 1:1 — 2 members, explicit id,
not distinct — draws a **two-avatar cluster (including the current user)** where the source showed the
single other person. For `memberCount <= 2`, override the avatar to the **other member's** single one:
`StreamUserAvatar(user: m.user)` for the `channel.state.members` entry whose `user.id != currentUser.id`
— pass it as `StreamChannelListView(itemBuilder:)` → `StreamChannelListTile(leading:)` and as the chat
header's leading. Do the same for the DM **title** (the other member's name, not the channel name, which
is usually blank for a DM).

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
builder's `defaultProps` so the row keeps its default rendering. `fromProps` is safe here — `messageBuilder` is a per-widget param, not the `messageItem` slot; the recursion rule ([`RULES.md`](RULES.md)) applies only to slot overrides. (Unknown attachment root keys are promoted into
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

This table only maps the concepts. The *how* for the regions migrations keep shipping at Stream
defaults — the composer, the message-row metadata, the bubble fill/text, and avatars — is inlined
below; the fully general procedure and every other region's mechanics (reaction relocation, custom
cards → §5, media overlays, the full theme-token tables) live in
[`design-matching.md`](design-matching.md). Name concrete Sendbird values from `SBUColors` /
`SBUThemeProvider` per §0.5 habit 1 (which carries the source path), confirming against the running app when runnable.

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
and reproduce exactly that set — no more, no less.

**The mechanisms (v10 — confirm each name against the pinned source, [`design-matching.md`](design-matching.md) Step 3).**
The composer is slot-composed — `[messageComposerLeading] [messageComposerInput → (inputHeader |
inputLeading | inputCenter | inputTrailing)] [messageComposerTrailing]` — and every slot is overridden
via `StreamChat(componentBuilders: StreamComponentBuilders(extensions: streamChatComponentBuilders(<slot>: (context, props) => …)))`:

- **Bar + pill chrome (top hairline · pill fill · border · radius) — where the source's bar differs
  from Stream's, matching it needs a scoped-token override, not just a wrapper.** The composer paints
  its **own** bar (`Material(color: backgroundElevation1)`) with a top hairline (`Border(top:)` in
  `colorScheme.borderDefault`); the pill reads the SAME tokens (`backgroundElevation1` fill,
  `borderDefault` border, `radius.xxxl` corner ≈24). So wrapping the composer in a `Container(color:)`
  does nothing, and **leaving Stream's chrome where the source's bar looks different — its top separator
  and bordered pale pill against, say, a borderless solid field — is a FAIL, not a cosmetic detail.**
  Read the source bar's fill/border/hairline/corner off the baseline crop and drive the tokens to
  match; the mechanism is a scoped `Theme` around the terminal default (most Sendbird composers land on
  a borderless solid pill with no hairline — this skeleton reaches that; adjust the values to your
  source):

  ```dart
  messageComposerInput: (context, props) {
    final t = StreamTheme.of(context);
    return Theme(
      data: Theme.of(context).copyWith(extensions: [
        t.copyWith(colorScheme: t.colorScheme.copyWith(
          backgroundElevation1: <source field fill>,   // pill fill
          borderDefault: <source border, or transparent>,  // transparent kills the pill border (the BAR hairline is outside this scope — see below)
        )),
      ]),
      child: DefaultStreamMessageComposerInput(props: props),  // NOT StreamMessageComposerInput — recurses
    );
  },
  ```
  Corner differs? add `radius: t.radius.copyWith(xxxl: <measured>)`. The bar paints its own chrome —
  its fill AND its top hairline (`Border(top:)` at bar level) — *outside* this input-slot scope: to
  retint the bar or kill the hairline, scope a second `Theme` with the same tokens around the **whole
  composer**.
- **Leading `+`.** Stock is an **outlined `+` chip**; Sendbird's is a plain rounded-square glyph
  tinted with the accent. Override `messageComposerLeading`: render the measured glyph and wire
  `props.onAttachmentButtonPressed`.
- **Send presence.** Disable the mic the source doesn't have (`enableVoiceRecording: false`) — but the
  stock trailing then renders a **persistent enabled send**, where Sendbird **hides send on an empty
  field**. Override `messageComposerInputTrailing`: listen to `props.controller`, return
  `SizedBox.shrink()` while the text is empty, else the accent-tinted send calling
  `props.onSendPressed`. The default slot is a **state machine** (slow-mode countdown · voice UI ·
  confirm-edit · confirm-command · send) — reproduce the states the app uses, at minimum
  **edit → confirm-edit**.
- **Vertical centering is a measured gate.** The bar row AND the in-pill row are both
  `Row(crossAxisAlignment: end)`, so a custom side-slot glyph **bottom-anchors and rides low**. Wrap
  each in `SizedBox(height: <measured single-line field height>, child: Center(glyph))` — every side
  slot in one pass (fixing send but not the `+` is the recurring miss). Gate: |glyph center-Y − pill
  center-Y| ≤ 2 px on a native-scale crop.

These recipes cover the stock Sendbird composer; for anything beyond them — each slot's full Props,
stock defaults per sub-slot, attachment-picker presentation, custom-field caveats — Grep
[`design-matching.md`](design-matching.md) → Composer.

### Message-row metadata — match the source's row layout, wherever it puts name/time/receipts

**The target is the source's arrangement, not any fixed layout.** Read off the baseline where the author
name, timestamp, and receipts actually sit relative to the bubble, and reproduce *that*. Stream's default
bundles author + time + ticks into one footer **below** the bubble, rendered only on the last message of
a run — so **leaving that default when the source arranges the row differently is a FAIL, the same as
shipping the default composer.** This is a standard, expected step; don't defer it as "risky
restructuring." It's a set of narrow slot overrides that each keep the default composite running (v10 —
confirm the names against the pinned source):

- **Name in a different place** (e.g. above the bubble) → the extension slot **`messageHeader`** (its
  default carries pin/reminder annotations, never the name) — render the author row for the source's
  cases (per its grouping).
- **Time/receipts beside the bubble** → the core **`messageContent`** slot (on `StreamComponentBuilders`
  **directly**, not under `extensions:`); it hands you the composed bubble as `props.child`, so return
  `Row[props.child, timeReceiptColumn]`. It will **not** appear in `streamChatComponentBuilders(...)` — to
  confirm it (or any leaf slot) exists, grep the `StreamComponentBuilders` factory in
  `stream_component_factory.dart`, **not just** the extension helper `stream_chat_component_builders.dart`;
  a slot absent from one is usually a core param on the other. **Do not reach for the intuitively-named `messageFooter` slot
  to put time beside — it only stacks *below* the bubble.** `messageFooter` is the right tool only when
  the source actually renders the timestamp **below** (then use it and skip `messageContent`); a
  beside-the-bubble layout is `messageContent` or nothing.
- **Hide the default footer** you've replaced → `StreamTheme.messageItemTheme.metadataVisibility` gone.

The one non-obvious constraint: `messageContent` sees only `props.child`, not the `Message`, so pass the
message down from the `messageItem` slot (which has it) through a tiny `InheritedWidget`. **That
hand-off is the reusable mechanism — the skeleton below is worked for the common stock-Sendbird case
(name-above, time-beside); if your source differs (metadata *inside* the bubble, a role/status badge,
inline meta on short messages, a different order), keep the same message-hand-off + slot pattern and
build whatever the source shows — the arrangement inside the slots is yours, not fixed:**

```dart
// carries the message down to messageContent
class _MsgScope extends InheritedWidget {
  const _MsgScope({required this.message, required super.child});
  final Message message;
  static Message of(BuildContext c) =>
      c.dependOnInheritedWidgetOfExactType<_MsgScope>()!.message;
  @override bool updateShouldNotify(_MsgScope o) => o.message != message;
}

// messageItem publishes it (and raises maxWidth so flanking meta doesn't force early wraps)
messageItem: (context, props) => _MsgScope(
  message: props.message,
  child: DefaultStreamMessageItem(props: props.copyWith(maxWidth: <measured>)), // NOT StreamMessageItem.fromProps — recurses
),

// messageContent reads it and arranges the bubble + meta as the source does (inline lambda — its Props isn't nameable)
messageContent: (context, props) => Row(
  crossAxisAlignment: CrossAxisAlignment.end,
  children: [Flexible(child: props.child), _timeReceipt(_MsgScope.of(context))],
),
```

- **Two gates after the `messageItem` override:** seed one attachment message into a scratch channel
  rendered by the same UI and confirm the list still paints (SDK attachment widgets embed
  shrink-wrapping viewports that can blank the whole list under intrinsic measurement), and re-crop
  **wrap parity** (multi-line bubbles break at the same words as the source).

The general machinery — content-kind routing for media overlays, metadata *inside* the bubble,
reaction-pill relocation — is [`design-matching.md`](design-matching.md) → Message row, bubble, metadata.

### Message bubble fill & text — set the color per side, and set the text with it

The message row reads **`StreamTheme`**, not the Material `ColorScheme`: the default outgoing bubble is
`colorScheme.brand.shade100` (a pale brand tint), incoming is `colorScheme.backgroundSurface` — so
recoloring `MaterialApp`'s seed leaves the bubbles unchanged. Set the source's fills on
`StreamTheme.messageItemTheme.bubble`, and set the **text** with them — a solid Sendbird outgoing bubble
needs its fill **and** an on-accent text color, or the text stays dark and illegible:

- **Fill (per side)** → `bubble.backgroundColor: StreamMessageLayoutProperty.resolveWith((p) =>
  p.alignment == StreamMessageAlignment.end ? outgoing : incoming)` — one property that resolves by
  alignment (don't set a flat color; it applies to both sides).
- **Text** → `messageItemTheme.text.textStyle` (resolve per alignment too if the sides differ); outgoing
  is usually white on a solid accent.

Bubble **geometry** — border/radius, the squared tail corner on the last message of a run, body-text
size, and `maxWidth` — is the §0.5 *Bubble geometry & text scale* row + [`design-matching.md`](design-matching.md) → Message row, bubble, metadata.

### Avatars — match the source's shape/size, don't invent

Match the source's avatar exactly and don't "upgrade" a plain placeholder. Where the source shows the
**default grey person-circle** (no uploaded images), Stream must too — not an invented colorful/initials
avatar; where the source **hides** the avatar (1:1 / bot chats), hide it
(`StreamTheme.messageItemTheme.avatarVisibility`), and set the default size via `.avatarSize`.
`StreamUserAvatar` renders **circular only** and sizes to fixed `StreamAvatarSize` buckets (`xs` 20 · `sm`
24 · `md` 32 · `lg` 40 · `xl` 48 · `xxl` 80 lp) — a **rounded-square** (Slack-style) avatar or an
off-bucket measured size needs a small custom widget (a `ClipRRect` around the user's image with an
initials fallback). For a migrated **1:1**, draw the **other member's single** avatar, not Stream's
member cluster (§4).

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
2. **Derive the source spec** (§0.5 habit 0) — read the Sendbird theme + UIKit default rendering for
   every **Sendbird-backed** screen/variant (§0's touchpoints — not the app's unrelated screens), list
   and chat, incoming and outgoing; **run the source and screenshot to confirm when it's runnable**,
   flagging unconfirmed values as unverified. Establish this spec **before** writing any Stream code.
3. **Swap packages** (§1).
4. **Credentials**: API key + token via the CLI (§2, [`SKILL.md`](SKILL.md) Step 0.5).
5. **Wire one client** + provider; repoint existing bootstraps without changing their public API (§2).
6. **Migrate each touchpoint** — views + navigation + action wiring (§3), channels (§4),
   messages/attachments (§5).
7. **Re-apply theming/customization** via the two axes (§6 — its inline *Composer parity* /
   *Message-row metadata* recipes included; [`design-matching.md`](design-matching.md) for the
   general procedure).
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
