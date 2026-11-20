"""The 2026-11-20 zero-cost / no-rules control: ten books, two regimes each.

Ten books = the first ten rows of results/top100_2026-10-31.md, unedited.
Nine adapter runs (two of the ten rows are two strategies inside the same
cbpackf artifact), each made twice on the same frozen cut:

    BASE = the regime the book was published under
    ZERO = fees 0.0, slippage 0.0, funding NOT charged, same engine bytes

Writes results/zerocost_matrix_2026-11-20.json and prints every run_id.
No gate is evaluated: this is a control, not a verdict (REGLA 0/1).

Run: python code/_zerocost_matrix.py
"""
import json
import os
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
os.chdir(ROOT)
sys.path.insert(0, CODE)

import vrun as V  # noqa: E402

OUT = os.path.join(ROOT, "results", "zerocost_matrix_2026-11-20.json")

# (tag, adapter, tf, symbol, base_params, zero_params)
CELLS = [
    ("xrpneutral-XRP-15m", "xrpneutral", "15m", "XRPUSDT",
     {"fee_bps": 2.0, "flat_fee_bps": 5.0, "slip_bps": 2.0,
      "funding": True, "control_long_only": False},
     {"fee_bps": 0.0, "flat_fee_bps": 0.0, "slip_bps": 0.0,
      "funding": False, "control_long_only": False}),
    ("pack100-HYPE-15m-F74", "pack100", "15m", "HYPEUSDT",
     {"strat": "F74-15m", "costs": "repo", "funding": True},
     {"strat": "F74-15m", "costs": "zero", "funding": False}),
    ("botstrat-SPX-1h", "botstrat", "1h", "SPXUSDT",
     {"costs": "repo"}, {"costs": "zero"}),
    ("eqpack-QQQ-1d", "eqpack", "1d", "QQQ",
     {"costs": "eq"}, {"costs": "zero"}),
    ("pack100-HYPE-1h-F74", "pack100", "1h", "HYPEUSDT",
     {"strat": "F74-1h", "costs": "repo", "funding": True},
     {"strat": "F74-1h", "costs": "zero", "funding": False}),
    ("botstrat-BNB-1h", "botstrat", "1h", "BNBUSDT",
     {"costs": "repo"}, {"costs": "zero"}),
    ("cvrmd-SUI-1h", "cvrmd", "1h", "SUIUSDT",
     {"costs": "repo"}, {"costs": "zero"}),
    ("cbpackf-XRP-1h", "cbpackf", "1h", "XRPUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}),
    ("cbpackf-SOL-1h", "cbpackf", "1h", "SOLUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}),
]

# the ten published rows -> where the number lives inside each artifact
# ("row",) = a metrics field, ("row", sid) = a table row for that strategy id
BOOKS = [
    (1, "xrpneutral-XRP-15m", "XRP delta-neutral grid v1", "XRPUSDT 15m", "metrics"),
    (2, "pack100-HYPE-15m-F74", "F74-15m market-structure HH/HL trend", "HYPEUSDT 15m", "metrics"),
    (3, "botstrat-SPX-1h", "botstrat", "SPXUSDT 1h", "metrics"),
    (4, "eqpack-QQQ-1d", "S02 Donchian + Flow Breakout", "QQQ 1d", "S02"),
    (5, "pack100-HYPE-1h-F74", "F74-1h market-structure HH/HL trend", "HYPEUSDT 1h", "metrics"),
    (6, "botstrat-BNB-1h", "botstrat", "BNBUSDT 1h", "metrics"),
    (7, "cvrmd-SUI-1h", "cvrmd", "SUIUSDT 1h", "metrics"),
    (8, "cbpackf-XRP-1h", "S10 Vol-Targeted Time-Series Momentum", "XRPUSDT 1h", "S10"),
    (9, "cbpackf-SOL-1h", "S10 Vol-Targeted Time-Series Momentum", "SOLUSDT 1h", "S10"),
    (10, "cbpackf-XRP-1h", "S02 Donchian + Flow Breakout", "XRPUSDT 1h", "S02"),
]


def num(x):
    return None if x is None else (float(x) if isinstance(x, (int, float)) else x)


def extract(art, where):
    """One normalized record for a published book, from the artifact's own
    numbers. `where` names the metrics block or the table row (strategy id)."""
    m = art["metrics"]
    if where == "metrics":
        if art["strategy"] == "pack100":
            return {"net_pct": num(m["return_pct"]), "pf": num(m["pf_pct"]),
                    "n_trades": m["n_trades"], "max_dd_pct": num(m["max_dd_pct"]),
                    "funding_paid": num(m.get("funding_paid")),
                    "bh_pct": num(m.get("bh_return_pct"))}
        return {"net_pct": num(m["return_pct"]), "pf": num(m["profit_factor"]),
                "n_trades": m["n_trades"], "max_dd_pct": num(m["max_dd_pct"]),
                "funding_paid": num(m.get("funding_paid")),
                "bh_pct": num(m.get("bh_return_pct"))}
    for r in art.get("tables") or []:
        if r.get("id") == where:
            return {"net_pct": num(r.get("net_%")), "pf": num(r.get("PF")),
                    "n_trades": num(r.get("trades")), "max_dd_pct": num(r.get("maxDD_%")),
                    "funding_paid": num(r.get("funding_paid_pct")),
                    "bh_pct": num(r.get("buy_hold_%"))}
    raise KeyError(f"{where} not in {art['strategy']} {art['symbol']} tables")


def main():
    cell_rec = {}
    for tag, adapter, tf, sym, bp, zp in CELLS:
        rec = {"tag": tag, "adapter": adapter, "symbol": sym, "tf": tf}
        for regime, params in (("base", bp), ("zero", zp)):
            print(f"[{tag}] {regime} ...", flush=True)
            a = V.make_artifact(adapter, tf, sym, dict(params))
            path = V.save_artifact(a)
            rec[regime] = {"run_id": a["run_id"], "params": params,
                           "artifact": os.path.relpath(path, ROOT).replace("\\", "/"),
                           "cut_ts": a["core"].get("cut_ts"),
                           "inputs": [os.path.basename(i["path"]) for i in a["inputs"]]}
            print(f"    {a['run_id']}  {os.path.basename(path)}", flush=True)
        cell_rec[tag] = rec

    books = []
    for row, tag, label, market, where in BOOKS:
        entry = {"row": row, "book": label, "market": market, "tag": tag, "where": where}
        for regime in ("base", "zero"):
            rid = cell_rec[tag][regime]["run_id"]
            art = V.load_artifact(rid)
            entry[regime] = {"run_id": rid, **extract(art, where)}
        b, z = entry["base"], entry["zero"]
        entry["delta_pct"] = (z["net_pct"] - b["net_pct"]
                              if z["net_pct"] is not None and b["net_pct"] is not None else None)
        books.append(entry)

    payload = {"campaign": "zerocost-2026-11-20", "cells": cell_rec, "books": books,
               "note": "control, not a verdict: no gate is evaluated and no row is "
                       "evidence of alpha (results/zerocost_pre_registration.md)"}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, default=str)
    print("wrote", OUT)

    print("\n%-3s %-46s %-13s %10s %10s %8s %6s %6s" % (
        "#", "book", "market", "base %", "zero %", "delta", "n", "PF"))
    for e in books:
        b, z = e["base"], e["zero"]
        print("%-3d %-46s %-13s %10.2f %10.2f %8.2f %6s %6.3f" % (
            e["row"], e["book"][:46], e["market"], b["net_pct"], z["net_pct"],
            e["delta_pct"], z["n_trades"], z["pf"]))


if __name__ == "__main__":
    main()
