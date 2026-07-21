# Sendbird -> Stream Chat React Native: extended long-tail symbol mapping (Track S appendix 2)

The machine-generated long tail behind [`sendbird-mapping.md`](sendbird-mapping.md): 226 rows
covering the **806 Sendbird symbols that no sampled real app used** but an arbitrary customer
codebase might. Load order when migrating a symbol:

1. [`sendbird-mapping.md`](sendbird-mapping.md) - curated, `tsc`-verified/used rows. Check it first.
2. **This file - grep for the exact symbol; never read it end-to-end.** It is a lookup table, not
   reading material.
3. On a miss here too: the live docs via [`DOCS.md`](DOCS.md) and the installed types under the
   target app's `node_modules` ([`../RULES.md`](../RULES.md) > Package version and docs discipline).

**Trust model - every row below is INFERRED.** The Sendbird symbol + signature is real (extracted
from `@sendbird/chat@4.22.7` + `@sendbird/uikit-react-native@3.12.7`), and every Stream target was
**existence-checked** against the installed `stream-chat@9.50.2` / `stream-chat-react-native@9.7.0`
symbol inventory (3,643 names, incl. 1,376 qualified `Class.method` members) - **so no target is
invented**. But the *pairing* is a hypothesis, **not `tsc`-verified** the way the curated file's
recipes are. Treat each row as a strong candidate: `npx tsc --noEmit` against the installed package
outranks it, and where a row names current props/hooks, confirm on [`DOCS.md`](DOCS.md) before
building. `- (gap)` rows (mapping `none`) are feature gaps - route them through the parity ledger and
[`sendbird-mapping.md`](sendbird-mapping.md) section 15's decision discipline, never a silent `TODO`.

Family rows like `AIAgent* (N symbols)` collapse a whole symbol family that shares one verdict.
`automation`/mapping legend matches the curated file: shape-shift · behavioral-diff · 1-to-n · n-to-1
· none (gap).

**Coverage:** 806 unmapped symbols (687 top-level + factory-class members) -> 226 rows across 9
sections below. The unmapped-symbol resolution protocol is at the end.

---

### 1. Connection, auth, session & users/presence

| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `AuthTokenType` | `TokenOrProvider` | shape-shift | No session-vs-access token enum; Stream takes one JWT as `TokenOrProvider` (string \| `() => Promise<string>`) passed to `connectUser` / `useCreateChatClient`. |
| `Unsubscribe.onTokenRefresh` | `- (gap)` | none | No token-refresh event/subscription. Supply a `TokenProvider` at connect; Stream re-invokes it automatically on expiry, no imperative push (curated §1). |
| `createUserListModule`, `UserList*` (`UserListContexts`/`Provider`/`Type`/`Header`/`List`/`Module`/`Props`/`StatusEmpty`/`StatusError`), `UserActionBar`, `UserSelectableBar` (12 symbols) | `- (gap)` | none | No prebuilt user-list / picker module in Stream RN. Build one from `client.queryUsers` (or `channel.queryMembers`) + `Avatar` + a FlatList; gate with `useChannelOwnCapabilities`. |
| `OnlineDetectorListener` | `useIsOnline` | shape-shift | No manual online-detector listener; SDK auto-detects connectivity. Read `useIsOnline` (own socket) / `connectionRecovering`, or `client.on('connection.changed')`. |
| `ReactedUserInfo` | `ReactionResponse` | shape-shift | Reactor identity rides on `ReactionResponse.user` / `.user_id`; no separate reacted-user class. Enumerate reactors via `message.latest_reactions`. |
| `RestrictedUser` | `UserResponse` | shape-shift | No restricted-user subclass — a plain `UserResponse`. Query the restricted/banned set via `client.queryBannedUsers(...)` and read `response.bans[]`. |
| `User` | `UserResponse` / `OwnUserResponse` | shape-shift | `userId`->`id`, `nickname`->`name`, `profileUrl`->`image`, metaData->top-level custom fields, `lastSeenAt`(ms)->`last_active`(ISO). `OwnUserResponse` for self. |
| `UserOnlineState` | `UserResponse` | shape-shift | Enum collapses to boolean `UserResponse.online` (+ `last_active`). Presence only tracked for users queried/watched with `{ presence: true }`, else stale. |
| `UserUpdateParams` | `PartialUserUpdate` | shape-shift | `{ id, set?, unset? }`; `nickname`->`set.name`, `profileUrl`->`set.image`. `unset` removes a field entirely (no Sendbird analog). Values must be JSON. |
| `User.addFriends` | `- (gap)` | none | No friends / social graph in stream-chat. Model relations in your own backend; approximate with `client.queryUsers` or channel membership (curated §15). |
| `User.connect`, `User.authenticate` (2 symbols) | `client.connectUser` | shape-shift | `connectUser({ id, name, image }, tokenOrProvider)` — user object + token, not a bare id. No feed-only auth; use the full connect. Prefer `useCreateChatClient` in RN. |
| `User.updateCurrentUserInfo` | `client.partialUpdateUser` | shape-shift | `partialUpdateUser({ id: client.userID, set: { name, image } })`; field-level set/unset, no dedicated current-user method (curated §1). Full replace via `upsertUser`. |
| `User.updateCurrentUserInfoWithPreferredLanguages` | `client.partialUpdateUser` | shape-shift | No first-class `preferredLanguages`; store the array as a custom field via `set`, or drive per-message translation with `client.translateMessage`. |

### 2. Channels: model, config & queries

| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `BaseChannel` | `Channel` | shape-shift | 3 Sendbird channel classes collapse to one Stream Channel; replace isGroupChannel()/isOpenChannel() branching with reads of channel.type; url->cid. |
| `ChannelType` / `GroupChannelType` (2 symbols) | `Channel.type` | shape-shift | Kind enum -> server-configured type string: group->'messaging'/'team', open->'livestream'; SUPER_GROUP/BROADCAST are type-level config, not values. |
| `CachedChannelInfo` | - (gap) | none | No channel serialize/cache-info object; rebuild a handle from (type,id) via StreamChat.channel(type,id).watch(). |
| `FriendDiscovery` | - (gap) | none | No social-graph/friends concept in stream-chat; model relations in your backend or approximate with StreamChat.queryUsers/membership. |
| `GroupChannelCreateParams` / `OpenChannelCreateParams` (2 symbols) | `ChannelData` / `CreateChannelOptions` | shape-shift | invitedUserIds/operatorUserIds -> one members array (+assignRoles); coverUrl->image; isDistinct->omit id; isSuper/isBroadcast/isPublic->server-side type config. |
| `GroupChannelUpdateParams` / `OpenChannelUpdateParams` (2 symbols) | `Channel.updatePartial` | shape-shift | Pass fields to updatePartial({set}); coverUrl->image. Avoid full update (wipes unlisted custom fields). |
| `GroupChannelHideParams` | `Channel.hide` | shape-shift | hidePreviousMessages/allowAutoUnhide -> hide(userId?, clearHistory?); read `hidden` off the query response; unhide via show(). |
| `GroupChannelFilterParams` / `GroupChannelUserIdsFilter` / `HiddenChannelFilter` / `PublicChannelFilter` / `SuperChannelFilter` / `UnreadChannelFilter` (6 symbols) | `ChannelFilters` | n-to-1 | Filter classes+enums collapse to one filter literal, e.g. {type,members:{$in:[uid]},hidden,frozen}; memoize so <ChannelList> re-queries. |
| `InactiveChannelListOrder` / `PublicGroupChannelListOrder` (2 symbols) | `ChannelSort` | shape-shift | Order enums -> sort object: LATEST_LAST_MESSAGE->{last_message_at:-1}, CHRONOLOGICAL->{created_at:1}, etc. |
| `GroupChannelSearchField` / `GroupChannelSearchFilter` (2 symbols) | `ChannelFilters` | shape-shift | No channel-search class; fold into filters: name->{name:{$autocomplete:q}}, member->{members:{$in:[ids]}}. |
| `GroupChannelCountParams` | - (gap) | none | No channel-count endpoint; approximate with StreamChat.queryChannels result length (returns no server-side total). |
| `GroupChannel.createChannel` / `GroupChannel.createChannelWithUserIds` / `OpenChannel.createChannel` (3 symbols) | `StreamChat.channel` + `Channel.create` | shape-shift | client.channel(type,id?,{members}).create(); Open->'livestream'; ids->members array; a client-chosen id makes create() idempotent; omit id for distinct/DM. |
| `GroupChannel.createDistinctChannelIfNotExist` | `StreamChat.channel` + `Channel.watch` | behavioral-diff | Distinct = client.channel('messaging',{members}) with NO id, then watch(); Stream hashes members to a stable id; members can't later change. |
| `GroupChannel.getChannel` / `OpenChannel.getChannel` (2 symbols) | `StreamChat.channel` + `Channel.watch` | shape-shift | Synchronous handle: client.channel(type,id) then watch() hydrates. Carry the type with the id (cid=type:id); can't resolve from id alone. |
| `GroupChannel.getChannelWithoutCache` / `OpenChannel.getChannelWithoutCache` (2 symbols) | `Channel.query` | behavioral-diff | No cache-bypass variant; channel.query() (or re-watch()) refetches state from the server. |
| `InvitationPreference.getChannelInvitationPreference` / `setChannelInvitationPreference` (2 symbols) | - (gap) | none | No auto-accept-invite preference; require invitee acceptInvite()/rejectInvite(), or skip the pending state by using addMembers instead of inviteMembers. |
| `createGroupChannelModule` / `GroupChannelFragment` / `GroupChannelProps` / `GroupChannelContexts(+Provider+Type)` (6 symbols) | `Channel` + `MessageList` + `MessageComposer` | shape-shift | Fragment factory -> compositional <Channel><MessageList/><MessageComposer/></Channel>; renderX overrides -> component-swap props on <Channel>; no <Window> in RN. |
| `createGroupChannelListModule` / `GroupChannelListFragment` / `GroupChannelListProps` / `GroupChannelListList` / `GroupChannelListModule` / `GroupChannelListContexts(+Provider+Type)` (8 symbols) | `ChannelList` | shape-shift | List module/fragment -> <ChannelList filters sort onSelect Preview/>; row override -> Preview prop; pass channel.cid through navigation, not the Channel object. |
| `GroupChannelListTypeSelector` | - (gap) | none | No type-selector step; the type string is chosen in code at client.channel(type,...); build your own selector if the UX needs one. |
| `GroupChannelCreateFragment` / `GroupChannelCreateProps` (2 symbols) | - (gap) | none | No prebuilt create screen; build a user picker then client.channel('messaging',{members}).create()/watch(). |
| `createGroupChannelSettingsModule` / `GroupChannelSettingsFragment` / `GroupChannelSettingsProps` / `GroupChannelSettingsModule` / `GroupChannelSettingsInfo` / `GroupChannelSettingsMenu` / `GroupChannelSettingsContexts(+Provider+Type)` (9 symbols) | `ChannelDetails` | shape-shift | No 1:1 settings fragment; compose ChannelDetails* + channel.updatePartial/mute()/push prefs; menu items -> your own actions gated by useChannelOwnCapabilities. |
| `createOpenChannelModule` / `createOpenChannelFragment` / `OpenChannelFragment` / `OpenChannelProps` / `OpenChannelContexts(+Provider+Type)` (7 symbols) | `Channel` + `MessageList` + `MessageComposer` | shape-shift | <Channel> over client.channel('livestream',id); enter/exit->watch/stopWatching; read_events off (use isLocalUnreadCountEnabled + markReadLocally/countUnread). |
| `createOpenChannelListFragment` / `createOpenChannelListModule` / `OpenChannelListFragment` / `OpenChannelListProps` / `OpenChannelListList` / `OpenChannelListModule` / `OpenChannelListContexts(+Provider+Type)` (9 symbols) | `ChannelList` | shape-shift | <ChannelList filters={{type:'livestream'}}>; discover via StreamChat.queryChannels filter, not a per-class open-channel list query. |
| `createOpenChannelCreateFragment` / `createOpenChannelCreateModule` / `OpenChannelCreateFragment` / `OpenChannelCreateProps` / `OpenChannelCreateModule` / `OpenChannelCreateContexts(+Provider+Type)` (8 symbols) | - (gap) | none | No prebuilt create screen; build a form then client.channel('livestream',id).create(); the client picks the id (Sendbird assigned URLs server-side). |
| `createOpenChannelModerationFragment` / `createOpenChannelModerationModule` / `OpenChannelModerationFragment` / `OpenChannelModerationProps` / `OpenChannelModerationModule` / `OpenChannelModerationMenu` / `OpenChannelModerationContexts(+Provider+Type)` (9 symbols) | - (gap) | none | No prebuilt moderation/operator/muted/banned screens; compose Channel.banUser/addModerators/shadowBan + useChannelOwnCapabilities gating. |
| `createOpenChannelParticipantsFragment` / `OpenChannelParticipantsFragment` / `OpenChannelParticipantsProps` (3 symbols) | `ChannelMemberList` + `ChannelState.watchers` | shape-shift | Livestream 'participants' are watchers, not persisted members: read channel.state.watcher_count/watchers; ChannelMemberList only for true members. |
| `createOpenChannelSettingsFragment` / `createOpenChannelSettingsModule` / `OpenChannelSettingsFragment` / `OpenChannelSettingsProps` / `OpenChannelSettingsModule` / `OpenChannelSettingsInfo` / `OpenChannelSettingsMenu` / `OpenChannelSettingsContexts(+Provider+Type)` (10 symbols) | `ChannelDetails` | shape-shift | No 1:1 settings fragment; compose ChannelDetails* + channel.updatePartial; delete-channel menu -> channel.delete() (soft by default). |
| `GroupChannelHeader` / `GroupChannelListHeader` / `GroupChannelSettingsHeader` / `OpenChannelHeader` / `OpenChannelListHeader` / `OpenChannelCreateHeader` / `OpenChannelModerationHeader` / `OpenChannelSettingsHeader` (8 symbols) | - (gap) | none | No <ChannelHeader> slot inside RN <Channel> and no list-header module; the header is app-owned (React Navigation / Expo Router). |
| `ChannelInput` / `ChannelInputProps` / `GroupChannelInput` / `OpenChannelInput` (4 symbols) | `MessageComposer` | shape-shift | Input component -> <MessageComposer/>; keystroke/typing + attachment pipeline handled internally; inputDisabled -> disabled/frozen channel state. |
| `ChannelCover` / `GroupChannelPreview` / `OpenChannelPreview` (3 symbols) | `ChannelPreview` + `ChannelAvatar` | shape-shift | Preview -> <ChannelList Preview={...}>; cover -> ChannelAvatar; frozen/badge/memberCount read from channel state, not props you pass. |
| `GroupChannelStatusEmpty` / `GroupChannelListStatusEmpty` / `OpenChannelStatusEmpty` / `OpenChannelListStatusEmpty` / `OpenChannelListStatusError` (5 symbols) | `EmptyStateIndicator` / `LoadingErrorIndicator` | shape-shift | Status slots -> EmptyStateIndicator/LoadingErrorIndicator override props on <ChannelList>/<MessageList>. |

