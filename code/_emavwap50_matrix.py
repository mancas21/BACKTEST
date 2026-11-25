"""Run the EMA×VWAP suite: one BTCUSDT artifact per runnable row, plus a
NO-DATA ledger for the refused rows. No gate is applied here; the report
applies the pre-registered screen from the artifacts' own metrics.

Run: python code/_emavwap50_matrix.py
"""
import json
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402
import emavwap50_engine as E  # noqa: E402

OUT = os.path.join(ROOT, "results", "emavwap50_matrix.json")


def main():
    cells = {}
    for rid, tf in sorted(E.RUNNABLE.items()):
        print(f"[row {rid:02d} {tf}] ...", flush=True)
        a = V.make_artifact("emavwap50", tf, "BTCUSDT", {"id": rid})
        p = V.save_artifact(a)
        m = a["metrics"]
        cells[str(rid)] = {"run_id": a["run_id"], "tf": tf,
                           "artifact": os.path.relpath(p, ROOT).replace("\\", "/"),
                           "cut_ts": a["core"].get("cut_ts"),
                           "inputs": [os.path.basename(i["path"]) for i in a["inputs"]]}
        print(f"    {a['run_id']}  net {m['net_pct']:.2f}%  PF "
              f"{m['profit_factor']}  n {m['n_trades']}", flush=True)
    payload = {"campaign": "emavwap50-2026-11-25", "cells": cells,
               "no_data": {str(k): v for k, v in sorted(E.NO_DATA.items())},
               "note": "one BTCUSDT cell per runnable row; see "
                       "results/emavwap50_pre_registration.md"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, default=str)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
