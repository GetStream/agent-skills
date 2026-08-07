#!/usr/bin/env python3
"""Compare full-width regions of a reference against the same regions of your render.

    # auto-locate the region in BOTH images — no coordinates needed
    python3 scripts/compare_regions.py ref.png mine.png --r composer --r header

    # several regions in ONE call; give a y only for the reference, mine is auto-aligned
    python3 scripts/compare_regions.py ref.png mine.png --r composer --r row-out:1180 --r header

    # fully explicit when you already know both
    python3 scripts/compare_regions.py ref.png mine.png --r bubble:1100:1140:260

Each `--r` is `name`, `name:refY`, `name:refY:mineY`, or `name:refY:mineY:height`.
`composer` and `header` self-locate in both images. With only `refY`, the matching
band in your render is found by row-profile alignment. Run every region you need in
ONE invocation — each prints its own table, all share one contact sheet, and the process
exits 1 if any region fails.

Prints a NUMERIC verdict table — surface colour, input-pill height / width / inset /
top-offset, per-glyph size / ink ratio / centring — and **every failing metric carries the
edit that closes it**. One labelled contact sheet is written for all regions in the call.

Read the numbers and the fixes first; open the sheet once for what numbers cannot judge:
overall balance, glyph identity, texture, material/glass.

Design note, learned the hard way: metrics must be NAMED and MAPPABLE. An earlier version
reported anonymous "ink band 3 top: off by -17.0pt" deltas, which correspond to no theme
key. Two real runs received that verdict twice, 51 turns apart, could do nothing with it,
and abandoned this tool for hand-rolled measurement. Placement is now reported as a
described note rather than a failing metric.

Two rules it encodes:
  * Crop FULL-WIDTH at native resolution, same device class. A crop framed on the
    sub-element you built verifies its CONTENTS and hides its POSITION — a real run
    cropped reactions in isolation, saw "emoji + count + add-button" on both sides,
    and missed that the source renders them INSIDE the bubble while it had built
    them BELOW. Same scale means no resizing, so sizes compare 1:1.
  * Numbers alone lie. A glyph box can match within a pixel while the field is too
    tall, a stroke too heavy, a glyph filled instead of outlined, or a control
    off-centre — hence ink ratio and centring are reported, and the stack still exists.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Detectors live in region_metrics so measure_region.py runs the SAME ones. They used to be
# duplicated here, and the copies diverged — see region_metrics.py's docstring.
from region_metrics import Image, glyphs, hexof, infer_scale, load, modal_bg, np, pill_band  # noqa: E402


# ---------- metrics ----------

def ink_bands(arr, tol, min_rows):
    """Contiguous row ranges departing from the modal background.

    The numeric proxy for PLACEMENT: band count and offsets answer 'reactions inside
    vs below the bubble', 'metadata inside/beside/below', 'send-mic inside vs outside
    the pill' without a vision pass.
    """
    bg = modal_bg(arr)
    rows = (np.abs(arr.astype(int) - bg).sum(2) > tol).sum(1)
    active = rows > max(min_rows, arr.shape[1] * 0.01)
    bands, start = [], None
    for i, on in enumerate(active):
        if on and start is None:
            start = i
        elif not on and start is not None:
            bands.append((start, i - 1)); start = None
    if start is not None:
        bands.append((start, len(active) - 1))
    return bands, bg


def wide_light_rows(g, white, min_frac):
    """Row indices whose longest near-white run covers min_frac of the width."""
    W = g.shape[1]
    thresh = W * min_frac
    light = g > white
    out = []
    for y in range(g.shape[0]):
        row = light[y]
        if row.sum() < thresh:            # cheap reject before the run scan
            continue
        best = cur = 0
        for v in row:
            cur = cur + 1 if v else 0
            if cur > best:
                best = cur
        if best > thresh:
            out.append(y)
    return out


# ---------- region location ----------

def locate(im, name, scale, white=248):
    """Find a named region in ONE image. Returns (y, h) or None."""
    arr = np.asarray(im).astype(int)
    H, W = arr.shape[:2]
    g = arr.mean(2)
    if name.startswith("composer"):
        # ANCHOR ON THE PILL, not on a row-colour scan. The scan below tests each row's outer
        # margins, which breaks the moment a control reaches into them: WhatsApp's mic FAB
        # sits 29px from the right edge inside a 47px probe, so the REFERENCE scan stopped
        # 37pt early while the render's ran on — two bands that were not the same region,
        # and every metric computed from them was noise. Pill detection is a colour-step
        # search that does not care where the buttons are, so deriving the band from it
        # applies the same rule to both images and yields comparable crops.
        win = max(0, H - int(620 * scale / 3))
        f = pill_band(arr[win:H], prefer="lowest")
        if f is not None:
            pad = int(round(0.75 * f["height"]))
            top = max(0, win + f["top"] - pad)
            return top, H - top
        band = int(560 * scale / 3)
        y0 = max(0, H - band)
        strip = arr[y0:H]
        base = modal_bg(strip[int(strip.shape[0] * 0.75):])   # colour near the very bottom
        # Test the row's OUTER MARGINS, not the whole row: the bar runs full width while an
        # inset pill occupies the middle, so a whole-row test stops the scan at the pill and
        # truncates the crop (it did, on a dark-bar composer).
        edge = max(4, int(W * 0.04))
        top = H
        for y in range(H - 1, y0 - 1, -1):
            row = arr[y].astype(int)
            # Tolerance 6, not 12: a light composer bar (252) and the page background
            # above it (240) differ by exactly 12, so a looser test walks straight through
            # the boundary and swallows the page into the crop.
            lo = (np.abs(row[:edge] - base).max(1) <= 6).mean()
            hi = (np.abs(row[-edge:] - base).max(1) <= 6).mean()
            if lo < 0.6 or hi < 0.6:
                break
            top = y
        if top >= H - int(40 * scale / 3):                   # no bar found; fall back
            rows = wide_light_rows(g[y0:H], white, 0.45)
            if not rows:
                return None
            top = y0 + rows[0] - int(28 * scale / 3)
        return max(0, top), H - max(0, top)
    if name.startswith("header"):
        # Below the status bar, down to the first strong horizontal edge.
        sb = int(50 * scale / 3)
        prof = g[sb:int(sb + 240 * scale / 3)].mean(1)
        d = np.abs(np.diff(prof))
        edge = int(d.argmax()) + sb if len(d) else int(sb + 100 * scale / 3)
        return 0, min(H, edge + int(8 * scale / 3))
    return None


def align(ref_arr, mine_im, ref_y, h, window):
    """Find the y in mine whose row profile best matches the reference crop."""
    m = np.asarray(mine_im).astype(int)
    H = m.shape[0]
    target = ref_arr[ref_y:ref_y + h].mean(2).mean(1)
    if len(target) < h:
        return ref_y
    best, best_y = None, ref_y
    lo, hi = max(0, ref_y - window), min(H - h, ref_y + window)
    for y in range(lo, hi + 1, max(1, (hi - lo) // 240 or 1)):
        cand = m[y:y + h].mean(2).mean(1)
        if len(cand) < h:
            break
        score = float(np.abs(cand - target).mean())
        if best is None or score < best:
            best, best_y = score, y
    return best_y


# ---------- reporting ----------

def correction(metric, delta, s, ref_hex=None):
    """Turn a measured delta into the edit that closes it.

    A verdict the reader cannot act on generates another round instead of a fix. Two real
    runs got 'ink band 3 top: off by -17.0pt' twice, 51 turns apart, and abandoned this
    tool — anonymous band indices map to no theme key. Every failing metric now names the
    knob and the amount.
    """
    d = abs(delta)
    if metric.startswith("surface "):
        return f"set the bar/surface colour to {ref_hex} (`messageComposer.wrapper` + `floatingWrapper` for a composer; NOT `container`, which paints only a band around the controls)"
    if metric == "pill height":
        return (f"{'reduce' if delta > 0 else 'increase'} `messageComposer.inputBox` "
                f"paddingTop AND paddingBottom by ~{d/2:.1f}pt each (symmetric — never a fixed "
                f"minHeight/height on the wrapper, which drops the slack below the text)")
    if metric == "pill top offset":
        return f"{'reduce' if delta > 0 else 'increase'} `messageComposer.wrapper` paddingTop by ~{d:.1f}pt"
    if metric == "pill left inset":
        return (f"{'reduce' if delta > 0 else 'increase'} the leading cluster by ~{d:.1f}pt — "
                f"`MessageComposerLeadingView` button size or `container`/`contentContainer` "
                f"horizontal padding. The pill width is the LEFTOVER, so fix the buttons, not the pill")
    if metric == "pill width":
        return "consequence of the leading/trailing clusters and gaps — fix those, not the pill directly"
    if metric.endswith(" w") or metric.endswith(" h"):
        return f"{'shrink' if delta > 0 else 'grow'} this icon by ~{d:.1f}pt (icon size in its slot, or an `icons` map override — several icon sizes are hardcoded in the SDK and unreachable by theme)"
    if metric.endswith(" ink"):
        return ("fill character differs — swap outlined for filled (or vice versa). A matching box "
                "with a different ink ratio is a different glyph, not a size problem")
    if metric.endswith(" centring"):
        return (f"this control is {d:.1f}pt off the pill's centre — frame the side button to the "
                f"measured pill height and centre within it, rather than tuning one-sided padding")
    return None


def implausible(f, glyph_list, W, s, side):
    """Is this 'pill' a real measurement, or did the crop land in the wrong place?

    A mis-anchored composer crop still yields numbers — a real run got a pill inset 198pt on
    a 393pt screen with glyphs 4-5pt tall, published it as a verdict table, and the reader
    had to re-measure everything by hand. Absurd geometry is a LOCATION failure and must be
    reported as one, not as a design delta the reader is invited to "fix".
    """
    if f is None:
        return None
    if f["x0"] / s > 0.35 * (W / s):
        return (f"{side}: the located pill starts {f['x0']/s:.0f}pt from the left on a "
                f"{W/s:.0f}pt screen — that is not an input field, the crop is mis-anchored")
    if f["height"] / s < 12:
        return (f"{side}: the located pill is only {f['height']/s:.1f}pt tall — a sliver, "
                f"not a field; the crop starts below the real bar")
    tiny = [g for g in glyph_list if g["h"] / s < 8]
    if glyph_list and len(tiny) == len(glyph_list):
        return (f"{side}: every glyph measures under 8pt tall (max {max(g['h'] for g in glyph_list)/s:.1f}pt) "
                f"— the crop caught the edge of the controls, not the controls")
    return None


def compare_one(name, ri, mi, ry, my, h, sr, sm, a, scaled=False):
    rc = ri.crop((0, ry, ri.size[0], min(ri.size[1], ry + h)))
    mc = mi.crop((0, my, mi.size[0], min(mi.size[1], my + h)))
    hh = min(rc.size[1], mc.size[1])
    rc, mc = rc.crop((0, 0, rc.size[0], hh)), mc.crop((0, 0, mc.size[0], hh))
    ra, ma = np.asarray(rc).astype(int), np.asarray(mc).astype(int)

    rbg, mbg = modal_bg(ra), modal_bg(ma)
    ref_hex, mine_hex = hexof(rbg), hexof(mbg)
    rf, mf = pill_band(ra), pill_band(ma)
    rg = glyphs(ra, a.dark, a.gap, int(80 * sr))
    mg = glyphs(ma, a.dark, a.gap, int(80 * sm))

    rows, fails, notes = [], [], []
    # Only a composer CLAIMS to contain an input field, so only there is absurd pill geometry
    # evidence of a mis-anchored crop. A header has no pill at all: pill_band finds a ~10pt
    # divider sliver there, identically on both sides, and treating that as a location
    # failure rejected a pair of IDENTICAL screenshots that passed every other metric.
    bad = [m for m in (implausible(rf, rg, ri.size[0], sr, "reference"),
                       implausible(mf, mg, mi.size[0], sm, "render"))
           if m and name.startswith("composer")]

    def check(label, rv, mv, tol, unit="pt", div=False, integral=False):
        # ONE divisor per side. Across device classes the two images have different scales,
        # and dividing both by the reference's turns a same-size control into a fake delta.
        dr, dm = (sr, sm) if div else (1, 1)
        if rv is None or mv is None:
            if rv is None and mv is None:
                rows.append((label, "-", "-", "-", "n/a")); return
            fails.append((f"{label}: present in only one crop (ref={rv}, mine={mv})",
                          "one side has this element and the other does not — that is a structural "
                          "difference, not a size one"))
            rows.append((label, str(rv), str(mv), "-", "FAIL")); return
        delta = (mv / dm) - (rv / dr)
        ok = abs(delta) <= tol
        f = "{:+.0f}" if integral else "{:+.1f}"
        v = "{:.0f}" if integral else "{:.1f}"
        if not ok:
            fails.append((f"{label}: off by {f.format(delta)}{unit}",
                          correction(label, delta, sr, ref_hex)))
        rows.append((label, v.format(rv / dr) + unit, v.format(mv / dm) + unit,
                     f.format(delta) + unit, "PASS" if ok else "FAIL"))

    def check_pct(label, rv, mv, tol=1.5):
        """A horizontal position as % of screen width — the only cross-class-comparable form."""
        if rv is None or mv is None:
            rows.append((label, "-", "-", "-", "n/a")); return
        rp, mp = 100.0 * rv / ri.size[0], 100.0 * mv / mi.size[0]
        d = mp - rp
        ok = abs(d) <= tol
        if not ok:
            fails.append((f"{label}: off by {d:+.1f}% of screen width",
                          correction(label.replace(" %W", ""), d, sr, ref_hex)))
        rows.append((label, f"{rp:.1f}%", f"{mp:.1f}%", f"{d:+.1f}%", "PASS" if ok else "FAIL"))

    # --- surface
    chan_off = max(abs(int(rbg[i]) - int(mbg[i])) for i in range(3))
    if chan_off > a.tol_rgb:
        fails.append((f"surface colour: {ref_hex} vs {mine_hex} (max channel {chan_off})",
                      correction("surface colour", chan_off, sr, ref_hex)))
    rows.append(("surface colour", ref_hex, mine_hex, f"±{chan_off}",
                 "PASS" if chan_off <= a.tol_rgb else "FAIL"))

    # --- the input pill, measured against the bar rather than by absolute brightness
    check("pill height", rf and rf["height"], mf and mf["height"], a.tol_px, div=True)
    check("pill width", rf and rf["x1"] - rf["x0"], mf and mf["x1"] - mf["x0"], a.tol_px, div=True)
    check("pill left inset", rf and rf["x0"], mf and mf["x0"], a.tol_px, div=True)
    check("pill top offset", rf and rf["top"], mf and mf["top"], a.tol_px, div=True)
    if scaled:
        # Absolute x is not comparable across device classes — a pill 58pt from the left on a
        # 393pt screen and one 58pt in on a 402pt screen are NOT the same design. Judge the
        # proportion instead, and leave the pt rows above as information only.
        check_pct("pill width %W", rf and rf["x1"] - rf["x0"], mf and mf["x1"] - mf["x0"])
        check_pct("pill left inset %W", rf and rf["x0"], mf and mf["x0"])
    if rf and mf and rf.get("pill_hex") and mf.get("pill_hex") and rf["pill_hex"] != mf["pill_hex"]:
        notes.append(f"pill fill {rf['pill_hex']} vs {mf['pill_hex']} — "
                     "`messageComposer.inputBoxWrapper` backgroundColor")

    # --- glyphs
    # Glyph detection assumes dark ink on a lighter surface. On a dark bar the default
    # threshold swallows both, and the honest report is "not measured" — a silent 0 that
    # PASSes is how a whole metric family disappears without anyone noticing.
    if not rg and not mg and rbg.mean() < 90:
        notes.append(f"glyph metrics not measured: this surface is dark ({ref_hex}) and the ink "
                     f"threshold is --dark {a.dark}. Re-run with a higher --dark (e.g. "
                     f"{int(rbg.mean()) + 60}) to measure icons here.")
    check("glyph count", len(rg), len(mg), 0, unit="", integral=True)
    # Once the two sides hold a different NUMBER of controls, glyph N on the left and glyph N
    # on the right are different buttons, so every pairwise delta is noise dressed as a
    # measurement. A real run deliberately dropped the sticker button and then had to discard
    # a full table of glyph verdicts by hand. Say what differs; do not pretend to align them.
    aligned = len(rg) == len(mg)
    if not aligned and (rg or mg):
        notes.append(f"per-glyph rows SUPPRESSED: {len(rg)} control(s) in the reference vs "
                     f"{len(mg)} in yours, so glyph N is a different button on each side. "
                     f"Fix the count first (or compare a state where they match); sizes here "
                     f"cannot be compared pairwise.")
    for i in range(min(len(rg), len(mg)) if aligned else 0):
        check(f"glyph {i+1} w", rg[i]["w"], mg[i]["w"], a.tol_px, div=True)
        check(f"glyph {i+1} h", rg[i]["h"], mg[i]["h"], a.tol_px, div=True)
        d = mg[i]["ink"] - rg[i]["ink"]
        ok = abs(d) <= a.tol_ink
        if not ok:
            fails.append((f"glyph {i+1} ink: {d:+.3f}", correction(f"glyph {i+1} ink", d, s)))
        rows.append((f"glyph {i+1} ink", f"{rg[i]['ink']:.3f}", f"{mg[i]['ink']:.3f}",
                     f"{d:+.3f}", "PASS" if ok else "FAIL"))
        if rf and mf:
            check(f"glyph {i+1} centring",
                  rg[i]["cy"] - (rf["top"] + rf["bottom"]) // 2,
                  mg[i]["cy"] - (mf["top"] + mf["bottom"]) // 2, a.tol_px, div=True)

    # --- placement, as a described observation rather than an anonymous band index.
    # Reported, never failed on: it is a hint about structure, not a spec, and failing on
    # it produced verdicts nobody could act on.
    rb, _ = ink_bands(ra, a.band_tol, 3)
    mb, _ = ink_bands(ma, a.band_tol, 3)
    def describe(bands, H):
        return ", ".join(f"{100*b[0]//max(H,1)}–{100*b[1]//max(H,1)}%" for b in bands) or "none"
    if len(rb) != len(mb):
        notes.append(f"content sits in {len(rb)} band(s) in the reference at {describe(rb, hh)} "
                     f"but {len(mb)} in yours at {describe(mb, hh)} — check whether an element is "
                     f"INSIDE vs BELOW its container (metadata in the bubble, reactions in the "
                     f"bubble, send/mic in the pill). Confirm on the sheet.")
    return rows, fails, notes, (rc, mc), (ry, my, hh), bad


def contact_sheet(entries, path):
    """One labelled sheet for every region in the call — not one PNG per region.

    A run that wrote a file per region then read each one back spent more on images
    than the numeric tables saved. One sheet is one image read.
    """
    try:
        from PIL import ImageDraw
    except ImportError:
        ImageDraw = None
    LABEL, GAP, SEP = 20, 4, 14
    W = max(rc.size[0] for _, (rc, _), _ in entries)
    H = sum(LABEL + rc.size[1] + GAP + mc.size[1] + SEP for _, (rc, mc), _ in entries)
    sheet = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(sheet) if ImageDraw else None
    y = 0
    for name, (rc, mc), verdict in entries:
        if d:
            # ASCII only: the sheet is drawn with PIL's built-in bitmap font, which has no
            # glyph for U+2014 and renders an em-dash as a tofu box in the one label the
            # reader relies on to tell the two crops apart.
            d.text((4, 5), f"{name}  --  top: reference   bottom: mine   [{verdict}]",
                   fill=(255, 220, 90))
        y += LABEL
        sheet.paste(rc, (0, y)); y += rc.size[1] + GAP
        sheet.paste(mc, (0, y)); y += mc.size[1] + SEP
    sheet.save(path)
    return path


def default_out(ref_path, names):
    """Alongside the reference image. Never the cwd, and never inside the skill dir."""
    d = os.path.dirname(os.path.abspath(ref_path)) or os.getcwd()
    skill = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.abspath(d) == skill or os.path.abspath(d).startswith(skill + os.sep):
        sys.exit(f"refusing to write output into the skill directory ({skill}).\n"
                 "Pass --out <path-in-your-project> — keep artifacts with the project, not the skill.")
    stem = "-".join(n.split(":")[0] for n in names)[:60] or "regions"
    return os.path.join(d, f"compare-{stem}.png")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("ref"); p.add_argument("mine")
    p.add_argument("--r", "--region", dest="regions", action="append", required=True,
                   metavar="NAME[:refY[:mineY[:H]]]",
                   help="repeatable. 'composer' and 'header' self-locate; others need at least refY")
    p.add_argument("--h", type=int, default=210, help="default crop height, device px")
    p.add_argument("--scale", default="auto")
    p.add_argument("--out", default=None,
                   help="contact sheet path. Default: alongside the REFERENCE image, never the cwd — "
                        "a '.' default wrote crops into the skill directory in a real run")
    p.add_argument("--align-window", type=int, default=200, help="+/- px searched when mineY is omitted")
    p.add_argument("--white", type=int, default=248)
    p.add_argument("--dark", type=int, default=110)
    p.add_argument("--gap", type=int, default=8)
    p.add_argument("--band-tol", type=int, default=40)
    p.add_argument("--tol-px", type=float, default=1.0, help="size tolerance, logical px")
    p.add_argument("--tol-rgb", type=int, default=6)
    p.add_argument("--tol-ink", type=float, default=0.08)
    p.add_argument("--json", action="store_true")
    p.add_argument("--allow-scale-mismatch", action="store_true",
                   help="compare across device classes in logical pt; x-offsets judged as %% of width")
    p.add_argument("--no-color-manage", action="store_true",
                   help="do NOT convert to sRGB first (a P3 reference vs an sRGB render then lies)")
    a = p.parse_args()

    ri, mi = load(a.ref, manage=not a.no_color_manage), load(a.mine, manage=not a.no_color_manage)
    sr, lwr = infer_scale(ri.size[0])
    sm, lwm = infer_scale(mi.size[0])
    if a.scale not in (None, "auto"):
        sr = sm = float(a.scale)
        lwr, lwm = int(ri.size[0] / sr), int(mi.size[0] / sm)
    if ri.size[0] != mi.size[0] and not a.allow_scale_mismatch:
        sys.exit(
            f"device-class mismatch: reference {ri.size[0]}px (={lwr}pt) vs render "
            f"{mi.size[0]}px (={lwm}pt).\n"
            f"Sizes cannot compare 1:1 across device classes, and resizing invents its own error.\n"
            f"  BEST — rebuild the loop on a matching device (do this before the native build):\n"
            f"      bash scripts/sim.sh boot --logical-width {lwr}\n"
            f"  Or, if you must compare across classes, accept scale-normalised numbers:\n"
            f"      --allow-scale-mismatch   (sizes in pt stay comparable; absolute x-offsets do\n"
            f"                                not, so they are also reported as % of screen width)")
    scaled = ri.size[0] != mi.size[0]
    s = sr
    if scaled:
        print(f"NOTE: scale-normalised comparison — reference {lwr}pt vs render {lwm}pt. Heights and\n"
              f"      sizes in pt are comparable; horizontal insets/widths are NOT (different screen\n"
              f"      widths), so those are judged on the % -of-width rows.\n", file=sys.stderr)
    for tag, im in (("reference", ri), ("render", mi)):
        if im.info.get("color_managed"):
            print(f"NOTE: {tag} carried a {im.info['source_profile']!r} profile; converted to sRGB "
                  f"before measuring.", file=sys.stderr)
    if ri.info.get("source_profile") != mi.info.get("source_profile") and a.no_color_manage:
        print(f"WARNING: colour management is OFF and the two images are in DIFFERENT spaces "
              f"({ri.info.get('source_profile')} vs {mi.info.get('source_profile')}). Every colour "
              f"verdict below is meaningless.", file=sys.stderr)
    ra = np.asarray(ri).astype(int)
    out_path = a.out or default_out(a.ref, a.regions)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    results, any_fail, locate_failures = [], False, []
    for spec in a.regions:
        parts = spec.split(":")
        name = parts[0]
        ry = my = None
        h = a.h
        if len(parts) > 1 and parts[1]:
            ry = int(parts[1])
        if len(parts) > 2 and parts[2]:
            my = int(parts[2])
        if len(parts) > 3 and parts[3]:
            h = int(parts[3])

        auto = ry is None                      # only guard what the tool chose itself
        if ry is None:
            loc = locate(ri, name, sr, a.white)
            if loc is None:
                print(f"!! could not auto-locate {name!r} in the reference — pass "
                      f"'{name}:<refY>' (auto-location supports composer and header)", file=sys.stderr)
                any_fail = True; continue
            ry, h = loc[0], loc[1]
        if my is None:
            loc = locate(mi, name, sm, a.white)
            if loc:
                # CROSS-VALIDATE. Each side is located independently, and the taller of the
                # two is then silently truncated to the shorter — so when the two bands
                # disagree the crops are not the same region at all and every metric below
                # is a comparison of different things. A real run compared a 158px reference
                # band against a 270px render band (WhatsApp's mic FAB stopped the reference
                # scan 37pt early) and published a pill inset of 198pt on a 393pt screen.
                mh = loc[1]
                rh_pt, mh_pt = h / sr, mh / sm
                if auto and abs(mh_pt - rh_pt) > max(0.25 * max(mh_pt, rh_pt), 12):
                    locate_failures.append((name, ry, my, [
                        f"auto-location disagrees between the two images: the reference band is "
                        f"{rh_pt:.0f}pt tall but yours is {mh_pt:.0f}pt. One of the two scans stopped "
                        f"early (usually a control that reaches into the screen margin), so the "
                        f"crops are not the same region."]))
                    continue
                my = loc[0]
            else:
                my = align(ra, mi, ry, h, a.align_window)

        rows, fails, notes, crops, geom, bad = compare_one(name, ri, mi, ry, my, h, sr, sm, a, scaled)
        if bad and auto:
            locate_failures.append((name, ry, my, bad))
            continue
        results.append((name, rows, fails, notes, crops, geom))
        any_fail = any_fail or bool(fails)

    if locate_failures:
        print("\n!! AUTO-LOCATION FAILED — no verdict issued for these regions.", file=sys.stderr)
        print("   Absurd geometry is a mis-anchored crop, not a design difference; measuring it "
              "anyway is how a\n   run gets a table it has to throw away.\n", file=sys.stderr)
        for name, ry, my, why in locate_failures:
            print(f"  {name}  (tried ref y={ry}, render y={my})", file=sys.stderr)
            for w in why:
                print(f"      {w}", file=sys.stderr)
            print(f"      -> re-run with an explicit y for this region: --r '{name}:<refY>'\n"
                  f"         find it by eye from the reference, or give both: '{name}:<refY>:<mineY>'",
                  file=sys.stderr)
        any_fail = True

    if not results:
        sys.exit("no region could be compared — see the messages above")
    contact_sheet([(n, c, "FAIL" if f else "PASS") for n, _, f, _, c, _ in results], out_path)

    if a.json:
        print(json.dumps({"scale_ref": sr, "scale_mine": sm, "logical_width_ref": lwr,
                          "logical_width_mine": lwm, "scale_normalised": scaled,
                          "color_profile_ref": ri.info.get("source_profile"),
                          "color_profile_mine": mi.info.get("source_profile"),
                          "sheet": out_path, "regions": [
            {"name": n, "ref_y": g[0], "mine_y": g[1], "height": g[2], "rows": r,
             "fails": [{"metric": m, "fix": fx} for m, fx in f], "notes": nt,
             "verdict": "FAIL" if f else "PASS"}
            for n, r, f, nt, _, g in results]}, indent=2))
    else:
        for name, rows, fails, notes, _, (ry, my, hh) in results:
            w = max(len(r[0]) for r in rows) + 2
            hdr = (f"@{sr:g}x {lwr}pt vs @{sm:g}x {lwm}pt  SCALE-NORMALISED" if scaled
                   else f"scale @{sr:g}x")
            print(f"\n=== {name}   {hdr}   ref y={ry} mine y={my} h={hh}px   units: logical px")
            print(f"{'metric'.ljust(w)}{'reference':>12}{'mine':>12}{'delta':>10}   verdict")
            print("-" * (w + 46))
            for n, rv, mv, d, v in rows:
                print(f"{n.ljust(w)}{rv:>12}{mv:>12}{d:>10}   {v}")
            if fails:
                print(f"VERDICT: FAIL ({len(fails)}) — each with the edit that closes it:")
                for metric, fix in fails:
                    print(f"  - {metric}")
                    if fix:
                        print(f"      fix: {fix}")
            else:
                print("VERDICT: PASS on every measured metric.")
            for nt in notes:
                print(f"  note: {nt}")
        print(f"\ncontact sheet (all {len(results)} region(s), labelled, reference above mine): {out_path}")
        print("\n" + ("SOME REGIONS FAILED. A region's only terminal states are Fixed or "
                      "Impossible: <reason> — fix and re-run; do not downgrade a FAIL to a qualifier."
                      if any_fail else
                      "ALL REGIONS PASS on measurable metrics. Open the sheet ONCE for what numbers "
                      "cannot judge: overall balance, glyph identity, texture, material/glass."))
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
