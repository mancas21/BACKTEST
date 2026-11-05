#!/usr/bin/env python
"""_pack50c_run_shard.py -- run one shard of pack50c prompts.

Usage: python _pack50c_run_shard.py <shard_index> <n_shards>
Writes results/_pack50c_shard_<i>.json; the merge step assembles
results/_pack50c_ids.json. Artifacts are append-only, so a re-run of an
already-built prompt simply creates the same run_id again (deterministic).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vrun
import pack50c_strats as SC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

i = int(sys.argv[1])
n = int(sys.argv[2])
runnable = [sid for sid in sorted(SC.SPECS) if not SC.SPECS[sid].get("no_data")]
mine = runnable[i::n]
out = {}
for sid in mine:
    spec = SC.SPECS[sid]
    code = SC.CODE[sid]
    try:
        a = vrun.make_artifact("pack50c", spec["tf"], spec["sym"], {"strat": sid})
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
with open(os.path.join(ROOT, "results", f"_pack50c_shard_{i}.json"), "w") as f:
    json.dump(out, f, indent=2)
print("shard", i, "done", flush=True)
