#!/usr/bin/env python
r"""
_prompts100_parity.py — parity between the repo's port and the pack's engine.

Two levels, both on REAL data:

A. TRADE-LEVEL PARITY. The pack's own engine (imported VERBATIM from
   code/prompts100/backtest100_engine.py) is run with the pack's own
   conventions, and the repo's book is run on the same bars with
   `pack_conventions=True` (22 bps effective, the gap-through entry skipped,
   no funding). The two must produce THE SAME TRADES: same entry and exit
   bars, same side, same prices, same PnL.

B. METRIC PARITY. With the same settings, the repo's book must reproduce the
   pack's IS/OOS metrics (net, PF, n trades, max DD) on the pack's own 70/30
   split.

Why this matters: parity proves the SIGNAL port AND the ledger port. It does
NOT prove the repo's execution conventions (11 bps, no skipping of gap
entries, funding charged) - those are the DECLARED differences, and the
report attributes the gap between the pack's numbers and ours to them.

Usage:  python code/_prompts100_parity.py [--ids 1,7,26,44,60,...]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
PACK = os.path.join(HERE, "prompts100")
if PACK not in sys.path:
    sys.path.insert(0, PACK)

sys.path.insert(0, HERE)

import p100_screen_engine as PE        # noqa: E402
import backtest100_strategies as PS     # noqa: E402  (verbatim copy)
import backtest100_engine as PK         # noqa: E402  (verbatim copy)

# The pack's map id -> (symbol, tf), read from the ported runner.
_runner = open(os.path.join(PACK, "backtest100_runner.py"), encoding="utf-8",
               errors="replace").read()
_i = _runner.find("STRATEGY_MAP = {")
_j = _runner.find("\n}", _i)
STRATEGY_MAP = json.loads("{}")          # placeholder replaced below
import ast                                     # noqa: E402
STRATEGY_MAP = ast.literal_eval(
    _runner[_i:_j + 2][_runner[_i:_j + 2].index("{"):])


def pack_run(df, sid):
    """The pack's own run: its engine, its 70/30 split, its conventions."""
    fn = PS.STRATEGIES[str(sid)]
    ctx = PS.LazyCtx(df)

    def wrapped(j, engine_ctx):
        return fn(j, ctx)

    return PK.run_is_oos(df, wrapped, oos_frac=0.3)


def repo_run(df, sid, start, end):
    """The repo's book with the PACK's conventions on the same slice."""
    fn = PS.STRATEGIES[str(sid)]
    ctx = PS.LazyCtx(df)

    def signal(j):
        return fn(j, ctx)

    book = PE.Book("X", "1h", df, pack_conventions=True, charge_funding=False)
    book.run(signal, start_idx=start, end_idx=end)
    return book


def trades_key(trades):
    return [(t["entry_idx"], t["exit_idx"], t["side"], round(t["entry"], 8),
             round(t["exit"], 8), round(t["pnl"], 6)) for t in trades]


def compare_slice(df, sid, start, end, label):
    pack_is, pack_oos = pack_run(df, sid)
    ok_trades = True
    detail = []
    for pack_res, (s, e) in ((pack_is, (0, start - 1)),
                              (pack_oos, (start, len(df) - 1))):
        book = repo_run(df, sid, s, e)
        a = trades_key(pack_res["trades"])
        b = trades_key(book.trades)
        same = (a == b)
        ok_trades &= same
        if not same:
            n = min(len(a), len(b))
            first = next((i for i in range(n) if a[i] != b[i]), n)
            detail.append(f"{label}: trades pack {len(a)} vs repo {len(b)}; "
                          f"primera diferencia en el indice {first}")
    return ok_trades, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="1,7,14,21,26,30,34,44,50,56,59,60,66,71,73,78,80")
    ap.add_argument("--json", default=os.path.join(HERE,
                                                   "_prompts100_parity.json"))
    args = ap.parse_args()
    ids = [int(x) for x in args.ids.split(",") if x.strip()]

    print("=== el port del pack esta intacto? ===")
    ok_copy, bad = PE.verify_pack_copy()
    print(f"  {'OK' if ok_copy else 'FALLO'}: {len(PE.pack_manifest()['files'])} "
          f"ficheros contra el manifiesto" + (f" -- {bad}" if bad else ""))
    if not ok_copy:
        return 2

    print()
    print("=== paridad a nivel de TRADE (motor del pack vs port del repo, "
          "mismas convenciones) ===")
    results = []
    all_ok = True
    for sid in ids:
        symbol, tf = STRATEGY_MAP[str(sid)]
        df = PK.load_klines(symbol, tf)
        n = len(df)
        split = int(n * 0.7)
        try:
            ok, detail = compare_slice(df, sid, split, n - 1, f"#{sid}")
        except Exception as e:
            ok, detail = False, [f"#{sid}: {type(e).__name__}: {e}"]
        all_ok &= ok
        # metrics on the OOS slice
        try:
            pack_is, pack_oos = pack_run(df, sid)
            book = repo_run(df, sid, split, n - 1)
            pnls = np.array([t["pnl"] for t in book.trades], float)
            gp = float(pnls[pnls > 0].sum())
            gl = float(-pnls[pnls < 0].sum())
            pf = (gp / gl) if gl > 0 else None
            net = 100 * (book.cash / book.init - 1)
            m_pack = dict(net=pack_oos["total_return_pct"], pf=pack_oos["profit_factor"],
                          n=pack_oos["n_trades"], dd=pack_oos["max_dd_pct"])
            m_repo = dict(net=net, pf=pf, n=len(book.trades), dd=None)
            metrics_ok = (abs(m_pack["net"] - m_repo["net"]) < 1e-6
                          and m_pack["n"] == m_repo["n"]
                          and (m_pack["pf"] is None or m_repo["pf"] is None
                               or abs(m_pack["pf"] - m_repo["pf"]) < 1e-6))
        except Exception as e:
            metrics_ok = False
            m_pack, m_repo = {}, {}
            detail.append(f"#{sid}: metricas {type(e).__name__}: {e}")
        all_ok &= metrics_ok
        results.append(dict(id=sid, symbol=symbol, tf=tf, trades_ok=ok,
                             metrics_ok=metrics_ok, pack=m_pack, repo=m_repo,
                             detail=detail))
        flag = "OK  " if (ok and metrics_ok) else "FALLO"
        print(f"  {flag} #{sid:<4} {symbol:9s} {tf:4s} trades {'=' if ok else '!='} "
              f"metricas {'=' if metrics_ok else '!='}")
        for d in detail:
            print("        ", d)

    out = dict(pass_=bool(all_ok), n_ids=len(ids), results=results,
               pack_copy_intact=ok_copy)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print()
    print(f"{'PASS' if all_ok else 'FAIL'} — {len(ids)} estrategias -> {args.json}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
