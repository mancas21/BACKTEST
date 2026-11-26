"""Run the MTF top-down cell: SOLUSDT 5m, repo cost regime + real funding.
Author-cost and zero-cost controls are measured inside the same artifact.

Run: python code/_mtf_topdown_matrix.py
"""
import json
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402

OUT = os.path.join(ROOT, "results", "mtf_topdown_matrix.json")


def main():
    a = V.make_artifact("mtftopdown", "5m", "SOLUSDT", {"costs": "repo"})
    p = V.save_artifact(a)
    rec = {"run_id": a["run_id"], "params": {"costs": "repo"},
           "artifact": os.path.relpath(p, ROOT).replace("\\", "/"),
           "cut_ts": a["core"].get("cut_ts"),
           "inputs": [os.path.basename(i["path"]) for i in a["inputs"]]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"campaign": "mtftopdown-2026-11-26", "cells": [rec]},
                  f, indent=1, sort_keys=False)
    print(rec["run_id"], "->", OUT)
    print(json.dumps(a["metrics"], indent=1, default=str))


if __name__ == "__main__":
    main()
