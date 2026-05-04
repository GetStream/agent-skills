---
name: stream-react-native
description: "Build and integrate Stream Chat React Native v9 in React Native Community CLI and Expo apps. Use for React Native, Expo, Stream Chat RN, stream-chat-react-native, stream-chat-expo, v9 migration/setup, channel list, message list, MessageComposer, threads, thread list, React Navigation, Expo Router, theming, offline support, push notifications, and Chat customization. Chat only in v1; not for Stream Video, Feeds, or Moderation UI."
license: See LICENSE in repository root
compatibility: Requires an existing React Native CLI or Expo project with React Native New Architecture enabled for Chat RN v9. The `stream` CLI is the default credentials path; pasted API key and token are accepted as fallback.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(ls *), Bash(find . *), Bash(grep *),
  Bash(cat package.json), Bash(cat app.json), Bash(cat app.config.js), Bash(cat app.config.ts),
  Bash(cat babel.config.js), Bash(cat metro.config.js),
  Bash(command -v stream), Bash(stream token *), Bash(stream config *),
  Bash(stream --safe api *), Bash(stream api *),
  Bash(npm install *), Bash(yarn add *), Bash(pnpm add *), Bash(npx expo install *),
  Bash(npx pod-install *), Bash(cd ios && pod install)
---

# Stream React Native - skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session. Every non-negotiable React Native Chat rule is stated there.

This file is the single entrypoint: intent classification, local project detection, and module pointers for Stream Chat React Native v9 work.

---

## Step 0: Intent classifier (mandatory first - never skip)

Before any tool call, decide the track from the user's input alone. Do not probe the filesystem first.

### Signals -> track

| Signal in user input | Track |
|---|---|
| `React Native`, `Expo`, `Expo Router`, `stream-chat-react-native`, `stream-chat-expo`, `Stream Chat RN`, `Chat React Native`, `v9 migration` | **C - Reference lookup** if the user only asks how/docs; otherwise **B - Existing app** |
| Words "docs" or "documentation" around Stream Chat React Native / Expo work | **C - Reference lookup** |
| "How do I {X} in React Native/Expo?", "What does {SDK component/hook/prop} do?" | **C - Reference lookup** |
| "Build me a new React Native app", "create an Expo app" + Stream Chat | **A - New app** |
| "Add/integrate Stream Chat into this app", "wire Chat RN", "set up stream-chat-expo" | **B - Existing app** |
| "Install Stream packages", "set up Chat RN", "wire auth/token flow" with no broader feature request | **D - Bootstrap / setup** |
| Video, Feeds, Moderation review UI, or non-Chat Stream RN product | **Reject bundled scope** and route to live docs only if the user wants docs |
| Bare `/stream-react-native` with no args | List the tracks briefly and wait |

### Disambiguation flow

If the request is ambiguous between wiring code and reference lookup, ask one short question and wait:

> Do you want me to wire this into the project, or just map the React Native SDK pattern and files?

### Scope rejection

This v1 skill bundles **Chat React Native only**. If the user asks for Stream Video, Feeds, or Moderation UI in React Native, say:

> The React Native skill currently bundles Chat references only. I can help with Chat RN v9 here, or switch to live docs for Video/Feeds.

Do not invent missing React Native Video or Feeds API details from memory.

### After classification

- **Tracks A, B, D** -> run [`credentials.md`](credentials.md) once per session, then run Project signals and continue in [`builder.md`](builder.md) and [`sdk.md`](sdk.md).
- **Track C** -> skip credentials and project probes if the product + runtime are explicit. Only run a read-only probe if RN CLI vs Expo is ambiguous and the answer affects the guidance.

---

## Step 0.5: Credentials, token, and seed data (tracks A, B, D only)

Run [`credentials.md`](credentials.md) once per session, right after intent classification and before Project signals.

It resolves:

- Stream API key
- user id and display name
- user token or token provider plan
- optional seed channels via `UpdateUsers` and `GetOrCreateChannel`

If code work starts and credentials have not been resolved, return to [`credentials.md`](credentials.md) before editing Chat setup.

---

## Project signals (tracks A/B/D - once per session; Track C on demand only)

Read-only local probe. Use it to detect RN CLI vs Expo, New Architecture hints, navigation setup, and existing Stream packages.

