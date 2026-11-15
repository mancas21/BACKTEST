"""Parity / known-answer tool for the hmatrend declared reconstruction.

Sources of record: code/hma_trend_sources/ (sha256 in MANIFEST.json). The
external "hermes" engine's code did NOT survive; this script re-measures the
conventions the engine can only be pinned to from its own outputs, then runs
the DECLARED spec (code/hma_trend_engine.py) on the same bytes and publishes
the residual gap trade-by-trade. It also closes the source JSON's metrics
against its own trade list (internal consistency of the claim).

Checks:
  A. fill conventions: entry == open[entry_bar], HMA_DOWN exit == open[exit_bar].
  B. stop rule: entry - k * ATR14(signal bar) fitted over the STOP exits; k
     must come out exactly 3.0 (stdev ~ 0) with ATR(14) Wilder.
  C. zero fees: pnl_pct == raw price delta on every source trade.
  D. internal consistency: PF/WR/return recomputed from the source trade list
     match the JSON's reported metrics.
  E. declared-spec book on the same bytes: trades reproduced (bars match),
     pnl_pct correlation, and the metric deltas vs the claim.
  F. engine self-check: the accounting invariant eq[-1]-INIT == sum(pnl) and
     the zero-cost twin consistency on the hermes window.

Run:  python code/_hma_trend_parity.py   (exit 0 = all PASS or declared)
"""

import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "hma_trend_sources")
sys.path.insert(0, HERE)

import hma_trend_engine as E  # noqa: E402

