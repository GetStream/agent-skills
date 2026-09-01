#!/usr/bin/env python3
"""Render a markdown results report from one or more eval run directories.

  python3 evals/compare.py evals/results/<run-B> evals/results/<run-C> [...]

Each run dir is one configuration (its name ends in -A/-B/-C). The report has the
objective data: per case and configuration, scored graders passed / scored (summed over
the case's completed runs), run status, cost, and the per-grader verdicts. The unit is
the grader, not the case: a 16-grader build and a 1-grader question weigh what they
checked. Runs that timed out, ran out of turns, or errored are counted but labeled (T),
and their failures are tallied separately as ambiguous: a pass in a truncated run is a
pass, a failure may only be the budget. Judged findings are written by hand into the
report afterwards.
"""

import json
import sys
from pathlib import Path


def load(run_dir):
    run_dir = Path(run_dir)
    summary = json.loads((run_dir / "summary.json").read_text())
    config = run_dir.name.rsplit("-", 1)[-1]
    by_case = {}
    for r in summary:
        by_case.setdefault(r["case"], []).append(r)
    return config, run_dir.name, by_case


def status_of(r):
    m = r["metrics"]
    if m.get("timed_out"):
        return "timeout"
    sub = m.get("subtype") or "?"
    if m.get("is_error") and sub == "success":
        return "error"  # e.g. a spend-limit refusal: the CLI says subtype "success" but is_error true
    return sub


def truncated(r):
    return status_of(r) != "success"


def tally(runs):
    """Aggregate the runs of one case in one configuration.

    Returns dict(passed, scored, runs, truncated, ambiguous, all_pass, status, cost): passed/scored
    count scored graders over ALL runs; truncated is how many runs hit a budget or errored and
    ambiguous is the number of failures inside those runs (budget or content - cannot tell);
    all_pass is how many runs had every scored grader pass; cost is agent + judge."""
    out = {"passed": 0, "scored": 0, "runs": 0, "truncated": 0, "ambiguous": 0, "all_pass": 0,
           "status": "-", "cost": 0.0}
    if not runs:
        return out
    for r in runs:
        out["cost"] += (r["metrics"].get("cost_usd") or 0) + (r["metrics"].get("judge_cost_usd") or 0)
        out["runs"] += 1
        scored = [g for g in r["graders"] if g.get("scored", True)]
        passed = sum(1 for g in scored if g["pass"])
        out["scored"] += len(scored)
        out["passed"] += passed
        out["all_pass"] += int(r["pass"])
        if truncated(r):
            out["truncated"] += 1
            out["ambiguous"] += len(scored) - passed
    out["status"] = "/".join(sorted({status_of(r) for r in runs}))
    return out


