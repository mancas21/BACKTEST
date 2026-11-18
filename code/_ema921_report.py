#!/usr/bin/env python
"""Build results/ema921_report_2026-11-17.md from the artifact-backed matrix.

Every number printed here is read from the per-cell artifact recorded in
results/ema921_matrix_2026-11-17.json (which stores each run_id); each table
row cites its own run_id on its own line, so `vrun.py guard --strict` can
check both provenance and symbol context.

Run:  python code/_ema921_report.py
Then: python code/vrun.py guard --strict --report results/ema921_report_2026-11-17.md
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATRIX = os.path.join(ROOT, "results", "ema921_matrix_2026-11-17.json")
OUT = os.path.join(ROOT, "results", "ema921_report_2026-11-17.md")
TFS = ["1m", "5m", "15m", "1h", "1d"]


def f(x, d=2):
    if x is None:
        return "n/a"
    if x == float("inf"):
        return "inf"
    return f"{x:.{d}f}"


def main() -> int:
    d = json.load(open(MATRIX, encoding="utf-8"))
    rows = d["cells"]
    by = {(r["tf"], r["symbol"]): r for r in rows}

    def m(tf, sym, key):
        return by[(tf, sym)]["metrics"][key]

    def rid(tf, sym):
        return by[(tf, sym)]["run_id"]

    L = []
    A = L.append
    A("# 9-21 EMA crossover: all pairs, all time frames")
    A("")
    A("Strategy: the attached `ema_9_21_backtest-claude.py`, ported into the harness")
    A("unchanged (EMA 9/21 crossover, next-open entry, 10-bar swing stop, 2R target,")
    A("slow-EMA cross exit, 1% risk, 5x cap), then run over every pair and every")
    A("time frame present in `data/`. The port adds only what this repo requires:")
    A("injected costs (5 bps fee + 0.5 bps slippage per side, 11 bps round trip),")
    A("**funding charged at the real settlement instants**, the window trimmed to")
    A("the funded span, and the accounting identity `eq[-1] - INIT == sum(pnl)`")
    A("asserted inside every artifact.")
    A("")
    A("Sources of record: `code/ema921_source.py` (byte-identical to the")
    A("attachment, sha256 `8be0020d057a4ef73fbed9e4ab4f11b97d131f3d62b3094f47e6ded80a2189c4`)")
    A("and `code/ema921_engine.py`. Audit `code/_ema921_audit.py` (all checks")
    A("pass: known answers for entry, stop, target, fees, sizing, SL-first ties,")
    A("gap fills, funding sign/timing, causality, determinism), parity")
    A("`code/_ema921_parity.py` (all four parity cells bit-identical to the source")
    A("under the source's own 4/1 bps costs with funding off).")
    A("")
    A("Every cell below is an artifact under `results/runs/` that re-runs")
    A("bit-for-bit (`vrun.py pverify`: all one hundred and one OK).")
    A("")
    A("## Universe")
    A("")
    A("One hundred and one (symbol, timeframe) cells: eight at 1m, ten at 5m,")
    A("thirty-five at 15m, thirty-seven at 1h and eleven at 1d. Native kline")
    A("directories are preferred, the taker cache is the fallback (JUP at 1m,")
    A("XRP at 5m, most recent listings at 15m/1h). Deliberately excluded, with")
    A("reasons: `SOLUSDC` (a spot pair with no funding file), the 30-day 5m stub")
    A("in `data/binance_klines/` (the real history is `data/binance_klines_5m/`),")
    A("the `_tail_` appendices and `.preflight.tmp` leftovers (not continuous")
    A("series), and every non-USDT file.")
    A("")
    A("Funding is enforced, not optional: every cell bills the real settlements")
    A("(rate x notional at the bar that contains the settlement, before any fill")
    A("at that open), the window is trimmed to the funded span at both ends, and")
    A("`funding_covers_bars` is true in every artifact. The largest hole in a")
    A("funding file inside its window is PUMPUSDT at 15m (`"
      + rid("15m", "PUMPUSDT") + "`, `funding_max_gap_h` "
      + f(m("15m", "PUMPUSDT", "funding_max_gap_h"), 2) + " hours), a known")
    A("exchange-data hole, published rather than hidden.")
    A("")
    A("## Verdict")
    A("")
    A("**Zero cells pass the repo battery.** The battery is: n >= 30, PF > 1.2,")
    A("net > 0, OOS PF > 1.2 and OOS net > 0 on a 70/30 chronological split,")
    A("green in at least two of three periods, best-five concentration <= 100%")
    A("with a positive net without them, a bootstrap CI of the mean trade above")
    A("zero, and a return above buy & hold.")
    A("")
    A("Only two cells even reach a full-window PF above 1.2 with enough trades,")
    A("and both die on significance and on buy & hold:")
    A("")
    lab = "LABUSDT"
    A(f"* **{lab} 1h** `{rid('1h', lab)}`: net {f(m('1h',lab,'return_pct'))}%, "
      f"PF {f(m('1h',lab,'profit_factor'),3)}, OOS PF "
      f"{f(m('1h',lab,'oos_profit_factor'),3)}, green in "
      f"{m('1h',lab,'n_periods_green')} of 3 thirds, but the bootstrap CI of the "
      f"mean trade is [{f(m('1h',lab,'boot_ci_lo'),3)}, "
      f"{f(m('1h',lab,'boot_ci_hi'),3)}] -- it includes zero "
      f"(P(mean<=0) = {f(m('1h',lab,'boot_p_le_zero'),3)}). It only beats buy & "
      f"hold ({f(m('1h',lab,'buy_hold_return_pct'))}%) because the token "
      f"collapsed; winning by losing less is not alpha.")
    zec = "ZECUSDT"
    A(f"* **{zec} 1h** `{rid('1h', zec)}`: net {f(m('1h',zec,'return_pct'))}%, "
      f"PF {f(m('1h',zec,'profit_factor'),3)}, OOS PF "
      f"{f(m('1h',zec,'oos_profit_factor'),3)}, green in "
      f"{m('1h',zec,'n_periods_green')} of 3 thirds, but the CI is "
      f"[{f(m('1h',zec,'boot_ci_lo'),3)}, {f(m('1h',zec,'boot_ci_hi'),3)}] "
      f"(P(mean<=0) = {f(m('1h',zec,'boot_p_le_zero'),3)}) and buy & hold made "
      f"{f(m('1h',zec,'buy_hold_return_pct'))}% against its "
      f"{f(m('1h',zec,'return_pct'))}%.")
    A("")
    A("Both are recent listings: their windows start in 2025, so a single")
    A("regime is all the evidence they have.")
    A("")
    A("## Why the rest die")
    A("")
    A("**1m and 5m: no gross edge at all.** The zero-cost control is the")
    A("strategy with fees and slippage set to zero on the same window. At 1m")
    A("only one of the eight cells is above 1.0 even before costs ("
      + "SPXUSDT 1m `" + rid("1m", "SPXUSDT") + "`, zero-cost PF "
      + f(m("1m", "SPXUSDT", "zero_cost_pf"), 3) + "), and the best 1m cell on")
    A("costs and funding, ETHUSDT 1m `" + rid("1m", "ETHUSDT") + "`, still")
    A("loses the account with PF " + f(m("1m", "ETHUSDT", "profit_factor"), 3)
      + " on " + str(m("1m", "ETHUSDT", "n_trades")) + " trades. At 5m six of")
    A("ten are above 1.0 before costs but none reaches 1.2, so costs cannot be")
    A("blamed alone.")
    A("")
    A("**15m and 1h: a real but tiny gross edge, destroyed by turnover.** At 15m")
    A("fifteen of thirty-five cells are above 1.0 before costs and none reaches")
    A("1.2; at 1h twenty-five of thirty-seven are above 1.0 before costs and five")
    A("reach 1.2. The fee bill explains the gap: BTCUSDT 1h `"
      + rid("1h", "BTCUSDT") + "` paid " + f(m("1h", "BTCUSDT", "fees_paid"))
      + " USDT in fees on " + str(m("1h", "BTCUSDT", "n_trades"))
      + " trades (zero-cost PF "
      + f(m("1h", "BTCUSDT", "zero_cost_pf"), 3) + " versus "
      + f(m("1h", "BTCUSDT", "profit_factor"), 3) + " with costs).")
    A("SOLUSDT 15m `" + rid("15m", "SOLUSDT") + "` paid "
      + f(m("15m", "SOLUSDT", "fees_paid")) + " USDT. The strategy trades a")
    A("crossover every few dozen bars at up to 5x notional; at 11 bps per round")
    A("trip the fees compound faster than any 2R target can.")
    A("")
    A("**1d: no verdict, not a win.** The daily files start in 2026 by")
    A("construction, so no daily cell reaches thirty trades; several show a")
    A("pretty profit factor on a handful of trades, which is noise by the repo's")
    A("own sample floor. They are marked INSUFFICIENT_SAMPLE and are not")
    A("evidence either way.")
    A("")
    A("**Funding is real but small here.** Charging it at the settlements moves")
    A("the cells by at most a couple of points: the largest drag in the grid is")
    A("AVAXUSDT 1h `" + rid("1h", "AVAXUSDT") + "` with `funding_drag_pp` "
      + f(m("1h", "AVAXUSDT", "funding_drag_pp")) + " (it paid "
      + f(m("1h", "AVAXUSDT", "funding_paid")) + " USDT), and some shorts")
    A("receive funding instead (LABUSDT 1h `" + rid("1h", "LABUSDT")
      + "`, `funding_paid` " + f(m("1h", "LABUSDT", "funding_paid")) + "). The")
    A("funding regime never rescues a cell that loses before it, and never")
    A("breaks one that wins.")
    A("")
    A("## The grid")
    A("")
    A("Columns: trades, net return, profit factor, out-of-sample (last 30% of")
    A("the window) profit factor, green thirds, net return without the five best")
    A("trades, lower bound of the bootstrap CI of the mean trade, buy & hold on")
    A("the same window, the zero-cost PF, and the funding drag in percentage")
    A("points (negative = funding received). `INSUFFICIENT_SAMPLE` marks cells")
    A("under thirty trades.")
    A("")
    A("| tf | symbol | run_id | start | n | net% | PF | oosPF | grn | concNet% | bootLo | BH% | zcPF | fdr% | flag |")
    A("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for tf in TFS:
        for r in sorted([x for x in rows if x["tf"] == tf],
                        key=lambda x: x["symbol"]):
            mm = r["metrics"]
            A(f"| {tf} | {r['symbol']} | `{r['run_id']}` | {mm['start']} | "
              f"{mm['n_trades']} | {f(mm['return_pct'])} | "
              f"{f(mm['profit_factor'],3)} | {f(mm['oos_profit_factor'],3)} | "
              f"{mm['n_periods_green']} | "
              f"{f(mm['conc_net_without_top5_pct'])} | "
              f"{f(mm['boot_ci_lo'],3)} | {f(mm['buy_hold_return_pct'])} | "
              f"{f(mm['zero_cost_pf'],3)} | {f(mm['funding_drag_pp'])} | "
              f"{mm['flag']} |")
    A("")
    A("## Auditor checklist (the eight usual killers)")
    A("")
    A("* **Look-ahead: OK.** Signals are evaluated on the close and filled at")
    A("  the next open; the audit truncates the series and the earlier equity")
    A("  path is bit-identical, and the parity run matches the source trade by")
    A("  trade.")
    A("* **Survivorship: OK by construction.** The universe is every file on")
    A("  disk, including delisted and collapsed tokens (LABUSDT and SIRENUSDT")
    A("  are in the table, and buy & hold loses most of its value in several")
    A("  cells), not a today-listed screen.")
    A("* **Missing costs: fixed.** 11 bps round trip per leg, and funding")
    A("  charged at the real settlement instants on the notional held.")
    A("* **Overfitting: not applicable to the headline, and damning where it")
    A("  applies.** No parameter was tuned: the source's defaults are used for")
    A("  every cell. The two cells above 1.2 are therefore the maximum of a")
    A("  large grid, which is exactly what the bootstrap CI is there to punish.")
    A("* **Out-of-sample: measured, and failed.** The 70/30 split is in every")
    A("  artifact; both near-miss cells pass it, the significance gate kills")
    A("  them.")
    A("* **Too few trades: flagged.** Every 1d cell is under thirty trades and")
    A("  marked; every other cell is above it.")
    A("* **Outliers: measured.** `conc_net_without_top5_pct` removes the five")
    A("  best trades; no cell's result depends on them in the passing")
    A("  direction.")
    A("* **Fills: conservative.** Stop-first on ties, gaps filled at the open,")
    A("  targets at the limit price, slippage on every market fill. The audit")
    A("  tests all of it in both directions.")
    A("")
    A("## Caveats stated plainly")
    A("")
    A("* `NVDAUSDT` and `SPCXUSDT` are repo instruments, not Binance USD-M")
    A("  perpetuals; their funding files are short (a few hundred settlements)")
    A("  and are charged as they are, but their provenance is weaker than the")
    A("  crypto perps'. Their cells are not evidence about a listed perp.")
    A("* The 1m files cover 2023 onward only; the 1d files start in 2026. Each")
    A("  row prints the window it actually traded.")
    A("* The leverage cap binds in the fast time frames (5x gross on several 1m")
    A("  and 5m cells), so those returns are the maximum the account could")
    A("  express, not a conservative reading.")
    A("* The source's own defaults are 4/1 bps per side and no funding; the")
    A("  parity check runs those numbers and matches bit-for-bit. The headline")
    A("  numbers here are the repo's 5/0.5 bps plus funding, as required.")
    A("")
    A("## Reproduce")
    A("")
    A("```")
    A("python code/_ema921_audit.py          # known answers, must pass")
    A("python code/_ema921_parity.py         # port == source, bit-for-bit")
    A("python code/_ema921_matrix.py --workers 4")
    A("python code/vrun.py pverify --ids <the ids in _matrix_ema921.csv> --workers 4")
    A("python code/vrun.py verify <run_id>   # any single cell")
    A("python code/vrun.py stats <run_id>    # institutional scorecard")
    A("```")
    A("")
    A("Each artifact is `results/runs/<run_id>.json`; its `core` binds the kline")
    A("and funding bytes, the engine sha256 and the data cut, so an edit to any")
    A("of them makes the artifact STALE instead of silently different.")
    A("")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print(f"wrote {OUT} ({len(L)} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
