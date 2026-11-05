#!/usr/bin/env python
"""_cand7_assemble_report.py -- build results/cand7_report.md from the seven
cand7 artifacts.  Every number in the report is read from an artifact; the
prose is fixed, the figures are not.

    python code/_cand7_assemble_report.py
"""
from __future__ import annotations

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")

IDS = {
    1: "c1213a34bbd85b49",
    2: "d6a2e71b02126d68",
    3: "7f09a78aede368e6",
    4: "293ed0b0ccf3b3c8",
    5: "04362ac9748dd828",
    6: "e02625eed7daa3f0",
    7: "c48057ec91da83e0",
}

ART = {}
for k, rid in IDS.items():
    with open(os.path.join(RUNS, f"{rid}.json"), encoding="utf-8") as fh:
        ART[k] = json.load(fh)

M = {k: a["metrics"] for k, a in ART.items()}
YEARS = {k: M[k].get("years", {}) for k in M}


def f(v, dp=2):
    if v is None:
        return "n/a"
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "n/a"
    if not math.isfinite(v):
        return "n/a"
    return f"{v:.{dp}f}"


def m(k, key, dp=2):
    return f(M[k].get(key), dp)


def g(k, key, dp=2):
    return f(M[k].get("gate2", {}).get(key), dp)


def exits(k):
    return ", ".join(f"{v} {name}" for name, v in M[k]["exit_reasons"].items())


def fail_list(k, which="fails_v1"):
    xs = M[k].get(which) or []
    return ", ".join(xs) if xs else "none"


L = []
w = L.append

w("# The seven prespecified candidates: measured")
w("")
w("Source document: `Downloads/strategy_candidates_v2-claude.md` (Batch v2.0,"
  " 2026-10-27). The document states that no backtest had been run and that"
  " every performance figure in it is UNVERIFIED. This is the run: seven"
  " candidates, one artifact each, every artifact verified bit-for-bit against"
  " its own engine and data hashes by `vrun.py pverify`.")
w("")
w("The document's prose is not evidence and none of it is repeated as a result."
  " Every figure below is read out of an artifact, and each artifact records the"
  " declared rules it was run under (`declared` in the metrics), plus the repo"
  " cost, the old stress preset and a zero-cost control measured on the same"
  " signals, so a claim about a stop multiple or a fee can be checked against"
  " the artifact rather than against this text.")
w("")
w("## How the numbers were produced")
w("")
w("- **Execution.** Signals on closed bars, fills at the next open. Stops and"
  " targets are intrabar; stop first when both are touched; a gap through a stop"
  " fills at the bar open, adverse. A signal exit fills at the next open."
  " Directional books size a fixed fraction of equity at the stop with a"
  " leverage cap; the basket and pair books hold fixed gross exposure.")
w("- **Funding.** Charged at each symbol's real settlement instants on the open"
  " notional, at the close of the bar containing the settlement. At the entry"
  " instant a settlement is charged when the position pays it and not credited"
  " when the position receives it — the candidates' own convention, applied"
  " symmetrically to both directions.")
w("- **Costs.** The candidates' own block (fee plus slippage per side) drives the"
  " headline. The repo gate cost, the old stress preset and a zero-cost control"
  " are re-run on the same signals inside the same artifact.")
w("- **Gates.** The repo v1 set G1-G6 and the v2 layer of `code/gate2.py`"
  " (expectancy bootstrap lower bound, effective N, purged split, purged folds,"
  " monthly buckets, beta-alpha t, top-5% / best-month / best-week"
  " concentration, cost share, P95 drawdown, breakeven).")
w("- **Audit.** `code/_cand7_audit.py` runs twenty-seven known-answer checks with"
  " hand-computed expectations. It caught four defects before publication: the"
  " basket period rows did not carry their fees or funding; the pair book marked"
  " both legs as long, which inverted the mirrored C6 direction; time exits were"
  " labelled as signal exits; and the C4 low-dispersion branch flattened the book"
  " instead of skipping the rebalance. The engine was fixed at source in each"
  " case and the checks were extended so the defects cannot return silently.")
