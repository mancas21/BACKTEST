"""grid_param.py — is the grid's edge real, or is it leverage?

WHY THIS TEST
-------------
The headline numbers (SOL +23,336%, XRP +70,671%) are the SAME thin edge
compounded, because each grid sizes off current equity. Return therefore
measures how hard the strategy levered a rising asset, not whether the grid has
an edge. The parameter sweep makes that unmistakable: on the truncated cache,
band 2.0 gave +3985% and band 8.0 gave +28%, which reads like "tune the band"
and is actually "tune the leverage".

The discriminating question is PROFIT FACTOR per cell, not return per cell:

  - PF flat across cells  -> there is no parameter-dependent edge. The
    strategy's edge is whatever it is, and the parameter only changes exposure.
    Deployment should pick a cell on DRAWDOWN grounds and stop.
  - PF peaks in a band    -> the parameters matter, and that peak is a real
    (if fragile) discovery worth its own walk-forward test.

Second question: is the return just beta? Buy & hold at the grid's OWN measured
average exposure, over the same window, is the only benchmark that does not
flatter either side. grid_bench.py did this; this re-runs it on the CORRECTED
full Binance 15m data rather than the truncated cache.

THIRD question, because it decides venue: PF under MAKER vs TAKER fees. A
post-only strategy's edge is mostly its fee tier, and that has to be stated as a
number rather than assumed.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import grid_audit as GA
import paper_grid as PG

SYMS = ["SOLUSDT", "BTCUSDT", "ETHUSDT", "XRPUSDT"]


def metrics(tr):
    cp = tr.get("closed_pnl") or []
    w = [x for x in cp if x > 0]
    l = [x for x in cp if x <= 0]
    pf = (sum(w) / abs(sum(l))) if l and sum(l) != 0 else (np.inf if w else 0.0)
    wr = 100.0 * len(w) / max(len(cp), 1)
    return pf, wr, len(cp)


def bh_matched(bars, tr):
    """Buy & hold at the grid's own average time-weighted exposure."""
    C = np.array([b[4] for b in bars])
    expo = tr["expo_curve"]
    avg = float(np.mean(expo))
    notional = GA.INIT * avg
    qty = notional / C[0]
    cash = GA.INIT - notional
    eq = cash + qty * C[-1]
    path = GA.INIT - notional + qty * C
    pk, mdd = path[0], 0.0
    for v in path:
        pk = max(pk, v)
        mdd = max(mdd, (pk - v) / pk)
    return (eq / GA.INIT - 1) * 100, mdd * 100, avg


def run(bars, sym, gate, atr_mult=None, levels=None, leg_fee=None):
    """Run the validated engine with optional parameter overrides.

    grid_audit.simulate reads ATR_MULT and GRID_LEVELS as module globals and
    takes no levels argument, so a sweep must set and restore them rather than
    pass kwargs that do not exist. Every override is restored in a finally, or a
    mid-sweep exception would leave the module in a wrong state for every later
    run in the same process -- including the paper bot.
    """
    m_old, l_old = GA.ATR_MULT, GA.GRID_LEVELS
    try:
        if atr_mult is not None:
            GA.ATR_MULT = atr_mult
        if levels is not None:
            GA.GRID_LEVELS = levels
        tr = {}
        eq = GA.simulate(bars, sym, gate, track=tr,
                         leg_fee=leg_fee if leg_fee is not None else GA.MAKER_FEE,
                         flat_fee=GA.TAKER_FEE,
                         leg_slip=GA.MAKER_SLIP, flat_slip=0.0005,
                         funding=True)
        return eq, tr
    finally:
        GA.ATR_MULT, GA.GRID_LEVELS = m_old, l_old


