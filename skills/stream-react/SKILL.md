---
name: stream-react
description: "Build, integrate, audit, or upgrade Stream Chat, Video, Feeds, and Moderation in React / Next.js web apps - the default skill for web work. Scaffold a new app, add Stream to an existing project, review an integration, upgrade an SDK major, or migrate from Sendbird. Covers team messaging, DMs, video conferencing, livestreaming, and social feeds. Web React only - React Native uses stream-react-native."
license: See LICENSE in repository root
metadata:
  author: GetStream
---

# Stream React (web)

## Docs

Don't write Stream SDK code from memory - APIs move between majors (e.g. chat v14
replaced `MessageInput` with `MessageComposer`). The docs are local:
`getstream docs list`, then read the INDEX.md of the matching id and the pages it names:

```bash
cat $(getstream docs chat-sdk/react)/INDEX.md
```

Ids for this skill: `chat-sdk/react`, `video/react`, `activity-feeds/react` for the UI;
`chat/node`, `activity-feeds/node`, `moderation/node` for the Next.js backend.

## Flow

**1. Init.** `getstream init` - authenticates, selects or creates the org and app, writes
project credentials. Its prompts are the only pause. If the app will use Feeds, pick a
Feeds v3 region when offered.

**2. Scaffold** - new apps only. Next.js + Tailwind + shadcn, default theme, avoid
overrides. The
scaffolder wants to create its own directory, so scaffold into `.scaffold/` and move
everything up; `-n .scaffold` also lands in `package.json` as the package name, which npm
rejects (names can't start with `.`), so rewrite it:

```bash
npx shadcn@latest init -t next -b base -n .scaffold --no-monorepo && mv .scaffold/* .scaffold/.* . 2>/dev/null; rm -rf .scaffold && node -e "const fs=require('fs'),path=require('path'),j=require('./package.json');j.name=path.basename(process.cwd()).toLowerCase().replace(/[^a-z0-9._-]+/g,'-').replace(/^[._-]+/,'')||'app';fs.writeFileSync('package.json',JSON.stringify(j,null,2)+'\n')"
```

Add shadcn components as the UI needs them (`npx shadcn@latest add button card avatar ...`).
Note: shadcn here uses **Base UI, not Radix** - `asChild` doesn't exist; pass `className`
to trigger components directly and don't wrap them in `<Button>`.

**3. Credentials.** `getstream env`.

**4. SDKs.** Install only what the use case needs, with `--legacy-peer-deps` (npm; in an
existing project, its own package manager). Never bump an already-installed Stream major
as a side effect - build against the installed major's docs (e.g. `chat-sdk/react/v13`):

- Chat: `stream-chat stream-chat-react`; Video: `@stream-io/video-react-sdk` -
  Feeds: `@stream-io/feeds-react-sdk`; server: `@stream-io/node-sdk`

**5. Configure.** Product setup (channel types, feed groups, moderation policies) via
`getstream api` - endpoint shapes from `getstream api -h` and the docs, not memory.
Moderation is configured here and reviewed in the Stream Dashboard: never build a review
queue / flagged-item UI in the app. End-user actions (report, block, mute) are fine.
Gotchas: `CreateBlockList` 400s if the list already exists - check `ListBlockLists` first,
and fill blocklists with real words, not `badword1` placeholders. Custom moderation rules
return 403 on free plans - use blocklist + config instead. Call-type setting changes don't
apply to existing calls - test with a fresh call id.

For Video apps, also label the app's use case once (metadata, no runtime effect - set it
automatically, don't ask):

```bash
getstream api UpdateApp --request '{"video_primary_use_case":"livestreaming"}'
```

Allowed values, hard-coded (don't discover via `--schema`): `video-calling`,
`voice-calling`, `livestreaming`, `audio-rooms`, `ai-agents`, `live-shopping`, `other`.
Derive it from what the app *is*, not from the call type in use - many apps run on the
`livestream` call type without being livestreaming apps (Whatnot: `livestream` call type,
`live-shopping` label). Any commerce signal (TikTok Shop, auctions) means `live-shopping`;
when unsure, `other`.

**6. Build.** Read the docs first (section above), then:

Products by use case - build only what the user asked for; if unclear, ask:

| Sounds like | Use case | Products |
|---|---|---|
| Twitch, YouTube Live | Livestreaming | Video + Chat + Feeds |
| Zoom, Meet | Video conferencing | Video [+ Chat] |
| Slack, Discord | Team messaging | Chat |
| WhatsApp, iMessage | Direct messaging | Chat [+ Video] |
| Instagram, X | Social feed | Feeds + Chat |
| Support bot, help desk, AI agent | AI support agent | Chat + an LLM - follow [`ai-support-agent.md`](ai-support-agent.md) |

App shape:
- **Login screen first.** The root page asks who you are - never auto-connect or hardcode
  a user. Keep credentials in React state, not localStorage, so two tabs can be two users.
  Never seed demo users or content; the token route upserts only the requesting user. An
  app with existing auth keeps it - wire Stream tokens into its session instead.
- **Tokens are minted server-side.** A route (e.g. `/api/token`) uses the secret to mint
  the user's token(s) and returns them with the apiKey; the secret never reaches the
  client. An app that already has a token endpoint gets it extended - never a second one.
- **Clients mount once, at the app shell.** Per-screen cleanup is `channel.stopWatching()`
  or `call.leave()` - never `disconnectUser()` on screen unmount; it kills the client every
  other screen shares.
- **Hub first.** Land on a home screen (channel list, lobby, feed) - never directly in a
  call or camera prompt. Camera/mic permission is requested only on an explicit action
  (Join, Go Live), behind a preview. Empty states say what to do next.
- **Prebuilt components first.** Compose the SDK's prebuilt components and customize via
  documented props/hooks; Feeds has no prebuilt UI - build from its hooks. A social feed
  needs a visible follow control (a timeline without follows is permanently empty), and
  follows go through the timeline feed instance - not `client.follow()` - so the feed
  hooks update. Follow your own user feed too, or your own posts never appear in your
  timeline.

React strict-mode wiring (double-mount breaks naive setup):
- Chat: `useCreateChatClient()`; Feeds: `useCreateFeedsClient()` - never
  `getInstance()` client-side (server-side `getInstance` is fine).
- Video: construct `StreamVideoClient` in a `useEffect` with `disconnectUser()` cleanup -
  the constructor is synchronous, no timer or mounted flag needed. Define the
  `tokenProvider` inside that effect: an inline provider listed in the dependency array is
  a new identity every render and recreates/disconnects the client.
- Never use a `useRef` flag as a run-once guard in effects that have cleanup: the ref
  survives strict mode's unmount/remount, so the second mount skips setup entirely.

Traps the docs don't state:
- Custom reaction types are slugs (`[A-Za-z0-9_.-]`; emoji characters are rejected
  server-side) and must be registered in `reactionOptions` - unregistered types silently
  don't render. Fallback: render pills from `message.reaction_groups`.
- Features gate silently on the channel type's flags and the user's capabilities - no
  error, no warning. Diagnose from the connected user's `channel.data?.own_capabilities`
  (a server-side query shows an inflated admin set). `useCanCreatePoll()` is poll-form
  validity, not permission - never gate menu visibility on it.

**7. Verify.** `npx tsc --noEmit` first - it reports all type errors in one pass, while
`next build` stops at the first error per file. Then `npx next build`. On a non-Next.js
React project, use its own build command, and the token route lives in its backend.

**8. Run.** Start the dev server in the background and summarize: org/app, what was
created, the URL - and suggest opening two tabs with different usernames to test
multi-user flows.

## Auditing an integration

Read-only: check the code against the docs, report findings, and fix only if asked.

## Upgrading an SDK version

Read the upgrade notes for both the installed and the target major (versioned docs ids:
`chat-sdk/react/v13`, `chat-sdk/react/v14`, ...), apply them, then verify as in step 7.

## Matching a reference design

When the request carries a target appearance - a screenshot, a Figma frame, "make it look
like WhatsApp" - follow [`design-matching.md`](design-matching.md).

## Migrating from Sendbird

For the code migration, follow [`sendbird-migration.md`](sendbird-migration.md). When the
user also wants their existing data moved (users, channels, message history), follow the
`stream` skill's `sendbird-data-migration.md`.
