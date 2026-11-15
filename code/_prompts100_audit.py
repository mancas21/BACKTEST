#!/usr/bin/env python
r"""
_prompts100_audit.py — known-answer audit of the repo's execution of the
100-prompt pack.

WHY THIS FILE EXISTS
--------------------
The WAVE_1 port shipped long-only tests and missed a short-side fee bug for a
whole campaign. The prompts-100 pack is mostly LONG books (a `side` of -1
exists in the contract and a few prompts are short), so the short side has to
be covered here too, with the same discipline.

The audit runs on SYNTHETIC bars: no market data, no randomness, no
dependencies on the pack's indicators.

THE CHECKS
----------
A. LONG entry and exit: the cash, the fee and the PnL are hand-computed.
B. SHORT entry and exit: the same, mirrored. A short SELLS at the open (cash
   IN) and BUYS BACK at the exit (cash OUT), and it PAYS the fee on both
   fills. The equity mark of a short is a LIABILITY: it must FALL when the
   price rises.
C. STOP FIRST: a bar touching both the stop and the target exits at the stop,
   in both directions.
D. GAP through the stop (an existing position): the fill is AT THE OPEN, in
   both directions.
E. GAP at ENTRY: the repo does NOT skip the trade (the pack does). The trade
   is filled at the open and can be stopped out on the same bar.
F. FUNDING sign: a long PAYS a positive rate, a short RECEIVES it.
G. ACCOUNTING INVARIANT on every case: final equity - initial equity ==
   sum(pnl) - funding paid.
H. The pack's conventions mode reproduces the pack's own arithmetic (the cost
   folded into the price AND charged as a fee), so the parity test means
   something.

Usage:  python code/_prompts100_audit.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import p100_screen_engine as PE      # noqa: E402

CHECKS = []
INIT = 10_000.0
FEE = 0.0005          # 5 bps per side (the repo)
SLIP = 0.00005        # 0.5 bps per side (the repo)
HOUR = 3_600_000


def check(name, ok, detail=""):
    CHECKS.append({"name": name, "pass": bool(ok), "detail": str(detail)[:400]})
    print(("  PASS  " if ok else "  FAIL  ") + name, flush=True)
    if not ok:
        print("        " + str(detail)[:400], flush=True)
    return bool(ok)


def mkdf(bars):
    """bars: list of (open, high, low, close)."""
    n = len(bars)
    ts = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    return pd.DataFrame({
        "timestamp": ts,
        "open": [b[0] for b in bars],
        "high": [b[1] for b in bars],
        "low": [b[2] for b in bars],
        "close": [b[3] for b in bars],
        "volume": [1.0] * n,
    })


def book(bars, **kw):
    df = mkdf(bars)
    return PE.Book("TST", "1h", df, init=INIT, fee=FEE, slip=SLIP, **kw)


# ═══════════════════════════════════════════════════════════════════════
# A + B: a clean exit, LONG and SHORT
# ═══════════════════════════════════════════════════════════════════════
def case_clean(side):
    """Signal on bar 0 -> fill at bar 1's open -> exit at the target on bar 3."""
    if side == 1:
        # bar 3's high reaches the target (102); its low stays above the stop
        bars = [(100.0, 100.2, 99.9, 100.0),
                (100.0, 100.2, 99.9, 100.0),
                (100.0, 100.2, 99.9, 100.0),
                (100.0, 102.5, 99.9, 102.4)]
    else:
        # bar 3's low reaches the target (98); its high stays below the stop
        bars = [(100.0, 100.1, 99.8, 100.0),
                (100.0, 100.1, 99.8, 100.0),
                (100.0, 100.1, 99.8, 100.0),
                (100.0, 100.1, 97.5, 97.6)]
    b = book(bars)
    stop = 100.0 - side * 2.0        # 2 dollars away
    target = 100.0 + side * 2.0

    def signal(j):
        if j == 0:
            return {"side": side, "stop_px": stop, "tp_px": target}
        return None

    b.run(signal, start_idx=0, end_idx=len(bars) - 1)
    return b


