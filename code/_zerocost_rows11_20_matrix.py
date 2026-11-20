"""The 2026-11-20 zero-cost / no-rules control, rows 11-20: ten books, two
regimes each.

Ten books = rows 11-20 of results/top100_2026-10-31.md, unedited. Nine
adapter runs (rows 16 and 17 are two strategies inside the same eqpack QQQ
artifact), each made twice:

    BASE = the regime the book was published by
    ZERO = fees 0.0, slippage 0.0, funding cash flow 0.0, same engine bytes

The cand7 cell runs with cut_ts="full" (legacy hashing): that engine reads
its data by repo-root path, not from the served files, so a generation-2 cut
would describe bytes it does not read (declared in the pre-registration).
No gate is evaluated: this is a control, not a verdict (REGLA 0/1).

Run: python code/_zerocost_rows11_20_matrix.py
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

OUT = os.path.join(ROOT, "results", "zerocost_rows11_20_matrix.json")
_RID = re.compile(r"^[0-9a-f]{16}$")
_RUNS = os.path.realpath(os.path.join(ROOT, "results", "runs"))


def _check_rid(rid):
    """A run_id is 16 hex chars; refuse anything else before any path use."""
    if not _RID.match(str(rid)):
        raise ValueError(f"refusing non run_id: {rid!r}")
    return rid


def _load_artifact_safe(rid):
    """Normalized, prefix-checked read of one artifact by validated run_id."""
    _check_rid(rid)
    p = os.path.realpath(os.path.join(_RUNS, str(rid) + ".json"))
    if not (p.startswith(_RUNS + os.sep) and os.path.isfile(p)):
        raise ValueError(f"artifact outside the runs dir: {rid!r}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# (tag, adapter, tf, symbol, base_params, zero_params)
CELLS = [
    ("qs-HYPE-1h-QS001", "qs", "1h", "HYPEUSDT",
     {"strat": "QS-001", "variant": "two-sided", "costs": "repo", "funding": True},
     {"strat": "QS-001", "variant": "two-sided", "costs": "zero", "funding": False}),
    ("botstrat-AVAX-1h", "botstrat", "1h", "AVAXUSDT",
     {"costs": "repo"}, {"costs": "zero"}),
    ("cand7-SOL-1h-C7", "cand7", "1h", "SOLUSDT",
     {"cand": 7, "costs": "repo", "funding": True},
     {"cand": 7, "costs": "zero", "funding": False}),
    ("botstrat-ETH-1h", "botstrat", "1h", "ETHUSDT",
     {"costs": "repo"}, {"costs": "zero"}),
    ("botstrat-SOL-1h", "botstrat", "1h", "SOLUSDT",
     {"costs": "repo"}, {"costs": "zero"}),
    ("eqpack-QQQ-1d", "eqpack", "1d", "QQQ",
     {"costs": "eq"}, {"costs": "zero"}),
    ("smqe-SOL-1h", "smqe", "1h", "SOLUSDT",
     {"cost_mode": "repo", "funding": True},
     {"cost_mode": "zero", "funding": False}),
    ("cvrmd-SOL-1h", "cvrmd", "1h", "SOLUSDT",
     {"costs": "repo"}, {"costs": "zero"}),
    ("botstrat-BTC-1h", "botstrat", "1h", "BTCUSDT",
     {"costs": "repo"}, {"costs": "zero"}),
]

# the ten published rows -> where the number lives inside each artifact
# ("row",) = a metrics field, ("row", sid) = a table row for that strategy id
BOOKS = [
    (11, "qs-HYPE-1h-QS001", "QS-001 Moving-average trend continuation", "HYPEUSDT 1h", "metrics"),
    (12, "botstrat-AVAX-1h", "botstrat", "AVAXUSDT 1h", "metrics"),
    (13, "cand7-SOL-1h-C7", "C7", "SOLUSDT 1h", "metrics"),
    (14, "botstrat-ETH-1h", "botstrat", "ETHUSDT 1h", "metrics"),
    (15, "botstrat-SOL-1h", "botstrat", "SOLUSDT 1h", "metrics"),
    (16, "eqpack-QQQ-1d", "S01 Taker-Flow Drift Bands", "QQQ 1d", "S01"),
    (17, "eqpack-QQQ-1d", "S05 HTF Trend Pullback (RSI-2)", "QQQ 1d", "S05"),
    (18, "smqe-SOL-1h", "smqe", "SOLUSDT 1h", "metrics"),
    (19, "cvrmd-SOL-1h", "cvrmd", "SOLUSDT 1h", "metrics"),
    (20, "botstrat-BTC-1h", "botstrat", "BTCUSDT 1h", "metrics"),
]

# each adapter names its own net / pf / drawdown / funding field; the report
# quotes them AS STORED, including the differing funding sign conventions
KEYS = {
    "qs": dict(net="return_base_pct", pf="pf", n="n_trades", dd="max_dd_pct",
               fund="funding_paid", bh="bh_return_pct"),
    "cand7": dict(net="return_pct", pf="profit_factor", n="n_trades",
                  dd="max_dd_pct", fund="funding_net_usdt", bh="bh_return_pct"),
    "smqe": dict(net="return_pct", pf="pf_nextopen", n="n_trades",
                 dd="max_dd_pct", fund="funding_paid_usd", bh="bh_return_pct"),
}
DEFAULT_KEYS = dict(net="return_pct", pf="profit_factor", n="n_trades",
                    dd="max_dd_pct", fund="funding_paid", bh="bh_return_pct")


def num(x):
    return None if x is None else (float(x) if isinstance(x, (int, float)) else x)


def extract(art, where):
    """One normalized record for a published book, from the artifact's own
    numbers. `where` names the metrics block or the table row (strategy id)."""
    m = art["metrics"]
    if where == "metrics":
        k = KEYS.get(art["strategy"], DEFAULT_KEYS)
        return {"net_pct": num(m[k["net"]]), "pf": num(m[k["pf"]]),
                "n_trades": m[k["n"]], "max_dd_pct": num(m[k["dd"]]),
                "funding_paid": num(m.get(k["fund"])),
                "bh_pct": num(m.get(k["bh"]))}
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
        cut = "full" if adapter == "cand7" else "auto"
        rec = {"tag": tag, "adapter": adapter, "symbol": sym, "tf": tf,
               "cut_ts_mode": cut}
        for regime, params in (("base", bp), ("zero", zp)):
            print(f"[{tag}] {regime} ...", flush=True)
            a = V.make_artifact(adapter, tf, sym, dict(params), cut_ts=cut)
            path = V.save_artifact(a)
            rec[regime] = {"run_id": a["run_id"], "params": params,
                           "artifact": "results/runs/" + os.path.basename(path),
                           "cut_ts": a["core"].get("cut_ts"),
                           "inputs": [os.path.basename(i["path"]) for i in a["inputs"]]}
            print(f"    {a['run_id']}  {os.path.basename(path)}", flush=True)
        cell_rec[tag] = rec

    books = []
    for row, tag, label, market, where in BOOKS:
        entry = {"row": row, "book": label, "market": market, "tag": tag, "where": where}
        for regime in ("base", "zero"):
            rid = cell_rec[tag][regime]["run_id"]
            art = _load_artifact_safe(rid)
            entry[regime] = {"run_id": rid, **extract(art, where)}
        b, z = entry["base"], entry["zero"]
        entry["delta_pct"] = (z["net_pct"] - b["net_pct"]
                              if z["net_pct"] is not None and b["net_pct"] is not None else None)
        books.append(entry)

    out_real = os.path.realpath(OUT)
    root_real = os.path.realpath(ROOT)
    if not out_real.startswith(root_real + os.sep):
        raise ValueError(f"output outside the repo root: {OUT}")
    payload = {"campaign": "zerocost-rows11-20-2026-11-20", "cells": cell_rec,
               "books": books,
               "note": "control, not a verdict: no gate is evaluated and no row is "
                       "evidence of alpha (results/zerocost_rows11_20_pre_registration.md)"}
    with open(out_real, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1, sort_keys=False, default=str)
    print("wrote", OUT)

    print("\n%-3s %-46s %-13s %10s %10s %8s %6s %6s" % (
        "#", "book", "market", "base %", "zero %", "delta", "n", "PF"))
    for e in books:
        b, z = e["base"], e["zero"]
        print("%-3d %-46s %-13s %10.2f %10.2f %8.2f %6s %6.3f" % (
            e["row"], e["book"][:46], e["market"], b["net_pct"], z["net_pct"],
            e["delta_pct"], z["n_trades"], z["pf"]))


def regime_params(p):
    return p


if __name__ == "__main__":
    main()
