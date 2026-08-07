#!/usr/bin/env bash
# iOS simulator capture loop for Stream RN apps.
#
# THE ONE COMMAND YOU NORMALLY WANT — idempotent, does everything in a single call:
#
#   bash scripts/sim.sh capture <bundleId> <out.png> --project <abs-dir> [--lane expo|cli]
#                               [--port 8081] [--device <name>] [--logical-width <pt>]
#
# PIN THE DEVICE CLASS to the reference screenshot's, before the native build:
#   python3 scripts/measure_region.py scale <reference.png>   # prints logical_width
#   bash scripts/sim.sh devices [<pt>]                        # what is available, by width
#   bash scripts/sim.sh boot --logical-width 393
# Comparing a 402pt render against a 393pt reference is not 1:1 at any scale, and
# compare_regions.py refuses it — one real run lost the whole comparison to this.
#
# It boots or reuses a simulator, preps permissions once, starts Metro if it isn't
# already up, terminates + launches the app, polls until the frame settles, and saves
# the screenshot. Repeat calls reuse the booted device and running Metro, so a capture
# loop is ONE tool call per screenshot instead of four.
#
# Granular subcommands, for when you need one step on its own:
#   boot [name | --logical-width <pt>] · devices [<pt>] · prep <udid> <bundleId>
#   metro expo|cli <dir> · shot <udid> <bundleId> <out> · appearance <udid> light|dark <out>
#   reboot <udid> · udid
#
# Every decision here was a measured cost in a real run:
#   * `shot` POLLS for a settled frame instead of sleeping. Across seven runs, 86% of
#     capture wall time was `sleep` (~100 min) and 40% of cycles changed nothing. The
#     cap does NOT grow — a timeout is a defect to diagnose, not a longer sleep.
#   * It always terminates first: `simctl launch` on a running app returns the existing
#     PID WITHOUT restarting, so you screenshot the old UI.
#   * `prep` REVOKES photo access. The gallery's permission alert is SpringBoard-owned,
#     untappable, survives terminate, and `privacy grant photos` does not reliably
#     suppress it on iOS 26. Denied -> the SDK renders an ordinary in-app panel instead.
#   * Metro is redirected to a log, never piped: a closing pipe kills Metro.
#   * Output filenames are never reused — a retry that overwrites its predecessor can be
#     unrecoverable when the app won't render the same state twice.
set -u

STATE_DIR="${TMPDIR:-/tmp}/rn-sim-state"
mkdir -p "$STATE_DIR"
BUNDLE_TIMEOUT="${BUNDLE_TIMEOUT:-180}"   # seconds allowed for Metro to build the bundle
md5of() { if command -v md5 >/dev/null 2>&1; then md5 -q "$1"; else md5sum "$1" | cut -d' ' -f1; fi; }
die() { echo "SIM_ERROR: $*" >&2; exit 1; }
key() { echo "$1" | tr -c 'A-Za-z0-9._-' '_'; }

booted_udid() { xcrun simctl list devices booted | grep -oE '[0-9A-F-]{36}' | head -1; }

cmd_udid() { local u; u=$(booted_udid); [ -n "$u" ] || die "no simulator is booted (run: sim.sh boot)"; echo "$u"; }

# "<udid>|<name>" per available device, so a name can be matched as a WHOLE name.
device_rows() {
  xcrun simctl list devices available \
    | sed -nE 's/^[[:space:]]*(.+) \(([0-9A-F-]{36})\) \((Booted|Shutdown)\).*$/\2|\1/p'
}