### 3. Pagination, queries & collections

| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `GroupChannelListQuery*` (5 symbols) | `client.queryChannels` / `ChannelList` | n-to-1 | Stateless client.queryChannels({members:{$in:[me]}},sort,{offset,limit}); .next()/.loadMore->offset=channels.length. UI:<ChannelList>; hasNext=short-page heuristic. |
| `GroupChannelCollection*` (11 symbols) | `ChannelManager` / `ChannelList` | n-to-1 | Live list->ChannelManager behind <ChannelList>; delete collection+handlers, read useChannelsContext().channels/loadNextPage. Filter->ChannelFilters. |
| `*.build*FromSerializedData` (8 symbols) | `- (gap)` | none | No serializable query/entity in Stream. Rebuild channels from (type,id)+watch(); re-run queryChannels/queryUsers. Drop serialize/rehydrate. |
| `PublicGroupChannelListQuery*` (3 symbols) | `client.queryChannels` | n-to-1 | client.queryChannels with a discoverable channel-type filter; offset/limit paging. No public/private query object. |
| `InactiveChannelListQuery*` (3 symbols) | `client.queryChannels` | n-to-1 | client.queryChannels with a filter (e.g. last_message_at range / {hidden:true}); no dedicated inactive-channel query. |
| `OpenChannelListQuery*` (4 symbols) | `client.queryChannels` | n-to-1 | OpenChannel->livestream channel; client.queryChannels({type:'livestream'},sort,{offset,limit}). .next()->offset paging. |
| `PreviousMessageListQuery*` (5 symbols) | `Channel.query` | n-to-1 | channel.query({messages:{limit,id_lt:oldestId}}); .load()/.next()->loadMore (PaginatedMessageListContext). id cursor; hasNext=short-page heuristic. |
| `MessageCollection*` (7 symbols) | `Channel.watch` / `MessageList` | n-to-1 | No collection; channel.watch() seeds channel.state.messages, <MessageList> pages via loadMore/loadMoreRecent. Init-policy + onCache/onApi dropped. |
| `ThreadedParentMessageListQuery*` (3 symbols) | `client.queryThreads` / `Channel.getReplies` | n-to-1 | Parent-thread inbox->client.queryThreads (Thread objs); replies->channel.getReplies(parentId,{limit,id_lt}). Stateless id cursor. |
| `PinnedMessageListQuery*` (4 symbols) | `Channel.getPinnedMessages` | n-to-1 | channel.getPinnedMessages() or read channel.state.pinnedMessages; no stateful pinned cursor. .next()->re-query with paging opts. |
| `MemberListQuery*` (4 symbols) | `Channel.queryMembers` | n-to-1 | channel.queryMembers(filter,sort,{offset,limit}); MemberStateFilter INVITED/JOINED->filter on invited. .next()->offset paging. |
| `ParticipantListQuery*` (3 symbols) | `Channel.query` / `ChannelState.watchers` | n-to-1 | Open-channel participants->watchers: channel.query({watchers:{limit,offset}}), read channel.state.watchers/watcher_count. No participant query. |
| `ApplicationUserListQuery*` (4 symbols) | `client.queryUsers` | n-to-1 | client.queryUsers(filters,sort,{offset,limit}); userIdsFilter->{id:{$in}}, nicknameStartsWith->{name:{$autocomplete}}. .next()->offset. |
| `RestrictedUser.next` (1 symbol) | `client.queryBannedUsers` | shape-shift | Muted/banned users->client.queryBannedUsers({channel_cid?},sort,{offset,limit}); read response.bans[]. RestrictedUser fields differ. |
| `FriendListQuery*` (3 symbols) | `- (gap)` | none | No social graph in Stream. Model friends in your own backend; approximate with queryUsers/membership. Route via gaps ledger. |
| `MessageSearchQuery*` (2 symbols) | `client.search` | n-to-1 | client.search(channelFilters,query,{limit,next}); next cursor, not hasNext. Full-text search must be enabled on the app. |
| `FileUpload*/Upload*` (8 symbols) | `AttachmentManager` / `Channel.sendFile` | n-to-1 | Two-step: AttachmentManager owns upload->attach->send + per-file AttachmentLoadingState. UploadedFileInfo->Attachment (url->asset_url, fileName->title). |
| `DownloadedPath*` (2 symbols) | `- (gap)` | none | UIKit download-to-disk helper; no Stream primitive. Use expo-file-system / RN-fs with attachment.asset_url; <ImageGallery> handles image viewing. |
| `*StatusLoading / LoadingSpinner` (8 symbols) | `LoadingIndicator` | n-to-1 | UIKit loading placeholders->Stream <LoadingIndicator>; list/message components auto-render ChannelListLoadingIndicator/InlineLoadingMoreIndicator. |
| `*PubSubContextPayload` (3 symbols) | `- (gap)` | none | UIKit-internal message-sent/received pubsub bridge; Stream UI owns state via contexts (useMessagesContext). No payload-type equivalent. |
| `CollectionEventSource / QueryType` (2 symbols) | `- (gap)` | none | Internal Sendbird enums (collection event source, query type); Stream events keyed by e.type strings, no query-type enum. Drop them. |

### 4. Messages, threads, reactions & mentions

| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `AppInfo` | `AppSettings` | shape-shift | App config -> client AppSettings (client.getAppSettings). uploadSizeLimit/file-count limits move to AttachmentManager config; reactions enabled dashboard-side. |
| `BaseMessageCreateParams` | `Message` | shape-shift | Send payload = Message object: message->text, mentionedUserIds->mentioned_users, parentMessageId->parent_id, customType/data->top-level custom fields. |
| `BaseMessageUpdateParams` + `UserMessageUpdateParams` (2 symbols) | `MessageUpdatableFields` | shape-shift | Edit payload; apply via client.partialUpdateMessage(id,{set,unset}) (or updateMessage full replace). One path for user+file; re-specify mentions. |
| `BaseMessage.getMessage/getMessagesByMessageId/getMessagesByTimestamp` (3 symbols) | `Channel.getMessagesById` / `Channel.query` | shape-shift | By-id -> Channel.getMessagesById; by-timestamp -> channel.query({messages:{created_at_around}}), convert epoch-ms->ISO. Stateless. |
| `MessageListParams/MessageRetrievalParams/ThreadedMessageListParams/MessageFilterParams` (4 symbols) | `MessagePaginationOptions` / `MessageFilters` / `Channel.getReplies` | shape-shift | Stateless options: prev/next size->limit + id_lt/id_gt (not offset); MessageFilterParams->MessageFilters; threaded->channel.getReplies(parentId,opts). |
| `UserMessage.copyUserMessage` | `- (gap)` | none | No server copy. Read source then target.sendMessage({...content}); return shape differs. Section 15. |
| `UserMessage.resendUserMessage` | `MessagesContext` / `MessageList` | behavioral-diff | retrySendMessage(message) from useMessagesContext; default MessageList taps failed bubble to retry. Same message id (no new handler); no user/file branch. |
| `UserMessage.translateUserMessage` | `StreamChat.translateMessage` | shape-shift | client.translateMessage(msg.id, lang) per language; read from message.i18n. Requires translation enabled on the app. |
| `UserMessage.updateUserMessage` | `StreamChat.updateMessage` / `StreamChat.partialUpdateMessage` | shape-shift | Edit is client-level by id. Prefer partialUpdateMessage(id,{set,unset}); full updateMessage can clobber attachments. One path for text+file. |
| `MessageType` | `MessageLabel` | shape-shift | Enum 'user'|'file'|'admin' -> message.type ('regular'|'system'|'ephemeral'|'error'|'reply'|'deleted') + attachments[]. admin->'system'; file = attachments.length>0. |
| `MessageModule` | `- (gap)` | none | No module system; one StreamChat client exposes send/edit/query directly. Drop the modules array. |
| `MessageForm/MessageFormItem/MessageFormItemLayout/MessageFormItemResultCount/MessageFormItemStyle` (5 symbols) | `- (gap)` | none | CSAT / message forms / submitForm have no stream-chat primitive. Model via custom message/attachment fields or external tool. Section 15. |
| `MessageReviewInfo` + `MessageReviewStatus` (2 symbols) | `- (gap)` | none | No client pre-send message-review state. Server-side Moderation review queue (queryReviewQueue) + flagMessage; reactive, nothing to call client-side. |
| `MessageTemplate/MessageTemplateListParams/MessageTemplateListResult/getMessageTemplate/getMessageTemplatesByToken` (5 symbols) | `- (gap)` | none | No message-template concept in stream-chat. Model structured content as a custom attachment.type rendered via UnsupportedAttachment. Section 15. |
| `MessageSearchContextsType/Fragment/Module/Props/ResultItem` (5 symbols) | `MessageSearchSource` / `Channel.search` | n-to-1 | No prebuilt RN search screen/fragment. Build your own results list on MessageSearchSource or client.search(channelFilters,query,{limit,next}). Section 9. |
| `OriginalMessageInfo` | `- (gap)` | none | No direct equivalent for Sendbird original-message info. Edit history (if enabled) surfaces via MessageHistoryEntry; otherwise no client shape. |
| `PinnedMessage` | `Channel.getPinnedMessages` / `MessagePinnedHeader` | shape-shift | No PinnedMessage class. Pin via channel.pin/unpin; read channel.state.pinnedMessages; list via ChannelPinnedMessageListProvider; header MessagePinnedHeader. |
| `Reaction` | `ReactionResponse` | shape-shift | Reactions live on the message: latest_reactions/own_reactions/reaction_counts. Sendbird reaction 'key' -> Stream 'type'. Aggregated server-side. |
| `ReactionAddons` + `ReactionBottomSheets` + `useReaction` (3 symbols) | `MessageReactionPicker` / `MessageUserReactions` | n-to-1 | Built-in picker + reactions/user bottom-sheet overlays. Declare the emoji palette via the Channel supportedReactions prop; no useReaction hook. |
| `ThreadInfo` | `Thread` | shape-shift | Parent carries reply_count; rich client Thread state (Thread.state, Thread.ownUnreadCount) replaces threadInfo. Consumed via ThreadContext/useThreadContext. |
| `LastMessageThreadingPolicy` + `UnreadCountThreadingPolicy` (2 symbols) | `- (gap)` | none | Threading policies are server/dashboard threading config; no client symbol. show_in_channel controls per-reply list visibility instead. |
| `createGroupChannelThreadModule` + `GroupChannelThread*` (12 symbols) | `Thread` / `ThreadContext` / `useThreadContext` | n-to-1 | No thread fragment factory. Use <Channel channel thread={t}><Thread/>; input=MessageComposer; header app-owned (React Navigation); status/empty built-in. |
| `GroupChannelMessage` + `GroupChannelMessageList` + `GroupChannelMessageProps` + `ChannelMessageList` (4 symbols) | `MessageList` | n-to-1 | renderMessage-style overrides -> Message component-swap prop on <Channel>. Bubble props -> MessageProps/MessageContextValue; ChannelMessageList -> MessageList. |
| `OpenChannelMessage` + `OpenChannelMessageProps` + `OpenChannelMessageRenderer` (3 symbols) | `MessageList` | n-to-1 | OpenChannel -> 'livestream' channel type; same MessageList + Message override. OpenChannelMessageRenderer -> Message swap; presence via watcher_count. |
| `MentionedUser` + `useMentionTextInput` + `UseMentionTextInputParams` + `UseMentionTextInputReturn` (4 symbols) | `TextComposer` / `MentionsSearchSource` | n-to-1 | Composer captures @-mentions via mentions middleware -> mentioned_users. Drop the manual useMentionTextInput hook + range/user bookkeeping. |
| `GroupChannelSuggestedMentionList` | `AutoCompleteSuggestionList` / `MentionSuggestion` | shape-shift | Built-in autocomplete list inside the composer; MentionsSearchSource feeds MentionSuggestion/MentionItem. No standalone suggested-list to wire. |
| `NewMessagesButton` | `MessageList` | shape-shift | Scroll-to-new-messages / unread indicator is rendered by MessageList automatically; no standalone button component to port. |
| `TypingIndicatorBubble` | `TypingIndicator` | shape-shift | Auto-rendered inside MessageList (or read useTypingContext().typing). Remove the manual bubble component. |
| `Member.getTypingUsers` | `useTypingContext` / `ChannelState.typing` | shape-shift | Read the typing map from context/state (channel.state.typing); filter out your own id. No pull method; events keep it live. |
| `UnreadMessageCount` + `TotalUnreadMessageCountParams` (2 symbols) | `Channel.countUnread` / `StreamChat.getUnreadCount` | shape-shift | Per-channel countUnread()/countUnreadMentions() (methods, not live props); global client.getUnreadCount(). No unread-reply count -> Thread.ownUnreadCount. |

