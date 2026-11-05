# AUDIT BRIEF — independent review of the backtest engine and its rules

You are auditing a backtesting pipeline that has rejected hundreds of
trading-strategy hypotheses (LLM-generated indicator strategies, delivered as
prompts and a specification catalog) while passing essentially none. The
author of the pipeline suspects nothing is wrong, but concedes the suspicion
is healthy and has packaged everything you need. Your job: determine whether
the rejections are correct, or whether the engine systematically produces
false negatives.

Everything below is a file in this package. No step requires the author.

## What the pipeline claims (the hypotheses under audit)

1. G1 — sizing: qty = (1% × equity) / (|entry − stop| + RT cost/unit),
   gross cap 3×, daily-loss halt 3%, risk halved at −15% from peak,
   review halt at −25%.
2. G2 — execution: signals evaluate on CLOSED bars; fills at the NEXT bar's
   open as taker orders; stops are stop-market filling at the WORSE of stop
   and open plus adverse slippage; SL-first when stop and target are both
   inside one bar; cost ladder Base 14 / Adverse 22 / Stress 35 bps RT
   (+11 bps repo point).
3. G3 — realized funding charged at actual settlement instants on the held
   position.
4. G4 — validation: 5 walk-forward folds + a once-opened final 20% holdout,
   embargo + purge, truncation causality, PSR, and a seeded random-entry
   null per cell.
5. G7 — verdicts: PASS requires net expectancy ≥ 20 bps/trade at Base,
   positive at Adverse, ≥ 4/5 folds profitable, P95 DD < 35%, ≥ 60%
   positive months, worst month ≥ −15%, PSR ≥ 0.95.
6. Every number in every report is generated from a persisted JSON artifact
   whose run_id = sha256(engine bytes + params + data hashes) and which
   verifies bit-for-bit by re-running the engine.

## The counter-evidence you must explain (or overturn)

The pipeline is not a universal shredder. Before concluding it produces
only false negatives, account for:

- One strategy PASSED every gate (XRP neutral book, 2026-10-22; engine in
  code/xrp_neutral_engine.py; STATUS.md entry "2026-10-22").
- Family A near-misses: QS-006 long-only HYPE 1h reached +17.0 bps/trade at
  Base and +14.1 at Adverse (artifact 2004f74a0e4fc2cc) — killed only by the
  fold-stability gate (2/5 folds), not by catastrophic arithmetic.
