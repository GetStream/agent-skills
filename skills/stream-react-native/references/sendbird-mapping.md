# Sendbird -> Stream Chat React Native: symbol & behavior mapping (Track S appendix)

The lookup tables behind [`../sendbird-migration.md`](../sendbird-migration.md). Load this file when
you migrate a touchpoint - then migrate from the row, not from memory. **If a symbol isn't in this
file, resolve it via [`sendbird-mapping-extended.md`](sendbird-mapping-extended.md)** (concept-level
directions + the unmapped-symbol protocol) before falling back to the live docs
([`DOCS.md`](DOCS.md)).

Import every Stream symbol from the **flavor package** - `stream-chat-react-native` (bare RN CLI) or
`stream-chat-expo` (Expo). The component/hook names are identical; only the package specifier differs
([`../sendbird-migration.md`](../sendbird-migration.md) > Flavor first). Client-layer symbols come
from `stream-chat`.

**Provenance & trust model.** These rows were extracted from the installed type definitions of
`@sendbird/chat@4.22.7` + `@sendbird/uikit-react-native@3.12.7` (`-foundation@3.12.7`) and
`stream-chat@9.50.2` + `stream-chat-react-native@9.7.0` / `stream-chat-expo@9.7.0`, cross-checked
against real usage across four sample apps, and every `after` recipe is `tsc`-verified against the
installed Stream RN types. Coverage is the **used** surface: 126 mapped symbols (93 core-SDK, 33
UIKit), of which **1** is a pure rename, ~110 are agent-guided shape-shifts/behavioral-diffs, and 28
are hard gaps (`- (gap)`). Three rules follow:

1. **The installed package outranks this file.** If `npx tsc --noEmit` disagrees with a row, the
   compiler is right - a newer major may have renamed the symbol
   ([`RULES.md`](../RULES.md) > Package version and docs discipline).
2. Where a row touches a Stream RN component's *current* props/hooks rather than the cross-SDK
   mapping itself, fetch the matching page via [`DOCS.md`](DOCS.md) before building.
3. `- (gap)` rows have **no Stream equivalent** - route them through the parity ledger and section 15's
   decision discipline (substitute / rebuild / drop), never a silent `TODO`.

`automation` legend: **codemod-safe** (1:1 auto) · **agent-guided** (mechanical + caveat) · **manual**
(gap -> `TODO(migration)`).

---

