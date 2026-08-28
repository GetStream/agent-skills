---
name: stream
description:
  "Stream overview, CLI, and router for Chat, Video, Feeds, and Moderation. Use
  for any Stream task: building or integrating Stream into web, iOS, Android,
  React Native, Flutter, Unity, or Unreal apps, querying Stream data, running
  getstream CLI commands, looking up Stream SDK docs, or migrating (from
  Sendbird, or Feeds v2 to v3). Routes to the right skill."
license: See LICENSE in repository root
metadata:
  author: GetStream
---

# Stream

Stream (getstream.io) provides APIs and SDKs for adding Chat, Video (calls and
livestreaming), Activity Feeds, and Moderation to apps. A Stream account has
organizations; an organization has apps; an app has one or more API key + secret
pairs. All data - users, channels, calls, feeds - is scoped to an app. Client
SDKs cover React, iOS, Android, React Native, Flutter, Unity, and Unreal;
server-side SDKs mint user tokens and call the same API. Most client SDKs
provide UI kits.

## The CLI

The `getstream` CLI is the base tool for everything account- and data-side:
authenticating, onboarding a project (org, app, credentials), calling any API
endpoint, obtaining credentials, minting user tokens, reading the docs, and
installing the other Stream skills. Don't work from memory of it - run
`getstream -h` and `getstream <command> -h` and follow what they print.

To install (unless already present):

```bash
curl -fsSL https://getstream.io/cli.sh | bash
getstream --version
```

Alternatively, the user can install the CLI from getstream.io/cli.

## Routing

First match wins:

1. **Work on an app for a specific platform** (build, integrate, audit,
   upgrade): use the platform-specific skill.
   - stream-react (React / Next.js)
   - stream-react-native (React Native / Expo)
   - stream-swift (iOS / SwiftUI / UIKit)
   - stream-android (Kotlin / Compose)
   - stream-flutter
   - stream-unity (Chat and Video)
   - stream-unreal (Chat only)

   Install a missing skill with `getstream skills <name>`, then follow it. For a
   web app, or a generic app, pick stream-react. A framework beats an OS: "an
   Unreal chat app for iOS" is stream-unreal.

2. **Migrate Feeds v2 to v3:** use stream-feeds-migration skill.
3. **Migrate from Sendbird:** use the platform-specific skill to migrate the
   code; to move the data itself (users, channels, message history), read
   sendbird-data-migration.md.
4. **Docs / "how does X work" questions:** use the `getstream docs` command.
5. **Query or mutate app data** ("list channels", "any flagged messages?",
   one-off API calls): use the `getstream api` command.
6. **Genuinely ambiguous:** ask.
