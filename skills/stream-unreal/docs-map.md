# Stream Unreal - docs routing map

Map a request to the exact docs page, then fetch its `.md` twin ([`SKILL.md`](SKILL.md) explains the convention). Live index that lists every page:

```
https://getstream.io/cli/docs/chat-unreal.md
```

Prefix every path below with `https://getstream.io/chat/docs/unreal` unless stated otherwise. Fetch at most 3 pages per request. Cite what you used. Do not guess paths - if it is not below, use the index.

---

## Read this before using the table

The `/chat/docs/unreal/` tree is largely **shared cross-SDK prose**. Only about **26 of its 61 pages carry an `Unreal` code tab**; the rest show JavaScript, Node, Kotlin, or (on one page) C#/Unity. So the **Unreal code** column is the most important column here:

| Marker | Meaning | What to do |
|---|---|---|
| **yes** | The page has an `Unreal` code tab. | Fetch it, use the code verbatim. |
| **prose** | No code on the page at all (concepts, config, reference tables). | Fetch it; there is nothing to translate. |
| **JS only** | Code is JavaScript/Node/Kotlin, but the feature **is** implemented in Unreal. | Fetch it for the concepts, then get the API from the **plugin headers** (see "When the docs fall short"). **Never translate the JS.** |
| **N/A** | The feature is **not implemented** in the Unreal SDK; the page's JS code does not apply. | Do not fetch to write code. Tell the user the feature is unavailable ([`SKILL.md`](SKILL.md) Gate 2). |

An **N/A** row is a page that will happily show you working JavaScript for something the Unreal SDK cannot do. The introduction page warns about this once, in prose; the individual pages do not. That is the trap this column exists to prevent.

---

## Start here

| Want to ... | Page (.md) | Unreal code |
|---|---|---|
| Introduction, install, supported features | `.md` (root) | **yes** |
| First integration walkthrough (Blueprint, screenshot-driven) | `https://getstream.io/chat/sdk/unreal/tutorial.md` | **yes** |
| What Stream's backend is and how it scales | `/architecture-and-benchmark.md` | prose |
| Roadmap and changelog | `/roadmap-and-changelog.md` | prose |

> There is **no C++ quickstart page** upstream. The nearest thing is the sample's `Source/StreamChatSample/StreamChatSampleHud.cpp` - a working connect + query + show-UI in 40 lines. [`setup.md`](setup.md) 4 carries a verified version of it.

## Client, users, and auth

| Want to ... | Page (.md) | Unreal code |
|---|---|---|
| Create the client, connect a user, disconnect | `/init-and-users.md` | **yes** |
| Tokens, expiry, refresh, dev tokens, auth error codes | `/tokens-and-authentication.md` | **yes** |
| Guest and anonymous users (spectators) | `/authless-users.md` | **yes** |
| Create / update users, partial update, custom fields | `/update-users.md` | **yes** |
| Query users, search by presence | `/query-members.md` | **yes** |
| Presence, watchers, online state | `/presence-format.md` | **yes** |
| Teams / multi-tenant isolation | `/multi-tenant-chat.md` | **yes** |
| User groups | `/user-groups.md` | JS only |

> `ITokenProvider` - the Unreal interface for production token refresh - is **not shown anywhere in the docs**. Read `Plugins/StreamChat/Source/Backend/TokenProvider/Public/ITokenProvider.h`; [`setup.md`](setup.md) 4b has the pattern.
>
> Note also that `/init-and-users.md` shows `Client->ApiKey = TEXT(...)` with no surrounding lifecycle context. The **`ApiKey` must be set before `BeginPlay`** - see [`RULES.md`](RULES.md). The docs do not say this anywhere.

## Channels

