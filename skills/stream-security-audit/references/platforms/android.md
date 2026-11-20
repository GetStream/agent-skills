# Android (Kotlin, Java, Jetpack Compose, Views)

Read with `../checklist.md`.

## Credentials and storage
- `SharedPreferences` / DataStore are plain files in the app sandbox. Tokens there are a finding when the SDK claims secure storage or the token is long-lived; prefer Android Keystore-backed encryption (`EncryptedSharedPreferences` is deprecated in newer security-crypto versions - check what the SDK uses and whether it handles Keystore failures).
- `MODE_WORLD_READABLE`/`WRITEABLE`, files on external storage (`getExternalStorageDirectory`, `getExternalFilesDir` on old API levels), `MediaStore` inserts of private content.
- Backups: `android:allowBackup`, `fullBackupContent`, `dataExtractionRules`. Library manifests merge into the app's - an SDK manifest that sets backup flags or adds components changes the host app.
- Room/SQLite: `rawQuery`/`execSQL` with string concatenation; database encryption (SQLCipher) claims.
- Token types (AUTH-08): a Kotlin `data class` (or Java `record`) generates `toString()` with every field, so `"$token"` in a log line prints the JWT. Override `toString()` to redact.
- Clipboard (STORE-06): `ClipboardManager.setPrimaryClip` is visible to the keyboard and, before Android 10, to background apps. Mark sensitive clips with `ClipDescription.EXTRA_IS_SENSITIVE` (Android 13+).
- Randomness (CRYPTO-03): `java.util.Random` and `kotlin.random.Random` are not cryptographic; use `SecureRandom` for tokens, nonces and `state`.

## Transport
- `res/xml/network_security_config.xml`: `cleartextTrafficPermitted="true"`, `<certificates src="user"/>` (trusting user-installed CAs in release), debug-overrides leaking into release.
- `android:usesCleartextTraffic="true"` in the library manifest.
- Custom `X509TrustManager` with empty `checkServerTrusted`, `HostnameVerifier { _, _ -> true }`, `SSLSocketFactory` overrides, OkHttp `CertificatePinner` that can be disabled by config.
- OkHttp interceptors: `HttpLoggingInterceptor.Level.BODY`/`HEADERS` enabled in release; auth interceptors added to a client that is also used for content URLs (images, files) -> token sent to arbitrary hosts. Check `Authenticator` on 401 re-sending credentials to redirected hosts.

## Untrusted input
- Kotlin `!!`, `as` (unsafe cast), `error()`, `require`/`check` on payload data, `toInt()` on strings (`NumberFormatException`), `Math.toIntExact`, array/list indexing, `substring` with server offsets, `Regex` on untrusted patterns.
- JSON libraries: Gson (reflection, defaults to nulls in non-null Kotlin types -> NPE later), Moshi/kotlinx.serialization strictness, polymorphic deserialization with type discriminators from payloads.
- `ObjectInputStream`, `Parcelable`/`Serializable` from Intents (`getSerializableExtra`), `Bundle` from untrusted sources.
- `ZipInputStream`/`ZipFile` without canonical path checks (zip slip).
- `XmlPullParser`/`DocumentBuilderFactory` with external entities.

## Rendering, links and navigation
- `WebView`: `setJavaScriptEnabled(true)`, `addJavascriptInterface` (any page loaded can call it), `setAllowFileAccess`, `setAllowFileAccessFromFileURLs`, `setAllowUniversalAccessFromFileURLs`, `setAllowContentAccess`, `onReceivedSslError { handler.proceed() }`, `shouldOverrideUrlLoading` scheme handling, `loadDataWithBaseURL` with a file base.
- `Intent.ACTION_VIEW` with `Uri.parse(untrusted)`: `intent:` URIs (`Intent.parseUri`) can target internal components; `content://` and `file://` URIs; missing `CATEGORY_BROWSABLE` / package restrictions.
- `Linkify`, `Html.fromHtml`, `LinkMovementMethod`, Compose `AnnotatedString` with `LinkAnnotation.Url`, `UriHandler.openUri` - scheme allowlists.
- Coil/Glide/Picasso loading arbitrary URLs: which `OkHttpClient` they share (auth headers), disk cache location, size limits for huge images/GIFs.
- Custom Tabs vs WebView for links.

## Platform integration
- Library manifest components: `exported="true"` activities/services/receivers/providers, intent filters (deep links), `FileProvider` path XML (`<root-path>` exposes everything; broad `<files-path path=".">`), `grantUriPermissions`.
- `PendingIntent` without `FLAG_IMMUTABLE` (implicit base intents can be hijacked), `PendingIntent` for notifications built from payload data.
- Firebase Messaging services: payload parsing, notification content from untrusted fields, `data` messages triggering network calls.
- Broadcast receivers without permissions; `LocalBroadcastManager` deprecated.
- Permissions declared in the library manifest (they merge into every host app): flag unnecessary dangerous permissions.
- `FLAG_SECURE` for sensitive screens if the SDK claims it.

## Logging
- `Log.d/v/i` in release (readable via `adb logcat`; on old Android other apps with `READ_LOGS`). Timber trees planted by the SDK. Crashlytics custom keys with personal data.
- ProGuard/R8 consumer rules: `-keep` of everything is not a security issue, but `-assumenosideeffects` for logs is a common mitigation to check.

## Concurrency and native code
- Coroutines/`Flow` races on auth state; `@Volatile` misuse; `synchronized` gaps.
- JNI/NDK libraries (`.so` files): versions of bundled native libs (image codecs, WebRTC, SQLCipher) and their CVEs; `System.loadLibrary` from writable paths.

## Distribution and release artifacts
- Build what ships: `./gradlew :lib:assembleRelease` and `unzip -l lib/build/outputs/aar/*.aar`. Check `classes.jar`, `jni/` native libraries, `AndroidManifest.xml` (merged into the host: exported components, permissions, `usesCleartextTraffic`, `networkSecurityConfig`), `proguard.txt`/consumer rules (keep rules that disable obfuscation of security code), and `assets/`.
- `./gradlew :lib:publishToMavenLocal` and inspect the POM: dependency versions and scopes integrators will resolve.
- Exact versions: `./gradlew :lib:dependencies --configuration releaseRuntimeClasspath`; Gradle lockfiles and version catalogs (`gradle/libs.versions.toml`) if present.
- Advisories: `osv-scanner scan source -r .` (reads Gradle lockfiles), OWASP dependency-check, or GitHub Dependabot alerts. Record the tool and the database date, and check that the vulnerable class is actually used.

## Useful greps
```
rg -n 'addJavascriptInterface|setJavaScriptEnabled|setAllowFileAccess|setAllowUniversalAccessFromFileURLs|onReceivedSslError|loadDataWithBaseURL'
rg -n 'exported="true"|<provider|grantUriPermissions|<root-path|PendingIntent\.get|FLAG_MUTABLE|Intent\.parseUri|ACTION_VIEW'
rg -n 'X509TrustManager|HostnameVerifier|checkServerTrusted|cleartextTrafficPermitted|usesCleartextTraffic|certificates src="user"'
rg -n 'HttpLoggingInterceptor|Level\.BODY|addInterceptor|authenticator\('
rg -n 'SharedPreferences|MODE_WORLD|getExternalStorage|allowBackup|rawQuery|execSQL|ObjectInputStream|getSerializableExtra|ZipInputStream'
rg -n 'Log\.[dvi]\(|Timber\.' 
```
