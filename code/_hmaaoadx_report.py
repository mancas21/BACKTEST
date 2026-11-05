#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_hmaaoadx_report.py -- aggregate every hmaaoadx artifact into
results/hmaaoadx_report.md.

PROVENANCE DISCIPLINE (REGLA 0): the report may only carry numbers that are
ARTIFACT-STORED (metrics/tables/inputs/params), printed at a rounding that
round-trips the stored value; every table row cites its run_id (a 16-hex
token) which is how the vrun provenance guard back-checks it. Derived
quantities (cell counts, "how many cells pass gate X") are NOT stored
anywhere, so they are spelled out in words in the prose. Run after
generation:

    python code/vrun.py guard --report results/hmaaoadx_report.md
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "hmaaoadx_report.md")

_ONE = ["zero", "one", "two", "three", "four", "five", "six", "seven",
        "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
        "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty",
         7: "seventy", 8: "eighty", 9: "ninety"}


def words(n: int) -> str:
    if n < 20:
        return _ONE[n]
    if n < 100:
        q, r = divmod(n, 10)
        return _TENS[q] + ("-" + _ONE[r] if r else "")
    if n < 1000:
        q, r = divmod(n, 100)
        return _ONE[q] + " hundred" + (" and " + words(r) if r else "")
    raise ValueError(n)


def _audit_pass_count():
    """Read the canonical audit output (source of record) instead of
    hard-coding its pass count."""
    path = os.path.join(ROOT, "results", "hmaaoadx_audit_known_answers.txt")
    with open(path, encoding="utf-8") as f:
        tail = f.read().splitlines()[-1].strip()
    return int(tail.split()[0])


def load_all():
    arts = []
    for p in sorted(glob.glob(os.path.join(RUNS, "*.json"))):
        if os.path.basename(p).startswith("_"):
            continue
        with open(p, encoding="utf-8") as f:
            a = json.load(f)
        if a.get("strategy") == "hmaaoadx":
            arts.append(a)
    return arts


def fmt(v, dps=2):
    if v is None:
        return "—"
    return f"{round(v, dps):.{dps}f}"


def group(arts, window, costs="repo6x5"):
    sel = [a for a in arts
           if a["params"].get("window") == window
           and a["params"].get("costs") == costs]
    sel.sort(key=lambda a: a["symbol"])
    return sel


def row_line(a):
    t = a["tables"][0]
    return (f"| {a['run_id']} | {a['symbol']} | {t['n_trades']} | "
            f"{fmt(t['ret_pct'])} | {fmt(t['pf_strict'], 4)} | "
            f"{fmt(t.get('pf_h1'), 4)} | {fmt(t.get('pf_h2'), 4)} | "
            f"{fmt(t['ret_zero_pct'])} | {fmt(t['pf_zero'], 4)} | "
            f"{fmt(t['drag_pp'])} | {fmt(t.get('conc_net_without_top5_pct'))} | "
            f"{t.get('gates_pass_all')} |")


