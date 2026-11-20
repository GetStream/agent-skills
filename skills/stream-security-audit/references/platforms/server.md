# Server-side SDKs (Go, Python, Ruby, Node, Java/Kotlin, .NET, PHP, Rust)

Server SDKs hold the product's **secret** (API secret, signing key) and run in the integrator's backend. The threat model shifts: the attacker is usually an end user of the integrator's app who controls values the backend passes to the SDK (user IDs, file names, URLs, webhook bodies), or a network attacker. Read with `../checklist.md`; sections 1, 2, 3, 9 and 14 matter most.

## Secrets and tokens
- How the secret is supplied (env var, constructor) and whether it can leak: `__repr__`/`toString`/`inspect` of client objects, exception messages, debug logs, HTTP client logging of headers, serialization of the client object.
- Token generation (JWT): algorithm pinned (no `none`, no algorithm taken from input), `exp`/`iat` set and sensible by default, claims built from structured input (no string-concatenated JSON), secret length checks. A helper whose expiry is optional and off by default mints permanent credentials in every integrator's backend (AUTH-01): check the default, the docs' examples, and whether there is a way to revoke tokens.
- Token verification helpers: algorithm allowlist, `kid` handling, audience/issuer checks, clock skew limits.
- Webhook signature verification: HMAC over the **raw** body (not re-serialized JSON), constant-time comparison (`hmac.compare_digest`, `crypto.timingSafeEqual`, `MessageDigest.isEqual`, `hmac.Equal`, `ActiveSupport::SecurityUtils.secure_compare`, `CryptographicOperations.FixedTimeEquals`, `hash_equals`), timestamp/replay window if the protocol has one.

## Requests built from integrator input
- URL path construction with user-controlled IDs: path traversal against the API (`../`), unescaped segments, query injection. Each ID should be escaped as a path segment.
- SSRF: SDK methods that fetch a URL given by the caller (file import, image upload by URL, link preview): do they restrict schemes/hosts, follow redirects to internal addresses, or send the API secret to that URL?
- Header injection: CR/LF in values placed into headers.
- Multipart uploads: file names from users placed into `Content-Disposition` without escaping.

## Transport
- TLS verification flags: Python `verify=False`, Go `InsecureSkipVerify`, Node `rejectUnauthorized: false`, Java trust-all managers, .NET `ServerCertificateCustomValidationCallback = (...) => true`, PHP `CURLOPT_SSL_VERIFYPEER => false`, Ruby `VERIFY_NONE`.
- Base URL overrides accepting `http://`; proxy environment variables honored silently (`HTTP(S)_PROXY`) - usually fine, note if secrets would go to a proxy unexpectedly.
- Retries on non-idempotent requests (duplicate side effects), unbounded timeouts (resource exhaustion in the integrator's server).

## Parsing and local operations
- Deserialization: `pickle`, `yaml.load` (use `safe_load`), `Marshal.load`, `ObjectInputStream`, `BinaryFormatter`, Newtonsoft `TypeNameHandling`, PHP `unserialize`.
- XML: external entities (Java `DocumentBuilderFactory`, Python `xml.etree` with `lxml` resolvers, .NET `XmlDocument` with `XmlResolver`, PHP `libxml_disable_entity_loader` legacy).
- Archives: zip slip, decompression bombs.
- Command execution: `subprocess` with `shell=True`, `os.system`, `exec.Command("sh", "-c", ...)`, `Runtime.exec(String)`, backticks in Ruby, `child_process.exec`.
- Temp files: predictable names, world-readable permissions.
- ReDoS in validation helpers.

## Language-specific notes
- **Go**: `http.DefaultClient` has no timeout; `io.ReadAll` on unbounded bodies; ignoring `err` from crypto functions.
- **Python**: `requests` without `timeout`; `str.format` with user templates (attribute access).
- **Ruby**: `send`/`public_send` with user method names; `open()` (Kernel) with user strings -> command execution via `|cmd`; `YAML.load` (Psych 4 is safe by default).
- **Node**: prototype pollution in option merging; `Buffer` allocation from sizes in input.
- **Java/Kotlin**: Jackson default typing (`enableDefaultTyping`/`activateDefaultTyping`) -> gadget deserialization.
- **.NET**: `JsonSerializerSettings.TypeNameHandling`, `Process.Start` with user strings.
- **PHP**: loose comparison (`==`) of signatures/tokens, `unserialize`, `extract()`.

## Distribution and release artifacts
- Python: `python -m build`, then `unzip -l dist/*.whl` and `tar -tzf dist/*.tar.gz`; `pip-audit -r requirements.txt` or on the lock file.
- Ruby: `gem build *.gemspec` then `tar -xOf *.gem data.tar.gz | tar -tz`; `bundle audit check --update` (record the date).
- Node: see `web-js.md` (`npm pack --dry-run`, `npm audit --omit=dev`).
- Go: modules ship as source, so check `go.mod` and `go.sum`, and run `govulncheck ./...`. It reports only vulnerabilities whose functions are actually called, which is the applicability check you want.
- Java/Kotlin: inspect the published jar and POM; `osv-scanner` or OWASP dependency-check.
- .NET: `dotnet pack`, then `unzip -l *.nupkg`; `dotnet list package --vulnerable --include-transitive`.
- PHP: `composer archive --dry-run` (or check `.gitattributes export-ignore`); `composer audit`.
- Note when examples or test helpers ship in the package and contain credentials or insecure defaults.

## Useful greps
```
rg -n 'verify\s*=\s*False|InsecureSkipVerify|rejectUnauthorized|VERIFY_NONE|ServerCertificateCustomValidationCallback|CURLOPT_SSL_VERIFYPEER'
rg -n 'compare_digest|timingSafeEqual|secure_compare|hash_equals|hmac\.Equal|FixedTimeEquals|==\s*signature|signature\s*=='
rg -n 'jwt\.(encode|decode|sign|verify)|algorithms?=|alg'
rg -n 'pickle|yaml\.load|Marshal\.load|ObjectInputStream|TypeNameHandling|unserialize|activateDefaultTyping'
rg -n 'shell=True|os\.system|exec\.Command|Runtime\.getRuntime|child_process|Process\.Start'
rg -n 'timeout' # check presence on HTTP clients
```
