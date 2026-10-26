---
name: stream-feeds-migration
description: "Generate the v2 -> v3 sync mapping for a Stream Activity Feeds app by sampling its live v2 activities and reactions and, when the app's v2 integration code is available, reading its write paths, and, from that code, plan how the app's code moves from v2 to v3. Use when setting up a Feeds v2 to v3 migration, when asked to build, review, or debug a v3 sync mapping, when someone asks 'what mapping do we need for our app?', when asked how to port an app's v2 Feeds code to v3, or when a migrated activity lands in v3 with missing text, missing attachments, comments that are not comments, or bookmarks that went missing. Triggers on v3sync, v2 to v3, feeds migration, activity feeds migration, sync mapping, extra_context, reaction kinds, comments and bookmarks mapping, porting plan. The same mapping drives both the live syncer and the bulk exporter."
license: See LICENSE in repository root
compatibility: Requires the v2 app's API key and secret, exported as environment variables, plus Python 3 (standard library only - no pip install). Read-only against the v2 app; writes one sample file to the working directory. No project or SDK required; when the app's repository is available, its v2 integration code is read to cover what a sample cannot and to write a porting plan. The skill never modifies the code; porting it is a follow-up done only when the user asks.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Glob, Grep,
  Bash(python3 *),
  Bash(ls *),
  Bash(git log *),
  Bash(getstream *)
---

# Stream Feeds - v2 to v3 sync mapping

For CLI commands or routing to another Stream skill, read
[`../stream/SKILL.md`](../stream/SKILL.md).

Produce the `mapping` object for an app's v2 -> v3 sync configuration by looking
at what the app's v2 data actually contains, rather than at what anyone believes
it contains.

One mapping serves both migration paths - the live syncer and the bulk exporter
read the same configuration. Getting it right once fixes both; getting it wrong
breaks both in the same way.

---

## Workflow

### 1. Get credentials into the environment

Use `getstream env` to write the **v2 app's** credentials to an env file. Read
`getstream env -h` for app selection and output options. Use `--target web` so
the file contains both `STREAM_API_KEY` and `STREAM_API_SECRET`, which the
sampler expects.

Load that file when running the sampler below. Do not print its contents or put
credential values in chat or tool commands.

### 2. Pick the target

**Default to production** - `https://api.stream-io-api.com`. Use it unless the
user names a different environment (EU, dedicated, staging), in which case pass
`--base-url <that URL>`.

Do not raise alternative environments on your own; production is the assumed
target and the user will say so if they mean otherwise.

### 3. Fetch the sample

```bash
set -a
. "<env-file>"
set +a
python3 <skill-dir>/fetch_sample.py --out v3sync-sample.json
```

`<env-file>` is the absolute path to the file written by `getstream env`. Run
the block in one shell invocation so Python inherits the credentials.

`<skill-dir>` is the directory holding this `SKILL.md`. Resolve it to an
absolute path before running - the skill runs from whatever directory the user
happens to be in, so a relative path only works by accident. `getstream skills`
links the pack into one of two places, so it is one of:

- `.agents/skills/stream-feeds-migration` (Cursor, Codex)
- `.claude/skills/stream-feeds-migration` (Claude Code)

Glob `{.agents,.claude}/skills/stream-feeds-migration/SKILL.md` to settle which.

The key and secret are read from `STREAM_API_KEY` and `STREAM_API_SECRET`. The
script takes **no `--secret` flag** by design - a secret passed as an argument
would land in the process list and the shell history, which is exactly what the
environment variable avoids. (`--api-key` exists, since the key is not
sensitive.) The sample is written to the working directory, which is where you
want it.

Standard library only - no pip install. It calls two server-side-only endpoints:

- `GET /api/v1.0/migration/sample/activities` - up to 100 activities, drawn
  from several periods (the newest, then at or before 7d, 30d, 180d, 1y and
  2y ago)
- `GET /api/v1.0/migration/sample/reactions` - 5 reactions per distinct kind

Both return **raw** stored payloads: unflattened `extra_context`, unmodified
reaction `data`. That is the point - you are looking for the real field names
and nesting.

A 401 or 403 means the secret is wrong, or the token was built as a user token
rather than a server-side one. A 404 means these endpoints are not available on
the app's deployment yet; [Stream support](https://getstream.io/contact/) can
confirm.

An empty `activities` array alongside a `200` is worth calling out rather than
working around: the app is either genuinely empty or its activity store cannot
serve this scan. Reactions carry an `activity_id`, so reactions in the sample
prove activities exist and point to the second explanation.

