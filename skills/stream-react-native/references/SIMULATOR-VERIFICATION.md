# Verifying on the iOS simulator — the fast loop

Running a Stream RN app on the iOS simulator to screenshot and verify it is the most **expensive**
part of a build (a native build is minutes, not seconds). Most of the wasted time comes from a
handful of avoidable mistakes: a second native rebuild, a stale Metro bundle, and fighting the
simulator's lack of touch input. This page is the playbook that avoids them.

Two lanes, and they behave **differently** at launch/reload — pick yours and read its column:

- **Expo dev-client / native-build** (`npx expo prebuild` + `expo run:ios`, Metro via `expo start`).
- **React Native Community CLI** (`pod install` + `npx react-native run-ios`, Metro via
  `react-native start`). No expo-dev-launcher, so several Expo-only steps below **do not apply**.

**A third lane exists for BASELINE captures only: Expo Go.** Stream apps never target Expo Go, but the
*pre-migration* app you are capturing a baseline from often does (Track S). It launches tap-free the
same way the dev client does — `xcrun simctl launch <udid> host.exp.Exponent --initialUrl
"http://127.0.0.1:<port>"`. Do **not** reach for `simctl openurl exp://…`: that fires an un-tappable
"Open in Expo Go?" alert that survives `terminate` and forces a reboot (§3). Expo Go may not be
installed on a fresh simulator — install it from `~/.expo/ios-simulator-app-cache/Expo-Go-*.tar.app`.

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

**Verifying the attachment picker — REVOKE photo access before first launch; do NOT grant it.** The
picker's gallery tab requests photo-library access, and that alert is SpringBoard-owned: you can't tap
Allow/Don't Allow, and it survives `terminate`/`launch`, so it covers every later screenshot until you
reboot. **`simctl privacy grant photos` does not reliably suppress it on iOS 26** — two real runs
granted (one also pre-seeded the library and rebooted) and the un-dismissable prompt fired anyway,
costing 5 simulator reboots between them. **Revoke instead:** a *denied* permission makes the SDK
render its in-app *"You have not granted access to the photo library — Change in Settings"* panel,
which is an ordinary view — no alert, nothing to tap, nothing to reboot out of.

```bash
# Run both while the app is NOT running, then cold-launch.
xcrun simctl privacy <udid> revoke photos <bundleId>
# Grant the MIC, though — without it expo-audio can't start the recorder (see §4).
xcrun simctl privacy <udid> grant microphone <bundleId>
```

Then drive the picker open in code. **Order matters:** the SDK's `reactToIndex` forces
`selectedPicker='images'` when the sheet settles at index 0, so a tab selected *before* the open call
is discarded — switch **after** the sheet settles (both real runs hit this and landed on the same fix):

```tsx
useMessageInputContext().openAttachmentPicker();
// AFTER the sheet settles, not before — a pre-set picker is overwritten by reactToIndex.
setTimeout(() => attachmentPickerStore.setSelectedPicker('files'), 1200);
```

The **Files** tab never touches the photo library, so it's the tab to verify the selection bar and
layout on. Confirm the real populated photo grid on a physical device.

**Layout is verifiable in ANY picker state — don't wait on a populated grid.** The composer↔picker
relationship (e.g. the `topInset` gap covered in
[regions-chat.md](regions-chat.md) > Composer - attachment picker) renders identically whether the
sheet shows a photo grid, the Files list, or the "not granted" panel — the sheet always fills its
reserved height. So you can confirm there's no gap between the composer and the picker without ever
populating the grid; conversely, **an empty or not-granted grid is not a layout bug** — don't chase
it as one, and don't let it mask a real gap (verify spacing against the composer, not the grid
contents).

If a blocking prompt did fire from an earlier run, a reboot is the only tap-free recovery:
`xcrun simctl shutdown <udid> && xcrun simctl boot <udid>`.