# Logical width (points) per iPhone class. The reference screenshot's device class decides
# this — compare_regions.py refuses a 402pt render against a 393pt reference, and rightly so.
# The table is a convenience; `capture --logical-width` VERIFIES against the real screenshot,
# which is what actually protects you if a row here is wrong or a new device ships.
logical_width_of() {
  case "$1" in
    # ORDER MATTERS — first match wins, so the "e" models must precede the bare number, or
    # "iPhone 17e" is swallowed by the *"iPhone 17"* pattern and reported as 402pt.
    *"iPhone 16e"*|*"iPhone 17e"*)                              echo 390;;
    *"iPhone 16 Pro Max"*|*"iPhone 17 Pro Max"*)                echo 440;;
    *"iPhone 16 Pro"*|*"iPhone 17 Pro"*|*"iPhone 17"*)          echo 402;;
    *"iPhone 16 Plus"*|*"iPhone 15 Plus"*|*"iPhone 15 Pro Max"*|*"iPhone 14 Pro Max"*) echo 430;;
    *"iPhone 14 Plus"*|*"iPhone 13 Pro Max"*|*"iPhone 12 Pro Max"*) echo 428;;
    *"iPhone Air"*)                                             echo 420;;
    *"iPhone 14"*|*"iPhone 13 Pro"*|*"iPhone 13"*|*"iPhone 12 Pro"*|*"iPhone 12"*) echo 390;;
    *"iPhone 16"*|*"iPhone 15 Pro"*|*"iPhone 15"*|*"iPhone 14 Pro"*) echo 393;;
    *"iPhone 11 Pro Max"*|*"iPhone XS Max"*|*"iPhone 11"*|*"iPhone XR"*) echo 414;;
    *"iPhone SE"*|*"iPhone 13 mini"*|*"iPhone 12 mini"*|*"iPhone X"*) echo 375;;
    *) echo "";;
  esac
}

cmd_devices() {
  local want="${1:-}"
  echo "logical  device                                    udid"
  device_rows | while IFS='|' read -r u n; do
    [ "${n#iPhone}" = "$n" ] && continue
    w=$(logical_width_of "$n")
    [ -n "$want" ] && [ "$w" != "$want" ] && continue
    printf "%-8s %-42s %s\n" "${w:-?}pt" "$n" "$u"
  done
}

resolve_by_width() {
  local want="$1" line
  line=$(device_rows | while IFS='|' read -r u n; do
    [ "${n#iPhone}" = "$n" ] && continue
    [ "$(logical_width_of "$n")" = "$want" ] && echo "$u|$n"
  done | head -1)
  [ -n "$line" ] || die "no available iPhone simulator is ${want}pt wide. Choose from:
$(cmd_devices)
  Match the REFERENCE screenshot's device class — its logical width is printed by
  'python3 scripts/measure_region.py scale <reference.png>'."
  echo "using $(echo "$line" | cut -d'|' -f2) for ${want}pt" >&2
  echo "$line" | cut -d'|' -f1
}

resolve_device() {
  # Exact name wins over substring. `grep -i "iPhone 17"` matched "iPhone 17 Pro" first and
  # returned it — the caller silently got a different device than the one they named, which
  # is precisely the wrong-device failure the comment below describes. A UDID is accepted
  # verbatim. An ambiguous substring is reported with the candidates rather than guessed at.
  local want="$1" rows exact subs
  rows=$(device_rows)
  if printf '%s' "$want" | grep -qE '^[0-9A-Fa-f-]{36}$'; then
    printf '%s\n' "$rows" | grep -qi "^$want|" || die "no available simulator with udid '$want'"
    printf '%s' "$want" | tr 'a-f' 'A-F'; return
  fi
  exact=$(printf '%s\n' "$rows" | awk -F'|' -v w="$want" 'tolower($2)==tolower(w){print $1}')
  if [ -n "$exact" ]; then printf '%s\n' "$exact" | head -1; return; fi
  subs=$(printf '%s\n' "$rows" | awk -F'|' -v w="$want" 'index(tolower($2),tolower(w)){print}')
  [ -n "$subs" ] || die "no available simulator matched '$want' — run: xcrun simctl list devices available"
  if [ "$(printf '%s\n' "$subs" | wc -l | tr -d ' ')" -gt 1 ]; then
    { echo "'$want' matched more than one device; using the first. Name it exactly to pin one:"
      printf '%s\n' "$subs" | awk -F'|' '{print "  " $2 "  (" $1 ")"}'; } >&2
  fi
  printf '%s\n' "$subs" | head -1 | cut -d'|' -f1
}

wait_booted() {
  local u="$1" i
  for i in $(seq 1 60); do
    xcrun simctl list devices booted | grep -q "$u" && return 0
    sleep 1
  done
  return 1
}

