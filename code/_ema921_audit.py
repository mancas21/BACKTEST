#!/usr/bin/env python
"""Known-answer audit for code/ema921_engine.py (9-21 EMA crossover port).

Every execution rule is tested in BOTH directions on hand-built price paths,
plus the funding sign/timing, the accounting identity, causality and
determinism. The audit must pass BEFORE any real-data run (AGENTS.md: a port
that returns trades is not a validated port; WAVE_1 shipped long-only tests and
missed a short-side fee bug for a whole campaign).

Run:  python code/_ema921_audit.py
Writes results/_ema921_audit.json and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))

import ema921_engine as E  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, detail=""):
    cond = bool(cond)
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    return cond


def mk(closes, step=1.0, freq="1h", start="2026-01-01"):
    """OHLC frame: open = previous close, high/low a fixed spread around it."""
    c = np.asarray(closes, float)
    o = np.r_[c[0], c[:-1]]
    h = np.maximum(o, c) + step
    l = np.minimum(o, c) - step
    idx = pd.date_range(start, periods=len(c), freq=freq, tz="UTC")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)


def P(**kw):
    d = dict(fee_bps=5.0, slip_bps=0.5, risk_pct=1.0, max_leverage=5.0)
    d.update(kw)
    return E.Params(**d)


def pick(tr, side):
    g = tr[tr.side == side]
    return g.iloc[0] if len(g) else None


def ref_ema(x, n):
    a = 2.0 / (n + 1)
    out = np.full(len(x), np.nan)
    out[n - 1] = x[:n].mean()
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out


def ref_rma(x, n):
    out = np.full(len(x), np.nan)
    src = np.asarray(x, float)
    out[n - 1] = src[:n].mean()
    for i in range(n, len(x)):
        out[i] = (out[i - 1] * (n - 1) + src[i]) / n
    return out


def ref_atr(h, l, c, n):
    tr = np.empty(len(c))
    tr[0] = h[0] - l[0]
    for i in range(1, len(c)):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    return ref_rma(tr, n)


# --------------------------------------------------------------------------- #
# 0. Indicators against an independent implementation
# --------------------------------------------------------------------------- #
rng0 = np.random.default_rng(3)
x = 100 + np.cumsum(rng0.standard_normal(300))
check("EMA matches independent reference (seed = SMA of first n)",
      np.allclose(E.ema(x, 9)[8:], ref_ema(x, 9)[8:], rtol=0, atol=1e-12) and
      np.allclose(E.ema(x, 21)[20:], ref_ema(x, 21)[20:], rtol=0, atol=1e-12))
check("RMA matches independent reference", np.allclose(E.rma(x, 14)[13:], ref_rma(x, 14)[13:]))
df_i = mk(x)
h_i, l_i, c_i = (df_i[k].to_numpy(float) for k in ("high", "low", "close"))
check("ATR(14) = RMA of true range",
      np.allclose(E.atr_wilder(h_i, l_i, c_i, 14)[13:],
                  ref_atr(h_i, l_i, c_i, 14)[13:], atol=1e-12))

# --------------------------------------------------------------------------- #
# Paths: 30 flat bars (warmup), then a clean trend, TP disabled where a long
# hold is needed.
# --------------------------------------------------------------------------- #
UP = list(np.full(30, 100.0)) + list(np.linspace(100, 160, 170))
DN = list(np.full(30, 100.0)) + list(np.linspace(100, 40, 170))
df_up, df_dn = mk(UP), mk(DN)
p = P()                      # TP enabled (defaults)
pH = P(use_tp=False)         # TP disabled: the trade holds until a signal exit

tr_up, eq_up, _ = E.run_backtest(df_up, p)
tr_dn, eq_dn, _ = E.run_backtest(df_dn, p)
tr_upH, eq_upH, _ = E.run_backtest(df_up, pH)
tr_dnH, eq_dnH, _ = E.run_backtest(df_dn, pH)

check("uptrend produces long trades", pick(tr_up, "long") is not None, f"n={len(tr_up)}")
check("downtrend produces short trades", pick(tr_dn, "short") is not None, f"n={len(tr_dn)}")

fee = p.fee_bps / 1e4
slip = p.slip_bps / 1e4


def structure_checks(df, tr, eq, side):
    t = pick(tr, side)
    if t is None:
        return check(f"{side}: trade exists", False)
    d = 1 if side == "long" else -1
    idx = list(df.index)
    i = idx.index(t["entry_time"])
    sig = i - 1
    o = df["open"].to_numpy(float)
    l = df["low"].to_numpy(float)
    h = df["high"].to_numpy(float)
    lo = max(0, sig - p.swing_lookback + 1)
    exp_sl = l[lo:sig + 1].min() if d == 1 else h[lo:sig + 1].max()
    ok_entry = abs(t["entry"] - o[i] * (1 + slip * d)) < 1e-12
    ok_sl = abs(t["sl"] - exp_sl) < 1e-12
    risk = (t["entry"] - t["sl"]) * d
    ok_tp = (np.isnan(t["tp"]) and not p.use_tp) or \
        abs(t["tp"] - (t["entry"] + d * p.rr * risk)) < 1e-12
    ok_fee = abs(t["fees"] - t["qty"] * (t["entry"] + t["exit"]) * fee) < 1e-9
    ok_bars = int(t["bars"]) == idx.index(t["exit_time"]) - i
    gross = t["qty"] * (t["exit"] - t["entry"]) * d
    ok_pnl = abs(t["pnl"] - (gross - t["fees"] - t.get("funding", 0.0))) < 1e-9
    eq_before = eq.iloc[i - 1] if i > 0 else p.initial_equity
    risk_amt = t["qty"] * risk
    capped = t["qty"] * t["entry"] / max(eq_before, 1e-9) >= p.max_leverage - 1e-9
    ok_size = capped or abs(risk_amt / eq_before - p.risk_pct / 100) < 2e-3
    check(f"{side}: entry = next open +/- slippage", ok_entry)
    check(f"{side}: stop = rolling {p.swing_lookback}-bar swing at the signal bar", ok_sl)
    check(f"{side}: target = entry +/- {p.rr}R", ok_tp)
    check(f"{side}: fees charged qty x price on both sides", ok_fee)
    check(f"{side}: trade pnl = gross - fees - funding", ok_pnl)
    check(f"{side}: bars = exit bar - entry bar", ok_bars)
    check(f"{side}: sized to {p.risk_pct}% of equity (or leverage cap)", ok_size)


structure_checks(df_up, tr_up, eq_up, "long")
structure_checks(df_dn, tr_dn, eq_dn, "short")

# --------------------------------------------------------------------------- #
# Tie: both levels touched in one bar -> SL wins (both directions)
# --------------------------------------------------------------------------- #
def tie_case(df, tr, side):
    t = pick(tr, side)
    if t is None or np.isnan(t["tp"]):
        return None
    d = 1 if side == "long" else -1
    i = list(df.index).index(t["entry_time"]) + 1
    if i >= len(df):
        return None
    out = df.copy()
    out.iloc[i, out.columns.get_loc("open")] = t["entry"]
    if d == 1:
        out.iloc[i, out.columns.get_loc("high")] = t["tp"] * 1.01
        out.iloc[i, out.columns.get_loc("low")] = t["sl"] * 0.99
    else:
        out.iloc[i, out.columns.get_loc("high")] = t["sl"] * 1.01
        out.iloc[i, out.columns.get_loc("low")] = t["tp"] * 0.99
    tr2, _, _ = E.run_backtest(out, p)
    got = tr2[tr2.entry_time == t["entry_time"]]
    return t, got.iloc[0] if len(got) else None, d


for side, df, tr in (("long", df_up, tr_up), ("short", df_dn, tr_dn)):
    tc = tie_case(df, tr, side)
    ok = tc is not None and tc[1] is not None and tc[1]["reason"] == "SL" and \
        abs(tc[1]["exit"] - tc[0]["sl"] * (1 - slip * tc[2])) < 1e-12
    check(f"{side}: SL wins when SL and TP are both touched in one bar", ok,
          f"reason={tc[1]['reason'] if tc and tc[1] is not None else 'none'}")

# --------------------------------------------------------------------------- #
# Gap through the stop -> fill at the OPEN (both directions)
# --------------------------------------------------------------------------- #
def gap_case(df, tr, side):
    t = pick(tr, side)
    if t is None:
        return None
    d = 1 if side == "long" else -1
    i = list(df.index).index(t["entry_time"]) + 1
    if i >= len(df):
        return None
    out = df.copy()
    o = t["sl"] * (0.98 if d == 1 else 1.02)
    out.iloc[i, out.columns.get_loc("open")] = o
    out.iloc[i, out.columns.get_loc("high")] = o * 1.001
    out.iloc[i, out.columns.get_loc("low")] = o * 0.999
    tr2, _, _ = E.run_backtest(out, p)
    got = tr2[tr2.entry_time == t["entry_time"]]
    return o, got.iloc[0] if len(got) else None


for side, df, tr in (("long", df_up, tr_up), ("short", df_dn, tr_dn)):
    gc = gap_case(df, tr, side)
    ok = gc is not None and gc[1] is not None and gc[1]["reason"] == "SL_gap" and \
        abs(gc[1]["exit"] - gc[0]) < 1e-12
    check(f"{side}: gap through the stop fills at the OPEN", ok,
          f"reason={gc[1]['reason'] if gc and gc[1] is not None else 'none'}")

# --------------------------------------------------------------------------- #
# Target fill at the limit price, no slippage (both directions)
# --------------------------------------------------------------------------- #
def tp_case(df, tr, side):
    t = pick(tr, side)
    if t is None or np.isnan(t["tp"]):
        return None
    d = 1 if side == "long" else -1
    i = list(df.index).index(t["entry_time"]) + 1
    if i >= len(df):
        return None
    out = df.copy()
    out.iloc[i, out.columns.get_loc("open")] = t["entry"]
    mid = (t["entry"] + t["sl"]) / 2.0
    if d == 1:
        out.iloc[i, out.columns.get_loc("high")] = t["tp"] * 1.01
        out.iloc[i, out.columns.get_loc("low")] = mid
    else:
        out.iloc[i, out.columns.get_loc("low")] = t["tp"] * 0.99
        out.iloc[i, out.columns.get_loc("high")] = mid
    tr2, _, _ = E.run_backtest(out, p)
    got = tr2[tr2.entry_time == t["entry_time"]]
    return t, got.iloc[0] if len(got) else None


for side, df, tr in (("long", df_up, tr_up), ("short", df_dn, tr_dn)):
    tc = tp_case(df, tr, side)
    ok = tc is not None and tc[1] is not None and tc[1]["reason"] == "TP" and \
        abs(tc[1]["exit"] - tc[0]["tp"]) < 1e-12
    check(f"{side}: target fills at the limit price (no slippage)", ok,
          f"reason={tc[1]['reason'] if tc and tc[1] is not None else 'none'}")

# --------------------------------------------------------------------------- #
# Filters and flags
# --------------------------------------------------------------------------- #
tr_f, _, _ = E.run_backtest(df_up, P(min_sl_pct=50.0))
check("min_sl_pct filter removes every trade", len(tr_f) == 0)
tr_none, _, _ = E.run_backtest(mk(list(np.linspace(100, 100.2, 300))), p)
check("flat path produces no trades", len(tr_none) == 0)
tr_lo, _, _ = E.run_backtest(df_up, P(allow_short=False))
check("allow_short=False leaves only long trades",
      len(tr_lo) > 0 and set(tr_lo.side) == {"long"})
tr_so, _, _ = E.run_backtest(df_dn, P(allow_long=False))
check("allow_long=False leaves only short trades",
      len(tr_so) > 0 and set(tr_so.side) == {"short"})

# Expensive asset: a 1% risk must be 1% whatever the price (the WAVE_1 bug).
EXP = list(np.full(25, 50_000.0)) + list(np.linspace(50_000, 46_500, 20)) + \
      list(np.linspace(46_500, 70_000, 150))
df_exp = mk(EXP, step=25.0)
tr_e, eq_e, _ = E.run_backtest(df_exp, P(use_tp=False))
te = pick(tr_e, "long")
if check("expensive asset produces a long trade", te is not None):
    i = list(df_exp.index).index(te["entry_time"])
    eq_before = eq_e.iloc[i - 1] if i > 0 else p.initial_equity
    risk_amt = te["qty"] * (te["entry"] - te["sl"])
    lev = te["qty"] * te["entry"] / eq_before
    check("expensive asset: loss at the stop = 1% of equity (not price-dependent)",
          lev < p.max_leverage and abs(risk_amt / eq_before - 0.01) < 2e-4,
          f"risk%={100*risk_amt/eq_before:.4f} lev={lev:.2f}")

# --------------------------------------------------------------------------- #
# Funding: sign, timing, amount
# --------------------------------------------------------------------------- #
def funding_case(df, tr, eq, side, where, rate=0.001):
    t = pick(tr, side)
    if t is None:
        return None
    d = 1 if side == "long" else -1
    idx = list(df.index)
    i_in, i_out = idx.index(t["entry_time"]), idx.index(t["exit_time"])
    if where == "entry":
        j = i_in
    elif where == "mid":
        j = i_in + 1
    else:
        j = i_out
    if j >= len(df) or (where == "mid" and j >= i_out):
        return None
    rates = np.zeros(len(df))
    rates[j] = rate
    tr2, eq2, _ = E.run_backtest(df, pH, rates)
    got = tr2[tr2.entry_time == t["entry_time"]]
    if not len(got):
        return None
    t2 = got.iloc[0]
    o = df["open"].to_numpy(float)
    exp = d * t2["qty"] * o[j] * rate
    return t2, exp, t["pnl"], t2["pnl"]


lc = funding_case(df_up, tr_upH, eq_upH, "long", "mid", 0.001)
check("long pays positive funding at the settlement bar open",
      lc is not None and abs(lc[0]["funding"] - lc[1]) < 1e-9 and
      abs((lc[3] - lc[2]) + lc[1]) < 1e-9,
      f"funding={lc[0]['funding']:.6f} expected={lc[1]:.6f}" if lc else "no case")
sc = funding_case(df_dn, tr_dnH, eq_dnH, "short", "mid", 0.001)
check("short receives positive funding at the settlement bar open",
      sc is not None and abs(sc[0]["funding"] - sc[1]) < 1e-9 and
      abs((sc[3] - sc[2]) + sc[1]) < 1e-9,
      f"funding={sc[0]['funding']:.6f} expected={sc[1]:.6f}" if sc else "no case")
bc = funding_case(df_up, tr_upH, eq_upH, "long", "entry", 0.001)
check("no funding is charged on the entry bar (not held before the open)", 
      bc is not None and bc[0]["funding"] == 0.0,
      f"funding={bc[0]['funding'] if bc else None}")
ec = funding_case(df_up, tr_upH, eq_upH, "long", "exit", 0.002)
check("funding at the exit bar is charged BEFORE the exit (held at the open)",
      ec is not None and abs(ec[0]["funding"] - ec[1]) < 1e-9,
      f"funding={ec[0]['funding']:.6f} expected={ec[1]:.6f}" if ec else "no case")

# Funding with zero rates must be BIT-IDENTICAL to funding disabled.
tr_z, eq_z, _ = E.run_backtest(df_up, pH, np.zeros(len(df_up)))
same = (len(tr_z) == len(tr_upH) and
        np.array_equal(eq_z.to_numpy(float), eq_upH.to_numpy(float)) and
        np.allclose(tr_z.pnl.to_numpy(float), tr_upH.pnl.to_numpy(float),
                    rtol=0, atol=0))
check("zero funding rates == funding disabled (bit-identical)", same)

# --------------------------------------------------------------------------- #
# funding_by_bar: containing bar, sum, edge counts
# --------------------------------------------------------------------------- #
# REGRESSION (unit bug): the first BTC 1h run trimmed 62,686 of 62,687 bars
# because pandas gave the index microseconds and the old code divided by 1e6.
for unit in ("ns", "us", "s"):
    idx = pd.date_range("2026-01-01", periods=5, freq="1h", tz="UTC").as_unit(unit)
    check(f"_index_to_ms is unit-independent ({unit})",
          np.array_equal(E._index_to_ms(idx),
                         np.array([1767225600000, 1767229200000, 1767232800000,
                                   1767236400000, 1767240000000], dtype=np.int64)))

open_ms = np.array([0, 3_600_000, 7_200_000, 10_800_000], dtype=np.int64)
settle = np.array([-1, 0, 1_800_000, 7_200_000, 10_800_000, 14_400_000],
                  dtype=np.int64)
rate = np.array([0.5, 0.01, 0.02, 0.04, 0.08, 0.16])
by, st = E.funding_by_bar(open_ms, settle, rate, bar_ms=3_600_000)
check("funding_by_bar: settlement ON an open bills that bar",
      abs(by[0] - 0.03) < 1e-12 and abs(by[2] - 0.04) < 1e-12 and
      abs(by[3] - 0.08) < 1e-12)
check("funding_by_bar: two settlements in one bar are SUMMED",
      st["multi_bar_events"] == 1)
check("funding_by_bar: before-window and after-window are counted, not charged",
      st["before_first"] == 1 and st["after_last"] == 1 and abs(by.sum() - 0.15) < 1e-12)

# --------------------------------------------------------------------------- #
# Accounting identity with random funding
# --------------------------------------------------------------------------- #
rng = np.random.default_rng(11)
rates = rng.uniform(-0.001, 0.001, len(df_up))
tr_r, eq_r, aux_r = E.run_backtest(df_up, pH, rates)
resid = eq_r.iloc[-1] - pH.initial_equity - tr_r.pnl.sum()
check("accounting identity holds with random funding", abs(resid) < 1e-6 * abs(eq_r.iloc[-1]),
      f"resid={resid:.2e} funding={aux_r['funding_paid']:.2f}")

# --------------------------------------------------------------------------- #
# Causality and determinism
# --------------------------------------------------------------------------- #
k = int(len(df_up) * 0.7)
tr_full, eq_full, _ = E.run_backtest(df_up, pH)
tr_cut, eq_cut, _ = E.run_backtest(df_up.iloc[:k], pH)
# bars 0..k-2 cannot depend on data at/after bar k-1: compare the whole
# mark-to-market path (the truncated run's eod close only touches bar k-1).
path_same = np.array_equal(eq_full.to_numpy(float)[:k - 1],
                           eq_cut.to_numpy(float)[:k - 1])
closed = tr_full[pd.to_datetime(tr_full.exit_time, utc=True) < df_up.index[k - 1]]
trades_same = (len(closed) == len(tr_cut) - (1 if len(tr_cut) else 0) or
               len(closed) == len(tr_cut))
check("truncation leaves the earlier equity path bit-identical (no lookahead)",
      path_same and trades_same,
      f"bars={k-1} closed_trades_full={len(closed)} cut_trades={len(tr_cut)}")
tr_a, eq_a, _ = E.run_backtest(df_up, p)
tr_b, eq_b, _ = E.run_backtest(df_up, p)
check("deterministic: two runs are bit-identical",
      np.array_equal(eq_a.to_numpy(float), eq_b.to_numpy(float)) and
      np.array_equal(tr_a.pnl.to_numpy(float), tr_b.pnl.to_numpy(float)))
check("equity curve is fully defined (no NaN)",
      np.isfinite(eq_up.to_numpy(float)).all())

out = {"engine": "code/ema921_engine.py", "checks": len(PASS) + len(FAIL),
       "pass": len(PASS), "fail": len(FAIL), "failed": FAIL}
path = os.path.join(ROOT, "results", "_ema921_audit.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} PASS  -> {path}")
sys.exit(1 if FAIL else 0)
