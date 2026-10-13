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

Abbreviations used in the tables below (expand them before fetching):

- `CS/` = `https://getstream.io/chat/docs/sdk/flutter/`
- `CD/` = `https://getstream.io/chat/docs/flutter-dart/`
- `V/` = `https://getstream.io/video/docs/flutter/`
- `F/` = `https://getstream.io/activity-feeds/docs/flutter/`

---

## Chat

**First decide the layer** (see "pick the UI strategy" in [`SKILL.md`](SKILL.md)):

- Standard-messenger vertical (social, marketplace, workplace, support, DMs) -> **pre-built UI** (`stream_chat_flutter`); reference design -> [`design-matching.md`](design-matching.md).
- Livestream / overlay / bespoke surface -> **custom UI on `stream_chat_flutter_core`** -> run [`custom-ui.md`](custom-ui.md).

**Version:** these docs (and this skill) target **v10**. If the project pins 9.x or earlier, see [`setup.md`](setup.md) "Version prerequisite" and route the upgrade through `CS/guides/migration-guide-10-0.md`.

### Setup and app shell

| Want to ... | Page (.md) |
|---|---|
| Overview | `https://getstream.io/chat/docs/sdk/flutter.md` |
| Install packages | `CS/basics/installation.md` |
| Getting started, pre-built UI (+ platform requirements) | `CS/stream-chat-flutter/introduction.md` |
| Getting started, core / custom UI | `CS/stream-chat-flutter-core/introduction.md`, `CS/stream-chat-flutter-core/setup.md` |
| Client init, connect / disconnect users | `CD/init-and-users.md` |
| Tokens and auth | `CD/tokens-and-authentication.md`, `CS/guides/token-generation-with-firebase.md` |
| Guest / anonymous users | `CD/authless-users.md` |
| Chat in only part of the widget tree, lazy connect, logout | `CS/guides/initialize-stream-chat-widget-tree.md` |
| `StreamChatCore` / reconnect recovery | `CS/stream-chat-flutter-core/stream-chat-core.md` |
| Theming (`StreamTheme`, `StreamColorScheme`, `StreamChatThemeData`) | `CS/stream-chat-flutter/stream-chat-and-theming.md` |
| Component factory (`StreamComponentBuilders`, `streamChatComponentBuilders`, `StreamComponentFactory`) | `CS/stream-chat-flutter/customizing-widgets.md` |
| Localization | `CS/guides/localization.md` |
| Logging | `CS/basics/logging.md` |
| v9 -> v10 migration | `CS/guides/migration-guide-10-0.md` |

### Channel list and channels

| Want to ... | Page (.md) |
|---|---|
| Channel list widget / item / `itemBuilder` | `CS/stream-chat-flutter/channel-list/stream-channel-list-view.md` |
| Channel list header | `CS/stream-chat-flutter/channel-list/stream-channel-list-header.md` |
| Channel list controller (filter, sort, `doInitialLoad`) | `CS/stream-chat-flutter-core/stream-channel-list-controller.md` |
| Channel list event handling | `CS/stream-chat-flutter-core/stream-channel-list-event-handler.md` |
| Filter syntax | `CS/guides/understanding-filters.md` |
| Custom channel list | `CS/cookbook/custom-channel-list.md` |
| Create channels | `CS/cookbook/creating-channels.md`, `CD/creating-channels.md` |
| Query channels / pagination | `CD/query-channels.md`, `CD/channel-pagination.md` |
| Archive / pin / mute / hide channels | `CD/archiving-channels.md`, `CD/pinning-channels.md`, `CD/muting-channels.md`, `CD/hiding-channels.md` |
| Add / remove members, query members | `CD/channel-members.md`, `CD/query-members.md` |

### Channel screen and messages

