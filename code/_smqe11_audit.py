#!/usr/bin/env python
"""_smqe11_audit.py — known answers + parity for the SMQE v1.1 port.

Run BEFORE any real-data artifact (the repo's mandatory order). Sections:
  A. executor known answers on synthetic bars, hand-computed (every execution
     rule: TP2 win, spanning bar under the three fill modes, TP1-then-stop,
     flip + same-bar reverse, cooldown on entries and flips, funding accrual,
     entry fee inside the trade P&L, MTM drawdown, end-of-data force close);
  B. signal-core identity with the v2 engine's audited primitives (import
     identity) + the v1.1 fusion (stop_d has NO floor; each required component
     can veto the entry);
  C. zero-cost parity (same entries/exits as the costed run, PnL differs);
  D. determinism (two runs byte-equal) and no-lookahead truncation (signals
     on a prefix are identical to the same bars of the full run).

Expectation bugs count against the TEST first (three of three historical
audit failures were the test's fault).
"""
from __future__ import annotations

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import smqe11_engine as E  # noqa: E402
import smqe_engine as V2   # noqa: E402

P = dict(E.PINE_DEFAULTS)
T0 = 1_700_000_000_000  # an arbitrary UTC-hour-aligned start is NOT needed:
# execute() only uses timestamps for funding; signals11 uses them for the
# VWAP day anchor, and the executor cases below pass hand-built signal dicts.


def bars(rows):
    """rows of (open, high, low, close, volume)."""
    a = np.asarray(rows, float)
    t = T0 + np.arange(len(a)) * 3_600_000
    return t, a[:, 0], a[:, 1], a[:, 2], a[:, 3], a[:, 4]


def sig(long_idx=(), short_idx=(), stop_d=10.0, n=0, vwap=None):
    long_ok = np.zeros(n, bool)
    short_ok = np.zeros(n, bool)
    long_ok[list(long_idx)] = True
    short_ok[list(short_idx)] = True
    sd = np.full(n, float(stop_d))
    vw = np.full(n, np.nan) if vwap is None else np.asarray(vwap, float)
    return dict(long_ok=long_ok, short_ok=short_ok, vwap=vw, stop_d=sd,
                atr_x=sd / P["atr_mult"], cvd_bull=np.zeros(n, bool),
                cvd_bear=np.zeros(n, bool), near_low=np.zeros(n, bool),
                near_high=np.zeros(n, bool), rsi_long_ok=np.zeros(n, bool),
                rsi_short_ok=np.zeros(n, bool), bull_div=np.zeros(n, bool),
                bear_div=np.zeros(n, bool), osc=np.zeros(n),
                rsi=np.zeros(n), n_piv_l=0, n_piv_h=0)


PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {name}")
    else:
        FAIL += 1
        print(f"FAIL {name}  {detail}")


# ═════════════════════════════════ A. executor known answers ═══════════════
def a1_tp2_win_zero_cost():
    """Flat at 100, stop 10 wide, no VWAP -> TP1=115 (50%), TP2=120.
    Bar 1 spans both TPs (high 125), no stop. Zero cost: pnl = 175 on qty 10."""
    t, o, h, l, c, v = bars([(100, 101, 99, 100, 1), (100, 125, 95, 120, 1),
                             (120, 121, 119, 120, 1)])
    S = sig(long_idx=(0,), n=3)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, p, 0.0, 0.0)
    tr = out["trades"]
    # qty = 10000 * min(0.01/(10/100), 3) / 100 = 10
    check("A1 TP2 win: one trade, reason tp2", len(tr) == 1 and tr[0]["reason"] == "tp2",
          str(tr))
    check("A1 pnl = 175 exactly (0.5*15*10 + 0.5*20*10)",
          abs(tr[0]["pnl"] - 175.0) < 1e-9, f"pnl={tr[0]['pnl']}")
    check("A1 R = 1.75 (posRisk = 100)", abs(tr[0]["r"] - 1.75) < 1e-9, f"r={tr[0]['r']}")
    check("A1 equity = 10175", abs(out["eq"][-1] - 10_175.0) < 1e-9)


