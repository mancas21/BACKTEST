"""The 2026-11-23 zero-cost / no-rules control, rows 71-80: ten books, two
regimes each. Same protocol as code/_zerocost_rows51_60_matrix.py.

Run: python code/_zerocost_rows71_80_matrix.py
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

OUT = os.path.join(ROOT, "results", "zerocost_rows71_80_matrix.json")
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


CELLS = [
    ("pack100-SPX-15m-A01", "pack100", "15m", "SPXUSDT",
     {"strat": "A01-15m", "costs": "repo", "funding": True},
     {"strat": "A01-15m", "costs": "zero", "funding": False}),
    ("qs-HYPE-15m-QS002-long", "qs", "15m", "HYPEUSDT",
     {"strat": "QS-002", "variant": "long-only", "costs": "repo", "funding": True},
     {"strat": "QS-002", "variant": "long-only", "costs": "zero", "funding": False}),
    ("qs-BTC-1h-QS009", "qs", "1h", "BTCUSDT",
     {"strat": "QS-009", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-009", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("pack50-SUI-4h-S05", "pack50", "4h", "SUIUSDT",
     {"strat": 5, "costs": "repo", "funding": True},
     {"strat": 5, "costs": "zero", "funding": False}),
    ("qs-HYPE-1h-QS005", "qs", "1h", "HYPEUSDT",
     {"strat": "QS-005", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-005", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("qs-ETH-1h-QS007", "qs", "1h", "ETHUSDT",
     {"strat": "QS-007", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-007", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("dspack-SOL-1h-ds1", "dspack", "1h", "SOLUSDT",
     {"strat": "ds1", "costs": "repo6x5", "window": "full"},
     {"strat": "ds1", "costs": "author", "window": "full"}),
    ("dspack-ETH-1h-ds3", "dspack", "1h", "ETHUSDT",
     {"strat": "ds3", "costs": "author", "window": "full"},
     {"strat": "ds3", "costs": "author", "window": "full"}),
    ("qs-HYPE-15m-QS001", "qs", "15m", "HYPEUSDT",
     {"strat": "QS-001", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-001", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("pack100-SOL-1h-B25", "pack100", "1h", "SOLUSDT",
     {"strat": "B25-1h", "costs": "repo", "funding": True},
     {"strat": "B25-1h", "costs": "zero", "funding": False}),
]

BOOKS = [
    (71, "pack100-SPX-15m-A01", "A01-15m RSI14 L/S mean-reversion", "SPXUSDT 15m", "metrics"),
    (72, "qs-HYPE-15m-QS002-long", "QS-002 EMA alignment with volatility confirmation (long-only)", "HYPEUSDT 15m", "metrics"),
    (73, "qs-BTC-1h-QS009", "QS-009 Volatility-adjusted momentum", "BTCUSDT 1h", "metrics"),
    (74, "pack50-SUI-4h-S05", "S5 Heikin-Ashi trend", "SUIUSDT 4h", "metrics"),
    (75, "qs-HYPE-1h-QS005", "QS-005 Time-series momentum", "HYPEUSDT 1h", "metrics"),
    (76, "qs-ETH-1h-QS007", "QS-007 Higher-timeframe trend, lower-timeframe entries", "ETHUSDT 1h", "metrics"),
    (77, "dspack-SOL-1h-ds1", "ds1", "SOLUSDT 1h", "metrics"),
    (78, "dspack-ETH-1h-ds3", "ds3", "ETHUSDT 1h", "metrics"),
    (79, "qs-HYPE-15m-QS001", "QS-001 Moving-average trend continuation", "HYPEUSDT 15m", "metrics"),
    (80, "pack100-SOL-1h-B25", "B25-1h Keltner breakout (long)", "SOLUSDT 1h", "metrics"),
]

KEYS = {
    "qs": dict(net="return_base_pct", pf="pf", n="n_trades", dd="max_dd_pct",
               fund="funding_paid", bh="bh_return_pct"),
    "cbpackf": dict(net="return_pct", pf="profit_factor", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
    "pack100": dict(net="return_pct", pf="pf_pct", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
    "dspack": dict(net="return_pct", pf="profit_factor", n="n_trades",
                   dd="max_dd_pct", fund=None, bh=None),
    "dspack2": dict(net="return_pct", pf="profit_factor", n="n_trades",
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
    for tag, adapter, tf, sym, bp, zp in CELLS:
        rec = {"tag": tag, "adapter": adapter, "symbol": sym, "tf": tf}
        if bp == zp:
            print(f"[{tag}] base==zero (author regime), one run ...", flush=True)
            r = _record(adapter, tf, sym, bp)
            rec["base"] = r
            rec["zero"] = dict(r)
        else:
            for regime, params in (("base", bp), ("zero", zp)):
                print(f"[{tag}] {regime} ...", flush=True)
                rec[regime] = _record(adapter, tf, sym, params)
        if bp == zp:
            print(f"[{tag}] costed (author-regime informative re-run) ...", flush=True)
            extra = dict(bp)
            extra["costs"] = "repo6x5"
            rec["costed"] = _record(adapter, tf, sym, extra)
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
    payload = {"campaign": "zerocost-rows71-80-2026-11-23", "cells": cell_rec,
               "books": books,
               "note": "control, not a verdict: no gate is evaluated and no row is "
                       "evidence of alpha (results/zerocost_rows71_80_pre_registration.md)"}
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