| Want to ... | Page (.md) |
|---|---|
| `StreamChannel` scope | `CS/stream-chat-flutter/channel.md` |
| Channel header | `CS/stream-chat-flutter/stream-channel-header.md` |
| Message list (`config:` / `builders:`, threads) | `CS/stream-chat-flutter/message-list/stream-message-list-view.md` |
| Message item / custom message UI | `CS/stream-chat-flutter/message-list/stream-message-item.md`, `CS/cookbook/custom-message-list.md` |
| Message actions | `CS/stream-chat-flutter/custom-widgets/customize-message-actions.md` |
| Inline replies | `CS/stream-chat-flutter/message-list/inline-replies.md` |
| Thread list / threads API | `CS/stream-chat-flutter/stream-thread-list-view.md`, `CD/threads.md` |
| Typing / read indicators | `CS/stream-chat-flutter/message-list/typing-indicators.md`, `CS/stream-chat-flutter/message-list/read-indicators.md` |
| Reactions (UI / API) | `CS/stream-chat-flutter/reactions.md`, `CD/send-reaction.md` |
| Avatars | `CS/stream-chat-flutter/avatars.md` |
| Custom message list state (core) | `CS/stream-chat-flutter-core/message-list-core.md` |
| Send / edit / delete messages | `CD/send-message.md` |
| Pinned messages | `CD/pinned-messages.md` |
| Unread counts | `CD/unread.md` |
| Delivered / read status | `CD/message-delivery-and-read-status.md` |

### Composer and rich content

| Want to ... | Page (.md) |
|---|---|
| Message composer | `CS/stream-chat-flutter/message-composer/stream-message-composer.md` |
| Composer controller (core) | `CS/stream-chat-flutter-core/stream-message-composer-controller.md` |
| Attachments / system picker | `CS/stream-chat-flutter/message-composer/attachments.md`, `CS/stream-chat-flutter/message-composer/system-attachments-picker.md` |
| File uploads (API) | `CD/file-uploads.md` |
| Mentions / autocomplete triggers | `CS/stream-chat-flutter/message-composer/mentions.md`, `CS/stream-chat-flutter/custom-widgets/autocomplete-triggers.md` |
| Voice recording | `CS/stream-chat-flutter/stream-voice-recording.md` |
| Polls (UI / API) | `CS/stream-chat-flutter/polls.md`, `CD/polls-api.md` |
| Drafts | `CS/stream-chat-flutter/drafts.md` |
| Location sharing | `CS/guides/location-sharing.md` |
| Extra data on models | `CS/client/extra-data.md` |

### Users, search and lists

| Want to ... | Page (.md) |
|---|---|
| Member list / grid | `CS/stream-chat-flutter/member-list/stream-member-list-view.md`, `CS/stream-chat-flutter/member-list/stream-member-grid-view.md` |
| User list / grid | `CS/stream-chat-flutter/user-list/stream-user-list-view.md`, `CS/stream-chat-flutter/user-list/stream-user-grid-view.md` |
| User / member controllers | `CS/stream-chat-flutter-core/stream-user-list-controller.md`, `CS/stream-chat-flutter-core/stream-member-list-controller.md` |
| Message search (UI / controller / API) | `CS/stream-chat-flutter/message-list/stream-message-search-list-view.md`, `CS/stream-chat-flutter-core/stream-message-search-list-controller.md`, `CD/search.md` |
| Paging helpers | `CS/stream-chat-flutter-core/paged-value-listenable-builder.md`, `CS/stream-chat-flutter-core/lazy-load-scroll-view.md` |
| User presence | `CD/presence-format.md` |

### Production

| Want to ... | Page (.md) |
|---|---|
| Push notifications (run [`push.md`](push.md)) | `CS/guides/push-notifications.md` |
| Offline / local persistence | `CS/basics/offline-support.md`, `CD/flutter-offline.md` |
| Permissions / channel types | `CD/permissions-reference.md`, `CD/channel-features.md` |
| Moderation | `CS/guides/moderation.md` |
| Go-live checklist / best practices | `CS/guides/go-live-checklist.md`, `CD/best-practices.md` |
| Rate limits / query budget | `CD/rate-limits.md`, `CD/api-budget.md` |
| Livestream chat | `CS/guides/adding-chat-to-video-livestreams.md`, `CS/guides/livestream-best-practices.md` |
| AI assistants | `CS/guides/ai-integrations.md`, `CS/guides/ai-integrations/stream-chat-integration.md`, `CS/guides/ai-integrations/client-side-tools.md` |
| Custom CDN / E2E encryption / Sentry | `CS/client/custom-cdn.md`, `CS/guides/end-to-end-chat-encryption.md`, `CS/guides/error-reporting-with-sentry.md` |

