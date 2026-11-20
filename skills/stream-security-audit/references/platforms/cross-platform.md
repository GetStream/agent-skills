# Cross-platform and native: React Native, Flutter, Unity, Unreal, Electron, C/C++/Rust

Read with `../checklist.md`. Cross-platform SDKs usually wrap native SDKs: audit the bridge, then apply `apple.md` / `android.md` to the native side the wrapper ships.

## React Native
- Storage: `AsyncStorage` is unencrypted; secure options are Keychain/Keystore wrappers (`react-native-keychain`, `expo-secure-store`). MMKV encryption keys hard-coded in JS are not protection.
- The JS bundle ships to the device and can be extracted: no secrets in JS, including `.env` values inlined by Babel plugins.
- Native modules: methods exposed to JS that take paths, URLs or intents without validation; event emitters leaking tokens.
- `Linking.openURL` with content URLs (scheme allowlists); deep link handling (`Linking.getInitialURL`) routing into privileged screens.
- `react-native-webview`: `originWhitelist`, `javaScriptEnabled`, `allowFileAccess`, `onMessage` bridges trusting any page, `injectedJavaScript`.
- OTA updates (CodePush/EAS Update): signing of update bundles.
- Hermes/JS engine: `eval` availability, and Markdown/HTML renderers in JS.
- Logs: `console.log` reaches device logs in release unless stripped (`babel-plugin-transform-remove-console`).

## Flutter / Dart
- Storage: `shared_preferences` is plain; `flutter_secure_storage` maps to Keychain/Keystore (check iOS accessibility and Android options).
- `HttpClient.badCertificateCallback = (_, _, _) => true`, custom `SecurityContext`, `dio` interceptors logging bodies.
- Platform channels (`MethodChannel`): handlers on the native side that accept arbitrary arguments.
- `url_launcher` (`launchUrl`) with content URLs; `webview_flutter` JavaScript mode and `JavascriptChannel`s.
- `dart:convert` `jsonDecode` of untrusted data + `as` casts (throws), `int.parse`, list indexing, `!` null assertion.
- `flutter_markdown` / HTML widgets: link tap handlers and image builders.
- Release logs: `print`/`debugPrint` still emit in release.

## Unity (C#)
- `PlayerPrefs` are plain text (registry on Windows, plist on Apple, XML on Android): no tokens there.
- `UnityWebRequest` with `certificateHandler` returning true; `Application.OpenURL` on content URLs.
- Deserialization: `BinaryFormatter`, `JsonUtility` is safe-ish, Newtonsoft with `TypeNameHandling` other than `None` is not.
- Native plugins (`.bundle`, `.so`, `.dll`) bundled with the SDK: provenance and versions.
- IL2CPP doesn't hide secrets; managed assemblies are trivially decompiled.

## Unreal (C++)
- All of the C/C++ section below. `FHttpModule` TLS settings, `FPlatformProcess::LaunchURL` with content URLs, config files (`.ini`) with keys shipped in packaged builds.

## Electron and desktop web shells
- `BrowserWindow`: `nodeIntegration: false`, `contextIsolation: true`, `sandbox: true`, `webSecurity: true`. Any deviation in a window that renders remote or user content is a likely RCE path.
- `preload` scripts exposing powerful APIs via `contextBridge` without validation.
- `shell.openExternal(url)` on content URLs (can launch arbitrary protocol handlers -> code execution on some OSes); allowlist `https:`/`mailto:`.
- `will-navigate` / `setWindowOpenHandler` handling; `webview` tags.
- Auto-update channels: signature verification, HTTPS.
- Custom protocol handlers (`protocol.registerFileProtocol`) with path traversal.

## C, C++ and unsafe Rust (native SDK cores and vendored libraries)
- Identify every native library: name, version, upstream, local patches. Check the upstream changelog and advisories (GitHub Security Advisories, OSV.dev, NVD) for fixes after the vendored version; then check whether the vendored code contains the fix (compare the patched function).
- Attacker-reachable parsers (Markdown, image codecs, compression, protocol framing, SDP/RTP in media SDKs) are the priority: they get remote input.
- Bugs: buffer overflows (`memcpy`/`strcpy`/`sprintf`/manual indexing), integer overflow in size math, use-after-free in callbacks crossing language boundaries, double free on error paths, format strings, uninitialized memory returned to managed code.
- Algorithmic complexity: quadratic/exponential parsing paths (common in Markdown and regex engines) -> CPU DoS.
- Symbol collisions: a vendored library with unprefixed symbols linking alongside the host's own copy (wrong version wins).
- Rust: `unsafe` blocks, FFI boundary assumptions (null, lifetimes, UTF-8), `unwrap()`/`expect()` on remote input (panics across FFI abort the process).
- Build hardening: stack protectors, FORTIFY_SOURCE, PIE, no executable stacks (mostly platform defaults; flag only if disabled).

## Distribution and release artifacts
- React Native: `npm pack --dry-run` for the JS package, plus the native `ios/` podspec (`pod ipc spec`) and `android/` Gradle module that autolinking pulls in. They ship separately and differ.
- Flutter: `flutter pub publish --dry-run` lists the package contents; check plugin platform folders and any prebuilt binaries.
- Unity/Unreal: unpack the `.unitypackage`/`.upm` or plugin zip and list the native plugins per platform (`Plugins/iOS`, `Plugins/Android`, `.dll`/`.so`/`.dylib`/`.bundle`).
- Electron: unpack `app.asar` (`npx asar list`) and compare it with the source. Check `asarUnpack`, preload scripts and native modules.
- Rust: `cargo package --list`; `cargo audit` (RustSec, record the date); `cargo tree -e features` to see whether a vulnerable feature is enabled.
- C/C++: check which sources the build actually compiles (CMake targets, `SOURCES` lists). Vendored files that are present but not compiled aren't exposure.

## Useful greps
```
rg -n 'AsyncStorage|shared_preferences|PlayerPrefs|MMKV'
rg -n 'badCertificateCallback|certificateHandler|rejectUnauthorized|ServerCertificateValidationCallback'
rg -n 'Linking\.openURL|launchUrl|Application\.OpenURL|shell\.openExternal|LaunchURL'
rg -n 'nodeIntegration|contextIsolation|sandbox:|webSecurity|contextBridge|setWindowOpenHandler'
rg -n 'TypeNameHandling|BinaryFormatter|MethodChannel|addJavascriptInterface|JavascriptChannel'
rg -n 'memcpy|strcpy|strcat|sprintf|alloca|unsafe \{|\.unwrap\(\)'
```
