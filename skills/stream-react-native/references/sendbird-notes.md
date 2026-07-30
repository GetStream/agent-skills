# Sendbird -> Stream Chat React Native: mapping notes (Track S appendix)

**Symbol lookups are NOT in this file.** They live in
[`sendbird-symbols.tsv`](sendbird-symbols.tsv) — 361 rows, one per Sendbird symbol.
It is a lookup table, not reading material: **grep it, never read it.**

```bash
R=references/sendbird-symbols.tsv
grep -F 'createGroupChannelFragment' $R              # one symbol
grep -F -f app-sendbird-symbols.txt $R               # the whole app inventory at once
awk -F'\t' '$4=="curated"' $R | grep -F 'queryChannels'
```

Columns: `sendbird` · `stream` · `automation` · `tier` · `section` · `note`.

- `tier=curated` — extracted from installed types and **`tsc`-verified** against
  `stream-chat@9.50.2` / `stream-chat-react-native@9.7.0`, cross-checked against four real apps.
  126 mapped symbols (93 core-SDK, 33 UIKit): 1 pure rename, ~110 agent-guided shape-shifts,
  28 hard gaps.
- `tier=inferred` — the machine-generated long tail (226 rows covering the 806 symbols no sampled
  app used). Every Stream target was **existence-checked** against the installed symbol inventory
  (3,643 names), so no target is invented — but the *pairing* is a hypothesis, not `tsc`-verified.
- `automation` legend: **codemod-safe** (1:1 auto) · **agent-guided** (mechanical + caveat) ·
  **manual** (gap -> `TODO(migration)`) · **none** (gap). Extended rows also use
  shape-shift · behavioral-diff · 1-to-n · n-to-1.
