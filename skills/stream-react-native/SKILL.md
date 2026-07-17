---
name: stream-react-native
description: "Use when creating, building, or integrating Stream Chat, Stream Video, or Stream Feeds in React Native Community CLI or Expo apps - new RN/Expo Chat / Video / Feeds apps from scratch, existing-app integration, stream-chat-react-native, stream-chat-expo, @stream-io/video-react-native-sdk, @stream-io/feeds-react-native-sdk, useCreateFeedsClient, StreamFeeds, StreamFeed, activity feed, timeline feed, notification feed, for-you feed, useFeedActivities, useActivityComments, reactions, comments, follows, migration/setup, migrate or upgrade an SDK version, upgrade stream-chat-react-native to v9, v8 to v9, bump Stream version, channel list, message list, MessageComposer, attachment picker, image/file attachments, media picker, audio messages, threads, thread list, video call, livestream, audio room, ringing, CallContent, ParticipantView, React Navigation, Expo Router, theming, offline support, push notifications, and Chat / Video / Feeds UI customization. Not for Moderation review UI."
license: See LICENSE in repository root
compatibility: Supports new or existing React Native CLI and Expo apps running Stream Chat RN or Stream Video RN with React Native New Architecture. The `getstream` CLI is the default credentials and requested demo-data path; pasted API key and token are accepted as fallback.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  WebFetch(domain:getstream.io),
  WebFetch(domain:raw.githubusercontent.com),
  Bash(ls *), Bash(find . *), Bash(grep *), Bash(sips *),
  Bash(cat package.json), Bash(cat app.json), Bash(cat app.config.js), Bash(cat app.config.ts),
  Bash(cat babel.config.js), Bash(cat metro.config.js),
  Bash(command -v getstream), Bash(getstream *),
  Bash(npm view *), Bash(npm install *), Bash(yarn add *), Bash(pnpm add *),
  Bash(curl -Ls https://getstream.io/chat/docs/sdk/react-native/llms.txt),
  Bash(curl -Ls https://getstream.io/chat/docs/react-native/llms.txt),
  Bash(curl -Ls https://getstream.io/video/docs/react-native/llms.txt),
  Bash(curl -Ls https://getstream.io/activity-feeds/docs/react-native/llms.txt),
  Bash(npx create-expo-app@latest *), Bash(npx create-expo-app *),
  Bash(npx @react-native-community/cli@latest init *),
  Bash(npx expo install *), Bash(npx expo prebuild *), Bash(npx expo start *),
  Bash(npm run *), Bash(yarn *), Bash(pnpm *),
  Bash(npx pod-install *), Bash(cd ios && pod install)
---

# Stream React Native - skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session. Every non-negotiable React Native Chat, Video, and Feeds rule is stated there.

This file is the single entrypoint: intent classification, product selection, project detection, and module pointers for Stream Chat React Native, Stream Video React Native, and Stream Feeds React Native work.

---

## Step 0: Intent classifier (mandatory first - never skip)

Before any tool call, decide the track from the user's input alone. Do not probe the filesystem first.

### Signals -> track

| Signal in user input | Track |
|---|---|
| "Build/create/scaffold a new React Native app", "create an Expo app", "new Stream Chat RN app", "new Stream Video RN app", "new Stream Feeds RN app", empty directory + React Native/Expo Chat / Video / Feeds | **A - New app** |
| "Upgrade/migrate/bump a Stream SDK version", "upgrade stream-chat-react-native to v9", "migrate Chat RN to the new SDK", "v8 to v9", "bump Stream Video/Feeds", "Feeds v2 -> v3" | **M - Migrate / upgrade** |
| "Add/integrate Stream Chat into this app", "wire Chat RN", "set up stream-chat-expo", "add a video call", "wire Stream Video", "set up @stream-io/video-react-native-sdk", "add an activity feed", "wire Stream Feeds", "set up @stream-io/feeds-react-native-sdk", "change/customize this Chat / Video / Feeds UI" | **B - Existing app** |
| `React Native`, `Expo`, `Expo Router`, `stream-chat-react-native`, `stream-chat-expo`, `@stream-io/video-react-native-sdk`, `@stream-io/feeds-react-native-sdk`, `Stream Chat RN`, `Stream Video RN`, `Stream Feeds RN`, `Chat React Native`, `Video React Native`, `Feeds React Native`, migration | **C - Reference lookup** if the user only asks how/docs; otherwise **B - Existing app** |
| Explicit product/runtime token: `Chat React Native`, `Chat Expo`, `Video React Native`, `Video Expo`, `Feeds React Native`, `Feeds Expo` | **C - Reference lookup** |
| Words "docs" or "documentation" around Stream Chat, Stream Video, or Stream Feeds React Native / Expo work | **C - Reference lookup** |
| "How do I {X} in React Native/Expo?", "What does {SDK component/hook/prop} do?" | **C - Reference lookup** |
| "Audit/review/check an existing Stream **Video** integration against best practices", "is my video app production-ready?", "what am I missing before launch?" | **C - Reference lookup** (read-only) - run the **Integration best-practices audit** in [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md) |
| "Install Stream packages", "set up Chat RN", "set up Video RN", "set up Feeds RN", "wire auth/token flow" with no broader feature request | **D - Bootstrap / setup** |
| Stream Moderation review UI or any other non-Chat / non-Video / non-Feeds Stream RN product | **Reject bundled scope** and route to live docs only if the user wants docs |
| Bare `/stream-react-native` with no args | List the tracks briefly and wait |

### Disambiguation flow

If the request is ambiguous between wiring code and reference lookup, ask one short question and wait:

> Do you want me to wire this into the project, or just map the React Native SDK pattern and files?

If the user wants a new app but did not name Expo or RN CLI, default to Expo because it is the shortest successful path. Use RN CLI when the user asks for it or when native project constraints require it.

### Product classifier (after track is known)

Identify the product from the user's input or detected packages. Tracks A, B, and D all need the product before continuing; Track C selects the matching reference pair.

| Product signal | Product | References |
|---|---|---|
| `stream-chat-react-native`, `stream-chat-expo`, channel, message, MessageComposer, thread, attachment, offline support | **Chat** | [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md) + [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) |
| `@stream-io/video-react-native-sdk`, video call, livestream, audio room, ringing, CallContent, ParticipantView, screenshare, picture in picture | **Video** | [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md) + [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md) |
| `@stream-io/feeds-react-native-sdk`, `useCreateFeedsClient`, `StreamFeeds`, `StreamFeed`, activity feed, timeline feed, notification feed, for-you feed, `useFeedActivities`, `useActivityComments`, reactions, comments, follows, follow / unfollow, activity composer, `activityWithStateUpdates` | **Feeds** | [`references/FEEDS-REACT-NATIVE.md`](references/FEEDS-REACT-NATIVE.md) + [`references/FEEDS-REACT-NATIVE-blueprints.md`](references/FEEDS-REACT-NATIVE-blueprints.md) |
| Two or more products in one app (chat alongside a video call, feeds + chat, feeds + video, etc.) | **Combined** | Load only the reference pairs for the products in scope. Nest the providers (e.g. `<StreamVideo>` inside `<OverlayProvider><Chat>` inside `<StreamFeeds>`); do not place them as siblings. See [`RULES.md`](RULES.md) and the manifest-selected `/video/docs/react-native/advanced/chat-with-video.md` for the Chat + Video interop notes |

If the request is ambiguous between products, ask one short question and wait:

> Are you wiring Stream Chat (channels, messages), Stream Video (calls, livestream, audio rooms), or Stream Feeds (activity feed, timeline, comments, reactions, follows)? Or more than one in the same app?

### Scope rejection

This skill bundles **Chat, Video, and Feeds React Native**. If the user asks for Stream Moderation review UI or another non-bundled Stream RN product, say:

> The React Native skill currently bundles Chat, Video, and Feeds references. I can help with any combination of those here, or switch to live docs for other products.

Do not invent missing React Native Moderation API details from memory.

### After classification

- **Tracks A, B, D** -> run Project signals, then continue in [`builder.md`](builder.md) and [`sdk.md`](sdk.md). Run [`credentials.md`](credentials.md) before writing Chat, Video, or Feeds connection code or creating requested demo data.
- **Track M** -> Read [`migrate.md`](migrate.md) first; it fetches the live upgrade guide before any edit. Run Project signals for lane / package-manager / New-Architecture detection, but **skip credentials, provisioning, and the scaffold path** - it edits an existing project.
- **Track C** -> skip credentials and project probes if the product + runtime are explicit. Only run a read-only probe if RN CLI vs Expo is ambiguous and the answer affects the guidance.

---

## Step 0.5: Credentials, token, and demo data (tracks A, B, D only)

Use [`credentials.md`](credentials.md) once per session before writing code that connects to Stream Chat, Stream Video, or Stream Feeds.

It resolves:

- Stream API key
- user id and display name
- user token or token provider plan
- optional demo data, only when requested, via Stream CLI calls (Chat: `UpdateUsers`, `GetOrCreateChannel`, `SendMessage`; Video and Feeds do not require seed data because calls are ephemeral and activities can be posted at runtime)

For Track A, it is acceptable to scaffold the app first if the runtime or target directory must be resolved before credentials. Do not render a connected Chat, Video, or Feeds UI until credentials or a token-provider plan are resolved.

---

## Project signals (tracks A/B/D - once per session; Track C on demand only)

Read-only local probe. Use it to detect empty/new workspace, RN CLI vs Expo, New Architecture hints, navigation setup, and existing Stream packages.

```bash
bash -c 'echo "=== PACKAGE ==="; test -f package.json && grep -oE "\"(stream-chat-react-native|stream-chat-expo|@stream-io/video-react-native-sdk|@stream-io/feeds-react-native-sdk|@stream-io/react-native-webrtc|@stream-io/react-native-callingx|react-native|expo|@react-navigation/[^\"]+|expo-router|react-native-reanimated|react-native-worklets|react-native-teleport|@op-engineering/op-sqlite)\": *\"[^\"]*\"" package.json 2>/dev/null; echo "=== EXPO ==="; find . -maxdepth 2 \( -name "app.json" -o -name "app.config.js" -o -name "app.config.ts" -o -path "./app/_layout.*" \) -print 2>/dev/null; echo "=== NATIVE ==="; find . -maxdepth 2 \( -name "ios" -o -name "android" \) -type d -print 2>/dev/null; echo "=== CONFIG ==="; find . -maxdepth 2 \( -name "babel.config.js" -o -name "metro.config.js" \) -print 2>/dev/null; echo "=== EXPO_SDK ==="; node -e "try{console.log(require(\"./node_modules/expo/package.json\").version)}catch(e){try{console.log(require(\"./package.json\").dependencies.expo)}catch(e){console.log(\"-\")}}" 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Hold the result in conversation context. Do not re-run unless the user changes directory, packages are installed, or the project shape changes.

Use the result to produce a one-line status, for example:

- `Empty workspace detected - defaulting to Expo new app unless the user asked for RN CLI`
- `Expo app detected - stream-chat-expo absent - Expo Router present - ready for Chat setup`
- `Expo app detected - Expo SDK 56+ - apply RULES.md > Expo Router SDK 56+ rule (no @react-navigation/*)`
- `Expo app detected - @stream-io/video-react-native-sdk absent - ready for Video setup`
- `Expo app detected - @stream-io/feeds-react-native-sdk absent - ready for Feeds setup`
- `RN CLI app detected - ios/android present - stream-chat-react-native installed - checking provider placement`
- `RN CLI app detected - both @stream-io/video-react-native-sdk and stream-chat-react-native installed - Chat + Video interop applies`
- `Expo app detected - @stream-io/feeds-react-native-sdk and stream-chat-expo installed - nest StreamFeeds + Chat providers (no sibling mounts)`
- `No RN/Expo app detected in a non-empty directory - create a new app in a child directory or ask before reusing this directory`

If there is no RN/Expo project and Track A applies, scaffold one through [`builder.md`](builder.md) > **2. New app scaffold**. If Track B/D applies in a non-RN directory, ask before creating a child app because that changes project ownership.

---

## Module map

| Track | Module(s) |
|---|---|
| A - New app | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + `llms.txt` docs lookup + product references (Chat / Video / Feeds) |
| B - Existing app | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + `llms.txt` docs lookup + product references (Chat / Video / Feeds) |
| C - Reference lookup | [`sdk.md`](sdk.md) + [`references/DOCS.md`](references/DOCS.md) + relevant product reference files |
| D - Bootstrap / setup | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + `llms.txt` docs lookup |
| M - Migrate / upgrade | [`migrate.md`](migrate.md) + [`references/DOCS.md`](references/DOCS.md) (live upgrade guide) + product reference for the migrated SDK |

---

## Reference layout

Shared React Native and Expo patterns live in **[`sdk.md`](sdk.md)**.

Product-specific setup, docs lookup, gotchas, and UI blueprints live under **`references/`**:

- **`llms.txt` docs lookup (Chat, Video, Feeds):** [`references/DOCS.md`](references/DOCS.md)
- **Chat setup/reference:** [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md)
- **Chat screen/component blueprints:** [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md)
- **Video setup/reference:** [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md)
- **Video screen/component blueprints:** [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md)
- **Feeds setup/reference:** [`references/FEEDS-REACT-NATIVE.md`](references/FEEDS-REACT-NATIVE.md)
- **Feeds screen/component blueprints:** [`references/FEEDS-REACT-NATIVE-blueprints.md`](references/FEEDS-REACT-NATIVE-blueprints.md)
- **iOS simulator verification (fast run/screenshot loop):** [`references/SIMULATOR-VERIFICATION.md`](references/SIMULATOR-VERIFICATION.md)

If the requested product file is not bundled yet, say so plainly and only switch to live docs if the user asks.

---

## Docs-first triggers (consult docs before building)

The bundled blueprints cover the **common scaffold path only** - root providers, auth gate, fresh-app scaffold, channel list, channel/message screen, threads (and the Video/Feeds equivalents). For anything that **customizes or extends** that path, the live `llms.txt`-selected page is the source of truth for the current API and recommended pattern. Fetch it **before** writing code.

Docs-first applies when the request hits any of these:

- **UI customization / theming / component overrides** - themes, design tokens, replacing a slot (message bubble, composer, call controls, participant tile, activity row), custom render props.
- **Cookbook recipes** - typing indicators, message actions, reactions UI, attachment handling, mentions, search, link previews, etc.
- **Advanced guides** - push notifications, offline support, PiP, ringing, screenshare, broadcasting, video filters, Chat+Video interop, notification/For-You feeds, polls, moderation.
- **Migration / version upgrades.**
- **Any exact API, prop, hook, or component detail** not already in the bundled blueprints.

Mechanism (mirrors the `stream-react` skill):

**match -> run the [`references/DOCS.md`](references/DOCS.md) manifest lookup -> `WebFetch` (or `curl -Ls`) the selected `.md` page -> implement to match.** On fetch failure, hand to the `stream-docs` skill; if neither resolves the API, **stop and ask the user - never build customization, cookbook, or advanced features from memory.**

Enforced by [`RULES.md`](RULES.md) > Package version and docs discipline.

---

## Styling-depth flag: matching a provided design

Orthogonal to the track above: if a request carries a **target appearance** - an attached
screenshot, a Figma frame, or "make it look like WhatsApp / iMessage / Slack / \<app\>" - do not
treat it as a set-a-few-colors task. **Before** writing UI code, run
[`references/design-matching.md`](references/design-matching.md):
it decomposes the reference region by region and plans **every** difference as one of three axes -
**theming** (the `Theme` object), **layout** (`WithComponents` slot overrides + props), or
**functional** (props / config / SDK hooks) - then verifies region-by-region against the reference.
Implement every region, the composer included; a region left at the SDK default is a FAIL, not a
"known cosmetic gap."

This runs in addition to (not instead of) the `DOCS.md` lookup: fetch the manifest-selected
theming/customization pages to confirm exact theme paths and component names. A plain request
with **no** target appearance does not trip this flag - build from the blueprints as usual.

---

## Track A - New app

**Full detail:** [`builder.md`](builder.md) - use the new-app path.

| Phase | Name | What you do |
|---|---|---|
| **A1** | Detect | Run Project signals. Empty workspace is valid for Track A. |
| **A2** | Choose lane and product | Default to Expo if unspecified; use RN CLI when requested. Confirm product (Chat, Video, Feeds, or any combination). |
| **A3** | Scaffold | Create the app with current framework tooling; do not explain full RN/Expo environment setup. |
| **A4** | Install + wire | Use the manifest-selected Installation docs for each product, verify npm dist-tags, install package and peers, then wire providers and first UI. |
| **A5** | Verify | Confirm install, root providers, permissions (Video: camera/mic), auth, and first rendered Chat / Video / Feeds screen. |

---

## Track B - Existing app

**Full detail:** [`builder.md`](builder.md) - use the existing-project path.

| Phase | Name | What you do |
|---|---|---|
| **B1** | Detect | Run Project signals and inspect existing app structure before editing. Note any existing Chat / Video / Feeds packages. |
| **B2** | Preserve | Keep Expo/RN CLI lane, package manager, navigation stack, and auth architecture. If the user asks to **upgrade/migrate an SDK version**, that is **Track M** -> [`migrate.md`](migrate.md), not a Track B edit. |
| **B3** | Integrate | Use `llms.txt` lookup for the requested area, then load only the Chat / Video / Feeds reference/blueprint sections needed. |
| **B4** | Verify | Confirm the requested Stream Chat / Video / Feeds flow builds and renders in the existing app. |

---

## Track C - Reference lookup

Load only the relevant files for the requested product:

- `llms.txt` manifest lookup rules -> [`references/DOCS.md`](references/DOCS.md)
- Shared lifecycle / auth / provider / runtime patterns -> [`sdk.md`](sdk.md)
- Chat RN setup and gotchas -> [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md)
- Chat RN screen/component structure -> [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md)
- Video RN setup and gotchas -> [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md)
- Video RN screen/component structure -> [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md)
- Feeds RN setup and gotchas -> [`references/FEEDS-REACT-NATIVE.md`](references/FEEDS-REACT-NATIVE.md)
- Feeds RN screen/component structure -> [`references/FEEDS-REACT-NATIVE-blueprints.md`](references/FEEDS-REACT-NATIVE-blueprints.md)
- **Audit an existing Video integration against best practices** -> the **Integration best-practices audit** section in [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md) (read-only review; produce findings before changing any code)

If the user asks for exact API details not bundled here, use [`references/DOCS.md`](references/DOCS.md) to fetch the right manifest and selected markdown page. If implementation still needs source-level confirmation, inspect the installed package under the target app's `node_modules` after dependencies are installed. Do not use machine-specific documentation paths.

---

## Track D - Bootstrap / setup

Use when the user wants package install and shared wiring more than a full feature build. Branch by product:

- detect RN CLI vs Expo
- use `llms.txt` lookup for the matching product's Installation docs and verify current npm dist-tags
- install the correct package and required peers (Chat: `stream-chat-react-native` or `stream-chat-expo`; Video: `@stream-io/video-react-native-sdk`; Feeds: `@stream-io/feeds-react-native-sdk` + `@react-native-community/netinfo`)
- Chat-specific wiring: add Reanimated/Worklets Babel plugin as the last plugin, wrap the entry point with `GestureHandlerRootView`, place `OverlayProvider` and `Chat`, wire `useCreateChatClient` or the app's backend token provider
- Video-specific wiring: declare camera/mic permissions, add Expo config plugins where applicable, create `StreamVideoClient` and mount `StreamVideo`
- Feeds-specific wiring: call `useCreateFeedsClient` (returns `undefined` while connecting), mount `<StreamFeeds client={client}>` once near the app root, and (typically) wrap an `OwnFeedsContextProvider` that creates the user + timeline feeds and the self-follow
- stop before product-specific UI if the user only asked for setup

---

## Track M - Migrate / upgrade a version

**Full detail:** [`migrate.md`](migrate.md) - Read it first; it fetches the live upgrade guide before any edit. Docs-driven and read-only until the guide is fetched - **never migrate from memory** ([`RULES.md`](RULES.md) > Package version and docs discipline). Skip credentials, provisioning, and scaffold; preserve the project's runtime lane, package manager, and lockfile.

| Phase | Name | What you do |
|---|---|---|
| **M1** | Detect | Run Project signals + read `package.json`/lockfile: which Stream packages, their from -> to versions, runtime lane, package manager, and RN/Expo New-Architecture status. |
| **M2** | Fetch the guide | From the product manifest ([`references/DOCS.md`](references/DOCS.md)) fetch the matching upgrade guide (known entry point: Chat RN **v8 -> v9**). Hard gate on failure -> `stream-docs` -> stop and ask. |
| **M2.5** | Prerequisites | Clear RN-specific blockers first: New Architecture requirement, new native/peer deps (e.g. `react-native-teleport` for Chat v9), native rebuild. |
| **M3** | Apply | Bump only the targeted packages (each at its own target; bump the lane's Chat wrapper), apply every documented breaking change, ground each symbol in installed `node_modules/stream-chat-react-native-core` source, grep for renamed symbols, do native config + keyboard cleanup. |
| **M4** | Verify | `tsc --noEmit` -> Metro bundle -> native build -> simulator/device smoke of the core flow. No `next build`; a green `tsc` is not a render. |
| **M5** | Summarize | Packages bumped, breaking changes applied, native/New-Arch changes, files touched, manual follow-ups. Offer (don't auto-run) the next step. |