**Write every capture to a UNIQUE filename.** Never reuse one path across capture attempts. A retry
that overwrites its predecessor can be unrecoverable, because the app you are capturing may not render
the same state twice — a real run lost the only baseline holding reaction pills (the source SDK's local
cache dropped reactions on reload), and recovering it cost a `git worktree` rebuild of the original app
on a second Metro. Name shots `<screen>-<state>-<attempt>.png` and delete the rejects at the end.

### Expo dev-client lane

```bash
# 1) Start Metro SEPARATELY, in the background, NOT in CI mode.
#    Redirect to a log — NEVER pipe it. A closing pipe (| head, | tail) KILLS Metro; a real run
#    lost its dev server mid-session to `expo start … | head -N` and had to restart detached.
npx expo start --dev-client --clear > /tmp/metro-<proj>.log 2>&1 &

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
#    ALWAYS terminate first: launch on a running app returns its PID without restarting (§2).
xcrun simctl terminate <udid> <bundleId>
xcrun simctl launch <udid> <bundleId> --initialUrl "http://localhost:8081"

# 5) Screenshot — but POLL for readiness first, never `sleep`. Copy the loop from §5.
#    A bare launch→screenshot here catches the splash; a fixed sleep was 86% of capture wall time
#    across seven real runs. §5 is two zero-dependency stages and is usually done in 2-8 s.
xcrun simctl io <udid> screenshot <screen>-<state>-1.png
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
# 1) Start Metro SEPARATELY, in the background. Redirect to a log, never pipe it (a closing
#    pipe kills Metro). See §2 for the watchman caveat.
npx react-native start > /tmp/metro-<proj>.log 2>&1 &

# 2) Build + install + launch ONCE (the expensive native build). This also launches cleanly.
npx react-native run-ios --udid <udid>

# 3) FAST relaunch on every later iteration — bare launch, NO --initialUrl. Auto-connects to Metro.
#    Terminate first — launch on a running app returns its PID without restarting (§2).
xcrun simctl terminate <udid> <bundleId>
xcrun simctl launch <udid> <bundleId>

# 4) Screenshot — POLL for readiness first (§5), never `sleep`.
xcrun simctl io <udid> screenshot <screen>-<state>-1.png
```

The CLI's dev overlay is a **LogBox "Open debugger to view warnings" toast** (bottom of screen), not a
gear — also dev-only, ignore it (see §7).

---

## 2. Force a clean relaunch after code changes (avoid a stale bundle)

Fast Refresh usually applies edits in place, but when you **remove** a component or import — e.g.
deleting the temp navigation scaffold from §3 — the in-memory bundle can keep referencing the gone
code and the app crashes on next interaction. Don't debug that as a real bug; it's a stale bundle.

**Expo lane — `terminate` FIRST, then launch:**

```bash
xcrun simctl terminate <udid> <bundleId>
xcrun simctl launch <udid> <bundleId> --initialUrl "http://localhost:8081"
```

**`simctl launch` against an already-running app returns the existing PID and does NOT restart it** —
so the "relaunch" is a no-op, you screenshot the old UI, and read it as a failed fix (a real run did
exactly that). The dev client can also hold a stale module-resolution error after the file is fixed,
which only a genuine terminate+launch clears. You do **not** need another `npx expo run:ios` — the
native binary hasn't changed, only JS.

**RN CLI lane — the watchman caveat (important):** if **`watchman` is not installed**, Metro does
**not** detect file edits, so **no** reload path surfaces your change — not Fast Refresh, not the
packager `GET /reload`, not even a cold `simctl launch` (the CLI app reuses its on-disk cached
bundle). Symptom: you edit a file, relaunch, and the screen is unchanged. The fix is one of:

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

Metro's interactive `r` reload only exists when Metro runs in a **foreground** terminal; the
background Metro above has no TTY to receive it (true for both lanes).

---

### Two "looks-like-a-crash" issues that are really Metro/port problems

