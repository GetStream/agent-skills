# Stream Flutter - docs routing map

Map a request to the exact Flutter docs page, then fetch its `.md`. This table is the curated 80% - the high-frequency intents. For anything not here, fetch the live product index and pick from it:

| Product | Live index (lists every page) |
|---|---|
| Chat - Flutter SDK (`stream_chat_flutter` UI + `stream_chat_flutter_core`) | `https://getstream.io/cli/docs/chat-sdk-flutter.md` |
| Chat - low-level client API reference (`stream_chat`) | `https://getstream.io/cli/docs/chat-flutter-dart.md` |
| Video (`stream_video_flutter`) | `https://getstream.io/cli/docs/video-flutter.md` |
| Feeds (`stream_feeds`) | `https://getstream.io/cli/docs/activity-feeds-flutter.md` |

Chat has **two doc trees**: the Flutter SDK (`.../chat/docs/sdk/flutter/...` - widgets, core controllers, guides) and the low-level client reference (`.../chat/docs/flutter-dart/...` - the full client capability surface: channels, messages, members, permissions). Broad search fallback for the Chat SDK: `https://getstream.io/chat/docs/sdk/flutter/llms-full.txt`.

All page URLs end in `.md` (the Markdown twin - see [`SKILL.md`](SKILL.md)). Fetch at most 3 pages per request. Cite what you used. Do not guess paths - if it is not below, use the index.

---

## Chat

**First decide the layer** (see "pick the UI strategy" in [`SKILL.md`](SKILL.md)):

- Standard-messenger vertical (social, marketplace, workplace, support, DMs) -> **pre-built UI** (`stream_chat_flutter`); reference design -> [`design-matching.md`](design-matching.md).
- Livestream / overlay / bespoke surface -> **custom UI on `stream_chat_flutter_core`** -> run [`custom-ui.md`](custom-ui.md).

**Version:** these docs (and this skill) target **v10**. If the project pins 9.x or earlier, see [`setup.md`](setup.md) "Version prerequisite" and route the upgrade through `https://getstream.io/chat/docs/sdk/flutter/guides/migration-guide-10-0.md`.

### Setup and app shell

| Want to ... | Page (.md) |
|---|---|
| Overview | `https://getstream.io/chat/docs/sdk/flutter.md` |
| Install packages | `https://getstream.io/chat/docs/sdk/flutter/basics/installation.md` |
| Getting started, pre-built UI (+ platform requirements) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/introduction.md` |
| Getting started, core / custom UI | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/introduction.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/setup.md` |
| Client init, connect / disconnect users | `https://getstream.io/chat/docs/flutter-dart/init-and-users.md` |
| Tokens and auth | `https://getstream.io/chat/docs/flutter-dart/tokens-and-authentication.md`, `https://getstream.io/chat/docs/sdk/flutter/guides/token-generation-with-firebase.md` |
| Guest / anonymous users | `https://getstream.io/chat/docs/flutter-dart/authless-users.md` |
| Chat in only part of the widget tree, lazy connect, logout | `https://getstream.io/chat/docs/sdk/flutter/guides/initialize-stream-chat-widget-tree.md` |
| `StreamChatCore` / reconnect recovery | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-chat-core.md` |
| Theming (`StreamTheme`, `StreamColorScheme`, `StreamChatThemeData`) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-chat-and-theming.md` |
| Component factory (`StreamComponentBuilders`, `streamChatComponentBuilders`, `StreamComponentFactory`) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/customizing-widgets.md` |
| Localization | `https://getstream.io/chat/docs/sdk/flutter/guides/localization.md` |
| Logging | `https://getstream.io/chat/docs/sdk/flutter/basics/logging.md` |
| v9 -> v10 migration | `https://getstream.io/chat/docs/sdk/flutter/guides/migration-guide-10-0.md` |

### Channel list and channels

