# Verifying on the iOS simulator — the fast loop

Running a Stream RN app on the iOS simulator to screenshot and verify it is the most **expensive**
part of a build (a native build is minutes, not seconds). Most of the wasted time comes from a
handful of avoidable mistakes: a second native rebuild, a stale Metro bundle, and fighting the
simulator's lack of touch input. This page is the playbook that avoids them.

Two lanes, and they behave **differently** at launch/reload — pick yours and read its column:

- **Expo dev-client / native-build** (`npx expo prebuild` + `expo run:ios`, Metro via `expo start`).
- **React Native Community CLI** (`pod install` + `npx react-native run-ios`, Metro via
  `react-native start`). No expo-dev-launcher, so several Expo-only steps below **do not apply**.

The lane differences are called out inline and summarized in **§8**.

---

## 1. The run loop (boot → build once → launch to Metro → screenshot)

```bash
# Pick a booted device (or boot one). Grab its UDID.
xcrun simctl list devices
xcrun simctl boot <udid>; open -a Simulator
```

**Pin that one UDID for the whole verification loop.** Once you've booted a device, reuse its UDID
in every `simctl`/`run:ios` call for the task instead of re-picking or re-booting mid-loop —
juggling multiple booted simulators is how a screenshot ends up on the wrong device or a stale build.

**Verifying the attachment picker — pre-seed photos + pre-grant BEFORE first launch.** The picker's
gallery tab requests photo-library access, and that alert is SpringBoard-owned: you can't tap
Allow/Don't Allow, and it survives `terminate`/`launch`, so it covers every later screenshot until you
reboot. Get ahead of it — add photos to the library and grant access **before** you launch the app,
so the gallery has content and (usually) no blocking prompt fires:

```bash
# 1) Put images in the simulator's photo library (any local files — reuse the reference PNGs).
xcrun simctl addmedia <udid> /path/to/a.png /path/to/b.png /path/to/c.png
# 2) Grant photo access to the app's bundle id (do this while the app is NOT running, then cold-launch).
xcrun simctl privacy <udid> grant photos <bundleId>
```

Then drive the picker open in code (`reactToIndex` forces the `images` tab on open, so the gallery
grid shows the seeded photos):

```tsx
useAttachmentPickerContext().attachmentPickerStore.setSelectedPicker('images'); // or 'files'
useMessageInputContext().openAttachmentPicker();
```

**iOS 26 caveat (verified):** `simctl privacy grant photos` reliably **suppresses the un-dismissable
SpringBoard prompt**, but it does **not** always satisfy `expo-media-library`'s own permission check —
the Stream picker may still render its in-app *"You have not granted access to the photo library —
Change in Settings"* panel (not a blocking alert) even after a grant **and** a reboot. When the
gallery won't populate on the sim, fall back to the **Files** tab (`setSelectedPicker('files')` — it
never touches the photo library, so no prompt and no not-granted panel), and verify the real photo
grid on a physical device.

