#!/usr/bin/env python3
"""Validate design-analysis.md before you call a design match done.

    python3 scripts/check_analysis.py [design-analysis.md] [--require-evidence] [--strict]

Two severities, so this converges in ONE run instead of becoming a retry loop:

  FAIL (exit 1)  a region has no terminal verdict, or its verdict is a synonym for
                 "good enough", or an N/A is really a schedule excuse. These are the
                 defects that actually shipped, and they are unambiguous.
  WARN (exit 0)  everything advisory: an unmeasured spec, an empty Plan, an unknown
                 Axis, a missing evidence artifact. Printed, not blocking. Pass
                 --strict to make warnings fail too.

Terminal verdicts:

    Fixed                      the region matches the reference
    Impossible: <reason>       genuinely unreachable — say what and why
    N/A - <design reason>      the target legitimately does not have it
    GAP - not implemented      knowingly skipped, in exactly those words

Expected table (extra columns fine, order irrelevant):

    | Region | Spec (measured) | Plan (Stream SDK feature) | Axis | Status |

Evidence paths are resolved relative to the ANALYSIS FILE first, then the cwd —
so it works whether you run it from the project or from the skill directory.
"""
import argparse
import os
import re
import sys

# Phrases that mean "good enough" wherever they appear in a Status cell.
# Deliberately excludes bare words like "minor" / "partial" / "mostly" that were
# false-positive generators: they appear legitimately inside an Impossible reason.
BANNED_PHRASES = [
    "acceptable approximation", "close enough", "good enough", "close to",
    "keep default", "kept default", "left default", "difference noted",
    "nice-to-have", "nice to have", "cosmetic residual", "wontfix", "won't fix",
]
# Deferral words are excuses only when they ARE the verdict, so they are matched at the
# START of the status, not anywhere in it. Substring-matching them was a false-positive
# generator against real UI copy: this very app ships a "Save for later" bookmark row, so
# `Fixed - bookmark row reads "Save for later"` was rejected as a deferral.
DEFERRAL_PREFIXES = [
    "tbd", "todo", "deferred", "defer", "for now", "later", "not yet", "will fix",
]
NOT_DESIGN_REASONS = [
    "deferred", "defer", "later", "moving fast", "out of scope for now", "no time",
    "ran out of time", "too risky", "risky", "too much effort", "more effort",
]
VALID_AXES = {
    "theming", "layout", "functional", "structural", "app-owned", "already-default",
    "theme", "structure", "already default", "app owned", "default", "n/a",
    # The single-letter codes the analysis template itself legends:
    # "Axis: **T**heming · **L**ayout/structure · **F**unctional · **A**pp-owned."
    # Without these, every row of a correctly-written table warned.
    "t", "l", "f", "a", "d",
}
# An axis cell may combine codes: "T/L", "F/T", "theming + layout".
AXIS_SPLIT = re.compile(r"[/,+&]| and ")


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(line):
    s = line.strip()
    return bool(re.fullmatch(r"\|?[\s:\-|]+\|?", s)) and "-" in s


def find_tables(text):
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|") and i + 1 < len(lines) and is_separator(lines[i + 1]):
            header, rows, j = split_row(lines[i]), [], i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                if not is_separator(lines[j]):
                    rows.append((j + 1, split_row(lines[j])))
                j += 1
            yield header, rows
            i = j
        else:
            i += 1


def col_index(header, *names):
    low = [h.lower() for h in header]
    for n in names:
        for k, h in enumerate(low):
            if h.startswith(n):
                return k
    return None


# A terminal verdict may be followed by its evidence: `Fixed - 284.0x40.0 vs 284.3x40.3`.
# Requiring the BARE word rejected all 40 rows of a well-measured analysis, which made this
# check unusable — and it contradicted --require-evidence, which reads a cited artifact path
# out of the very same cell. So match the verdict as a HEAD and let detail follow it.
TERMINAL_HEADS = ("fixed", "pass", "ported", "rewritten", "matches",
                  "already default", "already-default", "default matches")
DASHES = ":\\-–—"


def classify_status(s):
    """-> ('terminal'|'fail', message_or_None)"""
    t = re.sub(r"[*`]", "", s).strip()
    low = t.lower()
    if not t or t in ("-", "—", "?"):
        return "fail", "blank status — a region with no verdict is incomplete, not done"

    if re.match(rf"^gap\s*[{DASHES}]\s*not implemented", low):
        return "terminal", None
    if low.startswith("gap"):
        return "fail", "a GAP must read exactly 'GAP - not implemented' so it stays visible"

    hit = next((w for w in DEFERRAL_PREFIXES if re.match(rf"^{re.escape(w)}\b", low)), None)
    if hit:
        return "fail", (f"Status opens with {hit!r} — a deferral is not a verdict. Use "
                        "'GAP - not implemented' so it stays visible")

    # "Impossible to diff at this scale: <reason>" is as valid as "Impossible: <reason>";
    # the reason is what matters, not whether the colon hugs the word.
    if re.match(r"^impossible\b", low):
        m = re.match(rf"^impossible\b[^{DASHES}]*[{DASHES}]\s*(.+)$", t, re.I)
        if m and len(m.group(1).strip()) >= 10:
            return "terminal", None
        return "fail", "Impossible needs a concrete reason (what and why), not a word"

    m = re.match(rf"^n/?a\s*[{DASHES}]\s*(.+)$", t, re.I)
    if m:
        reason = m.group(1).strip().lower()
        hit = next((w for w in NOT_DESIGN_REASONS if w in reason), None)
        if hit:
            return "fail", (f"N/A reason {reason!r} is a schedule excuse ({hit!r}), not a design "
                            "reason — that is 'GAP - not implemented', not N/A")
        return ("terminal", None) if len(reason) >= 6 else ("fail", "N/A needs a real design reason")

    if any(re.match(rf"^{re.escape(h)}\b", low) for h in TERMINAL_HEADS):
        return "terminal", None
    return "fail", ("not a terminal verdict. Valid: 'Fixed', 'Impossible: <reason>', "
                    "'N/A - <design reason>', 'GAP - not implemented' — each may be followed "
                    "by detail, e.g. 'Fixed - 40.0pt vs 40.3pt'")