```bash
bash -c 'echo "=== PACKAGE ==="; test -f package.json && grep -oE "\"(stream-chat-react-native|stream-chat-expo|react-native|expo|@react-navigation/[^\"]+|expo-router|react-native-reanimated|react-native-worklets|react-native-teleport|@op-engineering/op-sqlite)\": *\"[^\"]*\"" package.json 2>/dev/null; echo "=== EXPO ==="; find . -maxdepth 2 \( -name "app.json" -o -name "app.config.js" -o -name "app.config.ts" -o -path "./app/_layout.*" \) -print 2>/dev/null; echo "=== NATIVE ==="; find . -maxdepth 2 \( -name "ios" -o -name "android" \) -type d -print 2>/dev/null; echo "=== CONFIG ==="; find . -maxdepth 2 \( -name "babel.config.js" -o -name "metro.config.js" \) -print 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Hold the result in conversation context. Do not re-run unless the user changes directory, packages are installed, or the project shape changes.

Use the result to produce a one-line status, for example:

- `Expo app detected - stream-chat-expo absent - Expo Router present - ready for Chat setup`
- `RN CLI app detected - ios/android present - stream-chat-react-native installed - checking provider placement`
- `No React Native or Expo project found - user needs to create the app first`

If there is no RN/Expo project, do **not** scaffold one from this skill. Tell the user to create a React Native CLI or Expo app first, then continue.

---

## Module map

| Track | Module(s) |
|---|---|
| A - New app | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + Chat references |
| B - Existing app | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + Chat references |
| C - Reference lookup | [`sdk.md`](sdk.md) + relevant Chat reference files |
| D - Bootstrap / setup | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) |

---

## Reference layout

Shared React Native and Expo patterns live in **[`sdk.md`](sdk.md)**.

Chat-specific setup, gotchas, and UI blueprints live under **`references/`**:

- **Chat setup/reference:** [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md)
- **Chat screen/component blueprints:** [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md)

Future React Native product coverage should stay in this naming family instead of creating more top-level skills:

- `VIDEO-REACT-NATIVE.md`
- `FEEDS-REACT-NATIVE.md`

If the requested product file is not bundled yet, say so plainly and only switch to live docs if the user asks.

---

## Track A - New app

**Full detail:** [`builder.md`](builder.md) - use the new-project path.

| Phase | Name | What you do |
|---|---|---|
| **A1** | Detect | Run Project signals. If no RN/Expo app exists, tell the user to create one first. |
| **A2** | Choose lane | Resolve Expo vs RN CLI from project files; do not mix packages. |
| **A3** | Install + wire | Follow [`builder.md`](builder.md) + [`sdk.md`](sdk.md), then load Chat references. |
| **A4** | Verify | Confirm install, Babel plugin, root providers, auth, and first rendered Chat screen. |

---

## Track B - Existing app

**Full detail:** [`builder.md`](builder.md) - use the existing-project path.

| Phase | Name | What you do |
|---|---|---|
| **B1** | Detect | Run Project signals and inspect existing app structure before editing. |
| **B2** | Preserve | Keep Expo/RN CLI lane, package manager, navigation stack, and auth architecture unless asked to migrate. |
| **B3** | Integrate | Use [`sdk.md`](sdk.md), then load only the Chat reference/blueprint sections needed for the requested work. |
| **B4** | Verify | Confirm the requested Stream Chat flow builds and renders in the existing app. |

---

## Track C - Reference lookup

Load only the relevant files:

- Shared lifecycle / auth / provider / runtime patterns -> [`sdk.md`](sdk.md)
- Chat RN v9 setup and gotchas -> [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md)
- Chat RN screen/component structure -> [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md)

If the user asks for exact API details not bundled here, use the local docs at `~/Projects/docs/data/docs/chat-sdk/react-native/v9-latest` or the SDK source at `~/Projects/stream-chat-react-native/package/src`. Prefer those over memory.

---

## Track D - Bootstrap / setup

Use when the user wants package install and shared wiring more than a full feature build:

- detect RN CLI vs Expo
- install the correct Chat package and required peers
- add Reanimated/Worklets Babel plugin as the last plugin
- wrap the entry point with `GestureHandlerRootView`
- place `OverlayProvider` and `Chat` correctly
- wire `useCreateChatClient` or the app's backend token provider
- stop before product-specific UI if the user only asked for setup
