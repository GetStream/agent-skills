# Stream Android - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Target SDK version

Target Stream Chat Android SDK **v7+** (`io.getstream:stream-chat-android-compose:7.x` and matching `stream-chat-android-client` / `stream-chat-android-ui-components`). v7 changed plugin wiring, theme APIs, and several Composable signatures vs. v6. If a pattern in your training data conflicts with this skill's blueprints or the [v7 docs](https://getstream.io/chat/docs/sdk/android/), trust the docs - do not fall back to remembered v6 shapes.

For Stream Video, target the latest published `io.getstream:stream-video-android-ui-compose` (and its transitive `-core`). Verify any signature you are about to write against the bundled `VIDEO-COMPOSE.md` reference or the [Video Android docs](https://getstream.io/video/docs/android/).

For Stream Feeds (V3), target the latest published `io.getstream:stream-feeds-android-client`. Feeds V3 is in closed alpha — public APIs may shift between versions, and there is no pre-built UI artifact. Verify any signature against the bundled `FEEDS-COMPOSE.md` reference, the [Feeds Android docs](https://getstream.io/activity-feeds/docs/android/), or the source on [`GetStream/stream-feeds-android`](https://github.com/GetStream/stream-feeds-android).

### Version lookup

When you need the current Stream artifact version, use one of these sources:

- Maven Central (Sonatype): `https://central.sonatype.com/artifact/io.getstream/stream-chat-android-compose/versions` (or `/stream-chat-android-ui-components/versions`, `/stream-video-android-ui-compose/versions`, `/stream-feeds-android-client/versions`)
- GitHub releases: `https://github.com/GetStream/stream-chat-android/releases`, `https://github.com/GetStream/stream-video-android/releases`, `https://github.com/GetStream/stream-feeds-android/releases`

**Do not use `search.maven.org`** — it is deprecated and its index is stale; it does not surface v7 (Chat) or recent Video releases and will lead you to ship outdated versions by mistake. If a tool result shows `search.maven.org` as the source, discard it and re-query one of the sources above.

---

## Secrets and auth

Never hardcode a Stream API secret in app code, `AndroidManifest.xml`, BuildConfig, `local.properties` shipped to source control, or chat. The client may hold the **API key** and a **user token**; the **API secret** stays server-side only.

Default token model:

- Use a backend-issued token (via a `TokenProvider`) when the user already has a backend.
- Use a CLI-generated token (`stream token <user_id>`, optionally with `--ttl 30s|2h|1d` — see [`credentials.md`](credentials.md)) for local dev and demo flows - this is the preferred path when no backend exists. The binary is `stream`, not `stream-cli`.
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

Initialize Stream SDK clients once at app launch via the `Application` class (or an equivalent app-scoped owner like a Hilt/Koin singleton). Never create a client in:

- a `@Composable` function body
- a `remember { ... }` factory that re-runs on recomposition
- an `Activity.onCreate` that runs every time the activity is recreated
- a transient callback or coroutine with no stored owner

Stateful SDK objects (the Stream-provided `ViewModel`s, query controllers, and the `Call` returned by `streamVideo.call(type, id)`) must live in owned scopes (`viewModels { factory }`, `hiltViewModel()`, an Activity or ViewModel field), not in a Composable body or `remember { ... }`.

If the user switches accounts, tear down the current session before starting the next one — see the matching reference file for the exact disconnect / logout calls.

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
- `VIDEO-COMPOSE.md` for Video + Jetpack Compose
- `VIDEO-COMPOSE-blueprints.md` for concrete call-screen structure
- `FEEDS-COMPOSE.md` for Feeds + Jetpack Compose (headless data SDK — no pre-built UI)
- `FEEDS-COMPOSE-blueprints.md` for custom Composable scaffolding driven by `FeedState` / `ActivityState`

Do not invent missing XML / UI-Components API details. If a requested reference is not bundled yet, say so plainly and fall back to shared guidance from [`sdk.md`](sdk.md) or live docs only when the user wants that.

### Blueprints are mandatory, on every turn

Before writing or editing **any** Stream Chat, Stream Video, or Stream Feeds screen, Composable, navigation handler, deep-link route, theming override, ringing handler, or channel/message/call/feed UI customization, you **must** open the matching section of the corresponding `<PRODUCT>-<UI_LAYER>-blueprints.md` file (e.g. [`references/CHAT-COMPOSE-blueprints.md`](references/CHAT-COMPOSE-blueprints.md), [`references/VIDEO-COMPOSE-blueprints.md`](references/VIDEO-COMPOSE-blueprints.md), [`references/FEEDS-COMPOSE-blueprints.md`](references/FEEDS-COMPOSE-blueprints.md)) and follow its structure. This applies on **every turn**, not just the first time the skill is invoked in a session — follow-up requests like *"add navigation to the channel screen"*, *"open a channel on tap"*, *"add a button to start a call"*, *"customize the call controls"*, *"theme the call screen"*, *"add a comments sheet"*, or *"add a follow button"* count as new screen work and require a fresh blueprint read.

Use the **Request → Blueprint section** table at the top of each blueprints file to resolve which section to read. If no section matches, say so explicitly before improvising — do not silently fall back to remembered SDK shapes from training data.

Do **not** assume that because a blueprint section was read earlier in the session, its content is still in working context. Re-read the relevant section before each Stream screen edit.
