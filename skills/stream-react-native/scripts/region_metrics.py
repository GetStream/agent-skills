#!/usr/bin/env python3
"""Shared image primitives for measure_region.py and compare_regions.py.

Not a CLI — import it. It exists because the two scripts each grew their OWN input-field
detector and they diverged: compare_regions.py learned to find the pill as a surface
DISTINCT FROM THE BAR, while measure_region.py kept the original "rows that are near-white"
test. On a light composer bar (Slack's is RGB 252) that older test matches every row, so
`measure_region.py band` reported the whole 402pt bar as the input field — a wrong number
that looks perfectly plausible in a JSON blob. One detector, one behaviour.

Requires Pillow + numpy:
    python3 -m venv .designvenv && .designvenv/bin/pip install Pillow numpy
"""
import io
import sys

try:
    import numpy as np
    from PIL import Image, ImageCms
except ImportError as e:
    sys.exit(
        f"missing dependency ({e.name}). Run:\n"
        "  python3 -m venv .designvenv && .designvenv/bin/pip install Pillow numpy\n"
        "then re-run with .designvenv/bin/python3"
    )

# Logical widths of the iPhone classes these references normally come from.
KNOWN_LOGICAL_WIDTHS = (320, 375, 390, 393, 402, 414, 428, 430, 440)


