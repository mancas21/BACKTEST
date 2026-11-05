#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_artifact_metrics.py — print one run-artifact's metrics block.

Usage:  python code/_artifact_metrics.py <run_id> [run_id ...]
        python code/_artifact_metrics.py --gate <run_id> [...]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(os.path.dirname(HERE), "results", "runs")

GATE_KEYS = ["ret_pct", "bench_ret_pct", "beats_bh", "n", "n_open", "pf_strict",
             "pf_h1", "n_h1", "pf_h2", "n_h2",
             "conc_top5_share_pct", "conc_net_without_top5_pct",
             "drag_pp", "fee_over_gross_pct", "dd_pct",
             "win_rate_strict_pct", "ret_zero_pct", "n_signals_long",
             "n_signals_short", "bars", "scored_bars"]


def load(run_id):
    p = os.path.join(RUNS, run_id + ".json")
    if not os.path.exists(p):
        raise SystemExit("no artifact " + p)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    gate_mode = argv[1] == "--gate"
    ids = argv[2:] if gate_mode else argv[1:]
    out = []
    for rid in ids:
        a = load(rid)
        m = a.get("metrics", {})
        if gate_mode:
            row = {"run_id": rid, "strategy": a["strategy"],
                   "tf": a["timeframe"], "symbol": a["symbol"],
                   "window": m.get("window"), "costs": m.get("costs")}
            row.update({k: m.get(k) for k in GATE_KEYS if k in m})
            out.append(row)
        else:
            out.append({"run_id": rid, "strategy": a["strategy"],
                        "tf": a["timeframe"], "symbol": a["symbol"], "metrics": m})
    if len(out) == 1:
        print(json.dumps(out[0], indent=2))
    else:
        keep = ["symbol", "tf", "window", "costs", "ret_pct", "bench_ret_pct",
                "n", "pf_strict", "pf_h1", "pf_h2", "conc_net_without_top5_pct",
                "drag_pp", "beats_bh"]
        hdr = ["run_id"] + keep
        print("\t".join(hdr))
        for row in out:
            print("\t".join(str(row.get(k, "-"))[:10] for k in hdr))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
