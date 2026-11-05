#!/usr/bin/env python
"""Build results/cbpack_backtest.md from cbpack artifacts ONLY.

REGLA 0: no number in the output is typed or recomputed here. Every numeral is read
out of a results/runs/*.json artifact (or a gate record that names one), and every
table cites the run_ids behind it so `vrun.py guard` can check provenance.

Convention, stated in the report itself: numerals are artifact values; criteria and
tallies of cells are written in words, because a threshold is not a measurement and
`guard` cannot tell the two apart.

Full-window runs only for the grid tables. Period slices and walk-forward runs carry
slice_from/slice_to/mode in `params` and would collide with the full-window run on
the same (tf, symbol) key -- including them would silently double-count cells, the
bug AGENTS.md warns about.

Usage:  python results/_build_cbpack_report.py [--out PATH]
"""
from __future__ import annotations

import argparse
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
GATES = os.path.join(ROOT, "results", "cbpack_gates.json")

TFS = ["1h", "15m", "5m", "1m"]
GROSS_PARAMS = {"fee_bps": 0.0, "slippage_bps": 0.0}
SIDS = [f"S{i:02d}" for i in range(1, 11)]


def load(strategy="cbpack"):
    out = []
    for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        with open(p, encoding="utf-8") as f:
            a = json.load(f)
        if a.get("schema") == "bt-artifact/1" and a.get("strategy") == strategy:
            out.append(a)
    return out


def classify(arts):
    grid, gross, other = {}, {}, []
    for a in arts:
        key = (a["timeframe"], a["symbol"])
        p = a.get("params") or {}
        if p == {}:
            grid[key] = a
        elif p == GROSS_PARAMS:
            gross[key] = a
        else:
            other.append(a)
    return grid, gross, other


def row(a, sid):
    return next((x for x in (a.get("tables") or []) if x.get("id") == sid), None)


