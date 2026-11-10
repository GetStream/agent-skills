---
name: stream-react-native
description: "Build, integrate, audit, or upgrade Stream Chat, Video, and Feeds in React Native CLI and Expo / Expo Router apps, and answer RN / Expo how-to questions about them. Scaffold a new app, add Stream to an existing project, review an integration, upgrade an SDK major, migrate from Sendbird (@sendbird/chat, @sendbird/uikit-react-native), or build an AI assistant / ChatGPT-style app on the Chat SDK's ai-components (replacing the deprecated @stream-io/chat-react-native-ai). Covers channel lists, messages, MessageComposer, threads, the attachment picker, audio messages, offline support, push notifications, video calls, CallContent and ParticipantView, ringing, livestreams, audio rooms, StreamFeeds activity / timeline / notification feeds, comments, reactions, follows, and theming or matching a design, with stream-chat-react-native, stream-chat-expo, @stream-io/video-react-native-sdk, and @stream-io/feeds-react-native-sdk. React Native and Expo only - web React uses stream-react."
license: See LICENSE in repository root
metadata:
  author: GetStream
---

# Stream React Native

## Docs

Don't write Stream SDK code from memory. APIs change between majors, so your
memory is stale. Read the docs first, via the `getstream docs` command:

```bash
cat $(getstream docs chat-sdk/react-native)/INDEX.md
```

Client and UI: chat-sdk/react-native, video/react-native,
activity-feeds/react-native; the low-level Chat client (permissions, query
filters, channel types) is chat/react-native. Node.js backend (token route,
webhooks): chat/node, activity-feeds/node, moderation/node. Previous Chat
majors are available too (chat-sdk/react-native/v<major>).

Chat SDK majors can differ deeply (state, channel lists, threads,
configuration). Before any Chat code, pin the installed major, read only that
major's docs (never the unversioned id on trust), and treat SDK names in this
skill and in your memory as leads to confirm there - follow chat-versions.md.

Video versions its docs too: `getstream docs list` shows which
`video/react-native` major is Latest and which is a beta. Read the installed
`@stream-io/video-react-native-sdk` major and pass the versioned id
(video/react-native/v<major>) when it isn't the Latest one.

A how-to question needs no setup: answer it from the pinned major's docs and
say which major the answer is for.

## Setup

Start with `getstream init` (binds the working dir to a Stream app, existing or
new) and `getstream env --target expo` (writes `EXPO_PUBLIC_STREAM_API_KEY` to
`.env`). `getstream env` writes `.env` to the folder `getstream init` ran in,
which isn't always the app folder (an app scaffolded in a subfolder): move it
next to the app's `package.json`, or Metro never reads it. A bare RN CLI app
has no env target: put the public API key in the app's config, never the
secret.

For new apps, Expo (`npx create-expo-app@latest`, Expo Router) is the default
unless the user asks for RN CLI. In an existing app, read the lane before
editing: Expo or RN CLI (`app.json` / `app.config.*`, `ios/` + `android/`),
the Expo SDK version, Expo Router or React Navigation, and the package manager.
Keep all of them. In a non-empty directory that isn't an RN app, ask before
scaffolding a child app there.

Install the SDKs, with the peers listed on each product's Installation page:

- Chat: `stream-chat` plus one wrapper for the lane - `stream-chat-expo` on
  Expo, `stream-chat-react-native` on RN CLI, never both (see
  chat-versions.md for which major)
- Video: `@stream-io/video-react-native-sdk` (both lanes)
- Feeds: `@stream-io/feeds-react-native-sdk` (both lanes)
- Server-side: `@stream-io/node-sdk`

Don't bump an already-installed Stream major. Expo apps use `npx expo install`
so versions match the Expo SDK.

Writes through `getstream api` (product configuration: channel types, feed
groups, moderation policies, and the Video label below) are app-wide. Before the
first one, run `getstream status` and tell the user which app it will change, so
a stale CLI binding doesn't write to the wrong (possibly production) app.

For Video apps, label the use case once, without asking the user (metadata, no
runtime effect):

```sh
getstream api UpdateApp --request '{"video_primary_use_case":"livestreaming"}'
```

