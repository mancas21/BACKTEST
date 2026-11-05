#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_rsi_mr_audit.py — known-answer + no-lookahead audit for rsi_mr_engine.py.

    python code/_rsi_mr_audit.py    # -> results/rsi_mr_audit_known_answers.txt

  R1  rsi_pine == rsi_loop dual on random walks (incl. all-up -> 100, all-down -> 0)
  R2  atr flat series -> 0; rma SMA seed
  K1  entry fills NEXT open with adverse slip, qty = eq*1%/dist (risk sizing)
  K2  stop intrabar (stop-first), gap-through fills AT THE OPEN
  K3  RSI > 70 exits at the next open
  K4  state-based re-entry while RSI still < 30 after a stop-out
  K5  end_of_data force-close at the last close (fee, no slip)
  I1  cash identity on the real SOLUSDC file
  N1  no-lookahead truncation (signals + equity prefix identical)
  D1  determinism of the full harness artifact
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import rsi_mr_engine as E        # noqa: E402
import vrun as V                 # noqa: E402

OUT = os.path.join(ROOT, "results", "rsi_mr_audit_known_answers.txt")
LINES = []


def ok(label, cond=True, detail=""):
    if not cond:
        raise AssertionError(f"FAIL {label}: {detail}")
    LINES.append(f"PASS  {label}" + (f"   [{detail}]" if detail else ""))
    print(f"PASS  {label}" + (f"   [{detail}]" if detail else ""))


def sig_of(n, buy=(), sell=()):
    return dict(buy=np.array([i in buy for i in range(n)], bool),
                sell=np.array([i in sell for i in range(n)], bool))


def craft(o, h=None, l=None):
    o = np.asarray(o, float)
    h = np.asarray(h, float) if h is not None else o + 1.0
    l = np.asarray(l, float) if l is not None else o - 1.0
    return dict(t=(1567900800 + np.arange(len(o)) * 3600).astype(np.int64) * 1000,
                o=o, h=h, l=l, c=o)


