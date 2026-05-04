# Stream Swift - build and integration flow

Use this module after intent classification and, when needed, the local **Project signals** probe from [`SKILL.md`](SKILL.md).

---

## 1. Detect the workspace

Start by understanding what kind of Swift project is in front of you:

- `*.xcodeproj` / `*.xcworkspace` -> existing Xcode app or workspace
- `Package.swift` with no Xcode project -> ask whether this is an app package, a shared module, or just support code
- `Podfile` -> preserve CocoaPods unless the user wants to migrate
- no Xcode project and `EMPTY_CWD` -> tell the user to create a new iOS app in Xcode first

Do **not** try to scaffold Xcode projects from the CLI.

---

## 2. Choose the integration lane

Resolve three things before editing:

1. **Product:** Chat, Video, Feeds, or a combination
2. **UI layer:** SwiftUI, UIKit, or mixed
3. **Scope:** app bootstrap, auth, a specific screen, or a full product shell

If the user only asked for setup, stop after the shared wiring in [`sdk.md`](sdk.md).

---

## 3. Install the SDKs

Prefer the project's existing package workflow:

- **Xcode app without `Package.swift`:** guide the user through **File -> Add Package Dependencies...**
- **Swift package-managed project:** edit `Package.swift` directly
- **CocoaPods app:** keep Pods if the project already uses them and the user does not want a migration

Install only the packages needed for the requested Stream products.

---

## 4. Wire the shared app setup

**Before writing any code**, confirm that Step 0.5 in [`SKILL.md`](SKILL.md) has completed - API key, token, and optional seed channels should already be in context. If not, run that step now before continuing.

Follow [`sdk.md`](sdk.md) for:

- client lifetime and app ownership
- auth and token transport - use the real API key and token from Step 0.5, never placeholder strings
- state management and main-actor boundaries
- disconnect/reconnect rules when changing users

If seed channels were created in Step 0.5, the app should render them on first launch without any extra setup - no additional sample data or hardcoded channel IDs needed in the code.

Keep the existing app shell intact. Add the minimum composition points needed for Stream.

---

## 5. Load only the needed reference files

Use the product + UI layer to choose the smallest relevant reference set.

Available extracted modules:

- Chat + SwiftUI: [`references/CHAT-SWIFTUI.md`](references/CHAT-SWIFTUI.md)
- Chat + SwiftUI view blueprints: [`references/CHAT-SWIFTUI-blueprints.md`](references/CHAT-SWIFTUI-blueprints.md)
- Chat + UIKit: [`references/CHAT-UIKIT.md`](references/CHAT-UIKIT.md)
- Chat + UIKit view controller blueprints: [`references/CHAT-UIKIT-blueprints.md`](references/CHAT-UIKIT-blueprints.md)
- Video + SwiftUI: [`references/VIDEO-SWIFTUI.md`](references/VIDEO-SWIFTUI.md)
- Video + SwiftUI view blueprints: [`references/VIDEO-SWIFTUI-blueprints.md`](references/VIDEO-SWIFTUI-blueprints.md)

Future modules should follow the same naming family:

- `VIDEO-UIKIT.md`
- `FEEDS-SWIFTUI.md`
- `FEEDS-UIKIT.md`

If the exact file is not present yet, say so directly instead of faking a reference.

---

## 6. Verify before you stop

Check the smallest set of outcomes that proves the integration works:

- package resolution succeeds
- the Stream client is initialized from an owned lifecycle entry point
- the app does not render Stream views before that client exists
- the requested login, channel, call, or feed surface appears where expected
- switching users does not leave multiple active sessions behind
