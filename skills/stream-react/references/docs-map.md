# Stream React (web) - docs routing map

Map a request to the exact React docs page, then fetch its `.md`. **Best practices live in the live docs, not in training data** - Stream's React SDKs evolve quickly, so the component-reference, cookbook, and advanced-guide pages are the authority for the current API and recommended pattern. The trigger tables below are the curated 80% (the high-frequency intents); **for anything not listed, fetch the live index and pick from it - never guess a path.**

This skill is **prebuilt-component-first** ([`../RULES.md`](../RULES.md) > Reference authority): build the common path with the SDK's prebuilt components and customize via the documented hooks/props on the pages below. For fully bespoke UI on the low-level client, see [`custom-ui.md`](custom-ui.md).

---

## The docs convention (the core mechanism)

Every Stream docs page has a Markdown twin a coding agent can read directly: **take the page URL, drop the trailing `/`, add `.md`.**

```
https://getstream.io/chat/docs/sdk/react/components/core-components/channel/   ->   https://getstream.io/chat/docs/sdk/react/components/core-components/channel.md
```

Always fetch the `.md` variant - it is clean Markdown with verbatim code, no page chrome.

Each product has a **live index** that lists every page with its `.md` URL. Fetch the index to discover or confirm a page whenever a request does not match a trigger row below:

| Product | Live index (always current) | Page URL shape |
|---|---|---|
| Chat React (SDK: UI components + hooks) | `https://getstream.io/cli/docs/chat-sdk-react.md` | `https://getstream.io/chat/docs/sdk/react/...md` |
| Chat React (low-level client / API reference) | `https://getstream.io/cli/docs/chat-react.md` | `https://getstream.io/chat/docs/react/...md` |
| Video React | `https://getstream.io/cli/docs/video-react.md` | `https://getstream.io/video/docs/react/...md` |
| Feeds React | `https://getstream.io/cli/docs/activity-feeds-react.md` | `https://getstream.io/activity-feeds/docs/react/...md` |

(The same manifests are also published as `llms.txt` in list form: Chat SDK `.../chat/docs/sdk/react/llms.txt`, Chat API `.../chat/docs/react/llms.txt`, Video `.../video/docs/react/llms.txt`, Feeds `.../activity-feeds/docs/react/llms.txt`.)

**URL grounding (non-negotiable).** Only fetch a page URL you got from a trigger row below or from a live index fetch *in this conversation*. **Do not construct a doc path from memory or from a pattern** - many look guessable but are wrong (e.g. the Feeds React quick start is `https://getstream.io/activity-feeds/docs/react.md`, **not** `.../docs/react/quick-start.md`, which 404s). If a page is not in a table below, fetch the product index and pick the real URL from it; on fetch failure, escalate to the `stream-docs` skill, then stop and ask - never build from memory.

**Version note.** The Chat React index is versioned (v14 latest, then v13, ...). When a project pins a specific major (check `package.json`), route to that version's pages - this matters most for Track M migrations ([`../migrate.md`](../migrate.md)).

## Docs-first protocol

1. **Match** the user's request against a trigger row below (Chat / Video / Feeds; component, cookbook, or advanced guide), or against the relevant index when it does not match a row.
2. **Fetch before coding** - `WebFetch` the page's `.md` URL (every row links the raw markdown). Read it this turn.
3. **Implement to match** the fetched guidance - do not write the feature from memory or from the bundled blueprints alone. The blueprints in `*-blueprints.md` cover the prebuilt common path; these pages cover the customization/advanced path and override memory.
4. **On fetch failure** - hand the lookup to the `stream-docs` skill (live docs with citations) before coding. If neither the page nor `stream-docs` resolves it, **stop and ask the user** - do not implement from memory. Never guess the API.

This protocol is a non-negotiable rule - see [`../RULES.md`](../RULES.md) > Docs-first for cookbook / advanced features. It also governs **migration** (Track M) - fetch the release/upgrade guide before applying an upgrade ([`../migrate.md`](../migrate.md)).

