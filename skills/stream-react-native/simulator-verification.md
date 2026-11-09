# Verifying on a simulator

Running the app to screenshot and check it is the most expensive part of an RN build.
Most of the wasted time comes from a second native build, a stale Metro bundle, and fixed
waits. This file covers the iOS simulator in both lanes (Expo development build, RN CLI),
with Android emulator equivalents at the end.

Pin one simulator UDID for the whole loop and pass it to every `simctl` and `run:ios`
call; several booted simulators is how a screenshot lands on the wrong device.

## Two ways to drive it

- **A simulator tool that can tap** (an iOS Simulator MCP or similar: tap, type,
  long-press, swipe, screenshots): prefer it. Reach screens and interaction states with
  real taps instead of temporary code, and poll with its screenshots. Its traps are in
  "Driving it with taps".
- **Only `xcrun simctl`:** it can't tap, type, or scroll. Reach screens with temporary code
  ("Reaching screens and states with only simctl").

The rules are the same either way: never wait with a fixed `sleep` - poll ("Wait by
polling, not sleeping"); terminate before every relaunch; and drive every handler, because
a screenshot doesn't prove a tap works.

## The run loop

Decide every native capability package before the first build (SKILL.md, Setup). Then:

**Expo development build**

```bash
# 1) Metro separately, in the background, not in CI mode. Redirect to a log - never
#    pipe it: a closing pipe (| head, | tail) kills Metro.
npx expo start --dev-client --clear > /tmp/metro-<proj>.log 2>&1 &

# 2) Build and install once.
npx expo run:ios --device <udid>

# 3) Skip the development build's onboarding sheet.
xcrun simctl spawn <udid> defaults write <bundleId> EXDevMenuIsOnboardingFinished -bool YES

# 4) Launch, and relaunch on every later iteration: terminate first, always.
xcrun simctl terminate <udid> <bundleId>
xcrun simctl launch <udid> <bundleId> --initialUrl "http://localhost:8081"
```

- `expo run:ios` often ends with an `osascript ... count processes` error. That is a
  macOS automation-permission failure on its own launch step, not a build failure - the
  app is installed. It may also fire an `openurl` that leaves an "Open in <app>?" alert
  on screen (see Blocking alerts).
- Launch only with `--initialUrl "http://localhost:<port>"`. A bare launch opens the
  development build's server menu, which needs a tap; an `exp+<scheme>://` URL or
  `simctl openurl` raises an alert that needs a tap.

**RN CLI**

```bash
npx react-native start > /tmp/metro-<proj>.log 2>&1 &
npx react-native run-ios --udid <udid>          # builds, installs, and launches
xcrun simctl terminate <udid> <bundleId>         # every later iteration
xcrun simctl launch <udid> <bundleId>            # bare launch; the bundle URL is baked in
```

Without `watchman`, Metro doesn't see file edits, and no reload path picks them up -
not Fast Refresh, not a relaunch. Install it (`brew install watchman`), or restart Metro
with `--reset-cache` per change. Confirm an edit reached the bundle before trusting a
screenshot:
`curl -s "http://localhost:8081/index.bundle?platform=ios&dev=true" | grep -c "<marker>"`.

## Traps that look like app bugs

- **`launch` on a running app is a no-op.** It returns the existing PID without
  restarting, so you screenshot the old UI and read it as a failed fix. Terminate first.
- **Stale bundle after removing code.** Deleting a component or temporary scaffold can
  leave the in-memory bundle pointing at it, and the app crashes on the next
  interaction. Terminate and relaunch; no native rebuild needed.
- **`EXPO_PUBLIC_*` is inlined at bundle time.** After editing `.env`, restart Metro with
  `--clear`, or the app keeps the old values (a "credentials missing" gate with a
  correct `.env`).
- **`PlatformConstants could not be found`** usually means the app loaded another
  project's Metro already on 8081. Run yours on a free port (`--port 8082`), launch onto
  it, and don't kill the user's other server.
- **Piped commands lie.** A pipe reports the pipe's exit status: `npx tsc --noEmit |
  head` prints 0 on a failing check. Redirect to a file instead:
  `<cmd> > /tmp/out.log 2>&1; echo "EXIT=$?"; tail -20 /tmp/out.log`. `PIPESTATUS` is
  empty in zsh. Run project commands from an absolute `cd`: `npx tsc` outside the project
  resolves an unrelated package and looks like a pass.

## Blocking alerts and permissions

System alerts (permission prompts, "Open in <app>?") can't be tapped, survive
terminate and launch, and cover every later screenshot. The only tap-free recovery is a
reboot: `xcrun simctl shutdown <udid> && xcrun simctl boot <udid>`. Prevent them, with
the app not running:

```bash
xcrun simctl privacy <udid> revoke photos <bundleId>      # revoke, don't grant
xcrun simctl privacy <udid> grant microphone <bundleId>   # the recorder needs it
```

- Photos: on iOS 26, granting doesn't reliably suppress the photo prompt. A denied
  permission makes the attachment picker show its in-app "not granted" panel instead, an
  ordinary view. Check the picker's layout on the Files tab: the sheet fills its height
  in any state, so an empty or not-granted grid is not a layout bug. Confirm a populated
  gallery on a real device.
- Opening the picker from code: switch tabs about a second after
  `openAttachmentPicker()` - a tab set before the sheet settles is overwritten.
- Microphone: without the grant the recorder fails to start. The simulator captures no
  audio, but the recorder UI still renders; attempt the capture before concluding it
  can't be done.

## Driving it with taps

- Poll after every tap that navigates or opens a sheet, until the new screen settles,
  before typing. Keys typed before the input has focus go to the app (in development a
  `d` opens the Expo dev menu).
- A key press can switch the simulator to its hardware keyboard: the on-screen keyboard
  hides, and the SDK's edit action, which waits for it, silently does nothing. Show the
  on-screen keyboard again before an edit or a keyboard-avoidance check.
- Fast typing races a confirm button: let the input settle before tapping send or save,
  then check the saved text.
- Expo's floating dev gear covers header-right buttons; drag it aside before tapping them.
- In development, saving a theme module can remount the navigator: expect to navigate back
  to the screen under test after each theme edit.

## Reaching screens and states with only simctl

`simctl` can't tap, type, or scroll. Drive navigation and state from temporary code,
screenshot, then delete the code, type-check, and relaunch:

- Expo Router: a temporary `useEffect` that calls
  ``router.push(`/channel/${encodeURIComponent(cid)}`)`` after a short delay. Encode the
  cid: its `:` breaks the path segment.
- React Navigation: `navigationRef.navigate('Channel', { cid })` from the container's
  `onReady`.
- Inside `<Channel>`, a temporary child that calls SDK hooks: typing via
  `useMessageComposer().textComposer.setText('hello')` (shows the send button), the
  picker via `openAttachmentPicker()`, an edit via the edit action on an own message.
- `setText` doesn't raise the keyboard. To check keyboard avoidance, focus the input (a
  ref or a temporary `autoFocus`) and turn off the simulator's hardware keyboard
  (I/O > Keyboard > Connect Hardware Keyboard).
- Drive edit mode whenever a custom override reads message context (quoted message,
  header): the composer mounts those slots without a message, and that's where it
  crashes.

Screenshots don't test taps. A custom `ChannelPreview` that read `onSelect` from props
passed every screenshot check while channel taps did nothing. Drive each handler.

## Wait by polling, not sleeping

A fixed `sleep` either shoots the splash or wastes time on every capture. Poll: mark the
Metro log, launch, wait for this launch's bundle line, then take screenshots until one
differs from the splash and the next is identical. With a screenshot tool, the rule is
the same - after a launch or a tap, take screenshots until two in a row match, instead of
sleeping. The script below is the `simctl` version.

```bash
U=<udid>; B=<bundleId>; LOG=/tmp/metro-<proj>.log; OUT=<screen>-<state>-1.png
MARK=$(wc -l < "$LOG")
xcrun simctl terminate $U $B 2>/dev/null
xcrun simctl launch $U $B --initialUrl "http://localhost:8081" >/dev/null   # bare launch on RN CLI
xcrun simctl io $U screenshot /tmp/splash.png
for i in $(seq 1 20); do
  tail -n +$((MARK+1)) "$LOG" | grep -qE 'iOS Bundled|metro:bundling:done' && break; sleep 1
done
SPLASH=$(md5 -q /tmp/splash.png); PREV=""; OK=0
for i in $(seq 1 25); do
  xcrun simctl io $U screenshot "$OUT" >/dev/null 2>&1; H=$(md5 -q "$OUT")
  [ "$H" = "$SPLASH" ] && { PREV=""; sleep 1; continue; }
  [ "$H" = "$PREV" ] && { OK=1; break; }
  PREV=$H; sleep 1
done
[ $OK -eq 1 ] || { echo "NOT READY - don't trust $OUT"; rm -f "$OUT"; }
```

`packager-status:running` only means Metro is up, not that your app bundled. If the wait
runs out, don't raise the cap: it's a skipped terminate, a stale bundle or wrong port, a
blocking alert, or a client that never connects (read the Metro log). A first connect on a
cold app can take 30-60 s; poll for it rather than reading it as a hang.

Name every capture `<screen>-<state>-<attempt>.png`; a retry that overwrites its
predecessor may not be reproducible.

## Light and dark

`xcrun simctl ui <udid> appearance dark` re-renders apps that follow `useColorScheme()`.
If the app keeps its theme in app state (a persisted toggle), the flip does nothing: set
the theme the app's own way. Colors that reach the screen through a `WithComponents`
override resolve at first mount and don't follow a runtime flip, so cold-launch each mode
(terminate, set the appearance, launch).

## What the simulator can't show

- Camera capture crashes there: `takeAndUploadImage()` raises a native exception
  ("Source type 1 not available") that kills the app.
- Camera and microphone capture, a populated photo gallery, push delivery, and sizes
  relative to the real keyboard (the attachment picker's height): check on a device.
- On the iOS simulator, the first native multipart upload after a cold launch can fail;
  retry, and check on a device before calling it an SDK bug.
- Dev overlays (Expo's floating gear, the RN CLI's LogBox toast) aren't app elements.

## Android emulator

```bash
adb devices                                         # pin one serial with -s <serial>
npx expo run:android                                # or: npx react-native run-android
adb shell am force-stop <applicationId>             # the terminate step
adb exec-out screencap -p > <screen>-<state>-1.png
adb shell cmd uimode night yes                      # dark mode; "no" for light
```

The emulator reaches the machine's `localhost` as `10.0.2.2`; a physical Android device
needs `adb reverse tcp:8081 tcp:8081` for Metro (and the same for a local backend port).
A native module added since the last build isn't linked until `run-android` rebuilds the
app.
