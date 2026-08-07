# Verifying on the iOS simulator — the fast loop

Running a Stream RN app on the iOS simulator to screenshot and verify it is the most **expensive** part
of a build (a native build is minutes, not seconds). Most of the wasted time comes from a handful of
avoidable mistakes: a second native rebuild, a stale Metro bundle, and fighting the simulator's lack of
touch input. This page is the playbook that avoids them.

Two lanes, and they behave **differently** at launch/reload — pick yours and read its column:

- **Expo dev-client / native-build** (`npx expo prebuild` + `expo run:ios`, Metro via `expo start`).
- **React Native Community CLI** (`pod install` + `npx react-native run-ios`, Metro via
  `react-native start`). No expo-dev-launcher, so several Expo-only steps below **do not apply**.

**A third lane exists for BASELINE captures only: Expo Go.** Stream apps never target Expo Go, but the
*pre-migration* app you are capturing a baseline from often does (Track S). It launches tap-free the same
way the dev client does — `xcrun simctl launch <udid> host.exp.Exponent --initialUrl
"http://127.0.0.1:<port>"`. Do **not** reach for `simctl openurl exp://…`: that fires an un-tappable
"Open in Expo Go?" alert that survives `terminate` and forces a reboot (§3). Expo Go may not be installed
on a fresh simulator — install it from `~/.expo/ios-simulator-app-cache/Expo-Go-*.tar.app`.

The lane differences are called out inline and summarized in **§8**.

---

## 1. The run loop — run `scripts/sim.sh`, don't hand-roll it

**`scripts/sim.sh capture` IS this loop.** One call boots or reuses the device, preps permissions,
starts Metro (and waits until it *serves*), terminates, launches onto the bundle, gates on the
bundle actually being served, polls until the frame settles, and writes the PNG:

```bash
# 0) PIN THE DEVICE CLASS to the reference's, BEFORE the build. A 402pt render cannot be
#    compared 1:1 to a 393pt reference, and compare_regions.py refuses the pair — one real
#    run discovered that after building and hand-measured everything instead.
python3 scripts/measure_region.py scale <reference.png>   # prints logical_width
bash scripts/sim.sh devices 393                           # simulators of that class

# 1) build once (the expensive native step) — gate.sh reports its REAL exit status
bash scripts/gate.sh "$P" npx expo run:ios --device "$(bash scripts/sim.sh boot --logical-width 393)"

# 2) then one call per screen STATE, repeatable — reuses the device and Metro
bash scripts/sim.sh capture <bundleId> chat-atrest-1.png --project "$P" --lane expo \
     --logical-width 393 [--port 8081]
```

Granular subcommands for the rare step you need alone:
`boot [name] · prep <udid> <bundleId> · metro expo|cli <dir> · shot <udid> <bundleId> <out> ·
appearance <udid> light|dark <out> · reboot <udid> · udid`.

It refuses to hand you a screenshot it cannot stand behind — **each of these was a green capture
of the wrong screen before it was a check**, so do not work around them:

- **No bundle line for this launch → hard failure**, file deleted. The app was not running your JS,
  and the launcher menu it falls back to is a stable non-splash frame the settle check would accept.
  (RN CLI on a cached launch may print none — then pass `--no-bundle-gate`.)
- **Metro must answer `/status`, not merely hold the port.** It binds seconds before it can serve;
  launching into that gap is what produced the launcher-menu capture above, at exit 0.
- **`--device <name>` matches the name exactly** before falling back to substring (`iPhone 17` must
  not resolve to `iPhone 17 Pro`) and lists candidates when ambiguous. Pin one device for the loop —
  juggling booted simulators is how a screenshot lands on the wrong device or a stale build.
- **It will not pick between two booted simulators.** With more than one booted and no `--device` /
  `--logical-width`, it stops and lists them. A real run shot whichever happened to be first and had
  to report afterwards that landing on the right device "was luck". `--logical-width` additionally
  **verifies the captured PNG's width**, so a wrong guess about a device's class is caught here rather
  than at comparison time.
- **Output filenames are never reused** (`<screen>-<state>-<attempt>.png`). A retry that overwrites
  its predecessor can be unrecoverable: a real run lost the only baseline holding reaction pills and
  recovering it cost a `git worktree` rebuild on a second Metro.
