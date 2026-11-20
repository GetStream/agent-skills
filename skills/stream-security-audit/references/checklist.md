# SDK security check catalog

Platform-agnostic. Each item has an ID, a description of what to look for and, where it isn't obvious, how to check it and when it becomes a reportable vulnerability. Platform APIs and grep targets are in `platforms/*.md`. The recon script (recon.md) labels its leads with these IDs.

**How to use it.** Walk every item, in the order the threat model suggests, and record a result for each one in the coverage ledger (end of this file):
- a finding or hardening ID;
- Clean, with what you read or ran;
- N/A, with why;
- Not checked, with why.

An item with no result is a gap in the audit, not a clean result. Where an item says **Report**, that's the usual classification and severity. The rubric in `reporting.md` decides.

Contents
- Attacker positions and content provenance
- 1. SECRET: secrets in the codebase and in what ships
- 2. AUTH: tokens, credentials and authentication
- 3. TLS: transport security
- 4. INPUT: parsing untrusted data
- 5. RENDER: rendering untrusted content
- 6. LINK: links, URLs and navigation
- 7. STORE: local storage, files and caches
- 8. SESSION: logout, user switching and multiple accounts
- 9. IPC: platform integration and IPC
- 10. LOG: logging, errors, telemetry and diagnostics
- 11. CRYPTO: cryptography and randomness
- 12. CONC: concurrency and state
- 13. NATIVE: memory-unsafe and native code
- 14. AI: AI and LLM features
- 15. AUTHZ: client-side authorization assumptions
- 16. SUPPLY: supply chain, build and CI
- 17. API: defaults, API design, samples and docs
- 18. DIST: distribution, dependencies and release artifacts
- Coverage ledger

## Attacker positions and content provenance

- **Remote peer**: another user of the product who can send content (messages, profiles, file names, reactions, custom fields) that the SDK renders or processes on the victim's device. Usually the most important position: low cost, often scales to many victims.
- **Model output**: text, tool calls or UI programs produced by an LLM, steerable by anyone who can get text into its context (prompt injection via a message, a web page, a tool result, a file).
- **Network**: on-path attacker (public Wi-Fi, hostile proxy). Only matters when transport protection can be weakened or bypassed.
- **Malicious or compromised backend / CDN / third-party host**: the SDK's own server, a configurable base URL, an attachment host, a link-preview or GIF provider.
- **Local app / process**: another app on the device, a browser extension, another tab or origin, a process on the same host.
- **Integrator misuse**: a developer using the SDK in a way its API invites (insecure default, misleading name, doc example with a secret).
- **Physical / forensic**: someone with the unlocked or locked device, a backup, a sysdiagnose or bug report, or a shared device after logout.
- **Anyone with the repository or package**: for secrets committed to a public repo or shipped in a binary.

**Content provenance.** Before assigning one of these positions, establish who writes the field. The backend generates some fields (ids, timestamps, counts). It normalizes others (file names, URLs, scraped link previews), only admins can set some, and only some are passed through verbatim from a peer. A field that looks peer-controlled in the client model may never be peer-controlled in practice. When the server's behavior is unknown, the finding is conditional on it.

---

## 1. SECRET: secrets in the codebase and in what ships

Anything in a client binary, a published package or a public repository is public. Sort every hit into one of two kinds:
- A **secret**: server API secret, signing key, private key, service-account key, admin or server token, LLM provider key, database password, CI or registry token.
- A **public identifier**: publishable API key, app ID, OAuth client ID, Firebase config keys meant for clients, tenant ID.

Only secrets are findings. Never test a credential you find against a live service. Judge whether it is real from its format, its context and the owner's answer. Refer to it by type, location and fingerprint, never by value.

- **SECRET-01 Secrets in shipped code and resources.** Look in:
  - source files, resource bundles and config JSON or plist files;
  - `Info.plist`, `AndroidManifest.xml` meta-data, `BuildConfig` fields, `.xcconfig`, `gradle.properties`;
  - values inlined at build time (`process.env.*`, `import.meta.env.*`, `--dart-define`, Babel env plugins);
  - generated config.

  **Report:** Vulnerability, rated by what the secret grants. A secret that mints tokens for any user, or gives admin API access, is account takeover for every user of every integrator.
- **SECRET-02 Provider keys in the client.** LLM keys (OpenAI, Anthropic, Gemini) and maps, translation, speech, GIF or link-preview keys with billing or data access. Separate keys designed for client use (restricted by bundle ID or referrer) from server keys. **Report:** a server-grade key in a client is a vulnerability: abuse, billing and access to data.
- **SECRET-03 Secrets in samples, docs and tests.** Look in:
  - demo apps and example projects;
  - README snippets and generated docs;
  - fixtures, UI-test configuration and mock servers.

  Samples get copied into production, and the repo is public. **Check:** is the credential real? Its format (test or live prefix), whether it matches a known demo environment, and whether code uses it against a real host. **Report:**
  - a real credential with meaningful access is a vulnerability, with Exposure "Sample only";
  - credentials for a public demo environment: say what they grant (usually Low, or hardening);
  - placeholders and fake fixtures are Clean.
- **SECRET-04 Secrets in git history.** Removed files and edited lines stay in history, in forks and in every clone. **Check:** the recon script with `--history`, plus deleted `.env` files, keystores, `.p8`/`.p12` files and service-account JSON. **Report:** as SECRET-01 or SECRET-03, unless the owner confirms rotation. Recommend rotation; rewriting history is not enough.
- **SECRET-05 Secrets in published artifacts.** Look for:
  - source maps with `sourcesContent`;
  - `.env` or config files in npm tarballs, wheels and gems;
  - test-support products;
  - XCFramework and AAR resources and assets;
  - container images.

  See DIST-01.
