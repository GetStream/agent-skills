# Feeds — region checklist + routing

Activity card, composer, comments, follow affordances, notification feed. Feeds has no prebuilt RN UI, so the Axis column means something different here — read the section preamble.

Tier 2 of the design-match decomposition. The method that drives it — the three axes, how to
measure sizes, how to sample colours, and the Step 3 verify loop — lives in
[`design-matching.md`](design-matching.md); read that first, then walk **every row** below.

The **Route to** column names the *mechanism*. Confirm the exact theme key / slot / prop name in
the manifest-selected docs and the installed package, never from memory.

---

Ported from the web skill's Feeds taxonomy + activity-card / comment-row / feed-composer contracts.
Feeds has **no prebuilt RN UI** — every region is a **fully custom component** you build yourself on
**state hooks** (from `@stream-io/feeds-react-native-sdk`) plus `client` / `feed` methods. Chat's
Theming / Layout / Functional axis taxonomy therefore doesn't apply; the **Axis** column below uses a
Feeds-specific vocabulary and the **Route to** column names the exact hook + method:

- **Custom · read** — render-only from a state hook
- **Custom · action** — read + a `client` / `feed` mutation
- **Custom · structure** — feed instantiation / navigation / server-side config

There is no theme object and no component-override slot to reach for here — matching a reference means
reproducing the design's layout, spacing, and colors in your own components. **Confirm every exact
hook / method / field name against the installed package** (`@stream-io/feeds-react-native-sdk`, which
re-exports `@stream-io/feeds-client`) **and the RN Feeds docs** before coding — names below are
verified against the current source but can drift across versions.

**Feed surfaces** (if in scope)