- **It never kills a dev server it did not start** — two real runs silently killed a sibling
  project's. Metro is redirected to a log, never piped (a closing pipe kills it).

§3–§4 are the states `capture` cannot reach on its own.

### Photo-library permission — REVOKE it before first launch; do NOT grant it

The picker's gallery tab requests photo-library access, and that alert is SpringBoard-owned: you can't tap
Allow/Don't Allow, and it survives `terminate`/`launch`, so it covers every later screenshot until you
reboot. **`simctl privacy grant photos` does not reliably suppress it on iOS 26** — two real runs granted
(one also pre-seeded the library and rebooted) and the prompt fired anyway, costing 5 reboots between
them. **Revoke instead:** a *denied* permission makes the SDK render its in-app *"You have not granted
access to the photo library — Change in Settings"* panel, an ordinary view with nothing to tap.

**`sim.sh` does this for you** — `capture` calls `prep` on first use per device+bundle, which revokes
photos, grants the mic, and dismisses the dev-menu onboarding sheet, then records a marker so later
captures skip it. It deliberately does **not** mark an app that is not installed yet, so the prep
still happens after the native build rather than being silently skipped forever.

```bash
bash scripts/sim.sh prep <udid> <bundleId>          # only if you are driving steps by hand
```

Then drive the picker open in code. **Order matters:** the SDK's `reactToIndex` forces
`selectedPicker='images'` when the sheet settles at index 0, so a tab selected *before* the open call is
discarded — switch **after** the sheet settles (both real runs hit this):

```tsx
useMessageInputContext().openAttachmentPicker();
// AFTER the sheet settles, not before — a pre-set picker is overwritten by reactToIndex.
setTimeout(() => attachmentPickerStore.setSelectedPicker('files'), 1200);
```

The **Files** tab never touches the photo library, so it's the tab to verify the selection bar and layout
on. Confirm the real populated photo grid on a physical device.

**Layout is verifiable in ANY picker state — don't wait on a populated grid.** The composer↔picker
relationship (e.g. the `topInset` gap in [regions-chat.md](regions-chat.md) > Composer - attachment
picker) renders identically whether the sheet shows a photo grid, the Files list, or the "not granted"
panel — the sheet always fills its reserved height. So confirm there's no gap without ever populating the
grid; conversely **an empty or not-granted grid is not a layout bug** — don't chase it as one, and don't
let it mask a real gap (verify spacing against the composer, not the grid contents).

If a blocking prompt did fire from an earlier run, a reboot is the only tap-free recovery:
`bash scripts/sim.sh reboot <udid>`.

### Both lanes — one command, `--lane` is the only difference

```bash
# Build + install ONCE (the expensive native step). gate.sh reports the REAL exit status and
# recognises the osascript case below.
bash scripts/gate.sh "$P" npx expo run:ios --device <udid>       # expo
bash scripts/gate.sh "$P" npx react-native run-ios --udid <udid> # rn cli

# Then every capture, repeatable:
bash scripts/sim.sh capture <bundleId> <screen>-<state>-1.png --project "$P" --lane expo
bash scripts/sim.sh capture <bundleId> <screen>-<state>-1.png --project "$P" --lane cli
```

**`expo run:ios` commonly exits non-zero AFTER a successful build** with
`Error: osascript -e tell app "System Events" to count processes … exited with non-zero code: 1`.
That is a macOS Automation-permission error on the Simulator-window activation, **not** a build
failure — the `.app` is built and installed. `gate.sh` detects exactly this (Build Succeeded +
osascript in the log) and says so, so it is not read as a broken build. Then capture normally.

**Why `--initialUrl` and nothing else (Expo):** on a dev client the app must load a JS bundle from Metro.
A **bare** `simctl launch` (no `--initialUrl`) opens the **expo-dev-launcher menu** ("Development Servers"
list), and selecting the server needs a **tap** you can't perform. `simctl openurl <udid>
"<scheme>://…"` triggers an iOS **"Open in <app>?"** confirmation that also needs a tap — **never use it**
(§3). `--initialUrl "http://localhost:<port>"` loads the bundle directly: no menu, no modal. It is a
plain process argument the dev launcher parses itself (`initialUrlFromProcessInfo`), so use the
**http:// Metro URL**; passing the full `exp+<scheme>://…` deep link re-triggers the "Open?" modal.
`sim.sh --lane expo` passes it for you and matches it to `--port`.