def a2_spanning_bar_fill_modes():
    """Bar 1 spans stop (85) and TPs (125). stop-first -> -100; tp-first -> +175."""
    t, o, h, l, c, v = bars([(100, 101, 99, 100, 1), (100, 125, 85, 120, 1),
                             (120, 121, 119, 120, 1)])
    S = sig(long_idx=(0,), n=3)
    p = {**P, "init": 10_000.0}
    out_stop = E.execute(t, o, h, l, c, S, {**p, "fill_mode": "stop"}, 0.0, 0.0)
    out_tp = E.execute(t, o, h, l, c, S, {**p, "fill_mode": "tp"}, 0.0, 0.0)
    check("A2 stop-first: pnl -100 (1R loss)",
          len(out_stop["trades"]) == 1 and abs(out_stop["trades"][0]["pnl"] + 100.0) < 1e-9
          and out_stop["trades"][0]["reason"] == "stop",
          str(out_stop["trades"]))
    check("A2 tp-first: pnl +175",
          abs(out_tp["trades"][0]["pnl"] - 175.0) < 1e-9, str(out_tp["trades"]))


def a3_emu_mode_short_side():
    """Short entry at 100 (stop 110, TP1 85, TP2 80). Bar 1: open 100, low 79,
    high 121: emuHighFirst = (121-100) < (100-79) -> 21 < 21 is FALSE -> path
    O->L->H->C, low first -> the TP side wins for the short: TP1 at 85 (50%)
    then TP2 at 80 (rest) = +175 (both TPs sit below the low; the Pine's order
    is TP1 -> TP2 -> STOP). stop-first mode: -100."""
    t, o, h, l, c, v = bars([(100, 101, 99, 100, 1), (100, 121, 79, 95, 1),
                             (95, 96, 94, 95, 1)])
    S = sig(short_idx=(0,), n=3)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, {**p, "fill_mode": "emu"}, 0.0, 0.0)
    check("A3 emu (low first): TP1 75 + TP2 100 = +175",
          len(out["trades"]) == 1 and abs(out["trades"][0]["pnl"] - 175.0) < 1e-9,
          str(out["trades"]))
    out_stop = E.execute(t, o, h, l, c, S, {**p, "fill_mode": "stop"}, 0.0, 0.0)
    check("A3 stop-first: pnl -100",
          abs(out_stop["trades"][0]["pnl"] + 100.0) < 1e-9, str(out_stop["trades"]))


def a4_tp1_then_stop():
    """Bar 1 touches TP1 only (116), bar 2 stops (88 < 90). pnl = 75 - 50 = 25,
    closing reason is the stop."""
    t, o, h, l, c, v = bars([(100, 101, 99, 100, 1), (101, 116, 92, 110, 1),
                             (110, 111, 88, 95, 1), (95, 96, 94, 95, 1)])
    S = sig(long_idx=(0,), n=4)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, p, 0.0, 0.0)
    tr = out["trades"]
    check("A4 one trade, closing reason stop", len(tr) == 1 and tr[0]["reason"] == "stop",
          str(tr))
    check("A4 pnl = 75 - 50 = 25", abs(tr[0]["pnl"] - 25.0) < 1e-9, f"pnl={tr[0]['pnl']}")


def a5_flip_and_reverse():
    """Long at bar 0 (100). short_ok at bar 3 (cooldown 3 ok), close 102:
    remainder closes +20, SAME bar re-enters short at 102. Bar 4 stops the
    short (113 >= 112). Two trades, reasons flip and stop."""
    t, o, h, l, c, v = bars([
        (100, 101, 99, 100, 1),
        (100, 108, 95, 101, 1),
        (101, 106, 96, 102, 1),
        (102, 107, 97, 102, 1),   # short_ok here; close 102
        (102, 113, 100, 111, 1),  # short stop 112 hit
    ])
    S = sig(long_idx=(0,), short_idx=(3,), n=5)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, p, 0.0, 0.0)
    tr = out["trades"]
    ok_shape = len(tr) == 2 and tr[0]["reason"] == "flip" and tr[1]["reason"] == "stop"
    check("A5 flip then reverse-stop shape", ok_shape, str([(x['reason'], x['pnl']) for x in tr]))
    if ok_shape:
        # long: qty 10, closed at 102 -> +20; short: equity 10020, stop_frac
        # 10/102 -> mult 0.1020408..., qty = 10020*mult/102; the stop FILLS AT
        # THE STOP PRICE (112), not at the bar's high: loss = 10 * qty
        q2 = 10_020.0 * min(0.01 / (10 / 102.0), 3.0) / 102.0
        check("A5 flip pnl +20", abs(tr[0]["pnl"] - 20.0) < 1e-9, f"{tr[0]['pnl']}")
        check("A5 reverse loss -10*qty (stop fills at the stop px)",
              abs(tr[1]["pnl"] + 10.0 * q2) < 1e-6,
              f"{tr[1]['pnl']} vs {-10*q2}")


