# Sendbird -> Stream Chat React: symbol & behavior mapping (Track S appendix)

The lookup tables behind [`../sendbird-migration.md`](../sendbird-migration.md). Load this file
when you migrate a touchpoint whose symbols aren't covered by the runbook's inline tables - then
migrate from the row, not from memory. **If a symbol isn't in this file either, grep
[`sendbird-mapping-extended.md`](sendbird-mapping-extended.md)** - the machine-generated long
tail (~520 more rows, all inferred, covering the APIs no sampled app used) - before falling back
to the live docs.

**Provenance & trust model.** These rows were extracted from the installed type definitions of
`@sendbird/chat` 4.21.1 + `@sendbird/uikit-react` 3.18.2 and `stream-chat` 9.x +
`stream-chat-react` v14, cross-checked against real app usage, and the code recipes compile-verified
against the real Stream v14 packages. Three rules follow:

1. **The installed package outranks this file.** If `npx tsc --noEmit` disagrees with a row, the
   compiler is right - a newer major may have renamed the symbol (see
   [`RULES.md`](../RULES.md) > Docs-first).
2. Where a row touches a Stream component's *current* props/hooks rather than the cross-SDK
   mapping itself, fetch the matching page from [`docs-map.md`](docs-map.md) before building.
3. Rows marked **(inferred)** were derived from type definitions without a real-app usage sample -
   treat them as strong hypotheses and verify with the compiler.

---

## 1. Init, auth & user

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `SendbirdChat.init({ appId, modules })` | `new StreamChat(apiKey)` or `useCreateChatClient` | No modules array - one client exposes everything. **`StreamChat.getInstance(apiKey)` is a bare process-wide singleton NOT keyed by apiKey** - a second call with a different key silently returns the first client. Client-side, use `useCreateChatClient` (strict-mode safe, per [`RULES.md`](../RULES.md) > Strict mode). |
| `sdk.connect(userId, authToken?)` | `client.connectUser({ id, name, image }, tokenOrProvider)` | **Sendbird's token-less userId-only connect has NO Stream equivalent** - Stream always requires a signed JWT. `client.devToken(id)` works only while "Disable Auth Checks" is ON for the Stream app; otherwise mint real tokens (see runbook > Credentials). |
| `SendbirdChat.setSessionHandler` + `onSessionTokenRequired(resolve, reject)` | `tokenProvider: () => Promise<string>` passed as `tokenOrProvider` | `resolve(token)` -> `return token`; `reject(err)` -> `throw err`. **A plain string token never refreshes** - anything with expiry needs the function form. |
| `onSessionRefreshed` / `onSessionClosed` / `onSessionError` | - (gap) | No session-lifecycle callbacks; observe `connection.changed` and token-provider failures. |
| `ConnectionHandler` (7-callback reconnect state machine) | `client.on('connection.changed' \| 'connection.recovered', cb)` | Reconnection is automatic in both; Stream reports it via events, not a handler object. |
| `sdk.disconnect()` | `client.disconnectUser()` | Call before switching users / on logout. `useCreateChatClient` tears down on unmount. |
| `sdk.currentUser` | `client.user` (+ `client.userID`) | Field renames everywhere: `userId` -> `id`, `nickname` -> `name`, `profileUrl` -> `image`. |
| `sdk.appId` | `client.key` | Accessor -> plain property. |
| `updateCurrentUserInfo({ nickname, profileUrl })` | `client.partialUpdateUser({ id: client.userID, set: { name, image } })` | No dedicated current-user method. `profileImage` file upload has no equivalent - upload first, then set the URL. |
| `User.createMetaData` / `updateMetaData` / `deleteMetaData` | `client.partialUpdateUser({ id, set: {...} })` / `{ unset: [key] }` | No separate metaData map - custom data is top-level user fields; values widen from string-only to any JSON. |
| `UserOnlineState` enum | `user.online` (boolean) + `user.last_active` | - |
| Guest / anonymous connect | - | Stream's guest/anonymous users are NOT a substitute for userId-only login - different permission model. |

## 2. Channels: model & queries