- **SECRET-06 Secrets in CI and release tooling.** Look for:
  - plaintext values in workflows, Fastfiles and Makefiles;
  - `.npmrc` `_authToken`, `.pypirc`, `.netrc`;
  - signing passwords, and keystores with their passwords next to them;
  - `set -x` or `echo` printing secrets into public logs;
  - secrets written into artifacts or caches.
- **SECRET-07 Hard-coded credentials and backdoors.** Look for:
  - default passwords, shared test accounts, master keys;
  - "skip auth" flags;
  - magic user IDs or headers that bypass checks;
  - debug endpoints that also work in release builds.
- **SECRET-08 Obfuscation used as protection.** XOR'd, base64'd, split or "encrypted" keys whose decryption key ships alongside. Treat them as plaintext and report them under SECRET-01 or SECRET-02.

## 2. AUTH: tokens, credentials and authentication

- **AUTH-01 Non-expiring and long-lived tokens.** Look for:
  - JWTs without `exp`, or with lifetimes of months or years, in samples, docs, fixtures, test-support products and CI;
  - token helpers (dev tokens, server-SDK `createToken`) whose expiry is optional or off by default;
  - a connect API that accepts a static token only when it never expires, while expiring tokens need a refresh callback. That makes "static, non-expiring" the easy path that quick starts teach.

  **Check:**
  - recon's JWT table: claims and `exp`, never the signature;
  - the defaults of every token helper;
  - what the quick-start docs and samples pass to connect.

  **Report:**
  - a non-expiring credential that ships, is the default, or is what samples teach for production: a vulnerability, rated by what the token grants and who can get it;
  - an SDK that merely *allows* non-expiring tokens: hardening.

  Either way, a non-expiring token turns every token leak (LOG-01, AUTH-05, AUTH-07, STORE-06) into permanent access. Say so in those findings.
- **AUTH-02 Expiry and refresh.**
  - Is there a refresh path: a token provider, or a refresh token?
  - What happens when refresh fails? Does the client keep the stale token, fall back to a cached or another user's token, or silently go anonymous?
  - Are refresh tokens stored with the same care as access tokens?
  - Does the client act on `exp`, or only on 401s?

  **Report:** using a stale credential, or another user's, is a vulnerability (see SESSION-02). Retry loops with no attacker are reliability problems, not findings.
- **AUTH-03 Development, guest and unsigned token modes.** Dev tokens, `alg: none`, fixed or empty signatures, "auth disabled" switches, anonymous or guest modes. **Check:**
  - Is the mode clearly named and opt-in?
  - Does a production backend reject it by default (documented, or server source in scope)?
  - Do samples use it the way integrators will copy it?

  **Report:**
  - a dev mode that works against production by default, or that samples present as the normal path, is a vulnerability: anyone can impersonate any user;
  - a clearly labelled helper that production rejects is Clean.
- **AUTH-04 Client-side token minting.** Any signing of auth tokens in client code, samples or test-support products; a secret must then ship. Report it here and under SECRET-01 or SECRET-03.
- **AUTH-05 Tokens in URLs.** Look in:
  - query strings of REST and WebSocket connect URLs;
  - signed media URLs and redirect URLs.

  From there tokens reach:
  - server, proxy and CDN logs;
  - analytics, crash reports and `Referer` headers;
  - browser history;
  - the SDK's own request logging.

  **Check:** build the connect URL and every request URL, then find every log, error and callback that includes them. **Report:**
  - a session token in a URL that gets logged or sent to a third party: a vulnerability (pair with LOG-01);
  - a token in the query of a TLS WebSocket connect to the vendor's own host: common practice, hardening at most, unless it is logged.
- **AUTH-06 Credentials sent to the wrong host.** Look for:
  - a shared HTTP client, interceptor or cookie store that attaches auth to URLs taken from content: attachments, images, previews, avatars, model-provided URLs;
  - redirects across hosts;
  - configurable base URLs.

  **Check:** trace every request path that takes a URL from content or configuration, and list the headers it sends. Verify redirect behavior with a local redirect server, not from documentation. **Report:** a token sent to a host a peer chose is High-shaped.
- **AUTH-07 Token storage.**
  - Plain preferences, files, databases or web storage, vs secure storage.
  - Keychain accessibility class, and iCloud Keychain sync.
  - Inclusion in device backups.
  - Copies kept after logout.
  - Tokens in extension or app-group containers.

  **Report:** rate by attacker (physical, backup, local app): usually Low to Medium. Medium to High when a long-lived token lands where other apps or backups can read it.
- **AUTH-08 Tokens exposed through the API surface.** Look for:
  - public getters for the raw token;
  - tokens in delegate, callback and event payloads;
  - `description`/`debugDescription`/`toString`/`__repr__`/`inspect` of tokens, clients, configs, requests and errors;
  - `Codable`/`Serializable` encoding of objects that hold a token;
  - request objects handed to integrator interceptors and analytics hooks.

  **Report:**
  - a vulnerability when a default path sends the token somewhere persistent or third-party (logs, crash reports, analytics);
  - otherwise hardening: redact it in descriptions.
