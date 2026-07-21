# Sendbird -> Stream Chat React Native: extended concept map & long-tail resolution (Track S appendix 2)

The companion to [`sendbird-mapping.md`](sendbird-mapping.md). Where the curated file maps the
**126 used symbols** at the symbol level, this file handles everything outside that set: the
**concept-level model map** (the domain reasoning behind the symbol rows) and the **protocol for
resolving an unmapped symbol**.

**How this differs from the web Track S long-tail.** The web (`stream-react`) extended file is ~520
*inferred* symbol rows derived from type definitions but never exercised. The RN corpus is
**grounded-only**: every row in [`sendbird-mapping.md`](sendbird-mapping.md) was extracted from real
sample-app usage and `tsc`-verified. There is deliberately **no inferred RN symbol table here** -
emitting one would be guessing, which the trust model forbids. So for a symbol not in the curated
file, you **resolve by concept + live types**, not by reading a pre-baked row.

Load order when migrating a symbol:

1. [`sendbird-mapping.md`](sendbird-mapping.md) - curated, `tsc`-verified rows. Check it first.
2. **This file - the concept map below.** Find the domain, read the Sendbird->Stream *direction*,
   then pick the concrete Stream symbol from the installed types.
3. On a miss: the live docs via [`DOCS.md`](DOCS.md) and the installed package under the target app's
   `node_modules` ([`RULES.md`](../RULES.md) > Package version and docs discipline).

---

## The unmapped-symbol protocol (three tiers)

Every `@sendbird/*` symbol the detector finds falls into one tier. Never skip one, and never emit an
unverified Stream symbol:

- **`mapped`** - has a row in [`sendbird-mapping.md`](sendbird-mapping.md). Apply it: an
  `agent-guided` rewrite, or a `manual` gap -> `TODO(migration): <workaround>`.
- **`unmapped-known`** - a real Sendbird API with no curated row (no sampled app used it). **Resolve
  it here:** find the concept domain below, read the direction, choose the Stream symbol, confirm it
  exists in the installed Stream RN types (`node_modules/stream-chat-react-native-core`,
  `node_modules/stream-chat`), and verify the rewrite with `npx tsc --noEmit`.
- **`unknown`** - imported from `@sendbird` but not in the indexed SDK surface. Almost always a
  version skew; check against the Sendbird version the target actually has installed before treating
  it as anything else.

**Confidence tags** below: **V** = VERIFIED (AST/usage-backed) · **I** = INFERRED (docs/reasoning).

---

## Concept map (domain-level directions)

### connection-auth
- **Client init:** `SendbirdChat.init({ appId })` -> `new StreamChat(apiKey)` / `getInstance` (in RN,
  `useCreateChatClient`). `appId` -> `apiKey`. `getInstance` is first-call-wins, not keyed by key. **(V)**
- **Connect:** `connect(userId, authToken?)` -> `connectUser({ id, name, image }, tokenOrProvider)` -
  a user **object** + a required token; no userId-only auto-create. **(V)**
- **Token refresh:** `SessionHandler.onSessionTokenRequired` -> a declarative `tokenProvider`
  function; no register-handler step, refresh is automatic. **(V)**
- **Connection state:** `ConnectionState` enum + `ConnectionHandler` -> `connection.changed` /
  `connection.recovered` events + `isOnline` / `connectionRecovering` on `useChatContext`. **(I)**
- **Anonymous/guest:** `connectAnonymousUser()` / `setGuestUser()` - a **capability gain** over
  Sendbird's throwaway-userId pattern. **(V)**

### users-presence
- **User object:** `userId`->`id`, `nickname`->`name`, `profileUrl`->`image`, `metaData` map ->
  top-level custom fields, `lastSeenAt` (ms) -> `last_active` (ISO). **(V)**
- **Profile update:** `updateCurrentUserInfo` -> `partialUpdateUser({ id, set, unset })`. **(V)**
- **Presence:** `connectionStatus`/`lastSeenAt` (pushed automatically) -> `online`/`last_active`,
  tracked only for users subscribed with `{ presence: true }`; `user.presence.changed` events.
  Prefer `useUserActivityStatus` / `OnlineIndicator` / `useChannelOnlineMemberCount`. **(V)**

### channel-types
- **Model:** three classes (`GroupChannel`/`OpenChannel`/`FeedChannel`) -> **one** `Channel` +
  `type` string (`messaging`/`team`/`livestream`/... or custom). Replace `isGroupChannel()`/
  `isOpenChannel()` with `channel.type` checks. **(V)**