## 1. Init, auth & user

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `SendbirdChat.init({ appId, modules, localCacheEnabled })` | `new StreamChat(apiKey)` / `StreamChat.getInstance(apiKey)` | agent-guided | No modules array - one client exposes everything. **`getInstance` is a process-wide, first-call-wins singleton NOT keyed by apiKey** - a second call with a different key silently returns the first client. In RN prefer `useCreateChatClient` (strict-safe, [`RULES.md`](../RULES.md) > Client lifetime and providers). |
| `SendbirdChat.connect(userId, authToken?)` | `client.connectUser({ id, name, image }, tokenOrProvider)` | agent-guided | Takes a user **object**, not a bare id, so profile fields are set at connect. **Sendbird's token-less userId-only connect has NO Stream equivalent** - a token is always required. `client.devToken(id)` works only while dev tokens are enabled; else mint real tokens (runbook section 4). |
| `SendbirdChat.setSessionHandler` + `onSessionTokenRequired(resolve, reject)` | `tokenProvider: () => Promise<string>` as `tokenOrProvider` | agent-guided | `resolve(token)` -> `return token`; `reject(err)` -> `throw err`. Stream re-invokes it on expiry automatically - don't imperatively push a token. A plain string token never refreshes. |
| `onSessionRefreshed` / `onSessionClosed` / `onSessionError` | - (gap) | manual | No session-lifecycle callbacks. Fold refresh logic into the `tokenProvider`; for closed/error, catch the rejection and observe `isOnline === false` / `connectionRecovering` from `useChatContext`, then log out + `disconnectUser()`. |
| `ConnectionHandler` / `SendbirdChat.addConnectionHandler` / `connectionState` (`ConnectionState` enum) | `client.on('connection.changed' \| 'connection.recovered', cb)` + `useChatContext().isOnline` / `connectionRecovering` (or `useIsOnline`) | agent-guided | Reconnection is automatic - delete the reconnect state machine. Stream reports it via events + reactive context booleans, not a handler object or enum. |
| `useConnection().reconnect()` | - | manual | No `reconnect()` call - automatic. Ensure a `tokenProvider` (not a static token) so re-auth is silent across a reconnect. |
| `SendbirdChat.disconnect()` | `client.disconnectUser()` | **codemod-safe** | The one 1:1 rename. With `useCreateChatClient`, disconnect happens on unmount / `userData` change, so a manual call is only needed when switching users outside the hook. |
| `SendbirdChat.currentUser` | `client.user` (+ `client.userID`) | agent-guided | Field renames everywhere: `userId` -> `id`, `nickname` -> `name`, `profileUrl` -> `image`, `lastSeenAt` (epoch ms) -> `last_active` (ISO string - convert). |
| `updateCurrentUserInfo({ nickname, profileUrl })` | `client.partialUpdateUser({ id: client.userID, set: { name, image } })` | agent-guided | No dedicated current-user method; `set`/`unset` are field-level. Full replace via `upsertUser`. |
| `User.createMetaData` / `updateMetaData` / `deleteMetaData` | `client.partialUpdateUser({ id, set: {...} })` / `{ unset: [key] }` | agent-guided | No separate metaData map - custom data is top-level user fields; values widen from string-only to any JSON. |
| `SendbirdChatSDK` / `SendbirdChat` type | `StreamChat` | agent-guided | Replace type annotations with the `StreamChat` client instance type. |
| `SendbirdUser` | `UserResponse` (`OwnUserResponse` for self) | agent-guided | `userId`->`id`, `nickname`->`name`, `profileUrl`->`image`, metaData -> top-level custom fields. |
| `LogLevel` (init enum) | `LogLevel` string-union + `{ logger }` option | agent-guided | No init-time enum flag; filter levels inside a `logger` callback passed in `StreamChat` options. |
| Anonymous / guest connect | `client.connectAnonymousUser()` / `client.setGuestUser({ id, name })` | agent-guided | **Capability gain, not a rename** - Sendbird had no anonymous connect. Use for read-only watchers (livestream) or temporary guests; both are auth-scoped server-side (no secret on device). |

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

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `GroupChannel` / `SendbirdGroupChannel` | `Channel` of type `'messaging'` (or `'team'`) | agent-guided | `channel.url` -> `channel.cid` (`type:id`) / `channel.id`; per-kind branching -> reads of `channel.type`. `watch()` loads state and subscribes. |
| `OpenChannel` + `.enter()` / `.exit()` | `client.channel('livestream', id)` + `channel.watch()` / `stopWatching()` | agent-guided | Presence via `channel.state.watcher_count`, not enter/exit. **`read_events` is off on `livestream`** - enable client-side unread: `new StreamChat(apiKey, { isLocalUnreadCountEnabled: true })` + `markReadLocally()` / `countUnread()`. Type must be configured server-side first. |
| `FeedChannel` / `NotificationMessage` | - (gap) | manual | No equivalent in stream-chat. Approximate with an admin-post-only `messaging` channel (loses templates/categories/impression analytics), or adopt the separate Stream Feeds product. Section 15. |
| `isDistinct: true` (dedupe by member set) | `client.channel('messaging', { members: [...] })` with **no id** | agent-guided | Stream derives a deterministic id from the member set. Passing an explicit id disables dedupe. Members of a distinct channel cannot later change. |
| `isSuper` / `isBroadcast` / `isPublic` / `isDiscoverable` flags | - (gap) | manual | Not per-channel flags: scale/broadcast/discoverability are the channel **type's** server-side config + permission grants. The client picks a type name; it cannot define one. |
| `GroupChannelModule.createChannel(params)` / `createChannelWithUserIds` | `client.channel(type, id?, { members, ...custom })` then `await channel.create()` | agent-guided | `invitedUserIds`/`operatorUserIds` -> one `members` array (operators are a **server-side** role change, not a create param — see the operators row). A client-chosen id makes `create()` idempotent. Omit id + pass members for distinct/DM. **Set `name` on team channels; leave DMs nameless and derive their title from members — `name` is optional, so its presence *is* the DM-vs-channel discriminator. No custom `kind`/`slack_kind` field needed.** |
| `GroupChannelModule.getChannel(url)` / `OpenChannelModule.getChannel` | `client.channel(type, id)` then `await channel.watch()` | agent-guided | Synchronous handle; `watch()` loads state. **Carry the type alongside the id** - you can't resolve a channel from an id alone (`cid` = `type:id`). |
| `GroupChannel.updateChannel(params)` | `channel.updatePartial({ set: { name, image, ... } })` | agent-guided | Prefer `updatePartial` over `channel.update` (full replace wipes unlisted custom fields). `coverUrl` -> `image`. **Trap (permissions):** the default `messaging` type allows `update-channel` for the channel **owner** (creator) only. A **non-owner member** calling `updatePartial`/`update` on channel data fails — even though Sendbird lets members update channel info by default. Know which party owns each channel-data write and design around it; this is a behavioral difference to be aware of. |
| `GroupChannel.delete()` | `channel.delete()` (soft) | agent-guided | **Stream soft-deletes by default; Sendbird's delete is permanent** - a 1:1 port silently changes retention. |
| `GroupChannel.hide()` / `.unhide()` | `channel.hide(userId?, clearHistory?)` / `channel.show()` | agent-guided | No `isHidden()` getter; read the `hidden` boolean off the query response. |
| `GroupChannel.markAsRead()` | `channel.markRead()` | agent-guided | Near-rename. `<Channel>` auto-marks read; delete manual timers (kill-list #14). Requires "Read Events" enabled on the channel type. |
| `GroupChannelListOrder` enum | `ChannelSort` object, e.g. `{ last_message_at: -1 }` | agent-guided | `LATEST_LAST_MESSAGE` -> `{ last_message_at: -1 }`, etc. |
| `GroupChannelFilter` (setter methods) | `ChannelFilters` object literal | agent-guided | e.g. `{ type: 'messaging', members: { $in: [uid] } }`. **Search both fields** (Sendbird `channelNameContainsFilter` + `nicknameContainsFilter`): **channel name** -> `{ name: { $autocomplete: q } }`, **member name** -> `{ 'member.user.name': { $autocomplete: q } }` — both are first-class `ChannelFilters` keys (confirm in the installed `stream-chat` types). A 1:1/DM channel usually has **no `name`**, so a name-only filter misses it — the `member.user.name` filter is what finds DMs. Reproduce Sendbird's name+nickname search with a single `$or`: `{ ...base, $or: [{ name: { $autocomplete: q } }, { 'member.user.name': { $autocomplete: q } }] }` — **annotate the filter `: ChannelFilters`** so the `$or` array gets its `ArrayTwoOrMore` contextual type (an un-annotated array literal is inferred as a plain array and rejected — tsc-verified). Two merged queries also work if you prefer. Do **not** load channels and filter client-side — that only searches the first page. **A transient/secondary search `queryChannels` (a search screen, a picker) should pass `{ watch: false, state: true }`** — you don't need live updates on search results, and the default `watch: true` opens channel subscriptions whose events get re-processed by any live `<ChannelList>` still mounted **elsewhere in the nav stack** (native-stack keeps the list screen you navigated *from* mounted in the background), causing repeated re-querying — the "search keeps reloading" loop, visible as spammed `client._buildSort()` warnings. (`watch: false` is verified to eliminate it; that the re-query is specifically the background `ChannelList` vs the client's channel-state machinery is inferred.) `state: true` still loads members/messages so result rows render. Also **`member.user.name` search works with a user token** (not server-only) — an empty result is almost always the *connected* user genuinely having no matching channel, so log the actual filter (`members.$in` shows who you're querying as) before blaming the SDK. Memoize `filters`/`sort` so `<ChannelList>` re-queries. |
| Channel metadata / meta counters | `channel.updatePartial` read-modify-write | agent-guided | No atomic counter primitive - Sendbird's dedicated endpoints were atomic; serialize concurrent writers app-side if it matters. |
| `getChannelWithoutCache` / `serialize` / `buildChannelFromSerializedData` | `channel.query()` / re-`client.channel().watch()` | manual | Channels aren't serialized in Stream; rebuild from `(type,id)` + `watch()`/`queryChannels`. |

## 3. Messages: sending & state

One `MessageResponse` shape replaces Sendbird's class hierarchy (`BaseMessage` / `UserMessage` /
`FileMessage` / `MultipleFilesMessage` / `AdminMessage`): discriminate via `message.type`
(`'regular' | 'system' | 'ephemeral' | 'error' | 'reply' | 'deleted'`) and `message.attachments`.

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `channel.sendUserMessage(params)` -> `MessageRequestHandler` | `await channel.sendMessage({ text })` **via the UI path** | agent-guided | **Only the UI-context send is optimistic** - `channel.sendMessage` on the client inserts no pending message. Send through `MessageComposer` / `useMessageInputContext().sendMessage`, or override `<Channel doSendMessageRequest>`. Kill-list #1. |
| `.onPending()` / `.onSucceeded()` / `.onFailed(code)` | `message.status` (`MessageStatusTypes`) + try/catch | agent-guided | Drop the callback chain. `PENDING`->`'sending'`, `SUCCEEDED`->`'received'`, `FAILED`->`'failed'`. `SCHEDULED`/`CANCELED` have no equivalent (section 15). |
| Optimistic identity: `reqId` swapped for `messageId` on success | Stable client-generated id | agent-guided | Delete `reqId` reconciliation - Stream keeps one id across the lifecycle (list keys, retry, edit, delete). Kill-list #2. |
| `channel.resendMessage(failed)` + `isResendable` | `retrySendMessage(message)` from `useMessagesContext` | agent-guided | Default `MessageList` renders tap-to-retry on failed messages, so custom resend UI is usually unnecessary. Pass the failed `LocalMessage`; no user-vs-file branch. |
| `removeFailedMessage(reqId)` | `removeMessage(message)` from `useMessagesContext` | agent-guided | Local-only cleanup of a failed/optimistic message. |
| `channel.updateUserMessage(id, params)` / `updateFileMessage` | `client.updateMessage(message)` / `client.partialUpdateMessage(id, { set, unset })` | agent-guided | Edit is **client-level**, keyed by id; one path for text and files. Prefer `partialUpdateMessage` (full `updateMessage` can clobber `attachments`). |
| `channel.deleteMessage(message)` | `client.deleteMessage(messageId, hard?)` | agent-guided | Client-level, by id; **soft by default** (reappears as `type: 'deleted'`). |
| `MessageType` / `isUserMessage()` / `isFileMessage()` / `isAdminMessage()` | `message.type` + `message.attachments.length` | agent-guided | `isAdminMessage` -> `type === 'system'`; `isFileMessage`/`isMultipleFilesMessage` -> `attachments.length > 0`; `isUserMessage` -> `'regular'` with text + no attachments. |
| `AdminMessage` | `MessageResponse` with `type === 'system'` | agent-guided | No sender user; render via the `MessageSystem` override. Generated server-side. |
| `customType` / `data` (two reserved slots) | arbitrary top-level custom fields, or a custom `attachment.type` | agent-guided | Stream persists nested JSON directly (no stringify); route custom rendering through `attachment.type` + the `UnsupportedAttachment` override. |
| `silent` flag | `type: 'ephemeral'` **or** `options.skip_push` | agent-guided | **Not identical** - Sendbird `silent` = persisted-but-quiet; Stream `ephemeral` = transient. For persisted-but-no-push, send a `regular` message with `skip_push`, not `ephemeral`. |
| Threads: `msg.getThreadedMessagesByTimestamp(ts, params)` | `channel.getReplies(parentId, { limit, id_lt })` | agent-guided | Timestamp anchor -> id cursor; response `{ messages }` without a bundled parent. Send replies with `parent_id` (+ `show_in_channel`). |
| `ReplyType` enum (`NONE`/`ALL`/`ONLY_REPLY_TO_CHANNEL`) | - (gap) | manual | No per-query enum. `show_in_channel: true` on a reply makes it also appear in the main list; there is no toggle to hide all replies from the list. |
| `channel.copyMessage(msg, target)` | - (gap) | manual | No server copy - read the source and `target.sendMessage({ ...content })`; the return shape differs. |
| `channel.translateUserMessage(msg, langs)` | `client.translateMessage(msg.id, lang)` (per language) | agent-guided | Read results from `message.i18n`. Requires translation enabled on the app. |

