#!/usr/bin/env python
r"""
_xsml_engine_audit.py — known-answer audit of the `xsml` engine's LEDGER.

WHY THIS FILE EXISTS
--------------------
The engine's version 1 had a SIGN bug on the short leg: it multiplied the
already-signed quantity by `side` a second time, so every short was booked
as a mirror-long (its fee was CREDITED instead of charged) and the funding
was charged on the wrong side. The repo's own accounting invariant caught it
(residual 1689.65 USDT = four commissions for each of the 507 short
trades), but the invariant was NOT asserted inside the artifact, so the
book ran and published a plausible-looking number.

The WAVE_1 port already paid this bill once (AGENTS.md: "shipped long-only
tests and missed a short-side fee bug for a whole campaign"). This audit is
therefore written to cover BOTH directions for every execution rule, and it
is run BEFORE any market run.

THE CHECKS (all on SYNTHETIC bars, no market data, no randomness)
------------------------------------------------------------------
A. LONG, clean exit at the target: the cash, the fee and the PnL are
   hand-computed and must match to the last cent.
B. SHORT, clean exit at the target: the same, mirrored. A short SELLS at the
   open (cash IN) and BUYS BACK at the exit (cash OUT), and it PAYS the fee
   on both fills. This is the case version 1 got wrong.
C. STOP-FIRST tie: a bar that touches both the stop and the target exits at
   the STOP, in both directions.
D. GAP through the stop: a bar that opens beyond the stop fills AT THE OPEN
   (a worse price), in both directions.
E. FUNDING sign: a long PAYS a positive funding rate and a short RECEIVES
   it. The sign is checked on the cash and on the reported metric.
F. ACCOUNTING INVARIANT: eq[-1] - INIT == sum(pnl) - funding_paid, on every
   synthetic case.
G. FULL TURNOVER: at a rebalance, every open leg is closed and the new book
   is opened at the next open; a leg that stays selected is closed and
   reopened too, with its stop frozen at the CURRENT signal bar.
H. ENTRY BAR's range is checked: a position opened at a bar's open can be
   stopped out on that same bar's range.

Usage:  python code/_xsml_engine_audit.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

_spec = importlib.util.spec_from_file_location(
    "xsml_engine", os.path.join(HERE, "xsml_engine.py"))
xe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(xe)

CHECKS = []
FEE = 0.0005            # 5 bps per side
SLIP = 0.00005          # 0.5 bps per side
INIT = 10_000.0
HOUR = 3_600_000
DAY = 86_400_000


def check(name, ok, detail=""):
    CHECKS.append({"name": name, "pass": bool(ok), "detail": str(detail)[:400]})
    print(("  PASS  " if ok else "  FAIL  ") + name, flush=True)
    if not ok:
        print("        " + str(detail)[:400], flush=True)
    return bool(ok)


def sym(name, bars, preds, atr_bps=100.0):
    """bars: list of (open, high, low, close). preds: one per bar."""
    ms = np.arange(len(bars), dtype=np.int64) * HOUR + 1_700_000_000_000
    o = np.array([b[0] for b in bars], float)
    h = np.array([b[1] for b in bars], float)
    lo = np.array([b[2] for b in bars], float)
    c = np.array([b[3] for b in bars], float)
    return dict(sym=name, ms=ms, open=o, high=h, low=lo, close=c,
                volume=np.ones(len(bars)), atr_bps=np.full(len(bars), atr_bps),
                pred=np.array(preds, float))


def run(symbols, **kw):
    """run_book with the harness-level knobs the audit needs."""
    p = dict(kw)
    p.setdefault("fee", FEE)
    p.setdefault("slip", SLIP)
    p.setdefault("init", INIT)
    p.setdefault("top_k", 1)
    p.setdefault("min_names", 1)
    p.setdefault("charge_funding", False)
    p.setdefault("rebalance_bars", 24)
    return xe.run_book(symbols, {}, **p)


# ── the rebalance fires on the bar whose hour is 00:00 UTC ───────────────
def midnight_bars():
    """A timestamp base whose FIRST bar is at 00:00 UTC, so bar 0 rebalances."""
    # 2024-01-01T00:00:00Z = 1704067200000 ms
    return 1_704_067_200_000


# ═══════════════════════════════════════════════════════════════════════
# A + B: a clean exit, LONG and SHORT, hand-computed
# ═══════════════════════════════════════════════════════════════════════
def case_clean(side):
    """One leg, entered at bar 1's open, exits at its target on bar 3.

    Geometry (bar 1 = the fill bar, open 100):
      long : fill = 100*(1+slip) = 100.005 ; target = fill*(1+100bps)
      short: fill = 100*(1-slip) = 99.995  ; target = fill*(1-100bps)
    ATR is 100 bps, stop_mult = 1 and target_mult = 1, so the target is
    100 bps away and the stop is 100 bps away on the other side.
    """
    base = midnight_bars()
    ms = np.array([base, base + HOUR, base + 2 * HOUR, base + 3 * HOUR],
                  dtype=np.int64)
    # bar 0: the signal bar (rebalance). bar 1: the fill bar (open).
    # bar 2: nothing. bar 3: the target is reached.
    if side == 1:
        bars = [(100.0, 100.2, 99.9, 100.0),
                (100.0, 100.2, 99.9, 100.0),
                (100.0, 100.2, 99.9, 100.0),
                (100.0, 101.5, 99.9, 101.4)]
    else:
        bars = [(100.0, 100.1, 99.8, 100.0),
                (100.0, 100.1, 99.8, 100.0),
                (100.0, 100.1, 99.8, 100.0),
                (100.0, 100.1, 98.5, 98.6)]
    s = dict(sym="TST", ms=ms, open=np.array([b[0] for b in bars], float),
             high=np.array([b[1] for b in bars], float),
             low=np.array([b[2] for b in bars], float),
             close=np.array([b[3] for b in bars], float),
             volume=np.ones(4), atr_bps=np.full(4, 100.0),
             pred=np.array([1.0, 1.0, 1.0, 1.0], float))
    res = run([s], top_k=1, min_names=1, long_only=(side == 1),
               short_only=(side == -1), stop_mult=1.0, target_mult=1.0)
    trades = res["trades"]
    if len(trades) != 1:
        return None, None, trades, res
    t = trades[0]
    # ── hand computation ──
    notional = INIT * 0.5 / 1
    fill_in = 100.0 * (1 + SLIP * side)
    qty = side * notional / fill_in
    fee_in = notional * FEE
    # the ledger: entry cash -= qty*fill + fee (a short RECEIVES the proceeds
    # and PAYS the fee), exit cash += qty*fill - fee
    cash = INIT - qty * fill_in - fee_in
    target = fill_in * (1 + side * 100 / 1e4)
    fill_out = target * (1 - SLIP * side)
    fee_out = abs(qty) * fill_out * FEE
    cash += qty * fill_out - fee_out
    pnl = qty * (fill_out - fill_in) - fee_in - fee_out
    expect_cash = cash
    expect_pnl = pnl
    return expect_cash, expect_pnl, trades, res


def audit_clean():
    for side, name in ((1, "LONG"), (-1, "SHORT")):
        exp_cash, exp_pnl, trades, res = case_clean(side)
        if exp_cash is None:
            check(f"A/B {name}: exactly one trade", False,
                  f"{len(trades)} trades")
            continue
        t = trades[0]
        ok_fill = abs(t["entry_px"] - (100.0 * (1 + SLIP * side))) < 1e-9
        ok_pnl = abs(t["pnl"] - exp_pnl) < 1e-6
        ok_cash = abs(res["final_equity"] - exp_cash) < 1e-6
        ok_side = t["side"] == side
        ok_why = t["why"] == "target"
        check(f"A/B {name}: fill price with slippage against the book",
              ok_fill, f"got {t['entry_px']}")
        check(f"A/B {name}: trade PnL matches the hand computation",
              ok_pnl, f"got {t['pnl']:.6f} expected {exp_pnl:.6f}")
        check(f"A/B {name}: final cash matches the hand computation",
              ok_cash, f"got {res['final_equity']:.6f} expected {exp_cash:.6f}")
        check(f"A/B {name}: the side on the trade is the side traded",
              ok_side, f"got {t['side']}")
        check(f"A/B {name}: the exit is the target", ok_why, t["why"])
        # the direction test that version 1 failed: a short must PAY fees,
        # and a short whose price FALLS must make money.
        if side == -1:
            check("B SHORT: a falling price makes the short PROFIT",
                  t["pnl"] > 0, f"pnl {t['pnl']:.6f}")
            check("B SHORT: the fee is CHARGED, not credited",
                  res["fees_paid"] > 0, f"fees {res['fees_paid']}")
        else:
            check("A LONG: a rising price makes the long PROFIT",
                  t["pnl"] > 0, f"pnl {t['pnl']:.6f}")
            check("A LONG: the fee is CHARGED, not credited",
                  res["fees_paid"] > 0, f"fees {res['fees_paid']}")


# ═══════════════════════════════════════════════════════════════════════
# C: STOP-FIRST tie, in both directions
# ═══════════════════════════════════════════════════════════════════════
def case_stop_first(side):
    base = midnight_bars()
    ms = np.array([base, base + HOUR, base + 2 * HOUR], dtype=np.int64)
    if side == 1:
        # bar 2 touches BOTH the stop (below) and the target (above)
        bars = [(100.0, 100.1, 99.9, 100.0),
                (100.0, 100.1, 99.9, 100.0),
                (100.0, 101.5, 98.5, 100.0)]
    else:
        bars = [(100.0, 100.1, 99.9, 100.0),
                (100.0, 100.1, 99.9, 100.0),
                (100.0, 101.5, 98.5, 100.0)]
    s = dict(sym="TST", ms=ms, open=np.array([b[0] for b in bars], float),
             high=np.array([b[1] for b in bars], float),
             low=np.array([b[2] for b in bars], float),
             close=np.array([b[3] for b in bars], float),
             volume=np.ones(3), atr_bps=np.full(3, 100.0),
             pred=np.array([1.0, 1.0, 1.0], float))
    res = run([s], top_k=1, min_names=1, long_only=(side == 1),
               short_only=(side == -1), stop_mult=1.0, target_mult=1.0)
    return res


def audit_stop_first():
    for side, name in ((1, "LONG"), (-1, "SHORT")):
        res = case_stop_first(side)
        trades = res["trades"]
        ok = len(trades) == 1 and trades[0]["why"] == "stop"
        check(f"C {name}: a bar touching stop AND target exits at the STOP",
              ok, [t["why"] for t in trades])
        if trades:
            fill_in = 100.0 * (1 + SLIP * side)
            stop = fill_in - side * (fill_in * 100 / 1e4)
            exp_fill = stop * (1 - SLIP * side)
            check(f"C {name}: the stop fill price is the stop level",
                  abs(trades[0]["exit_px"] - exp_fill) < 1e-9,
                  f"got {trades[0]['exit_px']} expected {exp_fill}")


# ═══════════════════════════════════════════════════════════════════════
# D: GAP through the stop -> the fill is AT THE OPEN
# ═══════════════════════════════════════════════════════════════════════
def case_gap(side):
    base = midnight_bars()
    ms = np.array([base, base + HOUR, base + 2 * HOUR], dtype=np.int64)
    if side == 1:
        # bar 2 opens BELOW the stop (the stop is 100 bps below 100.005)
        bars = [(100.0, 100.1, 99.9, 100.0),
                (100.0, 100.1, 99.9, 100.0),
                (98.0, 98.2, 97.0, 97.5)]
    else:
        # bar 2 opens ABOVE the stop (the stop is 100 bps above 99.995)
        bars = [(100.0, 100.1, 99.9, 100.0),
                (100.0, 100.1, 99.9, 100.0),
                (102.0, 103.0, 101.5, 102.5)]
    s = dict(sym="TST", ms=ms, open=np.array([b[0] for b in bars], float),
             high=np.array([b[1] for b in bars], float),
             low=np.array([b[2] for b in bars], float),
             close=np.array([b[3] for b in bars], float),
             volume=np.ones(3), atr_bps=np.full(3, 100.0),
             pred=np.array([1.0, 1.0, 1.0], float))
    res = run([s], top_k=1, min_names=1, long_only=(side == 1),
               short_only=(side == -1), stop_mult=1.0, target_mult=1.0)
    return res


def audit_gap():
    for side, name in ((1, "LONG"), (-1, "SHORT")):
        res = case_gap(side)
        trades = res["trades"]
        if len(trades) != 1:
            check(f"D {name}: gap through the stop produces one trade", False,
                  f"{len(trades)} trades")
            continue
        t = trades[0]
        gap_open = 98.0 if side == 1 else 102.0
        exp_fill = gap_open * (1 - SLIP * side)
        check(f"D {name}: the gap-through stop fills AT THE OPEN",
              abs(t["exit_px"] - exp_fill) < 1e-9,
              f"got {t['exit_px']} expected {exp_fill}")
        check(f"D {name}: the exit is the stop", t["why"] == "stop", t["why"])


# ═══════════════════════════════════════════════════════════════════════
# E: FUNDING sign — a long PAYS a positive rate, a short RECEIVES it
# ═══════════════════════════════════════════════════════════════════════
def case_funding(side):
    base = midnight_bars()
    ms = np.array([base, base + HOUR, base + 2 * HOUR], dtype=np.int64)
    bars = [(100.0, 100.1, 99.9, 100.0),
            (100.0, 100.1, 99.9, 100.0),
            (100.0, 100.1, 99.9, 100.0)]
    s = dict(sym="TST", ms=ms, open=np.array([b[0] for b in bars], float),
             high=np.array([b[1] for b in bars], float),
             low=np.array([b[2] for b in bars], float),
             close=np.array([b[3] for b in bars], float),
             volume=np.ones(3), atr_bps=np.full(3, 100.0),
             pred=np.array([1.0, 1.0, 1.0], float))
    # a funding event on the LAST bar, rate = +10 bps (the book PAYS it)
    rate = np.zeros(3)
    ev = np.zeros(3, bool)
    rate[2] = 0.001
    ev[2] = True
    orig = xe.funding_events
    xe.funding_events = lambda sym_name, bar_ms: (rate, ev, 1)
    try:
        res = run([s], top_k=1, min_names=1, long_only=(side == 1),
                   short_only=(side == -1), charge_funding=True,
                   stop_mult=1.0, target_mult=1.0)
    finally:
        xe.funding_events = orig
    return res


def audit_funding():
    for side, name, sign in ((1, "LONG", +1), (-1, "SHORT", -1)):
        res = case_funding(side)
        paid = res["funding_paid"]
        # qty * mark * rate with a signed qty: a long pays, a short receives
        ok = sign * paid > 0
        check(f"E {name}: a positive funding rate has the RIGHT sign "
              f"({'pays' if side == 1 else 'receives'})",
              ok, f"funding_paid {paid:.6f}")


# ═══════════════════════════════════════════════════════════════════════
# F: the ACCOUNTING INVARIANT on every synthetic case
# ═══════════════════════════════════════════════════════════════════════
def audit_invariant():
    worst = 0.0
    worst_case = ""
    cases = [("clean long", case_clean(1)), ("clean short", case_clean(-1)),
             ("stop-first long", (None, None, None, case_stop_first(1))),
             ("stop-first short", (None, None, None, case_stop_first(-1))),
             ("gap long", (None, None, None, case_gap(1))),
             ("gap short", (None, None, None, case_gap(-1)))]
    for label, (_, _, trades, res) in cases:
        if trades is None:
            continue
        pnls = np.array([t["pnl"] for t in res["trades"]], float)
        resid = ((res["final_equity"] - INIT)
                 - (pnls.sum() - res["funding_paid"]))
        if abs(resid) > worst:
            worst = abs(resid)
            worst_case = label
    check("F: eq[-1]-INIT == sum(pnl) - funding on every synthetic case",
          worst < 1e-6, f"worst residual {worst:.3e} in {worst_case}")


# ═══════════════════════════════════════════════════════════════════════
# G: FULL TURNOVER at the rebalance
# ═══════════════════════════════════════════════════════════════════════
def audit_turnover():
    """Both turnover readings, both declared in
    results/xsml_turnover_pre_registration.md.

    "full": every open leg is closed and the new book is opened at the next
            open (the portfolio IS top-3/bottom-3 at every rebalance).
    "keep": only the legs that LEAVE the ranking are closed; a leg that stays
            selected keeps its position, its stop and its size.
    """
    base = midnight_bars()
    n = 26
    ms = np.array([base + i * HOUR for i in range(n)], dtype=np.int64)
    bars = [(100.0, 100.1, 99.9, 100.0)] * n
    s = dict(sym="TST", ms=ms, open=np.array([b[0] for b in bars], float),
             high=np.array([b[1] for b in bars], float),
             low=np.array([b[2] for b in bars], float),
             close=np.array([b[3] for b in bars], float),
             volume=np.ones(n), atr_bps=np.full(n, 100.0),
             pred=np.ones(n, float))

    res_full = run([s], top_k=1, min_names=1, long_only=True, stop_mult=1.0,
                    target_mult=1.0, turnover="full")
    rebal_full = [t for t in res_full["trades"] if t["why"] == "rebalance"]
    check("G: 'full' turnover closes and reopens the selected leg at the "
          "rebalance", len(rebal_full) >= 1,
          f"{len(res_full['trades'])} trades, {len(rebal_full)} by rebalance")

    res_keep = run([s], top_k=1, min_names=1, long_only=True, stop_mult=1.0,
                    target_mult=1.0, turnover="keep")
    rebal_keep = [t for t in res_keep["trades"] if t["why"] == "rebalance"]
    check("G: 'keep' turnover does NOT close a leg that stays selected",
          len(rebal_keep) == 0,
          f"{len(res_keep['trades'])} trades, {len(rebal_keep)} by rebalance")
    check("G: the 'keep' reading trades less than the 'full' one "
          "(that is the whole cost difference)",
          len(res_keep["trades"]) < len(res_full["trades"]),
          f"keep {len(res_keep['trades'])} vs full {len(res_full['trades'])}")

    try:
        run([s], top_k=1, min_names=1, long_only=True, turnover="nonsense")
        check("G: an unknown turnover mode is refused", False, "no error raised")
    except ValueError:
        check("G: an unknown turnover mode is refused", True)


# ═══════════════════════════════════════════════════════════════════════
# H: the ENTRY bar's range is checked
# ═══════════════════════════════════════════════════════════════════════
def audit_entry_bar():
    base = midnight_bars()
    ms = np.array([base, base + HOUR], dtype=np.int64)
    # the fill bar opens at 100 and its LOW is below the stop: the position
    # must be stopped out on the entry bar itself
    bars = [(100.0, 100.1, 99.9, 100.0),
            (100.0, 100.1, 97.0, 99.0)]
    s = dict(sym="TST", ms=ms, open=np.array([b[0] for b in bars], float),
             high=np.array([b[1] for b in bars], float),
             low=np.array([b[2] for b in bars], float),
             close=np.array([b[3] for b in bars], float),
             volume=np.ones(2), atr_bps=np.full(2, 100.0),
             pred=np.array([1.0, 1.0], float))
    res = run([s], top_k=1, min_names=1, long_only=True, stop_mult=1.0,
              target_mult=1.0)
    trades = res["trades"]
    check("H: the entry bar's own range is checked (a stop on the fill bar "
          "exits immediately)",
          len(trades) == 1 and trades[0]["why"] == "stop",
          [(t["why"], t["exit_ms"]) for t in trades])


def audit_asymmetric():
    """An ASYMMETRIC stop/target (stop 1x ATR, target 3x ATR).

    This is the case that exposed a latent tuple bug in the engine: the
    pending order was removed with (stop, target) swapped, which only
    raised when the two were different. The audit must pin it down.
    """
    base = midnight_bars()
    ms = np.array([base, base + HOUR, base + 2 * HOUR], dtype=np.int64)
    bars = [(100.0, 100.2, 99.9, 100.0),
            (100.0, 100.2, 99.9, 100.0),
            (100.0, 104.0, 99.9, 103.5)]
    s = dict(sym="TST", ms=ms, open=np.array([b[0] for b in bars], float),
             high=np.array([b[1] for b in bars], float),
             low=np.array([b[2] for b in bars], float),
             close=np.array([b[3] for b in bars], float),
             volume=np.ones(3), atr_bps=np.full(3, 100.0),
             pred=np.array([1.0, 1.0, 1.0], float))
    try:
        res = run([s], top_k=1, min_names=1, long_only=True,
                  stop_mult=1.0, target_mult=3.0)
    except Exception as e:                     # a latent engine bug
        check("I: an asymmetric stop/target (1x ATR stop, 3x ATR target) "
              "runs and fills the order", False, f"{type(e).__name__}: {e}")
        return
    trades = res["trades"]
    check("I: an asymmetric stop/target (1x ATR stop, 3x ATR target) "
          "runs and fills the order",
          len(trades) == 1, f"{len(trades)} trades")
    if trades:
        fill_in = 100.0 * (1 + SLIP)
        target = fill_in * (1 + 300 / 1e4)
        exp_fill = target * (1 - SLIP)
        check("I: the asymmetric TARGET level is the one used",
              abs(trades[0]["exit_px"] - exp_fill) < 1e-9,
              f"got {trades[0]['exit_px']} expected {exp_fill}")


def main() -> int:
    out_path = os.path.join(HERE, "_xsml_engine_audit.json")
    print("=== xsml engine audit: known answers, BOTH directions ===")
    audit_clean()
    audit_stop_first()
    audit_gap()
    audit_funding()
    audit_invariant()
    audit_turnover()
    audit_entry_bar()
    audit_asymmetric()
    passed = all(c["pass"] for c in CHECKS)
    out = {"pass": passed, "checks": CHECKS,
           "n_checks": len(CHECKS),
           "engine_version": xe.ENGINE_VERSION}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"\n{'PASS' if passed else 'FAIL'} — {len(CHECKS)} checks -> {out_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
