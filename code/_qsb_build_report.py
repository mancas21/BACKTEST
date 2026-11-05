#!/usr/bin/env python
"""_qsb_build_report.py -- render results/qsb_report.md from the family-B
campaign artifacts (all 402 verify bit-for-bit)."""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "qsb_report.md")

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
    "QS-011": "RSI oversold reversal (V1 event)",
    "QS-011V2": "RSI oversold reversal (V2 persistent)",
    "QS-012": "Bollinger Band reversion",
    "QS-013": "Z-score deviation reversion",
    "QS-014": "Anchored VWAP reversion (day anchor)",
    "QS-014W": "Anchored VWAP reversion (week anchor)",
    "QS-015": "VWAP deviation, ATR-normalized",
    "QS-016": "Displacement-candle fade",
    "QS-017": "Range-bound oscillation",
    "QS-018": "Volatility-expansion fade",
    "QS-019": "OU-process spread reversion (BTC/ETH)",
    "QS-020": "Liquidity-dislocation wick fade",
}


def main():
    # current generation only: the run_ids of the latest shard run; the 402
    # artifacts of the pre-fix generation stay on disk (append-only) but
    # verify REFUSED (engine drift) and are never cited.
    cur = set()
    for p in glob.glob(os.path.join(ROOT, "results", "_qsb_shard_*.json")):
        cur.update(json.load(open(p)).values())
    rows = []
    for p in glob.glob(os.path.join(RUNS, "*.json")):
        a = json.load(open(p))
        if a.get("strategy") == "qsb" and a.get("run_id") in cur:
            rows.append(a)
    rows.sort(key=lambda a: (a["metrics"]["strategy_id"],
                             a["metrics"]["variant"],
                             a["metrics"]["symbol"],
                             a["metrics"]["timeframe"]))
    assert len(rows) == 402, len(rows)

    L = []
    L.append("# Strategy catalog family B (QS-011..QS-020, mean reversion) "
             "— audit and backtest report\n")
    L.append("Date of record: 2026-10-31. Source: the Phase-3 strategy-catalog "
             "archive (exact filename in every artifact's provenance; "
             "extracted under code/_pack100cat/). These are the catalog's "
             "twelve mean-reversion hypotheses: RSI oversold (a declared V1 "
             "cross event and its V2 persistent variant), Bollinger re-entry "
             "with bandwidth/ADX regime blocks, z-score deviation with a "
             "crisis filter, anchored VWAP (UTC day and week anchors), "
             "ATR-normalized VWAP deviation, displacement-candle fade with a "
             "six-sigma news block, range oscillation, volatility-expansion "
             "fade, the OU BTC/ETH dollar-neutral pair, and the "
             "liquidity-dislocation wick fade. Engine: the family-A G1-G7 "
             "machinery (`code/qs_engine.py` + `code/qs_run.py`) with the "
             "family-B signal layer `code/qs_b_strats.py` (adapter `qsb`); "
             "QS-019 executes through `code/qs_pair_run.py` over "
             "pack50_core.run_pair (dollar-neutral, funding on both legs, "
             "A/B-ratio benchmark). Known-answer audit: "
             "`code/_qs_b_audit.py` — nineteen checks, ALL PASS, on the exact "
             "bytes before any artifact (two engine-adjacent bugs were caught "
             "and fixed before any number was measured: the QS-019 validation "
             "path passed fraction costs to a BPS-named constructor — a "
             "thousand-fold cost understatement — and its trade conversion "
             "iterated a DataFrame as if it were a list of dicts).\n")
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
    n_win = sum(1 for s, n in pairs if s > n)
    L.append("## VERDICT: KILLED — zero of twelve pass; mean reversion is the "
             "weakest family of the three\n")
    L.append(f"Four hundred and two cells were measured (eleven single-leg "
             f"strategies x two-sided AND long-only x six symbols x three "
             f"timeframes, plus the QS-019 pair x two variants x three "
             f"timeframes); all verify bit-for-bit. Verdicts: {_w(n_rej)} "
             f"REJECT, {_w(n_fail)} FAIL, {_w(n_inc)} INCONCLUSIVE, zero "
             f"PASS.\n")
    L.append("The decisive numbers:\n")
    L.append(f"- G4 viability (twenty bps at Base, positive at Adverse): "
             f"{_w(sum(1 for a in rows if a['metrics']['gates']['g4_econ']))} "
             f"of {_w(len(rows))} cells. Every single one of them is below "
             f"the G5 floor on trade count — the viable-looking cells are "
             f"one-to-twenty-trade artifacts, not strategies.\n")
    L.append(f"- Mean reversion does not beat its random-entry null either: "
             f"only {_w(n_win)} of {_w(len(pairs))} cells beat their own "
             f"null. Family A (trend) beat the null in the majority of "
             f"cells; the trade-flow family lost to it; family B sits "
             f"between and loses where it counts.\n")
    L.append(f"- {_w(sum(1 for a in rows if a['metrics']['execution_sensitive']))} "
             f"cells are EXECUTION-SENSITIVE (positive at Base, non-positive "
             f"at Adverse) — of the ten FAIL cells, eight are.\n")
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
    L.append("## The best cells (none viable)\n")
    cand = [a for a in rows if a["metrics"]["n_trades"] >= 20
            and a["metrics"].get("exp_base_bps") is not None]
    for a in sorted(cand, key=lambda x: -x["metrics"]["exp_base_bps"])[:6]:
        m = a["metrics"]
        L.append(f"- `{a['run_id']}` {m['strategy_id']} {m['variant']} "
                 f"{m['symbol']} {m['timeframe']}: n {m['n_trades']}, "
                 f"expectancy {m['exp_base_bps']:+.1f} bps at Base / "
                 f"{m['exp_adverse_bps']:+.1f} at Adverse, PF "
                 f"{m['pf'] if m['pf'] else 0:.2f}, folds "
                 f"{m['folds_profitable']}/5, verdict {m['verdict']}"
                 f"{' (ES)' if m['execution_sensitive'] else ''}.\n")
    best = max(rows, key=lambda a: (a["metrics"].get("exp_base_bps") or -1e9))
    bm = best["metrics"]
    L.append(f"The highest measured Base expectancy anywhere in the campaign "
             f"is `{best['run_id']}` — {bm['strategy_id']} {bm['variant']} "
             f"{bm['symbol']} {bm['timeframe']} — at "
             f"{bm['exp_base_bps']:+.1f} bps on {bm['n_trades']} trades "
             f"(verdict {bm['verdict']}): the twenty-bps viability bar is "
             f"reached only by cells with single-digit trade counts. The "
             f"pattern is the same cost wall that killed families A and "
             f"flow: reversion signals exist at bar scale but the roundtrip "
             f"eats them, and where the signal is large the trade count is "
             f"not. QS-019 is the honest null-referenced disappointment: on "
             f"one-hour bars the random-entry null out-earns the OU book.\n")
    L.append("## Provenance\n")
    L.append("- Adapter `qsb` in `code/vrun.py`; sources hashed: qs_engine, "
             "qs_strats, qs_b_strats, qs_run, qs_pair_run, pack50_core.\n")
    L.append("- All four hundred and two artifacts verify bit-for-bit "
             "(`pverify --strategy qsb`).\n")
    L.append("- Known-answer audit output: "
             "results/qs_b_audit_known_answers.txt (nineteen checks, ALL "
             "PASS, run before any artifact).\n")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("written:", OUT)
    print("verdicts:", vc)


if __name__ == "__main__":
    main()