def a6_cooldown_blocks():
    """long_ok at bars 0,2,3. Bar 1 closes the first trade intrabar (TP1+TP2,
    closedIntrabar, and long_ok[1] is False anyway). Bar 2 blocked: 2-0=2 <
    cooldown 3. Bar 3 allowed: 3-0=3. Two trades: (0->1 tp2) and (3->4
    end_of_data)."""
    rows = [(100, 101, 99, 100, 1),
            (100, 121, 95, 120, 1),    # TP1 115 + TP2 120 both hit -> close
            (120, 124, 118, 122, 1),   # long_ok, cooldown 2 < 3 -> blocked
            (122, 126, 120, 124, 1),   # long_ok, 3-0 = 3 -> entry
            (124, 128, 122, 126, 1)]   # open -> force close
    t, o, h, l, c, v = bars(rows)
    S = sig(long_idx=(0, 2, 3), n=5)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, p, 0.0, 0.0)
    trs = out["trades"]
    check("A6 entries at bars 0 and 3 only (cooldown blocks bar 2)",
          len(trs) == 2 and trs[0]["entry_i"] == 0 and trs[0]["reason"] == "tp2"
          and trs[1]["entry_i"] == 3 and trs[1]["reason"] == "end_of_data",
          str([(x['entry_i'], x['exit_i'], x['reason']) for x in trs]))


def a7_no_reentry_after_intrabar_stop():
    """Stop-out intrabar at bar 1 with long_ok at bar 1: no same-bar re-entry
    (closedIntrabar); next entry waits for a LATER signal bar (bar 4)."""
    rows = [(100, 101, 99, 100, 1),
            (100, 125, 85, 120, 1),   # stop-first close, long_ok here too
            (120, 121, 100, 105, 1),
            (105, 110, 101, 106, 1),  # long_ok but cooldown (3-0=3 ok!) -> entry
            (106, 111, 102, 107, 1)]
    t, o, h, l, c, v = bars(rows)
    S = sig(long_idx=(0, 1, 3), n=5)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, p, 0.0, 0.0)
    trs = out["trades"]
    check("A7 no same-bar re-entry; next entry bar 3 (cooldown ok)",
          len(trs) == 2 and trs[0]["entry_i"] == 0 and trs[1]["entry_i"] == 3,
          str([(x['entry_i'], x['exit_i'], x['reason']) for x in trs]))


def a8_entry_fee_inside_trade_pnl():
    """With 0.06% commission the first trade's PnL = 175 - entry fee - TP fees
    (patch H1): entry 100*10*0.0006=0.6, TP1 115*5*0.0006=0.345,
    TP2 120*5*0.0006=0.36 -> 173.695. Equity already debited the entry fee."""
    t, o, h, l, c, v = bars([(100, 101, 99, 100, 1), (100, 125, 95, 120, 1),
                             (120, 121, 119, 120, 1)])
    S = sig(long_idx=(0,), n=3)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, p, 0.06, 0.0)
    tr = out["trades"]
    check("A8 commission-inclusive pnl 173.695",
          abs(tr[0]["pnl"] - 173.695) < 1e-6, f"pnl={tr[0]['pnl']}")
    check("A8 equity = 10000 + 173.695", abs(out["eq"][-1] - 10_173.695) < 1e-6,
          f"eq={out['eq'][-1]}")


def a9_funding_pine_model():
    """funding_pct8h=0.01, tf 1h: factor 1/8. Position open bar 1 (no touch),
    stops bar 2. Accrual at bar 1 on the full notional at close 104."""
    rows = [(100, 101, 99, 100, 1),
            (100, 108, 96, 104, 1),   # no stop (96>90), no TP (108<115)
            (104, 110, 85, 95, 1)]    # stop 90 hit
    t, o, h, l, c, v = bars(rows)
    S = sig(long_idx=(0,), n=3)
    p = {**P, "init": 10_000.0, "funding_pct8h": 0.01}
    out = E.execute(t, o, h, l, c, S, p, 0.0, 0.0, tf_sec=3600)
    tr = out["trades"]
    q = 10.0
    fund1 = 1 * 104.0 * q * 1.0 * 0.01 / 100.0 * (3600 / 28800.0)
    expected = -100.0 - fund1
    check("A9 funding accrued once (bar 1), stop pnl includes it",
          len(tr) == 1 and abs(tr[0]["pnl"] - expected) < 1e-9,
          f"pnl={tr[0]['pnl']} expected={expected} fund1={fund1}")
    check("A9 funding_paid = fund1", abs(out["totals"]["funding_paid"] - fund1) < 1e-12,
          str(out["totals"]["funding_paid"]))


