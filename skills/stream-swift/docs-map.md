# Stream Swift - docs routing map

Map a request to the exact iOS docs page, then fetch its `.md`. This table is the curated 80% - the high-frequency intents. For anything not here, fetch the live product index and pick from it:

| Product | Live index (lists every page) |
|---|---|
| Chat - iOS SDK (UI components + State Layer) | `https://getstream.io/cli/docs/chat-sdk-ios.md` |
| Chat - low-level client API reference | `https://getstream.io/cli/docs/chat-ios-swift.md` |
| Video | `https://getstream.io/cli/docs/video-ios.md` |
| Feeds | `https://getstream.io/cli/docs/activity-feeds-ios.md` |

Chat has **two doc trees**: the iOS SDK (`.../sdk/ios/...` - pre-built UI plus the `client/` State Layer) and the low-level API reference (`.../ios-swift/...` - the full client capability surface). See the Chat section below for which to use.

All page URLs end in `.md` (the Markdown twin - see [`SKILL.md`](SKILL.md)). Fetch at most 3 pages per request. Cite what you used. Do not guess paths - if it is not below, use the index.

---

## Chat

**First decide the layer** (see "pick the UI strategy" in [`SKILL.md`](SKILL.md)):

- Standard-messenger vertical (social, marketplace, workplace, support, DMs) -> **Pre-built UI** (sections below).
- Livestream / live-shopping / overlay chat -> **Custom UI on the low-level client + State Layer** (its own section below) - do not use the pre-built components.

**Matching a reference design (screenshot / Figma / "make it look like <app>")?** Do not pick rows à la carte and stop at theming. First run [`design-matching.md`](design-matching.md): it decomposes the design into every region (header, composer button set, timestamp + read-receipt placement, bubble shape/tail, date separators, attachments, ...) and maps each to its `ViewFactory` slot or theming token. The rows below are where it sends you per region; the full ~100-slot surface lives in `ViewFactory.swift` (read it - most slots are undocumented).

Install is shared by both layers: `https://getstream.io/chat/docs/sdk/ios/basics/integration.md`

### Chat - Pre-built UI (SwiftUI / UIKit)

**Start here:**

- Getting started, SwiftUI: `https://getstream.io/chat/docs/sdk/ios/swiftui/getting-started.md`
- Getting started, UIKit: `https://getstream.io/chat/docs/sdk/ios/uikit/getting-started.md`
- Overview: `https://getstream.io/chat/docs/sdk/ios.md`

#### Chat - SwiftUI

| Want to ... | Page (.md) |
|---|---|
| Channel screen overview | `.../swiftui/chat-channel-components/overview.md` |
| Message list | `.../swiftui/chat-channel-components/message-list.md` |
| Channel header | `.../swiftui/chat-channel-components/channel-header.md` |
| Message composer | `.../swiftui/chat-channel-components/message-composer-overview.md` |
| Composer commands / slash | `.../swiftui/chat-channel-components/composer-commands.md` |
| Custom attachments in composer | `.../swiftui/chat-channel-components/message-composer.md` |
| Channel list item | `.../swiftui/channel-list-components/channel-list-item.md` |
| Channel list header | `.../swiftui/channel-list-components/channel-list-header.md` |
| Channel list search | `.../swiftui/channel-list-components/channel-list-search.md` |
| Channel list helper views | `.../swiftui/channel-list-components/helper-views.md` |
| Channel list tap handling | `.../swiftui/channel-list-components/list-tap-events.md` |
| Channel filters and sorting | `.../swiftui/channel-list-components/query-filters.md` |
| Swipe actions | `.../swiftui/channel-list-components/swipe-actions-channels.md` |
| Reactions | `.../swiftui/message-components/message-reactions.md` |
| Threads | `.../swiftui/message-components/message-threads.md` |
| Inline replies | `.../swiftui/message-components/inline-replies.md` |
| Attachments | `.../swiftui/message-components/attachments.md` |
| Typing indicators | `.../swiftui/message-components/typing-indicators.md` |
| Read indicators | `.../swiftui/message-components/read-indicators.md` |
| Message display options | `.../swiftui/message-components/message-display-options.md` |
| Custom avatar | `.../swiftui/message-components/custom-avatar.md` |
| Thread list | `.../swiftui/thread-list.md` |
| Theming (colors, fonts, images) | `.../swiftui/theming.md` |
| ViewFactory / customizing components | `.../swiftui/view-customizations.md` |
| Polls | `.../swiftui/polls.md` |
| Draft messages | `.../swiftui/drafts.md` |
| Voice recording | `.../swiftui/voice-recording.md` |
| Localization | `.../swiftui/localization.md` |
| Cookbook: create-channel flow | `.../swiftui/swiftui-cookbook/creating-channels.md` |
| Cookbook: custom channel list | `.../swiftui/swiftui-cookbook/custom-channel-list.md` |
| Cookbook: custom message list | `.../swiftui/swiftui-cookbook/custom-message-list.md` |
| Cookbook: custom composer | `.../swiftui/swiftui-cookbook/custom-composer.md` |
| Cookbook: blocking users | `.../swiftui/swiftui-cookbook/blocking-users.md` |

