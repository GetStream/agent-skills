# Porting plan: moving the app's code from v2 to v3

The mapping moves the app's data. The porting plan covers its code: what each
v2 call in the app becomes in v3, and when in the switch-over it changes. It is
built from the code inventory (see `code-inventory.md`), so it exists only
when the app's repository is available.

A plan can be written from the code alone, before or without the sample.
Mark every row whose outcome depends on the mapping (field names, ids, older
formats) as pending the sample, and settle it once the mapping is.

The plan is a document. Writing it changes nothing in the app. Edit code only
when the user asks for it after reading the plan, and then follow the rules in
**Porting the code** below.

---

## 1. The switch-over order

Live replication keeps mirroring v2 writes into v3 until the migration is
completed in the Dashboard. Every plan follows this order:

| Step | Writes go to | Reads come from | What changes in the code |
| --- | --- | --- | --- |
| 1 | v2 (replicated) | v2 | nothing |
| 2 | v2 (replicated) | v2, plus shadow reads from v3 | ported read paths run beside the v2 ones and are compared |
| 3 | v2 (replicated) | v3 | the read flag is flipped |
| 4 | v3 | v3 | every write path flips together; v2 writes stop in the same deploy |

Code that runs on users' devices moves with its kind: realtime subscriptions,
user tokens and client-side reads move with the reads (steps 2 and 3);
client-side writes move with the writes (step 4). If client apps write to
Feeds directly, step 4 cannot wait for every user to update the app: control
the write flag remotely (a server-side setting the apps read), or route those
writes through the backend before the switch.

Never let the app write the same thing to both versions: a v2 write is
replicated into v3, so a v3 write on top of it is applied twice. Write paths
are switched all at once, never one feature at a time.

---

## 2. Find the read paths

The scanner lists writes only. Find the read paths by hand: search for
`.get(` on feeds (`feed(...).get`, `flatFeed(...).get`), `getActivityDetail`,
`getActivities`, `reactions.filter` / `reactions.get`, `collections.get`,
`user(...).get`, and user-token creation (`createUserToken`, `create_user_token`,
`createToken`). Note what each read renders: the fields it takes from the
response decide which v3 fields replace them.

## 3. Find the v3 call for each path

The authoritative table of v2 -> v3 calls is the **V2 to V3 Code Migration**
guide (`/activity-feeds/docs/<sdk>/v2-to-v3-code-migration/`, through
`stream-docs`). Read it for each call; do not rely on memory of either API.
The SDK reference pages it links to hold the exact request fields.

Things the plan must call out per path, because they change behaviour rather
than just syntax:

- **Feeds and to-targets.** v2 `to` targets and `addToMany` become one `feeds`
  list on the v3 activity. Removing an activity from one feed while it stays in
  others is an update of that list, not a delete.
- **Fan-out: feeds list or follow.** When the content decides the feeds (a
  post's hashtags: `user:<author>`, `hashtag:cooking`), keep them in the
  activity's `feeds`. When the audience decides them (an announcement to every
  user, any list that grows with the user count), write once to one feed and
  have the recipients' feeds follow it. An activity is in at most 25 feeds by
  default; flag any list that can exceed it.
- **Feeds that must exist first.** v3 creates a missing feed on write only
  when its id is an existing user's id (`notification:bob`). Feeds keyed by
  something else (`hashtag:<tag>`, `announcement:all`) are the app's job to
  create before the first write; name the path that does it, or add one. Do not
  recreate them on every write (`createFeedsBatch` overwrites an existing
  feed's name, custom data and owner).
- **Ids.** v2 `foreign_id` becomes the v3 `id`. Updates by `foreign_id` +
  `time` become updates by `id`. With an `id`/`foreign_id` mapping, migrated
  activities carry the mapped id (the v2 id moves to `custom.original_id`);
  without it, activities and comments keep their v2 ids. Choose by what the app
  stores: if it stores v2 activity ids (database columns, URLs, mobile
  clients), keep them (no id mapping) and port `foreign_id`-based edits and
  deletes to use the stored id; if it only ever addresses activities by
  `foreign_id`, map `foreign_id` to `id`. Put the choice in the plan as a
  decision for the user, since it also decides the mapping.
- **Reactions are three APIs.** Activity reactions, comments (replies are
  comments with a `parent_id`), and bookmarks. A v2 child `like` on a comment is
  a v3 comment reaction. A v3 activity reaction is deleted by activity, type and
  user, so code that stored v2 reaction ids to delete likes changes shape.
- **Notifications.** v2 `targetFeeds` on reactions maps to `target_feeds` on v3
  activity reactions; for comments it becomes `create_notification_activity`.
- **Repeat reactions.** v3 holds one reaction of a type per user on an
  activity. A v2 guard against double-likes becomes redundant; an unguarded v2
  path changes behaviour (say so).
- **Reads.** Enriched v2 fields (`actor.data`, `reaction_counts`,
  `own_reactions`, `latest_reactions`, enriched `object`) move to `user`,
  `reaction_groups`, `own_reactions`, comment reads, `collections` and
  `parent`. Pagination moves from `id_lt` to `next` cursors.
- **Older formats.** If the inventory found older activity formats, the ported
  read path must still render them from `custom` (or the mapping must cover
  them).
- **Users and tokens.** v2 user `create`/`update` become user upserts with
  `name`, `image` and `custom`; user tokens come from the v3 client.

---

## 4. Write the plan

One row per write or read path from the inventory:

| Path | Code | v2 call | v3 call | Step | Changes and decisions |
| --- | --- | --- | --- | --- | --- |
| Like a post | `reactions.js:12` | `reactions.add('like', id, {}, { userId, targetFeeds })` | `feeds.addActivityReaction({ activity_id, type: 'like', user_id, target_feeds })` | 4 | delete changes from reaction id to activity + user; DB guard now redundant |
| Home timeline | `feeds.js:40` | `feed('timeline', id).get({ enrich: true, withOwnReactions: true })` | `feeds.feed('timeline', id).getOrCreate({ user_id, limit, next })` | 2, 3 | counts from `reaction_groups`; `body` posts render from `custom.body` |

Then, below the table:

- **Read flag and write flag**: where each would live in this app. The read
  flag has three states (`off`, `shadow`, `on`); the write flag has two, and
  must be controllable without shipping a client update if clients write
  directly.
- **Stored ids**: every place the app stores or compares v2 ids (database
  columns, URLs, caches), and whether each keeps working (see **Ids** above).
- **Open decisions** for the user: behaviour that changes (repeat reactions,
  notifications), and any path whose v3 equivalent the guide does not cover.
- **What was not read**: paths built at runtime or reached through code the
  inventory could not follow.

---

## 5. Porting the code (only when asked)

When the user asks you to port the code, keep the switch-over order in the
code itself:

- Add the v3 client beside the v2 client; do not remove v2 code.
- Put every ported read path behind the **read flag** (with a shadow mode that
  calls both and logs differences) and every ported write path behind the one
  **write flag**. With both flags off the app behaves exactly as before.
- Never add a code path that writes to both versions.
- Port path by path from the plan, and keep the plan's row next to each change
  (in the commit message or PR description) so a reviewer can check it.
- Leave removing the v2 code for after the migration is completed.
