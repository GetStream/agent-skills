# Stream Swift - non-negotiable rules

Every rule below is stated once. Other files reference this file - do not duplicate these rules inline.

---

## Secrets and auth

Never hardcode a Stream API secret in app code, `Info.plist`, or chat. The client may hold the **API key** and a **user token**; the **API secret** stays server-side only.

Default token model:

- Use a backend-issued token when the user already has a backend.
- Use a CLI-generated token (`stream token <user_id>` or `stream token <user_id> --ttl <duration>`) for local dev and demo flows - this is the preferred path when no backend exists.
- Use a static token only when the user explicitly wants to paste one themselves.
- Never invent or generate fake production credentials.
- The API secret never leaves the CLI/server side; only the API key and the generated token go into app code.

---

## Project ownership

Preserve the app's existing architecture:

- Do **not** convert UIKit to SwiftUI unless the user asks.
- Do **not** replace CocoaPods with SPM unless the user asks.
- Do **not** flatten an existing coordinator, DI, or navigation setup just to fit a sample.

If there is **no iOS project**, do not try to scaffold one from the CLI. Tell the user to create the app in Xcode first, then continue.

---

## Client lifetime

Initialize Stream SDK clients once at app launch or in an owned service object. Never create a client in:

- a SwiftUI `View` body
- a computed property that re-runs on redraw
- a transient callback with no stored owner

Stateful controllers, view models, and SDK helper objects must be stored as owned state (`@State`, `@StateObject`, `ObservableObject`, or stored properties), not recreated from computed vars.

If the user switches accounts, disconnect/logout the current user before connecting the next one.

---

## UI and concurrency

UI state changes belong on the main actor. Prefer explicit ownership over implicit globals:

- update SwiftUI state from the main actor
- keep UIKit controller ownership obvious
- avoid singleton-style shortcuts unless the SDK explicitly requires them

When adapting examples, match the project's actual lifecycle (`App`, `AppDelegate`, `SceneDelegate`, coordinator, tab shell) instead of forcing a different one.

---

## Reference discipline

Load only the product/framework reference files that match the request.

- `CHAT-SWIFTUI.md` for Chat + SwiftUI
- `CHAT-SWIFTUI-blueprints.md` for concrete SwiftUI view structure

Do not invent missing Video, Feeds, or UIKit API details. If a requested reference is not bundled yet, say so plainly and fall back to shared guidance from [`sdk.md`](sdk.md) or live docs only when the user wants that.
