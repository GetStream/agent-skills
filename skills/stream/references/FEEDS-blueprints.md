# Feeds - full component blueprints

Setup, routes, and gotchas: [FEEDS.md](FEEDS.md). Rules: [../RULES.md](../RULES.md).

---

## Activity

The core content unit in a feed.

### Blueprint

```html
<article class="activity">

  <header class="activity__header">
    <a class="activity__actor" href="/user/{user.id}">
      <img class="activity__avatar" src="" alt="" />
    </a>
    <div class="activity__meta">
      <a class="activity__author" href="/user/{user.id}"></a>
      <span class="activity__type"></span>
      <time class="activity__time" datetime=""></time>
    </div>
    <div class="activity__menu">
      <button class="activity__menu-trigger" aria-label="More options"></button>
      <div class="activity__menu-dropdown">
        <!-- CONDITIONAL: only if activity.user.id === currentUser.id -->
        <button class="activity__menu-item activity__menu-item--edit">Edit</button>
        <button class="activity__menu-item activity__menu-item--delete">Delete</button>
        <!-- Always visible -->
        <button class="activity__menu-item activity__menu-item--report">Report</button>
        <button class="activity__menu-item activity__menu-item--copy-link">Copy link</button>
      </div>
    </div>
  </header>

  <div class="activity__body">
    <!-- Parse @mentions -> <a class="activity__mention">, #hashtags -> <a class="activity__hashtag">, URLs -> <a class="activity__link"> -->
    <div class="activity__text"></div>

    <!-- CONDITIONAL: activity.attachments contains item with og_scrape_url -->
    <a class="activity__og" href="" target="_blank" rel="noopener">
      <img class="activity__og-image" src="" alt="" />
      <div class="activity__og-content">
        <span class="activity__og-title"></span>
        <span class="activity__og-description"></span>
        <span class="activity__og-domain"></span>
      </div>
    </a>

    <!-- CONDITIONAL: activity.attachments contains items with type === "image" -->
    <!-- Modifiers: activity__gallery--single | --double | --triple | --grid -->
    <div class="activity__gallery">
      <figure class="activity__gallery-item">
        <img src="" alt="" />
      </figure>
      <!-- When image attachments count > 4, last item: -->
      <figure class="activity__gallery-item activity__gallery-item--overflow">
        <img src="" alt="" />
        <span class="activity__gallery-overflow-count">+3</span>
      </figure>
    </div>

    <!-- CONDITIONAL: activity.attachments contains items with type === "file" -->
    <div class="activity__files">
      <a class="activity__file" href="" download>
        <span class="activity__file-icon"></span>
        <span class="activity__file-name"></span>
        <span class="activity__file-size"></span>
      </a>
    </div>
  </div>

  <footer class="activity__footer">
    <div class="activity__reaction-summary"></div>
    <div class="activity__actions">
      <!-- See Reaction Bar component -->
    </div>
    <!-- CONDITIONAL: activity.latest_comments exists -->
    <div class="activity__comment-preview"></div>
  </footer>

</article>
```

### Wiring

