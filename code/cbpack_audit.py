#!/usr/bin/env python
"""Known-answer audit of strategy_pack.py's EXECUTION ENGINE.

AGENTS.md forbids trusting an engine's numbers before a parity/self-check. The
pack ships no tests and no reference results, so this file IS the parity check:
every case below states the arithmetic independently (in the expected_* values)
and asserts the engine reproduces it to floating-point tolerance.

What is under test is the part that silently costs money -- fills, fees, the
SL/TP race, the time stop, end-of-data handling and equity accounting. The
signal definitions are NOT under test here; they are exercised separately by
signal_count() so that a strategy silently emitting zero signals cannot hide.

Run:  python code\\cbpack_audit.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

PACK = os.path.join(os.path.expanduser("~"), "Downloads", "strategy_pack.py")
sys.path.insert(0, os.path.dirname(PACK))
import strategy_pack as P  # noqa: E402

TOL = 1e-9
FAILS = []


def check(name, got, want, tol=TOL):
    if isinstance(want, (int, float, np.integer, np.floating)) and not isinstance(want, bool):
        ok = abs(float(got) - float(want)) <= tol
    else:
        ok = bool(got == want)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")
    if not ok:
        FAILS.append(name)
    return ok


def mkdf(rows, vol=1000.0):
    rows = [[*r, vol] if len(r) == 4 else list(r) for r in rows]
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1h", tz="UTC")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=idx, dtype=float)


def mksig(df, buy=None, sell=None, sl=None, tp=None, mh=0, exl=None, exs=None):
    n = len(df)
    z = np.zeros(n, bool)
    return pd.DataFrame(
        {"buy": z if buy is None else np.asarray(buy, bool),
         "sell": z if sell is None else np.asarray(sell, bool),
         "sl_dist": np.full(n, np.nan) if sl is None else np.asarray(sl, float),
         "tp_dist": np.full(n, np.nan) if tp is None else np.asarray(tp, float),
         "max_hold": int(mh),
         "exit_long": z if exl is None else np.asarray(exl, bool),
         "exit_short": z if exs is None else np.asarray(exs, bool)},
        index=df.index)


def cfg(fee=5.0, slip=2.0, sizing="fixed_pct", rule="sl_first", pct=100.0, lev=3.0, opposite="ignore"):
    return P.BacktestConfig(fee_bps=fee, slippage_bps=slip, sizing_mode=sizing, pct_equity=pct,
                            max_leverage=lev, both_hit_rule=rule, opposite_signal=opposite)


# ─────────────────────────────────────────────────────────── case 1: long via TP
def case_tp_fill():
    print("\nCASE 1 -- long entry at next open + slippage, exit at TP, fees on both fills")
    df = mkdf([[100, 101, 99, 100], [100, 105, 99.5, 104], [104, 106, 103, 105]])
    sig = mksig(df, buy=[True, False, False], sl=[5.0, np.nan, np.nan], tp=[3.0, np.nan, np.nan])
    r = P.backtest(df, sig, cfg())          # fixed_pct 100%, lev 3, fee 5bps, slip 2bps
    fee, slip = 5 / 1e4, 2 / 1e4

    entry = 100.0 * (1 + slip)                       # bar-1 OPEN, adverse slippage
    qty = min(10000.0 * 1.0 / 100.0, 10000.0 * 3.0 / entry)
    efee = qty * entry * fee
    tp = entry + 3.0
    xfee = qty * tp * fee
    gross = 1 * qty * (tp - entry)
    pnl = gross - xfee - efee
    cash = 10000.0 - efee + gross - xfee

    check("entry price", r.trades.entry.iloc[0], entry)
    check("qty", r.trades.qty.iloc[0], qty)
    check("exit price == TP", r.trades.exit.iloc[0], tp)
    check("exit reason", r.trades.reason.iloc[0], "tp")
    check("trade pnl", r.trades.pnl.iloc[0], pnl)
    check("fees paid (both fills)", r.trades.fees.iloc[0], efee + xfee)
    check("final cash == equity[last]", r.equity.iloc[-1], cash)
    check("net_return_pct", r.metrics["net_return_pct"], (cash / 10000.0 - 1) * 100)
    check("gross_return_pct (pre-fee)", r.metrics["gross_return_pct"], (pnl + efee + xfee) / 10000.0 * 100)
    check("n_trades", r.metrics["n_trades"], 1)
    check("entry bar is the bar AFTER the signal", r.trades.entry_time.iloc[0], df.index[1])
    check("exit_reasons", r.metrics["exit_reasons"], {"tp": 1})
    check("buy_hold_%", r.metrics["buy_hold_return_pct"], (105 / 100 - 1) * 100)
    check("win_rate_%", r.metrics["win_rate_pct"], 100.0)


# ──────────────────────────────────────── case 2: SL-first when both levels hit
def case_sl_first():
    print("\nCASE 2 -- SL and TP both inside one bar; sl_first rule must take the SL")
    df = mkdf([[100, 101, 99, 100], [100, 103, 97, 100]])
    sig = mksig(df, buy=[True, False], sl=[2.0, np.nan], tp=[2.0, np.nan])
    r = P.backtest(df, sig, cfg(rule="sl_first"))
    slip = 2 / 1e4
    entry = 100.0 * (1 + slip)
    sl, tp = entry - 2.0, entry + 2.0
    check("exit price == slipped SL", r.trades.exit.iloc[0], sl * (1 - slip))
    check("exit reason", r.trades.reason.iloc[0], "sl")

    r2 = P.backtest(df, sig, P.BacktestConfig(fee_bps=5, slippage_bps=2, sizing_mode="fixed_pct",
                                              pct_equity=100, max_leverage=3, both_hit_rule="tp"))
    check("configurable rule: tp wins -> exit price == TP", r2.trades.exit.iloc[0], tp)
    check("configurable rule: reason", r2.trades.reason.iloc[0], "tp")


# ──────────────────────────────────────────────────────────── case 3: time stop
def case_time_stop():
    print("\nCASE 3 -- time stop fires at max_hold bars and exits at the NEXT open")
    df = mkdf([[100, 101, 99, 100], [100, 101, 99, 100], [100, 102, 99, 101],
               [101, 103, 100, 102], [102, 103, 101, 102]])
    sig = mksig(df, buy=[True, False, False, False, False], sl=[50.0, np.nan, np.nan, np.nan, np.nan], mh=2)
    r = P.backtest(df, sig, cfg())
    slip = 2 / 1e4
    check("exit bar", r.trades.exit_time.iloc[0], df.index[3])   # entry at 1, hold 2 -> decide at 2, fill at 3
    check("exit reason", r.trades.reason.iloc[0], "time_stop")
    check("exit price == open[3] slipped", r.trades.exit.iloc[0], 101.0 * (1 - slip))
    check("bars in trade", r.trades.bars.iloc[0], 2)


# ─────────────────────────────────────────────────────── case 4: end of data
def case_end_of_data():
    print("\nCASE 4 -- position still open at the last bar is closed there, with slippage")
    df = mkdf([[100, 101, 99, 100], [100, 101, 99, 100], [100, 101, 99, 100]])
    sig = mksig(df, buy=[True, False, False], sl=[50.0, np.nan, np.nan])
    r = P.backtest(df, sig, cfg())
    slip = 2 / 1e4
    entry = 100.0 * (1 + slip)
    efee = 100.0 * entry * (5 / 1e4)
    exit_px = 100.0 * (1 - slip)
    xfee = 100.0 * exit_px * (5 / 1e4)
    gross = 1 * 100.0 * (exit_px - entry)
    check("exit reason", r.trades.reason.iloc[0], "end_of_data")
    check("exit price == close[last] slipped", r.trades.exit.iloc[0], exit_px)
    check("equity[last] == cash after the forced close", r.equity.iloc[-1], 10000.0 - efee + gross - xfee)
    check("net_return_pct after the forced close", r.metrics["net_return_pct"],
          (10000.0 - efee + gross - xfee) / 10000.0 * 100 - 100)


# ─────────────────────────────────────────────────────────── case 5: short side
def case_short():
    print("\nCASE 5 -- short: entry below the open, SL ABOVE, TP BELOW")
    df = mkdf([[100, 101, 99, 100], [100, 105, 97, 98]])          # h=105 clears the short's stop
    sig = mksig(df, sell=[True, False], sl=[2.0, np.nan], tp=[2.0, np.nan])
    r = P.backtest(df, sig, cfg(rule="sl_first"))
    slip = 2 / 1e4
    entry = 100.0 * (1 - slip)
    check("dir", r.trades.dir.iloc[0], -1)
    check("entry (adverse for a short = below open)", r.trades.entry.iloc[0], entry)
    check("sl level is ABOVE entry", bool(r.trades.exit.iloc[0] > entry), True)
    check("SL fill is slipped FURTHER against the short", r.trades.exit.iloc[0], (entry + 2.0) * (1 + slip))
    check("reason", r.trades.reason.iloc[0], "sl")

    df2 = mkdf([[100, 101, 99, 100], [100, 101, 97, 98]])
    sig2 = mksig(df2, sell=[True, False], sl=[10.0, np.nan], tp=[1.0, np.nan])
    r2 = P.backtest(df2, sig2, cfg())
    check("short TP below entry", r2.trades.exit.iloc[0], entry - 1.0)
    check("short reason", r2.trades.reason.iloc[0], "tp")


# ─────────────────────────────────────────────────── case 6: no same-bar entry
def case_no_lookahead():
    print("\nCASE 6 -- the signal bar's own price is never used for the fill")
    rows = [[100, 101, 99, 100.5], [200, 201, 199, 200], [300, 301, 299, 300]]
    df = mkdf(rows)
    sig = mksig(df, buy=[False, True, False], sl=[50.0, 50.0, np.nan])
    r = P.backtest(df, sig, cfg())
    slip = 2 / 1e4
    check("entry bar index", r.trades.entry_time.iloc[0], df.index[2])
    check("entry uses bar-2 open (300), not bar-1 close (200)",
          r.trades.entry.iloc[0], 300.0 * (1 + slip))


# ─────────────────────────────────────────── case 7: sizing / leverage / risk
def case_sizing():
    print("\nCASE 7 -- stop_risk sizing and the leverage cap")
    df = mkdf([[100, 101, 99, 100], [100, 105, 99, 104], [104, 106, 103, 105]])
    sig = mksig(df, buy=[True, False, False], sl=[10.0, np.nan, np.nan], tp=[3.0, np.nan, np.nan])
    c = P.BacktestConfig(fee_bps=5, slippage_bps=2, sizing_mode="stop_risk", risk_pct=1.0, max_leverage=3.0)
    r = P.backtest(df, sig, c)
    entry = 100.0 * 1.0002
    want_qty = min(10000.0 * 0.01 / 10.0, 10000.0 * 3.0 / entry)   # 10 units, cap 299.94
    check("stop_risk qty", r.trades.qty.iloc[0], want_qty)

    c2 = P.BacktestConfig(fee_bps=5, slippage_bps=2, sizing_mode="stop_risk", risk_pct=1.0, max_leverage=3.0)
    sig_tight = mksig(df, buy=[True, False, False], sl=[0.1, np.nan, np.nan], tp=[3.0, np.nan, np.nan])
    r2 = P.backtest(df, sig_tight, c2)
    # the cap is eq*max_lev / close[signal bar] -- NOT the entry price, which is not
    # known when the size is computed. Slippage can therefore push realised notional
    # a hair above the cap (300 * 100.02 = 3.0006x here).
    check("leverage cap binds on a tight stop", r2.trades.qty.iloc[0], 10000.0 * 3.0 / 100.0)
    check("cap is computed on the signal bar close, not the fill",
          bool(r2.trades.qty.iloc[0] * r2.trades.entry.iloc[0] > 10000.0 * 3.0), True)


# ────────────────────────────────────────── case 9: signals are causal (no peek)
def case_causality(df):
    print("\nCASE 9 -- truncating the FUTURE must not change a past signal")
    k = 4000
    for sid, spec in P.STRATEGIES.items():
        if spec.requires:
            continue
        try:
            full = spec.fn(df)
            cut = spec.fn(df.iloc[:k])
        except Exception as e:
            print(f"  [SKIP] {sid} {type(e).__name__} {e}")
            continue
        j = k - 1
        same = (bool(full["buy"].iloc[j]) == bool(cut["buy"].iloc[j]) and
                bool(full["sell"].iloc[j]) == bool(cut["sell"].iloc[j]))
        print(f"  [{'PASS' if same else 'FAIL'}] {sid} signal at row {j} identical when the future is removed")
        if not same:
            FAILS.append(f"{sid} signal peeks at the future")


# ─────────────────────────────────────── case 8: signal-level sanity on real data
def signal_count(df, tag):
    print(f"\nCASE 8 -- every strategy must emit signals on real data ({tag})")
    for sid, spec in P.STRATEGIES.items():
        try:
            sig = spec.fn(df)
        except P.MissingData as e:
            print(f"  [SKIP] {sid} {spec.name}: {e}")
            continue
        nb, ns = int(sig["buy"].sum()), int(sig["sell"].sum())
        ok = (nb + ns) > 0
        print(f"  [{'PASS' if ok else 'FAIL'}] {sid} buy={nb:<6} sell={ns:<6} flow_source={sig.attrs.get('meta', {}).get('flow_source')}")
        if not ok:
            FAILS.append(f"{sid} emitted zero signals on {tag}")


def main() -> int:
    case_tp_fill()
    case_sl_first()
    case_time_stop()
    case_end_of_data()
    case_short()
    case_no_lookahead()
    case_sizing()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(root, "data", "binance_klines_1h_taker", "HYPEUSDT_1h.csv")
    raw = pd.read_csv(d)
    raw = raw.rename(columns={"open_ts": "open_time"})
    raw["open_time"] = pd.to_datetime(raw["open_time"], unit="ms", utc=True)
    df = P.prepare(raw.set_index("open_time"))
    signal_count(df, "HYPEUSDT 1h taker")
    case_causality(df)

    print("\n" + "=" * 78)
    if FAILS:
        print(f"AUDIT FAILED -- {len(FAILS)} case(s):")
        for f in FAILS:
            print("   -", f)
        return 1
    print("AUDIT PASSED -- engine arithmetic, fill convention and sizing all reproduce")
    return 0


if __name__ == "__main__":
    sys.exit(main())