Allowed values: `video-calling`, `voice-calling`, `livestreaming`,
`audio-rooms`, `ai-agents`, `live-shopping`, `other`. Derive it from what the
app is, not from the call type in use (Whatnot runs on the `livestream` call
type but is `live-shopping`). Any commerce signal means `live-shopping`. Unsure
means `other`.

Native setup that costs real runs:

- Chat and Video ship native code: Expo apps run in a development build
  (`expo-dev-client`, `npx expo prebuild`), never Expo Go. Every native package
  added later means another prebuild and native build, so decide the full set
  of capability packages (picker, camera, audio recording, video playback,
  offline, ringing) before the first build.
- Babel: on Expo SDK 54+, `babel-preset-expo` adds the worklets plugin itself -
  don't create a `babel.config.js` (a hand-written one can break Metro with
  `Cannot read properties of undefined (reading 'transformFile')`). On RN CLI
  the Reanimated / worklets plugin goes last in `babel.config.js`.
- Expo SDK 57 pins `react-native-reanimated@4.5.0` + `react-native-worklets@0.10.0`,
  a pair that crashes on animation paths (not at boot, so a clean launch proves
  nothing). Require reanimated >= 4.5.1 and worklets >= 0.10.2, installed after
  the other `npx expo install` calls, which re-pin the bad pair. Check the
  installed versions, not the launch.
- With Reanimated 4 and Chat, set
  `"reanimated": { "staticFeatureFlags": { "FORCE_REACT_RENDER_FOR_SETTLED_ANIMATIONS": false } }`
  in the root `package.json` (the default breaks bottom sheets, the message
  overlay, and context menus). It is read at pod install: rebuild native after.
- Expo Router on SDK 56+ refuses to bundle with any `@react-navigation/*`
  package. Don't install one, even for `useHeaderHeight`: recent Expo Router
  (SDK 58) exports it from `expo-router/react-navigation`.
- `react-native-teleport` (a Chat peer) has `react-dom` as an optional peer:
  when the app already has `react-dom` (the default Expo template does), pin it
  to the app's exact `react` version, or the install resolves a mismatch.
- Safe areas: `SafeAreaProvider` from `react-native-safe-area-context` at the
  root, never `SafeAreaView` from `react-native`. On RN 0.85 / Expo 56 the
  package's `SafeAreaView` can fail to apply insets; `useSafeAreaInsets()` plus
  padding works. Android draws edge-to-edge (`edgeToEdgeEnabled`: Expo
  `app.json`, RN CLI 0.81+ `gradle.properties`).

## Auth and users

Tokens are minted server-side: a route uses the secret and returns the token
with the apiKey. The route derives the Stream user id from its own session
(cookie, JWT, OAuth subject), never from a `user_id` the app sends - that lets
any signed-in user impersonate any other. The secret never reaches the app
bundle, `app.json`, or native config. An app that already has auth or a token
endpoint gets it extended, not a second one.

Start with a login screen. Don't auto-connect, don't hardcode user credentials,
don't seed demo users or content on app load. The token route upserts only the
requesting user.

Without a backend: a new Stream app has dev tokens off, so `devToken()` is
rejected. Don't turn auth checks off to get around it (an app-wide security
setting). Mint a token per test user with `getstream token <user_id>` (one
call per user) into a `__DEV__`-gated, gitignored module, let the login screen
pick from that roster, and say a real deployment needs a token route.
`EXPO_PUBLIC_*` values are inlined at bundle time: restart Metro with `--clear`
after editing `.env`.

## Building

Clients mount once, at the app root, above the navigator. Don't
`disconnectUser()` in a screen's cleanup - it kills the client every other
screen shares. A call screen's cleanup is `call.leave()`. A channel screen needs
no cleanup: don't `stopWatching()` a channel when its screen closes - the
channel list still shows it and needs its events.

