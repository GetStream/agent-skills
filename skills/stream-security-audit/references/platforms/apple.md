# Apple platforms (Swift, Objective-C, SwiftUI, UIKit, AppKit)

Read with `../checklist.md`. These are the platform APIs where the checklist's issues show up, and what "safe" looks like.

## Credentials and storage
- Keychain: `kSecAttrAccessible*`. `WhenUnlocked(ThisDeviceOnly)` or `AfterFirstUnlock(ThisDeviceOnly)` are normal for tokens; `Always*` is deprecated and a finding. Non-`ThisDeviceOnly` items migrate to new devices via encrypted backups; `kSecAttrSynchronizable` syncs through iCloud Keychain.
- `UserDefaults`, plist files, Core Data, SQLite, `URLCache`, `NSCache`-backed disk caches: not secure storage. Tokens there are a finding; personal data there needs file protection.
- Data Protection: `FileProtectionType` / `NSFileProtection*` on files, `NSPersistentStoreFileProtectionKey` on Core Data stores, `.completeFileProtection*` write options. Default for app files is `completeUntilFirstUserAuthentication`, which is acceptable for most chat-like data; flag when the SDK documents stronger protection than it applies, or when it stores data in shared containers.
- App group containers (`containerURL(forSecurityApplicationGroupIdentifier:)`) are shared with the host's extensions; check what goes there.
- Backups: `URLResourceValues.isExcludedFromBackup` for caches that should not go to iCloud/Finder backups.
- `URLCache.shared` stores responses (including authenticated ones) on disk by default when cache headers allow it; check `URLSessionConfiguration.urlCache` / `requestCachePolicy` on authenticated sessions.
- Token types (AUTH-08): a Swift struct or class without a custom `description` prints every stored property, including the raw token, through `print`, string interpolation, `String(describing:)`, `dump` and crash reporters that capture state. Redact with `CustomStringConvertible`, `CustomDebugStringConvertible` and `CustomReflectable`.
- Test hooks (LOG-08): `ProcessInfo.processInfo.arguments` / `.environment` that change hosts, TLS or auth must sit behind `#if DEBUG`. SwiftPM compiles packages without `DEBUG` in Release, so debug-only hooks never reach App Store builds; Xcode framework targets need the same check per configuration.

## Transport
- ATS: `NSAllowsArbitraryLoads`, `NSExceptionDomains`, `NSAllowsArbitraryLoadsInWebContent` in Info.plists. In an SDK, check the framework's Info.plist (rarely relevant) and sample apps (copied by integrators).
- `URLSessionDelegate` / `URLSessionTaskDelegate` `urlSession(_:didReceive:completionHandler:)`: returning `.useCredential` with `URLCredential(trust:)` without calling `SecTrustEvaluateWithError` (or after ignoring its result) disables TLS validation.
- `URLSessionWebSocketTask` and third-party WebSocket engines: same trust delegate rules; `ws://` URLs.
- `HTTPCookieStorage.shared` shared with the host app; cookies sent to any matching host.
- Redirects: `urlSession(_:task:willPerformHTTPRedirection:newRequest:completionHandler:)`. By default `URLSession` drops `Authorization` on cross-origin redirects only in recent OS versions and only for some headers; custom headers (e.g. `X-Auth`, `X-Auth-Type`) are carried along. Check explicitly.

