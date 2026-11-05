"""Decisive tests on the ATR grid: is +862% on SOL alpha, or just leveraged beta?

A long grid that spends most of its life holding inventory in a 45-month crypto
bull run will look excellent for reasons that have nothing to do with the grid.
Three questions decide it, and none of them is "did it make money":

  1. EXPOSURE-MATCHED PASSIVE. What is the grid's average time-weighted
     notional? Buy & hold at exactly that exposure, with the same funding and
     costs. If BH at matched exposure wins, the grid is beta, full stop. The
     obvious 125% benchmark is unfair to the strategy (125% is the PEAK, not the
     average) and the honest comparison is average-vs-average.

  2. WALK-FORWARD. Split each symbol's own history in half. Does the second
     half still work? A parameter-free-looking strategy that only works in the
     first half of a bull market is a regime artifact.

  3. PARAMETER STABILITY. Vary the band multiplier and the level count. If
     neighbouring cells collapse, the headline cell is noise, not a result.

Plus a year-by-year table, because "3/4 green years" hides which year carried it.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import cvrmd_port as P
import grid_audit as G

SYMS = ["SOLUSDT", "BTCUSDT", "ETHUSDT", "XRPUSDT", "SUIUSDT", "HYPEUSDT"]
INIT = G.INIT


def grid_exposure(sym, bars, gate, **kw):
    """The grid's own time-weighted exposure, read from the PRODUCTION
    simulator. An earlier version of this file re-implemented the state machine
    a second time to get the exposure profile, and a drift assertion caught it
    diverging from simulate() by 5% to 963% (963% on SUI). There is exactly one
    implementation of the strategy now, and the benchmark reads from it.
    """
    tr = {}
    eq = G.simulate(bars, sym, gate, track=tr, **kw)
    return eq, tr, tr["expo_curve"]


def bh_at_exposure(sym, bars, avg_notional_frac, fund_on=True):
    """Buy & hold holding `avg_notional_frac` of INITIAL equity as notional for
    the whole window, funding the same notional the grid would have, and paying
    the same taker fee on entry and exit. This is the benchmark that asks
    'would simply being this exposed have produced this result?'.
    """
    C = np.array([b[4] for b in bars])
    T = np.array([b[0] for b in bars], dtype=np.int64)
    notional = INIT * avg_notional_frac
    qty = notional / C[0]
    cash = INIT - notional
    if fund_on:
        fr, fev, _ = G.funding_events(sym, T)
        for i in range(len(C)):
            if fev[i]:
                cash -= qty * C[i] * fr[i]
    entry_fee = notional * G.TAKER_FEE
    exit_fee = qty * C[-1] * G.TAKER_FEE
    cash -= entry_fee + exit_fee
    eq = cash + qty * C[-1]
    path = (INIT - notional - entry_fee) + qty * C
    pk, mdd = path[0], 0.0
    for v in path:
        pk = max(pk, v)
        mdd = max(mdd, (pk - v) / pk)
    return (eq / INIT - 1) * 100, mdd * 100


def main():
    print("=" * 104)
    print("IS THE GRID ALPHA, OR LEVERAGED BETA?  exposure-matched passive, "
          "walk-forward, parameter stability")
    print("=" * 104)

    data = {}
    for s in SYMS:
        if os.path.exists(os.path.join(G.D1M, f"{s}_1m.csv")):
            data[s] = G.load15(s)

    # ---------- 1. exposure-matched passive ----------
    print("\n[1] EXPOSURE-MATCHED PASSIVE — the fair benchmark")
    print("    " + "-" * 100)
    print("    the grid's peak notional is 125% of equity, but that is the")
    print("    all-5-filled instant. the honest comparison is its own average")
    print("    time-weighted exposure, funded and costed identically.")
    print()
    print(f"  {'sym':<9}{'grid net':>10}{'grid DD':>9}{'avg expo':>10}"
          f"{'BH@avg':>9}{'BH@avg DD':>12}{'BH@125%':>10}{'verdict':>21}")
    print("  " + "-" * 100)
    expo_rows = []
    for s, b in data.items():
        gate = G.htf_filter(b)[0]
        eq, tr, expo = grid_exposure(s, b, gate)
        grid_net = (eq / INIT - 1) * 100
        gdd = tr["mdd"]
        avg_e = float(np.mean(expo))
        med_e = float(np.median(expo))
        bh_a, bh_a_dd = bh_at_exposure(s, b, avg_e)
        C = np.array([x[4] for x in b])
        bh125 = (C[-1] / C[0] - 1) * 125
        verdict = (f"ALPHA +{grid_net-bh_a:.0f}pp" if grid_net > bh_a
                   else f"BETA, {bh_a-grid_net:.0f}pp behind")
        expo_rows.append((s, grid_net, gdd, avg_e, bh_a, bh125))
        print(f"  {s:<9}{grid_net:>+9.0f}%{gdd:>8.1f}%{avg_e:>9.2f}x"
              f"{bh_a:>+8.0f}%{bh_a_dd:>11.1f}%{bh125:>+9.0f}%{verdict:>20}")
    print("  " + "-" * 100)
    n_alpha = sum(1 for r in expo_rows if r[1] > r[4])
    print(f"  beats exposure-matched passive: {n_alpha}/{len(expo_rows)}")

    # ---------- 2. walk-forward ----------
    print("\n[2] WALK-FORWARD — split each symbol's OWN history in half")
    print("    " + "-" * 100)
    print(f"  {'sym':<9}{'1st half net':>14}{'2nd half net':>14}"
          f"{'2nd DD':>9}{'2nd n':>8}{'2nd verdict':>22}")
    print("  " + "-" * 100)
    for s, b in data.items():
        gate = G.htf_filter(b)[0]
        mid = len(b) // 2
        g1 = gate.copy()
        g2 = gate.copy()
        g1[mid:] = False          # only the first half may trade
        g2[:mid] = False          # only the second half
        e1 = G.simulate(b[:mid], s, g1[:mid])
        tr2 = {}
        e2 = G.simulate(b[mid:], s, g2[mid:], track=tr2)
        n1 = (e1 / INIT - 1) * 100
        n2 = (e2 / INIT - 1) * 100
        verdict = "works" if n2 > 0 else "DEAD in 2nd half"
        print(f"  {s:<9}{n1:>+13.0f}%{n2:>+13.0f}%{tr2['mdd']:>8.1f}%"
              f"{tr2['fills']:>8}{verdict:>22}")
    print("  " + "-" * 100)
    print("  (each half re-runs with its own gate, so the second half is a true")
    print("   out-of-sample on the SAME 45-month bull tape, not a fresh market)")

    # ---------- 3. parameter stability ----------
    print("\n[3] PARAMETER STABILITY on SOL — band multiplier and level count")
    print("    " + "-" * 100)
    b = data["SOLUSDT"]
    gate = G.htf_filter(b)[0]
    C = np.array([x[4] for x in b])
    base_atr = G.ATR_MULT
    print(f"  {'band mult':<10}{'net':>10}{'DD':>8}   (levels fixed at 5)")
    print("  " + "-" * 100)
    for m in (2.0, 3.0, 4.0, 5.0, 6.0, 8.0):
        G.ATR_MULT = m
        tr = {}
        eq = G.simulate(b, "SOLUSDT", gate, track=tr)
        star = "  <- spec" if m == base_atr else ""
        print(f"  {m:<10.1f}{(eq/INIT-1)*100:>+9.0f}%{tr['mdd']:>7.1f}%{star}")
    G.ATR_MULT = base_atr
    print()
    print(f"  {'levels':<10}{'net':>10}{'DD':>8}   (band fixed at 5.0 ATR)")
    print("  " + "-" * 100)
    base_lv = G.GRID_LEVELS
    for lv in (3, 4, 5, 6, 8):
        G.GRID_LEVELS = lv
        tr = {}
        eq = G.simulate(b, "SOLUSDT", gate, track=tr)
        star = "  <- spec" if lv == base_lv else ""
        print(f"  {lv:<10}{(eq/INIT-1)*100:>+9.0f}%{tr['mdd']:>7.1f}%{star}")
    G.GRID_LEVELS = base_lv
    print("  " + "-" * 100)
    print(f"  buy & hold SOL {(C[-1]/C[0]-1)*100:+.0f}% at 1x, "
          f"{(C[-1]/C[0]-1)*125:+.0f}% at 125% notional")

    # ---------- 4. year by year ----------
    print("\n[4] YEAR-BY-YEAR — which year carried the headline")
    print("    " + "-" * 100)
    print(f"  {'sym':<9}{'yr':<6}{'closed P&L $':>14}{'share of total':>16}")
    print("  " + "-" * 100)
    for s, b in data.items():
        gate = G.htf_filter(b)[0]
        tr = {}
        G.simulate(b, s, gate, track=tr)
        yp = G.year_pnl(tr["closed_pnl"], tr["closed_t"])
        tot = sum(yp.values()) or 1.0
        for yr in sorted(yp):
            share = 100 * yp[yr] / tot
            print(f"  {s if yr == sorted(yp)[0] else '':<9}{yr:<6}"
                  f"{yp[yr]:>+14.0f}{share:>15.0f}%")
    print("  " + "-" * 100)


if __name__ == "__main__":
    main()
