# Sendbird → Stream Chat Android migration

A generic, repeatable procedure for migrating an **Android app** (Kotlin / Jetpack Compose /
XML Views) from the **Sendbird Chat SDK** to **Stream Chat**. Written to work on *any* Sendbird
project regardless of how the SDK was integrated — behind Sendbird UIKit (Compose or XML), on the
raw `sendbird-chat` SDK with fully custom UI, via MVVM/MVI, single- or multi-activity, fragments +
Jetpack Navigation or Compose Navigation, or spaghetti. Do **not** assume a specific symbol exists;
**detect the shape** of the integration and re-implement it in place.

Golden rule: **change as little application code as possible.** Preserve the app's architecture,
navigation, and public types. Swap what's *inside* the SDK touchpoints, not the touchpoints.

**Source access.** You have the customer's Sendbird code, this skill, the **public Stream docs**
(getstream.io — fetchable), the **sample app** (`stream-chat-android-compose-sample`, public on
github.com/GetStream/stream-chat-android), and the **SDK source** (same repo). Reference those.
When you need a screen Stream doesn't bundle, the recipe lives in a public **cookbook** (§3.5) —
never invent one, and never reference an internal path.

---

## 0. Detect the integration shape (do this first)

```bash
# Which Sendbird artifacts + symbols, and where?
grep -rn "com.sendbird" --include=*.gradle* .                 # uikit / uikit-compose / sendbird-chat(-ktx)
grep -rn "SendbirdUIKit\|SendbirdChat\|sendbirdGroupChannelNavGraph\|ChannelListFragment\|ChannelFragment\|GroupChannel\|OpenChannel\|MessageCollection\|GroupChannelCollection\|SessionHandler" --include=*.kt .
```

Classify the **UI layer** (this decides the whole migration path — see §3):

| Sendbird UI in the source | Migration path |
|---|---|
| **`uikit-compose`** (`sendbirdGroupChannelNavGraph`, `SendbirdTheme`, Compose screens) | → Stream **Compose bundled screens** (`ChannelsScreen`/`ChannelScreen` + info screens). §3.1 |
| **`uikit`** (XML Views: `ChannelListFragment`, `ChannelFragment`, activities) | → Stream **Compose** hosted in the existing fragments via `ComposeView` (cross-framework, §3.3), **or** Stream XML `ui-components` for a like-for-like Views migration. Compose is the default target. |
| **No UIKit** — custom UI drawn directly on `sendbird-chat` (+ `-ktx`) collections/handlers | → **keep the app's entire UI + architecture**; swap only the SDK layer underneath (§3.2). The surgical path. |
| **Spaghetti** (SDK calls scattered) | Migrate file-by-file; don't refactor unrelated code. |

Then classify **how the SDK is wrapped** — this decides what stays untouched. Migrate each pattern
preserving its **public surface**; callers don't change:

| Pattern in the source | How to migrate |
|---|---|
| **Repository / wrapper** (a class/interface hiding the SDK: `connect()`, `currentUser`, `messages()`) | Keep the interface **unchanged**; reimplement the concrete type against Stream. |
| **ViewModel calling the SDK directly** (`StateFlow`/`LiveData` + methods) | Keep the VM's public surface (exposed state + methods); replace the SDK calls inside. |
| **Singleton / global** (`object Chat`, `X.instance`) | Keep the object and its method signatures; swap the SDK calls inside. |
| **MVI / Redux store** (Intent → pure reducer → State, side effects re-dispatch) | Keep the store shape. The SDK touchpoints are **effects** (connect, send, watch, load) and **derived values** (a query built from state). Effects do the async Stream work **outside** the reducer and re-dispatch result intents; the reducer stays **pure**. (Verified on a real MVI app — this is the cleanest surgical case.) |
| **Direct / inline** (SDK calls straight in Activities/Composables) | Swap the calls in place; keep the surrounding layout + navigation. |
| **Spaghetti** (scattered, no boundary) | Migrate file-by-file; introduce a *thin* boundary only where it reduces churn. Don't rewrite unrelated code. |

