# Scripts — run these, don't re-derive them

Every script here replaces a procedure that used to be prose. Prose gets re-improvised each
run, which costs output tokens and varies between runs; these are deterministic and cheap.
**Execute them — do not read them into context** unless you need to change one.

## Batch, or the scripts cost more than they save

**Each tool call re-reads the whole conversation, so turn count — not file size — is what
drives cost and latency.** A measured pair of migration runs regressed 30–42% in turns
(and ~30% in wall-clock) mostly by calling these scripts one region and one step at a time.
So:

- **One `sim.sh capture` per screen *state*** — not per region. Compare every region of
  that state from the same PNG.
- **One `compare_regions.py` call for all regions of a state** — pass `--r` repeatedly. It emits
  ONE labelled contact sheet, so that is one image read, not one per region.
- **One `check_analysis.py` call** — it reports advisory warnings without failing, so
  it converges in a single run instead of a fix-and-retry loop.

`measure_region.py`, `compare_regions.py` and `region_metrics.py` need Pillow + numpy.
Check up front, before you start capturing — a tool missing mid-verify is a silent reason
the measurement gets skipped:

```bash
python3 -c "import PIL, numpy" \
  || (python3 -m venv .designvenv && .designvenv/bin/pip install Pillow numpy)
# then call .designvenv/bin/python3 instead of python3
```

| Script | Use it for | Replaces |
|---|---|---|
| `probe.sh <dir>` | project signals: lane, package manager, Expo SDK, New Arch, Stream/Sendbird packages, **and asserted peer hazards** | the inline `bash -c` probe |
| `gate.sh <abs-dir> <cmd...>` | running any verification command so its **real** exit status is reported | the never-pipe / absolute-`cd` warnings |
| `sim.sh capture` | **one call** = boot/reuse device · prep permissions · start/reuse Metro **and wait until it serves** · terminate · launch · **gate on the bundle** · **poll-for-settle** · save | the whole simulator bash block |
| `compare_regions.py` | N regions, reference vs render, **self-locating**: numeric verdict tables **with the fix for each failing metric** + **one** labelled contact sheet | image-only region diffs |
| `measure_region.py` | scale, input-field size, glyph boxes, sampled colours, flat-vs-texture, stroke→`fontWeight` | eyeballing round numbers |
| `region_metrics.py` | *not a CLI* — the shared detectors the two Python tools both import | two copies that silently diverged |
| `check_analysis.py` | validating `design-analysis.md`: terminal verdicts (blocking) + spec/plan/evidence (advisory) | the forbidden-phrase lists |
| `cleanup.sh <abs-dir>` | removing the run's artifacts from the **project**: capture folders, `design-analysis.md`, contact sheets, `.designvenv`. Dry-run by default | one prose line about one file |

## Before the native build: match the device class and check the colour space

Two properties of the REFERENCE decide the whole loop, and both are expensive to discover late:

```bash
python3 scripts/measure_region.py scale <reference.png>
#  -> "logical_width": 393          the simulator you must pin
#  -> "source_profile": "Display P3"  a real-device screenshot; captures are sRGB
bash scripts/sim.sh devices 393     # which simulators are that class
```

- **Device class.** A 402pt render cannot be compared 1:1 to a 393pt reference, and
  `compare_regions.py` refuses the pair. Pin it *before* the native build —
  `sim.sh boot --logical-width 393`, and `capture --logical-width 393` verifies the real
  screenshot afterwards. One real run built on an iPhone 17 against a 393pt reference and
  had to hand-roll every measurement the scripts exist to provide.
- **Colour space.** References off a real iPhone carry **Display P3**; simulator captures are
  sRGB. The same paint reads as different numbers (`#E0FCD6` P3 = `#D9FDD3` sRGB — a delta of
  7 against a default tolerance of 6), so every colour verdict flips on colour space alone.
  Both Python tools now convert to sRGB on load and say so; the numbers they print are sRGB.

## The design-match loop

```bash
bash scripts/probe.sh "$P"                                   # once
bash scripts/gate.sh "$P" npx expo run:ios --device "$(bash scripts/sim.sh boot --logical-width 393)"

# implement ALL differing regions, THEN capture — one call per screen state
bash scripts/sim.sh capture "$BUNDLE" chat-atrest-1.png --project "$P" --lane expo --logical-width 393

# every region of that state, one call, no coordinates needed
python3 scripts/compare_regions.py ref-atrest.png chat-atrest-1.png \
    --r composer --r header --r row-out:1180 --r row-in:1320

python3 scripts/check_analysis.py "$P/design-analysis.md" --require-evidence

# at the very end — these artifacts live in the USER'S project, so this is not optional
bash scripts/cleanup.sh "$P"          # dry run: shows what it would remove
bash scripts/cleanup.sh "$P" --yes
```

`compare_regions.py` self-locates `composer` and `header` in **both** images. For any other
region give a reference y (`name:1180`) and the matching band in your render is found by
row-profile alignment — you do not need to measure your own screenshot first. Evidence paths
in `check_analysis.py` resolve relative to the analysis file, so it works from any cwd.

**When it says AUTO-LOCATION FAILED, give it the y — do not argue with it.** It refuses when
the two images' located bands disagree, or when the geometry it measured is absurd (a pill
inset a third of the screen, glyphs under 8pt). Both mean the crops are not the same region,
and a table built from them is one you will have to throw away — a real run published a "10pt
input pill" that direct measurement put at 30pt. Pass `--r 'composer:<refY>'`, or
`'composer:<refY>:<mineY>'` for a floating/translucent composer over a wallpaper, where no
colour-step anchor exists.

Read the numbers and the `fix:` lines first — each failing metric names the knob and the
amount. Open the contact sheet **once** for what numbers cannot judge: overall balance,
glyph identity, texture, material/glass. If a metric reports `-`/`n/a`, that element was not
measured (no pill in the region, or a dark surface needing a higher `--dark`); treat it as
unmeasured, not as passing.

## Three ways `sim.sh` refuses to hand you a screenshot it can't stand behind

Each of these was a green capture of the wrong screen before it was a check:

- **Metro must be *serving*, not merely listening.** Metro binds the port seconds before it
  can answer a bundle request. Launching into that gap makes the dev client fall back to the
  **expo-dev-launcher menu** — a stable, non-splash frame that the settle check happily
  accepts. `capture --port 8099` returned a screenshot of that menu, exit 0.
- **The relaunch must actually bundle.** If no `iOS Bundled` line appears for this launch,
  the app is not running your JS and the capture is refused. (RN CLI on a cached launch may
  not print one — then pass `--no-bundle-gate`.)
- **`appearance` must move the pixels.** "The frame changed" is not evidence the flip landed:
  it passed on an MMKV-driven dark mode because the dev-menu bubble collapsed between shots,
  returning a *light* screenshot named `dark.png`. It now requires mean luminance to move
  ≥25 in the right direction, and names app-state-driven theming when it doesn't.

`capture` cannot tap. To reach a screen behind the first one, drive navigation from
**temporary in-code scaffold** and delete it afterwards — SIMULATOR-VERIFICATION.md §3.