- **`EXPO_PUBLIC_*` env vars are inlined at Metro BUNDLE time, not runtime.** After writing `.env` (e.g. the API key + a token), the running bundle keeps the OLD/empty values until you **restart Metro with `--clear`**. Symptom: the app shows its "credentials missing" gate even though `.env` is correct. Confirm the value actually reached the served bundle: `curl -s "http://localhost:<port>/node_modules/expo-router/entry.bundle?platform=ios&dev=true" | grep -c "<value-prefix>"`.
- **Wrong-Metro → `PlatformConstants could not be found` (`TurboModuleRegistry.getEnforcing('PlatformConstants')`).** This reads like a native/build failure but is a **JS-bundle ↔ native mismatch from loading the wrong Metro** — e.g. another dev server is already on `8081`, so the freshly built app loads *that* project's bundle. Fix: run your Metro on a **free port** (`--port 8082`) and **cold-launch** onto it (`xcrun simctl launch <udid> <bundle> --initialUrl "http://localhost:8082"`); a relaunch over a running app keeps the stale server, so terminate first. **Don't kill the user's other server** — just use a different port. **If the user PINNED the occupied port**, that's a conflict only they can resolve: report what's holding it (`lsof -nP -iTCP:<port> -sTCP:LISTEN`, and which project it belongs to) and either ask, or proceed on a free port and say so. Two real runs silently killed a sibling project's dev server to honour a pinned port and had to disclose it afterwards.

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
  **`expo run:ios` fires `openurl` itself** during its launch step, so the alert can appear even
  though *you* never ran `openurl` — if a run:ios leaves a modal on screen, reboot and relaunch with
  `--initialUrl` rather than hunting for what you did wrong.