| Want to ... | Page (.md) |
|---|---|
| Channel list widget / item / `itemBuilder` | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/channel-list/stream-channel-list-view.md` |
| Channel list header | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/channel-list/stream-channel-list-header.md` |
| Channel list controller (filter, sort, `doInitialLoad`) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-channel-list-controller.md` |
| Channel list event handling | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-channel-list-event-handler.md` |
| Filter syntax | `https://getstream.io/chat/docs/sdk/flutter/guides/understanding-filters.md` |
| Custom channel list | `https://getstream.io/chat/docs/sdk/flutter/cookbook/custom-channel-list.md` |
| Create channels | `https://getstream.io/chat/docs/sdk/flutter/cookbook/creating-channels.md`, `https://getstream.io/chat/docs/flutter-dart/creating-channels.md` |
| Query channels / pagination | `https://getstream.io/chat/docs/flutter-dart/query-channels.md`, `https://getstream.io/chat/docs/flutter-dart/channel-pagination.md` |
| Archive / pin / mute / hide channels | `https://getstream.io/chat/docs/flutter-dart/archiving-channels.md`, `https://getstream.io/chat/docs/flutter-dart/pinning-channels.md`, `https://getstream.io/chat/docs/flutter-dart/muting-channels.md`, `https://getstream.io/chat/docs/flutter-dart/hiding-channels.md` |
| Add / remove members, query members | `https://getstream.io/chat/docs/flutter-dart/channel-members.md`, `https://getstream.io/chat/docs/flutter-dart/query-members.md` |

### Channel screen and messages

| Want to ... | Page (.md) |
|---|---|
| `StreamChannel` scope | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/channel.md` |
| Channel header | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-channel-header.md` |
| Message list (`config:` / `builders:`, threads) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/stream-message-list-view.md` |
| Message item / custom message UI | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/stream-message-item.md`, `https://getstream.io/chat/docs/sdk/flutter/cookbook/custom-message-list.md` |
| Message actions | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/custom-widgets/customize-message-actions.md` |
| Inline replies | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/inline-replies.md` |
| Thread list / threads API | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-thread-list-view.md`, `https://getstream.io/chat/docs/flutter-dart/threads.md` |
| Typing / read indicators | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/typing-indicators.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/read-indicators.md` |
| Reactions (UI / API) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/reactions.md`, `https://getstream.io/chat/docs/flutter-dart/send-reaction.md` |
| Avatars | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/avatars.md` |
| Custom message list state (core) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/message-list-core.md` |
| Send / edit / delete messages | `https://getstream.io/chat/docs/flutter-dart/send-message.md` |
| Pinned messages | `https://getstream.io/chat/docs/flutter-dart/pinned-messages.md` |
| Unread counts | `https://getstream.io/chat/docs/flutter-dart/unread.md` |
| Delivered / read status | `https://getstream.io/chat/docs/flutter-dart/message-delivery-and-read-status.md` |
| Slow mode | `https://getstream.io/chat/docs/flutter-dart/slow-mode.md` |

### Composer and rich content

| Want to ... | Page (.md) |
|---|---|
| Message composer | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-composer/stream-message-composer.md` |
| Composer controller (core) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-message-composer-controller.md` |
| Attachments / system picker | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-composer/attachments.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-composer/system-attachments-picker.md` |
| File uploads (API) | `https://getstream.io/chat/docs/flutter-dart/file-uploads.md` |
| Mentions / autocomplete triggers | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-composer/mentions.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/custom-widgets/autocomplete-triggers.md` |
| Voice recording | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/stream-voice-recording.md` |
| Polls (UI / API) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/polls.md`, `https://getstream.io/chat/docs/flutter-dart/polls-api.md` |
| Drafts | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/drafts.md` |
| Location sharing | `https://getstream.io/chat/docs/sdk/flutter/guides/location-sharing.md` |
| Extra data on models | `https://getstream.io/chat/docs/sdk/flutter/client/extra-data.md` |

### Users, search and lists

