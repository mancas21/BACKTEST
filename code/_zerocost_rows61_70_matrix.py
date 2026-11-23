"""The 2026-11-23 zero-cost / no-rules control, rows 61-70: ten books, two
regimes each. Same protocol as code/_zerocost_rows51_60_matrix.py.

Run: python code/_zerocost_rows61_70_matrix.py
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

OUT = os.path.join(ROOT, "results", "zerocost_rows61_70_matrix.json")
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
    ("qs-JUP-1h-QS003", "qs", "1h", "JUPUSDT",
     {"strat": "QS-003", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-003", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("cbpackf-HYPE-1h-S02", "cbpackf", "1h", "HYPEUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}),
    ("dspack2-SPX-1h-ds7", "dspack2", "1h", "SPXUSDT",
     {"strat": "ds7", "costs": "repo6x5", "window": "full"},
     {"strat": "ds7", "costs": "author", "window": "full"}),
    ("qs-JUP-1h-QS002", "qs", "1h", "JUPUSDT",
     {"strat": "QS-002", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-002", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("qs-SOL-15m-QS001-long", "qs", "15m", "SOLUSDT",
     {"strat": "QS-001", "variant": "long-only", "costs": "repo", "funding": True},
     {"strat": "QS-001", "variant": "long-only", "costs": "zero", "funding": False}),
    ("dspack-LINK-1h-ds5", "dspack", "1h", "LINKUSDT",
     {"strat": "ds5", "costs": "author", "window": "full"},
     {"strat": "ds5", "costs": "author", "window": "full"}),
    ("qs-JUP-1h-QS001", "qs", "1h", "JUPUSDT",
     {"strat": "QS-001", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-001", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("pack100-SUI-15m-F75", "pack100", "15m", "SUIUSDT",
     {"strat": "F75-15m", "costs": "repo", "funding": True},
     {"strat": "F75-15m", "costs": "zero", "funding": False}),
    ("cbpackf-HYPE-1h-S03", "cbpackf", "1h", "HYPEUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}),
    ("qs-JUP-1h-QS004", "qs", "1h", "JUPUSDT",
     {"strat": "QS-004", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-004", "variant": "two-sided", "costs": "zero", "funding": False}),
]

BOOKS = [
    (61, "qs-JUP-1h-QS003", "QS-003 Supertrend continuation", "JUPUSDT 1h", "metrics"),
    (62, "cbpackf-HYPE-1h-S02", "S02 Donchian + Flow Breakout", "HYPEUSDT 1h", "S02"),
    (63, "dspack2-SPX-1h-ds7", "ds7", "SPXUSDT 1h", "metrics"),
    (64, "qs-JUP-1h-QS002", "QS-002 EMA alignment with volatility confirmation", "JUPUSDT 1h", "metrics"),
    (65, "qs-SOL-15m-QS001-long", "QS-001 Moving-average trend continuation (long-only)", "SOLUSDT 15m", "metrics"),
    (66, "dspack-LINK-1h-ds5", "ds5", "LINKUSDT 1h", "metrics"),
    (67, "qs-JUP-1h-QS001", "QS-001 Moving-average trend continuation", "JUPUSDT 1h", "metrics"),
    (68, "pack100-SUI-15m-F75", "F75-15m equal-highs liquidity grab (short)", "SUIUSDT 15m", "metrics"),
    (69, "cbpackf-HYPE-1h-S03", "S03 Squeeze Release", "HYPEUSDT 1h", "S03"),
    (70, "qs-JUP-1h-QS004", "QS-004 Donchian channel breakout", "JUPUSDT 1h", "metrics"),
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
    payload = {"campaign": "zerocost-rows61-70-2026-11-23", "cells": cell_rec,
               "books": books,
               "note": "control, not a verdict: no gate is evaluated and no row is "
                       "evidence of alpha (results/zerocost_rows61_70_pre_registration.md)"}
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