**React Native CLI lane:** no dev-launcher, so no onboarding sheet, no `--initialUrl`, no launcher menu,
no "Open?" modal, and `run-ios` launches cleanly by itself (no osascript error). The debug binary has the
`localhost:8081` bundle URL baked in and auto-connects on any launch — `--lane cli` issues the bare
launch. See §2 for the watchman caveat, which is CLI-only.

---

## 2. Force a clean relaunch after code changes (avoid a stale bundle)

Fast Refresh usually applies edits in place, but when you **remove** a component or import — e.g. deleting
the temp navigation scaffold from §3 — the in-memory bundle can keep referencing the gone code and the app
crashes on next interaction. Don't debug that as a real bug; it's a stale bundle.

**`simctl launch` against an already-running app returns the existing PID and does NOT restart it** — the
"relaunch" is a no-op, you screenshot the old UI, and read it as a failed fix (a real run did exactly
that). **Always `terminate` first, then launch** (per-lane commands in §1). The Expo dev client can also
hold a stale module-resolution error after the file is fixed, which only a genuine terminate+launch
clears. You do **not** need another `npx expo run:ios` — the native binary hasn't changed, only JS.

**RN CLI lane — the watchman caveat:** if **`watchman` is not installed**, Metro does **not** detect file
edits, so **no** reload path surfaces your change — not Fast Refresh, not the packager `GET /reload`, not
even a cold `simctl launch` (the CLI app reuses its on-disk cached bundle). Symptom: you edit a file,
relaunch, and the screen is unchanged. Fix:

```bash
# Best: install watchman once, then Fast Refresh + relaunch work normally.
brew install watchman

# Or, per-change without watchman: restart Metro with a cleared cache, THEN relaunch the app.
#   (kill the old Metro on 8081 first)
npx react-native start --reset-cache > /tmp/metro-<proj>.log 2>&1 &
xcrun simctl terminate <udid> <bundleId>          # launch alone no-ops on a running app
xcrun simctl launch <udid> <bundleId>
```

Confirm the served bundle actually contains your edit before trusting a screenshot:
`curl -s "http://localhost:8081/index.bundle?platform=ios&dev=true" | grep -c "<a marker from your edit>"`.

Metro's interactive `r` reload only exists when Metro runs in a **foreground** terminal; the background
Metro above has no TTY to receive it (both lanes).

### Two "looks-like-a-crash" issues that are really Metro/port problems

- **`EXPO_PUBLIC_*` env vars are inlined at Metro BUNDLE time, not runtime.** After writing `.env` (e.g.
  the API key + a token), the running bundle keeps the OLD/empty values until you **restart Metro with
  `--clear`**. Symptom: the app shows its "credentials missing" gate even though `.env` is correct.
  Confirm the value reached the served bundle: `curl -s
  "http://localhost:<port>/node_modules/expo-router/entry.bundle?platform=ios&dev=true" | grep -c
  "<value-prefix>"`.
- **Wrong-Metro → `PlatformConstants could not be found`
  (`TurboModuleRegistry.getEnforcing('PlatformConstants')`).** Reads like a native/build failure but is a
  **JS-bundle ↔ native mismatch from loading the wrong Metro** — e.g. another dev server is already on
  `8081`, so the freshly built app loads *that* project's bundle. Fix: run your Metro on a **free port**
  (`--port 8082`) and **cold-launch** onto it (`xcrun simctl launch <udid> <bundle> --initialUrl
  "http://localhost:8082"`); a relaunch over a running app keeps the stale server, so terminate first.
  **Don't kill the user's other server** — just use a different port. **If the user PINNED the occupied
  port**, that's a conflict only they can resolve: report what's holding it (`lsof -nP -iTCP:<port>
  -sTCP:LISTEN`, and which project it belongs to) and either ask, or proceed on a free port and say so.
  Two real runs silently killed a sibling project's dev server to honour a pinned port and had to disclose
  it afterwards.

---

## 3. Reaching non-initial screens without taps

