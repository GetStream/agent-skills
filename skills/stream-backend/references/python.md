# Python symbol reference

`stream-chat` (import `stream_chat`) to `getstream` (import `getstream`). Read with [`operations.md`](operations.md), which says which of these change behavior.

The generated SDK ships a migration guide under `docs/migration-from-stream-chat-python/` in the `stream-py` repository, with worked before-and-after examples. Use it as a starting point and confirm against the SDK source, which is the truth.

## How Python differs from the other languages

Two things to know before mapping anything.

**Calls take keyword arguments, not request objects.** Where some generated SDKs wrap every call in one request type, the Python SDK takes keyword arguments directly: `channel.truncate(hard_delete=True)`, not a truncate-request object. Typed dataclass models still exist, but for *payloads* nested inside a call: `MessageRequest`, `UserRequest`, `ChannelInput`. Import them from `getstream.models`.

**Sync and async are separate clients in both SDKs.** `StreamChat` and `StreamChatAsync` become `Stream` and `AsyncStream`. An existing async integration stays async; do not quietly convert it to sync. `client.as_async()` converts an existing sync client if that suits the codebase better than constructing a second one.

**There is no compiler.** Nothing will catch a wrong method name or argument for you. Verify each mapping against the SDK source, and lean on the customer's test suite. If they have none, say so: that is the largest single gap in confidence for a Python migration.

## Client and setup

| Legacy | Generated | Notes |
|---|---|---|
| `StreamChat(api_key, api_secret)` | `Stream(api_key=..., api_secret=...)` | |
| `StreamChatAsync(...)` | `AsyncStream(...)` | Or `client.as_async()` |
| `client.create_token(user_id, exp)` | `client.create_token(user_id, expiration=...)` | **Decision:** `exp` was an absolute timestamp, `expiration` is a duration in seconds |
| `client.channel(type, id)` | `client.chat.channel(type, id)` | |

Operations group under `client.chat`, `client.moderation`, `client.video` and `client.feeds`. Rows below showing a bare method are on the client itself.

Environment variables changed; see the behavior note in [`operations.md`](operations.md).

## Users

All on the client directly.

| Legacy | Generated | Notes |
|---|---|---|
| `upsert_user(dict)` | `upsert_users(UserRequest(...))` | A dict of loose keys becomes a typed model; custom fields nest under `custom` |
| `upsert_users(list)` | `upsert_users(*users)` | |
| `update_user` / `update_users` | `update_users` | |
| `update_user_partial` / `update_users_partial` | `update_users_partial` | Always a batch |
| `query_users` | `query_users` | Filter and sort move into structured parameters |
| `deactivate_user` / `deactivate_users` | `deactivate_user` / `deactivate_users` | |
| `reactivate_user` | `reactivate_user` | |
| `restore_users` | `restore_users` | |
| `delete_user` / `delete_users` | `delete_users` | **Behavior:** batch and asynchronous, returns a task; use `client.wait_for_task` if the code depended on it being done |
| `export_user` / `export_users` | `export_user` / `export_users` | |

## Channels

| Legacy | Generated | Notes |
|---|---|---|
| `channel.create(user_id)` | `channel.get_or_create(data=ChannelInput(created_by_id=...))` | |
| `channel.query()` | `channel.get()` | |
| `channel.update(...)` | `channel.update(...)` | Keyword arguments |
| `channel.update_partial(...)` | `channel.update_channel_partial(...)` | |
| `channel.delete()` | `channel.delete()` | |
| `channel.truncate()` | `channel.truncate(...)` | Options are keyword arguments |
| `channel.add_members(ids)` | `channel.update(add_members=[...])` | Members become member objects, not bare ids |
| `channel.remove_members(ids)` | `channel.update(remove_members=[...])` | Removal still takes ids |
| `channel.add_moderators(ids)` | `channel.update(add_moderators=[...])` | |
| `channel.demote_moderators(ids)` | `channel.update(demote_moderators=[...])` | |
| `channel.query_members(...)` | `client.chat.query_members(...)` | Moves off the channel object; type and id become parameters |
| `channel.mark_read` / `mark_unread` | `channel.mark_read` / `mark_unread` | |
| `channel.hide` / `show` | `channel.hide` / `show` | |
| `client.query_channels(...)` | `client.chat.query_channels(...)` | |
| `client.delete_channels(cids)` | `client.chat.delete_channels(...)` | **Behavior:** asynchronous, returns a task |

