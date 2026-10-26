---
name: stream
description:
  "Stream overview, CLI, and router for Chat, Video, Feeds, Moderation, and
  Agents. Use for any Stream task: building or integrating Stream into web, iOS,
  Android, React Native, Flutter, Unity, or Unreal apps, building voice or text
  AI agents with Stream Agents, querying Stream data, running
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

Stream Agents runs voice and text AI agents on Stream's backend. An agent is a
folder of plain files (`agents/<name>/agent.yaml`, instructions, guardrail,
knowledge, skills, simulations) synced with `getstream agents`, and sessions
with it are opened through the Agents SDKs (`@stream-io/calypso` on the web). A
session's conversation is a Chat channel and its voice is a Video call, so the
app around an agent is a Chat and Video app like any other.

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

The `getstream agents` commands are only in beta builds, whose version is a
date and a commit (`YYYY-MM-DD-<commit>`) rather than semver. A stable build
answers them with "agents unavailable". Install the beta over it:

```bash
curl -fsSL https://getstream.io/cli/beta/install.sh | bash
```

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

   For a review or audit of an existing integration ("is this ready for
   production?", "prepare for the integration review"), read
   integration-review.md together with the platform skill.

   Install a missing skill with `getstream skills <name>`, then follow it. For a
   web app, or a generic app, pick stream-react. A framework beats an OS: "an
   Unreal chat app for iOS" is stream-unreal.

   An app built around Stream Agents is platform work too, even when the request
   only says "agent" or "voice agent". Configure the agent from its folder and
   `getstream docs agents/<sdk>` (`javascript`, `ios`, `android`, `flutter`),
   and build the app with the platform skill: its Chat UI kit renders the
   session's conversation and its Video SDK holds the call. React Native, Unity,
   and Unreal have no Agents client SDK - tell the user before building.

2. **Migrate Feeds v2 to v3:** use stream-feeds-migration skill.
3. **Migrate from Sendbird:** use the platform-specific skill to migrate the
   code; to move the data itself (users, channels, message history), read
   sendbird-data-migration.md.
4. **Docs / "how does X work" questions:** use the `getstream docs` command. In
   a command substitution like `$(getstream docs <id>)` don't add `2>&1`. The
   path you need is on stdout.
5. **Query or mutate app data** ("list channels", "any flagged messages?",
   one-off API calls): use the `getstream api` command.
6. **Genuinely ambiguous:** ask.
