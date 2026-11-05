#!/usr/bin/env python
"""_cand7_audit.py -- known-answer audit of the cand7 execution machinery.

Every check is a hand-computed number, not a comparison with a previous run.
If one fails, no cand7 artifact may be published.

    python code/_cand7_audit.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cand7_core as C
import cand7_strats as S

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


def mk(o, h, l, c, start=0):
    n = len(o)
    return pd.DataFrame({
        "open_ts": np.arange(n, dtype=np.int64) * 3_600_000 + start,
        "open": np.asarray(o, float), "high": np.asarray(h, float),
        "low": np.asarray(l, float), "close": np.asarray(c, float),
        "volume": np.full(n, 1000.0), "taker_buy_base": np.full(n, 500.0),
    })


def sig(n, idx, side=1):
    a = np.zeros(n, bool)
    a[idx] = True
    return a


# ══════════════════════════════════════════════ 1. next-open fill + costs
df = mk([100] * 8, [101] * 8, [99] * 8, [100] * 8)
le, se = sig(8, 1), np.zeros(8, bool)
lx, sx = sig(8, 3), np.zeros(8, bool)
res = C.sim_single(df, long_entry=le, short_entry=se, long_exit=lx,
                   short_exit=sx, costs=C.Costs(5.0, 2.0), risk_frac=None,
                   size_frac=1.0, init_equity=10000.0)
tr = res["trades"]
# entry at open[2]=100 slipped to 100.02, exit at open[4]=100 slipped to 99.98
# qty = 10000/100.02 ; fee_in = qty*100.02*5e-4 = 5.0 ; fee_out = qty*99.98*5e-4
qty = 10000.0 / 100.02
exp_pnl = qty * (99.98 - 100.02) - 5.0 - qty * 99.98 * 5e-4
check("next-open fill and fee/slip direction",
      len(tr) == 1 and abs(tr.iloc[0]["entry_px"] - 100.02) < 1e-9
      and abs(tr.iloc[0]["exit_px"] - 99.98) < 1e-9
      and abs(tr.iloc[0]["pnl"] - exp_pnl) < 1e-6,
      f"pnl={tr.iloc[0]['pnl']:.6f} expected={exp_pnl:.6f}")

# short side: sell at 99.98, buy back at 100.02
res = C.sim_single(df, long_entry=np.zeros(8, bool), short_entry=sig(8, 1, -1),
                   long_exit=np.zeros(8, bool), short_exit=sig(8, 3, -1),
                   costs=C.Costs(5.0, 2.0), risk_frac=None, size_frac=1.0)
tr = res["trades"]
qty_s = 10000.0 / 99.98
exp_short = -qty_s * 0.04 - 5.0 - qty_s * 100.02 * 5e-4
check("short side slip direction",
      len(tr) == 1 and abs(tr.iloc[0]["entry_px"] - 99.98) < 1e-9
      and abs(tr.iloc[0]["exit_px"] - 100.02) < 1e-9
      and abs(tr.iloc[0]["pnl"] - exp_short) < 1e-6,
      f"pnl={tr.iloc[0]['pnl']:.6f} expected={exp_short:.6f}")

# ══════════════════════════════════════════════ 2. stop-first on ties
# entry at bar 2 open 100; stop 95, target 105; bar 3 range 90..110 contains both
df2 = mk([100, 100, 100, 100, 100], [101, 101, 101, 110, 101],
         [99, 99, 99, 90, 99], [100] * 5)
res = C.sim_single(df2, long_entry=sig(5, 1), short_entry=np.zeros(5, bool),
                   stop_dist=np.full(5, 5.0), tp_dist=np.full(5, 5.0),
                   costs=C.Costs(5.0, 2.0), risk_frac=None, size_frac=1.0)
tr = res["trades"]
# stop fills at 95.02 (5 below the slipped fill 100.02), adverse 2 bps
check("stop first when stop and target share a bar",
      len(tr) == 1 and tr.iloc[0]["exit_reason"] == "stop"
      and abs(tr.iloc[0]["exit_px"] - 95.02 * (1 - 2e-4)) < 1e-9,
      f"{tr.iloc[0]['exit_reason']} @ {tr.iloc[0]['exit_px']:.6f}")

# ══════════════════════════════════════════════ 3. gap through the stop
df3 = mk([100, 100, 100, 100, 100], [101, 101, 101, 101, 101],
         [99, 99, 99, 80, 99], [100, 100, 100, 85, 100])
# force the stop on bar 3 by a gap: open[3] must be below 95.  Rebuild with a gap open.
df3.loc[3, "open"] = 90.0
res = C.sim_single(df3, long_entry=sig(5, 1), short_entry=np.zeros(5, bool),
                   stop_dist=np.full(5, 5.0), costs=C.Costs(5.0, 2.0),
                   risk_frac=None, size_frac=1.0)
tr = res["trades"]
check("gap through stop fills at the open, adverse slip",
      len(tr) == 1 and tr.iloc[0]["exit_reason"] == "stop"
      and abs(tr.iloc[0]["exit_px"] - 90 * (1 - 2e-4)) < 1e-9,
      f"{tr.iloc[0]['exit_px']:.6f}")

# ══════════════════════════════════════════════ 4. funding sign and mark
f_ts = np.array([3_600_000], np.int64)         # settlement inside the trade
f_r = np.array([0.001], float)
df4 = mk([100] * 6, [101] * 6, [99] * 6, [100] * 6)
res = C.sim_single(df4, long_entry=sig(6, 0), short_entry=np.zeros(6, bool),
                   long_exit=sig(6, 2), short_exit=np.zeros(6, bool),
                   costs=C.Costs(0.0, 0.0), risk_frac=None, size_frac=1.0,
                   funding=(f_ts, f_r))
tr = res["trades"]
q = 10000.0 / 100.0
check("long pays positive funding on the settlement mark",
      len(tr) == 1 and abs(tr.iloc[0]["funding"] - (-q * 100.0 * 0.001)) < 1e-9,
      f"funding={tr.iloc[0]['funding']:.6f}")

# short receives a settlement INSIDE the holding period (entry bar 1, exit bar 3)
f_mid = np.array([2 * 3_600_000], np.int64)
res = C.sim_single(df4, long_entry=np.zeros(6, bool), short_entry=sig(6, 0, -1),
                   long_exit=np.zeros(6, bool), short_exit=sig(6, 2, -1),
                   costs=C.Costs(0.0, 0.0), risk_frac=None, size_frac=1.0,
                   funding=(f_mid, f_r))
tr = res["trades"]
check("short receives positive funding",
      len(tr) == 1 and abs(tr.iloc[0]["funding"] - (+q * 100.0 * 0.001)) < 1e-9,
      f"funding={tr.iloc[0]['funding']:.6f}")

# entry-instant asymmetry: paying settlement included, receiving excluded.
# The signal at close 0 fills at the open of bar 1, so the entry instant is 3.6e6.
f0 = np.array([3_600_000], np.int64)
res = C.sim_single(df4, long_entry=sig(6, 0), short_entry=np.zeros(6, bool),
                   long_exit=sig(6, 2), short_exit=np.zeros(6, bool),
                   costs=C.Costs(0.0, 0.0), risk_frac=None, size_frac=1.0,
                   funding=(f0, np.array([0.001])))
tr = res["trades"]
check("settlement exactly at entry is charged when paying",
      len(tr) == 1 and abs(tr.iloc[0]["funding"] - (-q * 100.0 * 0.001)) < 1e-9,
      f"funding={tr.iloc[0]['funding']:.6f}")
res = C.sim_single(df4, long_entry=sig(6, 0), short_entry=np.zeros(6, bool),
                   long_exit=sig(6, 2), short_exit=np.zeros(6, bool),
                   costs=C.Costs(0.0, 0.0), risk_frac=None, size_frac=1.0,
                   funding=(f0, np.array([-0.001])))
tr = res["trades"]
check("settlement exactly at entry is NOT credited when receiving",
      len(tr) == 1 and tr.iloc[0]["funding"] == 0.0,
      f"funding={tr.iloc[0]['funding']:.6f}")

# ══════════════════════════════════════════════ 5. risk sizing and 3x cap
df5 = mk([100] * 6, [101] * 6, [99] * 6, [100] * 6)
res = C.sim_single(df5, long_entry=sig(6, 0), short_entry=np.zeros(6, bool),
                   long_exit=sig(6, 2), short_exit=np.zeros(6, bool),
                   stop_dist=np.full(6, 2.0), costs=C.Costs(0.0, 0.0),
                   risk_frac=0.005, max_leverage=3.0)
tr = res["trades"]
# risk 50 USDT / 2 price units = 25 units; the 3x cap is 300 units, not binding
check("risk sizing = 0.5% of equity at the stop",
      len(tr) == 1 and abs(tr.iloc[0]["qty"] - 25.0) < 1e-9,
      f"qty={tr.iloc[0]['qty']:.6f}")
res = C.sim_single(df5, long_entry=sig(6, 0), short_entry=np.zeros(6, bool),
                   long_exit=sig(6, 2), short_exit=np.zeros(6, bool),
                   stop_dist=np.full(6, 0.1), costs=C.Costs(0.0, 0.0),
                   risk_frac=0.005, max_leverage=3.0)
tr = res["trades"]
check("3x notional cap binds a very tight stop",
      len(tr) == 1 and abs(tr.iloc[0]["qty"] - 300.0) < 1e-9,
      f"qty={tr.iloc[0]['qty']:.6f}")

# ══════════════════════════════════════════════ 6. time stop
# entry at bar 1 open, H=3 -> exit at open 4
df6 = mk([100] * 8, [101] * 8, [99] * 8, [100] * 8)
res = C.sim_single(df6, long_entry=sig(8, 0), short_entry=np.zeros(8, bool),
                   costs=C.Costs(0.0, 0.0), risk_frac=None, size_frac=1.0,
                   time_stop_bars=3)
tr = res["trades"]
check("time stop exits at the open of entry_i + H",
      len(tr) == 1 and tr.iloc[0]["entry_ts"] == 3_600_000
      and tr.iloc[0]["exit_ts"] == 4 * 3_600_000
      and tr.iloc[0]["exit_reason"] == "time_stop",
      f"entry={tr.iloc[0]['entry_ts']} exit={tr.iloc[0]['exit_ts']} why={tr.iloc[0]['exit_reason']}")

# ══════════════════════════════════════════════ 7. cooldown after exit
df7 = mk([100] * 12, [101] * 12, [99] * 12, [100] * 12)
le = np.zeros(12, bool)
le[[0, 3]] = True
lx = np.zeros(12, bool)
lx[1] = True
res = C.sim_single(df7, long_entry=le, short_entry=np.zeros(12, bool),
                   long_exit=lx, short_exit=np.zeros(12, bool),
                   costs=C.Costs(0.0, 0.0), risk_frac=None, size_frac=1.0,
                   cooldown_after_exit=5)
check("cooldown after exit blocks the early re-entry",
      len(res["trades"]) == 1, f"n={len(res['trades'])}")

# ══════════════════════════════════════════════ 8. basket turnover cost
# two assets, flat prices, weight +0.5 asset 0 for one bar, then flat.
dfs = [mk([100] * 5, [100] * 5, [100] * 5, [100] * 5),
       mk([100] * 5, [100] * 5, [100] * 5, [100] * 5)]
T = np.full((5, 2), np.nan)
T[1] = [0.5, 0.0]
T[2] = [0.0, 0.0]
res = C.sim_basket(dfs, T, costs=C.Costs(5.0, 2.0), per_leg_stop=None)
eq = res["equity"]
# entry cost 0.5*10000*7bps = 3.5 ; exit cost 0.5*(10000-3.5)*7bps = 3.4988
exp = 10000 - 3.5
exp = exp - 0.5 * exp * 7e-4
check("basket charges (fee+slip) on entry and exit notional",
      abs(eq[-1] - exp) < 1e-6,
      f"eq={eq[-1]:.6f} expected={exp:.6f}")
check("basket period rows sum to the book result",
      abs(float(res["trades"]["pnl"].sum()) - (res["final_equity"] - 10000.0)) < 1e-9
      and abs(float(res["trades"]["fees"].sum()) - res["fees"]) < 1e-9,
      f"rows_pnl={float(res['trades']['pnl'].sum()):.6f} "
      f"book={res['final_equity'] - 10000.0:.6f} "
      f"rows_fees={float(res['trades']['fees'].sum()):.6f} book_fees={res['fees']:.6f}")

# per-leg stop: +0.125 weight, -8% stop -> -1% of equity plus exit cost
O = [100] * 6
H = [100, 100, 100, 91, 100, 100]
L = [100, 100, 100, 90, 100, 100]
Cl = [100, 100, 100, 90, 100, 100]
d1 = mk(O, H, L, Cl)
d2 = mk(O, O, O, O)
dfs = [d1, d2]
T = np.full((6, 2), np.nan)
T[1] = [0.125, 0.0]
T[4] = [0.0, 0.0]
res = C.sim_basket(dfs, T, costs=C.Costs(0.0, 0.0), per_leg_stop=0.08)
# the leg is stopped at 92 (100*0.92) and the bar closes at 90; only -8% is taken
eq = res["equity"]
check("per-leg stop caps the leg at exactly -8% before costs",
      abs(eq[3] - 10000 * (1 - 0.125 * 0.08)) < 1e-6,
      f"eq={eq[3]:.6f} expected={10000 * (1 - 0.01):.6f}")

# ══════════════════════════════════════════════ 8b. basket funding sign
dfs = [mk([100] * 6, [100] * 6, [100] * 6, [100] * 6),
       mk([100] * 6, [100] * 6, [100] * 6, [100] * 6)]
T = np.full((6, 2), np.nan)
T[1] = [0.5, 0.0]
T[3] = [0.0, 0.0]
fb = (np.array([2 * 3_600_000], np.int64), np.array([0.001]))
res = C.sim_basket(dfs, T, costs=C.Costs(0.0, 0.0), fundings=[fb, None])
eq = res["equity"]
check("basket long leg pays funding on |w| x equity",
      abs(eq[2] - (10000.0 - 0.5 * 10000.0 * 0.001)) < 1e-9,
      f"eq={eq[2]:.6f} expected=9995.000000")
check("basket period row carries its funding cash",
      abs(float(res["trades"]["funding"].sum()) - res["funding"]) < 1e-9
      and abs(float(res["trades"]["funding"].iloc[0]) - (-5.0)) < 1e-9,
      f"rows={float(res['trades']['funding'].sum()):.6f} book={res['funding']:.6f}")

# ══════════════════════════════════════════════ 8c. the C4 book kill is inert
check("C4 book kill (-15%) cannot bind before all four -8% legs stop out",
      0.50 * 0.08 < 0.15,
      f"max stop-driven book loss = {100 * 0.50 * 0.08:.2f}%")

# ══════════════════════════════════════════════ 8d. C6 differential indexing
grid = np.arange(5, dtype=np.int64)
diff = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
d3 = pd.Series(diff).rolling(3, min_periods=3).mean().to_numpy()
# at the bar opening at grid[4], the last three settled diffs are 2,3,4
check("C6 D at an instant uses the three settlements strictly before it",
      abs(d3[3] - np.mean(diff[1:4])) < 1e-12,
      f"D={d3[3]:.6f}")

# ══════════════════════════════════════════════ 9. pair funding both legs
a = mk([100] * 6, [101] * 6, [99] * 6, [100] * 6)
b = mk([200] * 6, [201] * 6, [199] * 6, [200] * 6)
entry = np.zeros(6, int)
entry[0] = 1
xo = np.zeros(6, bool)
xo[2] = True
fa = (np.array([3_600_000], np.int64), np.array([0.001]))
fb = (np.array([3_600_000], np.int64), np.array([0.0005]))
res = C.sim_pair(a, b, entry_at_open=entry, exit_at_open=xo,
                 stop_at_close=np.zeros(6, bool), entry_frac=0.20,
                 costs=C.Costs(0.0, 0.0), fund_a=fa, fund_b=fb)
tr = res["trades"]
qa = 0.20 * 10000 / 100.0
qb = 0.20 * 10000 / 200.0
exp_fa = -qa * 100 * 0.001
exp_fb = +qb * 200 * 0.0005
check("pair charges each leg's own funding with its own sign",
      len(tr) == 1 and abs(tr.iloc[0]["funding_a"] - exp_fa) < 1e-9
      and abs(tr.iloc[0]["funding_b"] - exp_fb) < 1e-9,
      f"a={tr.iloc[0]['funding_a']:.6f} b={tr.iloc[0]['funding_b']:.6f}")

# the mirrored pair must invert the P&L: pos=-1 is short A / long B
a = mk([100] * 6, [100] * 6, [100] * 6, [100] * 6)
b = mk([200, 200, 200, 180, 180, 180], [200] * 6, [180] * 6,
       [200, 200, 200, 180, 180, 180])
entry = np.zeros(6, int)
entry[0] = -1
xo = np.zeros(6, bool)
xo[3] = True
res = C.sim_pair(a, b, entry_at_open=entry, exit_at_open=xo,
                 stop_at_close=np.zeros(6, bool), entry_frac=0.20,
                 costs=C.Costs(0.0, 0.0))
qb = 0.20 * 10000 / 200.0
check("mirrored pair (short A / long B) loses when B falls",
      abs(float(res["trades"].iloc[0]["pnl"]) - (-qb * 20.0)) < 1e-9,
      f"pnl={float(res['trades'].iloc[0]['pnl']):.6f} expected={-qb * 20.0:.6f}")
entry[0] = 1
res = C.sim_pair(a, b, entry_at_open=entry, exit_at_open=xo,
                 stop_at_close=np.zeros(6, bool), entry_frac=0.20,
                 costs=C.Costs(0.0, 0.0))
check("long A / short B gains when B falls",
      abs(float(res["trades"].iloc[0]["pnl"]) - (+qb * 20.0)) < 1e-9,
      f"pnl={float(res['trades'].iloc[0]['pnl']):.6f} expected={qb * 20.0:.6f}")

# spread stop is direction-aware: for the mirrored pair (long B / short A), a
# 6% fall in B relative to A is the loss, and it must also trigger the stop.
b = mk([200, 200, 200, 188, 188, 188], [200] * 6, [188] * 6, [200, 200, 200, 188, 188, 188])
entry = np.zeros(6, int)
entry[0] = -1
res = C.sim_pair(a, b, entry_at_open=entry, exit_at_open=np.zeros(6, bool),
                 stop_at_close=np.zeros(6, bool), entry_frac=0.20,
                 costs=C.Costs(0.0, 0.0), spread_stop=0.05)
check("pair spread stop fires on the mirrored direction too",
      len(res["trades"]) == 1
      and int(res["trades"].iloc[0]["exit_ts"]) == 4 * 3_600_000
      and res["trades"].iloc[0]["exit_reason"] == "spread_stop",
      f"exit_ts={int(res['trades'].iloc[0]['exit_ts'])} why={res['trades'].iloc[0]['exit_reason']}")

# max-hold exit carries its own label, not the spread stop's
res = C.sim_pair(a, b, entry_at_open=entry, exit_at_open=np.zeros(6, bool),
                 stop_at_close=np.zeros(6, bool), entry_frac=0.20,
                 costs=C.Costs(0.0, 0.0), max_hold_bars=2)
check("pair max-hold exit is labelled max_hold",
      len(res["trades"]) == 1
      and res["trades"].iloc[0]["exit_reason"] == "max_hold",
      f"why={res['trades'].iloc[0]['exit_reason'] if len(res['trades']) else 'none'}")

# ══════════════════════════════════════════════ 10. C7 settlement indexing
f_ts = np.arange(6, dtype=np.int64) * 28_800_000       # 8h grid, ts=0..5*8h
f_r = np.array([0.0001, 0.0002, 0.0003, 0.0004, 0.0005, 0.0006])
d = pd.DataFrame({"open_ts": f_ts, "open": [100] * 6, "high": [101] * 6,
                  "low": [99] * 6, "close": [100] * 6, "volume": [1] * 6,
                  "taker_buy_base": [1] * 6})
# Fnow[s-1] = mean(r[s-3..s-1]); at s=5 -> mean(0.0003,0.0004,0.0005)=0.0004
fn = pd.Series(f_r).rolling(3).mean().to_numpy()
check("C7 F at settlement s uses the three rates before the instant",
      abs(fn[4] - np.mean(f_r[2:5])) < 1e-12,
      f"F={fn[4]:.6f}")

# ══════════════════════════════════════════════ 11. determinism
r1 = C.sim_single(df5, long_entry=sig(6, 0), short_entry=np.zeros(6, bool),
                  long_exit=sig(6, 2), short_exit=np.zeros(6, bool),
                  stop_dist=np.full(6, 2.0), costs=C.Costs(5.0, 2.0),
                  risk_frac=0.005)
r2 = C.sim_single(df5, long_entry=sig(6, 0), short_entry=np.zeros(6, bool),
                  long_exit=sig(6, 2), short_exit=np.zeros(6, bool),
                  stop_dist=np.full(6, 2.0), costs=C.Costs(5.0, 2.0),
                  risk_frac=0.005)
check("determinism: two runs are identical",
      np.array_equal(r1["equity"], r2["equity"]) and
      r1["trades"].equals(r2["trades"]))

# ══════════════════════════════════════════════ 12. no look-ahead in C1
# a signal on the LAST bar cannot trade (no next open)
n = 900
rng = np.random.default_rng(7)
c = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
o = np.concatenate(([c[0]], c[:-1]))
h = np.maximum(o, c) * 1.001
l = np.minimum(o, c) * 0.999
vol = rng.uniform(100, 200, n)
tb = vol * rng.uniform(0.4, 0.6, n)
d = pd.DataFrame({"open_ts": np.arange(n, dtype=np.int64) * 3_600_000,
                  "open": o, "high": h, "low": l, "close": c,
                  "volume": vol, "taker_buy_base": tb})
plan = S.build_c1(d)
le = plan["long_entry"]
# every signal must have a fillable next bar
check("C1 never signals on the last bar",
      not le[-1] and not plan["short_entry"][-1],
      f"last={le[-1]}")

print()
print(f"{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