- **AUTH-09 Token and user binding.**
  - Does the client check that the token's subject is the user it connects as?
  - Can user A's token be in use while local state says user B (mixed caches)?
  - What happens when a guest upgrades to a user?

  **Report:** when it leads to cross-user data (see SESSION).
- **AUTH-10 Revocation on logout.** Does logout call the product's revoke or invalidate endpoint (if one exists), or only drop the token locally? With non-expiring tokens, a leaked token then stays valid forever. **Report:** usually hardening. Mention it in token-leak findings.
- **AUTH-11 Unverified token contents used for decisions.** Reading roles, permissions or user IDs from an unverified JWT payload to decide what the user may do. Using them for display is fine.
- **AUTH-12 OAuth, SSO and login flows** (if the SDK runs one):
  - system browser (`ASWebAuthenticationSession`, Custom Tabs) vs an embedded web view, which enables credential phishing and cookie access;
  - PKCE, `state`, exact redirect-URI matching, no implicit flow;
  - no client secret in the app;
  - no codes or tokens in logged URLs or fragments.
- **AUTH-13 Local authentication gates.** For biometric or passcode "app lock" features:
  - a boolean check, bypassable on a compromised device, vs a key released by secure hardware (Keychain access control, `BiometricPrompt` with a `CryptoObject`);
  - the fallback paths.

  **Report:** only against what the SDK claims.
- **AUTH-14 End-user passwords and one-time codes** (if the SDK handles them):
  - never logged, stored, kept in long-lived state, or sent anywhere but the auth endpoint;
  - secure text entry;
  - OTP autofill hints.
- **AUTH-15 What the public key alone allows.** Find out from the docs or the owner what the client-shipped API key permits without a user token: anonymous access, user creation, reading public data. A public key that allows privileged operations is a secret in disguise. That's a server-configuration issue: an open question unless it's confirmed.

## 3. TLS: transport security

- **TLS-01 Cleartext allowed.** Look for:
  - `http://` or `ws://` defaults and fallbacks;
  - configurable hosts that silently accept cleartext;
  - ATS or network-security-config exceptions in the SDK's own manifests (on Android, they merge into the host app) and in samples.
- **TLS-02 Certificate validation disabled or weakened.** Look for:
  - trust-all managers, and hostname verifiers that return true;
  - custom trust evaluation that ignores the result;
  - `verify=False`, `InsecureSkipVerify`, `rejectUnauthorized: false`;
  - debug switches that disable validation and can be on in release;
  - user-installed CAs trusted in release builds (Android).
- **TLS-03 Pinning.** If present: does it fail open on error, can configuration turn it off, are there backup pins, does it expire? A missing pin isn't a vulnerability; at most it's hardening for high-value SDKs.
- **TLS-04 Redirects.** HTTPS-to-HTTP downgrades, and credentials or custom auth headers carried to another host (see AUTH-06). Platform defaults differ by OS version and by header, so verify with a local redirect server.
- **TLS-05 WebSockets and long-lived connections.**
  - `wss` only, with the same trust rules as HTTP;
  - tokens in the connect URL (AUTH-05);
  - frame and message size limits (INPUT-05).
- **TLS-06 Secondary channels.** Each of these is its own transport to check:
  - uploads, CDN and link previews;
  - GIF providers and model endpoints;
  - analytics and crash reporting;
  - push providers and remote config.
- **TLS-07 Interception hooks.** Public interceptors, custom session or client injection and proxy settings are fine as API. Check that the docs don't suggest logging bodies, or disabling trust, in production.
- **TLS-08 Protocol versions and ciphers.** Explicitly enabled TLS 1.0 or 1.1, weak cipher lists, flags that accept expired or invalid certificates.

## 4. INPUT: parsing untrusted data

Data from the server or from other users must never crash, hang or corrupt the client. In a collaborative product, a payload that crashes the client is a remote denial of service against everyone who receives it. It is often persistent too: the payload is re-delivered, or re-read from the local cache, on every launch.

- **INPUT-01 Trapping operations on decoded data.** Look for:
  - force unwraps, forced casts, `try!`, `!!`, unchecked indexing;
  - `fatalError`/`precondition`/`require`/`check` running in release on payload data;
  - dictionary initializers given duplicate keys;
  - ranges whose lower bound exceeds the upper.
- **INPUT-02 Numeric conversions and arithmetic.**
  - floating-point to integer conversions that trap on NaN, infinity or out-of-range values (Swift `Int(Double)`);
  - checked arithmetic that traps on overflow, and `Math.toIntExact`;
  - C casts (undefined behavior);
  - sizes from payloads used in allocations.
- **INPUT-03 Date and time conversions.** Dates converted to integer nanoseconds or microseconds overflow for far-future or far-past values: 64-bit nanoseconds end in 2262. Look for user-settable timestamps (expiry; pin, mute or ban until; scheduled sends; reminders) flowing into custom date parsers.
- **INPUT-04 Recursion depth.** Recursive decoders, renderers and evaluators with no depth limit on nested input (JSON, Markdown, expression trees, UI component trees). Secondary threads often have small stacks (512 KiB on Apple GCD threads). A generic "any JSON" type that recurses once per level can overflow at a few hundred levels, below the platform parser's own limit. Free-form custom-data fields are the usual vector.
- **INPUT-05 Resource budgets.** Huge strings and arrays, quadratic algorithms on attacker-sized input, unbounded caches. Check every axis:
  - total bytes downloaded or buffered;
  - decoded dimensions;
  - node and component count;
  - recursion depth;
  - concurrency;
  - CPU or time per render, including repeated work on every streaming update;
  - cache growth.

  Read the caps that exist before calling something unbounded. "Each download is capped, but nothing limits how many run at once" is a narrower finding.
