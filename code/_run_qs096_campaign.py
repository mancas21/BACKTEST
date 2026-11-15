#!/usr/bin/env python
"""_run_qs096_campaign.py -- execute the full QS-096 matrix campaign and benchmark live."""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import vrun

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"]
TIMEFRAMES = ["1h", "15m", "5m"]
VARIANTS = ["two_side", "long"]

results = []

print(f"{'Cell':<25} {'Run ID':<18} {'Trades':<8} {'PF':<8} {'Net %':<10} {'Win %':<8} {'Time (s)':<10} {'Status'}")
print("-" * 100)

for tf in TIMEFRAMES:
    for sym in SYMBOLS:
        for var in ["two_side"]:  # Primary two-sided hypothesis first
            t0 = time.time()
            cell_label = f"{sym}_{tf}_{var}"
            try:
                # Use make_artifact to persist under REGLA 0
                params = {"variant": var, "cost": "gate"}
                art = vrun.make_artifact("qs096", tf, sym, params)
                vrun.save_artifact(art)
                elapsed = time.time() - t0
                m = art["metrics"]
                rid = art["run_id"]
                n = m.get("n_trades", 0)
                pf = round(m.get("profit_factor", 0.0), 3)
                net = round(m.get("return_pct", 0.0), 2)
                wr = round(m.get("win_rate", 0.0), 1)
                gate = "PASS" if m.get("gate_all") else "KILL"
                print(f"{cell_label:<25} {rid:<18} {n:<8} {pf:<8} {net:<10} {wr:<8} {elapsed:<10.2f} {gate}")
                results.append({"cell": cell_label, "sym": sym, "tf": tf, "var": var,
                                "run_id": rid, "n": n, "pf": pf, "net": net, "wr": wr,
                                "time": elapsed, "gate": gate, "metrics": m})
            except Exception as e:
                elapsed = time.time() - t0
                print(f"{cell_label:<25} {'ERROR':<18} {'-':<8} {'-':<8} {'-':<8} {'-':<8} {elapsed:<10.2f} {str(e)[:30]}")

print("-" * 100)