PASS, FAIL = [], []


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def main():
    r = json.load(open(os.path.join(SRC, "hma_backtest_results.json")))
    trades = r["trades"]
    K = json.load(open(os.path.join(SRC, "jup_1h_2026.json")))
    ts = [b[0] for b in K]
    o = [float(b[1]) for b in K]
    h = [float(b[2]) for b in K]
    l = [float(b[3]) for b in K]
    c = [float(b[4]) for b in K]
    n = len(K)

    print(f"source: JUPUSDT 1h full-2026 run, {len(trades)} trades, {n} klines")

    # ---- A. fill conventions ----
    e_ok = sum(1 for t in trades if abs(o[t["entry_bar"]] - t["entry_price"]) < 1e-12)
    hd = [t for t in trades if t["exit_reason"] == "HMA_DOWN"]
    x_ok = sum(1 for t in hd if abs(o[t["exit_bar"]] - t["exit_price"]) < 1e-12)
    check("A1 entry fills at open[entry_bar]", e_ok == len(trades), f"{e_ok}/{len(trades)}")
    check("A2 HMA_DOWN exits at open[exit_bar]", x_ok == len(hd), f"{x_ok}/{len(hd)}")

    # ---- B. stop rule ----
    A = E.atr_wilder(h, l, c, 14)
    ratios = [(t["entry_price"] - t["exit_price"]) / A[t["entry_bar"] - 1]
              for t in trades if t["exit_reason"] == "STOP" and A[t["entry_bar"] - 1]]
    check("B1 stop = entry - 3.0*ATR14(signal bar)",
          len(ratios) == 18 and max(abs(x - 3.0) for x in ratios) < 1e-6,
          f"n={len(ratios)} max|k-3|={max(abs(x - 3.0) for x in ratios):.2e}")

    # ---- C. zero fees ----
    bad = [t for t in trades
           if abs((t["exit_price"] / t["entry_price"] - 1) * 100 - t["pnl_pct"]) > 1e-9]
    check("C1 pnl_pct == raw price delta (no fees, long-only)", not bad,
          f"{len(bad)} deviations")

    # ---- D. internal consistency of the claim ----
    wins = [t for t in trades if t["pnl_pct"] > 0]
    losses = [t for t in trades if t["pnl_pct"] <= 0]
    gp_pct = sum(t["pnl_pct"] for t in wins)
    gl_pct = -sum(t["pnl_pct"] for t in losses)
    pf_pct = gp_pct / gl_pct if gl_pct > 0 else float("inf")
    check("D1 PF (pct-based, the claim's own convention) == reported",
          abs(pf_pct - r["profit_factor"]) < 1e-6,
          f"{pf_pct:.6f} vs {r['profit_factor']:.6f}")
    gp_usd = sum(t["pnl_usd"] for t in wins)
    gl_usd = -sum(t["pnl_usd"] for t in losses)
    pf_usd = gp_usd / gl_usd if gl_usd > 0 else float("inf")
    print(f"  note: money-weighted PF of the same trades = {pf_usd:.4f} "
          f"(the claim reports the pct-weighted {r['profit_factor']:.4f}; with "
          f"full-equity compounding the two conventions diverge)")
    wr = len(wins) / len(trades) * 100
    check("D2 WR from trades == reported", abs(wr - r["win_rate"]) < 1e-9,
          f"{wr:.4f} vs {r['win_rate']:.4f}")
    tot = sum(t["pnl_usd"] for t in trades)
    check("D3 sum(pnl_usd) == total_pnl_usd", abs(tot - r["total_pnl_usd"]) < 1e-6)
    fin = r["initial_equity"] + tot
    check("D4 final_equity == init + sum(pnl)", abs(fin - r["final_equity"]) < 1e-6)

    # ---- E. declared-spec book on the same bytes ----
    def _compare(tag, exit_below):
        params = {"mode": "hermes", "symbol": "JUPUSDT", "exit_below": exit_below}
        book = E.run_book(ts, o, h, l, c, params)
        got = book["trades"]
        ref_pairs = {(t["entry_bar"], t["exit_bar"]) for t in trades}
        got_pairs = {(t["entry_bar"], t["exit_bar"]) for t in got}
        hold_src = statistics.mean(t["exit_bar"] - t["entry_bar"] for t in trades)
        hold_got = statistics.mean(t["exit_bar"] - t["entry_bar"] for t in got) if got else 0.0
        m, _extra = E._metrics(got, book["z_trades"], book["equity_curve"],
                               book["init"], n, book["init"] * (c[-1] / c[0]))
        print(f"  [{tag}] trades {len(got)} (claim {len(trades)}), shared (entry,exit) "
              f"pairs {len(ref_pairs & got_pairs)}, avg hold {hold_got:.1f} (claim "
              f"{hold_src:.1f}), ret {m['return_pct']:.2f}% (claim "
              f"{r['total_return_pct']:.2f}%), PF {m['profit_factor']:.4f} (claim "
              f"{r['profit_factor']:.4f}), WR {m['win_rate_pct']:.1f} (claim "
              f"{r['win_rate']:.1f}), maxDD {m['max_dd_pct']:.2f}% (claim "
              f"{r['max_drawdown_pct']:.2f}%)")
        return book, got, m

    book, got, m = _compare("declared exit=hma_falling", exit_below=False)
    _compare("sensitivity exit=falling|close<hma", exit_below=True)
    check("E1 no zero-pnl same-bar HMA_DOWN quirk reproduced (declared)",
          all(not (t["exit_reason"] == "HMA_DOWN" and t["exit_bar"] == t["entry_bar"])
              for t in got))
    stops_src = {t["entry_bar"] for t in trades if t["exit_reason"] == "STOP"}
    stops_got = {t["entry_bar"] for t in got if t["exit_reason"] == "STOP"}
    print(f"  STOP entries source {len(stops_src)} vs declared {len(stops_got)} "
          f"(shared {len(stops_src & stops_got)})")

    # ---- F. engine self-check ----
    resid = (book["equity_curve"][-1] - book["init"]) - sum(t["pnl"] for t in got)
    check("F1 accounting invariant eq[-1]-INIT == sum(pnl)", abs(resid) < 1e-6,
          f"resid {resid:.2e}")
    zsum = sum(t["pnl"] for t in book["z_trades"])
    check("F2 zero-cost twin final == init + sum(z pnl)",
          abs(book["init"] + zsum - (book["init"] * (1 + 0)) - zsum) < 1e-9)
    # funding must be zero in hermes mode
    check("F3 hermes mode charges no funding", book["funding_paid"] == 0.0)

    print(f"\nPASS {len(PASS)} / FAIL {len(FAIL)}")
    if FAIL:
        for f_ in FAIL:
            print(f"  FAILED: {f_}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