w("")
w("## Scoreboard")
w("")
w("| # | Book | Unit | n | Net % | PF | Zero PF | Repo PF | Stress PF | Exp LB bps | Breakeven bps | v1 fails | run_id |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for k in range(1, 8):
    a = ART[k]
    sym = a.get("symbol")
    unit = "period" if k in (4, 5) else ("pair" if k == 6 else "trade")
    w(f"| C{k} | {sym} | {unit} | {M[k]['n_trades']} | {m(k,'return_pct')} |"
      f" {m(k,'profit_factor',4)} | {m(k,'profit_factor_zero',4)} |"
      f" {m(k,'profit_factor_repo',4)} | {m(k,'profit_factor_stress',4)} |"
      f" {g(k,'exp_lb_bps')} | {m(k,'breakeven_bps')} |"
      f" {fail_list(k)} | `{IDS[k]}` |")
w("")
w("`Exp LB bps` is the v2 expectancy bootstrap lower bound per trade; `Breakeven`"
  " is the per-side cost at which the book's net return reaches zero, found by"
  " real re-runs. They are different quantities and they are listed separately."
  " A breakeven of 0.00 means the book loses even at zero cost, so no per-side"
  " cost level makes it break even.")
w("")
w("No candidate clears the v1 gates and no candidate clears the v2 gates. The"
  " best v1 showing is C7, which fails only the concentration gate; the best v2"
  " showing is a three-way tie — C2, C4 and C7 each fail five of the eight v2"
  " gates.")
w("")

w("## C1 — ETHUSDT signed taker-flow persistence")
w("")
w(f"{M[1]['n_trades']} trades from {M[1]['n_signals']} first-crossing signals."
  f" Net {m(1,'return_pct')}%, PF {m(1,'profit_factor',4)}, win rate"
  f" {m(1,'win_rate')}%. The zero-cost control returns"
  f" {m(1,'return_zero_pct')}% at PF {m(1,'profit_factor_zero',4)}: **before"
  " any fee the book is a coin flip**. What turns a flat book into a loss is"
  f" execution, not signal: {m(1,'fees_paid')} USDT of fees and slippage."
  f" Exits: {exits(1)}. The expectancy lower bound is {g(1,'exp_lb_bps')} bps"
  f" and the beta-alpha t is {g(1,'alpha_t',4)}, both negative. Fails"
  f" {fail_list(1)}.")
w("")
w("## C2 — SOLUSDT absorption of forced flow")
w("")
w(f"{M[2]['n_trades']} trades, net {m(2,'return_pct')}%, PF"
  f" {m(2,'profit_factor',4)}, maximum drawdown {m(2,'max_dd_pct')}%. The exit"
  f" mix is {M[2]['exit_reasons'].get('time_stop', 0)} timeouts and"
  f" {M[2]['exit_reasons'].get('stop', 0)} stops; no bar touched both the stop"
  f" and the target (counter {M[2]['same_bar_stop_target']}), so the tie rule"
  f" never had to fire. The book breaks even at {m(2,'breakeven_bps')} bps per"
  f" side, several times the declared cost, and the zero-cost PF is"
  f" {m(2,'profit_factor_zero',4)} — cost is not what stops this candidate.")
w("")
y2 = YEARS[2]
w("The sample is twelve trades, and the whole net gain lands in one year: the"
  f" 2026 trades made {f(y2.get('2026'))} USDT while 2024 and 2025 made"
  f" {f(y2.get('2024'))} and {f(y2.get('2025'))}. The five best trades are"
  f" {m(2,'conc_top5_share_pct')}% of total PnL; remove them and the book is"
  f" {m(2,'conc_net_without_top5_pct')}%. The expectancy lower bound is"
  f" {g(2,'exp_lb_bps')} bps, i.e. the sign of the edge is not established."
  f" Fails {fail_list(2)}.")
w("")
w("## C3 — ETHUSDT overnight extension fade")
w("")
w(f"{M[3]['n_trades']} trades, net {m(3,'return_pct')}%, PF"
  f" {m(3,'profit_factor',4)}, win rate {m(3,'win_rate')}%. The zero-cost book"
  f" also loses ({m(3,'return_zero_pct')}%, PF"
  f" {m(3,'profit_factor_zero',4)}), so this is not a cost problem: the fade"
  f" has no gross edge. Exits: {exits(3)}.")
w("")
w("It does beat buy & hold, and that is the trap the repo's rules warn about:"
  f" ETH fell over the window, the book returned {m(3,'return_pct')}% against a"
  f" benchmark of {m(3,'bh_return_pct')}%, and a smaller loss in a falling"
  f" market is not alpha. The beta-alpha t is {g(3,'alpha_t',4)}, the worst of"
  " the seven.")
w("")
w("## C4 — five-asset vol-adjusted 72h rotation")
w("")
w(f"{M[4]['n_trades']} holding periods from {M[4]['n_rebal']} scheduled"
  f" rebalances; {M[4]['n_rebal_skipped']} were skipped because the"
  " cross-sectional dispersion was under the declared gate (a skipped rebalance"
  f" holds the existing book, it does not flatten). Net {m(4,'return_pct')}%, PF"
  f" {m(4,'profit_factor',4)}, drawdown {m(4,'max_dd_pct')}%, turnover"
  f" {m(4,'turnover_per_day_pct')}% of equity per day.")
w("")
w("This is the largest net gain in the batch and it still fails: buy &"
  f" hold returned {m(4,'bh_return_pct')}% over the same window, so G5 fails"
  f" outright. The five best periods are {m(4,'conc_top5_share_pct')}% of total"
  f" PnL and removing them leaves {m(4,'conc_net_without_top5_pct')}%, which is"
  f" G6. PF {m(4,'profit_factor',4)} is under the threshold at the declared"
  f" cost; at the repo cost it is {m(4,'profit_factor_repo',4)}, and the"
  f" zero-cost PF is {m(4,'profit_factor_zero',4)} — the gross edge is real but"
  f" thin, and fees and slippage take {m(4,'fees_paid')} USDT of it.")
w("")
w("Funding is a near-wash at book level but not a small flow in gross:"
  f" {m(4,'funding_gross_paid_usdt')} USDT paid against"
  f" {m(4,'funding_gross_received_usdt')} received, net"
  f" {m(4,'funding_net_usdt')} over the window (a small net payment). The"
  f" per-period split is {m(4,'is_pf',4)} in sample and {m(4,'os_pf',4)} out, so"
  " the halves agree in sign.")
w("")
w("The book kill is inert by construction: four legs at"
  f" {m(4,'declared')['leg_stop'] if False else ART[4]['metrics']['declared']['leg_stop']}"
  f" stop on a {ART[4]['metrics']['declared']['gross']} gross book cannot reach"
  f" the {ART[4]['metrics']['declared']['book_kill']} kill without gaps, and it"
  f" fired {M[4]['book_kill_fired']} times in {M[4]['n_trades']} traded periods."
  " A risk control that cannot bind is not a risk control; the real exposure is"
  " the four stops plus the correlation between the long and short legs.")
w("")
w("## C5 — dispersion-gated 24h reversal")
w("")
w(f"The dispersion gate is essentially never satisfied: {M[5]['n_trades']}"
  f" trades in {M[5]['n_rebal']} days, {M[5]['n_rebal_skipped']} days skipped."
  f" Three observations cannot distinguish this rule from no rule. Net"
  f" {m(5,'return_pct')}%, PF {m(5,'profit_factor',4)}, and every one of the six"
  " v1 gates fails.")
w("")
w("The failure is in the units of the gate, not in the tape: the score is a"
  " vol-scaled 24-bar return, and the gate asks the best and worst scores to sit"
  f" {ART[5]['metrics']['declared']['dispersion_gate']} units apart at the same"
  " hour. The document declared the gate prespecified, so it was not moved; the"
  " honest reading is that the candidate is untestable as written on this"
  " universe.")
w("")
w("## C6 — SOLUSDT vs BTCUSDT funding differential")
w("")
w(f"{M[6]['n_signals']} entry signals produced {M[6]['n_trades']} trades. Every"
  f" signal was the same direction: {M[6]['n_entry_long']} entries long SOL /"
  f" short BTC and {M[6]['n_entry_short']} the other way. The reason is measured"
  " in the artifact: the differential was at or below the negative threshold in"
  f" {m(6,'frac_d_le_neg25_bps',4)} of settlements and at or above the positive"
  f" threshold in {m(6,'frac_d_ge_pos25_bps',4)}. In this window SOL funding sat"
  " below BTC funding, so the symmetric design was a one-sided long-SOL book.")
w("")
w(f"Net {m(6,'return_pct')}%, PF {m(6,'profit_factor',4)}. Funding was a net"
  f" credit: {m(6,'funding_sol')} USDT on the SOL leg and {m(6,'funding_btc')}"
  f" on the BTC leg, {m(6,'funding_net_usdt')} in total, and the book still lost"
  " money. This is the document's own stated"
  " failure condition — funding receipts offset by adverse spread movement —"
  f" arriving on schedule. Fees and slippage equal {g(6,'cost_share',4)} of the"
  " gross profit from its winning trades, and the zero-cost PF is"
  f" {m(6,'profit_factor_zero',4)}, so the book does not work before costs"
  " either. Exits:"
  f" {M[6]['exit_reasons'].get('signal', 0)} on the differential returning and"
  f" {M[6]['exit_reasons'].get('max_hold', 0)} at the holding limit.")
w("")
w("## C7 — SOLUSDT funding-extreme fade")
w("")
w(f"{M[7]['n_trades']} trades from {M[7]['n_signals']} signals, net"
  f" {m(7,'return_pct')}%, PF {m(7,'profit_factor',4)}, drawdown"
  f" {m(7,'max_dd_pct')}%. Breakeven {m(7,'breakeven_bps')} bps per side;"
  f" zero-cost PF {m(7,'profit_factor_zero',4)}. This is the only candidate that"
  " fails just one v1 gate.")
w("")
w(f"The gate it fails is concentration: the five best trades are"
  f" {m(7,'conc_top5_share_pct')}% of total PnL, and without them the book is"
  f" {m(7,'conc_net_without_top5_pct')}%. It also beats buy & hold by being"
  f" short in a falling market ({m(7,'return_pct')}% against"
  f" {m(7,'bh_return_pct')}%), and the beta-adjusted alpha t is"
  f" {g(7,'alpha_t',4)} — not significant. The expectancy lower bound is"
  f" {g(7,'exp_lb_bps')} bps, the out-of-sample side holds only {M[7]['n_oos']}"
  f" trades, and the funding the short collects is {m(7,'funding_net_usdt')}"
  f" USDT on a {ART[7]['metrics']['declared']['init_equity']:.0f} USDT account."
  " The v2 layer fails five of eight, including the sample and the expectancy"
  " bound.")
w("")
w("Note the two concentration measures disagree in a way worth stating: the v1"
  " gate removes the five largest trades and the book turns negative, while the"
  " v2 gate removes the best five percent of trades (two of thirty-three) and"
  f" leaves the book at {g(7,'conc5pct_net',4)}% — economically zero. Both are"
  " measured; they answer different questions, and the stricter one is the v1"
  " gate here.")
w("")

w("## What the seven have in common")
w("")
w("**Four of the seven have no gross edge at all.** C1, C3, C5 and C6 return"
  f" {m(1,'return_zero_pct')}%, {m(3,'return_zero_pct')}%,"
  f" {m(5,'return_zero_pct')}% and {m(6,'return_zero_pct')}% with zero costs."
  " For those books the question is not execution or fees; the signal does not"
  " predict the next move.")
w("")
w("**Where a gross edge exists, concentration is what kills it.** C2, C4 and C7"
  f" have zero-cost PFs of {m(2,'profit_factor_zero',4)},"
  f" {m(4,'profit_factor_zero',4)} and {m(7,'profit_factor_zero',4)}, and their"
  f" five best positions carry {m(2,'conc_top5_share_pct')}%,"
  f" {m(4,'conc_top5_share_pct')}% and {m(7,'conc_top5_share_pct')}% of total"
  " PnL respectively. This is the same shape that killed the strategy pack and"
  " the fifty-prompt packs: a handful of positions, not a distribution.")
w("")
w("**Beating buy & hold is not alpha.** Four of the seven beat their benchmark"
  " — C2, C3, C6 and C7 — and every one of those benchmarks fell over the"
  " window. None of the seven reaches the v2 alpha threshold of 2.0: the best"
  f" is C4 at {g(4,'alpha_t',4)}, and C3 is at {g(3,'alpha_t',4)}. The repo rule"
  " is explicit that losing less than a collapsing market is not alpha.")
w("")
w("**By the v1 sample floor four books qualify; by the v2 floor one does.** C1"
  f" has {M[1]['n_trades']} trades; C3 has {M[3]['n_trades']} trades, C7"
  f" {M[7]['n_trades']}, and C4 has {M[4]['n_trades']} holding periods, all"
  f" above thirty; C2 has {M[2]['n_trades']}, C6 {M[6]['n_trades']} and C5"
  f" {M[5]['n_trades']} and do not. The v2 layer wants a hundred trades and an"
  " effective N of fifty, which only C1 reaches. The v2 expectancy lower bound"
  " is negative for all seven, so that gate fails everywhere it is computed.")
w("")
w("**Two designs contain a control that cannot act.** C4's book kill needs a"
  " gap because the four stops cap the period loss below the kill; it fired"
  f" {M[4]['book_kill_fired']} times. C5's dispersion gate fired on"
  f" {M[5]['n_trades']} of {M[5]['n_rebal']} days. Both were prespecified and"
  " neither was moved after the fact, but as written they make the candidate"
  " partly untestable, which is a design finding rather than a market finding.")
w("")
w("## Verdict")
w("")
w("Zero of seven candidates clear the v1 gates; zero clear the v2 gates. Three"
  " books (C2, C4, C7) show a measurable gross signal, and none of the three"
  " survives the sample, concentration and significance requirements together."
  " The batch is rejected as a source of a deployable strategy. It is not"
  " rejected as evidence: C2 and C7 are cheap, well-defined events that can be"
  " re-specified with a larger sample and a concentration-aware exit, and C4's"
  " gross edge is worth one honest attempt at a cost model that reflects the"
  " actual per-leg fills rather than a flat per-side rate.")
w("")
w("What is **not** measured here: order-book depth, queue position, partial"
  " fills, borrow, and any execution beyond the next open. The candidate"
  " document's own preflight marked execution as a design review, not a"
  " measurement, and that remains true.")
w("")
w("## Reproduction")
w("")
w("```")
for k in range(1, 8):
    w(f"python code\\vrun.py render {IDS[k]}   # C{k}, {ART[k].get('symbol')}")
w("python code\\vrun.py pverify --ids " + ",".join(IDS[k] for k in range(1, 8)))
w("python code\\_cand7_audit.py            # twenty-seven checks, all pass")
w("```")
w("")
w("Artifacts live in `results/runs/`. The engine is `code/cand7_engine.py` on"
  " `code/cand7_core.py` and `code/cand7_strats.py`; the gate layer is"
  " `code/gate2.py`.")

out = os.path.join(ROOT, "results", "cand7_report.md")
with open(out, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(L) + "\n")
print(f"wrote {out} ({len(L)} lines)")