Sendbird has three channel **classes**; Stream has **one** `Channel` class whose behavior comes from
a server-configured **type string** passed to `client.channel(type, id?)`.

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `GroupChannel` | `client.channel('messaging', id)` (`'team'` for workspace-style) | `channel.watch()` loads state and subscribes. |
| `OpenChannel` + `.enter()` / `.exit()` | `client.channel('livestream', id)` + `channel.watch()` / `stopWatching()` | No enter/exit; `participantCount` -> `channel.state.watcher_count` / `.watchers`, live via `user.watching.start/stop` events. Render with `<VirtualizedMessageList>` (section 12). |
| `FeedChannel` / `NotificationMessage` | - (gap) | No equivalent in stream-chat. Approximate with a frozen/admin-post-only channel, or Stream's separate Feeds product (different SDK, separate integration). |
| `isDistinct: true` (dedupe by member set) | `client.channel('messaging', { members: [...] })` with **no id** | (inferred) Stream derives a deterministic id from the member set. Passing an explicit id disables the dedupe. |
| `isSuper` / `isBroadcast` / `isPublic` flags | - | Not per-channel flags: scale/broadcast/discoverability are the channel **type's** server-side config + permission grants. The web client picks a type; it cannot define one. |
| `GroupChannelModule.createChannel(params)` | `client.channel(type, id?, { members, ...custom })` then `await channel.create()` | `invitedUserIds`/`operatorUserIds` -> one `members` array (+ `assignRoles` for moderators). A client-chosen id makes `create()` idempotent (find-or-create in one call). |
| `GroupChannelModule.getChannel(url)` | `client.channel(type, id)` | Synchronous handle; `watch()` loads state. |
| `GroupChannel.refresh()` | explicit `channel.watch()` or `channel.query()` | Both refetch when called explicitly. The trap sits one level up: the React `<Channel>` **component** skips its mount-time `watch()` when `channel.initialized` is already true, so re-mounting `<Channel>` is NOT a refresh - call watch/query yourself. |
| `GroupChannel.updateChannel(params)` | `channel.updatePartial({ set: { name, image, ... } })` | Or `channel.update(data)` (full replace - wipes unlisted custom fields). |
| `GroupChannel.delete()` | `channel.delete({ hard_delete: true })` | **Stream soft-deletes by default; Sendbird's delete is permanent** - a 1:1 port silently changes data retention. |
| `GroupChannel.hide({...})` / `.unhide()` | `channel.hide(userId?, clearHistory?)` / `channel.show()` | `HiddenChannelFilter` -> `queryChannels` filter `{ hidden: true\|false }`. |
| `GroupChannel.markAsRead()` | `channel.markRead()` | Stream pre-throttles this; delete any 1-req/sec self-throttle ported from Sendbird. |
| `GroupChannel.markAsUnread(message)` | `channel.markUnread({ message_id: message.id })` | - |
| `GroupChannelListOrder` enum | `ChannelSort` object, e.g. `{ last_message_at: -1 }` | - |
| Channel metadata / meta counters (`createMetaData`, `createMetaCounters`, ...) | `channel.updatePartial` read-modify-write | **Not atomic** (inferred) - Sendbird's dedicated endpoints were; serialize concurrent writers app-side if it matters. |

## 3. Messages: sending & state

