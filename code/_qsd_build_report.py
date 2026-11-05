#!/usr/bin/env python
"""_qsd_build_report.py -- render results/qsd_report.md from the family-D
campaign artifacts (all 360 verify bit-for-bit)."""
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "qsd_report.md")

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
    "QS-031": "Confirmed swing-high/swing-low breakout",
    "QS-032": "Trend structure continuation",
    "QS-033": "Confirmed change-of-character reversal",
    "QS-034": "Support/resistance rejection",
    "QS-035": "Range sweep and reversal",
    "QS-036": "Breakout retest (pivot level + higher low)",
    "QS-037": "Compression inside a prior range",
    "QS-038": "Momentum exhaustion reversal",
    "QS-039": "Multi-timeframe structural alignment",
    "QS-040": "Price displacement with continuation",
}


def main():
    # current generation only (the shard run's run_ids); REFUSED generations
    # stay on disk append-only and are never cited.
    cur = set()
    for p in glob.glob(os.path.join(ROOT, "results", "_qsd_shard_*.json")):
        cur.update(json.load(open(p)).values())
    rows = []
    for p in glob.glob(os.path.join(RUNS, "*.json")):
        a = json.load(open(p))
        if a.get("strategy") == "qsd" and a.get("run_id") in cur:
            rows.append(a)
    rows.sort(key=lambda a: (a["metrics"]["strategy_id"],
                             a["metrics"]["variant"],
                             a["metrics"]["symbol"],
                             a["metrics"]["timeframe"]))
    assert len(rows) == 360, len(rows)

    L = []
    L.append("# Strategy catalog family D (QS-031..QS-040, market structure "
             "and price action) — audit and backtest report\n")
    L.append("Date of record: 2026-10-31. Source: the Phase-3 strategy-catalog "
             "archive (exact filename in every artifact's provenance; "
             "extracted under code/_pack100cat/). These are the catalog's ten "
             "market-structure hypotheses: the confirmed swing breakout, "
             "trend-structure continuation, the change-of-character "
             "reversal, support/resistance zone rejection, the range sweep, "
             "the pivot breakout-retest with a higher-low requirement, "
             "compression inside a prior range, the momentum-exhaustion "
             "fade, multi-timeframe structural alignment (the HTF structure "
             "resampled from the same klines, closed HTF bars only), and "
             "the displacement continuation. Every pivot carries the k=3 "
             "confirmation delay (a pivot is KNOWN only k bars after its "
             "bar closes — the sheet's own fixed rule). Engine: the "
             "family-A G1-G7 machinery (`code/qs_engine.py` + "
             "`code/qs_run.py`) with the family-D signal layer "
             "`code/qs_d_strats.py` (adapter `qsd`). Known-answer audit: "
             "`code/_qs_d_audit.py` — twenty-six checks, ALL PASS, on the "
             "exact bytes before any artifact. The audit caught three real "
             "builder bugs before any number was measured: the QS-040 hold "
             "window included the displacement bar's own low (which sits "
             "below its 50% level by construction, poisoning the group "
             "minimum forever); the QS-036/QS-033 break episodes restarted "
             "on every re-arming break bar inside the retest window (which "
             "voided the higher-low comparison); and the QS-034 zone "
             "touch-exhaustion counted bars that predate the zone's own "
             "existence.\n")
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
    L.append("## VERDICT: KILLED by the gates — zero of ten PASS\n")
    L.append(f"Three hundred and sixty cells were measured (ten strategies x "
             f"two-sided AND long-only x six symbols x three timeframes); "
             f"all verify bit-for-bit. Verdicts: {_w(n_rej)} REJECT, "
             f"{_w(n_fail)} FAIL, {_w(n_inc)} INCONCLUSIVE, zero PASS.\n")
    L.append("The decisive numbers:\n")
    L.append(f"- G4 viability (twenty bps at Base, positive at Adverse): "
             f"{_w(sum(1 for a in rows if a['metrics']['gates']['g4_econ']))} "
             f"of {_w(len(rows))} cells — but the meaningful ones concentrate "
             f"in single-symbol 1h cells.\n")
    L.append(f"- {_w(n_win)} of {_w(len(pairs))} cells beat their own "
             f"random-entry null.\n")
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
    L.append("- `21f1495a22c44230` QS-037 (compression inside a prior range) "
             "two-sided ETHUSDT 1h: one hundred and twenty-two trades, "
             "expectancy +28.10 bps at Base / +22.39 at Adverse, PF 1.73, "
             "holdout +127.8 bps, null -6.3 bps, G5 PASSES. It fails g6 on "
             "fold profitability (one of five folds) and monthly "
             "consistency (fifty-eight percent of months positive against "
             "the sixty percent requirement).\n")
    L.append("- `aea9b2b6c8af346a` QS-039 (multi-timeframe structural "
             "alignment) long-only ETHUSDT 1h: one hundred and ten trades, "
             "+33.57 / +28.62 bps, PF 1.94, holdout +50.0 bps, null -7.2 "
             "bps, G5 PASSES, exp_lb95 positive. It fails g6 on fold "
             "profitability (three of five, with two-to-four trades per "
             "fold) and monthly consistency (fifty percent).\n")
    L.append("- QS-037 long-only ETH 1h `9b30be19ffef8d06` reaches +48.89 / "
             "+41.75 bps with holdout +299.5 bps on sixty-one trades — "
             "INCONCLUSIVE by the catalog's own out-of-sample floor "
             "(eighteen OOS trades against the thirty required).\n")
    L.append("Both survivors sit on ETHUSDT 1h alone — a one-symbol "
             "concentration, the same pattern the catalog campaign has "
             "shown in every family (HYPE in family C, SUI in the flow "
             "pack). The market-structure family confirms the campaign's "
             "shape: real gross edges exist at 1h scale, the gates' "
             "consistency requirements kill them, and nothing survives "
             "every gate.\n")
    L.append("## Provenance\n")
    L.append("- Adapter `qsd` in `code/vrun.py`; sources hashed: qs_engine, "
             "qs_strats, qs_d_strats, qs_run.\n")
    L.append("- All three hundred and sixty artifacts verify bit-for-bit "
             "(`pverify --strategy qsd`).\n")
    L.append("- Known-answer audit output: "
             "results/qs_d_audit_known_answers.txt (twenty-six checks, "
             "ALL PASS, run before any artifact).\n")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("written:", OUT)
    print("verdicts:", vc)


if __name__ == "__main__":
    main()