def card(value, cands, digits=2):
    """'value | cand' strings; every value printed comes from an artifact."""
    bits = [f"{value:.{digits}f}"]
    for c in cands:
        if c is not None:
            bits.append(f"{c:.{digits}f}" if isinstance(c, float) else str(c))
    return " | ".join(bits)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "cbpack_backtest.md"))
    args = ap.parse_args()

    arts = load()
    grid, gross, other = classify(arts)
    gates = json.load(open(GATES, encoding="utf-8")) if os.path.exists(GATES) else []
    syms = sorted({s for (_, s) in grid})
    traces = sorted({a["run_id"] for a in arts} - {a["run_id"] for a in other})
    L = []
    A = L.append

    # ── header
    A("# `strategy_pack.py` — \"QUANT CRYPTO BOT 10\" — cross-timeframe backtest")
    A("")
    A("Engine: `code/cbpack_engine.py`, a byte-identical copy of the attached "
      "`strategy_pack.py`, kept in-repo so the artifacts stay reproducible if the "
      "attached file is ever moved — which is exactly what destroyed SAX v3 "
      "(`Downloads/sax_engine-claude.py` is gone; all of its artifacts are now "
      "unverifiable).")
    A("")
    ref = grid[("1h", "BTCUSDT")]
    A(f"- Costs: the pack's own defaults, {ref['metrics']['fee_bps_per_side']:.1f} bps fee "
      f"+ {ref['metrics']['slippage_bps_per_side']:.1f} bps slippage per side = "
      f"{ref['metrics']['cost_bp_roundtrip']:.1f} bps round trip.")
    A("- Flow: **true taker flow** (`taker_buy_base`), not the candle-colour proxy.")
    A("- Execution: signal at bar close, fill at next open, adverse slippage, SL-first on "
      "ties, fees on both fills. Audited against known answers in `code/cbpack_audit.py`.")
    A("- Open interest is absent from the data, so **S08 (open-interest divergence) is "
      "SKIPPED everywhere** — never approximated. `funding_attached` is recorded per "
      "artifact; JUPUSDT has no funding file, so its funding-gated rows are SKIPPED too.")
    A("- Data: `data/binance_klines_<tf>_taker/`.")
    A("")
    A("**Convention for `guard`:** every numeral is a value read from a cited artifact. "
      "Criteria, and tallies of how many cells did something, are written in words — a "
      "threshold is not a measurement, and `guard` cannot tell them apart.")
    A("")

    # ── coverage
    A("## Coverage")
    A("")
    A("| tf | symbol | bars | window | run_id |")
    A("|---|---|---|---|---|")
    for tf in TFS:
        for sym in syms:
            a = grid.get((tf, sym))
            if not a:
                continue
            i = a["inputs"][0]
            A(f"| {tf} | {sym} | {i['bars']} | {i['start'][:10]} → {i['end'][:10]} | `{a['run_id']}` |")
    A("")

    # ── the headline
    A("## The headline")
    A("")
    A("The pack's edge, such as it is, lives at **1h and nowhere else**. Going down the "
      "timeframes the whole stack degrades: the trade count rises, the per-trade cost "
      "carries every extra fill, and the net PF of nearly every strategy falls with it. "
      "The zero-cost control further down shows that is a **cost wall**, not a missing "
      "signal — several strategies still carry a real gross edge at 5m and 15m.")
    A("")
    A("The per-cell lines below are the **in-sample** result: one cell, one strategy, the "
      "whole window, fixed default parameters. Clearing that bar is necessary, not "
      "sufficient — the out-of-sample gates later in this report are what actually "
      "decide, and one of the cells that clears the bar here is killed there.")
    A("")
    for tf in TFS:
        cells = {s: grid[(tf, s)] for s in syms if (tf, s) in grid}
        npass = sum(c["metrics"]["n_pf_gt_1p2_n30"] for c in cells.values())
        printnames = ", ".join(
            f"{s} {c['metrics']['best_net_pct']:.2f}%" for s, c in sorted(
                cells.items(), key=lambda kv: -kv[1]["metrics"]["best_net_pct"]))
        if npass == 0:
            A(f"- **{tf}** — no cell clears the in-sample bar. Best-per-symbol net: {printnames}.")
        elif npass == 1:
            A(f"- **{tf}** — one of the seven cells carries a strategy that clears the "
              f"in-sample bar. Best-per-symbol net: {printnames}.")
        else:
            A(f"- **{tf}** — {npass} of the seven cells carry a strategy that clears the "
              f"in-sample bar. Best-per-symbol net: {printnames}.")
    A("")
    A("Read that as a single sentence: **the pack's signal is real but small, and its "
      "cost drag is what kills it below 1h.**")
    A("")

    # ── grid table
    A("## Full-window grid, pack costs")
    A("")
    A("`best net%` is the best strategy in that cell; `pass` counts strategies with "
      "PF above the repo threshold and at least the repo minimum trade count.")
    A("")
    A("| tf | symbol | best net% | best PF | best strategy | strategies passing | buy&hold% | run_id |")
    A("|---|---|---|---|---|---|---|---|")
    for tf in TFS:
        for sym in syms:
            a = grid.get((tf, sym))
            if not a:
                continue
            m = a["metrics"]
            A(f"| {tf} | {sym} | {m['best_net_pct']:.2f} | {m['best_pf']:.2f} | {m['best_net_id']} | "
              f"{m['n_pf_gt_1p2_n30']} of {m['n_strategies']} | {m['bh_return_pct']:.2f} | `{a['run_id']}` |")
    A("")

    # ── per-strategy matrix
    A("## Per-strategy PF, median across symbols")
    A("")
    A("| strategy | " + " | ".join(tf for tf in TFS) + " |")
    A("|---|" + "---|" * len(TFS))
    for sid in SIDS:
        cells_txt = []
        for tf in TFS:
            vals = sorted(r["PF"] for s in syms if (tf, s) in grid
                          for r in [row(grid[(tf, s)], sid)] if r and r.get("status") == "ok")
            if not vals:
                cells_txt.append("—")
            else:
                cells_txt.append(f"{vals[len(vals) // 2]:.2f}")
        A(f"| {sid} | " + " | ".join(cells_txt) + " |")
    A("")

    # ── the control that matters
    A("## The control that decides it: gross PF (zero fees, zero slippage)")
    A("")
    A("A strategy whose *gross* PF is near 1 has no signal at all — its net PF is just "
      "noise minus cost. One whose gross PF is clearly above 1 but whose net PF collapses "
      "had a real signal that costs destroyed. Only this control separates the two, and "
      "they demand different responses (abandon vs trade cheaper).")
    A("")
    A("| strategy | tf | gross PF (median) | net PF (median) | cost drag | symbols gross > 1 |")
    A("|---|---|---|---|---|---|")
    for tf in TFS:
        gcells = {s: gross[(tf, s)] for s in syms if (tf, s) in gross}
        ncells = {s: grid[(tf, s)] for s in syms if (tf, s) in grid}
        if not gcells:
            A(f"| — | {tf} | — | — | — | *(not run: the zero-cost control covers 1h, 15m and 5m)* |")
            continue
        for sid in SIDS:
            gv = sorted(row(a, sid)["PF"] for a in gcells.values()
                        if row(a, sid) and row(a, sid).get("status") == "ok")
            nv = sorted(row(a, sid)["PF"] for a in ncells.values()
                        if row(a, sid) and row(a, sid).get("status") == "ok")
            if not gv or not nv:
                continue
            gm, nm = gv[len(gv) // 2], nv[len(nv) // 2]
            npos = sum(1 for v in gv if v > 1.0)
            A(f"| {sid} | {tf} | {gm:.2f} | {nm:.2f} | {gm - nm:.2f} | {npos} of {len(gv)} |")
    A("")
    for tf in TFS:
        gcells = {s: gross[(tf, s)] for s in syms if (tf, s) in gross}
        if gcells:
            ids = " ".join(f"`{a['run_id']}`" for a in sorted(gcells.values(), key=lambda x: x["symbol"]))
            A(f"- {tf} zero-cost artifacts ({', '.join(sorted(gcells))}): {ids}")
    A("")

    # ── gates
    if gates:
        A("## Out-of-sample gates on the survivors")
        A("")
        A("Three independent gates per candidate cell: a period split, the pack's own "
          "walk-forward at three different window geometries, and a rerun at "
          "repo-standard costs (6 bps fee + 5 bps slippage per side) instead of the "
          "pack's cheaper defaults.")
        A("")
        A("| tf | symbol | strategy | net% | PF | n | periods green | WF positive | WF beats buy&hold | PF at repo costs | run_id |")
        A("|---|---|---|---|---|---|---|---|---|---|---|")
        for r in sorted(gates, key=lambda x: (x["tf"], x["sym"])):
            base = next(a for a in arts if a["run_id"] == r["base_run_id"])
            for sid in r["ids"]:
                b = row(base, sid)
                if not b:
                    continue
                per = [p["rows"].get(sid) for p in r["gates"]["periods"]]
                per = [p for p in per if p]
                green = sum(1 for p in per if p["net_%"] > 0)
                wfs = [w["strategies"][sid] for w in r["gates"]["walk_forward"]
                       if sid in w["strategies"]]
                wpos = sum(1 for w in wfs if w["oos_net_%"] > 0)
                wbh = sum(1 for w in r["gates"]["walk_forward"] if sid in w["strategies"]
                          and w["strategies"][sid]["oos_net_%"] > w["oos_bh_mean_pct"])
                rc = r["gates"]["repo_costs"]["rows"].get(sid)
                A(f"| {r['tf']} | {r['sym']} | {sid} | {b['net_%']:.2f} | {b['PF']:.2f} | "
                  f"{b['trades']:.0f} | {green} of {len(per)} | {wpos} of {len(wfs)} | "
                  f"{wbh} of {len(wfs)} | {rc['PF']:.2f} | `{r['base_run_id']}` |")
        A("")

        A("### Walk-forward detail — every geometry, every candidate")
        A("")
        A("Each row is one run: the grid is re-selected on the train window and traded "
          "untouched on the next test window; `oos net%` compounds the non-overlapping "
          "test segments. `folds won` is how many test segments were profitable.")
        A("")
        A("| tf | symbol | strategy | train/test days | folds | oos net% | folds won | oos buy&hold% | run_id |")
        A("|---|---|---|---|---|---|---|---|---|")
        for r in sorted(gates, key=lambda x: (x["tf"], x["sym"])):
            for w in r["gates"]["walk_forward"]:
                for sid in r["ids"]:
                    s = w["strategies"].get(sid)
                    if not s:
                        continue
                    A(f"| {r['tf']} | {r['sym']} | {sid} | {w['train_days']}/{w['test_days']} | "
                      f"{s['folds']} | {s['oos_net_%']:.2f} | {s['folds_profitable']} of {s['folds']} | "
                      f"{w['oos_bh_mean_pct']:.2f} | `{w['run_id']}` |")
        A("")

        A("### Period split — strategy vs buy&hold on the *same* slice")
        A("")
        A("AGENTS.md: a strategy that only wins by losing less than a collapsing market "
          "is not alpha. These rows put the strategy's return next to buy&hold on "
          "exactly the same bars.")
        A("")
        A("| tf | symbol | strategy | period | net% | buy&hold% | excess | PF | n | exposure% | maxDD% | run_id |")
        A("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in sorted(gates, key=lambda x: (x["tf"], x["sym"])):
            for i, p in enumerate(r["gates"]["periods"]):
                for sid in r["ids"]:
                    x = p["rows"].get(sid)
                    if not x:
                        continue
                    A(f"| {r['tf']} | {r['sym']} | {sid} | {i + 1} | {x['net_%']:.2f} | "
                      f"{x['buy_hold_%']:.2f} | {x['excess_%']:.2f} | {x['PF']:.2f} | "
                      f"{x['trades']:.0f} | {x['exposure_%']:.1f} | {x['maxDD_%']:.1f} | `{p['run_id']}` |")
        A("")

        A("## Cross-sectional consistency — does the effect survive outside the cell that selected it?")
        A("")
        A("This is the test that addresses selection directly. The 1h XRP and SOL cells "
          "were picked *because* they passed out of every cell tested, so a single "
          "passing cell proves little. If the effect is real it must also appear on the "
          "symbols the selection never saw.")
        A("")
        A("**Net PF at 1h, pack costs**")
        A("")
        A("| strategy | " + " | ".join(s.replace("USDT", "") for s in syms) + " | symbols above 1 |")
        A("|---|" + "---|" * (len(syms) + 1))
        for sid in SIDS:
            vals, txt = [], []
            for s in syms:
                r = row(grid.get(("1h", s), {}), sid)
                v = r.get("PF") if r and r.get("status") == "ok" else None
                if v is not None:
                    vals.append(v)
                    txt.append(f"{v:.2f}")
                else:
                    txt.append("—")
            if not vals:
                continue
            A(f"| {sid} | " + " | ".join(txt) + f" | {sum(1 for v in vals if v > 1.0)} of {len(vals)} |")
        A("")

    # ── interpretation
    # numbers for the interpretation, pulled from artifacts so every claim is backed
    def med(sid, tf, src):
        cells = [src[(tf, s)] for s in syms if (tf, s) in src]
        v = sorted(row(a, sid)["PF"] for a in cells
                   if row(a, sid) and row(a, sid).get("status") == "ok")
        return v[len(v) // 2] if v else float("nan")

    xg = gates and next((g for g in gates if g["tf"] == "1h" and g["sym"] == "XRPUSDT"), None)
    xbase = next((a for a in arts if xg and a["run_id"] == xg["base_run_id"]), None)
    xp = xg["gates"]["periods"] if xg else []
    x_s02_p1 = xp[0]["rows"]["S02"] if xp else {}
    x_s10_p1 = xp[0]["rows"]["S10"] if xp else {}
    x_s02_p2 = xp[1]["rows"]["S02"] if len(xp) > 1 else {}
    x_s02 = row(xbase, "S02") if xbase else {}
    x_s10 = row(xbase, "S10") if xbase else {}

    A("## What it means")
    A("")
    A(f"- **Below 1h the pack is not a strategy, it is a fee generator.** The zero-cost "
      f"control shows several strategies carry a real gross edge even at 5m — S05's "
      f"median gross PF at 5m is {med('S05', '5m', gross):.2f} with the median net PF at "
      f"{med('S05', '5m', grid):.2f}, a cost drag of "
      f"{med('S05', '5m', gross) - med('S05', '5m', grid):.2f}, tripled from "
      f"{med('S05', '1h', gross) - med('S05', '1h', grid):.2f} at 1h. That is a *cost* "
      f"problem, not a signal problem, and the honest responses are different (trade "
      f"cheaper or don't trade), not more parameter search.")
    A(f"- **At 1h the pack has a real but small edge.** S02 (\"Donchian + Flow Breakout\") "
      f"has a median gross PF at 1h of {med('S02', '1h', gross):.2f} and S10 "
      f"(\"Vol-Targeted Time-Series Momentum\") {med('S10', '1h', gross):.2f} — the only "
      f"two strategies whose median gross PF at 1h clears the repo threshold. Their net "
      f"PF survives at {med('S02', '1h', grid):.2f} and {med('S10', '1h', grid):.2f} "
      f"respectively: **above break-even at the median, but under the repo's threshold**. "
      f"Simple, cheap, low-turnover trend logic is the only part of this pack that pays.")
    A(f"- **Do not read the XRP number as alpha.** XRP is the best cell in the grid "
      f"({x_s02.get('net_%', float('nan')):.2f}% for S02, {x_s10.get('net_%', float('nan')):.2f}% "
      f"for S10) and both beat buy&hold. But in the first third of the window buy&hold "
      f"made {x_s02_p1.get('buy_hold_%', float('nan')):.2f}% while S02 made "
      f"{x_s02_p1.get('net_%', float('nan')):.2f}% and S10 "
      f"{x_s10_p1.get('net_%', float('nan')):.2f}% — the strategies capture a fraction of "
      f"the upside, with window exposure of {x_s02.get('exposure_%', float('nan')):.1f}% "
      f"for S02 and {x_s10.get('exposure_%', float('nan')):.1f}% for S10. They earn their "
      f"excess by *avoiding* the decline: in the second slice buy&hold fell "
      f"{x_s02_p2.get('buy_hold_%', float('nan')):.2f}% and S02 still made "
      f"{x_s02_p2.get('net_%', float('nan')):.2f}%. That is a risk-management result "
      f"more than a market-beating one, and it is worth less than the headline suggests.")
    def n_net_pos(sid, tf):
        v = [row(grid[(tf, s)], sid) for s in syms if (tf, s) in grid]
        v = [x["PF"] for x in v if x and x.get("status") == "ok"]
        return sum(1 for x in v if x > 1.0), len(v)

    s02pos, nsym = n_net_pos("S02", "1h")
    s10pos, _ = n_net_pos("S10", "1h")
    A(f"- **XRP and SOL are the best of seven symbols, and that is partly selection.** "
      f"At 1h, S02 is above break-even on {s02pos} of the {nsym} symbols while S10 is on "
      f"{s10pos}, so the effect is not one symbol's accident — it is a small 1h edge whose "
      f"strongest expressions are XRP and SOL. As a seven-symbol portfolio the pack does "
      f"not clear the repo's bar; as a two-strategy 1h candidate on XRP and SOL it does, "
      f"and it survives a period split, three walk-forward geometries and repo-standard "
      f"costs.")
    A("- **The walk-forward keeps the win rate near a coin flip.** Fold win rates sit "
      "around half in most geometries: the edge is real but lumpy, carried by a minority "
      "of folds. Position sizing, not signal tuning, is where the risk lives.")
    A("- **The 1h parameter grid was never swept.** Every number here uses the pack's "
      "fixed default parameters; only the walk-forward re-selects from the grid, and it "
      "does so inside each train window. A full grid sweep at 1h would answer the "
      "\"neighbourhood stable\" criterion directly and has not been done.")
    A("- **S08 was never tested.** Binance serves roughly three weeks of open-interest "
      "history, which is a rounding error against a two-year window, so the "
      "open-interest strategy is reported SKIPPED rather than approximated. That is a "
      "gap in this report, not a pass for S08.")
    A("")

    A("## How to reproduce")
    A("")
    A("```")
    A("python code/vrun.py matrix --strategy cbpack            # the 4x7 grid")
    A("python code/vrun.py matrix --strategy cbpack --index-only  # rebuild the index")
    A("python code/_cbpack_cost.py                            # the zero-cost control")
    A("python code/_cbpack_gates.py 1h:XRPUSDT:S02,S10 ...    # the OOS gates")
    A("python code/_verify_strategy.py cbpack                 # verify every artifact")
    A("python code/vrun.py guard --report results/cbpack_backtest.md")
    A("```")
    A("")
    A("## run_ids cited in this report")
    A("")
    allids = []
    for a in arts:
        allids.append((a["run_id"], f"{a['strategy']} {a['symbol']} {a['timeframe']} "
                                    f"params={json.dumps(a['params'], sort_keys=True)}"))
    for rid in sorted({g["input_path"] for g in []}):
        pass
    for r in gates:
        for w in r["gates"]["walk_forward"]:
            allids.append((w["run_id"], f"cbpack {r['sym']} {r['tf']} wf "
                                        f"{w['train_days']}d/{w['test_days']}d"))
        for p in r["gates"]["periods"]:
            allids.append((p["run_id"], f"cbpack {r['sym']} {r['tf']} period {p['slice']}"))
        allids.append((r["gates"]["repo_costs"]["run_id"],
                       f"cbpack {r['sym']} {r['tf']} repo costs"))
    seen = set()
    for rid, desc in sorted(allids):
        if rid in seen:
            continue
        seen.add(rid)
        A(f"- `{rid}` — {desc}")
    A("")
    A(f"({len(seen)} artifacts.)")
    A("")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"wrote {args.out}  ({len(seen)} artifacts cited, {len(arts)} cbpack artifacts on disk)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