One Stream message shape replaces Sendbird's class hierarchy (`BaseMessage` / `UserMessage` /
`FileMessage` / `MultipleFilesMessage` / `AdminMessage`): discriminate via `message.type` and
`message.attachments`.

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `channel.sendUserMessage(params)` -> `MessageRequestHandler` | `await channel.sendMessage({ text, ... })` | Optimistic local message inserted immediately; resolved promise = succeeded, throw = failed. **Do NOT also append on success** - see runbook > Kill list (echo double-add). |
| `.onPending()` / `.onSucceeded()` / `.onFailed(errorCode)` | `message.status` transitions + try/catch | `'sending' \| 'received' \| 'failed'`. Failure detail is an error object on the local message, not a numeric code. |
| `SendingStatus` (5 values) | `message.status` (3 values) | `PENDING` -> `'sending'`, `SUCCEEDED` -> `'received'`, `FAILED` -> `'failed'`. **`SCHEDULED` and `CANCELED` have no equivalent** (see Feature gaps). |
| Optimistic identity: `reqId` swapped for `messageId` on success | Stable client-generated UUID | Stream's optimistic message keeps its id - delete any reqId-reconciliation code. |
| Failed-message queue + `removeFailedMessage(reqId)` | - (gap) | Failed sends live inline in `channel.state.messages` with `status: 'failed'`. |
| Resend: `channel.resendMessage(failed)` + `isResendable` | `useChannelActionContext().retrySendMessage(localMessage)` (or the `useRetryHandler` hook) | React-layer API - there is no resend method on the core `Channel`; with the raw client, re-call `channel.sendMessage`. No `isResendable` - any `status: 'failed'` message can be retried. |
| `channel.updateUserMessage(id, params)` | `client.updateMessage` / `client.partialUpdateMessage` | Message edits are client-level in Stream. |
| `channel.deleteMessage(message)` | `client.deleteMessage(messageId, hard?)` | Client-level; soft by default. |
| `channel.pinMessage` / `unpinMessage` | `client.pinMessage(message, timeoutOrExpiration?)` / `client.unpinMessage` | Client-level, with optional expiry. |
| `channel.copyMessage(msg, targetChannel)` | - (gap) | No server copy - read the source and `targetChannel.sendMessage({...content})`; the return shape differs from `MessageRequestHandler`. |
| `channel.translateUserMessage(msg, langs)` | `client.translateMessage(messageId, language)` | - |
| `message.isAdminMessage()` / `AdminMessage` | `message.type === 'system'` | - |
| Threads: `msg.getThreadedMessagesByTimestamp(ts, params)` | `channel.getReplies(parentId, { limit, id_lt })` | Timestamp anchor -> id cursor; response is `{ messages }` without a bundled parent. Send replies with `parent_id` (+ `show_in_channel`). |
| Message metadata (`addMessageMetaArrayValues`, meta counters) | `client.partialUpdateMessage` read-modify-write | Same atomicity warning as channel metadata. |
| `MessageFilter` (type/customType/sender for a collection) | - | No message-filter object; fold into `channel.query` params or `client.search`. |

## 4. Attachments & media

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `FileMessage` / `MultipleFilesMessage` | One message with `attachments: Attachment[]` | `type: 'image' \| 'file' \| 'video' \| 'audio'` per entry. Stream mixes images + files freely in one message (Sendbird could not). |
| `channel.sendFileMessage(params)` - uploads AND sends atomically | `channel.sendImage/sendFile` (CDN upload only) then `channel.sendMessage({ attachments })` | **Two steps in Stream.** In React, don't hand-roll it - `MessageComposer`'s built-in `AttachmentManager` owns the upload pipeline and per-file upload state. |
| `onFileUploaded` progress callbacks | Per-file upload state on the composer's `AttachmentManager` StateStore | - |
| `UploadedFileInfo` (per file of a multi-file message) | One `Attachment` | Build from `SendFileAPIResponse`: `url` -> `asset_url`/`image_url`, `fileName` -> `title`, `fileSize` -> `file_size`, plus `mime_type`. |
| `thumbnailSizes` -> `Thumbnail[]` pre-generated | Single CDN `thumb_url` + resize via URL query params | (inferred) Request sizes at render time instead of send time. |
| `AppInfo.uploadSizeLimit` client-side check | Server config surfaced as a `'blocked'` upload state | Size/extension limits are app config in Stream, not a client constant. |
| Voice messages (`useVoicePlayer`, `VoiceMessageItemBody`) | `useAudioPlayer`, `<VoiceRecording attachment>`; recording via `MessageComposer`'s audio recorder | `useVoicePlayerContext` (one-at-a-time playback) -> `useActiveAudioPlayer()`. Fetch the Audio Recorder / Voice Recording Attachment pages from [`docs-map.md`](docs-map.md) before wiring. |
| File/media viewer for arbitrary types | - (gap, inferred) | Stream's viewer handles image/video only. |

## 5. Events & real-time

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `new GroupChannelHandler({ onMessageReceived, ... })` + `addGroupChannelHandler(key, h)` / `removeGroupChannelHandler(key)` | `client.on(eventType, cb)` / `channel.on(eventType, cb)` -> `{ unsubscribe }` | Keyed registration -> retained unsubscribe handle called in the effect cleanup. Events arrive only for **watched** channels. |
| Named typed callbacks (`onMessageReceived`, `onMessageUpdated`, `onTypingStatusUpdated`, `onUserMarkedRead`, ...) | One `(event: Event) => void` per string type (`'message.new'`, `'message.updated'`, ...) | Every `event` field is optional - narrow by `event.type`. Granularity differs: one `onTypingStatusUpdated` = `typing.start` + `typing.stop`; one `onReactionUpdated` = `reaction.new`/`.updated`/`.deleted`. |
| Sendbird does NOT echo your own sent message | Stream DOES (`message.new` fires for your own send, on top of the optimistic insert) | The single most common runtime bug in real migrations - see runbook > Kill list. |
| `MessageCollection` + `setMessageCollectionHandler` (`onMessagesAdded/Updated/Deleted`) | `channel.watch()` loads `channel.state.messages`; `channel.on('message.new'\|'message.updated'\|'message.deleted')` keeps it live | No collection object. `collection.dispose()` -> call every retained `unsubscribe()`. |
| `MessageCollectionInitPolicy.CACHE_AND_REPLACE_BY_API` (`onCacheResult` + `onApiResult`) | `await channel.watch()` (resolves once, network-backed) | (gap) No cache-first callback on web - drop the cache branch, render after `watch()`. |
| `onHugeGapDetected` + changelog APIs | `client.sync()` / reactive recovery on `connection.recovered` | Gap-fill after reconnect is automatic for watched channels. |
| `UserEventHandler` | `client.on('user.presence.changed' \| 'notification.mutes_updated' \| ..., cb)` | - |
| Manually applying cached poll/reaction events | Auto-applied to reactive state | (inferred) Delete the manual apply-event fold code. |

