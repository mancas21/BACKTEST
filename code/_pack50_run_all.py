#!/usr/bin/env python
"""_pack50_run_all.py -- create one artifact per runnable prompt in the pack.

Writes results/runs/<run_id>.json for every strategy that has data on disk and
prints `strat<TAB>run_id` so the report builder can cite the ids without
copying them by hand. S34 and S49 are skipped by construction (no NVDA data).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vrun
import pack50_strats as S

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "_pack50_ids.json")


def main() -> int:
    rows = {}
    for sid in sorted(S.SPECS):
        spec = S.SPECS[sid]
        if spec.get("no_data"):
            print(f"S{sid:02d}\tNO_DATA\t{spec['no_data']}")
            continue
        a = vrun.make_artifact("pack50", spec["tf"], spec["sym"], {"strat": sid})
        p = vrun.save_artifact(a)
        rows[str(sid)] = {"run_id": a["run_id"], "symbol": spec["sym"],
                          "tf": spec["tf"], "name": spec["name"],
                          "artifact": p}
        m = a["metrics"]
        print(f"S{sid:02d}\t{a['run_id']}\tn={m['n_trades']}\tret={m['return_pct']:.2f}\t"
              f"pf={m['profit_factor']}\tbars={m['bars']}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, sort_keys=True)
    print("ids written to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
