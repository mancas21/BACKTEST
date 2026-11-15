#!/usr/bin/env python
"""_qs097_audit.py -- known answers for the QS-097 cross-asset confirmation
port. Run BEFORE any real-data artifact (repo mandatory order).

Sections:
  A. hand-built synthetic panels (3 assets: BTC traded, ETH + SOL confirm,
     min_others=1; the 2-of threshold semantics covered explicitly in A3):
     confirmation veto, pass + next-open fill, others threshold, stale veto,
     episode no-reentry, 10-bar-low exit, stop with gap, max-hold, short
     mirror, short exit.
  B. primitives imported BY IDENTITY from the catalog engine.
  C. determinism and no-lookahead truncation on the panel state.
Expectation bugs count against the TEST first (the audited lesson: every
failure in this file's first drafts was the test's geometry, not the engine).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
import qs097_engine as E          # noqa: E402
import qs_engine as Q             # noqa: E402

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


TF = 3_600_000
T0 = 1_700_000_000_000

# 3-asset panels: only ONE "other" exists, so the battery runs at
# min_others=1 here; the >=2 threshold is tested explicitly in A3.
CFG = dict(E.P, variant="long", min_others=1)


def mk_panel(btc, eth, sol, traded="BTCUSDT"):
    panel = {}
    for sym, bars in (("BTCUSDT", btc), ("ETHUSDT", eth), ("SOLUSDT", sol)):
        a = np.asarray(bars, float)
        n = len(a)
        panel[sym] = pd.DataFrame(dict(
            open_ts=T0 + np.arange(n) * TF,
            open=a[:, 0], high=a[:, 1], low=a[:, 2], close=a[:, 3]))
    assert traded in panel
    return panel


def flat_bars(n, px=100.0, spread=1.0):
    return [(px, px + spread, px - spread, px)] * n


def up_range(n, px, step):
    return [(px + step * i, px + step * i + 1.0, px + step * i - 1.0,
             px + step * i) for i in range(n)]


def dn_range(n, px, step):
    return [(px - step * i, px - step * i + 1.0, px - step * i - 1.0,
             px - step * i) for i in range(n)]


# a burst bar that clears a 0.2-step channel (prior 20-high ~ 112.8)
BURST = (111.0, 122.0, 110.0, 121.0)
# a breakdown bar that clears a 0.2-step channel (prior 20-low ~ 87.2)
BREAK = (89.0, 90.0, 78.0, 79.0)


def a1_confirmation_veto():
    """ETH below its EMA -> the REQUIRED confirmation fails -> no entry."""
    n = 90
    btc = up_range(60, 100.0, 0.2) + [BURST] + up_range(n - 61, 121.0, 0.2)
    eth = [(100 - 0.5 * i, 101 - 0.5 * i, 99 - 0.5 * i, 100 - 0.5 * i)
           for i in range(n)]
    sol = up_range(n, 100.0, 0.5)
    panel = mk_panel(btc, eth, sol)
    plan = E.build_plan(panel, "BTCUSDT", TF, CFG)
    le = np.asarray(plan["long_event"], bool)
    se = np.asarray(plan["short_event"], bool)
    req_l, req_s, oth_l, oth_s, stale = E._panel_state(panel, "BTCUSDT", TF, CFG)
    check("A1 ETH below EMA -> required confirmation false",
          not req_l[60], f"req_l[60]={req_l[60]}")
    check("A1 no long entry anywhere (veto active)", not le.any(),
          f"long events={le.sum()}")
    check("A1 no short events (variant=long)", not se.any())
    check("A1 SOL counted above (others=1)", int(oth_l[60]) == 1, str(oth_l[60]))


def a2_confirmation_pass_and_entry():
    """All three rising; BTC bursts above the 20-bar high -> exactly one long
    event at the burst bar, filled by the executor at the NEXT open."""
    n = 90
    btc = up_range(60, 100.0, 0.2) + [BURST] + up_range(n - 61, 121.0, 0.2)
    eth = up_range(n, 50.0, 0.2)
    sol = up_range(n, 200.0, 0.2)
    panel = mk_panel(btc, eth, sol)
    plan = E.build_plan(panel, "BTCUSDT", TF, CFG)
    le = np.asarray(plan["long_event"], bool)
    check("A2 exactly one long event (episode first bar)", int(le.sum()) == 1,
          str(np.where(le)[0]))
    check("A2 the event is the burst bar (index 60)", bool(le[60]),
          str(np.where(le)[0]))
    out = E.run_symbol(panel, "BTCUSDT", TF, CFG, cost="zero")
    tr = out["trades"]
    # the burst bar's close is 121.0; the next bar's open is also 121.0
    check("A2 executor fills at the NEXT open (bar 61, open 121.0)",
          len(tr) >= 1 and tr[0]["entry_i"] == 61
          and abs(tr[0]["entry_px"] - 121.0) < 1e-9,
          str([(t['entry_i'], t['entry_px']) for t in tr]))


def a3_others_threshold():
    """The >=2-of-others rule: BTC traded with ONE other above -> at
    min_others=2 the entry is vetoed even with BTC+ETH perfect."""
    n = 90
    up = up_range(n, 100.0, 0.2)
    dn = [(100 - 0.5 * i, 101 - 0.5 * i, 99 - 0.5 * i, 100 - 0.5 * i)
          for i in range(n)]
    burst = up_range(60, 100.0, 0.2) + [BURST] + up_range(n - 61, 121.0, 0.2)
    cfg2 = dict(E.P, variant="long", min_others=2)
    panel = mk_panel(burst, up, dn)
    le = np.asarray(E.build_plan(panel, "BTCUSDT", TF, cfg2)["long_event"], bool)
    check("A3a 0 of 1 others above, min_others=2 -> no entry", not le.any())
    le1 = np.asarray(E.build_plan(panel, "BTCUSDT", TF,
                                  dict(cfg2, min_others=1))["long_event"], bool)
    check("A3b the single other is BELOW -> vetoed even at min_others=1",
          not le1.any(), str(np.where(le1)[0]))


def a4_stale_veto():
    """A REAL 10-bar timestamp gap in ETH (rows dropped, stamps stay put):
    at the burst bar the latest ETH confirm is > stale_bars old -> stale ->
    entry vetoed. BTC+ETH are the required pair; SOL keeps flowing."""
    n = 90
    btc = up_range(58, 100.0, 0.2) + [(110.4, 121.4, 109.4, 120.4)] + \
        up_range(n - 59, 120.4, 0.2)
    eth = up_range(n, 50.0, 0.2)
    sol = up_range(n, 200.0, 0.2)
    panel = mk_panel(btc, eth, sol)
    panel["ETHUSDT"] = panel["ETHUSDT"].drop(range(50, 60)).reset_index(drop=True)
    req_l, req_s, oth_l, oth_s, stale = E._panel_state(panel, "BTCUSDT", TF, CFG)
    check("A4 stale flagged at the burst bar (58)", bool(stale[58]),
          str(stale[54:60].astype(int)))
    le = np.asarray(E.build_plan(panel, "BTCUSDT", TF, CFG)["long_event"], bool)
    check("A4 stale -> no long entry at the burst", not le[58])


def a5_episode_no_reentry():
    """Burst then a drift steeper than the spread: the breakout STATE holds
    forever. An ETH collapse fires the confirmation-lost exit; the book must
    NOT re-enter while the same breakout run holds (no new event after 60)."""
    n = 120
    btc = up_range(60, 100.0, 0.2) + [BURST] + up_range(n - 61, 122.5, 1.2)
    eth = up_range(70, 50.0, 0.2) + \
        [(60.0 - 0.5 * i, 61.0 - 0.5 * i, 59.0 - 0.5 * i, 60.0 - 0.5 * i)
         for i in range(n - 70)]
    sol = up_range(n, 200.0, 0.2)
    panel = mk_panel(btc, eth, sol)
    plan = E.build_plan(panel, "BTCUSDT", TF, CFG)
    le = np.asarray(plan["long_event"], bool)
    lx = np.asarray(plan["long_exit"], bool)
    check("A5 single first-episode event at 60", int(le.sum()) == 1 and bool(le[60]),
          str(np.where(le)[0]))
    check("A5 confirmation-lost exit fires when ETH closes below its EMA",
          bool(lx[75]), str(lx[70:80].astype(int)))


def a6_ten_bar_low_exit():
    """Burst at 60 (entry at 61's open 122.0), calm bars 61-69, then a bar at
    71 that CLOSES below the prior 10-bar low (the window 61..70 no longer
    contains the burst's low) WITHOUT hitting the 2*ATR stop (~116.6):
    exit signal at 71, executor exits at the NEXT open (72)."""
    n = 130
    btc = up_range(60, 100.0, 0.2) + [BURST] + up_range(10, 122.0, 0.2) + \
        [(119.0, 120.0, 118.0, 118.5)] + up_range(n - 72, 118.0, 0.2)
    eth = up_range(n, 50.0, 0.2)
    sol = up_range(n, 200.0, 0.2)
    panel = mk_panel(btc, eth, sol)
    plan = E.build_plan(panel, "BTCUSDT", TF, CFG)
    lx = np.asarray(plan["long_exit"], bool)
    check("A6 exit signal on the 10-bar-low break bar (71)",
          bool(lx[71]), str(np.where(lx)[0][:5]))
    out = E.run_symbol(panel, "BTCUSDT", TF, CFG, cost="zero")
    tr = out["trades"]
    check("A6 entry at 61, exit at the NEXT open after the exit signal (72)",
          len(tr) >= 1 and tr[0]["entry_i"] == 61 and tr[0]["exit_i"] == 72
          and tr[0]["why"] == "signal exit",
          str([(t['entry_i'], t['exit_i'], t['why']) for t in tr]))


def a7_stop_two_atr_with_gap():
    """Burst at 60 (entry at 61), one calm bar, then a gap-down bar through
    the 2*ATR stop: the stop fills at that bar (stop-first, gap at the open)."""
    n = 120
    btc = up_range(60, 100.0, 0.2) + [BURST] + \
        [(121.5, 122.5, 120.5, 122.0)] + [(90.0, 91.0, 80.0, 82.0)] + \
        flat_bars(n - 63, 82.0)
    eth = up_range(n, 50.0, 0.2)
    sol = up_range(n, 200.0, 0.2)
    panel = mk_panel(btc, eth, sol)
    out = E.run_symbol(panel, "BTCUSDT", TF, CFG, cost="zero")
    tr = out["trades"]
    ok = len(tr) >= 1 and tr[0]["why"] == "stop" and tr[0]["exit_i"] == 62
    check("A7 stop fills on the gap bar (62)", ok,
          str([(t['entry_i'], t['exit_i'], t['why'], t['exit_px']) for t in tr]))
    if ok:
        check("A7 gap fill counted", out["n_gap_fills"] >= 1,
              str(out["n_gap_fills"]))


def a8_max_hold():
    """Burst at 60 then a gentle rise: no 10-low break, no stop hit -> the
    position must close by the 150-bar time stop."""
    n = 300
    btc = up_range(60, 100.0, 0.2) + [BURST] + up_range(n - 61, 121.0, 0.2)
    eth = up_range(n, 50.0, 0.2)
    sol = up_range(n, 200.0, 0.2)
    panel = mk_panel(btc, eth, sol)
    out = E.run_symbol(panel, "BTCUSDT", TF, CFG, cost="zero")
    tr = out["trades"]
    check("A8 time stop closes at 150 bars", len(tr) >= 1
          and tr[0]["exit_i"] - tr[0]["entry_i"] + 1 >= 150
          and tr[0]["why"] == "time stop",
          str([(t['entry_i'], t['exit_i'], t['why']) for t in tr[:2]]))


def a9_short_mirror():
    """variant=two_side at min_others=1: a REAL breakdown bar + BTC/ETH below
    their EMAs -> short entry; the executor opens the short at the next open;
    a pop closing above the prior 10-bar high fires the short exit."""
    cfg = dict(E.P, variant="two_side", min_others=1)
    n = 120
    btc = dn_range(60, 100.0, 0.2) + [BREAK] + dn_range(n - 61, 79.0, 0.2)
    eth = dn_range(n, 50.0, 0.2)
    sol = dn_range(n, 200.0, 0.2)
    panel = mk_panel(btc, eth, sol)
    plan = E.build_plan(panel, "BTCUSDT", TF, cfg)
    se = np.asarray(plan["short_event"], bool)
    check("A9 short event on the breakdown bar", int(se.sum()) >= 1
          and bool(se[60]), str(np.where(se)[0][:5]))
    out = E.run_symbol(panel, "BTCUSDT", TF, cfg, cost="zero")
    tr = out["trades"]
    check("A9 executor opens the short at the next open",
          len(tr) >= 1 and tr[0]["side"] == -1 and tr[0]["entry_i"] == 61,
          str([(t['side'], t['entry_i']) for t in tr]))
    # short exit: close above the prior 10-bar high (the window 61..70 after
    # the breakdown bar no longer contains it) -> exit at the pop bar
    btc2 = dn_range(60, 100.0, 0.2) + [BREAK] + dn_range(9, 79.0, 0.2) + \
        [(81.0, 92.0, 80.5, 91.0)] + dn_range(n - 72, 91.0, 0.2)
    panel2 = mk_panel(btc2, eth, sol)
    sx2 = np.asarray(E.build_plan(panel2, "BTCUSDT", TF, cfg)["short_exit"], bool)
    check("A9 short exit on the 10-bar-high break (71)", bool(sx2[71]),
          str(np.where(sx2)[0][:5]))


# ── B/C ──────────────────────────────────────────────────────────────────────
def b1_identity():
    check("B1 catalog primitives BY IDENTITY",
          E.cat_run is Q.run and E.cat_ema is Q.ema and E.cat_atr is Q.atr
          and E.load_funding is Q.load_funding and E.G1 is Q.G1
          and E.COSTS["gate"] is Q.COSTS["gate"])
    check("B2 gate costs = repo 11 bps RT",
          abs((E.COSTS["gate"]["fee"] + E.COSTS["gate"]["slip"]) * 2 - 0.0011)
          < 1e-12)


def _rw(rng, n, px, s):
    x = px + np.cumsum(rng.normal(0, s, n))
    return [(x[i], x[i] + 1.0, x[i] - 1.0, x[i]) for i in range(n)]


def c1_no_lookahead():
    """The panel state at bar b uses only bars with open_ts <= traded open_ts:
    truncating every confirm asset after b leaves the state identical."""
    n = 120
    rng = np.random.default_rng(11)
    panel = mk_panel(_rw(rng, n, 100, 0.5), _rw(rng, n, 50, 0.3),
                     _rw(rng, n, 200, 0.4))
    full = E._panel_state(panel, "BTCUSDT", TF, CFG)
    k = 80
    panel2 = {s_: df.iloc[:k + 1].reset_index(drop=True)
              for s_, df in panel.items()}
    trunc = E._panel_state(panel2, "BTCUSDT", TF, CFG)
    ok = all(np.array_equal(a[:k + 1], b) for a, b in zip(full, trunc))
    check("C1 panel state identical on the prefix (no lookahead)", ok)


def c2_determinism():
    n = 150
    rng = np.random.default_rng(5)
    panel = mk_panel(_rw(rng, n, 100, 0.5), _rw(rng, n, 50, 0.3),
                     _rw(rng, n, 200, 0.4))
    o1 = E.run_symbol(panel, "BTCUSDT", TF, CFG, cost="zero")
    o2 = E.run_symbol(panel, "BTCUSDT", TF, CFG, cost="zero")
    check("C2 two runs identical",
          np.array_equal(o1["eq"], o2["eq"])
          and len(o1["trades"]) == len(o2["trades"]))


if __name__ == "__main__":
    for fn in (a1_confirmation_veto, a2_confirmation_pass_and_entry,
               a3_others_threshold, a4_stale_veto, a5_episode_no_reentry,
               a6_ten_bar_low_exit, a7_stop_two_atr_with_gap, a8_max_hold,
               a9_short_mirror, b1_identity, c1_no_lookahead, c2_determinism):
        fn()
    print(f"\n{PASS} PASS, {FAIL} FAIL")
    raise SystemExit(1 if FAIL else 0)