| Want to ... | Page (.md) |
|---|---|
| Member list / grid | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/member-list/stream-member-list-view.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/member-list/stream-member-grid-view.md` |
| User list / grid | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/user-list/stream-user-list-view.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/user-list/stream-user-grid-view.md` |
| User / member controllers | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-user-list-controller.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-member-list-controller.md` |
| Message search (UI / controller / API) | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter/message-list/stream-message-search-list-view.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/stream-message-search-list-controller.md`, `https://getstream.io/chat/docs/flutter-dart/search.md` |
| Paging helpers | `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/paged-value-listenable-builder.md`, `https://getstream.io/chat/docs/sdk/flutter/stream-chat-flutter-core/lazy-load-scroll-view.md` |
| User presence | `https://getstream.io/chat/docs/flutter-dart/presence-format.md` |

### Production

| Want to ... | Page (.md) |
|---|---|
| Push notifications (run [`push.md`](push.md)) | `https://getstream.io/chat/docs/sdk/flutter/guides/push-notifications.md` |
| Offline / local persistence | `https://getstream.io/chat/docs/sdk/flutter/basics/offline-support.md`, `https://getstream.io/chat/docs/flutter-dart/flutter-offline.md` |
| Permissions / channel types | `https://getstream.io/chat/docs/flutter-dart/permissions-reference.md`, `https://getstream.io/chat/docs/flutter-dart/channel-features.md` |
| Moderation | `https://getstream.io/chat/docs/sdk/flutter/guides/moderation.md` |
| Go-live checklist / best practices | `https://getstream.io/chat/docs/sdk/flutter/guides/go-live-checklist.md`, `https://getstream.io/chat/docs/flutter-dart/best-practices.md` |
| Rate limits / query budget | `https://getstream.io/chat/docs/flutter-dart/rate-limits.md`, `https://getstream.io/chat/docs/flutter-dart/api-budget.md` |
| Livestream chat | `https://getstream.io/chat/docs/sdk/flutter/guides/adding-chat-to-video-livestreams.md`, `https://getstream.io/chat/docs/sdk/flutter/guides/livestream-best-practices.md` |
| AI assistants | `https://getstream.io/chat/docs/sdk/flutter/guides/ai-integrations.md`, `https://getstream.io/chat/docs/sdk/flutter/guides/ai-integrations/stream-chat-integration.md`, `https://getstream.io/chat/docs/sdk/flutter/guides/ai-integrations/client-side-tools.md` |
| Custom CDN / E2E encryption / Sentry | `https://getstream.io/chat/docs/sdk/flutter/client/custom-cdn.md`, `https://getstream.io/chat/docs/sdk/flutter/guides/end-to-end-chat-encryption.md`, `https://getstream.io/chat/docs/sdk/flutter/guides/error-reporting-with-sentry.md` |

---

## Video

`stream_video_flutter` covers calls, audio rooms and livestreaming. Read the Video pitfalls in [`RULES.md`](RULES.md) first - several are build-breakers the docs do not mention. Patterns with no docs page (livestream feed pager, floating call over a broadcast, shared call state, Chat + Video glue) are in [`video-patterns.md`](video-patterns.md).

### Setup and calls

