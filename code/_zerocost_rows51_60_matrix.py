"""The 2026-11-23 zero-cost / no-rules control, rows 51-60: ten books, two
regimes each, same frozen cut, same engine bytes per pair. Same protocol as
code/_zerocost_rows31_40_matrix.py. No mirror row in this batch.

Run: python code/_zerocost_rows51_60_matrix.py
"""
import json
import os
import re
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402

OUT = os.path.join(ROOT, "results", "zerocost_rows51_60_matrix.json")
_RID = re.compile(r"^[0-9a-f]{16}$")
_RUNS = os.path.realpath(os.path.join(ROOT, "results", "runs"))


def _load_artifact_safe(rid):
    if not _RID.match(str(rid)):
        raise ValueError(f"refusing non run_id: {rid!r}")
    p = os.path.realpath(os.path.join(_RUNS, str(rid) + ".json"))
    if not (p.startswith(_RUNS + os.sep) and os.path.isfile(p)):
        raise ValueError(f"artifact outside the runs dir: {rid!r}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# (tag, adapter, tf, symbol, base_params, zero_params)
CELLS = [
    ("pack50d-ETH-1h-P08", "pack50d", "1h", "ETHUSDT",
     {"strat": 8, "costs": "repo", "funding": True},
     {"strat": 8, "costs": "zero", "funding": False}),
    ("qs-SUI-1h-QS009", "qs", "1h", "SUIUSDT",
     {"strat": "QS-009", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-009", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("cbpackf-SUI-1h-S10", "cbpackf", "1h", "SUIUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}),
    ("cbpackf-HYPE-1h-S10", "cbpackf", "1h", "HYPEUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}),
    ("qs-ETH-1h-QS006", "qs", "1h", "ETHUSDT",
     {"strat": "QS-006", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-006", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("cbpackf-ETH-1h-S07", "cbpackf", "1h", "ETHUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False,
      "funding_signal": True}),
    ("pack100-ETH-1h-C44", "pack100", "1h", "ETHUSDT",
     {"strat": "C44-1h", "costs": "repo", "funding": True},
     {"strat": "C44-1h", "costs": "zero", "funding": False}),
    ("dspack-SOL-1h-ds3", "dspack", "1h", "SOLUSDT",
     {"strat": "ds3", "costs": "repo6x5", "window": "full"},
     {"strat": "ds3", "costs": "author", "window": "full"}),
    ("qs-SOL-1h-QS003", "qs", "1h", "SOLUSDT",
     {"strat": "QS-003", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-003", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("mpv3-PORTFOLIO-1h-S10", "mpv3", "1h", "PORTFOLIO",
     {"costs": "repo", "strat": "MP-V3-S10", "window": "full"},
     {"costs": "zero", "strat": "MP-V3-S10", "window": "full"}),
]

BOOKS = [
    (51, "pack50d-ETH-1h-P08", "P08 Keltner breakout", "ETHUSDT 1h", "metrics"),
    (52, "qs-SUI-1h-QS009", "QS-009 Volatility-adjusted momentum", "SUIUSDT 1h", "metrics"),
    (53, "cbpackf-SUI-1h-S10", "S10 Vol-Targeted Time-Series Momentum", "SUIUSDT 1h", "S10"),
    (54, "cbpackf-HYPE-1h-S10", "S10 Vol-Targeted Time-Series Momentum", "HYPEUSDT 1h", "S10"),
    (55, "qs-ETH-1h-QS006", "QS-006 ADX-filtered directional continuation", "ETHUSDT 1h", "metrics"),
    (56, "cbpackf-ETH-1h-S07", "S07 Funding Extreme Fade", "ETHUSDT 1h", "S07"),
    (57, "pack100-ETH-1h-C44", "C44-1h fractal breakout", "ETHUSDT 1h", "metrics"),
    (58, "dspack-SOL-1h-ds3", "ds3", "SOLUSDT 1h", "metrics"),
    (59, "qs-SOL-1h-QS003", "QS-003 Supertrend continuation", "SOLUSDT 1h", "metrics"),
    (60, "mpv3-PORTFOLIO-1h-S10", "MP-V3-S10 Pure Equal Weight Momentum", "PORTFOLIO 1h", "metrics"),
]

KEYS = {
    "qs": dict(net="return_base_pct", pf="pf", n="n_trades", dd="max_dd_pct",
               fund="funding_paid", bh="bh_return_pct"),
    "cbpackf": dict(net="return_pct", pf="profit_factor", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
    "pack100": dict(net="return_pct", pf="pf_pct", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
    "pack50d": dict(net="return_pct", pf="pf_pct", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
    "dspack": dict(net="return_pct", pf="profit_factor", n="n_trades",
                   dd="max_dd_pct", fund=None, bh=None),
    "mpv3": dict(net="return_pct", pf="profit_factor", n="n_trades",
                 dd="max_dd_pct", fund=None, bh="bh_return_pct"),
}
DEFAULT_KEYS = dict(net="return_pct", pf="profit_factor", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct")


def num(x):
    return None if x is None else (float(x) if isinstance(x, (int, float)) else x)


def extract(art, where):
    m = art["metrics"]
    if where == "metrics":
        k = KEYS.get(art["strategy"], DEFAULT_KEYS)
        return {"net_pct": num(m[k["net"]]) if k["net"] else None,
                "pf": num(m[k["pf"]]) if k["pf"] else None,
                "n_trades": m[k["n"]] if k["n"] else None,
                "max_dd_pct": num(m[k["dd"]]) if k["dd"] else None,
                "funding_paid": num(m.get(k["fund"])) if k["fund"] else None,
                "bh_pct": num(m.get(k["bh"])) if k["bh"] else None}
    for r in art.get("tables") or []:
        if r.get("id") == where:
            return {"net_pct": num(r.get("net_%")), "pf": num(r.get("PF")),
                    "n_trades": num(r.get("trades")),
                    "max_dd_pct": num(r.get("maxDD_%")),
                    "funding_paid": num(r.get("funding_paid_pct")),
                    "bh_pct": num(r.get("buy_hold_%"))}
    raise KeyError(f"{where} not in {art['strategy']} {art['symbol']} tables")


def _record(adapter, tf, sym, params):
    a = V.make_artifact(adapter, tf, sym, dict(params))
    path = V.save_artifact(a)
    rec = {"run_id": a["run_id"], "params": params,
           "artifact": "results/runs/" + os.path.basename(path),
           "cut_ts": a["core"].get("cut_ts"),
           "inputs": [os.path.basename(i["path"]) for i in a["inputs"]]}
    print(f"    {a['run_id']}  {os.path.basename(path)}", flush=True)
    return rec


def main():
    cell_rec = {}
    for tag, adapter, tf, sym, bp, zp in CELLS:
        rec = {"tag": tag, "adapter": adapter, "symbol": sym, "tf": tf}
        for regime, params in (("base", bp), ("zero", zp)):
            print(f"[{tag}] {regime} ...", flush=True)
            rec[regime] = _record(adapter, tf, sym, params)
        cell_rec[tag] = rec

    books = []
    for row, tag, label, market, where in BOOKS:
        entry = {"row": row, "book": label, "market": market, "tag": tag, "where": where}
        for regime in ("base", "zero"):
            rid = cell_rec[tag][regime]["run_id"]
            entry[regime] = {"run_id": rid, **extract(_load_artifact_safe(rid), where)}
        b, z = entry["base"], entry["zero"]
        entry["delta_pct"] = (z["net_pct"] - b["net_pct"]
                              if z["net_pct"] is not None and b["net_pct"] is not None else None)
        books.append(entry)

    out_real = os.path.realpath(OUT)
    if not out_real.startswith(os.path.realpath(ROOT) + os.sep):
        raise ValueError(f"output outside the repo root: {OUT}")
    payload = {"campaign": "zerocost-rows51-60-2026-11-23", "cells": cell_rec,
               "books": books,
               "note": "control, not a verdict: no gate is evaluated and no row is "
                       "evidence of alpha (results/zerocost_rows51_60_pre_registration.md)"}
    with open(out_real, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, default=str)
    print("wrote", OUT)

    print("\n%-3s %-46s %-13s %10s %10s %6s %6s" % (
        "#", "book", "market", "base %", "zero %", "n", "PF"))
    for e in books:
        b, z = e["base"], e["zero"]
        print("%-3d %-46s %-13s %10.2f %10.2f %6s %6.3f" % (
            e["row"], e["book"][:46], e["market"], b["net_pct"], z["net_pct"],
            z["n_trades"], z["pf"]))


if __name__ == "__main__":
    main()