cmd_boot() {
  local want="${1:-}" udid
  if [ "$want" = "--logical-width" ]; then
    want=$(resolve_by_width "${2:?logical width in points}") || exit 1
  fi
  # An explicit --device/name MUST win over whatever happens to be booted. Reusing the
  # first booted simulator ignored the caller's choice, landed on a pre-existing iPhone
  # that never had the app installed, and every launch failed with
  # FBSOpenApplicationServiceErrorDomain code=4 — which reads like a crash, not a
  # wrong-device error. A real run had to abandon `capture` and drive the granular
  # subcommands by hand because of this.
  if [ -n "$want" ]; then
    udid=$(resolve_device "$want") || exit 1
    if ! xcrun simctl list devices booted | grep -q "$udid"; then
      xcrun simctl boot "$udid" >/dev/null 2>&1
      open -a Simulator
      # WAIT for the boot to finish. `simctl privacy` (which prep runs next) silently
      # no-ops on a device that is still booting, and prep then writes its marker anyway —
      # so the photo permission was never revoked, on this run or any later one.
      wait_booted "$udid" || die "$udid never reached Booted state"
    fi
    echo "$udid"
    return
  fi
  # More than one booted simulator and no choice from the caller is not a default, it is a
  # coin toss. A real run captured on whichever device happened to be first and said so
  # afterwards: "the first capture happened to land on the iPhone 17, but it was luck."
  local n; n=$(xcrun simctl list devices booted | grep -cE '\([0-9A-F-]{36}\)')
  if [ "$n" -gt 1 ]; then
    die "$n simulators are booted and no --device was given — refusing to guess which one to shoot:
$(xcrun simctl list devices booted | grep -E '\([0-9A-F-]{36}\)' | sed 's/^ */  /')
  Pin one:  --device '<name>'   or   --logical-width <pt of the reference>"
  fi
  udid=$(booted_udid)
  if [ -n "$udid" ]; then echo "$udid"; echo "(reusing already-booted device; pass --device <name> to pin a specific one)" >&2; return; fi
  udid=$(device_rows | awk -F'|' '$2 ~ /^iPhone (1[5-9]|[2-9][0-9])/{print $1}' | head -1)
  [ -n "$udid" ] || die "no available iPhone simulator found"
  xcrun simctl boot "$udid" >/dev/null 2>&1
  open -a Simulator
  wait_booted "$udid" || die "$udid never reached Booted state"
  echo "$udid"
}

cmd_prep() {
  local u="${1:?udid}" b="${2:?bundleId}" force="${3:-}"
  local marker="$STATE_DIR/prepped-$(key "$u")-$(key "$b")"
  if [ -f "$marker" ] && [ -z "$force" ]; then echo "already prepped (marker $marker)"; return; fi
  # `simctl privacy` is a no-op for a bundle id that is not installed yet. Writing the
  # marker anyway meant the FIRST capture (before the native build) permanently marked the
  # app as prepped, so photos were never actually revoked and the untappable SpringBoard
  # alert came back on every later run. No install -> no marker.
  if ! xcrun simctl get_app_container "$u" "$b" >/dev/null 2>&1; then
    echo "prep skipped: $b is not installed on $u yet (build first; prep re-runs after)"
    return
  fi
  xcrun simctl terminate "$u" "$b" >/dev/null 2>&1
  xcrun simctl privacy "$u" revoke photos "$b" >/dev/null 2>&1 \
    && echo "photos: REVOKED (in-app 'not granted' panel instead of an untappable alert)"
  xcrun simctl privacy "$u" grant microphone "$b" >/dev/null 2>&1 \
    && echo "microphone: granted (expo-audio cannot start the recorder without it)"
  xcrun simctl spawn "$u" defaults write "$b" EXDevMenuIsOnboardingFinished -bool YES >/dev/null 2>&1 \
    && echo "expo dev-menu onboarding: dismissed"
  : > "$marker"
}