- Chat: `useCreateChatClient()` (returns `null` while connecting - render
  nothing until it's ready). With offline support this blocks the cached UI;
  see the offline bullet under Chat.
- Feeds: `useCreateFeedsClient()` (returns `undefined` while connecting).
- Video: `StreamVideoClient.getOrCreateInstance()` in a `useEffect` with
  `disconnectUser()` cleanup, never `new StreamVideoClient()` - a second
  instance breaks push and ringing.

Providers nest; they are never siblings: `GestureHandlerRootView` >
`SafeAreaProvider` > Stream providers > navigator. Chat's `OverlayProvider` sits
above the navigator, or the long-press menu, attachment picker, and image
gallery render under the screen. Navigation params carry ids (`channel.cid`, a
call id, an activity id), never a `Channel`, `Call`, or activity object.

Start with prebuilt Stream SDK components. Customize them via documented props,
theme, and hooks. Feeds has no prebuilt UI - build from its hooks.

Land on a channel list, lobby, or feed by default - never directly in a call or
a camera prompt. Camera/mic permission is requested only on an explicit action
(Join, Go Live). Empty states say what to do next.

Chat:

- Component overrides go through `<WithComponents overrides={...}>`, placed
  above the navigator. To change a shared slot (such as `EmptyStateIndicator`,
  which the channel list, message list, and thread all read) on one screen
  only, wrap just that screen's component in its own `WithComponents`; nested
  ones merge with their parent. A component passed as a `<Channel>` prop is
  silently ignored and looks like a stale bundle. `WithComponents` reads its
  overrides once, at mount: an override that must change at runtime (theme,
  state) reads it inside the component (`useTheme()`, a hook), not by swapping
  the `overrides` object. Some slots (the
  `MessageContent*View` slots, `MessageSpacer`, `MessageText`, `Input`) are
  optional overrides, not defaults: grep both `DEFAULT_COMPONENTS` and
  `OptionalComponentOverrides` in the installed core before saying a slot
  doesn't exist.
- Keyboard and picker insets: omitting `<Channel>`'s `keyboardVerticalOffset`
  doesn't mean 0 - the keyboard view falls back to its own default (86.5 on
  iOS, -300 on Android). With the header rendered inside `<Channel>`, pass
  `keyboardVerticalOffset={0}` and `topInset={0}`. Under a native navigation
  header, pass the header height to both - `topInset` is what the attachment
  picker uses for its snap point. On Expo Router, take the height from
  `useHeaderHeight` in `expo-router/react-navigation` when the installed
  version exports it, else `(Platform.OS === 'ios' ? 44 : 56) + insets.top`.
  On iOS 26 the native header is transparent by default (content scrolls under
  it, so no offset is right): set `headerTransparent: false` on the stack. A
  gap between the composer and the picker means `topInset` is wrong; don't
  close it with `bottomInset`. Check by focusing the input so the real keyboard
  rises (`setText` doesn't raise it).
- Feature gating: the source of truth is the connected user's
  `channel.data?.own_capabilities`. Outside `<Channel>`, read them with
  `useChannelOwnCapabilities(channel)`; the context hook throws there.
- Custom reaction types are string ids, not emoji characters (emoji are
  rejected server-side), passed as `supportedReactions` on `<Channel>`. Extend the
  exported `reactionData` instead of rebuilding it, and mark the picker's
  entries `isMain: true` - entries without it never show in the picker.
- A channel created from a member list only (no id) can't change its members
  later. Give it an id when membership will change.
- A custom long-press menu owns its thread and edit wiring: open a thread with
  `openThread(message)` plus your navigation to the thread screen; start an
  edit with `setEditingState` after the menu's Modal has closed, then focus the
  input (an edit started while the Modal is open silently does nothing).
- Offline support is opt-in (`enableOfflineSupport` on `<Chat>` plus
  `@op-engineering/op-sqlite`). It only helps if the UI renders before the
  connection does: `useCreateChatClient` returns `null` until connected, so an
  offline launch shows a blank screen. Create the client yourself and call
  `connectUser` without awaiting it before rendering `<Chat>`, as
  `basics/offline-support.md` shows. On sign-out call
  `client.offlineDb?.resetDB()` before `disconnectUser()`, or the next user on
  the device sees the previous user's data.

Feeds:

- Import from `@stream-io/feeds-react-native-sdk`. Some docs snippets import
  the web package (`@stream-io/feeds-react-sdk`); don't copy that.
- A social feed needs a visible follow control - a timeline without follows is
  permanently empty. Follows go through the timeline feed instance, not
  `client.follow()`, so the feed hooks update. Follow your own user feed too, or
  your own posts never appear in your timeline.
- Screens that show live data read watched feeds through the state hooks, not
  `queryActivities` (a one-off query that never updates).
- A comments screen built on `client.activityWithStateUpdates(id)` must ask for
  comments in its `get()` call, or `useActivityComments` stays empty. Dispose
  the handle on unmount.
- The `foryou` feed group returns nothing until its `activity_selectors` are
  configured (`getstream api UpdateFeedGroup`), and a `popular` selector also
  needs activities that clear its `min_popularity`.
- Push devices are registered with `client.createDevice()` (native token, not
  the Expo push token) and removed with `client.deleteDevice()` before
  disconnecting - not Video's `addDevice`.

Video:

- The destination call screen is the only place that gets the call:
  `client.call(type, id, { reuseInstance: true })` - the same call may already
  exist from a ring, a deep link, or push, and without the flag the SDK builds a
  duplicate. Descendants read it with `useCall()`.
- Guard the cleanup leave:
  `if (call.state.callingState !== CallingState.LEFT) await call.leave()`. The
  default hang-up already leaves, and a second `leave()` throws. Hang-up
  handlers only navigate.
- Audio routing is automatic on join and leave. Don't add
  `callManager.start/stop` for normal calls; only a view-only audience
  (livestream viewer, audio-room listener) changes `audioRole` to `listener`.
- Ringing: `StreamVideoRN.setPushConfig` needs `createStreamVideoClient`,
  built with the same options as the app's client - a mismatch breaks ringing.
  Non-ringing call pushes are app-owned and on iOS use the APNs token, not the
  VoIP token.
- Insets reach the call UI through the theme (`variants.insets` from
  `useSafeAreaInsets()`). Don't also wrap `CallContent` and its siblings in
  `SafeAreaView` - that doubles the padding.
- Call-type setting changes don't apply to existing calls - test with a fresh
  call id.

Push, ringing, and Chat with Video follow the docs runbooks: Chat's
`guides/push-notifications.md`, Video's `advanced/incoming-calls/`, and
Video's `advanced/chat-with-video.md` (one API key and token for both, nested
providers).

