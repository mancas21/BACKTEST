#!/usr/bin/env python
"""_scalpma20_report.py -- aggregate the 120 scalpma20 screen artifacts into a
machine-readable matrix + the measured summary for the verdict report.
Every number comes from a persisted artifact (REGLA 0). Cites per-id run_ids
(REGLA 1: no 'best of family' claim)."""
from __future__ import annotations
import json, glob, os
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
# 2026-11-19 audit fixes: only the FIXED-engine artifacts are current. The 120
# pre-fix artifacts (engine_sha256 7ded8133...) are orphaned by design (engine
# drift) and kept append-only; they are NOT cited here.
NEW_SHA = "cbe3954bd6ab8626eb39fff0b214b94e63e4f2d96d1a919fb13df4a01728d817"

KEEP = ["strategy_id","strategy_name","symbol","timeframe","return_pct","profit_factor",
        "n_trades","win_rate","max_dd_pct","oos_profit_factor","oos_return_pct","oos_n_trades",
        "ret_zero_pct","pf_zero","n_zero","drag_pp","fees_paid_usdt","funding_paid_usdt",
        "funding_charged","funding_covers_bars","signal_rows","signal_gated","signal_gate_pass",
        "n_periods_green","best5_share_pct","boot_ci_lo","boot_ci_hi","boot_p_le_zero",
        "gate_pf","gate_n","gate_net","gate_thirds","gate_oos","gate_conc","gate_boot_ci","gate_all",
        "inv_gap_usd","n_bars","avg_bars_held","cost_bp_roundtrip"]

rows = []
for f in glob.glob(os.path.join(RUNS, "*.json")):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    if d.get("strategy") != "scalpma20":
        continue
    if (d.get("core") or {}).get("engine_sha256") != NEW_SHA:
        continue   # skip orphaned pre-fix artifacts
    m = d.get("metrics", {})
    r = {k: m.get(k) for k in KEEP}
    r["run_id"] = d.get("run_id")
    r["label"] = f"sm20_{int(m.get('strategy_id',0)):02d}_{m.get('symbol')}_{m.get('timeframe')}"
    r["created"] = d.get("created_utc")
    rows.append(r)

rows.sort(key=lambda r: (r["strategy_id"], r["symbol"], r["timeframe"]))
print(f"loaded {len(rows)} scalpma20 artifacts")

def cnt(pred):
    return sum(1 for r in rows if pred(r))

pf = np.array([r["profit_factor"] for r in rows if r["profit_factor"] is not None])
pfz = np.array([r["pf_zero"] for r in rows if r["pf_zero"] is not None])
net = np.array([r["return_pct"] for r in rows if r["return_pct"] is not None])
oos = np.array([r["oos_profit_factor"] for r in rows if r["oos_profit_factor"] is not None])
fees = np.array([r["fees_paid_usdt"] for r in rows if r["fees_paid_usdt"] is not None])
ident = np.array([abs(r["inv_gap_usd"]) for r in rows if r["inv_gap_usd"] is not None])

summary = {
    "n_cells": len(rows),
    "n_gate_all_pass": cnt(lambda r: r["gate_all"]),
    "n_pf_gt_1": cnt(lambda r: (r["profit_factor"] or 0) > 1.0),
    "n_pf_gt_1_2": cnt(lambda r: (r["profit_factor"] or 0) > 1.2),
    "n_net_gt_0": cnt(lambda r: (r["return_pct"] or 0) > 0),
    "n_oos_pf_gt_1": cnt(lambda r: (r["oos_profit_factor"] or 0) > 1.0),
    "n_oos_pf_gt_1_2": cnt(lambda r: (r["oos_profit_factor"] or 0) > 1.2),
    "n_zero_pf_gt_1": cnt(lambda r: (r["pf_zero"] or 0) > 1.0),
    "n_zero_pf_gt_1_2": cnt(lambda r: (r["pf_zero"] or 0) > 1.2),
    "n_zero_net_gt_0": cnt(lambda r: (r["ret_zero_pct"] or 0) > 0),
    "pf_min": float(pf.min()), "pf_max": float(pf.max()), "pf_median": float(np.median(pf)),
    "pf_zero_min": float(pfz.min()), "pf_zero_max": float(pfz.max()), "pf_zero_median": float(np.median(pfz)),
    "net_min": float(net.min()), "net_max": float(net.max()),
    "oos_pf_min": float(oos.min()), "oos_pf_max": float(oos.max()),
    "total_fees_usdt": float(fees.sum()),
    "max_identity_resid": float(ident.max()),
    "n_funding_charged": cnt(lambda r: r["funding_charged"]),
    "n_funding_covers": cnt(lambda r: r["funding_covers_bars"]),
    "total_signal_rows": int(sum(r["signal_rows"] or 0 for r in rows)),
    "total_signal_gated": int(sum(r["signal_gated"] or 0 for r in rows)),
}
# per-timeframe rollup
for tf in ("5m","1m"):
    sub = [r for r in rows if r["timeframe"]==tf]
    summary[f"{tf}_cells"] = len(sub)
    summary[f"{tf}_pf_max"] = float(max((r["profit_factor"] or 0) for r in sub))
    summary[f"{tf}_pf_zero_max"] = float(max((r["pf_zero"] or 0) for r in sub))
    summary[f"{tf}_net_max"] = float(max((r["return_pct"] or -1e9) for r in sub))
    summary[f"{tf}_n_pf_gt_1"] = sum(1 for r in sub if (r["profit_factor"] or 0)>1.0)
    summary[f"{tf}_n_zero_pf_gt_1"] = sum(1 for r in sub if (r["pf_zero"] or 0)>1.0)

out = {"summary": summary, "cells": rows}
op = os.path.join(ROOT, "results", "scalpma20_matrix.json")
json.dump(out, open(op,"w",encoding="utf-8"), indent=1)
print(json.dumps(summary, indent=1))
print(f"\nsaved -> {op}")

# best cells by net (for honest reporting of the least-bad, still failing)
best = sorted(rows, key=lambda r: -(r["return_pct"] or -1e9))[:6]
print("\nleast-bad 6 cells (ALL still fail the battery):")
for r in best:
    print(f"  {r['label']:<24} {r['run_id']}  net={r['return_pct']:+.2f}%  PF={r['profit_factor']:.3f}  "
          f"OOS_PF={r['oos_profit_factor']:.3f}  zeroPF={r['pf_zero']:.3f}  n={r['n_trades']}  gate_all={r['gate_all']}")