(Prefix every row with `https://getstream.io/chat/docs/sdk/ios`.)

#### Chat - UIKit

| Want to ... | Page (.md) |
|---|---|
| Customizing components | `.../uikit/custom-components.md` |
| Theming | `.../uikit/theming.md` |
| Channel list | `.../uikit/components/channel-list.md` |
| Channel | `.../uikit/components/channel.md` |
| Message list | `.../uikit/components/message-list.md` |
| Message view | `.../uikit/components/message.md` |
| Message composer | `.../uikit/components/message-composer.md` |
| Thread / thread list | `.../uikit/components/thread.md` / `.../uikit/components/thread-list.md` |
| Reactions | `.../uikit/views/reactions.md` |
| Avatar | `.../uikit/views/avatar.md` |
| Message actions | `.../uikit/guides/customize-message-actions.md` |
| Attachments / custom attachments | `.../uikit/guides/working-with-attachments.md` / `.../uikit/guides/custom-attachments.md` |
| Polls / drafts | `.../uikit/polls.md` / `.../uikit/drafts.md` |
| Navigation | `.../uikit/navigation.md` |
| Localization | `.../uikit/localization.md` |

(Prefix every row with `https://getstream.io/chat/docs/sdk/ios`.)

### Chat - Custom UI (low-level client + State Layer)

Use this layer for livestream / live-shopping / overlay chat and any bespoke surface. There are **no** pre-built views here - you drive the SDK's state objects and render your own SwiftUI/UIKit. Two sources:

**(a) State Layer + Controllers** - how to observe state and react in your own views. Prefix `https://getstream.io/chat/docs/sdk/ios`:

| Want to ... | Page (.md) |
|---|---|
| State overview (start here) | `.../client.md` |
| State Layer (modern async/await: `Chat`, `ChannelList`, `MessageSearch`, ...) | `.../client/state-layer/state-layer-overview.md` |
| Controllers (delegate-based alternative) | `.../client/controllers/controllers-overview.md` |
| Channels state and filtering | `.../client/controllers/channels.md` |
| Listening to events | `.../client/controllers/events.md` |
| Offline support | `.../client/offline-support.md` |
| Extra data | `.../client/extra-data.md` |
| Livestream chat (high-volume channel patterns) | `.../client/livestream-chat.md` |

**(b) Low-level API reference** - the full client capability surface (the `ios-swift` tree). Prefix `https://getstream.io/chat/docs/ios-swift`:

| Want to ... | Page (.md) |
|---|---|
| Introduction / init and users | `.md` (root) / `/init-and-users.md` |
| Tokens and authentication | `/tokens-and-authentication.md` |
| Query / create channels, pagination | `/query-channels.md`, `/creating-channels.md`, `/channel-pagination.md` |
| Channel types and features | `/channel-features.md` |
| Send messages | `/send-message.md` |
| Threads and replies | `/threads.md` |
| Reactions | `/send-reaction.md` |
| Typing indicators | `/typing-indicators.md` |
| Read and delivery status / unread counts | `/message-delivery-and-read-status.md`, `/unread.md` |
| Events | `/event-object.md` |
| Message search / query members | `/search.md`, `/query-members.md` |
| Permissions and policies | `/chat-permission-policies.md` |
| Polls / slow mode | `/polls-api.md`, `/slow-mode.md` |
| **Livestream and live-shopping best practices** | `/livestream-best-practices.md` |
| **Marketplace app best practices** | `/marketplace-best-practices.md` |
| Best practices overview | `/best-practices.md` |

For anything else in this tree, fetch the index: `https://getstream.io/cli/docs/chat-ios-swift.md`.

### Chat - cross-cutting (any layer)

Prefix `https://getstream.io/chat/docs/sdk/ios`:

| Want to ... | Page (.md) |
|---|---|
| Push notifications | `.../client/push-notifications.md` |
| Moderation | `.../guides/moderation.md` |
| Logging | `.../basics/logs.md` |
| Go-live checklist | `.../guides/go-live-checklist.md` |
| Add video calls to chat | `.../guides/video-integration.md` |
| Location sharing | `.../guides/location-sharing.md` |
| AI integrations | `.../ai-integrations/overview.md` |
| Migrate 4.x -> 5.x | `.../guides/migrating-from-4-to-5.md` |

### Chat - best practices and limits

Read before building or scaling a vertical (see [`RULES.md`](RULES.md) "Mindful API usage"). Prefix `https://getstream.io/chat/docs/ios-swift`:

| Topic | Page (.md) |
|---|---|
| Best practices overview | `/best-practices.md` |
| Livestream and live-shopping (disable read/typing/connect events, etc.) | `/livestream-best-practices.md` |
| Marketplace apps | `/marketplace-best-practices.md` |
| Query channels budget | `/api-budget.md` |
| Rate limits / fair usage | `/rate-limits.md`, `/fair-usage-limits.md` |
| Slow mode and throttling | `/slow-mode.md` |

### Chat - permissions and roles

Pick the channel type per vertical, then tune policies (see [`RULES.md`](RULES.md) "Permissions"). Prefix `https://getstream.io/chat/docs/ios-swift`:

| Want to ... | Page (.md) |
|---|---|
| Channel types and their defaults (messaging / livestream / team / gaming / ai) | `/channel-features.md` |
| Permission policies, roles, scopes (how to grant/revoke) | `/chat-permission-policies.md` |
| Full permission/action reference | `/permissions-reference.md` |
| Guest + anonymous users (livestream viewers, pre-auth) | `/authless-users.md` |
| Multi-tenant / teams isolation | `/multi-tenant-chat.md` |

---

## Push notifications (Chat push + Video VoIP / CallKit)

For setup, follow the runbook [`push.md`](push.md) (it automates the Stream CLI provider creation + client wiring). These are the pages it routes to:

| Want to ... | Page (.md) |
|---|---|
| Chat push: permission, register device, NSE | `https://getstream.io/chat/docs/sdk/ios/client/push-notifications.md` |
| Chat push providers / multi-bundle (config) | `https://getstream.io/chat/docs/ios-swift/push-providers-and-multi-bundle.md` |
| Chat push overview / register devices | `https://getstream.io/chat/docs/ios-swift/push-introduction.md`, `https://getstream.io/chat/docs/ios-swift/push-devices.md` |
| Chat push templates / testing | `https://getstream.io/chat/docs/ios-swift/push-template.md`, `https://getstream.io/chat/docs/ios-swift/push-test.md` |
| Video VoIP push for incoming calls | `https://getstream.io/video/docs/ios/advanced/incoming-calls/push-notifications.md` |
| Video CallKit integration (ringing) | `https://getstream.io/video/docs/ios/advanced/incoming-calls/callkit-integration.md` |
| Video ringing overview | `https://getstream.io/video/docs/ios/advanced/incoming-calls/ringing.md`, `https://getstream.io/video/docs/ios/advanced/incoming-calls/overview.md` |

---

## Video

**Start here:**