**Layout is verifiable in ANY picker state — don't wait on a populated grid.** The composer↔picker
relationship (e.g. the `topInset` gap covered in
[design-matching.md](design-matching.md#composer---attachment-picker)) renders identically whether the
sheet shows a photo grid, the Files list, or the "not granted" panel — the sheet always fills its
reserved height. So you can confirm there's no gap between the composer and the picker without ever
populating the grid; conversely, **an empty or not-granted grid is not a layout bug** — don't chase
it as one, and don't let it mask a real gap (verify spacing against the composer, not the grid
contents).

If a blocking prompt did fire from an earlier run (e.g. you launched before granting), reboot to clear
it: `xcrun simctl shutdown <udid> && xcrun simctl boot <udid>`.

### Expo dev-client lane

```bash
# 1) Start Metro SEPARATELY, in the background, NOT in CI mode
npx expo start --dev-client --clear     # leave this running in the background

# 2) Build + install the dev-client ONCE (the expensive native build).
#    The BUILD + INSTALL is what you need here. expo run:ios also tries to *launch* the app at the
#    end, and that launch step commonly fails with:
#        Error: osascript -e tell app "System Events" to count processes … exited with non-zero code: 1
#    That is a macOS Automation-permission error on the Simulator-window activation, NOT a build
#    failure — the .app is already built and installed. Ignore it and launch yourself in step 4.
npx expo run:ios --device <udid>

# 3) Dismiss the dev-client onboarding sheet (takes effect now that the app is installed).
xcrun simctl spawn <udid> defaults write <bundleId> EXDevMenuIsOnboardingFinished -bool YES

# 4) Launch (and RELAUNCH on every later iteration) straight onto the Metro bundle — tap-free.
#    `--initialUrl` tells expo-dev-client which JS bundle to load, so it skips the dev-launcher
#    menu AND never shows the "Open in <app>?" confirmation. This is the ONE reliable tap-free
#    launch. Use the http:// Metro URL (localhost:8081 for a simulator) — NOT the exp+<scheme>:// form.
xcrun simctl launch <udid> <bundleId> --initialUrl "http://localhost:8081"

# 5) Screenshot whatever is on screen.
xcrun simctl io <udid> screenshot out.png
```

**Why `--initialUrl` and nothing else (Expo):** on a dev-client the app must load a JS bundle from Metro.

- A **bare** `xcrun simctl launch <bundleId>` (no `--initialUrl`) opens the **expo-dev-launcher menu**
  ("Development Servers" list). Selecting the server needs a **tap** you can't perform — you're stuck
  on the dev menu.
- `xcrun simctl openurl <udid> "<scheme>://…"` triggers an iOS **"Open in <app>?"** confirmation that
  itself needs a tap — **never use it** (see §3).
- `--initialUrl "http://localhost:8081"` loads the bundle directly: no menu, no modal. Passing the
  full `exp+<scheme>://…` deep link to `--initialUrl` re-triggers the "Open?" modal — plain `http://` only.

The floating dev-menu **gear** icon still overlays the app (dev-only) — ignore it (see §7).

### React Native CLI lane

The CLI has **no dev-launcher**, so steps 3 and 4 above **do not apply** — no onboarding sheet, no
`--initialUrl`, no launcher menu, no "Open?" modal. `react-native run-ios` builds, installs **and
launches** the app itself, and it launches cleanly (no osascript error). The debug binary has the
`localhost:8081` bundle URL baked in, so it auto-connects to Metro on any launch.

```bash
# 1) Start Metro SEPARATELY, in the background
npx react-native start &                 # leave running (see §2 for the watchman caveat)

# 2) Build + install + launch ONCE (the expensive native build). This also launches cleanly.
npx react-native run-ios --udid <udid>

# 3) FAST relaunch on every later iteration — bare launch, NO --initialUrl. Auto-connects to Metro.
xcrun simctl launch <udid> <bundleId>

# 4) Screenshot.
xcrun simctl io <udid> screenshot out.png
```

The CLI's dev overlay is a **LogBox "Open debugger to view warnings" toast** (bottom of screen), not a
gear — also dev-only, ignore it (see §7).

---

## 2. Force a clean relaunch after code changes (avoid a stale bundle)

Fast Refresh usually applies edits in place, but when you **remove** a component or import — e.g.
deleting the temp navigation scaffold from §3 — the in-memory bundle can keep referencing the gone
code and the app crashes on next interaction. Don't debug that as a real bug; it's a stale bundle.

**Expo lane:** relaunch the app to force a fresh bundle fetch from Metro:

```bash
xcrun simctl launch <udid> <bundleId> --initialUrl "http://localhost:8081"
```

Each expo-dev-client launch re-downloads the bundle, so a relaunch can never carry a stale in-memory
bundle. You do **not** need another `npx expo run:ios` — the native binary hasn't changed, only JS.

**RN CLI lane — the watchman caveat (important):** if **`watchman` is not installed**, Metro does
**not** detect file edits, so **no** reload path surfaces your change — not Fast Refresh, not the
packager `GET /reload`, not even a cold `simctl launch` (the CLI app reuses its on-disk cached
bundle). Symptom: you edit a file, relaunch, and the screen is unchanged. The fix is one of:

```bash
# Best: install watchman once, then Fast Refresh + relaunch work normally.
brew install watchman

# Or, per-change without watchman: restart Metro with a cleared cache, THEN relaunch the app.
#   (kill the old Metro on 8081 first)
npx react-native start --reset-cache &
xcrun simctl launch <udid> <bundleId>
```

Confirm the served bundle actually contains your edit before trusting a screenshot:
`curl -s "http://localhost:8081/index.bundle?platform=ios&dev=true" | grep -c "<a marker from your edit>"`.

Metro's interactive `r` reload only exists when Metro runs in a **foreground** terminal; the
background Metro above has no TTY to receive it (true for both lanes).

---

## 3. Reaching non-initial screens without taps

`xcrun simctl` **cannot tap or scroll**, and GUI automation (AppleScript / System Events) is
unauthorized (this is also why the Expo first-launch dev-menu sheet needs the `defaults write`
workaround in §1, and why `expo run:ios`'s own launch step errors on osascript). To screenshot a
screen behind the first one, drive navigation from code with **temporary** scaffold, then remove it:

- **Auto-navigate to a channel — Expo Router:** a temp
  `useEffect(() => setTimeout(() => router.push(\`/channel/${encodeURIComponent(cid)}\`), 800), [])`
  in the index screen. **Encode the `cid`** — the `:` in `messaging:<id>` otherwise mis-parses the
  Expo Router path segment (`useLocalSearchParams` returns it decoded).
- **Auto-navigate to a channel — React Navigation (RN CLI):** navigate with a **params object**, so
  there is **no URL to encode**. Use the container ref so it fires once navigation is ready:
  ```tsx
  const navigationRef = createNavigationContainerRef();
  // <NavigationContainer ref={navigationRef} onReady={() =>
  //   setTimeout(() => navigationRef.navigate('Channel', { channelCid: cid }), 800)}>
  ```
  (An in-screen `useEffect(() => navigation.navigate('Channel', { channelCid: cid }), [])` also works;
  the `onReady` form is the most reliable.)
- **Exercise a state inside `<Channel>`** (composer typing, send button, attachment picker) with a
  temp child that calls the SDK hooks — this is its own required step, see **§4**.
- **A custom-scheme deep link is NOT a shortcut (Expo):** `simctl openurl <scheme>://…` triggers an
  iOS "Open in <app>?" confirmation that needs a tap. Worse, that alert is owned by SpringBoard: it
  **survives `simctl terminate`/`launch`** and overlays every later screenshot. If you fire it by
  accident, the only tap-free recovery is to **reboot the simulator**
  (`xcrun simctl shutdown <udid> && xcrun simctl boot <udid>`). Prefer the in-code temp nav above,
  and on Expo load the bundle with `--initialUrl "http://…"` (§1), never `openurl`.
- **Then DELETE all temp scaffold** (remove the branch/import, don't just disable it), re-typecheck,
  and **force a clean relaunch** (§2 — mind the RN CLI watchman caveat) — otherwise a stale bundle
  still referencing the removed temp component crashes the app.

For a region that's off-screen and awkward to reach, an alternative is to **seed** the state via the
Stream CLI (`getstream api SendMessage …`), screenshot, then hard-delete
(`getstream api DeleteMessage --request '{"hard":true}'`).

---

## 4. Drive composer & picker states

The composer is not one screenshot, it is **several states**, and the default (empty input) hides the
one people most often get wrong. `simctl` can't type, so drive each state from a temp child inside
`<Channel>` that calls SDK hooks, screenshot it, then delete the scaffold (§3 cleanup rules apply).

- **At rest (empty input):** - default state
- **Typing (input has text):** - Drive it in:
  ```tsx
  // temp child rendered inside <Channel>
  useMessageComposer().textComposer.setText('hello');   // → triggers the mic→send swap
  ```
  then screenshot and inspect the send button (shape, glyph, color, position).
- **Attachment picker open:** `useMessageInputContext().openAttachmentPicker()` (open to the Files
  tab, or pre-grant photos — see §1). Verify the composer↔picker spacing here too.

---

## 5. Wait for the client before you trust a screenshot

If the app gates its splash on the chat/video/feeds client resolving (e.g. splash hides only once
`chatClient` is ready), a screenshot taken too soon captures the launch/splash screen (Expo splash,
or the RN CLI launch screen / white screen), which looks like a hang. After any relaunch, **wait for
the client to reconnect** (poll Metro logs or just re-screenshot after a short delay) before
concluding anything is broken.

The same applies **within** a screen, not just at launch: after navigating or relaunching, give
images/avatars a moment to finish loading and any list entrance animation to settle before you take
the "real" screenshot for a design comparison — a shot fired immediately can catch a placeholder or
mid-transition frame and read as a mismatch that isn't one.

---

## 6. Verifying dark mode — flip the OS appearance, don't rebuild

If the design supports dark mode (or you applied the light/dark carve-out — pin brand/content colors,
keep structural surfaces semantic), verify **both** modes on the same build. Flip the OS appearance at
runtime and re-screenshot — no rebuild needed; a React Native app reading `useColorScheme()` re-renders
on the change:

```bash
# iOS simulator (pinned UDID from §1)
xcrun simctl ui <udid> appearance dark      # → light to switch back
xcrun simctl io <udid> screenshot dark.png

# Android emulator
adb shell "cmd uimode night yes"            # → no to switch back
adb exec-out screencap -p > dark.png
```

Then confirm the carve-out held: **structural surfaces** (message-list background, composer/input
background, borders) flipped to their dark values, while **pinned brand/content** colors (bubble
fills, glyphs, accent, read-receipt ticks) look identical to light mode. A surface that stayed light
is a pinned-to-literal bug; a brand color that washed out was pinned wrong. Sample both modes and diff
per the color-sampling method in [design-matching.md](design-matching.md).

---

## 7. Known environmental limits (don't fight these)

- **Component overrides won't show if wired wrong:** in `stream-chat-react-native` v9 a slot such as
  `MessageHeader` is applied through **`WithComponents overrides={{ MessageHeader: … }}`**, not by
  passing it as a `<Channel MessageHeader={…}>` prop (that prop is silently ignored — no error, no
  effect, which looks exactly like a stale bundle during verification). Same in both lanes. Also, the
  *default* `MessageHeader` renders nothing unless the message is pinned / saved-for-later / reminder
  / sent-to-channel, so verify an override with an explicit, visibly-distinct custom component.
- **iOS 26 Photo Library access:** opening the gallery grid without a prior grant fires a tap-only,
  SpringBoard-owned Photo Library prompt you can't dismiss. **Pre-grant + pre-seed before launch**
  (`simctl addmedia` + `simctl privacy grant photos <bundleId>`) to suppress that prompt — but note
  the grant may still not satisfy `expo-media-library`, so the picker can show its in-app "not
  granted" panel anyway. When the gallery won't populate on the sim, use the **Files** tab
  (`setSelectedPicker('files')`) to verify the selection bar/layout, and confirm the real grid on a
  device. Full procedure + the "layout is verifiable in any state" rule are in §1.
- The simulator has **no camera or microphone** — voice/video *capture* can only be verified on a
  real device (see the Video reference). The composer mic *button* still renders (with `expo-audio`
  installed); its recording just won't produce audio.
- **Physical-scale sizing reads correctly only on a device, not on the roomy sim window.** A
  keyboard-height–relative size — the attachment-picker sheet height (`attachmentPickerBottomSheetHeight`,
  should ≈ keyboard height), a safe-area gap, a bottom-bar height — can look fine on the large
  simulator window while being visibly oversized/undersized on a phone. Verify these against the thing
  they represent (the SDK default, a measured value), not by eye on the sim (a *green launch ≠ correct*
  case, [../RULES.md](../RULES.md)); when a size stands for the keyboard/safe area, confirm on a device.
- **Dev-only overlays — ignore them in screenshots:** the **Expo** dev-client overlays a small
  floating **gear / dev-menu launcher**; the **RN CLI** shows a **LogBox "Open debugger to view
  warnings" toast** at the bottom. Both are dev-only (gone in a release build) and not part of the
  app. Never treat either as an app element or a design mismatch to fix.

---

## 8. Expo vs RN CLI — quick reference

| Step | Expo dev-client | React Native CLI |
|---|---|---|
| Metro | `npx expo start --dev-client --clear` | `npx react-native start` (install `watchman` — see §2) |
| Build once | `npx expo run:ios --device <udid>` (its launch step errors on osascript — harmless) | `npx react-native run-ios --udid <udid>` (builds **and** launches cleanly) |
| Onboarding sheet | `defaults write <bundleId> EXDevMenuIsOnboardingFinished -bool YES` | n/a (no dev-launcher) |
| Launch / relaunch | `simctl launch <bundleId> --initialUrl "http://localhost:8081"` | `simctl launch <bundleId>` (bare — no `--initialUrl`) |
| Dev-launcher menu / "Open?" modal risk | Yes — avoid via `--initialUrl`, never `openurl` | None |
| Reload after edit | relaunch (re-fetches fresh) | Fast Refresh **iff** watchman installed; else `react-native start --reset-cache` + relaunch (§2) |
| Reach non-initial screen | Expo Router `router.push`, **encode the cid** | React Navigation `navigate('Channel', { channelCid })`, **no encoding** |
| Dev overlay to ignore | floating gear | LogBox "Open debugger" toast |