| Element | Read | Write | Property Path |
|---|---|---|---|
| `activity__avatar` | `feed.getOrCreate()` | User profile update | `activity.user.image` |
| `activity__author` | `feed.getOrCreate()` | User profile update | `activity.user.name` |
| `activity__time` | `feed.getOrCreate()` | Set at creation | `activity.created_at` |
| `activity__type` | `feed.getOrCreate()` | Set at creation | `activity.type` (e.g. `"post"`, `"video"`) |
| `activity__text` | `feed.getOrCreate()` | `feed.addActivity({ type, text })` | `activity.text` |
| `activity__og-*` | `feed.getOrCreate()` | Automatic URL enrichment, or `client.getOG({ url })` + attach to `attachments[]` with `skip_enrich_url: true` | `activity.attachments[].og_scrape_url`, `.title`, `.text`, `.image_url` |
| `activity__gallery-item` | `feed.getOrCreate()` | `client.uploadImage({ file })` -> attach CDN URL as `{ type: "image", image_url }` in `attachments[]` | `activity.attachments[].image_url` (where `type === "image"`) |
| `activity__file` | `feed.getOrCreate()` | `client.uploadFile({ file })` -> attach CDN URL as `{ type: "file", asset_url }` in `attachments[]` | `activity.attachments[].asset_url` (where `type === "file"`) |
| `activity__menu-item--edit` | `activity.user.id === currentUserId` | `client.updateActivityPartial({ id, set: { text } })` | - |
| `activity__menu-item--delete` | `activity.user.id === currentUserId` | `client.feeds.deleteActivity({ id, hard_delete: false })` | - |
| `activity__reaction-summary` | `feed.getOrCreate()` | - | `activity.reaction_groups` (keyed by type) + `activity.latest_reactions` |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| User enrichment | Automatic in v3 | On - `activity.user` is always an enriched object |
| Reaction groups | Included in `feed.getOrCreate()` response | On - `activity.reaction_groups` always present |
| Own reactions | Included in `feed.getOrCreate()` response | On - `activity.own_reactions` always present |
| Latest reactions | Included in `feed.getOrCreate()` response | On - `activity.latest_reactions` always present |
| Comments | Latest 5 top-level comments included automatically | On - `activity.latest_comments` in response |
| Image CDN | Stream CDN | On by default |
| OG Scraping | Automatic URL enrichment on activity creation (or manual via `client.getOG({ url })`) | On - can disable per-request with `skip_enrich_url: true` |
| @Mentions | Server-side via `mentioned_user_ids` on creation; client-side text parsing for display | Always available |

---

## Activity Composer

Input area for creating a new activity.

### Blueprint

```html
<form class="composer">

  <div class="composer__author">
    <img class="composer__avatar" src="" alt="" />
  </div>

  <div class="composer__input-area">
    <div class="composer__text" contenteditable="true" role="textbox" aria-multiline="true" data-placeholder="What's on your mind?"></div>

    <!-- CONDITIONAL: user types "@" + characters -->
    <div class="composer__mention-dropdown">
      <button class="composer__mention-option">
        <img class="composer__mention-avatar" src="" alt="" />
        <span class="composer__mention-name"></span>
        <span class="composer__mention-handle"></span>
      </button>
    </div>
  </div>

  <!-- CONDITIONAL: URL detected in text and OG data fetched -->
  <div class="composer__og-preview">
    <img class="composer__og-image" src="" alt="" />
    <div class="composer__og-content">
      <span class="composer__og-title"></span>
      <span class="composer__og-description"></span>
      <span class="composer__og-domain"></span>
    </div>
    <button class="composer__og-remove" aria-label="Remove preview"></button>
  </div>

  <!-- CONDITIONAL: user has selected files -->
  <div class="composer__attachments">
    <div class="composer__attachment">
      <!-- Modifiers: composer__attachment--uploaded | --error -->
      <img class="composer__attachment-preview" src="" alt="" />
      <button class="composer__attachment-remove" aria-label="Remove"></button>
      <div class="composer__attachment-progress">
        <div class="composer__attachment-progress-bar" style="width: 0%"></div>
      </div>
    </div>
  </div>

  <div class="composer__toolbar">
    <div class="composer__tools">
      <button class="composer__tool composer__tool--image" aria-label="Add image"></button>
      <button class="composer__tool composer__tool--file" aria-label="Attach file"></button>
      <button class="composer__tool composer__tool--emoji" aria-label="Add emoji"></button>
    </div>
    <!-- OPTIONAL: multiple feed groups -->
    <select class="composer__target">
      <option value="user:{userId}">My Timeline</option>
      <option value="group:{groupId}">Group Name</option>
    </select>
    <button class="composer__submit" type="submit" disabled>Post</button>
  </div>

</form>
```

### Wiring