- **INPUT-06 Decompression and archives.** Gzip, zip and image bombs; zip slip (entry names with `..` or absolute paths).
- **INPUT-07 Regular expressions.** Patterns built from input, and catastrophic backtracking on content: mentions, links, emoji, Markdown.
- **INPUT-08 Unsafe deserialization.** Native object formats used on data that crosses a trust boundary:
  - Apple: `NSKeyedUnarchiver` without secure coding;
  - Java: `ObjectInputStream`, Jackson default typing;
  - Python: `pickle`, `yaml.load`;
  - Ruby: `Marshal.load`;
  - .NET: `BinaryFormatter`, Newtonsoft `TypeNameHandling`;
  - PHP: `unserialize`.
- **INPUT-09 XML.** External entities or DTD processing enabled (XXE); entity-expansion bombs.
- **INPUT-10 Injection into interpreters.**
  - format strings: `String(format:)`, `printf`, `NSLog(var)`;
  - SQL and predicates built by interpolation: `NSPredicate(format:)`, `rawQuery`. Local query injection is usually low impact, but can expose other locally cached data;
  - `NSExpression(format:)`, which can call methods;
  - shell commands;
  - CR/LF in header values;
  - unescaped path segments in API URLs (see LINK-04).
- **INPUT-11 Type confusion and object pollution.**
  - loosely typed payloads (string vs number vs object) that reach a crash path or a security decision;
  - JavaScript prototype pollution through deep-merge or set-by-path of payload JSON (`__proto__`);
  - server payload fields that overwrite local-only state (mass assignment).
- **INPUT-12 Unicode.**
  - bidi overrides and zero-width characters in names and file names shown as trusted metadata;
  - normalization or case-folding differences between a check and a use (mention resolution, allowlists, file names);
  - homoglyph display names (see RENDER-05).
- **INPUT-13 Bad payloads persisted locally.** Is a bad payload stored in the local database or cache and decoded again at launch, before the user can do anything? That makes a crash loop that lasts until reinstall. Check the startup path.

## 5. RENDER: rendering untrusted content

- **RENDER-01 Script execution.**
  - web views showing content: JavaScript enabled, file access, universal access from file URLs, JS bridges that content can reach;
  - `innerHTML` and its equivalents;
  - HTML attachments previewed in a web view;
  - `NSAttributedString` HTML import.
- **RENDER-02 Markdown and rich text.** Is raw HTML enabled? Is output sanitized by a maintained sanitizer with a strict config, not a homemade regex? Do custom renderers build HTML strings? Check `javascript:` and `data:` link destinations under LINK-01.
- **RENDER-03 SVG and active formats.** Inline SVG with scripts or external references; PDFs or HTML opened in-process.
- **RENDER-04 Remote resources loaded automatically.** Images, link previews, avatars, video thumbnails and map snapshots from arbitrary URLs leak the viewer's IP, user agent and read time to whoever controls the URL (a tracking pixel). Client-side link-preview fetching leaks the same way, and on desktop it can reach internal hosts. It's worse with model output (AI-03). **Report:** a Low or Medium privacy leak when URLs a peer chose load on render with no proxy. Note it if the product promises otherwise.
- **RENDER-05 Spoofing.**
  - fake system or admin messages;
  - display names, avatars or mentions that imitate another user;
  - content that imitates SDK chrome: buttons, approval dialogs, "verified" badges;
  - bidi tricks in file names (`invoice<U+202E>fdp.exe`, shown as `invoiceexe.pdf`).

  Link text that differs from its destination is ordinary Markdown and HTML behavior, and IDN homographs are an ecosystem-wide display problem. Both are hardening at most, unless the SDK presents the text as verified or hides the destination where users expect to see it.
- **RENDER-06 Renderer complexity.** Markdown renderers, syntax highlighters and layout code are often recursive or super-linear. Probe with short pathological inputs:
  - one very long token or whitespace run in a code block;
  - a few hundred nested quotes;
  - 15 to 20 nested lists;
  - a table with a wide header and thousands of short rows.

  On the UI thread, these become a persistent crash or freeze of the screen that shows them.
- **RENDER-07 Media decoding.** Bundled third-party decoders (GIF, WebP, APNG, video); huge dimensions or frame counts that exhaust memory; missing downsampling.
- **RENDER-08 Custom content types.** Every custom attachment, poll, location, contact card, sticker or embed has its own parser and renderer: apply INPUT and RENDER to each. Location shares and map previews also send coordinates to third parties.
- **RENDER-09 Notification content.** Message content shown in local or push notifications and on the lock screen: the SDK's default vs what the product promises.

## 6. LINK: links, URLs and navigation

- **LINK-01 Scheme allowlists.** Before opening any URL from content or model output:
  - allow `http`, `https` and `mailto` (and `tel`, with confirmation);
  - block `javascript:`, `data:`, `file:`, `content:`, `intent:` and app-specific schemes.

  **Report:**
  - opening a non-web URL without a user gesture, or from a control whose appearance hides the destination: a vulnerability;
  - after a deliberate tap on a visible link: a conditional vulnerability at most, usually Low. The impact depends on the host's own handlers. Recommend a web-only default, and rate higher only with a concrete sensitive action in a realistic host.