### 5. Membership, roles & moderation
| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `GroupChannelInvite* (2 symbols)` | `ChannelAddMembersForm` + `Channel.inviteMembers` | shape-shift | UIKit invite fragment/props -> no prebuilt; build on ChannelAddMembers* + inviteMembers (pass ids); addMembers if auto-accept. |
| `GroupChannelMembers* (2 symbols)` | `ChannelMemberList` + `Channel.queryMembers` | shape-shift | Members screen fragment/props -> no 1:1 prebuilt; build on ChannelMemberList + queryMembers over ChannelState.members. |
| `Member` | `ChannelMemberResponse` | shape-shift | Class (role/state/isMuted/joinedAt) -> plain object keyed in channel.state.members; read channel_role/is_moderator/banned. |
| `Member.getReadMembers` | `MessageReceiptsTracker.readersForMessage` | shape-shift | Per-message readers -> derive from ChannelState.read / MessageReceiptsTracker; not a member method. |
| `Member.getUnreadMembers` | `MessageReceiptsTracker` | behavioral-diff | Members not yet read a message -> derive from ChannelState.read; MessageReceiptsTracker exposes read/delivered sets, no direct getter. |
| `MemberListOrder` | `MemberSort` | shape-shift | Order enum -> MemberSort object for channel.queryMembers (e.g. { created_at: -1 }). |
| `MembershipFilter` | `MemberFilters` | shape-shift | joined/invited/none enum -> MemberFilters object passed to queryMembers (filter on invite / user_id). |
| `MemberStateFilter` | `MemberFilters` | shape-shift | invited/joined enum -> filter queryMembers on ChannelMemberResponse.invited / invite_accepted_at. |
| `Role` | `ChannelRole` | shape-shift | OPERATOR/NONE enum -> channel_role strings (OPERATOR='channel_moderator', see BuiltinRoles); gate UI on capabilities not role. |
| `BannedUser* (3 symbols)` | `BannedUsersFilters` / `BannedUsersResponse` | shape-shift | createBannedUserListQuery/params -> client.queryBannedUsers(filter/sort) -> BannedUsersResponse; or read ChannelMemberResponse.banned. |
| `BlockedUser* (3 symbols)` | `BlockedUsersState` / `BlockedUserDetails` | behavioral-diff | Block-list query -> getBlockedUsers (BlockedUsersState); Stream block is DM-only, blocked users still post in shared groups. |
| `ChannelFrozenBanner` | - (gap) | none | No built-in frozen banner; freeze via channel.updatePartial({ set: { frozen: true } }), read `disabled` ChannelContext flag, render own. |
| `createOpenChannel* (7 symbols)` | - (gap) | none | Open-channel banned/muted/operators UIKit fragment+module factories; no prebuilt Stream RN; build on queryMembers + ban/moderator APIs. |
| `GroupChannelRegisterOperator* (2 symbols)` | `Channel.addModerators` | shape-shift | Register-operator screen fragment/props -> no prebuilt; build on ChannelMemberList + addModerators / assignRoles. |
| `MutedInfo* (2 symbols)` | - (gap) | none | Operator per-member muted-info / remainingDuration + getMyMutedInfo have no analog; Stream mute is personal - use timed ban expiry. |
| `MutedMemberFilter` | - (gap) | none | Filters members by muted state; Stream has no operator channel-mute, so no muted-member filter - use banned-user query instead. |
| `MutedState` | - (gap) | none | UNMUTED/MUTED enum for operator mute; no equivalent (mute is personal). Silenced state is a ban -> ChannelMemberResponse.banned/ban_expires. |
| `MutedUser* (3 symbols)` | `ChannelState.mutedUsers` | behavioral-diff | createMutedUserListQuery -> read-only ChannelState.mutedUsers/useMutedUsers (personal mutes); operator channel-mute absent, use timed ban. |
| `OpenChannel* (33 symbols)` | - (gap) | none | Open-channel banned-users/muted-participants/operators screen scaffolding (Contexts/Header/List/Status...); no prebuilt Stream RN equivalent. |
| `OperatorFilter` | `MemberFilters` | shape-shift | Filter members by operator -> filter queryMembers on channel_role='channel_moderator' (see GetMemberRoles). |
| `OperatorList* (3 symbols)` | `Channel.queryMembers` | shape-shift | createOperatorListQuery/params -> queryMembers filtered by channel_role='channel_moderator'; no dedicated operator query. |
| `OpenChannel.createChannelWithOperatorUserIds` | `Channel.create` + `Channel.addModerators` | shape-shift | Create channel with operators -> create then addModerators (or members with channel_role); no operatorUserIds param. |
| `ReportCategory* (3 symbols)` | - (gap) | none | No report-category enum/taxonomy; fold category into free-text reason of Moderation.flagMessage/flagUser. Build own category picker. |

### 6. Attachments, media & polls

| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `MultipleFiles* (5 symbols)` | `Channel.sendMessage` | n-to-1 | No MultipleFilesMessage type; upload each (sendImage/sendFile) then one sendMessage({attachments}). UI: AttachmentManager.uploadFiles; cap via maxNumberOfFilesPerMessage. |
| `FileMessage* (4 symbols)` | `Attachment` / `StreamChat.partialUpdateMessage` | n-to-1 | No FileMessage class; media is attachments[]. Edit via updateMessage/partialUpdateMessage; resendFileMessage->re-send (tap-to-retry); copyFileMessage->gap. |
| `MessageRequestHandler.sendFileMessage` / `sendFileMessages` (2 symbols) | `Channel.sendImage` / `Channel.sendFile` + `Channel.sendMessage` | 1-to-n | Two steps: upload (sendImage/sendFile)->attach URL->sendMessage({attachments}). No onPending/onSucceeded handler chain; AttachmentManager owns the pipeline. |
| `Thumbnail` / `ThumbnailSize` (2 symbols) | `Attachment` / `GenerateVideoThumbnailResult` | shape-shift | No multi-size thumbnails[] - single attachment.thumb_url; resize client-side. Video poster is your job: set thumb_url before send (gap). |
| `OGImage` (1 symbol) | `LinkPreview` / `URLPreview` | shape-shift | OG/link-preview data rides as URL enrichment on the message (LinkPreviewsManager), rendered by URLPreview. No OGImage object. |
| `FileService/FileSystem/MediaService interfaces + createNative*Service (5 symbols)` | - (gap) | none | No platformServices to register - Stream RN handles file/media/camera/clipboard internally via AttachmentManager + native pickers. |
| `FilePicker* (4 symbols)` | `AttachmentPicker` / `CameraPickerButton` / `FilePickerButton` | n-to-1 | Picker built into MessageComposer; camera/document buttons feed AttachmentManager (pick->upload->attach). No manual openCamera/openDocument calls. |
| `FileType` / `FileCompat` / `FileInfo` (3 symbols) | `FileReference` / `FileLike` | shape-shift | Stream file descriptor is FileReference/FileLike ({uri,name,size,type}); on the attachment: url->asset_url/image_url, name->title, size->file_size, type->mime_type. |
| `CompressImage* (3 symbols)` | - (gap) | none | No compress-image service. Wire compression in the <Channel doFileUploadRequest> hook (e.g. react-native-compressor) then channel.sendFile. 100 MB upload cap. |
| `GetVideo* (3 symbols)` | `VideoThumbnail` / `GenerateVideoThumbnailResult` | n-to-1 | No thumbnail service method; RN SDK renders VideoThumbnail for previews. For a video poster, generate it yourself and set attachment.thumb_url before send. |
| `OpenMediaLibraryOptions` (1 symbol) | `AttachmentMediaPicker` / `MediaPickerButton` | shape-shift | Media-library open options -> built-in media picker in the composer; selections flow into AttachmentManager. No options object to pass. |
| `VideoThumbnail` / `VideoProps` (2 symbols) | `VideoThumbnail` / `VideoThumbnailProps` | shape-shift | Near-rename: Stream ships its own VideoThumbnail (+VideoThumbnailProps); video also renders via Gallery/AnimatedGalleryVideo. Prop keys differ. |
| `Image` / `ImageWithPlaceholder` (2 symbols) | - (gap) | none | No themed Image atom exported; use RN's Image or let Gallery render image attachments (ImageBackground exists but isn't a drop-in replacement). |
| `ProfileCard` / `UserProfile* / useUserProfile` (4 symbols) | - (gap) | none | No built-in user-profile card/overlay; Sendbird's tap-avatar->profile sheet has no Stream RN analog. Build your own from client.queryUsers + a bottom sheet. |
| `OpenChannelCreateProfileInput` (1 symbol) | - (gap) | none | No prebuilt open-channel create screen (section 11). Build a form; ChannelEditDetailsForm/ChannelEditImageSheet cover name+image editing for group channels. |
| `Emoji* / EmojiCategory* / EmojiContainer* (6 symbols)` | - (gap) | none | No emoji catalog API; Stream reactions are free-form type strings. Provide your own emoji palette via the Channel supportedReactions prop. |
| `Poll* (9 symbols)` | `Poll` / `StreamChat.createPoll` | shape-shift | Ops->client/Poll: create->createPoll, addPollOption->createPollOption, closePoll->closePoll, updatePoll->updatePoll, get->getPoll; serialize/next->gap. |
| `PollCreateParams` (1 symbol) | `CreatePollData` / `PollComposer` | shape-shift | Fields->createPoll params/PollComposer. allowMultipleVotes->enforce_unique_vote (INVERTS); set max_votes_allowed, allow_user_suggested_options, voting_visibility. |
| `PollData` (1 symbol) | `PollData` / `PollResponse` | shape-shift | Field renames; poll carries options, vote_counts_by_option, latest_votes_by_option, is_closed, enforce_unique_vote - not Sendbird's status/allowMultipleVotes. |
| `PollOption* (3 symbols)` | `PollOption` / `StreamChat.getPollOption` | shape-shift | Option shape-shifts (PollOptionData); getOption->getPollOption; add/edit via createPollOption/updatePollOption. Vote tallies read from poll state. |
| `PollRetrievalParams` (1 symbol) | `StreamChat.getPoll` / `Poll.query` | shape-shift | Params for getPoll; no retrieval-params class. Poll.query() hydrates the reactive Poll state client-side. |
| `PollUpdate* (2 symbols)` | `PartialPollUpdate` / `StreamChat.updatePoll` | shape-shift | updatePoll/partialUpdatePoll (PartialPollUpdate). Update events arrive via WS (poll.updated) -> Poll.handlePollUpdated; no PollUpdateEvent object. |
| `PollVote* (2 symbols)` | `StreamChat.castPollVote` / `Poll.castVote` | shape-shift | votePoll->castPollVote (one option per call; also Channel.vote). Vote events via WS->Poll.handleVoteCasted; remove with removePollVote/Channel.removeVote. |
| `PollList* (3 symbols)` | `StreamChat.queryPolls` / `QueryPollsParams` | n-to-1 | Stateful list query dies; queryPolls(filter,sort,options) is stateless. Params->QueryPollsFilters/QueryPollsOptions; cursor `next`, not hasNext. |
| `PollVoter* (3 symbols)` | `StreamChat.queryPollVotes` / `Poll.queryOptionVotes` | n-to-1 | Stateless queryPollVotes / Poll.queryOptionVotes; params->QueryVotesFilters/Options / PollOptionVotesQueryParams. Answers via queryPollAnswers. |
| `PollChangelogs* (3 symbols)` | - (gap) | none | No poll changelog API; poll deltas arrive as WS events (poll.updated / poll.vote_*) and reconcile automatically on reconnect. Drop changelog polling. |
| `PollModule` (1 symbol) | `StreamChat.polls` / `StreamChat.createPoll` | n-to-1 | No poll Module; poll methods live directly on the client (createPoll/castPollVote/queryPolls...) + client.polls (PollManager cache). No sdk.poll. |
| `PollStatus` (1 symbol) | - (gap) | none | No status enum; read poll.is_closed (open/closed), closePoll sets it, REMOVED->deletePoll. No PollStatus symbol. |