- Install: `https://getstream.io/video/docs/ios/basics/installation.md`
- Quickstart: `https://getstream.io/video/docs/ios/basics/quickstart.md`
- Client and authentication: `https://getstream.io/video/docs/ios/guides/client-auth.md`
- Introduction: `https://getstream.io/video/docs/ios.md`

### Video - core

| Want to ... | Page (.md) |
|---|---|
| Join / create a call | `.../guides/joining-creating-calls.md` |
| Call and participant state | `.../guides/call-and-participant-state.md` |
| Calling state machine | `.../guides/call-state.md` |
| Camera and microphone | `.../guides/camera-and-microphone.md` |
| Query calls / members | `.../guides/querying-calls.md` / `.../guides/querying-call-members.md` |
| Configure call types | `.../guides/configuring-call-types.md` |
| Reactions / custom events / events | `.../guides/reactions.md` / `.../guides/custom-events.md` / `.../guides/events.md` |
| Permissions and moderation | `.../guides/permissions-and-moderation.md` |
| Noise cancellation | `.../guides/noise-cancellation.md` |

### Video - UI components

| Want to ... | Page (.md) |
|---|---|
| UI overview | `.../ui-components/overview.md` |
| SwiftUI vs UIKit | `.../ui-components/swiftui-vs-uikit.md` |
| Customizing views (ViewFactory) | `.../ui-components/customizing-views.md` |
| UIKit customizations | `.../ui-components/uikit-customizations.md` |
| CallViewModel | `.../ui-components/view-model.md` |
| Theme | `.../ui-components/video-theme.md` |
| CallContainer / CallControls | `.../ui-components/call/call-container.md` / `.../ui-components/call/call-controls.md` |
| Active / incoming / outgoing call view | `.../ui-components/call/active-call.md` / `.../ui-components/call/incoming-call.md` / `.../ui-components/call/outgoing-call.md` |
| Participants / local video | `.../ui-components/participants/call-participants.md` / `.../ui-components/participants/local-video.md` |
| UI cookbook: lobby, pinning, layout, etc. | check index under `.../ui-cookbook/...` |

### Video - livestream / streaming

| Want to ... | Page (.md) |
|---|---|
| Streaming overview | `.../streaming/overview.md` |
| Livestreaming guide | `.../guides/livestreaming.md` |
| Backstage (go live / stop live) | `.../streaming/backstage.md` |
| WebRTC viewer | `.../streaming/webrtc.md` |
| HLS viewer | `.../streaming/hls.md` |
| RTMP ingress / broadcasts | `.../streaming/rtmp.md` / `.../streaming/rtmp-broadcasts.md` |
| Mobile livestreaming (broadcast from device) | `.../streaming/mobile-livestreaming.md` |
| Watch a livestream (player UI) | `.../ui-cookbook/livestream-player.md` |

### Video - advanced

| Want to ... | Page (.md) |
|---|---|
| Ringing | `.../advanced/incoming-calls/ringing.md` |
| CallKit integration | `.../advanced/incoming-calls/callkit-integration.md` |
| VoIP push for incoming calls | `.../advanced/incoming-calls/push-notifications.md` |
| Screen sharing | `.../advanced/screensharing.md` |
| Picture-in-picture | `.../advanced/picture-in-picture.md` |
| Add chat to a call | `.../advanced/chat-integration.md` |
| Deeplinking | `.../advanced/deeplinking.md` |
| Troubleshooting calls | `.../advanced/troubleshooting-calls.md` |
| Video / audio filters | `.../advanced/apply-video-filters.md` |
| Background modes | `.../advanced/background-modes.md` |

(Prefix every Video row with `https://getstream.io/video/docs/ios`.)

---

## Feeds

> Feeds has **no pre-built UI** - the SDK exposes state (feeds, activities, reactions, comments, follows); you build the views. Always read the relevant state page before assuming an API.

**Start here:**

- Install: `https://getstream.io/activity-feeds/docs/ios/installation.md`
- Quick start: `https://getstream.io/activity-feeds/docs/ios.md`
- Tokens and authentication: `https://getstream.io/activity-feeds/docs/ios/tokens-and-authentication.md`
- State layer: `https://getstream.io/activity-feeds/docs/ios/state.md`

