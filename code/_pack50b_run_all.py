#!/usr/bin/env python
"""_pack50b_run_all.py -- create one artifact per runnable prompt in the
claude2 fifty-prompt pack.

Writes results/runs/<run_id>.json for every strategy that has data on disk and
prints `code<TAB>run_id` so the report builder can cite the ids without copying
them by hand. S08, S23, D08 and D18 are skipped by construction (no NVDA data).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vrun
import pack50b_strats as SB

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "_pack50b_ids.json")


def main() -> int:
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    rows = {}
    if os.path.exists(OUT) and not only:
        rows = json.load(open(OUT, encoding="utf-8"))
    for sid in sorted(SB.SPECS):
        code = SB.CODE[sid]
        if only and code not in only:
            continue
        spec = SB.SPECS[sid]
        if spec.get("no_data"):
            print(f"{code}\tNO_DATA\t{spec['no_data']}")
            continue
        a = vrun.make_artifact("pack50b", spec["tf"], spec["sym"], {"strat": sid})
        p = vrun.save_artifact(a)
        rows[str(sid)] = {"run_id": a["run_id"], "symbol": spec["sym"],
                          "tf": spec["tf"], "name": spec["name"],
                          "code": code, "artifact": p}
        m = a["metrics"]
        print(f"{code}\t{a['run_id']}\tn={m['n_trades']}\tret={m['return_pct']:.2f}\t"
              f"pf={m['profit_factor']}\tzero={m['zero_cost_pf']}\tbars={m['bars']}\t"
              f"gates={''.join('G1' if not m['g1_pf'] else '')}"
              f"{'G2' if not m['g2_n'] else ''}{'G3' if not m['g3_halves'] else ''}"
              f"{'G4' if not m['g4_years'] else ''}{'G5' if not m['g5_beats_bh'] else ''}"
              f"{'G6' if not m['g6_conc'] else ''}")
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, sort_keys=True)
    print("ids written to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
