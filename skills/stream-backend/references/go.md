# Go symbol reference

`github.com/GetStream/stream-chat-go` to `github.com/GetStream/getstream-go`. Read with [`operations.md`](operations.md), which says which of these change behavior.

Confirm the current major version before editing; the table below is written against the module paths in use, not a fixed version. The generated SDK's own migration guide, under `docs/migration-from-stream-chat-go/` in the `getstream-go` repository, carries worked before-and-after examples for most of these and is the best next stop when a mapping needs detail. Treat it as a strong starting point and confirm against the SDK source, which is the actual truth.

## Client and setup

| Legacy | Generated | Notes |
|---|---|---|
| `NewClient(key, secret)` | `NewClient(key, secret)` | |
| `NewClientFromEnvVars()` | `NewClientFromEnvVars()` | **Behavior:** reads different environment variable names |
| `CreateToken(user, expiry)` | `CreateToken(user, WithExpiration(d))` | **Decision:** absolute time becomes a duration |
| `client.Channel(type, id)` | `client.Chat().Channel(type, id)` | Returns a channel object, not a response |

The generated client groups operations under `Chat()`, `Moderation()`, `Video()` and `Feeds()`. Where a row below shows a bare method, it is on the root client.

## Users

| Legacy | Generated | Notes |
|---|---|---|
| `UpsertUser(user)` | `UpdateUsers(UpdateUsersRequest)` | Users keyed by id; extra data becomes `Custom` |
| `UpsertUsers(users...)` | `UpdateUsers(UpdateUsersRequest)` | Same call, a map instead of variadic |
| `QueryUsers(opts, sort)` | `QueryUsers(QueryUsersRequest)` | Filter moves under `Payload`, `Filter` becomes `FilterConditions` |
| `PartialUpdateUser(update)` | `UpdateUsersPartial(request)` | Always a batch; a single user is a slice of one |
| `DeactivateUser(id, opts...)` | `DeactivateUser(id, request)` | Options become request fields |
| `DeleteUser(id, opts...)` | `DeleteUsers(DeleteUsersRequest)` | **Behavior:** batch and asynchronous, returns a task id |

## Channels

| Legacy | Generated | Notes |
|---|---|---|
| `CreateChannel(type, id, creator, req)` | `Chat().Channel(type, id).GetOrCreate(request)` | Creator moves to `CreatedByID`; members become objects |
| `CreateChannel(type, "", creator, req)` | `Chat().GetOrCreateDistinctChannel(type, request)` | Distinct channels have their own method |
| `QueryChannels(opts, sort)` | `Chat().QueryChannels(request)` | `Filter` becomes `FilterConditions` |
| `ch.AddMembers(ids)` | `ch.Update(UpdateChannelRequest{AddMembers})` | No dedicated method; members are objects |
| `ch.RemoveMembers(ids, msg)` | `ch.Update(UpdateChannelRequest{RemoveMembers})` | Removal still takes plain ids |
| `ch.Update(data, msg)` | `ch.Update(UpdateChannelRequest)` | Custom data under `Data.Custom` |
| `ch.PartialUpdate(update)` | `ch.UpdateChannelPartial(request)` | |
| `ch.Delete()` | `ch.Delete(DeleteChannelRequest)` | Takes a request; hard delete is a field |
| `DeleteChannels(cids, hard)` | `Chat().DeleteChannels(request)` | **Behavior:** asynchronous, returns a task id |
| `ch.QueryMembers(opts)` | `Chat().QueryMembers(request)` | **Decision:** type and id move onto the payload |
| `ch.Truncate(opts...)` | `ch.Truncate(TruncateChannelRequest)` | |

## Messages and reactions

| Legacy | Generated | Notes |
|---|---|---|
| `ch.SendMessage(msg, userID)` | `ch.SendMessage(SendMessageRequest)` | User id moves inside the message |
| `GetMessage(id)` | `Chat().GetMessage(id, request)` | |
| `UpdateMessage(msg, id)` | `Chat().UpdateMessage(id, request)` | Id is positional, not a message field |
| `PartialUpdateMessage(id, req)` | `Chat().UpdateMessagePartial(id, request)` | `Set` and `Unset` sit directly on the request |
| `DeleteMessage(id, opts...)` | `Chat().DeleteMessage(id, request)` | Hard delete is a field |
| `SendReaction(reaction, msgID, userID)` | `Chat().SendReaction(msgID, request)` | User id moves inside the reaction |
| `GetReactions(msgID, params)` | `Chat().GetReactions(msgID, request)` | Query params become typed fields |
| `DeleteReaction(msgID, type, userID)` | `Chat().DeleteReaction(msgID, type, request)` | User id moves into the request |

