#!/usr/bin/env python
"""Reads the 8 MPS20 artifacts and prints the per-strategy gate table.

PRE-DECLARED gates (repo criteria, AGENTS.md/quant-research):
  G1 pf_strict > 1.2   (discrete; weight-mode rb-period PF labelled separately)
  G2 n >= 30 closed trades (discrete) / 30 rebalance periods (weight, weaker)
  G3 period split: pf_h1 > 1 AND pf_h2 > 1
  G4 full-window years green in >= 2/3 (full artifacts only)
  G5 beats equal-weight buy&hold on the same scored window
  G6 concentration: conc_net_without_top5_pct > 0
A cell passes ONLY with G1..G6 (or, for 6mo artifacts, G4 marked n/a).
Usage: python code/_mps20_report_table.py [run_ids...]   (default: all mps20 runs)
"""
from __future__ import annotations

import glob
import json
import os
import sys

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "runs")


def load_all(ids=None):
    arts = []
    for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        with open(p, encoding="utf-8") as f:
            a = json.load(f)
        if a.get("strategy") != "mps20":
            continue
        if ids and a["run_id"] not in ids:
            continue
        arts.append(a)
    if not arts:
        raise SystemExit("no mps20 artifacts found")
    return arts


def main(only_ids):
    arts = load_all(only_ids or None)
    arts.sort(key=lambda a: (a["metrics"]["config"], a["metrics"]["window"], a["metrics"]["costs"]))
    print(f"{'run_id':<18} {'cfg':<3} {'window':<8} {'costs':<8} {'id':<11} {'mode':<8} "
          f"{'ret%':>9} {'pfs':>6} {'pf':>6} {'n':>5} {'h1':>6} {'h2':>6} "
          f"{'GYR':>4} {'B&H':>9} {'beat':>4} {'conc>0':>6} {'dragpp':>7} {'fees/g':>7} {'PASS':>4}")
    pass_count = {}
    for a in arts:
        m = a["metrics"]
        window = m["window"]
        for r in a["tables"]:
            if "error" in r:
                print(f"{a['run_id']:<18} {m['config']:<3} {window:<8} {m['costs']:<8} "
                      f"{r['id']:<11} {r['mode']:<8} ERROR {r['error']}")
                continue
            pf_gate = r["pf_strict"] if r["mode"] == "discrete" else r["pf"]
            g1 = (pf_gate or 0) > 1.2
            g2 = (r["n_trades"] or 0) >= 30
            pf_h1, pf_h2 = r.get("pf_h1"), r.get("pf_h2")
            g3 = (pf_h1 is not None and pf_h1 > 1 and pf_h2 is not None and pf_h2 > 1)
            yrs = r.get("year_returns") or []
            n_yr = len(yrs)
            n_green = len([y for y in yrs if y["ret_pct"] > 0])
            g4 = (n_yr >= 3 and n_green * 3 >= n_yr * 2) if window == "full" else None
            g5 = bool(r.get("beats_bh"))
            c = r.get("conc_net_without_top5_pct")
            g6 = c is not None and c > 0
            gates = [g1, g2, g3] + ([g4] if g4 is not None else []) + [g5, g6]
            passed = all(gates)
            key = (m["config"], window, m["costs"])
            pass_count[key] = pass_count.get(key, 0) + (1 if passed else 0)
            drag = r.get("drag_pp")
            cs = r.get("cost_share_pct")
            print(f"{a['run_id']:<18} {m['config']:<3} {window:<8} {m['costs']:<8} {r['id']:<11} "
                  f"{r['mode']:<8} {r['ret_pct']:>9.2f} "
                  f"{'—' if pf_gate is None else format(pf_gate, '.2f'):>6} "
                  f"{'—' if r['pf'] is None else format(r['pf'], '.2f'):>6} "
                  f"{r['n_trades'] or 0:>5} "
                  f"{'—' if pf_h1 is None else format(pf_h1, '.2f'):>6} "
                  f"{'—' if pf_h2 is None else format(pf_h2, '.2f'):>6} "
                  f"({'%d/%d' % (n_green, n_yr) if n_yr else 'n/a'}) "
                  f"{m['bench_ret_pct']:>9.2f} {'yes' if g5 else 'no':>4} "
                  f"{'ok' if g6 else 'no':>6} "
                  f"{'—' if drag is None else format(drag, '.1f'):>7} "
                  f"{'—' if cs is None else format(cs, '.1f'):>7} "
                  f"{'PASS' if passed else 'fail':>4}")
    print("\nGate-pass counts by cell (in words):")
    for k, v in sorted(pass_count.items()):
        names = {
            ("c5", "full", "author"): "five-pair author universe, full history, author costs",
            ("c5", "full", "repo6x5"): "five-pair author universe, full history, repo costs",
            ("c5", "last6mo", "author"): "five-pair author universe, last-6-months, author costs",
            ("c5", "last6mo", "repo6x5"): "five-pair author universe, last-6-months, repo costs",
            ("c4", "full", "author"): "prior 4-pair config, full history, author costs",
            ("c4", "full", "repo6x5"): "prior 4-pair config, full history, repo costs",
            ("c4", "last6mo", "author"): "prior 4-pair config, last-6-months, author costs",
            ("c4", "last6mo", "repo6x5"): "prior 4-pair config, last-6-months, repo costs",
        }
        print(f"  {k[0]}/{k[1]}/{k[2]}: {v} of twenty strategies pass G1..G6 ({names[k]})")


if __name__ == "__main__":
    main(sys.argv[1:])