- **LINK-02 Deep links into the host app.** Content or model output that opens the host's own URL scheme or universal links can drive in-app actions: one-tap actions, OAuth callbacks, payments. A safe default is "web links only; the integrator can widen it".
- **LINK-03 Hidden destinations.** Buttons, cards or generated UI that open URLs without showing them.
- **LINK-04 URL construction.**
  - untrusted path segments concatenated into API URLs (`../admin`);
  - unescaped query components;
  - protocol-relative `//attacker.com` treated as a relative URL;
  - base-URL overrides taken from content.
- **LINK-05 Parser differentials.** A URL validated with one parser and opened with another; checks on a string prefix; tricks with percent-encoding and Unicode.
- **LINK-06 Where links open.** The system browser, `SFSafariViewController` or Custom Tabs, vs an in-app web view without browser protections (phishing; no address bar). `target="_blank"` without `rel="noopener"` is minor in modern browsers.
- **LINK-07 Data detectors.** Automatic linking of phone numbers, addresses and dates in peer content gives one tap to call or open maps. That's fine as a visible link; note it if it dials without confirmation.
- **LINK-08 Open redirects.** SDK-hosted pages or server-SDK helpers that redirect to a URL taken from a parameter.

## 7. STORE: local storage, files and caches

- **STORE-01 At-rest protection.** Databases, caches, logs and downloaded attachments: platform file-protection classes, encryption claims, where the database lives. Flag it when the SDK documents stronger protection than it applies.
- **STORE-02 Shared or world-readable locations.**
  - app groups and shared preference suites;
  - external storage and `MODE_WORLD_*`;
  - `/tmp` and Downloads on desktop;
  - permissions on created files (umask).
- **STORE-03 File names and paths from content.** Server or peer names used in paths allow traversal (`../../Library/Preferences/x.plist`), overwriting other files, or writing outside the intended folder. Path APIs may percent-decode names. Check containment after standardizing the path.
- **STORE-04 Handling downloaded files.**
  - extension or type confusion when the saved file is opened;
  - on desktop, executables or scripts saved without the platform's quarantine mark (macOS `com.apple.quarantine`, Windows Mark-of-the-Web);
  - downloads opened automatically with the default handler.
- **STORE-05 HTTP and media caches.** Authenticated responses, signed URLs or private images cached on disk (`URLCache`, the OkHttp cache, service-worker caches) and left behind after logout (SESSION-01).
- **STORE-06 Clipboard.**
  - tokens, secrets or debug cURL commands copied to a global or synced clipboard;
  - sensitive content copied without expiry or local-only flags;
  - the clipboard read without a user action.
- **STORE-07 Backups and cloud sync.** Tokens, keys and message databases included in device or cloud backups (iCloud, `allowBackup`); Keychain items without `ThisDeviceOnly`; synchronizable Keychain items.
- **STORE-08 Temporary files and exports.** Exports, previews, decrypted copies, log bundles and share files left in temp or cache folders; predictable names; files never deleted.
- **STORE-09 Retention of deleted content.** Messages, attachments and edits that were deleted, expired, moderated or "disappearing", still in the local database, caches or thumbnails. **Report:** when the product promises deletion.
- **STORE-10 Sensitive input fields.** Secure text entry for secrets; autocorrect and keyboard learning off on secret fields; autofill hints for OTPs and passwords; secrets kept in long-lived view state.
- **STORE-11 Screen capture.** Screenshots, screen recording and app-switcher snapshots of sensitive screens. Usually the integrator's choice. **Report:** only if the SDK claims protection.

## 8. SESSION: logout, user switching and multiple accounts

- **SESSION-01 Wipe on logout and user switch.** Every trace of user A is removed before user B uses the device:
  - database, caches and files;
  - tokens and Keychain items;
  - in-memory state, pending requests, offline queues and drafts;
  - push registration;
  - extension containers.

  Cross-user exposure on shared devices (families, kiosks, support staff) is a common, high-impact SDK bug.
- **SESSION-02 In-flight work across logout.** Token-provider callbacks, request completions, retry and offline queues, and periodic workers can complete after logout and either:
  - write A's data into B's session; or
  - send B's queued actions with A's token, or A's with B's.

  Look for a session generation or user-ID check before they act.
- **SESSION-03 Push registration.** Is the device registration removed or moved on logout and user switch? Otherwise B's device receives A's notifications.
- **SESSION-04 Multiple clients and accounts.** Two client instances in one process (multi-account apps, extensions) sharing singletons, caches or database paths keyed by something other than the user.
- **SESSION-05 Extensions and background processes.** Notification, share and widget extensions still holding a token, or data, for a user who has logged out of the main app.

## 9. IPC: platform integration and IPC

- **IPC-01 URL schemes, universal links and intents** registered or recommended by the SDK; routing helpers that open screens from link parameters.
- **IPC-02 Exported components.**
  - Android activities, services, receivers and providers exported by the library manifest, which merges into the host;
  - `PendingIntent` mutability, and implicit intents;
  - `FileProvider` paths and `grantUriPermissions`.
- **IPC-03 Push payloads.** Notification service extensions and FCM handlers parse untrusted fields, may download URLs from them, and may store data in shared containers.
- **IPC-04 Files from other apps.** Share extensions, document pickers, drag and drop, `content://` URIs: untrusted names, types and sizes.
- **IPC-05 Web messaging and isolation.**
  - `postMessage` handlers without origin checks, and `postMessage(data, '*')` with sensitive data;
  - iframes without `sandbox`;
  - service workers;
  - cookies without `Secure`/`HttpOnly`/`SameSite`;
  - CORS assumptions;
  - CSP compatibility: an SDK that needs `unsafe-eval` forces integrators to weaken their CSP.