| Want to ... | Page (.md) | Unreal code |
|---|---|---|
| Create a channel (`WatchChannel`, `CreateChannel`, `FChannelProperties`) | `/creating-channels.md` | **yes** |
| Query channels: `FFilter`, sort options, `EChannelFlags`, pagination | `/query-channels.md` | **yes** |
| Filter operator reference (`$in`, `$autocomplete`, ...) | `/query-syntax-operators.md` | prose |
| Update a channel (full and partial) | `/channel-update.md` | **yes** |
| Paginate channels and messages | `/channel-pagination.md` | **yes** |
| Members: add, remove, query | `/channel-members.md` | **yes** |
| Query members with filters | `/query-members.md` | **yes** |
| Channel management overview | `/channel-management.md` | prose |
| Hide / show a channel | `/hiding-channels.md` | **yes** |
| Mute a channel | `/muting-channels.md` | **yes** |
| Delete a channel | `/channel-delete.md` | **yes** |
| Truncate a channel | `/truncate-channel.md` | **yes** |
| Invites | `/channel-invites.md` | **yes** |
| Freeze / unfreeze a channel | `/freezing-channels.md` | JS only |
| Disable a channel | `/disabling-channels.md` | JS only |
| Channel types and their default config (`messaging`, `team`, `gaming`, `livestream`, `commerce`) | `/channel-features.md` | prose |
| Archive a channel | `/archiving-channels.md` | **N/A** |
| Pin a channel | `/pinning-channels.md` | **N/A** |

## Messages

| Want to ... | Page (.md) | Unreal code |
|---|---|---|
| Send, edit, delete, fetch messages; custom fields | `/send-message.md` | **yes** |
| Silent and system messages | `/silent-messages.md` | **yes** |
| Auto-translation | `/translation.md` | **yes** |
| Full-text message search | `/search.md` | JS only |
| Reactions: send with score, enforce-unique, remove, paginate | `/send-reaction.md` | JS only |
| Delivered / read status, mark read | `/message-delivery-and-read-status.md` | JS only |
| Unread counts | `/unread.md` | **yes** |
| Typing indicators (`KeyStroke`, `StopTyping`) | `/typing-indicators.md` | **yes** |
| Attachments, file and image uploads | `/file-uploads.md` | **N/A** |
| Threads and replies | `/threads.md` | **N/A** |
| Pinned messages | `/pinned-messages.md` | **N/A** |
| Reminders and bookmarks | `/message-reminders.md` | **N/A** |
| Draft messages | `/drafts.md` | **N/A** |
| Polls | `/polls-api.md` | **N/A** |
| Location sharing | `/location-sharing.md` | **N/A** |
| Pending messages | `/pending-messages.md` | JS only (server-side feature) |

> **Reactions are the sharpest JS-only trap** - they are fully implemented (`UChatChannel::SendReaction`, `GetReactions`, `DeleteReaction`) but the page shows only JavaScript. Read `Plugins/StreamChat/Source/StreamChat/Public/Channel/ChatChannel.h` (Reaction region) and `Public/Reaction/*.h`.

## Events and real-time

| Want to ... | Page (.md) | Unreal code |
|---|---|---|
| Event types, payloads, subscribing | `/event-object.md` | **yes** |
| Features overview | `/features-overview.md` | prose |

C++ subscription is templated and **not fully covered by the page** - `Client->On<FMessageNewEvent>(this, &AMyHud::OnNewMessage)` and the lambda/`FDelegateHandle` overloads. The event structs live under `Plugins/StreamChat/Source/Backend/StreamChatWebSocket/Public/Event/`; `UChatChannel` also exposes Blueprint-assignable delegates (messages updated, typing, reactions) that are usually the simpler route.

## Moderation

| Want to ... | Page (.md) | Unreal code |
|---|---|---|
| Ban, shadow ban, mute, flag, block, query bans | `/moderation.md` | JS only |
| Permission and role reference | `/permissions-reference.md` | prose |
| Slow mode and throttling | `/slow-mode.md` | **yes** |

> **`/moderation.md` has 22 code blocks and not one is Unreal**, despite moderation being one of the SDK's more complete areas. The API is on `UStreamChatClientComponent` (`BanUser`/`BanUserBP`, `UnbanUser`, `ShadowBanUser`, `ShadowUnbanUser`, `QueryBannedUsers`, `MuteUser`, `UnmuteUser`, `FlagMessage`, `FlagUser`, `BlockUser`, `UnblockUser`, `GetBlockedUsers`) and on `UChatChannel` (`BanMember`, `UnbanMember`). Read `Public/StreamChatClientComponent.h` - it is well commented.
>
> The page (and the introduction page) also **omit user blocking entirely**, which shipped in v2.0.0. See [`SKILL.md`](SKILL.md) Gate 2.

## Push notifications

