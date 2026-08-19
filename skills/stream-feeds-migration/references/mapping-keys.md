# v2 -> v3 mapping keys

Every key below lives inside the `mapping` object of an app's v2 -> v3 sync
configuration. The same map drives **both** the live syncer and the bulk
exporter - there is one mapping, not two. Any key you add produces the same v3
shape on both paths.

Omit a key to accept its default. An empty mapping is valid and correct for an
app whose v2 data already matches v3 conventions.

---

## Activity keys

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `id` | string (dot-path into extra_context) | `""` (off) | Read the v3 activity id from this field. Highest-precedence id source. |
| `foreign_id` | string | - | The literal value `"id"` makes the v2 `foreign_id` the v3 activity id. Any other value is an ordinary field rename. |
| `parent_id` | string (extra_context field) | `""` (off) | Field holding the parent activity ref for reshares/replies. |
| `activity_attachments_field` | string (dot-path) | `""` (off) | Lift this list out of extra_context into v3 `attachments`. |
| `text` | string | `"text"` | Which extra_context field feeds v3 `Text`. |
| `object` | string | - | Rename of the `object` field. Applies only when the v2 value is structurally a JSON object; plain refs like `object:abc` stay under `object`. |
| `extra_context` | string | `"extra_context"` | Key under which the whole v2 extra_context bag nests inside v3 `custom`. **`""` flattens it directly into custom** - distinct from unset. |
| `replaces` | map[string]string | `{}` | Literal string substitutions applied to user and foreign IDs *before* the `SU:` prefix is stripped. |
| *any other key* | string | - | Generic field rename, see below. |

### v3 activity id precedence

Applied identically by v3sync and the exporter:

1. `id` field mapping, if set **and** it resolves to a non-empty string
2. else `foreign_id: "id"`, if set -> use the v2 `foreign_id`
3. else the v2 activity UUID

Whenever the id is overridden the original v2 UUID is preserved at
`custom.original_id`, so the mapping stays reversible.

### Generic field renames

Any mapping entry that isn't one of the reserved keys above is a rename:

- **key** - a field name, or a dot-path, in the v2 extra_context
- **value with a dot** - a dot-path *back into* extra_context (moves it, still nested)
- **value without a dot** - promoted to a top-level key in v3 `custom`

A rename **moves** a field rather than copying it: the source path is removed,
so the field appears only at its new location.

---

## Reaction keys

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `comments` | []string | `["comment", "reply"]` | v2 reaction kinds that become v3 **comments**. |
| `bookmarks` | []string | `[]` | Kinds that become v3 **bookmarks on an activity**. |
| `comments_bookmarks` | []string | `[]` | Kinds that become **bookmarks on a comment**. The v2 reaction must carry the comment's foreign_id in its top-level `parent`. |
| `reactions` | map[v2kind]v3type | `{}` | Rename a reaction kind to a different v3 type. Unlisted kinds keep their name. |
| `comment_field` | string | `"message"` | Field in reaction `data` used as the comment text. |
| `attachments_field` | string (dot-path) | `"attachments"` | Field in reaction `data` holding attachments. |
| `parent_id_field` | string (envelope path) | `"parent"` | Path whose non-empty value marks the reaction a **reply**. `""` disables reply detection. |
| `reaction_comment_id_field` | string (envelope path) | `""` (off) | Path holding the id of a comment this reaction targets. Routes to `AddCommentReaction`. |

### Reaction envelope paths

`parent_id_field` and `reaction_comment_id_field` resolve against the reaction's
JSON envelope, not just its data blob:

- `data` / `data.x.y` - descends into the reaction's `data` map
- `parent` - the top-level `ParentReaction` field
- `id`, `user_id`, `kind`, `activity_id` - the corresponding top-level fields

Note the default: `parent_id_field` is `"parent"`, so an app that stores the
parent comment id in the v2 reaction's top-level `parent` field needs **no
config at all** for replies to work.

### Legacy layout flags

A handful of apps predate the general-purpose keys above and were onboarded with
a bespoke reaction layout. Those layouts are selected by **boolean** keys that
are deliberately not part of this catalogue. They default to `false`, they are
never correct for a new migration, and the sample can never justify one.

Recognize one by shape rather than by name: **a boolean key that is not in the
reaction table above is a legacy layout flag.**

- **Never set one.** There is no app you are mapping for which one is right -
  the documented keys cover every shape a new migration needs.
