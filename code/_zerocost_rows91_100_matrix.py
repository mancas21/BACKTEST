"""The 2026-11-23 zero-cost / no-rules control, rows 91-100: ten books, two
regimes each. Same protocol as code/_zerocost_rows51_60_matrix.py.

Run: python code/_zerocost_rows91_100_matrix.py
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

OUT = os.path.join(ROOT, "results", "zerocost_rows91_100_matrix.json")
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
    ("cbpackf-SUI-1h-S07", "cbpackf", "1h", "SUIUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False, "funding_signal": True}),
    ("cbpackf-SUI-1h-S09", "cbpackf", "1h", "SUIUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}),
    ("dspack2-DOGE-1h-ds7", "dspack2", "1h", "DOGEUSDT",
     {"strat": "ds7", "costs": "repo6x5", "window": "full"},
     {"strat": "ds7", "costs": "author", "window": "full"}),
    ("qs-HYPE-1h-QS002", "qs", "1h", "HYPEUSDT",
     {"strat": "QS-002", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-002", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("dspack-NEAR-1h-ds1", "dspack", "1h", "NEARUSDT",
     {"strat": "ds1", "costs": "repo6x5", "window": "full"},
     {"strat": "ds1", "costs": "author", "window": "full"}),
    ("qsf-SOL-1h-QS044", "qsf", "1h", "SOLUSDT",
     {"strat": "QS-044", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-044", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("dspack-LINK-1h-ds1", "dspack", "1h", "LINKUSDT",
     {"strat": "ds1", "costs": "repo6x5", "window": "full"},
     {"strat": "ds1", "costs": "author", "window": "full"}),
    ("dspack2-SOL-1h-ds7", "dspack2", "1h", "SOLUSDT",
     {"strat": "ds7", "costs": "repo6x5", "window": "full"},
     {"strat": "ds7", "costs": "author", "window": "full"}),
    ("dspack2-NEAR-1h-ds7", "dspack2", "1h", "NEARUSDT",
     {"strat": "ds7", "costs": "repo6x5", "window": "full"},
     {"strat": "ds7", "costs": "author", "window": "full"}),
    ("dspack-SUI-1h-ds1", "dspack", "1h", "SUIUSDT",
     {"strat": "ds1", "costs": "repo6x5", "window": "full"},
     {"strat": "ds1", "costs": "author", "window": "full"}),
]

BOOKS = [
    (91, "cbpackf-SUI-1h-S07", "S07 Funding Extreme Fade", "SUIUSDT 1h", "S07"),
    (92, "cbpackf-SUI-1h-S09", "S09 Liquidity Sweep Reversal", "SUIUSDT 1h", "S09"),
    (93, "dspack2-DOGE-1h-ds7", "ds7", "DOGEUSDT 1h", "metrics"),
    (94, "qs-HYPE-1h-QS002", "QS-002 EMA alignment with volatility confirmation", "HYPEUSDT 1h", "metrics"),
    (95, "dspack-NEAR-1h-ds1", "ds1", "NEARUSDT 1h", "metrics"),
    (96, "qsf-SOL-1h-QS044", "QS-044 Cumulative volume delta divergence", "SOLUSDT 1h", "metrics"),
    (97, "dspack-LINK-1h-ds1", "ds1", "LINKUSDT 1h", "metrics"),
    (98, "dspack2-SOL-1h-ds7", "ds7", "SOLUSDT 1h", "metrics"),
    (99, "dspack2-NEAR-1h-ds7", "ds7", "NEARUSDT 1h", "metrics"),
    (100, "dspack-SUI-1h-ds1", "ds1", "SUIUSDT 1h", "metrics"),
]

KEYS = {
    "qsf": dict(net="return_base_pct", pf="pf", n="n_trades",
               dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
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
    payload = {"campaign": "zerocost-rows91-100-2026-11-23", "cells": cell_rec,
               "books": books,
               "note": "control, not a verdict: no gate is evaluated and no row is "
                       "evidence of alpha (results/zerocost_rows91_100_pre_registration.md)"}
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