metro_up() { lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

# Listening is not the same as serving. Metro binds the port seconds before it can answer a
# bundle request, and `/status` (which replies `packager-status:running`) is the first moment
# it can. Launching into the gap is not harmless: the dev client fails to fetch, falls back
# to the LAUNCHER MENU, and that menu is a stable non-splash frame — so the settle check
# passes and you get a green capture of the wrong screen. That happened on the first
# --port run of this script.
metro_serving() { curl -sf --max-time 2 "http://127.0.0.1:$1/status" 2>/dev/null | grep -q 'packager-status:running'; }

wait_metro() {
  local port="$1" i
  for i in $(seq 1 "${METRO_TIMEOUT:-90}"); do
    metro_serving "$port" && { [ "$i" -ge 3 ] && echo "metro serving after ${i}s" >&2; return 0; }
    sleep 1
  done
  return 1
}

cmd_metro() {
  local lane="${1:?expo|cli}" dir="${2:?abs-project-dir}"; shift 2
  local port=8081
  while [ $# -gt 0 ]; do case "$1" in --port) port="$2"; shift 2;; *) die "unknown flag $1";; esac; done
  [ -d "$dir" ] || die "not a directory: $dir"
  local log="$STATE_DIR/metro-$(key "$(basename "$dir")")-${port}.log"
  if metro_up "$port"; then
    # DO NOT kill a dev server you did not start — two real runs silently killed a
    # sibling project's server to honour a pinned port and had to disclose it after.
    if ! metro_serving "$port"; then
      die "port $port is held by something that does not answer Metro's /status.
  Either it is still starting (re-run in a few seconds) or it is not Metro at all:
    lsof -nP -iTCP:${port} -sTCP:LISTEN
  Do NOT kill a server you did not start — pick a free port with --port instead."
    fi
    echo "metro already listening on $port (reusing) log=$log"
    echo "$log" > "$STATE_DIR/metrolog-${port}"
    return
  fi
  # No --clear. It wipes the Metro transform cache on EVERY start, so the first bundle
  # after each start is a full cold build (1–2 min on an SDK-sized app) — which is what
  # actually blew the settle budget and made the first capture of a run fail. Nothing here
  # needs it: `shot` terminates and relaunches the app, so the bundle is re-requested
  # anyway, and Metro invalidates on file change by itself. Clear it by hand on the rare
  # transformer/babel-config change: npx expo start --clear.
  ( cd "$dir" || exit 1
    if [ "$lane" = "expo" ]; then npx expo start --dev-client --port "$port" > "$log" 2>&1 &
    else npx react-native start --port "$port" > "$log" 2>&1 & fi
    echo "$!" > "$STATE_DIR/metropid-${port}" )
  echo "$log" > "$STATE_DIR/metrolog-${port}"
  # Block until it can actually serve — see metro_serving above.
  wait_metro "$port" || die "metro never became ready on port $port within ${METRO_TIMEOUT:-90}s. Read $log"
  echo "metro started log=$log port=$port"
}

cmd_shot() {
  local u="${1:?udid}" b="${2:?bundleId}" out="${3:?out.png}"; shift 3
  local lane=expo port=8081 log="" gate=1
  while [ $# -gt 0 ]; do
    case "$1" in
      --lane) lane="$2"; shift 2;;
      --port) port="$2"; shift 2;;
      --log)  log="$2";  shift 2;;
      --no-bundle-gate) gate=0; shift;;
      *) die "unknown flag $1";;
    esac
  done
  [ -e "$out" ] && die "$out exists — use a fresh <screen>-<state>-<attempt>.png; overwriting a capture can be unrecoverable"
  [ -n "$log" ] || log=$(cat "$STATE_DIR/metrolog-${port}" 2>/dev/null || echo "")

  local mark=0
  [ -n "$log" ] && [ -f "$log" ] && mark=$(wc -l < "$log")

  # Ensure the device is actually booted. A udid that was booted earlier can be in
  # "Shutdown" by the time you launch, and `simctl launch` then fails with the opaque
  # "Unable to lookup in current state: Shutdown". Five real failures were this.
  if ! xcrun simctl list devices booted | grep -q "$u"; then
    echo "device $u is not booted — booting it" >&2
    xcrun simctl boot "$u" >/dev/null 2>&1
    for _ in $(seq 1 20); do
      xcrun simctl list devices booted | grep -q "$u" && break
      sleep 1
    done
  fi
  # And the app has to be installed, or launch fails with FBSOpenApplicationServiceError
  # code=4 ("failed to launch"), which reads like a crash rather than "never installed".
  if ! xcrun simctl get_app_container "$u" "$b" >/dev/null 2>&1; then
    die "$b is not installed on $u — run the native build first (scripts/gate.sh <dir> npx expo run:ios --device $u); this is not a launch crash"
  fi

  xcrun simctl terminate "$u" "$b" >/dev/null 2>&1
  launch() {
    if [ "$lane" = "expo" ]; then
      # --initialUrl is the ONE reliable tap-free launch: a bare launch opens the
      # dev-launcher menu, and `simctl openurl` fires an untappable "Open in ...?" alert
      # that survives terminate. Plain http:// only — the exp+scheme:// form re-triggers it.
      xcrun simctl launch "$u" "$b" --initialUrl "http://localhost:${port}" >/dev/null 2>&1
    else
      xcrun simctl launch "$u" "$b" >/dev/null 2>&1
    fi
  }
  if ! launch; then
    # One retry after a settle: a device that just booted can refuse the first launch.
    sleep 3
    if ! launch; then
      die "launch failed twice for $b on $u. Check: is Metro up on port ${port} (scripts/sim.sh metro), and did the native build install this bundle id?"
    fi
  fi

  local splash="$STATE_DIR/splash-$$.png"
  xcrun simctl io "$u" screenshot "$splash" >/dev/null 2>&1   # this frame IS the splash reference

  # Stage A: wait for THIS relaunch's bundle. Unlike Stage B below, this is a compile whose
  # duration is genuinely variable — a cold Metro cache builds for 1–2 minutes on an
  # SDK-sized app. A 20s cap here did not surface a defect, it just fell through to Stage B
  # while the bundler was still working, so the first capture of every run failed with
  # "no settled frame" and sent the reader off diagnosing ports and modals. Waiting longer
  # is free when the bundle is fast: the loop breaks the moment the line appears.
  if [ -n "$log" ] && [ -f "$log" ] && [ "$gate" -eq 1 ]; then
    local waited=0 bundled=0
    for waited in $(seq 1 "$BUNDLE_TIMEOUT"); do
      if tail -n "+$((mark+1))" "$log" | grep -qE 'iOS Bundled|metro:bundling:done'; then
        bundled=1; break
      fi
      [ "$waited" = 20 ] && echo "still bundling (a cold Metro cache builds for 1-2 min)..." >&2
      sleep 1
    done
    # A missing bundle line is TERMINAL, not something to fall through. If this relaunch
    # never bundled, the app is not showing your JS — and the dev-launcher menu it falls
    # back to is a stable, non-splash frame, so Stage B below would "settle" on it and
    # report a green capture of the launcher. A real --port run did exactly that.
    if [ "$bundled" -ne 1 ]; then
      rm -f "$out"
      die "no bundle was served on port ${port} in ${BUNDLE_TIMEOUT}s — this app never loaded your JS.
  Do NOT trust or re-shoot; the frame on screen is most likely the expo dev-launcher menu.
  Check, in order:
    * is Metro on ${port} the one for THIS project?   tail ${log}
    * did the launch target the same port?           --port must match on capture and metro
    * is another dev server answering ${port}?       lsof -nP -iTCP:${port} -sTCP:LISTEN
  (RN CLI lane serves no 'iOS Bundled' line on a cached launch — pass --no-bundle-gate.)"
    fi
    [ "$waited" -ge 5 ] && echo "bundle ready after ${waited}s" >&2
  fi

  local sh ph="" h ok=0 i                                      # Stage B: leave splash, then settle
  sh=$(md5of "$splash")
  for i in $(seq 1 25); do
    xcrun simctl io "$u" screenshot "$out" >/dev/null 2>&1
    h=$(md5of "$out")
    if [ "$h" = "$sh" ]; then ph=""; sleep 1; continue; fi
    if [ "$h" = "$ph" ]; then ok=1; echo "settled in ${i}s"; break; fi
    ph="$h"; sleep 1
  done
  rm -f "$splash"

  if [ $ok -ne 1 ]; then
    rm -f "$out"          # a splash frame left behind looks exactly like a real capture
    cat >&2 <<MSG