| Want to ... | Page (.md) |
|---|---|
| Overview / packages | `https://getstream.io/video/docs/flutter.md` |
| Install packages + platform permissions | `https://getstream.io/video/docs/flutter/basics/installation.md` |
| First call in minutes | `https://getstream.io/video/docs/flutter/basics/quickstart.md` |
| Client init, tokens, guest / anonymous users | `https://getstream.io/video/docs/flutter/guides/client-auth.md` |
| Create / join calls, members, backstage join-ahead | `https://getstream.io/video/docs/flutter/guides/joining-and-creating-calls.md` |
| Read call and participant state | `https://getstream.io/video/docs/flutter/guides/call-and-participant-state.md` |
| Call types and settings | `https://getstream.io/video/docs/flutter/guides/configuring-call-types.md` |
| Camera control | `https://getstream.io/video/docs/flutter/guides/camera-and-microphone/camera.md` |
| Mic, audio output, audio policies | `https://getstream.io/video/docs/flutter/guides/camera-and-microphone/microphone-and-audio.md` |
| Initial camera / mic state on join | `https://getstream.io/video/docs/flutter/guides/camera-and-microphone/initial-call-configuration.md` |
| High-fidelity / music audio | `https://getstream.io/video/docs/flutter/guides/camera-and-microphone/high-fidelity-audio.md` |
| Noise cancellation | `https://getstream.io/video/docs/flutter/guides/noise-cancellation.md` |
| Query calls / members | `https://getstream.io/video/docs/flutter/guides/querying-calls.md`, `https://getstream.io/video/docs/flutter/guides/querying-call-members.md` |
| Roles, permissions, request-to-speak, moderation | `https://getstream.io/video/docs/flutter/guides/permissions-and-moderation.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/permission-requests.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/call-moderation.md` |
| Call events / custom events | `https://getstream.io/video/docs/flutter/guides/call-events.md` |
| Custom call data | `https://getstream.io/video/docs/flutter/advanced/custom-data.md` |
| End-to-end encryption | `https://getstream.io/video/docs/flutter/guides/end-to-end-encryption.md` |
| Participant sorting | `https://getstream.io/video/docs/flutter/guides/sorting-api.md` |
| Closed captions / transcription | `https://getstream.io/video/docs/flutter/guides/closed-captions.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/transcriptions.md` |
| Reactions | `https://getstream.io/video/docs/flutter/guides/reactions.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/reactions.md` |

### Call UI

| Want to ... | Page (.md) |
|---|---|
| Pre-built call screen | `https://getstream.io/video/docs/flutter/call-container.md`, `https://getstream.io/video/docs/flutter/call-content.md`, `https://getstream.io/video/docs/flutter/ui-components-overview.md` |
| Render a participant's video | `https://getstream.io/video/docs/flutter/video-render.md` |
| Participant layouts / tiles / list | `https://getstream.io/video/docs/flutter/call-participants.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/participant-label.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/participant-list.md` |
| Custom call controls | `https://getstream.io/video/docs/flutter/ui-cookbook/replacing-call-controls.md` |
| Pre-join lobby | `https://getstream.io/video/docs/flutter/ui-cookbook/call-lobby.md` |
| Theming | `https://getstream.io/video/docs/flutter/video-theme.md` |
| Picture-in-picture | `https://getstream.io/video/docs/flutter/advanced/picture-in-picture.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/in-app-picture-in-picture.md` |
| Screen sharing | `https://getstream.io/video/docs/flutter/guides/screensharing.md` |

### Livestream, audio rooms, combined products

| Want to ... | Page (.md) |
|---|---|
| Livestream: guide / host / watch | `https://getstream.io/video/docs/flutter/guides/livestreaming.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/hosting-a-livestream.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/watching-a-livestream.md` |
| HLS / RTMP broadcasting | `https://getstream.io/video/docs/flutter/advanced/broadcasting.md` |
| Recording | `https://getstream.io/video/docs/flutter/advanced/recording.md` |
| Audio rooms (+ chat) | `https://getstream.io/video/docs/flutter/ui-cookbook/audio-room-with-chat.md` |
| Chat app with video calls | `https://getstream.io/video/docs/flutter/ui-cookbook/chat-with-video.md` |
| Multiple simultaneous calls | `https://getstream.io/video/docs/flutter/advanced/multiple-simultaneous-calls-support.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/multicall.md` |

### Ringing and push (run [`push.md`](push.md))

| Want to ... | Page (.md) |
|---|---|
| Ringing overview (outgoing, `ring()`, auto-drop) | `https://getstream.io/video/docs/flutter/advanced/incoming-calls/overview.md`, `https://getstream.io/video/docs/flutter/advanced/incoming-calls/ringing.md` |
| Push providers + push manager config | `https://getstream.io/video/docs/flutter/advanced/incoming-calls/providers-configuration.md` |
| Regular push, missed calls, device registration | `https://getstream.io/video/docs/flutter/advanced/incoming-calls/push-notifications.md` |
| iOS CallKit / VoIP | `https://getstream.io/video/docs/flutter/advanced/incoming-calls/callkit-integration.md` |
| Android FCM ringing + Telecom | `https://getstream.io/video/docs/flutter/advanced/incoming-calls/android-firebase-integration.md` |
| Incoming / outgoing call UI and customization | `https://getstream.io/video/docs/flutter/ui-cookbook/incoming-call.md`, `https://getstream.io/video/docs/flutter/outgoing-call.md`, `https://getstream.io/video/docs/flutter/advanced/incoming-calls/customization.md` |

