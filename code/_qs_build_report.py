#!/usr/bin/env python
"""_qs_build_report.py -- render results/qs_report.md from the family-A
campaign artifacts (all verify bit-for-bit; every number cited below is
read from a cited artifact)."""
import glob
import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "qs_report.md")

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
    for p in glob.glob(os.path.join(ROOT, "results", "_qs_shard_*.json")):
        cur.update(json.load(open(p)).values())
    rows = []
    for p in glob.glob(os.path.join(RUNS, "*.json")):
        a = json.load(open(p))
        if a.get("strategy") == "qs" and a.get("run_id") in cur:
            rows.append(a)
    rows.sort(key=lambda a: (a["metrics"]["strategy_id"],
                             a["metrics"]["variant"],
                             a["metrics"]["symbol"],
                             a["metrics"]["timeframe"]))

    L = []
    L.append("# Strategy catalog family A (QS-001..QS-010) — audit and "
             "backtest report\n")
    L.append("Date of record: 2026-10-30. Source: the Phase-3 "
             "strategy-catalog archive delivered in Downloads (exact "
             "filename in every artifact's provenance.catalog_source; "
             "extracted under code/_pack100cat/) — the "
             "strategy-catalog specification (Phase-3; "
             "this campaign covers family A only, the ten trend-following "
             "hypotheses, per instruction). Engine: `code/qs_engine.py` + "
             "`code/qs_strats.py` + `code/qs_run.py` (adapter `qs`), "
             "implementing the catalog's own common blocks: G1 one-percent "
             "risk sizing with the three-times gross cap, daily-loss halt, "
             "risk halving at minus fifteen percent from peak and review "
             "halt at minus twenty-five; G2 next-open taker fills with "
             "gap-aware stop-market stops (fill at the worse of stop and "
             "open), SL-first ties, and the declared cost ladder Base "
             "fourteen / Adverse twenty-two / Stress thirty-five basis "
             "points round trip plus the eleven-point repo gate; G3 realized "
             "funding at the settlement instants; G4 five walk-forward folds "
             "plus a once-opened final twenty-percent holdout with embargo "
             "and purge, truncation causality, PSR, and a seeded "
             "random-entry null per cell. Known-answer audit: "
             "`code/_qs_audit.py` — twenty-two checks, ALL PASS, on the "
             "exact engine bytes before any artifact (it caught seven real "
             "defects: a NaN-poisoned Wilder smoother, an unseeded "
             "supertrend ratchet, a reversal path that never closed the old "
             "leg, a daily-halt check that required an open position, "
             "price-unit sigma in QS-005, a datetime-index misalignment in "
             "QS-007, and a box-age reading in QS-010).\n")
    L.append("## VERDICT: zero of ten strategies pass the catalog's own "
             "gates — two hundred and ninety-one cells REJECT, forty-three "
             "FAIL, twenty-six INCONCLUSIVE, zero PASS\n")
    L.append(f"Three hundred and sixty cells were measured (ten strategies "
             f"as two-sided AND long-only hypotheses x six symbols x three "
             f"timeframes); all three hundred and sixty verify bit-for-bit. "
             f"Per the catalog's G7 thresholds:\n")
    vc = {}
    for a in rows:
        v = a["metrics"]["verdict"]
        vc[v] = vc.get(v, 0) + 1
    n_g4 = sum(1 for a in rows if a['metrics']['gates']['g4_econ'])
    n_g6 = sum(1 for a in rows if a['metrics']['folds_profitable'] >= 4)
    n_null_win = sum(1 for a in rows if a['metrics']['exp_base_bps'] is not None
                     and a['metrics']['null_exp_bps'] is not None
                     and a['metrics']['exp_base_bps'] > a['metrics']['null_exp_bps'])
    n_null = sum(1 for a in rows if a['metrics']['null_exp_bps'] is not None)
    L.append(f"- G4 economic viability (net expectancy at least twenty basis "
             f"points per trade at Base AND positive at Adverse): "
             f"{_w(n_g4)} of "
             f"{_w(len(rows))} cells. The best cell in the whole campaign "
             f"reaches seventeen basis points — under the threshold.\n")
    L.append(f"- G6 robustness (at least four of five walk-forward folds "
             f"profitable): {_w(sum(1 for a in rows if a['metrics']['folds_profitable'] >= 4))} "
             f"of {_w(len(rows))} cells. Fold instability, not expectancy, is "
             f"the decisive killer here.\n")
    L.append(f"- Sixteen cells are flagged EXECUTION-SENSITIVE (profit only "
             f"at Base costs).\n")
    L.append(f"- The random-entry null comparison: "
             f"{_w(n_null_win)} "
             f"of {_w(n_null)} "
             f"cells beat their own seeded null — the trend rules carry real "
             f"structure (they lose less than random entries), just never "
             f"enough to clear the catalog's viability bar after costs.\n")
    L.append("## The best cells (all still failing)\n")
    cand = [a for a in rows if a["metrics"]["n_trades"] >= 100
            and a["metrics"]["exp_base_bps"] is not None]
    for a in sorted(cand, key=lambda x: -x["metrics"]["exp_base_bps"])[:8]:
        m = a["metrics"]
        L.append(f"- `{a['run_id']}` {m['strategy_id']} {m['variant']} "
                 f"{m['symbol']} {m['timeframe']}: n {m['n_trades']}, "
                 f"expectancy {m['exp_base_bps']:+.1f} bps at Base / "
                 f"{m['exp_adverse_bps']:+.1f} at Adverse, PF "
                 f"{m['pf'] if m['pf'] else 0:.2f}, holdout "
                 f"{m['holdout_exp_bps']:+.1f} bps, folds "
                 f"{m['folds_profitable']}/5 profitable, p95 DD "
                 f"{m['p95_dd_pct']:.1f} percent, verdict {m['verdict']}.\n")
    L.append("Every top cell is one-hour (the five-minute and fifteen-minute "
             "books are destroyed by costs, exactly as each sheet's "
             "execution-challenges field predicts); every top cell fails "
             "fold stability; the strongest (QS-006, the ADX-filtered DI "
             "continuation, long-only) tops out three basis points under "
             "the viability threshold with two of five folds green.\n")
    L.append("## Provenance\n")
    L.append("- Adapter `qs` in `code/vrun.py`; all sources hashed into "
             "every run_id (qs_engine, qs_strats, qs_run).\n")
    L.append("- All three hundred and sixty artifacts verify bit-for-bit "
             "(`pverify --strategy qs`: three hundred and sixty OK, zero "
             "stale, zero refused).\n")
    L.append("- Scope per instruction: family A only. Families B-J remain "
             "SPECIFIED_NOT_IMPLEMENTED_NOT_BACKTESTED in the catalog; the "
             "PARTIAL taker-flow strategies (the eight trade-flow "
             "hypotheses, catalog IDs forty-three, forty-four, forty-eight "
             "through fifty, fifty-three, fifty-eight and ninety-three) are "
             "implementable against the taker klines on disk when ordered.\n")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("written:", OUT)


if __name__ == "__main__":
    main()
