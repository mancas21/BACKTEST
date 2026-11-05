#!/usr/bin/env python
"""_qsd_shard.py -- run one shard of the family-D campaign.
Usage: python _qsd_shard.py <shard> <n_shards>
Cells: 10 IDs x 2 variants x 6 symbols x 3 TFs = 360 total."""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vrun
import qs_d_strats          # noqa: F401  registers the family-D specs
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
i, n = int(sys.argv[1]), int(sys.argv[2])
FAMILY_D = ("QS-031", "QS-032", "QS-033", "QS-034", "QS-035",
            "QS-036", "QS-037", "QS-038", "QS-039", "QS-040")
jobs = []
for sid in FAMILY_D:
    for variant in ("two-sided", "long-only"):
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "HYPEUSDT", "SUIUSDT", "JUPUSDT"):
            for tf in ("5m", "15m", "1h"):
                jobs.append((sid, variant, sym, tf))
mine = jobs[i::n]
out = {}
for sid, variant, sym, tf in mine:
    try:
        a = vrun.make_artifact("qsd", tf, sym,
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
with open(os.path.join(ROOT, "results", f"_qsd_shard_{i}.json"), "w") as f:
    json.dump(out, f, indent=2)
print("shard", i, "done", flush=True)
