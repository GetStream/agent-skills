# Stream for AI coding agents

Build with [Stream](https://getstream.io) Chat, Video, Feeds, and Moderation from your AI coding agent. The skills scaffold new apps and add Stream to existing React / Next.js, React Native, Swift/iOS, Android, Flutter, Unity, and Unreal projects. The Stream MCP server signs in with your Stream account and lets the agent list your apps and call the Stream API on them.

Full documentation lives at [getstream.io/agent-skills](https://getstream.io/agent-skills/) - start with the [Quickstart](https://getstream.io/agent-skills/docs/quickstart/), or read up on [how the skills compare to MCP](https://getstream.io/agent-skills/docs/concepts/skills-vs-mcp/).

## Install

### Claude Code

```
/plugin marketplace add GetStream/agent-skills
/plugin install getstream@getstream
```

Then run `/mcp` and sign in to the `getstream` server.

### Cursor

Open **Customize**, search for Stream, and select **Install**. Sign in to the `getstream` MCP server when Cursor asks.

### Any agent, with the Stream CLI

Install the [Stream CLI](https://getstream.io/agent-skills/docs/installation/), then run:

```bash
getstream skills
```

With no arguments, it installs every skill below. To install a subset, name the platform skills, such as `getstream skills stream-react stream-swift`; the `stream` skill and its compatibility entrypoints come with them. Run `getstream skills -h` for installation options. To set up a project (auth, org/app selection, credentials), run `getstream init`.

Step-by-step instructions are in the [installation guide](https://getstream.io/agent-skills/docs/installation/).

## Skills

Use `/stream` for generic routing, or invoke a skill directly by name. Each skill name links to its reference page on the docs site.

| Skill | Use for |
|---|---|
| [`/stream`](https://getstream.io/agent-skills/docs/skills/stream/) | Start here: routes requests to the right skill, and runs `getstream` CLI commands for data queries, app config, and onboarding |
| [`/stream-react`](https://getstream.io/agent-skills/docs/skills/stream-react/) | React / Next.js web apps, the default for web work: build, add Stream, audit, upgrade SDKs, migrate from Sendbird, add AI assistants, and build Stream Agents voice and text agents |
| [`/stream-swift`](https://getstream.io/agent-skills/docs/skills/stream-swift/) | Swift, SwiftUI, UIKit, and iOS apps |
| [`/stream-android`](https://getstream.io/agent-skills/docs/skills/stream-android/) | Android and Jetpack Compose apps |
| [`/stream-react-native`](https://getstream.io/agent-skills/docs/skills/stream-react-native/) | React Native CLI and Expo apps: Chat, Video, and Feeds - build, add Stream, audit, upgrade SDKs, migrate from Sendbird, and add AI assistants |
| [`/stream-flutter`](https://getstream.io/agent-skills/docs/skills/stream-flutter/) | Flutter apps: Chat, Video, and Feeds, plus AI assistants and Stream Agents voice and text agents |
| [`/stream-unity`](https://getstream.io/agent-skills/docs/skills/stream-unity/) | Unity projects (C#): Chat and Video, no Feeds |
| [`/stream-unreal`](https://getstream.io/agent-skills/docs/skills/stream-unreal/) | Unreal Engine 5.7/5.8 projects (C++ and Blueprint): Chat only |
| `/stream-feeds-migration` | Feeds v2 -> v3 migration: generates the sync mapping from your app's live data |
| `/stream-security-audit` | Security audit of an SDK or library, Stream's or any other: 148 explicit checks, verified findings, a calibrated report and a coverage ledger |

`stream-builder` and `stream-docs` remain for older CLI installations and forward to the skills above.

## What your agent can do

- **Scaffold a full app** - Next.js + Tailwind + Stream SDKs, wired end-to-end in one shot (`/stream-react`)
- **Add products to existing apps** - drop Chat, Video, or Feeds into a project that's already running (`/stream-react`)
- **Audit and migrate integrations** - review a Video integration against best practices, upgrade an SDK version from the live release guide, or migrate an existing Sendbird app to Stream Chat React (`/stream-react`)
- **Build and extend Swift apps** - wire Stream into SwiftUI or UIKit Xcode projects with iOS-specific setup patterns (`/stream-swift`)
- **Build and extend Android apps** - wire Stream into Jetpack Compose Android Studio / Gradle projects with Android-specific setup patterns (`/stream-android`)
- **Build and extend React Native apps** - wire Stream Chat, Video, or Feeds into Expo or RN CLI projects, match a design, or migrate from Sendbird (`/stream-react-native`)
- **Build and extend Unity games** - wire Stream Chat and Stream Video into a Unity project, build the chat and call UI on UGUI or UI Toolkit (neither SDK ships components), and get the player settings right for Android, iOS, desktop, or WebGL (`/stream-unity`)
- **Build and extend Unreal Engine games** - wire Stream Chat into UE 5.7/5.8 C++ or Blueprint projects, drop in the shipped UMG chat widgets, and package for mobile or desktop (`/stream-unreal`)
- **Plan a Feeds v2 -> v3 migration** - sample your v2 app's real activities and reactions and get back the sync `mapping` object, with the keys it deliberately left at their defaults (`/stream-feeds-migration`)
- **Security-audit an SDK** - walk 148 explicit checks (secrets in code and git history, token lifetime and logging, transport, untrusted content and LLM output, local data, crashes, CI and supply chain), verify each finding, and get a report that separates what is proven from what depends on the backend (`/stream-security-audit`)
- **Query live data** - "any active calls?", "show flagged messages", "list my channels" - natural language to the `getstream` CLI (`/stream`)
- **Configure apps and moderation** - channel types, roles, permissions, blocklists, automod - via the `getstream` CLI (`/stream`)
- **Answer SDK questions** - token patterns, strict mode, client/server instantiation, theme wiring (`/stream` or the relevant platform skill)
- **Look up SDK docs** - use `getstream docs` for the relevant product, framework, and version

## What gets installed

Skills are Markdown instructions and supporting files, including helper scripts where needed. The Stream MCP server is hosted by Stream at `https://mcp.getstream.io/mcp`.

The plugins do not include the `getstream` CLI, which skills use for data queries, app config, and SDK docs (`getstream docs`). When a skill needs it and it is not installed, the `stream` skill asks you, then installs a fixed version from npm (`npm install -g @stream-io/cli@1.12.1`, which needs Node.js 22.15 or newer). Without that, it asks you to install the CLI from [getstream.io/cli](https://getstream.io/cli) yourself. It also asks before updating a CLI that is too old. Stream Agents work needs the beta CLI, which the skill installs with Stream's install script (`curl -fsSL https://getstream.io/cli/beta/install.sh | bash`) after asking you. Tool permissions are managed by your agent harness.

## Network access and privacy

The skills and plugins connect to:

- **Stream MCP server** (`mcp.getstream.io`), once you sign in with your Stream account.
- **Stream API**, through the `getstream` CLI.
- **Docs and SDK source**: skills fetch Stream SDK docs from `getstream.io` and `getstream.github.io`, SDK source, releases and migration guides from Stream's repositories on GitHub (`github.com`, `api.github.com`, `raw.githubusercontent.com`), and Flutter package pages from `pub.dev`. Nothing from your project is sent in these requests.
- **Package versions and installs**: skills look up current SDK versions on Stream's Maven repository (`stream-io-repo.com`), `dl.google.com` and the npm registry. The apps they build install dependencies from the registries those apps already use (npm, Maven including `jitpack.io`, Swift packages on GitHub, `pub.dev`). The React design check can install Playwright and its Chromium build into a scratch folder.
- **Feeds migration**: when a sample is needed, the skill writes a temporary `fetch_sample.py` into the working directory and deletes it after the run. That script reads `STREAM_API_KEY` and `STREAM_API_SECRET` from the environment, signs a short-lived token with the secret on your machine, and reads activities from the Stream v2 API (`api.stream-io-api.com`). The secret itself is never sent. The script is not part of the plugin.
- **Sendbird data migration**: only when you ask for one, the `stream` skill reads your users, channels and messages from the Sendbird Platform API with your Sendbird API token, keeps the export on disk and uploads it to Stream with `getstream import`.
- **Stream Agents**: `getstream agents sync` uploads the agent folder you are working on (its configuration, instructions and knowledge files) to Stream.
- **Dev tunnels**: an AI support agent that replies from a webhook needs a public URL in development. If you choose the webhook trigger, the skill runs a `cloudflared` or ngrok tunnel to your local dev server, and Stream's webhook calls, which carry chat messages, pass through that provider.

- **Security audit**: the skill reads the audited code locally and sends nothing to Stream. It writes a temporary recon script to a scratch directory outside the repository and deletes it when the audit ends; the script is not part of the plugin. Dependency advisory checks send package names and versions to public advisory databases (OSV, GitHub Security Advisories, the ecosystem's audit command), and the skill asks first when dependencies are private. It never sends exploit traffic to live services.

Stream's [privacy policy](https://getstream.io/legal/privacy/) covers the data sent to Stream.

## Contributing

How the skills route requests, the repository layout, and how to check the plugin are in [`CONTRIBUTING.md`](CONTRIBUTING.md).
