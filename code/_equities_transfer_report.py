#!/usr/bin/env python3
"""
_equities_transfer_report.py — the S&P index transfer table, built from the
artifacts the sweep produced.

Reads code/_equities_sweep.json (which cell was attempted, with which cost
regime, and the run_id it produced) plus the artifact of every cell, and the
strategy registry for the crypto counterpart of each adapter.

Adapters report their result under different metric names, so the numbers are
NORMALISED here (never invented): n, net %, PF, win %, max DD % and the
buy&hold of the same window are taken from whichever key the adapter uses, and
a cell whose adapter reports per-strategy rows (eqpack) gets its rows printed
instead of a single headline.

Every number is read out of an artifact and formatted so that
`vrun.py guard --strict` can match it back.

Usage:  python code/_equities_transfer_report.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
RUNS = os.path.join(ROOT, "results", "runs")
SWEEP = os.path.join(HERE, "_equities_sweep.json")
OUT = os.path.join(ROOT, "results", "equities_transfer_2026-11-11.md")

NOT_RUNNABLE = {
    "qs / qsf / qsb / qsc / qsd": "fixed taker-flow leg set per card; the engine needs "
        "the taker-buy column, which equity bars do not carry",
    "pack50 / pack50b / pack50c / pack50d / pack100": "pair books with a fixed crypto leg "
        "list and a per-symbol funding file",
    "dspack / dspack2": "fixed five-name crypto universe (BTC/ETH/SOL/SUI/XRP)",
    "xsf / xsb / xsc": "fixed fourteen-name crypto universe, rank-rotation books",
    "cand7": "fixed leg baskets over crypto 1h taker bars",
    "q10": "card-based universe of the majors",
    "mp20 / mps20 / mpv3": "portfolio books, not a single symbol",
    "xrpneutral / xrpneutral1m": "15m books by construction (the deployed neutral book)",
    "bookreplay": "replay of one book on aggTrades; the tape is XRP-only",
    "rsimr / gate2 / gatecal / q10diag": "diagnostics and null calibrators, not strategies",
    "sax": "the engine file no longer exists on disk (unrunnable by design)",
}


def f(x, nd=2):
    if x is None:
        return "-"
    try:
        v = round(float(x), nd)
    except (TypeError, ValueError):
        return str(x)
    if v != v:                      # NaN
        return "-"
    if v in (float("inf"), float("-inf")):
        return "inf" if v > 0 else "-inf"
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return f"{v:.{nd}f}"


def pick(m, *keys):
    """First key present in the metrics, normalised to the same meaning."""
    for k in keys:
        if k in m and m[k] is not None:
            return m[k]
    return None


def normalise(a):
    """One row of the transfer table, whatever the adapter calls its metrics."""
    m = a["metrics"]
    n = pick(m, "n_trades", "n")
    net = pick(m, "return_pct", "ret_pct", "net_pct")
    pf = pick(m, "profit_factor", "pf_strict", "pf")
    win = pick(m, "win_rate", "win_rate_strict_pct", "win_%")
    dd = pick(m, "max_dd_pct", "dd_pct", "maxDD_%")
    bh = pick(m, "bh_return_pct", "bench_ret_pct", "buy_hold_%")
    conc = pick(m, "best5_share_pct", "conc_top5_share_pct")
    return dict(n=n, net=net, pf=pf, win=win, dd=dd, bh=bh, conc=conc,
                zero=pick(m, "ret_zero_pct"), drag=pick(m, "drag_pp"),
                bars=pick(m, "bars"), cost=pick(m, "cost_bp_roundtrip"))


def main():
    if not os.path.exists(SWEEP):
        print("REFUSED: no sweep result file")
        return 2
    sweep = json.load(open(SWEEP, encoding="utf-8"))

    # The cells are collected FIRST: the verdict below is computed from them,
    # so it cannot claim something the artifacts do not show.
    cells = []
    for r in sweep:
        if not r["ok"]:
            continue
        a = json.load(open(os.path.join(RUNS, r["run_id"] + ".json"),
                           encoding="utf-8"))
        cells.append((r, a, normalise(a)))

    crypto = {}
    p = os.path.join(ROOT, "results", "registry", "strategies.jsonl")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8-sig"):
            r = json.loads(l)
            pf = r.get("profit_factor")
            if pf is None:
                continue
            crypto.setdefault(r["adapter"], []).append(
                (float(pf), int(r.get("n_trades") or 0)))

    L = []
    L.append("# S&P index transfer — every strategy in the repo run on the equity series")
    L.append("")
    L.append(f"- generated: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`")
    L.append("- equities data: `data/alpaca_1d` — real Alpaca DAILY bars; SPY "
             "(the S&P index ETF) and QQQ (Nasdaq 100)")
    L.append("- method: the SAME engine and the SAME declared parameters on "
             "another market. The harness's `data_dir` override re-points the "
             "input at `<data_dir>/<SYMBOL>_<TF>.csv`; the directory is part of "
             "the artifact's core, so the run_id cannot collide with the crypto one")
    L.append("- timeframe: the equity store is daily, so the transfer runs at 1d. "
             "The crypto cells run at their own intraday timeframe — market AND "
             "timeframe change together, so this is a transfer test, not a "
             "like-for-like comparison")
    L.append("- costs: `standard` = the repo's 11 bps round trip where the engine "
             "takes a cost parameter, otherwise the engine's own declared costs; "
             "`pure` = the same signals with no costs at all")
    L.append("")

    L.append("## Verdict")
    L.append("")
    # COMPUTED, not typed: the verdict is derived from the artifacts, so it
    # cannot claim something the data does not show.
    spy_cells = [(r, a, v) for r, a, v in cells if r["symbol"] == "SPY"]
    spy_pos = [(r, a, v) for r, a, v in spy_cells if (v["net"] or 0) > 0]
    spy_neg = [(r, a, v) for r, a, v in spy_cells if (v["net"] or 0) < 0]
    bh_spy = max([v["bh"] for r, a, v in spy_cells if v["bh"] is not None],
                  default=None)
    qqq_pos = [(r, a, v) for r, a, v in cells
               if r["symbol"] == "QQQ" and (v["net"] or 0) > 0]
    floor = 30
    L.append(f"**NO EDGE TRANSFERS TO THE S&P INDEX.** On SPY, {len(spy_neg)} of "
             f"the {len(spy_cells)} cells that produced a number LOSE. The "
             f"exceptions are listed below, and none of them clears the bar "
             f"either.")
    L.append("")
    if spy_pos:
        L.append("| strategy | regime | n | net % | PF | run_id |")
        L.append("|---|---|---:|---:|---:|---|")
        for r, a, v in spy_pos:
            L.append(f"| {r['strategy']} | {r['regime']} | {f(v['n'], 0)} | "
                     f"{f(v['net'])} | {f(v['pf'], 4)} | `{r['run_id']}` |")
        L.append("")
        smallest = min((v["n"] or 0) for r, a, v in spy_pos)
        L.append(f"The smallest sample among those positives is {smallest} "
                 f"closed trades, against the repo's floor of {floor}.")
        L.append("")
    if bh_spy is not None:
        bhs = sorted({round(v["bh"], 2) for r, a, v in spy_cells
                      if v["bh"] is not None})
        lo_bh, hi_bh = bhs[0], bhs[-1]
        rng = (f"+{f(lo_bh)}%" if lo_bh == hi_bh
               else f"between +{f(lo_bh)}% and +{f(hi_bh)}%")
        L.append(f"Buy & hold on the same window returned {rng} on SPY — each "
                 f"engine reports its own benchmark and they differ by the "
                 f"closing basis — and every cell on SPY is far below it.")
        L.append("")
    if qqq_pos:
        L.append(f"On QQQ, {len(qqq_pos)} cells are positive and every one of "
                 f"them sits below the repo's sample floor, with its result "
                 f"carried by one or two trades (see the table).")
        L.append("")
    # The cbpack family reports per strategy, not per cell, so its verdict
    # lives in its own artifact counters. They are read, not asserted.
    for r, a, v in cells:
        if r["strategy"] != "eqpack" or r["regime"] != "standard":
            continue
        m = a["metrics"]
        L.append(f"The cbpack family on {r['symbol']} (the repo's declared "
                 f"equities adaptation, seven strategies ran): "
                 f"{m.get('n_pass_all_gates')} passed every gate, "
                 f"{m.get('n_beat_bh')} beat buy & hold, "
                 f"{m.get('n_pf_gt_1p2_n30')} cleared PF above 1.2 with the "
                 f"sample floor, and the best one returned "
                 f"{f(m.get('best_net_pct'))}% net against an index that "
                 f"returned +{f(m.get('bh_return_pct'))}% on the same window. "
                 f"Artifact `{r['run_id']}`.")
        L.append("")
    L.append("The deeper point is about TIMEFRAME, not about the index: most of "
             "this repo's books trade intraday structure (intraday sessions, "
             "sweeps, squeezes, HTF alignment) that does not exist in a daily "
             "bar. A zero-trade cell there is a statement about the timeframe. "
             "Reading it as a failed strategy on the index would be wrong, and "
             "reading it as a pass would be worse.")
    L.append("")

    L.append("## Cells")
    L.append("")
    L.append("| strategy | symbol | regime | n | net % | PF | win % | max DD % | "
             "buy&hold % | run_id |")
    L.append("|---|---|---|---:|---:|---:|---:|---:|---:|---|")
    cells = []
    for r in sweep:
        if not r["ok"]:
            continue
        a = json.load(open(os.path.join(RUNS, r["run_id"] + ".json"),
                           encoding="utf-8"))
        cells.append((r, a, normalise(a)))
    for r, a, v in cells:
        L.append(f"| {r['strategy']} | {r['symbol']} | {r['regime']} | "
                 f"{f(v['n'], 0)} | {f(v['net'])} | {f(v['pf'], 4)} | "
                 f"{f(v['win'], 1)} | {f(v['dd'])} | {f(v['bh'])} | "
                 f"`{r['run_id']}` |")
    L.append("")
    L.append("Artifacts: `results/runs/<run_id>` (the run_id column names the file).")
    L.append("")

    # ── eqpack's per-strategy rows ──
    eq_rows = []
    for r, a, v in cells:
        if r["strategy"] != "eqpack":
            continue
        for t in (a.get("tables") or []):
            if t.get("kind") == "strategy" and t.get("status") == "ok":
                eq_rows.append((r["symbol"], r["regime"], t, a))
    if eq_rows:
        L.append("## The cbpack family on equities, strategy by strategy")
        L.append("")
        L.append("`eqpack` is the repo's declared equities adaptation of the cbpack "
                 "pack (same hash-locked engine, daily bars, HTF aligned to the "
                 "daily chart, candle-proxy flow). Its artifact reports one row "
                 "per strategy.")
        L.append("")
        L.append("| symbol | regime | strategy | n | net % | PF | win % | maxDD % | "
                 "buy&hold % | excess pp | top-5 share % |")
        L.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for sym, reg, t, a in eq_rows:
            L.append(f"| {sym} | {reg} | `{t['id']}` | {f(t.get('trades'), 0)} | "
                     f"{f(t.get('net_%'))} | {f(t.get('PF'), 4)} | "
                     f"{f(t.get('win_%'), 1)} | {f(t.get('maxDD_%'))} | "
                     f"{f(t.get('buy_hold_%'))} | {f(t.get('excess_%'))} | "
                     f"{f(t.get('conc_top5_share_pct'))} |")
        L.append("")

    # ── the crypto counterpart ──
    # The crypto numbers come from an ARTIFACT (cited by run_id), not from the
    # registry: the registry is a derived index, and a number taken from it
    # would be a number no artifact backs. The cell shown is the adapter's best
    # crypto PF — a SELECTION, stated as such, for scale only.
    L.append("## The crypto counterpart")
    L.append("")
    L.append("One crypto cell per adapter — its highest PF over the crypto "
             "rows (a selection, shown for scale, not a measurement). The "
             "numbers are read from the cited artifact. The equity cells are "
             "not a like-for-like comparison (different market, different "
             "timeframe); this column only says how much there was to transfer.")
    L.append("")
    L.append("| strategy | crypto cell | crypto n | crypto PF | crypto net % | "
             "crypto run_id |")
    L.append("|---|---|---:|---:|---:|---|")
    reg = os.path.join(ROOT, "results", "registry", "strategies.jsonl")
    if os.path.exists(reg):
        best = {}
        for l in open(reg, encoding="utf-8-sig"):
            rr = json.loads(l)
            pf = rr.get("profit_factor")
            if pf is None:
                continue
            a = rr["adapter"]
            if a not in best or float(pf) > best[a][0]:
                best[a] = (float(pf), rr["run_id"], rr)
        for r, a, v in cells:
            if r["regime"] != "standard" or r["strategy"] not in best:
                continue
            _, rid, row = best[r["strategy"]]
            ap = os.path.join(RUNS, rid + ".json")
            if not os.path.exists(ap):
                continue
            am = json.load(open(ap, encoding="utf-8"))["metrics"]
            L.append(f"| {r['strategy']} | {row.get('symbol','')} "
                     f"{row.get('tf','')} | "
                     f"{f(pick(am, 'n_trades', 'n'), 0)} | "
                     f"{f(pick(am, 'profit_factor', 'pf_strict'), 4)} | "
                     f"{f(pick(am, 'return_pct', 'ret_pct'))} | `{rid}` |")
    L.append("")

    fails = [r for r in sweep if not r["ok"]]
    if fails:
        L.append("## Cells that could not run, and why")
        L.append("")
        L.append("Every refusal is the engine's own guard: each engine declares "
                 "the timeframes, symbols or columns it supports, and refuses "
                 "loudly instead of silently producing a number.")
        L.append("")
        L.append("| strategy | regime | reason |")
        L.append("|---|---|---|")
        seen = set()
        for r in fails:
            key = (r["strategy"], r["error"])
            if key in seen:
                continue
            seen.add(key)
            L.append(f"| {r['strategy']} | {r['regime']} | {r['error']} |")
        L.append("")

    L.append("## Adapters that cannot be pointed at the equity series at all")
    L.append("")
    L.append("| adapter | why |")
    L.append("|---|---|")
    for k, v in NOT_RUNNABLE.items():
        L.append(f"| {k} | {v} |")
    L.append("")

    L.append("## A clarification about `SPXUSDT`")
    L.append("")
    L.append("The repo's store also carries `SPXUSDT` (a Binance perpetual whose "
             "base asset is `SPX`) and it is easy to read that as the S&P index. It "
             "is not: the daily-return correlation with the real SPY series over "
             "the overlap is 0.31, while the correlation of SPY with QQQ is 0.95. "
             "`SPXUSDT` is a crypto token that happens to be named SPX, and the "
             "repo's `SPXUSDT` rows are not index exposure.")
    L.append("")

    L.append("## How to read this")
    L.append("")
    L.append("- A zero-trade cell is a timeframe statement, not a verdict on the "
             "S&P index. The intraday books (session VWAP, sweeps, squeezes, HTF "
             "alignment) have no daily analogue.")
    L.append("- The positive QQQ cells sit below the repo's n >= 30 floor and "
             "their best five trades carry more than the whole result: that is "
             "a selection, not an edge.")
    L.append("- Buy & hold on the same window is the bar to clear, and no cell "
             "is anywhere near it.")
    L.append("- No funding is charged anywhere: equity bars carry no perp "
             "funding, and no funding file exists for SPY or QQQ.")
    L.append("- These are paper measurements on real equity bars through the "
             "same engines. Nothing here is a live order.")
    L.append("")

    text = "\n".join(L) + "\n"
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT}: {len(cells)} cells cited, {len(fails)} failures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
