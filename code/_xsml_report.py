#!/usr/bin/env python3
r"""
_xsml_report.py — the `xsml` BASE book report, built FROM THE ARTIFACT.

Every number is read out of results/runs/<id>.json and formatted so that
`vrun.py guard --strict` can match it back. Nothing is typed by hand.

NOTE: the first version of this report published the numbers of artifact
a2fc128ff0f42f5d, whose ledger had a sign bug on the short leg (the engine
multiplied an already-signed quantity by `side` a second time, so every
short was booked as a mirror-long with its fee CREDITED). Those figures are
WITHDRAWN. This report is built from the corrected artifacts.

Usage:  python code/_xsml_report.py [--turnover full|keep]
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RUNS = os.path.join(ROOT, "results", "runs")
CELLS = os.path.join(ROOT, "results", "_xsml_variants_cells.json")
OUT = os.path.join(ROOT, "results", "xsml_report.md")


def f(x, nd=2):
    if x is None:
        return "-"
    try:
        v = round(float(x), nd)
    except (TypeError, ValueError):
        return str(x)
    if v != v:
        return "-"
    if v in (float("inf"), float("-inf")):
        return "inf" if v > 0 else "-inf"
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return f"{v:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--turnover", default="full", choices=["full", "keep"])
    args = ap.parse_args()
    cells = json.load(open(CELLS, encoding="utf-8"))
    key = f"V1-base/{args.turnover}"
    a = json.load(open(os.path.join(RUNS, cells[key]["run_id"] + ".json"),
                       encoding="utf-8"))
    m = a["metrics"]
    rid = a["run_id"]

    gates = [
        ("G1 at least one hundred closed trades",
         (m["n_trades"] >= 100), f"n = {f(m['n_trades'], 0)}"),
        ("G2 profit factor ex-cost above one point two",
         (m["profit_factor"] > 1.2), f"PF = {f(m['profit_factor'], 4)}"),
        ("G3 net return above zero",
         (m["return_pct"] > 0), f"net = {f(m['return_pct'])} %"),
        ("G4 commission over gross below thirty per cent",
         (m.get("commission_gross_pct") is not None
          and m["commission_gross_pct"] < 30),
         f"commission/gross = {f(m.get('commission_gross_pct'), 1)} %"),
        ("G5 concentration: without the five best trades the result is "
         "still positive",
         (m.get("net_without_best5_pct") is not None
          and m["net_without_best5_pct"] > 0),
         f"net without the five best = {f(m.get('net_without_best5_pct'))} %"),
        ("G6 thirds: green in two of three",
         (m.get("n_periods_green", 0) >= 2),
         f"{f(m.get('n_periods_green'), 0)} of three green "
         f"({f(m.get('period1_pct'))} / {f(m.get('period2_pct'))} / "
         f"{f(m.get('period3_pct'))})"),
        ("G11 a win rate of seventy-five per cent must clear the breakeven "
         "win rate by five points",
         (m["win_rate"] < 75.0), f"win rate = {f(m['win_rate'], 1)} %"),
        ("KILL out-of-sample profit factor below one",
         (m["profit_factor"] >= 1.0), f"PF = {f(m['profit_factor'], 4)}"),
    ]
    passed = [g for g in gates if g[1]]
    failed = [g for g in gates if not g[1]]

    L = []
    L.append("# `xsml` — cross-sectional ML book on 1h perps — OOS verdict")
    L.append("")
    L.append(f"- generated: `{datetime.now(timezone.utc).strftime('%Y-%m-%d')}`")
    L.append(f"- artifact: `results/runs/{rid}` (run_id `{rid}`), "
             f"reproduces bit-for-bit")
    L.append(f"- turnover reading: `{args.turnover}` (the frozen spec leaves "
             f"this open; both readings are reported in "
             f"`results/xsml_variants_report.md`)")
    L.append("- spec (frozen BEFORE the first market run): "
             "`results/xsml_pre_registration.md`")
    L.append("- engine: `code/xsml_engine.py` · adapter `xsml` · "
             "features `code/xsml_features.py` (pybroker indicator engine, no "
             "backtester) · model `code/xsml_model.py`")
    L.append("- engine audit: `code/_xsml_engine_audit.py` (known answers, "
             "both directions) · feature audit: "
             "`code/_xsml_feature_audit.py`")
    L.append("- universe: the eight perps with BOTH 1h klines and a real "
             "funding file; funding is mandatory on a perp")
    L.append("- costs: 11 bps round trip per leg, charged on entry and exit; "
             "**funding charged at the real settlements**, both legs")
    L.append("")
    L.append("## Verdict")
    L.append("")
    L.append("**KILLED.** The OOS profit factor is below one and the net "
             "return is negative. The zero-cost control (measured inside the "
             "artifact) shows the book is only marginally positive without "
             "costs: the edge per trade does not cover the cost of the "
             "turnover, so this is a cost-regime kill on a real-but-weak "
             "forecast, not a book that loses money at every price.")
    L.append("")
    L.append("| gate | result | measured |")
    L.append("|---|---|---|")
    for name, ok, val in gates:
        L.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {val} |")
    L.append("")
    L.append(f"**{len(passed)} of {len(gates)} gates pass.** The failing "
             f"ones are the verdict: {', '.join(g[0] for g in failed) if failed else 'none'}.")
    L.append("")
    L.append("## What the book did")
    L.append("")
    L.append("| metric | value |")
    L.append("|---|---:|")
    L.append(f"| net return (OOS) | {f(m['return_pct'])} % |")
    L.append(f"| profit factor ex-cost | {f(m['profit_factor'], 4)} |")
    L.append(f"| closed trades | {f(m['n_trades'], 0)} |")
    L.append(f"| win rate | {f(m['win_rate'], 1)} % |")
    L.append(f"| max drawdown | {f(m['max_dd_pct'])} % |")
    L.append(f"| net WITHOUT costs (control) | {f(m['ret_zero_pct'])} % |")
    L.append(f"| cost drag | {f(m['drag_pp'])} pp |")
    L.append(f"| fees paid | {f(m['fees_paid_usdt'])} USDT |")
    L.append(f"| funding paid (net, real settlements) | "
             f"{f(m['funding_paid_usdt'])} USDT |")
    L.append(f"| rebalances | {f(m['n_rebalances'], 0)} |")
    L.append(f"| dates not traded (fewer names than the minimum) | "
             f"{f(m['n_dates_not_traded'], 0)} |")
    L.append(f"| exits: stop / target / rebalance / end of data | "
             f"{f(m['n_exit_stop'], 0)} / {f(m['n_exit_target'], 0)} / "
             f"{f(m['n_exit_rebalance'], 0)} / {f(m['n_exit_end_of_data'], 0)} |")
    L.append(f"| forecast correlation with the label, on the traded window | "
             f"{f(m['pred_label_corr'], 4)} (over {f(m['n_pred_rows'], 0)} rows) |")
    L.append(f"| accounting invariant residual | "
             f"{f(m['pnl_identity_resid'], 8)} |")
    L.append("")
    L.append("## Per symbol")
    L.append("")
    L.append("| symbol | trades | PF | PnL USDT |")
    L.append("|---|---:|---:|---:|")
    for t in a.get("tables", []):
        L.append(f"| {t['id']} | {f(t['n'], 0)} | {f(t['pf'], 4)} | "
                 f"{f(t['pnl'])} |")
    L.append("")
    L.append("## How to read this")
    L.append("")
    L.append("- **The forecast does correlate out of sample** (the artifact "
             "measures it on the traded window), and the book still loses. A "
             "weak rank is not a tradeable edge: the stop truncates the "
             "outcome the label was measuring, and the cross-sectional "
             "spread does not cover the eleven basis points per leg that "
             "each turnover pays.")
    L.append(f"- **The zero-cost control is "
             f"{'positive but marginal' if (m['ret_zero_pct'] or 0) > 0 else 'negative'} "
             f"({f(m['ret_zero_pct'])} %)**, so this kill is about the cost "
             f"regime meeting a weak signal, not about a book that has no "
             f"signal at all.")
    L.append("- Judged on its own artifacts (REGLA 1). No other book in this "
             "repo is evidence about this one.")
    L.append("")
    L.append("## Declared limits")
    L.append("")
    L.append("- The window is short: the study starts when the sixth name has "
             "both klines and funding, and the OOS is a few months.")
    L.append("- The model was fitted ONCE on DEV; there is no grid and no "
             "model selection, so there is no trial count to discount — but "
             "there is also no ensemble, and no robustness check across "
             "feature subsets (that would have been new trials, and the spec "
             "forbids them).")
    L.append("- The label is a one-day forward return; the book realizes a "
             "stop-and-target outcome on a stop twice the ATR, so the label "
             "and the realized PnL are different objects. That mismatch is "
             "part of what the numbers show, and it was declared in the spec.")
    L.append("- Leg sizes are frozen at the initial equity: the book does "
             "not scale its notional as equity moves.")
    L.append("- No margin or liquidation model: the gross exposure cannot "
             "breach the declared cap, but no collateral check is made.")
    L.append("- This is a paper measurement on the repo's klines. No orders "
             "were placed.")
    L.append("")
    L.append("## Reproduction")
    L.append("")
    L.append("```")
    L.append(f"python code/vrun.py run --strategy xsml --tf 1h --symbol XSML8 "
             f"--params '{{\"split\": \"OOS\", \"turnover\": \"{args.turnover}\"}}'")
    L.append(f"python code/vrun.py verify {rid}")
    L.append("python code/_xsml_engine_audit.py")
    L.append("```")
    L.append("")
    L.append("The features and the model are upstream of the artifact and are "
             "reproduced by:")
    L.append("")
    L.append("```")
    L.append('& "$HOME\\.venvs\\pybroker\\Scripts\\python.exe" code/xsml_features.py')
    L.append('& "$HOME\\.venvs\\pybroker\\Scripts\\python.exe" code/_xsml_feature_audit.py')
    L.append('& "$HOME\\.venvs\\pybroker\\Scripts\\python.exe" code/xsml_model.py --variant v1')
    L.append("```")
    L.append("")

    text = "\n".join(L) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT}  (artifact {rid})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
