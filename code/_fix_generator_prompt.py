#!/usr/bin/env python
"""_fix_generator_prompt.py -- write a corrected copy of the generator prompt.

Reads the original from Downloads, applies the seven corrections identified in
results/doc_audit_2026-10-29.md, and writes the copy to results/. The original
is never modified. Every replacement must match exactly once; a miss aborts.

    python code/_fix_generator_prompt.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(os.path.expanduser("~"), "Downloads",
                   "STRATEGY_GENERATOR_PROMPT-GLM5.3.md")
DST = os.path.join(ROOT, "results",
                   "STRATEGY_GENERATOR_PROMPT-GLM5.3_corrected.md")

REPL = [
    # F4: unit of the multiple-testing count
    ("four killed 50-prompt packs (~200 candidate books, zero full passes)",
     "four killed 50-prompt packs (fifty prompts each, zero full passes)"),
    # F5: G8 is 2x the candidate's own block, not a fixed 22 bps
    ("at the pack's own block; the gate also tests 11 bps (repo) and 22 bps (2x).\n"
     "  A strategy must remain profitable at 22 bps round trip to pass G8.",
     "at the pack's own block; the gate also tests 11 bps (repo) and a stress at\n"
     "  twice the candidate's own per-side block (the 22 bps preset is kept as a\n"
     "  sensitivity). A strategy must remain profitable at that stress to pass G8,\n"
     "  and keep costs under 35% of gross profit."),
    # F8: which gate set owns the 100-trade floor
    ("- Sample size: the gates require >= 100 closed trades over the history (and\n"
     "  the out-of-sample half alone needs >= 30).",
     "- Sample size: the v2 gates require >= 100 closed trades over the history\n"
     "  (and the out-of-sample half alone needs >= 30); the v1 pack gates were\n"
     "  graded at 30."),
    # F4: strategies vs runs
    ("- Multiple testing: ~1,500 strategies have already been tried in this\n"
     "  pipeline. Your strategy is guilty of selection bias until proven otherwise;\n"
     "  prefer designs with a STRUCTURAL reason for the edge (mechanism, not\n"
     "  pattern-fit).",
     "- Multiple testing: about fifteen hundred backtest runs have already been\n"
     "  scored in this pipeline. Your strategy is guilty of selection bias until\n"
     "  proven otherwise; prefer designs with a STRUCTURAL reason for the edge\n"
     "  (mechanism, not pattern-fit)."),
    # F1 + F3: the family is not flatly dead, and the denominator is the pack's
    ("ignition copies, and every 1m/3m scalping book (33 of 42 such books were\n"
     "RUINED at these costs). \"ADX > 25\" as a filter on any of the above does not\n"
     "save it. Re-combos of these primitives with new stops/targets fail on signal,\n"
     "not on parameters \u2014 do not re-emit them with different constants.",
     "ignition copies below 15m and without a higher-timeframe regime gate\n"
     "(section 4 names the one 5m variant that came close), and every 1m/3m\n"
     "scalping book (in the Qwen pack, thirty-three of its forty-two runnable\n"
     "books ended the window ruined at these costs). \"ADX > 25\" as a filter on\n"
     "any of the above does not save it. Re-combos of these primitives with new\n"
     "stops/targets fail on signal, not on parameters \u2014 do not re-emit them with\n"
     "different constants."),
    # F7: state the near-miss's other failures
    ("1.32 on 266 trades, breakeven 14.3 bps per side, expectancy lower bound\n"
     "-0.57 bps (half a basis point short). The pattern across near-misses:",
     "1.32 on 266 trades, breakeven 14.3 bps per side, expectancy lower bound\n"
     "-0.57 bps (half a basis point short). It still fails the halves gate and\n"
     "five of the eight v2 gates: a template for the shape of an edge, not a\n"
     "strategy that almost passed. The pattern across near-misses:"),
    # F2: one book above 1.2, not a repeated result
    ("- Weekend/session gap fills on 1h bars repeatedly reached PF 1.2+.",
     "- Weekend/session gap fills on 1h bars are the only calendar family with a\n"
     "  book above PF 1.2 so far (1.3028, killed by concentration; the next best\n"
     "  is 1.1885)."),
    # F6: rotation was tested once
    ("rules \u2014 the pack never tested this family.",
     "rules \u2014 tested once as ds4 on thirteen symbols and killed; not tested in\n"
     "   the 50-prompt packs."),
    # F8: all seven symbols have all four taker timeframes
    ("JUP, XRP at 1m / 5m / 15m / 1h; XRP also at 15m/1m. OHLCV + taker-buy volume.",
     "JUP, XRP at 1m / 5m / 15m / 1h. OHLCV + taker-buy volume."),
]


def main() -> int:
    with open(SRC, encoding="utf-8") as fh:
        text = fh.read()
    for i, (old, new) in enumerate(REPL, 1):
        n = text.count(old)
        if n != 1:
            print(f"ABORT: replacement {i} matched {n} times, expected 1")
            print(repr(old[:90]))
            return 2
        text = text.replace(old, new)
    header = ("<!-- Corrected copy. The original is the file in Downloads,\n"
              "     STRATEGY_GENERATOR_PROMPT-GLM5.3.md, unmodified. -->\n"
              "<!-- Each edit is justified in results/doc_audit_2026-10-29.md. -->\n\n")
    with open(DST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(header + text)
    print(f"wrote {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
