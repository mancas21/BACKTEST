"""The 2026-11-23 zero-cost / no-rules control, rows 31-40: ten books, two
regimes each.

Ten books = rows 31-40 of results/top100_2026-10-31.md, unedited. Ten adapter
cells, each made twice (BASE = the regime the book was published under, ZERO =
fees 0.0, slippage 0.0, funding cash flow 0.0, same engine bytes).

ROWS 37 AND 38 SPECIAL CASE (declared in the pre-registration): ds1 was
PUBLISHED at costs=author (the pack declares no costs; the engine charges no
funding), so BASE and ZERO carry identical params and are the SAME artifact --
it is run ONCE and recorded under both regimes. One extra artifact per row with
costs=repo6x5 is minted as the row's "costed" measurement: the informative
comparison for those books runs the other way.

No gate is evaluated: this is a control, not a verdict (REGLA 0/1).

Run: python code/_zerocost_rows31_40_matrix.py
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

OUT = os.path.join(ROOT, "results", "zerocost_rows31_40_matrix.json")
_RID = re.compile(r"^[0-9a-f]{16}$")
_RUNS = os.path.realpath(os.path.join(ROOT, "results", "runs"))


def _load_artifact_safe(rid):
    """Normalized, prefix-checked read of one artifact by validated run_id."""
    if not _RID.match(str(rid)):
        raise ValueError(f"refusing non run_id: {rid!r}")
    p = os.path.realpath(os.path.join(_RUNS, str(rid) + ".json"))
    if not (p.startswith(_RUNS + os.sep) and os.path.isfile(p)):
        raise ValueError(f"artifact outside the runs dir: {rid!r}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# (tag, adapter, tf, symbol, base_params, zero_params, extra_params_or_None)
CELLS = [
    ("qs-JUP-1h-QS009", "qs", "1h", "JUPUSDT",
     {"strat": "QS-009", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-009", "variant": "two-sided", "costs": "zero", "funding": False}, None),
    ("cbpackf-ETH-1h-S10", "cbpackf", "1h", "ETHUSDT",
     {"fee_bps": 5.0, "slippage_bps": 0.5, "funding": True},
     {"fee_bps": 0.0, "slippage_bps": 0.0, "funding": False}, None),
    ("rsimr-SOLUSDC-1h", "rsimr", "1h", "SOLUSDC",
     {"costs": "repo"}, {"costs": "zero"}, None),
    ("qs-SOL-1h-QS004", "qs", "1h", "SOLUSDT",
     {"strat": "QS-004", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-004", "variant": "two-sided", "costs": "zero", "funding": False}, None),
    ("qs-SUI-1h-QS006", "qs", "1h", "SUIUSDT",
     {"strat": "QS-006", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-006", "variant": "two-sided", "costs": "zero", "funding": False}, None),
    ("fingrad-ETH-1h-day", "fingrad", "1h", "ETHUSDT",
     {"funding": True, "preset": "day", "costs": "author"},
     {"funding": False, "preset": "day", "costs": "zero"}, None),
    ("dspack-BNB-1h-ds1", "dspack", "1h", "BNBUSDT",
     {"strat": "ds1", "costs": "author", "window": "full"},
     {"strat": "ds1", "costs": "author", "window": "full"},
     {"strat": "ds1", "costs": "repo6x5", "window": "full"}),
    ("dspack-DOGE-1h-ds1", "dspack", "1h", "DOGEUSDT",
     {"strat": "ds1", "costs": "author", "window": "full"},
     {"strat": "ds1", "costs": "author", "window": "full"},
     {"strat": "ds1", "costs": "repo6x5", "window": "full"}),
    ("qs-HYPE-1h-QS006", "qs", "1h", "HYPEUSDT",
     {"strat": "QS-006", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-006", "variant": "two-sided", "costs": "zero", "funding": False}, None),
    ("qs-ETH-1h-QS005", "qs", "1h", "ETHUSDT",
     {"strat": "QS-005", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-005", "variant": "two-sided", "costs": "zero", "funding": False}, None),
]

# the ten published rows -> where the number lives inside each artifact
BOOKS = [
    (31, "qs-JUP-1h-QS009", "QS-009 Volatility-adjusted momentum", "JUPUSDT 1h", "metrics"),
    (32, "cbpackf-ETH-1h-S10", "S10 Vol-Targeted Time-Series Momentum", "ETHUSDT 1h", "S10"),
    (33, "rsimr-SOLUSDC-1h", "rsimr", "SOLUSDC 1h", "metrics"),
    (34, "qs-SOL-1h-QS004", "QS-004 Donchian channel breakout", "SOLUSDT 1h", "metrics"),
    (35, "qs-SUI-1h-QS006", "QS-006 ADX-filtered directional continuation", "SUIUSDT 1h", "metrics"),
    (36, "fingrad-ETH-1h-day", "fingrad", "ETHUSDT 1h", "metrics"),
    (37, "dspack-BNB-1h-ds1", "ds1", "BNBUSDT 1h", "metrics"),
    (38, "dspack-DOGE-1h-ds1", "ds1", "DOGEUSDT 1h", "metrics"),
    (39, "qs-HYPE-1h-QS006", "QS-006 ADX-filtered directional continuation", "HYPEUSDT 1h", "metrics"),
    (40, "qs-ETH-1h-QS005", "QS-005 Time-series momentum", "ETHUSDT 1h", "metrics"),
]

# each adapter names its own net / pf / drawdown / funding field; the report
# quotes them AS STORED, including the differing funding sign conventions
KEYS = {
    "qs": dict(net="return_base_pct", pf="pf", n="n_trades", dd="max_dd_pct",
               fund="funding_paid", bh="bh_return_pct"),
    "cbpackf": dict(net="return_pct", pf="profit_factor", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct"),
    "rsimr": dict(net="return_pct", pf="profit_factor", n="n_trades",
                  dd="max_dd_pct", fund=None, bh="bh_return_pct"),
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
    """One normalized record for a published book, from the artifact's own
    numbers."""
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
            art = _load_artifact_safe(rid)
            entry[regime] = {"run_id": rid, **extract(art, where)}
        if "costed" in cell_rec[tag]:
            rid = cell_rec[tag]["costed"]["run_id"]
            art = _load_artifact_safe(rid)
            entry["costed"] = {"run_id": rid, **extract(art, where)}
        b, z = entry["base"], entry["zero"]
        entry["delta_pct"] = (z["net_pct"] - b["net_pct"]
                              if z["net_pct"] is not None and b["net_pct"] is not None else None)
        books.append(entry)

    out_real = os.path.realpath(OUT)
    root_real = os.path.realpath(ROOT)
    if not out_real.startswith(root_real + os.sep):
        raise ValueError(f"output outside the repo root: {OUT}")
    payload = {"campaign": "zerocost-rows31-40-2026-11-23", "cells": cell_rec,
               "books": books,
               "note": "control, not a verdict: no gate is evaluated and no row is "
                       "evidence of alpha (results/zerocost_rows31_40_pre_registration.md)"}
    with open(out_real, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, default=str)
    print("wrote", OUT)

    print("\n%-3s %-46s %-13s %10s %10s %10s %6s %6s" % (
        "#", "book", "market", "base %", "zero %", "costed %", "n", "PF"))
    for e in books:
        b, z = e["base"], e["zero"]
        c = e.get("costed")
        print("%-3d %-46s %-13s %10.2f %10.2f %10s %6s %6.3f" % (
            e["row"], e["book"][:46], e["market"], b["net_pct"], z["net_pct"],
            f"{c['net_pct']:.2f}" if c else "-", z["n_trades"], z["pf"]))


if __name__ == "__main__":
    main()
