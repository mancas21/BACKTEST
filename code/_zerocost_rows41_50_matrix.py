"""The 2026-11-23 zero-cost / no-rules control, rows 41-50: ten books, two
regimes each. Same protocol as code/_zerocost_rows31_40_matrix.py; row 45 is
the author-regime mirror case with a costed re-run.

Run: python code/_zerocost_rows41_50_matrix.py
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

OUT = os.path.join(ROOT, "results", "zerocost_rows41_50_matrix.json")
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


# (tag, adapter, tf, symbol, base_params, zero_params, extra_params_or_None)
CELLS = [
    ("cbpackf-SUI-1h-S02", "cbpackf", "1h", "SUIUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}, None),
    ("cbpackf-XRP-1h-S03", "cbpackf", "1h", "XRPUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}, None),
    ("qs-BTC-15m-QS001-long", "qs", "15m", "BTCUSDT",
     {"strat": "QS-001", "variant": "long-only", "costs": "repo", "funding": True},
     {"strat": "QS-001", "variant": "long-only", "costs": "zero", "funding": False}, None),
    ("fingrad-SUI-1h-b", "fingrad", "1h", "SUIUSDT",
     {"sig_mode": "b", "costs": "author", "funding": False},
     {"sig_mode": "b", "costs": "zero", "funding": False}, None),
    ("dspack-HYPE-1h-ds1", "dspack", "1h", "HYPEUSDT",
     {"strat": "ds1", "costs": "author", "window": "full"},
     {"strat": "ds1", "costs": "author", "window": "full"},
     {"strat": "ds1", "costs": "repo6x5", "window": "full"}),
    ("cbpackf-ETH-1h-S02", "cbpackf", "1h", "ETHUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}, None),
    ("qs-SOL-1h-QS002", "qs", "1h", "SOLUSDT",
     {"strat": "QS-002", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-002", "variant": "two-sided", "costs": "zero", "funding": False}, None),
    ("qs-SUI-1h-QS007", "qs", "1h", "SUIUSDT",
     {"strat": "QS-007", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-007", "variant": "two-sided", "costs": "zero", "funding": False}, None),
    ("qs-JUP-1h-QS006", "qs", "1h", "JUPUSDT",
     {"strat": "QS-006", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-006", "variant": "two-sided", "costs": "zero", "funding": False}, None),
    ("qs-SUI-1h-QS003", "qs", "1h", "SUIUSDT",
     {"strat": "QS-003", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-003", "variant": "two-sided", "costs": "zero", "funding": False}, None),
]

BOOKS = [
    (41, "cbpackf-SUI-1h-S02", "S02 Donchian + Flow Breakout", "SUIUSDT 1h", "S02"),
    (42, "cbpackf-XRP-1h-S03", "S03 Squeeze Release", "XRPUSDT 1h", "S03"),
    (43, "qs-BTC-15m-QS001-long", "QS-001 Moving-average trend continuation (long-only)", "BTCUSDT 15m", "metrics"),
    (44, "fingrad-SUI-1h-b", "fingrad", "SUIUSDT 1h", "metrics"),
    (45, "dspack-HYPE-1h-ds1", "ds1", "HYPEUSDT 1h", "metrics"),
    (46, "cbpackf-ETH-1h-S02", "S02 Donchian + Flow Breakout", "ETHUSDT 1h", "S02"),
    (47, "qs-SOL-1h-QS002", "QS-002 EMA alignment with volatility confirmation", "SOLUSDT 1h", "metrics"),
    (48, "qs-SUI-1h-QS007", "QS-007 Higher-timeframe trend, lower-timeframe entries", "SUIUSDT 1h", "metrics"),
    (49, "qs-JUP-1h-QS006", "QS-006 ADX-filtered directional continuation", "JUPUSDT 1h", "metrics"),
    (50, "qs-SUI-1h-QS003", "QS-003 Supertrend continuation", "SUIUSDT 1h", "metrics"),
]

KEYS = {
    "qs": dict(net="return_base_pct", pf="pf", n="n_trades", dd="max_dd_pct",
               fund="funding_paid", bh="bh_return_pct"),
    "cbpackf": dict(net="return_pct", pf="profit_factor", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
    "fingrad": dict(net="return_pct", pf="profit_factor", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
    "dspack": dict(net="return_pct", pf="profit_factor", n="n_trades",
                   dd="max_dd_pct", fund=None, bh=None),
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
    for tag, adapter, tf, sym, bp, zp, ep in CELLS:
        rec = {"tag": tag, "adapter": adapter, "symbol": sym, "tf": tf}
        if bp == zp:
            print(f"[{tag}] base==zero (published regime is zero-cost), one run ...", flush=True)
            r = _record(adapter, tf, sym, bp)
            rec["base"] = r
            rec["zero"] = dict(r)
        else:
            for regime, params in (("base", bp), ("zero", zp)):
                print(f"[{tag}] {regime} ...", flush=True)
                rec[regime] = _record(adapter, tf, sym, params)
        if ep:
            print(f"[{tag}] costed (author-regime informative re-run) ...", flush=True)
            rec["costed"] = _record(adapter, tf, sym, ep)
        cell_rec[tag] = rec

    books = []
    for row, tag, label, market, where in BOOKS:
        entry = {"row": row, "book": label, "market": market, "tag": tag, "where": where}
        for regime in ("base", "zero"):
            rid = cell_rec[tag][regime]["run_id"]
            entry[regime] = {"run_id": rid, **extract(_load_artifact_safe(rid), where)}
        if "costed" in cell_rec[tag]:
            rid = cell_rec[tag]["costed"]["run_id"]
            entry["costed"] = {"run_id": rid,
                               **extract(_load_artifact_safe(rid), where)}
        b, z = entry["base"], entry["zero"]
        entry["delta_pct"] = (z["net_pct"] - b["net_pct"]
                              if z["net_pct"] is not None and b["net_pct"] is not None else None)
        books.append(entry)

    out_real = os.path.realpath(OUT)
    if not out_real.startswith(os.path.realpath(ROOT) + os.sep):
        raise ValueError(f"output outside the repo root: {OUT}")
    payload = {"campaign": "zerocost-rows41-50-2026-11-23", "cells": cell_rec,
               "books": books,
               "note": "control, not a verdict: no gate is evaluated and no row is "
                       "evidence of alpha (results/zerocost_rows41_50_pre_registration.md)"}
    with open(out_real, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, default=str)
    print("wrote", OUT)

    print("\n%-3s %-46s %-13s %10s %10s %10s %6s %6s" % (
        "#", "book", "market", "base %", "zero %", "costed %", "n", "PF"))
    for e in books:
        b, z, c = e["base"], e["zero"], e.get("costed")
        print("%-3d %-46s %-13s %10.2f %10.2f %10s %6s %6.3f" % (
            e["row"], e["book"][:46], e["market"], b["net_pct"], z["net_pct"],
            f"{c['net_pct']:.2f}" if c else "-", z["n_trades"], z["pf"]))


if __name__ == "__main__":
    main()
