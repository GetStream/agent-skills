# Stream Flutter - building a CUSTOM chat UI on `stream_chat_flutter_core` (livestream / bespoke surfaces)

Some chat UIs are **not** a messenger. Livestream chat (Twitch / YouTube / Kalshi), live-shopping ticker chat, an overlay on a video, a betting feed, a high-volume "drop" room - these look nothing like channel-list + bubbles + composer, and the pre-built `stream_chat_flutter` widgets fight you the whole way. For these you **drop the pre-built widgets and build your own Flutter widgets on the low-level `StreamChatClient` + the headless `stream_chat_flutter_core` controllers**.


This page is the procedure for that path - the mirror image of [`design-matching.md`](design-matching.md) (which is for *customizing the pre-built components*). Run it only when the decision in Step 0 lands on "custom". It targets `stream_chat_flutter` / `stream_chat_flutter_core` **v10**; confirm every symbol against the live core docs ([`docs-map.md`](docs-map.md) "Chat") and the project's pinned version (see "Grounding" at the end).

---

## Step 0: Decide components vs. custom - and LEAN HARD toward components

> The components-vs-custom decision is made in [`SKILL.md`](SKILL.md) Step 0 ("Chat only: pick the UI strategy first") - that is the canonical rubric, and you do **not** need to open this file to make it. This section recaps and expands it for when the decision has already landed on custom (or you arrived here directly).

This decision is the whole ballgame. Get it wrong toward custom and you throw away avatars, grouping, reactions, threads, attachments, typing, read state, slow-mode, the composer with its attachment pickers and voice notes - dozens of built, tested widgets - to rebuild a worse messenger by hand. Get it wrong toward components and you spend a day fighting the framework to force a shape it was never meant to take. **The first mistake is far more common and far more expensive, so the default is components.** Custom is the exception you justify, not the reflex.

**Default to the pre-built components ([`design-matching.md`](design-matching.md)).** Choose custom **only** when the design is genuinely not a messenger. Decide from concrete signals, not vibes:

| Signal in the screenshot / requirements | Points to |
|---|---|
| Message **bubbles** (incoming left / outgoing right), or could be styled into them | **Components** |
| A **channel list** -> tap -> conversation, or any 1:1 / small-group DM | **Components** |
| Per-message **avatar + name + timestamp + read receipts**, replies, reactions, attachments | **Components** |
| The ask is "make our chat look like **WhatsApp / iMessage / Telegram / Slack / Messenger / Discord DMs**" | **Components** (it's a tweak - the two axes: theming + a few component-builder slots) |
| Workplace / support / marketplace / social / dating chat | **Components** |
| A **flat, author-inline, bubble-less** feed (name in bold then text on one wrapping line), a la live chat | **Custom** |
| **No outgoing/incoming distinction** - every message rendered identically, regardless of sender | **Custom** |
| Chat is an **overlay / ticker / sidebar** on top of video or a non-chat surface, or shares the screen with bespoke app chrome (odds, product cards, reactions raining up) | **Custom** |
| **Very high volume + ephemeral** (hundreds of msgs/min, public viewers, nothing persisted) | **Custom** |
| Anonymous / guest **read-only viewers** vastly outnumber posters | **Custom** (and `livestream` channel type) |

**The litmus test:** *if you could get there with the two axes - theming (`StreamTheme` + `StreamChatThemeData`) + a few component-builder slots - it is a components job.* Only when matching the design through the components would mean **overriding the message row, the composer, the header, AND the list all at once into shapes they resist** - i.e. you're using the SDK only as a data source, not for any of its widgets - does custom win. When the count of widgets you'd have to fully replace approaches "all of them", that is the signal to drop to the core layer instead. When genuinely unsure, **build the components version first** - it's faster to confirm-or-reject than to discover mid-custom-build that a tweak would have done.

Note that "livestream" / "live-shopping" are **signals, not labels** - they route to custom because their *typical* shape matches the rows above (flat identical rows, overlay/ticker, high volume, read-only viewers), not because of the vertical's name. A livestream app that actually wants a normal bubble/channel-list chat panel stays on **components**.

If still ambiguous, ask one question (from [`SKILL.md`](SKILL.md)):
> Does this chat look like a standard messenger (channel list + bubbles), or a bespoke surface like livestream/overlay chat? It decides whether we customize the pre-built components or build custom UI on `stream_chat_flutter_core`.

State the decision and the signals that drove it before writing code. If the answer is **components**, stop here and go to [`design-matching.md`](design-matching.md) (read its procedure half in full - everything above the `# Reference` divider, which may span two Reads; its Reference half is per-region lookup). The rest of this page is the custom path.

---

## Step 1: Depend on the right packages (custom != `stream_chat_flutter`)

The custom path uses **`stream_chat_flutter_core`** (headless controllers and `*Core` builder widgets) on top of the low-level `stream_chat` client, which it re-exports (`StreamChatClient`, `User`, `Message`, `Channel`, `Filter`, ...). Add it with `flutter pub add stream_chat_flutter_core` and follow the "Getting started, core / custom UI" docs ([`docs-map.md`](docs-map.md)). Keep `stream_chat_flutter` out of this screen - reaching for `StreamChannelListView` / `StreamMessageListView` / `streamChatComponentBuilders` / `StreamChatThemeData` means you have drifted back onto the components path.

---

## Step 2: Pick the data source - `MessageListCore` over one `Channel`

`stream_chat_flutter_core` gives you **headless, builder-based** access to Stream data - the `*Core` widgets expose state + pagination through a `builder` callback with **no UI of their own**, so you render every pixel. For a single bespoke channel (a livestream feed, an overlay), the path is:

1. Own one `Channel` and provide it to the subtree with the **`StreamChannel`** inherited widget. `StreamChannel` calls `channel.watch()` on init when the channel is uninitialized - it subscribes to the channel's events and loads the first page for you (the WebSocket comes from `connectUser`) - and descendants read the channel via `StreamChannel.of(context).channel`.
2. Render the messages with **`MessageListCore`**, the headless message-list widget (docs: "Custom message list state (core)" in [`docs-map.md`](docs-map.md)). It reads the channel from the nearest `StreamChannel` and hands you the message list - plus loading / empty / error states and pagination - through builder callbacks:

```dart
MessageListCore(
  loadingBuilder: (context) => const Center(child: CircularProgressIndicator()),
  emptyBuilder:   (context) => const SizedBox.shrink(),
  errorBuilder:   (context, error) => Center(child: Text('$error')),
  messageListController: _messageListController, // MessageListController(), drives pagination
  messageListBuilder: (context, messages) => LiveFeed(messages: messages),
  paginationLimit: 25,
  maximumMessageLimit: 200, // caps messages kept in memory - see high-volume note below
)
```

`messageListBuilder` receives a `List<Message>` newest-first, ready for a bottom-anchored (`reverse: true`) list.

**High-volume feed (hundreds of msgs/min).** Keep it lean:
- Cap memory with `MessageListCore(maximumMessageLimit: N)` - older messages are trimmed as new ones arrive, so the feed stays light no matter how long it runs.
- Keep local persistence off (Step 3), so a hot feed does no per-message disk writes.
- Watch the `livestream` channel and render the SDK's native message order - render the list as delivered instead of re-sorting on every update.
- Pace the write path with slow mode (Step 5).

---

## Step 3: Connect the client - tune it for the vertical, and pick the viewer auth

Initialize the client **once** in an owned place (a service / provider / singleton), never in a widget `build()` ([`RULES.md`](RULES.md) "Client lifetime"), and provide it with `StreamChatCore` (wrap via `MaterialApp(builder: (context, child) => StreamChatCore(client: client, child: child!))` - its `child` is non-null). `StreamChatCore` turns off client-level state recovery, so listen for `EventType.connectionRecovered` and re-`watch()` the channel - see "`StreamChatCore` / reconnect recovery" in [`docs-map.md`](docs-map.md). Do **not** attach a persistence client: the default in-memory client is exactly right for an ephemeral, high-volume feed.

**Viewer auth - match it to whether the viewer posts** (see [`RULES.md`](RULES.md) "Permissions" and "Guest / anonymous users" in [`docs-map.md`](docs-map.md)). All three return a `Future<OwnUser>`:
- Read-only viewers (the majority on a livestream): `await client.connectAnonymousUser();` - no MAU cost, reads `livestream` channels.
- Pre-account viewers who post a little: `await client.connectGuestUser(User(id: 'guest-123'));` - only after you grant `create-message` (plus `create-reaction` etc.) to `guest` on the `livestream` type; by default guests can only read.
- A signed-in user who posts: `await client.connectUser(User(id: 'alice', name: 'Alice'), token);` with a backend/CLI token.

**Channel type:** use **`livestream`** (no membership gate: public read for guests and anonymous viewers, write for `user`):

```dart
final channel = client.channel('livestream', id: 'game5');
```

Set the per-message throttling knobs (slow mode, read/typing events) on the channel type **server-side** - Stream Dashboard -> Chat -> Channel Types, or the CLI / API - so they apply before the feed scales. Read the "Livestream chat" docs ([`docs-map.md`](docs-map.md)) before scaling.

---

## Step 4: Render the feed - observe state, render newest-at-bottom

Own the `Channel` in your service/provider, let `MessageListCore` observe it, and return a `ListView.builder(reverse: true, ...)` of `LiveMessageRow`s from `messageListBuilder` - the list arrives newest-first, so index 0 sits at the bottom. Load older history at the top with `_controller.paginateData?.call(direction: QueryDirection.top)`.

**Message row - this is where livestream diverges most from a messenger.** No bubbles, no left/right split, no read receipts. The common shape is **avatar + bold author name inline with the message text**, wrapping as one paragraph. Build it with a single `Text.rich` so the name and body flow and wrap as one block:

```dart
class LiveMessageRow extends StatelessWidget {
  const LiveMessageRow({super.key, required this.message});
  final Message message;

  @override
  Widget build(BuildContext context) {
    final author = message.user?.name ?? message.user?.id ?? '';
    const fontSize = 15.0; // MEASURE from the reference - see below
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: fontSize * 1.3, // first-line height -> the avatar centers on the name line
            child: LiveAvatar(user: message.user, size: 22),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text.rich(TextSpan(children: [
              TextSpan(
                text: '$author ',
                style: const TextStyle(fontSize: fontSize, fontWeight: FontWeight.w700),
              ),
              TextSpan(
                text: message.text ?? '',
                style: const TextStyle(fontSize: fontSize, fontWeight: FontWeight.w300),
              ),
            ])),
          ),
        ],
      ),
    );
  }
}
```

Pull fields off `Message`: `.text`, `.user` (`User` -> `.name`, `.image`, `.id`), `.createdAt`, `.id`, `.type` (branch on `MessageType.system` / `MessageType.deleted` if the design shows them). `User.name` falls back to the id when unset, so `message.user?.name ?? message.user?.id` is a safe author label.

> **A custom feed is still a design match - apply [`design-matching.md`](design-matching.md)'s rigor to it, do NOT eyeball.** "Render a name + text" is not the spec; the reference's exact **font size**, **weight**, **color**, **avatar size**, and **row spacing** are. Building a custom row does not exempt you from measuring - it's the opposite, because here there are no SDK defaults to fall back on, so every number is yours to get right. Concretely:
> - **Font size: MEASURE it** off the reference (the scale + ink-height method in [`design-matching.md`](design-matching.md) "How to actually get the dimensions right" - `sips` for scale, then measure). Live-chat text is typically **~14-15 lp**, not the 17 you'll guess.
> - **Weight: measure the username and the body SEPARATELY - they are usually different weights, and the body is lighter than your reflex.** The single biggest "the font is off" cause on this path is painting the whole row in one weight (or defaulting the body to `FontWeight.w400` without checking). The author name is the emphasis (often `w600`/`w700`); the **body is lighter - frequently `w300`, not `w400`.** Measure each per [`design-matching.md`](design-matching.md) "Weight is its own dimension" (horizontal dark-run width = stroke thickness), map the **stroke / font-size ratio** to a `FontWeight` using the table there, and set the two `TextSpan`s' `fontWeight` independently. Re-measure your own render and iterate.
> - **Text color: SAMPLE it** ([`design-matching.md`](design-matching.md) "Follow EVERY color from the reference"). It is very often a **soft near-black** (measured cores ~`#191919`/`#1C1C1C`). Sample the darkest stroke cores and use that exact value rather than `Colors.black` / the default `textTheme` color; check whether the username and body share one color or differ.
> - **Avatar size: MEASURE the diameter.** Livestream avatars are **small** (~20-26 lp - about one text line tall), far smaller than the ~32-40 lp you'd reach for. Oversized avatars are the most obvious custom-feed tell. Match the measured diameter and the small leading inset (~4-12 lp). For a measured, off-bucket size or a square avatar, build a small custom avatar: a `CircleAvatar` / `ClipRRect` around the image with a colored-initial fallback.
> - **Avatar vertical alignment + row spacing are part of the spec.** Center the avatar on the **first text line** (the name line), not the whole multi-line block. **Center it by construction: top-align the row and constrain the avatar to the first line's height** - a `Row(crossAxisAlignment: CrossAxisAlignment.start)` with the avatar wrapped in a `SizedBox(height: <first-line height>)` - so it centers on the name line while the body wraps beneath it. (Pushing the text down with top padding only lines up single-line messages and shifts the avatar off-center, so prefer the framed-height approach.) Then **verify the centering by measurement** (avatar center-Y vs the name glyphs' center-Y ~ 0), per [`design-matching.md`](design-matching.md)'s centering rule.
>
> Then verify with a **same-scale side-by-side crop** ([`design-matching.md`](design-matching.md) Step 5's crop-and-compare): stack your rendered feed against the reference at native scale and compare size/weight/color/avatar - numbers alone won't catch "it still looks bigger/heavier."

**Ordering + scroll.** `MessageListCore` gives you the messages newest-first; render them in a `reverse: true` `ListView` so the newest sits at the bottom above the composer. Scroll to the bottom when a new message arrives (animate a `ScrollController` to `0.0`, which is the bottom in a reversed list). Page older history in at the top with `_controller.paginateData?.call(direction: QueryDirection.top)`.

---

## Step 5: Compose + send

Build a plain `TextField` + button, clear the `TextEditingController` optimistically, and post with `channel.sendMessage(Message(text: body))` ("Send / edit / delete messages" in [`docs-map.md`](docs-map.md)).

**Slow-mode cooldown.** When the design shows it, gate the send button on the per-user cooldown and show a countdown:

```dart
// In the composer's State (import 'dart:async').
Timer? _ticker;
int _remaining = 0;

void _tickCooldown() {
  _ticker?.cancel();
  _remaining = channel.getRemainingCooldown(); // seconds; 0 when clear
  if (_remaining == 0) return;
  _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
    setState(() => _remaining = channel.getRemainingCooldown());
    if (_remaining == 0) _ticker?.cancel();
  });
}
// after each send: setState(_tickCooldown); dispose: _ticker?.cancel();
// while _remaining > 0: disable the send button and show "Wait ${_remaining}s"
```

`getRemainingCooldown()` is computed on demand and `channel.cooldownStream` emits the configured slow-mode duration, so the periodic `Timer` drives the countdown. `getRemainingCooldown()` already returns 0 for users who can skip slow mode. Show the composer for signed-in users (and for guests only if you granted them `create-message` on the channel type); give anonymous read-only viewers the feed without a composer.

---

## Step 6: Reuse Stream's UI primitives only when they earn their keep, not by reflex

For a **self-contained** custom surface (one livestream screen with no other Stream UI), plain Flutter is usually cleaner and more robust: `CachedNetworkImage` / `CircleAvatar` for avatars (with a colored-initial fallback so the feed looks right while images load or offline), system fonts, your own colors.

Reach for `stream_chat_flutter`'s theme tokens / `StreamUserAvatar` when you specifically want your custom surface to **align with a sibling components screen** in the same app - same spacing / radius / colors, its image cache, or its avatar handling. That is the reason to pull the pre-built UI package into an otherwise-headless screen; for avatars + text alone, a dozen lines of stock Flutter render the feed fine.

---

## Step 7: Pitfalls specific to the custom path

- **This is a single immersive screen, not a pushed channel.** There's no channel-list -> push and usually no nested navigation - build a **custom header widget** (back button, title, live badge, actions) as an ordinary widget at the top of your `Column` (or a plain `AppBar`).
- **A centered title MUST be bounded so it can't overlap the trailing controls.** A centered title given only symmetric horizontal padding runs under the action icons on a long channel name, because symmetric padding doesn't reserve the icons' width. Use a **3-zone `Row`** that reserves equal side widths (each >= the wider side cluster), with the centered title in an `Expanded` bounded by the two fixed-width side boxes and `maxLines: 1` + ellipsis:
  ```dart
  const side = 76.0; // >= the wider of {back button} and {trailing cluster}
  Row(
    crossAxisAlignment: CrossAxisAlignment.center,
    children: [
      SizedBox(width: side, child: backButton),
      Expanded(
        child: Column(children: [
          Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center),
          liveBadge,
        ]),
      ),
      SizedBox(width: side, child: Align(alignment: Alignment.centerRight, child: trailingCluster)),
    ],
  )
  ```
  Measure the title font from the reference too (usually a modest ~16-17 lp).
- **The app's own chrome is not Stream.** A betting bar, product cards, a video player, reactions - those are your app's widgets sitting above/below the chat. Build them as normal Flutter; only the message feed + composer talk to the SDK. Keep the SDK out of those files.
- **Resolve the channel title from the model, not the screenshot.** Use `channel.name` (it reads `extraData['name']`), then a sensible fallback. Reuse the shared `resolveChannelName(...)` helper from [`design-matching.md`](design-matching.md) "Model-driven title trap".
- **Own the client + channel lifetime; create them once, not in a `build()`.** Create the `StreamChatClient` and the `Channel` once in the owned service/provider, so a rebuild reuses the same references rather than re-watching each frame ([`RULES.md`](RULES.md) -> "Client lifetime").
- **Keep the feed live with `watch()`.** The `StreamChannel` widget watches the channel on init; if you hold the `Channel` yourself outside that widget, call `channel.watch()` once in your service so new messages stream into state. (A one-shot `query` without `watch` shows a static snapshot.)
- **Observe the channel state directly.** Render straight from `MessageListCore` (or `channel.state!.messagesStream`) so a hot feed stays fast - one source of truth, no extra copy of the message list per update.
- **Mind the message `type`.** `livestream` feeds contain `system` / `deleted` / `ephemeral` messages; render or filter them deliberately by `message.type` rather than drawing them as normal lines.

---

## Step 8: Verify against the reference (mandatory, same rigor as the components path)

A custom UI is not done until it builds, runs against **real seeded data**, and matches the reference region by region. **Run [`design-matching.md`](design-matching.md) Step 5's verification gate against this screen - adversarial (find where they DIFFER), cropping and diffing BOTH the reference and your own render; it applies verbatim.** The steps below are the custom-path specializations of it:

1. **Seed a `livestream` channel** with realistic, varied content (multiple authors, short and long/wrapping messages, emoji) via the CLI (server-side, so it bypasses client permissions):
   ```bash
   # authors
   getstream api UpdateUsers --request '{"users": {
     "alice": {"id": "alice", "name": "Alice"},
     "bob":   {"id": "bob",   "name": "Bob"}
   }}'
   # livestream channel
   getstream api GetOrCreateChannel --type livestream --id game5 \
     --request '{"data": {"created_by_id": "alice", "custom": {"name": "Game 5: New York at San Antonio"}}}'
   # one message per line (repeat with varied text + user_id)
   getstream api SendMessage --type livestream --id game5 \
     --request '{"message": {"text": "lets go fire", "user_id": "alice"}}'
   ```
2. **Run on a pinned device/simulator with hot reload**, and **wait for connect + the initial fetch to finish** before screenshotting (a too-early shot catches the "connecting" state).
3. **Measure the reference** (`sips`; divide by the scale factor to logical pixels) for the repeating elements - avatar diameter, row spacing, composer height, any app-chrome bar - and match them, don't eyeball (see [`design-matching.md`](design-matching.md) "How to actually get the dimensions right").
4. **Compare every region** - header (back/title/badge/actions), the feed row layout, the composer, and the app chrome - PASS/FAIL, and iterate until each passes. Implement **every** region, the composer and app chrome included - no "known gaps" ([`design-matching.md`](design-matching.md) Step 5's "no known gaps" rule applies to custom UIs too).
5. Delete any throwaway verification scaffolding before delivery.

---

## Grounding (do not guess controller / client signatures)

Per [`RULES.md`](RULES.md) "Docs discipline": confirm every symbol above against the project's **pinned** version - the core-layer and low-level-client APIs move between releases. Fetch the core docs first (the "Custom message list state (core)", "`StreamChatCore` / reconnect recovery", "Send / edit / delete messages" and "Slow mode" rows in [`docs-map.md`](docs-map.md)), then escalate to the pinned source:

```bash
# package roots of the pinned versions, from the resolved package graph (run `flutter pub get` first)
root() { jq -r --arg n "$1" '.packages[] | select(.name == $n) | .rootUri' .dart_tool/package_config.json | sed 's|^file://||'; }
CORE="$(root stream_chat_flutter_core)/lib/src"
LLC="$(root stream_chat)/lib/src"
# core: headless message list + pagination direction
grep -rn "class MessageListCore\|paginateData\|enum QueryDirection\|maximumMessageLimit" \
  "$CORE/message_list_core.dart" "$CORE/stream_channel.dart"
# client: connect + auth
grep -rn "connectAnonymousUser\|connectGuestUser\|Future<OwnUser> connectUser" "$LLC/client/client.dart"
# channel: live stream, send, slow mode
grep -rn "messagesStream\|getRemainingCooldown\|cooldownStream\|Future<SendMessageResponse> sendMessage" \
  "$LLC/client/channel/"
```

Say where you found anything source-derived rather than presenting it as documented.
