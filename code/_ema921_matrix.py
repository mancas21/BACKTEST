#!/usr/bin/env python
"""Run the 9-21 EMA grid (adapter `ema921`) over EVERY (symbol, time frame)
pair on disk, through the harness (make_artifact -> save_artifact), in a
process pool.

Universe rule (declared, same as the adapter's inputs):
  * per tf, the union of the native dir and the taker cache;
  * 5m resolves to data/binance_klines_5m (the real history), never
    data/binance_klines (a 30-day stub);
  * a file must be named exactly `<SYM>_<tf>.csv` (the `_tail_` appendices and
    the `.preflight.tmp` leftovers are not series);
  * USDT perps only. SOLUSDC is a spot pair with no funding file: excluded.

Outputs (both new files; artifacts are append-only under results/runs/):
  results/runs/_matrix_ema921.csv         harness index (tf, symbol, run_id, ...)
  results/ema921_matrix_2026-11-17.json   per-cell metrics for the report

Usage:
  python code/_ema921_matrix.py --workers 4 [--tf 1h] [--limit 2]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))

import vrun  # noqa: E402

TFS = ["1m", "5m", "15m", "1h", "1d"]
DATE = "2026-11-17"


def dirs_for(tf):
    if tf == "5m":
        return [os.path.join(vrun.DATA, "binance_klines_5m"),
                vrun.TF_TAKER["5m"][0]], "5m"
    return [vrun.TF_DIR[tf][0], vrun.TF_TAKER[tf][0]], vrun.TF_DIR[tf][1]


def universe(tf):
    dirs, suf = dirs_for(tf)
    syms = set()
    for d in dirs:
        for f in glob.glob(os.path.join(d, f"*_{suf}.csv")):
            sym = os.path.basename(f)[:-(len(suf) + 5)]
            if sym.endswith("_tail") or not sym.endswith("USDT"):
                continue
            if sym == "SOLUSDC":
                continue
            syms.add(sym)
    return sorted(syms)


def worker(job):
    tf, sym, cut = job
    try:
        art = vrun.make_artifact("ema921", tf, sym, {}, cut_ts=cut)
        vrun.save_artifact(art)
        return tf, sym, art["run_id"], None
    except Exception as e:  # never let one cell kill the grid
        return tf, sym, None, f"{type(e).__name__}: {e}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tf", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cut-ts", default="auto")
    a = ap.parse_args()

    tfs = [a.tf] if a.tf else TFS
    combos = [(tf, sym, a.cut_ts) for tf in tfs for sym in universe(tf)]
    if a.limit:
        combos = combos[:a.limit]
    print(f"ema921 grid: {len(combos)} cells, workers={a.workers}", flush=True)
    for tf in tfs:
        u = universe(tf)
        if u:
            print(f"  {tf:>3}: {len(u):2}  " + ", ".join(u), flush=True)

    t0 = time.time()
    done, errors = {}, []
    with ProcessPoolExecutor(max_workers=max(1, a.workers)) as ex:
        futs = [ex.submit(worker, c) for c in combos]
        for k, fut in enumerate(as_completed(futs), 1):
            tf, sym, rid, err = fut.result()
            if err:
                errors.append({"tf": tf, "symbol": sym, "error": err})
                print(f"[{k}/{len(combos)}] {tf:>3} {sym:<12} ERROR {err}", flush=True)
                continue
            done[(tf, sym)] = rid
            art = vrun.load_artifact(rid)
            m = art["metrics"]
            print(f"[{k}/{len(combos)}] {tf:>3} {sym:<12} {rid} "
                  f"n={m.get('n_trades'):>6} ret%={m.get('return_pct', 0):9.2f} "
                  f"PF={m.get('profit_factor', 0):.3f} "
                  f"oosPF={m.get('oos_profit_factor', 0):.3f} "
                  f"zcPF={m.get('zero_cost_pf', 0):.3f} "
                  f"{m.get('flag', '')}", flush=True)

    rows = []
    for tf, sym, _cut in combos:
        rid = done.get((tf, sym))
        if not rid:
            continue
        art = vrun.load_artifact(rid)
        m = art["metrics"]
        keep = ["bars", "start", "end", "n_trades", "return_pct", "final_equity",
                "profit_factor", "win_rate_pct", "max_dd_pct", "sharpe",
                "long_pnl", "short_pnl", "long_trades", "short_trades",
                "thirds_net_pct", "n_periods_green", "halves_net_pct",
                "n_halves_green", "oos_split_time", "oos_n_trades",
                "oos_return_pct", "oos_profit_factor", "conc_top5_share_pct",
                "conc_net_without_top5_pct", "boot_ci_lo", "boot_ci_hi",
                "boot_p_le_zero", "buy_hold_return_pct", "fees_paid",
                "funding_paid", "funding_model", "funding_events",
                "funding_max_gap_h", "funding_covers_bars",
                "funding_coverage_frac", "bars_trimmed_head_for_funding",
                "bars_trimmed_tail_for_funding", "pnl_identity_resid",
                "no_funding_return_pct", "no_funding_pf", "funding_drag_pp",
                "zero_cost_return_pct", "zero_cost_pf", "avg_gross_leverage",
                "max_gross_leverage", "fee_bps_per_side", "slippage_bps_per_side",
                "cost_bp_roundtrip", "flag"]
        row = {"tf": tf, "symbol": sym, "run_id": rid,
               "metrics": {k: m.get(k) for k in keep}}
        rows.append(row)

    vrun._write_matrix_index("ema921", [
        (r["tf"], r["symbol"], r["run_id"], r["metrics"]["n_trades"],
         r["metrics"]["return_pct"], r["metrics"]["profit_factor"],
         r["metrics"]["max_dd_pct"], r["metrics"]["flag"]) for r in rows])
    out = os.path.join(ROOT, "results", f"ema921_matrix_{DATE}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"date": DATE, "cells": rows, "errors": errors}, f, indent=1)
    print(f"\n{len(rows)} artifacts, {len(errors)} errors, "
          f"{time.time() - t0:.0f}s -> {out}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
