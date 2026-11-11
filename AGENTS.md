# AGENTS.md - Codex entrypoint for the Stream skill pack

This repository contains the Stream skill pack. Skill source lives under `skills/`.

**Router:** [`skills/stream/SKILL.md`](skills/stream/SKILL.md) - Stream overview, CLI discovery, and routing to platform skills. SDK documentation is available through `getstream docs`. Each platform skill contains its own integration guidance and supporting files.

## Sub-skills

| Sub-skill | Use for |
|---|---|
| [`skills/stream-react/SKILL.md`](skills/stream-react/SKILL.md) | **Default for web React/Next.js.** Scaffold, enhance, audit, or migrate a React/Next.js app with Chat/Video/Feeds/Moderation, including AI assistants and agentic chat (`stream-chat-react/ai-components`, generative UI with A2UI / OpenUI) and apps built on Stream Agents |
| [`skills/stream-react-native/SKILL.md`](skills/stream-react-native/SKILL.md) | Build, integrate, audit, or upgrade Stream Chat/Video/Feeds in React Native or Expo apps, including AI assistants (`stream-chat-react-native/ai-components`) and apps built on Stream Agents, design matching, and Sendbird migration |
| [`skills/stream-swift/SKILL.md`](skills/stream-swift/SKILL.md) | Build or integrate Stream Chat/Video/Feeds in Swift/SwiftUI/UIKit/iOS apps, including AI assistants and agentic chat (StreamChatAI) |
| [`skills/stream-android/SKILL.md`](skills/stream-android/SKILL.md) | Build or integrate Stream Chat/Video/Feeds in Android/Jetpack Compose apps, including AI assistants and agentic chat (`stream-chat-android-ai-compose`) |
| [`skills/stream-flutter/SKILL.md`](skills/stream-flutter/SKILL.md) | Build or integrate Stream Chat, Video, and Feeds in Flutter apps (stream_chat_flutter, stream_chat_flutter_core, stream_video_flutter, stream_feeds) |
| [`skills/stream-unity/SKILL.md`](skills/stream-unity/SKILL.md) | Build or integrate Stream Chat and Stream Video in Unity Engine projects (C#). Chat + Video - no Feeds SDK for Unity |
| [`skills/stream-unreal/SKILL.md`](skills/stream-unreal/SKILL.md) | Build or integrate Stream Chat in Unreal Engine 5.7/5.8 projects (C++ and Blueprint). Chat only - no Video or Feeds SDK for Unreal |
| [`skills/stream-feeds-migration/SKILL.md`](skills/stream-feeds-migration/SKILL.md) | Generate the v2 -> v3 Activity Feeds sync mapping by sampling the v2 app's live activities and reactions, and by reading the app's v2 integration code when it is available. No CLI and no project required - it emits a config object |

For Sendbird data migration, use the shared [`skills/stream/sendbird-data-migration.md`](skills/stream/sendbird-data-migration.md) runbook.

---

## Working on this repository

- Keep skill instructions focused on workflows, observed integration pitfalls, command/docs pointers, and concrete verification. Use plain wording.
- Use `getstream -h`, `getstream <command> -h`, and `getstream docs` for CLI and SDK reference details. Avoid duplicating that material in skills.
- Tool permissions belong to the agent harness; avoid adding approval scripts or permission rules to skill prose.
- In skill instructions, refer to files within the same skill by raw relative path: "Read migration.md".
- For a file in another skill, name the skill and path: "Read stream skill's migration.md".
- For another skill's SKILL.md, name only the skill: "Refer to stream skill".
- `getstream skills` installs every skill under `skills/` into the user's project, next to the skills they keep there. Name a new skill `stream-<name>` so it never collides with one of theirs.
- When moving or removing skill files, update their callers, the skills table in README.md, and the contents list in CONTRIBUTING.md, then check local links. Run affected helper scripts when needed to verify behavior and report what was checked.
- **ASCII only:** all files in this repo must contain ASCII characters only. No em/en dashes, smart quotes, ellipsis chars, arrows, checkmarks, or other non-ASCII glyphs - use plain ASCII equivalents (`-`, `'`, `"`, `...`, `->`, `OK`, etc.).

Installation instructions are in [`README.md`](README.md#install).
