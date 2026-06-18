# Stream Swift - setup flow (integrate / new app)

Run this once per session for integrate or new-app requests, before feature work. How-to / reference requests skip this entirely and go straight to docs lookup. Obey [`RULES.md`](RULES.md) throughout.

---

## 1. Project signals (read-only probe)

Detect the project shape once:

```bash
bash -c 'echo "=== XCODE ==="; find . -maxdepth 3 \( -name "*.xcodeproj" -o -name "*.xcworkspace" \) -print 2>/dev/null; echo "=== MANIFESTS ==="; find . -maxdepth 3 \( -name "Package.swift" -o -name "Package.resolved" -o -name "Podfile" \) -print 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Interpret and hold in context:

- `*.xcodeproj` / `*.xcworkspace` -> existing Xcode app; preserve its UI layer and package manager.
- `Package.swift`, no Xcode project -> ask whether it is an app package, a shared module, or support code.
- `Podfile` -> keep CocoaPods unless the user wants to migrate.
- `EMPTY_CWD` / no Xcode project -> **stop**: tell the user to create the iOS app in Xcode first. Do not scaffold from the CLI.

State a one-line status (e.g. `SwiftUI app detected - MyApp.xcodeproj - ready for Stream wiring`).

---

## 2. Credentials (ask once, then act)

Collect the API key, a user token, and (Chat only) optional seed channels in **one** message, then execute without pausing between steps.

**Chat:**
> To wire this with real data I need: (1) should I fetch your API key and generate a token via the Stream CLI, or will you paste them? (2) token expiry (`1h`, `1d`, never)? (3) seed a few channels so the app shows data on first launch?

**Feeds:** same as Chat but replace seed channels with feed groups (defaults `user`, `timeline`, `notification`).

**Video:** API key + token only (calls are ephemeral - nothing to seed).

If the user says they will paste credentials, take them and skip the CLI steps below.

### CLI steps (run in sequence, narrate one line each)

```bash
# API key -> Secrets.xcconfig (read via Info.plist / Bundle.main); the secret is never printed
getstream env --target ios

# Token (never-expiring, or add --ttl <duration>)
getstream token <user_id>
getstream token <user_id> --ttl <duration>

# Seed channels (Chat only, if requested): create the users first, then each channel
getstream api UpdateUsers --request '{"users":{"<token_user_id>":{"id":"<token_user_id>","name":"Token User"},"alice":{"id":"alice","name":"Alice"}}}'
getstream api GetOrCreateChannel --type messaging --id <channel-id> --request '{"data":{"created_by_id":"<token_user_id>","members":[{"user_id":"<token_user_id>"},{"user_id":"alice"}]}}'
```

Pick `--type` to match the vertical, not always `messaging`: `messaging` for social / marketplace / DMs, `team` for workplace, `livestream` for livestream / live-shopping (its permissions allow public + anonymous access). See [`RULES.md`](RULES.md) "Permissions". Use short channel ids (`general`, `random`) and a small set of usernames (`alice`, `bob`, `carol`). Make the token user a member of at least one channel so it shows on first launch. Print a one-line summary of what was created.

Never put the API **secret** in app code - the CLI uses it server-side only. Never fabricate credentials. If a CLI step fails, explain briefly and ask the user to paste the missing value.

---

## 3. Install the SDKs

Use the project's existing package workflow; install only what the requested products need:

- **Xcode app, no `Package.swift`** -> guide the user through File -> Add Package Dependencies. For exact package names/URLs, fetch the installation doc from [`docs-map.md`](docs-map.md) (Chat: `basics/integration.md`; Video: `basics/installation.md`; Feeds: `installation.md`).
- **Swift package-managed** -> edit `Package.swift` directly.
- **CocoaPods** -> keep Pods unless the user asks to migrate.

---

## 4. Wire the client

Initialize the client once at an owned lifecycle entry point (`App` init, `AppDelegate`, or a service object) and connect the user. Reference credentials via named constants (`Config.apiKey`, `Config.userToken`), never inline.

The exact init + connect code lives in the docs - fetch the relevant page from [`docs-map.md`](docs-map.md) ("Getting started" / "Quickstart" / "Client and authentication") and apply it. Honor the lifecycle and combined-SDK pitfalls in [`RULES.md`](RULES.md). If channels were seeded, the app should render them on first launch with no hardcoded ids.

---

## 5. Verify before stopping

- the right package is on the right target and resolves
- the client is initialized before any Stream view renders
- the requested user connects without leaking the secret
- the feature renders inside the existing navigation structure
- switching users / logout tears down the previous session cleanly

Then return to **Docs lookup** in [`SKILL.md`](SKILL.md) for each requested screen.
