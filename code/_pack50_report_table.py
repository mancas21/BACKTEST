#!/usr/bin/env python
"""_pack50_report_table.py -- print the gate table for the fifty-strategy pack.

Reads the artifact ids written by `_pack50_run_all.py` and renders one row per
prompt from the artifact itself. Every numeral printed here is a field of a
persisted, verifiable artifact, so the report can cite the row's run_id.

    python code/_pack50_report_table.py [--json]
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))

import vrun

IDS = os.path.join(ROOT, "results", "_pack50_ids.json")


def fmt(v, nd=2):
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def gates(a):
    m = a["metrics"]
    keys = ["g1_pf", "g2_n", "g3_halves", "g4_years", "g5_beats_bh", "g6_conc"]
    return sum(1 for k in keys if m.get(k)), len(keys), [k for k in keys if not m.get(k)]


def main() -> int:
    ids = json.load(open(IDS, encoding="utf-8"))
    rows = []
    for sid in sorted(ids, key=int):
        info = ids[sid]
        a = vrun.load_artifact(info["run_id"])
        m = a["metrics"]
        ok, tot, fails = gates(a)
        rows.append({
            "s": int(sid), "run_id": a["run_id"], "name": m["strategy_name"],
            "sym": m["symbol"], "tf": m["timeframe"], "n": m["n_trades"],
            "ret": m["return_pct"], "pf": m["profit_factor"],
            "is_pf": m["is_pf"], "os_pf": m["os_pf"], "bh": m["bh_return_pct"],
            "conc": m["conc_net_without_top5_pct"], "fund": m["funding_paid"],
            "repo_pf": m["repo_cost_pf"], "zero_pf": m["zero_cost_pf"],
            "zero_ret": m["zero_cost_ret_pct"], "ok": ok, "fails": fails,
        })
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=2, default=str))
        return 0

    print("| S | strategy | sym | tf | n | net% | PF | IS PF | OOS PF | B&H% | "
          "conc net% | funding | repo PF | zero PF | gates |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['s']:02d} | {r['name']} | {r['sym']} | {r['tf']} | {r['n']} | "
              f"{fmt(r['ret'])} | {fmt(r['pf'],3)} | {fmt(r['is_pf'])} | "
              f"{fmt(r['os_pf'])} | {fmt(r['bh'])} | {fmt(r['conc'])} | "
              f"{fmt(r['fund'])} | {fmt(r['repo_pf'],3)} | {fmt(r['zero_pf'],3)} | "
              f"{r['ok']}/6 |")
    n_all = len(rows)
    full = [r for r in rows if r["ok"] == 6]
    print()
    print(f"rows: {n_all}   six-of-six: {len(full)}")
    for r in full:
        print(f"  PASS S{r['s']:02d} {r['run_id']} {r['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