## 6. Typing, presence, read state

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `startTyping()` / `endTyping()` + app-managed timeout | `channel.keystroke()` (self-throttles, auto-emits stop) | Delete the manual timer; `stopTyping()` exists but is usually unnecessary. `MessageComposer` calls keystroke for you. |
| `typingIndicatorThrottle` (ms) | on/off toggle only; throttling internal | - |
| `getTypingUsers()` (pull) | `channel.state.typing` + typing events (`useTypingContext().typing` in React) | - |
| Presence: poll `connectionStatus` on an interval | `client.queryUsers(..., { presence: true })` once, then `user.presence.changed` events | Real-time push replaces the poll loop - delete the interval. |
| `getUnreadMemberCount(message)` / `getUndeliveredMemberCount` (per-message receipts) | `readBy` / `deliveredTo` on the message (`<MessageStatus>` renders them) | **Stream keeps read data only for the latest own message by default** - set the `returnAllReadData` prop on `<MessageList>` for Sendbird-style per-message receipts. |
| `channel.unreadMessageCount` (live property) | `channel.countUnread()` (method) + `channel.state.read` | Global totals live on the own-user object / `notification.mark_read` events. |
| Read marking on open | `markRead()` is throttled, auto-marked on mount/scroll, and Stream intentionally keeps the unread separator visible | Don't "fix" the separator - it's by design. |

## 7. Pagination: every stateful cursor dies

Sendbird queries are stateful objects (`.next()` / `.hasNext`); Stream calls are stateless. This is
the largest mechanical-but-not-codemod-safe transform in the whole migration - convert each:

| Sendbird query | Stream call | Paging |
|---|---|---|
| `GroupChannelCollection` / `createMyGroupChannelListQuery` | `client.queryChannels({ members: { $in: [me] } }, sort, options)` | offset = `channels.length`; in React prefer `<ChannelList>` / `usePaginatedChannels` (they dedupe by `cid`; offset pages over a reordering list can duplicate/skip rows the collection used to reconcile). |
| `createPublicGroupChannelListQuery` | `queryChannels` with a discoverable-type filter | offset/limit |
| `OpenChannelListQuery` | `queryChannels({ type: 'livestream', ... })` | offset/limit |
| `MessageCollection.loadPrevious()` / `loadNext()` | `channel.query({ messages: { limit, id_lt: oldestId } })` (or `id_gt`) | id cursor, not timestamp |
| `startingPoint` timestamp jump | `useChannelActionContext().jumpToMessage(messageId, limit?, highlightDuration?)` (+ `jumpToLatestMessage()`) | Message-id anchor, one call - it also replaces any hand-rolled scroll+highlight timer. Raw client: `channel.query({ messages: { id_around } })`. |
| `ApplicationUserListQuery` | `client.queryUsers(filters, sort, { offset, limit })` | `nicknameStartsWithFilter` -> `{ name: { $autocomplete } }`, `userIdsFilter` -> `{ id: { $in } }` |
| `BlockedUserListQuery` | `client.getBlockedUsers()` | No paging - returns the full `blocks` array. |
| `BannedUserListQuery` / `createBannedUserListQuery` | `client.queryBannedUsers({ channel_cid? }, sort, { offset, limit })` | Read `response.bans[]`. |
| `createOperatorListQuery` | `channel.queryMembers({ channel_role: 'channel_moderator' }, sort, { offset, limit })` | - |
| `MessageSearchQuery` | `client.search(channelFilters, queryOrMessageFilters, options)` | `options.next` token or offset. |
| Member lists | `channel.queryMembers(filter, sort, options)` | - |
| Thread replies (`getThreadedMessagesByTimestamp`) | `channel.getReplies(parentId, { limit, id_lt })` | id cursor. |
| `ScheduledMessageListQuery` | - | Feature gap (below). |