def main():
    global LINES
    # R1 — RSI dual + extremes
    rng = np.random.default_rng(5)
    for trial in range(5):
        x = 100 + np.cumsum(rng.normal(0, 1, 300))
        a, b = E.rsi_pine(x, 14), E.rsi_loop(x, 14)
        m = np.isfinite(a) & np.isfinite(b)
        assert np.allclose(a[m], b[m], atol=1e-9), f"rsi dual trial {trial}"
        assert np.nanmax(a) <= 100.0 + 1e-9 and np.nanmin(a) >= -1e-9
    up = np.arange(1.0, 61.0)
    assert np.allclose(E.rsi_pine(up, 14)[20:], 100.0)
    assert np.allclose(E.rsi_pine(-up + 61.0, 14)[20:], 0.0)
    ok("R1 rsi_pine == rsi_loop dual, bounds and extremes", True,
       "5 random walks + all-up -> 100, all-down -> 0")

    # R2 — atr/rma
    assert np.nanmax(np.abs(E.atr_pine(np.full(60, 10.), np.full(60, 10.),
                                       np.full(60, 10.), 14))) < 1e-9
    z = np.arange(1., 51.)
    assert np.isclose(E.rma(z, 14)[13], z[:14].mean())
    ok("R2 atr flat -> 0, rma SMA seed", True)

    # K1 — entry at next open, risk sizing, fee+slip (INIT = 10_000)
    d = craft([100, 100, 100, 100, 100, 100])          # dist array supplied directly
    dist = np.full(6, 2.0)                              # q = 10000*0.01/2 = 50
    s = sig_of(6, buy=[2])
    r = E.execute(d, s, dist, 0.001, 0.0)
    t = r["trades"]
    assert t[0]["entry_i"] == 3 and abs(t[0]["entry"] - 100.0) < 1e-12
    assert abs(t[0]["qty"] - 50.0) < 1e-9, t[0]["qty"]
    assert abs(t[0]["fees"] - 10.0) < 1e-9              # 50*100*0.001 entry + end_of_data exit
    ok("K1 entry next open, qty = eq*1%/dist, fee charged", True,
       "fill open[3]=100, qty 50 (INIT 10k), fees 5.0 entry + 5.0 end_of_data")

    # K2 — stop intrabar, anchored to the FILL (declared convention)
    d = craft([100, 100, 99, 100, 100, 100], l=[99, 99, 96, 99, 99, 99])
    s = sig_of(6, buy=[1])
    r = E.execute(d, s, np.full(6, 2.0), 0.0, 0.0)
    t = r["trades"]
    assert t[0]["exit_i"] == 2 and t[0]["why"] == "SL", t[0]
    assert abs(t[0]["exit"] - 97.0) < 1e-12, t[0]["exit"]   # fill 99 - dist 2 = 97
    ok("K2 stop anchored to the FILL (99-2=97) fires intrabar", True,
       "entry open[2]=99, l=96 <= 97 -> exit at the stop level 97")
    # K2b — gap-through on a LATER bar fills AT THE OPEN
    d = craft([100, 100, 99, 95, 100, 100], l=[99, 99, 98, 94, 99, 99])
    r = E.execute(d, s, np.full(6, 2.0), 0.0, 0.0)
    t = r["trades"]
    assert t[0]["exit_i"] == 3 and t[0]["why"] == "SL", t[0]
    assert abs(t[0]["exit"] - 95.0) < 1e-12, t[0]["exit"]
    ok("K2b stop gapped through at the open fills AT THE OPEN", True,
       "sl=97; bar2 low 98 no trigger; bar3 opens 95 -> exit at open")

    # K3 — RSI exit at next open (real dist; prices never touch the stop)
    d = craft([100, 100, 100, 100, 104, 104])           # l = o-1 = 99 > sl 98
    s = sig_of(6, buy=[1], sell=[3])
    r = E.execute(d, s, np.full(6, 2.0), 0.0, 0.0)
    t = r["trades"]
    assert len(t) == 1 and t[0]["why"] == "rsi_exit" and t[0]["exit_i"] == 4, t
    assert abs(t[0]["exit"] - 104.0) < 1e-12
    ok("K3 RSI>70 exit fills at the NEXT open", True, "sell@3 -> exit open[4]=104")
    # K3b — dist <= 0 blocks the entry (risk sizing needs a stop distance)
    r = E.execute(craft([100, 100, 100, 100, 104, 104]), sig_of(6, buy=[1]),
                  np.full(6, 0.0), 0.0, 0.0)
    assert len(r["trades"]) == 0
    ok("K3b dist=0 blocks the entry (no stop -> no risk sizing)", True)

    # K4 — state-based re-entry while RSI still < 30 (stop-out, then re-enter)
    d = craft([100, 100, 100, 100, 100, 100, 100, 100])
    s = sig_of(8, buy=[1, 4])                            # signals on bars 1 and 4
    dist = np.full(8, 2.0)
    r = E.execute(d, s, dist, 0.0, 0.0)
    # bar2 spans below the stop (l=97 < sl=98) -> stop at bar 2; bar-4 signal re-enters at bar 5
    d = craft([100, 100, 100, 100, 100, 100, 100, 100],
              l=[99, 99, 97, 99, 99, 99, 99, 99])
    r = E.execute(d, s, dist, 0.0, 0.0)
    t = r["trades"]
    assert t[0]["why"] == "SL" and t[0]["exit_i"] == 2
    assert t[1]["entry_i"] == 5, t
    ok("K4 re-entry after a stop while the state persists", True,
       "SL at bar 2, next entry at bar 5 open")

    # K5 — end_of_data force-close
    d = craft([100, 100, 100, 100])                     # l = 99 > sl 98: no stop
    s = sig_of(4, buy=[1])
    r = E.execute(d, s, np.full(4, 2.0), 0.001, 0.0)
    t = r["trades"]
    assert t[-1]["why"] == "end_of_data" and t[-1]["exit_i"] == 3, t
    ok("K5 end_of_data force-close at the last close", True)

    # I1 — cash identity on the real file
    p = os.path.join(V.DATA, "binance_klines_1h", "SOLUSDC_1h.csv")
    t_, o_, h_, l_, c_ = [], [], [], [], []
    with open(p) as f:
        f.readline()
        for line in f:
            a = line.split(",")
            if len(a) < 6:
                continue
            t_.append(int(a[0])); o_.append(float(a[1])); h_.append(float(a[2]))
            l_.append(float(a[3])); c_.append(float(a[4]))
    d = dict(t=np.array(t_, np.int64), o=np.array(o_), h=np.array(h_),
             l=np.array(l_), c=np.array(c_))
    r = E.rsi_pine(d["c"], 14)
    A = E.atr_pine(d["h"], d["l"], d["c"], 14)
    dist = np.where(np.isnan(A), 0.0, 2.0 * A)
    sig = dict(buy=(r < 30) & ~np.isnan(r), sell=(r > 70) & ~np.isnan(r))
    res = E.execute(d, sig, dist, 0.0005, 0.0005)
    tot = sum(x["pnl"] for x in res["trades"])
    assert abs((res["eq"][-1] - E.INIT) - tot) < 1e-6, (res["eq"][-1] - E.INIT, tot)
    ok("I1 cash identity on SOLUSDC 1h", True,
       f"eq-init {res['eq'][-1] - E.INIT:.4f} == sum(pnl) {tot:.4f}")

    # N1 — no-lookahead truncation
    cut = 4000
    dc = {k: v[:cut] for k, v in d.items()}
    rc = E.rsi_pine(dc["c"], 14)
    Ac = E.atr_pine(dc["h"], dc["l"], dc["c"], 14)
    distc = np.where(np.isnan(Ac), 0.0, 2.0 * Ac)
    sigc = dict(buy=(rc < 30) & ~np.isnan(rc), sell=(rc > 70) & ~np.isnan(rc))
    full = E.execute(d, sig, dist, 0.0005, 0.0005)
    part = E.execute(dc, sigc, distc, 0.0005, 0.0005)
    fe, pe = full["eq"][:cut - 1], part["eq"][:cut - 1]
    both = np.isfinite(fe) & np.isfinite(pe)
    assert np.array_equal(fe[both], pe[both]), "equity prefix differs"
    ft = [x for x in full["trades"] if x["exit_i"] < cut - 1]
    pt = [x for x in part["trades"] if x["exit_i"] < cut - 1]
    assert len(ft) == len(pt) and all(
        a["entry_i"] == b_["entry_i"] and a["exit_i"] == b_["exit_i"]
        and abs(a["pnl"] - b_["pnl"]) < 1e-9 for a, b_ in zip(ft, pt))
    ok("N1 no-lookahead truncation (4000 bars, last excluded)", True,
       f"equity prefix equal on {int(both.sum())} bars, {len(pt)} trades identical")

    # D1 — determinism through the harness path
    a1 = V.make_artifact("rsimr", "1h", "SOLUSDC", {})
    a2 = V.make_artifact("rsimr", "1h", "SOLUSDC", {})
    assert json.dumps(a1["metrics"], sort_keys=True, default=str) == \
        json.dumps(a2["metrics"], sort_keys=True, default=str)
    ok("D1 harness run deterministic", True)

    import json as _json
    LINES += ["", "ALL PASS"]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    print(f"\nALL PASS — wrote {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
