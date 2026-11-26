"""Run the Non-Trend 50 Suite: rows 51-92 first (one artifact per row on
its declared universe). Composites 93-100 are a second phase and are only
attempted if their source sleeves cleared the gates on their own, per the
attachment. No gate is applied here: the matrix stores what the artifacts
say; the report applies the pre-registered gates.

Run: python code/_nontrend50_matrix.py
"""
import json
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402

OUT = os.path.join(ROOT, "results", "nontrend50_matrix.json")


def pseudo(row):
    if 51 <= row <= 68 or 83 <= row <= 92:
        return "U_1H", "1h"
    if 69 <= row <= 76:
        return "T_5M", "5m"
    return "F_1H", "1h"


def main():
    cells = {}
    no_data = {r: "overlay not faithfully implemented (pre-registration addendum)"
               for r in (65, 66, 68)}
    for row in range(51, 93):
        if row in no_data:
            continue
        sym, tf = pseudo(row)
        print(f"[row {row} {sym}] ...", flush=True)
        a = V.make_artifact("nontrend50", tf, sym, {"id": row})
        p = V.save_artifact(a)
        m = a["metrics"]
        cells[str(row)] = {"run_id": a["run_id"], "tf": tf, "universe": m["universe"],
                           "artifact": os.path.relpath(p, ROOT).replace("\\", "/"),
                           "cut_ts": a["core"].get("cut_ts"),
                           "inputs": [os.path.basename(i["path"]) for i in a["inputs"]],
                           "gate_pass": bool(m["gate_pass"]),
                           "gates": m["gates"]}
        print(f"    {a['run_id']}  net {m['net_pct']:.2f}%  PF "
              f"{m['profit_factor']}  n {m['n_trades']}  gates "
              f"{sum(m['gates'].values())}/{len(m['gates'])}", flush=True)
    payload = {"campaign": "nontrend50-2026-11-26", "cells": cells,
               "no_data": {str(k): v for k, v in no_data.items()},
               "composites": "phase 2 — only if source sleeves pass",
               "note": "see results/nontrend50_pre_registration.md"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, default=str)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