Two behavioral notes: Sendbird's `hasNext` is server-authoritative; Stream's equivalents are a
count-vs-limit heuristic (a short page = end). And guard reconnect reloads with `<ChannelList>`'s
`recoveryThrottleIntervalMs` (>= 2000ms) instead of porting hand-rolled refresh throttles (inferred).

**Not every Sendbird channel-list filter has a server-side Stream equivalent.**
`UnreadChannelFilter` (unread-only) and member-name search (`nicknameContainsFilter`) can't be
expressed in the `queryChannels` filter. In `<ChannelList>`, apply them client-side with
`channelRenderFilterFn` reading `channel.countUnread()` / `channel.state.members` - not a query
filter. (`{ hidden: true }` for the archived list *is* a server filter and stays in `queryChannels`.)

## 8. Membership, roles & moderation

**The most dangerous mismap in the whole migration lives here** - see the `muteUser` row.

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `channel.invite(users)` / `inviteWithUserIds(ids)` | `channel.inviteMembers(ids)`; invitee calls `channel.acceptInvite()` / `rejectInvite()` | `acceptInvitation(accessCode?)` -> `acceptInvite()`; `declineInvitation()` -> `rejectInvite()`. |
| `channel.join(accessCode?)` | `channel.addMembers([client.userID])` | No dedicated self-join; subject to permission grants. |
| `channel.leave()` | `channel.removeMembers([client.userID])` (+ `stopWatching()`) | - |
| `myRole: Role` (`OPERATOR` \| `NONE`) | `channel.state.membership.channel_role` | Binary flag -> layered roles + server-configured permission grants. `OPERATOR` -> `'channel_moderator'`, `NONE` -> `'channel_member'`. Confirm the channel type's grants actually give the role the ban/mute/delete rights the app relied on. |
| `addOperators(ids)` / `removeOperators(ids)` | `channel.addModerators(ids)` / `channel.demoteModerators(ids)` | Or `channel.assignRoles([{ user_id, channel_role }])` for custom roles. |
| `channel.muteUser(user, duration?)` - **operator-enforced silencing**, visible to all via `Member.isMuted` | timed `channel.banUser(id, { timeout, reason })` | **`client.muteUser` is the WRONG target**: in Stream it is a personal, caller-scoped notification mute that does not stop the target from posting. Reserve it for an "I don't want to hear from X" feature. **Convert the duration: Sendbird seconds -> Stream `timeout` minutes.** |
| `blockUser(user)` - **global** (hides messages everywhere) | `client.blockUser(id)` - **DM-only** | To approximate global hiding, additionally `client.muteUser(id)` and filter with the mute state. Unblock is `client.unBlockUser(id)` - note the capital B. Read state via `client.getBlockedUsers()` (no `isBlockedByMe` flag). |
| `channel.report(category, desc)` | - (gap) | No channel-report endpoint - flag a representative message instead. |
| `reportMessage` / `reportUser` + `ReportCategory` enum | `client.flagMessage(id, { reason })` / `client.flagUser(id, { reason })` | No category enum - fold the category label into the free-text `reason`. |
| `channel.freeze()` / `unfreeze()` + built-in `FrozenNotification` banner | `channel.updatePartial({ set: { frozen: true } })` | A data field, not a method; no built-in banner - build one, gated on the acting user's permissions. |
| `channel.banUser(user, durationSec?, desc?)` / `unbanUserWithUserId` | `channel.banUser(id, { timeout?, reason? })` / `channel.unbanUser(id)` | Pass the user **id**, not the User object, and **convert seconds -> minutes** (`timeout` is minutes - a 1:1 port makes every ban 60x longer). Channel-scoped like Sendbird; Stream adds app-wide ban (`client.banUser`/`unbanUser`) and shadow ban (`removeShadowBan`) - `channel.unbanUser` reverses only the channel-scoped ban. |
| End-user actions vs. review UI | - | Reminder: [`RULES.md`](../RULES.md) > Moderation is Dashboard-only - port report/block/mute actions, never build a review queue. |

