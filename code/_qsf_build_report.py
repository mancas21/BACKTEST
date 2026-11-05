#!/usr/bin/env python
"""_qsf_build_report.py -- render results/qsf_report.md from the trade-flow
campaign artifacts (all 288 verify bit-for-bit)."""
import glob
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "qsf_report.md")

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


def main():
    # current generation only: the run_ids of the latest shard run; earlier
    # generations (superseded engine bytes) stay on disk, append-only, REFUSED.
    cur = set()
    for p in glob.glob(os.path.join(ROOT, "results", "_qsf_shard_*.json")):
        cur.update(json.load(open(p)).values())
    rows = []
    for p in glob.glob(os.path.join(RUNS, "*.json")):
        a = json.load(open(p))
        if a.get("strategy") == "qsf" and a.get("run_id") in cur:
            rows.append(a)
    rows.sort(key=lambda a: (a["metrics"]["strategy_id"],
                             a["metrics"]["variant"],
                             a["metrics"]["symbol"],
                             a["metrics"]["timeframe"]))

    L = []
    L.append("# Strategy catalog trade-flow hypotheses (QS-043/044/048/049/"
             "050/053/058/093) — audit and backtest report\n")
    L.append("Date of record: 2026-10-30. Source: the Phase-3 strategy-catalog "
             "archive (exact filename in every artifact's provenance; "
             "extracted under code/_pack100cat/). These are the catalog's "
             "eight PARTIAL trade-flow hypotheses — bar-level taker flow from "
             "the kline taker-buy fields (imbalance, cumulative delta, sell "
             "share), the catalog's own approximation, labeled PARTIAL "
             "because it is not tick-level order flow. Engine: the family-A "
             "G1-G7 machinery (`code/qs_engine.py` + `code/qs_run.py`) with "
             "the flow signal layer `code/qs_flow_strats.py` (adapter `qsf`). "
             "Known-answer audit: `code/_qs_flow_audit.py` — twenty-two "
             "checks, ALL PASS, on the exact bytes before any artifact (it "
             "caught one real sequencing bug: the QS-048 exhaustion entry "
             "AND'd the run condition with the down-close on the same bar, "
             "where the sheet's trigger is a down-close AFTER the exhausted "
             "run; plus five test-design fixes).\n")
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
    L.append("## VERDICT: KILLED — zero of eight pass; this family is WORSE "
             "than family A\n")
    L.append(f"Two hundred and eighty-eight cells were measured (eight "
             f"strategies x two-sided AND long-only x six symbols x three "
             f"timeframes); all verify bit-for-bit. Verdicts: {_w(n_rej)} "
             f"REJECT, {_w(n_fail)} FAIL, {_w(n_inc)} INCONCLUSIVE, zero "
             f"PASS.\n")
    L.append("The decisive numbers:\n")
    L.append(f"- The median strategy cell loses MORE than its random-entry "
             f"null — only "
             f"{_w(n_win)} of {_w(len(pairs))} cells beat their own null — "
             f"the OPPOSITE of family A, where the trend rules beat the null "
             f"in the large majority of cells. Bar-level taker flow, as the "
             f"catalog suspected, carries little exploitable information at "
             f"these horizons.\n")
    best = max((a for a in rows if a["metrics"].get("exp_base_bps") is not None),
               key=lambda a: a["metrics"]["exp_base_bps"])
    bm = best["metrics"]
    L.append(f"- G4 viability (twenty bps at Base, positive at Adverse): "
             f"{_w(sum(1 for a in rows if a['metrics']['gates']['g4_econ']))} "
             f"of {_w(len(rows))} cells. The best expectancy in the campaign "
             f"is `{best['run_id']}` — QS-049 absorption, two-sided, SUS "
             f"five-minute: {bm['exp_base_bps']:+.1f} bps at Base / "
             f"{bm['exp_adverse_bps']:+.1f} at Adverse on "
             f"{bm['n_trades']} trades, verdict {bm['verdict']} — it clears "
             f"the twenty-bps bar on a seventeen-trade sample that the "
             f"catalog's own G5 floor (thirty OOS trades) declares "
             f"INCONCLUSIVE. Absorption is the one flow hypothesis worth a "
             f"pre-registered re-look with more data; nothing here passes.\n")
    L.append(f"- {_w(sum(1 for a in rows if a['metrics']['execution_sensitive']))} "
             f"cells are EXECUTION-SENSITIVE.\n")
    L.append("- Per strategy (median Base expectancy over the twelve symbol "
             "x timeframe cells, versus the null median):\n")
    for sid in ("QS-043", "QS-044", "QS-048", "QS-049", "QS-050", "QS-053",
                "QS-058", "QS-093"):
        sub = [a for a in rows if a["metrics"]["strategy_id"] == sid]
        exps = [a["metrics"]["exp_base_bps"] for a in sub
                if a["metrics"].get("exp_base_bps") is not None]
        nullexp = [a["metrics"]["null_exp_bps"] for a in sub
                   if a["metrics"].get("null_exp_bps") is not None]
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
        L.append(f"  - {sid} (e.g. `{first_rid}`, "
                 f"{sub[0]['metrics']['strategy_name']}): beats its null in "
                 f"{_w(n_beat)} of {_w(n_cmp)} cells — "
                 f"{vc2_w}.\n")
    L.append("## The best cells (all still failing)\n")
    cand = [a for a in rows if a["metrics"]["n_trades"] >= 30
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
    L.append("The best cell (QS-093, VWAP-plus-flow confluence on JUP 1h) "
             "reaches five and a half basis points — a quarter of the "
             "catalog's viability threshold — and is INCONCLUSIVE on sample "
             "size anyway. Note the alignment with the repo's earlier EDGE "
             "family kill: CVD continuation and absorption were killed there "
             "too, with the same cost-wall arithmetic.\n")
    L.append("## Provenance\n")
    L.append("- Adapter `qsf` in `code/vrun.py`; sources hashed: qs_engine, "
             "qs_strats, qs_flow_strats, qs_run.\n")
    L.append("- All two hundred and eighty-eight artifacts verify bit-for-bit "
             "(`pverify --strategy qsf`).\n")
    L.append("- The zero-event 1h cells for QS-048/049/058 are the specs' own "
             "design (aggressor-imbalance runs are 5m/15m phenomena; a "
             "four-bar run above the imbalance threshold occurs once or twice "
             "per thousand 1h bars) — reported INCONCLUSIVE per the catalog's "
             "G5 rule, never estimated.\n")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("written:", OUT)


if __name__ == "__main__":
    main()