| Element | Read | Write | Property Path |
|---|---|---|---|
| `composer__avatar` | Connected user | - | `currentUser.image` |
| `composer__text` | - (user input) | Becomes `activity.text` | - |
| `composer__mention-dropdown` | `client.queryUsers(...)` for user search | - | Match typed query against users |
| `composer__og-preview` | `client.getOG({ url })` on URL detection | Attach to `activity.attachments[]` with `skip_enrich_url: true` | Response: `{ og_scrape_url, title, text, image_url }` |
| `composer__attachment` (image) | Local blob preview | `client.uploadImage({ file })` -> CDN URL | Collect as `{ type: "image", image_url }` in `attachments[]` |
| `composer__attachment` (file) | Local blob preview | `client.uploadFile({ file })` -> CDN URL | Collect as `{ type: "file", asset_url }` in `attachments[]` |
| `composer__submit` | - | `feed.addActivity({ type: "post", text, attachments, mentioned_user_ids })` | Target feed from `composer__target`; or use `feeds: ["user:john"]` for multi-feed |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| Image/file upload | Stream CDN via `client.uploadImage` / `client.uploadFile` | On - max size 100MB |
| OG scraping | `client.getOG({ url })` for preview before posting; or automatic enrichment on creation | Available - cache client-side |
| @Mention search | `client.queryUsers(...)` to find users; pass `mentioned_user_ids` on creation | Returns enriched `mentioned_users` in response |
| Target feed | `feeds` array in `addActivity` or call `feed.addActivity` on specific feed | - |

---

## Feed

Container that holds a list of activities. Handles pagination and real-time updates.

### Blueprint

```html
<div class="feed">

  <header class="feed__header">
    <h1 class="feed__title"></h1>
    <!-- OPTIONAL: sort/filter -->
    <div class="feed__controls">
      <select class="feed__sort">
        <option value="latest">Latest</option>
        <option value="popularity">Popular</option>
      </select>
    </div>
  </header>

  <!-- CONDITIONAL: real-time subscription has new activities -->
  <button class="feed__new-activities">
    <span class="feed__new-activities-count">3</span> new posts
  </button>

  <!-- OPTIONAL: show composer on own/home feeds -->
  <div class="feed__composer">
    <!-- Insert Composer component -->
  </div>

  <div class="feed__list" role="feed" aria-busy="false">
    <article class="feed__item">
      <!-- Insert Activity component -->
    </article>
    <!-- CONDITIONAL: aggregated/notification feeds -->
    <article class="feed__item feed__item--aggregated"></article>
  </div>

  <!-- States: feed__loading (skeleton), feed__empty, feed__error (with feed__error-retry button) -->

  <!-- Pagination: pick one -->
  <div class="feed__sentinel" aria-hidden="true"></div>        <!-- IntersectionObserver -->
  <button class="feed__load-more">Load more</button>           <!-- Manual -->

  <div class="feed__end">
    <p class="feed__end-message">You're all caught up</p>
  </div>

</div>
```

### Wiring

| Element | Read | Write | Notes |
|---|---|---|---|
| `feed__list` | `feed.getOrCreate({ watch: true, limit: 25 })` | - | Returns activities with reactions, comments, user data enriched automatically. Access via `feed.state.getLatestValue().activities` |
| `feed__load-more` / `feed__sentinel` | `feed.getNextPage()` (JS) or `feed.queryMoreActivities(limit:)` (native) | - | Cursor pagination: `next` token from response. Check `feed.state.getLatestValue().next` for more pages |
| `feed__new-activities` | `feed.getOrCreate({ watch: true })` then `feed.state.subscribe(callback)` | - | Real-time updates via WebSocket when `watch: true` |
| `feed__item` (remove) | - | `client.feeds.deleteActivity({ id })` | Optimistic: remove from DOM, rollback on error |
| Follow | `client.queryFollows(...)` | `timeline.follow("user:tom")` or `client.follow({ source: "timeline:alice", target: "user:tom" })` | Required for aggregated "Home" feeds |
| Unfollow | - | `timeline.unfollow("user:tom")` or `client.unfollow({ source, target })` | - |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| Feed group | Must exist in Dashboard -> Feed Groups | `user` and `timeline` exist by default |
| Real-time | `feed.getOrCreate({ watch: true })` then `feed.state.subscribe(callback)` | Available - managed WebSocket |
| Enrichment | Automatic in v3 | On - user, reactions, comments included by default |
| Flat feed | Feed group type = "flat" | Standard chronological |
| Aggregated feed | Feed group type = "aggregated" | Groups activities |
| Notification feed | Feed group type = "notification" | Adds `is_read` / `is_seen` |
| Ranking | Dashboard -> Feed Groups -> [group] -> Ranking | Off |
| Follow relationships | `timeline.follow("user:tom")` calls | Required for "Home" feeds |