def resolve(path, *roots):
    """Try each root in turn; return the first that exists, else None."""
    if os.path.isabs(path):
        return path if os.path.exists(path) else None
    for r in roots:
        cand = os.path.normpath(os.path.join(r, path))
        if os.path.exists(cand):
            return cand
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path", nargs="?", default="design-analysis.md")
    p.add_argument("--require-evidence", action="store_true",
                   help="warn when a Fixed row cites no comparison artifact")
    p.add_argument("--strict", action="store_true", help="treat warnings as failures too")
    a = p.parse_args()

    try:
        with open(a.path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        sys.exit(
            f"{a.path} not found.\n"
            "The design spec is the contract the implementation and the verify step satisfy.\n"
            "Run design-matching Step 1 against the reference and write it first."
        )

    here = os.path.dirname(os.path.abspath(a.path)) or "."
    fails, warns, checked, tables = [], [], 0, 0

    for header, rows in find_tables(text):
        ri, si = col_index(header, "region"), col_index(header, "status", "verdict")
        if ri is None or si is None:
            continue
        tables += 1
        pi, ai = col_index(header, "plan"), col_index(header, "axis")
        spi = col_index(header, "spec")
        ei = col_index(header, "evidence", "crop", "artifact", "proof")

        for lineno, cells in rows:
            if len(cells) <= max(ri, si):
                warns.append((lineno, "row", "malformed row — fewer cells than the header"))
                continue
            region = cells[ri] or f"line {lineno}"
            if not region or region in ("-", "—"):
                continue
            checked += 1
            status = cells[si]

            kind, why = classify_status(status)
            if kind == "fail":
                fails.append((lineno, region, f"Status {status!r}: {why}"))
            low = re.sub(r"[*`]", "", status).lower()
            for b in BANNED_PHRASES:
                if b in low:
                    fails.append((lineno, region,
                                  f"Status contains {b!r} — a synonym for 'good enough' is still "
                                  "'good enough'"))
                    break

            if spi is not None and spi < len(cells):
                spec = cells[spi]
                if not spec or spec in ("-", "—", "?"):
                    warns.append((lineno, region, "empty Spec — record the measured attributes "
                                                  "(radius, size, weight, padding, sampled colours)"))
                # A hex colour is a measured spec even when it carries no decimal digit
                # (#FFFFFF), so test for either.
                elif not re.search(r"\d|#[0-9a-fA-F]{3,8}\b", spec) and "n/a" not in spec.lower():
                    warns.append((lineno, region, "Spec has no measured number — "
                                                  "'looks roughly like it' is the failure mode"))

            if pi is not None and pi < len(cells):
                if not cells[pi] or cells[pi] in ("-", "—", "?"):
                    warns.append((lineno, region, "empty Plan — name the concrete Stream mechanism "
                                                  "(theme key / slot / Channel prop / hook)"))

            if ai is not None and ai < len(cells):
                axis = re.sub(r"[*`]", "", cells[ai]).strip().lower()
                if axis and axis not in ("-", "—"):
                    parts = [p.strip() for p in AXIS_SPLIT.split(axis) if p.strip()]
                    bad = [p for p in parts if p not in VALID_AXES
                           and not any(v in p for v in VALID_AXES if len(v) > 1)]
                    if bad:
                        warns.append((lineno, region,
                                      f"Axis {cells[ai]!r}: {', '.join(repr(b) for b in bad)} is not "
                                      "one of theming / layout / functional / app-owned / "
                                      "already-default (or the T / L / F / A codes)"))

            if a.require_evidence and kind == "terminal" and low.startswith("fixed"):
                cite = cells[ei] if (ei is not None and ei < len(cells)) else ""
                paths = re.findall(r"[\w./\-]+\.(?:png|jpg|jpeg)", cite + " " + status)
                if not paths:
                    warns.append((lineno, region, "Fixed without a cited comparison artifact — the "
                                                  "evidence is the baseline<->migrated crop pair"))
                else:
                    missing = [q for q in paths if resolve(q, here, os.getcwd()) is None]
                    if missing:
                        warns.append((lineno, region,
                                      f"cited artifact(s) not found relative to {here} or the cwd: "
                                      f"{', '.join(missing)}"))

    if tables == 0:
        sys.exit(f"{a.path} has no table with Region and Status columns.\n"
                 "Expected: | Region | Spec (measured) | Plan (Stream SDK feature) | Axis | Status |")

    print(f"{a.path}: {tables} table(s), {checked} region row(s) checked")
    if warns:
        print(f"\n{len(warns)} warning(s) — advisory, not blocking"
              f"{' (fatal under --strict)' if a.strict else ''}:")
        for lineno, region, msg in warns:
            print(f"  line {lineno}  [{region}]\n      {msg}")
    if fails:
        print(f"\nFAIL — {len(fails)} blocking problem(s):")
        for lineno, region, msg in fails:
            print(f"  line {lineno}  [{region}]\n      {msg}")
        print("\nA region left at the SDK default is a FAIL, not a known cosmetic gap.")
        sys.exit(1)
    if warns and a.strict:
        sys.exit(1)
    print("\nPASS — every region has a terminal verdict."
          + (f" {len(warns)} advisory warning(s) above." if warns else ""))


if __name__ == "__main__":
    main()