---

## Chat React - prebuilt components (build the common path with these)

| Trigger keywords | Component | Fetch first |
|---|---|---|
| chat root, provider, client setup, useCreateChatClient | Chat | https://getstream.io/chat/docs/sdk/react/components/core-components/chat.md |
| channel list, channel sidebar, list of channels | ChannelList | https://getstream.io/chat/docs/sdk/react/components/core-components/channel-list.md |
| channel, active channel, channel provider | Channel | https://getstream.io/chat/docs/sdk/react/components/core-components/channel.md |
| message list | MessageList | https://getstream.io/chat/docs/sdk/react/components/core-components/message-list.md |
| virtualized list, large channel, high volume messages | VirtualizedMessageList | https://getstream.io/chat/docs/sdk/react/components/core-components/virtualized-list.md |
| message composer, message input, send box (v14: MessageComposer, not MessageInput) | MessageComposer | https://getstream.io/chat/docs/sdk/react/components/message-composer/message-composer.md |
| thread, replies panel | Thread | https://getstream.io/chat/docs/sdk/react/components/core-components/thread.md |
| message component, message UI | Message | https://getstream.io/chat/docs/sdk/react/components/message-components/message.md |
| window, main panel layout | Window | https://getstream.io/chat/docs/sdk/react/components/utility-components/window.md |
| channel state context, read channel state in a custom component | ChannelStateContext | https://getstream.io/chat/docs/sdk/react/components/contexts/channel-state-context.md |
| message context, read message state in a custom component | MessageContext | https://getstream.io/chat/docs/sdk/react/components/contexts/message-context.md |

## Chat React - feature components (beyond the common path)

First-class prebuilt features the common-path blueprints don't cover. Most need a Dashboard/channel-type toggle (e.g. `polls`) - fetch the page before building.

