#!/usr/bin/env python
"""_qsf_shard.py -- run one shard of the trade-flow campaign.
Usage: python _qsf_shard.py <shard> <n_shards>"""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vrun
import qs_flow_strats          # noqa: F401  registers the flow specs
import qs_strats as SD
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
i, n = int(sys.argv[1]), int(sys.argv[2])
FLOW = ["QS-043", "QS-044", "QS-048", "QS-049", "QS-050", "QS-053",
        "QS-058", "QS-093"]
jobs = []
for sid in FLOW:
    for variant in ("two-sided", "long-only"):
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"):
            for tf in ("5m", "15m", "1h"):
                jobs.append((sid, variant, sym, tf))
mine = jobs[i::n]
out = {}
for sid, variant, sym, tf in mine:
    try:
        a = vrun.make_artifact("qsf", tf, sym,
                               {"strat": sid, "variant": variant})
        vrun.save_artifact(a)
        m = a["metrics"]
        out[f"{sid}|{variant}|{sym}|{tf}"] = a["run_id"]
        fails = "".join(k[1] for k in ("g1_data", "g2_causality", "g4_econ",
                                       "g5_stat", "g6_robust", "g7_oper")
                        if not m["gates"][k])
        print(f"{sid} {variant[:4]} {sym[:3]} {tf} n={m['n_trades']:5d} "
              f"exp={m['exp_base_bps']} adv={m['exp_adverse_bps']} "
              f"verdict={m['verdict']}{' ES' if m['execution_sensitive'] else ''}"
              f"{'' if not fails else ' F:' + fails}", flush=True)
    except Exception as e:
        print(f"{sid} {variant[:4]} {sym[:3]} {tf} ERROR {type(e).__name__}: {e}",
              flush=True)
with open(os.path.join(ROOT, "results", f"_qsf_shard_{i}.json"), "w") as f:
    json.dump(out, f, indent=2)
print("shard", i, "done", flush=True)
