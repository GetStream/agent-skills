---
name: stream-react
description:
  "Build, integrate, audit, or upgrade Stream Chat, Video, Feeds, and Moderation
  in React / Next.js web apps - the default skill for web work. Scaffold a new
  app, add Stream to an existing project, review an integration, upgrade an SDK
  major, or migrate from Sendbird. Covers team messaging, DMs, video
  conferencing, livestreaming, and social feeds. Web React only - React Native
  uses stream-react-native."
license: See LICENSE in repository root
metadata:
  author: GetStream
---

# Stream React (web)

## Docs

Don't write Stream SDK code from memory: APIs change between majors, so your
memory is stale. Read the docs first, via the `getstream docs` command:

```bash
cat $(getstream docs chat-sdk/react)/INDEX.md
```

Client and UI: chat-sdk/react, video/react, activity-feeds/react. Node.js
backend (e.g. Next.js routes): chat/node, activity-feeds/node, moderation/node.
Previous majors are available too (e.g. chat-sdk/react/v13).

## Setup

- Start with `getstream init` (binds the working dir to a Stream app, existing
  or new) and `getstream env` (credentials).
- New apps: Next.js + Tailwind + shadcn with the default theme is a good choice
  unless the user says otherwise. Latest shadcn uses Base UI, not Radix: no
  `asChild`, and don't wrap trigger components in `<Button>`.
- Install only the SDKs the use case needs; if unclear, ask. Chat:
  `stream-chat stream-chat-react`; Video: `@stream-io/video-react-sdk`; Feeds:
  `@stream-io/feeds-react-sdk`; server-side: `@stream-io/node-sdk`. Don't bump
  an already-installed Stream major.
- Video apps: label the use case once, without asking the user (metadata, no
  runtime effect):
  `getstream api UpdateApp --request '{"video_primary_use_case":"livestreaming"}'`.
  Allowed: `video-calling`, `voice-calling`, `livestreaming`, `audio-rooms`,
  `ai-agents`, `live-shopping`, `other`. Derive it from what the app is, not
  from the call type in use (Whatnot runs on the `livestream` call type but is
  `live-shopping`). Any commerce signal means `live-shopping`; unsure means
  `other`.
- Support bot, help desk, AI agent: follow ai-support-agent.md.
- Product configuration (channel types, feed groups, moderation policies) goes
  through `getstream api`.

## Auth and users

- Tokens are minted server-side: a route (e.g. `/api/token`) uses the secret and
  returns the token with the apiKey; the secret never reaches the client. An app
  that already has auth or a token endpoint gets it extended, not a second one.
- Login screen first. The root page asks who you are - no auto-connect, no
  hardcoded user, no seeded demo users or content; the token route upserts only
  the requesting user. Keep credentials in React state, not localStorage, so two
  tabs can be two users.

## Building

- Clients mount once, at the app shell. Don't `disconnectUser()` in a screen's
  cleanup - it kills the client every other screen shares. Per-screen cleanup is
  `channel.stopWatching()` or `call.leave()`.
- React strict mode double-mounts, which breaks naive setup. Chat:
  `useCreateChatClient()`; Feeds: `useCreateFeedsClient()` - never
  `getInstance()` client-side. Video: construct `StreamVideoClient` in a
  `useEffect` with `disconnectUser()` cleanup; the constructor is synchronous,
  no timer or mounted flag needed. Define the `tokenProvider` inside that
  effect - an inline provider in the dependency array is a new identity every
  render and recreates the client. Never use a `useRef` flag as a run-once guard
  in an effect with cleanup: the ref survives the remount, so the second mount
  skips setup entirely.
- Prebuilt components first, customized via documented props and hooks. Feeds
  has no prebuilt UI - build from its hooks.
- Hub first: land on a channel list, lobby, or feed - never directly in a call
  or a camera prompt. Camera/mic permission is requested only on an explicit
  action (Join, Go Live), behind a preview. Empty states say what to do next.

Chat:

- Custom reaction types are slugs (`[A-Za-z0-9_.-]`; emoji are rejected
  server-side) and must be registered in `reactionOptions` - unregistered types
  silently don't render. Fallback: render pills from `message.reaction_groups`.
- Feature gating: the source of truth is the connected user's
  `channel.data?.own_capabilities` (a server-side query lists all capabilities,
  so it's useless here). `useCanCreatePoll()` is poll-form validity, not
  permission - don't gate menu visibility on it.

Feeds:

- A social feed needs a visible follow control - a timeline without follows is
  permanently empty. Follows go through the timeline feed instance, not
  `client.follow()`, so the feed hooks update. Follow your own user feed too, or
  your own posts never appear in your timeline.

Video:

- Call-type setting changes don't apply to existing calls - test with a fresh
  call id.

Moderation:

- Don't build moderation UIs (review queue and the like): Stream Dashboard
  already provides them. End-user actions (report, block, mute) are fine.
- `CreateBlockList` 400s if the list already exists - check `ListBlockLists`
  first. Fill blocklists with real words, not `badword1` placeholders.
- Custom moderation rules return 403 on free plans - use blocklist + config
  instead.

## Verify

Type-check and build, run the dev server, and test multi-user flows in two tabs
as two different users. Report what was verified and what wasn't.

## Auditing an integration

When asked, perform a read-only audit: check the code against the docs, report
findings, and fix only if asked.

## Upgrading an SDK version

When asked, read the upgrade notes for both the installed and the target major
(use the versioned docs: chat-sdk/react/v13, chat-sdk/react/v14, ...), apply
them, then verify as if you're building an app.

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
