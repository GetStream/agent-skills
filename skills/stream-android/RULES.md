# Stream Android - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Target SDK version

Target Stream Chat Android SDK **v7+** (`io.getstream:stream-chat-android-compose:7.x` and matching `stream-chat-android-client` / `stream-chat-android-ui-components`). v7 changed plugin wiring, theme APIs, and several Composable signatures vs. v6. If a pattern in your training data conflicts with this skill's blueprints or the [v7 docs](https://getstream.io/chat/docs/sdk/android/), trust the docs - do not fall back to remembered v6 shapes.

---

## Secrets and auth

Never hardcode a Stream API secret in app code, `AndroidManifest.xml`, BuildConfig, `local.properties` shipped to source control, or chat. The client may hold the **API key** and a **user token**; the **API secret** stays server-side only.

Default token model:

- Use a backend-issued token (via a `TokenProvider`) when the user already has a backend.
- Use a CLI-generated token (`stream token <user_id>` or `stream token <user_id> --ttl <duration>`) for local dev and demo flows - this is the preferred path when no backend exists.
- Use a static token only when the user explicitly wants to paste one themselves.
- Never use `ChatClient.devToken(userId)` in production - dev tokens disable token verification and let any client impersonate any user.
- Never invent or generate fake production credentials.
- The API secret never leaves the CLI/server side; only the API key and the generated token go into app code.

---

## Project ownership

Preserve the app's existing architecture:

- Do **not** convert XML/Views to Compose unless the user asks.
- Do **not** convert Compose to XML/Views unless the user asks.
- Do **not** flip a project off Gradle Kotlin DSL onto Groovy (or vice versa) unless the user asks.
- Do **not** ignore the version catalog (`gradle/libs.versions.toml`) when the project already uses one - add Stream entries there instead of hardcoding versions in `build.gradle.kts`.
- Do **not** flatten an existing Hilt/Koin DI graph, navigation setup, or multi-module structure just to fit a sample.

If there is **no Android project**, do not try to scaffold one from the CLI. Tell the user to create the app in Android Studio first, then continue.

---

## Client lifetime

Initialize `ChatClient` once at app launch via the `Application` class (or an equivalent app-scoped owner like a Hilt/Koin singleton). Never create a `ChatClient` in:

- a `@Composable` function body
- a `remember { ... }` factory that re-runs on recomposition
- an `Activity.onCreate` that runs every time the activity is recreated
- a transient callback or coroutine with no stored owner

Stateful SDK objects (`ChannelListViewModel`, `MessageListViewModel`, `MessageComposerViewModel`, `AttachmentsPickerViewModel`, query controllers) must be obtained via `viewModels { factory }` or `hiltViewModel()` - never instantiated in a Composable body or recreated on each recomposition.

If the user switches accounts, call `ChatClient.disconnect()` and wait for it to complete before calling `connectUser` for the next user.

---

## UI and concurrency

UI state changes belong on the main dispatcher. Prefer explicit ownership over implicit globals:

- collect SDK `Flow`s with `collectAsStateWithLifecycle()` (Compose) or `repeatOnLifecycle` (Views)
- run `client.connectUser(...).enqueue { ... }` (or `await()`) from a lifecycle-aware scope
- avoid creating ad-hoc `CoroutineScope`s inside Composables - use `rememberCoroutineScope` or a ViewModel scope

When adapting examples, match the project's actual entry points (`Application`, `Activity`, `Fragment`, navigation graph) instead of forcing a different one.

---

## Reference discipline

Load only the product/UI-layer reference files that match the request.

- `CHAT-COMPOSE.md` for Chat + Jetpack Compose
- `CHAT-COMPOSE-blueprints.md` for concrete Composable screen structure

Do not invent missing Video, Feeds, or XML/UI-Components API details. If a requested reference is not bundled yet, say so plainly and fall back to shared guidance from [`sdk.md`](sdk.md) or live docs only when the user wants that.
