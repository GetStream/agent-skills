# Stream Android - build and integration flow

Use this module after intent classification and, when needed, the local **Project signals** probe from [`SKILL.md`](SKILL.md).

---

## 1. Detect the workspace

Start by understanding what kind of Android project is in front of you:

- `settings.gradle.kts` / `settings.gradle` at the root -> existing Gradle project
- `app/build.gradle.kts` (or any `*/build.gradle.kts` with `com.android.application`) -> the app module
- `gradle/libs.versions.toml` -> a version catalog is in use; add Stream entries there
- `AndroidManifest.xml` under a module's `src/main/` -> confirms an Android module
- no Gradle files and `EMPTY_CWD` -> tell the user to create a new Android app in Android Studio first

Inspect the app module's `build.gradle.kts` for existing Compose / View System usage before choosing a UI lane.

By default, do **not** scaffold an Android Studio project from the CLI. If the directory is `EMPTY_CWD` / has no Gradle project, tell the user to create the app in Android Studio first. **Only when the user explicitly insists you scaffold it anyway**, follow *Scaffold on explicit override* below.

---

## Scaffold on explicit override

Reached **only** when there is no Gradle project **and** the user, after being told to use Android Studio, explicitly asks you to create the project anyway. Do not scaffold under any other condition. Android Studio normally owns the toolchain; when you take that on yourself, derive every version instead of guessing.

**Derive the toolchain - never guess it:**

1. **compileSdk / targetSdk** - do not assume "latest". Prefer the value the user gave, but verify it against the SDK: the app's `compileSdk` must be at least the level the Stream SDK was built against - AGP fails the build and names the exact required level if it is lower, so honor that rather than blindly jumping to the newest API. For `targetSdk`, follow Stream's documented recommendation for this SDK version (getting-started / release notes) instead of the latest platform, since a newer target can enable platform behavior changes the SDK version has not adapted to yet.
2. **Kotlin** - do not guess a version, and do not hardcode a Maven-Central URL to look one up (fragile). Let the toolchain be the source of truth. Two robust ways, in order:
   - **Let the build tell you (primary).** Add the Stream dependency, then run a Gradle sync/build. If your Kotlin is older than the SDK's, it fails fast with the exact requirement - `Class '...' was compiled with an incompatible version of Kotlin. The binary version of its metadata is X, expected version is Y` - which *names* the version to move to. Bump the Kotlin plugin (and, since Kotlin 2.0, the bundled Compose plugin moves with it) to satisfy it and re-sync. A compiler more than one minor version behind the SDK is the classic first-build crash.
   - **Resolve it before building.** Run `./gradlew :app:dependencies` (any configuration that includes the Stream artifact) and read the resolved `org.jetbrains.kotlin:kotlin-stdlib` version Gradle pulls in transitively; set the Kotlin plugin to at least that. This asks Gradle, not a web page.
3. **Compose compiler** - since Kotlin 2.0 it is the bundled `org.jetbrains.kotlin.plugin.compose` Gradle plugin, applied at the **same version as Kotlin**. There is no separate Compose-compiler version to pick.
4. **AGP + Gradle** - choose a stable AGP that supports the chosen compileSdk, and the Gradle version that AGP requires. Confirm the pairing against the official table at `developer.android.com/build/releases/gradle-plugin` - do not guess it.

**Set up edge-to-edge, system insets, and the keyboard** in the host Activity - standard Android behavior a sample must get right, and the usual source of "content draws under the status bar" and janky keyboard reports:

- Call `enableEdgeToEdge()` in `onCreate` (requires `androidx.activity` 1.8+).
- Keep `android:windowSoftInputMode="adjustResize"` on the Activity in the manifest, and apply `Modifier.imePadding()` at the screen / composer root so the keyboard animates smoothly instead of jumping.
- Consume the system-bar insets on the host container (a `Scaffold`, or `Modifier.windowInsetsPadding(WindowInsets.systemBars)`) so content clears the status and navigation bars - but check [`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md) first, since Stream's Compose screens already apply some insets; do not double-pad.

Then continue with the normal shared wiring in [`sdk.md`](sdk.md) (ChatClient in `Application.onCreate`, auth, ViewModels) and the product reference files below.

---

## 2. Choose the integration lane

Resolve three things before editing:

1. **Product:** Chat, Video, Feeds, or a combination
2. **UI layer:** Jetpack Compose, XML / Views, or mixed
3. **Scope:** app bootstrap, auth, a specific screen, or a full product shell

If the user only asked for setup, stop after the shared wiring in [`sdk.md`](sdk.md).

---

## 3. Install the SDKs

Prefer the project's existing dependency strategy:

- **Version catalog (`gradle/libs.versions.toml`) present:** add Stream entries to the catalog, then reference them from the app module's `build.gradle.kts`.
- **No version catalog:** add the dependency directly to the module's `build.gradle.kts` (or `build.gradle`) under `dependencies { ... }`.

For the exact artifact ids, see the matching reference file (`CHAT-COMPOSE.md`, `VIDEO-COMPOSE.md`, `FEEDS-COMPOSE.md`, …).

When you need the current artifact version, follow [`RULES.md`](RULES.md) → *Version lookup*. Never query `search.maven.org` — its index is stale.

After editing, sync Gradle (Android Studio "Sync Now" or `./gradlew help`) and confirm the dependency resolves before continuing.

Install only the artifacts needed for the requested Stream products.

---

## 4. Wire the shared app setup

**Before writing any code**, confirm that the credentials flow in [`credentials.md`](credentials.md) has completed — API key, token, and optional seed channels should already be in context. If not, run it now before continuing.

Follow [`sdk.md`](sdk.md) for:

- Stream client lifetime in an app-scoped owner (`Application`, Hilt `@Singleton`, Koin `single`)
- auth and token transport — reference credentials via named constants (e.g., `Config.apiKey`, `Config.userToken` from a local config file), never embed raw credential values inline
- ViewModel ownership and main-dispatcher boundaries
- user switching and session teardown

If seed channels were created during the credentials flow, the app should render them on first launch without any extra setup — no additional sample data or hardcoded channel IDs needed in the code.

Keep the existing app shell intact. Add the minimum composition points needed for Stream (typically: `Application` subclass registered in the manifest, one host Activity that sets up `ChatTheme { ... }`, and the requested screen Composable).

---

## 5. Load only the needed reference files

Use the product + UI layer to choose the smallest relevant reference set.

Available extracted modules:

- Chat + Compose: [`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md)
- Chat + Compose screen blueprints: [`references/CHAT-COMPOSE-blueprints.md`](references/CHAT-COMPOSE-blueprints.md)
- Chat + XML: [`references/CHAT-XML.md`](references/CHAT-XML.md)
- Chat + XML screen blueprints: [`references/CHAT-XML-blueprints.md`](references/CHAT-XML-blueprints.md)
- Video + Compose: [`references/VIDEO-COMPOSE.md`](references/VIDEO-COMPOSE.md)
- Video + Compose call/screen blueprints: [`references/VIDEO-COMPOSE-blueprints.md`](references/VIDEO-COMPOSE-blueprints.md)
- Feeds + Compose: [`references/FEEDS-COMPOSE.md`](references/FEEDS-COMPOSE.md)
- Feeds + Compose screen blueprints: [`references/FEEDS-COMPOSE-blueprints.md`](references/FEEDS-COMPOSE-blueprints.md)

Per [`RULES.md`](RULES.md) → *Blueprints are mandatory, on every turn*: every Stream Chat, Stream Video, or Stream Feeds screen, Composable, navigation handler, deep-link route, ringing flow, or UI customization must be preceded by reading the matching section in the corresponding blueprints file. Use the **Request → Blueprint section** table at the top of each `*-blueprints.md` file to pick the section. This applies to follow-up requests in the same session too — re-open the file and re-read the matching section before each Stream screen edit, do not rely on what was loaded earlier.

If the exact file is not present yet, say so directly instead of faking a reference.

---

## 6. Verify before you stop

Check the smallest set of outcomes that proves the integration works:

- Gradle sync succeeds and the Stream artifact resolves
- `ChatClient`, `StreamVideo`, and/or `FeedsClient` are initialized from `Application.onCreate()` (or an owned DI binding) before any Stream Composable renders
- the app does not call `ChatClient.instance()` / `StreamVideo.instance()` before the corresponding builder has run; for Feeds, `FeedsClient` is owned (no global singleton) — never reach for an `instance()` shape
- for Feeds: `feedsClient.connect()` has been awaited before any `feed.getOrCreate()` / `addActivity(...)` call
- for Video: `CAMERA` and `RECORD_AUDIO` are requested at runtime before the first `call.join(...)` (via `LaunchCallPermissions(call)` or `rememberCallPermissionsState(call)`)
- the requested login, channel list, channel, call, or feed surface appears where expected
- switching users does not leave a previous WebSocket connection or persisted state behind: Chat `disconnect()` completes before the next `connectUser`; Video `StreamVideo.instance().logOut()` and `StreamVideo.removeClient()` complete before the next `StreamVideoBuilder(...).build()`; Feeds `client.disconnect()` completes before constructing a fresh `FeedsClient` for the next user
