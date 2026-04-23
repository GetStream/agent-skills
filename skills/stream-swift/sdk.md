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

- **Backend exists:** prefer a backend-issued Stream token
- **No backend / demo flow:** use a static token only if the user explicitly wants that simpler path

Keep the split clear:

- **client:** API key, user id, user token
- **server:** API secret and token minting

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

## Verification checklist

Before calling the work done, confirm:

- the right package is added to the right target
- the client is initialized before product views render
- the requested user can connect without leaking the API secret
- the edited flow works within the existing navigation structure
- user switching or logout tears down the previous session cleanly
