# Stream Swift - shared SDK patterns

This file holds the shared iOS patterns that cut across Chat, Video, and Feeds. Load it before product-specific references when you need lifecycle, auth, or architecture guidance.

---

## App shapes

Match the project that already exists:

- **SwiftUI app:** ownership usually starts in `App`, an app-scoped model, or `AppDelegate`
- **UIKit app:** ownership usually starts in `AppDelegate`, `SceneDelegate`, a coordinator, or a composition root
- **Mixed app:** keep Stream setup at the shared boundary instead of duplicating it per screen

Do not rewrite the app into a different UI framework unless the user asks.

---

## Client ownership

Create the Stream client once, store it in an owned object, and pass or inject it from there.

Good ownership points:

- SwiftUI `App` initialization
- `AppDelegate` / `SceneDelegate`
- an app-scoped service or container
- a coordinator that already owns long-lived SDK clients

Bad ownership points:

- SwiftUI `body`
- computed properties that recreate the client
- leaf views that do not own app lifecycle

---

## Auth model

Use the simplest token shape that matches the user's environment:

- **Backend exists:** prefer a backend-issued Stream token.
- **No backend / demo flow:** generate a token with the Stream CLI (see Step 0.5 in `SKILL.md`). Never-expiring: `stream token <user_id>`. Expiring: `stream token <user_id> --ttl <duration>` (e.g. `1h`, `1d`, `30m`, `1800s`).
- **User pastes their own:** accept it and move on.

Keep the split clear:

- **client:** API key, user id, user token
- **server:** API secret and token minting (the CLI handles this automatically)

If the app already has its own auth system, extend that flow instead of adding a second login model beside it.

---

## State and view models

Stateful SDK helpers should have explicit ownership:

- SwiftUI: `@State`, `@StateObject`, or an injected observable owner
- UIKit: stored properties on the controller, coordinator, or service that owns the flow

Avoid computed-property factories for controllers, lists, or query objects that are supposed to stay stable across redraws.

---

## Main-actor boundaries

Keep UI updates on the main actor. When an SDK callback or async task returns data, hop back to the main actor before mutating SwiftUI or UIKit state.

Preserve the project's concurrency style. If the app already uses `async`/`await`, stay there. If it uses completion handlers, bridge carefully instead of rewriting unrelated code.

---

## Combined Chat + Video apps

When the app uses both SDKs, load [`references/COMBINED-CHAT-VIDEO.md`](references/COMBINED-CHAT-VIDEO.md). It covers:

- Type-name mapping (`UserInfo`/`User`, `Token`/`UserToken`, and the SwiftUI-layer collisions)
- Which collisions cause actual compiler errors (SwiftUI layer only) vs. conceptual confusion (UIKit)
- File isolation blueprints for SwiftUI and UIKit combined apps
- Shared API key and token details

---

## Verification checklist

Before calling the work done, confirm:

- the right package is added to the right target
- the client is initialized before product views render
- the requested user can connect without leaking the API secret
- the edited flow works within the existing navigation structure
- user switching or logout tears down the previous session cleanly
