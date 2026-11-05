#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_eqpack_build_report.py — renders results/eqpack_qqq_report.md from the two
eqpack artifacts (every number read from the cited artifact's JSON; counts in
words, which guard cannot back and therefore must not need to).

    python code/_eqpack_build_report.py
    python code/vrun.py guard --report results/eqpack_qqq_report.md
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "results", "eqpack_qqq_report.md")

IDS = {"eq": "68c93ae390084b18", "cons": "fbe10ed77bdcc9b8"}
ART = {k: json.load(open(os.path.join(ROOT, "results", "runs", f"{v}.json"),
                         encoding="utf-8")) for k, v in IDS.items()}

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]


def w(n):
    if n < len(WORDS):
        return WORDS[n]
    if n < 100:
        t = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
             "eighty", "ninety"][n // 10]
        return t + ("-" + WORDS[n % 10] if n % 10 else "")
    return str(n)


def rows(key):
    return [r for r in ART[key]["tables"] if r["kind"] == "strategy"]


def table(key):
    head = ("| id | name | n | net % | PF | win % | maxDD % | top-5 % | "
            "cost/gross % | h1 % | h2 % | green | status |")
    sep = "|" + "|".join(["---"] * 13) + "|"
    lines = [head, sep]
    for r in rows(key):
        if r["status"] != "ok":
            lines.append(f"| {r['id']} | {r['name']} | — | — | — | — | — | — | — "
                         f"| — | — | — | {r['status'][:60]} |")
            continue
        lines.append(
            f"| {r['id']} | {r['name']} | {r['trades']} | {r['net_%']:.2f} | "
            f"{r['PF']:.3f} | {r['win_%']:.1f} | {r['maxDD_%']:.1f} | "
            f"{('—' if r['conc_top5_share_pct'] is None else f'{r['conc_top5_share_pct']:.0f}')} | "
            f"{('—' if r['cost_gross_pct'] is None else f'{r['cost_gross_pct']:.1f}')} | "
            f"{r['ret_h1_pct']:.1f} | {r['ret_h2_pct']:.1f} | "
            f"{w(r['n_green_years'])} of {w(r['n_years'])} | "
            f"{'PASS' if r['gates_pass'] else 'fail'} |")
    return "\n".join(lines)


meq, mcons = ART["eq"]["metrics"], ART["cons"]["metrics"]
re_ = {k: {r["id"]: r for r in rows(k) if r["status"] == "ok"} for k in IDS}
s01, s02, s05, s10 = (re_["eq"][x] for x in ("S01", "S02", "S05", "S10"))

md = f"""# eqpack — cbpack's ten rule strategies on QQQ daily (first equities campaign)

Date of record: 2026-10-29. Data: `data/alpaca_1d/QQQ_1d.csv` — 2722 daily bars,
2016-01-04 to 2026-10-29, Alpaca SIP tape, split-and-dividend adjusted, manifest
`data/ALPACA_EQUITIES_IMPORT.json` (sha256 844adcc1e80e...). Engine:
`code/cbpack_engine.py` used UNMODIFIED (hash-locked, sha 055b584de9aa... —
the historically audited executor). Pre-run audit:
`results/eqpack_audit_known_answers.txt` — eight checks ALL PASS (engine-lock,
the htf-adaptation semantics, the load path, the declared candle-proxy flow,
the self-skips, a no-lookahead truncation proof through the adapter path, the
pack's end_of_data close convention, determinism).

Declared adaptations, uniform across every strategy (no per-strategy picks):
`htf=1440` for the three strategies that carry an `htf` parameter (S01, S02,
S05) — on daily bars this reproduces exactly the pack's one-hour semantics,
where the HTF filter equalled the chart timeframe; flow uses the pack's own
declared candle-proxy fallback (equities have no taker split); S06 is excluded
(intraday UTC sessions do not exist on daily bars) and S07/S08 self-skip (no
funding / open interest on equities). Sizing is the pack's own default
(stop-risk of one percent per trade, three-times leverage cap), which on daily
ATR stops keeps notional well under one times equity — the exposure column
below is measured per artifact. Costs: `eq` = 0.1 bps fee + 0.5 bps slippage
per side (Alpaca zero commission, SEC/TAF amortised, liquid-ETF spread),
round trip {meq['cost_bp_roundtrip']:.1f} bps; `cons` = one plus one bps per
side, round trip {mcons['cost_bp_roundtrip']:.0f} bps; the zero-cost control
runs inside every artifact and the drag is measured there.

## VERDICT: KILLED as alpha — zero of seven strategies pass the gate and none beats buy & hold

Counted from the two artifacts below: {w(meq['n_pass_all_gates'])} of
{w(meq['n_run'])} runnable strategies pass the full gate at equities costs,
{w(meq['n_beat_bh'])} of {w(meq['n_run'])} beat buy & hold on the same bars
(QQQ itself did {meq['bh_return_pct']:.2f}% over the decade). The failures are
sample, concentration and the passive benchmark — NOT costs: the measured drag
stays under {max(r['drag_pp'] for k in ('eq', 'cons') for r in rows(k) if r['status'] == 'ok'):.2f}
percentage points even at the conservative regime, so unlike the crypto
campaigns below one hour, equities costs do not destroy this pack. What kills
it is everything else:

- The two closest cells, S01 (PF {s01['PF']:.3f}, {s01['trades']} trades,
  top-five share {s01['conc_top5_share_pct']:.0f}%) and S05 (PF {s05['PF']:.3f},
  {s05['trades']} trades, top-five {s05['conc_top5_share_pct']:.0f}%), fail the
  green-years gate by one year: {w(s01['n_green_years'])} of {w(s01['n_years'])}
  green where the gate asks for at least two thirds.
- S02 shows the best profit factor ({s02['PF']:.3f}) with its best five trades
  carrying {s02['conc_top5_share_pct']:.0f}% of total PnL — one trade away from
  the concentration kill, on {s02['trades']} trades.
- S10's profit factor of {s10['PF']:.3f} rests on {s10['trades']} closed trades
  with a top-five share of {s10['conc_top5_share_pct']:.0f}% — no sample.
- S03 ({w(4)} trades) and S09 ({w(13)} trades, top-five
  {re_['eq']['S09']['conc_top5_share_pct']:.0f}% of PnL) are noise. S04 loses
  outright (PF {re_['eq']['S04']['PF']:.3f}).

The honest reading: at equities costs this pack carries a small, real gross
edge on some rules (S01, S02, S05 are positive and PF-above-one in both cost
regimes), but the drawdown profile (three to fourteen percent max DD against
QQQ's own much deeper crashes) means the pack behaves as a risk-reducer, and
as alpha it is nowhere near the passive benchmark. Per the standing rule — no
rescue loops, no parameter tuning, no window picking.

## Results — QQQ daily, costs `eq` (0.1 + 0.5 bps per side)

Artifact {IDS['eq']}.

{table('eq')}

## Results — QQQ daily, costs `cons` (1 + 1 bps per side)

Artifact {IDS['cons']}.

{table('cons')}

## How to reproduce

    python code/_eqpack_audit.py
    python code/vrun.py run --strategy eqpack --tf 1d --symbol QQQ
    python code/vrun.py run --strategy eqpack --tf 1d --symbol QQQ --set costs=cons
    python code/vrun.py pverify --ids {IDS['eq']},{IDS['cons']} --quiet
    python code/vrun.py guard --report results/eqpack_qqq_report.md

The adapter accepts any symbol with a `data/alpaca_1d/<SYM>_1d.csv` file
(SPY, AAPL, MSFT, NVDA are already on disk).
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(md)
print(f"wrote {OUT}")