## 4. Attachments & media

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `FileMessage` / `MultipleFilesMessage` | one message with `attachments: Attachment[]` | agent-guided | `type: 'image' \| 'file' \| 'video' \| 'audio' \| 'giphy'` per entry. Stream mixes images + files freely in one message (Sendbird's multi-file bundle was images-only). |
| `channel.sendFileMessage(params)` (uploads AND sends atomically) | `channel.sendImage`/`sendFile` (CDN upload) then `channel.sendMessage({ attachments })` | agent-guided | **Two steps.** In practice don't hand-roll it - `MessageComposer`'s `AttachmentManager` owns the upload->attach->send pipeline and per-file state. |
| `sendMultipleFilesMessage` | one `channel.sendMessage({ attachments: [...] })` | agent-guided | Stream was multi-attachment from the start - no special call. Cap via `AttachmentManager.maxNumberOfFilesPerMessage`. |
| `onFileUploaded` progress callbacks | `AttachmentManager` upload state (`AttachmentLoadingState`) | agent-guided | `'uploading' \| 'finished' \| 'failed' \| 'blocked' \| 'pending'` per file, not a callback. |
| `UploadedFileInfo` fields | one `Attachment` | agent-guided | `url` -> `asset_url`/`image_url`, `fileName` -> `title`, `fileSize` -> `file_size`, `type` -> `mime_type`, `thumbnails` -> `thumb_url`. |
| `thumbnailSizes` -> `Thumbnail[]` pre-generated | single CDN `thumb_url` | manual | No server-side multi-size thumbnails; resize client-side. For **video**, generate a poster frame yourself and set `attachment.thumb_url` before sending. |
| `AppInfo.uploadSizeLimit` / `multipleFilesMessageFileCountLimit` (server) | `AttachmentManager` config (`maxNumberOfFilesPerMessage`) + 100 MB Stream cap | agent-guided | Count limit moves client-side; use `availableUploadSlots()` to gate the attach button. Pre-upload compression is a `doFileUploadRequest` hook on `<Channel>`, not a param. |
| `cancelUploadingFileMessage` | `AttachmentManager.cancelAttachmentUploads()` / `clearAttachments()` | agent-guided | For manual uploads cancelled pre-send, call `channel.deleteImage(url)` / `deleteFile(url)` to avoid orphaned CDN files. |
| Voice messages (Sendbird `enableVoiceMessage: true`) | built-in `AudioPlayer` / `AudioRecorder` + `useAudioRecorder` | agent-guided | **Recording is OPT-IN: `<Channel audioRecordingEnabled>` defaults to `false`** (confirm in the pinned Channel source), so Sendbird's `enableVoiceMessage: true` maps to *setting this prop* — omit it and you silently drop voice messages (the composer shows a send button at rest instead of a mic; a "Ported" claim here is meaningless unless you saw the mic render). Needs an audio package installed — Expo SDK 53+: `expo-audio`; expo-av on older; RN CLI: the audio matrix in [`CHAT-REACT-NATIVE.md`](CHAT-REACT-NATIVE.md#optional-dependency-map) (`stream-chat-expo` lists `expo-audio`/`expo-av` as optional peers). The recorder UI tints from `semantics.accentPrimary` / `chatWaveformBar(Playing)` — recolour those too. The record button renders on the simulator but capture needs a real device (no mic on the sim). Confirm exact symbol names against the installed package / [`DOCS.md`](DOCS.md). |

## 5. Events & real-time

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `new GroupChannelHandler({ onMessageReceived, ... })` + `addGroupChannelHandler(key, h)` / `removeGroupChannelHandler(key)` | `client.on(type, cb)` / `channel.on(type, cb)` -> `{ unsubscribe }` | agent-guided | Keyed registration -> retained `unsubscribe` handle called in effect cleanup. **Drop the string-key bookkeeping.** Events arrive only for **watched** channels. |
| Named typed callbacks (`onMessageReceived`, `onMessageUpdated`, `onTypingStatusUpdated`, `onUserMarkedRead`, ...) | one `(event) => void` per string type (`'message.new'`, `'message.updated'`, `'typing.start'`/`'typing.stop'`, `'message.read'`, ...) | agent-guided | Narrow by `event.type`. Granularity differs: one `onTypingStatusUpdated` = `typing.start` + `typing.stop`. |
| Sendbird does NOT echo your own send | Stream UI components subscribe to WS events internally | agent-guided | **Don't hand-wire message listeners to update the list** - `MessageList` re-renders from events automatically. Subscribe by hand only for side-effects the components don't own (badges, analytics, nav). |
| `MessageCollection` + `setMessageCollectionHandler` (`onMessagesAdded/Updated/Deleted`) | `channel.watch()` loads `channel.state.messages`; `channel.on(...)` keeps it live | agent-guided | No collection object. Mount `<Channel><MessageList/></Channel>` and read context hooks. `collection.dispose()` -> call the retained `unsubscribe()`s (unmount handles teardown; no `dispose` to look for). |
| `MessageCollectionInitPolicy.CACHE_AND_REPLACE_BY_API` (`onCacheResult` + `onApiResult`) | `await channel.watch()` (offline hydration automatic) | manual | No cache-first callback pair. With `enableOfflineSupport` the SDK loads local state first, then reconciles from the API transparently. |
| `onHugeGapDetected` + changelog APIs | automatic reconnect recovery / `client.sync(cids, lastSyncAt)` | manual | Gap-fill after reconnect is automatic (`recoverStateOnReconnect`). Delete the changelog-rebuild logic. |
| `UserEventHandler` (`onTotalUnreadMessageCountChanged`, blocked/unblocked) | `client.on(e => ...)` reading `e.total_unread_count`, etc. | agent-guided | Unread totals ride ordinary events; block/unblock surface via user-level events + `client.getBlockedUsers()`. |
| `FeedChannelHandler` | `notification.message_new` / `notification.added_to_channel` / `notification.removed_from_channel` | manual | No feed-channel product; `notification.*` events fire on the client for member (non-watched) channels. |

## 6. Typing, presence, read state

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `startTyping()` / `endTyping()` + app timeout | `channel.keystroke()` (self-throttles, auto-emits stop) / `channel.stopTyping()` | agent-guided | Delete the manual timer; `MessageComposer` calls `keystroke()` for you. Toggle with the `sendTypingEvents` Channel prop. |
| `typingIndicatorThrottle` (ms) | - (gap) | manual | No client-configurable throttle; the SDK debounces internally. Throttle your own `keystroke()` calls if driving typing manually. |
| `getTypingUsers()` (pull) / `TypingIndicatorType` enum | `useTypingContext().typing` + built-in `<TypingIndicator>` | agent-guided | In preview rows use `useChannelTypingState({ channel }).usersTyping`. Filter out your own id. |
| Presence: `connectionStatus` / poll on interval | `client.queryUsers(..., { presence: true })` once + `user.presence.changed` events | agent-guided | Real-time push replaces the poll. Stream tracks presence only for users you subscribed to (`presence: true`), else `online`/`last_active` may be stale. |
| Presence UI (baked into UIKit avatars) | `OnlineIndicator` + `useUserActivityStatus` + `useChannelOnlineMemberCount` | agent-guided | `useIsOnline` is the **current user's own** connectivity, not another user's presence - don't confuse them. |
| `getReadMembers()` / `getReadStatus()` / `getUnreadMembers()` / `isReadMessage()` (per-member) | `channel.state.read` (`ChannelReadStatus` keyed by userId) + `channel.lastRead()` | agent-guided | Read receipts must be enabled per channel type ("Read Events") or `markRead()` is a no-op. Derive readers from `read[userId].last_read >= message.created_at`. |
| `channel.unreadMessageCount` / `unreadMentionCount` (live props) | `channel.countUnread()` / `countUnreadMentions()` (methods) | agent-guided | Global totals via `client.getUnreadCount()` (async) + `e.total_unread_count` on events. No per-channel "unread reply count" - thread unread is `Thread.ownUnreadCount`. |
| `getDeliveryStatus` / `getUndeliveredMemberCount` / `markAsDelivered` | `channel.messageReceiptsTracker` (`deliveredForMessage` / `deliveredNotReadForMessage` / `hasUserDelivered`) + `message.delivered` event; RN renders it in the default `<MessageStatus>` | agent-guided | **Per-member delivery IS supported (stream-chat ≥9.x — verified in 9.50.2).** Enable `delivery_events: true` on the channel *type* (via `UpdateChannelType`/`chat.updateChannelType`, not only the dashboard); the SDK auto-marks delivery (`markChannelsDelivered` / `syncDeliveredCandidates`) so drop explicit `markAsDelivered`. `<MessageStatus>` shows three tiers on outgoing messages: single check (sent) → **grey** double-check (`deliveredToCount > 1`) → **accent** double-check (read). The delivered tier only advances when the recipient's client is connected to emit `message.delivered`, and is transient (skipped when the reader has the channel open). Was previously (wrongly) documented as "no per-member delivery" — corrected. |

## 7. Pagination: every stateful cursor dies

Sendbird queries are stateful objects (`.next()` / `.load()` / `.hasNext`); Stream calls are
stateless. Convert each; in UI, the prebuilt components paginate for you.

| Sendbird query | Stream call | Paging |
|---|---|---|
| `createMyGroupChannelListQuery` / `GroupChannelCollection` | `client.queryChannels({ members: { $in: [me] } }, sort, options)` | offset = `channels.length`; in UI prefer `<ChannelList>` (dedupes by `cid`, live updates). Its `channelNameContainsFilter` / `nicknameContainsFilter` search args -> `{ name: { $autocomplete } }` / `{ 'member.user.name': { $autocomplete } }` server-side filters (section 2), **not** a client-side filter over a loaded page. |
| `createPublicGroupChannelListQuery` | `queryChannels` with a discoverable-type filter | offset/limit |
| `OpenChannelListQuery` / `createOpenChannelListQuery` | `queryChannels({ type: 'livestream', ... })` | offset/limit |
| `MessageCollection.loadPrevious()` / `loadNext()` | `channel.query({ messages: { limit, id_lt: oldestId } })` (or `id_gt`) | id cursor, not timestamp/offset. UI: `usePaginatedMessageListContext().loadMore` / `loadMoreRecent`. |
| `createPreviousMessageListQuery().load()` | same as above; for open channels, `channel.query({ messages: { limit } })` after `watch()` | id cursor. `MessageList` loads older pages on scroll automatically. |
| `startingPoint` timestamp jump | `channel.state.loadMessageIntoState(messageId)` (or `channel.query({ messages: { id_around, limit } })`); `loadLatestMessages()` for the tail | message-id anchor |
| `getMessagesByTimestamp` | `channel.query({ messages: { created_at_around: <ISO>, limit } })` | convert epoch-ms -> ISO first |
| `createApplicationUserListQuery` | `client.queryUsers(filters, sort, { offset, limit })` | `userIdsFilter` -> `{ id: { $in } }`, `nicknameStartsWithFilter` -> `{ name: { $autocomplete } }` |
| `BannedUserListQuery` | `client.queryBannedUsers({ channel_cid? }, sort, { offset, limit })` | read `response.bans[]` |
| `createOperatorListQuery` | `channel.queryMembers({ channel_role: 'channel_moderator' }, sort, options)` | - |
| `createMemberListQuery` | `channel.queryMembers(filter, sort, options)` | `MemberStateFilter.INVITED/JOINED` -> filter on `invited` |
| `MessageSearchQuery` / `createMessageSearchQuery` | `client.search(channelFilters, query, { limit, next })` | `next` cursor, not `hasNext` |
| `createThreadedParentMessageListQuery` | `client.queryThreads(options)` (cross-channel inbox) | returns `Thread` objects |
| Thread replies (`getThreadedMessagesByTimestamp`) | `channel.getReplies(parentId, { limit, id_lt })` | id cursor |
| `ScheduledMessageListQuery` | - | Feature gap (section 15). |

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

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `channel.invite(users)` / `inviteWithUserIds(ids)` | `channel.inviteMembers(ids)`; invitee calls `acceptInvite()` / `rejectInvite()` | agent-guided | Pass **ids**, not `User` objects. Use `addMembers` instead if your app auto-accepts invites (immediate membership, no pending state). |
| `channel.join(accessCode?)` | `channel.addMembers([client.userID])` (private) or `watch()` (open) | agent-guided | No dedicated self-join; drop `accessCode` and move access control to channel-type permissions. |
| `channel.leave(shouldRemoveOperatorStatus?)` | `channel.removeMembers([client.userID])` (+ `stopWatching()`) | agent-guided | Open-channel `exit()` -> `stopWatching()`. `shouldRemoveOperatorStatus` has no analog (roles drop on leave). |
| Remove another member (no client method in Sendbird) | `channel.removeMembers(ids)` | agent-guided | Stream has a first-class client-side remove (Sendbird required server/ban). |
| `myRole: Role` (`OPERATOR` \| `NONE`) / `Member.role` | `channel.state.membership.channel_role` + `own_capabilities` | agent-guided | Binary flag -> layered roles + server-configured grants. `OPERATOR` -> `'channel_moderator'`. **There is no `owner` channel_role — the channel owner is `channel.data.created_by`.** **Editing the channel differs by default: in Sendbird any group-channel member can update channel info (name/cover); in Stream the default channel types grant `update-channel` only to the owner (`created_by`) + moderators/admins, so a regular member's `channel.update`/`updatePartial` is rejected server-side.** Gate any edit-channel UI on the `update-channel` own-capability (don't show it to plain members), or loosen the channel type's grants server-side if the app truly relied on member editing. **Gate UI on `useChannelOwnCapabilities` / `useCanAddMembersToChannel`, not a role-string check.** Capability strings (`update-channel`, `update-channel-members`, `ban-channel-members`, `delete-any-message`, …) are enumerated in `stream-chat-react-native-core`'s `OwnCapabilitiesContext` — read them there, don't invent slugs. |
| `addOperators(ids)` / `removeOperators(ids)` | `channel.addModerators(ids)` / `channel.demoteModerators(ids)` — **server-side only** | GAP (server-side) | **`addModerators` / `demoteModerators` / `assignRoles` / `partialUpdateMember`, and `addMembers` with a `channel_role`, are privileged role changes — a normal user token cannot grant/revoke roles, so they must NOT appear in client code.** Do them from a backend/server SDK and record a migration gap. The only client-safe membership calls are role-less: `addMembers(ids)` / `removeMembers(ids)`. |
| `channel.muteUser(user, duration?)` - **operator-enforced silencing** | timed `channel.banUser(id, { timeout, reason })` | agent-guided | **`client.muteUser` is the WRONG target** - it is a personal, caller-scoped mute that does NOT stop the target from posting. Reserve it for an "I don't want to hear from X" feature. Kill-list #5. |
| `blockUser(user)` - **global** | `client.blockUser(id)` - **DM-only** | agent-guided | Blocked users still post in shared group channels. Filter client-side or ban/moderate for group hiding. `unBlockUser(id)` (capital B); read state via `getBlockedUsers()`. |
| `channel.report(category, desc)` | - (gap) | manual | No channel-report endpoint - flag a representative message instead. |
| `reportMessage` / `reportUser` + `ReportCategory` enum | `client.flagMessage(id, { reason })` / `client.flagUser(id, { reason })` | agent-guided | No category enum - fold the category into the free-text `reason` (e.g. `` `${category}: ${desc}` ``). Build your own category picker. `flagMessage` is also a built-in message action. |
| `channel.freeze()` / `unfreeze()` + `ChannelFrozenBanner` | `channel.updatePartial({ set: { frozen: true } })` | agent-guided | A data field, not a method; no built-in banner - read `frozen` / the `disabled` ChannelContext flag, set `disableIfFrozenChannel`, and render your own banner. |
| `channel.banUser(user, durationSec?, desc?)` / `unbanUserWithUserId` | `channel.banUser(id, { timeout?, reason? })` / `channel.unbanUser(id)` | agent-guided | Pass the user **id**; **convert duration -> minutes** (`timeout = Math.round(ms/60000)`; confirm the Sendbird unit). Stream adds app-wide (`client.banUser`) + shadow ban (`shadowBan`/`removeShadowBan`). Kill-list #6. |