---

## Reaction Bar

Action buttons beneath an activity: like, comment, repost, bookmark. All toggleable reactions use optimistic UI: toggle class + count immediately, API call async, rollback on error.

### Blueprint

```html
<div class="reaction-bar">

  <!-- LIKE: toggle, shows count -->
  <button class="reaction-bar__btn reaction-bar__btn--like" aria-pressed="false" aria-label="Like">
    <!-- aria-pressed="true" + modifier --active when own_reactions includes "like" -->
    <span class="reaction-bar__icon reaction-bar__icon--like"></span>
    <span class="reaction-bar__count reaction-bar__count--like"></span>
    <!-- Hide count when 0. Format: "1", "23", "1.2K" -->
  </button>

  <!-- COMMENT: not a toggle, opens comment thread -->
  <button class="reaction-bar__btn reaction-bar__btn--comment" aria-label="Comment">
    <span class="reaction-bar__icon reaction-bar__icon--comment"></span>
    <span class="reaction-bar__count reaction-bar__count--comment"></span>
  </button>

  <!-- REPOST: toggle, shows count -->
  <button class="reaction-bar__btn reaction-bar__btn--repost" aria-pressed="false" aria-label="Repost">
    <span class="reaction-bar__icon reaction-bar__icon--repost"></span>
    <span class="reaction-bar__count reaction-bar__count--repost"></span>
  </button>

  <!-- BOOKMARK: toggle, shows count -->
  <button class="reaction-bar__btn reaction-bar__btn--bookmark" aria-pressed="false" aria-label="Bookmark">
    <span class="reaction-bar__icon reaction-bar__icon--bookmark"></span>
    <span class="reaction-bar__count reaction-bar__count--bookmark"></span>
  </button>

</div>
```

### Wiring

| Element | Read | Write | Property Path |
|---|---|---|---|
| Like - count | `feed.getOrCreate()` | - | `activity.reaction_groups.like.count` |
| Like - active | `feed.getOrCreate()` | - | `activity.own_reactions` (check for `"like"` type) |
| Like - add | - | `client.addActivityReaction({ activity_id, type: "like" })` | Returns `{ reaction }` |
| Like - remove | - | `client.deleteActivityReaction({ activity_id, type: "like" })` | - |
| Comment - count | `feed.getOrCreate()` | - | `activity.reaction_groups.comment.count` or comment count from `activity.latest_comments` |
| Comment - click | - | Opens Comment Thread | No API call - UI only |
| Repost - count | `feed.getOrCreate()` | - | `activity.share_count` |
| Repost - add | - | `feed.addActivity({ type: "post", text, parent_id: activity.id })` | Creates a share/repost; increments `share_count` on parent |
| Repost - remove | - | `client.feeds.deleteActivity({ id: repostActivityId })` | - |
| Bookmark - active | `feed.getOrCreate()` | - | `activity.own_bookmarks` (array, truthy = bookmarked) |
| Bookmark - count | `feed.getOrCreate()` | - | `activity.bookmark_count` |
| Bookmark - add | - | `client.addBookmark({ activity_id })` | - |
| Bookmark - remove | - | `client.deleteBookmark({ activity_id })` | - |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| Reactions | Included in feed response | On - `reaction_groups`, `own_reactions`, `latest_reactions` always present |
| Reaction types | Any string works as a reaction type | `like` common - custom types supported via `client.addActivityReaction({ type: "celebrate" })` |
| Bookmarks | First-class entity in v3 | On - `own_bookmarks` and `bookmark_count` included in activity response |
| Reposts/Shares | Via `parent_id` on `addActivity` | Increments `share_count` on parent; parent accessible via `activity.parent` |
| Reaction notifications | Push notifications available | Off by default - use `skip_push: false` |

