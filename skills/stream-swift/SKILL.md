---
name: stream-swift
description: "Build and integrate Stream Chat, Video, and Feeds in Swift apps. Use for SwiftUI, UIKit, Xcode, and iOS project work with Stream package setup, auth wiring, and view blueprints."
license: See LICENSE in repository root
compatibility: Requires an Xcode or Swift/iOS project. No Stream CLI required.
metadata:
  author: GetStream
allowed-tools: >-
  Read, Write, Edit, Glob, Grep,
  Bash(ls *),
  Bash(grep *),
  Bash(find . *),
  Bash(cat Package.swift), Bash(cat Package.resolved), Bash(cat Podfile)
---

# Stream Swift - skill router + execution flow

**Rules:** Read **[`RULES.md`](RULES.md)** once per session - every non-negotiable rule is stated there, nowhere else.

This file is the **single entrypoint**: intent classification, local project detection, and module pointers for Stream work in Swift apps.

---

## Step 0: Intent classifier (mandatory first - never skip)

Before any tool call, decide the **track** from the user's input alone - no probes first.

### Signals -> track

| Signal in user input | Track |
|---|---|
| Explicit product/framework token: `Chat SwiftUI`, `Chat UIKit`, `Video iOS`, `Feeds Swift`, etc. | **C - Reference lookup** |
| Words "docs" or "documentation" around Stream Swift/iOS work | **C - Reference lookup** |
| "How do I {X} in SwiftUI/UIKit/Xcode?", "What does {SDK type/method/view} do?" | **C - Reference lookup** |
| "Build me a new iOS app", "create a SwiftUI app", "new UIKit app" + Stream product | **A - New app** |
| "Add/integrate Stream into this app", "wire Chat/Video/Feeds into my Xcode project" | **B - Existing app** |
| "Install Stream packages", "set up Stream in Xcode", "wire auth/token flow" with no broader feature request | **D - Bootstrap / setup** |
| Bare `/stream-swift` with no args | List the tracks briefly and wait |

### Disambiguation flow

If the request is ambiguous between **build/integrate** and **reference lookup**, ask one short question and wait:

> Do you want me to wire this into the project, or just map the Swift SDK pattern and files?

### After classification

- **Tracks A, B, D** -> run **Project signals** once per session, then continue in [`builder.md`](builder.md) and [`sdk.md`](sdk.md).
- **Track C** -> skip the probe if the product + framework are explicit. Only run it on demand if the SDK or UI layer is ambiguous.

---

## Project signals (tracks A/B/D - once per session; Track C on demand only)

Read-only local probe. Use it to detect whether the user is in an Xcode project, a Swift package, or an empty directory.

```bash
bash -c 'echo "=== XCODE ==="; find . -maxdepth 3 \( -name "*.xcodeproj" -o -name "*.xcworkspace" \) -print 2>/dev/null; echo "=== MANIFESTS ==="; find . -maxdepth 3 \( -name "Package.swift" -o -name "Package.resolved" -o -name "Podfile" \) -print 2>/dev/null; echo "=== EMPTY ==="; test -z "$(ls -A 2>/dev/null)" && echo "EMPTY_CWD" || echo "NON_EMPTY"'
```

Hold the result in conversation context. Don't re-run it unless the user changes directory or the project shape clearly changed.

Use the result to produce a **one-line status**, for example:

- `SwiftUI app detected - MyApp.xcodeproj - ready for Stream wiring`
- `UIKit workspace detected - Podfile present - preserve existing package manager`
- `No Xcode project found - user needs to create the app in Xcode first`

---

## Module map

| Track | Module(s) |
|---|---|
| A - New app | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + relevant reference files |
| B - Existing app | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) + relevant reference files |
| C - Reference lookup | [`sdk.md`](sdk.md) + relevant reference files |
| D - Bootstrap / setup | [`builder.md`](builder.md) + [`sdk.md`](sdk.md) |

---

## Reference layout

Shared Swift/iOS patterns live in **[`sdk.md`](sdk.md)**.

Product and framework specifics live under **`references/`** using a flat naming scheme that can grow with the full Stream Swift surface:

- **Reference:** `references/<PRODUCT>-<FRAMEWORK>.md`
- **Blueprints:** `references/<PRODUCT>-<FRAMEWORK>-blueprints.md`

Current extracted module:

- **Chat + SwiftUI:** [`references/CHAT-SWIFTUI.md`](references/CHAT-SWIFTUI.md) + [`references/CHAT-SWIFTUI-blueprints.md`](references/CHAT-SWIFTUI-blueprints.md)

Future Swift product coverage should stay in this naming family instead of creating more top-level skills:

- `CHAT-UIKIT.md`
- `VIDEO-SWIFTUI.md`
- `VIDEO-UIKIT.md`
- `FEEDS-SWIFTUI.md`
- `FEEDS-UIKIT.md`

If the requested product/framework file is not bundled yet, say so plainly, use `sdk.md` for the shared iOS patterns, and only switch to live docs if the user asks.

---

## Track A - New app

**Full detail:** [`builder.md`](builder.md) - use the **new-project path**.

| Phase | Name | What you do |
|---|---|---|
| **A1** | Detect | Run **Project signals**. If there is no iOS app yet, tell the user to create one in Xcode first. |
| **A2** | Choose lane | Confirm product(s) and UI layer: SwiftUI, UIKit, or mixed. |
| **A3** | Install + wire | Follow [`builder.md`](builder.md) + [`sdk.md`](sdk.md), then load only the needed product references. |
| **A4** | Verify | Confirm package resolution, client lifetime, auth, and first rendered screen. |

---

## Track B - Existing app

**Full detail:** [`builder.md`](builder.md) - use the **existing-project path**.

| Phase | Name | What you do |
|---|---|---|
| **B1** | Detect | Run **Project signals** and inspect the existing app structure before editing. |
| **B2** | Preserve | Keep the current UI layer, package manager, and navigation architecture unless the user asks for a migration. |
| **B3** | Integrate | Use [`sdk.md`](sdk.md) for shared wiring, then load only the needed product reference files. |
| **B4** | Verify | Confirm the requested Stream flow builds and renders inside the existing app. |

---

## Track C - Reference lookup

Load only the relevant files for the requested product and UI layer.

- Shared lifecycle / auth / state patterns -> [`sdk.md`](sdk.md)
- Chat SwiftUI setup and gotchas -> [`references/CHAT-SWIFTUI.md`](references/CHAT-SWIFTUI.md)
- Chat SwiftUI view structure -> [`references/CHAT-SWIFTUI-blueprints.md`](references/CHAT-SWIFTUI-blueprints.md)

If the user asks for an exact Video, Feeds, or UIKit module that is not bundled yet, say that clearly instead of inventing API details.

---

## Track D - Bootstrap / setup

Use when the user wants the install and wiring path more than a feature build:

- detect the project shape
- choose SwiftUI vs UIKit ownership
- install Stream packages with the project's existing package strategy
- wire auth and client lifetime via [`sdk.md`](sdk.md)
- stop before product-specific UI if the user only asked for setup
