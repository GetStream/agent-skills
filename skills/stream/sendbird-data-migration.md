# Sendbird -> Stream Chat data migration (language-agnostic)

This runbook migrates the **data** (users, channels, messages, reactions, members,
devices) from **Sendbird** into **Stream Chat**. It is **server-side and SDK-independent**:
the exact same procedure applies whether the client app is Swift, Kotlin, Flutter, React,
or React Native. A platform skill's *code* migration (e.g. `stream-swift`
`sendbird-migration.md`) swaps the SDK; **this** file moves the history behind it.

> **When to run this:** after the code/SDK migration builds and connects. The platform
> skill hands off here and **asks the user whether they also want to migrate data** - do
> not start a data migration unsolicited (it touches production data and may incur
> attachment-transfer cost). If the user only wants the SDK swap, stop after the code
> migration.

Source of truth (fetch the `.md` twins, don't answer from memory):
- Migration guide: `https://getstream.io/chat/docs/node/migrating-from-sendbird.md`
- Import format + CLI: `https://getstream.io/chat/docs/node/import.md`

Everything below is grounded in those two pages plus the `getstream` CLI. Re-fetch them at
run time in case the format changed.

---

## 0. Decide the strategy first (ASK the user - this is the branch point)

There are three strategies. They trade implementation effort against downtime. Present
this table, recommend one, and let the user pick - the rest of the runbook branches on it.

| Strategy | Downtime | Effort | Pick it when |
|---|---|---|---|
| **A. No Sync (hard switch)** | Scheduled downtime; users must update the app | Simplest | Small / low-traffic app, or a maintenance window is acceptable. One-shot export -> import -> deploy. |
| **B. Uni-directional sync** (**most common**) | Zero downtime, momentary interruption only | Moderate | The default for most apps. Bulk-import history, mirror *new* Sendbird events into Stream in real time, then cut over when ready. |
| **C. Bi-directional sync** | Zero downtime, zero service interruption, no forced app update | Most complex (Enterprise) | Large user base you can't force-upgrade; old and new clients must coexist during a gradual rollout. Data flows **both** directions. |

Recommendation to lead with: **B (uni-directional)** for most migrations; **A** for small
apps or when a maintenance window is fine; **C** only when you genuinely cannot force an
app update and need the two systems live at once (Enterprise plan + premium support).

> All three share the same **bulk import** core (sections 2-5). B and C add a **real-time
> sync** layer on top (section 6). So run 1-5 regardless, then add 6 for B/C.

Ask, e.g.:

> The SDK migration is done. Do you also want to migrate your Sendbird **data** (users,
> channels, message history, reactions)? If so, which approach: **A** hard switch (simplest,
> needs a maintenance window), **B** uni-directional sync (zero downtime, most common), or
> **C** bi-directional sync (zero downtime, no forced app update, Enterprise)?

---

## 1. What can be migrated

Stream's import accepts these object types, and they must appear **in this order** in the
file (referenced objects must already exist earlier in the file or in your app):

```
users -> devices -> future_channel_ban -> channels -> members -> messages -> reactions
```

| Stream type | From Sendbird | Notes |
|---|---|---|
| `user` | Users | id, name, image, custom data (<= 5KB) |
| `device` | Registered push tokens | keeps push working post-cutover (firebase / apn / huawei / xiaomi) |
| `channel` | Group + Open channels | group -> `messaging`, open -> `livestream` (or your mapping) |
| `member` | Channel members | one row per (channel, user); `last_read` drives unread counts |
| `message` | Messages (text + file) | attachments by URL; threads via `parent_id` |
| `reaction` | Message reactions | **one row per (message, user)** - Sendbird aggregates these, you must expand |
| `future_channel_ban` | Banned users | optional |

Not everything maps 1:1 - see the gotchas in section 7.

---

## 2. Export from Sendbird

Pull the data via the **Sendbird Platform API** (server-side, needs your Sendbird app id +
API token). The relevant list endpoints:

- Users: `GET https://api-{app_id}.sendbird.com/v3/users`
- Group channels: `GET /v3/group_channels` (include `?show_member=true`)
- Open channels: `GET /v3/open_channels`
- Messages in a channel: `GET /v3/{channel_type}/{channel_url}/messages` (paginate with
  `message_ts` / `next`)
- Reactions ship **inline** on each message (`reactions: [{ key, user_ids }]`).

For very large apps prefer Sendbird's **Data Export API** (`POST /v3/export/{messages|channels|users}`)
which produces downloadable JSON/CSV archives instead of paging live endpoints.

This is the only language-specific step, and even here the language is just "whatever your
backend speaks." Illustrative Node sketch (any HTTP client in any language works the same):

```js
// Illustrative only - paginate every endpoint; handle rate limits and retries.
const headers = { 'Api-Token': SENDBIRD_API_TOKEN };
const base = `https://api-${SENDBIRD_APP_ID}.sendbird.com/v3`;

async function listAll(path, key) {       // generic cursor pager
  const out = []; let token = '';
  do {
    const r = await fetch(`${base}/${path}?limit=100&token=${token}`, { headers });
    const j = await r.json();
    out.push(...j[key]); token = j.next || '';
  } while (token);
  return out;
}

const users    = await listAll('users', 'users');
const channels = await listAll('group_channels?show_member=true', 'channels');
// messages: loop channels, page /group_channels/{url}/messages by message_ts
```

Keep the raw export on disk; section 3 transforms it.

---

## 3. Build the Stream import file (JSONL)

The import file is **JSON Lines**: one JSON object per line, each wrapped in a
`{ "type", "data" }` envelope. Max **300 MB** per file (split into multiple ordered files
if larger). Timestamps are **RFC3339** (e.g. `2017-02-01T02:00:00Z`).

### Field mapping (Sendbird -> Stream)

**Users**

| Stream field | Sendbird field | Notes |
|---|---|---|
| `id` | `user_id` | required, string |
| `name` | `nickname` | display name |
| `image` | `profile_url` | avatar URL |
| (custom) | `metadata` | custom fields, <= 5KB total |
| `deactivated_at` | from `is_active = false` | optional |

**Channels** (one `channel` row; members become separate `member` rows)

| Stream field | Sendbird field | Notes |
|---|---|---|
| `id` | `channel_url` | required; **<= 64 chars** - hash/truncate long Sendbird URLs (see gotchas) |
| `type` | group vs open channel | group -> `messaging`, open -> `livestream` (choose your mapping) |
| `created_by` | `created_by` / `creator.user_id` | creator user id |
| `name` | `name` | channel name |
| `created_at` | `created_at` | RFC3339 |
| (custom) | `data` / `custom_type` | custom fields |
| *(members)* | `members[].user_id` | emit as `member` rows, not on the channel |

For distinct / 1:1 channels, **omit `id`** and set `member_ids` instead.

**Messages**

| Stream field | Sendbird field | Notes |
|---|---|---|
| `id` | `message_id` | required, **string** (cast the numeric id) |
| `channel_id` | parent channel `channel_url` | (the mapped id) |
| `channel_type` | parent channel type | `messaging` / `livestream` |
| `user` | `user.user_id` / `sender_id` | sender user id |
| `text` | `message` | message text |
| `type` | - | usually `regular`; thread replies `reply` |
| `parent_id` | `parent_message_id` | for threaded replies |
| `created_at` | `created_at` | Sendbird is **epoch ms** -> convert to RFC3339 |
| `attachments` | file message `url` / `type` / `name` | `[{ type, asset_url, image_url, thumb_url, ... }]` |
| (custom) | `data` / `custom_type` | custom fields, <= 5KB |

**Reactions** - Sendbird aggregates as `{ key, user_ids: [...] }`; Stream wants **one row
per user**:

| Stream field | Sendbird field |
|---|---|
| `message_id` | `message_id` |
| `type` | reaction `key` |
| `user_id` | each entry of `user_ids` |

### Example file (`migration.jsonl`)

```json
{"type":"user","data":{"id":"user_001","name":"Jesse","image":"https://cdn.example.com/jesse.png"}}
{"type":"user","data":{"id":"user_002","name":"Ada"}}
{"type":"device","data":{"id":"token_abc","user_id":"user_001","push_provider_type":"apn","push_provider_name":"production-apn"}}
{"type":"channel","data":{"id":"general","type":"messaging","created_by":"user_001","name":"General","created_at":"2017-01-01T01:00:00Z"}}
{"type":"member","data":{"channel_id":"general","channel_type":"messaging","user_id":"user_001","created_at":"2017-01-01T01:00:00Z"}}
{"type":"member","data":{"channel_id":"general","channel_type":"messaging","user_id":"user_002","created_at":"2017-01-02T01:00:00Z","last_read":"2017-02-01T03:00:00Z"}}
{"type":"message","data":{"id":"msg_001","channel_id":"general","channel_type":"messaging","user":"user_001","text":"Welcome!","type":"regular","created_at":"2017-02-01T02:00:00Z"}}
{"type":"reaction","data":{"message_id":"msg_001","type":"love","user_id":"user_002","created_at":"2017-02-01T02:05:00Z"}}
```

---

## 4. Validate before uploading

Stream validates with JSON Schema (schemas:
`https://github.com/GetStream/protocol/tree/main/jsonschemas`). Validate locally first -
it catches ~99% of problems before a failed import. Common errors:

| Error | Cause |
|---|---|
| `user id doesn't exist` | message/member/reaction references a user not in the file or app (ordering or missing `user` row) |
| `either channel.id or channel.member_ids should be provided` | you set both - pick one (distinct channels use `member_ids`, omit `id`) |
| `field required` | missing a required field (e.g. message `id`, `user`, `channel_type`) |
| `duplicated item id` | same id twice for one type |
| `max field length exceeded` | over a limit (channel `id` > 64, custom data > 5KB) |
| `invalid item type` | type not in {user, device, channel, member, message, reaction, future_channel_ban} |
| malformed JSON | a line is not a single valid JSON object |

---

## 5. Import into Stream (the bulk import - all strategies)

Use the **`getstream` CLI** (this pack's CLI; it drives the import REST API). Run inside an
initialized project (`getstream init`) so the API key/secret are picked up.

```bash
# 1. Get a signed upload URL + the import path
getstream api CreateImportURL --request '{"filename":"migration.jsonl"}'
#    -> returns { "upload_url": "https://...s3...", "path": "<import-path>" }

# 2. Upload the file to that signed URL (PUT, raw body)
curl -X PUT --upload-file migration.jsonl \
  -H 'Content-Type: application/octet-stream' "<upload_url>"

# 3. Kick off the import (mode: upsert = overwrite existing; insert = skip existing)
getstream api CreateImport --request '{"path":"<import-path>","mode":"upsert"}'
#    -> returns the created import; note its id for polling

# 4. Poll status until completed/failed (re-run; check state + any error file)
getstream api GetImport --id <import-id>

# list all imports / history
getstream api ListImports
```

Import **modes**: `upsert` (default) overwrites existing items (custom data replaced
wholesale); `insert` skips items whose id already exists. Use `merge_custom: true` on
`CreateImport` to merge rather than replace custom fields on upsert.

> Alternative (Node SDK, if scripting end-to-end): `client.createImportURL(filename)` ->
> PUT the file to the returned URL -> `client.createImport(path, 'upsert')` ->
> `client.getImport(id)`. Same three steps as the CLI.

**Start tiny.** Import a handful of users + one channel + a few messages first, verify it in
the dashboard / via `getstream api QueryChannels`, *then* run the full export. A full
historical import can take hours-to-days for large datasets and runs asynchronously.

For **strategy A (hard switch)**: schedule the window, run the full import, verify counts,
deploy the new app build, done. Stop here.

---

## 6. Real-time sync (strategies B and C only)

Bulk import is a snapshot; B/C also mirror **new** Sendbird activity into Stream so nothing
is lost between the snapshot and cutover.

**Stream supports Sendbird sync out of the box** (no custom relay to build):

1. Provide your **Sendbird app id and API token** to Stream (dashboard / support).
2. In Sendbird, set the webhook URL to:
   ```
   https://chat.stream-io-api.com/sendbird/webhook?api_key=<YOUR_STREAM_API_KEY>
   ```
3. Enable the events you need. Supported Sendbird events:

   **Open channels:** `open_channel:create`, `open_channel:remove`, `open_channel:enter`,
   `open_channel:exit`, `open_channel:message_send`, `open_channel:message_update`,
   `open_channel:message_delete`

   **Group channels:** `group_channel:create`, `group_channel:changed`,
   `group_channel:remove`, `group_channel:invite`, `group_channel:join`,
   `group_channel:decline_invite`, `group_channel:leave`, `group_channel:message_send`,
   `group_channel:message_read`, `group_channel:message_update`,
   `group_channel:message_delete`, `group_channel:reaction_add`,
   `group_channel:reaction_delete`

- **B (uni-directional):** Sendbird -> Stream only. New events replicate forward; flip clients
  to Stream when ready, then disable the Sendbird webhook.
- **C (bi-directional):** events also flow Stream -> Sendbird so legacy (un-upgraded) clients
  still see new messages during a gradual rollout. This is the Enterprise path - involve
  Stream support to configure both directions.

---

## 7. Cut over, verify, and gotchas

**Cutover**
1. Confirm the import finished (`GetImport` state) and spot-check counts (users, channels,
   messages) against Sendbird.
2. Verify in-app: open a migrated channel, scroll history, check reactions/threads/attachments.
3. Switch client traffic to Stream (the SDK migration already did the code side).
4. For B/C, keep the sync running through the rollout, then disable the Sendbird webhook and
   decommission Sendbird.

**Gotchas (these bite during transform, section 3)**
- **Channel id length:** Sendbird `channel_url` can exceed Stream's **64-char** id limit ->
  hash or truncate to a stable id and keep a mapping table so messages/members line up.
- **Timestamps:** Sendbird message `created_at` is **epoch milliseconds**; Stream needs
  **RFC3339**. Convert every timestamp.
- **Reactions are aggregated** in Sendbird (`key` + `user_ids[]`) -> emit **one `reaction`
  row per user**.
- **Attachments must be publicly reachable URLs.** To copy them onto Stream's CDN (instead of
  hot-linking Sendbird), set `migrate_resources: true` on the attachment (slower import).
- **Ordering matters:** users -> devices -> future_channel_ban -> channels -> members ->
  messages -> reactions. A message before its user/channel fails validation.
- **Distinct (1:1) channels:** omit `id`, set `member_ids` - never both.
- **Unread state:** all imported messages are read by default; set `last_read` on `member`
  rows to reproduce real unread counts.
- **Custom fields:** 5KB per object; unknown reserved field names are rejected.
- **Idempotency:** re-running with `mode: upsert` is safe and overwrites; use `insert` to
  resume without clobbering already-imported items.

---

## Source

- Migrating from Sendbird: `https://getstream.io/chat/docs/node/migrating-from-sendbird.md`
- Import (format, CLI, limits): `https://getstream.io/chat/docs/node/import.md`

Cite these when you apply the runbook. If a detail here disagrees with the live `.md`, the
live docs win - re-fetch and follow them.