## 9. Polls

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `PollModule.create(params)` | `client.createPoll(pollData)` then `channel.sendMessage({ poll_id })` | Poll rides a message. |
| `channel.votePoll(pollId, optionIds)` | `client.castPollVote(messageId, pollId, { option_id })` | **One option per call** - loop for multi-select. |
| `allowMultipleVotes: true` | `enforce_unique_vote: false` | **The boolean inverts.** Both trial migrations flagged this. |
| `channel.addPollOption` / `closePoll` | `client.createPollOption(pollId, { text })` / `client.closePoll(pollId)` | `PollStatus` enum -> `poll.is_closed` boolean. |
| Hand-rolled re-fetch on `onPollVoted` / `onPollUpdated` | `client.polls.fromState(pollId)` + `useStateStore` (reactive) | Delete the event-fold machinery - Stream's poll state is first-class reactive. The idiomatic rewrite is smaller than the port. |

## 10. Search

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `createMessageSearchQuery(params)` + `.next()` | `client.search(channelFilters, query, options)` | Stateless; `MessageSearchOrder` -> sort argument. |
| UIKit `<MessageSearch>` / `MessageSearchPannel` (single-channel) | `channel.search()` + your own results UI | `SearchController` / `<SearchContextProvider>` is for **cross-channel** search - only reach for it if the panel searched everything, not one channel. Row renderer -> `MessageSearchResultItem` via the search results UI's component map. |

## 11. Push notifications

`stream-chat-react` itself has **no device-push registration** - its "notifications" guidance is
in-app toasts. Device push is `stream-chat` client calls + your service worker.

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `registerFCMPushTokenForCurrentUser` / `registerAPNSPushToken...` | `client.addDevice(token, push_provider, userID?, push_provider_name?)` | One call, provider as an argument. |
| `unregisterFCMPushTokenForCurrentUser` etc. | `client.removeDevice(token)` | (inferred) Must run **before** `disconnectUser()`; no "unregister all" helper - track tokens app-side. |
| `getPushTriggerOption` / cached accessors | `client.user?.push_preferences` | (inferred) Sync cached reads become async/derived - `setPushPreferences` is write-only. |
| `channel.setMyPushTriggerOption(option)` (per-channel mute) | `client.setPushPreferences([{ channel_cid, chat_level }])` | `PushTriggerOption` enum -> `chat_level` values. |
| `setPushTemplate` at runtime | - (gap) | Templates are Dashboard/server-side only. |
| Recurring Do-Not-Disturb quiet hours (with timezone) | - (gap) | Only one-shot snooze maps (`disabled_until`). |

## 12. UI components (UIKit -> stream-chat-react)

