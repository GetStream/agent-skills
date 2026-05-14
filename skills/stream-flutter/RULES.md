# Stream Flutter - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Secrets and auth

Never hardcode a Stream API secret in app code, `pubspec.yaml`, or chat. The client may hold the **API key** and a **user token**; the **API secret** stays server-side only.

Default token model:

- Use a backend-issued token when the user already has a backend.
- Use a CLI-generated token (`stream token <user_id>` or `stream token <user_id> --ttl <duration>`) for local dev and demo flows - this is the preferred path when no backend exists.
- Use a static token only when the user explicitly wants to paste one themselves.
- Never invent or generate fake production credentials.
- The API secret never leaves the CLI/server side; only the API key and the generated token go into app code.

---

## No wrapper or bridge abstractions

Do **not** introduce intermediate types - `ChatManager`, `VideoCallBridge`, `StreamWrapper`, `SDKAdapter`, or similar - between the app and the Stream SDK.

Use SDK types directly:

- `StreamChatClient` initialized once before `runApp`
- `StreamChat` widget wrapping the app's widget tree
- `StreamChannel` inherited widget for per-screen channel context
- `StreamChannelListController` stored as a field on a `State` object
- `StreamVideo` initialized once before `runApp`; accessed via `StreamVideo.instance`
- `Call` objects retrieved via `StreamVideo.instance.makeCall(...)` and used directly

The only exception is a thin service class to isolate initialization when the app uses multiple Stream products.

---

## Project ownership

Preserve the app's existing architecture:

- Do **not** convert existing navigation patterns (GoRouter, auto_route, Navigator) unless the user asks.
- Do **not** replace existing state management (Provider, Riverpod, Bloc) unless the user asks.
- Do **not** flatten existing widget trees just to fit a sample pattern.

If there is **no Flutter project**, do not try to scaffold one. Tell the user to run `flutter create my_app` first, then continue.

---

## Client lifetime

Initialize Stream SDK clients once, before `runApp`. Never create them:

- inside a `build` method
- in a `StatelessWidget` body
- in a computed getter that re-runs on rebuild

**Chat:** `StreamChatClient` initialized once before `runApp`. `StreamChat` must appear in the widget tree before any Stream Chat widget renders - typically as a `builder` wrapper around `MaterialApp`. If the user switches accounts, call `await client.disconnectUser()` before connecting the next one.

**Video:** `StreamVideo(...)` initialized once before `runApp`. It registers a singleton - access it anywhere with `StreamVideo.instance`. Accessing `StreamVideo.instance` before construction throws a `StateError`. If the user switches accounts, construct a new `StreamVideo` instance after disposing of the previous one.

---

## UI and concurrency

Stream SDK callbacks and `async` methods return on the main isolate by default - do not `compute()` or `Isolate.spawn()` Stream work unless it is confirmed CPU-bound.

Prefer `StreamBuilder` and `ValueListenableBuilder` for reactive UI over manual `setState` + stream subscription management. Always cancel stream subscriptions in `dispose()`.

---

## Reference discipline

Load only the product/package reference files that match the request.

- `CHAT-FLUTTER.md` + `CHAT-FLUTTER-blueprints.md` for Chat with pre-built UI (`stream_chat_flutter`)
- `CHAT-CORE.md` + `CHAT-CORE-blueprints.md` for Chat with custom UI (`stream_chat_flutter_core`)
- `VIDEO-FLUTTER.md` + `VIDEO-FLUTTER-blueprints.md` for Video calling (`stream_video_flutter`)
- `LIVESTREAM-FLUTTER.md` + `LIVESTREAM-FLUTTER-blueprints.md` for Livestreaming (host/viewer flows, backstage, HLS)

Do not invent missing API details. If a requested pattern is not bundled yet, say so plainly and fall back to guidance from [`sdk.md`](sdk.md) or live docs only when the user wants that.