---

## Comment Thread

Threaded comments beneath an activity. Comments are first-class entities in v3 (not reactions). Nested replies via `parent_id`.

### Blueprint

```html
<div class="comment-thread">

  <div class="comment-thread__header">
    <span class="comment-thread__count"></span>
    <!-- OPTIONAL: sort (first, last, top, controversial, best) -->
    <button class="comment-thread__sort"></button>
  </div>

  <button class="comment-thread__load-previous">View previous comments</button>

  <div class="comment-thread__list">
    <div class="comment-thread__item">
      <div class="comment">
        <a class="comment__actor" href="/user/{user.id}">
          <img class="comment__avatar" src="" alt="" />
        </a>
        <div class="comment__body">
          <div class="comment__bubble">
            <a class="comment__author" href="/user/{user.id}"></a>
            <p class="comment__text"></p>
          </div>
          <div class="comment__meta">
            <time class="comment__time" datetime=""></time>
            <button class="comment__action comment__action--like">Like</button>
            <button class="comment__action comment__action--reply">Reply</button>
            <!-- CONDITIONAL: comment.user.id === currentUserId -->
            <button class="comment__action comment__action--edit">Edit</button>
            <button class="comment__action comment__action--delete">Delete</button>
          </div>
          <!-- CONDITIONAL: comment.reaction_groups.like exists -->
          <div class="comment__likes" aria-label="3 likes"></div>

          <!-- CONDITIONAL: comment.replies_count > 0 -->
          <div class="comment__replies">
            <button class="comment__replies-toggle">View <span>5</span> replies</button>
            <div class="comment__replies-list">
              <div class="comment-thread__item comment-thread__item--reply">
                <div class="comment">
                  <!-- Same structure, limit nesting to 1-2 levels -->
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="comment-thread__input">
    <img class="comment-thread__input-avatar" src="" alt="" />
    <div class="comment-thread__input-area">
      <div class="comment-thread__input-text" contenteditable="true" role="textbox" aria-label="Write a comment" data-placeholder="Write a comment..."></div>
      <!-- CONDITIONAL: replying to a specific comment -->
      <div class="comment-thread__reply-context">
        Replying to <span class="comment-thread__reply-target"></span>
        <button class="comment-thread__reply-cancel" aria-label="Cancel reply"></button>
      </div>
    </div>
    <button class="comment-thread__submit" aria-label="Post comment" disabled></button>
  </div>

</div>
```

### Wiring

