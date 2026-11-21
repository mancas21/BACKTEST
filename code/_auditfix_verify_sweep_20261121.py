#!/usr/bin/env python
"""Verify sweep for the 2026-11-21 audit-fix re-runs.

Verifies every artifact of the current p100screen cell generation plus the
new gatecal calibration, and prints the OK/REFUSED tally with exit codes.

    python code/_auditfix_verify_sweep_20261121.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
CELLS = os.path.join(ROOT, "results", "_p100_cells")
CELLS_DIR = os.path.join(ROOT, "results", "_p100_cells")
EXTRA = ["d590af40751a6002"]          # the current gatecal calibration (gen-3)


def main():
    rids = set(EXTRA)
    src = CELLS if os.path.isdir(CELLS) else CELLS_DIR
    for fn in os.listdir(src):
        if fn.endswith(".json"):
            d = json.load(open(os.path.join(src, fn), encoding="utf-8"))
            if d.get("run_id"):
                rids.add(d["run_id"])
    ok = refused = stale = other = 0
    refused_ids = []
    for rid in sorted(rids):
        p = subprocess.run(
            [sys.executable, "-X", "utf8", os.path.join(HERE, "vrun.py"),
             "verify", rid],
            cwd=ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        txt = (p.stdout or "") + (p.stderr or "")
        if "OK:" in txt:
            ok += 1
        elif "REFUSED" in txt:
            refused += 1
            refused_ids.append(rid)
        elif "STALE" in txt:
            stale += 1
        else:
            other += 1
            print(f"  ?? {rid}: {txt.strip()[-200:]}")
    print(f"verify sweep: {ok} OK / {refused} REFUSED / {stale} STALE / "
          f"{other} other -- of {len(rids)} artifacts")
    if refused_ids:
        print("  REFUSED:", ", ".join(refused_ids))
    return 0 if (refused == 0 and stale == 0 and other == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