#### Read what the activity sample left out

Recent deployments also return `reaction_reference_count`,
`reaction_references` and `slices`, and the script keeps them in the sample
file. Read them before the activities, because they say how representative the
activities are:

- **`reaction_reference_count`** - how many target-feed copies of reactions
  the sample left out. v2 writes one of these when a reaction has
  `target_feeds`. You can recognise them by a `foreign_id` of `reaction:<id>`
  and an `extra_context.reaction` holding an `SR:` ref. They carry no post
  fields, so they say nothing about the mapping; up to 3 are in
  `reaction_references` for reference.
- **`slices`** - one entry per period, with `scanned`, `posts` and
  `reaction_references`. `before` is the period's cutoff; the newest slice has
  none. `extended` means the period was re-read with a larger scan because
  reaction references crowded it.
  - A slice whose `posts` is small next to `scanned` was crowded: posts from
    that period are under-represented. Say so.
  - A slice with `scanned: 0` held no activities **inserted** in that window.
    Periods are by insert time, not by the activity's `time`, so data imported
    into v2 recently all lands in the newest slice.

When the older slices are empty on an app that has existed for a while, the
sample cannot show what older posts look like. Ask whether the post format ever
changed (different field names for text, media or ids), and say the mapping only
covers the shape the sample shows.

If these keys are missing, the deployment predates them: the activities are the
newest 100 and can include reaction references. Leave those out yourself by the
shape above before analysing.

#### Cover every feed group

The sample is app-wide: it takes the newest activities wherever they were
written, and does not say which feed group each came from. A feed group with
little or old traffic can be missing entirely. One mapping serves the whole app,
so a group whose activities are written differently (a backend job, a
notification feed, an older client) gets a mapping fitted to the others.

Recent deployments list the app's feed groups in `feed_groups` (name and
type); on older ones, ask the user which groups the app uses. Either way the
sample does not say which group each activity came from, so ask whether any
group is written by a different code path. For each group the sample may have
missed, read a feed or two of it directly with `--feed` (read-only,
repeatable):

```bash
python3 <skill-dir>/fetch_sample.py --out v3sync-sample.json \
  --feed notification:<user-id> --feed timeline:<user-id>
```

The activities land under `feed_samples` in the same file, normalised to the
sample's shape (custom fields under `extra_context`, plus a `feed` field), so
analyse them the same way. Aggregated and notification feeds are unwrapped into
their activities. They also hold the target-feed copies of reactions; leave
those out as above. A feed that fails (for example an unknown group) is
recorded with its error and does not stop the run.

### 4. Read the integration code (when you have it)

The sample shows what is stored; the app's v2 integration code shows every way
it gets written - including the paths the sample is weakest on: low-traffic
feed groups, rarely used reaction kinds, child reactions, how users are
created, and whether `foreign_id` is unique. If the user's repository is in the
working directory (or they point you at it), read it. If not, ask once whether
it is available; the skill works without it.

Follow [`code-inventory.md`](code-inventory.md):

1. Run `<skill-dir>/scan_v2_calls.py --root <repo> --out v2-code-scan.json` to list every v2 write call
   site (read-only; secrets in snippets are redacted - never quote one from the
   code yourself).
2. Read the call sites and build the **inventory**: one row per write path,
   with its feed group(s), to-targets, fields, `foreign_id` construction,
   reaction kinds and data shape, child reactions, and user fields.
3. Check history for fields that changed (`git log -S'<field>'`): older
   activities still carry the old format.
4. Cross-check the inventory against the sample. Agreement confirms a key;
   code-only evidence is a rare or new path (map it, say so, and read a feed of
   it with `--feed`); sample-only evidence is another writer or an older
   version (ask). The sample stays the source of truth - the code is rarely
   the only writer.

### 5. Analyze

Read `v3sync-sample.json` and work through the checklist below. Read
[`mapping-keys.md`](mapping-keys.md) for the full key catalogue, defaults, exact
resolution rules, and worked examples of the common shapes - **do not guess key
names or defaults from memory.**

The single most common mistake is over-configuring. Every key has a default that
is right for a conventional v2 app. Only emit a key when the sample shows the
app deviates from that default. An empty mapping is a valid answer.

### 6. Emit the mapping

Produce **only** the `mapping` object, ready to paste into the app's existing
sync configuration. Do not emit the surrounding configuration (`enabled`,
`base_url`, `api_key`, `secret`, `sample_rates`, `feed_groups_synced`); those
are deployment concerns, they are not derived from the sample, and restating
them with placeholder credentials invites someone deploying a config with a
`<v3 app key>` still in it.