---

## Video

`stream_video_flutter` covers calls, audio rooms and livestreaming. Read the Video pitfalls in [`RULES.md`](RULES.md) first - several are build-breakers the docs do not mention. Patterns with no docs page (livestream feed pager, floating call over a broadcast, shared call state, Chat + Video glue) are in [`video-patterns.md`](video-patterns.md).

### Setup and calls

| Want to ... | Page (.md) |
|---|---|
| Overview / packages | `https://getstream.io/video/docs/flutter.md` |
| Install packages + platform permissions | `V/basics/installation.md` |
| First call in minutes | `V/basics/quickstart.md` |
| Client init, tokens, guest / anonymous users | `V/guides/client-auth.md` |
| Create / join calls, members, backstage join-ahead | `V/guides/joining-and-creating-calls.md` |
| Read call and participant state | `V/guides/call-and-participant-state.md` |
| Call types and settings | `V/guides/configuring-call-types.md` |
| Camera control | `V/guides/camera-and-microphone/camera.md` |
| Mic, audio output, audio policies | `V/guides/camera-and-microphone/microphone-and-audio.md` |
| Initial camera / mic state on join | `V/guides/camera-and-microphone/initial-call-configuration.md` |
| High-fidelity / music audio | `V/guides/camera-and-microphone/high-fidelity-audio.md` |
| Noise cancellation | `V/guides/noise-cancellation.md` |
| Query calls / members | `V/guides/querying-calls.md`, `V/guides/querying-call-members.md` |
| Roles, permissions, request-to-speak, moderation | `V/guides/permissions-and-moderation.md`, `V/ui-cookbook/permission-requests.md`, `V/ui-cookbook/call-moderation.md` |
| Call events / custom events | `V/guides/call-events.md` |
| Custom call data | `V/advanced/custom-data.md` |
| End-to-end encryption | `V/guides/end-to-end-encryption.md` |
| Participant sorting | `V/guides/sorting-api.md` |
| Closed captions / transcription | `V/guides/closed-captions.md`, `V/ui-cookbook/transcriptions.md` |
| Reactions | `V/guides/reactions.md`, `V/ui-cookbook/reactions.md` |

### Call UI

| Want to ... | Page (.md) |
|---|---|
| Pre-built call screen | `V/call-container.md`, `V/call-content.md`, `V/ui-components-overview.md` |
| Render a participant's video | `V/video-render.md` |
| Participant layouts / tiles / list | `V/call-participants.md`, `V/ui-cookbook/participant-label.md`, `V/ui-cookbook/participant-list.md` |
| Custom call controls | `V/ui-cookbook/replacing-call-controls.md` |
| Pre-join lobby | `V/ui-cookbook/call-lobby.md` |
| Theming | `V/video-theme.md` |
| Picture-in-picture | `V/advanced/picture-in-picture.md`, `V/ui-cookbook/in-app-picture-in-picture.md` |
| Screen sharing | `V/guides/screensharing.md` |

### Livestream, audio rooms, combined products

| Want to ... | Page (.md) |
|---|---|
| Livestream: guide / host / watch | `V/guides/livestreaming.md`, `V/ui-cookbook/hosting-a-livestream.md`, `V/ui-cookbook/watching-a-livestream.md` |
| HLS / RTMP broadcasting | `V/advanced/broadcasting.md` |
| Recording | `V/advanced/recording.md` |
| Audio rooms (+ chat) | `V/ui-cookbook/audio-room-with-chat.md` |
| Chat app with video calls | `V/ui-cookbook/chat-with-video.md` |
| Multiple simultaneous calls | `V/advanced/multiple-simultaneous-calls-support.md`, `V/ui-cookbook/multicall.md` |

### Ringing and push (run [`push.md`](push.md))