def main():
    print("=" * 104)
    print("IS THE GRID'S EDGE REAL?  PF per parameter cell, on CORRECTED full "
          "Binance 15m data")
    print("=" * 104)

    data = {}
    for s in SYMS:
        p = PG.csv_path(s, "15m")
        if os.path.exists(p):
            b = PG.load_bars(p)
            if len(b) > 10000:
                data[s] = (b, PG.gate_fixed(b))

    if not data:
        print("no 15m data; run paper_grid.py --once first")
        return

    # ---------- 1. PF by band multiplier, per symbol ----------
    print("\n[1] BAND MULTIPLIER — return scales with exposure, but does PF?")
    print("    " + "-" * 100)
    bands = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
    print(f"    {'sym':<9}{'band':>6}{'net%':>11}{'DD%':>7}{'PF':>7}{'WR%':>6}"
          f"{'n':>7}{'avgExpo':>9}{'BH@expo%':>11}{'BHdd%':>8}")
    print("    " + "-" * 100)
    pf_by_band = {}
    for s, (b, g) in data.items():
        for m in bands:
            eq, tr = run(b, s, g, atr_mult=m)
            pf, wr, n = metrics(tr)
            net = (eq / GA.INIT - 1) * 100
            bh, bhdd, avg = bh_matched(b, tr)
            pf_by_band.setdefault(m, []).append(pf)
            star = "  <- spec" if m == GA.ATR_MULT else ""
            print(f"    {s:<9}{m:>6.1f}{net:>+10.0f}%{tr['mdd']:>6.1f}%{pf:>7.2f}"
                  f"{wr:>5.0f}%{n:>7,}{avg:>9.2f}{bh:>+10.0f}%{bhdd:>7.0f}%{star}")
        print("    " + "-" * 100)

    print("\n    PF spread across bands (the whole question in one line):")
    print(f"    {'band':>6}{'median PF':>12}{'min':>8}{'max':>8}{'spread':>9}")
    for m in bands:
        v = np.array([x for x in pf_by_band[m] if np.isfinite(x)])
        if len(v):
            print(f"    {m:>6.1f}{np.median(v):>12.2f}{v.min():>8.2f}"
                  f"{v.max():>8.2f}{v.max()-v.min():>9.2f}")
    med = [np.median([x for x in pf_by_band[m] if np.isfinite(x)]) for m in bands]
    lo, hi = min(med), max(med)
    print()
    if hi - lo < 0.10:
        print(f"    VERDICT: median PF varies only {hi-lo:.2f} across a 4x range of")
        print("    band width. The band is a LEVERAGE knob, not an edge knob.")
        print("    There is no parameter to tune. Pick the cell on drawdown and stop.")
    else:
        print(f"    VERDICT: median PF varies {hi-lo:.2f} across band width — the")
        print("    parameters matter. The peak cell needs its own walk-forward test.")

    # ---------- 2. PF by level count ----------
    print("\n[2] LEVEL COUNT — more levels is more leverage in a trench coat")
    print("    " + "-" * 100)
    lv = [3, 4, 5, 6, 8, 10]
    print(f"    {'sym':<9}{'levels':>7}{'net%':>11}{'DD%':>7}{'PF':>7}{'WR%':>6}"
          f"{'n':>7}{'avgExpo':>9}")
    print("    " + "-" * 100)
    pf_by_lv = {}
    for s, (b, g) in data.items():
        for L in lv:
            eq, tr = run(b, s, g, levels=L)
            pf, wr, n = metrics(tr)
            net = (eq / GA.INIT - 1) * 100
            avg = float(np.mean(tr["expo_curve"]))
            pf_by_lv.setdefault(L, []).append(pf)
            star = "  <- spec" if L == GA.GRID_LEVELS else ""
            print(f"    {s:<9}{L:>7}{(net):>+10.0f}%{tr['mdd']:>6.1f}%{pf:>7.2f}"
                  f"{wr:>5.0f}%{n:>7,}{avg:>9.2f}{star}")
        print("    " + "-" * 100)
    print()
    print(f"    {'levels':>7}{'median PF':>12}{'min':>8}{'max':>8}")
    for L in lv:
        v = np.array([x for x in pf_by_lv[L] if np.isfinite(x)])
        if len(v):
            print(f"    {L:>7}{np.median(v):>12.2f}{v.min():>8.2f}{v.max():>8.2f}")

    # ---------- 3. maker vs taker ----------
    print("\n[3] FEE TIER — how much of the edge is the maker fee?")
    print("    " + "-" * 100)
    print(f"    {'sym':<9}{'maker net%':>12}{'maker PF':>10}"
          f"{'taker net%':>12}{'taker PF':>10}{'edge kept':>12}")
    print("    " + "-" * 100)
    for s, (b, g) in data.items():
        eq_m, tr_m = run(b, s, g)
        eq_t, tr_t = run(b, s, g, leg_fee=GA.TAKER_FEE)
        pfm, _, _ = metrics(tr_m)
        pft, _, _ = metrics(tr_t)
        nm = (eq_m / GA.INIT - 1) * 100
        nt = (eq_t / GA.INIT - 1) * 100
        kept = 100 * (pft - 1) / (pfm - 1) if pfm > 1 else float("nan")
        print(f"    {s:<9}{nm:>+11.0f}%{pfm:>10.2f}{nt:>+11.0f}%{pft:>10.2f}"
              f"{kept:>11.0f}%")
    print("    " + "-" * 100)
    print("    'edge kept' = share of the maker-fee profit factor above 1.0 that")
    print("    survives taker fees. Near 0% means the strategy only works because")
    print("    it posts passive orders, which is venue-specific and not portable.")


if __name__ == "__main__":
    main()