Explain each key you set by pointing at the evidence: rows in the sample, and,
when you read the code, the call sites (`file:line`). Say which keys rest on
code alone.

Flag explicitly anything you could not determine from the sample - see **Limits
of the sample** below. Silence there reads as "verified", which it is not.

### 7. Plan the code port (when you read the code)

If you read the integration code in step 4, also write a **porting plan**,
following [`porting-plan.md`](porting-plan.md): one row
per write and read path with its v2 call, its v3 call, the switch-over step it
belongs to (reads move first, every write moves together last), and the
behaviour that changes. Take the v3 calls from the **V2 to V3 Code Migration**
guide (through `getstream docs`), not from memory.

The plan is a document: do not edit the app's code. Offer to port it; if the
user asks, follow **Porting the code** in that reference (v3 read paths behind a
read flag, every write path behind one write flag, never writing to both
versions).

---

## Analysis checklist

### Activities

Look at `activities[].extra_context` across the whole sample.

- **Custom field names** - any field whose name collides with a v3 reserved key,
  or that should be surfaced at the top level of `custom`, needs a rename entry.
  Fields that are already conventionally named need nothing.
- **Activity id** - does a field hold a stable external id (`external_id`,
  `post_id`, `uuid`)? If so, `id` should point at it. If instead `foreign_id`
  is populated and meaningful across the sample, `foreign_id: "id"` is the
  simpler answer. If neither, omit both and let the v2 UUID carry over.
  Before recommending `foreign_id: "id"`, check that no two sampled activities
  share a `foreign_id`. v2 allows several activities with the same foreign_id
  (they differ by `time`), but as v3 ids they collide and only one survives. If
  any repeat, or the sample is too small to tell, ask whether foreign_ids are
  unique in the app, and keep the v2 UUID when they are not.
- **Reshares / replies** - a field holding an `SA:<uuid>` ref (commonly
  `shared_origin_post`) is the `parent_id` field. Note that `SA:` refs are also
  autodetected, so only configure this when the sample shows the ref buried
  somewhere the autodetection would not reach first.
- **Text** - is the post body under `text` (default, no config) or something
  else like `body` / `message` / `content`? Set `text` only if it differs.
- **Attachments** - a list of media objects under a custom path means
  `activity_attachments_field`.
- **Actor format** - check `actor` across the sample. `SU:<id>` is handled
  natively. A different prefix (`User:<id>`) needs a `replaces` entry. An actor
  that is a whole JSON blob is a known legacy shape and needs no mapping.
- **extra_context nesting** - decide whether the bag should stay nested under
  `custom.extra_context` (default), be renamed, or be flattened (`""`). This one
  is a preference, not something the sample can settle: ask.

### Reactions

Look at `kinds` first - that list contains the reaction kinds represented in
the sample.

- **Classify every kind** into exactly one of: comment, bookmark,
  comment-bookmark, or plain reaction. Then set `comments`, `bookmarks`,
  `comments_bookmarks` accordingly. A kind you leave out of all three is a
  plain reaction, which is often correct.
- Remember the defaults: `comments` already covers `["comment", "reply"]`.
  Kind matching is case-insensitive, so `COMMENT` and `REPLY` are those same
  kinds. If those are the app's only comment kinds, do not restate them.
- **Comment text** - inspect the `data` of every comment-kind reaction. The
  default is `data.message`. If that field is missing and the text is under
  `text` or `body`, set `comment_field` to that key (`"text"`, not
  `"data.text"`). Empty text is dropped only when there is no attachment
  object and no http(s) URL in the reaction data. Whitespace-only text is
  kept, and so is a comment that only contains an http(s) URL. A dropped
  comment is not kept as a reaction.
- **Replies** - is the parent comment id in the top-level `parent` (the
  default, no config needed) or nested in `data`? If nested, set
  `parent_id_field` to that envelope path. Confirm against a **non**-reply too:
  a top-level comment must leave that path empty, or every comment would be
  treated as a reply.
- **Reactions on comments** - a non-comment reaction that targets a comment
  needs `reaction_comment_id_field`. Two shapes are common:
  - the comment id in its `data` (for example `data.comment_id`)
  - v2's native child reaction, created with `reactions.addChild`: a
    non-comment kind, often `like`, whose top-level `parent` is set. This needs
    `"reaction_comment_id_field": "parent"`.

  Without it, a like on a comment lands in v3 as a like on the activity.
  Reactions with no parent and no comment id are unaffected, so a sample mixing
  both is fine.