| Want to ... | Page (.md) |
|---|---|
| Ringing overview (outgoing, `ring()`, auto-drop) | `V/advanced/incoming-calls/overview.md`, `V/advanced/incoming-calls/ringing.md` |
| Push providers + push manager config | `V/advanced/incoming-calls/providers-configuration.md` |
| Regular push, missed calls, device registration | `V/advanced/incoming-calls/push-notifications.md` |
| iOS CallKit / VoIP | `V/advanced/incoming-calls/callkit-integration.md` |
| Android FCM ringing + Telecom | `V/advanced/incoming-calls/android-firebase-integration.md` |
| Incoming / outgoing call UI and customization | `V/ui-cookbook/incoming-call.md`, `V/outgoing-call.md`, `V/advanced/incoming-calls/customization.md` |

### Production

| Want to ... | Page (.md) |
|---|---|
| Video filters / compositing | `V/advanced/apply-video-filters.md`, `V/ui-cookbook/video-compositing.md` |
| Background behavior / audio interruptions | `V/advanced/background-modes.md`, `V/advanced/handling-system-audio-interruptions.md` |
| Per-call preferences (timeouts, ringing drop) | `V/advanced/call-preferences.md` |
| Session timers / call duration | `V/ui-cookbook/session-timers.md`, `V/ui-cookbook/call-duration.md` |
| Network drops / low bandwidth / quality | `V/ui-cookbook/network-disruption.md`, `V/ui-cookbook/low-bandwidth.md`, `V/ui-cookbook/manual-video-quality-selection.md`, `V/ui-cookbook/network-quality-indicator.md` |
| Call rating / stats | `V/ui-cookbook/call-quality-rating.md`, `V/guides/call-statistics.md` |
| Deep links (join via link) | `V/advanced/deeplinking.md` |
| Troubleshooting | `V/advanced/troubleshooting.md` |
| Upgrade from v0.x | `V/migration-guides/1.0.0.md` |

---

## Feeds

`stream_feeds` (v3, plural) has **no pre-built UI**: the SDK gives you state objects, and you build the widgets (Twitter-style by default - see [`RULES.md`](RULES.md) "Feeds"). The deprecated `stream_feed` / `stream_feed_flutter_core` packages are a different API - never route to their docs.

Start with: quick start `https://getstream.io/activity-feeds/docs/flutter.md`, install `F/installation.md`, state layer `F/state.md`, errors / `Result<T>` `F/error-handling.md`.

| Want to ... | Page (.md) |
|---|---|
| Built-in feed groups (user / timeline / notification / foryou / stories), get-or-create a feed | `F/feeds.md` |
| Post / update / partial-update / delete activities | `F/activities.md` |
| Query activities across feeds | `F/query-activities.md` |
| Watch state in widgets (`StateNotifierBuilder`, `queryMore*`, dispose) | `F/state.md` |
| Real-time events | `F/events.md` |
| Likes / reactions | `F/reactions.md` |
| Comments (threaded) | `F/comments.md` |
| Bookmarks | `F/bookmarks.md` |
| Follow / unfollow, batch follows | `F/follows.md` |
| Notification feed (bell, seen / read) | `F/notification-feeds.md` |
| Stories | `F/stories.md` |
| Image / file uploads in a post | `F/file-uploads.md` |
| @mentions / URL previews | `F/user-mentions.md`, `F/url-previews.md` |
| Pins / polls | `F/pins.md`, `F/polls.md` |
| Feed members / visibility | `F/feed-members.md`, `F/feed-and-activity-visibility.md` |
| Search feeds | `F/search-for-feeds.md` |
| Aggregation / activity selectors (for-you) | `F/aggregation.md`, `F/activity-selectors.md` |
| Moderation | `F/moderation.md` |
| Push notifications | `F/push-notifications.md` |
| Best practices, performance, rate limits | `F/best-practices.md`, `F/performance.md`, `F/rate-limits.md` |
| Version changes | `F/roadmap-and-changelog.md` |

---

## Combined Chat + Video

Read the Chat + Video glue in [`video-patterns.md`](video-patterns.md) (aliased imports, one token, call id derived from the channel). Then route per product above. The integration narratives:

- Video side (chat in a call app): `V/ui-cookbook/chat-with-video.md`
- Chat side (chat next to a livestream): `CS/guides/adding-chat-to-video-livestreams.md`

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