- **GroupChannel -> `messaging`/`team`**; **OpenChannel -> `livestream`** (enter/exit ->
  `watch`/`stopWatching`); **FeedChannel -> gap** (admin-only channel or Stream Feeds product). **(V/I)**
- **Distinct:** `isDistinct` flag -> omit the channel id + pass `members`. **(V)**
- **isSuper/isBroadcast/isPublic/isDiscoverable:** client flags -> server-side channel-type config +
  permissions (not client-settable). **(I)**
- **customType:** decide per-app - promote to a Stream channel type (if it implies rules) or keep as
  custom channel data (if purely a label). **(I)**

### membership-roles
- **List members:** `channel.members` array + `createMemberListQuery().next()` ->
  `Object.values(channel.state.members)` + `channel.queryMembers(filter, sort, options)`. **(V)**
- **Add/remove:** `invite`/`inviteWithUserIds` -> `inviteMembers(ids)` (or `addMembers` for
  auto-accept); Stream adds client-side `removeMembers`. **(V)**
- **Roles:** binary operator -> `channel_role` (`channel_moderator`) + `own_capabilities`;
  `addOperators`/`removeOperators` -> `addModerators`/`demoteModerators`/`assignRoles`. **Gate UI on
  capabilities (`useChannelOwnCapabilities`), not role strings.** **(V)**
- **Ban/mute/freeze:** see moderation. **(V/I)**

### message-kinds & message-features
- **Hierarchy:** `UserMessage`/`FileMessage`/`MultipleFilesMessage`/`AdminMessage` -> one
  `MessageResponse`; branch on `message.type` + `attachments[]`. `AdminMessage` -> `type: 'system'`. **(V)**
- **Send:** `sendUserMessage` -> `sendMessage({ text })` **via the UI path** for optimistic state;
  `sendFileMessage` -> upload + `sendMessage({ attachments })`. **(V)**
- **customType/data:** -> arbitrary custom fields or a custom `attachment.type`. **(I)**
- **silent:** -> `skip_push` on a `regular` message (NOT `type: 'ephemeral'`, which is transient). **(I)**
- **Reactions:** `addReaction(message, key)`/`deleteReaction` -> `sendReaction(messageId, { type })`/
  `deleteReaction(messageId, type)`; RN draws only reactions in the `supportedReactions` prop. **(V)**
- **Threads:** `parentMessageId` -> `parent_id` (+ `show_in_channel`); `getThreadedMessagesByTimestamp`
  -> `channel.getReplies(parentId, { id_lt, limit })`; UIKit thread fragment -> `<Thread>` +
  `ThreadContext`. **(V)**
- **Mentions:** `mentionedUserIds` -> `mentioned_users`; `MentionType` (USERS/CHANNEL) has no
  first-class @here equivalent; unread mentions via `countUnreadMentions()`. **(V)**
- **Edit/delete:** `updateUserMessage`/`updateFileMessage` -> `updateMessage`/`partialUpdateMessage`
  (client-level, by id); `deleteMessage` -> soft delete by default (`hardDelete` to purge). **(V)**

### querying-pagination
- **Stateful cursor -> stateless call** everywhere: `GroupChannelListQuery.next()` ->
  `queryChannels(filter, sort, { limit, offset })`; `MessageCollection.loadPrevious()` ->
  `channel.query({ messages: { id_lt, limit } })`; `startingPoint` timestamp ->
  `loadMessageIntoState(messageId)` / `id_around`. `hasNext` -> count-vs-limit heuristic. **(V)**
- **Live lists/collections -> components:** `GroupChannelCollection` -> `<ChannelList>` /
  `ChannelManager`; `MessageCollection` -> `channel.watch()` + `<MessageList>`. Prefer the
  components over manual offset math (offset drifts on a live-mutating list). **(V)**

### events-listeners
- **Architecture:** many typed handler classes -> one event bus. `add/removeXHandler(key, h)` ->
  `client.on(...)`/`channel.on(...)` returning `{ unsubscribe }` (call in effect cleanup); branch on
  `event.type`. **(V)**
- **Scope:** subscribe on `Channel` for one channel, on `StreamChat` for all (filter by `e.cid`).
  Events arrive only for watched channels. **(I)**
- **UI auto-subscribes:** don't hand-wire message listeners to update the list - components re-render
  from events. Subscribe by hand only for side-effects (badges, analytics, nav). **(V)**
- **Notifications:** `FeedChannelHandler` -> `notification.*` events on the client. **(I)**