def profile_name(im):
    """Name of the image's embedded ICC profile, or None."""
    icc = im.info.get("icc_profile")
    if not icc:
        return None
    try:
        return ImageCms.getProfileName(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip()
    except Exception:
        return None


def load(path, manage=True):
    """Open as RGB, CONVERTED TO sRGB when the file says it is something else.

    A reference screenshot off a real iPhone carries a **Display P3** profile; a simulator
    capture is sRGB. The same paint therefore reads as two different numbers — WhatsApp's
    outgoing bubble is #E0FCD6 in P3 and #D9FDD3 in sRGB, a max-channel delta of 7 against a
    default --tol-rgb of 6. So every colour verdict between a device reference and a
    simulator render flipped on colour space alone, silently, with no warning. Normalise on
    load and record what happened on the returned image (`source_profile`, `color_managed`).
    """
    try:
        im = Image.open(path)
    except FileNotFoundError:
        sys.exit(f"no such image: {path}")
    except OSError as e:
        sys.exit(f"cannot read {path}: {e}")
    src = profile_name(im)
    icc = im.info.get("icc_profile")
    rgb = im.convert("RGB")
    converted = False
    if manage and icc and src and "srgb" not in src.lower():
        try:
            rgb = ImageCms.profileToProfile(
                rgb, ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                ImageCms.createProfile("sRGB"), outputMode="RGB")
            converted = True
        except Exception as e:                     # never fail the measurement over this
            print(f"WARNING: could not convert {path} from {src!r} to sRGB ({e}); "
                  "colour numbers are in the FILE's space, not sRGB.", file=sys.stderr)
    rgb.info["source_profile"] = src or "none (assumed sRGB)"
    rgb.info["color_managed"] = converted
    return rgb


def infer_scale(width):
    """Return (scale, logical_width). Falls back to 1.0."""
    for s in (3.0, 2.0, 1.0):
        if width % s == 0 and (width / s) in KNOWN_LOGICAL_WIDTHS:
            return s, int(width / s)
    for s in (3.0, 2.0):
        if width % s == 0:
            return s, int(width / s)
    return 1.0, width


def modal_bg(arr):
    q = (arr.reshape(-1, 3) // 8).astype(np.int32)
    keys, counts = np.unique(q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2], return_counts=True)
    k = keys[counts.argmax()]
    return np.array([(k // 4096) * 8 + 4, ((k // 64) % 64) * 8 + 4, (k % 64) * 8 + 4])


def hexof(rgb):
    return "#%02x%02x%02x" % tuple(int(round(float(v))) for v in rgb)


def pill_band(arr, min_frac=0.35, tol=2, prefer="area"):
    """Find the input pill as a surface DISTINCT FROM THE BAR, not as "the light rows".

    An absolute-brightness test ("rows that are near-white") silently fails on a light
    composer bar: Slack's bar measures RGB 252, so every row of the crop matches and the
    whole bar is reported as the field. Two real runs got an unusable composer verdict that
    way. So detect the pill *relative to the bar surface*:

      1. the bar is the crop's modal colour;
      2. the pill is the next colour cluster that forms a wide, horizontally INSET band
         (buttons flank it, so it does not span the full width);
      3. if no colour step exists, fall back to a bordered pill — two strong horizontal
         edges bounding a wide band.

    Works for a light pill on a light bar, a light pill on a dark bar, and returns None for
    a region that genuinely has no pill.
    """
    # 2-unit buckets, not 4: a white pill (255) on a near-white bar (252) falls in the SAME
    # 4-unit bucket, so the pill was literally unrepresentable and the measurement returned
    # the glyph row instead. The inset + density constraints below are what reject noise, so
    # the colour step can be this fine safely.
    H, W = arr.shape[:2]
    flat = arr.reshape(-1, 3)
    q = (flat // 2).astype(np.int32)
    keys, counts = np.unique(q[:, 0] * 16384 + q[:, 1] * 128 + q[:, 2], return_counts=True)
    order = np.argsort(-counts)
    if len(order) == 0:
        return None
    unpack = lambda k: np.array([(k // 16384) * 2 + 1, ((k // 128) % 128) * 2 + 1, (k % 128) * 2 + 1])
    # The bar is the surface at the crop's BOTTOM OUTER MARGINS — structurally, the strip
    # beside/below the controls. It is NOT "the crop's most common colour": when the crop
    # reaches up far enough to include a white message bubble, white outvotes the bar, the
    # roles invert, and the tool reports the BEIGE BACKGROUND as the input pill. That is
    # exactly what happened on a WhatsApp reference — a 571px-wide "pill" inset 608px, which
    # then flowed into a published verdict table.
    edge = max(3, int(W * 0.06))
    margins = np.concatenate([arr[int(H * 0.75):, :edge].reshape(-1, 3),
                              arr[int(H * 0.75):, -edge:].reshape(-1, 3)])
    bar = modal_bg(margins.reshape(1, -1, 3))

    # Score every candidate cluster and take the best, rather than the first that matches.
    # The decisive constraint is that a composer pill is HORIZONTALLY INSET — buttons flank
    # it — so a full-bleed band is some other surface (the page background above the bar,
    # a divider) no matter how plausible its colour is.
    # Scan from order[0], not order[1]: the bar is identified by the margins above, so the
    # crop's most common colour is often the PILL itself (a wide white field on a thin beige
    # bar). Skipping index 0 made the real pill unreachable and left only near-bar noise.
    cands = []
    for k in order[:14]:
        col = unpack(keys[k])
        if np.abs(col.astype(int) - bar.astype(int)).max() < tol:
            continue                                        # same surface, adjacent bucket
        mask = np.abs(arr.astype(int) - col).max(2) <= 1     # tight: keep the step meaningful
        rows = np.where(mask.sum(1) > W * min_frac)[0]
        if len(rows) == 0:
            continue
        # EVERY contiguous row-run of this colour is its own candidate, not just the longest.
        # A message bubble and the composer pill are frequently the SAME colour (both white),
        # so collapsing the cluster to its longest run made the composer pill unreachable
        # whenever a taller bubble was in frame — and prefer="lowest" then had nothing to
        # choose from. Enumerate the runs; let the caller's preference pick.
        runs, r0, prev = [], int(rows[0]), int(rows[0])
        for y in rows[1:]:
            y = int(y)
            if y != prev + 1:
                runs.append((r0, prev)); r0 = y
            prev = y
        runs.append((r0, prev))
        for top, bot in runs:
            if bot - top + 1 < 4 or (bot - top + 1) > 0.9 * H:
                continue
            mid = (top + bot) // 2
            cols = np.where(mask[mid])[0]
            if len(cols) == 0:
                continue
            # The longest run of pill colour, BRIDGING SMALL GAPS. Neither extreme works alone:
            #   * min..max stretches the box across an icon that shares the pill's colour (a
            #     white camera outline's interior), dropping density below the solid-rectangle
            #     gate and rejecting the real pill;
            #   * a strictly contiguous run stops at the PLACEHOLDER TEXT inside the pill and
            #     returns a fragment (Slack's 285pt field came back as 163pt).
            # Letter gaps are a few px; the gap to a flanking button is tens. Bridge below 2%.
            bridge = max(6, int(W * 0.02))
            cruns, b0, prev = [], cols[0], cols[0]
            for c in cols[1:]:
                if c - prev > bridge:
                    cruns.append((b0, prev)); b0 = c
                prev = c
            cruns.append((b0, prev))
            x0, x1 = max(cruns, key=lambda r: r[1] - r[0])
            x0, x1 = int(x0), int(x1)
            # EITHER edge, not both. A composer pill is flanked by buttons, so it never runs to a
            # screen edge; a background band usually runs to one. Requiring BOTH edges before
            # rejecting let a beige background strip that reached only the right edge outscore
            # the real white pill on raw area, on a WhatsApp reference.
            if x0 <= 2 or x1 >= W - 3:
                continue                                        # touches a screen edge -> a surface
            # A pill is a SOLID rectangle. A row of separate icons also forms a wide, short
            # band of one colour, so density inside the bounding box is what separates them:
            # ~1.0 for a filled pill, ~0.2 for three glyphs spread across the same span.
            density = float(mask[top:bot + 1, x0:x1 + 1].mean())
            if density < 0.75:
                continue
            # An input field is WIDE AND SHORT. Requiring that separates it from the blocky
            # light patches around a tab-bar icon, which otherwise satisfy every other test and
            # got reported as an 82pt-tall "input pill" on a screen that has no composer at all.
            if (x1 - x0 + 1) < 2.5 * (bot - top + 1):
                continue
            cands.append(((bot - top + 1) * (x1 - x0 + 1), top, bot, x0, x1, col))
    if cands:
        # key= is mandatory: bare max() compares tuples element-wise, so two candidates with
        # the same area fall through to comparing the trailing numpy colour arrays and raise
        # "truth value of an array ... is ambiguous". That crashed two real runs.
        #
        # prefer="lowest" is for a WIDE search window (locating the composer band in a whole
        # screenshot): a message bubble is also a wide, inset, solid rounded rect and beats
        # the composer pill on area, so "the biggest one" finds the wrong element. The
        # composer pill is by construction the bottom-most field on the screen.
        key = (lambda c: (c[2], c[0])) if prefer == "lowest" else (lambda c: (c[0], c[1]))
        _, top, bot, x0, x1, col = max(cands, key=key)
        return {"top": top, "bottom": bot, "height": bot - top + 1, "x0": x0, "x1": x1,
                "bar_hex": hexof(bar), "pill_hex": hexof(col)}

    # fallback: a pill drawn with a border rather than a fill change
    g = arr.mean(2)
    d = np.abs(np.diff(g.mean(1)))
    if len(d) > 8:
        idx = np.argsort(-d)[:8]
        idx = sorted(int(i) for i in idx if d[i] > 2.0)
        if len(idx) >= 2:
            top, bot = idx[0] + 1, idx[-1]
            if 4 <= bot - top + 1 <= 0.9 * H:
                row = g[(top + bot) // 2]
                inner = np.where(np.abs(row - row[W // 2]) < 8)[0]
                if len(inner):
                    x0, x1 = int(inner.min()), int(inner.max())
                    # Same full-bleed rejection the colour-step path applies. Without it this
                    # fallback answers for bars that have NO pill: a tab bar reported a
                    # 401.7pt-wide "input field" spanning the whole screen, which is a wrong
                    # number that looks entirely plausible in a JSON blob.
                    if not (x0 <= 2 and x1 >= W - 3):
                        return {"top": top, "bottom": bot, "height": bot - top + 1,
                                "x0": x0, "x1": x1,
                                "bar_hex": hexof(bar), "pill_hex": "(bordered, no fill step)"}
    return None


def glyphs(arr, dark, gap, max_w):
    """Icon/text clusters: dark ink projected onto columns, grouped by column gaps.

    Returns absolute pixel boxes as well as sizes, so a caller that needs coordinates
    (measure_region) and one that only compares sizes (compare_regions) share one result.
    """
    g = arr.mean(2)
    ink = g < dark
    cols = np.where(ink.sum(0) > 2)[0]
    groups, start, prev = [], None, None
    for c in cols:
        if start is None:
            start = prev = c
            continue
        if c - prev > gap:
            groups.append((start, prev))
            start = c
        prev = c
    if start is not None:
        groups.append((start, prev))
    res = []
    for c0, c1 in groups:
        if c1 - c0 + 1 > max_w:
            continue
        sub = ink[:, c0:c1 + 1]
        rows = np.where(sub.sum(1) > 0)[0]
        if len(rows) == 0:
            continue
        r0, r1 = int(rows.min()), int(rows.max())
        res.append({"x0": int(c0), "x1": int(c1), "y0": r0, "y1": r1,
                    "w": int(c1 - c0 + 1), "h": int(r1 - r0 + 1),
                    "cy": int((r0 + r1) // 2), "ink": round(float(sub.mean()), 3)})
    return res
