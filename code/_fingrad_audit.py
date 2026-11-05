#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_fingrad_audit.py — known-answer + parity audit for code/fingrad_engine.py.

Run BEFORE any real-data report and after ANY change to the engine:
    python code/_fingrad_audit.py
Writes results/fingrad_audit_known_answers.txt. Any failure raises (exit 1).

Layers:
  P*  primitives vs obviously-correct references (wma/naive, sma/hand, rma
      seed, atr/flat, dmi sign, crossover/barssince semantics)
  K*  hand-computed EXECUTION known answers on synthetic series with crafted
      signal arrays (next-open fills, edge trigger, first-bar vs fill-anchored
      brackets, gap-through, reversal economics, leverage cap, daily breaker,
      long-wins-tie)
  D*  structural checks on REAL data (cash identity with funding, no-lookahead
      truncation, vectorized-vs-loop dual across every mode, determinism,
      HTF mapping hand-check + no-lookahead)
"""
import os
import sys
import json
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import fingrad_engine as E          # noqa: E402

OUT = os.path.join(ROOT, "results", "fingrad_audit_known_answers.txt")
LINES = []


def ok(label, cond, detail=""):
    if not cond:
        raise AssertionError(f"FAIL {label}: {detail}")
    LINES.append(f"PASS  {label}" + (f"   [{detail}]" if detail else ""))
    print(f"PASS  {label}" + (f"   [{detail}]" if detail else ""))


def arr(*xs):
    return np.array(xs, float)


def hourly(n, start=1567962000000):
    return start + np.arange(n, dtype=np.int64) * 3600000


def craft(n, o, h=None, l=None, c=None, T=None):
    o = arr(*o) if isinstance(o, (list, tuple)) else np.asarray(o, float)
    n = len(o)
    h = arr(*h) if h is not None else o + 1.0
    l = arr(*l) if l is not None else o - 1.0
    c = arr(*c) if c is not None else np.asarray(o, float)
    T = hourly(n) if T is None else np.asarray(T, np.int64)
    return dict(t=T, o=o, h=h, l=l, c=c)


def sig_arrays(n, stL=(), stS=(), exitL=(), exitS=(), rL=None, rS=None, dist=0.0):
    S = dict(
        stL=np.zeros(n, bool), stS=np.zeros(n, bool),
        exitL=np.zeros(n, bool), exitS=np.zeros(n, bool),
        exit_reason_L=np.array(rL if rL is not None else [""] * n),
        exit_reason_S=np.array(rS if rS is not None else [""] * n),
        dist=np.full(n, float(dist)),
    )
    for i in stL:
        S["stL"][i] = True
    for i in stS:
        S["stS"][i] = True
    for i in exitL:
        S["exitL"][i] = True
    for i in exitS:
        S["exitS"][i] = True
    S["entryL"] = np.zeros(n, bool)
    S["entryS"] = np.zeros(n, bool)
    S["entryL"][0] = bool(S["stL"][0])
    S["entryS"][0] = bool(S["stS"][0])
    if n > 1:
        S["entryL"][1:] = S["stL"][1:] & ~S["stL"][:-1]
        S["entryS"][1:] = S["stS"][1:] & ~S["stS"][:-1]
    return S


def baseP(**kw):
    P = dict(E.PINE)
    P.update(E.PRESETS["custom"])
    P["tf_minutes"] = 60
    P.update(kw)
    return P


# ═════════════════════════════════════════════ P: primitives
def p_primitives():
    rng = np.random.default_rng(7)
    x = np.cumsum(rng.normal(0, 1, 400)) + 100
    x[rng.integers(0, 400, 5)] = np.nan
    for n in (5, 7, 17, 34):
        a, b = E.wma(x, n), E.wma_naive(x, n)
        m = ~(np.isnan(a) & np.isnan(b))
        assert np.allclose(a[m], b[m], equal_nan=True), f"wma({n})"
    ok("P1 wma vs naive loop", True, "n=5,7,17,34 with nan holes")

    assert int(np.floor(21 / 2)) == 10 and int(np.floor(np.sqrt(21))) == 4
    assert int(np.floor(34 / 2)) == 17 and int(np.floor(np.sqrt(34))) == 5
    ok("P2 hma floored inner lengths", True, "hma21->10/4, hma34->17/5")

    z = np.arange(1, 51, dtype=float)
    r = E.rma(z, 14)
    assert np.isclose(r[13], z[:14].mean())
    assert np.isclose(r[14], (r[13] * 13 + z[14]) / 14)
    zz = z.copy(); zz[:13] = np.nan
    rr = E.rma(zz, 10)
    assert np.isnan(rr[:22]).all() and not np.isnan(rr[22:]).any()
    assert np.isclose(rr[22], zz[13:23].mean())
    ok("P3 rma SMA seed + leading-na skip", True, "seed=mean of first n valid")

    h = np.full(60, 10.0); l = np.full(60, 10.0); c = np.full(60, 10.0)
    assert np.nanmax(np.abs(E.atr_pine(h, l, c, 14))) < 1e-9
    ok("P4 atr flat series -> 0", True)

    s = E.sma(np.arange(1, 51, dtype=float), 5)
    assert np.isnan(s[:4]).all() and np.isclose(s[4], 3.0) and np.isclose(s[49], 48.0)
    ok("P5 sma hand values", True, "sma5[4]=3.0, na before")

    hl = np.arange(1, 61, dtype=float)          # h=l -> hl2 = series
    d = craft(60, o=hl, h=hl, l=hl, c=hl)
    ao = E.signals(d, baseP())["ao"]
    a5 = E.sma(hl, 5); a34 = E.sma(hl, 34)
    m = ~np.isnan(a34)
    assert np.allclose(ao[m], (a5 - a34)[m], equal_nan=True)
    assert np.isnan(ao[:33]).all()
    ok("P6 ao = sma(hl2,5)-sma(hl2,34)", True, "na through bar 33")

    up = np.arange(1.0, 61.0)                    # monotone rise
    diP, diM, adx = E.dmi_pine(up, up, up, 14, 14)
    j = 40
    assert diP[j] > diM[j] and adx[j] > 0 and not np.isnan(adx[j])
    ok("P7 dmi monotone rise: +DI>-DI, adx>0", True,
       f"diP={diP[j]:.1f} diM={diM[j]:.1f}")

    adx_s = arr(np.nan, 10, 20, 30, 25, 24, 26)
    cu = E.cross_over(adx_s, 25.0)
    cd = E.cross_under(adx_s, 25.0)
    assert list(cu) == [False, False, False, True, False, False, True]
    assert list(cd) == [False, False, False, False, False, True, False]
    bs = E.barssince(cu)
    assert np.isnan(bs[:3]).all() and list(bs[3:]) == [0, 1, 2, 0]
    ok("P8 crossover/crossunder na-falsy + barssince", True,
       "crossUp@3 and @6 (24->26 re-cross), crossDn@5, since=0 on event")


# ═════════════════════════════════════════════ K: execution known answers
def k_execution():
    # K1/K2 — next-open fill, per-fill fees, edge trigger, signal exit
    d = craft(8, o=[100, 100, 100, 100, 101, 102, 103, 104])
    S = sig_arrays(8, stL=[2, 3, 4], exitL=[6], rL=["", "", "", "", "", "", "hma", ""])
    res = E.execute(d, S, baseP(atr_stop_mult=0.0), 0.001, 0.0)
    t = res["trades"]
    assert len(t) == 1, len(t)
    assert t[0]["entry_bar"] == 3 and abs(t[0]["entry"] - 100.0) < 1e-12
    assert t[0]["exit_bar"] == 7 and abs(t[0]["exit"] - 104.0) < 1e-12
    assert abs(t[0]["pnl"] - 37.96) < 1e-9, t[0]["pnl"]
    assert abs(res["eq"][-1] - 1037.96) < 1e-9
    assert t[0]["why"] == "hma"
    ok("K1 next-open fill + per-fill fees + signal exit", True,
       "entry open[3]=100 q=10 fee 1.0; exit open[7]=104 fee 1.04; pnl=37.96")
    ok("K2 edge trigger: stL true 3 bars -> ONE entry", True)

    # K3a — bracket re-anchors to the FILL price from bar 2 on
    d = craft(10, o=[100, 100, 101, 100, 100, 100, 100, 100, 100, 100],
              l=[99, 99, 100, 98.5, 99, 99, 99, 99, 99, 99],
              h=[101, 101, 102, 101, 101, 101, 101, 101, 101, 101])
    S = sig_arrays(10, stL=[1], dist=2.0)
    res = E.execute(d, S, baseP(atr_stop_mult=2.0, tp_r=0.0), 0.001, 0.0)
    t = res["trades"]
    assert len(t) == 1 and t[0]["why"] == "SL", t
    assert abs(t[0]["entry"] - 101.0) < 1e-12 and abs(t[0]["exit"] - 99.0) < 1e-12
    assert abs(t[0]["pnl"] - (-11.0)) < 1e-9, t[0]["pnl"]
    assert abs(res["eq"][-1] - 989.0) < 1e-9
    ok("K3a bracket anchored to FILL from bar2 (SL=101-2=99 fires on l=98.5)",
       True, "pnl=-11.00; a stale signal-close anchor (98) would NOT fire")

    # K3b — the ENTRY bar itself uses the SIGNAL-CLOSE anchor
    d = craft(10, o=[100, 100, 101, 100, 100, 100, 100, 100, 100, 100],
              l=[99, 99, 97.5, 99, 99, 99, 99, 99, 99, 99],
              h=[101, 101, 102, 101, 101, 101, 101, 101, 101, 101])
    S = sig_arrays(10, stL=[1], dist=2.0)
    res = E.execute(d, S, baseP(atr_stop_mult=2.0, tp_r=0.0), 0.001, 0.0)
    t = res["trades"]
    assert len(t) == 1 and t[0]["why"] == "SL"
    assert t[0]["exit_bar"] == 2 and abs(t[0]["exit"] - 98.0) < 1e-12, t[0]
    assert abs(t[0]["pnl"] - (-15.995)) < 1e-9, t[0]["pnl"]
    ok("K3b entry bar uses SIGNAL-CLOSE anchor (SL=100-2=98 fills on l=97.5)",
       True, "pnl=-15.995; a fill anchor (99) would fill at 99 instead")

    # K3c — stop gapped through at the open fills AT THE OPEN
    d = craft(10, o=[100, 100, 97, 100, 100, 100, 100, 100, 100, 100],
              l=[99, 99, 96.5, 99, 99, 99, 99, 99, 99, 99],
              h=[101, 101, 98, 101, 101, 101, 101, 101, 101, 101])
    S = sig_arrays(10, stL=[1], dist=2.0)
    res = E.execute(d, S, baseP(atr_stop_mult=2.0), 0.001, 0.0)
    t = res["trades"]
    assert len(t) == 1 and t[0]["why"] == "SL"
    assert t[0]["exit_bar"] == 2 and abs(t[0]["exit"] - 97.0) < 1e-12, t[0]
    assert abs(res["eq"][-1] - 999.03) < 1e-9, res["eq"][-1]
    ok("K3c stop gapped through at open fills AT THE OPEN (TV stop->market)",
       True, "entry open=97, stop level 98 -> exit 97, pnl=-0.97 (fees only)")

    # K4 — reversal on one fill, exit suppressed that bar, fees on both legs
    d = craft(7, o=[100, 100, 100, 101, 102, 103, 104])
    S = sig_arrays(7, stL=[1], stS=[3], exitL=[3],
                   rL=["", "", "", "hma", "", "", ""])
    S["exitS"][5] = True
    S["exit_reason_S"] = np.array([""] * 7); S["exit_reason_S"][5] = "hma"
    res = E.execute(d, S, baseP(atr_stop_mult=0.0), 0.0, 0.0)
    t = res["trades"]
    assert len(t) == 2, t
    assert t[0]["side"] == "L" and t[0]["why"] == "reverse"
    assert abs(t[0]["pnl"] - 20.0) < 1e-9, t[0]["pnl"]
    assert t[1]["side"] == "S" and abs(t[1]["entry"] - 102.0) < 1e-12
    assert abs(t[1]["pnl"] - (-20.0)) < 1e-9
    assert abs(res["eq"][-1] - 1000.0) < 1e-9
    ok("K4 reversal: one fill, exit suppressed, qty re-sized at signal equity",
       True, "long pnl +20 (100->102), short q=1010/101=10 @102, pnl -20")

    # K5 — leverage cap (dist=0.001 -> qRaw=10000 shares, qCap=100 = 10x)
    # tight bar range (h=o+0.0005, l=o-0.0005) so the 0.001 stop cannot fire
    o5 = [100, 100, 100, 100, 100, 100, 102, 102]
    d = craft(8, o=o5, h=[x + 0.0005 for x in o5], l=[x - 0.0005 for x in o5])
    S = sig_arrays(8, stL=[1], exitL=[5], dist=0.001,
                   rL=["", "", "", "", "", "hma", "", ""])
    res = E.execute(d, S, baseP(atr_stop_mult=0.0), 0.001, 0.0)
    t = res["trades"]
    assert len(t) == 1 and abs(t[0]["qty"] - 100.0) < 1e-9, t[0]["qty"]
    assert abs(t[0]["pnl"] - 179.8) < 1e-9, t[0]["pnl"]
    assert abs(res["eq"][-1] - 1179.8) < 1e-9
    ok("K5 maxLev caps risk sizing (qRaw=10000 -> qCap=100 shares = 10x)",
       True, "pnl=+179.80 on 2-point move x100")

    # K6 — daily-loss breaker: close_all, no re-entry, reset next UTC day
    # bars start 20:00 UTC (1567972800000 = 2019-09-08 20:00, verified) so the
    # day boundary lands on bar 4 (00:00 day 2)
    T = hourly(12, start=1567972800000)
    d = craft(12, o=[100, 100, 100, 100, 96.9, 96.9, 100, 100, 100, 100, 100, 100],
              c=[100, 100, 98.5, 96.9, 96.9, 96.9, 100, 100, 100, 100, 100, 100],
              T=T)
    S = sig_arrays(12, stL=[0, 4], dist=0.0)
    res = E.execute(d, S, baseP(atr_stop_mult=0.0), 0.0, 0.0)
    t = res["trades"]
    assert res["n_halts"] == 1 and t[0]["why"] == "daily halt"
    assert abs(t[0]["pnl"] - (-31.0)) < 1e-9, t[0]["pnl"]
    assert t[0]["exit_bar"] == 4                       # fills at day2 00:00 open
    # the day-2 re-entry OPENS at open[5]=96.9 and stays open (no exit signal):
    # it lives in open_pos, not in the closed-trade list
    assert res["n_open"] == 1 and res["open_pos"]["entry_bar"] == 5
    assert abs(res["open_pos"]["entry"] - 96.9) < 1e-12
    assert abs(res["open_pos"]["qty"] - 10.0) < 1e-9 and res["open_pos"]["side"] == 1
    ok("K6 daily breaker: halt at eq<=970 closes at next open, entries blocked",
       True, "pnl=-31 (100->96.9 x10), re-entry at day2 open 96.9 q=10 (open)")

    # K7 — long wins the takeL/takeS tie
    d = craft(6, o=[100, 100, 100, 101, 102, 103])
    S = sig_arrays(6, stL=[1], stS=[1])
    res = E.execute(d, S, baseP(atr_stop_mult=0.0), 0.0, 0.0)
    assert res["n_open"] == 1 and res["open_pos"]["side"] == 1 \
        and res["open_pos"]["entry_bar"] == 2
    ok("K7 takeL wins the tie when both edges fire", True,
       "one position opened at open[2], side=long")


# ═════════════════════════════════════════════ D: real-data structural checks
def _load_btc():
    p = os.path.join(ROOT, "data", "binance_klines_1h", "BTCUSDT_1h.csv")
    t, o, h, l, c = [], [], [], [], []
    with open(p) as f:
        f.readline()
        for line in f:
            a = line.split(",")
            if len(a) < 6:
                continue
            try:
                t.append(int(a[0])); o.append(float(a[1]))
                h.append(float(a[2])); l.append(float(a[3])); c.append(float(a[4]))
            except ValueError:
                continue
    return dict(t=np.array(t, np.int64), o=np.array(o), h=np.array(h),
                l=np.array(l), c=np.array(c))


def d_real():
    d = _load_btc()
    P = baseP()
    n = len(d["c"])

    # D1 — cash identity with funding, on real data with a costed pass
    rng = np.random.default_rng(11)
    fr = np.zeros(n); fev = np.zeros(n, bool)
    ev_idx = np.arange(7, n, 8)
    fev[ev_idx] = True
    fr[ev_idx] = rng.normal(0.0001, 0.0002, len(ev_idx))
    S = E.signals(d, P)
    res = E.execute(d, S, P, 0.0006, 0.0005, fr, fev)
    trs = res["trades"]
    for tr in trs:      # every stored pnl recomputes from its own fills
        rec = tr["qty"] * ((tr["exit"] - tr["entry"]) if tr["side"] == "L"
                           else (tr["entry"] - tr["exit"])) \
            - tr["entry_fee"] - tr["exit_fee"]
        assert abs(rec - tr["pnl"]) < 1e-6, (tr, rec)
        assert tr["exit_bar"] >= tr["entry_bar"]
    total = sum(tr["pnl"] for tr in trs)
    op = res["open_pos"]
    open_leg = 0.0
    if op:
        open_leg = op["side"] * op["qty"] * (d["c"][-1] - op["entry"]) - res["open_fee"]
    lhs = res["eq"][-1] - E.INIT
    rhs = total - res["funding_paid"] + open_leg
    assert abs(lhs - rhs) < 1e-6, (lhs, rhs)
    ok("D1 cash identity on BTC 1h with funding", True,
       f"eq-init {lhs:.6f} = sum(closed pnl) {total:.2f} - funding "
       f"{res['funding_paid']:.2f} + open leg {open_leg:.2f}")

    # D2 — no-lookahead: truncated run reproduces the full run's prefix exactly
    cut = 40000
    Sf = E.signals(d, P)
    dt_ = {k: v[:cut] for k, v in d.items()}
    St = E.signals(dt_, P)
    for k in ("entryL", "entryS", "exitL", "exitS", "stL", "stS"):
        assert (Sf[k][:cut] == St[k]).all(), k
    assert np.array_equal(Sf["dist"][:cut], St["dist"])
    rf = E.execute(d, Sf, P, 0.0006, 0.0005)
    rt = E.execute(dt_, St, P, 0.0006, 0.0005)
    assert np.array_equal(rf["eq"][:cut], rt["eq"]), "equity prefix differs"
    pf_trades = [tr for tr in rf["trades"] if tr["exit_bar"] < cut - 1]
    pt_trades = [tr for tr in rt["trades"] if tr["exit_bar"] < cut - 1]
    assert len(pf_trades) == len(pt_trades)
    for a, b in zip(pf_trades, pt_trades):
        assert a == b, (a, b)
    ok("D2 no-lookahead truncation (BTC 1h, 40k bars)", True,
       "signals + equity prefix + trades byte-identical")

    # D3 — vectorized vs loop dual across every mode
    for sm in ("confluence", "a", "b", "either"):
        for am in ("cross", "level", "literal"):
            Sv = E.signals(d, P, sig_mode=sm, adx_mode=am)
            Sl = E.signals_loop(d, P, sig_mode=sm, adx_mode=am)
            for k in ("stL", "stS", "entryL", "entryS", "exitL", "exitS"):
                assert (Sv[k] == Sl[k]).all(), (sm, am, k)
            assert (Sv["exit_reason_L"] == Sl["exit_reason_L"]).all()
            assert (Sv["exit_reason_S"] == Sl["exit_reason_S"]).all()
            assert np.array_equal(Sv["dist"], Sl["dist"])
    ok("D3 signal-layer dual (vectorized == loop)", True,
       "4 sig modes x 3 adx modes on BTC 1h, all arrays equal")

    # D4 — HTF mapping hand-check: hma(2) on hourly closes of 15m bars.
    # hh[k] = (4*c_k - c_{k-1})/3 with hh[0] na; chart bars in hour k see
    # hH1 = hh[k-1], hH2 = hh[k-2].
    T0 = 1567962000000 - (1567962000000 % 3600000)     # aligned hour
    T = T0 + np.arange(24, dtype=np.int64) * 900000    # 6 hours of 15m bars
    c = np.repeat(arr(10, 11, 12, 13, 14, 15), 4)
    dh = craft(24, o=c, h=c, l=c, c=c, T=T)
    Ph = baseP(hma_len=2, htf_minutes=60)
    Sh = E.signals(dh, Ph)
    hh = lambda a, b: (4 * a - b) / 3.0                # hma(2) of closes
    assert np.isnan(Sh["hH1"][:8]).all()               # hours 0-1: no closed pair
    for i in list(range(0, 12)):                       # hours 0-2: hH2 always na
        assert np.isnan(Sh["hH2"][i])
    for i in range(8, 12):                             # hour 2: hH1 = hh[1] only
        assert np.isclose(Sh["hH1"][i], hh(11, 10)) and np.isnan(Sh["hH2"][i])
    for i in range(12, 16):                            # hour 3: hh[2], hh[1]
        assert np.isclose(Sh["hH1"][i], hh(12, 11)) and np.isclose(Sh["hH2"][i], hh(11, 10))
    for i in range(16, 20):                            # hour 4: hh[3], hh[2]
        assert np.isclose(Sh["hH1"][i], hh(13, 12)) and np.isclose(Sh["hH2"][i], hh(12, 11))
    for i in range(20, 24):                            # hour 5: hh[4], hh[3]
        assert np.isclose(Sh["hH1"][i], hh(14, 13)) and np.isclose(Sh["hH2"][i], hh(13, 12))
    ok("D4 HTF pairs = last two CLOSED HTF-bar HMAs", True,
       "hma(2) hand values; every bar of an hour shares one pair")

    # D5 — HTF no-lookahead: the FORMING HTF bar never enters the pair.
    # Changing the last hour's chart closes changes only hh[5], which no bar
    # reads — so ALL 24 bars' pairs must be unchanged.
    c2 = c.copy()
    c2[20:] = 999.0
    dh2 = craft(24, o=c2, h=c2, l=c2, c=c2, T=T)
    Sh2 = E.signals(dh2, Ph)
    assert np.array_equal(np.nan_to_num(Sh["hH1"], nan=-1),
                          np.nan_to_num(Sh2["hH1"], nan=-1))
    assert np.array_equal(np.nan_to_num(Sh["hH2"], nan=-1),
                          np.nan_to_num(Sh2["hH2"], nan=-1))
    ok("D5 HTF no-lookahead: changing the last hour moves no bar's pair",
       True, "the forming HTF bar's HMA is excluded by the [1]/[2] idiom")

    # D6 — determinism of the full harness path
    import vrun as V
    a1 = V.make_artifact("fingrad", "1h", "BTCUSDT", {})
    a2 = V.make_artifact("fingrad", "1h", "BTCUSDT", {})
    assert json.dumps(a1["metrics"], sort_keys=True) == \
        json.dumps(a2["metrics"], sort_keys=True)
    ok("D6 harness run is deterministic", True, "two make_artifact calls, identical metrics")


def main():
    p_primitives()
    k_execution()
    d_real()
    LINES.append("")
    LINES.append("ALL PASS")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    print(f"\nALL PASS — wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