Moderation:

- Don't build moderation UIs (review queue and the like): Stream Dashboard
  already provides them. End-user actions (report, block, mute) are fine.
- `CreateBlockList` 400s if the list already exists - check `ListBlockLists`
  first. Fill blocklists with real words, not `badword1` placeholders.
- Custom moderation rules return 403 on free plans - use blocklist + config
  instead.

## Defaults to keep

The prebuilt components ship features users expect. Keep each one on unless the
user turns it off by name. A design reference that doesn't show a feature, or
"keep it minimal", is not turning it off: keep the feature and style it to
match, or ask.

Override the smallest slot that does the job, and add to existing
`WithComponents` overrides instead of replacing them. Replacing a whole region
drops everything it rendered by default:

- A custom message must put back what the default renders: text, attachments,
  quoted message, polls, reactions, replies count, the long-press menu,
  timestamp, read status, edited and deleted states.
- A custom composer must put back the attachment picker and previews, the
  quoted-message preview, audio recording, link previews, and the send / stop
  button.

The defaults, and what usually turns them off:

- Markdown in message text. Rendering `message.text` in a plain `<Text>`, or a
  custom `MessageText` that doesn't build on the SDK's, turns it off. Check:
  send `**bold**`, a list, and a code block.
- Reactions. A custom message without the reaction list, or custom reaction
  types missing `isMain`. Check: long-press, react, and see the reaction.
- Threads. A navigator without a thread screen, or a custom message without
  the replies count. Check: reply in a thread, and open it from the parent.
- Attachment picker. Keep the SDK's `AttachmentPicker` and override only
  `AttachmentPickerSelectionBar` / `AttachmentPickerContent`; don't build a
  separate modal. The picker's toggle lives inside the default `AttachButton`
  and isn't exported: a custom attach button reproduces it (design-matching.md,
  Build). Check: open the picker, attach an image, send.
- Send and mic. Reuse `OutputButtons` (it swaps send, mic, and stop by state)
  instead of hand-rolling buttons. Audio recording is off by default
  (`audioRecordingEnabled` on `<Channel>`). Check: type, send, and record if
  enabled.
