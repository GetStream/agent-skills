# Sendbird -> Stream Chat data migration

Moves the data (users, channels, members, message history, reactions) from Sendbird into
Stream Chat. Server-side and SDK-independent - the same procedure whatever the client
platform: a platform pack's `sendbird-migration.md` swaps the code, this file moves the
history behind it. Run it after the code migration builds and connects, and only when the
user asked for it - it touches production data and may incur attachment-transfer cost.

The docs are the source of truth; this file adds only the decision flow, the transform
gotchas, and the current CLI commands. Read both pages before building anything:

```bash
cat $(getstream docs chat/node)/migrating-from-sendbird.md  # strategies, field mappings, real-time sync
cat $(getstream docs chat/node)/import.md                   # JSONL format, schemas, ordering, limits
```

One caveat: `import.md` shows the old standalone `stream-cli` - don't install it. Use that
page for the file format only; the import itself runs through `getstream import` (step 4).

## 1. Pick a strategy - ask the user

- **A. Hard switch** - simplest; needs a maintenance window.
- **B. Uni-directional sync** - zero downtime; the most common choice. Recommend this.
- **C. Bi-directional sync** - zero downtime, no forced app update; Enterprise - involves
  Stream support.

All three share the bulk import (steps 2-4); B and C add real-time sync (step 5) on top.

## 2. Export from Sendbird

Pull users, channels, members, and messages (reactions ship inline on messages) via the
Sendbird Platform API (server-side; needs the Sendbird app id + API token), or the Data
Export API for very large datasets. Any HTTP client works; paginate every endpoint, handle
rate limits, keep the raw export on disk.

## 3. Build + validate the import file

Follow `import.md` exactly - the JSONL shape, per-type schemas, object ordering, and limits
- and map fields per the table in `migrating-from-sendbird.md`. What the docs don't spell
out, the Sendbird -> Stream transform gotchas:

- **Channel id length:** Sendbird `channel_url` often exceeds Stream's 64-char id limit -
  hash/truncate to a stable id and keep a url->id map so members and messages line up.
- **Timestamps:** Sendbird emits epoch milliseconds; Stream needs RFC3339. Convert every one.
- **Reactions are aggregated** in Sendbird (`{ key, user_ids: [...] }`) - emit one Stream
  `reaction` row per user, not per key.
- **Channel type:** group channels -> `messaging`, open channels -> `livestream` (or your own
  choice); distinct/1:1 channels use `member_ids` and omit `id`.
- **Attachments** need publicly reachable URLs; set `migrate_resources: true` to copy them
  onto Stream's CDN instead of hot-linking Sendbird.

Validate against the JSON Schema before uploading - it catches almost everything offline.

## 4. Import

Inside an initialized project (`getstream init`):

```bash
getstream import chat migration.jsonl --watch   # upload, create the task, follow it
getstream import status <task-id>               # or check on it later
```

Start tiny - a few users, one channel, a few messages; verify in the Dashboard (or
`getstream api QueryChannels`), then run the full export. A full historical import is
asynchronous and can take hours to days at scale; split exports over the documented size
limit into multiple ordered files.

For strategy A that's it: schedule the window, run the full import, verify, deploy.

## 5. Real-time sync (B and C only)

The bulk import is a snapshot; B and C also mirror new Sendbird activity into Stream so
nothing is lost between the snapshot and cutover. Stream supports Sendbird sync out of the
box - the real-time-sync section of `migrating-from-sendbird.md` has the webhook URL and the
supported-event list. **B:** Sendbird -> Stream only; flip clients to Stream when ready, then
disable the webhook. **C:** also Stream -> Sendbird so un-upgraded clients keep working
during a gradual rollout - involve Stream support to configure both directions.

## 6. Cut over and verify

Confirm the import finished (`getstream import status`) and spot-check counts (users,
channels, messages) against Sendbird; open a migrated channel and check history, reactions,
threads, and attachments in-app; then switch client traffic to Stream. For B/C keep the sync
running through the rollout, then disable the Sendbird webhook and decommission Sendbird.
