#!/usr/bin/env python
"""_qsc_shard.py -- run one shard of the family-C campaign.
Usage: python _qsc_shard.py <shard> <n_shards>
Cells: 9 single-leg IDs x 2 variants x 6 symbols x 3 TFs
     + QS-024 (BTC/ETH/SOL, 5m/15m only) x 2 variants = 336 total."""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vrun
import qs_c_strats          # noqa: F401  registers the family-C specs
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
i, n = int(sys.argv[1]), int(sys.argv[2])
FAMILY_C = ("QS-021", "QS-022", "QS-023", "QS-025", "QS-026", "QS-027",
            "QS-028", "QS-029", "QS-030")
jobs = []
for sid in FAMILY_C:
    for variant in ("two-sided", "long-only"):
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"):
            for tf in ("5m", "15m", "1h"):
                jobs.append((sid, variant, sym, tf))
for variant in ("two-sided", "long-only"):
    for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
        for tf in ("5m", "15m"):
            jobs.append(("QS-024", variant, sym, tf))
mine = jobs[i::n]
out = {}
for sid, variant, sym, tf in mine:
    try:
        a = vrun.make_artifact("qsc", tf, sym,
                               {"strat": sid, "variant": variant})
        vrun.save_artifact(a)
        m = a["metrics"]
        out[f"{sid}|{variant}|{sym}|{tf}"] = a["run_id"]
        fails = "".join(k for k in ("g1_data", "g2_causality", "g4_econ",
                                    "g5_stat", "g6_robust", "g7_oper")
                        if not m["gates"][k])
        print(f"{sid} {variant[:4]} {sym[:9]:9s} {tf} n={m['n_trades']:5d} "
              f"exp={m['exp_base_bps']} adv={m['exp_adverse_bps']} verdict={m['verdict']}"
              f"{' ES' if m['execution_sensitive'] else ''}"
              f"{'' if not fails else ' F:' + fails}", flush=True)
    except Exception as e:
        print(f"{sid} {variant[:4]} {sym[:9]:9s} {tf} ERROR {type(e).__name__}: {e}",
              flush=True)
with open(os.path.join(ROOT, "results", f"_qsc_shard_{i}.json"), "w") as f:
    json.dump(out, f, indent=2)
print("shard", i, "done", flush=True)
