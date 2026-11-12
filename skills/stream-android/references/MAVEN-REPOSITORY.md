# Stream's Maven repository (`stream-io-repo.com`)

Stream Android libraries (Chat, the AI components, Stream Agents, Video, Feeds) are published to Stream's Maven repository, `https://stream-io-repo.com`. Maven Central only has earlier versions (Chat stops at 7.13.0, the standalone `stream-chat-android-ai-compose` at 0.3.0, and `stream-agents-android-core` was never there), so a project that lists only `mavenCentral()` resolves an old API or fails to resolve at all.

Docs: [Chat](https://getstream.io/chat/docs/sdk/android/basics/installation.md), [Video](https://getstream.io/video/docs/android/basics/installation.md), [Feeds](https://getstream.io/activity-feeds/docs/android/installation.md). Browse a product's releases at `https://browse.stream-io-repo.com/releases/<repo>` (`stream-chat-android`, `stream-video-android`, `stream-feeds-android`).

## Setup

Add the repository to `dependencyResolutionManagement.repositories` in `settings.gradle.kts`, next to the repositories the project already lists. This is the docs' block (Video, Feeds, AI components Quickstart):

```kotlin
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven("https://stream-io-repo.com")
    }
}
```

Groovy `settings.gradle`:

```groovy
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven { url "https://stream-io-repo.com" }
    }
}
```

- Keep the project's own `repositoriesMode`; the Feeds docs leave the line out. Do not add or change it just for Stream.
- The Chat docs also list `maven { url "https://jitpack.io" }`, for some transitive dependencies. Add it for Chat when the project doesn't already have it.
- The docs use no `content { includeGroup(...) }` filter. Do not add one.
- An older project that declares repositories in the root `build.gradle` uses the legacy form the docs show:

```groovy
allprojects {
    repositories {
        google()
        mavenCentral()
        maven { url "https://stream-io-repo.com" }
    }
}
```

## Versions

Read `<release>` from the artifact's metadata. `<latest>` matched `<release>` for every Stream artifact checked (2026-11-11), but `<release>` is the field to use:

```bash
curl -s https://stream-io-repo.com/io/getstream/stream-chat-android-compose/maven-metadata.xml | grep -o '<release>[^<]*'
curl -s https://stream-io-repo.com/io/getstream/stream-chat-android-ui-components/maven-metadata.xml | grep -o '<release>[^<]*'
curl -s https://stream-io-repo.com/io/getstream/stream-chat-android-ai-compose/maven-metadata.xml | grep -o '<release>[^<]*'
curl -s https://stream-io-repo.com/io/getstream/stream-agents-android-core/maven-metadata.xml | grep -o '<release>[^<]*'
curl -s https://stream-io-repo.com/io/getstream/stream-video-android-ui-compose/maven-metadata.xml | grep -o '<release>[^<]*'
curl -s https://stream-io-repo.com/io/getstream/stream-feeds-android-client/maven-metadata.xml | grep -o '<release>[^<]*'
```

One release ships every module of an SDK at one version. The Chat client, Compose, XML UI components and the AI artifacts (`-ai-compose`, `-ai-ondevice`, `-ai-a2ui`, `-ai-openui`) all carry the Chat version, so use one version entry for them. Video's modules share the Video version. Stream Agents (`stream-agents-android-core`) and Feeds have versions of their own.

Never take a version from Maven Central (`repo1.maven.org`, `central.sonatype.com`) or `search.maven.org`: they are behind.

## Troubleshooting

- **`Could not find io.getstream:<artifact>:<version>`**: the repository is missing from `dependencyResolutionManagement.repositories`. An entry under `pluginManagement` doesn't count. Check the version against the metadata too.
- **`FAIL_ON_PROJECT_REPOS`**: with this mode, Gradle rejects repositories declared in a module's `build.gradle(.kts)`. Add Stream's repository in settings, not in the module.