- **Never name one in output** - not in the mapping, not in the omitted-keys
  list, not in prose, not even to note it was considered and rejected. Naming a
  flag that belongs to a different app's layout tells the reader about an
  arrangement that is not theirs.

You will only meet one while reading an existing config that already has it. In
that case leave it untouched and refer to it as "a legacy layout flag" rather
than carrying the literal key name into your response.

---

## User keys

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `name` | string (dot-path) or `false` | `"name"` | v2 user-data key the v3 user's **name** is read from. |
| `image` | string (dot-path) or `false` | `"image"` | v2 user-data key the v3 user's **image** is read from. |

**These two read in the opposite direction from every other string key**: the
map key is the *v3* field, the value is the *v2* source. They apply to users
only - an activity carrying its own `name` custom field is untouched by them,
because these two names are never treated as activity field renames.

Set `""` or `false` to disable a rename. Only non-empty *string* values are
renamed; a number or object at the source key stays put as ordinary custom data.

---

## Diagnostics

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `debug` | bool | `false` | Stamps the live mapping onto `custom._v3sync_debug` of every synced activity. Useful while validating a new mapping; turn it off afterwards. |

---

## Non-mapping config fields

These sit alongside `mapping` in the sync configuration, not inside it. They are
listed so you recognize them as *not* mapping keys - the deliverable is the
`mapping` object alone, so do not emit them:

- `enabled` - the sole on/off switch for replication
- `base_url` - v3 endpoint, defaults to `https://feeds.stream-io-api.com`
- `api_key` / `secret` - the **v3** app credentials
- `sample_rates` - per-operation replication rate (`FeedAdd`, `AddReaction`,
  `UpsertUser`, ...); `1.0` mirrors everything
- `feed_groups_synced` - whether feed groups already exist in v3

---

## Worked examples

Each block is a v2 shape as it appears in the sample, paired with the mapping
key it calls for. Matching one of these is good evidence the path and nesting
are right.

**Reply comment, parent nested in `data`** - top-level `parent` is absent, so
the default reply detection would find nothing:

```json
{ "kind": "comment",
  "data": { "comment": { "parent": { "id": "top-level-comment-fid" } },
            "message": "a reply" } }
```
-> `"parent_id_field": "data.comment.parent.id"`

A non-reply comment in the same app must leave that path absent:

```json
{ "kind": "comment", "data": { "message": "a top-level comment" } }
```

**Comment attachments under a nested path**:

```json
{ "kind": "comment",
  "data": { "message": "look", "media": { "files": [ { "type": "image" } ] } } }
```
-> `"attachments_field": "media.files"`

**Comment text under a different key**:

```json
{ "kind": "comment", "data": { "body": "the text" } }
```
-> `"comment_field": "body"`

**Bookmark on a comment** - the target comment's foreign_id must be in the
top-level `parent`:

```json
{ "kind": "comment_bookmark", "parent": "the-comment-fid" }
```
-> `"comments_bookmarks": ["comment_bookmark"]`

**Plain reaction that targets a comment** rather than the activity:

```json
{ "kind": "like", "data": { "comment_id": "the-comment-fid" } }
```
-> `"reaction_comment_id_field": "data.comment_id"`

**Activity id from a nested custom field**, with a fallback to `foreign_id`
when that field is absent:

```json
{ "extra_context": { "ext": { "activity_id": "external-123" } } }
```
-> `"id": "ext.activity_id"`, optionally with `"foreign_id": "id"`

**Reshare ref in a custom field**:

```json
{ "extra_context": { "shared_origin_post": "SA:9f1c..." } }
```
-> `"parent_id": "shared_origin_post"`

**Post body under a different key**:

```json
{ "extra_context": { "body": "the post text" } }
```
-> `"text": "body"`

**Activity attachments posted at the top level of the v2 body**:

```json
{ "extra_context": { "attachments": [ { "type": "image" } ] } }
```
-> `"activity_attachments_field": "attachments"`

**Non-`SU:` actor prefix**:

```json
{ "actor": "User:1234" }
```
-> `"replaces": { "User:": "" }`

**extra_context placement** - a preference, not a sample finding. Default nests
the bag under `custom.extra_context`; `"extra_context": "stuff"` nests it under
`custom.stuff`; `"extra_context": ""` flattens every key directly into `custom`.
