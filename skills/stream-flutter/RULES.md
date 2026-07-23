# Stream Flutter - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Secrets and auth

Never hardcode a Stream API secret in app code, `pubspec.yaml`, or chat. The client may hold the **API key** and a **user token**; the **API secret** stays server-side only.

Default token model:

- Use a backend-issued token when the user already has a backend.
- Use a CLI-generated token (`getstream token <user_id>` or `getstream token <user_id> --ttl <duration>`) for local dev and demo flows - this is the preferred path when no backend exists.
- Use a static token only when the user explicitly wants to paste one themselves.
- Never invent or generate fake production credentials.
- The API secret never leaves the CLI/server side; only the API key and the generated token go into app code.

---

## Surface permission prerequisites proactively (Chat)

Permissions are checked on **client-side calls only**; server-side calls (CLI / backend with the secret) bypass them. So seeding works while the same action 403s from the app. **Whenever the app does more than chat inside channels the user already belongs to — discovering channels, self-joining, or signing in as a guest — name the required channel-type grant in the same turn you build the feature**, before any runtime error. Most commonly: `Read Channel` (`ReadChannel`) to browse non-member channels, `Add Own Channel Membership` (`AddOwnChannelMembership`) to self-join; `guest` is stricter than `user` and needs the grants too. Detail and exact error strings: [`references/CHAT-FLUTTER.md`](references/CHAT-FLUTTER.md) → Channel permissions & roles; the proactive prompt lives in [`SKILL.md`](SKILL.md) Step 0.5 → Permissions awareness. This is a heads-up, not a blocker — build the feature, but never let discover/join/guest flows fail silently on first run.

---

## No wrapper or bridge abstractions

Do **not** introduce intermediate types - `ChatManager`, `VideoCallBridge`, `StreamWrapper`, `SDKAdapter`, `FeedsService`, or similar - between the app and the Stream SDK.

Use SDK types directly:

- `StreamChatClient` initialized once before `runApp`
- `StreamChat` widget wrapping the app's widget tree
- `StreamChannel` inherited widget for per-screen channel context
- `StreamChannelListController` stored as a field on a `State` object
- `StreamVideo` initialized once before `runApp`; accessed via `StreamVideo.instance`
- `Call` objects retrieved via `StreamVideo.instance.makeCall(...)` and used directly
- `StreamFeedClient` initialized once before `runApp`; `FlatFeed` / `NotificationFeed` references obtained from `client.flatFeed(...)` / `client.notificationFeed(...)`
- `FeedBloc` wrapped in `FeedProvider` and accessed via `FeedProvider.of(context).bloc`

The only exception is a thin service class to isolate initialization when the app uses multiple Stream products.

---

## Project ownership

Preserve the app's existing architecture:

- Do **not** convert existing navigation patterns (GoRouter, auto_route, Navigator) unless the user asks.
- Do **not** replace existing state management (Provider, Riverpod, Bloc) unless the user asks.
- Do **not** flatten existing widget trees just to fit a sample pattern.

If there is **no Flutter project**:

- When the user **explicitly asks to create/build a new app** (Track A — e.g. "create a Flutter app that…"), scaffold it yourself: `flutter create --org <reverse.domain> --project-name <name> --platforms android,ios <dir>`. Creating the project _is_ the request — don't bounce it back. An empty, pre-named directory (e.g. `ringing/`) is a strong signal of where it should go.
- Otherwise (the user wants integration/setup but no app exists yet), do **not** scaffold silently. Tell them to run `flutter create my_app` first, then continue.

---

## Client lifetime

Initialize Stream SDK clients once, before `runApp`. Never create them:

- inside a `build` method
- in a `StatelessWidget` body
- in a computed getter that re-runs on rebuild

**Chat:** `StreamChatClient` initialized once before `runApp`. `StreamChat` must appear in the widget tree before any Stream Chat widget renders - typically as a `builder` wrapper around `MaterialApp`. If the user switches accounts, call `await client.disconnectUser()` before connecting the next one.

**Video:** `StreamVideo(...)` initialized once before `runApp`. It registers a singleton - access it anywhere with `StreamVideo.instance`. Accessing `StreamVideo.instance` before construction throws a `StateError`. If the user switches accounts, tear the singleton down with `await StreamVideo.reset(disconnect: true)` **before** constructing a new `StreamVideo(...)` - the constructor throws `failIfSingletonExists` otherwise. See [`references/VIDEO-FLUTTER.md`](references/VIDEO-FLUTTER.md) -> Switching users / resetting the client.

**Feeds:** `StreamFeedClient('apiKey')` initialized once before `runApp`. Call `await client.setUser(user, token)` before any feed operation. Wrap the widget tree with `FeedProvider(bloc: FeedBloc(client: client), child: ...)` when using `stream_feed_flutter_core`. Cancel all feed subscriptions in `dispose()`.

---

## UI and concurrency

Stream SDK callbacks and `async` methods return on the main isolate by default - do not `compute()` or `Isolate.spawn()` Stream work unless it is confirmed CPU-bound.

Prefer `StreamBuilder` and `ValueListenableBuilder` for reactive UI over manual `setState` + stream subscription management. Always cancel stream subscriptions in `dispose()`.

---

## Feeds UI — no pre-built components

The Stream Feeds SDK (`stream_feed`, `stream_feed_flutter_core`) ships **no UI widgets**. Every feed screen, activity card, like button, and follow button must be built with standard Flutter widgets.