### 7. Events, sync, push & offline

| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `AsyncLocalCacheStorage` | `- (gap)` | none | UIKit AsyncStorage cache adapter; Stream RN offline store is op-sqlite (SqliteClient) with no pluggable AsyncStorage/adapter interface. |
| `ConnectionHandler` | `client.on` | behavioral-diff | No ConnectionHandler class; reconnection/recovery is automatic. Observe connection via client.on events + isOnline/connectionRecovering from useChatContext. |
| `FailedMessageHandler` | `Channel.sendMessage` | behavioral-diff | onFailed(err,msg) callback -> catch on channel.sendMessage() Promise; failed state via MessageStatusTypes + retry(resend). |
| `FriendChangelogs*` (2 symbols) | `- (gap)` | none | Stream has no friends/contacts graph; no friend changelog-by-token endpoint. |
| `GroupChannelChangelogs*` (6 symbols) | `client.sync` | behavioral-diff | ChangeLogs by token/timestamp collapse to client.sync(cids,lastSyncAt); reconnect gap-fill automatic; Event context/source fold into one Event payload. |
| `MessageChangelogs*` (3 symbols) | `client.sync` | behavioral-diff | getMessageChangeLogsSince* -> client.sync / channel.watch reconciliation; reconnect resync is automatic, no manual changelog rebuild. |
| `MessageChangeLogsParams` | `client.sync` | shape-shift | Params class folds into client.sync arguments; no dedicated changelog-params object. |
| `MessageEventContext` / `MessageEventSource` (2 symbols) | `Event` | shape-shift | Collection event context/source enum folds into the single discriminated Event payload; branch on event.type (no CollectionEventSource). |
| `MessageHandler` | `Channel.sendMessage` | behavioral-diff | onSucceeded(message) callback -> await channel.sendMessage() resolution (Promise); list re-renders from the message.new event automatically. |
| `MessageRequestHandler*` (4 symbols) | `Channel.sendMessage` | n-to-1 | sendUserMessage/resendMessage/copyMessage + the chained handler collapse into channel.sendMessage() returning a Promise; retry via message state. |
| `ReactionEvent*` (4 symbols) | `channel.on` | behavioral-diff | Reaction changes arrive as reaction.new/reaction.updated/reaction.deleted via channel.on; ReactionEventOperation -> event.type. |
| `SessionHandler` | `TokenProvider` | behavioral-diff | Push onSessionTokenRequired -> pull TokenProvider passed to connectUser/useCreateChatClient; re-invoked on expiry. No session-handler object. |
| `ThreadInfoUpdateEvent` | `Thread` | behavioral-diff | Thread reply-count/participant updates ride client.on thread events; read via Thread state (Thread.ownUnreadCount, etc.), not a typed event. |
| `UserEventHandler` | `client.on` | behavioral-diff | onTotalUnreadMessageCountChanged/blocked ride ordinary client.on events (e.total_unread_count); block state via client.getBlockedUsers(). |
| `useSBUHandlers` | `- (gap)` | none | UIKit handler-registry hook; no equivalent. Register listeners directly with client.on/channel.on inside effects. |
| `AppleCriticalAlertOptions` | `- (gap)` | none | APNs critical-alert payload is provider/dashboard push config, not a client-side option in Stream RN. |
| `DndSchedule*` (4 symbols) | `- (gap)` | none | Recurring weekly do-not-disturb (quiet hours + timezone) unsupported; only one-shot snooze maps (setPushPreferences). |
| `DndSchedules*` (7 symbols) | `- (gap)` | none | Per-day/weekday/weekend recurring DND schedule builder has no analog; use one-shot snooze or channel.mute instead. |
| `DndTimeWindow*` (2 symbols) | `- (gap)` | none | Recurring DND time-window model unsupported; reimplement recurring quiet hours yourself. |
| `DoNotDisturbPreference*` (3 symbols) | `client.setPushPreferences` | behavioral-diff | Only one-shot DND maps: set a snooze/disabled_until window via setPushPreferences; recurring/timezone DND is a gap. |
| `PushTemplate*` (3 symbols) | `- (gap)` | none | Push templates are per-provider dashboard/server config (upsertPushProvider), not a runtime client switch. |
| `PushToken register/unregister*` (6 symbols) | `client.addDevice` | n-to-1 | register*->addDevice(id,push_provider), unregister*->removeDevice(id); PushTokenType->'apn'/'firebase' string; no registration-state enum (Promise). |
| `PushTokens*` (2 symbols) | `client.getDevices` | behavioral-diff | getMyPushTokensByToken -> client.getDevices(userID); enumerate + prune stale tokens (no auto-dedupe, no token cursor). |
| `PushTriggerOption*` (5 symbols) | `client.setPushPreferences` | n-to-1 | ALL/OFF/MENTION_ONLY -> chat_level 'all'/'none'/'mentions' via setPushPreferences (add channel_cid per-channel); read channel.push_preferences. |
| `SnoozePeriod*` (3 symbols) | `client.setPushPreferences` | behavioral-diff | One-shot snooze -> a disabled_until window on setPushPreferences; getSnoozePeriod reads it back. No standalone snooze object. |
| `usePushTokenRegistration` | `- (gap)` | none | No push-registration hook; call client.addDevice/removeDevice in your own effects around connectUser. |
| `CachedDataClearOrder` | `- (gap)` | none | OfflineDB is self-managed; no cache size/eviction-order tuning knob. |
| `LocalCacheConfig*` (3 symbols) | `Chat` | behavioral-diff | Enable via <Chat enableOfflineSupport> + op-sqlite; maxSize/clearOrder/encryption and pluggable store adapter are all gaps (DB self-managed). |
| `MMKVLocalCacheStorage` | `- (gap)` | none | No pluggable MMKV/AsyncStorage store; Stream RN offline store is op-sqlite (SqliteClient) only. |