## Moderation

| Legacy | Generated | Notes |
|---|---|---|
| `ch.AddModerators(ids...)` | `ch.Update(UpdateChannelRequest{AddModerators})` | No dedicated method |
| `ch.DemoteModerators(ids...)` | `ch.Update(UpdateChannelRequest{DemoteModerators})` | |
| `BanUser(target, by, opts...)` | `Moderation().Ban(BanRequest)` | Options become fields; expiration becomes `Timeout` |
| `ch.BanUser(target, by, opts...)` | `Moderation().Ban(BanRequest{ChannelCid})` | Channel scope is a field, formatted `type:id` |
| `UnBanUser(target, opts...)` | `Moderation().Unban(UnbanRequest)` | Channel scope via `ChannelCid` |
| `ShadowBan(target, by)` | `Moderation().Ban(BanRequest{Shadow: true})` | Not a separate method |
| `MuteUser(target, by, opts...)` | `Moderation().Mute(MuteRequest)` | Targets are a collection |
| `UnmuteUser(target, by)` | `Moderation().Unmute(UnmuteRequest)` | |
| `QueryBannedUsers(opts)` | `Chat().QueryBannedUsers(request)` | **Decision:** filter moves under `Payload` |

## User blocking

| Legacy | Generated | Notes |
|---|---|---|
| `BlockUser(target, by)` | `BlockUsers(BlockUsersRequest)` | Plural name |
| `UnblockUser(target, by)` | `UnblockUsers(UnblockUsersRequest)` | Not the video call method of a similar name |
| `GetBlockedUser(by)` | `GetBlockedUsers(request)` | |

## Blocklists

Note the spelling: `Blocklist` becomes `BlockList`. A search for the old spelling finds nothing and looks like a missing feature.

| Legacy | Generated |
|---|---|
| `CreateBlocklist(req)` | `CreateBlockList(CreateBlockListRequest)` |
| `GetBlocklist(name)` | `GetBlockList(name, request)` |
| `UpdateBlocklist(name, words)` | `UpdateBlockList(name, request)` |
| `ListBlocklists()` | `ListBlockLists(request)` |
| `DeleteBlocklist(name)` | `DeleteBlockList(name, request)` |

The generated request also exposes matching options the legacy SDK did not: list type, substring matching, leet and plural checks.

## Flags and review

| Legacy | Generated | Notes |
|---|---|---|
| `FlagMessage(msgID, by)` | `Moderation().Flag(FlagRequest)` | **Behavior:** v1 to v2, see `operations.md` |
| `FlagUser(target, by)` | `Moderation().Flag(FlagRequest)` | **Behavior:** v1 to v2, same as above; entity type distinguishes them |
| `QueryMessageFlags(opts)` | `Chat().QueryMessageFlags(request)` | **Decision:** filter moves under `Payload` |
| `QueryFlagReports(req)` | `Moderation().QueryReviewQueue(request)` | **Decision:** different model |
| `ReviewFlagReport(id, req)` | `Moderation().SubmitAction(request)` | **Decision:** an action against a queue item |

## Devices

| Legacy | Generated | Notes |
|---|---|---|
| `AddDevice(device)` | `CreateDevice(CreateDeviceRequest)` | Push provider becomes a plain string |
| `GetDevices(userID)` | `ListDevices(request)` | User id moves into the request |
| `DeleteDevice(userID, deviceID)` | `DeleteDevice(DeleteDeviceRequest)` | Both ids become fields |

## Types

| Legacy | Generated |
|---|---|
| `*Client` | `*Stream` |
| `*Channel` | `*Channels` |

Types such as the user, message, reaction and device types split into request and response variants. Pick per use, per the decision rule in [`operations.md`](operations.md).

## Beyond this table

File and image upload, unread counts, threads, drafts, polls, reminders, commands, permissions and roles, import and export, and message translation are not listed above. That means they are unverified here, **not that they are missing**: most exist on both sides under names that mostly match. Confirm each against the SDK source before migrating it, and report anything you cannot confirm rather than assuming it has no equivalent.