| Want to ... | Page (.md) |
|---|---|
| Feeds (create, read, query) | `.../feeds.md` |
| Feed groups (user, timeline, notification) | `.../feed-groups.md` |
| Activities (post, read, update) | `.../activities.md` |
| Reactions | `.../reactions.md` |
| Comments | `.../comments.md` |
| Follow / unfollow | `.../follows.md` |
| Notification feed | `.../notification_feeds.md` |
| For-you feed | `.../for_you_feed.md` |
| Feed views | `.../feed-views.md` |
| Bookmarks | `.../bookmarks.md` |
| Polls | `.../polls.md` |
| Stories | `.../stories.md` |
| Push notifications | `.../push-notifications.md` |
| File uploads | `.../file_uploads.md` |
| Moderation | `.../moderation.md` |
| Migrate v2 -> v3 | `.../v2_to_v3_migration.md` |

(Prefix every Feeds row with `https://getstream.io/activity-feeds/docs/ios`.)

---

## Combined Chat + Video

This breaks builds via name collisions - read the pitfall in [`RULES.md`](RULES.md) first (file isolation). Then route per product above. The integration narratives:

- Chat side (add calls to messaging): `https://getstream.io/chat/docs/sdk/ios/guides/video-integration.md`
- Video side (add chat to calls): `https://getstream.io/video/docs/ios/advanced/chat-integration.md`

---

## When the docs fall short: source code + example apps

For a specific UI customization or feature the docs do not cover - an exact `ViewFactory` method signature, a protocol's full surface, an undocumented option, or how a flow is really wired - read the **SDK source** and the **demo/example apps**. The source is the final source of truth.

| SDK | Repo (github.com/GetStream/...) | Source | Demo / example apps |
|---|---|---|---|
| Chat low-level + UIKit | `stream-chat-swift` | `Sources/` (StreamChat, StreamChatUI) | `DemoApp`, `DemoAppPush`, `StreamChatSample`, `Examples` |
| Chat SwiftUI | `stream-chat-swiftui` | `Sources/` | `DemoAppSwiftUI` |
| Video (SwiftUI + UIKit) | `stream-video-swift` | `Sources/` | `DemoApp` (SwiftUI), `DemoAppUIKit` |
| Feeds | `stream-feeds-swift` | `Sources/` (StreamFeeds) | `DemoApp` |

How to search (prefer the version-accurate local checkout - no network, matches what the project compiles):

1. **Local SwiftPM checkout** - the exact source for the project's pinned version:

   ```bash
   # List candidates WITH their actual tag — a sibling project's DerivedData can
   # hold a DIFFERENT version of the same package, so never blindly take head -1.
   for d in $(find ~/Library/Developer/Xcode/DerivedData /tmp -type d -path "*checkouts/stream-*-sw*" 2>/dev/null); do
     echo "$(git -C "$d" describe --tags 2>/dev/null)  ->  $d"
   done
   # Pick the one whose tag == the version in Package.resolved, then grep it:
   grep -rn "func makeMessageListModifier" <matching-checkout>/Sources
   ```

   (For `swift build` projects the checkout is under `.build/checkouts/`.) **Cross-check the tag against `Package.resolved` before reading — the API differs across majors/minors (Options-based slots, the `Styles` protocol, `chatBackground*` tokens, and the `StreamChatCommonUI` Appearance only exist on recent versions). The checkout the build actually compiles (this project's own DerivedData or your `-derivedDataPath`) is authoritative; if source you read contradicts the live docs about a symbol's existence, you are probably on the wrong version.**

2. **GitHub** - for the demo/example apps (not included in the SPM checkout) and when no local checkout exists. Browse `Sources/` for the API and the demo folder for real usage; read raw files from `raw.githubusercontent.com/GetStream/<repo>/<tag>/...`.

Match the version the project pins (`Package.resolved`). Do not present source-derived APIs as if documented - say where you found them.
