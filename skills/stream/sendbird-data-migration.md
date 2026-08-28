# Migrating data from Sendbird into Stream Chat

Moves the users, channels, members, message history, reactions from Sendbird
into Stream Chat. The procedure is the same whatever the client platform. This
file covers data migration; code migration is done by a platform-specific
skill. Follow this procedure after the code migration is done, and only when the
user asked for it - it touches production data and may incur attachment-transfer
cost.

Read the docs before proceeding:

```bash
cat $(getstream docs chat/node)/migrating-from-sendbird.md  # strategies, field mappings, real-time sync
cat $(getstream docs chat/node)/import.md                   # JSONL format, schemas, ordering, limits
```

When `stream-cli` is referenced in the docs, prefer `getstream` over it:
`getstream import -h` has the equivalent commands (the subcommands and flags
differ, so don't copy `stream-cli` invocations).

## 1. Pick a strategy - ask the user

- **Hard switch** - simplest; needs a maintenance window.
- **Uni-directional sync** - zero downtime; the most common choice. Recommend
  this.
- **Bi-directional sync** - zero downtime, no forced app update. Enterprise -
  involves Stream support.

## 2. Export from Sendbird

Pull users, channels, members, and messages (reactions ship inline on messages)
via the Sendbird Platform API (server-side; needs the Sendbird app id + API
token), or the Data Export API for very large datasets. Any HTTP client works;
paginate every endpoint, handle rate limits, keep the raw export on disk.

## 3. Build + validate the import file

Follow `import.md` exactly - the JSONL shape, per-type schemas, object ordering,
and limits - and map fields per the table in `migrating-from-sendbird.md`. Keep
in mind:

- **Channel id length:** Sendbird `channel_url` often exceeds Stream's 64-char
  id limit - hash/truncate to a stable id and keep a url->id map so members and
  messages line up.
- **Timestamps:** Sendbird emits epoch milliseconds; Stream needs RFC3339.
  Convert every one.
- **Reactions are aggregated** in Sendbird (`{ key, user_ids: [...] }`) - emit
  one Stream `reaction` row per user, not per key.
- **Channel type:** group channels -> `messaging`, open channels -> `livestream`
  (or your own choice); distinct/1:1 channels use `member_ids` and omit `id`.
- **Attachments** need publicly reachable URLs; set `migrate_resources: true` to
  copy them onto Stream's CDN instead of hot-linking Sendbird.

Validate against the JSON Schema before uploading.

## 4. Import

Inside an initialized project (`getstream init`):

```bash
getstream import chat migration.jsonl --watch   # upload, create the task, follow it
getstream import status <task-id>               # or check on it later
```

Start tiny - a few users, one channel, a few messages; verify in the Dashboard
(or `getstream api QueryChannels`), then run the full export. A full historical
import is asynchronous and can take hours to days at scale; split exports over
the documented size limit into multiple ordered files.

"Hard switch" strategy ends here: schedule the window, run the full import,
verify, deploy.

## 5. Real-time sync

The bulk import is just a snapshot. We can also mirror new Sendbird activity
into Stream so nothing is lost between the snapshot and cutover. Stream supports
Sendbird sync out of the box - the real-time-sync section of
`migrating-from-sendbird.md` has the webhook URL and the supported-event list.

For uni-directional sync (Sendbird -> Stream only): flip clients to Stream when
ready, then disable the webhook.

For bi-directional sync (un-upgraded clients keep working during a gradual
rollout): recommend involving Stream support to configure both directions.

## 6. Cut over and verify

Confirm the import finished (`getstream import status`) and spot-check counts
(users, channels, messages) against Sendbird; open a migrated channel and check
history, reactions, threads, and attachments in-app; then switch client traffic
to Stream. If migrating with sync, keep the sync running through the rollout,
then disable the Sendbird webhook and decommission Sendbird.