- **IPC-06 Desktop shells.** Electron `nodeIntegration`, `contextIsolation` and `sandbox`; preload bridges; `shell.openExternal` on content URLs; custom protocol handlers.
- **IPC-07 Permissions and device data.**
  - permissions requested only at the point of use;
  - library manifests that add dangerous permissions;
  - camera, microphone, location, contacts or photo data sent anywhere unexpected.
- **IPC-08 Overlays and tapjacking.** Approval and payment buttons that can be clicked through an overlay on Android (`filterTouchesWhenObscured`); clickjacking of web widgets in iframes.

## 10. LOG: logging, errors, telemetry and diagnostics

- **LOG-01 Tokens and secrets in logs.** Auth headers, tokens, API secrets, signed URLs and connect URLs in any log statement, at any level. They usually arrive through:
  - request and response dumps, and cURL renderings;
  - error descriptions;
  - URL logging of WebSocket connects.

  **Check:**
  1. Which level emits each one, and is that level on by default in release?
  2. How visible is that log on the platform: Apple unified-logging public/private, Android logcat, the browser console, server log aggregation?

  **Report:** a token in release logs by default is a vulnerability, typically Medium (local, physical or diagnostics attacker). It's higher if logs leave the device by default, or if the token never expires (AUTH-01).
- **LOG-02 Personal data and content in logs.** Message text, emails, phone numbers, names or locations at default log levels.
- **LOG-03 Release defaults.** The default log level and destinations in release builds; logging on by default; `privacy: .public` on sensitive values; `console.log` not stripped.
- **LOG-04 Log files and viewers.**
  - logs written to disk: where, how protected, how rotated;
  - in-app log viewers, "share logs" and shake-to-debug features;
  - whether release builds can reach them.
- **LOG-05 Errors and exceptions.**
  - error objects, descriptions and stack traces that carry tokens, full request URLs or headers;
  - server error bodies echoed into the UI or logs;
  - exceptions surfaced to integrators, who will log them.
- **LOG-06 Crash reporting and analytics.** Personal data or tokens in crash reports, breadcrumbs, custom keys and analytics events; whether integrators can opt out.
- **LOG-07 Telemetry the SDK sends itself.** Which personal data goes where, whether that's disclosed, and whether it can be turned off. **Report:**
  - undisclosed collection of personal data is a privacy vulnerability;
  - a missing declaration on its own is compliance, which is out of scope.
- **LOG-08 Debug features in release.** Debug menus, environment switchers, network inspectors, test hooks that read launch arguments or environment variables, and remote-config flags that change security behavior in release builds.

## 11. CRYPTO: cryptography and randomness

Find every cryptographic primitive, and every random value with a security purpose. Hashes used as cache keys, checksums against corruption and UUIDs used as message IDs are not security uses.

- **CRYPTO-01 Weak algorithms for security purposes.**
  - MD5 or SHA-1 for signatures, for integrity against attackers, or for passwords;
  - DES, 3DES or RC4;
  - ECB mode;
  - RSA without OAEP or PSS;
  - short keys.
- **CRYPTO-02 Hard-coded keys, IVs and salts.**
  - keys in the binary or the repo;
  - static or reused IVs and nonces with CTR or GCM;
  - encryption without authentication (CBC without a MAC);
  - keys derived from constants or device identifiers.
- **CRYPTO-03 Insecure randomness.** Non-cryptographic generators (`Math.random`, `java.util.Random`, `rand`, `mt_rand`, seeded generators) used for:
  - tokens and nonces;
  - OAuth `state` and PKCE verifiers;
  - temporary file names in shared directories;
  - IDs that act as capabilities.

  These are fine: `SecRandomCopyBytes`, `arc4random` and `UUID` on Apple, `SecureRandom`, `crypto.getRandomValues`, Python `secrets`, Go `crypto/rand`.
- **CRYPTO-04 Password and key derivation.** Passwords or PINs hashed without a slow KDF (PBKDF2 with many iterations, scrypt, Argon2) and a salt; keys derived with a plain hash.
- **CRYPTO-05 Signature and MAC verification.**
  - signatures and HMACs checked over the exact bytes received, not re-serialized JSON;
  - the algorithm pinned, never taken from the token;
  - `exp`, `aud` and `iss` checked wherever the SDK verifies tokens;
  - constant-time comparison;
  - replay windows and nonces honored.
- **CRYPTO-06 Integrity of downloaded code and models.** Updates, plugins, scripts, models and behavior-changing remote config are signature-checked before use, and fetched over TLS.
- **CRYPTO-07 Custom protocols and end-to-end encryption.** If the SDK claims E2EE or runs its own protocol, compare it against what the product promises:
  - who can add devices or keys silently;
  - how users verify keys;
  - forward secrecy;
  - metadata exposure;
  - fallbacks to plaintext.

## 12. CONC: concurrency and state

- **CONC-01 Races on security state.** Data races on auth, session, connection or user state that produce wrong-user requests, or crashes (memory corruption in languages without race safety).
- **CONC-02 Check-then-act.** TOCTOU on files (check if it exists, then write; check, then open) and on permissions.
- **CONC-03 Safety escape hatches.** `@unchecked Sendable`, `nonisolated(unsafe)`, `unsafe` blocks or manual locks around security-relevant state.
- **CONC-04 Reentrancy.** Callbacks into integrator code while holding locks, or in the middle of updating auth or session state.

