#!/usr/bin/env python3
"""Measure a reference screenshot instead of eyeballing round numbers.

    python3 scripts/measure_region.py scale  <img>
    python3 scripts/measure_region.py band   <img> [--from-bottom 380] [--scale auto]
    python3 scripts/measure_region.py colors <img> --box X,Y,W,H [--scale auto]
    python3 scripts/measure_region.py weight <img> --box X,Y,W,H --font-size N [--scale auto]

Every number it prints is in LOGICAL px (what RN StyleSheet takes), because
mobile screenshots are @2x/@3x and the recurring failure is landing device px in
a style value. Picking 24 / 28 / 44 by eye is the other recurring failure, and it
shows up worst in the composer: wrong input height, oversized icons, wrong padding.

Requires Pillow + numpy. If they are missing:
    python3 -m venv .designvenv && .designvenv/bin/pip install Pillow numpy
and call .designvenv/bin/python3 instead. Do this BEFORE you start capturing —
a tool missing mid-verify is a silent reason the measurement gets skipped.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Same detectors compare_regions.py uses. This file used to carry its own, and the two
# diverged: the local one found the input field by absolute brightness, which reports a
# light composer BAR as the field. See region_metrics.py's docstring.
from region_metrics import (  # noqa: E402
    glyphs, hexof, infer_scale, load as _load, modal_bg, np, pill_band,
)


def load(path, manage=True):
    im = _load(path, manage=manage)
    return im, np.asarray(im).astype(int)


def color_note(im):
    """The colour-space provenance every colour-bearing result must carry."""
    return {"source_profile": im.info.get("source_profile"),
            "converted_to_srgb": bool(im.info.get("color_managed"))}


def resolve_scale(arg, width):
    if arg in (None, "auto"):
        s, lw = infer_scale(width)
        if s == 1.0 and width > 800:
            print(
                f"WARNING: could not infer a scale for width {width}px; assuming @1x. "
                "Pass --scale explicitly if this shot is @2x/@3x.",
                file=sys.stderr,
            )
        return s, lw
    s = float(arg)
    return s, int(width / s)


def cmd_scale(args):
    im, _ = load(args.img)
    w, h = im.size
    s, lw = infer_scale(w)
    print(json.dumps({
        "pixels": [w, h],
        "scale": s,
        "logical": [round(w / s, 1), round(h / s, 1)],
        "logical_width": lw,
        # The number to pin the simulator to. Comparing a 402pt render against a 393pt
        # reference is not 1:1 at any scale, and compare_regions.py will refuse it — so
        # boot a matching device BEFORE the native build, not after.
        "pin_the_simulator": f"bash scripts/sim.sh boot --logical-width {lw}",
        **color_note(im),
        "note": "divide every measured pixel value by scale before it goes into a style",
    }, indent=2))


def cmd_band(args):
    """Find the input field band and the icon glyphs in a bar (default: the composer)."""
    im, arr = load(args.img)
    W, H = im.size
    S, _ = resolve_scale(args.scale, W)

    y0 = max(0, H - args.from_bottom)
    crop = arr[y0:H, :]
    result = {"scale": S, "searched_rows": [y0, H]}

    # The field is the surface DISTINCT FROM THE BAR, not "the near-white rows". The old
    # brightness test matched every row of a light bar and reported the whole 402pt bar as
    # the input field — a wrong number that reads as plausible in JSON.
    f = pill_band(crop)
    if f is None:
        result["field"] = None
        result["bar_hex"] = hexof(modal_bg(crop))
        result.update(color_note(im))
        result["hint"] = (
            "no input pill found in the searched band. Either this bar genuinely has none "
            "(a header), or --from-bottom is too small to contain it (a floating/taller bar)."
        )
        print(json.dumps(result, indent=2))
        return

    ft, fb = f["top"] + y0, f["bottom"] + y0
    mid = (ft + fb) // 2
    result["field"] = {
        "height_logical": round(f["height"] / S, 1),
        "width_logical": round((f["x1"] - f["x0"]) / S, 1),
        "left_inset_logical": round(f["x0"] / S, 1),
        "y_px": [ft, fb],
        "x_px": [f["x0"], f["x1"]],
        "center_y_px": mid,
    }
    result["bar_hex"] = f["bar_hex"]
    result["pill_hex"] = f["pill_hex"]
    result.update(color_note(im))

    # Icon glyphs: dark ink on the bar, projected onto columns and clustered.
    gy0 = max(0, f["top"] - args.pad)
    strip = crop[gy0:min(crop.shape[0], f["bottom"] + args.pad), :]
    found = glyphs(strip, args.dark, args.gap, args.max_glyph * S)
    result["glyphs"] = [{
        "x_px": [g["x0"], g["x1"]],
        "y_px": [g["y0"] + gy0 + y0, g["y1"] + gy0 + y0],
        "w_logical": round(g["w"] / S, 1),
        "h_logical": round(g["h"] / S, 1),
        "ink_ratio": g["ink"],
        "center_y_px": g["cy"] + gy0 + y0,
        # A consistent offset means your button frame height != the field's
        # rendered height. Frame side buttons to the field height and centre
        # within, instead of hand-tuning one-sided padding.
        "center_offset_from_field_logical": round((g["cy"] + gy0 + y0 - mid) / S, 1),
    } for g in found]
    result["glyph_count"] = len(result["glyphs"])
    result["notes"] = [
        "Controls are almost always SMALLER than you guess, and often smaller than the SDK default.",
        "The field width is the LEFTOVER: total - (leading cluster + trailing cluster + gaps).",
        "ink_ratio separates a FILLED glyph from an OUTLINED one — compare it, not just the box.",
    ]
    print(json.dumps(result, indent=2))


def _parse_box(s):
    try:
        x, y, w, h = (int(v) for v in s.split(","))
    except ValueError:
        sys.exit("--box wants X,Y,W,H in device pixels")
    return x, y, w, h


def cmd_colors(args):
    im, arr = load(args.img, manage=not args.no_color_manage)
    x, y, w, h = _parse_box(args.box)
    sub = arr[y:y + h, x:x + w]
    if sub.size == 0:
        sys.exit("empty box — check X,Y,W,H against the image size")
    flat = sub.reshape(-1, 3)
    mean = flat.mean(0)
    std = flat.std(0)

    # A background may be a TEXTURE, not a flat fill. Low std -> flat -> a colour
    # key. Varying (faint repeated marks, darker mins) -> reproduce it as a tiled
    # background; flattening it loses what separates the chat area from the composer.
    textured = bool(std.max() > args.texture_std)

    # Sample the saturated CORE, not the antialiased edges: take the pixels
    # furthest from the box mean in the dominant direction.
    d = np.abs(flat.astype(int) - mean.astype(int)).sum(1)
    core = flat[d >= np.percentile(d, 90)]
    print(json.dumps({
        "box": [x, y, w, h],
        "mean_rgb": [round(float(v), 1) for v in mean],
        "mean_hex": "#%02x%02x%02x" % tuple(int(round(v)) for v in mean),
        "std_rgb": [round(float(v), 1) for v in std],
        "verdict": "TEXTURE — reproduce as a tiled background" if textured
                   else "FLAT — a single colour key is correct",
        "core_hex": "#%02x%02x%02x" % tuple(int(round(v)) for v in core.mean(0)),
        "min_rgb": [int(v) for v in flat.min(0)],
        "max_rgb": [int(v) for v in flat.max(0)],
        **color_note(im),
        "notes": [
            "Multi-part elements have more than one colour — sample each part separately.",
            "Isolate small elements: a blue tick averaged against a blue sky loses to the photo.",
            "Pin brand/content colours; keep structural surfaces on semantic theme values.",
        ],
    }, indent=2))


# stroke-width / font-size ratio -> RN fontWeight string
WEIGHT_TABLE = ((0.06, "300"), (0.082, "400"), (0.10, "500"), (0.12, "600"), (99, "700"))


def cmd_weight(args):
    im, arr = load(args.img)
    x, y, w, h = _parse_box(args.box)
    S, _ = resolve_scale(args.scale, im.size[0])
    sub = arr[y:y + h, x:x + w]
    if sub.size == 0:
        sys.exit("empty box — check X,Y,W,H against the image size")
    g = sub.mean(2)
    ink = g < args.dark
    if not ink.any():
        sys.exit("no dark ink in the box — raise --dark, or the text may be light-on-dark")

    # Mean horizontal run length of ink across rows that contain ink ~= stroke width.
    runs = []
    for row in ink:
        cur = 0
        for v in row:
            if v:
                cur += 1
            elif cur:
                runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
    stroke_px = float(np.median(runs)) if runs else 0.0
    font_px = args.font_size * S
    ratio = stroke_px / font_px if font_px else 0.0
    weight = next(w for t, w in WEIGHT_TABLE if ratio < t)
    dark_core = arr[y:y + h, x:x + w][ink].mean(0)
    print(json.dumps({
        "stroke_px": round(stroke_px, 2),
        "font_size_logical": args.font_size,
        "stroke_over_fontsize": round(ratio, 4),
        "fontWeight": weight,
        "dark_core_hex": "#%02x%02x%02x" % tuple(int(round(v)) for v in dark_core),
        **color_note(im),
        "notes": [
            "Different text ROLES usually have different weights — measure each separately "
            "(a sender name is normally heavier than the body).",
            "Weight and colour are independent: a glyph that looks 'too light' may be the wrong "
            "base colour, not too thin a weight. Verify BOTH.",
            "'400' often renders heavier than a reference's light body — re-measure your own "
            "render and step down if so.",
        ],
    }, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scale", help="pixel size -> scale -> logical size")
    s.add_argument("img")
    s.set_defaults(fn=cmd_scale)

    b = sub.add_parser("band", help="input-field height/width + icon glyph boxes")
    b.add_argument("img")
    b.add_argument("--from-bottom", type=int, default=380, help="height of the bar band to search, in device px")
    b.add_argument("--scale", default="auto")
    b.add_argument("--dark", type=int, default=110, help="dark threshold for glyph ink")
    b.add_argument("--pad", type=int, default=6)
    b.add_argument("--gap", type=int, default=8, help="column gap that separates two glyphs")
    b.add_argument("--max-glyph", type=float, default=80.0, help="logical px above which a cluster is chrome, not a glyph")
    b.set_defaults(fn=cmd_band)

    c = sub.add_parser("colors", help="mean/std/core colour + flat-vs-texture verdict")
    c.add_argument("img")
    c.add_argument("--box", required=True, help="X,Y,W,H in device px")
    c.add_argument("--scale", default="auto")
    c.add_argument("--texture-std", type=float, default=6.0)
    c.add_argument("--no-color-manage", action="store_true",
                   help="report values in the FILE's colour space instead of converting to sRGB")
    c.set_defaults(fn=cmd_colors)

    w = sub.add_parser("weight", help="stroke/font-size ratio -> RN fontWeight")
    w.add_argument("img")
    w.add_argument("--box", required=True, help="X,Y,W,H in device px")
    w.add_argument("--font-size", type=float, required=True, help="the role's font size in LOGICAL px")
    w.add_argument("--scale", default="auto")
    w.add_argument("--dark", type=int, default=140)
    w.set_defaults(fn=cmd_weight)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