- A `note` of `-> sendbird-notes.md#anchor` means the trap was too long for one line; it is in
  [Long notes](#long-notes) at the bottom of this file.

**Three rules that outrank every row:**

1. **The installed package outranks this file.** If `npx tsc --noEmit` disagrees with a row, the
   compiler is right — a newer major may have renamed the symbol
   ([`../RULES.md`](../RULES.md) > Package version and docs discipline).
2. Where a row touches a Stream RN component's *current* props/hooks rather than the cross-SDK
   mapping itself, fetch the matching page via [`DOCS.md`](DOCS.md) before building.
3. `- (gap)` rows have **no Stream equivalent** — route them through the parity ledger and the
   [feature-gap decision discipline](#15-feature-gaps---no-stream-equivalent-decision-required)
   below, never a silent `TODO`.

Import every Stream symbol from the **flavor package** — `stream-chat-react-native` (bare RN CLI)
or `stream-chat-expo` (Expo). The component/hook names are identical; only the package specifier
differs ([`../sendbird-migration.md`](../sendbird-migration.md) > Flavor first). Client-layer
symbols come from `stream-chat`.

---

### `tier=inferred` sections

The long tail has no prose — only rows. Section names for `awk` filtering:

- `1. Connection, auth, session & users/presence`
- `2. Channels: model, config & queries`
- `3. Pagination, queries & collections`
- `4. Messages, threads, reactions & mentions`
- `5. Membership, roles & moderation`
- `6. Attachments, media & polls`
- `7. Events, sync, push & offline`
- `8. Metadata, counters, theming/i18n & other`
- `9. Feed channel, scheduled send & AI-Agent/Desk (gaps)`

---

## 1. Init, auth & user

**No-backend / demo auth = a fixed roster of known users, each with a single pre-minted token.** Stream
always requires a signed token (Sendbird's tokenless `connect(userId)` has no equivalent). For a
migration/demo, use a **fixed set of user ids**, each with one token minted by `getstream token <id>`,
held in app config — the same shape as the Swift runbook's `Config.userId` / `Config.userToken`. This
needs **no app-wide config change**. Production swaps the static token for a `tokenProvider` hitting a
backend that derives the user id from the authenticated session ([`RULES.md`](../RULES.md) > Secrets and
auth). Because the roster is fixed, seed those user records server-side once (`getstream api UpdateUsers`)
so they also satisfy channel membership (see section 8 — Stream does not auto-create member users).

## 2. Channels: model & queries

Sendbird has three channel **classes**; Stream has **one** `Channel` class whose behavior comes from
a server-configured **type string** passed to `client.channel(type, id?)`. Built-in types:
`messaging`, `team`, `livestream`, `commerce`, `gaming`.

## 3. Messages: sending & state

One `MessageResponse` shape replaces Sendbird's class hierarchy (`BaseMessage` / `UserMessage` /
`FileMessage` / `MultipleFilesMessage` / `AdminMessage`): discriminate via `message.type`
(`'regular' | 'system' | 'ephemeral' | 'error' | 'reply' | 'deleted'`) and `message.attachments`.

## 4. Attachments & media

_Symbol rows only._ `awk -F'\t' '$5 ~ /^4\./' sendbird-symbols.tsv`

## 5. Events & real-time

_Symbol rows only._ `awk -F'\t' '$5 ~ /^5\./' sendbird-symbols.tsv`

## 6. Typing, presence, read state

_Symbol rows only._ `awk -F'\t' '$5 ~ /^6\./' sendbird-symbols.tsv`

## 7. Pagination: every stateful cursor dies

Sendbird queries are stateful objects (`.next()` / `.load()` / `.hasNext`); Stream calls are
stateless. Convert each; in UI, the prebuilt components paginate for you.

Behavioral notes: Sendbird's `hasNext` is server-authoritative; Stream's equivalent is a
count-vs-limit heuristic (a short page = end). Offset paging on a live-mutating channel list can
drift - prefer `<ChannelList>` auto-paging over manual offset math. The
`while (query.hasNext) query.next()` drain-everything pattern doesn't translate cleanly - tighten the
server-side filter so the set fits in one or two pages instead.

## 8. Membership, roles & moderation

**The most dangerous mismap lives here** - see the `muteUser` row.

**Stream does not auto-create users named as members.** `channel.create({ members })` /
`addMembers([...])` **fails** if a listed user doesn't exist yet (`"The following users … don't
exist"`) — Sendbird auto-created invitees. Seed a **fixed roster** (agents/bots/support staff)
server-side first (`getstream api UpdateUsers`); dynamic members must have connected at least once or
be upserted server-side. Ties to the fixed-user-set note in section 1.

## 9. Search

_Symbol rows only._ `awk -F'\t' '$5 ~ /^9\./' sendbird-symbols.tsv`

## 10. Push notifications

`stream-chat-react-native` ships **no notification-service abstraction** - unlike Sendbird UIKit's
`createNativeNotificationService` / `createExpoNotificationService`. Wire React Native Firebase /
Notifee yourself and call the client methods (fetch the manifest-selected Push page via
[`DOCS.md`](DOCS.md) before wiring).

## 11. UI components (UIKit -> stream-chat-react-native / stream-chat-expo)

UIKit ships drop-in **fragment factories** customized via `renderX` props; Stream RN is
compositional - assemble primitives, customize by swapping components. Whenever a row makes you write
your own component for a prebuilt region, fill the completion contract in
[`design-matching.md`](design-matching.md) Step 2.5 (sub-feature inheritance) first. **There is no
`<Window>` in RN** (web-only) and **no `ChannelHeader` slot inside `<Channel>`** (the header is
app-owned - your React Navigation / Expo Router header).

## 12. Context hooks & selectors

_Symbol rows only._ `awk -F'\t' '$5 ~ /^12\./' sendbird-symbols.tsv`

### Own capabilities: TWO hooks, and the context one throws outside `<Channel>`

There are two ways to read a channel's own-capabilities, and picking the wrong one crashes the screen.
The failure is a **runtime throw, not a type error** — `tsc` passes and the screen dies on mount.

| Hook | Signature | Needs `<Channel>`? | Use it when |
|---|---|---|---|
| **`useChannelOwnCapabilities(channel)`** | `(channel?: Channel) => string[] \| undefined` | **No** — takes the channel as an argument | **Default choice**, and the only option in a screen that doesn't mount `<Channel>` |
| `useOwnCapabilitiesContext()` | `() => Record<OwnCapability, boolean>` | **Yes** | Only inside `<Channel>` (message row, composer, custom slots) |

`useOwnCapabilitiesContext()` defaults its context to a `DEFAULT_BASE_CONTEXT_VALUE` sentinel and
**throws** on it — *"The useOwnCapabilitiesContext hook was called outside the Channel Component."* It
does not return an empty object; it crashes. This bites exactly where a Sendbird migration needs
capabilities most: the hand-built **settings / members / invite / moderation / operators / muted /
banned** screens (section 11) are plain navigation screens, and they must **not** mount `<Channel>` just
to satisfy a hook — that drags in the message list, composer, keyboard handling and attachment picker
for a screen that renders rows.

So in those screens use `useChannelOwnCapabilities(channel)` and test slugs directly:

```tsx
const capabilities = useChannelOwnCapabilities(channel);          // string[] | undefined
const canRemoveMembers = !!capabilities?.includes('update-channel-members');
const canBan           = !!capabilities?.includes('ban-channel-members');
```

Both hooks read the same source (`channel.data.own_capabilities`) and both stay live on the
`capabilities.changed` event, so there is no reactivity cost to the context-free one — don't hand-roll
your own `channel.data.own_capabilities` reader.

**Notable capability slugs.** The SDK's typed subset is exported as **`allOwnCapabilities`** (an
`OwnCapability -> slug` map) from `stream-chat-react-native-core` — read slugs there, don't invent them:

| Area | Slugs |
|---|---|
| Messaging | `send-message`, `send-reply`, `send-reaction`, `send-links`, `send-typing-events`, `upload-file`, `quote-message` |
| Own vs. any message | `update-own-message` / `update-any-message`, `delete-own-message` / `delete-any-message` |
| Moderation | `ban-channel-members`, `flag-message`, `pin-message` |
| Membership / channel | `update-channel-members`, `read-events` |
| Polls | `send-poll`, `cast-poll-vote`, `query-poll-votes` |

**The raw array is a superset of that map — which is the other reason to prefer the `string[]` hook.**
The server also sends channel-level grants the SDK doesn't type, e.g. `delete-channel`, `freeze-channel`,
`mute-channel`, `leave-channel`, `join-channel`, `search-messages`, `create-attachment`, `create-mention`,
`connect-events`, `delivery-events`, `send-custom-events`, `notify-*`. Notably **`update-channel` is NOT
in `allOwnCapabilities`**, so an edit-channel affordance can only be gated by checking the raw slug —
`capabilities?.includes('update-channel')` — which `useOwnCapabilitiesContext()`'s typed record cannot
express. Capability sets are per-user-per-channel and configured on the channel **type**, so treat any
list as environment-specific and check the slug rather than assuming a role implies it.

**Rule of thumb: before calling any `use*Context()` from a screen you built yourself, confirm which
component provides it.** If the answer is `<Channel>` / `<ChannelList>` / `<Chat>` and your screen
doesn't mount it, use the argument-taking hook or the underlying `client` / `channel` object:

| Need | Inside `<Channel>` | Outside `<Channel>` (nav screens) |
|---|---|---|
| own capabilities | `useOwnCapabilitiesContext()` | **`useChannelOwnCapabilities(channel)`** |
| members | `useChannelContext().members` | `channel.state.members` after `await channel.watch()` |
| channel meta (name/image/frozen) | `useChannelContext().channel` | `channel.data` |

Verified against `stream-chat-expo@9.7.1`.

## 13. Theming & i18n

**Custom fields need TS module augmentation.** Stream's `Custom*Data` interfaces are empty by default,
so custom channel/user/message fields don't typecheck (`tsc` errors "does not exist in type …").
Augment them: `declare module 'stream-chat' { interface CustomChannelData {…}; interface CustomUserData
{…}; interface CustomMessageData {…} }`. Note `name` belongs on `CustomChannelData` (it's `Omit`-ed
inside `ChannelFilters`), so declare it there if you set or filter on it.

## 14. Offline & sync

_Symbol rows only._ `awk -F'\t' '$5 ~ /^14\./' sendbird-symbols.tsv`

## 15. Feature gaps - no Stream equivalent, decision required

Each needs an explicit user decision (substitute / rebuild app-side / drop) recorded in the parity
ledger and routed through the plan checkpoint (runbook section 2 - or its non-interactive
`provisional` fallback). Never leave one as a silent `TODO`.

| Sendbird feature | Status | Closest substitute |
|---|---|---|
| **`FeedChannel`** (notification/announcement feed, categories, impression/click analytics) | No stream-chat equivalent | Admin-post-only `messaging` channel (loses templates/categories/analytics), or the separate Stream Feeds product. |
| **Scheduled messages** (`createScheduledUserMessage`, `sendScheduledMessageNow`, list query, `SCHEDULED` status) | No client scheduled-send | Server-side job that calls `sendMessage` at the target time; drafts (`channel.createDraft`) save but never auto-send. |
| **Report a channel** (`channel.report`) | No channel-flag endpoint | Flag a representative message via `client.flagMessage`. |
| **`ReportCategory` enum** | Free-text `reason` only | Fold the category label into the reason string; build your own picker. |
| **`copyMessage`** | No server copy | Re-send content to the target channel. |
| **Offline cache tuning** (`LocalCacheConfig`, encryption) | Self-managed OfflineDB | Accept the SDK defaults; no knobs. |
| **Recurring DND quiet hours** (daily/weekly + timezone) | One-shot snooze only | Schedule `setPushPreferences` snooze windows client/server-side. |
| **Runtime push template switch**; **per-message push toggle** | Dashboard/server-side only | Configure templates on the push provider; use `skip_push` per send. |
| **Session lifecycle callbacks** (`onSessionRefreshed`/`Closed`/`Error`) | - | `connection.changed` + `tokenProvider` error handling. |
| **`ReplyType` list-visibility enum** | - | `show_in_channel` per reply; no toggle to hide all replies. |
| **Server-side multi-size thumbnails** (`thumbnailSizes`) | Single `thumb_url` | Resize client-side; generate video posters yourself. |
| **CSAT / message feedback / submitForm** (Desk) | No primitive | Custom message/attachment fields, a reaction, or an external tool. |
| **AI-Agent / Desk conversations** (`Conversation*`, handoff, resolution, context) | No stream-chat equivalent | Model as a `Channel` + your own backend for status/handoff; evaluate Stream's AI features separately. |
| **Friends / social graph** (`FriendListQuery`) | No concept | Model relations in your own backend; approximate with `queryUsers` / membership. |

---

## Resolving a symbol not in this table

The RN corpus is **grounded-only** - there is no inferred row for a symbol neither the curated file
nor the 806-symbol long tail covers. Resolve it with the three-tier protocol, and never emit an
unverified Stream symbol:

- **`mapped`** - `grep` hits a row in [`sendbird-symbols.tsv`](sendbird-symbols.tsv): apply it
  (agent-guided rewrite, or a `manual`/`none` gap -> `TODO(migration)`).
- **`unmapped-known`** - a real Sendbird API with no row in either tier: find the nearest
  concept/family among the rows you did hit,
  choose the Stream symbol, **confirm it exists in the installed Stream RN types**
  (`node_modules/stream-chat-react-native-core`, `node_modules/stream-chat`), and verify the rewrite
  with `npx tsc --noEmit`.
- **`unknown`** - imported from `@sendbird` but not in the indexed SDK surface: almost always a
  version skew; check against the Sendbird version the target actually has installed.

Every `- (gap)` is a **parity-ledger decision** (substitute / rebuild app-side / drop) routed through
the runbook's plan checkpoint ([`../sendbird-migration.md`](../sendbird-migration.md) section 2) -
never a silent `TODO`.

---

## Long notes

Referenced by `-> sendbird-notes.md#anchor` in the TSV.

<a id="sendbirdchat-init-appid-modules-localcacheenable"></a>

### `SendbirdChat.init({ appId, modules, localCacheEnabled })`

No modules array - one client exposes everything. **`getInstance` is a process-wide, first-call-wins singleton NOT keyed by apiKey** - a second call with a different key silently returns the first client. In RN prefer `useCreateChatClient` (strict-safe, [`RULES.md`](../RULES.md) > Client lifetime and providers).

<a id="sendbirdchat-connect-userid-authtoken"></a>

### `SendbirdChat.connect(userId, authToken?)`

Takes a user **object**, not a bare id, so profile fields are set at connect. **Sendbird's token-less userId-only connect has NO Stream equivalent** - a token is always required. `client.devToken(id)` works only while dev tokens are enabled, and a **new app has them off** - the resolution is then a pre-minted fixed user roster, decided once in [`../credentials.md`](../credentials.md#dev-tokens-disabled) (runbook section 4).

<a id="openchannel-enter-exit"></a>

### `OpenChannel` + `.enter()` / `.exit()`

Presence via `channel.state.watcher_count`, not enter/exit. **`read_events` is off on `livestream`** - enable client-side unread: `new StreamChat(apiKey, { isLocalUnreadCountEnabled: true })` + `markReadLocally()` / `countUnread()`. Type must be configured server-side first.

<a id="groupchannelmodule-createchannel-params-createch"></a>

### `GroupChannelModule.createChannel(params)` / `createChannelWithUserIds`

`invitedUserIds`/`operatorUserIds` -> one `members` array (operators are a **server-side** role change, not a create param — see the operators row). A client-chosen id makes `create()` idempotent. Omit id + pass members for distinct/DM. **Set `name` on team channels; leave DMs nameless and derive their title from members — `name` is optional, so its presence *is* the DM-vs-channel discriminator. No custom `kind`/`slack_kind` field needed.**

<a id="groupchannel-updatechannel-params"></a>

### `GroupChannel.updateChannel(params)`

Prefer `updatePartial` over `channel.update` (full replace wipes unlisted custom fields). `coverUrl` -> `image`. **Trap (permissions):** the default `messaging` type allows `update-channel` for the channel **owner** (creator) only. A **non-owner member** calling `updatePartial`/`update` on channel data fails — even though Sendbird lets members update channel info by default. Know which party owns each channel-data write and design around it; this is a behavioral difference to be aware of.

<a id="groupchannelfilter-setter-methods"></a>

### `GroupChannelFilter` (setter methods)

e.g. `{ type: 'messaging', members: { $in: [uid] } }`. **Search both fields** (Sendbird `channelNameContainsFilter` + `nicknameContainsFilter`): **channel name** -> `{ name: { $autocomplete: q } }`, **member name** -> `{ 'member.user.name': { $autocomplete: q } }` — both are first-class `ChannelFilters` keys (confirm in the installed `stream-chat` types). A 1:1/DM channel usually has **no `name`**, so a name-only filter misses it — the `member.user.name` filter is what finds DMs. Reproduce Sendbird's name+nickname search with a single `$or`: `{ ...base, $or: [{ name: { $autocomplete: q } }, { 'member.user.name': { $autocomplete: q } }] }` — **annotate the filter `: ChannelFilters`** so the `$or` array gets its `ArrayTwoOrMore` contextual type (an un-annotated array literal is inferred as a plain array and rejected — tsc-verified). Two merged queries also work if you prefer. Do **not** load channels and filter client-side — that only searches the first page. **A transient/secondary search `queryChannels` (a search screen, a picker) should pass `{ watch: false, state: true }`** — you don't need live updates on search results, and the default `watch: true` opens channel subscriptions whose events get re-processed by any live `<ChannelList>` still mounted **elsewhere in the nav stack** (native-stack keeps the list screen you navigated *from* mounted in the background), causing repeated re-querying — the "search keeps reloading" loop, visible as spammed `client._buildSort()` warnings. (`watch: false` is verified to eliminate it; that the re-query is specifically the background `ChannelList` vs the client's channel-state machinery is inferred.) `state: true` still loads members/messages so result rows render. Also **`member.user.name` search works with a user token** (not server-only) — an empty result is almost always the *connected* user genuinely having no matching channel, so log the actual filter (`members.$in` shows who you're querying as) before blaming the SDK. Memoize `filters`/`sort` so `<ChannelList>` re-queries.

<a id="voice-messages-sendbird-enablevoicemessage-true"></a>

### Voice messages (Sendbird `enableVoiceMessage: true`)

**Recording is OPT-IN: `<Channel audioRecordingEnabled>` defaults to `false`** (confirm in the pinned Channel source), so Sendbird's `enableVoiceMessage: true` maps to *setting this prop* — omit it and you silently drop voice messages (the composer shows a send button at rest instead of a mic; a "Ported" claim here is meaningless unless you saw the mic render). Needs an audio package installed — Expo SDK 53+: `expo-audio`; expo-av on older; RN CLI: the audio matrix in [`CHAT-REACT-NATIVE.md`](CHAT-REACT-NATIVE.md#optional-dependency-map) (`stream-chat-expo` lists `expo-audio`/`expo-av` as optional peers). The recorder UI tints from `semantics.accentPrimary` / `chatWaveformBar(Playing)` — recolour those too. The record button renders on the simulator but capture needs a real device (no mic on the sim). Confirm exact symbol names against the installed package / [`DOCS.md`](DOCS.md).

<a id="getdeliverystatus-getundeliveredmembercount-mark"></a>

### `getDeliveryStatus` / `getUndeliveredMemberCount` / `markAsDelivered`

**Per-member delivery IS supported (stream-chat ≥9.x — verified in 9.50.2).** Enable `delivery_events: true` on the channel *type* (via `UpdateChannelType`/`chat.updateChannelType`, not only the dashboard); the SDK auto-marks delivery (`markChannelsDelivered` / `syncDeliveredCandidates`) so drop explicit `markAsDelivered`. `<MessageStatus>` shows three tiers on outgoing messages: single check (sent) → **grey** double-check (`deliveredToCount > 1`) → **accent** double-check (read). The delivered tier only advances when the recipient's client is connected to emit `message.delivered`, and is transient (skipped when the reader has the channel open). Was previously (wrongly) documented as "no per-member delivery" — corrected.

<a id="createmygroupchannellistquery-groupchannelcollec"></a>

### `createMyGroupChannelListQuery` / `GroupChannelCollection`

offset = `channels.length`; in UI prefer `<ChannelList>` (dedupes by `cid`, live updates). Its `channelNameContainsFilter` / `nicknameContainsFilter` search args -> `{ name: { $autocomplete } }` / `{ 'member.user.name': { $autocomplete } }` server-side filters (section 2), **not** a client-side filter over a loaded page.

<a id="createapplicationuserlistquery"></a>

### `createApplicationUserListQuery`

`userIdsFilter` -> `{ id: { $in } }`, `nicknameStartsWithFilter` -> `{ name: { $autocomplete } }`. **TRAP: `queryUsers({}, …)` with an EMPTY filter is not "list all users" — it returns none for a user token, silently** (no throw), so a hand-built user picker renders its empty state and looks like a data bug. Sendbird's list-every-user query has no client-side equivalent; always pass a real condition (`{ id: { $in: rosterIds } }` for a fixed roster, `{ name: { $autocomplete: q } }` for a search field, or a team/contact field of your own).

<a id="myrole-role-operator-none-member-role"></a>

### `myRole: Role` (`OPERATOR` | `NONE`) / `Member.role`

Binary flag -> layered roles + server-configured grants. `OPERATOR` -> `'channel_moderator'`. **There is no `owner` channel_role — the channel owner is `channel.data.created_by`.** **Editing the channel differs by default: in Sendbird any group-channel member can update channel info (name/cover); in Stream the default channel types grant `update-channel` only to the owner (`created_by`) + moderators/admins, so a regular member's `channel.update`/`updatePartial` is rejected server-side.** Gate any edit-channel UI on the `update-channel` own-capability (don't show it to plain members), or loosen the channel type's grants server-side if the app truly relied on member editing. **Gate UI on own-capabilities, not a role-string check — and pick the right hook, because one of the two throws.** See the capability-hook rules + slug list in section 12.

