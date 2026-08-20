---
name: stream-feeds-migration
description: "Generate the v2 -> v3 sync mapping for a Stream Activity Feeds app by sampling its live v2 activities and reactions. Use when setting up a Feeds v2 to v3 migration, when asked to build, review, or debug a v3 sync mapping, when someone asks 'what mapping do we need for our app?', or when a migrated activity lands in v3 with missing text, missing attachments, comments that are not comments, or bookmarks that went missing. Triggers on v3sync, v2 to v3, feeds migration, activity feeds migration, sync mapping, extra_context, reaction kinds, comments and bookmarks mapping. The same mapping drives both the live syncer and the bulk exporter."
license: See LICENSE in repository root
compatibility: Requires the v2 app's API key and secret, exported as environment variables, plus Python 3 (standard library only - no pip install). Read-only against the v2 app; writes one sample file to the working directory. No project or SDK required.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Glob, Grep,
  Bash(python3 *),
  Bash(ls *),
  Bash(getstream *)
---

# Stream Feeds - v2 to v3 sync mapping

> **Read first (every session):** Glob `../stream/SKILL.md` and Read [`../stream/RULES.md`](../stream/RULES.md) (both ship with this skill). The **Secrets** rule governs every step below: the app secret never enters the conversation. RULES.md also carries the **Peer skills** procedure for installing and invoking any other pack skill on demand.

Produce the `mapping` object for an app's v2 -> v3 sync configuration by looking
at what the app's v2 data actually contains, rather than at what anyone believes
it contains.

One mapping serves both migration paths - the live syncer and the bulk exporter
read the same configuration. Getting it right once fixes both; getting it wrong
breaks both in the same way.

---

## Workflow

### 1. Get credentials into the environment

You need the **v2 app's** API key and secret. The secret signs an HS256 JWT
locally, stamped with `iat`/`exp` so it expires five minutes after it is minted.
The secret itself is never written to the sample file, never echoed back, and
never sent anywhere except as that signature.

Per [`../stream/RULES.md`](../stream/RULES.md) > **Secrets**, do not ask the user
to paste the secret into the chat, and never `cat`, `grep`, or Read a `.env`
file to find it. Ask them to export it themselves so it stays out of the
transcript:

```
! export STREAM_API_KEY=<v2 app key> STREAM_API_SECRET=<v2 app secret>
```

The `!` prefix runs the command in the user's own session, so the value lands in
the environment without passing through the conversation. Confirm it took with a
presence check that never prints the value:

```bash
test -n "$STREAM_API_SECRET" && echo SECRET_SET || echo SECRET_MISSING
```

Do not proceed without a real key and secret. There is no useful analysis to do
against a made-up app, and a wrong secret only produces a 403.

### 2. Pick the target

**Default to production** - `https://api.stream-io-api.com`. Use it unless the
user names a different environment (EU, dedicated, staging), in which case pass
`--base-url <that URL>`.

Do not raise alternative environments on your own; production is the assumed
target and the user will say so if they mean otherwise.

### 3. Fetch the sample

```bash
python3 <skill-dir>/scripts/fetch_sample.py --out v3sync-sample.json
```

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
environment variable avoids. (`--api-key` exists, since the key is not sensitive.)
The sample is written to the working directory, which is where you want it.

Standard library only - no pip install. It calls two server-side-only endpoints:

- `GET /api/v1.0/migration/sample/activities` - the last 100 activities
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

### 4. Analyze

Read `v3sync-sample.json` and work through the checklist below. Read
[`references/mapping-keys.md`](references/mapping-keys.md) for the full key
catalogue, defaults, exact resolution rules, and worked examples of the common
shapes - **do not guess key names or defaults from memory.**

The single most common mistake is over-configuring. Every key has a default
that is right for a conventional v2 app. Only emit a key when the sample shows
the app deviates from that default. An empty mapping is a valid answer.

### 5. Emit the mapping

Produce **only** the `mapping` object, ready to paste into the app's existing
sync configuration. Do not emit the surrounding configuration (`enabled`,
`base_url`, `api_key`, `secret`, `sample_rates`, `feed_groups_synced`); those
are deployment concerns, they are not derived from the sample, and restating
them with placeholder credentials invites someone deploying a config with a
`<v3 app key>` still in it.

Explain each key you set by pointing at the evidence in the sample.

Flag explicitly anything you could not determine from the sample - see
**Limits of the sample** below. Silence there reads as "verified", which it is not.

---

## Analysis checklist

### Activities

Look at `activities[].extra_context` across all 100.