- QS-049 absorption SUI 5m reached +59.2 bps at Base / +30.9 at Adverse
  (artifact bd138f716573c90e) — above the 20 bps viability bar, killed only
  by sample size (17 trades < the catalog's own 30-trade G5 floor).
- Null calibration (results/gate_calibration_report.md): on real BTC data,
  the trend strategies beat their seeded random-entry nulls in the majority
  of cells — the engine distinguishes structure from noise; the null
  false-positive rate of the gate set was measured at 0–0.25% per candidate
  at high sample counts.

## Where the auditor should look hardest (ranked)

1. THE COST MODEL (results/cost_model_2026-10-25.json + code/funding_cost.py,
   code/_cbpack_cost.py). Measured 2026-10-25 on live books:
   RT = 2×taker_fee(5 bps) + spread + 2×impact_at_10k, ≈ 11 bps round trip.
   The median strategy's breakeven is 0.2–2 bps per side against 5.5–7
   charged, so costs — not signals — kill most candidates. If this
   measurement double-counts impact or uses the wrong spread percentile,
   hundreds of verdicts flip. INDEPENDENTLY RE-MEASURE IT.
2. GATE POWER vs the 20 bps threshold. The gate set is a CONJUNCTION of six
   conditions; each is individually reasonable, but joint power was never
   formally bounded. code/gatecal_engine.py + results/
   gate_calibration_report.md contain the measured power curve at 5/10/20
   bps planted edges through the real executor. Re-derive it: plant a known
   +20 bps/trade edge on synthetic and real series, run it through
   qs_engine.run + the G7 gates, and check the pipeline detects it. If a
   true 20 bps edge fails the gate set, the gates are miscalibrated and the
   author concedes the point.
3. THE FILL MODEL. Next-open fills are conservative relative to same-bar
   fills, and stop fills at the worse of stop/open are conservative. Verify
   there is no ADDITIONAL hidden cost: read qs_engine.run's fill branches
   line by line (every branch is a case in code/_qs_audit.py).
4. THE FOLD GATE (≥ 4/5 WF folds profitable). With 5 folds and moderate
   trade counts, a genuinely positive strategy can fail this by binomial
   variance. Check the power of this gate at the catalog's trade counts.
5. SIGNAL-QUALITY: the strategies being tested are LLM-generated indicator
   rules. The null calibration says they beat random entry more often than
   not but never by enough. The honest prior from the literature is that
   most published indicator edges are smaller than roundtrip costs. The
   audit question is not "why did everything fail" but "would a real 20 bps
   edge have been recognized" — which is test 2.

## File map

code/
  vrun.py               artifact harness: run_id = sha256(engine+params+data
                        hashes); verify (bit-for-bit reproduction), guard
                        (every report number must exist in a cited artifact),
                        pverify, matrix runners
  qs_engine.py          the G1/G2/G3 executor (sizing, gap-aware stops, cost
                        ladder, funding, risk devices) — the newest engine
  qs_run.py             G4/G7 validation: folds/holdout/embargo/purge,
                        truncation causality, PSR, random-entry null, gate
                        booleans, verdicts
  qs_strats.py          family A signal plans (QS-001..010)
  qs_flow_strats.py     trade-flow signal plans (QS-043/044/048/049/050/053/
                        058/093)
  pack50_core.py        the frozen earlier-generation executor (fills at next
                        open, SL-first, funding) behind the pack50/pack100
                        verdicts
  pack50b_engine.py / pack50b_strats.py / pack50d_engine.py /
  pack50d_strats.py     earlier pack layers the newer ones import
  gate2.py              v2 statistical gate layer (bootstrap, purged splits,
                        concentration, breakeven)
  gatecal_engine.py     the null/power calibration engine
  _qs_audit.py          known-answer tests for the family-A engine (22 checks)
  _qs_flow_audit.py     known-answer tests for the flow layer (22 checks)
  _qs_build_report.py / _qsf_build_report.py / _pack100_build_report.py
                        report renderers (reports are generated FROM the
                        artifacts; the guard step refuses any number that
                        does not exist in a cited artifact)
  funding_cost.py / _cbpack_cost.py   cost plumbing
  _pack100cat/strategy_catalog_100.json (+ .md)
                        the source specification catalog (100 strategies,
                        G1-G7 common blocks) the strategies were ported from

results/
  cost_model_2026-10-25.json          the measured cost model (AUDIT FIRST)
  gate_calibration_report.md          null false-positive rate + power curve
  methodology_audit_2026-10-25.md     the author's own self-audit of the
                                      framework (M1-M12), including the gaps
                                      flagged BEFORE this review
  repo_reaudit_2026-10-25.md          code-level findings F1-F12 on published
                                      engines (two real bugs found, incl. a
                                      lookahead in a passing strategy —
                                      measured CONSERVATIVE)
  qs_report.md / qsf_report.md / pack100_report.md   campaign verdicts
  qs_audit_known_answers.txt / qs_flow_audit_known_answers.txt
                                      the known-answer outputs
  runs/                               representative artifacts (JSON; each
                                      carries engine sha256, data hashes,
                                      params, metrics, trade tables). Full
                                      set is 2,888 files / 107 MB — a
                                      representative subset is included;
                                      every number in the reports traces to
                                      one of these.

data/ (sample, so one cell can be re-run end to end)
  binance_klines_1h_taker/BTCUSDT_1h.csv   1h klines with taker_buy fields
  binance_klines_15m_taker/BTCUSDT_15m.csv
  binance_funding/BTCUSDT_funding.json     funding history (t, r)

STATUS.md              the complete dated verdict log with run_ids

## How to re-run one cell end to end

  python --version        # 3.12.9
  pip install numpy==2.4.6 pandas==3.0.5
  python code/vrun.py run --strategy qs --tf 1h --symbol BTCUSDT \
      --params '{"strat":"QS-001","variant":"two-sided"}'
  # -> writes results/runs/<run_id>.json; compare with the packaged copy
  python code/vrun.py verify <run_id>
  # -> must print "reproduces bit-for-bit"

The artifact's metrics include every gate boolean, the null comparison, the
cost ladder, and the fold table. The trade tables (tables.kind == "trade")
carry entry/exit/qty/pnl per fill — hand-verify any trade against the CSV
bars and the declared G1/G2 rules.

## Sharpest falsification tests

1. Re-measure the cost model against live books at $10k notional. If true
   RT < 11 bps materially, re-run the campaigns.
2. Plant a +20 bps/trade edge (synthetic and real series) through
   qs_engine.run + the G7 gates. If it does not pass, the gate conjunction
   is underpowered — the author concedes this is the one unmeasured gap.
3. Hand-verify any single trade from any artifact's trade table against the
   CSV bars and G1/G2 rules.
4. Check the known-answer tests actually fail when the engine is broken:
   flip one constant in qs_engine.py, re-run _qs_audit.py, and confirm the
   audit catches it (mutation testing).