NOT READY — no settled frame. Deleted the output; do NOT raise the cap and re-shoot.
It is one of:
  * stale bundle / dev server on the wrong port  -> SIMULATOR-VERIFICATION.md §2
  * blocking modal surviving terminate           -> bash scripts/sim.sh reboot $u
  * the client genuinely never connects          -> read ${log:-the Metro log} and the app's output
MSG
    exit 1
  fi
  echo "$out"
}

cmd_capture() {
  local b="${1:?bundleId}" out="${2:?out.png}"; shift 2
  local dir="" lane=expo port=8081 device="" nometro="" gate="" lw=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --logical-width) lw="$2"; shift 2;;
      --project) dir="$2"; shift 2;;
      --lane) lane="$2"; shift 2;;
      --port) port="$2"; shift 2;;
      --device) device="$2"; shift 2;;
      --no-metro) nometro=1; shift;;
      --no-bundle-gate) gate="--no-bundle-gate"; shift;;
      *) die "unknown flag $1";;
    esac
  done
  local u
  # Do NOT swallow stderr here: it hides `resolve_device`'s "no available simulator matched
  # 'X'" behind a generic "could not boot", which sends you looking at the wrong thing.
  # cmd_boot writes only the udid to stdout; its notes already go to stderr.
  if [ -z "$device" ] && [ -n "$lw" ]; then device="--logical-width|$lw"; fi
  if [ "${device%%|*}" = "--logical-width" ]; then
    u=$(cmd_boot --logical-width "${device##*|}") || exit 1
  else
    u=$(cmd_boot "$device") || exit 1
  fi
  u=$(printf '%s\n' "$u" | head -1)
  [ -n "$u" ] || die "could not boot or find a simulator"
  cmd_prep "$u" "$b" >/dev/null
  if [ -z "$nometro" ]; then
    if [ -n "$dir" ]; then cmd_metro "$lane" "$dir" --port "$port" >/dev/null
    elif ! metro_up "$port"; then
      die "nothing is listening on port $port and no --project given to start Metro"
    fi
  fi
  echo "device: $(device_rows | awk -F'|' -v u="$u" '$1==u{print $2}') ($u)" >&2
  cmd_shot "$u" "$b" "$out" --lane "$lane" --port "$port" ${gate:+$gate} || exit 1

  # VERIFY the device class against the real screenshot, not against the name table above.
  # A reference is a fixed device class; shooting a 402pt render for a 393pt reference makes
  # every size comparison invalid, and compare_regions.py will (correctly) refuse it — better
  # to find out here than after the build.
  if [ -n "$lw" ] && command -v sips >/dev/null 2>&1; then
    local pw got=""
    pw=$(sips -g pixelWidth "$out" 2>/dev/null | awk '/pixelWidth/{print $2}')
    for sc in 3 2 1; do [ -n "$pw" ] && [ "$((lw * sc))" = "$pw" ] && got=$lw; done
    if [ -z "$got" ]; then
      rm -f "$out"
      die "wrong device class: asked for ${lw}pt but the capture is ${pw}px wide (not ${lw}x2 or ${lw}x3).
  The name->width table picked the wrong device. Pick one explicitly:
$(cmd_devices)"
    fi
    echo "device class verified: ${pw}px = ${lw}pt" >&2
  fi
}

# Mean luminance of a screenshot, 0-255, using only macOS built-ins (sips resamples the
# whole image to one averaged pixel; xxd reads it back). Prints nothing if unavailable.
luma_of() {
  local img="$1" tmp="$STATE_DIR/luma-$$.bmp" off px b g r
  command -v sips >/dev/null 2>&1 && command -v xxd >/dev/null 2>&1 || return 1
  sips -s format bmp -z 1 1 "$img" --out "$tmp" >/dev/null 2>&1 || { rm -f "$tmp"; return 1; }
  # The pixel-data offset is a little-endian u32 at byte 10. It is NOT the textbook 54:
  # sips emits a BITMAPV4/V5 header (138 here), and assuming 54 reads header bytes as a
  # colour — which silently yields a constant, meaningless "luminance".
  off=$(xxd -s 10 -l 4 -p "$tmp" 2>/dev/null | sed 's/\(..\)\(..\)\(..\)\(..\)/0x\4\3\2\1/')
  [ -n "$off" ] || { rm -f "$tmp"; return 1; }
  px=$(xxd -s $((off)) -l 3 -p "$tmp" 2>/dev/null); rm -f "$tmp"
  [ ${#px} -eq 6 ] || return 1
  b=$((16#${px:0:2})); g=$((16#${px:2:2})); r=$((16#${px:4:2}))
  echo $(( (r*299 + g*587 + b*114) / 1000 ))
}

cmd_appearance() {
  local u="${1:?udid}" mode="${2:?light|dark}" out="${3:?out.png}"
  # Only works when the app reads useColorScheme(). If dark mode is driven by app state
  # (a persisted toggle in MMKV/AsyncStorage/a theme context — common in migrated apps),
  # this is a NO-OP: drive the app's own flag instead.
  [ -e "$out" ] && die "$out exists — use a fresh filename"
  local before="$STATE_DIR/appear-$$.png" ph="" h ok=0 i bh
  xcrun simctl io "$u" screenshot "$before" >/dev/null 2>&1
  bh=$(md5of "$before")
  local lb; lb=$(luma_of "$before")
  xcrun simctl ui "$u" appearance "$mode" >/dev/null 2>&1 || die "appearance $mode failed"
  for i in $(seq 1 15); do
    xcrun simctl io "$u" screenshot "$out" >/dev/null 2>&1
    h=$(md5of "$out")
    if [ "$h" = "$bh" ]; then ph=""; sleep 1; continue; fi
    if [ "$h" = "$ph" ]; then ok=1; break; fi
    ph="$h"; sleep 1
  done
  rm -f "$before"
  [ $ok -eq 1 ] || { rm -f "$out"; die "the frame never changed — the app likely drives dark mode from app state, not useColorScheme(); flip its own persisted flag instead"; }

  # "The frame changed" is NOT evidence the flip landed. Transient chrome changes it too:
  # this check passed on an app whose dark mode is MMKV-driven, because the Expo dev-menu
  # bubble happened to collapse between the two shots — so it returned a LIGHT screenshot
  # named dark.png, exit 0. Require the brightness to actually move, and in the right
  # direction (a real light->dark flip moves mean luma by ~200, chrome by ~1).
  local la; la=$(luma_of "$out")
  if [ -n "$lb" ] && [ -n "$la" ]; then
    local moved=0
    [ "$mode" = dark ]  && [ $((lb - la)) -ge 25 ] && moved=1
    [ "$mode" = light ] && [ $((la - lb)) -ge 25 ] && moved=1
    if [ $moved -ne 1 ]; then
      rm -f "$out"
      die "the appearance flip did NOT reach the app (mean luminance $lb -> $la, mode=$mode).
  Something in the frame changed, but the UI is still $([ "$mode" = dark ] && echo light || echo dark).
  This app almost certainly drives dark mode from APP STATE (a persisted toggle in
  MMKV/AsyncStorage/a theme context), where 'simctl ui appearance' is a no-op.
  Drive the app's own flag instead — see SIMULATOR-VERIFICATION.md §6."
    fi
    echo "luminance $lb -> $la" >&2
  fi
  echo "$out"
}

cmd_reboot() {
  local u="${1:?udid}"                 # the only tap-free recovery from a SpringBoard modal
  xcrun simctl shutdown "$u" >/dev/null 2>&1
  xcrun simctl boot "$u" >/dev/null 2>&1
  rm -f "$STATE_DIR"/prepped-"$(key "$u")"-*
  echo "rebooted $u"
}

case "${1:-}" in
  capture)    shift; cmd_capture "$@";;
  devices)    shift; cmd_devices "$@";;
  boot)       shift; cmd_boot "$@";;
  udid)       shift; cmd_udid "$@";;
  prep)       shift; cmd_prep "$@";;
  metro)      shift; cmd_metro "$@";;
  shot)       shift; cmd_shot "$@";;
  appearance) shift; cmd_appearance "$@";;
  reboot)     shift; cmd_reboot "$@";;
  *) sed -n '2,20p' "$0"; exit 2;;
esac