UIKit ships drop-in smart modules customized via `renderX` props; Stream is compositional -
assemble primitives, customize by swapping components. Whenever a row makes you write your own
component for a prebuilt region, [`RULES.md`](../RULES.md) > Reference authority gates it behind
[`custom-ui.md`](custom-ui.md) - load it first.

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `<SendbirdProvider appId userId accessToken nickname>` (connects internally) | `<Chat client={client}>` (provider only) | You build + connect the client yourself (`useCreateChatClient`). `colorSet` / `stringSet` / `dateLocale` props -> section 14. |
| `<App>` (prebuilt full application) | - | No equivalent - hand-compose `<Chat><ChannelList/><Channel>...</Channel></Chat>`. |
| `<GroupChannel channelUrl>` (module) | `<Channel channel={c}><Window><MessageList/><MessageComposer/></Window><Thread/></Channel>` | The single most-used Sendbird symbol in real apps. **v14 has `MessageComposer`; `MessageInput` was removed in v13->v14** (see [`../migrate.md`](../migrate.md)). |
| `<GroupChannelList>` | `<ChannelList filters sort options>` | Driven by props, not a query object. |
| `renderChannelPreview` | `<WithComponents overrides={{ ChannelListItemUI: Custom }}>` | **`ChannelList` has no `Preview` prop in v14** - the row swap goes through ComponentContext. |
| `renderMessage` | `<MessageList Message={Custom}/>` (or `WithComponents`) | Replacing the row drops every default sub-feature (reactions, receipts, grouping, ...) - that's the [`custom-ui.md`](custom-ui.md) completion contract. |
| `renderChannelHeader` / `<GroupChannelHeader>` with `renderLeft/Middle/Right` | `<ChannelHeader>` as first child of `<Window>` | **No region-override API and no ComponentContext swap key** - `HeaderStartContent`/`HeaderEndContent` inject content only; to change structure, render your own header component instead. |
| `<Thread>` module | `<Thread/>` as a sibling of `<Window>` inside `<Channel>` | To open a specific thread programmatically use `<ThreadProvider thread={t}>` - `<Thread>` has no `thread` prop (one is silently ignored). |
| `<ChannelSettings>` | `stream-chat-react/channel-detail` plugin: `<ChannelDetail>`, `ChannelDetailProvider`, `ChannelMembersView`, `ChannelManagementInfoBody` | Covers info, members browse/add/remove, pinned messages, media, files. No built-in freeze toggle - add via `ChannelManagementActionItem` custom actions. `ChannelSettingsContext` -> `useChannelDetailContext`. |
| `<CreateChannel>` / `<EditUserProfile>` / `InviteUsers` / `LeaveChannel` | - | No prebuilt equivalents: build forms over `client.channel(...).create()`, `client.partialUpdateUser`, `channel.addMembers`, `channel.removeMembers([me])`. |
| `<OpenChannel>` module | `<Channel>` on a `livestream`-type channel, with `<VirtualizedMessageList>` | **Livestream / high-message-throughput channels must render `<VirtualizedMessageList>`, not `<MessageList>`** - same `Message`-level props, plus `stickToBottomScrollBehavior` / `additionalVirtuosoProps`; fetch the VirtualizedMessageList page ([`docs-map.md`](docs-map.md)) before wiring. Participant list -> your own list over `channel.state.watchers`. |
| `<MessageSearch>` | section 10 | - |
| `TypingIndicatorType` enum (text/bubble) | `<TypingIndicator>` | Auto-rendered inside MessageList (which supplies its **required** `scrollToBottom` prop) - don't mount it bare with zero props; style via CSS. |
| `ui/MessageInput` (atomic textarea) | `TextareaComposer` (inside `MessageComposerUI`) | Match granularity: module-level `MessageInputWrapper` -> `<MessageComposer/>`. |
| `MessageItemMenu` / `MessageEmojiMenu` | `<MessageActions/>` / `<ReactionSelector/>` | To customize the action list in v14, pass `messageActionSet={[...defaultMessageActionSet, { Component, placement, type }]}` (both exported from the package root; the `.d.ts` marks them experimental) rather than the removed per-boolean props. Built-in read of the current set is `useMessageContext()`. |
| `EmojiReactions` (pill row) | `<MessageReactions/>` | Reads reaction state from MessageContext instead of message/channel props. |
| `QuoteMessage` / `QuoteMessageInput` | `<QuotedMessage/>` / `QuotedMessagePreviewUI` | `onClose` -> `onRemove`; state comes from the composer context. |
| `DateSeparator` (via `renderCustomSeparator`) | `<WithComponents overrides={{ DateSeparator }}>` | - |
| `OutgoingMessageStates` (receipt indicator) | `<MessageStatus/>` + `MessageDeliveredStatus`/`MessageReadStatus` override props | This is the read/delivery indicator, NOT the send-state machine (that's section 3). |

## 13. Context hooks & selectors

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `useSendbirdStateContext()` (one monolithic store) | Focused hooks: `useChatContext()` (client), `useChannelStateContext()` (messages/members), `useChannelActionContext()` (send/markRead/...), `useMessageContext()`, `useTypingContext()` | Replace each selector read with the specific hook - don't rebuild the monolith. |
| `sendbirdSelectors.getSdk(state)` | `useChatContext().client` | Action selectors (`getSendUserMessage`, ...) -> methods on client/channel or `useChannelActionContext()`. Drop the selector layer entirely. |
| `useGroupChannel` / `useGroupChannelContext` (`{ state, actions }` combined) | `useChannelStateContext` + `useChannelActionContext` | One hook splits into two. |
| `useGroupChannelListContext` | `useChannelListContext()` (inside `<ChannelList>`) | `{ channels, setChannels, hasNextPage, ... }`. |
| `useMessageContext` | `useMessageContext` | Same name, different shape (`MessageContextValue`: `message`, `isMyMessage()`, `handleOpenThread`, ...). |
| `useThread` / `useThreadContext` | `useThreadContext()` | Returns the Thread instance; use its methods instead of dispatched fetch actions. |
| `usePaste` | `useMessageComposerContext().onPaste` | Ready-made, bound to the active composer. |
| `withSendBird` HOC | - (gap) | Stream context is hooks-only. Convert the class component to a function component, or wrap it in a thin function adapter that calls the hooks and passes props down. |

## 14. Theming & i18n

| Sendbird | Stream | Notes / trap |
|---|---|---|
| `colorSet` JS prop (runtime CSS-var injection) | CSS custom properties (`--str-chat__*`) scoped to `.str-chat` | **No JS color prop exists in v14.** Delete the colorSet module; re-author the palette as CSS. Alias Stream's *semantic* tokens once (accent `--str-chat__accent-primary` off the `--str-chat__brand-*` ramp; bubbles `--str-chat__chat-bg-outgoing` / `--str-chat__chat-text-outgoing` / `--str-chat__chat-bg-incoming`) - they re-resolve under `.str-chat__theme-dark` automatically, so you don't duplicate every rule per theme. **Grep the installed `dist/css/index.css` for exact names** - it outranks both this file and the Theming docs page (which has been seen to drop the `--str-chat__` prefix); `--str-chat__primary-color` and other pre-v14 names no longer exist. |
| `theme="light" \| "dark"` (semantic values) | `theme="str-chat__theme-light"` etc. | **The `theme` prop of `<Chat>` is a CSS class name, not a mode string.** |
| `@sendbird/uikit-react/dist/index.css` | `import 'stream-chat-react/dist/css/index.css'` once at app entry | Forgetting it = unstyled UI. The legacy `dist/css/v2/index.css` path no longer resolves in v14; the SDK `EmojiPicker` needs its own extra CSS import. |
| `stringSet` (flat ~213 `SCREAMING_SNAKE` keys, English-only UIKit) | `Streami18n` (i18next; 12 built-in languages) | Stream's keys are the English source strings themselves - no 1:1 key mapping; re-key against Stream's English JSON via `new Streami18n({ language, translationsForLanguage })` -> `<Chat i18nInstance={...}>`. |
| `dateLocale` (date-fns) + `DATE_FORMAT__*` strings | Day.js + `timestamp/` i18n keys | Different date library and key scheme. |
| `breakpoint` / responsive prop | CSS/your own layout | - |
| RTL: provider prop | HTML `dir` attribute | - |

## 15. Feature gaps - no Stream equivalent, decision required

Each of these needs an explicit user decision (substitute / rebuild app-side / drop) recorded in
the parity ledger and routed through the plan checkpoint (runbook > Plan & checkpoint - or its
non-interactive `provisional` fallback). Never leave one as a silent TODO.

| Sendbird feature | Status | Closest substitute |
|---|---|---|
| **Scheduled messages** (`createScheduledUserMessage`, `sendScheduledMessageNow`, `cancelScheduledMessage`, list query) | No server-side scheduled send | Channel drafts (`channel.createDraft`/`getDraft`/`deleteDraft`) - saved, **never auto-sent**; or app/backend-side scheduling. |
| **Report a channel** (`channel.report`) | No channel-flag endpoint | Flag a representative (e.g. latest) message via `client.flagMessage`. |
| **`ReportCategory` enum** | Free-text `reason` only | Fold the category label into the reason string. |
| **`copyMessage`** | No server copy | Re-send content to the target channel. |
| **`FeedChannel`** (notification feed, categories, impression logging) | No stream-chat equivalent | Frozen/admin-only channel (loses categories + logging), or Stream's separate Feeds product. |
| **Offline cache** (`localCacheEnabled`, cache-first init, cache-lifecycle APIs) | Stream web ships no offline DB | Accept event-driven re-hydration (default); a custom `AbstractOfflineDB` is possible but rarely worth porting. |
| **Session lifecycle callbacks** (`onSessionRefreshed`/`Closed`/`Error`) | - | `connection.changed` + tokenProvider error handling. |
| **Runtime push template switch**; **recurring DND quiet hours** | Dashboard/server-side only; one-shot snooze only | `disabled_until` for snooze. |
| **UIKit one-liner toggles**: `enableSuggestedReplies`, `enableMarkdownForUserMessage`, `enableOgtag` previews as a config flag | No config-flag equivalents | Suggested replies: none (drop or build). Markdown rendering + link previews exist in Stream but as component/composer behavior, not provider flags - verify each against the current docs before promising parity. |
| **Category-browsable reaction picker** (inferred) | Different picker model | SDK `EmojiPicker` component (own CSS import). |
| **Friends / AI-agent conversation lists** | No concept | Model as user relations in your own backend. |
