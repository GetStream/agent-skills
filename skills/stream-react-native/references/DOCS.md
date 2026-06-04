# Stream React Native - llms.txt docs lookup (Chat, Video, Feeds)

Use `llms.txt` manifests as the only docs entrypoint for Stream Chat, Stream Video, and Stream Feeds React Native work. Do not maintain direct page URLs in this skill. The manifest is an index, not the source: fetch the selected markdown page from the manifest before coding or making API-specific claims.

Pick the manifest set that matches the requested product. Most requests touch one product only; for combined apps (Chat + Video interop, Feeds + Chat, etc.), consult each product's manifest.

---

## Manifests

### Chat (React Native)

| Manifest | Use for |
|---|---|
| `https://getstream.io/chat/docs/sdk/react-native/llms.txt` | Primary source for Stream Chat React Native UI SDK: installation, packages, components, contexts, theming, customization, UI cookbook, offline, push, New Architecture, native handlers, migration guides. |
| `https://getstream.io/chat/docs/react-native/llms.txt` | Secondary source for low-level Chat API/client topics: tokens, users, channels, messages, query syntax, permissions, events, webhooks, push provider setup, imports/exports. |

### Video (React Native)

| Manifest | Use for |
|---|---|
| `https://getstream.io/video/docs/react-native/llms.txt` | Primary source for Stream Video React Native: installation (RN CLI and Expo), quickstart, calls and call lifecycle, call types, components (CallContent, CallControls, ParticipantView, LivestreamPlayer, HostLivestream, IncomingCall, OutgoingCall), UI cookbook, incoming calls / ringing setup, push providers (Firebase, APNs/PushKit), advanced topics (Chat-with-Video interop, PiP, broadcasting, custom video filters, screenshots), migration guides. |

### Feeds (React Native)

| Manifest | Use for |
|---|---|
| `https://getstream.io/activity-feeds/docs/react-native/llms.txt` | Primary source for Stream Feeds React Native: installation, tokens and authentication, user permissions, feed groups, aggregation, activity selectors, processors, stories, search, feed visibility, membership levels, activities, activity feedback, reactions, comments, user mentions, pins, event handling, contexts and hooks, state layer, logging, importing data, push providers and multi-bundle setup, ranking, notification feeds, For You feed, follows, members, query activities, bookmarks, file uploads, URL previews, polls, moderation, error handling, V2-to-V3 migration. |

The primary Chat manifest should identify itself as the current React Native docs. If it does not, treat that as a docs-version problem and verify from the manifest title before continuing. The same applies to the Video and Feeds manifests.

---

## Lookup workflow

1. Identify the product (Chat, Video, or Feeds) from the user request, then fetch the matching primary manifest.
2. Search manifest link text for the exact component, hook, guide, or feature name.
3. Fetch the selected markdown URL from the manifest.
4. Confirm the markdown page matches the current React Native SDK docs when doing SDK work.
5. Code from the fetched markdown page plus this skill's rules and blueprints.
6. If the Chat primary manifest does not contain the topic and the request is low-level Chat API/client behavior, repeat the lookup in the Chat secondary manifest.
7. If multiple titles match, prefer the exact component or guide title over generic `Overview` pages.

Do not code from the manifest list alone. Do not paste or rely on direct docs URLs outside the manifests.

Before installing, verify current npm tags for the selected product. Pick the package(s) that match the request:

```bash
# Chat
npm view stream-chat-react-native version dist-tags --json
npm view stream-chat-expo version dist-tags --json

# Video
npm view @stream-io/video-react-native-sdk version dist-tags --json

# Feeds
npm view @stream-io/feeds-react-native-sdk version dist-tags --json
```

Install `@latest` when the npm dist-tag matches the selected docs. If it does not, use the tag or exact version recommended by the manifest-selected installation page.

---

## Manifest search strategy

Do not maintain a feature-to-page table in this skill. The manifest is the live table of contents, and agents should search it at task time.

Build search terms from the current request and codebase:

1. Exact SDK symbols, packages, props, hooks, and component names already present in the prompt or code.
2. Exact user phrases for the requested feature or behavior.
3. Runtime words from the request or codebase when setup differs by runtime or architecture.
4. Broad domain words from the request only when exact terms do not hit.

Search order:

1. Search the primary manifest for exact symbols and exact phrases first.
2. If no exact result exists, search with split feature nouns from the user's request.
3. If several manifest entries match, fetch the two or three most relevant markdown pages and choose from their contents.
4. For cookbook or customization requests, find the current cookbook/customization entries in the primary manifest instead of assuming page names.
5. For low-level Chat API/client behavior, repeat the same search process in the secondary manifest only after deciding the UI SDK manifest is not the right source.
6. If neither manifest has a clear match, say the manifest has no exact match, fetch the closest overview or API page, and inspect installed package source only when code-level verification is still needed.

Do not convert these heuristics into a static mapping. If the docs add, rename, move, or split a page, the next agent should discover that from the manifest.

---

## Source selection

**Chat work.** Use the Chat primary manifest for React Native UI SDK work: package installation, providers, components, hooks, theming, customization, native handlers, offline UI behavior, push UI setup, migration, and cookbook-style UI recipes. Use the Chat secondary manifest for Chat API/client work: tokens, auth, users, channels, messages, reactions, query syntax, permissions, events, typing, webhooks, import/export, rate limits, and API errors.

**Video work.** Use the Video manifest for everything: installation (RN CLI + Expo), client and call lifecycle, ringing/push, UI components and cookbook, advanced topics. Video does not have a separate API/client manifest; the same manifest covers both UI and lower-level call/state behavior.

**Feeds work.** Use the Feeds manifest for everything: installation, client creation (`useCreateFeedsClient`, `StreamFeeds`), feed groups, activities, reactions, comments, follows, notification feeds, For You feed, activity selectors, contexts and hooks (state layer), error handling, push, polls, moderation. Feeds does not have a separate API/client manifest; the same manifest covers both contexts/hooks and lower-level state behavior.

**Combined apps (Chat + Video, Feeds + Chat, Feeds + Video, or all three).** Consult each product's manifest. The canonical Chat-with-Video interop entrypoint is the Video manifest's `https://getstream.io/video/docs/react-native/advanced/chat-with-video.md`. Feeds has no built-in cross-product integration page; link out from your own UI.
