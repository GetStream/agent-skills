# Sendbird -> Stream Chat data migration (language-agnostic)

Migrates the **data** (users, channels, message history, reactions, members, devices) from
**Sendbird** into **Stream Chat**. It is **server-side and SDK-independent** - the same
procedure applies whether the client is Swift, Kotlin, Flutter, React, or React Native. A
platform pack's *code* migration (e.g. `stream-swift` `sendbird-migration.md`) swaps the SDK;
this file moves the history behind it.

**The docs are the source of truth - fetch them, don't reproduce them.** This file is an
**orchestrator**: it picks the strategy with the user, points at the exact doc pages, and adds
only the three things the docs don't give you - the interactive decision flow, the **verified
`getstream` CLI** import sequence (the docs show the older standalone `stream-cli`), and the
**Sendbird -> Stream transform gotchas**. Everything else - strategy pros/cons, field-mapping
tables, the JSONL schema, validation errors, the Sendbird event list, the webhook URL - lives
in the docs. Fetch the `.md` twins at run time and follow them:

- **Migration guide** (strategies, Sendbird->Stream field mappings, real-time sync + webhook +
  event list): `https://getstream.io/chat/docs/node/migrating-from-sendbird.md`
- **Import** (JSONL format, object schema, ordering, validation, limits):
  `https://getstream.io/chat/docs/node/import.md`

> **When to run:** after the code migration builds and connects. A migrated app talks to an
> **empty** Stream app until you import. **Ask the user first** - never start a data migration
> unsolicited (it touches production data and may incur attachment-transfer cost).

---

## Step 1 - Pick a strategy (ASK the user; this is the branch point)

The guide describes three approaches. Summarize them, recommend one, and let the user choose -
fetch the guide for the full pros/cons:

- **A. No Sync (hard switch)** - simplest; needs a maintenance window; users update the app.
- **B. Uni-directional sync** - zero downtime, the most common choice. **Lead with this.**
- **C. Bi-directional sync** - zero downtime, no forced app update; most complex (Enterprise).

All three share the same **bulk import** (steps 2-4). **B and C** add **real-time sync** on top
(step 5). So run 2-4 regardless, then add step 5 for B/C.

Ask, e.g.:

> The SDK migration is done. Do you also want to migrate your Sendbird **data** (users,
> channels, message history, reactions)? If so: **A** hard switch (simplest, needs a window),
> **B** uni-directional sync (zero downtime, most common), or **C** bi-directional sync (zero
> downtime, no forced app update, Enterprise)?

---

## Step 2 - Export from Sendbird

Pull users, channels, members, messages (reactions ship inline on messages) via the **Sendbird
Platform API** (server-side; needs your Sendbird app id + API token), or the **Data Export API**
for very large datasets. This is the only language-specific step - any HTTP client in any
language works; paginate every endpoint and handle rate limits. Keep the raw export on disk for
step 3.

---

## Step 3 - Build + validate the import file

Read **`import.md`** for the exact format and follow it - JSONL, one `{ "type", "data" }`
object per line, the per-type schema, the required object **ordering**, the 300 MB / 5 KB /
RFC3339 / 64-char limits, and the JSON-Schema validation. Map Sendbird fields to Stream fields
per the table in **`migrating-from-sendbird.md`**. Don't hand-roll either from memory - re-read
them.

What those docs *don't* spell out - the **Sendbird -> Stream transform gotchas** (this is the
real value of doing it as a migration rather than a generic import):

- **Channel id length:** Sendbird `channel_url` often exceeds Stream's 64-char id limit ->
  hash/truncate to a stable id and **keep a url->id map** so members and messages line up.
- **Timestamps:** Sendbird emits **epoch milliseconds**; Stream needs **RFC3339**. Convert every one.
- **Reactions are aggregated** in Sendbird (`{ key, user_ids: [...] }`) -> emit **one Stream
  `reaction` row per user**, not per key.
- **Channel type:** map Sendbird **group** channels -> `messaging`, **open** channels ->
  `livestream` (or your own choice); distinct/1:1 channels use `member_ids` and **omit `id`**.
- **Attachments** need publicly reachable URLs; set `migrate_resources: true` to copy them onto
  Stream's CDN instead of hot-linking Sendbird.

Validate against the JSON Schema before uploading - it catches almost everything offline.

---

## Step 4 - Import via the `getstream` CLI

The import docs show the older standalone `stream-cli`. This pack uses **`getstream`**, which
drives the same import API. Run inside an initialized project (`getstream init`) so the API
key/secret are picked up:

```bash
# 1. Get a signed upload URL + the import path
getstream api CreateImportURL --request '{"filename":"migration.jsonl"}'
#    -> returns an upload_url (signed S3) and a path

# 2. Upload the file to that signed URL (PUT, raw body)
curl -X PUT --upload-file migration.jsonl \
  -H 'Content-Type: application/octet-stream' "<upload_url>"

# 3. Start the import. mode: "upsert" (overwrite) or "insert" (skip existing).
#    Add "merge_custom": true to merge custom fields instead of replacing on upsert.
getstream api CreateImport --request '{"path":"<path>","mode":"upsert"}'
#    -> returns the created import; note its id

# 4. Poll until completed/failed; list past imports
getstream api GetImport --id <import-id>
getstream api ListImports
```

**Start tiny** - import a few users + one channel + a few messages, verify in the dashboard (or
`getstream api QueryChannels`), *then* run the full export. A full historical import is
asynchronous and can take hours-to-days at scale; split exports larger than 300 MB into
multiple ordered files.

For **strategy A**, that's it: schedule the window, run the full import, verify, deploy. Stop here.

---

## Step 5 - Real-time sync (strategies B and C only)

Bulk import is a snapshot; B/C also mirror **new** Sendbird activity into Stream so nothing is
lost between the snapshot and cutover. Stream supports Sendbird sync **out of the box** - read
the **"real-time sync"** section of `migrating-from-sendbird.md` for the exact webhook URL and
the supported-event list. In short: give Stream your Sendbird app id + token, point Sendbird's
webhook at the Stream endpoint, and enable the events you need.

- **B (uni-directional):** Sendbird -> Stream only; flip clients to Stream when ready, then
  disable the webhook.
- **C (bi-directional):** also Stream -> Sendbird so un-upgraded clients keep working during a
  gradual rollout - the Enterprise path; involve Stream support to configure both directions.

---

## Step 6 - Cut over and verify

Confirm the import finished (`GetImport` state) and spot-check counts (users, channels,
messages) against Sendbird; open a migrated channel and check history, reactions, threads, and
attachments in-app; then switch client traffic to Stream. For B/C keep the sync running through
the rollout, then disable the Sendbird webhook and decommission Sendbird.

---

## Source

- `https://getstream.io/chat/docs/node/migrating-from-sendbird.md`
- `https://getstream.io/chat/docs/node/import.md`

Cite these when you apply the runbook, and if anything here disagrees with the live `.md`, the
docs win - re-fetch and follow them.