<a id="addoperators-ids-removeoperators-ids"></a>

### `addOperators(ids)` / `removeOperators(ids)`

**`addModerators` / `demoteModerators` / `assignRoles` / `partialUpdateMember`, and `addMembers` with a `channel_role`, are privileged role changes — a normal user token cannot grant/revoke roles, so they must NOT appear in client code.** Do them from a backend/server SDK and record a migration gap. The only client-safe membership calls are role-less: `addMembers(ids)` / `removeMembers(ids)`.

<a id="channel-setmypushtriggeroption-option-per-channe"></a>

### `channel.setMyPushTriggerOption(option)` (per-channel)

**Prefer `setPushPreferences` — it preserves the 3-way ALL/MENTION_ONLY/OFF (`chat_level: 'all'`/`'mentions'`/`'none'`).** `channel.mute()`/`unmute()` is a binary fallback that DROPS the "mentions only" tier, so don't default to it for a trigger-option port. Read the current value from `channel.push_preferences.chat_level`; requires the push-preferences feature enabled on the app.

<a id="creategroupchannelmoderationfragment-operators-r"></a>

### `createGroupChannelModerationFragment` / `Operators` / `RegisterOperator` / `MutedMembers` / `BannedUsers`

No prebuilt moderation/operator screens - compose from **client-safe** ops (`banUser`/`muteUser`/`removeMembers`) + own-capability gating. **Operator promote/demote is server-side only: build the Operators screen read-only and move role changes to a backend. `RegisterOperator` (a client-side promote screen) has no client equivalent — omit it.** **These screens are NOT inside `<Channel>`, so do not call `useOwnCapabilitiesContext()` in them — it throws. Use `useChannelOwnCapabilities(channel)` (returns `string[]`) — see section 12.**

<a id="deliverystatus"></a>

### `DeliveryStatus`

Per-member delivery IS available (stream-chat ≥9.x): enable `delivery_events: true` on the channel type; the SDK auto-marks delivery. RN `<MessageStatus>` renders sent → delivered (grey double-check) → read (accent double-check). Not a capability gap.