### offline-sync
- **Enable:** `localCacheEnabled` (AsyncStorage) -> `enableOfflineSupport` + `@op-engineering/op-sqlite`
  (native; Expo dev client). **(V)**
- **Cache-then-API:** `MessageCollection.initialize(CACHE_AND_REPLACE_BY_API)` + `onCacheResult`/
  `onApiResult` -> automatic (DB-first hydration on `watch()`), no callback pair. **(V)**
- **Catch-up:** `getMessageChangeLogsSince*` / `onHugeGapDetected` -> `client.sync(cids, lastSyncAt)`
  + automatic `recoverStateOnReconnect`. **(V)**
- **Tuning:** `LocalCacheConfig` (`maxSize`/`clearOrder`/encryption) -> **gap** (self-managed). **(I)**
- **Reset on sign-out:** `clearCachedData()` -> `offlineDb.resetDB()` before `disconnectUser()`. **(V)**
- **Dispose:** collection `dispose()` -> nothing (unmount handles it; `stopWatching()` only to drop
  server events). Don't over-migrate. **(I)**

### push
- **Register/unregister:** platform-specific `registerFCM/APNSPushToken...` -> one
  `addDevice(id, push_provider, ...)`; `removeDevice(id)` (+ `getDevices()` to prune). **(V)**
- **User/channel push level:** `PushTriggerOption` -> `setPushPreferences([{ chat_level }])` /
  `channel.mute()`. **(I)**
- **DND / templates / delivery analytics:** recurring DND, runtime template switch,
  `markPushAs Delivered/Clicked` -> **gaps** (snooze window / provider config / app-side handlers). **(I)**
- **RN wiring:** UIKit's `createNativeNotificationService` / `createExpoNotificationService` +
  `usePushTokenRegistration` -> **no abstraction**; wire RN Firebase / Notifee yourself and call the
  client methods in effects. **(I)**

### moderation
- **Ban:** `banUser(user, seconds/ms?, desc?)` -> `channel.banUser(id, { timeout: minutes, reason })`
  (convert units); Stream adds app-wide `client.banUser` + `shadowBan`. **(V)**
- **Mute:** operator `channel.muteUser` (silences for everyone) -> **timed `channel.banUser`**;
  `client.muteUser` is a **personal** mute, not the same thing. **(I)**
- **Freeze:** `freeze()`/`unfreeze()` + `ChannelFrozenBanner` -> `updatePartial({ set: { frozen } })`
  + your own banner. **(I)**
- **Report/flag:** `reportMessage(msg, category, desc)` -> `flagMessage(id, { reason })` (fold
  category into reason); `reportUser` -> `flagUser`; channel report -> gap. **(V)**
- **Shadow ban:** net-new Stream capability with no Sendbird source concept. **(I)**

### attachments-media
- See [`sendbird-mapping.md`](sendbird-mapping.md) section 4: no `FileMessage` type (attachments on a
  normal message), two-step upload-then-send, single `thumb_url` (no multi-size), client-side count
  limit + 100 MB cap + `doFileUploadRequest` compression hook. **(V)**

### theming & ui
- **Theme:** `createTheme`/`colorSet`/`Palette`/`Light/DarkUIKitTheme` (JS) -> a `DeepPartial<Theme>`
  object on **both** `<OverlayProvider value={{ style }}>` and `<Chat style>`, read via `useTheme()`.
  **No CSS**; the theme object carries color AND spacing/dimension. Light/dark via `useColorScheme()`. **(V)**
- **i18n:** `StringSet`/`createBaseStringSet` -> `Streami18n` on `<Chat i18nInstance>`. **(V)**
- **Fragments -> composition:** every `createGroupChannel*Fragment` -> composed primitives or a
  `manual` gap (no prebuilt members/moderation/settings/search screens); `renderX` -> component-swap
  props / `WithComponents`. **No `<Window>`; header is app-owned.** **(V)**
- **Platform services:** `createExpo*Service` (clipboard/file/media/player/recorder/notification) ->
  **dropped** (handled internally by Stream RN). **(V)**

---

## Gap catalog

The `- (gap)` / `manual` rows across the curated file and the concepts above are the features with
**no Stream equivalent**. They are enumerated with substitutes in
[`sendbird-mapping.md`](sendbird-mapping.md) section 15. Every gap is a **parity-ledger decision**
(substitute / rebuild app-side / drop) routed through the runbook's plan checkpoint
([`../sendbird-migration.md`](../sendbird-migration.md) section 2) - never a silent `TODO`.