Also classify the **architecture** (MVVM / MVI / plain) and **navigation** (single- vs multi-activity;
Compose Navigation vs fragments + Jetpack Navigation). **All of these are preserved** — the migration
never rewrites the architecture or nav host; it only swaps SDK touchpoints inside them.

Note the **shared infrastructure** (SDK init, credentials/config, seeding). That layer always changes.

---

## 0.5 Design & functional fidelity (read every time — it's the part that's always wrong)

Swapping the SDK so the app *builds and connects* is the easy 80%. The migration is judged on the
**last 20%: does each screen look and behave like the Sendbird original?** Those gaps are almost never
visible from the channel **list** — they live **inside the chat screen** (bubbles, alignment, header,
composer, custom cards) and in **screens the source had that a naive swap silently drops** (§3.5). A
green build and a correct channel list are **not** "done".

**The source app IS the spec — build it first if a screen doesn't exist yet.** Never design a migrated
screen from scratch. If you're adding a use-case that has no Sendbird original, build the **Sendbird**
version first (in the source SDK), run and screenshot it, and treat that as the benchmark — then match
it on Stream. Going straight to the Stream version means inventing a design with nothing to check
against, and it will be wrong.

**The FIDELITY MANDATE.** A migration is not an SDK swap that compiles. It must REPRODUCE the source's
design and custom behavior, screen by screen:
- **Theme:** a Sendbird app with "no custom theme" is still not Stream-default. `uikit-compose` uses an
  M3 `SendbirdTheme`; `uikit` (XML) themes from **color resources** (`primary_*` / SBUColorSet family
  in `res/values/colors.xml`). Stream Compose reads **neither** — translate the accent to a
  `StreamDesign.ColorScale` brand + `accentPrimary` (§6). Never accept Stream's default blue.
- **Bubbles:** Sendbird's outgoing bubble is a **solid** accent fill with **white** text. Stream's
  derived bubble tokens are only a *pale tint* of the accent, and Stream's message text **ignores
  `LocalContentColor`** — so you must override both fill and text at the slot level (§6). Set the
  background alone and the text is dark/illegible.
- **Custom message types** (Sendbird `customType` + `data`, e.g. an RSVP/event card): re-implement on
  Stream (§5). Do NOT let them fall back to a plain text bubble.
- **DM names:** a nameless 1:1 must resolve to the other member's name (Sendbird's default), not
  Stream's "Channel" (§4).

**Reuse the design-matching rigor.** The per-screen UI-match craft — decomposing each screen region by
region, the **recolored → theme token / realigned → config / rearranged → `ChatComponentFactory` slot**
triage, composer parity button-by-button, avatars, date separators — is exactly
[`design-matching.md`](design-matching.md). Load it for the look-matching pass: this skill covers the
**SDK migration**, that one covers **matching the look**. The single most common miss is flipping a
theme token when the answer is a **structural slot override** (radius/shape/padding/layout are structure
on Android — there is no Shapes theme axis).