### Production

| Want to ... | Page (.md) |
|---|---|
| Video filters / compositing | `https://getstream.io/video/docs/flutter/advanced/apply-video-filters.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/video-compositing.md` |
| Background behavior / audio interruptions | `https://getstream.io/video/docs/flutter/advanced/background-modes.md`, `https://getstream.io/video/docs/flutter/advanced/handling-system-audio-interruptions.md` |
| Per-call preferences (timeouts, ringing drop) | `https://getstream.io/video/docs/flutter/advanced/call-preferences.md` |
| Session timers / call duration | `https://getstream.io/video/docs/flutter/ui-cookbook/session-timers.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/call-duration.md` |
| Network drops / low bandwidth / quality | `https://getstream.io/video/docs/flutter/ui-cookbook/network-disruption.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/low-bandwidth.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/manual-video-quality-selection.md`, `https://getstream.io/video/docs/flutter/ui-cookbook/network-quality-indicator.md` |
| Call rating / stats | `https://getstream.io/video/docs/flutter/ui-cookbook/call-quality-rating.md`, `https://getstream.io/video/docs/flutter/guides/call-statistics.md` |
| Deep links (join via link) | `https://getstream.io/video/docs/flutter/advanced/deeplinking.md` |
| Troubleshooting | `https://getstream.io/video/docs/flutter/advanced/troubleshooting.md` |
| Upgrade from v0.x | `https://getstream.io/video/docs/flutter/migration-guides/1.0.0.md` |

---

## Feeds

`stream_feeds` (v3, plural) has **no pre-built UI**: the SDK gives you state objects, and you build the widgets (Twitter-style by default - see [`RULES.md`](RULES.md) "Feeds"). The deprecated `stream_feed` / `stream_feed_flutter_core` packages are a different API - never route to their docs.

Start with: quick start `https://getstream.io/activity-feeds/docs/flutter.md`, install `https://getstream.io/activity-feeds/docs/flutter/installation.md`, state layer `https://getstream.io/activity-feeds/docs/flutter/state.md`, errors / `Result<T>` `https://getstream.io/activity-feeds/docs/flutter/error-handling.md`.

| Want to ... | Page (.md) |
|---|---|
| Built-in feed groups (user / timeline / notification / foryou / stories), get-or-create a feed | `https://getstream.io/activity-feeds/docs/flutter/feeds.md` |
| Post / update / partial-update / delete activities | `https://getstream.io/activity-feeds/docs/flutter/activities.md` |
| Query activities across feeds | `https://getstream.io/activity-feeds/docs/flutter/query-activities.md` |
| Watch state in widgets (`StateNotifierBuilder`, `queryMore*`, dispose) | `https://getstream.io/activity-feeds/docs/flutter/state.md` |
| Real-time events | `https://getstream.io/activity-feeds/docs/flutter/events.md` |
| Likes / reactions | `https://getstream.io/activity-feeds/docs/flutter/reactions.md` |
| Comments (threaded) | `https://getstream.io/activity-feeds/docs/flutter/comments.md` |
| Bookmarks | `https://getstream.io/activity-feeds/docs/flutter/bookmarks.md` |
| Follow / unfollow, batch follows | `https://getstream.io/activity-feeds/docs/flutter/follows.md` |
| Notification feed (bell, seen / read) | `https://getstream.io/activity-feeds/docs/flutter/notification-feeds.md` |
| Stories | `https://getstream.io/activity-feeds/docs/flutter/stories.md` |
| Image / file uploads in a post | `https://getstream.io/activity-feeds/docs/flutter/file-uploads.md` |
| @mentions / URL previews | `https://getstream.io/activity-feeds/docs/flutter/user-mentions.md`, `https://getstream.io/activity-feeds/docs/flutter/url-previews.md` |
| Pins / polls | `https://getstream.io/activity-feeds/docs/flutter/pins.md`, `https://getstream.io/activity-feeds/docs/flutter/polls.md` |
| Feed members / visibility | `https://getstream.io/activity-feeds/docs/flutter/feed-members.md`, `https://getstream.io/activity-feeds/docs/flutter/feed-and-activity-visibility.md` |
| Search feeds | `https://getstream.io/activity-feeds/docs/flutter/search-for-feeds.md` |
| Aggregation / activity selectors (for-you) | `https://getstream.io/activity-feeds/docs/flutter/aggregation.md`, `https://getstream.io/activity-feeds/docs/flutter/activity-selectors.md` |
| Moderation | `https://getstream.io/activity-feeds/docs/flutter/moderation.md` |
| Push notifications | `https://getstream.io/activity-feeds/docs/flutter/push-notifications.md` |
| Best practices, performance, rate limits | `https://getstream.io/activity-feeds/docs/flutter/best-practices.md`, `https://getstream.io/activity-feeds/docs/flutter/performance.md`, `https://getstream.io/activity-feeds/docs/flutter/rate-limits.md` |
| Version changes | `https://getstream.io/activity-feeds/docs/flutter/roadmap-and-changelog.md` |

