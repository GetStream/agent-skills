# Moderation - component blueprints (end-user actions only)

Setup, routes, and gotchas: [MODERATION.md](MODERATION.md). Rules: [`../RULES.md`](../RULES.md) > Moderation is Dashboard-only.

**This file covers end-user moderation actions only** (report, block, mute, blocked-list). Moderation **review** UI - review queue, flagged-item cards, auto-mod status panels - is deliberately not bundled: review happens exclusively in the [Stream Dashboard](https://beta.dashboard.getstream.io), and the builder must never recreate those blueprints ([`../RULES.md`](../RULES.md) > Moderation is Dashboard-only).

The BEM class names below are a structural spec (elements + conditional states) - implement with Shadcn components and Tailwind utilities; do not ship the BEM classes or hand-written CSS.

---

## Report Modal

End-user dialog for reporting content or users. Triggered from message/activity context menus.

### Blueprint

```html
<dialog class="report-modal">

  <header class="report-modal__header">
    <h3 class="report-modal__title">Report</h3>
    <button class="report-modal__close" aria-label="Close"></button>
  </header>

  <form class="report-modal__form">
    <p class="report-modal__context">
      <!-- Shows what is being reported: message preview, activity preview, or user name -->
    </p>

    <fieldset class="report-modal__reasons">
      <legend class="report-modal__reasons-label">Why are you reporting this?</legend>
      <label class="report-modal__reason">
        <input type="radio" name="reason" value="spam" />
        Spam
      </label>
      <label class="report-modal__reason">
        <input type="radio" name="reason" value="harassment" />
        Harassment
      </label>
      <label class="report-modal__reason">
        <input type="radio" name="reason" value="inappropriate" />
        Inappropriate content
      </label>
      <label class="report-modal__reason">
        <input type="radio" name="reason" value="other" />
        Other
      </label>
    </fieldset>

    <!-- CONDITIONAL: "other" selected -->
    <textarea class="report-modal__details" placeholder="Provide additional details..." rows="3"></textarea>

    <div class="report-modal__actions">
      <button class="report-modal__cancel" type="button">Cancel</button>
      <button class="report-modal__submit" type="submit" disabled>Report</button>
    </div>
  </form>

  <!-- Success state after submission -->
  <div class="report-modal__success">
    <span class="report-modal__success-icon"></span>
    <p class="report-modal__success-text">Thanks for reporting. We'll review this shortly.</p>
    <button class="report-modal__success-close">Done</button>
  </div>

</dialog>
```

### Wiring

| Element | Read | Write | Property Path |
|---|---|---|---|
| Report message (Chat) | - | `client.flagMessage(message.id)` | Flags message for admin review |
| Report user (Chat) | - | `client.flagUser(userId)` | Flags user |
| Report activity (Feeds v3) | - | **Docs-first:** fetch the current Moderation API page before wiring (hand to `stream-docs` on fetch failure) - v3 flagging goes through the Moderation API, not reactions | Never wire this call from memory ([`../RULES.md`](../RULES.md) > Docs-first) |
| Report reason | - | Pass as `reason` param or in custom data | Client-side value from radio selection |
| Report details | - | Include in flag custom data | Optional text from textarea |
| `--submit` enabled | At least one reason selected | - | Client-side validation |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| Chat message flagging | - | Available - `client.flagMessage()` always available |
| Chat user flagging | - | Available - `client.flagUser()` always available |
| Feeds flagging (v3) | Moderation API - fetch the current docs page first | Not reaction-based |
| Flag review | Dashboard -> Moderation dashboard | Available - flags appear in admin dashboard |
| Custom reasons | Client-side | No config - include reason in flag custom data |
| Webhook on flag | Dashboard -> Webhooks -> `message.flagged` / `user.flagged` events | Off - enable to notify external systems |

---

## Block / Mute Controls

End-user controls for blocking and muting other users or channels. Typically surfaced in user profile popovers or channel settings.

### Blueprint

```html
<!-- User-level block/mute (in user profile popover or settings) -->
<div class="user-moderation">
  <button class="user-moderation__btn user-moderation__btn--mute" aria-pressed="false">
    <!-- aria-pressed="true" + --active when user is muted -->
    <span class="user-moderation__icon user-moderation__icon--mute"></span>
    Mute user
  </button>
  <button class="user-moderation__btn user-moderation__btn--block" aria-pressed="false">
    <span class="user-moderation__icon user-moderation__icon--block"></span>
    Block user
  </button>
</div>

<!-- Channel-level mute (in channel settings) -->
<div class="channel-moderation">
  <button class="channel-moderation__btn channel-moderation__btn--mute" aria-pressed="false">
    <span class="channel-moderation__icon channel-moderation__icon--mute"></span>
    Mute channel
    <!-- Muted channels don't trigger notifications; still visible in channel list with --muted modifier -->
  </button>
</div>
```

### Wiring

| Element | Read | Write | Property Path |
|---|---|---|---|
| Mute user (Chat) | `client.mutedUsers` | `client.muteUser(userId)` | `client.mutedUsers[]` - array of `{ target, created_at }` |
| Unmute user (Chat) | `client.mutedUsers` | `client.unmuteUser(userId)` | - |
| Block user (1:1) | - | `client.blockUser(userId)` | Hides DM channels, stops push notifications - for 1:1 blocking between end users |
| Unblock user (1:1) | - | `client.unBlockUser(userId)` | Reverses `blockUser` - restores DM visibility |
| Ban user (channel) | - | `channel.banUser(userId)` | Prevents posting in the channel - different from 1:1 blocking |
| Unban user (channel) | - | `channel.unbanUser(userId)` | - |
| Ban user (global) | - | `client.banUser(userId, { banned_by_id: currentUserId })` | Global ban across all channels |
| Shadow ban (channel) | - | `channel.shadowBan(userId)` | User can post but messages only visible to them |
| Remove shadow ban | - | `client.removeShadowBan(userId)` or `channel.removeShadowBan(userId)` | Reverses shadow ban |
| Mute channel | `client.mutedChannels` | `channel.mute()` | `client.mutedChannels[]` |
| Unmute channel | `client.mutedChannels` | `channel.unmute()` | - |
| Check if muted | `client.mutedUsers.find(m => m.target.id === userId)` | - | Truthy = muted |
| Check channel muted | `channel.muteStatus()` | - | Returns `{ muted, createdAt, expiresAt }` |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| User mute | - | Available - muted user's messages hidden client-side |
| User block (1:1) | - | Available - `client.blockUser()` hides DM channels and stops push |
| User ban (channel) | User must have `'ban-members'` capability | Admins/moderators by default |
| User ban (global) | Server-side only or admin user | Requires server auth |
| Channel mute | - | Available - suppresses notifications, channel still accessible |
| Shadow ban | `channel.shadowBan(userId)` | Available - user can post but messages only visible to them |
| Remove shadow ban | `client.removeShadowBan(userId)` or `channel.removeShadowBan(userId)` | Available - reverses shadow ban |

---

## Blocked Users List

End-user settings page showing users they've blocked or muted, with unblock/unmute actions.

### Blueprint

```html
<div class="blocked-list">

  <header class="blocked-list__header">
    <h3 class="blocked-list__title">Blocked & Muted</h3>
  </header>

  <!-- Tab toggle -->
  <div class="blocked-list__tabs">
    <button class="blocked-list__tab blocked-list__tab--active" data-tab="blocked">Blocked</button>
    <button class="blocked-list__tab" data-tab="muted">Muted</button>
  </div>

  <div class="blocked-list__items">
    <div class="blocked-list__item">
      <img class="blocked-list__item-avatar" src="" alt="" />
      <div class="blocked-list__item-info">
        <span class="blocked-list__item-name"></span>
        <time class="blocked-list__item-since"></time>
        <!-- CONDITIONAL: muted with expiry -->
        <span class="blocked-list__item-expires">Expires in 3 days</span>
      </div>
      <button class="blocked-list__item-action">
        <!-- "Unblock" or "Unmute" depending on active tab -->
      </button>
    </div>
  </div>

  <!-- States: blocked-list__empty ("You haven't blocked anyone") -->

</div>
```

### Wiring

| Element | Read | Write | Property Path |
|---|---|---|---|
| Blocked users | `client.getBlockedUsers()` | - | Returns `{ blocks: [...] }` - the users the current user has blocked. NOT `queryBannedUsers()` - bans are an admin op, blocking is the 1:1 end-user feature |
| Muted users | `client.mutedUsers` | - | Available on `client.connectUser()` response |
| Muted channels | `client.mutedChannels` | - | Available on `client.connectUser()` response |
| `blocked-list__item-since` | Block/mute data | - | `block.created_at` or `mute.created_at` |
| `blocked-list__item-expires` | Mute data | - | `mute.expires` - null if permanent; blocks have no expiry |
| Unblock | - | `client.unBlockUser(userId)` | Reverses `client.blockUser()` |
| Unmute | - | `client.unmuteUser(userId)` | - |

### Requirements

| Feature | Requirement | Default |
|---|---|---|
| List blocked users | `client.getBlockedUsers()` - requires an active `client.connectUser()` connection | Returns `{ blocks }` |
| Muted users list | `client.mutedUsers` | Populated on connect |
| Muted channels list | `client.mutedChannels` | Populated on connect |