`xcrun simctl` **cannot tap or scroll**, and GUI automation (AppleScript / System Events) is unauthorized
(hence the `defaults write` workaround for the Expo dev-menu sheet in §1, and `expo run:ios`'s own
osascript error). To screenshot a screen behind the first one, drive navigation from code with
**temporary** scaffold, then remove it:

- **Auto-navigate to a channel — Expo Router:** a temp
  `useEffect(() => setTimeout(() => router.push(\`/channel/${encodeURIComponent(cid)}\`), 800), [])`
  in the index screen. **Encode the `cid`** — the `:` in `messaging:<id>` otherwise mis-parses the Expo
  Router path segment (`useLocalSearchParams` returns it decoded).
- **Auto-navigate to a channel — React Navigation (RN CLI):** navigate with a **params object**, so there
  is **no URL to encode**. Use the container ref so it fires once navigation is ready:
  ```tsx
  const navigationRef = createNavigationContainerRef();
  // <NavigationContainer ref={navigationRef} onReady={() =>
  //   setTimeout(() => navigationRef.navigate('Channel', { channelCid: cid }), 800)}>
  ```
  (An in-screen `useEffect(() => navigation.navigate('Channel', { channelCid: cid }), [])` also works; the
  `onReady` form is the most reliable.)
- **Exercise a state inside `<Channel>`** (composer typing, send button, attachment picker) with a temp
  child that calls the SDK hooks — its own required step, see **§4**.
- **A custom-scheme deep link is NOT a shortcut (Expo):** `simctl openurl <scheme>://…` triggers an iOS
  "Open in <app>?" confirmation that needs a tap, and that alert is owned by SpringBoard: it **survives
  `simctl terminate`/`launch`** and overlays every later screenshot. The only tap-free recovery is to
  **reboot the simulator** (`xcrun simctl shutdown <udid> && xcrun simctl boot <udid>`). Prefer the in-code
  temp nav above, and load the bundle with `--initialUrl "http://…"` (§1), never `openurl`. **`expo
  run:ios` fires `openurl` itself** during its launch step, so the alert can appear even though *you*
  never ran it — if a run:ios leaves a modal on screen, reboot and relaunch with `--initialUrl` rather than
  hunting for what you did wrong.