### 8. Metadata, counters, theming/i18n & other
| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `MetaData*` (5: `MetaData`, `createMetaData`, `getAllMetaData`, `getMetaData`, `updateMetaData`) | `channel.updatePartial({ set / unset })` + read `channel.data` | shape-shift | Channel metadata -> top-level custom fields; no separate meta map. Values widen string-only -> any JSON. |
| `MetaCounter*` (7: `MetaCounter`, `create`/`decrease`/`getAll`/`get`/`increase`/`updateMetaCounters`) | `- (gap)` | none | No atomic counter primitive. Emulate via `channel.updatePartial` read-modify-write (races) or a server endpoint. |
| `MessageMetaArray` + `BaseMessage.*MessageMetaArray*` (5) | `client.partialUpdateMessage(id, { set, unset })` | behavioral-diff | Message meta-arrays -> message custom fields; NO atomic array add/remove or unique-key ops. |
| `OGMetaData` | `Attachment` (auto og-scrape) | shape-shift | Stream auto-enriches URLs into an og/url-preview `Attachment` (og_scrape_url/title/text/image_url); no standalone OG object. |
| `createTheme` | `Theme` (`DeepPartial<Theme>` object) | shape-shift | No factory: author a plain `DeepPartial<Theme>`, pass on `<OverlayProvider value={{style}}>` + `<Chat style>`; read `useTheme()`. |
| `UIKit theme types*` (6: `UIKitTheme`, `UIKitColors`, `UIKitColorScheme`, `UIKitPalette`, `UIKitTypography`, `UIKitTypographyOverrides`) | `Theme` | shape-shift | Collapse to Stream's `Theme` (component-slot style tree). No palette->colors derivation, no global typography (per-slot). |
| `createTypography` | `- (gap)` | none | No global typography object in `Theme`; set fontFamily/size per-component style slot. |
| `StringSet` + `StringSetEn` (2) | `Streami18n` | shape-shift | Re-key to i18next: keys are English source strings, not namespaced constants. `registerTranslation`/`setLanguage`; pass via `<Chat i18nInstance>`. |
| `UIKitThemeProvider` + `UIKitThemeContext` (2) | `OverlayProvider` (value.style) + `useTheme` | shape-shift | Theme travels on `<OverlayProvider value={{style}}>`/`<Chat style>`; read with `useTheme()`. No standalone theme provider to mount. |
| `SendbirdUIKit` | `- (gap)` | none | Version/platform/default-flags constants object; no analog (those defaults become client options/props). |
| `UIKitConfigInfo` | `- (gap)` | none | Dashboard UIKit-config payload from @sendbird/chat; no client-facing Stream equivalent. |
| `Foundation UI atoms*` (30: `ActionMenu`,`Alert`,`Avatar`,`Badge`,`BottomSheet`,`Box`,`Button`,`Divider`,`Header`,`Icon`,`Modal`,`Switch`,`Text`,`TextInput`,`Toast`,`Prompt`,`Placeholder`,+prop types) | `- (gap)` | none | UIKit visual primitives; no drop-in set. Rebuild with RN core + Stream primitives; style via `Theme`. Stream does export `Avatar`. |
| `Dialog/overlay providers+hooks*` (10: `DialogProvider`,`ToastProvider`,`useActionMenu`,`useAlert`,`useBottomSheet`,`usePrompt`,`useToast`,`StatusComposition`,`TypedPlaceholder`,`ProviderLayout`) | `- (gap)` | none | Stream `OverlayProvider` covers only action-sheet/image/attachment overlays. Roll dialogs yourself; use `EmptyStateIndicator`/`LoadingIndicator`. |
| `Foundation theming/style helpers*` (15: `Component`,`ComponentColors`,`ComponentColorTree`,`GetColorTree`,`FontAttributes`,`TypoName`,`createScaleFactor`,`createSelectByColorScheme`,`createStyleSheet`,`getDefaultHeaderHeight`,`CommonComponent`,`HeaderStyle*`,`useHeaderStyle`) | `- (gap)` | none | Color-tree/typography/scale/stylesheet + header-style context helpers; Stream `Theme` + RN `StyleSheet` replace them. |
| `Platform services*` (18: `*ClipboardService*`,`*PlayerService*`,`*RecorderService*`,`RecorderOptions`,`PlatformService*`,`usePlatformService`,`Open*Options`,`OpenResultListener`,`SaveOptions`,`Unsubscribe`+listeners) | `- (gap)` | none | Platform-service abstraction (clipboard/player/recorder/camera/file) dropped; Stream RN handles media/clipboard/audio internally. |
| `LocalizationContext` + `LocalizationProvider` + `useLocalization` (3) | `useTranslationContext` / `Streami18n` | shape-shift | UIKit localization context -> `useTranslationContext()`; strings from a `Streami18n` instance on `<Chat i18nInstance>`. |
| `SendbirdChatContext` + `SendbirdChatProvider` (2) | `Chat` provider + `useChatContext` | shape-shift | Mount `<Chat client={client}>`; read client/user via `useChatContext()`. No hidden internal SDK instance. |
| `SendbirdChat client types*` (6: `SendbirdChatOptions`, `SendbirdChatParams`, `SendbirdChatWith`, `SendbirdGroupChat`, `SendbirdOpenChat`, `SendbirdChatWith.init`) | `StreamChat` | shape-shift | One `StreamChat` client type (no modules generics/options classes). `init` -> `new StreamChat(apiKey)` + `connectUser`. |
| `SendbirdError` + `SendbirdErrorCode` (2) | `ErrorFromResponse` | shape-shift | Stream throws `ErrorFromResponse` with numeric `error.code`; no exported error-code enum — branch on the code number. |
| `SBUError` | `- (gap)` | none | UIKit-internal error wrapper; no analog. Catch `ErrorFromResponse` from client calls. |
| `UnreadItem*` (4: `UnreadItemCount`, `UnreadItemCountParams`, `UnreadItemKey`, `getUnreadItemCount`) | `client.getUnreadCount()` / `channel.countUnread()` | shape-shift | Per-item unread breakdown -> `getUnreadCount()` (totals) + `countUnread()`/`countUnreadMentions()` per channel. |
| `CountPreference` + `setMyCountPreference` (2) | `- (gap)` | none | No per-user unread-count-mode toggle; Stream always counts (enable "Read Events"); split mentions via `countUnreadMentions()`. |
| `SendingStatus` | `MessageStatusTypes` (`message.status`) | shape-shift | PENDING->'sending', SUCCEEDED->'received', FAILED->'failed' on `LocalMessage`; SCHEDULED/CANCELED have no equivalent. |
| `DeliveryStatus` | `MessageDeliveryStatus` | behavioral-diff | Inferred from ack + read state (delivered vs read); no per-member delivery count/object. Delivery Events is a dashboard flag. |
| `ReadStatus` | `ReadResponse` (`channel.state.read`) | shape-shift | Read via `channel.state.read[userId].last_read`; requires "Read Events". No per-message ReadStatus object. |
| `Sender` + `Participant` (2) | `UserResponse` | shape-shift | Message sender / open-channel participant collapse into `UserResponse` (`message.user`, watchers/members). userId->id, nickname->name, profileUrl->image. |
| `ChatFlatList` | `MessageList` | shape-shift | `MessageList` owns the internal inverted FlatList + pagination; don't render a raw list. |
| `EditInput` | `MessageComposer` (edit mode) | shape-shift | Edit is a composer state (`useMessageInputContext` editing), not a separate input component. |
| `ScrollToBottomButton` | `ScrollToBottomButton` | behavioral-diff | Stream ships its own, auto-rendered inside `MessageList`; override via context rather than mounting standalone. |
| `HiddenState` | `- (gap)` | none | `channel.hide()`/`show()` exist but no HIDDEN_ALLOW/PREVENT_AUTO_UNHIDE modes; read `hidden` off the query response. |
| `InvitationPreference` | `- (gap)` | none | No global auto-accept setting; choose per call: `addMembers` (immediate) vs `inviteMembers` (pending accept/reject). |
| `RestrictionInfo` + `RestrictionType` (2) | `- (gap)` | none | No restriction-info object; use `channel.banUser(id,{timeout,reason})`/`unbanUser` (+ shadow ban). Read via `queryBannedUsers`. |
| `Encryption` | `- (gap)` | none | Stream OfflineDB is self-managed (op-sqlite); no cache-encryption hook (section 14). |
| `MemoryStore*` (3: `MemoryStore`, `MemoryStoreParams`, `getMemoryStoreForDebugging`) | `- (gap)` | none | No pluggable in-memory cache store; offline state lives in op-sqlite `offlineDb`, not app-configurable. |
| `StoreItem` | `- (gap)` | none | Cache store-item type; OfflineDB internal, not exposed. |
| `DeviceOsInfo` + `DeviceOsPlatform` (2) | `- (gap)` | none | SDK device/OS telemetry types; no client-facing Stream equivalent. |
| `SendbirdPlatform` + `SendbirdProduct` + `SendbirdSdkInfo` (3) | `- (gap)` | none | Internal platform/product/SDK-info descriptors; no analog (the SDK sets its own agent). |
| `DayOfWeek` | `- (gap)` | none | Only used for recurring DND quiet hours (a gap, sections 10/15); Stream supports one-shot snooze only. |
| `MessengerSettingsParams` | `- (gap)` | none | AI-Agent/Desk messenger settings; no stream-chat equivalent (section 15). |
| `Plugin` | `- (gap)` | none | SDK plugin base class; stream-chat has no plugin system. |
| `SBUUtils` | `- (gap)` | none | UIKit utility class; no analog — inline the specific helpers you use. |
| `ErrorBoundaryProps` | `- (gap)` | none | UIKit error-boundary prop type; use your own RN error boundary. |
| `Range` | `- (gap)` | none | UIKit mention text-range type; no exported analog (mentions handled by the composer). |
| `KeyValuePairGet` + `KeyValuePairSet` (2) | `- (gap)` | none | AsyncStorage KV cache-adapter types; Stream offline uses op-sqlite, no KV adapter to implement. |

