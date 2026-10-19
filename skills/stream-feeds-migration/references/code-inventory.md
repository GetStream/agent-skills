# Reading the v2 integration code

The sample shows what the v2 app has stored. The integration code shows every
way the app writes it: each write path, the feed group it writes to, the fields
it sets, the reaction kinds it uses, how child reactions are made, and how users
are created. Use both. Code is intent; stored data is the truth. Where they
disagree, the disagreement is the finding.

---

## 1. Find the write paths

Run the scanner from the skill's `scripts/` directory against the app's
repository (read-only, standard library only, writes one JSON file):

```bash
python3 <skill-dir>/scripts/scan_v2_calls.py --root <repo> --out v2-code-scan.json
```

It lists every v2 write call site with its file, line, call kind, the feed
groups named near it (`feed_groups_nearby`), the reaction kind when it is a
literal, and a short snippet. Long key-like tokens and string literals on lines that
mention a secret are replaced with `<redacted>`. Never copy a secret out of the
code into the conversation, even if the scanner missed one.

Call kinds:

| Kind | What it writes |
| --- | --- |
| `add_activity`, `add_activities` | a new activity in one feed |
| `add_to_many` | one activity into many feeds |
| `update_activities`, `partial_update` | activity content |
| `update_to_targets` | an activity's to-targets |
| `remove_activity` | an activity removed from a feed |
| `reaction_add`, `reaction_add_child` | a reaction, or a child reaction (reply or reaction on a reaction) |
| `reaction_update`, `reaction_delete` | reaction edits and deletes |
| `follow`, `follow_many`, `unfollow`, `unfollow_many` | follows |
| `user_write` | user creation and updates |
| `collection_write` | collection entries |
| `rest_call` | raw REST calls to the v2 API |

Most apps create the client in one module (`lib/stream.js`,
`StreamService.java`) and import it everywhere else. The scanner follows that
one level: a file that imports the SDK module counts as SDK code
(`sdk_files_indirect` names the module it came through). Feed groups kept in
constants (`FeedGroup = { USER: 'user' }`, `USER_FEED = "user"`) and helpers
that return one feed (`userFeed = (id) => client.feed('user', id)`) are read
from those modules (`feed_group_constants`, `feed_helpers`), and a reference
to either near a call counts as that group.

The scanner finds calls, not meaning. Feed groups and reaction kinds built at
runtime, a client reached through more than one module, and Java's positional
arguments (`reactions().add(userId, kind, ...)`) show up without a value: read
those call sites. Calls through the app's own wrapper functions are listed as
`wrapper_call` (`wraps` names the function); the payload is built either inside
the wrapper or at these call sites, so read both.

The output JSON holds `calls` (each with `file`, `line`, `kinds`,
`feed_groups_nearby`, `reaction_kinds`, `snippet`, and `sdk_via` when the file
reaches the SDK through another module), plus `sdk_files`,
`sdk_files_indirect`, `feed_group_constants` and `feed_helpers`.

Method names by SDK, for searching by hand:

| SDK | Activities | Reactions | Users |
| --- | --- | --- | --- |
| JavaScript (`getstream`) | `feed(g, id).addActivity`, `addActivities`, `client.addToMany`, `updateActivities`, `activityPartialUpdate`, `removeActivity` | `reactions.add`, `reactions.addChild` | `user(id).create` / `update` / `getOrCreate` |
| Python (`stream`) | `feed(g, id).add_activity`, `add_activities`, `add_to_many`, `update_activities`, `activity_partial_update` | `reactions.add`, `reactions.add_child` | `users.add`, `users.update` |
| Ruby (`stream`) | `feed(g, id).add_activity`, `add_activities`, `add_to_many` | `reactions.add`, `reactions.add_child` | `users.add` |
| PHP (`GetStream\Stream`) | `feed(g, id)->addActivity`, `addActivities`, `addToMany` | `reactions()->add`, `reactions()->addChild` | `users()->add` |
| Go (`stream-go2`) | `FlatFeed(g, id)`, `AddActivity`, `AddActivities`, `AddToMany`, `UpdateActivities`, `PartialUpdateActivities` | `Reactions().Add`, `Reactions().AddChild` (kind in the request's `Kind`) | `Users().Add` |
| Java (`io.getstream.client`) | `flatFeed(g, id).addActivity`, `addActivities` | `reactions().add(user, kind, ...)`, `reactions().addChild(...)` | `user(id).create` |
| .NET (`Stream.Net`) | `Feed(g, id).AddActivityAsync`, `AddActivitiesAsync` | `Reactions.AddAsync`, `Reactions.AddChildAsync` | `Users.AddAsync` |

---

## 2. Build the inventory

Read each call site the scanner found (and the code that builds its payload),
and fill one row per **write path** - a distinct place in the app that writes
v2 data, not one row per line:

| Write path | Code | Feed group(s) | To-targets | Fields set | `foreign_id` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| New post | `posts/service.js:42` | `user` | `notification:<mentioned>` | `text`, `attachments.images`, `mentions` | `post:<db id>` (unique) | |
| Like | `reactions.js:10` | - | `notification:<owner>` | kind `like` | - | target feeds: writes reference activities |

For each write path, settle these. They map directly onto mapping keys:

- **Fields** - which keys hold the post text, media, mentions, reshare refs
  (`SA:`), collection refs (`SO:`), and anything the app reads back. Every key
  other than `actor`, `verb`, `object`, `target`, `time`, `foreign_id`, `to`
  and `id` lands in `extra_context`.
- **`foreign_id`** - how it is built. A database id (`post:<id>`) is unique; a
  value reused across activities (a shared object id, a slug) is not, so
  `"foreign_id": "id"` must not be recommended (see SKILL.md).
- **Feed groups** - which group each path writes to. A path that writes to a
  group nothing else writes to (a backend job filling `notification`, an
  import script) is exactly what the sample can miss: check it with `--feed`.
- **Reaction kinds and data** - every kind, the key that holds comment text
  (`comment_field`), comment attachments (`attachments_field`), and the kinds
  added with `addChild`:
  - a comment-kind child is a reply (default `parent_id_field: "parent"`);
  - a non-comment child (a like on a comment) needs
    `"reaction_comment_id_field": "parent"`.
- **Repeat reactions** - whether the app checks for an existing reaction before
  adding one. If not, a user can hold two reactions of the same kind in v2;
  v3 keeps one, so counts can drop. Say so.
- **Users** - which keys hold the display name and avatar
  (`name`/`username`, `image`/`profileImage`/`avatar` are covered by default;
  anything else needs `name`/`image`).
- **Reads** - how the app renders an activity tells you which fields matter
  and whether it reads custom data flat or nested, which informs
  `extra_context`.

### History: older formats still in storage

Stored data outlives the code that wrote it. When a write path's fields look
like they changed, find out when:

```bash
git log -S'body' --oneline -- <file>
```

A field that was renamed or dropped means older activities still carry the old
one. One mapping serves one format: say which format the mapping targets and
which older activities will keep their content in `custom`.

---

## 3. Cross-check with the sample

| Code | Sample | Meaning |
| --- | --- | --- |
| field / kind / group present | present | Confirmed: map it. |
| present | absent | A rare, new or low-traffic path. Map it, say the evidence is code only, and read a feed of it with `--feed` if you can. |
| absent | present | Another writer (a different service, a mobile client writing with a user token, a script) or an older code version. Ask the user; the mapping must still cover it. |
| differs (e.g. `body` vs `text`) | either | An older format. Pick the current one, and name the activities the mapping will not fit. |

The sample stays the source of truth: the code is rarely the only writer, and
it cannot show what an old version stored. A mapping built from the code alone
is never "verified".

---

## Worked example

A small Node.js integration writes four kinds of activity. The inventory
(trimmed) shows:

- **Posts** in `user:<author>` with `text`, `attachments.images` and `mentions`
  (`SU:` refs); every sixth post also goes to `notification:<mentioned>` and
  `tag:<topic>`. `foreign_id` is `post:<id>`, unique by construction.
- **Older posts** used `body` and `media` instead of `text` and `attachments`
  (in a real repository, `git log -S'body'` dates the change). The sample only
  contained the current format, so the code is the only evidence for the old one.
- **Reshares** with `shared_origin_post: "SA:<id>"` (autodetected).
- **Likes** sent with `targetFeeds: ["notification:<owner>"]`, so v2 also
  writes reference activities into notification feeds. The sample leaves
  those out (`reaction_reference_count`).
- **Comments** with text under `data.text` -> `comment_field: "text"`;
  replies made with `reactions.addChild("comment", ...)` (default parent
  handling) and likes on comments made with `reactions.addChild("like", ...)`
  -> `reaction_comment_id_field: "parent"`.
- **Users** created with either `name` + `profileImage` or `username` +
  `avatar` - both covered by the defaults, so no `name`/`image` keys.
- **No repeat-reaction guard** around `reactions.add` - counts can drop in v3.

Resulting mapping:

```json
{ "comment_field": "text", "bookmarks": ["bookmark"], "reaction_comment_id_field": "parent" }
```

with the limits stated: older `body`/`media` posts keep that content in
`custom`, and repeat likes collapse to one.