## 13. NATIVE: memory-unsafe and native code

- **NATIVE-01 Vendored and bundled native libraries.**
  - name, version, upstream and local patches;
  - advisories fixed upstream since that version;
  - whether the vulnerable function is compiled in and reachable with attacker input (DIST-04).
- **NATIVE-02 Manual memory management in safe languages.** `UnsafeMutablePointer`, `withUnsafeBytes`, `sun.misc.Unsafe`, `unsafe` in Go, Rust or C#. At JNI and FFI boundaries: null, lifetimes, UTF-8, and panics crossing FFI.
- **NATIVE-03 Classic C sinks.**
  - `memcpy`, `strcpy`, `sprintf`;
  - length arithmetic, and integer overflow in allocation sizes;
  - use-after-free in callbacks;
  - format strings.
- **NATIVE-04 Symbol collisions.** A vendored library with unprefixed symbols linked next to the host's own copy, where the wrong version wins.
- **NATIVE-05 Dynamic loading.** Libraries loaded from writable paths, search-order hijacking on desktop, code loaded from downloaded files.

## 14. AI: AI and LLM features

Treat model output like content from an anonymous remote peer: anything in the model's context can steer it.

- **AI-01 Actions from model output.** Model output that, without the user deciding:
  - opens URLs;
  - calls client tools or runs mutations;
  - sends messages;
  - reads device data: location, contacts, files, clipboard, photos;
  - navigates the app.
- **AI-02 Approval and consent.** Look for:
  - auto-approve flags;
  - approval keyed on a name the model controls;
  - approval UI the model renders itself;
  - controls that stay live while the reply streams, so the action can change after its label was shown.

  A generated control that runs an integrator-registered tool only after a deliberate tap is not "without consent", and not a vulnerability. Hardening options: show the tool and its arguments, use SDK-owned confirmation for sensitive tools, and mark generated UI.
- **AI-03 Exfiltration channels.**
  - auto-loaded images and links whose URLs the model controls (query-string exfiltration);
  - tool arguments that carry private context to third parties;
  - URLs *computed* in generative UI (bindings, interpolation, function calls) from user input, password fields or tool results.

  Safe pattern: load only URLs that appear literally in model output, or verbatim in a tool result.
- **AI-04 Generative UI and model-written programs.**
  - a sandbox: no reflection, no arbitrary host calls;
  - resource limits: depth, nodes, loops, string sizes, evaluation time;
  - the cost of re-evaluating on every streaming update.
- **AI-05 Confused deputy.** Which host tools, queries and mutations a program or tool call can invoke, with whose privileges, and how their arguments are validated.
- **AI-06 Cross-context reads.** Programs or tool calls reading state they shouldn't: other surfaces, other conversations, other users' data, hidden form fields.
- **AI-07 Prompt injection into privileged context.** Untrusted content (messages, web pages, files, tool results) placed in system or developer roles, or concatenated into instructions without delimiters.
- **AI-08 Secrets in prompts and tool definitions.** System prompts, hidden context and tool schemas shipped in the client are public. Flag secrets in them, or security that depends on keeping them secret. For provider keys, see SECRET-02.
- **AI-09 Local models.** Where model files are downloaded from and loaded; whether their integrity is checked; formats that run code on load (pickle-based checkpoints).
- **AI-10 Rendering model output.** Markdown, code blocks, and "run" or "copy" affordances: apply RENDER and LINK to model output.

## 15. AUTHZ: client-side authorization assumptions

The server must enforce permissions; the SDK only reflects them. Findings here are about the SDK claiming or implying enforcement it can't provide, or delivering data it only hides.

- **AUTHZ-01 Enforcement in the UI only.** A hidden button whose API call is still possible isn't an SDK vulnerability unless the server doesn't check either. List it as "verify server-side".
- **AUTHZ-02 Privacy features enforced on the client.** Hidden read receipts, invisible mode, blocks and mutes, deleted or moderated messages, shadow bans: if the data still reaches the device and is only hidden, anyone with a proxy sees it. **Report:** severity depends on what the product promises.
- **AUTHZ-03 Over-fetching.** Payloads carrying other users' emails, phone numbers, IP addresses, devices, or private fields the UI never shows.
- **AUTHZ-04 Local state used for decisions.** Cached roles or permissions still used after they changed on the server; local "is admin" flags.
- **AUTHZ-05 Identity supplied by the client.** Requests in which the client sends a user ID, role or tenant that the server might trust instead of the token. Verify it server-side; it stays an open question unless server source is in scope.

## 16. SUPPLY: supply chain, build and CI

- **SUPPLY-01 Dependency pinning.** Lock files committed for the repo's own builds; dependencies on branches or unpinned git refs. Version ranges in published library manifests are normal.
- **SUPPLY-02 Binary dependencies.** Binary targets, prebuilt frameworks and native libraries without checksums or provenance.
- **SUPPLY-03 Provenance of vendored code.** Version and commit recorded, an update script, local patches documented.
- **SUPPLY-04 Code that runs at build or install time.** Package-manager lifecycle scripts, build plugins, codegen with network access, Run Script phases.
- **SUPPLY-05 Privileged CI triggers.**
  - `pull_request_target`, `workflow_run` and comment-triggered jobs that check out or build untrusted code while holding secrets or write tokens;
  - self-hosted runners on public repos.