### 9. Feed channel, scheduled send & AI-Agent/Desk (gaps)
| Sendbird | Stream | Mapping | Note (INFERRED) |
|---|---|---|---|
| `FeedChannel*` (16 symbols) | `- (gap)` | none | No stream-chat FeedChannel class/module/query/changelogs. Approximate a read-only feed with an admin-post-only `messaging` channel, or adopt the separate Stream Feeds SDK. |
| `Notification*` (Message/Collection/Template/Category/Data/Setting, 18 symbols) | `- (gap)` | none | Sendbird Notifications feed has no chat analog; templates/categories/impression logging are gone. Model as plain admin messages; rebuild telemetry app-side. |
| `GroupChannelNotifications*` / `createNativeNotificationService` (UIKit, 10 symbols) | `- (gap)` | none | No prebuilt notifications-feed screen in stream-chat-react-native; build a read-only `MessageList` over an admin-post `messaging` channel. |
| `*Scheduled*` (create/update/query/status/info, 17 symbols) | `- (gap)` | none | No client scheduled send in stream-chat. Schedule server-side (server SDK/cron); for compose-later use drafts (`Channel.createDraft`/`getDraft`). |
| `AIAgent*` (32 symbols) | `- (gap)` | none | No managed AI-Agent product; wire your own LLM backend. Stream Chat AI primitives exist: `Channel.updateAIState`/`stopAIResponse`/`clearAIIndicator` + `AIState`. |
| `Conversation*` / `Desk` / `Helpdesk*` (handoff/CSAT/close/resolution, 17 symbols) | `- (gap)` | none | No conversation/handoff/CSAT/close model; model as a `messaging` Channel + backend. Handoff/close/CSAT become custom events/data + `channel.update`. |
| `Feedback` / `FeedbackRating` / `FeedbackStatus` (3 symbols) | `- (gap)` | none | No message-feedback API in stream-chat. Model thumbs up/down as a reaction (`Channel.sendReaction`) or custom message data. |

---

## Resolving a symbol not in this table

The RN corpus is **grounded-only** - there is no inferred row for a symbol neither the curated file
nor the 806-symbol long tail covers. Resolve it with the three-tier protocol, and never emit an
unverified Stream symbol:

- **`mapped`** - in [`sendbird-mapping.md`](sendbird-mapping.md): apply the row (agent-guided rewrite,
  or a `manual` gap -> `TODO(migration)`).
- **`unmapped-known`** - a real Sendbird API with no row here: find the nearest concept/family above,
  choose the Stream symbol, **confirm it exists in the installed Stream RN types**
  (`node_modules/stream-chat-react-native-core`, `node_modules/stream-chat`), and verify the rewrite
  with `npx tsc --noEmit`.
- **`unknown`** - imported from `@sendbird` but not in the indexed SDK surface: almost always a
  version skew; check against the Sendbird version the target actually has installed.

Every `- (gap)` is a **parity-ledger decision** (substitute / rebuild app-side / drop) routed through
the runbook's plan checkpoint ([`../sendbird-migration.md`](../sendbird-migration.md) section 2) -
never a silent `TODO`.