| Element | Read | Write | Property Path |
|---|---|---|---|
| `comment-thread__count` | `feed.getOrCreate()` | - | `activity.reaction_groups.comment.count` or derived from comments array |
| Comment list | `feed.loadNextPageActivityComments(activity, { sort: "best", limit: 10 })` or `client.getComments({ object_type: "activity", object_id, sort, limit })` | - | Returns `{ comments: [...] }` stored in feed state |
| Comment list (paginate) | `feed.loadNextPageActivityComments(activity, { sort, limit })` | - | Cursor-based via feed state |
| Comment - avatar | Included in comment response | - | `comment.user.image` |
| Comment - author | Included in comment response | - | `comment.user.name` |
| Comment - text | Included in comment response | - | `comment.text` (NOT `comment.comment` - asymmetric with the `comment` param used in `addComment`) |
| Comment - time | Included in comment response | - | `comment.created_at` |
| Comment - add | - | `client.addComment({ comment: "text", object_id: activity.id, object_type: "activity" })` | Returns `{ comment: { id, text, user, ... }, duration }` - unwrap with `result.comment` |
| Comment - edit | - | `client.updateComment({ id: comment.id, comment: "new text" })` | Partial update - only specified fields changed |
| Comment - delete | - | `client.deleteComment({ id: comment.id })` | Optional `hard_delete` param |
| Comment like - count | In comment response | - | `comment.reaction_groups.like.count` |
| Comment like - add | - | `client.addCommentReaction({ id: comment.id, type: "like" })` | - |
| Comment like - remove | - | `client.deleteCommentReaction({ id: comment.id, type: "like" })` | - |
| Nested replies - list | `comment.latest_replies` or `client.getComments({ object_type: "comment", object_id: parentId })` | - | `comment.replies_count` for count |
| Nested reply - add | - | `client.addComment({ comment: "text", parent_id: parentComment.id })` | - |
| Load previous | `feed.loadNextPageActivityComments(activity, { sort, limit })` | - | - |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| Comments | First-class entity in v3 | Always available |
| Nested threading | Via `parent_id` on `addComment` | API supports unlimited; cap at 2 levels in UI |
| User enrichment | Automatic in v3 | `comment.user` always enriched with `id`, `name`, `image` |
| @Mentions | `mentioned_user_ids` on `addComment`; returns `mentioned_users` | Always available |
| Comment reactions | `client.addCommentReaction({ id, type })` / `client.deleteCommentReaction(...)` | `comment.reaction_groups` and `comment.own_reactions` included |
| Comment sorting | `sort` param: `first`, `last`, `top`, `controversial`, `best` | `best` recommended - Wilson score balancing |
| Comment notifications | `create_notification_activity: true` on `addComment` | Off by default |

---

## Live Activity Card

Used in livestreaming apps (Video + Feeds). A live activity represents an active stream and appears at the top of the feed, separate from regular posts.

### Blueprint

```html
<!-- CONDITIONAL: activity.type === "live" - render LiveCard instead of standard Activity -->
<div class="live-card">
  <div class="live-card__badge">
    <span class="live-card__dot"></span> <!-- Pulsing red dot via CSS animation -->
    LIVE
  </div>
  <div class="live-card__info">
    <img class="live-card__avatar" src="" alt="" />
    <div class="live-card__meta">
      <span class="live-card__author"></span>
      <span class="live-card__title"></span>
    </div>
  </div>
  <button class="live-card__watch">Watch</button>
</div>
```

### Wiring

| Element | Read | Write | Property Path |
|---|---|---|---|
| Live activities | `feed.getOrCreate()` - filter by `type === "live"` | - | `activity.type === "live"` |
| `live-card__author` | Feed response | - | `activity.user.name` |
| `live-card__title` | Feed response | - | `activity.text` |
| `live-card__watch` | - | Navigate to `/watch/{callId}` | `activity.custom.call_id` |
| Go Live (create) | - | `client.feeds.addActivity({ feeds: ["user:community"], type: "live", text: title, user_id, custom: { call_id } })` | - |
| End Stream (remove) | - | `client.feeds.deleteActivity({ id: liveActivityId })` | - |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| Live activity type | Use `type: "live"` to distinguish from posts | Convention - not enforced by API |
| Custom fields | Store `call_id` in `activity.custom` to link feed activity to video call | - |
| Rendering | FeedList should partition activities: `type === "live"` at top, rest below | Client-side logic |

### API Route

| Route | Method | Params | Action | Response |
|---|---|---|---|---|
| `/api/feed/live` | POST | `{ userId, text, callId }` | `addActivity({ feeds: ["user:community"], type: "live", text, user_id, custom: { call_id: callId } })` | `{ activity }` |
| `/api/feed/live` | DELETE | `{ activityId }` | `client.feeds.deleteActivity({ id: activityId })` | `{ removed: true }` |