## 9. Search

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `createMessageSearchQuery(params)` + `.next()` | `client.search(channelFilters, query, options)` | agent-guided | Stateless; full-text search must be enabled on the app. `MessageSearchOrder` -> a `SearchMessageSort` object (`{ created_at: -1 }`); relevance is the default. |
| `MessageFilter` (type/customType/sender) | `MessageFilters` object folded into `client.search` | agent-guided | Rebuild as `{ type, 'attachments.type', user_id: { $in } }`; no message-filter class. |
| UIKit `createMessageSearchFragment` | `Channel.search` / `MessageSearchSource` + your own results list | manual | No prebuilt RN search screen. |

## 10. Push notifications

`stream-chat-react-native` ships **no notification-service abstraction** - unlike Sendbird UIKit's
`createNativeNotificationService` / `createExpoNotificationService`. Wire React Native Firebase /
Notifee yourself and call the client methods (fetch the manifest-selected Push page via
[`DOCS.md`](DOCS.md) before wiring).

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `registerFCMPushTokenForCurrentUser` / `registerAPNSPushTokenForCurrentUser` | `client.addDevice(id, push_provider, userID?, push_provider_name?)` | agent-guided | One call; `push_provider` is `'apn' \| 'firebase' \| 'huawei' \| 'xiaomi'`. Call **after** `connectUser`. `push_provider_name` must match a dashboard-configured provider. |
| `unregister...` / `unregister...All` | `client.removeDevice(id)` | agent-guided | No "remove all" helper - `getDevices()` then `removeDevice` each. On token refresh: `removeDevice(old)` then `addDevice(new)`. |
| (no client list) | `client.getDevices(userID?)` | agent-guided | Enumerate + prune stale tokens (Stream lacks Sendbird's auto-dedupe). |
| `setPushTriggerOption(PushTriggerOption)` (account-wide) | `client.setPushPreferences([{ chat_level }])` | agent-guided | `ALL`/`OFF`/`MENTION_ONLY` -> `'all'`/`'none'`/`'mentions'` (+ optional snooze). `addDevice`/`removeDevice` remains a valid coarse toggle. |
| `channel.setMyPushTriggerOption(option)` (per-channel) | `client.setPushPreferences([{ channel_cid, chat_level }])` | agent-guided | **Prefer `setPushPreferences` — it preserves the 3-way ALL/MENTION_ONLY/OFF (`chat_level: 'all'`/`'mentions'`/`'none'`).** `channel.mute()`/`unmute()` is a binary fallback that DROPS the "mentions only" tier, so don't default to it for a trigger-option port. Read the current value from `channel.push_preferences.chat_level`; requires the push-preferences feature enabled on the app. |
| `setDoNotDisturb` / `setWeeklyDoNotDisturb` (recurring quiet hours + timezone) | - (gap) | manual | Only one-shot snooze maps (a `disabled_until`-style window). Reimplement recurring DND yourself. |
| `setPushTemplate` at runtime | - (gap) | manual | Templates are per-provider dashboard/server config (`upsertPushProvider`), not a runtime client switch. |
| `markPushNotificationAsDelivered` / `AsClicked` (analytics) | - (gap) | manual | No client analytics calls; wire open-handling/navigation in your Notifee/messaging handlers. |

## 11. UI components (UIKit -> stream-chat-react-native / stream-chat-expo)

UIKit ships drop-in **fragment factories** customized via `renderX` props; Stream RN is
compositional - assemble primitives, customize by swapping components. Whenever a row makes you write
your own component for a prebuilt region, fill the completion contract in
[`design-matching.md`](design-matching.md) Step 2.5 (sub-feature inheritance) first. **There is no
`<Window>` in RN** (web-only) and **no `ChannelHeader` slot inside `<Channel>`** (the header is
app-owned - your React Navigation / Expo Router header).

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `SendbirdUIKitContainer` (`appId`, `platformServices`, connects internally) | `useCreateChatClient({ apiKey, tokenOrProvider, userData })` + `<OverlayProvider><Chat client={client}>` | agent-guided | One container -> three pieces. `appId` -> `apiKey`; `platformServices` are **dropped** (Stream RN handles media/file/clipboard/player/recorder internally). |
| `_default` (SendbirdUIKit namespace) | - (gap) | manual | No single namespace export - import `Chat`, `ChannelList`, `Channel`, ... directly. |
| `createGroupChannelFragment` / `GroupChannelMessageRenderer` | `<Channel channel={c}><MessageList/><MessageComposer/></Channel>` (+ `Message` override) | agent-guided | `renderMessage`-style overrides -> component-swap props on `<Channel>`. **No `<Window>`.** |
| `createGroupChannelListFragment` | `<ChannelList filters sort options onSelect Preview />` | agent-guided | Row/preview overrides -> the `Preview` prop, not a module override. Pass `channel.cid` through navigation, not the `Channel` object. |
| `createGroupChannelThreadFragment` | `<Channel channel={c} thread={t}><Thread/></Channel>` | agent-guided | Set the thread via channel context; no dedicated thread fragment factory. |
| `FileViewer` | `<ImageGallery>` (mounted by `OverlayProvider`) | agent-guided | Full-screen image viewing triggered from attachments; non-image files open via the platform (no single FileViewer). |
| `TypingIndicatorType` | `<TypingIndicator>` (auto-rendered inside `MessageList`) or `useTypingString()` | agent-guided | Remove the enum-based config. |
| `createGroupChannelCreateFragment` | - (gap) | manual | No prebuilt create screen - build a user picker then `client.channel('messaging', { members }).create()`/`watch()`. |
| `createGroupChannelMembersFragment` | - (gap) | manual | Build on `Object.values(channel.state.members)` / `channel.queryMembers` + the channel-details contexts. |
| `createGroupChannelInviteFragment` | - (gap) | manual | Use `ChannelAddMembers*` contexts + `channel.inviteMembers`/`addMembers`. |
| `createGroupChannelModerationFragment` / `Operators` / `RegisterOperator` / `MutedMembers` / `BannedUsers` | - (gap) | manual | No prebuilt moderation/operator screens - compose from **client-safe** ops (`banUser`/`muteUser`/`removeMembers`) + `useChannelOwnCapabilities` gating. **Operator promote/demote is server-side only: build the Operators screen read-only and move role changes to a backend. `RegisterOperator` (a client-side promote screen) has no client equivalent — omit it.** |
| `createGroupChannelSettingsFragment` / `Notifications` | - (gap) | manual | Build from `channel.update`/`updatePartial` and the **push-preference API (`client.setPushPreferences([{ channel_cid, chat_level }])`)** for the notification trigger — not `channel.mute()`, which is binary and loses the mentions tier. |
| `createMessageSearchFragment` | - (gap) | manual | Section 9. |

## 12. Context hooks & selectors

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `useSendbirdChat()` | `useChatContext()` | agent-guided | `sdk`/`currentUser` -> `client` + `client.user`/`client.userID`. |
| `useConnection()` (`connect`/`disconnect`/`reconnect`) | `useCreateChatClient` (lifecycle) or `client.connectUser`/`disconnectUser` | agent-guided | Delete manual reconnect logic (automatic). |
| `useGroupChannel` / `useGroupChannelContext` (`{ state, actions }`) | `useChannelContext()` + `useMessagesContext()` + `useMessageInputContext()` | agent-guided | One hook splits into focused contexts; fetch via `client.channel(type,id).watch()` and render inside `<Channel>`. |
| `useGroupChannelList` | `useChannelsContext()` (inside `<ChannelList>`) | agent-guided | `loadNextPage`/`hasNextPage`; the list does live updates for you. |
| `useUIKitTheme()` | `useTheme()` | agent-guided | Returns `{ theme }` in Stream's `Theme` shape - color/typography keys differ. |
| `useMessageContext` | `useMessageContext` (different shape) | agent-guided | `MessageContextValue`: `message`, `isMyMessage()`, handlers, ... |
| `usePushTokenRegistration` | - (gap) | manual | No hook - call `addDevice`/`removeDevice` in your own effects. |

## 13. Theming & i18n

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `createTheme` / `colorSet` / `Palette` (JS, from `-foundation`) | `DeepPartial<Theme>` object on **both** `<OverlayProvider value={{ style }}>` **and** `<Chat style={…}>` | agent-guided | **No CSS/DOM on native.** The theme object carries **color AND spacing/dimension**, so most reskins are theme-only. Confirm exact keys against the installed package + Theming page ([`DOCS.md`](DOCS.md)); read at runtime via `useTheme()`. |
| `LightUIKitTheme` / `DarkUIKitTheme` | `defaultTheme` deep-merged + `useColorScheme()` selection | agent-guided | No `theme="light"\|"dark"` prop - build two theme objects and select on the RN `useColorScheme()`; pin brand colors, keep chrome adaptive. |
| `createBaseStringSet` / `StringSet` | `Streami18n` (i18next; `registerTranslation`/`setLanguage`) -> `<Chat i18nInstance={…}>` | agent-guided | Stream's keys are the English source strings themselves - re-key, no 1:1 key map. |
| `dateLocale` / date format strings | Day.js + `timestamp/` i18n keys | agent-guided | Different date library and key scheme. |

**Custom fields need TS module augmentation.** Stream's `Custom*Data` interfaces are empty by default,
so custom channel/user/message fields don't typecheck (`tsc` errors "does not exist in type …").
Augment them: `declare module 'stream-chat' { interface CustomChannelData {…}; interface CustomUserData
{…}; interface CustomMessageData {…} }`. Note `name` belongs on `CustomChannelData` (it's `Omit`-ed
inside `ChannelFilters`), so declare it there if you set or filter on it.

## 14. Offline & sync

| Sendbird | Stream | Automation | Notes / trap |
|---|---|---|---|
| `localCacheEnabled` / `initializeCache` (AsyncStorage) | `enableOfflineSupport` on `<Chat>` + `@op-engineering/op-sqlite` | agent-guided | Native SQLite, not a declarative flag; Expo needs a dev client (not Expo Go). Call `connectUser` before rendering but **don't await** it so components render from the DB while the socket connects. |
| `LocalCacheConfig` (`maxSize`, `clearOrder`, `enableAutoResend`, encryption) | - (gap) | manual | The OfflineDB is self-managed - no size/eviction/encryption knobs. Drop the tuning; auto-resend comes free with offline support (a persisted pending-task queue: sends, deletes, reactions, drafts). |
| `clearCachedData()` / `clearCachedMessages(url)` | `await client.offlineDb.resetDB()` (DB-wide) before `disconnectUser()` | agent-guided | The app's responsibility on sign-out - prevents cross-user leaks. No per-channel clear. Kill-list #11. |
| `MessageCollection.dispose()` / `GroupChannelCollection.dispose()` | - | manual | No collection to dispose - unmounting `<Channel>`/`<ChannelList>` tears down; `stopWatching()` only to stop server events. Don't over-migrate looking for `dispose`. |

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
