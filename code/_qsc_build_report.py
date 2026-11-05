#!/usr/bin/env python
"""_qsc_build_report.py -- render results/qsc_report.md from the family-C
campaign artifacts (all 336 verify bit-for-bit)."""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "qsc_report.md")

_WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
          6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
          11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
          15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
          19: "nineteen"}
_TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty",
         7: "seventy", 8: "eighty", 9: "ninety"}


def _w(n):
    if n < 20:
        return _WORDS[n]
    if n < 100:
        t, r = divmod(n, 10)
        return _TENS[t] + ("-" + _WORDS[r] if r else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return _WORDS[h] + " hundred" + (" and " + _w(r) if r else "")
    return str(n)


NAMES = {
    "QS-021": "ATR compression followed by expansion",
    "QS-022": "Bollinger Band squeeze breakout",
    "QS-023": "Realized-volatility regime breakout",
    "QS-024": "Opening-range breakout (UTC 00:00 anchor)",
    "QS-025": "Donchian breakout with volume confirmation",
    "QS-026": "NR7 range expansion",
    "QS-027": "Chandelier stop-and-reverse",
    "QS-028": "Failed breakout reversal",
    "QS-029": "Breakout with retest confirmation",
    "QS-030": "Breakout filtered by higher-timeframe regime",
}


def main():
    # current generation only (the shard run's run_ids); REFUSED generations
    # stay on disk append-only and are never cited.
    cur = set()
    for p in glob.glob(os.path.join(ROOT, "results", "_qsc_shard_*.json")):
        cur.update(json.load(open(p)).values())
    rows = []
    for p in glob.glob(os.path.join(RUNS, "*.json")):
        a = json.load(open(p))
        if a.get("strategy") == "qsc" and a.get("run_id") in cur:
            rows.append(a)
    rows.sort(key=lambda a: (a["metrics"]["strategy_id"],
                             a["metrics"]["variant"],
                             a["metrics"]["symbol"],
                             a["metrics"]["timeframe"]))
    assert len(rows) == 336, len(rows)

    L = []
    L.append("# Strategy catalog family C (QS-021..QS-030, volatility and "
             "breakout) — audit and backtest report\n")
    L.append("Date of record: 2026-10-31. Source: the Phase-3 strategy-catalog "
             "archive (exact filename in every artifact's provenance; "
             "extracted under code/_pack100cat/). These are the catalog's ten "
             "volatility-and-breakout hypotheses: ATR compression then "
             "expansion, Bollinger bandwidth squeeze, realized-vol regime "
             "breakout, the UTC-00:00 opening range (BTC/ETH/SOL, 5m/15m "
             "only — the catalog's own instrument restriction), Donchian "
             "with volume, NR7 expansion, the chandelier stop-and-reverse, "
             "the failed-breakout reversal, the breakout-with-retest, and "
             "the higher-timeframe-regime breakout (the HTF regime resampled "
             "from the same klines, closed bars only). Engine: the family-A "
             "G1-G7 machinery (`code/qs_engine.py` + `code/qs_run.py`) with "
             "the family-C signal layer `code/qs_c_strats.py` (adapter "
             "`qsc`). Known-answer audit: `code/_qs_c_audit.py` — "
             "twenty-three checks, ALL PASS, on the exact bytes before any "
             "artifact. The audit caught two real builder bugs before any "
             "number was measured: the bars-since helper (a cumsum-based "
             "formula that stays at zero between flags, which would have "
             "silently broken the within-N-bars windows of QS-026 and "
             "QS-028 on real data) and the QS-021 short mirror (both sides "
             "shared the top-30%-of-range close condition, so the short "
             "never fired on a bottom-closing expansion bar). It also "
             "corrected a spec reading: the failed-breakout recovery level "
             "is the broken 20-bar low, not the breakdown bar's own low.\n")
    vc = {}
    for a in rows:
        v = a["metrics"]["verdict"]
        vc[v] = vc.get(v, 0) + 1
    n_rej = vc.get("REJECT", 0)
    n_fail = vc.get("FAIL", 0)
    n_inc = vc.get("INCONCLUSIVE", 0)
    pairs = [(a["metrics"]["exp_base_bps"], a["metrics"]["null_exp_bps"])
             for a in rows
             if a["metrics"].get("exp_base_bps") is not None
             and a["metrics"].get("null_exp_bps") is not None]
    n_win = sum(1 for s, nn in pairs if s > nn)
    L.append("## VERDICT: KILLED by the gates — zero of ten PASS — but this "
             "family carries the first G5-passing edges of the whole catalog "
             "campaign\n")
    L.append(f"Three hundred and thirty-six cells were measured (nine "
             f"strategies x two-sided AND long-only x six symbols x three "
             f"timeframes, plus QS-024 x two variants x three symbols x two "
             f"timeframes); all verify bit-for-bit. Verdicts: {_w(n_rej)} "
             f"REJECT, {_w(n_fail)} FAIL, {_w(n_inc)} INCONCLUSIVE, zero "
             f"PASS.\n")
    L.append("The decisive numbers:\n")
    L.append(f"- G4 viability (twenty bps at Base, positive at Adverse): "
             f"{_w(sum(1 for a in rows if a['metrics']['gates']['g4_econ']))} "
             f"of {_w(len(rows))} cells — an order of magnitude more than "
             f"families A and B produced, and concentrated in 1h volatility "
             f"breakouts.\n")
    L.append(f"- {_w(n_win)} of {_w(len(pairs))} cells beat their own "
             f"random-entry null — between family A (trend, majority) and "
             f"the trade-flow pack (minority).\n")
    L.append(f"- {_w(sum(1 for a in rows if a['metrics']['execution_sensitive']))} "
             f"cells are EXECUTION-SENSITIVE.\n")
    L.append("- Per strategy (Base expectancy, null comparison, verdict mix):\n")
    for sid in NAMES:
        sub = [a for a in rows if a["metrics"]["strategy_id"] == sid]
        vc2 = {}
        for a in sub:
            v2 = a["metrics"]["verdict"]
            vc2[v2] = vc2.get(v2, 0) + 1
        first_rid = sorted(x["run_id"] for x in sub)[0]
        n_beat = sum(1 for a in sub
                     if a["metrics"].get("exp_base_bps") is not None
                     and a["metrics"].get("null_exp_bps") is not None
                     and a["metrics"]["exp_base_bps"] > a["metrics"]["null_exp_bps"])
        n_cmp = sum(1 for a in sub
                    if a["metrics"].get("exp_base_bps") is not None
                    and a["metrics"].get("null_exp_bps") is not None)
        vc2_w = ", ".join(f"{k} {_w(v)}" for k, v in sorted(vc2.items()))
        L.append(f"  - {sid} (e.g. `{first_rid}`, {NAMES[sid]}): beats its "
                 f"null in {_w(n_beat)} of {_w(n_cmp)} cells — "
                 f"{vc2_w}.\n")
    L.append("## The near-misses: two cells clear every gate except g6\n")
    L.append("The catalog's own verdict rule kills them; the honest record "
             "keeps what they cleared:\n")
    L.append("- `b59bf7e6e53987ac` QS-022 (Bollinger squeeze) two-sided "
             "JUPUSDT 1h: one hundred and sixty-five trades, expectancy "
             "+27.09 bps at Base / +25.71 at Adverse, PF 1.49, out-of-sample "
             "fifty-two trades, four of five folds profitable "
             "(+56.0 / +94.5 / +177.4 / +17.0 / -101.4 bps), holdout +13.57 "
             "bps, null -17.17 bps, G5 PASSES. It fails ONLY the monthly "
             "consistency sub-gate: fifty-two to fifty-four percent of "
             "months positive against the sixty percent requirement "
             "(p95 drawdown -30.68 and worst month -7.07 both pass).\n")
    L.append("- `5c2128e5190aa4b7` QS-022 two-sided HYPEUSDT 1h: one "
             "hundred and twenty-one trades, +36.64 / +32.21 bps, PF 1.57, "
             "holdout +29.95 bps, null -0.78 bps, G5 PASSES; fails g6 on "
             "both fold profitability (three of five, with single-trade "
             "folds) and monthly consistency (fifty-three percent).\n")
    L.append("- The big QS-023 (realized-vol regime) expectancies — +330.76 "
             "bps on HYPE (`70112723ff2582c4`), +84.12 on ETH "
             "(`35d22c8b49373a01`) — sit on eight-to-nineteen-trade samples "
             "and are INCONCLUSIVE by the catalog's own G5 floor; they are "
             "recorded, never ranked.\n")
    L.append("QS-022 (bandwidth squeeze then band break) is the strongest "
             "single hypothesis measured across the three catalog families: "
             "it clears viability AND the sample floor on two symbols at "
             "1h, and dies on monthly consistency, not on cost or sample. "
             "That is a pre-registered re-look candidate with more data, "
             "the same status the absorption cell holds in the flow family "
             "— and the same caution applies: the multiple-testing haircut "
             "over three hundred and thirty-six cells applies, and a "
             "two-symbol 1h concentration is a concentration fact, not an "
             "edge proof.\n")
    L.append("## Provenance\n")
    L.append("- Adapter `qsc` in `code/vrun.py`; sources hashed: qs_engine, "
             "qs_strats, qs_c_strats, qs_run.\n")
    L.append("- All three hundred and thirty-six artifacts verify bit-for-bit "
             "(`pverify --strategy qsc`).\n")
    L.append("- Known-answer audit output: "
             "results/qs_c_audit_known_answers.txt (twenty-three checks, "
             "ALL PASS, run before any artifact).\n")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("written:", OUT)
    print("verdicts:", vc)


if __name__ == "__main__":
    main()