| Trigger keywords (in the user's request) | Topic | Fetch first |
|---|---|---|
| poll, create poll, vote, poll message | Poll | https://getstream.io/chat/docs/sdk/react/components/message-components/poll.md |
| voice message, record audio, audio recorder, record voice in composer | Audio Recorder (composer) | https://getstream.io/chat/docs/sdk/react/components/message-composer/audio-recorder.md |
| voice recording attachment, play voice message, waveform | Voice Recording Attachment | https://getstream.io/chat/docs/sdk/react/components/message-components/attachment/voice-recording.md |
| chat view, channel + thread switcher, ChatView.Selector/.Channels/.Threads | ChatView | https://getstream.io/chat/docs/sdk/react/components/utility-components/chat-view.md |
| thread list, threads manager, unread threads, ThreadList/ThreadListItem | ThreadList | https://getstream.io/chat/docs/sdk/react/components/core-components/thread-list.md |
| message bounce, review bounced message, moderation prompt on own message | MessageBounceContext | https://getstream.io/chat/docs/sdk/react/components/contexts/message-bounce-context.md |

## Chat React - UI Cookbook (customization + theming recipes)

> **Writing your OWN component for one of these regions** (custom message row, composer, channel preview/header) instead of passing props/theme? **Load [`custom-ui.md`](custom-ui.md) first** - its completion contract lists every sub-feature you must reproduce or mark `N/A` (attachments, reactions, quoted replies, receipts, threads, edited/deleted, grouping) - **then** fetch the page below for the current API. Just passing props/theme to the prebuilt component? Fetch the page and skip the contract.

| Trigger keywords (in the user's request) | Topic | Fetch first |
|---|---|---|
| typing indicator, "user is typing", typing dots | Typing Indicator | https://getstream.io/chat/docs/sdk/react/guides/customization/typing-indicator.md |
| customize message UI, custom message component, message rendering, renderText | Message UI | https://getstream.io/chat/docs/sdk/react/guides/theming/message-ui.md |
| message actions, message context menu, custom action, message hover menu | Message Actions | https://getstream.io/chat/docs/sdk/react/guides/theming/actions/message-actions.md |
| reactions, custom reactions, emoji reaction set, reaction selector | Reactions Customization | https://getstream.io/chat/docs/sdk/react/guides/theming/reactions.md |
| message composer UI, input UI, custom composer, message input styling | Message Composer UI | https://getstream.io/chat/docs/sdk/react/guides/theming/input-ui.md |
| channel header, custom channel header | Channel Header | https://getstream.io/chat/docs/sdk/react/guides/customization/channel-header.md |
| channel list UI, channel preview, channel list item, custom preview | Channel List UI | https://getstream.io/chat/docs/sdk/react/guides/customization/channel-list-preview.md |
| emoji picker, custom emoji picker | Emoji Picker | https://getstream.io/chat/docs/sdk/react/guides/customization/emoji-picker.md |
| autocomplete, suggestion list, command autocomplete, mention suggestions | Autocomplete Suggestions | https://getstream.io/chat/docs/sdk/react/guides/customization/suggestion-list.md |
| link preview, URL preview, OG preview in composer | Link Previews in Message Composer | https://getstream.io/chat/docs/sdk/react/guides/customization/link-previews.md |
| pin indicator, pinned message badge | Pin Indicator | https://getstream.io/chat/docs/sdk/react/guides/customization/pin-indicator.md |
| thread header, customize thread header | Thread Header | https://getstream.io/chat/docs/sdk/react/guides/customization/thread-header.md |
| search menu, app menu | Search Menu | https://getstream.io/chat/docs/sdk/react/guides/customization/app-menu.md |
| search customization, customize channel search | Search Customization | https://getstream.io/chat/docs/sdk/react/guides/customization/channel-search.md |
| collapsible sidebar, collapse sidebar | Collapsible Sidebar | https://getstream.io/chat/docs/sdk/react/guides/customization/collapsible-sidebar.md |
| system message, custom system message | System Message | https://getstream.io/chat/docs/sdk/react/guides/customization/system-message.md |
| system notification banner, connection banner | System notification banner | https://getstream.io/chat/docs/sdk/react/guides/customization/system-notification-banner.md |
| mentions actions, @mention click, mention handler | Mentions Actions | https://getstream.io/chat/docs/sdk/react/guides/theming/actions/mentions-actions.md |
| attachment actions, custom attachment action | Attachment Actions | https://getstream.io/chat/docs/sdk/react/guides/theming/actions/attachment-actions.md |
| hide channel history, hide history for new members | Hide Channel History For Newly Added Members | https://getstream.io/chat/docs/sdk/react/guides/customization/hide-channel-history-for-new-members.md |
| localization, i18n, translations, language, locale | Localization | https://getstream.io/chat/docs/sdk/react/guides/theming/translations.md |

## Chat React - Advanced Guides

| Trigger keywords (in the user's request) | Topic | Fetch first |
|---|---|---|
| AI assistant, AI chat, streaming AI response, typewriter effect, AI bot | AI Integrations | https://getstream.io/chat/docs/sdk/react/guides/ai-integrations.md |
| LangChain | Stream Chat LangChain SDK | https://getstream.io/chat/docs/sdk/react/guides/ai-integrations/stream-chat-langchain-sdk.md |
| AI SDK (Vercel), Stream Chat AI SDK | Stream Chat AI SDK | https://getstream.io/chat/docs/sdk/react/guides/ai-integrations/stream-chat-ai-sdk.md |
| advanced search, message search, search filters | Advanced Search | https://getstream.io/chat/docs/sdk/react/guides/advanced-search.md |
| multiple channel lists, multiple lists, several channel lists | Multiple Lists | https://getstream.io/chat/docs/sdk/react/guides/multiple-channel-lists.md |
| channel list infinite scroll, paginate channels, load more channels | Infinite Scroll | https://getstream.io/chat/docs/sdk/react/guides/channel-list-infinite-scroll.md |
| read state, read receipts, unread count, mark read | Channel Read State | https://getstream.io/chat/docs/sdk/react/guides/channel-read-state.md |
| online status, presence, member list, who is online | Channel Members and Online Status | https://getstream.io/chat/docs/sdk/react/guides/channel-user-lists.md |
| location sharing, share location, live location | Location Sharing | https://getstream.io/chat/docs/sdk/react/guides/location-sharing.md |
| blocking users, block user, unblock | Blocking Users | https://getstream.io/chat/docs/sdk/react/guides/blocking-users.md |
| message reminders, remind me, saved for later | Message Reminders | https://getstream.io/chat/docs/sdk/react/guides/message-reminders.md |
| notifications, web push, push notifications, browser notifications | Notifications | https://getstream.io/chat/docs/sdk/react/guides/notifications.md |
| attachment previews, composer attachment preview | Attachment Previews in Message Composer | https://getstream.io/chat/docs/sdk/react/guides/message-composer/attachment-previews.md |
| audio playback, voice message playback, play audio attachment | Audio Playback | https://getstream.io/chat/docs/sdk/react/guides/audio-playback.md |
| date formatting, time formatting, timestamp format, dayjs | Date and time formatting | https://getstream.io/chat/docs/sdk/react/guides/date-time-formatting.md |
| state management, state store, useStateStore, subscribe to state | SDK State Management | https://getstream.io/chat/docs/sdk/react/guides/sdk-state-management.md |
| dialog management, dialogs, modal management | Dialog Management | https://getstream.io/chat/docs/sdk/react/guides/dialog-management.md |
| custom data types, custom fields, TypeScript generics, typing custom data | TypeScript & Custom Data Types | https://getstream.io/chat/docs/sdk/react/guides/typescript-and-custom-data-types.md |
| chat plus video, call from chat, video in chat, audio call in chat | Video & Audio by Stream | https://getstream.io/chat/docs/sdk/react/guides/video-integration/video-integration-stream.md |
| upgrade to v14, migrate chat react, v13 to v14, breaking changes | Upgrade to v14 | https://getstream.io/chat/docs/sdk/react/release-guides/upgrade-to-v14.md |

---

## Video React - prebuilt components (build the common path with these)

| Trigger keywords | Component | Fetch first |
|---|---|---|
| video root provider, StreamVideo, video client setup | StreamVideo | https://getstream.io/video/docs/react/ui-components/core/stream-video.md |
| StreamCall, call provider | StreamCall | https://getstream.io/video/docs/react/ui-components/core/stream-call.md |
| call layout, SpeakerLayout, PaginatedGridLayout, LivestreamLayout, grid/speaker view | Call layout | https://getstream.io/video/docs/react/ui-components/core/call-layout.md |
| participant tile, ParticipantView, render one participant | ParticipantView | https://getstream.io/video/docs/react/ui-components/core/participant-view.md |
| call controls, mic/camera/screenshare buttons, leave button | Call Control Actions | https://getstream.io/video/docs/react/ui-components/call/call-controls.md |
| device settings, camera/mic/speaker selector | Device settings | https://getstream.io/video/docs/react/ui-components/participants/device-settings.md |
| video preview, lobby self-view | Video preview | https://getstream.io/video/docs/react/ui-components/participants/video-preview.md |

## Video React - UI Cookbook (customization recipes)

> **Writing your OWN call layout/controls component** instead of passing props? **Load [`custom-ui.md`](custom-ui.md) first** (completion contract: each participant via `ParticipantView`, screenshare, dominant-speaker, join/leave, device state), **then** fetch the page below. Passing props to a prebuilt component? Fetch the page.

| Trigger keywords (in the user's request) | Topic | Fetch first |
|---|---|---|
| replace call controls, custom control bar, custom buttons | Replacing Call Controls | https://getstream.io/video/docs/react/ui-cookbook/replacing-call-controls.md |
| lobby, pre-join screen, preview before joining | Lobby Preview | https://getstream.io/video/docs/react/ui-cookbook/lobby-preview.md |
| picture in picture, PiP, pop-out video | Picture-in-Picture | https://getstream.io/video/docs/react/ui-cookbook/picture-in-picture.md |
| network quality, connection indicator, signal bars | Network Quality Indicator | https://getstream.io/video/docs/react/ui-cookbook/network-quality-indicator.md |
| watch livestream, viewer, HLS player, LivestreamPlayer | Watching a livestream | https://getstream.io/video/docs/react/ui-cookbook/watching-a-livestream.md |
| ringing, incoming call, accept/reject call | Ringing Call | https://getstream.io/video/docs/react/ui-cookbook/ringing-call.md |

> Custom call layouts, runtime layout switching, transcriptions, closed captions, audio rooms, and more cookbook recipes are not listed above - fetch the Video React index (top of this file) and look for `ui-cookbook/<slug>.md` before implementing.

## Video React - Advanced Guides

| Trigger keywords (in the user's request) | Topic | Fetch first |
|---|---|---|
| best practices, production readiness, audit (Track F anchor) | Integration Best Practices | https://getstream.io/video/docs/react/advanced/integration-best-practices.md |
| chat with video, chat alongside call, call + chat | Chat Integration | https://getstream.io/video/docs/react/advanced/chat-with-video.md |
| recording, record call, start/stop recording | Recording | https://getstream.io/video/docs/react/advanced/recording.md |
| broadcasting, HLS/RTMP egress, restream to YouTube/Twitch | Broadcasting (HLS/RTMP egress only - NOT the WebRTC host flow) | https://getstream.io/video/docs/react/advanced/broadcasting.md |
| video filters, background blur, audio filters | Video & Audio filters | https://getstream.io/video/docs/react/advanced/apply-video-filters.md |

---

## Feeds React (v3) - headless; build from hooks

Feeds has **no prebuilt UI components** - always build from its hooks (`useFeedActivities`, `useActivityComments`, ...) per [`FEEDS-blueprints.md`](FEEDS-blueprints.md). Fetch the page first for the current hook/method API.

| Trigger keywords (in the user's request) | Topic | Fetch first |
|---|---|---|
| feeds setup, install, client, useCreateFeedsClient, quick start | Quick Start | https://getstream.io/activity-feeds/docs/react.md |
| installation, packages | Installation | https://getstream.io/activity-feeds/docs/react/installation.md |
| post, activity, addActivity, create post | Activities | https://getstream.io/activity-feeds/docs/react/activities.md |
| read a feed, timeline, useFeedActivities, getOrCreate, pagination | Feeds | https://getstream.io/activity-feeds/docs/react/feeds.md |
| comments, useActivityComments, addComment, reply | Comments | https://getstream.io/activity-feeds/docs/react/comments.md |
| reactions, like, addActivityReaction | Reactions | https://getstream.io/activity-feeds/docs/react/reactions.md |
| bookmarks, save post, addBookmark | Bookmarks | https://getstream.io/activity-feeds/docs/react/bookmarks.md |
| follow, unfollow, timeline feed follow | Follow and Unfollow | https://getstream.io/activity-feeds/docs/react/follows.md |
| notification feed, aggregated, useAggregatedActivities, useNotificationStatus | Notification Feeds | https://getstream.io/activity-feeds/docs/react/notification-feeds.md |
| polls, vote, poll activity | Polls | https://getstream.io/activity-feeds/docs/react/polls.md |
| mentions, @mention, user mentions in posts | User Mentions | https://getstream.io/activity-feeds/docs/react/user-mentions.md |
| url preview, link preview, OG enrichment | URL Previews | https://getstream.io/activity-feeds/docs/react/url-previews.md |
| for you feed, algorithmic feed, personalized | For You Feed | https://getstream.io/activity-feeds/docs/react/for-you-feed.md |
| ranking, custom ranking, sort activities | Ranking | https://getstream.io/activity-feeds/docs/react/custom-ranking.md |

> When a request names a feature not in the tables above, fetch the matching product index (top of this file) and find the page before implementing.