---

## Combined Chat + Video

Read the Chat + Video glue in [`video-patterns.md`](video-patterns.md) (aliased imports, one token, call id derived from the channel). Then route per product above. The integration narratives:

- Video side (chat in a call app): `https://getstream.io/video/docs/flutter/ui-cookbook/chat-with-video.md`
- Chat side (chat next to a livestream): `https://getstream.io/chat/docs/sdk/flutter/guides/adding-chat-to-video-livestreams.md`

---

## When the docs fall short: source code + example apps

For a specific customization or behavior the docs do not cover - an exact component-builder slot, a theme property, a default widget's `build()`, an undocumented option, or how a flow is really wired - read the **SDK source** and the **example apps**. The source is the final source of truth.

| SDK | Repo (github.com/GetStream/...) | Packages | Example apps |
|---|---|---|---|
| Chat | `stream-chat-flutter` | `packages/stream_chat`, `stream_chat_flutter_core`, `stream_chat_flutter`, `stream_chat_persistence`, `stream_chat_localizations` | `sample_app/`, each package's `example/` |
| Chat theming + base components | `stream-core-flutter` | `stream_core_flutter` (`StreamTheme`, `StreamComponentBuilders`, `StreamColorScheme`) | - |
| Video | `stream-video-flutter` | `packages/stream_video`, `stream_video_flutter`, `stream_video_push_notification`, `stream_video_filters` | `dogfooding/`, `packages/*/example/` |
| Feeds | `stream-feeds-flutter` | `packages/stream_feeds` | `sample_app/` |

How to search (prefer the version-accurate local checkout - no network, matches what the project compiles):

1. **Local pub cache** - the exact source for the project's pinned version:

   ```bash
   # The resolved versions:
   grep -A1 -E '^  (stream_[a-z_]+):' pubspec.lock | grep -E 'stream_|version'
   # The matching source (several versions can coexist - pick the one pubspec.lock names):
   ls -d ~/.pub-cache/hosted/pub.dev/stream_* 2>/dev/null
   grep -rn "class StreamMessageListView" ~/.pub-cache/hosted/pub.dev/stream_chat_flutter-<version>/lib
   ```

   A symbol can live in any package in the re-export chain (`stream_chat_flutter` -> `stream_chat_flutter_core` -> `stream_chat`, plus `stream_core_flutter`). Grep the whole resolved set before concluding an API is missing - see [`RULES.md`](RULES.md) "Never declare an API missing without evidence".

2. **GitHub** - for the example apps (not in the pub cache) and when no local checkout exists. Read raw files from `raw.githubusercontent.com/GetStream/<repo>/<tag>/...`, using the tag that matches `pubspec.lock`.

Do not present source-derived APIs as if documented - say where you found them.
