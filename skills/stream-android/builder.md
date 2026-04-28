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

Do **not** try to scaffold Android Studio projects from the CLI.

---

## 2. Choose the integration lane

Resolve three things before editing:

1. **Product:** Chat, Video, Feeds, or a combination
2. **UI layer:** Jetpack Compose, XML / Views (UI Components), or mixed
3. **Scope:** app bootstrap, auth, a specific screen, or a full product shell

If the user only asked for setup, stop after the shared wiring in [`sdk.md`](sdk.md).

---

## 3. Install the SDKs

Prefer the project's existing dependency strategy:

- **Version catalog (`gradle/libs.versions.toml`) present:** add Stream version + library entries to the catalog, then reference them from the app module's `build.gradle.kts`.
- **No version catalog:** add the dependency directly to the app module's `build.gradle.kts` (or `build.gradle`) under `dependencies { ... }`.
- **Compose-only project:** add `io.getstream:stream-chat-android-compose:<version>`.
- **XML / Views project:** add `io.getstream:stream-chat-android-ui-components:<version>`.
- **Both UIs side-by-side:** add both artifacts; the underlying client (`stream-chat-android-client`) is brought in transitively.

After editing, sync Gradle (Android Studio "Sync Now" or `./gradlew help`) and confirm the dependency resolves before continuing.

Make sure `<uses-permission android:name="android.permission.INTERNET" />` is in the app's `AndroidManifest.xml`.

Install only the artifacts needed for the requested Stream products.

---

## 4. Wire the shared app setup

**Before writing any code**, confirm that Step 0.5 in [`SKILL.md`](SKILL.md) has completed — API key, token, and optional seed channels should already be in context. If not, run that step now before continuing.

Follow [`sdk.md`](sdk.md) for:

- `ChatClient` lifetime in the `Application` class (or app-scoped DI provider)
- auth and token transport — use the real API key and token from Step 0.5, never placeholder strings
- ViewModel ownership and main-dispatcher boundaries
- `disconnect()` / `connectUser()` ordering when changing users

If seed channels were created in Step 0.5, the app should render them on first launch without any extra setup — no additional sample data or hardcoded channel IDs needed in the code.

Keep the existing app shell intact. Add the minimum composition points needed for Stream (typically: `Application` subclass registered in the manifest, one host Activity that sets up `ChatTheme { ... }`, and the requested screen Composable).

---

## 5. Load only the needed reference files

Use the product + UI layer to choose the smallest relevant reference set.

Available extracted module:

- Chat + Compose: [`references/CHAT-COMPOSE.md`](references/CHAT-COMPOSE.md)
- Chat + Compose screen blueprints: [`references/CHAT-COMPOSE-blueprints.md`](references/CHAT-COMPOSE-blueprints.md)

Future modules should follow the same naming family:

- `CHAT-XML.md`
- `VIDEO-COMPOSE.md`
- `VIDEO-XML.md`
- `FEEDS-COMPOSE.md`
- `FEEDS-XML.md`

If the exact file is not present yet, say so directly instead of faking a reference.

---

## 6. Verify before you stop

Check the smallest set of outcomes that proves the integration works:

- Gradle sync succeeds and the Stream artifact resolves
- `ChatClient` is initialized from `Application.onCreate()` (or an owned DI binding) before any Stream Composable renders
- the app does not call `ChatClient.instance()` before the builder has run
- the `INTERNET` permission is declared in the manifest
- the requested login, channel list, channel, call, or feed surface appears where expected
- switching users does not leave a previous WebSocket connection or persisted state behind (`disconnect()` completes before the next `connectUser`)
