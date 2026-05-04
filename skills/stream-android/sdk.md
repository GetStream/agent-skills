# Stream Android - shared SDK patterns

This file holds the shared Android patterns that cut across Chat, Video, and Feeds. Load it before product-specific references when you need lifecycle, auth, or architecture guidance.

---

## App shapes

Match the project that already exists:

- **Compose-only app:** ownership usually starts in `Application` and a single-Activity host with a `NavHost`
- **XML / Views app:** ownership usually starts in `Application`, an `AppCompatActivity`, or a Fragment-based shell
- **Mixed app:** keep Stream setup at the shared boundary (`Application` or app-scoped DI) instead of duplicating it per screen

Do not rewrite the app into a different UI framework unless the user asks.

---

## Client ownership

Create each Stream client once, store it in an owned object, and pass or inject it from there.

Good ownership points:

- `Application.onCreate()`
- a Hilt `@Singleton` provider, Koin `single`, or other app-scoped DI binding
- a composition root or `App` initializer that runs before any Stream UI is rendered

Bad ownership points:

- inside a `@Composable` body
- inside a `remember { ... }` factory
- inside a leaf `Activity` or `Fragment` that does not own app lifecycle

Exact builder shapes and singleton accessors live in the matching reference file.

---

## Auth model

Use the simplest token shape that matches the user's environment:

- **Backend exists:** prefer a backend-issued Stream token via a `TokenProvider` — the SDK will call it again automatically when the token expires.
- **No backend / demo flow:** generate a token with the Stream CLI (binary is `stream` — see [`credentials.md`](credentials.md)). Never-expiring: `stream token <user_id>`. Expiring: `stream token <user_id> --ttl 1h` (units: `s`/`m`/`h`/`d`).
- **User pastes their own:** accept it and pass it to the client.

Keep the split clear:

- **client:** API key, `User` (`id`, `name`, `image`), user token
- **server:** API secret and token minting (the CLI handles this automatically)

If the app already has its own auth system, extend that flow instead of adding a second login model beside it. Connect / build once per user session, not on every screen entry.

---

## State and ViewModels

Stateful SDK helpers should have explicit ownership:

- **Compose:** obtain ViewModels via `viewModels { factory }` (Activity / Fragment) or `hiltViewModel()` (Hilt). Pass them into Composables; never `remember { SomeViewModel(...) }`.
- **Views:** retain ViewModels via `ViewModelProvider` or DI; collect SDK `Flow`s in `repeatOnLifecycle(Lifecycle.State.STARTED)`.

Avoid creating query objects, channel controllers, message lists, or call objects inside Composables — hoist them into a ViewModel.

---

## Main-dispatcher boundaries

Keep UI updates on the main dispatcher. In Compose, collect `Flow` state with `collectAsStateWithLifecycle()`; in Activities / Fragments, use `lifecycleScope.launch { repeatOnLifecycle(STARTED) { ... } }`.

Preserve the project's concurrency style. If the app already uses coroutines + `Flow`, stay there. If parts of it still use callbacks, bridge carefully instead of rewriting unrelated code.

---

## Combined Chat + Video apps

The Android Chat and Video modules don't collide at the type level (unlike iOS — `User`, theming, and DI primitives live under different package names). Build both clients in `Application.onCreate()` with the same API key and JWT token. See [`references/VIDEO-COMPOSE.md`](references/VIDEO-COMPOSE.md) → *Gotchas* (the "Chat + Video coexist" bullet) for the package-path detail.

---

## Verification checklist

Before calling the work done, confirm:

- the right Stream artifact is added to the right module's `build.gradle.kts` (e.g. `:app`, not `:core`)
- each Stream client is built before any Stream UI renders
- `INTERNET` permission is present in `AndroidManifest.xml`
- for Video, `CAMERA` / `RECORD_AUDIO` are requested at runtime before the first `call.join(...)`
- the requested user can connect without leaking the API secret
- the edited flow works within the existing navigation structure (Compose `NavHost`, Navigation Component, or Fragment back stack)
- user switching or logout tears down the previous session cleanly