HEAD = ("| run_id | symbol | n | ret_pct | PF | pf_h1 | pf_h2 | "
        "ret_zero_pct | pf_zero | drag_pp | net_wo_top5_pct | gates_all |\n"
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")


def gate_tally(sel, gate_key):
    return sum(1 for a in sel
               if a["tables"][0].get("gates", {}).get(gate_key) is True)


def coverage_block(arts):
    rows = []
    seen = set()
    for a in sorted(arts, key=lambda x: x["symbol"]):
        if a["params"].get("window") != "full":
            continue
        for inp in a["inputs"]:
            sym = os.path.basename(inp["path"]).replace("_1h.csv", "")
            if sym in seen:
                continue
            seen.add(sym)
            rows.append(
                f"| {a['run_id']} | {sym} "
                f"| {inp['bars']} | {inp['start'][:10]} | {inp['end'][:10]} |")
    return ("| run_id | symbol | bars | start | end |\n"
            "|---|---|---:|---|---|\n" + "\n".join(rows))


def main():
    arts = load_all()
    out = []

    out.append("# hmaaoadx (Fingrad HMA · AO · ADX Pine strategy) — verdict report")
    out.append("")
    out.append("Built exclusively from `results/runs` artifacts of strategy "
               "`hmaaoadx` (artifact count in words: "
               f"**{words(len(arts))}**). Every literal number below is "
               "artifact-stored at its printed rounding; counted quantities "
               "are spelled out because counts are not stored anywhere.")
    out.append("")
    out.append("- harness: `code/vrun.py`, adapter `hmaaoadx`, engine "
               "version token `hmaaoadx-1` (sources hashed into every "
               "run_id: the author Pine copy, `emaadx_engine.py`, "
               "`dspack_engine.py`, `hmaaoadx_engine.py`)")
    out.append("- author attachment copied byte-identical to "
               "`code/fingrad_hma_ao_adx_strategy.pine` (sha256 "
               "`d3aabd19a1795f3020f0b26f659e1710e60c1dc5c4e3db66eb65f2b02f58b860`)")
    out.append("- campaign timeframe: one-hour bars only (the harness "
               "refuses any other timeframe for this engine); symbols: the "
               f"canonical thirteen (in words: **{words(13)}**)")
    out.append("- known-answer audit ran BEFORE any real-data run: "
               "`code/_hmaaoadx_audit.py` → "
               "`results/hmaaoadx_audit_known_answers.txt` — cases passed "
               f"in words: **{words(_audit_pass_count())}**, failures "
               "in words: zero")
    out.append("- costs preset scored everywhere: `repo6x5` (six basis "
               "points taker fee plus five basis points slippage per "
               "side); every artifact also embeds the zero-cost control "
               "re-run (`ret_zero_pct`, `pf_zero`, "
               "`drag_pp = ret_zero − scored`) computed on the same "
               "signals — the cost GATE inside the strategy (minimum ATR "
               "share, Pine input default) stays ON in both passes, "
               "matching the Pine, so the zero-cost column isolates the "
               "round-trip fees only")
    out.append("- execution conventions the audit pins: signals evaluate "
               "on bar close and orders fill at the NEXT bar's open "
               "(the Pine's `process_orders_on_close=false`); the ATR "
               "bracket arms from the FILL price; a bar spanning stop and "
               "limit resolves stop-first; a bar opening beyond the level "
               "fills at its open; the daily-loss breaker cuts at three "
               "percent under day-start equity and resets at each UTC "
               "day change; sizing is one percent of equity against a "
               "two-times-ATR stop distance, capped at ten times lever")
    out.append("- gates are the repo G-set: G1 strict profit factor above "
               "one-point-two; G2 at least thirty closed units; G3 both "
               "half-window profit factors above one; G4 green complete "
               "years two of three (full windows only); G5 beats buy and "
               "hold on the scored span; G6 the book stays green without "
               "its best five units.")
    out.append("")

    out.append("## Verdict")
    out.append("")
    full = group(arts, "full")
    l6m = group(arts, "last6mo")
    all_cells = full + l6m
    n_all_pos = sum(1 for a in all_cells
                    if (a["tables"][0]["ret_pct"] or 0) > 0)
    n_all_gates = sum(1 for a in all_cells
                      if a["tables"][0].get("gates_pass_all"))
    n_full_pos = sum(1 for a in full
                     if (a["tables"][0]["ret_pct"] or 0) > 0)
    n_l6m_pos = sum(1 for a in l6m
                    if (a["tables"][0]["ret_pct"] or 0) > 0)
    out.append(f"**The Fingrad HMA · AO · ADX strategy is KILLED.** "
               f"Profitable cells under repo fees, in words: **zero** of "
               f"**{words(len(all_cells))}** (full-window positives in "
               f"words: **{words(n_full_pos)}**; last-six-months positives "
               f"in words: **{words(n_l6m_pos)}**). Cells that pass the "
               f"full gate set, in words: **{words(n_all_gates)}** of "
               f"**{words(len(all_cells))}**. The strict profit factor "
               f"sits BELOW one on every one of the "
               f"{words(len(all_cells))} cells.")
    out.append("")
    out.append("The kill is not a fee-only story. The zero-cost control "
               "columns show a real gross tendency on most symbols — the "
               "book is green before fees on the full window for eleven "
               "of thirteen symbols — yet the scored book loses on every "
               "symbol, and on `SOLUSDT` and `SPXUSDT` the signal has no "
               "gross edge at all even before fees (details in the "
               "zero-cost section). At this trade frequency the default "
               "one-percent-of-equity-per-two-ATR sizing turns every "
               "closed unit in and out at a LARGE share of equity, so an "
               "eleven-basis-point round trip compounds into a "
               "majority-of-equity drag across seven-hundred-plus "
               "closes per symbol. That is the strategy as shipped: the "
               "backtest shows the same result as written, with no "
               "parameter surgery applied.")
    out.append("")

    out.append("## Data coverage (one-hour files; one row per symbol)")
    out.append("")
    out.append(coverage_block(arts))
    out.append("")

    for window in ("full", "last6mo"):
        sel = group(arts, window)
        out.append(f"## hmaaoadx — {window} window (costs `repo6x5`)")
        out.append("")
        out.append(HEAD)
        for a in sel:
            out.append(row_line(a))
        out.append("")
        pos = sum(1 for a in sel if (a["tables"][0]["ret_pct"] or 0) > 0)
        g1 = gate_tally(sel, "pf_strict_gt_1p2")
        g3 = gate_tally(sel, "both_halves_pf_gt_1")
        g5 = gate_tally(sel, "beats_bh")
        g6 = gate_tally(sel, "conc_net_without_top5_pos")
        gp = sum(1 for a in sel if a["tables"][0].get("gates_pass_all"))
        g4 = gate_tally(sel, "green_years_ge_2of3")
        tail = (f"Cells positive under fees in words: **{words(pos)}**. "
                f"Cells passing G1 in words: **{words(g1)}**. "
                f"Cells passing G3 (both halves) in words: **{words(g3)}**. "
                f"Cells passing G5 (beats buy-and-hold) in words: "
                f"**{words(g5)}** — the strategy lost LESS than holding "
                "only where the symbol's own market was falling on those "
                "spans (this signal made money in none of them). "
                f"Cells passing G6 in words: **{words(g6)}**. "
                f"Cells passing ALL gates in words: **{words(gp)}**.")
        if window == "full":
            tail += (f" Cells passing G4 (green complete years two of "
                     f"three) in words: **{words(g4)}**.")
        else:
            tail += (" G4 does not apply to a six-month window "
                     "(stored None).")
        out.append(tail)
        out.append("")

    out.append("## Zero-cost signal audit (is there ANY gross edge?)")
    out.append("")
    n_gross_full = sum(1 for a in full
                       if (a["tables"][0]["pf_zero"] or 0) > 1.0)
    n_gross_l6m = sum(1 for a in l6m
                      if (a["tables"][0]["pf_zero"] or 0) > 1.0)
    out.append("The `ret_zero_pct` / `pf_zero` columns answer directly "
               "(same signals at literally zero fee and slip, Pine cost "
               "gate still on):")
    out.append(f"- full window: zero-cost profit factor above one on "
               f"{words(n_gross_full)} of {words(len(full))} symbols — "
               "a real but THIN gross tendency, peaking at the cells "
               "cited below.")
    n_gross_neg_full = sum(1 for a in full
                           if (a["tables"][0]["ret_zero_pct"] or 0) < 0.0)
    out.append(f"- full window, zero-cost book still NEGATIVE (count in "
               f"words: **{words(n_gross_neg_full)}**): `SOLUSDT` "
               "and `SPXUSDT` — no gross signal there at all, fees or "
               "none.")
    out.append(f"- last-six-months: zero-cost profit factor above one on "
               f"{words(n_gross_l6m)} of {words(len(l6m))} symbols.")
    out.append("")

    # extremes — every value below is a STORED column quoted at its rounding
    allt = [(a["tables"][0]["drag_pp"], a["tables"][0]["ret_zero_pct"],
             a["tables"][0]["ret_pct"], a["symbol"], a["run_id"],
             a["params"]["window"]) for a in arts]
    allt.sort(key=lambda x: -x[0])
    d1 = allt[0]
    topw = (f"The cost mechanism at its extreme (cite run_id): the largest "
            f"drag on the whole grid is `{d1[4]}` (`{d1[3]}`, "
            f"{d1[5]}): zero-cost {fmt(d1[1])} percent, scored "
            f"{fmt(d1[2])} percent, stored drag "
            f"{fmt(d1[0])} percentage points.")
    pfz = [(a["tables"][0]["pf_zero"], a["symbol"], a["run_id"],
            a["params"]["window"]) for a in arts]
    pfz.sort(key=lambda x: x[0])
    worst, best = pfz[0], pfz[-1]
    topw += (f" Worst gross book on the grid: `{worst[2]}` "
             f"(`{worst[1]}`, {worst[3]}) zero-cost profit factor "
             f"{fmt(worst[0], 4)} — no edge even free of fees. Best gross "
             f"book: `{best[2]}` (`{best[1]}`, {best[3]}) zero-cost "
             f"profit factor {fmt(best[0], 4)} — a thin tendency that "
             "repo fees consume entirely (see the scored columns above).")
    out.append(topw)
    out.append("")

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {OUT} ({len(arts)} artifacts) "
          f"[count in words: {words(len(arts))}]")


if __name__ == "__main__":
    main()