## Untrusted input
- Swift traps (crash in release): `!`, `as!`, `try!`, `fatalError`, `precondition`, `preconditionFailure`, array subscripts, `Dictionary(uniqueKeysWithValues:)` with duplicate keys, `Int(_: Double)` / `Int(_: Float)` with NaN, infinity or out-of-range values, integer arithmetic overflow (`+`, `*` on `Int`), `String.Index` misuse, `stride(from:to:by: 0)`, `Range` with lower > upper (`a..<b`), `Character(String)` with multi-character strings, `UnicodeScalar(Int)!`.
- Paths: `URL.standardizedFileURL` and `appendingPathComponent` resolve or keep `..`; `URL.lastPathComponent` percent-decodes, so `..%2F..%2Fx` becomes `../../x`. Containment needs an explicit check after standardizing.
- Stack size: the iOS main thread has 1 MB (SwiftUI bodies run there), GCD worker threads and `Thread` default to 512 KB; recursive `Codable` types (generic JSON enums) overflow at a few hundred nesting levels.
- `Int64` nanosecond arithmetic on dates overflows past 2262 and traps.
- `Codable`: custom `init(from:)` with forced unwraps; `JSONSerialization` returning `NSNumber` that is cast with `as!`; very deep nesting (Foundation's JSON parser has a depth limit of 512 in recent versions, custom recursive decoders may not).
- `NSKeyedUnarchiver`: `unarchiveObject(with:)` and `unarchiveTopLevelObjectWithData` are insecure; require `unarchivedObject(ofClass:from:)` with `requiresSecureCoding`.
- `NSPredicate(format:)` with string interpolation instead of `%@`/`%K` arguments; `NSExpression(format:)` on untrusted input can call methods (`FUNCTION(...)`) - a real code-execution primitive.
- `String(format:)` / `NSLog(variable)` with an untrusted format string.
- `NSRegularExpression` on untrusted patterns or catastrophic patterns over untrusted text.
- `XMLParser`: `shouldResolveExternalEntities` must stay false.
- `AttributedString(markdown:)`, `NSAttributedString(markdown:)`, `NSAttributedString(html:)` / `.documentType: .html` (HTML import runs WebKit, loads remote resources, is slow and crash-prone on the main thread).
- Image decoding: `UIImage(data:)` / ImageIO are system-maintained; third-party GIF/WebP decoders and vendored image code are not. Large dimensions -> memory exhaustion; check downsampling.

## Rendering, links and navigation
- `UIApplication.shared.open`, `NSWorkspace.shared.open`, SwiftUI `openURL` / `OpenURLAction`, `Link`, `Text` with markdown links (SwiftUI `Text(LocalizedStringKey)` renders markdown links from string literals and interpolations), `UITextView` with `.link` attributes and data detectors (`dataDetectorTypes`), `textView(_:shouldInteractWith:in:)` / `primaryActionFor` delegates. Check scheme allowlists everywhere a URL from content reaches one of these.
- `WKWebView`: `javaScriptEnabled` / `allowsContentJavaScript`, `loadFileURL(_:allowingReadAccessTo:)` (scope of read access - never a parent directory of sensitive data), `loadHTMLString(_:baseURL:)` with a file base URL, `WKScriptMessageHandler` bridges, `configuration.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")`. `UIWebView` is removed and an App Store rejection.
- `QLPreviewController` is sandboxed and generally safe for previews; previewing HTML/SVG attachments in a `WKWebView` is not.
- `SFSafariViewController` is the safe way to show web links in-app.
- `UIPasteboard.general` is global and synced via Universal Clipboard; consider `localOnly` / `expirationDate` options for sensitive copies. Reading `UIPasteboard.general` triggers the paste banner since iOS 14.

## Platform integration
- Notification Service Extension: parses push payloads (attacker can't usually send pushes, but payload fields often contain user content), may download attachments from URLs in the payload, shares data via app groups.
- Share extension / `NSItemProvider`: files from other apps, untrusted names and types.
- Universal links and custom URL schemes handled by sample apps or by SDK routing helpers.
- Permission prompts (camera, microphone, photos, speech recognition, location): requested lazily at point of use; `Info.plist` usage strings are the host's, but the SDK should not request permissions on import.

## Logging
- `print`, `NSLog`, `os_log`, `Logger`: `NSLog` and `print` go to the unified log in release builds and can be read with a cable (`log stream`, Console.app) or in sysdiagnoses. `os_log`/`Logger` interpolations are private by default unless marked `privacy: .public`; check that tokens and message content are not marked public.
- Custom log destinations writing files: location, protection, rotation, and any "export logs" UI.

## Concurrency and memory
- `@unchecked Sendable`, `nonisolated(unsafe)`, `NSLock`/`os_unfair_lock` misuse, `DispatchQueue` races on dictionaries/arrays (crashes under contention).
- `Unsafe*Pointer`, `withUnsafeBytes`, `Data.withUnsafeMutableBytes`, `memcpy`, C interop via module maps; vendored C targets (check upstream CVEs for the vendored version; e.g. cmark-gfm has had DoS/quadratic-complexity and memory-safety advisories).
- Objective-C: `performSelector` with untrusted selectors, `NSClassFromString` on untrusted strings, KVC (`setValue:forKey:`) with untrusted keys.

## Distribution and release artifacts
- **Channels**:
  - SwiftPM: `swift package describe --type json` lists products, targets, resources and binary targets; `swift package show-dependencies`; `Package.resolved` has the revisions.
  - CocoaPods: `pod ipc spec X.podspec` resolves the spec, including `resource_bundles`, `vendored_frameworks` and `script_phases`.
  - XCFramework or binary: list the bundle (`find X.xcframework`) and each slice's `Info.plist` and `PrivacyInfo.xcprivacy`.
- Privacy manifests (`PrivacyInfo.xcprivacy`) are App Store compliance, not security. Leave them out of the report unless the user asks.
- **The Xcode project is evidence**: `project.pbxproj` holds Run Script build phases (`shellScript = `), resource membership, entitlements files (`CODE_SIGN_ENTITLEMENTS`), extension targets, and per-target build settings such as `ENABLE_TESTABILITY` or `SWIFT_OPTIMIZATION_LEVEL`. Don't exclude it from review.
- **Products for tests**: SwiftPM products such as `*TestTools` or `*MockServer` are installable by integrators. Note them as distribution scope; they become findings only if they ship secrets or get linked into release builds.
- **Advisories**: `osv-scanner --lockfile=Package.resolved` (or `osv-scanner scan source -r .`) covers SwiftPM and CocoaPods lock files; record the run date. Vendored copies need a manual check against upstream changelogs.

## Simulator, device and macOS differences
- The iOS Simulator runs on the Mac's kernel: its main thread has an 8 MB stack (a device's has 1 MiB), and memory limits aren't the device's (no jetsam at device limits). A crash or pass on the simulator's main thread isn't a device result. To approximate the device main thread in recursion tests, run the code on a `Thread` with `stackSize = 1 << 20`. GCD and `Thread` secondary threads are 512 KiB on both, so thresholds measured on the queue the SDK really uses carry over.
- Reproduce with the real modules: a scratch SwiftPM package whose test target depends on a `git archive` snapshot of the audited commit (and on first-party dependencies pinned `exact:`), built once with `xcodebuild build-for-testing ... -configuration Release ENABLE_TESTABILITY=YES`. Crashing tests can hang `xcodebuild test-without-building` after the first crash. Run each case with `xcrun simctl spawn <device> xctest -XCTest <Class/test> <path>.xctest` instead, passing parameters as environment variables (`SIMCTL_CHILD_<NAME>`). Crash reports land in `~/Library/Logs/DiagnosticReports`. Copied or re-implemented code gives different thresholds: a proxy and the real module can disagree by 20% or more.
- Measure memory with `task_info(TASK_VM_INFO).phys_footprint`, not RSS, and compare it with the device's jetsam limits (roughly 2 to 3 GB on current iPhones, lower on older ones and in extensions: NSE about 24 MB, share extensions about 120 MB).
- Release vs Debug changes frame sizes (and so recursion thresholds), inlining and timing. Reproduce in Release; with `@testable import` use `-configuration Release ENABLE_TESTABILITY=YES` and say so.
- macOS apps may be unsandboxed: "the app container" becomes the user's home directory, which raises file-write and storage findings. Rate per platform when they differ.

## Useful greps
```
# opening URLs and rendering links
rg -n 'UIApplication\.shared\.open|NSWorkspace\.shared\.open|openURL|OpenURLAction|Link\(|dataDetectorTypes|shouldInteractWith' 
# web content
rg -n 'WKWebView|loadHTMLString|loadFileURL|evaluateJavaScript|WKScriptMessageHandler|NSAttributedString.DocumentType.html|documentType: .html'
# trust and transport
rg -n 'didReceive challenge|serverTrust|SecTrust|URLCredential\(trust|NSAllowsArbitraryLoads|ws://|http://'
# storage
rg -n 'UserDefaults|kSecAttrAccessible|FileProtectionType|NSFileProtection|NSPersistentStoreFileProtectionKey|isExcludedFromBackup|containerURL\(forSecurityApplicationGroupIdentifier|urlCache|URLCache'
# crashes on untrusted data
rg -n 'try!|as!|fatalError\(|preconditionFailure\(|precondition\(|Int\([^)]*(Double|Float|\.rounded)'
# injection and deserialization
rg -n 'NSPredicate\(format: *"[^"]*\\\(|NSExpression\(format|String\(format: *[a-z]|NSKeyedUnarchiver|unarchiveObject'
# logging
rg -n 'privacy: *\.public|NSLog\(|print\(' 
```
