# Web and JavaScript/TypeScript (browser SDKs, React/Vue/Angular/Svelte components, Node clients)

Read with `../checklist.md`. For server-side Node SDKs also read `server.md`.

## Credentials and storage
- Tokens in `localStorage`/`sessionStorage`/IndexedDB are readable by any script on the origin (XSS anywhere in the host app = token theft). Not always avoidable for a client SDK, but flag long-lived tokens there, and check whether the SDK offers in-memory or cookie-based options.
- Cookies set by the SDK: `Secure`, `HttpOnly` (if the SDK doesn't need to read them), `SameSite`.
- Secrets in the bundle: anything in client code is public. Check build-time env injection (`process.env.*`, `import.meta.env.*`) for secrets, and published source maps.
- Tokens in URLs: WebSocket connect URLs, image URLs with signed tokens, `Referer` leaks to third parties (check `referrerPolicy` on images/links).
- Token objects (AUTH-08): classes holding a token print it through `console.log(obj)`, `JSON.stringify` and error reporters. Keep the raw value in a private field (`#token`) and define `toJSON` / `[Symbol.for('nodejs.util.inspect.custom')]` to redact.
- Randomness (CRYPTO-03): `Math.random()` for nonces, `state`, PKCE verifiers or IDs that grant access; use `crypto.getRandomValues` / `crypto.randomUUID`.

## Transport
- `ws://`/`http://` defaults or fallbacks; mixed content; custom base URLs.
- `fetch`/`XMLHttpRequest` with `credentials: 'include'` to configurable or content-derived hosts.
- Node clients: `rejectUnauthorized: false`, `NODE_TLS_REJECT_UNAUTHORIZED`, custom agents.

## Rendering untrusted content (XSS)
- Sinks: `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, React `dangerouslySetInnerHTML`, Vue `v-html`, Angular `bypassSecurityTrust*`, Svelte `{@html}`, jQuery `.html()`, `srcdoc`, `setAttribute('href'|'src'|'on*')`.
- Markdown -> HTML: which library, is raw HTML enabled, is output sanitized (DOMPurify with a safe config, not a homemade regex)? Custom renderers that build HTML strings.
- `href` from content: `javascript:` and `data:` URLs pass React's warnings in older versions; check explicit allowlists. `target="_blank"` without `rel="noopener"` (minor in modern browsers).
- SVG from content rendered inline (scripts, external references); `<img>` SVGs are safe from script but still fetch.
- CSS injection via `style` props from content (data exfiltration via `url()`, UI redress).
- Link previews/embeds: iframes from content (`sandbox` attribute, `allow` list).

## Messaging and isolation
- `window.addEventListener('message')` without `event.origin` checks; `postMessage(data, '*')` with sensitive data.
- Iframe-based widgets: sandboxing, origin validation both ways.
- Service workers registered by the SDK: scope, cache poisoning, handling of auth headers.
- CSP compatibility: does the SDK require `unsafe-eval`/`unsafe-inline` (blocks integrators from a strict CSP)? Any `eval`, `new Function`, `setTimeout(string)`?

## JavaScript-specific bugs
- Prototype pollution in deep-merge/set-by-path utilities fed with payload JSON (`__proto__`, `constructor.prototype`).
- ReDoS: regexes with nested quantifiers on content (mentions, links, emoji, markdown).
- `JSON.parse` of huge payloads on the main thread; unbounded recursion in renderers.
- `Math.random()` for IDs that matter for security (nonces, request IDs used for idempotency are fine).
- Type confusion: payload numbers as strings reaching arithmetic or comparisons.

## Supply chain (npm)
- `package.json` dependency ranges in published packages are normal; check for git/URL dependencies, `postinstall`/`preinstall` scripts in the SDK itself, and deprecated or typo-squattable package names.
- `files`/`.npmignore`: does the published tarball include tests, `.env`, source maps with secrets?
- Lock files committed for the repo's own builds; `npm ci` in CI; provenance (`npm publish --provenance`).
- Bundled third-party code (minified vendor files) with known CVEs.

## Electron
See `cross-platform.md`.

## Distribution and release artifacts
- `npm pack --dry-run` (or `pnpm pack`, `yarn pack --dry-run`) lists exactly what is published. Compare with `files` / `.npmignore` and `exports`. Committed or prebuilt `dist/` bundles, minified code and source maps ship as is, and are what integrators run. Audit them, not only `src/`.
- Source maps (`*.map`) in the package can disclose original source, internal paths or embedded secrets. Check `sourcesContent`.
- Lifecycle scripts in the published `package.json` (`preinstall`, `install`, `postinstall`, `prepare`) run on integrators' machines.
- CDN builds (UMD/IIFE on unpkg, jsDelivr) can differ from the npm entry points: check what the docs tell integrators to load, and whether they are told to use SRI hashes.
- Exact versions: `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock`. Advisories: `npm audit --omit=dev --json`, `osv-scanner scan source -r .`. Record the date, and decide reachability: is the vulnerable function imported in shipped code?

## Useful greps
```
rg -n 'innerHTML|outerHTML|insertAdjacentHTML|dangerouslySetInnerHTML|v-html|bypassSecurityTrust|\{@html|document\.write|srcdoc'
rg -n 'addEventListener\(.message|postMessage\(|origin'
rg -n 'localStorage|sessionStorage|indexedDB|document\.cookie'
rg -n 'eval\(|new Function|setTimeout\(["'"'"']'
rg -n 'marked|markdown-it|remark|showdown|DOMPurify|sanitize'
rg -n '__proto__|deepMerge|merge\(|set\(.*path'
```