| Region | What to check | Axis | Route to |
|---|---|---|---|
| Activity card | avatar + author name + relative timestamp + text; attachments (image / link preview); long-text handling | Custom · read | `useFeedActivities(feed)` → `{ activities, is_loading, has_next_page, loadNextPage }` (feed optional inside `StreamFeed`). Render each `ActivityResponse` yourself: `user` (author), `created_at`, `text`, `attachments` (`image_url`/`asset_url` by `type`). No prebuilt card — you own the layout, avatar shape, and long-text truncation. |
| Activity reactions | heart/like glyph + count; own-reaction (selected) state toggle | Custom · action | Own/counts from `activity.own_reactions` / `activity.reaction_groups` (+ `latest_reactions`); toggle with `client.addActivityReaction({ activity_id, type, enforce_unique })` / `client.deleteActivityReaction({ activity_id, type })`. Gate the button on `useOwnCapabilities(feed)` (`ADD_ACTIVITY_REACTION` / `DELETE_OWN_ACTIVITY_REACTION`). |
| Comments | speech-bubble + count, open-comments affordance; comment row (avatar, author, timestamp, text); nested replies; post-a-comment input | Custom · action | Count from `activity.comment_count`; list with `useActivityComments({ feed, activity })` (or `useComments({ parent: activity })`) → `{ comments, has_next_page, is_loading_next_page, loadNextPage }`; add via `client.addComment({ object_id: activity.id, object_type: 'activity', comment, mentioned_user_ids })`. **Nested replies:** pass a comment as the parent (`useComments({ parent: comment })` / `useActivityComments({ parentComment })`), read `comment.reply_count`. Comment reactions: `client.addCommentReaction` / `deleteCommentReaction` (no dedicated hook — reuse the same reaction UI). |
| Repost | two circular arrows + count — present? | Custom · action | **No dedicated repost method.** Share by `feed.addActivity({ type, text, parent_id: original.id })`, which increments `original.share_count`; read the shared parent via `activity.parent`, and the count via `activity.share_count`. |
| Bookmark | bookmark/save flag toggle — present? | Custom · action | Own/count from `activity.own_bookmarks` / `activity.bookmark_count`; toggle with `client.addBookmark({ activity_id, folder_id? })` / `client.deleteBookmark({ activity_id })`. Folders (if the design groups saves): `client.queryBookmarkFolders` / `updateBookmarkFolder`. No dedicated hook — read off the activity. |
| Follow button | follow / unfollow affordance (profiles, suggestions); follower / following counts | Custom · action | Follow state via `useOwnFollows(feed)` → `own_follows` (match `source_feed.group_id === 'timeline'`, read `.status`: `accepted` / `pending` / `rejected` → Following / Requested / Follow); toggle `timelineFeed.follow(targetFeed, { create_notification_activity, push_preference })` / `timelineFeed.unfollow(targetFeed)`. Counts/lists: `useFeedMetadata(feed)` (`follower_count` / `following_count`) or `useFollowers(feed)` / `useFollowing(feed)`. Suggestions: `client.getFollowSuggestions`. |
| Feed composer | "What's on your mind" post box: text input + submit, attachment upload / preview, mentions, poll creation; position; posts appear without reload | Custom · action | Create with `feed.addActivity({ type, text, attachments, mentioned_user_ids, poll_id })` (or `client.addActivity({ feeds: [...] })` to post to multiple feeds at once). Uploads: `client.uploadImage({ file })` / `client.uploadFile({ file })` (helpers `isImageFile` / `isVideoFile`, type `StreamFile`) → map results into `attachments` (`image_url` vs `asset_url`). Mentions: `mentioned_user_ids` (find candidates via `client.queryUsers`; the app renders the @-text itself). Poll: `client.createPoll(...)` then attach `poll_id`. Posts appear live when the feed is watched (`getOrCreate({ watch: true })`). |
| Notification feed | aggregated "X and N others…" rows + bell; unread / unseen treatment | Custom · action | Feed group `notification` (`client.feed('notification', userId)`); rows via `useAggregatedActivities(feed)` → `aggregated_activities` (each `AggregatedActivityResponse`: `is_read` / `is_seen`, `activity_count`, `user_count`, `.activities`, `.group`). Bell/badge counts: `useNotificationStatus(feed)` → `{ unread, unseen }`; per-row read/seen from `aggregatedActivity.is_read` / `.is_seen` directly (`useIsAggregatedActivityRead` / `…Seen` are deprecated). Mark: `feed.markActivity({ mark_read: [group] })` / `{ mark_all_seen: true }`. |
| Multiple / For You feeds | tab switcher over the feed (e.g. Timeline vs. For You) — present? | Custom · structure | Each feed is a separate `client.feed(group, id)` + `feed.getOrCreate({ watch: true })`, wrapped in its own `<StreamFeed feed={…}>`; the tab switcher renders one feed at a time (e.g. `timeline` vs `user` vs a For-You group). For-You ranking is server-side (feed-group `activity_selectors` + `ranking`); RN just reads it like any feed (optionally `getOrCreate({ interest_weights })`), and `activity.selector_source` (`following`/`popular`/`interest`) tells you why an item ranked. Instantiate feeds with a query-hook pattern (see the sample's `useCreateAndQueryFeed`). |
| Poll activity | poll inside a post (options, vote bars, counts) — present? | Custom · action | Poll data on `activity.poll` (`PollResponseData`: `options`, `vote_count`, `vote_counts_by_option`, `own_votes`); for live vote updates use `client.pollFromState(pollId)` + `useStateStore(poll.state, selector)` (**no `usePoll` hook**). Vote: `client.castPollVote({ activity_id, poll_id, vote: { option_id } })`; remove: `client.deletePollVote(...)`; manage: `client.closePoll` / `createPollOption`. Create in the composer via `client.createPoll(...)` → `poll_id`. |
| Loading / empty / pagination | empty-feed state, loading skeleton, load-more / infinite scroll | Custom · read | Loading from the hook's `is_loading` / `is_loading_next_page`; infinite scroll = wire `loadNextPage()` to `FlatList` `onEndReached`, gated on `has_next_page` (start narrow with `getOrCreate({ limit })`). Empty state: check `activities.length === 0 && !is_loading` (no dedicated empty-state API). Connection-lost banner: `useWsConnectionState()`; `useClientConnectedUser()` returns `null` until connected — render a placeholder until then. |