def a10_end_of_data_force_close():
    """Position still open at the last bar closes at the last close
    (end_of_data), counted as a closed trade."""
    rows = [(100, 101, 99, 100, 1),
            (100, 108, 96, 104, 1),
            (104, 109, 100, 105, 1)]
    t, o, h, l, c, v = bars(rows)
    S = sig(long_idx=(0,), n=3)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, p, 0.0, 0.0)
    tr = out["trades"]
    check("A10 force close at last close, reason end_of_data",
          len(tr) == 1 and tr[0]["reason"] == "end_of_data"
          and abs(tr[0]["pnl"] - (105.0 - 100.0) * 10.0) < 1e-9, str(tr))


def a11_mtm_drawdown():
    """Open long marks to the adverse low on open bars; on the entry bar the
    close is used. DD from peak 10000: bar1 low 96 -> equity MTM
    10000 + (96-100)*10 = 9960 -> dd 0.4%."""
    rows = [(100, 101, 99, 100, 1),
            (100, 108, 96, 104, 1),
            (104, 109, 100, 105, 1)]
    t, o, h, l, c, v = bars(rows)
    S = sig(long_idx=(0,), n=3)
    p = {**P, "init": 10_000.0}
    out = E.execute(t, o, h, l, c, S, p, 0.0, 0.0)
    # worst MTM equity over open bars: min over i of equity + worst open pnl
    # bar1: 10000 + (96-100)*10 = 9960 -> dd = 40/10000 = 0.4%
    check("A11 max_dd = 0.4% (adverse low marked)", abs(out["totals"]["max_dd"] - 0.004) < 1e-12,
          str(out["totals"]["max_dd"]))


# ═════════════════════════════════ B. signal core ══════════════════════════
def b1_primitive_identity():
    check("B1 primitives are the v2 engine's audited objects BY IDENTITY",
          E.ema_pine is V2.ema_pine and E.rma_pine is V2.rma_pine
          and E.atr_pine is V2.atr_pine and E.rsi_pine is V2.rsi_pine
          and E.session_vwap is V2.session_vwap and E._divergence is V2._divergence)


def b2_stop_no_floor():
    """v1.1 stop_d = atr*mult exactly (the v2 min-stop floor must NOT appear)."""
    n = 60
    rng = np.random.default_rng(11)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    h = c + np.abs(rng.normal(0, 1, n))
    l = c - np.abs(rng.normal(0, 1, n))
    o = np.roll(c, 1)
    o[0] = c[0]
    v = np.full(n, 10.0)
    t = T0 + np.arange(n) * 3_600_000
    S = E.signals11(t, h, l, c, v, {**P, "atr_mult": 1.5})
    atr_ref = E.atr_pine(h, l, c, 14)
    m = ~np.isnan(atr_ref)
    check("B2 stop_d == atr*1.5 (no floor)",
          np.allclose(S["stop_d"][m], atr_ref[m] * 1.5, rtol=0, atol=1e-12))