- Default to Twitter-style UI. Build it immediately without asking — do not pause to confirm the style.
- Only deviate from Twitter-style when the user explicitly states a different preference (e.g., "Instagram grid", "Reddit-style votes", "photo-first").
- The UI style only affects widget composition — the SDK calls (activities, reactions, follow/unfollow) are the same regardless of style.

---

## Reference discipline

Load only the product/package reference files that match the request.

- `CHAT-FLUTTER.md` + `CHAT-FLUTTER-blueprints.md` for Chat with pre-built UI (`stream_chat_flutter`)
- `CHAT-CORE.md` + `CHAT-CORE-blueprints.md` for Chat with custom UI (`stream_chat_flutter_core`)
- `CHAT-ADVANCED-FLUTTER.md` + `CHAT-ADVANCED-FLUTTER-blueprints.md` for advanced Chat concerns — push notifications, offline/local persistence, connection lifecycle & backgrounding (both UI tiers)
- `VIDEO-FLUTTER.md` + `VIDEO-FLUTTER-blueprints.md` for Video calling (`stream_video_flutter`)
- `LIVESTREAM-FLUTTER.md` + `LIVESTREAM-FLUTTER-blueprints.md` for Livestreaming (host/viewer flows, backstage, HLS)
- `VIDEO-ADVANCED-FLUTTER.md` + `VIDEO-ADVANCED-FLUTTER-blueprints.md` for advanced Video use cases (audio rooms, multicall, chat+video, livestream feed, querying/events/preferences/moderation)
- `RINGING-FLUTTER.md` + `RINGING-FLUTTER-blueprints.md` for ringing / incoming calls with push (CallKit on iOS, FCM on Android, foreground/background/terminated handling)
- `FEEDS-FLUTTER.md` + `FEEDS-FLUTTER-blueprints.md` for Activity Feeds (`stream_feed` / `stream_feed_flutter_core`)

Do not invent missing API details. If a requested pattern is not bundled yet, say so plainly and fall back to guidance from [`sdk.md`](sdk.md) or live docs only when the user wants that.

---

## Design fidelity

- **Matching a reference design is not a theming task — there are TWO axes.** When the request carries a target appearance (a screenshot, a Figma frame, "make it look like <app>" — or a migration's source-app baseline), run [`design-matching.md`](design-matching.md) and decompose every region first. Setting the bubble color and wallpaper and stopping is the known failure — the composer button set, the metadata placement (author name / timestamp / receipts relative to the bubble), the bubble tail, the header, and the date-separator pill are all **structural** and need widget replacement (component-builder slots / per-widget builders), not a theme token. The grouped 1/2/3/4+ photo collage, by contrast, is already the default — do not rebuild it. The two axes: **theming** (`StreamTheme` for foundations + the message row and every leaf widget; `StreamChatThemeData` for the chat composite widgets only) and **structure** (the component factory — core slots on `StreamComponentBuilders`, chat slots via `streamChatComponentBuilders(...)` — plus per-widget builders). Routing a problem to the wrong axis is the core failure mode.
- **Padding / insets / corner radius are theme VALUES, never a reason to replace a widget.** They live on `StreamTheme.messageItemTheme` (`bubble.padding`, `text.padding`, `attachment.padding`, shapes) and friends — and those are content-kind-resolved `StreamMessageLayoutProperty` values, so override with `resolveWith(...)` preserving the branches you aren't changing, not a flat constant. If a token isn't on `StreamChatThemeData`, it lives on `StreamTheme` — check both before concluding it doesn't exist.
- **Overriding a composite slot drops every sub-feature the default rendered.** `messageItem` / `messageBuilder`, `messageComposer` (+ its input sub-slots), and `itemBuilder` each draw many things internally: the incoming-message avatar, grouping, reactions, replies, delivery status — or, for the composer input trailing, the send / voice / confirm-edit / slow-mode state machine. A near-empty test channel hides the loss. Before overriding one, read the default widget's `build()` in the pinned source, enumerate every sub-view, and reproduce each (reuse the SDK's public sub-widgets) or tell the user what you dropped. And **never return a public widget from its own slot override** (`StreamMessageItem.fromProps`, `StreamMessageBubble`, `StreamMessageComposerInput`) — it re-enters the factory and stack-overflows; wrap the barrel-exported `Default*` terminal widget instead.
- **Keep one reaction type→emoji map.** Flutter has no global SDK reaction-emoji config, so every custom reaction UI (row pills, picker, overlay) must read a single app-level `Map<String, String>` — per-view literals desync the surfaces.
- **Match dimensions by MEASURING, not eyeballing — then verify and iterate.** The reference is a spec: reproduce header height, font/icon sizes and weights, paddings, corner radius, and alignment — not just colors and presence. Find the screenshot's scale (`sips -g pixelWidth -g pixelHeight`; ÷2/÷3 for iOS shots, ÷ the density bucket for Android) and work in logical pixels — the numbers Flutter APIs take directly. A match is unverified until you build, seed data that triggers **every** region (incoming + outgoing, a same-author run so grouping/avatars show, album, reactions, reply, long text, date separator), open the real screen, measure your render against the reference at the same scale, and iterate region by region until each passes ([`design-matching.md`](design-matching.md) Steps 1 + 5).

---

## Never assume a default

Never assume a widget's default behavior, what a callback does, what a theme token controls, or that two widgets auto-wire to each other (a message list and a composer do not). Ground the claim against the pinned SDK source, or drive it on the device and watch it happen. Unverified assumptions about defaults are where migrations and design-matches silently lose features.
