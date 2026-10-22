# Stream Android - llms.txt docs lookup (Chat, Video, Feeds)

Use `llms.txt` manifests as the docs entrypoint for Stream Chat, Stream Video, and Stream Feeds Android work. Do not maintain direct page URLs in this skill. The manifest is an index, not the source: fetch the selected markdown page from the manifest before coding or making API-specific claims.

Pick the manifest set that matches the requested product. Most requests touch one product only; for combined apps (Chat + Video interop, Feeds + Chat, etc.), consult each product's manifest.

---

## Relationship to the bundled references

This pack bundles curated references and blueprints (`CHAT-COMPOSE.md`, `VIDEO-COMPOSE.md`, ...). They are not replaced by the manifests - the two cover different things:

- **Bundled references and blueprints stay mandatory** for screen structure, slot maps, and the Android-specific rules in [`../RULES.md`](../RULES.md). Read them as that file requires, on every turn.
- **The manifests are the source for anything not bundled**: guides, API detail, newer surfaces, and any product/UI-layer combination this pack does not carry (AI integrations, moderation, location sharing, migration guides).

When the two disagree about an API signature, the fetched docs page wins and the bundled reference is stale - say so rather than quietly picking one.

---

## Manifests

### Chat (Android)

| Manifest | Use for |
|---|---|
| `https://getstream.io/chat/docs/sdk/android/llms.txt` | Primary source for the Stream Chat Android UI SDKs (Compose and XML): installation, Compose components and `ChatComponentFactory`, theming, UI cookbook, XML view components, offline support, push, guides, migration guides, and the `ai-integrations` pages (AI Integrations, Compose Integration, Stream Chat AI SDK, Stream Chat LangChain SDK). |
| `https://getstream.io/chat/docs/android/llms.txt` | Secondary source for low-level Chat API/client topics: tokens, users, channels, messages, query syntax, permissions, events, webhooks, push provider setup, imports/exports. |

### Video (Android)

| Manifest | Use for |
|---|---|
| `https://getstream.io/video/docs/android/llms.txt` | Primary source for Stream Video Android: installation, quickstart, call lifecycle and call types, Compose components (`CallContent`, `CallControls`, `ParticipantView`, livestream players), UI cookbook, ringing and push setup, advanced topics (Chat-with-Video interop, PiP, screen sharing, video filters), migration guides. |

### Feeds (Android)

| Manifest | Use for |
|---|---|
| `https://getstream.io/activity-feeds/docs/android/llms.txt` | Primary source for Stream Feeds Android (V3): installation, tokens and authentication, feed groups, activities, reactions, comments, follows, notification feeds, activity selectors, state layer, polls, moderation, push, and V2-to-V3 migration. |

The primary Chat manifest should identify itself as the current Android docs (`# Android v7 (Latest)`). If it identifies as v6 or older, treat that as a docs-version problem and verify before continuing - this pack targets v7+ ([`../RULES.md`](../RULES.md) "Target SDK version"). The same applies to the Video and Feeds manifests.

---

## Lookup workflow

1. Identify the product (Chat, Video, or Feeds) from the user request, then fetch the matching primary manifest.
2. Search manifest link text for the exact component, Composable, guide, or feature name.
3. Fetch the selected markdown URL from the manifest.
4. Confirm the markdown page matches the current Android SDK docs when doing SDK work.
5. Code from the fetched markdown page plus this pack's rules, references, and blueprints.
6. If the Chat primary manifest does not contain the topic and the request is low-level Chat API/client behavior, repeat the lookup in the Chat secondary manifest.
7. If multiple titles match, prefer the exact component or guide title over generic `Overview` pages.

Do not code from the manifest list alone. Do not paste or rely on direct docs URLs outside the manifests.

---

## Manifest search strategy

Do not maintain a feature-to-page table in this skill. The manifest is the live table of contents, and agents should search it at task time.

Build search terms from the current request and codebase:

1. Exact SDK symbols, artifacts, Composables, slots, and class names already present in the prompt or code.
2. Exact user phrases for the requested feature or behavior.
3. UI-layer words (Compose vs XML) when setup differs by layer.
4. Broad domain words from the request only when exact terms do not hit.

Search order:

1. Search the primary manifest for exact symbols and exact phrases first.
2. If no exact result exists, search with split feature nouns from the user's request.
3. If several manifest entries match, fetch the two or three most relevant markdown pages and choose from their contents.
4. For cookbook or customization requests, find the current cookbook/customization entries in the primary manifest instead of assuming page names.
5. For low-level Chat API/client behavior, repeat the same search process in the secondary manifest only after deciding the UI SDK manifest is not the right source.
6. If neither manifest has a clear match, say the manifest has no exact match, fetch the closest overview or API page, and inspect the SDK source only when code-level verification is still needed.

Do not convert these heuristics into a static mapping. If the docs add, rename, move, or split a page, the next agent should discover that from the manifest.

---

## Source selection

**Chat work.** Use the Chat primary manifest for UI SDK work in either layer: artifact installation, `ChatClient` setup pages, Compose components and `ChatComponentFactory` slots, theming, XML view components and binding, offline, push UI setup, cookbook recipes, guides, and the `ai-integrations` pages. Use the Chat secondary manifest for Chat API/client work: tokens, auth, users, channels, messages, reactions, query syntax, permissions, events, typing, webhooks, import/export, rate limits, and API errors.

**Video work.** Use the Video manifest for everything: installation, client and call lifecycle, ringing/push, Compose components and cookbook, advanced topics. Video does not have a separate API/client manifest.

**Feeds work.** Use the Feeds manifest for everything: installation, client creation, feed groups, activities, reactions, comments, follows, notification feeds, state layer, push, polls, moderation. Feeds has no pre-built UI artifact, so the manifest covers the data SDK only - screen structure comes from [`FEEDS-COMPOSE-blueprints.md`](FEEDS-COMPOSE-blueprints.md).

**Combined apps (Chat + Video, Feeds + Chat, or all three).** Consult each product's manifest. The Chat-with-Video interop entrypoint lives in the Video manifest.

---

## Version lookup before installing

Verify the current published version before writing a dependency, using the sources [`../RULES.md`](../RULES.md) "Version lookup" allows (never `search.maven.org`):

```bash
# Chat - Compose UI SDK / XML UI SDK
curl -s https://repo1.maven.org/maven2/io/getstream/stream-chat-android-compose/maven-metadata.xml | grep -o '<release>[^<]*'
curl -s https://repo1.maven.org/maven2/io/getstream/stream-chat-android-ui-components/maven-metadata.xml | grep -o '<release>[^<]*'

# Chat - AI components (versioned independently of the Chat SDK)
curl -s https://repo1.maven.org/maven2/io/getstream/stream-chat-android-ai-compose/maven-metadata.xml | grep -o '<release>[^<]*'

# Video
curl -s https://repo1.maven.org/maven2/io/getstream/stream-video-android-ui-compose/maven-metadata.xml | grep -o '<release>[^<]*'

# Feeds
curl -s https://repo1.maven.org/maven2/io/getstream/stream-feeds-android-client/maven-metadata.xml | grep -o '<release>[^<]*'
```

Install the latest release when it matches the manifest-selected docs version. If it does not, use the version the manifest's installation page recommends. Add the coordinates to `gradle/libs.versions.toml` when the project already uses a version catalog ([`../RULES.md`](../RULES.md) "Project ownership").