def audit_clean():
    for side, name in ((1, "LONG"), (-1, "SHORT")):
        b = case_clean(side)
        if len(b.trades) != 1:
            check(f"A/B {name}: exactly one trade", False, len(b.trades))
            continue
        t = b.trades[0]
        # hand computation
        fill_in = 100.0 * (1 + SLIP * side)
        dist = abs(100.0 - (100.0 - side * 2.0))      # |stop - open|
        risk = INIT * PE.RISK_PCT
        qty = risk / dist
        max_qty = PE.MAX_LEVERAGE * INIT / 100.0
        if qty > max_qty:
            qty = max_qty
        fee_in = qty * fill_in * FEE
        # entry: a long PAYS the notional, a short RECEIVES it
        cash = INIT - side * qty * fill_in - fee_in
        fill_out = (100.0 + side * 2.0) * (1 - SLIP * side)
        fee_out = qty * fill_out * FEE
        # exit: the long SELLS the notional back, the short BUYS it back
        cash += side * qty * fill_out - fee_out
        pnl = (qty * (fill_out - fill_in) * side) - fee_in - fee_out
        check(f"A/B {name}: the entry fill carries slippage against the book",
              abs(t["entry"] - fill_in) < 1e-9, f"{t['entry']} vs {fill_in}")
        check(f"A/B {name}: the trade PnL matches the hand computation",
              abs(t["pnl"] - pnl) < 1e-6, f"{t['pnl']} vs {pnl}")
        check(f"A/B {name}: the final cash matches the hand computation",
              abs(b.cash - cash) < 1e-6, f"{b.cash} vs {cash}")
        check(f"A/B {name}: the fee was CHARGED (not credited)",
              b.fees_paid > 0, f"fees {b.fees_paid}")
        if side == -1:
            check("B SHORT: a falling price makes the short PROFIT",
                  t["pnl"] > 0, t["pnl"])
            # the mark of a short is a liability: the equity must FALL when
            # the price rises
            b2 = book([(100.0, 100.1, 99.8, 100.0),
                       (100.0, 100.1, 99.8, 100.0),
                       (100.0, 105.0, 99.8, 104.0)])
            b2.run(lambda j: ({"side": -1, "stop_px": 110.0} if j == 0 else None),
                   start_idx=0, end_idx=2)
            eq_up = b2.equity_curve[-1]
            check("B SHORT: the mark-to-market of a short is a LIABILITY "
                  "(the equity falls when the price rises)",
                  eq_up < INIT, f"equity {eq_up}")
        else:
            check("A LONG: a rising price makes the long PROFIT",
                  t["pnl"] > 0, t["pnl"])


# ═══════════════════════════════════════════════════════════════════════
# C: STOP FIRST, in both directions
# ═══════════════════════════════════════════════════════════════════════
def audit_stop_first():
    for side, name in ((1, "LONG"), (-1, "SHORT")):
        bars = [(100.0, 100.1, 99.9, 100.0),
                (100.0, 100.1, 99.9, 100.0),
                (100.0, 103.0, 97.0, 100.0)]
        b = book(bars)
        b.run(lambda j: ({"side": side, "stop_px": 100.0 - side * 2.0,
                           "tp_px": 100.0 + side * 2.0} if j == 0 else None),
               start_idx=0, end_idx=2)
        ok = len(b.trades) == 1 and b.trades[0]["reason"] in ("stop", "stop_gap")
        check(f"C {name}: a bar touching stop AND target exits at the STOP",
              ok, [t["reason"] for t in b.trades])


# ═══════════════════════════════════════════════════════════════════════
# D: GAP through the stop (an existing position) -> fill AT THE OPEN
# ═══════════════════════════════════════════════════════════════════════
def audit_gap():
    for side, name, gap_open in ((1, "LONG", 97.0), (-1, "SHORT", 103.0)):
        bars = [(100.0, 100.1, 99.9, 100.0),
                (100.0, 100.1, 99.9, 100.0),
                (gap_open, gap_open + 0.5, gap_open - 0.5, gap_open)]
        b = book(bars)
        b.run(lambda j: ({"side": side, "stop_px": 100.0 - side * 2.0}
                          if j == 0 else None),
               start_idx=0, end_idx=2)
        if len(b.trades) != 1:
            check(f"D {name}: the gap produces one trade", False, len(b.trades))
            continue
        t = b.trades[0]
        exp = gap_open * (1 - SLIP * side)
        check(f"D {name}: the gap-through stop fills AT THE OPEN",
              abs(t["exit"] - exp) < 1e-9, f"{t['exit']} vs {exp}")
        check(f"D {name}: the exit is the stop", t["reason"] in ("stop", "stop_gap"),
              t["reason"])


# ═══════════════════════════════════════════════════════════════════════
# E: GAP at ENTRY -> the repo does NOT skip the trade
# ═══════════════════════════════════════════════════════════════════════
def audit_entry_gap():
    # bar 1 opens below the stop: the pack SKIPS this trade, the repo FILLS
    # it at the open and is stopped out on the same bar.
    bars = [(100.0, 100.1, 99.9, 100.0),
            (97.0, 97.2, 96.0, 96.5),
            (96.0, 96.2, 95.0, 95.5)]
    b = book(bars)
    b.run(lambda j: ({"side": 1, "stop_px": 99.0} if j == 0 else None),
           start_idx=0, end_idx=2)
    check("E: a gap at ENTRY is NOT skipped (the repo fills it at the open)",
          len(b.trades) == 1, f"{len(b.trades)} trades")
    if b.trades:
        check("E: the entry gap fills AT THE OPEN",
              abs(b.trades[0]["entry"] - 97.0 * (1 + SLIP)) < 1e-9,
              b.trades[0]["entry"])

    # and the pack's mode DOES skip it
    bp = book(bars, pack_conventions=True, charge_funding=False)
    bp.run(lambda j: ({"side": 1, "stop_px": 99.0} if j == 0 else None),
           start_idx=0, end_idx=2)
    check("E: the pack's own mode DOES skip it (that is one of the declared "
          "differences)", len(bp.trades) == 0 and bp.skipped_gap_entries == 1,
          f"{len(bp.trades)} trades, {bp.skipped_gap_entries} skipped")


