"""Run EMA×VWAP Suite 2: one BTCUSDT artifact per runnable row (#101–150).
Rows 148/149 are declared NO DATA (selector book not faithfully ported).

Run: python code/_emavwapv2_matrix.py
"""
import json
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402
import emavwapv2_engine as E  # noqa: E402

OUT = os.path.join(ROOT, "results", "emavwapv2_matrix.json")


def main():
    cells = {}
    no_data = {str(r): "cross-sectional selector book not faithfully implemented"
               for r in (148, 149)}
    for row in range(101, 151):
        if row in (148, 149):
            continue
        tf = E.ROWS2[row]
        print(f"[row {row} {tf}] ...", flush=True)
        a = V.make_artifact("emavwapv2", tf, "BTCUSDT", {"id": row})
        p = V.save_artifact(a)
        m = a["metrics"]
        cells[str(row)] = {"run_id": a["run_id"], "tf": tf,
                           "artifact": os.path.relpath(p, ROOT).replace("\\", "/"),
                           "cut_ts": a["core"].get("cut_ts"),
                           "inputs": [os.path.basename(i["path"]) for i in a["inputs"]],
                           "gate_pass": bool(m["gate_pass"])}
        print(f"    {a['run_id']}  net {m['net_pct']:.2f}%  PF "
              f"{m['profit_factor']}  n {m['n_trades']}  ctrl "
              f"{m['control_net_pct']:.2f}%  gates {sum(m['gates'].values())}", flush=True)
    payload = {"campaign": "emavwapv2-2026-11-26", "cells": cells,
               "no_data": no_data,
               "note": "see results/emavwapv2_pre_registration.md"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, default=str)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