## Messages and reactions

| Legacy | Generated | Notes |
|---|---|---|
| `channel.send_message({...}, user_id=)` | `channel.send_message(message=MessageRequest(..., user_id=...))` | User id moves inside the message model |
| `client.get_message(id)` | `client.chat.get_message(id)` | |
| `client.update_message(msg)` | `client.chat.update_message(...)` | |
| `client.update_message_partial(...)` | `client.chat.update_message_partial(...)` | |
| `client.delete_message(id)` | `client.chat.delete_message(id)` | |
| `channel.send_reaction(...)` | `client.chat.send_reaction(...)` | Moves off the channel object |
| `channel.get_reactions(...)` | `client.chat.get_reactions(...)` | |
| `channel.delete_reaction(...)` | `client.chat.delete_reaction(...)` | |
| `client.translate_message(...)` | `client.chat.translate_message(...)` | |
| `client.unread_counts(...)` | `client.unread_counts(...)` | |

## Moderation

| Legacy | Generated | Notes |
|---|---|---|
| `client.ban_user(target, **opts)` | `client.moderation.ban(...)` | Options become keyword arguments; channel scope is a channel cid |
| `channel.ban_user(...)` | `client.moderation.ban(channel_cid=...)` | No channel-level method |
| `client.unban_user(...)` | `client.moderation.unban(...)` | |
| `client.shadow_ban(...)` | `client.moderation.ban(shadow=True)` | Not a separate method |
| `client.remove_shadow_ban(...)` | `client.moderation.unban(...)` | |
| `client.mute_user` / `mute_users` | `client.moderation.mute(...)` | Targets are a collection |
| `client.unmute_user` / `unmute_users` | `client.moderation.unmute(...)` | |
| `client.query_banned_users(...)` | `client.chat.query_banned_users(...)` | Filter moves into a structured payload |

## User blocking

| Legacy | Generated |
|---|---|
| `client.block_user(target, user_id)` | `client.block_users(...)` |
| `client.unblock_user(target, user_id)` | `client.unblock_users(...)` |
| `client.get_blocked_users(user_id)` | `client.get_blocked_users(...)` |

## Blocklists

Note the rename: `blocklist` becomes `block_list`. Searching for the old spelling finds nothing and looks like a missing feature.

| Legacy | Generated |
|---|---|
| `create_blocklist` | `create_block_list` |
| `get_blocklist` | `get_block_list` |
| `list_blocklists` | `list_block_lists` |
| `update_blocklist` | `update_block_list` |
| `delete_blocklist` | `delete_block_list` |

## Flags and review

| Legacy | Generated | Notes |
|---|---|---|
| `client.flag_message(id, user_id)` | `client.moderation.flag(...)` | **Behavior:** v1 to v2, see `operations.md` |
| `client.flag_user(target, user_id)` | `client.moderation.flag(...)` | Entity type distinguishes them |
| `client.unflag_message` / `unflag_user` | no direct equivalent | **Decision:** handle through the v2 review queue |
| `client.query_message_flags(...)` | `client.chat.query_message_flags(...)` | |
| review of flagged content | `client.moderation.query_review_queue`, `get_review_queue_item`, `submit_action` | **Decision:** a different model, not a rename |

## Devices

| Legacy | Generated | Notes |
|---|---|---|
| `client.add_device(...)` | `client.create_device(...)` | Push provider is a plain string |
| `client.get_devices(user_id)` | `client.list_devices(...)` | |
| `client.delete_device(id, user_id)` | `client.delete_device(...)` | |

## Responses

Legacy responses are dicts, read by key: `response["users"]`. Generated responses are typed and wrapped, so the same payload is reached through `response.data`, for example `response.data.users`. Where a legacy call returned a single object and the generated one returns a collection, the read changes shape as well as depth.

## Verify before mapping anything not listed here

The legacy client is wide, and the surface beyond this table is real work rather than a gap: campaigns, segments, imports and exports, permissions and roles, channel types, commands, drafts, reminders, polls, push providers, search and file upload all exist on both sides under names that mostly match. Confirm each against the SDK source before migrating it, and report anything you cannot confirm.
