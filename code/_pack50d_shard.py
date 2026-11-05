#!/usr/bin/env python
"""_pack50d_shard.py -- run one shard of pack50d prompts (same contract as
_pack50c_run_shard.py). Usage: python _pack50d_shard.py <shard> <n_shards>."""
from __future__ import annotations
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vrun
import pack50d_strats as SD
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
i, n = int(sys.argv[1]), int(sys.argv[2])
runnable = [sid for sid in sorted(SD.SPECS) if not SD.SPECS[sid].get("no_data")]
out = {}
for sid in runnable[i::n]:
    spec = SD.SPECS[sid]
    code = SD.CODE[sid]
    try:
        a = vrun.make_artifact("pack50d", spec["tf"], spec["sym"], {"strat": sid})
        vrun.save_artifact(a)
        m = a["metrics"]
        out[str(sid)] = {"run_id": a["run_id"], "code": code, "name": spec["name"],
                         "sym": spec["sym"], "tf": spec["tf"]}
        v1 = "".join(k[1] for k in ("g1_pf", "g2_n", "g3_halves", "g4_years",
                                    "g5_beats_bh", "g6_conc") if not m["v1"][k])
        v2 = "".join(k[1] for k in ("g1v2_lb_pos", "g2v2_n", "g3v2_split_folds",
                                    "g4v2_buckets", "g5v2_alpha_t", "g6v2_conc",
                                    "g8_cost", "g9v2_dd") if not m[k])
        print(f"{code}\t{a['run_id']}\tn={m['n_trades']}\tpackPF={m['pack_pf']}"
              f"\tzeroPF={m['zero_cost_pf']}\texpLB={m['expectancy_lb95_bps']}"
              f"\tbe={m['breakeven_side_cost_bps']}\tv1={v1 or 'none'}\tv2={v2 or 'none'}",
              flush=True)
    except Exception as e:
        print(f"{code}\tERROR\t{type(e).__name__}: {e}", flush=True)
with open(os.path.join(ROOT, "results", f"_pack50d_shard_{i}.json"), "w") as f:
    json.dump(out, f, indent=2)
print("shard", i, "done", flush=True)
