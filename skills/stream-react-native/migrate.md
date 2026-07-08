# Migrate / upgrade an SDK version (Track M)

For upgrading an existing React Native / Expo app's Stream SDK to a newer major/minor - "upgrade `stream-chat-react-native` to v9", "migrate Chat RN to the new SDK", "bump my Stream Video / Feeds version", "Feeds v2 -> v3". **Docs-driven and read-only until you've fetched the guide** - never apply a migration from memory ([`RULES.md`](RULES.md) > Package version and docs discipline).

> **Rules:** [`RULES.md`](RULES.md) (docs authority via [`references/DOCS.md`](references/DOCS.md) manifests, runtime lane ownership, New Architecture, secrets) and the cross-cutting [`../stream/RULES.md`](../stream/RULES.md). This track does **not** scaffold, provision, or authenticate - it edits an existing project, so **skip Step 0.5 credentials and the scaffold path in [`builder.md`](builder.md)**. **Preserve the project's runtime lane, package manager, and lockfile.**

---

## Source of truth - every fact comes from the guide, node_modules, or live docs (never memory)

Migrations are where APIs move, so **memory is stale here by definition.** Every symbol, prop, hook, rename, removed export, version number, native requirement, and step you apply MUST trace to one of these three authorities - never to recall, and never to the illustrative examples in this file:

1. **The AI migration guide document** - the symbol-level checklist for the upgrade (Chat RN v8 -> v9: `https://raw.githubusercontent.com/GetStream/stream-chat-react-native/develop/ai-docs/ai-migration.md`). This is the authoritative list of *what changed*. Fetch it and work from it - do not reconstruct it from memory.
2. **The installed source in `node_modules`** - ground truth for what actually exists in the **pinned target version**. For Chat that is `node_modules/stream-chat-react-native-core/src/` (the core package, not the wrapper). Verify every symbol here before you write it.
3. **The live docs** - the product `llms.txt` manifest + selected markdown page ([`references/DOCS.md`](references/DOCS.md)), including the human upgrade guide.

**The concrete names in this file are illustrations of the *kinds* of change, not a change list to apply.** Any symbol below (e.g. `MessageComposer`, `react-native-teleport`) is there to show scope - re-confirm it in the guide + `node_modules` for the actual target version before writing it. This file can go stale; the three sources cannot.

**Provenance rule:** for every change you apply, you must be able to name its source - a guide section, a `node_modules` path, or a docs page. A change you cannot attribute to one of the three is a hallucination - drop it.

**Hard gate:** if the guide, `node_modules`, and live docs together do not confirm a fact, **stop and ask the user** - do not fill the gap from memory. A guess that happens to compile is still a guess.

| Excuse | Reality |
|--------|---------|
| "I know the v8 -> v9 renames" | Knowing the concept != the pinned target's actual exports. Confirm each in the guide + `node_modules`. |
| "The examples in migrate.md list the changes" | Those are scope illustrations. The fetched AI guide is the authoritative list. |
| "The guide didn't mention this symbol, but I remember it" | Not in the guide AND not in `node_modules` = it doesn't exist for this version. Drop it or ask. |
| "The docs page is close enough for the API name" | Confirm the exact export in `node_modules` for the installed version - docs can lag or lead the pinned build. |
| "WebFetch failed, I'll wire it from memory" | Failure -> `stream-docs`, then stop and ask. Never memory. |
| "It compiled, so it's right" | Compiling is not correctness - a wrong-but-typed symbol still ships a broken migration. |

**Red flags - STOP:**
- About to write a symbol / prop / hook you have not confirmed in the fetched guide AND `node_modules` this turn.
- Reaching for a remembered v8 or v9 name instead of the one in the guide.
- Applying a change from the examples in this file without re-confirming it against the guide.
- Adding a native / peer requirement or a version number you did not read from the guide or docs.
- Continuing after a failed fetch instead of escalating to `stream-docs` or asking.

---

## M1: Detect what's installed

Run **Project signals** ([`SKILL.md`](SKILL.md)) once, then read the target versions from `package.json` + lockfile (do not guess):