- **Custom field names** - any field whose name collides with a v3 reserved key,
  or that should be surfaced at the top level of `custom`, needs a rename entry.
  Fields that are already conventionally named need nothing.
- **Activity id** - does a field hold a stable external id (`external_id`,
  `post_id`, `uuid`)? If so, `id` should point at it. If instead `foreign_id`
  is populated and meaningful across the sample, `foreign_id: "id"` is the
  simpler answer. If neither, omit both and let the v2 UUID carry over.
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

Look at `kinds` first - that list is the app's whole reaction vocabulary.

- **Classify every kind** into exactly one of: comment, bookmark,
  comment-bookmark, or plain reaction. Then set `comments`, `bookmarks`,
  `comments_bookmarks` accordingly. A kind you leave out of all three is a
  plain reaction, which is often correct.
- Remember the defaults: `comments` already covers `["comment", "reply"]`. If
  those are the app's only comment kinds, do not restate them.
- **Comment text** - inspect the `data` of a comment-kind reaction. Default is
  `data.message`; if the text lives under `body` or `text`, set `comment_field`.
- **Replies** - is the parent comment id in the top-level `parent` (the
  default, no config needed) or nested in `data`? If nested, set
  `parent_id_field` to that envelope path. Confirm against a **non**-reply too:
  a top-level comment must leave that path empty, or every comment would be
  treated as a reply.
- **Reactions on comments** - a non-comment reaction carrying a comment id in
  its `data` needs `reaction_comment_id_field`.
- **Kind renames** - only if the app should use different type names in v3.
- **Attachments** - `attachments_field` if comment attachments are not under
  `data.attachments`.

Watch for **one kind carrying two incompatible shapes** - e.g. some `like`
rows holding a comment id at one path and others at a different one. The
single-path keys (`parent_id_field`, `reaction_comment_id_field`) cannot serve
both. Say which rows the mapping will not cover instead of picking one silently.

Some apps carry **legacy layout flags** - see *Legacy layout flags* in
[`references/mapping-keys.md`](references/mapping-keys.md). Never set one.

### Users

The sample endpoints return activities and reactions, not users, so **user
field mapping cannot be inferred from it**. If display name or avatar are stored
under non-standard keys, ask, then set `name` / `image` - remembering those two
keys read v3-key-to-v2-source, backwards from every other string key.

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
legacy layout flag (see [`references/mapping-keys.md`](references/mapping-keys.md))
in that list, in the mapping, or anywhere else in your response - not as a row,
not as an aside, not even to say it was considered and rejected. They are
irrelevant to the app in front of you, so there is nothing to justify: leave
them out silently.

Suggest `"debug": true` in the mapping for the initial validation run - it
stamps the live mapping onto `custom._v3sync_debug` of every synced activity -
and remind the user to remove it once the mapping is confirmed.

---

## Limits of the sample

State whichever of these apply alongside the generated mapping. They are the
difference between "this mapping is correct" and "this mapping fits the sample":

- **Activities are the most recent 100.** A field that only older activities
  carry will not appear. Apps whose schema changed over time are exactly the
  ones where this bites.
- **Reactions are drawn from a bounded recent window.** A kind that has not
  been used lately can be missing from `kinds` entirely, so the vocabulary may
  be incomplete on a long-lived app.
- **Users are not sampled at all.** Any `name` / `image` mapping has to be
  confirmed separately.
- **Rare shapes hide in the tail.** A field present on 1% of activities may not
  show up in 100 rows. Where a mapping decision hinges on a field's presence,
  say which sampled rows carried it.
- **The sample moves.** Re-running later can rotate rows out under the
  5-per-kind cap and bring new shapes in, so a second run is a cheap way to
  firm up a decision that rested on a single row.

Before finalizing, check each key you emitted against the worked examples in
[`references/mapping-keys.md`](references/mapping-keys.md). Matching a documented
shape is good evidence the path and nesting are right; not matching one is worth
a second look at the sample.

---

## Hand-off

- **SDK questions about the v3 Feeds API** (what a v3 activity, comment, or
  bookmark looks like in a given SDK) -> `stream-docs`.
- **Building or updating the app against v3** once the mapping is settled ->
  the platform pack for that app (`stream-react`, `stream-swift`,
  `stream-android`, `stream-react-native`, `stream-flutter`), per
  [`../stream/peers.yaml`](../stream/peers.yaml).

Offer, do not auto-execute - see [`../stream/RULES.md`](../stream/RULES.md) >
**Cross-track follow-ups**.

## Support

If the user asks for support or how to contact someone, direct them to
[getstream.io/contact](https://getstream.io/contact/).