- **Kind renames** - only if the app should use different type names in v3.
- **Attachments** - `attachments_field` if comment attachments are not under
  `data.attachments`.

Watch for **one kind carrying two incompatible shapes** - e.g. some `like` rows
holding a comment id at one path and others at a different one. The single-path
keys (`parent_id_field`, `reaction_comment_id_field`) cannot serve both. Say
which rows the mapping will not cover instead of picking one silently.

Some apps carry **legacy layout flags** - see _Legacy layout flags_ in
[`mapping-keys.md`](mapping-keys.md). Never set one.

### Users

The sample endpoints return activities and reactions, not users, so **user
field mapping cannot be inferred from it**. The defaults already cover the
common v2 conventions:
- **name:** `name`, then `username`
- **image:** `image`, then `profileImage`, then `avatar`

So only ask when display name or avatar may be stored under some other key.
Then set `name` / `image`, remembering those two keys read v3-key-to-v2-source,
backwards from every other string key. A list (`"image": ["avatar_url",
"profileImage"]`) tries each source in order.

---

## Output format

The mapping object on its own:

```json
{
  "bookmarks": ["bookmark"],
  "parent_id_field": "data.comment.parent.id",
  "attachments_field": "media.files"
}
```

Every key present must be one the sample justified. An empty mapping (`{}`) is a
valid and correct answer for an app whose v2 data already matches v3
conventions - say so plainly rather than padding it with defaults.

Alongside the object, list the keys you deliberately **omitted** and why (which
default already covers the app's shape). That is what tells the reader the
absence was a decision rather than an oversight.

**The omitted list covers only the general-purpose keys.** Never include a
legacy layout flag (see [`mapping-keys.md`](mapping-keys.md)) in that list, in
the mapping, or anywhere else in your response - not as a row, not as an aside,
not even to say it was considered and rejected. They are irrelevant to the app
in front of you, so there is nothing to justify: leave them out silently.

Suggest `"debug": true` in the mapping for the initial validation run - it
stamps the live mapping onto `custom._v3sync_debug` of every synced activity -
and remind the user to remove it once the mapping is confirmed.

---

## Limits of the sample

State whichever of these apply alongside the generated mapping. They are the
difference between "this mapping is correct" and "this mapping fits the sample":

- **Activities are at most 100, by insert time.** The sample reaches back up to
  2 years, but a field that only older activities carry can still be missing:
  when older periods are empty or crowded (see `slices`), or when data was
  bulk-loaded recently. One mapping serves one post format. If older posts
  store text or media under other fields, they arrive in v3 with that content
  in `custom` instead. Apps whose schema changed over time are exactly the ones
  where this bites.
- **Reactions are drawn from a bounded recent window.** A kind that has not
  been used lately can be missing from `kinds` entirely, so the vocabulary may
  be incomplete on a long-lived app.
- **Users are not sampled at all.** The defaults cover `name`/`username` and
  `image`/`profileImage`/`avatar`; any other key has to be confirmed separately.
- **Code is not the only writer.** When the mapping used the integration code,
  say which keys rest on code alone, and that other services, mobile clients
  writing with user tokens, scripts and older app versions may write shapes the
  code does not show.
- **Feed groups are not covered evenly.** The sample does not say which group
  an activity came from. Name the groups you read with `--feed`, and the ones
  neither the sample nor `--feed` covered.
- **Rare shapes hide in the tail.** A field present on 1% of activities may not
  show up in 100 rows. Where a mapping decision hinges on a field's presence,
  say which sampled rows carried it.
- **The sample moves.** Re-running later can rotate rows out under the
  5-per-kind cap and bring new shapes in, so a second run is a cheap way to firm
  up a decision that rested on a single row.

Before finalizing, check each key you emitted against the worked examples in
[`mapping-keys.md`](mapping-keys.md). Matching a documented shape is good
evidence the path and nesting are right; not matching one is worth a second look
at the sample.

---

## Hand-off

- **SDK questions about the v3 Feeds API** (what a v3 activity, comment, or
  bookmark looks like in a given SDK) -> `getstream docs`.
- **Porting the app's existing v2 code** -> the porting plan (step 7); edit
  code only when the user asks, following the plan.
- **Building or updating the app against v3** once the mapping is settled ->
  the platform pack for that app (`stream-react`, `stream-swift`,
  `stream-android`, `stream-react-native`, `stream-flutter`).

## Support

If the user asks for support or how to contact someone, direct them to
[getstream.io/contact](https://getstream.io/contact/).