def cell(t):
    if t["runs"] == 0:
        return "-"
    s = "%d/%d" % (t["passed"], t["scored"])
    if t["runs"] > 1:
        s += " (%d runs)" % t["runs"]
    if t["truncated"]:
        s += " T%d" % t["truncated"]
        if t["ambiguous"]:
            s += " (%d fail%s ambiguous)" % (t["ambiguous"], "s" if t["ambiguous"] != 1 else "")
    return s


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    # Several run dirs may share a configuration (re-runs, serial batches): merge them per
    # configuration, later dirs overriding earlier ones case by case.
    merged = {}
    for path in argv[1:]:
        config, name, by_case = load(path)
        cfg_config, cfg_names, cfg_cases = merged.setdefault(config, (config, [], {}))
        cfg_names.append(name)
        cfg_cases.update(by_case)
    runs = [(c, "+".join(n), by) for c, n, by in (merged[k] for k in sorted(merged))]
    configs = [c for c, _, _ in runs]
    cases = sorted({c for _, _, by in runs for c in by})

    out = ["# Eval results: " + " vs ".join("%s (%s)" % (c, n) for c, n, _ in runs), ""]
    prov_lines = []
    for config, _, by in runs:
        prov = next((r.get("provenance") for rs in by.values() for r in rs if r.get("provenance")), None)
        if prov:
            prov_lines.append("- %s: agent %s, judge %s, claude %s, repo %s%s%s" % (
                config, prov.get("agent_model"), prov.get("judge_model"), prov.get("claude_version"),
                prov.get("repo_sha"), " (dirty)" if prov.get("repo_dirty") else "",
                ", v1-skills %s" % prov["v1_skills_sha"] if prov.get("v1_skills_sha") else ""))
    if prov_lines:
        out += prov_lines + [""]
    out.append("## Objective results")
    out.append("")
    out.append("Cells are scored graders passed / scored, summed over the case's runs. `T<n>` marks runs that hit "
               "a budget or errored; their failures are counted but flagged ambiguous (budget or content).")
    out.append("")
    out.append("| case | " + " | ".join(configs) + " | run status (" + "/".join(configs) + ") | cost agent+judge (" + "/".join(configs) + ") |")
    out.append("|---|" + "---|" * len(configs) + "---|---|")
    totals = {c: {"passed": 0, "scored": 0, "all_pass": 0, "runs": 0, "truncated": 0, "ambiguous": 0, "cost": 0.0} for c in configs}
    for case in cases:
        cells, statuses, costs = [], [], []
        for config, _, by in runs:
            t = tally(by.get(case, []))
            for k in totals[config]:
                totals[config][k] += t[k]
            cells.append(cell(t))
            statuses.append(t["status"])
            costs.append("$%.2f" % t["cost"] if t["runs"] else "-")
        out.append("| %s | %s | %s | %s |" % (case, " | ".join(cells), " / ".join(statuses), " / ".join(costs)))
    out.append("| **graders passed** | " + " | ".join(
        "**%d/%d**" % (totals[c]["passed"], totals[c]["scored"]) for c in configs) + " | | " + " / ".join(
        "$%.2f" % totals[c]["cost"] for c in configs) + " |")
    out.append("| runs with every grader passing | " + " | ".join(
        "%d/%d" % (totals[c]["all_pass"], totals[c]["runs"]) for c in configs) + " | | |")
    out.append("| truncated runs / ambiguous failures | " + " | ".join(
        "%d / %d" % (totals[c]["truncated"], totals[c]["ambiguous"]) for c in configs) + " | | |")
    out.append("")

    out.append("## Per-grader verdicts")
    out.append("")
    out.append("Per grader: passes / runs (`(ind)` = unscored indicator; `T<n>` = n of the runs were truncated, so "
               "a failure there may be budget). Detail is the grader's own note from the last run, truncated.")
    out.append("")
    for case in cases:
        out.append("### " + case)
        out.append("")
        out.append("| grader | " + " | ".join(configs) + " |")
        out.append("|---|" + "---|" * len(configs))
        names = []
        for _, _, by in runs:
            for r in by.get(case, []):
                for g in r["graders"]:
                    if g["name"] not in names:
                        names.append(g["name"])
        for name in names:
            cells = []
            for _, _, by in runs:
                pairs = [(r, g) for r in by.get(case, []) for g in r["graders"] if g["name"] == name]
                if not pairs:
                    cells.append("-")
                    continue
                n_trunc = sum(1 for r, _ in pairs if truncated(r))
                ind = "" if pairs[-1][1].get("scored", True) else " (ind)"
                passed = sum(1 for _, g in pairs if g["pass"])
                mark = ("PASS" if passed == 1 else "FAIL") if len(pairs) == 1 else "%d/%d" % (passed, len(pairs))
                detail = (pairs[-1][1].get("detail") or "").replace("|", "\\|").replace("\n", " ")[:90]
                cells.append("%s%s%s - %s" % (mark, ind, " T%d" % n_trunc if n_trunc else "", detail))
            out.append("| %s | %s |" % (name, " | ".join(cells)))
        out.append("")

    out.append("## Judged findings")
    out.append("")
    out.append("_(written by hand after inspecting transcripts; see evals/FINDINGS.md for the cumulative log)_")
    out.append("")
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv)