- **Chat:** `stream-chat-react-native` (RN CLI) **or** `stream-chat-expo` (Expo) - both peer-depend on `stream-chat-react-native-core`, where the SDK source actually lives - plus `stream-chat`.
- **Video:** `@stream-io/video-react-native-sdk`.
- **Feeds:** `@stream-io/feeds-react-native-sdk`.

Establish **from version -> to version** for each package the user wants to move. If no target was named, the target is the latest published major - confirm it with `npm view <package> version dist-tags --json` ([`references/DOCS.md`](references/DOCS.md)) before proceeding.

Also record the three things RN migrations turn on:

- **Runtime lane** - RN CLI vs Expo (from Project signals). It decides which Chat wrapper you bump and whether native config is edited directly or regenerated via `expo prebuild`.
- **Package manager** - from the lockfile (`package-lock.json` -> npm, `yarn.lock` -> yarn, `pnpm-lock.yaml` -> pnpm). Use it for every install/build below; never strand the active lockfile.
- **React Native / Expo SDK version + New Architecture status** - many current majors (e.g. Chat RN v9) **require the New Architecture**. If the project is on the old architecture, that is a prerequisite upgrade, not an afterthought (M2.5).

## M2: Fetch the matching upgrade guide (before any edit)

**Match the upgrade to its guide and fetch it this turn** - the `llms.txt` manifest is the authority ([`references/DOCS.md`](references/DOCS.md)), not memory and not these notes. Find the "upgrade" / "migration" entry in the product's **primary manifest**, then fetch the selected markdown page.

Known entry point - **Chat RN v8 -> v9** (a ground-up UI-layer redesign; scope it as large, not a rename pass). **Fetch both, this turn - the AI checklist is the authoritative, symbol-level source and is required, not optional:**

- **AI migration guide (authoritative change list):** `https://raw.githubusercontent.com/GetStream/stream-chat-react-native/develop/ai-docs/ai-migration.md`. Every rename, removed export, and prerequisite you apply comes from here (cross-checked against `node_modules`), not from memory.
- **Human upgrade guide (context + rationale):** `https://getstream.io/chat/docs/sdk/react-native/basics/upgrading-from-v8.md` (fetch the `.md`; the manifest also lists it under "upgrading to v9").

For **Video RN** or **Feeds RN** (including **Feeds v2 -> v3**), discover the guide from the matching manifest ([`references/DOCS.md`](references/DOCS.md)) - look for the upgrade / migration entry matching the from/to versions; if that product ships an AI-migration doc, fetch it too and treat it as authoritative.

Read the guide(s) in full before touching code; extract every **prerequisite, breaking change, rename, removed export, new peer dependency, native-config change, and theme / token change** into a working checklist you drive from - this checklist, not memory, is what you apply in M3.

**Hard gate ([`RULES.md`](RULES.md)):** if no guide loads, hand the lookup to the `stream-docs` skill. If neither the guide nor `stream-docs` confirms the steps, **stop and tell the user** - report that you could not confirm the upgrade path and ask how to proceed. Do not migrate from memory; a guess that happens to compile is still a guess.

## M2.5: Clear the prerequisites gate (RN-specific)

Before editing app code, satisfy whatever the guide lists as a hard blocker - these are RN concerns the web migration never has:

- **New Architecture.** If the target major requires it (Chat RN v9: RN **0.76+** or an Expo SDK that defaults to New Arch, and every native module New-Arch compatible), and the project is on the old architecture, that upgrade comes **first**. Surface it as its own step - do not silently proceed on the old architecture.
- **New native / peer dependencies.** Install what the guide requires with the detected package manager (Chat RN v9 adds `react-native-teleport@>=0.5.4` for portal-hosted overlays - [`RULES.md`](RULES.md) > Required peer setup).
- **A native rebuild is required after any native dependency change** - this is not a JS-only bump (M3, native config).

## M3: Apply the documented changes

Work strictly from the fetched guide:

1. **Bump only the packages being migrated**, each to ITS OWN resolved target from M1. Stream packages carry **independent version numbers** - never apply one target to several. **Bump the wrapper that matches the lane** (Expo -> `stream-chat-expo`; RN CLI -> `stream-chat-react-native`); the shared `stream-chat-react-native-core` follows as their peer. Use the **detected package manager** (yarn / pnpm don't need `--legacy-peer-deps`; npm may):
   ```bash
   # examples - bump only what the user is upgrading, each at its own target
   yarn add stream-chat-expo@<target> stream-chat@<target>                                 # Expo Chat
   npm install stream-chat-react-native@<target> stream-chat@<target> --legacy-peer-deps   # RN CLI Chat
   yarn add @stream-io/video-react-native-sdk@<target>                                     # Video
   yarn add @stream-io/feeds-react-native-sdk@<target>                                     # Feeds
   ```
2. **Apply each breaking change from the M2 checklist** (which came from the fetched guide) - work down that list, not from memory. *Illustrative of the scope only, NOT a list to apply from this file:* for Chat RN v8 -> v9 the surface is large - component / hook / theme-key renames, component-override props on `Channel` / `ChannelList` / `Chat` / `Thread` centralized into one `<WithComponents overrides={{...}}>` wrapper, removed props with replacements, inverted audio semantics, a `messageContentOrder` default swap, and semantic design-token renames. **The exact names, directions, and defaults come from the fetched guide + `node_modules` - re-confirm each before writing it; do not copy the shapes above.**
3. **Ground every symbol in the installed source before wiring it - each one, not a sample.** Export names move between majors, so confirm the symbol / prop / hook you are about to write actually exists in the installed package - and for Chat, in the **core** package, not the wrapper. Verify the specific names from your M2 checklist:
   ```bash
   # substitute the actual symbols you're migrating; expect a hit for each before you use it
   grep -RnE "<symbol1>|<symbol2>" node_modules/stream-chat-react-native-core/src/index.ts
   ```
   A symbol absent from both the guide and `node_modules` does not exist for this version - do not write it from memory; drop it or ask ([`references/DOCS.md`](references/DOCS.md)). If a name resolves differently than the guide implies, `node_modules` wins (it is the pinned build).
4. **Search the codebase** for every removed / renamed symbol **on your M2 checklist** so nothing is missed (build the pattern from that list, not from memory): `grep -RnE "<old1>|<old2>|<old3>" src/ app/ components/`.
5. **Native config + keyboard cleanup** the guide calls for:
   - **RN CLI:** install new native peers, then rebuild pods (`npx pod-install` / `cd ios && pod install`) and let Gradle re-sync; apply any `minSdkVersion` / Java / New-Architecture flag changes.
   - **Expo:** add any new config plugins to `app.json`, then `npx expo prebuild --clean` and rebuild the dev client (Expo Go is not a supported target).
   - **Keyboard (Chat v9):** remove negative `keyboardVerticalOffset` values, drop `SafeAreaView` wrappers around `MessageComposer`, and strip manual Android IME padding hacks - the refactored `KeyboardCompatibleView` handles them ([`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md)).
6. Do **not** introduce features the user didn't ask for; this track is an upgrade, not a redesign.

## M4: Verify

Run with the **detected** package manager (do not introduce a second lockfile). There is no `next build` - it is a native app, so verification is type-check -> bundle -> native build -> smoke:

```bash
npx tsc --noEmit # or: yarn tsc --noEmit / pnpm exec tsc --noEmit  - reports all type errors at once
```

Then confirm it bundles and runs:

- **Metro bundles clean** (`npx expo start` / the project's start script) with no unresolved-import errors from renamed / removed exports.
- **The native app builds** after the native-config changes (dev-client rebuild for Expo; `pod install` + Gradle for RN CLI).
- **Smoke-test the core flow on a simulator / device**, driving what the guide's checklist names - for Chat v9: render `Chat` -> `Channel` -> `MessageList` + `MessageComposer`, send a message, long-press for reactions, swipe to reply, attach an image, record audio, open the gallery. A green `tsc` is not a render.

Re-run until type-check, bundle, and the smoke flow all pass.

## M5: Summarize

Report: packages bumped (from -> to), breaking changes applied, native-config / New-Architecture changes made, files touched, and anything from the guide needing manual follow-up (New Architecture enablement, Dashboard / push config, third-party native modules not yet New-Arch compatible). Per the provenance rule, keep each applied change attributable to its source (guide section / `node_modules` path / docs page) so the migration is auditable, not asserted. Offer - do not auto-run - the natural next step (e.g. "want me to migrate your Video RN SDK too, or bump the server SDK?").