- **SUPPLY-06 Script injection.** Event fields (titles, bodies, branch names, commit messages) interpolated into shell. Trace it through shared actions, reusable workflows and plugins (fastlane plugins, composite actions) at the version the lock file pins.
- **SUPPLY-07 Unpinned third-party actions** in jobs that hold secrets or write tokens.
- **SUPPLY-08 CI secrets and token scope.**
  - secrets available to fork PRs, printed to logs, or written to artifacts;
  - overly broad `GITHUB_TOKEN` permissions;
  - cache poisoning between untrusted jobs and release jobs.
- **SUPPLY-09 Unverified downloads.** `curl | sh`; tools downloaded without checksum or signature verification.
- **SUPPLY-10 Release integrity.**
  - who can publish, and registry 2FA;
  - signing, provenance and attestations;
  - tag and branch protection;
  - release jobs triggered by mutable refs.
- **SUPPLY-11 Dependency confusion and typosquatting.** Internal package names that resolve from public registries; registry scoping; look-alike dependency names.
- **SUPPLY-12 Committed binaries** of unknown origin: `.ipa`, `.apk`, `.jar`, `.so`, `.a`, `.xcframework`.

Report each root cause on its own, with its preconditions. They have different owners and severities:
- "an admin must comment `/merge` on the attacker's PR" (injection);
- "an upstream tag must be moved" (unpinned action);
- "the download host must be compromised" (no checksum).

## 17. API: defaults, API design, samples and docs

- **API-01 Insecure defaults.** Secure by default, with an integrator opt-out, for each of these:
  - logging level and debug features;
  - TLS;
  - approvals;
  - auto-loading media and opening links;
  - data retention and storage encryption.
- **API-02 APIs that invite misuse.** Names and docs that make the insecure path the easy one:
  - `devToken` in production samples;
  - `allowAllCertificates`;
  - "pass your secret here";
  - a static, non-expiring token as the quick-start path.
- **API-03 Missing security hooks.** No way to:
  - restrict link schemes;
  - disable remote images;
  - clear data on logout;
  - supply a trust policy;
  - redact logs;
  - require approval for tools.
- **API-04 Samples and docs.** Sample apps, README snippets and docs that show hard-coded tokens and secrets, dev tokens, disabled TLS, broad permissions or insecure storage. Samples get copied into production. **Report:** Exposure is "Sample only".
- **API-05 Failing open.** Errors in security checks treated as success: pin validation errors, permission lookups, signature-verification exceptions, approval timeouts.

## 18. DIST: distribution, dependencies and release artifacts

- **DIST-01 Artifact parity.** What integrators install is not the repository:
  - Build or dry-run each distribution channel and list its contents.
  - Look for files the manifest adds or drops, prebuilt or minified bundles, source maps, generated code, native libraries, install scripts, and test-support products that ship secrets or insecure code.
  - A safe source file that isn't packaged, sitting next to an old vulnerable bundle that is, means the bundle is what you audit.
- **DIST-02 Channel differences.** The same SDK can ship differently through each package manager: resources, compiler flags, optional modules, minimum OS. Note which channels each finding applies to.
- **DIST-03 Exact dependencies.**
  - Record the resolution source (lock file, resolved file) and the revision of every first-party and security-relevant dependency. Audit those revisions, not whatever is cached locally.
  - First-party dependencies used only by a debug or optional product still need a disposition, even if it's "excluded: debug-only, not reviewed".
- **DIST-04 Advisories and applicability.**
  1. Run the ecosystem's advisory tool, and record its name and the database date.
  2. For each hit, decide whether it applies: is the vulnerable function or extension compiled in, and reachable with attacker input?
  3. Report applicable advisories as findings. List the others under "Reviewed and rejected", with the reason.
  4. Check vendored copies by hand against the upstream changelog and advisories; scanners don't see them.
  5. For memory-safety advisories in vendored native code, close the question explicitly, one way or the other.
- **DIST-05 Test-support and sample code in packages.** Test helpers, mock servers and samples published as products or included in packages: what they contain (secrets, insecure defaults) and whether they can end up in release builds.
- **DIST-06 Debug information.** Source maps, debug symbols, internal paths and hostnames in what ships. That's information disclosure, usually hardening.
- **DIST-07 Support-policy impact.** Which released versions contain each finding, and the first version that will contain the fix. Integrators pinned to older versions stay exposed.

## Coverage ledger

Keep the ledger next to the report as `<report-name>-coverage.md`, private like the report. Give every catalog item one row:

```markdown
| ID | Result | Evidence |
|---|---|---|
| AUTH-01 | Finding SEC-07 | `Sample/Credentials.kt:12`: sample token has no `exp`; README quick start uses it |
| AUTH-12 | N/A | The SDK runs no login flow |
| LOG-01 | Finding SEC-03 | `HttpLogger.kt:48` logs request headers at info level, on by default |
| TLS-02 | Clean | No custom trust handling: the OkHttp client keeps the platform trust manager (`NetworkModule.kt:30`) |
| CRYPTO-07 | Not checked | No E2EE claims found; owner to confirm |
```

Use one of these results:
- `Finding SEC-n`, or `Hardening H-n`;
- `Rejected`, with the reason (also listed under "Reviewed and rejected" in the report);
- `Clean`;
- `N/A`, with why;
- `Not checked`, with why.

"Clean" needs evidence: what you read or ran, not "no grep hits". When an item has several results (one finding and one hardening line, say), list them all. The report's Method section gives the counts and lists every item that's Not checked.