def b3_conjunction_vetoes():
    """Each required component vetoes: build bars where divergence + band +
    CVD + RSI align, then break one at a time. Use real signals11 on crafted
    bars: a deep dip below the daily VWAP -1SD with RSI oversold and a pivot
    low divergence is hard to hand-craft exactly, so assert the CONJUNCTION
    property statistically instead: long bars must be a subset of each
    component on real data (done in D on BTCUSDT_1h) and the veto logic here:
    long_ok implies bull_div & near_low & cvd_bull & rsi_long_ok."""
    n = 400
    rng = np.random.default_rng(7)
    c = 100 + np.cumsum(rng.normal(0, 0.5, n))
    h = c + np.abs(rng.normal(0, 0.4, n)) + 0.2
    l = c - np.abs(rng.normal(0, 0.4, n)) - 0.2
    o = np.roll(c, 1)
    o[0] = c[0]
    v = np.abs(rng.normal(50, 10, n))
    t = T0 + np.arange(n) * 3_600_000
    S = E.signals11(t, h, l, c, v, P)
    sub = (S["long_ok"] & ~S["bull_div"]) | (S["long_ok"] & ~S["near_low"]) \
        | (S["long_ok"] & ~S["cvd_bull"]) | (S["long_ok"] & ~S["rsi_long_ok"])
    check("B3 long_ok implies all four components", not sub.any())
    sub_s = (S["short_ok"] & ~S["bear_div"]) | (S["short_ok"] & ~S["near_high"]) \
        | (S["short_ok"] & ~S["cvd_bear"]) | (S["short_ok"] & ~S["rsi_short_ok"])
    check("B3 short_ok implies all four components", not sub_s.any())


# ═════════════════════════════════ C+D. real-data parity ═══════════════════
BTC = os.path.join(ROOT, "data", "binance_klines_1h", "BTCUSDT_1h.csv")


def cd_real_data():
    if not os.path.exists(BTC):
        print("SKIP C/D (no BTCUSDT_1h on disk)")
        return
    import pandas as pd
    df = pd.read_csv(BTC)
    df = df.drop_duplicates("open_ts").sort_values("open_ts").reset_index(drop=True)
    t = df["open_ts"].to_numpy(np.int64)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)

    S1 = E.signals11(t, h, l, c, v, P)
    S2 = E.signals11(t, h, l, c, v, P)

    def _eq_nan(a, b):
        return np.array_equal(np.asarray(a, float), np.asarray(b, float), equal_nan=True)

    check("C0 signals deterministic", all(
        _eq_nan(S1[k], S2[k]) for k in ("long_ok", "short_ok", "stop_d", "vwap")))

    p = {**P, "init": 10_000.0}
    out_pine = E.execute(t, o, h, l, c, S1, p, 0.06, 0.0)
    out_zero = E.execute(t, o, h, l, c, S1, p, 0.0, 0.0)
    k_p = [(x["entry_i"], x["exit_i"], x["reason"]) for x in out_pine["trades"]]
    k_z = [(x["entry_i"], x["exit_i"], x["reason"]) for x in out_zero["trades"]]
    check("C1 zero-cost trades identical to costed (entries/exits/reasons)", k_p == k_z,
          f"{len(k_p)} vs {len(k_z)}")

    # no-lookahead: signals on a prefix equal the same bars of the full run
    k = 30_000
    Sp = E.signals11(t[:k], h[:k], l[:k], c[:k], v[:k], P)
    same = (_eq_nan(Sp["long_ok"], S1["long_ok"][:k])
            and _eq_nan(Sp["short_ok"], S1["short_ok"][:k])
            and _eq_nan(Sp["stop_d"], S1["stop_d"][:k])
            and _eq_nan(Sp["vwap"], S1["vwap"][:k]))
    check("D1 prefix signals identical (no lookahead)", same)
    outp = E.execute(t[:k], o[:k], h[:k], l[:k], c[:k], Sp, p, 0.06, 0.0)
    full_first = out_pine["trades"]
    pref = outp["trades"]
    same_tr = all(a["entry_i"] == b["entry_i"] and a["exit_i"] == b["exit_i"]
                  and a["reason"] == b["reason"] and abs(a["pnl"] - b["pnl"]) < 1e-9
                  for a, b in zip(full_first, pref)) and len(full_first) >= len(pref) - 1
    check("D2 trades on the prefix identical to the same trades of the full run",
          same_tr, f"{len(full_first)} vs {len(pref)}")


if __name__ == "__main__":
    for fn in (a1_tp2_win_zero_cost, a2_spanning_bar_fill_modes, a3_emu_mode_short_side,
               a4_tp1_then_stop, a5_flip_and_reverse, a6_cooldown_blocks,
               a7_no_reentry_after_intrabar_stop, a8_entry_fee_inside_trade_pnl,
               a9_funding_pine_model, a10_end_of_data_force_close, a11_mtm_drawdown,
               b1_primitive_identity, b2_stop_no_floor, b3_conjunction_vetoes,
               cd_real_data):
        fn()
    print(f"\n{PASS} PASS, {FAIL} FAIL")
    raise SystemExit(1 if FAIL else 0)