- **Then DELETE all temp scaffold** (remove the branch/import, don't just disable it), re-typecheck,
  and **force a clean relaunch** (§2 — mind the RN CLI watchman caveat) — otherwise a stale bundle
  still referencing the removed temp component crashes the app.

For a region that's off-screen and awkward to reach, an alternative is to **seed** the state via the
Stream CLI (`getstream api SendMessage …`), screenshot, then hard-delete
(`getstream api DeleteMessage --request '{"hard":true}'`).

---

## 4. Drive composer & picker states

**Capture at-rest, typing and picker-open on every run; drive any other state only when a reference
screenshot shows it** ([design-matching.md](design-matching.md#32-screenshot-every-screen-then-check-it) > composer gate). `simctl`
can't type, so drive a state from a temp child inside `<Channel>` that calls SDK hooks, screenshot it,
then delete the scaffold (§3 cleanup rules apply).

**Mandatory — every run:**

- **At rest (empty input):** - default state
- **Typing (input has text):** - Drive it in:
  ```tsx
  // temp child rendered inside <Channel>
  useMessageComposer().textComposer.setText('hello');   // → triggers the mic→send swap
  ```
  then screenshot and inspect the send button (shape, glyph, color, position).
- **Attachment picker open:** `useMessageInputContext().openAttachmentPicker()` (open to the Files
  tab — see the open-then-switch order in §1). Verify the composer↔picker spacing here too.

**Only when a reference screenshot shows the state** (driving these speculatively has not caught a
defect; what they'd find — an unset `audioRecordingEnabled`, an off-screen composer — shows at rest):

- **Keyboard UP (a SEPARATE state — `setText` does NOT raise the keyboard).** Programmatic
  `setText` fills the input but never opens the software keyboard, so it does **not** exercise
  keyboard-avoidance (`keyboardVerticalOffset` / `topInset` on `<Channel>`). To verify that, **focus
  the input** so the real keyboard rises (focus the composer's input, e.g. via the input ref in
  context or a temp `autoFocus`). On the iOS simulator the software keyboard is **hidden while a
  hardware keyboard is connected** — enable it (Simulator ▸ I/O ▸ Keyboard ▸ *Connect Hardware
  Keyboard* off, or ⌘K) or the keyboard won't appear and you'll wrongly conclude it's fine. Then
  confirm the composer sits above the keyboard with no gap/overlap.
- **Voice-recording in progress:** start a recording via the SDK's audio-recording context/controller
  (confirm the hook in the installed package). The sim has no mic so no audio is captured, but the
  **in-progress recorder UI still renders** — screenshot it and sample its tint (waveform / mic /
  timer): it draws from `accentPrimary` / `chatWaveformBar`, a common place a stray SDK-default colour
  survives a theme pass. **`xcrun simctl privacy <udid> grant microphone <bundleId>` is a
  prerequisite** (§1): without it the mic prompt blocks like the photo one, and `expo-audio` can
  refuse to start with a "Missing audio…" error. One real run captured this state cleanly after the
  grant; another still hit the `expo-audio` error even with it. **If the reference shows this state,
  grant the mic and ATTEMPT the capture** — "the simulator has no mic" is a conclusion you reach after
  the attempt fails, not before it.
- **Edit mode:** put the composer into edit state (trigger the edit action on an own message) and
  screenshot the edit banner + confirm button. **Worth driving whenever a custom override reads message
  context** (`Reply`/quoted message, `MessageHeader`): the composer mounts those slots too, with no
  message around them — a real run found a crash exactly there.

---

## 5. Wait for the client before you trust a screenshot — POLL, never `sleep`

If the app gates its splash on the chat/video/feeds client resolving (e.g. splash hides only once
`chatClient` is ready), a screenshot taken too soon captures the launch/splash screen (Expo splash,
or the RN CLI launch screen / white screen), which looks like a hang.

**Never put a fixed `sleep` between `launch` and `screenshot`.** A blind sleep is either too short
(you shoot the splash) or too long (you pay for it on every one of the ~20 captures a run makes).
Measured across seven real runs: 138 capture cycles, **86% of their wall time was `sleep`**, ~100
minutes total, and **40% of the cycles changed nothing at all** — they were re-shoots of a frame that
came back too early. Poll instead; the app is usually ready in 2-8 s.

Two stages, both zero-dependency. The frame captured immediately after `launch` **is** your splash
reference — no baseline needed:

```bash
U=<udid>; B=<bundleId>; LOG=/tmp/metro-<proj>.log; OUT=<screen>-<state>-1.png

# Stage A — wait for THIS relaunch's bundle. Mark the log first, or you match an older line.
MARK=$(wc -l < "$LOG")
xcrun simctl terminate $U $B 2>/dev/null
xcrun simctl launch $U $B --initialUrl "http://localhost:8081" >/dev/null   # Expo; bare launch for RN CLI (§1)
xcrun simctl io $U screenshot /tmp/splash.png                               # ← the splash reference
for i in $(seq 1 20); do
  tail -n +$((MARK+1)) "$LOG" | grep -qE 'iOS Bundled|metro:bundling:done' && break
  sleep 1
done

# Stage B — poll until the frame LEAVES the splash and then STOPS changing (two identical in a row).
SPLASH=$(md5 -q /tmp/splash.png); PREV=""; OK=0
for i in $(seq 1 25); do
  xcrun simctl io $U screenshot "$OUT" >/dev/null 2>&1
  H=$(md5 -q "$OUT")
  [ "$H" = "$SPLASH" ] && { PREV=""; sleep 1; continue; }        # still splash
  [ "$H" = "$PREV" ] && { OK=1; echo "settled in ${i}s"; break; } # stable → this shoot is good
  PREV=$H; sleep 1
done
# FAIL LOUDLY. A silent timeout leaves a splash frame in $OUT and it looks like a real capture.
[ $OK -eq 1 ] || { echo "NOT READY — do NOT trust $OUT; diagnose (do NOT raise the cap)"; exit 1; }
```

On success `$OUT` already holds the settled frame — don't re-shoot it. On failure it holds a splash or
mid-transition frame; **delete it** rather than leaving it to be mistaken for a capture later.

Stage B's two-identical-frames test is what §5's second half used to ask for by feel: it also covers
avatars still loading and list entrance animations, because a mid-transition frame never matches its
predecessor. A shot fired immediately can catch a placeholder and read as a design mismatch that isn't
one — the poll removes the guesswork.

`iOS Bundled 1214ms index.ts (745 modules)` is the Expo/RN Metro ready line; a JSON-logging Metro
prints `{"_e":"metro:bundling:done",…}`. A cached relaunch still prints one (`iOS Bundled 38ms … (1
module)`). Note that `packager-status:running` only proves Metro is **up** — it says nothing about
whether *your* app finished bundling, so don't gate on it.

**The wait is capped, and the cap does NOT grow.** If Stage A or B runs out, you have a real defect —
**diagnose it, do not raise the timeout and re-shoot.** In the seven runs the sleep ratcheted 20 s →
40-90 s and never came back down, because one early frame was read as "too fast" instead of "broken";
that single habit is where most of the 100 minutes went. When the cap trips, it is one of:

- a **stale bundle** or a dev server on the wrong port → §2 (and the `PlatformConstants` note in §3);
- `launch` **no-op'd** on an already-running app because you skipped `terminate` → §1/§2;
- a **blocking modal** ("Open in Expo Go?", a permission prompt) that survives terminate → §3, reboot;
- the client genuinely never connects → read the Metro log and the app's own error output.

A longer sleep hides all four and produces a screenshot you cannot trust.

---

## 6. Verifying dark mode — flip the OS appearance, don't rebuild

If the design supports dark mode (or you applied the light/dark carve-out — pin brand/content colors,
keep structural surfaces semantic), verify **both** modes on the same build. Flip the OS appearance at
runtime and re-screenshot — no rebuild needed; a React Native app reading `useColorScheme()` re-renders
on the change:

```bash
# iOS simulator (pinned UDID from §1). Shoot light FIRST — it is the reference the flip must move.
U=<udid>
xcrun simctl io $U screenshot light.png
xcrun simctl ui $U appearance dark          # → light to switch back
# The re-render is NOT instant. Poll until the frame differs from light and settles (§5, Stage B).
LIGHT=$(md5 -q light.png); PREV=""; OK=0
for i in $(seq 1 15); do
  xcrun simctl io $U screenshot dark.png >/dev/null 2>&1
  H=$(md5 -q dark.png)
  [ "$H" = "$LIGHT" ] && { PREV=""; sleep 1; continue; }          # flip hasn't landed yet
  [ "$H" = "$PREV" ] && { OK=1; break; }
  PREV=$H; sleep 1
done
[ $OK -eq 1 ] || { echo "appearance flip never changed the frame — see the caveat below"; rm -f dark.png; }
```

**Caveat — `simctl ui appearance` only works if the app follows the OS.** The flip above assumes dark
mode is driven by `useColorScheme()`. If the app drives dark mode from **app state** — a manual toggle
persisted in MMKV / AsyncStorage / a theme context (common in migrated apps, e.g. a moon/sun button) —
then `simctl ui appearance dark` is a **no-op** and you'll wrongly conclude dark mode is broken (or
waste a relaunch chasing it). **Check the app's theme-toggle source first:** if it reads
`useColorScheme()`, use the flip above; if it reads a persisted flag, drive dark mode the app's own way
— flip the persisted flag from temporary scaffold (set the MMKV/AsyncStorage key or call the theme
context's setter), then relaunch/re-render and screenshot. Don't reach for `simctl ui appearance` on an
app-state-driven toggle.

Then confirm the carve-out held: **structural surfaces** (message-list background, composer/input
background, borders) flipped to their dark values, while **pinned brand/content** colors (bubble
fills, glyphs, accent, read-receipt ticks) look identical to light mode. A surface that stayed light
is a pinned-to-literal bug; a brand color that washed out was pinned wrong. Sample both modes and diff
per the color-sampling method in [design-matching.md](design-matching.md).

---

## 7. Known environmental limits (don't fight these)

- **Screenshots verify appearance, NOT interaction.** `simctl` can't tap, so a screenshot diff never
  exercises `onPress`/`onSelect`/navigation handlers — a broken tap looks identical to a working one.
  Any custom slot with a handler (a custom `ChannelPreview` row, message press, a custom button) must
  be verified by *driving* it: temp auto-nav (§3), a seeded state, or a real device. A custom
  `ChannelPreview` that read `onSelect` from props instead of `useChannelsContext()` silently no-op'd
  channel-tap and passed every screenshot check.
- **Component overrides won't show if wired wrong:** in `stream-chat-react-native` v9 a slot such as
  `MessageHeader` is applied through **`WithComponents overrides={{ MessageHeader: … }}`**, not by
  passing it as a `<Channel MessageHeader={…}>` prop (that prop is silently ignored — no error, no
  effect, which looks exactly like a stale bundle during verification). Same in both lanes. Also, the
  *default* `MessageHeader` renders nothing unless the message is pinned / saved-for-later / reminder
  / sent-to-channel, so verify an override with an explicit, visibly-distinct custom component.
- **iOS 26 Photo Library access:** the gallery grid fires a tap-only, SpringBoard-owned prompt you
  can't dismiss, and `simctl privacy grant photos` does **not** reliably suppress it. **Revoke photo
  access before launch** so the SDK renders its in-app "not granted" panel instead of an alert, and
  verify the selection bar/layout on the **Files** tab. Full procedure + the "layout is verifiable in
  any state" rule are in §1.
- The simulator has **no camera or microphone** — video/audio *capture* can only be verified on a real
  device (see the Video reference). But the recorder **UI** is still screenshot-able: grant the mic
  (§1) and drive the state (§4) before concluding otherwise.
- **A piped command reports the PIPE's exit status, not the command's — never pipe a verification
  command.** `npx tsc --noEmit | head -5; echo $?` prints `0` on a *failing* typecheck, and
  `run-ios … | tail` prints tail's success on a build that died with 65. Both happened in one real
  run, which then reported a passing gate on a broken build. Redirect to a file and read it back
  instead: `<cmd> > /tmp/out.log 2>&1; echo "EXIT=$?"; tail -20 /tmp/out.log`. (Don't reach for
  `${PIPESTATUS[0]}` either — this shell is zsh, where that expands to nothing and you get a blank
  where the exit code should be.) Related: run project commands from an **absolute** `cd`, because
  `npx <tool>` outside a project silently resolves an unrelated registry package — `npx tsc` in the
  wrong directory prints "This is not the tsc command you are looking for" and looks like a pass.
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

Expo Go appears only as a **baseline-capture** lane (a pre-migration app you're screenshotting, never a
Stream target — see §1): Metro is that app's own dev server, and you launch with
`simctl launch host.exp.Exponent --initialUrl "http://127.0.0.1:<port>"`.

| Step | Expo dev-client | React Native CLI |
|---|---|---|
| Metro | `npx expo start --dev-client --clear > log 2>&1 &` | `npx react-native start > log 2>&1 &` (install `watchman` — see §2) — **never pipe either** |
| Build once | `npx expo run:ios --device <udid>` (its launch step errors on osascript — harmless; it also fires `openurl`, so a modal may be left on screen) | `npx react-native run-ios --udid <udid>` (builds **and** launches cleanly) |
| Onboarding sheet | `defaults write <bundleId> EXDevMenuIsOnboardingFinished -bool YES` | n/a (no dev-launcher) |
| Launch / relaunch | `simctl terminate` **then** `simctl launch <bundleId> --initialUrl "http://localhost:8081"` | `simctl terminate` **then** `simctl launch <bundleId>` (bare — no `--initialUrl`) |
| Dev-launcher menu / "Open?" modal risk | Yes — avoid via `--initialUrl`, never `openurl` | None |
| Reload after edit | relaunch (re-fetches fresh) | Fast Refresh **iff** watchman installed; else `react-native start --reset-cache` + relaunch (§2) |
| Reach non-initial screen | Expo Router `router.push`, **encode the cid** | React Navigation `navigate('Channel', { channelCid })`, **no encoding** |
| Dev overlay to ignore | floating gear | LogBox "Open debugger" toast |