- **Then DELETE all temp scaffold** (remove the branch/import, don't just disable it), re-typecheck, and
  **force a clean relaunch** (§2 — mind the watchman caveat) — otherwise a stale bundle still referencing
  the removed component crashes the app.

For a region that's off-screen and awkward to reach, an alternative is to **seed** the state via the Stream
CLI (`getstream api SendMessage …`), screenshot, then hard-delete
(`getstream api DeleteMessage --request '{"hard":true}'`).

---

## 4. Drive composer & picker states

**Capture at-rest, typing and picker-open on every run; drive any other state only when a reference
screenshot shows it**
([design-matching.md](design-matching.md#42-screenshot-every-screen-then-check-it) > composer gate).
`simctl` can't type, so drive a state from a temp child inside `<Channel>` that calls SDK hooks,
screenshot it, then delete the scaffold (§3 cleanup rules apply).

**Mandatory — every run:**

- **At rest (empty input):** default state.
- **Typing (input has text):**
  ```tsx
  // temp child rendered inside <Channel>
  useMessageComposer().textComposer.setText('hello');   // → triggers the mic→send swap
  ```
  then screenshot and inspect the send button (shape, glyph, color, position).
- **Attachment picker open:** `useMessageInputContext().openAttachmentPicker()` (open to the Files tab —
  see the open-then-switch order in §1). Verify the composer↔picker spacing here too.

**Only when a reference screenshot shows the state** (driving these speculatively has not caught a defect;
what they'd find — an unset `audioRecordingEnabled`, an off-screen composer — shows at rest):

- **Keyboard UP (a SEPARATE state — `setText` does NOT raise the keyboard).** `setText` fills the input but
  never opens the software keyboard, so it does **not** exercise keyboard-avoidance
  (`keyboardVerticalOffset` / `topInset` on `<Channel>`). **Focus the input** so the real keyboard rises
  (via the input ref in context, or a temp `autoFocus`). On the simulator the software keyboard is
  **hidden while a hardware keyboard is connected** — turn that off (Simulator ▸ I/O ▸ Keyboard ▸ *Connect
  Hardware Keyboard*, or ⌘K) or the keyboard won't appear and you'll wrongly conclude it's fine. Then
  confirm the composer sits above the keyboard with no gap/overlap.
- **Voice-recording in progress:** start a recording via the SDK's audio-recording context/controller
  (confirm the hook in the installed package). The sim has no mic so no audio is captured, but the
  **in-progress recorder UI still renders** — screenshot it and sample its tint (waveform / mic / timer):
  it draws from `accentPrimary` / `chatWaveformBar`, a common place a stray SDK-default colour survives a
  theme pass. **`xcrun simctl privacy <udid> grant microphone <bundleId>` is a prerequisite** (§1):
  without it the mic prompt blocks like the photo one, and `expo-audio` can refuse to start with a
  "Missing audio…" error. One real run captured this state cleanly after the grant; another still hit the
  `expo-audio` error even with it. **If the reference shows this state, grant the mic and ATTEMPT the
  capture** — "the simulator has no mic" is a conclusion you reach after the attempt fails, not before.
- **Edit mode:** put the composer into edit state (trigger the edit action on an own message) and
  screenshot the edit banner + confirm button. **Worth driving whenever a custom override reads message
  context** (`Reply`/quoted message, `MessageHeader`): the composer mounts those slots too, with no message
  around them — a real run found a crash exactly there.

---

## 5. Wait for the client before you trust a screenshot — POLL, never `sleep`

If the app gates its splash on the chat/video/feeds client resolving (e.g. splash hides only once
`chatClient` is ready), a screenshot taken too soon captures the launch/splash screen (Expo splash, or the RN CLI launch / white screen), which looks like a hang.

**Never put a fixed `sleep` between `launch` and `screenshot`.** A blind sleep is either too short (you
shoot the splash) or too long (you pay it on every one of the ~20 captures a run makes). Measured across
seven real runs: 138 capture cycles, **86% of their wall time was `sleep`**, ~100 minutes total, and **40%
of the cycles changed nothing** — re-shoots of a frame that came back too early. Poll instead; the app is
usually ready in 2-8 s.

**`scripts/sim.sh capture` implements both stages** — you do not write this loop. Two stages, both
zero-dependency; the frame captured immediately after `launch` **is** the splash reference, so no
baseline is needed:

- **Stage A — did THIS relaunch bundle?** It marks the Metro log first (or it matches an older line),
  then waits for `iOS Bundled` / `metro:bundling:done`. **A missing bundle line is terminal**, not
  something to fall through: it means the app never loaded your JS, and the dev-launcher menu it falls
  back to is a stable non-splash frame that Stage B would happily "settle" on and report green.
- **Stage B — has the frame left the splash and stopped changing?** Two identical consecutive
  screenshots. This also covers avatars still loading and list entrance animations, because a
  mid-transition frame never matches its predecessor — a shot fired immediately can catch a
  placeholder and read as a design mismatch that isn't one.

On success the output file already holds the settled frame — don't re-shoot it. On failure `sim.sh`
**deletes** it rather than leaving a splash or mid-transition frame to be mistaken for a capture, and
prints the diagnosis list below.

`iOS Bundled 1214ms index.ts (745 modules)` is the Expo/RN Metro ready line; a JSON-logging Metro prints
`{"_e":"metro:bundling:done",…}`. A cached relaunch still prints one (`iOS Bundled 38ms … (1 module)`).
`packager-status:running` only proves Metro is **up** — `sim.sh` gates *Metro readiness* on it (§1) but
never the bundle, because it says nothing about whether *your* app finished bundling.

**The cap does NOT grow.** Stage A allows a generous budget (`BUNDLE_TIMEOUT`, 180 s — a cold Metro cache
genuinely compiles for 1–2 min) and Stage B 25 s. If either runs out you have a real defect —
**diagnose it, do not raise the timeout and re-shoot.** In the seven runs the sleep ratcheted 20 s → 40-90
s and never came back down, because one early frame was read as "too fast" instead of "broken"; that habit
is where most of the 100 minutes went. When the cap trips, it is one of:

- a **stale bundle** or a dev server on the wrong port → §2;
- `launch` **no-op'd** on an already-running app because you skipped `terminate` → §2;
- a **blocking modal** ("Open in Expo Go?", a permission prompt) that survives terminate → §1/§3, reboot;
- the client genuinely never connects → read the Metro log and the app's own error output.

A longer sleep hides all four and produces a screenshot you cannot trust.

---

## 6. Verifying dark mode — flip the OS appearance, don't rebuild

Verify **both** modes on the same build — no rebuild needed; an app reading `useColorScheme()` re-renders
on the change. **What to check in each mode is
[design-matching.md](design-matching.md#44-check-dark-mode) §4.4**; this section is only how to capture
them.

```bash
# Shoot light FIRST — it is the reference the flip must move.
bash scripts/sim.sh capture <bundleId> <screen>-light-1.png --project "$P" --lane expo
bash scripts/sim.sh appearance <udid> dark <screen>-dark-1.png     # 'light' to switch back
```

`appearance` flips the OS setting and then polls until the frame settles (§5, Stage B) — the re-render
is not instant.

**It requires the pixels to actually move, and that check matters.** "The frame changed" is *not*
evidence the flip landed: transient chrome changes it too. On an app whose dark mode is MMKV-driven,
the Expo dev-menu bubble collapsed between the two shots, the frame-hash check passed, and the tool
returned a **light** screenshot named `dark.png` with exit 0. It now measures mean luminance before and
after and demands a move of ≥25 in the right direction, and when that fails it names the likely cause
instead of handing you the file.

**Caveat — `simctl ui appearance` only works if the app follows the OS.** The flip assumes
`useColorScheme()` drives dark mode. If the app drives it from **app state** — a manual toggle persisted
in MMKV / AsyncStorage / a theme context (common in migrated apps, e.g. a moon/sun button) — then it is a
**no-op**, and `sim.sh appearance` fails with exactly that diagnosis rather than letting you wrongly
conclude dark mode is broken. **Check the app's theme-toggle source first:** if it reads a persisted flag,
drive dark mode the app's own way — flip the flag from temporary scaffold (set the MMKV/AsyncStorage key
or call the theme context's setter), then re-render and screenshot.

**Caveat — a `WithComponents` slot override does NOT re-resolve on a runtime flip.** Whenever a colour
reaches the screen through a slot override, **cold-launch each mode** (terminate → `simctl ui … appearance`
→ launch) instead of flipping while the app runs: those overrides resolve at first mount, so on a runtime
flip they stay light while everything around them flips. The frame-hash settle check above still passes,
because the surfaces that *do* flip change the frame — so this defect survives a green verification.

---

## 7. Known environmental limits (don't fight these)

- **A green launch does not prove correctness.** Boot success proves nothing about a version-gated crash
  (surfaces on worklet/animation paths, not at boot), an unfilled background, or an off-by-a-safe-area
  size. Verify by the thing that's actually wrong — a version number, a sampled pixel, an on-device check
  — not by "it ran."
- **Physical-scale sizing reads correctly only on a device, not on the roomy sim window.** A
  keyboard-height–relative size — the attachment-picker sheet height, a safe-area gap, a bottom-bar height
  — can look fine on the large simulator window while being visibly oversized/undersized on a phone.
  Verify these against the thing they represent (the SDK default, a measured value), not by eye on the
  sim; when a size stands for the keyboard/safe area, confirm on a device.
- **Screenshots verify appearance, NOT interaction.** `simctl` can't tap, so a screenshot diff never
  exercises `onPress`/`onSelect`/navigation handlers — a broken tap looks identical to a working one. Any
  custom slot with a handler (a custom `ChannelPreview` row, message press, a custom button) must be
  verified by *driving* it: temp auto-nav (§3), a seeded state, or a real device. A custom
  `ChannelPreview` that read `onSelect` from props instead of `useChannelsContext()` silently no-op'd
  channel-tap and passed every screenshot check.
- **Component overrides won't show if wired wrong:** in `stream-chat-react-native` v9 a slot such as
  `MessageHeader` is applied through **`WithComponents overrides={{ MessageHeader: … }}`**, not by passing
  it as a `<Channel MessageHeader={…}>` prop (silently ignored — no error, no effect, which looks exactly
  like a stale bundle). Same in both lanes. Also, the *default* `MessageHeader` renders nothing unless the
  message is pinned / saved-for-later / reminder / sent-to-channel, so verify an override with an
  explicit, visibly-distinct custom component.
- **iOS 26 Photo Library access:** the gallery grid fires a tap-only, SpringBoard-owned prompt you can't
  dismiss. Revoke photo access before launch and verify on the **Files** tab — full procedure in §1.
- The simulator has **no camera or microphone** — video/audio *capture* can only be verified on a real
  device (see the Video reference). But the recorder **UI** is still screenshot-able: grant the mic (§1)
  and drive the state (§4) before concluding otherwise.
- **A piped command reports the PIPE's exit status, not the command's — so run every verification
  command through `scripts/gate.sh`, which cannot make this mistake.**
  ```bash
  bash scripts/gate.sh <abs-project-dir> npx tsc --noEmit
  ```
  It absolute-`cd`s, redirects (never pipes), prints `EXIT=<real status>`, and tails the log.
  `npx tsc --noEmit | head -5; echo $?` prints `0` on a *failing* typecheck, and `run-ios … | tail`
  prints tail's success on a build that died with 65. Both happened in one real run, which then
  reported a passing gate on a broken build. (Don't reach for `${PIPESTATUS[0]}` either — this shell
  is zsh, where it expands to nothing.) The absolute `cd` matters just as much: `npx <tool>` outside a
  project silently resolves an unrelated registry package — `npx tsc` in the wrong directory prints
  "This is not the tsc command you are looking for" and looks like a pass.
- **Dev-only overlays — ignore them in screenshots:** the **Expo** dev-client overlays a small floating
  **gear / dev-menu launcher**; the **RN CLI** shows a **LogBox "Open debugger to view warnings" toast** at
  the bottom. Both are dev-only (gone in a release build) and not part of the app. Never treat either as
  an app element or a design mismatch to fix.

---

## 8. Expo vs RN CLI — quick reference

**Metro, onboarding, launch/relaunch and screenshot are all `scripts/sim.sh capture --lane expo|cli`** —
the rows below are what it does per lane, kept so you can read *why*, not so you retype them. Expo Go
appears only as a **baseline-capture** lane (§1): Metro is that app's own dev server, and you launch with
`simctl launch host.exp.Exponent --initialUrl "http://127.0.0.1:<port>"`.

| Step | Expo dev-client | React Native CLI |
|---|---|---|
| Everything below, in one call | `sim.sh capture <bundleId> <out.png> --project "$P" --lane expo` | `sim.sh capture <bundleId> <out.png> --project "$P" --lane cli` |
| Metro (§1 — never pipe) | `npx expo start --dev-client > log 2>&1 &`, then wait for `/status` | `npx react-native start > log 2>&1 &` (install `watchman` — §2) |
| Build once (§1 — via `gate.sh`) | `npx expo run:ios --device <udid>` (its launch step errors on osascript — harmless; it also fires `openurl`, so a modal may be left on screen) | `npx react-native run-ios --udid <udid>` (builds **and** launches cleanly) |
| Onboarding sheet (§1) | `defaults write <bundleId> EXDevMenuIsOnboardingFinished -bool YES` | n/a (no dev-launcher) |
| Launch / relaunch (§2) | `simctl terminate` **then** `simctl launch <bundleId> --initialUrl "http://localhost:<port>"` | `simctl terminate` **then** `simctl launch <bundleId>` (bare) |
| Bundle gate (§5) | `iOS Bundled` required | same; pass `--no-bundle-gate` if a cached launch prints none |
| Dev-launcher menu / "Open?" modal risk (§1, §3) | Yes — avoid via `--initialUrl`, never `openurl` | None |
| Reload after edit (§2) | relaunch (re-fetches fresh) | Fast Refresh **iff** watchman installed; else `react-native start --reset-cache` + relaunch |
| Reach non-initial screen (§3) | Expo Router `router.push`, **encode the cid** | React Navigation `navigate('Channel', { channelCid })`, **no encoding** |
| Dev overlay to ignore (§7) | floating gear | LogBox "Open debugger" toast |