- AI replies: `isMessageAIGenerated` on `<Chat>` (streamed text), and the stop
  button the default composer shows while the AI works (replacing the composer
  drops it). Check: as in ai-integration.md.

## Verify

Type-check (from an absolute `cd` into the project, never piped - a pipe
reports the pipe's exit status, so a failing check reads as green), build
native, run the app on a simulator or emulator, and test multi-user flows as
two different users: two simulators, a simulator and an emulator, or - with one
device - the second user acting server-side
(`getstream api SendMessage ... "user_id":"<other user>"`) while you watch the
message arrive live; that user must exist and be a channel member (log in as
them once first). That is a verification step, not app seeding. Drive the
interactions (tap, long-press, type, send); a screenshot doesn't prove a tap
works. Follow simulator-verification.md for the run loop.

Run the check for each default in Defaults to keep. Report what was verified
and what wasn't, and list each default that is off with the user's words that
turned it off.

## Auditing an integration

When asked, perform a read-only audit: check the code against the docs and the
rules in Building, report findings, and fix only if asked. Video has a
checklist page for this: `advanced/integration-best-practices.md` in
video/react-native. For a pre-launch review, also follow the stream skill's
integration-review.md.

## Upgrading an SDK version

When asked, read the upgrade notes for both the installed and the target major
(use the versioned docs), apply them, then verify as if you're building an app.
For Chat, follow the AI migration guide for the exact pair of majors
(chat-versions.md), one major per pass.

RN upgrades also carry native work, in this order: prerequisites the guide
names (New Architecture, React Native / Expo floors), new native peers, then
the code. Bump the lane's wrapper and `stream-chat` together; Stream packages
version independently, so each gets its own target. Confirm every renamed
symbol in the installed `stream-chat-react-native-core` source, not the
wrapper. Rebuild native (`pod install`, or `npx expo prebuild --clean` and a new
development build) before testing.

Feeds v2 to v3 is a data migration as well as a code one: use the
stream-feeds-migration skill for the mapping.

## Matching a reference design

When the request carries a target appearance - a screenshot, a Figma frame,
"make it look like WhatsApp" - follow design-matching.md.

A named app without a reference ("a Slack-like team chat", "a WhatsApp-style DM
app") is guidance on structure - the shape, built from prebuilt components - not
a look to match. Only explicit design reference warrants design-matching.md.

## Migrating from Sendbird

For the code migration, follow sendbird-migration.md. When the user also wants
their existing data moved (users, channels, message history), follow the stream
skill's sendbird-data-migration.md.

## AI assistants, support bots, agents

The model runs on a backend agent, never in the app: no LLM provider key or
Stream secret in the bundle, `app.json`, or native config.

- Stream Agents (voice and text agents run on Stream, `getstream agents`) has no
  React Native client SDK: `@stream-io/stream-agents` is for Node and the browser.
  Tell the user before building.
- Support bot, help desk, RAG chat: the backend is the same as on the web -
  follow stream-react skill's ai-support-agent.md for it, then
  ai-integration.md for the app.
- ChatGPT-style app, an assistant inside an existing chat, streaming answers,
  stop generating, voice input, client tools, generative UI: follow
  ai-integration.md.

## Other skills

This skill covers Stream. For general React Native and Expo work, use these
skills if they're installed:

- vercel-react-native-skills: performance - list rendering, animations, native
  modules.
- Expo's skills (expo/skills): Expo Router, development builds, EAS, upgrading
  the Expo SDK.

Where general advice conflicts with this skill, this skill wins for Stream
code:

- Create clients as described in Building, even if a performance rule suggests
  restructuring the effect or memoizing differently.
- Customize Stream UI through its documented overrides (`WithComponents`, the
  theme, props, hooks), not by rebuilding it as your own components. Defaults
  to keep applies.
- Keep the Chat and Video packages in a development build even where a general
  skill prefers Expo Go.

If these skills aren't installed, carry on without them. Don't install skills
yourself; mention them once in the final summary:

```bash
npx skills add vercel-labs/agent-skills --skill vercel-react-native-skills
npx skills add expo/skills
```
