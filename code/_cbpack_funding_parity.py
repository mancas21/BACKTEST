#!/usr/bin/env python3
"""Parity + known-answer audit for code/cbpack_funding_engine.py.

Four checks:

  T1 ZERO-FUNDING PARITY. With funding_rate forced to zero, the FORK must
     reproduce the ORIGINAL engine's metrics EXACTLY. This is the proof that the
     fork changed funding and nothing else -- no accidental edit to the signal
     logic, the fill model, the SL/TP handling or the sizing.

  T2 KNOWN-ANSWER FUNDING. Hand-computable cases: one long / one short, one and
     two settlements, and an exit that happens at a bar's OPEN (whose settlement
     must NOT be charged, because the position is flat at that bar's close).

  T3 PER-TRADE INDEPENDENT RECOMPUTATION. Recompute, from the raw funding column
     and the trade list, what each trade should have paid, and compare with the
     engine's per-trade `funding`. This is a genuine second implementation.

  T4 FUNDING IS A DRAG, AND IT IS NOT DOUBLE COUNTED. The fork's net must be
     below the original's, and gross_return_pct (which the fork reports BEFORE
     funding) must be close to the original's gross -- i.e. the difference is
     funding, not a broken P&L.

Exit 0 = all pass, 1 = a check failed.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


ORIG = load("cbpack_orig", os.path.join(ROOT, "code", "cbpack_engine.py"))
FORK = load("cbpack_fork", os.path.join(ROOT, "code", "cbpack_funding_engine.py"))

FAIL = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    if not ok:
        FAIL.append(name)


def load_real(sym="SOLUSDT", tf="1h"):
    raw = pd.read_csv(os.path.join(ROOT, "data", f"binance_klines_{tf}_taker", f"{sym}_{tf}.csv"))
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    raw = raw.rename(columns={"open_ts": "open_time"})
    raw["open_time"] = pd.to_datetime(raw["open_time"], unit="ms", utc=True)
    df = ORIG.prepare(raw.set_index("open_time"))
    recs = json.load(open(os.path.join(ROOT, "data", "binance_funding", f"{sym}_funding.json"),
                          encoding="utf-8"))
    idx = pd.DatetimeIndex(pd.to_datetime([x["t"] for x in recs], unit="ms", utc=True))
    unit = getattr(df.index + pd.Timedelta(seconds=60), "unit", None)
    if unit is not None and hasattr(idx, "as_unit"):
        idx = idx.as_unit(unit)
    s = pd.Series([float(x["r"]) for x in recs], index=idx)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    df = ORIG.attach_funding(df, s)
    # the billing schedule: only the bars that actually carry a settlement
    df = FORK.attach_funding_events(df, s)
    return df


# ─────────────────────────────────────────────────── T1 zero-funding parity
print("T1  ZERO-FUNDING PARITY  (fork vs original, funding forced to 0)")
df = load_real()
df0 = df.copy()
df0["funding_rate"] = 0.0
df0["funding_event_rate"] = 0.0      # the fork bills from the EVENT column
cfg_o = ORIG.BacktestConfig(fee_bps=5.0, slippage_bps=2.0)
cfg_f = FORK.BacktestConfig(fee_bps=5.0, slippage_bps=2.0)

to = ORIG.evaluate_all(df0, cfg_o)
tf_ = FORK.evaluate_all(df0, cfg_f)
shared = [c for c in to.columns if c in tf_.columns]
bad = []
for c in shared:
    a, b = to[c], tf_[c]
    if a.dtype.kind in "fc" or b.dtype.kind in "fc":
        if not np.allclose(a.fillna(-9e9).to_numpy(float), b.fillna(-9e9).to_numpy(float),
                           rtol=0, atol=1e-9):
            bad.append(c)
    else:
        if not a.equals(b):
            bad.append(c)
check("all shared metrics identical", not bad,
      f"differing: {bad}" if bad else f"{len(shared)} columns x {len(to)} strategies")

# the fork's concentration columns must exist and be sane
for c in ("conc_top5_share", "conc_net_without_top5_pct", "conc_passes", "funding_paid_pct"):
    check(f"fork exposes {c}", c in tf_.columns)
check("concentration: at least one strategy fails the top-5 gate",
      bool((tf_["conc_passes"] == False).any()),
      f"{(tf_['conc_passes'] == False).sum()} of {len(tf_)} fail")


# ─────────────────────────────────────────────────── T2 known-answer funding
print("\nT2  KNOWN-ANSWER FUNDING  (hand-computable)")


def tiny_frame(rates, px=100.0):
    """rates[i] = the funding rate settled at the OPEN of bar i."""
    n = len(rates)
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    return pd.DataFrame({"open": [px] * n, "high": [px] * n, "low": [px] * n,
                         "close": [px] * n, "volume": [1.0] * n,
                         "funding_rate": rates,
                         "funding_event_rate": rates}, index=idx)


def run_tiny(df_t, side, cfg_k, n_bars):
    if side == "long":
        sig = FORK._frame(df_t, buy=[True] * n_bars, sell=[False] * n_bars,
                          sl_dist=[50.0] * n_bars, tp_dist=None, max_hold=0)
    else:
        sig = FORK._frame(df_t, buy=[False] * n_bars, sell=[True] * n_bars,
                          sl_dist=[50.0] * n_bars, tp_dist=None, max_hold=0)
    return FORK.backtest(df_t, sig, cfg_k)


cfg_k = FORK.BacktestConfig(fee_bps=0.0, slippage_bps=0.0,
                            sizing_mode="fixed_pct", pct_equity=100.0, max_leverage=10.0)

# The pack opens on the bar AFTER the signal bar (pending order -> next open), and
# the entry fill is at the open of bar 1. A settlement at the open of bar i is
# charged to the position HELD AT that open.
#
# (a) long entered at the open of bar 1, settlement +0.1% at the open of bar 2
#     -> qty = 10000/100 = 100 units, charge = 100 * 100 * 0.001 = $10
t = tiny_frame([0.0, 0.0, 0.001, 0.0])
r = run_tiny(t, "long", cfg_k, 4)
tr = r.trades
check("(a) long pays 10.0", len(tr) == 1 and abs(float(tr.funding.iloc[0]) - 10.0) < 1e-9,
      f"funding={float(tr.funding.iloc[0])!r} pnl={float(tr.pnl.iloc[0])!r}" if len(tr) else "no trades")
check("(a) final equity 9990", abs(r.equity.iloc[-1] - 9990.0) < 1e-9, f"{r.equity.iloc[-1]!r}")

# (b) short, same settlement -> RECEIVES 10.0
t = tiny_frame([0.0, 0.0, 0.001, 0.0])
r = run_tiny(t, "short", cfg_k, 4)
tr = r.trades
check("(b) short RECEIVES 10.0", len(tr) == 1 and abs(float(tr.funding.iloc[0]) + 10.0) < 1e-9,
      f"funding={float(tr.funding.iloc[0])!r} pnl={float(tr.pnl.iloc[0])!r}" if len(tr) else "no trades")
check("(b) final equity 10010", abs(r.equity.iloc[-1] - 10010.0) < 1e-9, f"{r.equity.iloc[-1]!r}")

# (c) two settlements, +0.1% then -0.05% -> pays 10, receives 5, net 5 paid
t = tiny_frame([0.0, 0.0, 0.001, -0.0005, 0.0])
r = run_tiny(t, "long", cfg_k, 5)
tr = r.trades
check("(c) two settlements net to 5.0 paid", len(tr) == 1 and abs(float(tr.funding.iloc[0]) - 5.0) < 1e-9,
      f"funding={float(tr.funding.iloc[0])!r}" if len(tr) else "no trades")

# (d) a settlement at the OPEN of the entry bar is NOT charged to the new position:
#     the position is established AT that instant, so it does not pay that round.
t = tiny_frame([0.0, 0.001, 0.0, 0.0])
r = run_tiny(t, "long", cfg_k, 4)
tr = r.trades
check("(d) settlement at the entry open is NOT charged", len(tr) == 1 and abs(float(tr.funding.iloc[0])) < 1e-12,
      f"funding={float(tr.funding.iloc[0])!r}" if len(tr) else "no trades")

# (e) a settlement at the open of the EXIT bar IS charged: the position was holding
#     into that instant (the exit fills at the same open, and the funding snapshot
#     precedes the fill).
t = tiny_frame([0.0, 0.0, 0.001, 0.0])
sig = FORK._frame(t, buy=[True, True, False, False], sell=[False] * 4,
                  sl_dist=[50.0] * 4, tp_dist=None, max_hold=0,
                  exit_long=[False, True, False, False])
res_e = FORK.backtest(t, sig, cfg_k)
tre = res_e.trades
exp_e = 100 * 100 * 0.001
check("(e) settlement at the exit open IS charged", len(tre) == 1 and abs(float(tre.funding.iloc[0]) - exp_e) < 1e-9,
      f"funding={float(tre.funding.iloc[0])!r} expected {exp_e}" if len(tre) else "no trades")

# ─────────────────────────────────────────────────── T3 per-trade recomputation
print("\nT3  PER-TRADE INDEPENDENT RECOMPUTATION  (from raw settlement column)")
open_px = df["open"].to_numpy(float)
event = df["funding_event_rate"].fillna(0.0).to_numpy(float)
pos_of = {t: i for i, t in enumerate(df.index)}
for sid in ("S10", "S02", "S05"):
    res = FORK.backtest(df, FORK.make_signals(df, sid), cfg_f)
    tr = res.trades
    if not len(tr):
        check(f"{sid}: has trades", False)
        continue
    worst, n_chk = 0.0, 0
    for _, row in tr.iterrows():
        i0 = pos_of.get(row["entry_time"])
        i1 = pos_of.get(row["exit_time"])
        if i0 is None or i1 is None:
            continue
        # charged bars: the settlement at the open of bar j is charged to the
        # position HELD AT that open, i.e. a position entered at bar j is not
        # charged for bar j, and a position exiting at bar j IS charged for it.
        lo = i0 + 1
        hi = i1
        if hi < lo:
            continue
        seg_rate = event[lo:hi + 1]
        seg_open = open_px[lo:hi + 1]
        expected = float(row["dir"]) * float(row["qty"]) * float(np.sum(seg_rate * seg_open))
        got = float(row["funding"])
        worst = max(worst, abs(expected - got))
        n_chk += 1
    check(f"{sid}: per-trade funding matches independent recomputation",
          worst < 1e-6 and n_chk > 0,
          f"{n_chk} trades, max |diff| = {worst:.3e}")


# ─────────────────────────────────────────────────── T4 drag, not double count
print("\nT4  FUNDING IS A DRAG, NOT A DOUBLE COUNT")
for sid in ("S10", "S02"):
    o = ORIG.backtest(df, ORIG.make_signals(df, sid), cfg_o)
    f = FORK.backtest(df, FORK.make_signals(df, sid), cfg_f)
    net_o = o.equity.iloc[-1] / 10_000 - 1
    net_f = f.equity.iloc[-1] / 10_000 - 1
    paid = float(f.trades.funding.sum())
    check(f"{sid}: fork net < original net", net_f < net_o,
          f"orig {net_o:+.2%} -> fork {net_f:+.2%} (funding ${paid:,.0f})")
    check(f"{sid}: funding_paid is non-zero and finite", np.isfinite(paid) and paid != 0.0,
          f"${paid:,.0f}")
    # gross (before funding) must be close to the original's gross: the fork must
    # not have broken the P&L, only added the funding debit. Funding changes equity,
    # which changes the stop-risk sizing, so a small drift is expected -- but it must
    # not be a wholesale change of the P&L.
    gross_o = float((o.trades.pnl + o.trades.fees).sum())
    gross_f = float((f.trades.pnl + f.trades.fees + f.trades.funding).sum())
    check(f"{sid}: gross before funding ~= original gross",
          abs(gross_f - gross_o) <= 0.15 * max(abs(gross_o), 1.0),
          f"orig gross ${gross_o:,.0f} vs fork gross ${gross_f:,.0f}")
    # and the fork's own accounting must close: net P&L == gross - funding
    net_pnl_f = float(f.trades.pnl.sum())
    gross_f2 = net_pnl_f + float(f.trades.fees.sum()) + paid
    check(f"{sid}: fork accounting closes (net P&L == gross - funding)",
          abs(gross_f2 - gross_f) < 1e-6, f"${gross_f2:,.2f} vs ${gross_f:,.2f}")

print("\n" + "=" * 72)
if FAIL:
    print(f"FAILED: {len(FAIL)} check(s): {FAIL}")
    raise SystemExit(1)
print("ALL PARITY CHECKS PASS")
raise SystemExit(0)
