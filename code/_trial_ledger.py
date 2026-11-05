#!/usr/bin/env python
"""_trial_ledger.py -- the append-only trial ledger, counted from the artifact store.

The v2 gate layer needs a trial count N for the deflated Sharpe ratio and the
program-level haircut (audit C1). The store of run artifacts IS the ledger:
every artifact is one tried candidate. This script walks results/runs/*.json,
groups them by strategy (adapter) and engine version, and writes
results/_trial_ledger.json with the counts and per-strategy lists of run_ids.

Re-run after every campaign; the file is a derived view of the append-only
store, not an independent record.
"""
from __future__ import annotations

import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "_trial_ledger.json")


def main() -> int:
    rows = []
    for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                a = json.load(f)
        except Exception:
            continue
        meta = a.get("meta") or a.get("engine_meta") or {}
        rows.append({
            "run_id": a.get("run_id"),
            "strategy": a.get("strategy"),
            "engine_version": (a.get("engine") or {}).get("engine_version")
                              or meta.get("engine_version"),
            "ts": a.get("created_utc") or a.get("created"),
        })
    by_strat = {}
    for r in rows:
        by_strat.setdefault(r["strategy"] or "unknown", []).append(r["run_id"])
    ledger = {
        "generated": "results/_trial_ledger.json",
        "note": "derived view of the append-only results/runs store; one artifact = one tried candidate",
        "total_artifacts": len(rows),
        "by_strategy": {k: {"n": len(v), "run_ids": v} for k, v in sorted(by_strat.items())},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, sort_keys=True)
    print(f"total tried candidates (artifacts): {len(rows)}")
    for k, v in sorted(by_strat.items()):
        print(f"  {k:12s} {len(v)}")
    print("wrote", OUT)
    sys.exit(chain_output(rows))




def chain_output(rows) -> int:
    """Also emit the hash-chained JSONL ledger (the reference layer's
    TrialLedger format), one entry per artifact, deterministic order. This is
    the tamper-evident form of the trial count; the JSON view above stays the
    human-readable one."""
    import _gates_v2 as G
    path = os.path.join(ROOT, "results", "_trial_ledger.jsonl")
    if os.path.exists(path):
        os.remove(path)
    led = G.TrialLedger(path)
    for r in rows:                      # rows are already sorted by path
        if r["run_id"]:
            led.register(r["strategy"] or "unknown", r["run_id"], 1)
    ok, bad = led.verify()
    print(f"chained ledger: {led.total_trials()} trials, verify: {'OK' if ok else 'BROKEN'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
