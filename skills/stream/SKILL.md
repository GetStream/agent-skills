---
name: stream
description: "Stream overview, CLI, and router for Chat, Video, Feeds, and Moderation. Use for any Stream task: building or integrating Stream into web, iOS, Android, React Native, Flutter, Unity, or Unreal apps, querying Stream data, running getstream CLI commands, looking up Stream SDK docs, or migrating (from Sendbird, or Feeds v2 to v3). Routes to the right skill."
license: See LICENSE in repository root
metadata:
  author: GetStream
---

# Stream

Stream (getstream.io) provides hosted APIs and SDKs for adding Chat, Video (calls and
livestreaming), Activity Feeds, and Moderation to apps. An account has organizations; an
organization has apps; an app has an API key and secret and holds all data - users,
channels, calls, feeds. Client SDKs cover React, iOS, Android, React Native, Flutter,
Unity, and Unreal; server-side SDKs mint user tokens and call the same API.

## The CLI

The `getstream` CLI is the base tool for everything account- and data-side: authenticating,
onboarding a project (org, app, credentials), calling any API endpoint, writing credentials
into a project, minting user tokens, reading local copies of the SDK docs, and installing
the other Stream skills. Don't work from memory of it - run `getstream -h` and
`getstream <command> -h` and follow what they print. If it isn't installed, ask the user to
install it from getstream.io.

## Routing

First match wins:

1. **Work on a platform app** (build, integrate, audit, upgrade) -> the platform skill:
   `stream-swift` (iOS / SwiftUI / UIKit), `stream-android` (Kotlin / Compose),
   `stream-react-native` (RN / Expo), `stream-flutter`, `stream-unity` (Chat + Video),
   `stream-unreal` (Chat only). Install a missing skill with `getstream skills <name>`,
   then follow it. An engine token beats an OS token - "an Unreal chat app for iOS" is
   `stream-unreal`. A game with no engine named: ask "Unity or Unreal?".
2. **Work on a web app, or no platform named** -> `stream-react`.
3. **Migrate Feeds v2 -> v3** (sync mapping, v3sync) -> `stream-feeds-migration`.
4. **Migrate from Sendbird** -> the platform skill owns the code swap (rows 1-2); to move
   the data itself (users, channels, message history), read
   [`sendbird-data-migration.md`](sendbird-data-migration.md).
5. **Docs / "how does X work" questions** -> the local docs: `getstream docs list`, then
   read the INDEX.md of the matching id.
6. **Query or change live data** ("list channels", "any flagged messages?", one-off API
   calls) -> handle here with `getstream api`.
7. **Genuinely ambiguous** -> ask one short question.