| Want to ... | Page (.md) | Unreal code |
|---|---|---|
| Register a device (`AddDevice`, `RemoveDevice`, `ListDevices`) | `/push-devices.md` | **yes** |
| Push overview and provider setup | `/push-introduction.md` | JS only |
| Push preferences | `/push-preferences.md` | JS only |
| Testing push | `/push-test.md` | JS only (Bash/Node) |
| Push troubleshooting | `/push-common-issues-and-faq.md` | prose |

The SDK implements device registration only; provider config and payload templates are server-side. See [`platforms.md`](platforms.md) 8 for what Unreal does and does not do here.

## Best practices, limits, and operations

Read before building or scaling a vertical ([`RULES.md`](RULES.md) "Mindful API usage").

| Want to ... | Page (.md) | Unreal code |
|---|---|---|
| Best practices overview | `/best-practices.md` | prose |
| Livestream and live-shopping (disable read/typing/connect events, slow mode) | `/livestream-best-practices.md` | prose |
| Query-channels budget | `/api-budget.md` | prose |
| Rate limits and backoff | `/rate-limits.md` | JS only - and the page serves a **C#/Unity** sample; ignore it |
| API error codes | `/api-errors-response.md` | JS only (Node) |
| Server-side overview | `/server-side.md` | prose |
| Stream CLI | `/cli-introduction.md` | Bash |

---

## When the docs fall short: source code + sample project

For this SDK that is the normal path, not the exception - the whole UMG layer and roughly a third of the implemented client surface have no Unreal code in the docs. The **plugin headers are the final authority**, and they are already in the user's project.

### Where to look

| What you need | Where |
|---|---|
| Client API: connect, query, channels, users, moderation, devices, events | `Plugins/StreamChat/Source/StreamChat/Public/StreamChatClientComponent.h` |
| Channel API: messages, reactions, typing, read state, members, moderation | `Plugins/StreamChat/Source/StreamChat/Public/Channel/ChatChannel.h` |
| Filters (`FFilter::In`, `And`, `Or`, `Nor`, `Autocomplete`, `Exists`, ...) | `.../Public/Channel/Filter.h` |
| Channel creation properties, sort fields, flags | `.../Public/Channel/ChannelProperties.h`, `ChannelSortOption.h`, `Source/Backend/StreamChatApi/Public/ChannelFlags.h` |
| Messages, reactions, members, reads | `.../Public/Channel/Message.h`, `Public/Reaction/*.h`, `Public/Channel/Member.h`, `Read.h` |
| Users, own user, pagination | `.../Public/User/*.h`, `Public/PaginationOptions.h` |
| Token provider | `Source/Backend/TokenProvider/Public/ITokenProvider.h`, `ConstantTokenProvider.h`, `Token.h` |
| Event structs | `Source/Backend/StreamChatWebSocket/Public/Event/**` |
| Widgets and theming | `Source/StreamChatUi/Public/**` - and [`widgets.md`](widgets.md), which is the runbook for this layer |

```bash
# Prefer the vendored plugin - it is the exact version the project compiles
grep -rn "SendReaction" Plugins/StreamChat/Source/StreamChat/Public/
ls Plugins/StreamChat/Source/StreamChatUi/Public/
```

If the project has no vendored copy yet, read from GitHub at the **tag matching the release**, not `main`:

```
https://raw.githubusercontent.com/GetStream/stream-chat-unreal/v2.0.0/Plugins/StreamChat/Source/StreamChat/Public/StreamChatClientComponent.h
```

### Other rungs

| Source | Use for |
|---|---|
| **Doxygen C++ reference** - https://getstream.github.io/stream-chat-unreal/ | Browsing the class surface when you do not know the header name. |
| **Sample project** - the repo root *is* the sample. `Source/StreamChatSample/` (Team Chat, In-Game Chat, Jumpy Lion, Tutorial), `Source/DocsSamples/` (the snippets behind the docs pages) | Real end-to-end wiring. `StreamChatSampleHud.cpp` is the canonical connect + query + show-UI. |
| **Repo README** - https://github.com/GetStream/stream-chat-unreal#feature-support | The **accurate** feature-support list. Prefer it over the docs introduction page, which is stale on user blocking. |
| **Release notes** - https://github.com/GetStream/stream-chat-unreal/releases | What changed per version. Note the v2.0.0 body names `QueryBlockedUsers`, which does not exist - the method is `GetBlockedUsers`. |

Never present a source-derived API as if it were documented - say where you found it (`Source: Plugins/StreamChat/Source/StreamChat/Public/Channel/ChatChannel.h`).