**Derive every value from the source.** Read the Sendbird theme; if the app runs, screenshot it and
**pixel-sample** the accent (don't eyeball a constant). Keep the source APK + baseline screenshots and
compare the migrated app against them, screen by screen, on the real navigation path.

**Verify inside the chat, not just the list.** Open the list AND the chat, with an **incoming and an
outgoing** message visible, and check: outgoing bubble bg+text, incoming bg+text, DM title, header
action, composer button set, custom cards. An incoming-only chat hides the outgoing-bubble bug (the
most common one) — seed an outgoing message before shooting.

---

## 1. Packages + the v7 packaging gotcha

Remove Sendbird; add Stream. The dependency depends on the path you'll pick in §3:

| Path | Stream dependency |
|---|---|
| Bundled screens or cross-framework Compose (§3.1/§3.3) | `io.getstream:stream-chat-android-compose:<v>` |
| Custom UI on the low-level SDK (§3.2) | `io.getstream:stream-chat-android-client:<v>` **only** (no `-compose`) |

**GOTCHA — v7 published packaging differs from the source tree / the SDK's own dev docs.** Verify
against the published artifact (or the sources jar), not the local dev source, before writing imports:
- `stream-chat-android-state` and `-offline` are **NOT published separately** at 7.x (frozen at 6.41.0).
  The whole low-level **state layer is folded into `stream-chat-android-client`.**
- The public state extensions are in **`io.getstream.chat.android.client.api.state`**:
  `queryChannelsAsState`, `watchChannelAsState`, `QueryChannelsState`, `globalState`. (NOT
  `io.getstream.chat.android.state.extensions.*` — that package is absent from the published jar.)
  `ChannelState` is at `io.getstream.chat.android.client.channel.state.ChannelState`.
- The state layer **auto-installs** — a bare `ChatClient.Builder(apiKey, ctx).build()` is enough. Do
  **not** call `withPlugins(StreamOfflinePluginFactory, StreamStatePluginFactory)`; those factories are
  shaded to `client.internal.*` and are not the public path (the SDK sample's `withPlugins` is dev-only).

---

## 2. Initialization & authentication

| Sendbird | Stream |
|---|---|
| `SendbirdChat.init(InitParams(appId, ctx, useCaching, logLevel))` (async, `InitResultHandler`) | `ChatClient.Builder(apiKey, ctx).logLevel(...).build()` — **synchronous**. The async init gate (init-state flow, `InitResultHandler`) **collapses**; there's nothing to wait on. |
| `SendbirdUIKit.init(SendbirdUIKitAdapter{ appId, userInfo, accessToken, InitResultHandler })` (XML) | same — `ChatClient.Builder(...).build()`; the adapter's identity moves to `connectUser` |
| `SendbirdUikitCompose.init(UikitInitParams(appId, …))` (a Flow) + `prepare(UikitCurrentUserInfo)` + `connect()` (uikit-compose) | same — `ChatClient.Builder(...).build()`; the init Flow / `prepare` / `connect` trio collapses into `build()` + one `connectUser(...)` |
| App ID is the only credential | client-safe **API key** + per-user **token** (dev token from `getstream token <id>` for local; backend-issued in prod). Never ship the API secret. |
| `SendbirdChat.connect(userId)` [tokenless test mode] | `chatClient.connectUser(User(id, name), token).await()` — **always token-authed** |
| `connect(userId, authToken)` | `connectUser(User(id, name), token).await()` |
| `SessionHandler.onSessionTokenRequired(requester)` (app-global) | a per-connect **`TokenProvider { loadToken() }`** passed to `connectUser`. NO app-global session handler; Stream calls the provider on connect and on expiry. |
| `updateCurrentUserInfo(nickname)` | set `name` inline on `User(...)` at connect — no separate round-trip |

Every Stream call is a `Call<T>` with two shapes — pick by the source's style:
- **`.await()`** (suspend; in the `stream-result-call` artifact) for a coroutine/suspend source.
- **`.enqueue { result -> }`** or `.enqueue(onSuccess, onError)` (non-suspend) for a **callback-shaped**
  source — usually the smaller diff (map each Sendbird `Handler` callback to an `enqueue` lambda).

**Both return `io.getstream.result.Result<T>` (a sealed `Success`/`Failure`) — they do NOT throw.**
Branch on the result (`result.onSuccess { }.onError { }` or `when (result) { is Result.Success -> …;
is Result.Failure -> … }`); don't wrap in try/catch expecting an exception. So a callback source's
`connect(userId, null, ConnectHandler{ onConnected(user, e) })` → `connectUser(User(id,name), token)
.enqueue { it.onSuccess{…}.onError{…} }` — a near-mechanical 1:1 with the old callback.

---

## 3. UI migration — pick the path from §0, then map screens

Stream Chat Compose bundles these **whole screens** (verified public 7.4.0):
`ChannelsScreen`, `ChannelScreen` (a.k.a. the messages screen), `GroupChannelInfoScreen`,
`DirectChannelInfoScreen` (settings + members + add-members + mute/hide/leave/delete),
`ChannelMediaAttachmentsScreen`, `ChannelFilesAttachmentsScreen`, `MediaGalleryPreviewScreen`,
`CreatePollScreen`, `ChatsScreen` (adaptive multi-pane). It does **NOT** bundle: a channel-**creation**
screen, a dedicated search screen, or standalone threads/mentions/pinned screens (§3.5).

### 3.1 Sendbird `uikit-compose` → Stream Compose bundled screens

| Sendbird | Stream |
|---|---|
| `SendbirdUIKit.init` / `SendbirdUikitCompose` init | `ChatClient.Builder(apiKey, ctx).build()` (§2) |
| `sendbirdGroupChannelNavGraph(navController)` (bundles 6 screens) | app-owned `NavHost` hosting Stream screens (a structural rewrite of ONE file, usually simplifying). Enumerate the 6 slots it exposed and map each (§3.5). |
| `channelsScreen` slot | `ChannelsScreen(viewModelFactory, title, onChannelClick, onHeaderActionClick, onBackPressed)` |
| `channelScreen(channelUrl)` slot | `ChannelScreen(viewModelFactory = ChannelViewModelFactory(context, channelId = cid), onBackPressed, onHeaderTitleClick)`; `channelUrl` → `cid` |
| `channelSettingsScreen` / `membersScreen` / `userInvitationScreen` slots | ONE screen: `GroupChannelInfoScreen`/`DirectChannelInfoScreen` (§3.5) |
| `channelCreationScreen` slot | NOT bundled → cookbook (§3.5) |
| per-screen slots / `MessageItemFactory` | `ChatComponentFactory` slots (§6) |

### 3.2 Custom UI on `sendbird-chat` → keep the UI, swap the data layer (SURGICAL)

If the source drew its own UI (no UIKit), do **not** adopt Stream's bundled screens. Keep 100% of the
app — every screen, the theme, navigation, the MVVM/MVI scaffolding, the domain models — and rewrite
**only** the SDK-touching files (init, auth, the data layer, mappers). Map Sendbird's data layer to
Stream's **state layer** (§4). This is the highest-fidelity path because almost nothing changes.

### 3.3 Sendbird `uikit` (XML) → Stream Compose (cross-framework)

Keep the fragments + Jetpack-Navigation + MVVM architecture. Replace each Sendbird UIKit fragment with
a plain `Fragment` whose `onCreateView` returns a `ComposeView` hosting the Stream Compose screen:

```kotlin
override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View =
    ComposeView(requireContext()).apply {
        setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
        setContent { AppTheme { ChannelsScreen(/* … */) } }   // or ChannelScreen(...)
    }
```

The module runs `viewBinding = true` AND `compose = true` side by side (add the Compose plugin). Route
row clicks through the existing `NavController` exactly as the Sendbird `OnItemClickListener` did
(`channel.url` → `channel.cid`); wire `ChannelScreen(onBackPressed = { findNavController().navigateUp() })`.
Do **not** rewrite to single-activity Compose — this is the realistic incremental-adoption path.

### 3.5 Missing out-of-the-box screens — the GAP-HANDLING PROTOCOL (do NOT skip)

Sendbird UIKit hands the user whole screens **for free** (via `sendbirdGroupChannelNavGraph`'s 6 slots,
or `ChannelFragment`/`ChannelListFragment` default header buttons): channel list, channel, **creation**,
**settings**, **members**, **user invitation**. A naive SDK swap keeps list + channel and **silently
drops the rest** — a regression the user *will* notice. For **every** screen/feature the source exposed
(audit the nav graph / fragment builders / handlers to enumerate what was reachable):

1. **Detect & name it.** State that the Sendbird app had this and a naive migration loses it.
2. **Classify against Stream and respond:**
   - **(a) Stream bundles it** (channel settings/members → `GroupChannelInfoScreen` /
     `DirectChannelInfoScreen`; media/files/pinned): tell the user it IS supported, name the
     composable, and **wire it up** — it was just not auto-wired. Example wire-up:
     ```kotlin
     // In the messages screen: open info from the header (Sendbird's header settings button).
     ChannelScreen(
         viewModelFactory = ChannelViewModelFactory(context, channelId = cid),
         onBackPressed = { nav.popBackStack() },
         onHeaderTitleClick = { channel ->
             val direct = channel.isOneToOne(ChatClient.instance().getCurrentUser())
             nav.navigate("info/${Uri.encode(channel.cid)}?direct=$direct")
         },
     )
     // The info route: DirectChannelInfoScreen for 1:1, else GroupChannelInfoScreen.
     val factory = ChannelInfoViewModelFactory(cid = cid)   // NB: ctor is (cid, optionFilter)
     if (direct) DirectChannelInfoScreen(factory, onNavigationIconClick = { nav.popBackStack() })
     else        GroupChannelInfoScreen(factory, onNavigationIconClick = { nav.popBackStack() })
     ```
     `GroupChannelInfoScreen` handles add-members internally (a fullscreen `AddMembersScreen` dialog),
     so this one hookup restores settings + members + invitation together.
   - **(b) Stream does NOT bundle it** (channel **creation**; a dedicated search screen): this is the
     case to handle explicitly. Message the user CLEARLY, then let them decide:
     > "Your Sendbird app let users create channels from the list's **+** button. Stream Compose
     > doesn't bundle a creation screen out of the box, but it's a documented cookbook recipe:
     > https://getstream.io/chat/docs/sdk/android/compose-cookbook/creating-channels/ . Want me to add
     > it — ported from that cookbook and themed to match? (~1 screen + 1 ViewModel.)"
     On yes, **port from the cookbook** (or the sample app), themed to the app's accent. Never (c)
     silently omit, and never (d) hand-roll from scratch.
3. **Build only from the cookbook or the bundled screen — never from nothing.**

**Cookbook URL pattern** (public docs, fetchable): `https://getstream.io/chat/docs/sdk/android/compose-cookbook/<slug>/`.
Slugs (each maps to a Sendbird customization): `custom-channel-list`, `custom-message-list`,
`custom-channel-header`, `custom-message-composer`, `custom-attachments-picker`, `blocking-users`,
`location-sharing`, `hide-channel-history-before`, **`creating-channels`**. Bundled-component docs live
under `.../compose-ui-components/` (incl. `channel-info`). You can also read the same recipes in the
**sample app** (`stream-chat-android-compose-sample`, e.g. `feature/channel/add`) and verify signatures
in the **SDK source**.

---

## 4. Channels, messages & the state layer

Channel-type mapping applies to **every** path; the state-flow subset (rows 4+) is the **custom-UI
path** (§3.2) — the bundled screens (§3.1/§3.3) drive their own ViewModels, so you only pass filters.

| Sendbird | Stream |
|---|---|
| **Group channel** | `messaging` channel type |
| **Open channel** (public, participants, enter/exit) | **`livestream`** channel type: watch = enter, `watcherCount` = participant count, `stopWatching()` = exit |
| `channelUrl` | `cid` = `"type:id"` |
| `GroupChannelCollection` + `GroupChannelCollectionHandler` | `chatClient.queryChannelsAsState(request, coroutineScope = scope)` → `QueryChannelsState.channels: StateFlow<List<Channel>?>` (add/update/delete events auto-folded; the handler is deleted). Pagination: `state.nextPageRequest.value` → `chatClient.queryChannels(it)`. |
| `MessageCollection` + handler + `initializeFlow` | `chatClient.watchChannelAsState(cid, messageLimit, scope)` → `ChannelState.messages: StateFlow<List<Message>>`; title from `channelState.toChannel()` |
| `GroupChannelListQuery` filters | `QueryChannelsRequest(filter = Filters.and(Filters.eq("type","messaging"), Filters.\`in\`("members", listOf(userId))), offset, limit, querySort = QuerySortByField.descByName("last_message_at"), messageLimit, memberLimit)` |
| `createMyGroupChannelListQuery(...).next()` | membership filter above |
| `GroupChannel.createChannel(params)` | `chatClient.createChannel("messaging", channelId, memberIds, extraData)` — but there's **no bundled creation UI** (§3.5) |
| `channel.sendUserMessage(text)` | `chatClient.channel(cid).sendMessage(Message(text = text)).await()` |
| collection handler channel-deleted | no state flow → keep one typed sub: `chatClient.channel(cid).subscribeFor(ChannelDeletedEvent::class.java) { }` |

**Open-channel *layout* (bundled-UI path, §3.1/§3.3 only).** A Sendbird open channel isn't just
left-aligned bubbles — the cell is **restructured**: a small avatar, the **author name on top**, the
text plainly underneath with **NO bubble**, the row left-aligned full-width. A theme token can't express
that; override the **`ChatComponentFactory` message-item slot** with your own row (the Compose analog of
a custom item view — see §6). **Grouping gotcha:** Stream shows full author info **avatar-at-bottom**
(the newest message of a same-author run), the *opposite* of Sendbird's author-on-top — so render the
author header on **every** message rather than keying off the grouping flag. (The custom-UI path §3.2
keeps the source's own open-channel layout, so this only applies when an open channel renders through
Stream's bundled `ChannelScreen`.)

**Traps:**
- `queryChannelsAsState`'s 2nd positional arg is a `ChatEventHandlerFactory`, so pass
  `coroutineScope = scope` **by name**.
- **The state handles are NESTED flows**: `queryChannelsAsState` returns `StateFlow<QueryChannelsState?>`
  whose `.channels` is itself a `StateFlow<List<Channel>?>` (same for `watchChannelAsState` →
  `ChannelState.messages`). A naive `collect { s -> s.channels.collect { } }` blocks the outer
  collector — use **`flatMapLatest { it?.channels ?: emptyFlow() }`** (then `filterNotNull()`),
  collected from `lifecycleScope` (Activity/Fragment) via `repeatOnLifecycle(STARTED)`.
- **Nameless DM → resolve the other member's name.** In the **bundled-UI path** (§3.1/§3.3) this is a
  `ChannelNameFormatter` on `ChatTheme` — a **Compose-only** API, so do NOT reach for it on the
  **custom-UI path** (§3.2); there you resolve the name **in your own adapter/title** from
  `channel.members` (filter out the current user). Either way the channel **list** query returns
  `members = []` unless you set `memberLimit` on the request — set it so members are hydrated.
- **`Channel.lastMessage` is `internal`** in the published jar — for the list preview use
  `channel.messages.lastOrNull()?.text` (needs `messageLimit` on the request). A source reading
  `channel.lastMessage` maps to this, not to a same-named property.

---

## 5. Messages & custom data (customType / data)

Sendbird carries custom payloads on `message.customType` + `message.data` (a JSON string). Stream has
no `customType` field. Match the carrier to **how the app renders**:

- **Custom-UI app (draws its own message list):** carry the payload on **`Message.extraData`**
  (`mapOf("customType" to "event_rsvp", "eventId" to ..., "response" to ...)`) and render with the
  app's own Compose card, unchanged. `Message.extraData` is the documented custom slot and round-trips.
  **No `AttachmentFactory` needed** — that's only for apps rendering through Stream's bundled
  message list.
- **Bundled-rendering app (uses `ChannelScreen`/`MessageList`):** register a custom `AttachmentFactory`
  (`canHandle = attachment.type == "event_rsvp"`) via `ChatTheme(attachmentFactories = …)`, or override
  a `ChatComponentFactory` message-content slot, to draw the card.

Rule: match the carrier to the renderer. Custom UI → `extraData` + your card. Bundled UI → attachment
type + factory. Send: `channelClient.sendMessage(Message(text = "…", extraData = payload))`.

**Verify the payload survived the round-trip — don't assume.** After sending, confirm your keys come
back:
```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":{"$eq":"<cid>"}},"state":true}'
```
`Message.extraData` is the surviving slot (verified round-tripping an RSVP card), but the server can
drop **unknown top-level** custom fields on some write paths — if you find fields stripped, move the
payload into a **custom attachment type** (whose known fields survive) instead.

Domain-model id types follow the SDK: Sendbird `messageId` is a **Long**, Stream `Message.id` is a
**String** — change the app's model id type accordingly (UI keys/dedup that never assumed numeric survive).

---

## 6. Theming & customization

| Sendbird | Stream |
|---|---|
| `uikit-compose` M3 `SendbirdTheme(lightColorScheme, darkColorScheme)` | `ChatTheme(colors = StreamDesign.Colors.default(brand = <scale>)/.defaultDark())` — light/dark chosen at the call site |
| `uikit` (XML) `primary_*` / SBUColorSet **color resources** | a `StreamDesign.ColorScale` brand + `accentPrimary` in a `ChatTheme` wrapper — Stream does NOT read Android color resources |
| M3 `ColorScheme.primary` (accent) | `StreamDesign.Colors.accentPrimary` + full `brand` ColorScale |
| `SendbirdUIKit.setDefaultThemeMode(Light)` (light-only) | pin the light palette in the theme wrapper regardless of system dark |
| Shapes (M3) / radius / padding | **no Shapes axis on Android** — radius/shape/padding = **structure** → `ChatComponentFactory` slot overrides, never theme tokens |
| `MessageItemFactory` per-type renderers | `ChatComponentFactory` slots (`MessageBubble`, `MessageTextContent`, headers, composer, list items) |

**Solid outgoing bubble + white text** (the always-needed fidelity fix): Stream's bubble tokens only
tint the accent, and its message text ignores `LocalContentColor`. Override two slots:
```kotlin
class BrandComponentFactory : ChatComponentFactory {
    @Composable override fun MessageBubble(p: MessageBubbleParams) {
        if (p.message.user.id == CURRENT_USER_ID)
            Surface(color = BrandAccent, shape = p.shape, modifier = p.modifier) { p.content() }
        else Surface(color = p.color, shape = p.shape, border = p.border, modifier = p.modifier) { p.content() }
    }
    @Composable override fun MessageTextContent(p: MessageTextContentParams) {
        if (p.message.user.id == p.currentUser?.id)
            Text(p.message.text, style = ChatTheme.typography.bodyDefault.copy(color = Color.White),
                 modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))
        else super.MessageTextContent(p)   // incoming keeps default markdown/mentions/links
    }
}
```
**Composite-slot warning:** overriding a composite slot (`MessageContainer`, header, composer) drops
every sub-feature the default drew (avatar, grouping, reactions, status). Read the default's body first
and reproduce them, or override the narrowest slot. For the full region-by-region UI-match procedure,
use [`design-matching.md`](design-matching.md) (§0.5).

---

## 7. Event handlers & unread counts

| Sendbird | Stream |
|---|---|
| `SendbirdChat.addChannelHandler(GroupChannelHandler{ onMessageReceived })` | `chatClient.subscribeFor<NewMessageEvent> { event -> event.message… }` — the **reified** extension (`import io.getstream.chat.android.client.subscribeFor`). The Java `Class<T>` overload erases the listener to `ChatEvent` (can't read `.message`). |
| `getTotalUnreadMessageCount(params, handler)` (polled) | `chatClient.globalState.totalUnreadCount: StateFlow<Int>` — auto-updates, no polling. Live only after `connectUser`. |
| `ConnectionHandler` | `chatClient.clientState.connectionState` flow / `subscribeFor<ConnectedEvent/DisconnectedEvent>` |
| `onTypingStatusUpdated` / read receipts | `ChannelState.typing` / `reads` flows; `keystroke()`/`stopTyping()`, `markRead()` |

---

## 8. Seeding / demo data

Sendbird's client-side multi-user seeding (connect as A, then B, then C — test mode auto-creates them)
**does not map**: the Stream client can only act as the connected user and can't mint others.
- Create users / cross-user messages → **server-side** (`getstream api UpdateUsers`, `GetOrCreateChannel`,
  `UpdateChannel add_members`, `SendMessage user_id=…`) or a backend.
- Channels the current user owns + their own messages → the client can do these.
- **Import member RECORDS, not just `member_count`.** A channel imported with only `member_count` set
  (no member objects) makes the bundled info screen show "0 members" even though the header count looks
  right — verify member lists populate client-side after any data migration.

---

## 9. Pitfalls (build/runtime breakers)

- **v7 packaging** (§1): don't import `io.getstream.chat.android.state.*`; use `...client.api.state.*`.
  Don't `withPlugins(...)`. Verify coordinates against the published artifact / sources jar.
- **`ChannelScreen` owns an internal `BackHandler`** — always wire `onBackPressed` (→ `navigateUp()`)
  so device/header back pops your nav stack.
- **`ChannelInfoViewModelFactory(cid)`** — the published 7.4.0 ctor is `(cid, optionFilter)`, not the
  `(context, cid)` the dev source shows. Always check the sources jar for exact signatures.
- **Extended Material icons** (`Icons.Filled.PersonAdd`) are NOT in the core icons artifact — use core
  (`Person`, `Add`) or add `material-icons-extended`. Cookbook code may reference app-local drawables
  (`R.drawable.ic_member*`) and helpers (`LoadMoreHandler` "left for brevity") — adapt/implement them.
- **Sendbird `OpenChannelCreateParams(String)` sets coverUrl, NOT name** — set `name` explicitly (a
  source-side gotcha when building/reading the baseline).
- Keep the source APK installed and give the migrated build an `applicationIdSuffix` so both coexist for
  side-by-side comparison.

---

## 10. Procedure checklist

1. **Detect** the UI layer + wrapping pattern + architecture + nav; inventory Sendbird touchpoints and
   the bundled screens the source exposed (§0, §3.5).
2. **Pick the path** (§3): bundled screens / custom-UI-surgical / cross-framework.
3. **Swap packages** (§1) — mind the v7 packaging gotcha and pick client-only vs -compose by path.
4. **Credentials:** API key + dev/backend token in the config type (replace the Sendbird App ID). Never
   commit the secret.
5. **Init + connect** (§2): `ChatClient.Builder().build()`; `connectUser(User(id, name), token)`;
   `SessionHandler` → `TokenProvider`.
6. **Migrate each screen** by path (§3), mapping channels/messages/state (§4, §5), preserving the
   source's wrapping pattern (§0).
7. **GAP-HANDLING (§3.5):** for every screen the source exposed that a naive swap dropped — wire the
   bundled equivalent, or (if unbundled) explain it's not out-of-the-box, **link the public cookbook**,
   and **offer to build it** from the cookbook. Never silently drop or invent.
8. **Re-apply theming + custom messages** (§6, §5) — derive every value from the source (§0.5); solid
   bubble bg+text, DM name resolution, custom cards. Match the look with [`design-matching.md`](design-matching.md).
9. **Move seeding server-side** (§8); import member records.
10. **Verify fidelity per screen — inside each chat** (§0.5): list AND chat, incoming AND outgoing,
    against the source. A green build + correct list are not "done".
11. **Offer data migration** (§11) once the code migration builds, connects, and looks right.

---

## 11. Data migration (offer it after the code migration)

The steps above migrate the **code/SDK** — they move **no history**. A migrated app connects to an
**empty** Stream app until seeded or imported. Once it builds, connects, and matches the source design,
**ask** whether to also migrate the Sendbird **data** (users, channels, messages, reactions).

Data migration is **server-side and SDK-independent** (identical for Kotlin/Swift/Flutter/RN), so it
lives in the shared runbook: [`../stream/sendbird-data-migration.md`](../stream/sendbird-data-migration.md).
If the user says yes, read that file and follow it (pick strategy → export → build JSONL → validate →
import via `getstream` CLI: `CreateImportURL` → upload → `CreateImport` → `GetImport`). Do **not** start
a data migration unsolicited — it touches production data. Upload content-type must be
`application/json`. Import member **records**, not just `member_count` (§8).
