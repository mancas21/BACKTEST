#!/usr/bin/env python3
"""
_scalp_wave_rank.py — add the WAVE_1 scalp cells to the strategy universe
(`code/_top100_rank.json`), the registry's INPUT (never hand-edited).

The universe file is the registry's source: `strategy_registry.py` reads it
and writes results/registry/. A new adapter's rows have to be there or the
registry does not know the family exists.

Only artifacts produced by the CURRENT engine are added, so the universe never
points at a superseded engine version.

Usage:  python code/_scalp_wave_rank.py
"""
from __future__ import annotations

import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RUNS = os.path.join(ROOT, "results", "runs")
RANK = os.path.join(HERE, "_top100_rank.json")
ENGINE = os.path.join(HERE, "scalp_wave_engine.py")


def engine_sha():
    return hashlib.sha256(open(ENGINE, "rb").read()).hexdigest()


def main():
    sha = engine_sha()
    rows = json.load(open(RANK, encoding="utf-8-sig"))
    have = {r["run_id"] for r in rows}
    added = 0
    skipped = 0
    for fn in sorted(os.listdir(RUNS)):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        try:
            a = json.load(open(os.path.join(RUNS, fn), encoding="utf-8"))
        except Exception:
            continue
        if a.get("strategy") != "scalpwave":
            continue
        if (a.get("provenance") or {}).get("engine_sha256") != sha:
            continue
        params = a.get("params") or {}
        # the universe holds ONE row per book (adapter x symbol x tf x params)
        if a["run_id"] in have:
            skipped += 1
            continue
        m = a["metrics"]
        label = f"WAVE_1 scalp {a['symbol']} {a['timeframe']}"
        if params:
            label += " (" + ",".join(f"{k}={v}" for k, v in sorted(params.items())) + ")"
        rows.append(dict(
            run_id=a["run_id"], adapter="scalpwave", symbol=a["symbol"],
            tf=a["timeframe"], label=label,
            ret=m["return_pct"], pf=m["profit_factor"], n=m["n_trades"],
            dd=m["max_dd_pct"], bh=None,
            fee=m.get("cost_bp_roundtrip"), slip=None,
            funding=a["provenance"].get("funding_charged", False),
            created=a.get("created_utc", "")[:10], gates=None))
        have.add(a["run_id"])
        added += 1
    if added:
        with open(RANK, "w", encoding="utf-8", newline="") as f:
            json.dump(rows, f)
    print(f"rank: {added} rows added, {skipped} already present, "
          f"{len(rows)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
