---
name: stream
description:
  "Stream overview, CLI, and router for Chat, Video, Feeds, Moderation, and
  Agents. Use for any Stream task: building or integrating Stream into web, iOS,
  Android, React Native, Flutter, Unity, or Unreal apps, building voice or text
  AI agents with Stream Agents, querying Stream data, running getstream CLI
  commands, looking up Stream SDK docs, migrating (from Sendbird, or Feeds v2 to
  v3), or security-auditing an SDK or library. Routes to the right skill."
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

You can build and run AI agents with Stream Agents.

## The CLI

The `getstream` CLI is the base tool for everything account- and data-side:
authenticating, onboarding a project (org, app, credentials), calling any API
endpoint, obtaining credentials, minting user tokens, reading the docs, and
installing the other Stream skills. Don't work from memory of it - run
`getstream -h` and `getstream <command> -h` and follow what they print.

If the `getstream` command is missing, ask the user before installing it:

```bash
curl -fsSL https://getstream.io/cli.sh | bash
getstream --version
```

Alternatively, the user can install the CLI from getstream.io/cli. Ensure the
CLI is up-to-date with `getstream update`.

`getstream init` and `getstream login` can open a browser for a user to sign in,
even in non-interactive terminals. Check login with `getstream status`. Use
`getstream login --guest` (a temporary account an agent can use) only with the
user's OK.

## Routing

First match wins:

1. **Build an AI agent.** Refer to `getstream docs agents`. Quickstart and index
   are good starting points.

2. **Work on an app for a specific platform** (build, integrate, audit,
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
   integration-review.md together with the platform skill. A security audit of
   SDK or library code itself (find vulnerabilities, threat-model it, re-check a
   security report), for Stream's SDKs or any other, is not integration work:
   use stream-security-audit skill.

   Install a missing skill with `getstream skills <name>`, then follow it
   (`getstream skills` alone installs every skill; an older CLI installs only
   stream, stream-builder and stream-docs, so `getstream update` first). For a
   web app, or a generic app, pick stream-react. A framework beats an OS: "an
   Unreal chat app for iOS" is stream-unreal.

   AI work is the exception to that default. When the request names an AI
   feature (AI Components, an AI assistant, a voice agent, generative UI) but no
   platform, and the working directory doesn't show one (an `.xcodeproj`, a
   `build.gradle`, a `pubspec.yaml`, a `package.json`), ask which platform
   before routing. The AI components differ by platform, so a build started on
   the wrong one is thrown away.

   An app built around Stream Agents is platform work too, even when the request
   only says "agent" or "voice agent". Read the Agents docs with
   `getstream docs agents`: one doc set for every SDK, where each page has the
   code for every language (there are no `agents/<sdk>` ids). Configure the
   agent from its folder. A folder from `getstream agents init --template` is an
   example agent for "Acme Corp": replace its `agent.yaml` description,
   `instructions.md`, `guardrail.md`, `knowledge/`, `confirm` skill and
   simulations before the first sync. Build the app with the platform skill: its
   Chat UI kit renders the session's conversation and its Video SDK holds the
   call. React Native runs `@stream-io/stream-agents` for text agents, with no
   call-based voice (stream-react-native skill's stream-agents.md). Flutter runs
   the `stream_agents` Dart package for text and voice (stream-flutter skill's
   ai-integration.md). Unity and Unreal have no Agents client SDK - tell the
   user before building.

3. **Migrate Feeds v2 to v3:** use stream-feeds-migration skill.
4. **Migrate from Sendbird:** use the platform-specific skill to migrate the
   code; to move the data itself (users, channels, message history), read
   sendbird-data-migration.md.
5. **Docs / "how does X work" questions:** use the `getstream docs` command,
   with an id from `getstream docs list`. In a command substitution like
   `$(getstream docs <id>)` don't add `2>&1`. The path you need is on stdout. On
   a wrong id stdout is empty and the error goes to stderr, so a bare
   `ls $(getstream docs <id>)` lists the current directory instead. Check the
   result first: `d=$(getstream docs <id>) && ls "$d"`.
6. **Query or mutate app data** ("list channels", "any flagged messages?",
   one-off API calls): use the `getstream api` command.
7. **Genuinely ambiguous:** ask.