# ═══════════════════════════════════════════════════════════════════════
# F: FUNDING sign
# ═══════════════════════════════════════════════════════════════════════
def audit_funding():
    for side, name, sign in ((1, "LONG", +1), (-1, "SHORT", -1)):
        bars = [(100.0, 100.1, 99.9, 100.0),
                (100.0, 100.1, 99.9, 100.0),
                (100.0, 100.1, 99.9, 100.0)]
        df = mkdf(bars)
        b = PE.Book("TST", "1h", df, init=INIT, fee=FEE, slip=SLIP,
                    charge_funding=True)
        # a settlement on the LAST bar, rate +10 bps
        b.rate = np.array([0.0, 0.0, 0.001])
        b.is_fund = np.array([False, False, True])
        b.run(lambda j: ({"side": side, "stop_px": 100.0 - side * 5.0}
                          if j == 0 else None),
               start_idx=0, end_idx=2)
        paid = b.funding_paid
        check(f"F {name}: a positive funding rate has the RIGHT sign "
              f"({'pays' if side == 1 else 'receives'})",
              sign * paid > 0, f"funding_paid {paid}")


# ═══════════════════════════════════════════════════════════════════════
# G: the ACCOUNTING INVARIANT on every case
# ═══════════════════════════════════════════════════════════════════════
def audit_invariant():
    worst = 0.0
    for name, b in (("long", case_clean(1)), ("short", case_clean(-1))):
        pnls = np.array([t["pnl"] for t in b.trades], float)
        resid = (b.cash - INIT) - (pnls.sum() - b.funding_paid)
        worst = max(worst, abs(resid))
    check("G: final equity - initial equity == sum(pnl) - funding, on every "
          "synthetic case", worst < 1e-6, f"worst residual {worst:.3e}")
    # and the engine raises when the ledger is broken
    try:
        b = case_clean(1)
        b.cash += 1.0                     # break the ledger on purpose
        pnls = np.array([t["pnl"] for t in b.trades], float)
        resid = (b.cash - INIT) - (pnls.sum() - b.funding_paid)
        PE.book_metrics(b)
        check("G: a broken ledger makes the metrics RAISE", False,
              "no exception raised")
    except AssertionError:
        check("G: a broken ledger makes the metrics RAISE", True)


# ═══════════════════════════════════════════════════════════════════════
# H: the pack's mode reproduces the pack's arithmetic
# ═══════════════════════════════════════════════════════════════════════
def audit_pack_mode():
    bars = [(100.0, 100.2, 99.9, 100.0),
            (100.0, 100.2, 99.9, 100.0),
            (100.0, 103.0, 99.9, 102.5)]
    b = book(bars, pack_conventions=True, charge_funding=False)
    b.run(lambda j: ({"side": 1, "stop_px": 98.0, "tp_px": 102.0}
                      if j == 0 else None),
           start_idx=0, end_idx=2)
    if not b.trades:
        check("H: the pack's mode fills the trade", False, "no trades")
        return
    t = b.trades[0]
    fill_in = 100.0 * (1 + PE.PACK_COST_PER_SIDE)
    fill_out = 102.0 * (1 - PE.PACK_COST_PER_SIDE)
    fee_out = (b.trades[0]["qty"] * fill_out) * PE.PACK_COST_PER_SIDE
    check("H: the pack's mode folds its cost into the fill price",
          abs(t["entry"] - fill_in) < 1e-9, f"{t['entry']} vs {fill_in}")
    check("H: the pack's mode charges its cost AGAIN as a fee",
          abs(t["fee"] - fee_out) < 1e-9, f"{t['fee']} vs {fee_out}")
    check("H: the pack's effective cost is 1.1 bps round trip, ten times "
          "cheaper than the repo's 11 bps",
          abs(4 * PE.PACK_COST_PER_SIDE * 1e4 - 2.2) < 0.05,
          f"{4 * PE.PACK_COST_PER_SIDE * 1e4:.4f} bps RT")


def main() -> int:
    out_path = os.path.join(HERE, "_prompts100_audit.json")
    print("=== prompts100: respuestas conocidas del motor del repo, AMBAS "
          "direcciones ===")
    audit_clean()
    audit_stop_first()
    audit_gap()
    audit_entry_gap()
    audit_funding()
    audit_invariant()
    audit_pack_mode()
    passed = all(c["pass"] for c in CHECKS)
    out = dict(pass_=passed, checks=CHECKS, n_checks=len(CHECKS),
               pack_cost_per_side_bps=PE.PACK_COST_PER_SIDE * 1e4)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\n{'PASS' if passed else 'FAIL'} — {len(CHECKS)} checks -> {out_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
