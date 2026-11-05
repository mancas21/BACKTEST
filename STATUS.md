# Backtest System — Estado al 2026-09-26

## 2026-11-01 — Family D (QS-031..QS-040, market structure) KILLED by the gates, 0/10 — two more G5-passing near-misses, both on ETH 1h

The fifth catalog family under the same G1-G7 contract. Report
`results/qsd_report.md` (guard OK); known-answer audit
`code/_qs_d_audit.py` — twenty-six checks, ALL PASS, output
`results/qs_d_audit_known_answers.txt`.

- **Cells**: three hundred and sixty (ten strategies x two-sided AND
  long-only x six symbols x three timeframes). All three hundred and
  sixty verify bit-for-bit (`pverify --strategy qsd`).
- **Verdicts**: three hundred and five REJECT, twenty-four FAIL,
  thirty-one INCONCLUSIVE, zero PASS. G4 viability in fourteen cells;
  one hundred and fifty-eight of three hundred and fifty-nine beat the
  random-entry null.
- **All pivots carry the k=3 confirmation delay** (a pivot is known only
  k bars after its bar closes — the sheet's own fixed rule, enforced by a
  dedicated confirmation-bar machinery, never a rolling extremum).
- **The near-misses**: QS-037 (compression inside a prior range)
  two-sided ETH 1h `21f1495a22c44230` — one hundred and twenty-two
  trades, +28.10/+22.39 bps, holdout +127.8 bps, G5 PASSES, killed by
  folds (one of five) and monthly consistency (fifty-eight percent).
  QS-039 (multi-timeframe structural alignment) long ETH 1h
  `aea9b2b6c8af346a` — one hundred and ten trades, +33.57/+28.62 bps,
  holdout +50.0 bps, G5 PASSES, killed by folds (three of five, with
  two-to-four trades per fold) and months (fifty percent). Both sit on
  ETH 1h alone — the one-symbol concentration the campaign shows in
  every family. QS-037 long-only ETH 1h `9b30be19ffef8d06` reaches
  +48.89/+41.75 bps (holdout +299.5) on sixty-one trades — INCONCLUSIVE
  by the OOS floor.
- **Bugs caught before any number was measured** (twenty-six-check
  audit layer): (1) QS-040's hold window included the displacement
  bar's own low — below its 50% level by construction, poisoning the
  group minimum forever; (2) QS-036/QS-033 break episodes restarted on
  every re-arming break bar inside the retest window, voiding the
  higher-low comparison (fixed with spaced-edge anchors: a re-arm
  inside the window continues the same episode); (3) QS-034's zone
  touch-exhaustion counted bars predating the zone's own existence.
- **Hand-case lessons**: a swing period aliased with the pivot window
  (a 3-bar sawtooth against k=3) makes interior pivots structurally
  impossible; uniform warmup zigzags tie their own pivot values (no
  strict pivots); ATR/ADX need fourteen-plus warmup bars before any
  assertion; a fixed wick makes local peaks tie with the next bar
  (alternate the wicks).

## 2026-11-01 — EDGE project consolidated into this repo: imported, fixed, deduplicated

The sealed EDGE-first project (`Downloads/EDGE STRATEGY-2-V4-1-CLAUDE`, audited
in `results/edge_folder_audit_2026-10-29.md`) is now part of this repository and
the source folder is deleted. Its verdict does not change and it must not be
re-run: pre-registered batch A and B zero survivors, the sealed out-of-sample read
failed its own cluster-t gate, the v6 bridge stopped at P1, AMD reversal negative
before costs. Closure record: `results/edge_migration_2026-11-01.md` (guard OK,
words-only because there is no `run_id` behind a migration).

- **`edge/`** — the whole sealed project, 13.45 MiB after the cut: engine,
  `amd_engine`, tests, tools, **fifteen** dossiers, six spec files with their
  seals, ledger, figures, results, the three reports.
- **`recorder/`** — the LIVE Track R order-flow recorder at the repo root,
  2,304 MiB of day-partitioned parquet. Three live defects were fixed and
  measured: a two-process race (pids 17976 + 7460 writing the same files at
  once) closed with a named mutex in `keepalive.ps1`; `recorder_started_utc.txt`
  no longer rewritten on restart (it is the anchor of the 56-valid-day R_READY
  count, and every restart used to push the milestone to "today"); and
  `ParquetWriter` no longer truncates the current UTC day on restart — the day
  file is rotated to `{stream}.prev{HHMMSS}.parquet` (2026-10-28 measured 13.9
  MiB against 244.8 MiB on 2026-10-25 before the fix). Streams trimmed to the
  three with no bulk archive (bookTicker, depth@100ms, forceOrder): the other
  three were 40.2% of the on-disk volume and are re-downloadable.
  **The limit that cannot be fixed:** the machine was off overnight into
  2026-11-01 (no keepalive line for eleven hours), so that day is not a valid
  recording day and does not count toward R_READY.
- **`data/edge_panel/`** — the 1m kline + funding panel: 82 parquet, 1,082 MiB,
  **31 symbols** (not the 41 the project's universe list suggested), 581,760
  one-minute bars each, 2025-09-01..2026-09-30.
- **25 new symbols** resampled into `data/binance_klines_{1h,15m}_taker/`
  (9,696 and 38,784 rows per symbol) by `code/convert_edge_panel.py`, with
  sha256 manifest `data/EDGE_V41_IMPORT.json`. Verified: ADAUSDT 8/8 fields
  match an independent recompute, monotonic 3,600,000 ms steps, zero nulls, zero
  duplicates, and the manifest hash matches disk. Six symbols were skipped
  because the repo already had them.
- **`code/edge_stats.py`** — the one piece of code the repo lacked: vendored
  `edge/engine/stats.py` with a provenance header and a byte-identical body.
  It brings `benjamini_hochberg`, `spa_test`, `mde_bps`/`effective_n`,
  `cluster_t`, `matched_timing_null`, `circular_shift_null` and
  `factor_regression` — the FDR and power layer that `pack50` and `cand7` could
  not apply to their own trial counts. `python code/_edge_stats_vendor.py
  --check` proves the body has not drifted, and `python code/_edge_stats_audit.py`
  runs nineteen known-answer checks (all passing, output in
  `results/edge_stats_audit_known_answers.txt`): BH against an independent
  step-up implementation, `cluster_t` against a separately written CR1 formula,
  `effective_n` and `mde_bps` against hand values, SPA against a dominating trial
  and against an identical one, plus seed determinism. Writing the audit corrected
  two of my own wrong assumptions about the API — `effective_n` returns the
  cluster count for a balanced design, and `circular_shift_null` returns a pair.
- **Deleted, each verified by hash before deleting:** `docs/edge_v41/` (28
  files, all identical to `edge/`), `results/edge_v41/` (23 files, 22 identical
  to `edge/results/` and one identical to `edge/results/AMD/all_metrics.json`),
  the per-run `equity.csv`/`trades.csv` under `edge/results/AMD/` (39 dirs,
  144 MiB — the candidate is negative before costs, so the curves answer nothing;
  `metrics.json` and `all_metrics.json` kept), and the superseded launcher
  backup. With the source folder went its venv, the raw kline zips, the
  `aggTrades` bulk archive, mark/premium dumps and the original
  `data/processed/`.
- **Duplication audit:** `code/_find_duplicate_data.py` hashed 463 files /
  4,789 MiB across `data/` and `recorder/data` — **zero** byte-identical groups.
  The panel and the taker dirs describe the same market; they are not copies of
  the same bytes.
- **Not imported, on purpose:** the project's numbers (its evidence chain is
  commit + pre-registration hash + its own verifier, not `vrun verify`, so
  nothing there has a `run_id` and nothing there may be quoted as a result), its
  simulator/cost/data layer (this repo already has one engine and one cost
  model), and `amd_engine/`.

## 2026-10-31 — Family C (QS-021..QS-030, volatility and breakout) KILLED by the gates, 0/10 — but it carries the first G5-passing edges of the catalog campaign

The fourth catalog family under the same G1-G7 contract (after trend,
trade-flow and mean reversion). Report `results/qsb_report.md`'s sibling
`results/qsc_report.md` (guard OK); known-answer audit
`code/_qs_c_audit.py` — twenty-three checks, ALL PASS, output
`results/qs_c_audit_known_answers.txt`.

- **Cells**: three hundred and thirty-six (nine strategies x two-sided AND
  long-only x six symbols x three timeframes, plus the UTC-00:00 opening
  range QS-024 on BTC/ETH/SOL x 5m/15m — the catalog's own instrument
  restriction). All three hundred and thirty-six verify bit-for-bit
  (`pverify --strategy qsc`).
- **Verdicts**: two hundred and seventy-two REJECT, twenty-eight FAIL,
  thirty-six INCONCLUSIVE, zero PASS. G4 viability: seventeen of three
  hundred and thirty-six cells — an order of magnitude more than families
  A and B.
- **The near-misses (recorded, not rescued)**: QS-022 (Bollinger
  bandwidth squeeze, band-break trigger) two-sided JUP 1h
  `b59bf7e6e53987ac` — one hundred and sixty-five trades, +27.09/+25.71
  bps, PF 1.49, four of five folds profitable, holdout +13.57 bps, null
  -17.17 bps, G5 PASSES, killed ONLY by monthly consistency (fifty-four
  percent of months positive vs the sixty percent requirement). QS-022
  two-sided HYPE 1h `5c2128e5190aa4b7` — one hundred and twenty-one
  trades, +36.64/+32.21 bps, G5 PASSES, killed by folds and months.
  QS-022 is the strongest single hypothesis measured across all four
  catalog families and a pre-registered re-look candidate with more data
  (the multiple-testing haircut over the full grid applies).
- **Bugs caught before any number was measured** (the known-answer layer
  again doing its job): (1) the bars-since helper used a cumsum formula
  that stays at zero between flags — the within-N-bars windows of QS-026
  and QS-028 would have been silently broken on real data; fixed
  positionally. (2) QS-021's short mirror shared the long's top-30%
  close condition, so the short could never fire on a bottom-closing
  expansion bar. (3) The QS-028 recovery level is the broken 20-bar low,
  not the breakdown bar's own low (spec reading corrected by the hand
  case).
- **Declared gap-fillings** (sheets silent, nothing swept): QS-023's
  percentile window is 500 trailing bars; QS-024's anchor is UTC 00:00
  with a one-UTC-day time stop; QS-026's reference NR bar is the most
  recent one; QS-027's stop is the native trailing chandelier
  (best close since entry -/+ 3*ATR); QS-030's HTF regime is resampled
  from the same klines and maps back only after the HTF bar closes
  (truncation-causal, verified on real data).
- **State of the world**: four catalog families measured, zero PASS
  cells anywhere; family C is the first whose best cells die on
  consistency rather than on cost or sample size.

## 2026-10-31 — Family B (QS-011..QS-020, mean reversion) KILLED: zero of twelve pass the catalog G1-G7 gates

The third catalog family under the same contract as family A (trend,
`results/qs_report.md`) and the trade-flow pack (`results/qsf_report.md`).
Report `results/qsb_report.md` (guard OK); known-answer audit
`code/_qs_b_audit.py` — nineteen checks, ALL PASS, output
`results/qs_b_audit_known_answers.txt`.

- **Cells**: four hundred and two (eleven single-leg strategies x
  two-sided AND long-only x six symbols x three timeframes, plus the
  QS-019 BTC/ETH OU pair x two variants x three timeframes). All four
  hundred and two of the current generation verify bit-for-bit
  (`pverify --strategy qsb`; the four hundred and two pre-fix artifacts of
  the first generation stay on disk, append-only, and verify REFUSED by
  engine drift — never cited).
- **Verdicts**: three hundred and six REJECT, nine FAIL, eighty-seven
  INCONCLUSIVE, zero PASS.
- **G4 viability** (twenty bps Base, positive Adverse): five of four
  hundred and two cells, every one below the G5 trade floor —
  one-to-twenty-trade artifacts. The best measurable cell is QS-019 1h
  two-sided `ad15d7fbaaf993e1` (n thirty-four, +27.6 bps Base / +19.6
  Adverse, INCONCLUSIVE); on the same book the random-entry null out-earns
  the OU target at 1h.
- **Bugs caught before any number was measured** (the audit + smoke, both
  doing their job): (1) the QS-019 validation path passed fraction costs
  (0.0005) to `pack50_core.Costs`, whose fields are named `_bps` — a
  thousand-fold cost understatement that made Base and Adverse identical
  to the basis point; (2) its trade conversion iterated the run_pair
  DataFrame as a list of dicts; (3) the long-only variant was recorded in
  the metrics but never applied to the pair target (two-sided and
  long-only rows were byte-identical). All fixed; the fix superseded the
  first artifact generation, which was re-run in full.
- **Family-B hand-case lessons** (audit-test faults, not engine faults):
  QS-012's bandwidth median needs a finite 50-bar window, so the re-entry
  frame needs seventy-two-plus bars of swing history; QS-013's own crisis
  filter (|z| <= 4, vol below the 95th percentile) correctly refuses a
  fast crash — the hand case must be a slow drift that crosses -2 while
  staying inside the band; QS-016's volume condition needs a quiet
  baseline, not a uniformly loud one.
- **State of the world**: three catalog families measured, zero PASS
  cells anywhere. Mean reversion at bar scale is the weakest of the
  three: the reversion signals exist but the roundtrip eats them, and
  where the signal is large the trade count is not.
- **Engine-byte supersession handled the same day**: adding `rsi()` to
  `qs_engine.py` (needed by QS-011) changed the engine hash, so the whole
  family-A (three hundred and sixty cells) and trade-flow (two hundred
  and eighty-eight cells) stores verify REFUSED against the old bytes.
  Both campaigns were re-run in full on the new bytes: all six hundred
  and forty-eight cells reproduce their previous verdict AND Base
  expectancy exactly (zero changes — the addition is inert for those
  plans), and their reports were re-rendered from the current generation
  (`qs_report.md`, `qsf_report.md`, both guard OK again).

## 2026-10-31 — the hundred best books in the artifact store (READ-ONLY ranking): one validated book, forty-three strategies, and the books reproducibility removed

The user asked for the hundred best strategies ever tested here, best to
worst. No new backtest was run: the ranking is computed over the existing
artifact store. Deliverable `results/top100_2026-10-31.md` (guard exit 0,
eighty-seven cited artifacts); builder `code/_top100_rank2.py` +
`code/_top100_report.py`; machine table `code/_top100_rank2.json`.

- **Universe**: every artifact under `results/runs/` (two thousand nine
  hundred and fifty-five files, thirty-one adapters) collapsed to one row per
  measured book (adapter x strategy x symbol x timeframe). Pack-level
  aggregates and diagnostics are excluded (`gatecal`, `q10diag`, `gate2`,
  `mp20`, `mps20`, `cbot`, `cbpack` — the last because it is the same pack as
  `cbpackf` WITHOUT funding, so `cbpackf` is the honest copy).
- **Floors**: at least thirty closed trades, a finite profit factor above
  one, a positive net return, drawdown below ruin, no liquidated trade.
- **Reproducibility is a hard filter, not a footnote.** The sweep re-ran the
  representative artifacts under `pverify`: eighty-eight came back OK
  (bit-for-bit), thirty-four REFUSED (engine bytes changed since the run —
  treat as tampering) and eleven STALE (data files grew after the run). A
  book with no reproducible artifact is counted in the report and never
  ranked.
- **Result**: one hundred and two books clear every filter; the report lists
  the first hundred. Ordering is the one gate-passing book first, then profit
  factor descending (tie-break trade count). Head of the table:
  XRP delta-neutral grid v1 `295c21687960fadd` (PF 1.500, 5888 trades,
  +1598.19%, maxDD 10.18), pack100 F74-15m HYPE `3223187f21cf6708`
  (PF 3.206 on 38 trades, maxDD 70.84), botstrat SPX `f2aa1050b118e54f`
  (PF 3.079 on 31 trades), eqpack QQQ S02 `68c93ae390084b18` (PF 2.192).
  Tail `986ae236af7e6ad5` at PF 1.010; the cut at a hundred is presentational.
- **What the list is not**: it is books, not distinct strategies — the
  hundred rows come from forty-three strategy labels, because the same
  pack cell appears on several markets. Profit factors are not comparable
  across campaigns (each artifact records its own cost basis, from a
  fraction of a basis point to twenty round trip), and a high factor on a
  few dozen trades is arithmetic, not evidence. The verdict column records
  the campaign's own conclusion; no verdict was changed by this ranking.
- **What reproducibility cost**: forty-three net-positive books meeting the
  same floors have no reproducible artifact left. Among them the botstrat 15m
  cells (the adapter re-runs only the 1h file, so they can never reproduce),
  the pack50 S21 SOL cell `056f65013c9bc22f` and the cvrmd BNB cell
  `1e6d5ad221e0b6eb` (STALE: the funding and kline files grew after the run),
  and the smqe SUI cell `3a6053c52d7639f5` (REFUSED: engine drift). They are
  counted in the report, never in the table.

## 2026-10-30 (tarde) — trade-flow hypotheses (QS-043/044/048/049/050/053/058/093): KILLED — zero of eight pass; flow signals LOSE to random entry; QS-049 absorption flagged for a pre-registered re-look

The catalog's eight PARTIAL trade-flow strategies (bar-level taker flow from
the kline taker-buy fields — the catalog's own approximation, labeled
PARTIAL because it is not tick-level order flow), implemented as
`code/qs_flow_strats.py` on the family-A G1-G7 machinery (adapter `qsf`),
same executor, same risk sizing, same cost ladder, same validation. Data:
taker-buy fields verified present in all eighteen kline files.

- **Known-answer audit BEFORE any artifact**: `code/_qs_flow_audit.py` →
  `results/qs_flow_audit_known_answers.txt`, twenty-two checks ALL PASS. It
  caught one real sequencing bug (QS-048's exhaustion entry AND'd the run
  condition with the down-close on the SAME bar; the sheet's trigger is a
  down-close AFTER the exhausted run) plus five test-design fixes.
- **Measured**: two hundred and eighty-eight cells (eight strategies x
  two-sided AND long-only x six symbols x 5m/15m/1h), all verify bit-for-bit
  (`pverify --strategy qsf`: two hundred and eighty-eight OK). Verdicts:
  two hundred and twenty-three REJECT, one FAIL, sixty-four INCONCLUSIVE,
  **zero PASS**. Report `results/qsf_report.md` (guard OK).
- **The decisive finding, opposite of family A**: the flow rules LOSE to
  their own random-entry nulls — only one hundred and five of two hundred
  and thirty-seven cells beat their seeded null (family A: the large
  majority beat it). Bar-level taker flow carries little exploitable
  information at these horizons; several hypotheses (exhaustion, burst
  reversal, absorption fade) actively LOSE more than random. This aligns
  with the EDGE family kill already in this file (CVD continuation,
  absorption — same cost-wall arithmetic).
- **QS-049 absorption** (`bd138f716573c90e`): +59.2 bps at Base / +30.9 at
  Adverse on SUI 5m — the only cell above the twenty-bps viability bar —
  but on SEVENTEEN trades, which the catalog's own G5 floor (thirty OOS
  trades) declares INCONCLUSIVE. Flagged for a pre-registered re-look with
  more data; nothing passes.
- Zero-event 1h cells for QS-048/049/058 are the specs' own design
  (four-bar imbalance runs are 5m/15m phenomena) — INCONCLUSIVE, never
  estimated. Families B-J minus the flow eight remain unimplemented.


## 2026-10-30 — strategy catalog family A (QS-001..QS-010) under the catalog's own G1-G7 contract: KILLED — zero of ten pass; QS-006 is the nearest miss

Attachment `Downloads/100 strategies-claude.zip` = the Phase-3 strategy
catalog (100 specified hypotheses, ten families; JSON + md). Per instruction,
ONLY family A (the ten trend-following hypotheses) was implemented and
backtested, under the catalog's OWN common blocks rather than the repo's
pack conventions: G1 one-percent-risk sizing (qty = 1% equity / (stop dist +
RT cost/unit), gross cap 3x, daily-loss halt flat-and-block, risk halved at
-15% from peak, review halt at -25%); G2 next-open taker fills with
GAP-AWARE stop-market stops (fill at the worse of stop and open), SL-first
ties, cost ladder Base 14 / Adverse 22 / Stress 35 bps RT + the 11 bps repo
gate point; G3 realized funding at settlement instants; G4 five WF folds +
a once-opened final 20% holdout (embargo + purge), truncation causality,
PSR, and a seeded random-entry null per cell. Engine `code/qs_engine.py` +
`code/qs_strats.py` + `code/qs_run.py` (adapter `qs`); variants two-sided
AND long-only per the catalog.

- **Known-answer audit BEFORE any artifact**: `code/_qs_audit.py` →
  `results/qs_audit_known_answers.txt`, twenty-two checks ALL PASS. It caught
  seven real engine defects pre-data: a NaN-poisoned Wilder rma (every ADX
  filter was silently false), an unseeded supertrend ratchet (never flipped),
  a reversal path that never closed the old leg, a daily-halt check that
  required an open position (a same-day re-entry after an intrabar stop-out
  bypassed the ban), price-unit sigma in QS-005 (z could never exceed
  1e-4), a datetime-index misalignment in QS-007's HTF map, and a wrong
  box-age reading in QS-010.
- **Measured**: three hundred and sixty cells (ten strategies x two-sided
  AND long-only x six symbols x 5m/15m/1h), all verify bit-for-bit
  (`pverify --strategy qs`: three hundred and sixty OK, zero refused).
  Verdicts: two hundred and ninety-one REJECT, forty-three FAIL, twenty-six
  INCONCLUSIVE, **zero PASS**. Report `results/qs_report.md` (guard OK),
  built by `code/_qs_build_report.py`.
- **Why they die**: G4 viability (≥ 20 bps/trade at Base AND positive at
  Adverse) passes nowhere — the best cell reaches seventeen bps. G6
  robustness (≥ four of five WF folds profitable) passes nowhere — fold
  instability is the decisive killer. Sixteen cells are EXECUTION-SENSITIVE
  (Base-only profit). The null comparison is the honest silver lining:
  the trend rules beat their seeded random-entry nulls in the large
  majority of cells (they lose LESS than random), but never enough to clear
  the viability bar.
- **Nearest miss**: QS-006 (ADX-filtered DI continuation) long-only 1h —
  HYPE `2004f74a0e4fc2cc` (also JUP `72dbbae9805ec7f1`, SUI
  `55f12badd0a22027`); n 106, +17.0 bps at Base / +14.1 at
  Adverse, PF 1.39, holdout +78.6 bps, but two of five folds green → FAIL.
  All top cells are 1h; 5m/15m die on costs exactly as the catalog's own
  execution-challenges fields predict.
- **Scope note**: families B-J remain SPECIFIED_NOT_IMPLEMENTED; the eight
  PARTIAL trade-flow strategies are implementable against the taker klines
  on disk when ordered. The catalog's calibration grids were NOT swept
  (fixed rules only, declared); grid-DSR and PBO are recorded as pending in
  each artifact.


## 2026-10-29 — Sonnet 100-prompt pack (pack100): KILLED — zero of one hundred prompts pass as risk-specified; prompt 68 flagged as a sizing artifact with a real gross signal

Attachment `Downloads/strategy_prompts_100-sonnet-claude.md` (100 prompts,
numbered 01..100; multi-TF prompts expand one cell per timeframe per the
pack's own template). Adapter `ADAPTERS["pack100"]`: engine
`code/pack100_engine.py` + `code/pack100_strats{,2,3}.py` over the FROZEN
pack50_core execution machinery and the pack50d v2 gate definitions (imported
by identity, not copied). The pack declares no cost block, so the headline IS
the repo gate (5.0 fee + 0.5 slip bps per side); 2x, breakeven and zero-cost
controls live in every artifact. NO DATA, never estimated: fourteen NVDA
prompts, OI 95, long/short 96, JUP funding 94.

- **Measured**: two hundred and thirty-three cells verify bit-for-bit
  (`pverify --strategy pack100`: two hundred and thirty-three OK; the two
  superseded earlier generations, four hundred and sixty-three artifacts,
  verify REFUSED by design and are kept append-only). Two cells (C37 at 15m
  and 1h) produced zero trades — the prompt's own box filter never
  qualified — and are reported as measured. Report
  `results/pack100_report.md` (guard OK), built from the artifacts by
  `code/_pack100_build_report.py`.
- **The verdict numbers**: the median cell's zero-cost PF rounds to one
  (coin flip before costs); twenty-three of two hundred and thirty-two cells
  clear zero-cost PF one point two; the median breakeven side cost is a
  fraction of a basis point against the five and a half charged; twenty-three
  of two hundred and thirty-three cells end positive at repo costs; the
  median cell loses most of the account. The pack50-family pattern (0/46,
  0/42, 0/48) extends: 0/100 as risk-specified.
- **Prompt 68 (order-block retest, ETH, 5m/15m/1h — `e700ec8b52943139`,
  `ab11d9e0d116a63b`, `e623e7768e7ad2e3`) is the only gate passer and is
  DECLARED A SIZING ARTIFACT, not a result**: its zero-cost PF of eight to
  sixteen is the strongest gross book any pack has shown here, but the pack
  executor's declared full-equity sizing applied to one-candle-high order
  block stops (a tenth to a third of a percent on 5m ETH) is a
  hundred-to-one risk per trade — the prompt's own one-percent-risk spec is
  NOT what the pack50 executor implements — and stop fills carry no
  gap-through stress. Candidate for a properly risk-sized re-test; nothing
  more.
- **The port's own bug harvest (all caught, all re-run)**: the smoke test
  killed ten builder-bug classes before any artifact existed (argument
  shapes, a self-contradictory A03 entry, a swapped supertrend return, an
  inverted F68 short stop — the inversion produced a multi-billion-percent
  first run that BOTH gate layers passed, because the bug's profits were
  statistically consistent; only reading the magnitude caught it). Lesson
  for the gate layer, now recorded: statistical consistency does not imply
  physical plausibility — magnitude sanity checks belong in the report step.


**Refresh (2026-10-29).** The day's data extension (every 1h kline +159 bars,
every funding json +84 prints) made the seven artifacts STALE, so the batch was
re-run verbatim — same prespecified candidates, same parameters, no re-fits —
through the same adapter. New artifacts, all `pverify`-clean, report re-rendered
(guard OK):
C1 `c1213a34bbd85b49`, C2 `d6a2e71b02126d68`, C3 `7f09a78aede368e6`,
C4 `293ed0b0ccf3b3c8`, C5 `04362ac9748dd828`, C6 `e02625eed7daa3f0`,
C7 `c48057ec91da83e0`.
**Verdict unchanged: zero of seven clear v1 or v2.** C7 still fails only the
concentration gate at v1 (top-5 share 191.49% of PnL, -2.27% without them —
identical to two decimals); C2 still twelve trades at 285% concentration; C5
still fires its dispersion gate on three days; C4's benchmark is still +14.94%.
The old seven artifacts remain on disk as frozen evidence of the 2026-10-28 run.

## 2026-10-25 (tarde) — smqe engine v2: flip-sizing fix + methodology views; SUI's "beats B&H" inverted by the exposure-matched comparator

After the repo + methodology audits, the smqe engine was revised and the
whole 47-cell campaign re-run (new run_ids; the old generation plus the
`f3261c37e880f844` smoke artifact are superseded by design, recorded in
`code/_engine_lock.json` known_superseded; append-only kept).

- **Audit now forty-four checks ALL PASS** (`results/smqe_audit_known_answers.txt`).
  The revision caught a THIRD real bug in the engine's first generation: the
  flip branch computed pre-flip sizing equity and never used it — reversals
  were sized off POST-flip equity, contradicting the docstring. A zero-fee
  test case could not distinguish the two (E15 now runs with fees).
- **Timing sensitivity (audit M8), measured in-artifact**: identical signals
  filled at the next bar's open move every verdict cell by at most ~0.04pp
  of net return and ~0.003 of PF (`timing_drag_pp`, `pf_nextopen` in every
  artifact). The kills and the survivors do not depend on the same-close
  convention.
- **Exposure-matched comparator (audit M4), measured in-artifact**
  (`exposure_pct`, `bh_inmarket_pct`, `excess_vs_inmarket_pp`): the smqe
  book is in position only ~2% of bars. **SUI 1h's headline "beats B&H
  (−31.0%)" inverts**: passively holding SUI over exactly the strategy's
  in-market bars returns +37.7% against the strategy's +16.1% (−21.6pp).
  Its raw-B&H win was cash drag on a falling coin, not timing skill. The
  SUSPENDED verdict stands, now with a fourth reason. JUP 1h (+21.4pp over
  in-market) and BNB (+5.3pp) are the only cells positive vs their
  in-market passive; SOL is −187.9pp (the B&H kill was right).
- **Null calibration at smqe geometry (DIAGNOSTIC, no artifact)**: three
  hundred random-signal seeds through the smqe executor, BTC 1h full
  history, repo costs — median PF 0.766, p95 1.065, max 1.418, per-cell
  PF>1.2 & n≥30 false-positive rate 1.3% (expected false survivors across
  the 47-cell sweep ≈ 0.6). SUI's PF 1.828 is above the sampled null
  maximum; **SOL's PF 1.404 sits INSIDE the null's extreme tail** — one
  more reason its buy&hold kill stands. (Short-sample regime calibration
  in the methodology audit: 5% per cell at the n≈75 geometry.)

## 2026-10-25 — SMQE v2 (Smart Money Quant Engine: SMC + MA-OB + CVRMD fusion): KILLED; SUI 1h SUSPENDED

Attachment `Downloads/fingrad-entry scanner/smqe_v2_strategy.pine` (Pine v6
strategy build), copied BYTE-IDENTICAL to `code/smqe_v2_strategy.pine`
(sha256 `031730fabb9cc289fac78d5f9c2623d56d2bd7e6c168538e6d1eb87c428ec1f9`).
Port: `code/smqe_engine.py` (adapter `ADAPTERS["smqe"]`, version `smqe-1`).
Static finding that shapes everything: the Pine ships three engines, but every
confluence gate that would wire the SMC and MA-OB engines into trading is an
opt-in input defaulting to FALSE — the shipped strategy is the CVRMD v1.1 core
(MACD 12/26/9 histogram divergence on strict 3/3 pivots, sep 5..60, session
VWAP −1σWelford band touch-and-close-back, CLV×volume CVD slope EMA3/5, RSI14
arms 35/65 or the 50-line cross) under a NEW execution layer vs the repo's
killed `cvrmd` adapter: min-stop floor 0.2% of price, TP1-half at
VWAP-if-favourable else 1.5R, TP2 at 2R, TRUE reversals (close+reopen at the
signal close, process_orders_on_close), constant 0.01%/8h funding ledger booked
OUTSIDE strategy equity (feeds the daily breaker and net return, not sizing —
Pine design), 3% daily-loss breaker, 30% equity-DD killswitch. The SMC/MA-OB
engines are display-only in this configuration and are not ported (declared in
the engine docstring).

- **Known-answer audit BEFORE any real-data run**: `code/_smqe_audit.py` →
  `results/smqe_audit_known_answers.txt`. Cases in words: **forty**; failures:
  **zero**. It caught one REAL engine bug that the smoke run had silently
  carried — the TP1 partial exit never reduced `qty`, so the remainder rode at
  full size (a stopped remainder paid double) — and one cost-model bug (the
  adapter smoke artifact had the repo slip at 5 bps instead of 0.5 bps; the
  corrected engine re-audited 40/40 before the campaign).
- **Campaign**: 1h × fourteen symbols + 15m × seven + 5m × seven, two
  windows (full history; the Pine's own `sim_start=2024-01-01` where the data
  predates it), repo costs 5+0.5 bps = 11 bps RT primary with pine-cost and
  zero-cost views measured inside every artifact. JUPUSDT lives only in the
  taker directories (2024-10 onward) — the adapter falls back to them; the
  harness-native 5m files are two-month stubs, so the 5m sweep runs on the
  taker directory. Forty-seven artifacts; `pverify --strategy smqe` =
  forty-seven OK bit-for-bit, zero stale. Report `results/smqe_report.md`
  (guard OK), built from the artifacts by `code/_smqe_build_report.py`.
- **15m: dead, and NOT the cbpack cost pattern** — the signals are
  gross-negative on the majors (zero-cost PF: BTC `8759c0ac6f0dc3f0` 0.829,
  ETH `c6daa79bf2803eb3` 0.929, SOL `1b07fe3236195f8d` 0.885), every cell net
  PF < 1, and BTC/ETH/SOL/XRP tripped the 30% killswitch. XRP's zero-cost
  +13.64% (`045ec80fc588c92c`) dies under a 40.9pp drag.
- **5m (added after review): every one of the seven taker symbols fails.**
  Best PF is JUP 1.019 (`7e034fb9f6b89883`) — under every gate, with its
  best five trades at 673% of PnL; BTC/ETH/SOL tripped the 30% killswitch
  (BTC `0e587dcc30438f6d` PF 0.420 net −27.47%). **JUP 1h**
  (`6ea16247450d058b`) is the closest miss after SUI: PF 1.204, net +2.20%
  vs B&H −68.0%, but n=24 (INSUFFICIENT_SAMPLE) and best-five 359.9% of PnL
  (without them −259.9%) — a handful of trades on a falling coin. JUP 15m
  (`ea3bf48abceab5f9`) PF 0.689, dead.
- **1h full history: eleven of fourteen symbols fail PF or sample size.** SOL
  clears the trade gates (PF 1.404, n 83, best-five 63.6% of PnL, frozen-2023
  split test PF 1.390 n 61 — `ece0ce3f12b1c9fa`) and loses to buy & hold
  +2920% — not alpha by the repo rule. BNB (`4f31584e29761698`, PF 1.141,
  best-five 148%) and XRP (`e8f1794fe5593083`, PF 1.036, best-five 534%) fail
  PF and concentration together. BTC −17.30% vs B&H +706% (`5a4415397fda0e0f`).
- **Pine window (2024+)**: ETH `d7de0ccd8572e828` PF 1.369 dies on
  concentration (best-five 138%); SUI beats the strategy but not its B&H; SOL
  beats a flat B&H on thirty-six trades with best-five 76.7% (`f0b847173b59a137`).
- **SUI 1h — SUSPENDED, the one cell never falsified**
  (`3a6053c52d7639f5` full / `62ce63b88079c4e8` 2024+): net +16.06%, PF 1.828,
  n 49, wr 46.9%, maxDD 5.08%, 3/3 period-thirds green, every calendar year
  green, both sides positive, beats B&H (−31.0%), best-five 59.0% of PnL, cost
  drag 2.93pp. Why suspended, not validated: SUI's klines on disk start
  2023-05-03, so no out-of-sample split exists (the frozen-2023 legs are
  vacuous zeros in the artifact); it is the maximum over forty-seven cells;
  n is forty-nine; and this is the SAME core STATUS already killed as "recent
  and n-sensitive". The forward path is a paper bot, not a deployment; nothing
  was deployed.
- Provenance note: one superseded smoke artifact `f3261c37e880f844` (pre-fix
  cost constant) verifies REFUSED by design and is cited nowhere; kept under
  the append-only rule. `_matrix_smqe.csv` holds the second pass; both passes'
  ids are in the report tables.

## 2026-10-24 — hmaaoadx: SECOND port of Fingrad HMA · AO · ADX: KILLED

Same Pine attachment as the entry below, re-ported a second time independently
as `code/hmaaoadx_engine.py` (adapter `ADAPTERS["hmaaoadx"]`, version
`hmaaoadx-1`) under the dspack scorer contract: the Pine runs verbatim (modes
confluence / A / B / either / Literal; non-repainting HTF HMA filter;
min-ATR-share cost gate; next-open fills; 2×ATR hard stop armed from the FILL
price, stop-first on spanning bars, gap-open fills at the open; 1%-risk sizing
10×-capped; 3% daily-loss breaker; reverse-on-opposite) and the SCORING reuses
`dspack_engine._score_trades`/`_gates` verbatim (INIT 1000, G1..G6 gate set,
halves/years, zero-cost control embedded per artifact with the Pine cost gate
ON in both passes). Pine primitives (rma/atr_pine/dmi_pine/cross_over/
cross_under) imported BY IDENTITY from the audited `emaadx_engine.py`. All
FOUR sources hashed into every run_id (`fingrad_hma_ao_adx_strategy.pine`
byte-identical author copy, sha256
`d3aabd19a1795f3020f0b26f659e1710e60c1dc5c4e3db66eb65f2b02f58b860`,
`emaadx_engine.py`, `dspack_engine.py`, `hmaaoadx_engine.py`). 1h only (the
harness refuses every other timeframe for this engine). Parameters stay the
Pine defaults; CLI params are `window`/`costs` only.

- **Known-answer audit BEFORE any real-data run**: `code/_hmaaoadx_audit.py`
  → canonical `results/hmaaoadx_audit_known_answers.txt`. Cases in words:
  **forty-two**; failures in words: **zero**. The pass caught three real
  engine bugs that survived the A-block identity checks:
  (1) order routing sent EVERY order through the close branch (`kind =
  pending[0]` string-indexed the tuple; fixed to `kind = pending`) — visible
  as junk zero-qty "S" rows with entry 0.0 on every replay case;
  (2) intrabar stop fills degraded the level by ABSOLUTE slippage (`px −
  slip`) instead of the relative fraction — fixed in the engine AND in the
  audit's independent replay mirror; exposed by the hand-arithmetic gap
  assertion (bar-50 open 88 must fill 88 × (1 − slip) = 87.956, not 87.9995);
  (3) the daily-halt close-all one-tuple crashed reading `kind[1]` (verdict
  branch split; close-all fill 96 × (1 − slip) = 95.952).
  Case designs pinned, not diagnostic: B4 crashes while the position is fresh
  and OPENS through the stop (gap rule); B7 sets `atr_stop_mult = 0` (legal
  uncapped input state) because with 1%-risk/2×ATR sizing one stop-out is
  about one percent of equity, so a 3% intraday breach is unreachable inside
  ninety-six bars; B1 pins the CORRECT Pine behavior that an HMA catch-up can
  signal-exit a fresh ramp trade at a small loss (entry 99.0495 → exit
  98.9505). A-block fixes that round were ON THE AUDIT SIDE only (ref_rma
  seed-state inversion, A1 hand expectation, A5b re-expressed as pandas ewm
  over `[sma_seed]+tail`, C6 rebuilt to feed a full 6800-bar file).
- **Campaign**: 1h × thirteen canonical symbols × two windows (`full`,
  `last6mo`) × repo6x5 = twenty-six artifacts (in words: **twenty-six**), data
  honest: every symbol's file runs to 2026-10-24 except
  `HYPEUSDT_1h`/`SPXUSDT_1h` (stored end 2026-09-26); BTC full window 62466
  bars 2019-09-08..2026-10-24; last6mo windows are the last 6768 bars (2400
  warmup + 4368 scored). Six artifacts spot-verified bit-for-bit
  (`2c39ad6ee53a29d3`, `1ad620e45d05f27b`, `b618c6e7552052d2`,
  `53f78bc812a660b5`, `db79eead9b6cc841`, `d99675b84e223c36`).
- **Verdict — profitable cells, in words: ZERO of TWENTY-SIX** (full positives
  zero; last6mo positives zero); strict PF below one on EVERY cell; cells
  passing all gates in words: **zero**. Full window: PF 0.6132 (SOL
  `5666e45fecdc714a`) .. 0.9549 (SUI `b618c6e7552052d2`), returns −69.98%
  (BNB `22a8d44e90047e9e`) .. −2.63% (HYPE `1ad620e45d05f27b`); BTC full
  `f844336f4f6d3440` −69.67% PF 0.6690 (924 trades, maxDD −75.89%). last6mo:
  PF 0.1419 (SOL `db79eead9b6cc841`) .. 0.9999 (NEAR `d99675b84e223c36`,
  return −0.00%). G1/G3/G4/G6 pass zero cells anywhere; G5 (beats B&H) pass
  ONLY where the symbol's own market fell — full: SPX `98cb16430b8ec720`, SUI
  `b618c6e7552052d2` (in words: two); last6mo: ADA `53f78bc812a660b5`, AVAX
  `96a749540a540461`, DOGE `267f8c8faf28ceda`, XRP `110116926f9d15c2` (in
  words: four). `n_open_at_end` zero on every artifact.
- **Structure of the death** (from the embedded zero-cost controls; counts in
  words): thin gross edge is REAL on most symbols — pf_zero above one on
  eleven of thirteen full cells (SOL 0.8807, SPX 0.9648 below) and eight of
  thirteen last6mo cells — but no survivor anywhere. With 1%-risk/2×ATR
  sizing each close turns a large share of equity, so the 6+5 bp round trip
  at seven-hundred-plus to nine-hundred-plus closes per symbol grinds MOST of
  the account: zero-cost ETH full +99.43% → scored −32.30% (stored drag
  131.73 pp, `72e0613bfc121cf6`); BTC full drag 110.88 pp (`f844336f4f6d3440`).
  SOL full ret_zero −19.53 (pf_zero 0.8807, `5666e45fecdc714a`) and SPX full
  ret_zero −1.98 (pf_zero 0.9648, `98cb16430b8ec720`) have NO gross edge even
  fee-free. Best gross cell on the grid, BTC last6mo `233f9a552f4bd4e7`
  pf_zero 1.6867, still scores −6.80% — the thin tendency never clears the
  cost load.
- **Consistency with the port below**: identical verdict to the 2026-10-23
  `fingrad` pack (one hundred twenty artifacts, KILLED; BTC zero-cost +42.39%
  vs costed −28.11%). Two independent ports, same conclusion: the signal has
  a real but thin gross tendency that the required cost load consumes on every
  symbol, and the earlier sweep's best-looking cells were
  trade-concentration artifacts, not edge. No parameter surgery attempted.
- **Report**: `results/hmaaoadx_report.md` (vrun GUARD OK — every metric
  number backed by all twenty-six run_ids cited here; derived counts in
  words; generator `code/_hmaaoadx_report.py`). Full artifacts
  `results/runs/<run_id>.json`.

## 2026-10-23 — Fingrad HMA · AO · ADX port: KILLED

New deliverable: the requester's Pine v6 file from Downloads
(`fingrad_hma_ao_adx_strategy.pine` — two systems over one Hull MA: A = HMA +
Awesome Oscillator (above zero AND rising for longs, mirrored for shorts),
B = HMA + ADX cross-above-25 within a three-bar window with DI direction
(mirrored: BOTH sides use the cross-ABOVE event; the shipped "Literal" mode
shorts on the cross BELOW), confluence / A / B / either signal modes, a
non-repainting HTF HMA filter via the security [1]/[2]+lookahead_on idiom, a
minimum-ATR cost gate, edge-triggered entries on the WHOLE state, next-open
fills, ATR(2x) hard stop with risk-based sizing (1% per stop, 10x cap), a
three-percent daily-loss breaker, reverse-on-opposite). Ported as
`code/fingrad_engine.py` (adapter `fingrad`, Pine copied byte-identical to
`code/fingrad_hma_ao_adx_strategy.pine`, sha256 d3aabd19a1795f30...),
discipline per the ports rule:

- **Known-answer audit FIRST** (`code/_fingrad_audit.py`, output
  `results/fingrad_audit_known_answers.txt`): twenty-two checks ALL PASS —
  primitives vs naive references (wma/sma/hma floors/rma seed/dmi/crossover/
  barssince), hand-computed execution answers (next-open fill + per-fill fees,
  edge trigger, FIRST-bar bracket anchored at the signal close vs management
  re-anchor to the fill from bar two, stop-first ties, gap-through stops fill
  AT THE OPEN like TV's stop->market, reversal on one fill with the signal
  exit suppressed that bar, risk sizing + maxLev cap, daily breaker
  close_all/no-re-entry/next-day reset, long-wins-tie), cash identity with
  funding on real data, no-lookahead truncation on BTC 1h (signals, equity
  prefix and trades byte-identical), a vectorized-vs-loop DUAL of the whole
  signal layer across every signal mode x ADX mode, hand-checked HTF pair
  mapping, HTF no-lookahead, harness determinism.
- **Harness adapter** (`fingrad` in `code/vrun.py` ADAPTERS): 1h/15m/5m files,
  the strategy's OWN shipped knobs only (sig_mode, adx_mode, preset, exit
  auto-resolution), three cost sets (author = 5 bps + declared-zero tick
  slippage; repo6x5; zero-cost control with drag_pp measured in-artifact),
  optional real funding (default off, mirrors the Pine which has no funding
  model).
- **Grids**: one hundred twenty artifacts, all `verify` OK — 1h x thirteen
  symbols for the default confluence, B-only, Literal ADX, Day preset,
  A-only, "either", repo6x5 and funding variants; 15m x six (defaults,
  "either"); 5m x five (a thirty-day smoke window).
- **Result: zero configurations pass the repo gate.** Defaults at 1h: PF
  0.742-1.206, all far under buy & hold (BTC -28.11% vs +715.8%, run
  `749fc2eb9842d522`). The best-looking cells are selections that fail
  concentration: Literal ETH PF 1.258 with the best five trades carrying
  132.5% of PnL (run `5f51ef3458ef1fe2`), Literal HYPE PF 1.327 at 167.6%
  (run `2288aa01825d36ca`), default HYPE PF 1.206 at 254.7% (run
  `7934143c44479833`). The single cell that clears PF AND concentration
  (Day-preset ETH, PF 1.215, top-five 98.3%, halves and thirds green, run
  `cfc08b966ac07b08`) makes +65.76% over six years against +1556.08% for
  holding, and is the best of eighty-nine author-cost cells — the
  multiple-testing haircut applies. A-only and "either" over-trade to ruin
  (BTC A-only 5595 trades, -95.85%, run `ea0cb0588d2158fb`). Below one hour
  is ruin, same as cbpack/cbot: 15m defaults -48.74% to -97.66% (BTC run
  `c49e22c835ed0b48`). Repo costs sharpen everything (defaults 1h:
  -0.79% to -68.34%). Funding measured, negligible (BTC pays 0.15 USD over
  the window; four symbols' funding JSONs start/end days off the kline range
  — flagged `funding_covers_bars: false` in the artifacts, cannot change any
  verdict). The zero-cost control repeats the cbpack finding: a real gross
  edge exists (BTC zero-cost +42.39% vs costed -28.11%) — a cost problem,
  not a signal problem — and even at zero cost nothing approaches passive.
- Report: `results/fingrad_report.md` (guard OK; builder
  `code/_fingrad_build_report.py`; one hundred fourteen artifacts cited).

No walk-forward/neighborhood attempted: repo rule — stability checks apply to
survivors; there were none.

## 2026-10-29 (evening) — first equities campaign: cbpack's ten rules on QQQ daily — KILLED as alpha (zero of seven pass, none beats buy & hold)

The Alpaca equities pipeline (fetch script + SIP manifest, `data/ALPACA_EQUITIES_IMPORT.json`)
 fed its first backtest: adapter `eqpack` runs `code/cbpack_engine.py` UNMODIFIED
(hash-locked executor, audit `code/_eqpack_audit.py` E1-E7 ALL PASS:
engine-lock, htf-adaptation semantics pinned, load path, candle-proxy flow
declaration, self-skips, no-lookahead truncation, end_of_data convention,
determinism). Declared uniform adaptations: htf=1440 for S01/S02/S05 (the
pack's own 1h semantics on daily bars), candle-proxy flow, S06 excluded
(no intraday sessions on daily bars), S07/S08 self-skip. Costs declared, not
assumed: `eq` = 0.1+0.5 bps/side (zero commission, SEC/TAF amortised,
liquid-ETF spread), `cons` = 1+1, zero-cost control inside every artifact.

Result on 2722 daily bars (2016-2026): **zero of seven runnable strategies
pass the gate, zero beat buy & hold (+607.07%)**. Closest: S01 PF 1.427 on
81 trades (top-5 = 53% of PnL) and S05 PF 1.411 on 99 trades — both fail
green-years by one year (seven of eleven). S02 PF 2.192 with top-5 = 99% of
PnL on 39 trades; S10 PF 6.353 on ten trades. The counter-finding vs crypto:
at equities costs the drag stays under 1.46pp even at the conservative regime,
so this pack is NOT cost-destroyed — the killers are sample, concentration and
the passive benchmark. Artifacts `68c93ae390084b18` (eq) and
`fbe10ed77bdcc9b8` (cons), both pverify-clean; report
`results/eqpack_qqq_report.md` (guard OK, builder `code/_eqpack_build_report.py`).

## 2026-10-29 (night) — user-prespecified RSI mean-reversion on SOL/USDC spot 1h: positive but under buy & hold, PF barely over the line

The user's own spec, run verbatim (nothing tuned): RSI(14)<30 entry while flat,
RSI(14)>70 exit, ATR(14)x2 stop from the fill, 1% of equity risked per trade,
spot long-only. Data: data/binance_klines_1h/SOLUSDC_1h.csv (Binance spot,
5086 bars, 2026-04-01..2026-10-29, manifest data/SOLUSDC_IMPORT.json, sha
fd789284b309...), scored window = last 180 days, warmup excluded. Engine
code/rsi_mr_engine.py (adapter `rsimr`), audit code/_rsi_mr_audit.py — twelve
checks ALL PASS (RSI dual vs an independent loop, executor known answers,
cash identity on the real file, no-lookahead truncation, determinism).

Result (run `dcf66a3eb320e7a7`, pverify-clean, 60 closed trades): net +7.56%
vs buy & hold +15.20% on the same bars, PF 1.2172 (just over the 1.2 line),
win rate 31.67%, Sharpe 0.8552, max drawdown -14.88%, exposure 45.74%,
drag 3.93pp (zero-cost control +11.49%). The trade anatomy is the classic
mean-reversion one: all 18 RSI exits are winners (+5363.69 USDT total) while
all 41 stops are losers (-4450.64); the profit factor rests on that asymmetry,
and the halves split it (PF 0.6163 first half, 2.0623 second) — regime
dependent, no period stability. Verdict: NOT a gate pass (PF margin thin,
no B&H excess, halves unstable); recorded as a benchmark run of the user's
spec, not a strategy claim. Chart: inline visualization from the artifact.

## RECHAZO (2026-10-23) — pack Qwen de diez estrategias: no se porta

**El pedido.** Evaluar un hilo de Qwen
(`https://chat.qwen.ai/s/t_c0c1b2c5-1734-4fef-a442-f9abf311c842`) que propone diez
estrategias cripto nuevas "que pasen el gate". Se leyo completo (dos respuestas, unas
cincuenta y ocho mil letras) y se contrasto contra los datos en disco y contra lo ya
matado en este repo.

**Decision: se rechaza el pack entero. No se porta ninguna.** No hay artefactos de este
pack porque no se corrio nada: la decision es de diseno, no de resultado. **No citar
`run_id` para estas diez.** No son un backtest fallido, son un rechazo previo a la
corrida.

### Por que se rechaza, una por una

Cuatro piden datos que no existen en disco; cuatro son familias ya probadas aca sin
sobreviviente; una necesita una cinta de liquidaciones que no hay y su codigo contradice
su propio diseno; la ultima no tiene base sobre la que operar.

| estrategia | motivo |
|---|---|
| funding-basis carry | pide spot + borrow; en disco hay solo perps y funding. La version testeable (tilt de funding sobre el perp) ya existe como `cbpack` S07 |
| HMM momentum/reversal | familia probada sin sobreviviente (`emaadx`, `cbpack` S02/S10 a 1h, suite `cbot`). El codigo no es un HMM: es una EMA200 binaria mezclada con ranks |
| market making con filtro de toxicidad | sin historico de L2 (solo unos dias de agregados 5m en cuatro simbolos) y sin modelo de fills. El codigo fabrica el libro desde el close, asi que el OFI es el retorno |
| Kalman stat arb | familia matada (COINT-DYN, `dspack2` ds8): pierde contra pasivo en todos los pares. Una celda pre-declarada seria el unico caso defendible |
| vol risk premium | pide opciones (Deribit). Sin IV el codigo colapsa a un contrarian de funding |
| changepoint tendencia | familia matada (SAX, FFS, `dspack` ds1-ds3). El codigo no detecta changepoints: es una deriva Kalman con un penalty de una barra |
| lead-lag graph | familia matada (XPROP-LAG). Resta horizontes distintos (media de treinta barras contra suma de cinco) y deja a BTC operar como rezagado de un indice que lo contiene |
| fade de cascada de liquidaciones | no hay cinta de liquidaciones (el codigo usa un proxy de volumen x retorno absoluto) y entra en la barra de la cascada, que es justo lo que su propio texto prohibe |
| overlay de liquidez stablecoin | pide datos on-chain. Sin ellos el overlay es momentum de treinta barras mas momentum de diez: momentum dos veces |
| meta-labeling | sin base viable (ver "La correccion importante" abajo) |

(Las filas estan en el orden del hilo original: la primera es el carry, la ultima el
meta-labeling.)

### Los tres defectos que habrian fabricado resultados

Independientes de los datos, y la razon por la que el codigo no se porta ni como punto
de partida:

- **Fuga de etiquetas.** El split es cronologico unico, sin purge ni embargo, cuando la
  etiqueta se resuelve hasta `max_holding` barras despues: las ultimas etiquetas de train
  se resuelven con precios del tramo de test. El fallback del `except` promedia etiquetas
  precedentes en una ventana rodante de un anio de dias: forward-looking por construccion,
  y se activa en silencio ante cualquier error de sklearn.
- **Costos.** `backtest_single` cobra fee de un solo lado, sin slippage y sin funding. El
  repo exige seis bps de fee mas cinco de slippage **por lado** (preset `repo6x5`), y
  funding por settlement en perpetuos.
- **Fallbacks sinteticos silenciosos.** Funding sintetico (carry), libro sintetico
  (market making), IV sintetica (vol risk premium), liquidaciones por proxy (cascade
  fade), supply por momentum (stablecoin overlay). Un fallback que se activa sin avisar
  convierte un backtest en una demo.

### Su gate es mas debil que el de este repo

Propone Sharpe OOS, PF, deflated Sharpe y "ningun dia suelto por encima de veinte o
treinta por ciento del PnL". Le faltan las cuatro cosas que efectivamente mataron
candidatos aca: la concentracion de los **cinco mejores trades** como share del PnL, el
**period split** (verde en dos de tres anios), la comparacion **contra buy & hold** y la
**estabilidad de vecindario**; y no exige n minimo. Un candidato puede pasar su gate y
morir en el nuestro, que es exactamente lo que paso con los dos sobrevivientes `cbpack`
a 1h.

### La correccion importante: meta-labeling no tiene base

Era el unico de los diez con una idea dirigida al problema real del repo (edge bruto que
los costos destruyen). Su premisa es filtrar trades de un libro con PnL amplio. La unica
base con edge bruto medido no es amplia:

- `de5a02eb67f6100a` (dspack2 ds7 RSI-2, SOLUSDT 1h): PF **1.0218**, n **1110**, maxDD
  **-67.17**, PF a costo cero **1.2391**, share de los cinco mejores trades **344.51%**,
  neto sin ellos **-96.49%**.

Un filtro no salva un libro cuyo PnL son cinco trades: si los conserva no filtro nada, si
los descarta no queda nada. Si alguna vez se retoma la idea, el walk-forward con embargo
ya esta en `code/cbot/model.py`; no hace falta importar la version del hilo.

### Base rate

Se suma a la lista de packs propuestos por un LLM ya evaluados aca (`dspack`, `dspack2`,
`cbpack`, la suite `cbot`, `emaadx`), y ninguno dejo un sobreviviente que pase todas las
gates a los costos del repo. El unico libro que limpio todos los gates —la grid neutral de
XRP— vino de un argumento estructural de funding, no de una lista de estrategias.

### Que queda

Nada de este pack. El edge vivo es la grid neutral de XRP y su OOS real es el forward
paper en el VPS. Un listado nuevo contra un corpus que no produjo sobrevivientes es el
gasto, no la investigacion.

## ACTUALIZACION (2026-10-23) — v2: 25 USDT x 10x, cuenta normalizada a 25

**El pedido.** Equity 25 USDT x 10x, neutral, configurado como un bot de Binance
neutral, con el analisis del par de hoy. El motor no se toco (sha `e6f7422f53d3`);
el sizing es un parametro del adaptador y del runner.

### Que significa 10x aqui

25 USDT x 10 = **250 USDT de capacidad bruta**, no exposicion promedio. 5 niveles
por lado x 25 USDT por nivel (1.0x equity por nivel) = 250. El libro cubre rapido
y casi nunca tiene mas de dos lotes abiertos: el maximo bruto medido es **2.14x**,
y el buffer minimo de margen es **98.93%** (mantenimiento 0.5% del bruto). El 10x
es techo; `max_gross_leverage` y `min_margin_buffer_pct` se miden cada ciclo.

### El tope de delta tuvo que moverse

Con 25 USDT y 1x por nivel, un lote son 25 USDT. Un tope de 0.5x (12.50 USDT)
rechazaria el primer fill y el bot nunca operaria. El tope es **2.0x equity**
(dos lotes netos): conserva la neutralidad por lotes de v1 y deja alcanzable el
10x bruto cuando ambos lados estan llenos.

### Cuenta normalizada (importante)

El motor replica 2020->hoy y COMPONE. Su equity terminal es **2,299,367.59**, que
no es una cuenta de 25 USDT. El day-0 normaliza la cuenta a **25.00**
(`account_scale = 1.08726e-05`); todos los campos USDT del status son
`engine_usdt x scale`. Es exacto porque el motor es lineal en equity: sizing,
fees, funding y el ratio del tope escalan juntos. `engine_equity` queda en el
status como procedencia. El forward P&L se mide desde el day-0, no desde 2020.

### La grid de 12 celdas, re-corrida al sizing nuevo

Mismas 12 celdas pre-declaradas (no una busqueda nueva), 2 pasan. Gana la misma
celda: trend_band 0.10, stop_atr_mult 0.50, cover_mult 1.0.

| gate | v2 (25 x 10) |
|---|---|
| PF | **1.302** |
| trades | 5963 |
| win rate | 87.20% |
| maxDD | 43.42% |
| max gross | 2.14x |
| min margin buffer | 98.93% |
| delta medio / max | 16.11% / 214.35% |
| tope de delta | 200% |
| fills rechazados por el tope | 19848 |
| best 5 / sin ellos | 4.35% / +8801886.68% |
| bootstrap (t) | 178.24..582.96 (3.73) |
| tercios | 3/3 (8850.48 / 11357.44 / 795.58%) |
| split 2023 | train +51403.38% -> test +17757.99%, PF 1.301, n 3375, maxDD 20.54% |
| long-only | +260983.81% vs neutral +9197370.36% |

El retorno terminal es un artefacto de composicion (25 -> 2,299,367.59). La
decision se toma por PF 1.302, maxDD 43.42% y 3/3 verdes, no por el numero final.

### El par hoy (2026-10-22 13:15 UTC, snapshot del analisis)

| lectura | valor |
|---|---|
| close | 1.3243 |
| ATR 15m | 0.345% (percentil 42.7 de 90d) |
| trend strength 1h vs band | 0.0087 vs 0.10 |
| rango 30d | 1.2553 .. 1.6582 (precio al 17%) |
| vol realizada diaria | 2.71% |
| funding | +0.005301% / 8h |
| rung / nivel externo / stop | 0.345% / 1.73% / 1.90% |

Lectura: ATR en el percentil 42.7 (vol media-baja), trend strength 0.0087 muy por
debajo del band 0.10 (el overlay no bloquea), precio en el 17% del rango de 30d
(cerca del piso) y funding positivo leve. La geometria de 0.345% por rung y stop a
1.90% es la del motor; el analisis no justifica cambiar la celda, y la grid
re-corrida al sizing nuevo elige la misma. Fuente: `results/xrp_neutral_grid_25.json`.

### Artefacto y despliegue

    results/runs/7737dd3dc499721f.json     v2 (25 x 10), verify OK
    results/xrp_neutral_25x10_report.md    informe v2, guard OK
    results/runs/8bf3575619eda66f.json     v1 (10,000 / 0.25x), sigue verificando
    results/xrp_neutral_report.md          informe v1, guard OK

Reproducir v2:

    python code/vrun.py run --strategy xrpneutral --tf 15m --symbol XRPUSDT ^
      --set init=25 --set equity_pct=1.0 --set delta_max_pct=2.0 --set leverage=10.0
    python code/vrun.py verify 7737dd3dc499721f
    python code/vrun.py guard --report results/xrp_neutral_25x10_report.md

Desplegado en el VPS el 2026-10-23 00:22 UTC: day-0 congelado en 25.00, 0 lotes
abiertos, forward 0, 238240 barras y 7446 prints de funding. El estado v1 quedo
archivado como `*.v1` en `/home/ubuntu/xrp-paper-bot/`. El log de eventos forward
arranca vacio: no vuelca los 5963 cierres del backtest.

**Cooldown activo al desplegar.** El motor tiene 96 barras de cooldown tras un
stop. El ultimo stop del historico es 2026-10-22 08:15 UTC; el cooldown termina
2026-10-23 08:15 UTC. Al cierre de la barra 00:15 quedan 32 barras, asi que el bot
no abrira un grid nuevo hasta ~08:15 UTC. El status expone `last_stop_utc`,
`cooldown_until_utc` y `cooldown_bars_left` para que la pausa sea visible, no
silenciosa.

### Forward al 2026-10-23 22:00 UTC

El cooldown expiro a las 08:15 UTC. Primer tramo forward: **5 cierres, 4 covers
y 1 stop**. Equity **24.87**, forward **-0.1295 USDT (-0.53%)**. El stop de las
19:00 UTC (-0.4063) se comio los cuatro covers (+0.2768); es el riesgo
estructural del libro: los stops cargan las perdidas.

| # | cierre UTC | lado | entrada | salida | P&L USDT | motivo |
|---|---|---|---|---|---|---|
| 1 | 10:00 | long | 1.31870113 | 1.32290057 | +0.0692 | cover |
| 2 | 13:15 | long | 1.31450170 | 1.31870113 | +0.0692 | cover |
| 3 | 14:30 | long | 1.31030226 | 1.31450170 | +0.0692 | cover |
| 4 | 15:15 | long | 1.30610283 | 1.31030226 | +0.0692 | cover |
| 5 | 19:00 | long | 1.32290057 | 1.30224855 | -0.4063 | stop |

| campo | valor |
|---|---|
| equity | 24.87 |
| forward P&L | -0.1295 (-0.528%) |
| lotes cerrados | 5 (4W / 1L) |
| forward PF | 0.681 |
| win rate forward | 80.0% |
| lotes abiertos | 0 |
| funding pagado | 0.0025 |
| cooldown | hasta 2026-10-24 19:00 UTC (85 barras al 21:45) |
| max gross / min buffer | 2.14x / 98.9% |

El P&L cerrado es -0.1295; el equity marca -0.13 porque suma -0.0025 de funding.
El stop de las 19:00 disparo el cooldown de 96 barras: el bot no abrira grid
nuevo hasta 2026-10-24 19:00 UTC.

**Lectura del kill criterion.** El informe v2 resumio el kill como PF < 1; el
baseline del repo (`code/xrp_neutral_baseline.py`) exige ademas **n >= 30
cierres**. Con 5 cierres, PF 0.681 es "too few trades", no un kill. Se deja
correr hasta 30 cierres forward y ahi se aplica la regla; si se prefiere la letra
estricta del informe, se detiene ahora. **Cinco cierres no son evidencia**: ni
los cuatro covers prueban el edge ni el stop prueba que no exista.

`forward_pf` se emite `null` cuando no hay perdedores (`Infinity` no es JSON
valido); ahora que hay un stop, el PF es finito. El status pasa un parseo
estricto.

**Actualizacion 2026-10-24 11:57 UTC.** Sin cambios en el libro: 0 lotes,
equity 24.87, forward -0.1295, 5 cierres, PF 0.681. Cooldown hasta las 19:00 UTC
(30 barras restantes al cierre de 11:30). XRP en 1.2784, **1.8% por debajo de la
salida del stop** (1.30225): el stop evito la caida posterior, aunque un solo
trade no valida la regla.

**Actualizacion 2026-10-26 22:20 UTC.** El bot reanudo el 24 a las 19:00 UTC y
cerro **5 covers nuevos, todos ganadores**:

| cierre UTC | lado | entrada | salida | P&L USDT |
|---|---|---|---|---|
| 2026-10-25 23:30 | short | 1.29155237 | 1.28630000 | +0.0916 |
| 2026-10-25 23:45 | short | 1.29680475 | 1.29155237 | +0.0915 |
| 2026-10-26 02:30 | long | 1.28104763 | 1.28630000 | +0.0916 |
| 2026-10-26 04:00 | long | 1.27579525 | 1.28104763 | +0.0917 |
| 2026-10-26 14:45 | short | 1.30205712 | 1.29680475 | +0.0915 |

Equity **25.33**, forward **+0.3284 (+1.33%)**, PF **1.808**, 9W/1L en 10
cierres, 0 lotes abiertos. El kill criterion ya no se dispara (PF > 1), pero
n=10 sigue por debajo de 30: "too few trades" para un veredicto. El funding
forward paso a **-0.0051** (recibido), no pagado.

**Actualizacion 2026-10-27 19:58 UTC.** Dos cierres nuevos:

| cierre UTC | lado | entrada | salida | P&L USDT | motivo |
|---|---|---|---|---|---|
| 2026-10-26 23:45 | short | 1.30730950 | 1.30205712 | +0.0914 | cover |
| 2026-10-27 12:30 | short | 1.31256187 | 1.31715825 | -0.1067 | stop |

Equity **25.32**, forward **+0.3132 (+1.27%)**, PF **1.611**, 10W/2L en 12
cierres, 0 lotes abiertos. El stop de hoy disparo cooldown hasta **2026-10-28
12:30 UTC** (68 barras al 19:30). XRP en 1.3246, 0.56% por encima de la salida
del stop: otra vez el stop evito la continuacion, pero el libro plano tambien se
perdio el rally. PF > 1 y n=12 < 30: sigue "too few trades", sin kill.

**Actualizacion 2026-10-31 20:17 UTC.** Nueve cierres desde el 27: 7 covers
(+0.4800) y 2 stops (-0.5727), neto **-0.0927**. Los dos stops son dos lotes
long que cerraron en la misma barra, el 29 a las 02:30; el status cuenta un
"stop trigger" por barra, no por lote, por eso `exit_reasons` sube 1 y no 2.

| cierre UTC | lado | entrada | salida | P&L USDT | motivo |
|---|---|---|---|---|---|
| 2026-10-28 13:30 | short | 1.31939083 | 1.31530000 | +0.0686 | cover |
| 2026-10-28 14:15 | long | 1.31120917 | 1.31530000 | +0.0686 | cover |
| 2026-10-28 18:00 | short | 1.32348166 | 1.31939083 | +0.0686 | cover |
| 2026-10-28 18:30 | short | 1.32757249 | 1.32348166 | +0.0685 | cover |
| 2026-10-28 19:30 | short | 1.33166333 | 1.32757249 | +0.0685 | cover |
| 2026-10-28 20:15 | short | 1.33575416 | 1.33166333 | +0.0685 | cover |
| 2026-10-29 01:45 | long | 1.30302751 | 1.30711834 | +0.0687 | cover |
| 2026-10-29 02:30 | long | 1.30711834 | 1.28905515 | -0.3651 | stop |
| 2026-10-29 02:30 | long | 1.29893667 | 1.28905515 | -0.2076 | stop |

Equity **24.90**, forward **-0.10 (-0.405%)**: el cerrado sigue en +0.2205 y el
lote abierto resta -0.3372 de MTM (funding recibido +0.0167). 21 cierres,
17W/4L, PF **1.203**, win 81.0%, 1 lote abierto. El stop del 29 disparo cooldown
hasta el 30 a las 02:30; ya expiro.

**Fix del log de eventos.** El CSV tenia 20 filas y el status 21: la clave
`(ts, side)` no es unica y dos lotes del mismo lado cerraron en la misma barra.
La clave ahora incluye entrada/salida/pnl; el ciclo siguiente appendo la fila
faltante (el segundo stop, -19095.52 engine) y el CSV quedo con 21 filas, en
linea con `forward_closed_lots`. Backup: `xrp_paper_bot_events.csv.pre_dedup_fix`.

Kill criterion: PF 1.203 > 1, n=21 < 30; sigue "too few trades". La regla se
aplica al llegar a 30 cierres.

**Caveat, igual que v1:** es el maximo de 12 celdas pre-declaradas, asi que el
haircut de multiple-testing aplica; el forward paper es el OOS real. El 10x es
capacidad, no exposicion promedio.

## ACTUALIZACION (octubre) — "XRP paper bot": book NEUTRAL en XRP, desplegado en el VPS

> **Superseded 2026-10-23 by v2 (25 USDT x 10x).** Esta seccion es el registro de
> v1 (10,000 USDT / 0.25x por nivel); sus numeros siguen verificando en
> `8bf3575619eda66f` y su informe. La config desplegada es la de la seccion v2.

**Que es.** Un grid de dos lados DELTA-NEUTRAL sobre el perpetuo XRPUSDT de Binance
USDT-M, 15m. Motor nuevo `code/xrp_neutral_engine.py`, runner
`code/xrp_paper_bot.py`, desplegado en el VPS como bot independiente:

    /home/ubuntu/xrp-paper-bot/            (directorio, datos, logs y estado propios)
    */5 * * * * /home/ubuntu/xrp-paper-bot/run.sh
    17 * * * * /home/ubuntu/xrp-paper-bot/watchdog.sh

Es deliberadamente SEPARADO de `~/paper`, `~/grid-paper`, `~/cqb` y
`~/freqtrade`: su directorio, sus lineas de cron, sus archivos `xrp_paper_bot_*` y
su propio engine. No toca los otros bots. **PAPER ONLY**: sin ordenes, sin keys,
sin cuenta, solo REST publico de Binance.

### POR QUE NEUTRAL (y el numero que lo prueba)

El grid long validado es un PAGADOR de funding: $188,284.85 solo en su pierna XRP,
porque el lado largo paga un rate positivo en un mercado que sube. Un libro
balanceado le paga al exchange casi nada.

    grid long (XRP leg)   funding pagado   $188,284.85
    XRP paper bot (neutro) funding pagado   $265.62     sobre toda la ventana

La neutralidad se MIDE en cada ciclo (`NEUTRALITY_avg_abs_delta_pct` en el status),
no se afirma: delta medio 4.01% del equity, con tope duro de 50% del notional neto
en el momento del fill. El control vive DENTRO del artefacto: el mismo libro con
el lado corto apagado.

    neutral (dos lados)  +1589.38%
    long only (control)   +648.41%

El short-only se corre aparte en `code/xrp_neutrality_check.py` y pierde todo el
capital en el mismo camino: el neutral no es beta direccional en ninguna de las dos
direcciones.

### POR QUE ES LA PRIMERA ESTRATEGIA QUE PASA TODO

| Test | Resultado | (contra los candidatos del pack) |
|---|---|---|
| Concentracion | 5 mejores trades = **2.04%** del PnL | 108-136% |
| Sin los 5 mejores | **+1559.48%** | -5.86% a -64.02% |
| Significancia | IC [+20.78, +33.21], t=**+8.51**, P(<=0)=**0.0%** | t 0.7-1.5 |
| Period split | **3/3** verdes (+202.30 / +220.83 / +74.12%) | 1-2 de 3 |
| Split congelado (sin re-fit) | train hasta 2023-01-01 +365.46% -> **test +262.95%**, PF 1.47, n 3328, maxDD 5.45% | PF < 1 |
| Neutralidad | delta medio **4.01%**, control long-only +648.41% | n/a |

Full history: net +1589.38%, PF 1.498, 5876 trades, win 86.81%, maxDD 10.18%,
fees 47785.84, funding 265.62.

**El caveat, dicho claro:** es el MAXIMO sobre una grid de 12 combinaciones
**DECLARADAS ANTES** de correr (2 de 12 pasaron), asi que el haircut de
multiple-testing aplica; y el numero de historia completa es una cota superior.
El paper run mide la ventana forward, que es el out-of-sample real.

### LOS TRES BUGS QUE EL DESPLIEGE ENCONTRO (leer antes de tocar un bot de perp)

1. **El funding nunca se cobro en `cbpack-1`** (ver la seccion de abajo). El mismo
   patron casi me rompe el bot: su historial de funding cubria solo 400 dias,
   las barras iniciales no cobraban NADA, y el equity salia mal en silencio
   (funding_paid −$49.96 recibido en vez de +$266.14 pagado). Ahora el bot trae
   el historial COMPLETO y `funding_covers_bars` en el status lo detecta. Un
   backtest con funding parcial es otro backtest.
2. **Binance IGNORA `startTime=0`** en `/fapi/v1/fundingRate` (devuelve lo mas
   reciente). Hay que paginar desde un timestamp real y temprano.
3. **La metrica de delta contaba dos veces** la posicion nueva (bug mio, corregido
   antes de desplegar).

### PROCEDENCIA DE ESTOS NUMEROS (leer antes de citarlos)

Desde 2026-10-22 el bot **es** un adaptador del harness (`xrpneutral`), asi que sus
cifras viven en un artefacto reproducible en vez de en el status del VPS:

    python code/vrun.py run --strategy xrpneutral --tf 15m --symbol XRPUSDT
    python code/vrun.py verify 8bf3575619eda66f

    results/runs/8bf3575619eda66f.json     cifras canonicas: historia completa,
                                           control long-only, concentracion/bootstrap,
                                           tercios, split congelado, funding, tablas
                                           por lado y por motivo de salida
    results/xrp_neutral_report.md          el informe; `guard` OK contra ese artefacto

El artefacto fija el sha de sus inputs (238197 barras 15m y 7444 prints de funding)
y el sha del motor, que es el MISMO archivo que corre el VPS. Los JSON de screening
previos al despliegue (`results/xrp_neutral_gauntlet.json`, `xrp_neutral_grid.json`,
`xrp_neutrality_check.json`) se corrieron sobre otro snapshot de datos, por eso
difieren en decimas (p.ej. +1608% vs +1589.38%): el artefacto manda.

La auditoria de correccion no es el artefacto: `code/xrp_neutral_audit.py` es el
known-answer (ALL PASS). `verify` solo demuestra determinismo, nunca correccion.

### AUDIT Y REGRESION

`code/xrp_neutral_audit.py` — ALL PASS: control sin operaciones, simetria
direccional por trade, signo del funding (largo paga / corto recibe), tope de
delta, no-look-ahead (truncar la historia no cambia el pasado), identidad
contabil, determinismo bit-a-bit, y un lock de sha256 sobre los engines
validados (`code/_engine_lock.json`) para que nadie los toque por accidente.

`code/_engine_lock.json` fija el sha256 de `cbpack_engine.py`,
`cvrmd_backtest.py`, `botstrat_backtest.py`, `mp20_report_ports.py` y
`grid_audit.py`. Este ultimo NUNCA fue adaptador del harness, asi que ningun
artefacto lo hashea: el lock es su ancla.

---

## ACTUALIZACION (octubre) — `cbpack` re-corrido CON FUNDING y CONCENTRACION

Adapter nuevo `cbpackf` (`code/cbpack_funding_engine.py`). Informe:
`results/cbpack_funding_report.md` (guard OK, artefactos de la matriz completa, todos
`verify` clean). Gates: `results/cbpack_gates.json` (ocho celdas).

### HALLAZGO 1 — `cbpack` NUNCA COBRO EL FUNDING

El engine `cbpack-1` adjunta la columna `funding_rate` y nunca la debita del PnL.
Su propio docstring lo dice: *"No funding payments, no liquidation engine, no partial
fills"*. **`funding_attached: true` significa que la COLUMNA se adjuntó, no que el
COSTO se cobró.**

Detalle que hace el bug silencioso: `attach_funding()` del pack arrastra el ultimo
rate conocido HACIA ADELANTE en cada barra posterior. Eso es lo que un z-score de
funding necesita (S07 lo lee asi) pero NO es un calendario de facturacion: en 1h
cobraria 8 liquidaciones por cada una real. El fork factura desde una columna
`funding_event_rate` construida con los timestamps crudos de liquidacion.

Drag medido (campo `funding_drag_pp`, medido dentro del artefacto):

| celda | run_id | net % sin funding | net % con funding | drag pp | funding % del equity |
|---|---|---|---|---|---|
| 1h SOL S10 | `f72ee7ef452b4986` | +75.45 | +71.99 | -3.45 | 2.51 |
| 1h XRP S10 | `9eba05720c385e77` | +184.22 | +178.62 | -5.59 | 4.75 |
| 1h XRP S02 | `9eba05720c385e77` | +184.01 | +177.90 | -6.11 | 4.26 |
| 15m HYPE S07 | `bb720c344ba68c9d` | +22.10 | +22.86 | **+0.76** | -0.66 |

HYPE S07 gana funding: es short y lo recibe. Las otras son long-biased y pagan.

**CORRECCION**: una medicion previa de este drag dio un valor mucho mayor que el
real. Era incorrecta: sumaba el rate arrastrado sobre cada barra del holding,
facturando 8 liquidaciones por cada real. El valor real es -3.45pp.
Los hallazgos de concentracion, significancia y replicacion cross-engine NO
involucran funding y no cambian.

### HALLAZGO 2 — CONCENTRACION: EL GATE QUE FALTABA

Un gate que falta en todo el repo. Si los 5 mejores trades de una estrategia pesan
MAS que todo su PnL, no es una estrategia con edge: son un puñado de posiciones
afortunadas. `conc_passes` es true solo si el retorno sobrevive a quitar esas 5.

| celda | run_id | best5 como % del PnL | net sin los 5 mejores | gate |
|---|---|---|---|---|
| 1h SOL S10 | `f72ee7ef452b4986` | 108.14 | -5.86 | FAIL |
| 1h XRP S10 | `9eba05720c385e77` | 135.84 | -64.02 | FAIL |
| 1h XRP S02 | `9eba05720c385e77` | 129.38 | -52.26 | FAIL |
| 15m HYPE S07 | `bb720c344ba68c9d` | 47.85 | +11.92 | PASS |

### VEREDICTO

A costos repo (6+5 bps) CON funding cobrado, **ninguna celda del pack pasa todas las
puertas**. Los dos candidatos de 1h que sobrevivian el grid `cbpack-1` fallan
concentracion. HYPE S07 pasa concentracion pero muere en PF a costos repo.

`cbpack` sigue KILLED bajo 1h y CONDITIONAL en 1h, y la condicion de 1h ahora lleva
una condicion mas: no sobrevive a quitar sus 5 mejores trades.

### NOTA DE DISCIPLINA

El `guard` REFUSO el primer informe porque las cifras de drag eran DERIVADAS
(diferencia de dos valores citados) y el guard no puede respaldarlas. La solucion no
 fue suavizar el informe: fue MEDIR el drag y la concentracion DENTRO del artefacto
(`funding_drag_pp`, `conc_top5_share_pct`, `conc_net_without_top5_pct`). `guard` es un
check de PROCEDENCIA, no de correccion: pregunta "esta cifra esta en un artefacto
citado?", no "es la cifra correcta para esta pregunta?".

---

## Reparto de roles (decidido 2026-09-26)
- **TradingView = solo eyeball.** Flechas, bandas VWAP, panel, alertas. NO se
  usan sus números: la cuenta gratuita entrega ~9 meses de 1H y recorta en
  silencio (pedir 2022 te devuelve 2026), así que el strategy tester no puede
  validar nada multi-año — en 1A y ALL reporta cero operaciones. Eso es falta de
  datos, no bug del script.
- **Binance = la verdad.** Todo número de performance sale de `code/*.py` contra
  `data/binance_klines*`. `cvrmd_backtest.py` es el backtest autoritativo.
- **MCP de TradingView se mantiene vivo** para consulta futura. Acceso y límites
  documentados en `claudeverstradingview-main/HERMES_ACCESS.md`.

## REGLA 0 — ningún número sin artefacto (2026-10-10)
Un informe de backtest fue **inventado en prosa** (sin corrida). Para que no
vuelva a pasar: todo número reportado debe salir de un artefacto persistido y
verificado por `code/vrun.py` (`run` -> `results/runs/<run_id>.json`, `render`
lee solo el artefacto, `verify` re-corre y exige reproducción bit-for-bit).
Detalle en `VALIDATION_PROTOCOL.md` y en la sección "SAX Scalper PRO v3.0" al
final de este documento. Sin `run_id`, un número no es admisible.

## Estructura
- `code/` — ports Python validados (los que importan están abajo)
- `data/binance_klines*` — klines 5m/1h/1m Binance USDT-M
- `pine/library/` — espejo de todos los .pine de Downloads
- `backups/` — zips con fecha

## Validados (dual-engine o PF robusto, 1H salvo nota)
| Estrategia | Port | Veredicto |
|---|---|---|
| CVRMD-v1.1 (SUI/ETH) | `cvrmd_backtest.py` | **SUSPENDIDO / FRÁGIL**: SUI +16.4% PF 1.98 n41 (reciente, sin OOS), ETH cae a PF 1.02 en historia completa (ver nota abajo) |
| BOT-Strat (ETH) | `botstrat_backtest.py` | +15.6% PF 1.80, 9/9 neighborhood |
| FFS-v1 (HYPE 5m) | `ffs_engine2.py` | **KILLED 2026-10-01**: +7.7%/1.24 no reproduce en datos actuales — full −46.6% PF 0.93, mitades 0.95/0.91, últimos 30/60d ≤1.06; solo ventana 94d verde (+5.5%/1.21). Window-pick, sin rescate |
| MP-17 rotación semanal | `kimi20_*.py` | +88% pero Sharpe 0.44, DD 53% — marginal |

### CVRMD-v1.1 — sensibilidad a la ventana (leer antes de confiar el número)
`cvrmd_backtest.py` apuntaba a un `%TEMP%\opencode` viejo (25,436 barras 1H desde
2023-11), no a `data/`. Los datos son idénticos (99.99% float-idéntico en el
solape; la diferencia fueron 2 barras por mi fetch más reciente), pero el repo ya
tiene backfill a 2017. **Las cifras de arriba son sobre la ventana 2023-11..ahora.**

| Símbolo | 23-11..ahora | 24-01..ahora | 25-01..ahora | 26-01..ahora |
|---|---|---|---|---|
| SUIUSDT | **+16.4% PF 1.98 n41** | +14.8% PF 1.92 n39 | +9.6% PF 1.77 n29 | +5.6% PF 1.96 n14 |
| ETHUSDT | **+11.1% PF 1.70 n40** | +6.9% PF 1.45 n37 | +8.6% PF 1.85 n27 | +8.2% PF 2.45 n18 |
| SOLUSDT | +8.6% PF 1.46 n39 | +8.3% PF 1.53 n34 | +14.2% PF 2.72 n24 | +4.2% PF 2.23 n9 |
| BTCUSDT | -3.7% PF 0.85 | -8.6% PF 0.61 | -6.6% PF 0.59 | -2.6% PF 0.68 |
| XRPUSDT | +0.5% PF 1.03 | -0.6% PF 0.98 | +1.5% PF 1.13 | +1.9% PF 1.32 |

**El edge es de SUI/ETH y es reciente.** PF se mantiene arriba de 1.2 en todas las
ventanas para SUI/ETH/SOL, pero el **n cae por debajo de 30** en cualquier ventana
más corta que ~2 años. Los tres años verdes de STATUS.md son 2024/2025/2026
(3 años calendario, no 3 años de historia) — no hay un cuarto año que lo confirme.
Corrido con historia completa (2017+) el warmup de 200+ barras se come todo y el
resultado es: SUI +16.7% PF 1.79 n49, ETH +0.6% PF 1.02, SOL +13.9% PF 1.35,
BTC -13.5% PF 0.74. **ETH cae a PF 1.02 con más historia** — eso es señal de que
el +11.1%/+1.70 de ETH es frágil, no un edge estable.

Reproducir con: `python code/cvrmd_windows.py`.

### SUPER FLOW SNIPER v3.0 — PORTEADO A PYTHON, 0/14 (2026-09-26)
Pine: `pine/library/Super_Flow_Sniper_v3.0_QWEN8.pine` (3,439 lineas, el que
tenias cargado en el chart como JYlxxl).
Port: `code/sfs_port.py` (gate de decision, Pine L2681-2757) + `code/sfs_house_gate.py`
Resultado: `results/sfs_house_gate.txt`

LO QUE CONFIRMASTE Y ES LA MEDIDA DEL DIA
TradingView no tiene feed L2, asi que el "order flow" de CUALQUIER script Pine
es sintetico. En SFS:
  f_delta_vsa   = ((close-low)/(high-low))*2-1, escalado por range/ATR
  f_delta_proxy = el mismo CLV sin escalar
  "LTF real delta" = sign(ltf_close - ltf_open) * ltf_volume  (tambien proxy)
  order walls / BAI / absorcion = construidos de pivots de delta OHLC, NO de DOM
No hay ningun feed de volumen traded en el script. Es el MISMO proxy sintetico
que en nuestro repo correlaciona r=0.06 con el CVD real y que costo a SUI
16.4% -> 3.8% en la variante delta-smoothing. Eso no lo arregla un port fiel.

RESULTADO (1H, 45 meses, 6bps+5bps/lado, mismo simulador que las demas)
  simbolo   long  short   net LO    PF     n     DD      gate   vs buy&hold
  BTCUSDT     21      3   -0.14%  1.00    21   6.8%   FAIL   -949.8pp
  ETHUSDT     27      0   +9.44%  1.65    27   4.2%   FAIL   -2041.8pp
  SOLUSDT     10      3   -3.70%  0.53    10   5.8%   FAIL   -4637.0pp
  SUIUSDT      7      4   +1.87%  1.56     7   2.7%   FAIL    -17.3pp
  XRPUSDT     21      1   -0.44%  0.98    20   8.6%   FAIL   -569.1pp
  HYPEUSDT      5      1   +1.10%  1.50     4   2.9%   FAIL   -154.0pp
  SPXUSDT      2      3   -2.06%  0.00     2   2.1%   FAIL    +43.7pp
  0/14 pasan el house gate (7 simbolos x 2 arms). 2/14 "baten" al pasivo y
  ambos son SPX, que cae -45.8%: perder menos que una moneda que se desploma no
  es alfa.

DOS FALLOS QUE MATAN LA MUESTRA ANTES DE MIRAR EL P&L
  1. SUBMUESTREO: el gate dispara 2-27 senales en 45 meses. El floor de la casa
     es n>=30 trades CERRADOS. Ningun simbolo llega. ETH con PF 1.65 y DD 4.2%
     esta a 3 trades de ser interesante, y aun asi +9.4% contra +2051% del pasivo.
  2. El filtro HTF y el gate de 6 scores recortan tanto que la estrategia casi
     no opera. Un gate que necesita 70/100 de EdgeScore, RR>=2.0 neto, vol de
     sesion y HTF alineado no es un filtro: es una puerta cerrada.

DONDE ESTA EL RIESGO REAL
El dashboard en vivo ya lo decia: "SEÑAL Sin senal", Edge L/S 0/18, Net RR
1.15/1.86 contra un minimo de 2.0. El port confirma el motivo cuantitativo.

BUG ENCONTRADO AL PORTAR (importante para futuros ports)
  ta.pivothigh NO es rolling_max. Mi primera version uso rolling_max, que sube
  para siempre y produjo CERO breakouts BOS en los 7 simbolos sin error. El
  pivote es el bar k cuyo high es el maximo ESTRICTO de high[k-L..k+R], y solo
  es visible desde k+R. Con el fix: 2,918 pivotes y 1,483 breakouts en SUI.
  Un filtro que devuelve cero no es un filtro roto, es un bug silencioso.

### SUITE "CLAUDE MULTIPAIR STRATEGIES 20" — ANALIZADA Y CORRIDA (2026-09-26)
Carpeta: `Downloads/CLAUDE MULTIPAIR STRATEGIES 20/`
Codigo copiado y ejecutado en `data/mp_suite/`. Spec honesto: el sandbox del
autor NO tenia red, asi que sus numeros eran SINTETICOS (GBM), no reales.

HALLAZGO 1 — EL PDF NO VIENE DE ESTE CODIGO
Los 20 NOMBRES no coinciden ni uno: 0/20. Mismos IDs MP-01..MP-20, estrategias
distintas. Ejemplos:
  MP-01  codigo: top-2 por mom 30d, rebalance diario
         PDF:    top-3 por mom 72h sobre SMA(200)
  MP-04  codigo: ranking por pendiente de histograma MACD, semanal
         PDF:    "Weekly Dual Momentum Rotation", 168h
  MP-17  codigo: top-2 por momentum mezclado 12h/72h/30d
         PDF:    satelitas ETH/SOL/AVAX/LINK vs BTC 24h
Son dos entregables independientes. El PDF no es evidencia de este codigo.

HALLAZGO 2 — CORRIDO EN DATOS REALES, EL RESULTADO DEPENDE DE LA VENTANA
45 meses de 1h reales (BTC/ETH/SOL/XRP, 32,636 barras, 2023-01-01..2026-09-21).
  VENTANA A  2025-05-30..2026-09-21  479 dias  benchmark +21.4%  -> 7/20 baten
  VENTANA B  2023-01-01..2026-09-21 1359 dias  benchmark +496.0% -> 1/20 bate
Mismo codigo, mismos parametros, ranking invertido. La unica que bate en la
ventana larga:
  MP-02  Dual MA Trend Filter  +1075.6%  Sharpe 1.36  DD -68.5%  n=686  PF 1.18
que sigue sin superar al pasivo en riesgo: DD 68.5% vs benchmark DD mucho menor.

TRAMPA ENCONTRADA: incluir HYPEUSDT (listado 2025-05) en el universo colapsa los
1360 dias a 479, porque align_universe() hace interseccion de timestamps. Cuatro
de los cinco simbolos aportan solo sus ultimos 480 dias.ASI cualquier moneda
reciente define la ventana del estudio entero.

BUGS EN EL CODIGO (no criticos, pero reales)
  MP-05 y MP-10 dan 0 trades: ambos indexan pares fijos por nombre
  ("BTCUSDC", "SOLUSDC"/"ETHUSDC") que no existen en el universo. El motor no
  valida nombres, asi que la suite corre en silencio con 2 estrategias muertas.
  El P&L de MP-07/MP-09/MP-11 llega a -100% por apalancamiento implicito
  sin tope de gross en modo discreto.

CONCLUSION
Ninguna de las 20 es una estrategia validada. La que mejor se ve (MP-02) gana en
una ventana alcista y pierde por drawdown en la larga. El resultado confirma el
patron del dia: 0.5% de plausibilidad en 6 meses no es validacion.

### FUNDING — el coste que faltaba en TODOS los backtests de perps (2026-09-26)
Hallazgo mayor del dia. Todo backtest anterior cargo comision + slippage pero
NO funding. Un largo en perpetuo PAGA el funding cada 8h cuando la tasa es
positiva, y en mercado alcista eso es casi siempre.

COSTO SIEMPRE-LARGO (eventos reales de Binance, no estimacion):
  simbolo   acumulado      anualizado   % eventos positivos
  XRPUSDT     +98.07%        +14.59%          80%
  ETHUSDT     +94.23%        +13.79%          86%
  BTCUSDT     +81.40%        +11.55%          86%
  SUIUSDT     +18.55%         +5.45%          72%
  HYPEUSDT    +11.26%         +4.25%          84%
  SPXUSDT      +4.29%         +1.20%          79%
  SOLUSDT      +1.28%         +0.21%          71%

IMPACTO EN EL SIZE OVERLAY (holdBars=168, que esta en mercado ~15% del tiempo):
  simbolo   sin funding   con funding    delta     fondo pagado
  SUIUSDT      +171.0%        +141.4%    -29.6pp     $1,982
  HYPEUSDT     +132.1%        +119.6%    -12.5pp       $764
  BTCUSDT      +543.1%        +289.6%   -253.5pp    $12,328
  XRPUSDT      +410.6%        +174.4%   -236.2pp    $13,047
  ETHUSDT     +1219.9%        +605.9%   -613.9pp    $26,239
  SOLUSDT     +4237.1%       +3718.7%   -518.4pp    $54,369

La conclusion NO cambia de direccion: el overlay sigue sin batir al pasivo
(SUI +141% vs +19% sigue ganando; BTC +290% vs +951% sigue perdiendo), pero las
cifrasoriginalmente publicadas eran demasiado optimistas. El SUI "+171%" es "+141%".

LA ESTRATEGIA CON SEÑALES NO PAGA CASI NADA
El motor de señal dispara ~30 veces en 3.5 años con posiciones de ~13 barras:
esta en mercado ~1% del tiempo, asi que su factura de funding es ~0.0-0.3pp.
El overlay es el que paga, porque esta expuesto continuo.

BUG ENCONTRADO Y CORREGIDO (importante)
Funding se cobra POR EVENTO cada 8h, no por barra horaria. Asignar la tasa
vigente a cada barra de 1h y cobrarla cobra EXACTAMENTE 8x de mas (29,810 barras
vs 3,726 eventos en SUI). Sin error, solo numeros imposibles: ETH -1324%,
SOL -3822%. Corregido y verificado contra el total siempre-largo.

Scripts: `code/funding_cost.py`, `code/funding_applied.py`, `code/overlay_funding.py`
Datos cacheados: `data/binance_funding/*.json`
Skill creada: `binance-public-data` (endpoints publicos sin clave, no las de cuenta)

### CVRMD SIZE OVERLAY — largo unico como control de TAMANO (2026-09-26)
NO es una estrategia de timing. Es un indicador: tu ya estas posicionado, el
script te dice que porcentaje mantener. No entra ni sale; tu rebalanceas a mano.
Fichero Pine: `pine/library/CVRMD_Size_Overlay.pine` (291 lineas, compila
0 errores / 0 warnings, verificado en TV). Copia en `Downloads/`.
Python: `code/cvrmd_sizer.py` (backtest) + `code/cvrmd_sizer_check.py` (invariantes).

LOGICA
    senal activa  -> FULL (100%)
    plana         -> REDUCED (50% por defecto)
    setup bajista -> FLOOR (25%)   <-- INACTIVO en long-only, ver abajo
    holdBars=168 (1 semana en 1H) mantiene FULL tras cada senal.

POR QUE EXISTE
Todo el backtest del dia convergio en: nada bate al pasivo en estos perps, pero
long-only CVRMD baja el DD de SUI de 87.9% a 3.3% (PF 1.97). Ese 3.3% vinha de
estar FUERA DE MERCADO, que no esta disponible si ya estas posicionado. La misma
informacion vale mas como input de TAMANO que de timing.

RESULTADO MEDIDO (1H, 6bps+5bps/lado, cada rebalance cobra coste)
  simbolo   overlay @ DD igualado   buy&hold
  SUI       +171%  @ 64% DD         +19%  @ 88% DD
  SOL       +4237% @ 85% DD         +4639% @ 97% DD
  ETH       +1220% @ 58% DD         +2054% @ 81% DD
  BTC        +543% @ 55% DD         +951%  @ 77% DD
  XRP        +411% @ 68% DD         +569%  @ 85% DD
  A DD igualado el overlay GANA en ETH, SOL, SUI y SPX; PIERDE en BTC, XRP, HYPE.

QUE CONFIAR Y QUE NO
  CONFIAR: la reduccion de drawdown. Consistente en todos los simbolos.
  NO CONFIAR: la mejora de retorno. holdBars por simbolo se eligio in-sample y
  no sobrevive walk-forward (SOL -1.0%, SUI -3.4%, XRP -13.2% en 2025-26).
  Descripcion honesta: pagas ~25-30 puntos de DD por un retorno SIMILAR.
  No es alpha.

LIMITE CONOCIDO
  En long-only la rama short nunca dispara (0 senales short en 7 simbolos), asi
  que el estado FLOOR es CODIGO MUERTO y szFloor no tiene efecto. El Pine lo
  mantiene para que el mismo codigo sirva si se reactivan las señales cortas,
  pero la descripcion correcta es: overlay de DOS estados, no tres.

### CVRMD en 15m — PROBADO Y DESCARTADO (2026-09-26)
Con 45 meses de 1m descargados (ver `data/binance_klines_1m/README.md`).
Ports: `cvrmd_tf_cost.py` (diagnóstico de costo) · `cvrmd_15m.py` (sweep) ·
`cvrmd_15m_audit.py` (MFE/MAE + walk-forward).

Lookbacks escalados ×4 (15m×4 = 1h) y ATR mult barrido 1.5→7.0, que es lo que
decide supervivencia: con stop 1.5×ATR el costo/R era 0.58× (marginal); a 5×ATR
cae a 0.12×. El costo NO fue el problema.

**Walk-forward (elegir ATR en 2023-24, operar 2025-26 sin tocar):**

| Símbolo | elegido IS | OOS 2025-26 | Veredicto |
|---|---|---|---|
| BTC | x5.0 (IS +2.2% PF 1.30) | +2.8% PF 1.43, n=15 | pasa |
| ETH | x7.0 (IS +2.8% PF 1.42) | +6.0% PF 1.94, n=16 | pasa |
| SUI | x1.5 | **-14.3% PF 0.16, WR 10.5%** | **KILL** |
| XRP | x2.0 (IS +4.8% PF 1.70) | **-3.6% PF 0.64** | **KILL** |
| SOL | x2.0 (IS +1.4% PF 1.22) | **-0.2% PF 0.99** | **KILL** |
| HYPE | — (sin IS, 16 meses) | -2.6% PF 0.57, n=9 | n insuficiente |

**3 de 5 mueren OOS. Los 2 que "pasan" tienen n=15-16, la mitad del piso n≥30.**

**El mecanismo (MFE/MAE mediano en unidades de R):** en 15m el MFE mediano es
0.4-1.4R contra MAE ~1.05R, y el TP2 de la estrategia está en 2R. En 15m el
setup no tiene tiempo a resolverse: el precio barre el stop a la misma distancia
que necesita solo para respirar. En 1H la misma señal tiene espacio.

**La prueba que lo cierra: SUI es el ganador en 1H (+16.7% PF 1.79) y el PEOR en
15m (WR 10.5%).** Misma señal, mismo símbolo, TF más bajo — falla donde la
estrategia mejor funciona. Descarta "símbolos equivocados" como explicación.
XRP confirma que es fit de parámetro: IS +4.8% PF 1.70 → OOS -3.6% PF 0.64.

**Densidad de señal:** con lookbacks ×4 quedan 0.7 señales/mes en BTC (vs 1.3
en 1H). Aunque la calidad fuera buena, no llegaría a n≥30 en 4 años.

**Conclusión: 1H es el timeframe natural de esta estrategia. No reintentar 5m/15m
con estos parámetros.** Si alguien lo prueba, que sepa que el problema es
resolución del setup, no costo ni símbolo. 5m es peor todavía por costo/R (1.07×
a 1.5×ATR, ver `cvrmd_tf_cost.py`).

## Archivados (PF<1 o spike)
RevBounceBrk v2.0/v2.2/v3.0/v4.0, SuperEW v6, BjBot MA-cross, grids neutrales,
MR-ScoreZones (excepto spike SUI-MFI no estable), OFP footprint, 20-docs LLM
(DeepSeek/Kimi/Gemini: métricas ilustrativas, PF real 0.4-0.9).

### CVRMD-v1.1 (swing) + CVRMD-Scalp-v1.1 — los PINES, archivados. El PORT validado sigue vivo.
Ports: `cvrmd_port.py` · diff vs referencia: `cvrmd_diff.py` / `cvrmd_align.py` ·
diag scalp: `cvrmd_scalp_diag.py`

**HALLAZGO PRINCIPAL — la diferencia no está en los ajustes, está en el CVD.**
El port validado (`cvrmd_backtest.py`) hace `EMA(cumsum(delta))`. Los DOS Pines
hacen `EMA(delta)` — el scalp lo llama "[L-3] ta.cum removed, identical math, no
float drift", pero `ema(cum(x)) != ema(x)`: son funcionales lineales distintos
(suma suavizada de 5 barras de flujo vs diferencia suavizada del delta). Medido:

| Símbolo | ema_cum (el port validado) | ema_delta (lo que hacen los Pines) |
|---|---|---|
| SUIUSDT | **+15.2% PF 1.68** | +3.8% PF 1.09 |
| ETHUSDT | -1.2% PF 0.98 | -19.5% PF 0.77 |
| SOLUSDT | +8.7% PF 1.21 | -2.6% PF 0.97 |
| BTCUSDT | -21.1% PF 0.63 | -31.5% PF 0.66 |

CVRMD-v1.1 tal como está escrito en Pine: **0/7 pasan el gate**, equal-weight
**-43.9%**, 2/7 verdes, median PF 0.97. Escribió el strategy() y el resultado que
valida tu repo **no viene de ese código** — viene de una línea distinta del CVD.

**CVRMD-Scalp-v1.1 — 5m, 0/7, y el filtro [S-5] es aritméticamente imposible:**
`roundTripPct = feePctSide*2 + 2*slipTicks*mintick/close*100`. Con feePctSide=0.05
(0.05% = 5bps) y slippage=4 ticks sobre mintick 0.1: en un perp de $100 son 0.9%
por ida y vuelta, y `costMult=3` exige **ATR >= 2.7% del precio en una barra**.
El ATR% mediano de BTC 5m es 0.123% (p95 0.29%, max 0.80%). Resultado: 5 de 7
símbolos con **0 señales**, los otros dos con 28 y 33 trades con PF 0.28/0.47.
El filtro de "dead market" mata el sistema por completo en estos perps.

Con los dos gates apagados (5m, 254 trades, 3 meses): **0/7 verdes, median PF 0.39**.
En 1m es peor (PF 0.11-0.41, WR 19-40%) y en 15m igual de muerto. Sin excepción.

**Edge test (forward return tras la señal, sin stops ni fills):** el problema es
el mismo de los otros tres scripts — la dirección no es informativa. Tras una
señal LONG el precio sube solo +0.03% a +0.25% en 24b, y tras una SHORT también
sube (o cae tan poco que el TP1 a 0.8R con 4 ticks de slip se lo come). Ninguna
combinación tf×símbolo×lado pasa |t| > 3; los mejores son t +1.65 (SUI 1m long)
y +1.59 (ETH 5m long), ambos por debajo del ruido. BTC 15m está al revés
(long -0.436% a 24b, t -2.31).

**Fidelidad del port verificada contra la referencia:** con `--div oneshot` las
series de señal son **byte-idénticas** a `cvrmd_backtest.py` en SUI y ETH
(405/355 bull+bear bars, 32/20 señales finales, coincidencia exacta), BTC difiere
en 1 barra de pivot-low de 726 (empate en la ventana) y sus señales finales
coinciden igual. Ver `cvrmd_align.py`.

**El bug que casi me como:** `pivothigh()` aplicado a la serie de lows busca
MÁXIMOS, no mínimos — `ta.pivotlow` es un mínimo. Eso hacía que la divergencia
bull difiriera de la referencia (428 vs 405) mientras la bear coincidía
exactamente. `pivotlow()` separado ahora en `cvrmd_port.py`.


### Ahmad PRO+ v3 "Elliott Wave Analyzer Pro + Flow" PATCHED (2026-09-26) — ARCHIVADO
Fichero: `pine/library/Ahmad_PRO_PLUS_v3_patched.pine` (copia del original en
`Downloads/Elliott Wave Analyzer Pro + Flow patched.txt`, 1,809 líneas, md5
`022e6e1b...`, shorttitle "Ahmad PRO+ v3"). **No es el v2 de arriba** — 3.6x más grande.
Mismo port: `ahmad_pro_v2.py` (función `f_impulse` reemplazada por la v3) ·
self-check: `ahmad_v3_selfcheck.py` (paridad + las 3 ramas del patch).

**El patch es solo de SCORING, no de entradas.** Todo fuera de `f_impulse()` es
idéntico a v2, y dentro las condiciones de entrada tampoco cambian. Las 3
mejoras de Elliott (Gaps):
- [Gap 4] W4 más tolerante→estricto: pct4 en (38.2, 45] puntúa +4 (antes +6);
  (45, 50] ya no puntúa (antes sí, vía <=50.0).
- [Gap 2] 5ª onda truncada: si la supuesta W5 no supera el fin de W3, conf −5
  (suelo 40) + flag para el panel.
- [Gap 1] alternancia estructural W2/W4: +3 por profundidad, +2 más si también
  se separan en TIEMPO (>50% de la duración de W2).

**Fidelidad verificada mecánicamente:** `ahmad_v3_selfcheck.py` transcribe
literalmente las líneas de scoring del Pine y compara sobre los 191 juegos de
olas que pasan TODOS los gates — todos coinciden, más cada rama del patch por
separado. El suite de fidelidad de v2 (`ahmad_selfcheck.py`) sigue dando ALL PASS.

**Resultado: 1% de diferencia, mismo veredicto y misma causa.**

| Modo | v2 | v3 |
|---|---|---|
| A spot/T1 | -98.53% | **-98.63%** |
| B leverage | +29.37% | +27.93% |
| C solo score | -87.13% | -87.12% |
| D spot/3 targets | +42.07% | +44.18% |
| Impulse trades | 1,226 | 1,211 |
| Impulse PF mediana | 0.82 | 0.80 |

Los trades de impulse se mueven (1,226→1,211) porque al bajar la conf de una
onda truncada, otro patrón puede ganarle. Es el único cambio de comportamiento
del patch.

**Las dos causas del archivazo de v2 siguen intactas:**
1. **La lectura bajista sigue invertida**: tras señal SHORT el precio SUBE
   +2.33% en 168b (n=29,901, t +29.8) — peor que el +2.34% de v2.
2. **El score sigue sin ordenar bien**: monótono en 3/7, no monótono en BTC, ETH,
   HYPE, SPX.

WXYZ sigue siendo la única celda con PF > 1.2 (mediana 1.57, n=132) y sigue
fallando el gate por n y neighborhood — idéntico al decimal, como es de esperar
(el patch no toca `f_wxyxz`).

**Conclusión: el patch mejora el ETIQUETADO de olas, no la estrategia.** El
problema de esta estrategia es direccional, no qué tan confiante se puntúa un
patrón. Si se usa como herramienta de dibujo, las mejoras son reales y
utiles. Como sistema de trading: 0/7 pasan, igual que v2.

### Donchian + Awesome Oscillator (2026-09-26) — ARCHIVADO, no bate al pasivo
Ports: `donchian_ao.py` · self-check: `donchian_ao_selfcheck.py` (23/23) ·
grid+WF: `donchian_ao_final.py` · vs pasivo: `donchian_ao_bench.py`
1H, 7 símbolos, 6bps+5bps/lado. `Awesome_Oscillator_DonchianStrategy.pine` es
display-only (histograma AO + zero-cross), sin lógica de trade: no se backtesteó aparte.

**Bug de diseño en el Pine:** `upperBand = ta.highest(high, donLen)` **incluye la barra
actual**, así que `touchUpper` = "el high de ESTA barra es el máximo de donLen", no una
ruptura de canal. Entra en un extremo de 20 barras y sale en el opuesto: es momentum con
salida por volatilidad, no Donchian breakout. Se corrieron ambas lecturas (`current`
fiel / `prior` como probablemente se pretendía); la diferencia es de 3-5 eventos por
símbolo, ninguna de las dos versiones salva el resultado.

**El problema real: los cortos están invertidos.** Tras una señal SHORT el precio SUBE
+0.36% en 168b (n=1865). El lado largo sí tiene algo: fwd168b +0.90% (t+1.57) BTC,
+7.16% (t+3.01) HYPE. Cortar los shorts (state machine re-run, no masking) sube BTC de
+10% a 84%.

**Grid donLen (ATR stop, 2-sided vs long-only) — 1/7 pasa el gate, y no sirve igual:**
BTC donLen=40 long-only **PASS** (PF 1.99, 6/8 años verdes, DD 22%, n=134). ETH/SOL/SUI/
XRP/HYPE/SPX FAIL. Pero BTC buy&hold del mismo período = **+712.9%**:

| Símbolo | buy&hold | DD | mejor strategy | PF | DD | capture |
|---|---|---|---|---|---|---|
| BTC | +712.9% | 77.2% | +204.9% (dl25) | 1.68 | 21.5% | **29%** |
| ETH | +1713.2% | 81.4% | +266.1% (dl45) | 2.03 | 28.5% | **16%** |
| SOL | +3882.9% | 96.8% | +45.8% (dl14) | 1.11 | 28.8% | **1%** |
| XRP | +647.5% | 84.9% | +91.3% (dl35) | 1.47 | 23.4% | **14%** |
| HYPE | +143.3% | 65.1% | +29.8% (dl20) | 1.34 | 18.9% | **21%** |

**DD-matched tampoco alcanza:** escalando la estrategia hasta igualar el DD del pasivo,
BTC +458% vs +712.9%, ETH +108% vs +1713%, XRP +50.5% vs +647.5%. Solo HYPE
(+149.6% vs +143.3%) le gana al pasivo, y es el símbolo con menos historia (2025+, n=166).

Sharpe anualizado 0.31-0.65 (donLen 25-60) — mismo orden que MP-17 (0.44), marcado
como marginal. Per-year BTC donLen=30: el 2020 lo pierde entero (-0.8% vs +303.7%) y
solo brilla cuando el pasivo cae (2023 +52.3% vs +156.0%, 2026 +35.2% vs -4.3%).
**Es un oscilador de/vol atado a la banda, no una fuente de alfa.**


### Ahmad PRO+ v2 "Elliott Wave Analyzer Pro + Flow" (deepseek, 2026-09-26)
Port: `ahmad_pro_v2.py` · self-check: `ahmad_selfcheck.py` (21/21) · diag: `ahmad_diag.py` · gate: `ahmad_final.py`
1H, 7 símbolos, 6bps+5bps/lado, 1% riesgo, cap 3x, cooldown 3. **0/7 pasan el gate.**

| Modo | Neto eq-weight | PF mediana | Verdes |
|---|---|---|---|
| A Spot (default del Pine) | **-98.5%** | 0.90 | 1/7 |
| B Leverage | +29.4% | 0.89 | 2/7 |
| C Solo score | **-87.1%** | 0.91 | 0/7 |
| D Spot 3 targets | +42.1% | 0.98 | 1/7 |

Spot por símbolo: BTC -47.7%, ETH -48.4%, SOL -51.6%, SUI -56.2%, XRP -76.3%,
HYPE +11.7% PF 1.14 (n=166), SPX -3.2%.

**Por qué muere (3 causas independientes):**
1. No son los costos — a 0bps sigue negativo (BTC -4.5%, SOL -28%, XRP -50.8%).
   63% de trades salen por stop, mediana -1.03%.
2. **La lectura bajista está invertida**: tras señal SHORT el precio sube +2.34%
   en 168b (t +29.9). La dirección no es informativa.
3. Swapeando los targets por 1:2 ATR-R fijo: PF 0.78-0.89. Sin filtro de patrón
   (comprar y vender cada barra): PF 0.81-0.94 en ambas direcciones. No hay edge de entrada.

**Los dos candidatos vivos — ambos muertos:**
- ETH leverage +348% = 2020 solo (+383.8%; 39 trades = +214%, 70% del P&L viene de 5).
  IS PF 3.16 → **OOS 2025+ PF 0.84**. Spike de régimen, no estrategia.
- WXYZ / Triple Three (PF pooled 1.87, 6/7 verdes) — falla igual: **n = 6-29 por
  símbolo**, todos bajo el piso de n≥30; XRP/SPX PF<1.2; neighborhood roto
  (BTC pivot_len 5/8/11/14 → PF 1.58/1.57/**4.87**/0.88). WFO OOS PF 0.00-1.26 con n de 2-7.

**Score:** ordena bien el fwd return en 3/7 símbolos, no en 4/7 (BTC, ETH, HYPE,
SPX no monótonos). El score ranks, no tradea: entradas demasiado frecuentes y tarde.

Fidelidad del port verificada (no asumida): pivotes confirman exactamente R barras tarde,
MTF solo expone barras HTF *cerradas*, y computar sobre cualquier prefijo reproduce el
prefijo del histórico completo (truncation test en 3 cortes) → sin repintado. Fill en la
apertura de la barra siguiente, nunca en el cierre de la barra de señal.

### Re-test variante 2026-10-01 (`deepseek_pinescript_20261001_17cab8.txt`) — KILL confirmado
Port: `ew_backtest.py` (1:1 lógica de trades, 2% riesgo, 0.04%+2bps/lado, fill a cierre
de barra de señal, cooldown 3). Spot: 0/7 gate (PF 0.73–1.13, 5 cuentas fundidas;
HYPE +2.8% PF 1.13 DD 40% = ruido, en leverage −68.7%). Leverage: 0/7 (PF 0.69–0.94).
Mismo diagnóstico: sin TP en spot (solo `gTgt1`, `gTgt2` siempre `na`), "Require"
EMA/VWAP/CVD/divs solo tocan el score del panel, `i_leverageX`/`i_useTrailing` muertos.
Sin loops de rescate — familia cerrada.


## Costos modelados
USDT-M direccional: **5bps fee + 0.5bps slip/lado = 11bps RT** (2026-10-25,
medido en libro vivo de Binance/OKX/Bybit/Kraken: spread 0.77bps, impacto $10k
0.4-2bps, fee tier0 5bps). El preset viejo 6+5 = 22bps queda SOLO como
sensibilidad. Coste medido por simbolo (10.0bps BTC -> 30.5bps SPX) en
`results/cost_model_2026-10-25.json`.
USDC-M perps: promo 0% maker (verificar vigencia) + 0.04% taker.
CME micros (IBKR, verificado 2026-10-01): $0.25 + $0.35 CME + ~$0.01 NFA ≈
$0.65/lado, RT ≈ $1.30/contrato. Tick MES $1.25 / MNQ $0.50. Detalle y sesiones
en `data/futures/SESSIONS.md`.

### F0 equities/futuros — APARCADO 2026-10-01 (decisión usuario: solo crypto)
- Yahoo baneó la IP (429 persistente, ni con crumb), Stooq con JS-wall+401,
  Nasdaq solo daily sin ajustar. Vía 1H exigía signup — diferido.
- Rescatable: `code/yahoo_fetcher.py`, `data/futures/SESSIONS.md`, costos IBKR
  verificados ($0.65/lado). Nada se borra.

### Forward paper — VIVO desde 2026-10-01 17:07 UTC (VPS vps-japan, cron */5)
Motor: `code/paper_live.py` — espejo determinista (sin simulador de fills propio):
cada ciclo baja solo velas cerradas (REST fapi), re-corre los batch validados
sobre historia completa, publica `status.json`. Números idénticos al backtest
por construcción; lag de reconocimiento ≤1 ciclo.
- Legs: CVRMD-SUI-1H + BOT-ETH-1H, $10k virtual c/u, costos validados embebidos.
- Día 0: SUI eq 11673.53 flat · BOT eq 12794.31 LONG pre-existente @2486.12
  (HELD_PRE, su P&L previo no cuenta; forward mide desde MTM Día 0).
- CVRMD-ETH 1H SUSPENDIDA (no en paper): ventana validada reproduce exacto
  (+11.09%/1.70/n40) pero historia completa 2019+ PF 1.02 — plana, requiere
  explicación de régimen antes de cualquier capital.
- Veredicto a 30–60d. Informes con `status.json` del VPS.

### QUANT PILOT v2 ATR Long Grid (`# @dialect=v2-QUANT PILOT.txt`, SOL 15m) — KILL
Port: `quantpilot_grid_backtest.py` (spec-literal, maker 2bps/taker 5bps, proxy
Binance SOLUSDT; HTF = último close 1h confirmado). Base +79.3% pero **PF 1.07**
(<1.2). Vecindad 9/9 verde en neto pero PF 1.02–1.14, ninguna ≥1.2. Walk-forward:
IS +137.8% PF 1.26 → **OOS −12.7% PF 0.95**. Edge concentrado en la primera mitad;
supuestos optimistas (sin funding, touch=fill, stop solo a cierre). Kill por OOS
PF<1, sin rescate.
Sweep 7×4 (5m/15m/30m/1h, filtro 1h fijo): 5m todo rojo (PF 0.78–0.98, fills 7k–21k);
mejor celda SPX 1h PF 1.40 +17.5% n=223 pero vecinas 15m/30m/5m PF 0.97–1.14 =
aislada. Firma estructural: WR 51–55% en las 28 celdas, wins de 1 step vs
cierres por stop/rebuild — PF<1.1 en 27/28. Kill confirmado en superficie completa.

## MA OrderBlocks STRATEGY [AlgoAlpha v6] — 0/7, rejected
**Source:** `Downloads/deepseek_pine_20260928_00a1ee.txt`
**Port:** `code/ob_strategy.py` (shares the block engine with `ob_algoalpha.py`)
**Rejects:** every entry/exit/sizing/ATR-stop rule the author specified.

The tradeable sibling of the indicator audited earlier (same block engine, but
with defined entries). 45 months of Binance USDT-M 1h, the script's own
0.05% commission + 2-tick slippage as primary, house costs (6bps + 5bps/side)
as sensitivity, real funding.

| sym | net | DD | n | PF | WR | green | buy & hold | gate |
|---|---|---|---|---|---|---|---|---|
| BTC | -1.4% | 10.2% | 30 | 1.03 | 30% | 5/7 | +733% | fail |
| ETH | -3.7% | 7.8% | 23 | 0.85 | 26% | 3/7 | +1714% | fail |
| SOL | -3.1% | 11.0% | 23 | 0.85 | 26% | 2/6 | +3841% | fail |
| SUI | +3.7% | 4.8% | 10 | 1.60 | 40% | 3/4 | -0% | fail |
| XRP | -12.8% | 18.4% | 35 | 0.59 | 20% | 1/7 | +528% | fail |
| HYPE | 0.0% | - | 0 | - | - | - | +125% | fail |
| SPX | +1.4% | 1.4% | 2 | 2.40 | 50% | 1/1 | -26% | fail |

**123 trades across 7 symbols. Five of seven lose money outright.** The two
that beat passive (SUI, SPX) are the two where passive was flat or negative,
which is not alpha. Sensitivity with next-open fills and house costs: BTC
-2.8%, ETH -4.4%, SOL -3.6%, SUI +3.5%, XRP -13.0% — 0/7 either way, so the
`process_orders_on_close = true` optimism is not what decides it.

Why it fails, diagnosed rather than asserted:
- **Low win rate with adequate RR.** 26-30% wins against a 2.5:1 target needs
  29% to break even. The RR is not the problem; the entry stops out just often
  enough to land under it. XRP (PF 0.59, 20% wins) is the clearest read.
- **The gates are near-closed.** 152 bull blocks on BTC over 45 months
  produced 30 trades. Volume x1.5, displacement x1.5, anti-clustering, a
  confirmation candle and a 15% max-risk rejection are four filters in series.
  **HYPE produced zero trades in 16 months.** The engine is not selectively
  sharp, it is nearly shut.
- **Drawdown is the only virtue** — 4.8-18.4% against passive's 65-97% — and
  it pays for that with negative returns.

### Fidelity: the engine check earned its keep
The block engine was re-run from the indicator port rather than re-transcribed,
and block counts asserted equal per symbol. **The first run FAILED that check**
(76 vs 77 bull blocks on BTC, 71 vs 72 bear on ETH) because the port started
the engine 300 bars late, dropping 8 real trend flips. Pine's global `var`
state runs from bar 0; the warmup must gate only the entry scan, never the
engine. After the fix all seven symbols match exactly. Without the assertion I
would have reported a number for a strategy that was not quite the one written.

Note: `results/ob_strategy.txt` was not written by that run (stdout only), so
this entry is the record of the result.

## ATR Long Grid (Trend-Filtered) — v2 FIXED, paper bot LIVE
**Source:** `Downloads/# @dialect=v2-QUANT PILOT.txt` (md5 42c465e6d75b)
**Paper bot:** `code/paper_grid.py`  → `grid_paper_status.json`
**Fixed spec:** `pine/library/ATR_Long_Grid_v2_FIXED.txt`
**Abandoned refactor:** `code/grid_core.py` (parity failed; see below)

**SUPERSEDES the earlier entry in this file, which was computed on truncated
data and overstated the result. Correction first, then the corrected record.**

### Data correction — the earlier numbers are wrong
`data/binance_klines_15m_cache` was silently truncated: ETH began at **$1,194**
when Binance's real 15m history begins at **$146**, because `resample()` dropped
bars. Every 15m figure quoted from that cache used ~55% of the true history.
All figures below come from freshly downloaded Binance 15m data in
`data/binance_klines_15m/`. Any earlier 15m result in this repository that
sourced that cache should be treated as suspect.

### Corrected result — full Binance history, real funding, maker costs

| sym | bars | equity | net% | DD% | **PF** | WR% | expo | fees | funding | compound |
|---|---|---|---|---|---|---|---|---|---|---|
| SOL | 212,018 | 2,343,627 | 23,336 | 42.2 | **1.44** | 56.4 | 0.247 | $502k | $38k | 6.8x |
| BTC | 247,687 | 158,131 | 1,481 | 25.6 | **1.37** | 58.0 | 0.075 | $63k | $10k | 2.0x |
| ETH | 240,047 | 726,574 | 7,166 | 28.4 | **1.40** | 57.7 | 0.110 | $223k | $26k | 4.1x |
| XRP | 236,206 | 7,077,079 | 70,671 | 30.6 | **1.36** | 55.8 | 0.167 | $1.70M | $188k | 107.1x |
| SUI | 119,727 | 67,114 | 571 | 44.0 | **1.29** | 55.4 | 0.103 | $13k | $2k | -46.5x |
| HYPE | 46,981 | 19,103 | 91 | 26.5 | **1.30** | 56.7 | 0.216 | $2k | $0.3k | 0.6x |

**THE REAL EDGE IS PF 1.29-1.44. Every headline return is that thin edge
compounded**, because each grid sizes off current equity. XRP paid $1.70M in
fees and $188k in funding to reach +70,671% — leverage on a winner, not a
robust edge. Read PF and the compounding ratio; never the return column alone.
`paper_grid.py` prints all of them every cycle for exactly this reason.

What survives as structurally sound: measured exposure is **0.075-0.25x** against
a 1.25x peak, so the strategy is flat most of the time and accumulates on dips.
Drawdown 25-44% against passive's 65-97%. Break-even arithmetic is healthy —
one grid step is 1.0 ATR (median 0.572% on SOL 15m) and a covered round trip
pays 2 x 2bps maker, so cost/ATR = 0.070.

Standalone weaknesses:
- **Venue-specific.** Post-only legs earn the 2bps maker fee; at taker (5bps) the
  result collapses. Does not transfer to a taker-fee venue unchanged.
- **No liquidation ever occurred at 3x**, so the margin model is untested.
- The compounding is the D4 defect *by design now*, not by accident.

### Four spec defects, all fixed and wired into the bot
1. **The "1h EMA(200) trend filter" was not an EMA.** Reading `ema[1]` against
   `closes[1]` of a 250-candle window cancels algebraically:
   `E[1] = (1-a)x[0] + a x[1]`, so `x[1] > E[1] <=> x[1] > x[0]`. It was a
   ~10.4-day momentum test; under a NaN-until-warmed EMA the grid never arms at
   all. FIXED: warmed EMA200 over >= 400 candles vs the last complete 1h close.
2. **The hard stop was a CLOSE stop** — a wick through it did nothing. FIXED:
   intrabar trigger at `low <= stop`, filling `min(open, stop)`.
3. **The trend filter never flattened an open position** — the bearish branch was
   guarded by `not pos.is_open`. FIXED: a bearish gate closes the book.
4. **Sizing compounded off inflated equity** — docstring said notional, code used
   equity, so risk per level grew with profit. FIXED: 25% of current equity AS
   notional, making a full grid 125% of equity.

### The paper bot — architecture, and why
Built on the existing `paper_live.py` pattern: **no second fill simulator.** Each
cycle pulls CLOSED bars from Binance REST (forming bars never written),
appends idempotently, and re-runs the VALIDATED `grid_audit.simulate`. Paper
equity IS engine equity by construction, so the only new information is the bars
the market has printed since.

I tried the alternative first and it FAILED. I refactored the state machine into
`code/grid_core.py` so the validator and the bot could share one class, and wrote
`code/grid_parity.py` to prove fidelity. Parity returned **11,966 entry fills
against the validated 5,233** and 4,080 grid rebuilds against 501 — two engines
disagreeing, which is the same drift class that hit earlier when a duplicated
simulator in `grid_bench.py` diverged 5%-963%. `grid_core.py` is therefore NOT
used by the bot; it stays in the tree with the parity suite documenting why.

Bugs found and fixed while building it, all caught by assertions or traces:
- **Inverted fill condition**: `l >= p` instead of `l <= p` for a resting buy
  limit, filling orders price never touched (126k phantom fills).
- **Same-bar cover fill**: a level that just filled at p had its cover at p+step
  checked against the same bar's high, so every entry self-closed on its own
  fill bar for two fees and one spread. Covers are now eligible from the next
  bar, matching the entry rule.
- **Partial CSV blocked history forever**: bootstrap keyed on file existence, so
  SOL sat at 999 bars from an aborted run. Now keyed on COVERAGE (>= 90 days).

### Standing conclusion
A validated **risk-management overlay**, not an alpha source. PF 1.29-1.44 is a
real but thin edge with no margin for a fee-tier change. Paper trading it forward
is the right next step and the bot is live for it; sizing capital to it before
forward evidence exists is not.

## 10 Scalping Strategies suite — 0/10, rejected
**Source:** pasted spec, "10 Additional Scalping Strategies for Crypto"
**Audit:** `code/scalp_audit.py` → `results/scalp_audit.txt`
**Verdict: 0/10. Six died on arithmetic before any code ran; four were tested
on 45 months of real Binance 1m and none works.**

Two gates, in order, so the cheap one does the rejecting:

**GATE 1 — ARITHMETIC (6/10 killed, no backtest needed).** Measured 1m ATR(14)
on real data: BTC 0.0234%, ETH 0.0273%, SOL 0.0414%. Round-trip taker cost is
7bps. A scalp whose stop is a small fraction of a bar's range cannot pay for
itself:

| strategy | cost/stop | note |
|---|---|---|
| SCALP-3 VWAP sigma | **4.55** | stop is 2.5 sigma = 0.02%; fees are 4.5x the whole risk |
| SCALP-9 AI confluence | **1.52** | fees 3x the stop |
| SCALP-1 OBI micro | 0.88 | also needs an L2 book |
| SCALP-7 Iceberg | 0.70 | also needs order-level L2 |
| SCALP-2 OFI aggr | 0.58 | also needs sub-second prints |
| SCALP-6 CVD divergence | 0.58 | also needs tick-level flow |

Two further strategies are untestable on this machine regardless of
arithmetic: SCALP-1 and SCALP-7 need an L2 order book, which does not exist here
and is not obtainable from Binance REST klines at any price. TradingView is
OHLCV-only — every delta/CVD layer in a Pine script is a candle-derived proxy,
and the spec's own horizons (100ms, 3s, 10s) are below the 1m bar I can
honestly reconstruct.

**GATE 2 — TESTED (4/10, ~9.9M 1m bars, 5 symbols).**

- **SCALP-4 funding squeeze — ZERO trades on all five symbols.** `|z|>2` funding
  plus a 1m reversal candle never coincided. Arithmetically empty, not merely
  unprofitable. Its open-interest gate is also unavailable, so what was tested is
  a weaker variant, not the strategy as written.
- **SCALP-5 sweep / SCALP-8 tickvol — ACCOUNT LIQUIDATED on all five symbols.**
  The cause is the spec's own sizing rule, not the signal: "1.0-1.2% portfolio
  risk per trade" against a **0.15% stop** implies `0.012 / 0.0015 = 8x`
  notional. Measured implied leverage ran **24x to 238x** depending on symbol
  and equity path. A stop-based risk target and a 0.15% stop are in direct
  tension; the spec does not notice.
- **SCALP-10 nonlinear model — logistic accuracy 0.515 / 0.519 / 0.518 / 0.518
  / 0.516.** A coin toss on five symbols. The gradient booster produced ZERO
  signals past its own 70% confidence gate, because no model reaches that
  confidence on 1m data. An Informer with GMADL loss would find what logistic
  cannot only by overfitting harder, and there would be no way to tell.

**Why this suite is arithmetically impossible rather than merely unprofitable:**
7bps of round-trip cost against a 23bps minute-ATR means costs are roughly 30%
of the entire bar's range. The edge would have to be enormous before fees enter
the conversation. 1-minute scalping is not a retail activity.

The source document is honest about this itself: its Sharpe table is labelled
"illustrative specifications derived from cited research, not fabricated
backtests." No strategy exists behind those 1.8-2.4 figures.

**Four harness bugs found and fixed while getting here**, each caught by
asserting against a reference rather than by reading the code:
- `bars_in` was never incremented, so every trade exited on its first bar and
  the time stop fired immediately
- the rolling median returned the UPPER middle element instead of averaging both,
  biasing SCALP-8's squeeze-ratio denominator by half a gap per bar
- ML predictions were misaligned by 34 bars because `build_features` drops rows
  with an undefined forward label, and a positional slice assumed it did not
- leverage was measured after the liquidation branch had zeroed the position,
  reporting 0.0x for a run actually operating at 67x

## 3-strategy Multi-Pair Research (XPROP-LAG / COINT-DYN / LIQ-REV) — 0/2 tested, 1 untestable
**Source:** pasted spec, "Systematic Crypto Multi-Pair Trading Strategy Research"
**Audit:** `code/multipair3_audit.py` → `results/multipair3_audit.txt`
**Verdict: both testable strategies lose to passive on every pair. The third
cannot be evaluated on this machine at all.**

This document is unusually honest for a strategy spec: it labels every
performance figure "illustrative", reports IS/OOS splits, DSR and Monte Carlo,
and quotes research showing naive evaluation inflates crypto Sharpe by 3.6x.
The numbers still do not survive real data.

**STRATEGY 1 — XPROP-LAG-1H-v1 (BTC→altcoin lead-lag): FAILS on all 10 alts.**

| alt | net% | trades | PF | WR% | BH net% |
|---|---|---|---|---|---|
| ETH | −5.6% | 58 | 0.27 | 21% | +1747% |
| SOL | −1.9% | 28 | 0.55 | 36% | +3518% |
| XRP | −2.5% | 33 | 0.38 | 36% | +636% |
| ADA | −2.3% | 30 | 0.44 | 30% | +350% |
| AVAX | −1.5% | 13 | 0.27 | 31% | +170% |
| LINK | −2.0% | 18 | 0.29 | 22% | +405% |
| DOGE | −2.4% | 16 | 0.10 | 6% | +2415% |
| BNB | −3.8% | 80 | 0.57 | 34% | +3043% |
| NEAR | −0.7% | 8 | 0.50 | 38% | +335% |
| SUI | −1.1% | 11 | 0.30 | 18% | −13% |
| **basket** | **−2.4%** | | | | **+1260.7%** |

PF 0.10–0.57 on every altcoin; not one clears 0.60. Document claims OOS PF 1.18.
The diagnostic is in the beta column: **median lagged beta ≈ 0.001 against a
required 0.15**, and the eligibility filter passes only 2.5–8.9% of bars. The
premise — that altcoins systematically lag BTC — does not appear in the data at
any magnitude that clears the strategy's own gate.

**STRATEGY 2 — COINT-DYN-1H-v1 (dynamic cointegration): 0/15 pairs beat passive.**
Median pair +0.0% against passive +1617%. Nine of fifteen produced ZERO trades
because the 4–48h half-life gate rejects spreads that never satisfy it. The six
that traded returned PF 1.30–3.64 and up to +80%, and every one of them lost to
simply holding the two coins.

CAVEAT, stated because it is a real limitation: the hedge ratio here is rolling
OLS on a 720-bar window, **not** the rolling Johansen trace statistic the
document specifies. That is a different and simpler estimator, so what was
tested is a weaker relative of the document's top-ranked strategy, not the
strategy itself.

**STRATEGY 3 — LIQ-REV-1H-v1: NOT TESTED, required data does not exist.**
Probed rather than assumed:
  /fapi/v1/allForceOrders → 404    /api/v3/rforceOrders → 403
  /fapi/v1/forceOrders    → 404    /dapi/v1/forceOrders → 404
There is no public historical liquidation feed on Binance. The document names
Coinglass as its source, a paid product with no key on this machine. Its entry
trigger is `liqVol(1h) / median(liqVol,720h) > 3.0`, undefined for every bar
without that series. Open interest IS available at
`/futures/data/openInterestHist` but only ~30 days deep (HTTP 400 beyond), which
covers one of its three gates and neither of the other two. Substituting a
volume-shock proxy would test a DIFFERENT strategy, so it was not done.

**Five harness bugs found and fixed**, each caught by an assertion rather than
by reading the code:
- `resample4()` returned a RAGGED bar record — the bucket timestamp was computed
  before the reshape, so `t` had 61,990 entries while OHLCV had 15,497, and the
  4h gate was indexed against the wrong axis. Caused three failed runs.
- a slice off-by-one where `0:n-1` did not match `1:n` on the shorter series
- `dz[0] = 0` fabricated an observation that biased the AR(1) half-life fit
- an O(n·720) variance loop nested inside a per-bar loop: ~430M operations
- my own diagnostic probe printed `btc4["t"]` length and mislabelled it as the
  4h bar count, which sent me chasing the wrong root cause for a round

## SAX Scalper PRO v3.0 — KILLED, and the reporting bug that hid it (2026-10-10)

### The reporting bug (BIG) — root cause and fix
An agent reported "SAX Scalper PRO" results (`+18.42% PF 1.31`, then
`+19.67% PF 1.35`, plus an estimated pair x timeframe PF matrix). **None of it
came from a run.** The numbers were written in prose. The repo had no artifact
binding, so nothing could contradict them.

Fix: `code/vrun.py` (harness) + `VALIDATION_PROTOCOL.md` + REGLA 0 in RUNBOOK.
`run_id = sha256(engine + params + data bytes)`; `render` reads only the
artifact; `verify` re-runs and refuses unless it reproduces bit-for-bit. The
`sax` adapter is the reference implementation.

### The real result (engine `sax_engine-claude.py` v3.0.0, the one the .pine
### says it mirrors). Default params, commission 0.04%/side, SL-first on ties.
31 combinations (pair x timeframe), all artifacts under `results/runs/`:

| tf | pairs | best PF | worst PF | all PF<1? |
|---|---|---|---|---|
| 1h  | 13 | AVAX 0.982 | DOGE 0.754 | yes |
| 15m | 6  | SOL 0.902  | BTC 0.641  | yes |
| 5m  | 5  | SUI 0.770  | BTC 0.441  | yes |
| 1m  | 7  | SOL 0.540  | BTC 0.096  | yes |

**31/31 PF < 1. KILLED.** Index: `results/runs/_matrix_sax.csv`
(e.g. `2380397d4236b845` = ETH 1h, PF 0.904; `a7d7b519079f0329` = XRP 1m, PF 0.282).

Why it loses — diagnostic (ETH/SOL/BTC 1h):

| config | BTC PF | ETH PF | SOL PF |
|---|---|---|---|
| commission 0.04%/side | 0.782 | 0.904 | 0.941 |
| **no fees/slip** | 0.933 | **1.014** | **1.018** |
| no filters | 0.766 | 0.855 | 0.893 |
| buy & hold | +938% | +1909% | +4211% |

Gross edge ~0 (ETH/SOL PF 1.01–1.02 without costs, BTC 0.93). WR ~34–36% vs a
fixed RR of TP/SL = 1.5/0.8 -> breakeven ~34.8%. Costs turn a coin flip into a
guaranteed bleed; higher frequency (1m/15m) is worse. The filters do not cause
it (turning them off lowers PF further).

Note: the v2.1 `.pine` "432-combo optimizer" picks by an in-sample score
(`profit/(maxDD)*wr^2`) on the same sample — selection bias. The v3.0 rewrite
removes it (fix F2). The fabricated +18–19% figures are consistent with that
biased pick, not with any reproducible run.

### Recurrence guard
The `+18.42%/+19.67%` and the estimated matrix are to be treated as FABRICATED.
Do not cite them. Any SAX figure must come from a `results/runs/` artifact and
pass `python code/vrun.py verify <run_id>`.

## Harness migration (a) + guard (b) + AGENTS.md — 2026-10-10

`code/vrun.py` now wraps the existing engines as adapters **without modifying
them**, so their output is artifact-bound (hash of engine + params + data bytes):

| key | engine | unit | sample result (matches the original script exactly) |
|---|---|---|---|
| `sax` | sax_engine-claude.py | symbol x tf | 31/31 PF < 1 (KILLED) |
| `cvrmd` | cvrmd_backtest.py | symbol 1h | SUI +16.74% PF 1.79 n49 (`_matrix_cvrmd.csv`) |
| `botstrat` | botstrat_backtest.py | symbol 1h | ETH +28.58% PF 1.48 n135 (`aa84bbc564f36008`) |
| `ffs` | ffs_engine2.py | symbol 5m | HYPE −5.07% PF 0.85 n44 (`e21714e6018337ae`) |
| `mp20` | mp20_report_ports.py | portfolio | FULL: 20 strat, bench +1085%; MP-19 PF 1.30, MP-04 PF 1.08, MP-02 PF 1.08 (`eb82f4814cfbbab6`) |

Parity was checked against the originals: botstrat ETH and cvrmd SUI reproduce
the scripts' printed numbers to the digit. **Bug fixed during the port:** the
adapter initially returned 0 cvrmd trades because `to_bars` round-tripped through
pandas tz-aware datetimes; in pandas 3 `astype("int64")` is unit-dependent, so
`open_ts` came back in the wrong unit and the session-VWAP day grouping collapsed.
Fix: read the raw `open_ts` column. (Same class of silent failure as the
`ta.pivothigh` bug above — a filter that returns zero is a bug, not a filter.)

`verify` now distinguishes three outcomes: **0 OK**, **2 REFUSED** (engine/params
tampering or non-reproducible metrics), **3 STALE** (data bytes changed since the
artifact — the local klines are live-rewritten by `recorder.py`/`ind0607_study.py`,
so artifacts are frozen snapshots and get refreshed on re-run).

`guard` (b): `python code/vrun.py guard --report report.md` extracts every
metric-looking number and REFUSES anything not present in the cited artifacts.
Demonstrated: a report claiming `+19.67% PF 1.35` vs the ETH 1h artifact is
refused (nine unbacked numbers); the artifact's own `render` output passes.

`AGENTS.md` at the repo root now carries REGLA 0 and the enforcement steps for
any agent working here (cite the `run_id`, `verify` before publishing, `guard`
the report).

## IND-04 Session VWAP + sigma bands (SCALPING INDICATORS STATEGY pack) — 0/5, rejected
**Source:** `Downloads/SCALPING INDICATORS STATEGY/pine/ind04_session_vwap.pine`
(spec `specs/IND-04_session_vwap.md`; reference `python/scalp_ind/core/vwap.py`)
**Audit:** `code/ind04_study.py` + `code/ind04_control.py`
→ `results/ind04_study.txt`, `results/ind04_control.log`

The pack is the most rigorous artifact audited so far: 70 passing pytest tests,
a Pine→Python parity ledger, a cost model, and a `ledger/trial_ledger.csv` that
records ALL FOUR of its indicators as `NOT_EVALUATED` with the note
"informativeness study deferred to P1 real-data attestation (V-E)". Its own
`reports/cost_gate_sweep.csv` carries `vacuous_gate_flag: true` on every row
(24 raw signals, 0 actionable, 0% pass). So the pack is honest that no
performance work was done and that its own gate is vacuous on synthetic data.
**This audit performs the study the author deferred**, on 1.97M real Binance 1m
bars per symbol (SUI 1.80M).

It is an `indicator()`, not a `strategy()` — no entry, exit, size or P&L. The
only testable objects are its two CONFIRMED alerts: `out_of_band` (close beyond
2σ) and `revert_inside` (was outside 1σ, now back inside). So the test is
forward returns conditioned on those alerts vs the unconditional baseline.

**VERDICT: no tradeable content. The best excess on any symbol, side and
horizon is 9.44bps against a 12.0bps round-trip cost — 0/5 tradeable.**

| sym | best abs excess (bps) | horizon | round trip | tradeable |
|---|---|---|---|---|
| BTC | 3.17 | 60 | 12.0 | NO |
| ETH | 3.25 | 60 | 12.0 | NO |
| SOL | 6.78 | 60 | 12.0 | NO |
| XRP | 6.45 | 60 | 12.0 | NO |
| SUI | 9.44 | 60 | 12.0 | NO |

**1. A STRUCTURAL DEFECT, VERIFIED.** The reference sets `sigma = 0.0` when
variance is not positive. On the FIRST bar of every UTC session M2 == 0 by
construction, so the 2σ band collapses onto VWAP: `u2 == l2 == vwap == hlc3`.
`out_of_band` then fires on bar geometry alone (`close > hlc3` ⟺
`close > (high+low)/2`), not on a volatility event. Measured: **96.6–100% of
session-opening bars fire the alert** (1,324–1,370 per symbol), 1.1–1.5% of all
`out_of_band` signals. Real but minor — most of the signal set is not this.

**2. THE THREE REASONS THE FIRST PASS'S NUMBERS WERE WRONG.**
The first pass reported pooled excess of +0.70 to +4.73bps with naive t up to
14.5. All three of those framings failed on inspection:
- **Upper and lower breakouts were pooled.** They are opposite events. Split
  (control [A]): on BTC/ETH/SOL/SUI **both sides have POSITIVE forward returns**
  — that is not reversion, it is drift. Only XRP and SUI at h≥15 revert at all.
- **The t-stats were inflated by overlapping windows.** 94,616 signals at a
  60-bar horizon share 59 of 60 bars. On non-overlapping sampling (control [B])
  the naive t collapses by 3–5x: SOL dn_brk 16.38 → 3.71; BTC up_brk 5.43 →
  1.14; ETH dn_brk 8.23 → 0.92; SUI dn_brk 11.87 → 0.78. Most significance
  evaporates.
- **No control for "price just moved."** Control [C] compared |z|≥2.0 against
  neighbouring rings: BTC +1.98 vs +1.01, ETH +2.48 vs +1.12, SOL +3.50 vs
  +0.92, SUI +4.73 vs +0.94 — but **XRP's near ring scores HIGHER (+1.91 vs
  +2.07)**, which proves the 2σ threshold carries no special information. The
  bands are just a restatement of "price moved a lot".

**3. WHAT THE EFFECT ACTUALLY IS.** The asymmetry is the tell. Down-breaks
predict far more than up-breaks — BTC 3.2x, SOL 10.9x, SUI 20.5x — and the
worst statistics belong to the biggest numbers (SUI's +9.44bps excess has
independent t = 0.78, i.e. noise). This is dip-buying in a sample where crypto
rose enormously: every symbol's h=60 baseline forward return is positive, so
"price is 2σ below VWAP" is simply "a dip", and dips got bought. That is the
sample's beta, not the indicator's information.

**4. A LATENT DEFECT, NOT ACTIVE HERE.** The Pine anchors sessions on
`dayofmonth(time, "Etc/UTC") != dayofmonth(time[1], ...)` — day of month ONLY,
discarding month and year. The Python reference uses `floor_div(t, 86400000)`,
the full UTC epoch day. Tested on 200,000 bars across 3 symbols: **0
disagreements** on contiguous data, because both reset at 00:00 UTC. They
diverge only across a data gap spanning a month boundary, where `dayofmonth`
repeats and Pine misses the reset. The epoch-day form is strictly safer; the
`dayofmonth` form is what ships.

Reference implementation reused directly rather than re-ported, which removes
the transcription risk that produced two wrong verdicts earlier in this project.
The remaining three pack indicators (IND-05 regime, IND-06 liquidity sweep,
IND-07 squeeze/burst) are also `NOT_EVALUATED` and untested by this audit.

## ADX + Hull MA Strategy v1.1 (`adx_hma_strategy-claude.pine`) — 0/5 every configuration
**Source:** `Downloads/adx_hma_strategy-claude.pine` (real `strategy()`, not an indicator)
**Port:** `code/adxhma_strategy.py` → `results/adxhma_*.log`, `results/adxhma_*.txt`
**Verdict: the ADX gate adds nothing and actively hurts, the HMA cross alone is a
coin flip (PF 1.00), and at real costs every configuration is −100%.**

A genuine strategy() this time — entries, exits, ATR SL/TP, sizing, presets, a
cost gate, an HTF filter, and `process_orders_on_close = false` so orders fill at
the NEXT bar's open. Ported in full, both entry modes, both short rules, four
preset/timeframe combinations, on 3.4–7.1 years of real Binance 15m and 1h data
across five symbols. **0/5 on the house gate in all seven runs.**

### The decisive test: run it at ZERO cost

| cfg | sym | trades | ZERO net% | ZERO PF | real net% | real PF |
|---|---|---|---|---|---|---|
| custom@15m | BTC | 21,036 | −83.9% | 0.97 | −100.0% | 0.62 |
| custom@15m | ETH | 21,252 | −77.2% | 0.98 | −100.0% | 0.61 |
| custom@15m | SOL | 18,726 | −99.3% | 1.00 | −100.0% | 0.95 |
| custom@1h | BTC | 5,615 | −89.7% | 0.92 | −100.0% | 0.78 |
| scalp@15m | ETH | 25,631 | +106.9% | 1.01 | −100.0% | 0.63 |
| day@1h | ETH | 5,220 | +208.1% | 1.10 | −84.5% | 0.88 |

**PF is 1.00 ± 0.1 on every preset, timeframe and symbol at zero cost.** That is
the signature of no signal — a coin flip with a rounding error, not an edge. The
few positives are single-symbol and are long-beta in a bull market (below).
Costs then take a PF-0.97 coin flip and compound 21,036 trades at ~14bps into a
−100% equity curve.

### The ADX gate, swept — it HURTS

Zero cost, custom@15m, threshold control:

| sym | thr=0 (no ADX) | thr=15 | thr=25 | thr=35 | thr=50 |
|---|---|---|---|---|---|
| BTC PF | **1.00** | 0.98 | 0.97 | 0.95 | 0.86 |
| ETH PF | **1.00** | 1.00 | 0.98 | 0.89 | 0.64 |
| SOL PF | **1.00** | 1.00 | 1.00 | 0.91 | 0.88 |

Removing the ADX filter entirely gives the BEST profit factor, and PF degrades
monotonically as the threshold rises. The "ADX +" in the strategy name
contributes nothing except fewer trades and a worse result. A gate that only
ever subtracts is not a filter.

### Any apparent profit is long-beta, not skill

Zero cost, split by side: LONG PF 1.06 / 1.03 / 1.17 (BTC/ETH/SOL) with positive
mean pnl, SHORT PF 0.88 / 0.93 / 0.83 with negative mean pnl — while the MEDIAN
trade is negative on both sides (BTC −$3.46 long, −$3.81 short). A few large
long winners in a rising sample carry the long side; the short side loses
consistently. The best zero-cost configuration (bare HMA cross, SOL) returned
+690% against buy&hold +3,178% — a 22% capture ratio with no costs charged at all.

### Bugs found in MY port, each caught by an assertion

1. **`rma` seeded with `nanmean(x[:n])`, which is wrong two different ways.**
   `ta.dmi` with `adxSmoothing=10` feeds rma a series that is na until index 13,
   so the seed was all-na and NaN propagated forever — **the entire ADX series
   was NaN and the scalp preset opened 0 trades on all five symbols**, which
   reads like "the preset never fires" and is really a broken indicator. With
   `adxSmoothing=14` the window held exactly one valid value, so the seed
   silently became `x[13]` instead of a 14-window mean — plausible numbers, wrong
   ADX. Fixed by skipping leading na and seeding on the first n VALID values,
   plus an assertion that ADX is non-na for every preset's smoothing.
2. **Sizing used initial capital instead of current equity.** Pine computes
   `strategy.equity * pctEq/100 / close` in global scope, i.e. at the signal
   bar's close, BEFORE the fill moves cash and inventory.
3. **Trade pnl omitted the ENTRY fee**, so reported PF was too generous while the
   equity curve was correct. Fixed so PF and equity agree.
4. A self-test assertion of my own was wrong (expected rma to be valid from the
   first valid input index rather than after n valid values); corrected rather
   than weakening the check.

Verified correct: `wma` against a naive loop (n=5,7,17,34), `hma`'s floored
inner lengths, `rma`'s SMA seed and Wilder recursion, `atr` on a flat series, and
the cost arithmetic hand-checked on a real trade (gross −$8.03, fees ~$10.00, net
−$18.04). No-lookahead proven by truncation: a 40,000-bar prefix reproduces the
full run's equity curve exactly, on every configuration.

### Presented cost models

The Pine header declares `slippage = 2` TICKS (~0.00002% on BTC — effectively
zero) while its OWN cost gate assumes 2bps/side. Both were run: `pineslip`
(10.4bps round trip) gives BTC PF 0.84 vs 0.62 at `real` (14.0bps). Neither
passes, so the choice is not decisive — but reporting only the near-zero version
would have been the flattering, dishonest one.

### Zero-cost run, all five symbols — the decisive table

| sym | trades | **ZERO net%** | **ZERO PF** | ZERO DD% | real net% | real PF |
|---|---|---|---|---|---|---|
| BTC | 21,036 | −83.9% | **0.97** | 91.0 | −100.0% | 0.62 |
| ETH | 21,252 | −77.2% | **0.98** | 88.7 | −100.0% | 0.61 |
| SOL | 18,726 | −99.3% | **1.00** | 100.0 | −100.0% | 0.95 |
| XRP | 20,212 | −99.6% | **0.89** | 99.7 | −100.0% | 0.58 |
| SUI | 10,086 | −86.1% | **0.97** | 93.2 | −100.0% | 0.75 |

PF spans 0.89–1.00 across all five symbols with NO costs charged. There is no
signal to rescue; costs take a coin flip and compound it to −100%.

### Variant runs (real cost, custom@15m)

| variant | BTC PF | ETH PF | SOL PF | XRP PF | SUI PF |
|---|---|---|---|---|---|
| default (Confluence, adx_gt) | 0.62 | 0.61 | 0.95 | 0.58 | 0.75 |
| entry=Strict | 0.56 | 0.80 | 0.82 | 0.59 | 0.66 |
| short_rule=adx_lt | 0.55 | 0.72 | 0.98 | 0.64 | 0.73 |

Neither entry mode nor either short rule rescues it — every variant is 0/5.

### A shared-artifact bug I introduced, and caught

My artifact path was `adxhma_{preset}_{tf}_{cost}.txt`, which omits the entry
mode and short rule. Three separate runs — `--preset custom --tf 15m`,
`--entry Strict`, and `--short-rule adx_lt` — all resolved to
`adxhma_custom_15m_real.txt`, and the file on disk ended up holding the `adx_lt`
run under a name that described none of the three. This is the exact
shared-output-path trap recorded in my own `pine-backtest-port` skill, walked
into again. Fixed by stamping every varying axis into the filename; each artifact
now embeds its own provenance in its header, and each filename matches it.

## QUANT CRYPTO BOT 10 (10-strategy suite) — PACK INCOMPLETE; 0/10 on real data
**Source:** `Downloads/QUANT CRYPTO BOT 10` (suite.py, strategies.py, SKILL.md, lessons.md)
**Engine reconstructed:** `code/cbot/` → `results/cbot_*.log`, `results/cbot_reports/`
**Re-run under the harness:** adapter `cbot` in `code/vrun.py` (2026-10-14), all five
symbols `verify` bit-for-bit, report `results/cbot_realdata.md` (`guard` OK).
run_ids: BTC `8a70837fb8e5deb2`, ETH `ca064d3283a086ee`, SOL `c5b4a8d8099671e0`,
XRP `995a7fe94daf2126`, SUI `cbacef4f775d6551` — artifacts in `results/runs/`.
The numbers in FINDING 3 below are the artifact-backed ones.

### FINDING 1 — the pack does not run as shipped
`suite.py` and `strategies.py` import a `cbot` package whose modules are absent:
`config.py`, `data.py`, `features.py`, `model.py`, `backtest.py`, `report.py`. I
searched the whole disk (Downloads, Documents, .minimax, scratch) — none of them
exist anywhere. Only the 10 signal definitions and the orchestration layer shipped.
So "audit and backtest" required rebuilding the engine. Their `strategies.py` and
`suite.py` were copied in **verbatim** (the signal definitions are the object of
study); the six missing modules were reconstructed to the contract visible in
their call sites, with every inference documented in the module docstrings.

### FINDING 2 — engine validated against the pack's own known-answer design
Each synthetic world plants ONE effect; a correct engine must find that family and
must find NOTHING in the null world. At a=1.0:

| world | top strategy | gross t | verdict |
|---|---|---|---|
| momentum | S09 autocorrelation | +30.5 | detected |
| meanrev | S09 autocorrelation | +24.0 | detected |
| flow | **S05 taker-flow** | **+49.4** | detected (net t +30.6, 4,627 trades) |
| season | S10 calendar | +194.6 | detected |
| regime_ac | S09 autocorrelation | +27.8 | detected |
| **null** | S02 | **+2.7** | **0 false positives, 0 passes** |

6/6 worlds behave correctly. Note S09 wins the momentum/meanrev/regime worlds
because these strategies feed FEATURES to a learned model that can invert a sign,
so the mapping is by family, not 1:1 — the pack's own "matched strategy" claim
describes its generator, which is not in the archive.
Eight bugs were found in MY reconstruction by this validation, not by reading:
an explosive AR(1) in the generator (price -> inf, `sig` all-NaN, t_stat NaN);
per-bar vol 17x too large; a volshock world that drifted to 1e135; a flow world
where the taker field was drawn independently of the return; and a flow effect
planted CONTEMPORANEOUSLY when every label is a FORWARD return.

### FINDING 3 — 0 of 10 on real data, three symbols
BTC/ETH/SOL, Binance futures 5m, 730 days (2024-10-14 -> 2026-10-14), 210,240 bars
each, taker 5bp + slippage 1bp per side, funding 1bp/8h, Bonferroni t > 2.58.

| sym | passes | AUC range | best net_t | best net% | best trades |
|---|---|---|---|---|---|
| BTC | **0/10** | 0.499-0.530 | +2.8 (S08) | +29.4% (S01) | 84 (S01) |
| ETH | **0/10** | 0.502-0.538 | +2.8 (S10) | +3.7% (S07) | 607 (S02) |
| SOL | **0/10** | 0.504-0.528 | +1.7 (S05) | +75.3% (S02) | 232 (S03) |
| XRP | **0/10** | 0.505-0.531 | +0.9 (S02) | +41.6% (S02) | 869 (S02) |
| SUI | **0/10** | 0.502-0.529 | +1.6 (S06) | +243.7% (S06) | 772 (S02) |

**Five symbols, fifty strategy-runs, zero passes.**

### FINDING 4 — the pack's own escape hatch does not work either
Its SKILL names "horizontes mayores" (longer horizons) as the normal way short-term
perp edge becomes operable. Tested directly, 3 symbols x 4 holding horizons:

| sym | hold 3 (15m) | hold 12 (1h) | hold 48 (4h) | hold 144 (12h) |
|---|---|---|---|---|
| BTC net_t | +2.8 | +2.5 | -2.4 | -15.0 |
| ETH net_t | +2.8 | +2.2 | -2.5 | -5.4 |
| SOL net_t | +1.7 | +2.7 | -2.0 | -9.1 |
| **passes** | 0 | 0 | 0 | 0 |

AUC stays 0.49-0.52 at EVERY horizon, and trade counts explode with the horizon
(BTC 29 -> 22,742; SOL 64,805 at 12h) because a longer hold inflates `E|ret|` and
lets the gate admit ever-weaker signals, which costs then destroy (-100%).
Longer horizons buy more trades, not more information.

**AUC 0.499-0.538 across all 30 strategy-symbol runs.** No feature set carries
meaningful directional information at this horizon. The handful of positive net
t-stats (max +2.8) sit below the Bonferroni bar of 2.58 only in some cases and
never alongside the trade-count (>=100) and permutation (>=90%) requirements.

The pack's own SKILL anticipates this exactly: short-horizon perp edge requires
`|2p-1| * E|ret|` to beat the round trip, and "con horizontes de 15 min exige un
AUC irrealmente alto, lo normal es que NO sea operable salvo maker/VIP o
horizontes mayores."

### WHAT THIS PACK GETS RIGHT
It is the most methodologically serious artifact audited in this project: a
Bonferroni correction for the 10 tests (t > 2.58, not 2), a permutation null, a
calibration-slope check (0.7-1.3), a gross-vs-net decomposition that isolates
whether costs or signal are at fault, a minimum trade count, a synthetic
known-answer matrix, and an explicit "do NOT automate" verdict path. Its
`lessons.md` even records that several strategies can be proxies of ONE effect
and must be attributed before claiming diversification. The engineering is not
the problem; the signal is.

### FINDING 5 — 1m timeframe (2026-10-15; BTC verified, ETH refreshed after backfill)
Taker 1m, 2024-10-14 -> 2026-10-14, 1,051,200 bars/symbol, same costs and gates.
BTC artifacts `verify` bit-for-bit OK.

| combo | passes | best net_t | note |
|---|---|---|---|
| BTC 1m hold 3m (`ccb5e182158b3405`) | **0/10** | +2.8 (S08, 7 tr) | 3-min gate admits almost nothing (max 12 trades); cost >> 3-min E\|ret\| |
| BTC 1m hold 15m (`d2048ac32b01126b`) | **2/10** | +7.7 (S10, 24 tr — FAILS trades/slope) | passes: **S06** +4.1/166 tr/+114% and **S01** +3.1/308 tr/+93%, both perm 100%, slope ~0.85, gross_t positive |
| ETH 1m hold 3m (`35e786d592a4585f`, full 1,051,200-bar file) | **0/10** | +2.8 (S06, 12 tr) | same 3-min gate starvation as BTC; verify pending |
| ETH 1m hold 15m (`b113de7b4f745354`, full file, **verify OK**) | **1/10: S07** +4.9/404 tr/+419%, perm 100%, slope 0.80 | — | candidate SURVIVED the refresh stronger (was +4.2/147 tr on the 675k-bar partial). Gross/net inversion persists (gross_t −3.5): the confidence gate, not raw direction, carries it |

**Cross-symbol replication fails for all three 1m candidates:** S07@ETH (+4.2)
is +0.7/29 tr on BTC; S06@BTC (+4.1) is −1.0 on ETH; S01@BTC (+3.1) is −1.6 on
ETH. 190 strategy-runs campaign-wide, 3 symbol-specific passes, zero replications.
Candidates, not edge — stability probe (half-split, adjacent holds) required
before any forward-paper talk. The 1m hold-3m result also confirms FINDING 4's
mechanism at the extreme: shorter holds buy fewer (not better) trades.

### FINDING 6 — cross-timeframe sweep + period-split gate (2026-10-16): KILLED EVERYWHERE
Data fetched with `code/fetch_taker_tf.py` (kline field 9 at 1m/15m/1h/5m; resumable,
atomic writes, 429 backoff). 7 symbols (BTC/ETH/SOL/XRP/SUI/JUP/HYPE), 51 configs,
**510 strategy-runs → 5 passes.** Report `results/xtf_backtest.md` (guard OK, 140
artifacts). Campaign report `results/cbot_1m_campaign.md` (guard OK).

| tf | hold | passes |
|---|---|---|
| 5m / 15m / 1h, all 7 symbols | both modes | **0 / 510** |
| 1m hold-3m, all 7 symbols | — | **0 / 70** |
| 1m hold-15m | BTC 2, ETH 1, SOL 1, HYPE 1 | 5 / 70 |

**The 5 aggregate passes ALL die on the period split** (AGENTS.md: green in ≥2/3):

| sym | P1 | P2 | P3 |
|---|---|---|---|
| BTC | 0/10 | S01 +2.90 | 0/10 |
| ETH | 0/10 | S06 +3.05, S07 +4.25 | 0/10 |
| SOL | 0/10 | 0/10 | S06 +2.94 |
| HYPE | 0/10 | 0/10 | 0/10 |

**4 passing periods out of 12.** And the winning strategy MIGRATES between aggregate
and split (BTC S06→S01, SOL S07→S06). The most recent 8 months are flat everywhere
(best net_t +0.95 / +0.96 / +2.94). This is the FFS-v1 / SAX pattern.

**JUP: 0 passes in all 8 configs** (fell −67%; every strategy lost with it).
**HYPE: 1 pass aggregate → 0/3 on split**, and it was measured against buy&hold of
+132.69%, so "beats costs" is a far weaker claim than on SOL (−33.42%).

### THE GENERAL LESSON — permutation ≠ sample selection
The pack's permutation control shuffles predictions WITHIN a sample, so it answers
"does this signal beat its own scrambled version?" — which all 5 passes did, at the
100th percentile. It structurally CANNOT answer "was this sample selected?", which is
the actual failure. **A period-split stability probe is a separate, mandatory gate
and must run before any aggregate pass is reported as a candidate.** Note also that
`guard` is a PROVENANCE check (numbers are artifact-backed), not a CORRECTNESS check:
it passed on a report whose builder was silently double-counting cells.

### TOOLING DEFECTS FOUND (fixed)
- `code/vrun.py`: cvrmd/botstrat/ffs adapters hardcoded their native timeframe in the
  `inputs` lambda, so `--tf` was silently ignored and `matrix --tf 1m` would have
  emitted 1h artifacts labelled 1m — the "filename describes none of the variants" trap.
  Now they honour the requested tf, with the semantics caveat recorded in the adapter.
- `sax` is now UNRUNNABLE: `Downloads/sax_engine-claude.py` no longer exists on disk, so
  all 34 pre-existing SAX artifacts fail `verify` with FileNotFoundError. SAX was
  already KILLED so no conclusion moves, but the repo can no longer reproduce its own
  SAX evidence. **Recover that file or drop the adapter.**
- At 5m `hold_mode=bars` and `hold_mode=minutes` resolve to the same 3-bar hold, so
  each symbol got two different run_ids with byte-identical metrics (wasted compute,
  and two ids for one result).

### VAULT SCANNER — Quant Trading Vault (5,806 specs), primera pasada (2026-09-27)
Carpeta escaneada: `C:/Users/Lenovo/Downloads/The-Quant-Trading-Vault-main/The-Quant-Trading-Vault-main/strategies`
Codigo: `code/vault_survey.py` · `code/vault_transpile.py` · `code/vault_extract.py` ·
`code/vault_scan.py` · checks: `code/vault_transpile_check.py` (30/30 PASS).
Resultado: `results/vault_scan_run.txt` · `results/vault_survey.json` ·
`results/vault_preregistration.json` (sha256 ANTES de correr) · `results/vault_rows.json`.

QUE ES EL VAULT
5,807 md, 5,283 Pine (5,286 declarados en su README), 363 JS, 130 Python,
27 MyLanguage, 3 C++, 1 sin codigo. Son dumps de FMZ; 96% declaran simbolo y
timeframe propios (BTC_USDT 4,727 de 5,192). 44% usa Pine LEGACY con llamadas
desnudas (`sma(` no `ta.sma(`) — sin eso el 44% cae en un cluster inutil.

DEDUPE: 4,785 elegibles (con primitivas, con gate, sin grid/martingale/DCA/
scalp) → **1,737 representantes estructurales unicos** por firma de primitivas.

RESULTADO MEDIDO (150 representantes aleatorizados, 7 simbolos, 1H, 6bps+5bps
por lado + funding real por evento de 8h, OOS = segunda mitad de historia)

  CONTROLES: always-long BTC +719%, ETH +1842%, SOL +3029%, XRP +562%,
  SUI -25.8%, HYPE +176.5%, SPX -28.8%.

  **0 de 7 pasan el house gate. 3 de 150 specs compilan (2%).**

  file                           sym       PF    PFex      net      DD      n
  Clear-Trend-Tracking-Strategy   BTCUSDT  0.26   0.94   -99.9%  -99.9%  3090
  Clear-Trend-Tracking-Strategy   ETHUSDT  0.36   0.97   -99.9%  -99.9%  2993
  Clear-Trend-Tracking-Strategy   HYPEUSDT 0.44   0.81   -83.4%  -84.2%   594
  Clear-Trend-Tracking-Strategy   XRPUSDT  0.45   1.00   -99.9%  -99.9%  2967
  Clear-Trend-Tracking-Strategy   SOLUSDT  0.50   0.96   -99.8%  -99.8%  2654
  Clear-Trend-Tracking-Strategy   SUIUSDT  0.53   0.99   -96.8%  -96.9%  1511
  Clear-Trend-Tracking-Strategy   SPXUSDT  0.59   0.98   -84.5%  -84.6%   788

EL NUMERO QUE CIERRA LA PREGUNTA: **PFex 0.81-1.00 con coste CERO.** No es un
problema de coste. La senal two-sided (flip largo/corto en cada cruce) no tiene
direccionalidad: en BTC con n=3,090 trades el PF a cero costes es 0.94. Coste
no arregla eso, y ningun parametro lo arregla.

POR QUE EL SCAN SOLO VE 3 DE 150 (limit real del transpiler, no del vault)
  44  no strategy.entry/alertcondition gate  (el extractor pierde el patron)
  21  compile:unexpected_        (construcciones que el parser no cubre)
  11  compile:want_got_
  7   gate_fires_on_most_bars    (gate constante detectado y rechazado)
   4  compile:_time_  (time/hour/minute requieren columna timestamp)
   3  compile:_strategy_position_size_ (estado; no es serie)
El 2% NO es el rendimiento del vault: es la cobertura del parser. Un scan que
dice "0 de 7" sobre 3 specs no es un veredicto sobre el vault entero — es un
veredicto sobre Clear-Trend-Tracking-Strategy.md. Falta subir cobertura antes
de leer ranking.

BUGS DEL HARNESS ENCONTRADOS Y CORREGIDOS (para futuros scans)
1. `ta.crossover` no parseaba: los nombres cualificados (`ta.` / `math.`) no
   estaban en el parser; 2,333 archivos parecian "sin primitivas".
2. La comparacion broadcast a 2-D: `x, y = as_bool(x), as_bool(y) if cond
   else (x, y)` asigna una TUPLA por precedencia de Python. Cada comparacion
   salia con shape (2, N).
3. `trade_pf` (loop separado de `simulate`) no cerraba la posicion terminal →
   n_trades=0 en TODOS los specs y el ranking imprimia "NO RESULTS". Los dos
   loops divergieron. Arreglado: UN solo walk (`run_sim`) produce equity Y
   retornos por trade.
4. El simulador no marcaba a mercado entre barras: DD 0.0% en el control
   always-long (sonaba plausible y era falso).
5. Funding: cobrado por EVENTO de 8h, no por barra horaria (el bug 8x de antes).
6. `input.*()` (kwargs tipo `defval=`): el tokenizer no tenia `=` y fallaba en
   84 de 120 muestras. Ahora resuelve al default que trae el autor.

REGLAS APLICADAS (no negociadas)
- Specs pre-registrados con sha256 antes de correr; sin tuning posterior.
- n>0 por fila (cero trades = bug report, no resultado).
- Fill en la apertura de la barra SIGUIENTE, nunca en el cierre de la senal.
- Controles do-nothing y always-long corridos e impresos.
- OOS = segunda mitad; se rankea en OOS.
- Los perdedores se listan con la misma prominencia (arriba, tabla unica).
- `vault_transpile_check.py` incluye prueba de TRUNCADO (prefijo identico) que
  prueba no-lookahead, y un control negativo para que no sea vacua.

SIGUIENTE PASO (no hecho): subir cobertura del extractor/parser (kwargs,
`time()`, funciones definidas por el usuario) y re-correr antes de leer
ranking sobre el vault completo. Con 2% de cobertura el ranking no dice nada
de los otros 5,600.

## `code/vrun.py` WAS LOST AND RECONSTRUCTED — 2026-10-16/17
### Read this before trusting any run_id, including the 186 pre-existing ones.

**What was found.** `code/vrun.py` on disk was **syntactically invalid** — a
`SyntaxError` at line 176, it could not execute at all — and it was **not** the harness
that wrote the 186 artifacts in `results/runs/`. That is proof, not inference: its
sha256 appears in **none** of them. The artifacts record **8** distinct
`harness_sha256` values (seven hashes, plus 22 artifacts old enough to predate the
field), so at least seven harness revisions wrote them and the file on disk was a
later, broken edit. Preserved as `code/attic/vrun_broken_2026-10-16.py`, sha256
`65BC299B306EAC258A47EC5B399347707AA04E631AD79371E2D2A7F6E9906010`.

**How the id was recovered** — from the artifacts themselves, then checked against
all 186:

```
core   = {strategy, params, inputs:[[path, sha256, bars]], engine_sha256, engine_version}
run_id = sha256(json.dumps(core, sort_keys=True, separators=(",", ":")))[:16]
```

`engine_sha256` = sha256 of the engine sources concatenated in **filename-sorted
order** (a single file ⇒ its own sha256). **All 186 stored run_ids reproduce exactly.**

**The property that makes this recoverable is undocumented and must not be "fixed":**
`harness_sha256` lives in `provenance` and deliberately does **not** enter `run_id`.
Rebuilding the harness therefore *restores* verification instead of invalidating
everything. Hashing the harness into the id would have destroyed 186 artifacts and
would do so again on the next harness edit.

`verify` semantics: **0** OK, **2** REFUSED (engine/params/metrics drift — do not
publish), **3** STALE (input bytes changed since the artifact — re-run to refresh, it
is **not** a fabrication). Harness drift is a printed note, never a failure.

**Adapters re-derived bit-for-bit:** cvrmd, botstrat, ffs, cbot. Two real defects in
the *reconstruction* were caught by the artifacts rather than by reading:
1. **cbot `best_net_ret` is the return OF THE BEST-t ROW**, not the largest return in
   the table — `best_net_ret_id == best_net_t_id` in every artifact (BTC 15m
   `412dc10538e78196`: best-t is S05 at +2.90% while S02 returned +9.79%).
2. **`matrix` hardcoded `return_pct`/`max_dd_pct`**, which `cbpack` does not have, so
   every cbpack cell printed `ERROR TypeError ...NoneType.__format__` **while still
   writing its artifact** (the append precedes the print). Now adapter-agnostic
   (`_first`/`_f`), plus `matrix --index-only` to rebuild an index *from* artifacts
   instead of re-running them — rewriting good evidence to fix a cosmetic index is the
   wrong trade. `_matrix_cols` also refuses to label `n_ok` (a count of STRATEGIES) as
   `n_trades`, which made a 224-trade cell read as "9 trades".

**Status — the sweep is complete, and over the whole corpus.** `results/conformance_sweep.json`
now covers **all 297 artifacts on disk**: 181 reproduce bit-for-bit, 67 are STALE, and 49
are the sax artifacts that can never verify because the engine file is gone.
**Non-sax failures: zero.**

Reading rc=3 correctly is the point of having it. It is not a defect in the artifact: the
two cbot ETHUSDT 1m artifacts that look odd (`8a77592516058147`, `ba53d34ac48a9dbd`)
recorded `ETHUSDT_1m.csv` at 675,000 bars while the file now holds 1,051,200 — they are
frozen snapshots of an earlier copy of the same series. rc=3 separates "the world moved"
from "the engine or params drifted" (rc=2), and that distinction is what makes 67 stale
entries survivable rather than alarming.

The first pass, run before the slice-warmup fix, refused three cbot artifacts; the finish
pass retried them and all three now reproduce. That is the evidence that the warmup
restored the original behaviour rather than that the check was relaxed — a resumed sweep
retries rc=2 by construction, so a "fixed" refusal that was really a loosened test would
come back as a refusal again.

Helper: `code/_finish_sweep.py` waits for a running sweep to finish and then runs the
resume pass (~13 minutes over this corpus).

**sax is permanently undecidable:** `Downloads/sax_engine-claude.py` is gone, so all
**49** sax artifacts can never verify. Recover the file or drop the adapter.

#### Two `guard` fidelity bugs found by auditing its own output (2026-10-17)
Auditing the reconstruction against reports that were already documented as
"guard OK" is what found these — reading the code did not.

1. **A hyphenated range was read as a negative number.** `0.652-1.788` tokenised as
   `0.652` and `-1.788`, so `guard` refused reports over a "negative number" that is
   not in the report at all. Any table printing a min–max range was a false refusal.
   Fixed with a lookbehind (`(?<![\w.])[+-]?…`): a sign is only a sign when it is not
   glued to a preceding digit. Real negatives (`net -0.53`, `(-1.005)`) are unaffected;
   dates now yield positive components too (`2024-10-14` → `2024, 10, 14`, previously
   `2024, -10, -14`).
2. **`params` was not scanned.** A slice report necessarily quotes its slice window,
   and the window is recorded in `params.slice_to` (`"2025-06-14"`), not in `inputs`
   (which spans the full data). `guard` now collects `metrics` + `tables` + `inputs` +
   `params`. Still deliberately **not** scanned: `cmd` and `created_utc` — provenance
   metadata, not measurements, and scanning `cmd` would let a report quote any number
   by hiding it in a command line.

Re-checked after the fix: `results/cbpack_backtest.md` OK, `results/cbot_1m_campaign.md`
OK, `results/xtf_backtest.md` **still refused, on exactly one number**.

#### Third reconstruction gap: the cbot slice WARMUP (2026-10-17)
The conformance sweep refused three `cbot` 1m artifacts that nothing had flagged before:
same input bytes, same params, different `n_bars` (442,080 recomputed as 351,360).
Diagnosis: the reconstruction sliced `[slice_from, slice_to)`, but the original sliced
`[slice_from − 63 days, slice_to)`.

The original's intent is **documented, not inferred** — `code/_xtf_periods.py`, the
driver that generated those runs, says it outright: "Each slice keeps TRAIN_DAYS of
warmup before the scored region (see run_cbot), so slicing shrinks the evaluation window
WITHOUT starving the model of training data." `TRAIN_DAYS` lived only in the lost
`run_cbot`; solving for the window in each artifact recovers it exactly: **every** slice
starts 63.00 days before its recorded `slice_from`, on a midnight-UTC boundary
(2025-06-14 → 2025-04-12, 2026-02-13 → 2025-12-12, 2025-11-14 → 2025-09-12,
2026-04-30 → 2026-02-26) — four symbols, three windows each, no exceptions. The first
slice of each symbol simply clamps to the data start. `slice_to` is never moved, so the
campaign report's period labels are the SCORED regions and remain correct.

Restored as `TRAIN_DAYS = 63` in `run_cbot`; all twelve slice artifacts now reproduce
bit-for-bit. This leaves a deliberate asymmetry in the harness: `cbpack` slices carry
**no** warmup, because cbpack's slice artifacts were produced by the current code and
verify as they are.

Why it stayed invisible: the first slice of each symbol is clamped by the data start, so
it reproduces under either convention. Testing only the first window turns a
twelve-artifact bug into something that looks like a four-artifact success.

#### `results/xtf_backtest.md` is NOT guard-clean (one unbacked tally)
The report states "**5 passes out of 510 strategy-runs**". `510` appears in **none** of
the 297 artifacts on disk, and it cannot be re-derived from them: only **65** cbot
artifacts exist, and the campaign table in that report accounts for roughly 43 runs.
So the tally is unverifiable — the pass counts and the metrics it summarises *are*
artifact-backed, but the denominator is not. This is a REGLA 0 violation in a report
that has been cited as guard-clean, so: **do not repeat the 510 figure**, and treat the
"both guard OK" claim in AGENTS.md as having been wrong for this file.

Lesson, and it is the same one as the `guard`-is-provenance note: **state tallies in
words.** A tally is a derived count, not a measurement, and `guard` cannot back it. The
cbpack report writes every count of cells in words for exactly this reason, and
`code/_assert_report_totals.py` reconciles the derived counts by recomputation instead.

## `strategy_pack.py` — single-file 10-strategy pack (2026-10-17): real edge at 1h, costs kill it below
**Source:** `~/Downloads/strategy_pack.py`, 39,418 bytes, 717 lines, sha256
`055b584de9aa23c2…`. **This is NOT `Downloads/QUANT CRYPTO BOT 10`** (the multi-file ML
suite further up this file, adapter `cbot`): same marketing name, different code. This
one is ten **rule-based** strategies in a single file and it runs as shipped.
Engine copied byte-identical to `code/cbpack_engine.py` **before** running anything —
the SAX v3 lesson. Adapter `cbpack` (`mode=full|wf`). Report
`results/cbpack_backtest.md` (**guard OK**, 111 artifacts, all `verify` clean).

### Two defects in the pack itself
1. `load_ohlcv` does not recognise `open_ts`; the adapter renames it. Cosmetic.
2. **`attach_funding` cannot run on pandas 3.x**: `df.index + Timedelta` upcasts
   datetime64[ms] → [us] and `merge_asof` then rejects the mixed resolutions. The
   adapter aligns the funding index unit (same instants, no semantic change); the
   pack's own code is left untouched.
Run against `data/binance_klines_<tf>_taker/` so flow is **true taker flow**, not the
candle-colour proxy. **S08 (open interest) is SKIPPED everywhere** — Binance serves
~20 days of OI against a two-year window; never approximated.

### The grid — 4 timeframes x 7 symbols x 10 strategies, pack's own 5+2 bps/side
| tf | cells clearing PF>1.2 and n>=30 |
|---|---|
| 1h | **3 of 7** (XRP S02, XRP S10, SOL S10) |
| 15m | **1 of 7** (HYPE S07) |
| 5m | **0 of 7** |
| 1m | **0 of 7** |

1m is ruin, not underperformance: best-per-symbol net runs **−79.25%** (HYPE) to
**−96.62%** (BTC) at 800+ trades. 5m runs −15.00% to −83.96%.

### The decisive control — gross PF at ZERO cost
This is what separates "no signal" from "signal destroyed by cost", and the two demand
opposite responses:

| strategy | tf | gross PF | net PF | drag | symbols gross>1 |
|---|---|---|---|---|---|
| S02 Donchian+Flow | 1h | **1.28** | 1.15 | 0.14 | 7/7 |
| S10 Vol-Tgt TSMOM | 1h | **1.23** | 1.15 | 0.07 | 6/7 |
| S05 HTF Pullback RSI-2 | 5m | **1.08** | 0.43 | **0.65** | 7/7 |
| S09 (unnamed family) | 1h | 0.84 | 0.67 | 0.17 | 1/7 |

S02 and S10 carry a **real** 1h edge (gross PF above 1.2 on most symbols). **S05 carries
a real 5m signal that 14 bp of round-trip cost annihilates** — its fix is cheaper
execution (maker/VIP), *not* more parameter search. S09 has no signal at all: abandon.

### Out-of-sample gates (period split / pack walk-forward at 3 geometries / repo costs)
- **XRP 1h S02** `a30083333490d945` — passes **everything**: periods 3/3 green
  (+88.75 / +20.53 / +23.91), walk-forward positive in **3/3** geometries
  (+32.29 / +69.48 / +18.34), PF **1.47** at repo costs. → **candidate**
- **SOL 1h S10** `814c80675d570aae` — periods 2/3 (−0.53 / +45.52 / +21.42),
  walk-forward **3/3** positive (+40.74 / +23.36 / +8.42), PF **1.56** at repo costs.
  → **candidate**
- **XRP 1h S10** — same cell, PF 1.75 at repo costs, but walk-forward **fails one
  geometry** (−17.93 at 180d/90d). Fragile.
- **15m HYPE S07** `ac4ff6d3a465a268` — **KILLED**: walk-forward negative in **3/3**
  geometries (−0.69 / −0.62 / −0.45) *while buy&hold made +22.65 / +12.94 / +47.55*,
  and PF collapses 1.29 → **1.10** at repo-standard costs.

Caveat on the period split, in light of the `cbot` warmup finding above: cbpack's
period slices start **cold** (no warmup), so the first bars of each period have NaN
indicators. The pack guards every indicator with `min_periods` (rolling/ewm windows
default to it), a NaN comparison is False, and the largest window in any shipped grid
is 84 bars — so a cold start costs **bars, not truth**: at 1h that is ≤ 84 of ~5,832
bars per period (~1.4%) and no bias is introduced. The walk-forward gates never had
this question: `pack.walk_forward` precomputes causal signals over the **full** series
and only then scores each test window, so those folds are fully warmed.

### The XRP headline is NOT alpha
+184.01% (S02) against buy&hold +142.83% looks like a win; it is mostly risk
management. In the **first third** buy&hold made **+293.07%** while S02 made +88.75% and
S10 +103.92% (window exposure only 34.5% and 71.0%). The excess is earned in the
*declining* slices, where S02 made +20.53% while buy&hold fell −36.07%, and +23.91%
while it fell −4.37%.

### Verdict
Cross-sectionally, S02 at 1h is above break-even on **7/7** symbols and S10 on **6/7**,
so the 1h effect is not one symbol's accident — but as a seven-symbol portfolio the
median 1h net PF (1.15) sits **under** the repo threshold. **Not done:** a full
parameter-grid sweep at 1h, which is what the "neighbourhood stable" criterion actually
requires. Candidates, not deployed edge.

---

## 2026-10-22 (evening) — EMA Cross + ADX [Quant] port: KILLED

New deliverable: the requester's Pine v6 file from Downloads (EMA Cross + ADX [Quant]
— EMA(20)/EMA(50) cross filtered by ADX(14) >= 25 with DI alignment, ATR(14) stop at
2x and take-profit at twice that distance, 100% of equity per entry, five bps
taker commission, process_orders_on_close). Ported as `code/emaadx_engine.py`,
discipline per the ports rule:

- **Known-answer audit FIRST** (`code/_emaadx_audit.py`, output
  `results/emaadx_audit_known_answers.txt`): all 35 cases PASS, and it caught one
  real engine bug before any real-data run — short entries never credited the sale
  proceeds, which silently zeroed the book's equity while short (`eq[-1] == pnl`
  instead of `INIT + pnl`). Fixed: proceeds credit at entry; the money-identity
  test (INIT + sum(pnl) == final equity, tolerance 1e-6) now runs over every
  playthrough. The audit also locks Pine-faithfulness details that violate the
  repo's usual next-open convention ON PURPOSE: fills at the signal bar's close
  (process_orders_on_close=true), stop-first tie-break on spanning bars, adverse
  slip on stop fills, honest limit fills, whole-order fee on reversals, and the
  duplicate-signal bracket re-set (second cross_up while long re-anchors SL/TP;
  proven by the exit price matching the re-set bar's anchor — 204.6049 — not the
  entry bar's, 86.2043). Status of the audit's own decisions: EMA is gated by
  min_periods (no arbitrary first-bar seed), ta.dmi na-seed subtlety handled the
  same way `adxhma_strategy.py` handles it (that file's primitives
  rma/atr_pine/dmi_pine/fixnan are reused).
- **Harness adapter** (`emaadx` in `code/vrun.py` ADAPTERS): 1h files, two windows
  (full; half-year = last 4368 bars after 600 warmup), three cost sets (author
  5bps+declared-zero tick; repo6x5; zero-cost control inside EVERY artifact so
  drag_pp is measured in-artifact), matrix True.
- **Matrix**: 13 symbols x 2 windows x 2 cost sets = **52 canonical cells** (driver:
  `code/_emaadx_matrix_driver.py`; every cell run + verify OK). Result: **zero of
  thirteen symbols pass G1..G6 in any cell-set** — BTC full/author PF 0.7993
  (-67.4379% vs B&H +715.75%, run `041e85cf248622b1`), ETH full/author PF 1.1121
  (+88.04% vs B&H +1556.08%, conc -9.2796, drag 62.2728pp, run `8ec8753e67f7bffa`),
  the best half-year cell (HYPE, `23a00d8be53d1d3d`) PF 1.66 with both halves above
  1 but n=16 closed trades and conc -101.45. The zero-cost control is the
  damning one: BTC is -55.4665% BEFORE costs. Report: `results/emaadx_report.md`
  (guard OK; builder `code/_emaadx_build_report.py`; 55 artifacts cited. Three
  duplicates with default params exist: `83a6e062c85b6406`, `8c1c3acceb9e957f`,
  `4805f0fd37708b6d` — repeats, not cells).
- **Structure of the death** (from the artifacts' trade tables, counts in words):
  stops outweigh targets on every symbol; with the 1-to-2 stop/target geometry the
  book needs a hit rate above one third before costs and delivers about thirty
  percent. Costs are NOT the excuse (repo gate verdict would only sharpen it);
  the signal is underwater before costs. G5 anti-alpha twice (SUI and DOGE
  half-year "beat" B&H while both lose).
- **No walk-forward/neighborhood attempted**: repo rule — stability checks apply
  to survivors; there were none.

Instrumentation left behind: `code/_emaadx_report_table.py` (gate table),
`code/_emaadx_exits.py` (exit-reason distribution from artifact tables),
`code/_artifact_metrics.py` (generic artifact metrics viewer, gate view).

Superseded: the MPS20 full-window rebuild chain is **settled** — eight canonical
cells, all verified bit-for-bit. See "2026-10-27 — MPS20" at the end of this file.
Polymarket recorder continues unchanged (Phase one: recorder only, pre-registration
stands).

## 2026-10-22 — DSPACK (DeepSeek five-strategy pack): ported, audited (54/0), KILLED at every gate in every cost set but one author-cost cell that dies at repo costs

Requester's five-strategy pack (`file delivered 2026-10-22`) ported WITH its bugs
and run through the harness. Pack file preserved byte-identical as
`code/deepseek_pack.py` (sha256 b6ca6f58f36e6c3bb140e39c389dff22319ad5d1668180
72844999cb5976f212); engine `code/dspack_engine.py` imports it and injects
nothing else. Adapter `dspack` in `code/vrun.py` (sources: engine + pack;
inputs: 13 canonical 1h files for ds4/PORTFOLIO else the one symbol's file;
matrix False; tf validated 1h-only).

- **Audit**: `code/_dspack_audit.py` — **fifty-four PASS, zero FAIL**
  (`results/dspack_audit_known_answers.txt`). Hand-built panels pin each
  strategy's vector; EMA closed form equals pandas adjust=True; hand-computed
  fee ladders (entry / hold / whole-order reversal charged once to the CLOSING
  trade / zero-delta bars); ds4 ladder + period segmentation (each switch fee
  booked to the closing period; period i>=1 ref = lv[bars[i]+1]; open tail fees
  zero); engine trade-for-trade == an independent straight-line simulator
  (B3); B4 causality prefixes for ds1..ds5 incl. the ds4 panel; C defaults.
  Fix history this session: A6 rewritten when the pack source settled that
  ds5's `ffill(limit=24)` is a DEAD NO-OP (pos never contains NaN; ds5 stateless
  like ds2 — the author's 24-bar hold never happens); B1/B2 were audit
  transcription slips (double-multiplied delta; missing bar-4 factor in
  exp_lv[6]); B5 exposed and fixed a real engine off-by-one (period ref_idx);
  B6 de-duplicated the zero-position case. Engine + pack sha printed in the
  audit file every run.
- **Observed gates G1..G6 (pre-declared repo criteria)** computed in-engine
  (`gates`, `gates_pass_all` in every artifact) and independently re-evaluated
  by `code/_dspack_build_report.py`, which REFUSES on any missing/duplicated
  canonical cell or on engine-vs-tool gate disagreement (none occurred).
- **Matrix**: 4 strats x 13 symbols x {full, last6mo} x {author, repo6x5} +
  ds4 on PORTFOLIO = **212 canonical cells** (driver
  `code/_dspack_matrix_driver.py`; every cell run + verify OK). Result:
  **exactly one cell passes every gate** — ds1 AVAXUSDT full/author
  (`21e2bcb475fd6fd3`: PF 1.2727, +281.0977% vs B&H +141.8582%, 5/7 green
  years, conc-w/o-top5 +95.9774) at the pack's own ZERO costs — and the same
  book at repo costs (`88b51ed249563add`) drops to PF 1.0529 with conc
  -67.8040. At repo6x5: **zero of fifty-two cells pass for any strategy**.
  ds2/ds3/ds5: zero of fifty-two pass EVEN at the pack's zero costs.
- **Structure of the death** (from the artifacts; counts/ranges in words):
  ds1 full-window author books are all green (+130% to +412%) but B&H dwarfs
  all but three (AVAX, SPX, SUI; the latter two only because their own
  markets were negative), and repo costs flip the whole set to ruin (BTC
  drag 314.1443pp, `596c9c7399ef7081`; every ds1 repo cell prints a negative
  conc-w/o-top5). ds2 loses at zero costs (its only positive book anywhere,
  SUI full/author +10.5359%, PF 1.0226, conc -69.2668) and ends
  -92%..-99% at repo. ds3's headline (SOL +8321.2005% author,
  `55cbf103e822ae30`) is a whale drawer: conc-w/o-top5 **-10542.7391**; ten
  of thirteen names have h2 PF <= 0.99; no full-window ds3 PF reaches 1.2 and
  the >1.2 half-year PFs all carry under thirty trades. ds5's best PF anywhere
  is 1.14 (ETH last6mo author). ds4 (xs momentum, the only portfolio book,
  n = rebalance periods) fails exactly one gate in its best cell — last6mo
  repo6x5 `3acc62ace382118a`: PF 1.665, both halves > 1, beats the equal-weight
  B&H +43.3691%, but conc-w/o-top5 **-13.4134** (author sibling -10.5094):
  one window, one gate short, no second window agrees.
- **No walk-forward/neighborhood attempted**: repo rule — stability checks
  apply to survivors; none survived the gates.
- **Report**: `results/dspack_report.md` (GUARD OK — every metric number
  backed by the 212 artifacts; builder/tables
  `code/_dspack_build_report.py`, assembler `code/_dspack_assemble_report.py`,
  gate counts `results/dspack_gate_counts.json`).
- **Conventions + quirks documented in `results/dspack_report.md`**: fill at
  signal-bar close; fee = |dW|*fee on the changing bar with the whole-order
  reversal fee landing on the closing trade; ds1's dead clip(0,2); ds2
  stateless; ds3 age-out flips to -1 not flat; ds4 24-bar sample+ffill; ds5
  dead ffill; `author` = pack-declared zero cost (doubles as the zero-cost
  determinism control; measured drag exactly zero in all author artifacts);
  `repo6x5` = 6bps+5bps per side; drag_pp measured in-artifact everywhere.

Instrumentation left behind: `code/_dspack_audit.py`, `code/_dspack_engine.py`
(= `code/dspack_engine.py`) + `code/deepseek_pack.py` (verbatim pack),
`code/_dspack_matrix_driver.py`, `code/_dspack_build_report.py`,
`code/_dspack_assemble_report.py`.

Superseded: the MPS20 full-window rebuild chain is **settled** — eight canonical
cells, all verified bit-for-bit. See "2026-10-27 — MPS20" at the end of this file.
Polymarket recorder continues unchanged (Phase one: recorder only, pre-registration
stands).

## Addendum — DeepSeek pack 2 (strats 6–9) verdict: ALL KILLED (Oct 22, 2026)

Second DeepSeek attachment (`deepseek_python_20261022_848478.py`, strats ds6 BB-z
reversion / ds7 RSI-2 / ds8 BTC-ETH pairs / ds9 VWAP-deviation). Author file
copied byte-identical to `code/deepseek_pack2.py` (sha256
`bba9c6d61b57b370b4256dc9cadb802502fff4c9bcf9d39c740cbd1705f4b60d`); engine
`code/dspack2_engine.py` imports `dspack_engine`'s accounting verbatim (one code
object, `E2.E is E1` pinned in audit case C); harness adapter
`ADAPTERS["dspack2"]` (`dspack2-1`) hashes all THREE files into every run_id;
1h-only, same load_csv spacing gate as pack 1.

- **Known-answer audit BEFORE any real-data run**: `code/_dspack2_audit.py` —
  36/36 PASS — canonical `results/dspack2_audit_known_answers.txt`.
  Two semantics learned and pinned in the audit preamble: (a) pandas
  `.ewm(...)` default is **adjust=True** (weighted-mean recursion), NOT the
  Wilder form — the ds7 RSI/EMA expectations use the adjusted closed form;
  (b) with `rolling(n).std()`, max |z| = (n−1)/√n, so a 3-bar lookback makes
  z_entry=1.5 unreachable — crafted cases use lookback 5 with explicit
  non-vacuity guards (both trigger signs, gap and marker bars required).
- **Campaign**: 81 dspack2 artifacts — ds6/ds7/ds9 matrices (full + last6mo,
  13 canonical 1h symbols each, repo6x5) + ds8 trio (full repo6x5
  `895d1a4e7a266993`, last6mo `e1f3b5eeb118da36`, author-cost
  `bccaa612918c561b`). Spot `verify` 13/13 OK bit-for-bit
  (8ac4b0d47a9ab218, e303e9f913f9ac34, 2a617cb993e40c34, af15eaa4067d9bbb,
  1acd0fd6bf204925, 1cac08451c6a902e, 3c457e5c131f89fd, b5c18361f8cb3659,
  ddf34f6fde856d40, b852eb4fb2f1501f, + the ds8 trio).
- **Verdict — no cell passes the gate set anywhere**:
  * ds6 full: PF 0.31–0.81, returns −30.16% (HYPE) to −91.14% (LINK); last6mo
    PF 0.15–0.77. Stateless trigger-bar positions pay a full round-trip on a
    one-bar hold; even at zero cost most books were already negative.
  * ds9 full: PF 0.45–0.91, returns −58.19% (HYPE) to −99.96% (BTC); last6mo
    PF 0.29–0.72. Same stateless churn, catastrophic drag (hundreds of pp —
    e.g. AVAX zero-cost +798% → scored −98%).
  * ds8 (period accounting, symbol PAIRS_BTC_ETH): full −97.84% PF 0.8407
    (10,590 periods); last6mo −23.60% PF 0.7818; **author-cost run −59.4719
    equals the embedded zero-cost control exactly** (drag 0.00) — parity
    proof for the drag book; zero-cost PF 0.9671 → no gross edge either.
  * ds7: the only positive cells under fees — DOGE `b5c18361f8cb3659`
    +43.69% PF 1.0308, NEAR `d9bab10e9203cd71` +32.66% PF 1.0214, SOL
    `de5a02eb67f6100a` +39.46% PF 1.0218, SPX `b898dfed4e6f2395` +44.97% PF
    1.1078 — but ZERO-COST PF is only 1.2329/1.2220/1.2391/1.3163 with
    unbalanced halves and `gates_pass_all` False on the whole grid; the
    raw zero-cost gains (e.g. SOL +1505.41%) lose almost everything to
    round-trip fees at ~1,100 trades. Real-but-thin gross signal,
    fee-destroyed at this trade frequency; last6mo window all negative.
    No survivor ⇒ no walk-forward attempted (repo rule).
- **Report**: `results/dspack2_report.md` (GUARD OK — every metric number
  backed by the 81 artifacts; derived counts spelled out in words; generator
  `code/_dspack2_report.py`).
- Coverage note (artifact-honest): `HYPEUSDT_1h` (11,624 bars) and
  `SPXUSDT_1h` (15,726 bars) end 2026-09-26, all other symbols end
  2026-10-17; their cells carry the short spans they were scored on.
- Probe files deleted: `code/probe_ewm.py`, `code/probe_bench.py`,
  `code/_probe_chars.py` (diagnosis complete).

- **QWEN TEN-CARD PACK (2026-10-23): all six delivered cells KILLED at the
  repo cost basis; program closed.** After step zero (four cards dead by
  their own diagnostic bars) the six survivors (cards one, two, three,
  four, nine, ten) ran through the new `q10` adapter,
  engine `code/q10_engine.py` + `code/q10_diag.py`. Known-answer audit
  `code/_q10_audit.py`: sixty-nine of sixty-nine cases PASS on the final
  engine bytes (`results/q10_engine_audit.txt`). Six artifacts, all
  `verify` OK bit-for-bit:
  CARD1 `0f23886c0607a21a` (net +15.39%, PF 1.02, best-five 791.03% of
  book — dies on G1/G3/G4/G5/G6), CARD2 `76955428d8de4012` (+63.01%,
  PF 1.09, funding -1314.99 bps), CARD3 `beec2fbb495b611b` (+112.74%,
  PF 1.74 fee-free 1.59, concentration clean +42.15 pp-equivalent, but
  second-half PF 0.60 vs first-half 5.14 and its own BTC/ETH basket B&H
  +264.35% beats it), CARD4 `f8afa8673577bf59` (-18.94%, PF 0.96),
  CARD9 `abea6c8039307385` (-93.70%, PF 0.53, seventeen units),
  CARD10 `1261a609ec97809c` (+0.50%, zero-fee PF 0.99 — no gross edge).
  **Zero of six clear `gates_pass_all`; per pre-registration no
  frozen-parameter OOS step, no rescue loops.**
  Report `results/q10_pack_results.md` (GUARD OK — every metric number
  backed by the six artifacts; counts in words).
- Harness note: the `q10` adapter now records the card inside the artifact
  core (two majors cards share a file set, so the card key MUST be in
  core). Two pre-fix files were renamed out of the artifact namespace as
  incident evidence, not results:
  `4596f8f583d53b6d.COLLIDED-cardid.json` and
  `aa28f0084a37a6eb.PREFIX-no-card.json`.

## 2026-10-25 — costes: 22 bps (supuesto) -> 11 bps (medido) y re-run de los gates

- El 6+5 bps/lado = 22 bps/RT no era una medicion: era un supuesto
  "conservador vs TV 5bps + 2 ticks" escrito en `AGENTS.md`. Medido en
  libro vivo (2026-10-25, Binance/OKX/Bybit/Kraken, XRP \): spread 0.77
  bps en los cuatro, impacto \ 0.39 bps (Kraken 1.97), fee tier0 5 bps
  (Bybit 5.5). RT real: Binance 11.55, OKX 11.55, Bybit 12.55, Kraken 14.72.
- Coste medido por simbolo (Binance \): BTC 10.02, ETH 10.09, BNB 10.27,
  XRP 11.55, HYPE 11.56, LINK 11.79, SOL 11.99, AVAX 12.27, DOGE 12.61,
  SUI 13.75, NEAR 14.51, ADA 19.84, JUP 22.57, SPX 30.54. El gate plano de
  11 bps es optimista para 11 de 14 nombres; la tabla vive en
  `results/cost_model_2026-10-25.json`.
- Codigo: `code/vrun.py` (defaults 5.0/0.5), `code/_cbpack_gates.py`
  (REPO_FEE 5.0 / REPO_SLIP 0.5), `scanner-engine/backtest_link.py`
  (REPO_COST_RT_BPS 11.0), `code/sax_v4_engine.py` + `sax_v4_adapter.py`
  (slip 0.5). `cbpack_engine.py`/`cbpack_funding_engine.py` conservan su
  slip 2.0 a proposito: el audit los fija por SHA-256 para la paridad
  zero-funding, asi que el coste se inyecta desde el caller (audit 48/48 PASS).
- Re-run de los gates a 11 bps (`results/cbpack_gates.json`): XRP S10
  net +184.18% PF 1.83 n 168 (funding -5.72pp, B&H +142.8%, excess +41.4pp),
  XRP S02 +190.62% PF 1.63 n 223 (excess +47.8pp), SOL S10 +74.77% PF 1.645
  n 172 (B&H -33.7%, excess +108.5pp). WF: XRP S10 4/10, 10/21, 1/6;
  S02 4/10, 10/21, 2/6; SOL S10 4/10, 9/21, 3/6.
- **El gate final del repo sigue en FAIL por concentracion**: las cinco
  mejores operaciones son 106% (SOL S10), 124% (XRP S02) y 133% (XRP S10)
  del PnL; sin ellas el neto es -4.1%, -46.4% y -60.0%. Barrer 22 -> 11 bps
  sube el neto pero no convierte esto en alpha diversificado.
- `backtest_link` tenia dos agujeros que el re-run dejo a la vista y que
  ahora se aplican: (1) `excess_%` solo se reportaba, no se exigia, y
  admitia una fila con excess -279pp (HYPE S07, XRP S03); (2) los artefactos
  de corte (`slice_from`/`slice_to`) podian ganar el dedupe por ser mas
  recientes y sustituir el resultado de ventana completa por el de un trozo.
  Tras el fix: SOL/USD 1 candidato (S10), XRP/USD 2 (S10, S02), HYPE 0.
- Pendiente de decision: meter `conc_passes` como gate del scanner. Hoy
  los tres candidatos vivos lo incumplen; si se exige, la lista queda vacia.

## 2026-10-27 — PACK-50 (the fifty prompt pack): all forty-eight runnable prompts KILLED; S46 is the near miss and it fails concentration

Source document: `Downloads/50_strategies_crypto-claude1.md`, fifty numbered
prompts each naming its own market and timeframe. Adapter `pack50`
(`code/pack50_engine.py`, `code/pack50_core.py`, `code/pack50_strats.py`),
one artifact per prompt, report `results/pack50_report.md` (**guard OK**),
ids in `results/_pack50_ids.json`.

**S34 and S49 are NO DATA, not failures.** Both need an NVDA series; `data/etf`
is empty on this machine. Nothing is estimated, proxied or carried over from the
author. The other forty-eight were all run and all forty-eight reproduce
bit-for-bit under `python code/vrun.py pverify --workers 4`.

**Result: zero of the forty-eight clears all six gates.** The closest is
**S46 weekend-gap fade BTC 1h `be0a85f7ab2b522c`** — net +26.68%, PF 1.303,
out-of-sample PF 2.64, funding charged, loses only G6: with the five best of its
sixty trades removed the result is -8.65%. That is the same shape as the
`cbpack` 1h "winners": a handful of fills, not a distribution.
**S05 Heikin-Ashi SUI 4h `8321c904af22c0ad`** reaches four of six (PF 1.077,
conc -95.27%). **S01 `1dac06b2e17c8562`, S32 `8d5242a3a743b39d` and S45
`fdd964c4e8c669e5`** reach three of six.

**The cost control is measured inside every artifact, and it changes the
verdict.** Six prompts carry a gross factor above the repo threshold with fees
and slippage switched off: S47 1.538, S46 1.411, S31 1.378, S05 1.209, plus the
degenerate samples S32 5.561 (twenty-four trades) and S28 230.934 (four
trades). Costs take a bite out of every one of them — S47 falls to 0.948, S31 to
1.151, S05 to 1.077 — but the bite is not the whole story: the two that stay
above the threshold fail other gates. **The pack is not a portfolio of
cost-destroyed winners; most of it has no gross edge at all.** The breakout
block (S19-S26) is the cleanest example: its best zero-cost factor is S21's
1.116, i.e. below the threshold before a single fee is charged.

**Funding is charged at the settlement instants** and the bill is material:
S25 pays $1042.49 against a starting account of ten thousand — the largest drag
in the pack — S21 $431.12, S09 $304.37. S16 (short JUP) *receives* $715.14,
which is the correct sign and the reason the funding check is in the audit. JUP
funding history did not exist on disk; it was fetched from the public endpoint
by `code/fetch_jup_funding.py` (new file, 4539 settlements, no gap over nine
hours). Any earlier JUP artifact in this repo could not have charged funding.

**Three real engine bugs were found by the audit before the mass run, and
fixed:**
1. the entry fee was charged twice (the exit fill billed entry + exit notional);
2. resampled `open_ts` was silently written in seconds, so **funding was never
   charged on 4h, 30m or 3m** — exactly the timeframes most of the pack uses;
3. pair trades recorded only the last bar of the holding period instead of the
   mark-to-market segment (now full segment PnL with the entry cost inside it).
`code/_pack50_audit.py` pins fills, the SL-first tie rule, per-side fees,
per-side slippage, the funding sign, the pair leg split, the resampler,
the indicators, determinism and causality. All its checks pass on the bytes that
produced the artifacts. **Re-run it after any change to the engine** — the
engine bytes are hashed into the `run_id`, so a change also invalidates every id.

Conventions declared and used by every prompt: signal at close, fill at the next
open; signal exit also at the next open; stops/targets intrabar with the stop
filling first when one bar contains both; full-equity compounding; pairs 50/50
per leg; funding on the open notional at each settlement. The pack's own cost
block (taker fee wider on the three alts, slippage wider on alts and on scalp
timeframes) is the headline cost; the repo gate cost and a zero-cost control are
measured in the same artifact so the reader never assembles a sensitivity.

**Data bounds:** every market is the Binance USDT-M perpetual read from the
`*_taker` files, which start 2024-10-14 (HYPE 2025-05-30, JUP ends 2026-10-15).
The prompt's multi-year regime claim is therefore out of reach: the split is a
split of a short window. None of these results should be read as evidence about
a decade.

## 2026-10-27 — MPS20 (twenty-strategy multi-pair suite): ported, determinism fixed at source, KILLED in all eight cells

Requester's suite ("CLAUDE BOT STRATEGIES 1"). Engine `code/mps20_engine.py` imports
the author's `code/claude_bot_1/engine_core.py` + `strategies.py`; adapter `mps20`.
Report `results/mps20_report.md` (**guard OK**), eight cell artifacts, **all eight
verified bit-for-bit**:

| cell | config | window | costs | run_id |
|---|---|---|---|---|
| c5 full author | five-pair author universe | full | author | `cc33c9473c072c40` |
| c5 full repo | five-pair author universe | full | repo | `21c77c89154bddcb` |
| c5 6mo author | five-pair author universe | last six months | author | `c9153c3c660466d9` |
| c5 6mo repo | five-pair author universe | last six months | repo | `3ce0567eb24132fe` |
| c4 full author | prior four-pair config | full | author | `1692ab92c4ba0442` |
| c4 full repo | prior four-pair config | full | repo | `458658ab7289ea1a` |
| c4 6mo author | prior four-pair config | last six months | author | `f2f34d3891e8c687` |
| c4 6mo repo | prior four-pair config | last six months | repo | `d236d2620866295b` |

**Verdict: zero of twenty strategies clear the gates in any of the eight cells.**
That is one hundred sixty strategy-by-cell verdicts, none passing. The suite is KILLED
as shipped.

**DETERMINISM WAS BROKEN AND IS FIXED AT SOURCE, not by pinning a seed.** Three
strategies (`sig_01`, `sig_11`, `sig_14` in `code/claude_bot_1/strategies.py`) picked
their same-bar candidates by iterating **sets**; Python's set order depends on
`PYTHONHASHSEED`, so the fill order at one bar — and every float sum over trades after
it — differed between processes. Every artifact produced before the fix verify-REFUSED
with "engine non-determinism". The fix replaces each set with the ranked list it was
drawn from and resolves ties toward the first pair in volatility-ascending rank. **No
signal threshold, size or fee knob changed.** This is the general lesson: a
hash-order-dependent tie-break is a silent non-reproducibility bug, and `verify` in a
fresh process is what catches it. Do not "fix" such a failure by lowering the
comparison tolerance.

**Cost drag is measured inside each artifact** with a zero-cost control pass of the
same twenty strategies on the same aligned data (the `cbpackf` funding-drag pattern).
It is large: MP20 at c5/full/repo is 102.59% costed against 7676.31% zero-cost
(`21c77c89154bddcb`), MP15 26.77% against 7461.99%. At the author preset the same two
are 392.21% and 206.17%. Fees as a share of strict gross profit reach 43.21% (MP08,
c4/6mo/repo, `d236d2620866295b`) — above the repo's 30-40% ceiling.

**Universes, declared honestly.** c5 is the suite's own USDC-literal universe
(SOLUSDC/BTCUSDC/ETHUSDC/AVAXUSDC/LINKUSDC) fed with repo **USDT** 1h prices — a proxy,
declared as such; the USDC/USDT basis at hourly bars is small against the strategies'
own thresholds, and c5 is the only config where the two BTC-literal-indexed strategies
can trade at all. c4 is the prior four-pair USDT config (BTC/ETH/SOL/XRP), the parity
reference, where those two are structurally dead by their own not-in-data guard.

**Instrumentation left behind:** `code/_mps20_report_table.py` (gate table from
artifacts), `code/_mps20_assemble_report.py` (report builder; every numeral is read
from an artifact), `code/_claude_audit.py` (known-answer audit, re-run on the fixed
bytes), plus the existing `code/mps20_engine.py`.

No tuning is scheduled. Any revival must start from a pre-declared out-of-sample
design, not from re-running this one.

## pack50b — the claude2 fifty-prompt pack (2026-10-27): KILLED — zero of forty-six runnable prompts clear the six gates

Source: `Downloads/crypto_strategy_prompts_50-claude2.md` (S01-S25 scalping, D01-D25 day
trading). Adapter `pack50b` on the frozen `pack50_core`: `code/pack50b_engine.py`,
`code/pack50b_strats.py`. Report `results/pack50b_report.md` (guard OK), ids
`results/_pack50b_ids.json`, audit `code/_pack50b_audit.py` (one hundred forty checks,
all pass). All forty-six artifacts reproduce bit-for-bit under pverify. The pack's own
cost block is 5 bps fee + 2 bps slip per side (a fourteen bps round trip); the repo gate
cost and a zero-cost control are measured inside every artifact, and funding is charged
at the settlement instants.

- **The scalping block has no gross edge.** The best zero-cost profit factor in the
  whole block is S03 (SOL 1m RSI-2) at 1.091 (`2981e2a8fd579f43`); S13 (SUI 5m VWAP
  deviation fade) is net-negative even with costs switched off, 0.235
  (`4d370e11fe7f532d`). At the pack's own block the 1m/3m books are ruin (−100%).
- **The day block's best results die on the two gates that matter.** D05 (TTM squeeze,
  SUI 1h) nets +39.80% at PF 1.073 (`86f4ca910fe12ca5`) and D13 (Fibonacci pullback,
  SUI 30m) nets +13.11% at PF 1.099 (`7bc4da0aec131154`); both reach four of six gates
  and fail exactly G1 (factor) and G6 (their net without the five best trades is −3.7%
  and −10.8%). D04 (`e5f90f77104b1424`) and D23 (`71bf4c777fb2f104`) reach three of six.
  Five prompts beat buy & hold only while the underlying fell.
- **S08, S23, D08 and D18 are NO DATA** (no NVDA series on this machine) and are never
  estimated — the same class of exclusion as the claude1 pack's S34/S49.
- **The audit's no-stopless-entry group exists because it caught two live bugs
  mid-campaign**: a negated-NaN downtrend gate in S02 and an ATR-warmup entry in S13
  each produced a position with an undefined stop that occupied the book forever. The
  campaign was re-created after the fix, so every run_id above covers the final engine
  bytes; the pre-fix intermediates remain in `results/runs/` as orphans that verify
  REFUSED by construction. "SPCX" in the prompts is read as the SPXUSDT series on disk
  (plain 1m/1h klines; 5m/15m resampled from the 1m file, roughly three months).

## Gate-set audit response (2026-10-27): the statistical layer is now measured

An external audit of `GATES_AND_RULES.md` found the v1 gate set uncalibrated,
trial-count-blind, and lenient at small samples. The response, all measured:

- **`code/gate2.py`** — the v2 statistical layer (expectancy block-bootstrap
  LB, effective N, purged folds, monthly buckets, beta alpha, top-5%
  concentration + best-month removal, breakeven cost by bisection, P95
  drawdown, DSR, PBO/CSCV), pinned by `code/_gate2_audit.py` (32 checks, all
  pass). The pack50b audit grew a truncation-invariance group and now runs one
  hundred forty-one checks.
- **Trial ledger** — `code/_trial_ledger.py` derives the append-only trial
  count from the run store: twelve hundred and fifty-six artifacts at the time
  of writing, so survivor claims now carry a program-level haircut (G7) on top
  of any campaign-level one.
- **Calibration artifact** `ce5c2629e9290b63` (adapter `gatecal`, twelve cells
  x four hundred seeded null trials on real BTCUSDT 1h): the v1 all-six
  conjunction passes a null book at 0.0 to 0.25 percent per candidate
  depending on trade count — and a twenty-bps planted edge still clears it
  only 0.75 to 1.75 percent of the time, so v1 was simultaneously
  false-positive-prone across a thousand-plus trials AND near-powerless per
  candidate. The v2 conjunction measured 0.0 to 0.25 percent null rate with
  7.0 to 9.25 percent power at twenty bps. Null P95 drawdown: median 31.68,
  ninetieth percentile 47.76 percent. Report
  `results/gate_calibration_report.md` (guard OK).
- **v2 re-scoring of the claude2 near-misses** (`results/gate2_scoring.md`,
  guard OK; artifacts `3e3d3bb57babd884`, `62a7b39dd8ef675b`,
  `71b309ac7bd8bd46`, `4344340f041dadf9`, `1b4c40f16b58a5a8`,
  `0254d2d4a6cc70ff`, all pverify bit-for-bit): none of the six passes the v2
  set. The expectancy ninety-five percent lower bound is NEGATIVE for every
  one of them (D13, the strongest, at −29.62 bps) — the quantitative statement
  that the v1 near-misses were consistent with noise. The only gate with
  survivors is G8 cost robustness (D05, D13, D14).
- **`GATES_AND_RULES.md` rewritten to v2** (G1-G10): the PF definition is
  corrected (per-trade percentage returns at fixed size; risk-based sizing
  changes PF — the v1 text was wrong), the cost rule is amended (G8 + binding
  per-symbol costs for thin names), concentration is scale-free (top 5% of
  trades + best month), and the limitations register declares tick-data fill
  fidelity, survivorship, the cost-regime snapshot, and the deferred
  environment binding in the run_id.

## Cross-check of the second audit-fix implementation (2026-10-27): adopted as the reference layer, two real defects found in it, one gap closed here

A second implementation of the gate audit arrived (`BACKTEST AUDIT FIXES-CLAUDE.zip`:
`_gates_v2.py`, its self-test, and an alternative GATES_AND_RULES.md). It was cross-checked
against this repo's `gate2.py` layer and adopted as the reference layer
(`code/_gates_v2.py`, self-test all-pass) with merged ideas and two fixes:

- **Defect found on real data, fixed there**: `random_entry_trades` silently produced
  garbage timestamps on a positional-index frame (bar numbers read as nanoseconds — every
  trade on 1970-01-01) while the gate dict still looked plausible. It now fails loud on a
  non-DatetimeIndex.
- **Defect found on real data, fixed there**: the cost-model parser missed this repo's
  actual schema (`per_symbol_binance_usdtm.{SYM}.rt_10k_bp`) and misclassified metadata
  keys as symbols. Fixed; `admit_declared_costs` now resolves the real measured costs.
- **Gap closed here**: the best-week removal in G6 (audit H5) was missing from this repo's
  layer and is now implemented and gated.

**Agreement, measured**: DSR implementations agree to four decimals on the same inputs;
PBO agrees on a planted matrix; the null false-positive rates agree on real BTC 1h. The
head-to-head rates live inside the new calibration artifact `bdb602a549eeecbe`
(`reference_layer_cross_check`: reference-layer joint null 0.0, joint at twenty bps
planted edge 6.0 percent, against this repo's v2 conjunction 0.0 and 9.5 percent).
Legitimate semantic differences are declared in GATES_AND_RULES.md; the stricter reading
wins.

**Merged and re-run under the aligned policy** (`policy_hash` now in every gate artifact):
G3 gained the purged 70/30 split alongside the folds; G2 enforces effective N; G4 buckets
by exit month with a six-scored-bucket floor; G6 removes the top five percent, the best
month and the best week; G9 fails closed without declared leverage or per-trade MAE,
checks the liquidation distance, and caps P95 drawdown at 35 percent (the measured null
median is near a third of capital). The calibration artifact and the six near-miss
artifacts were re-created (`bdb602a549eeecbe`; `b97b59a512f29605`, `2cc68516438fa82e`,
`e2daedc82289e093`, `800234f18604d653`, `d6481bbef532fd47`, `875c5767e5eee139`), all
pverify bit-for-bit; both reports re-generated and guard OK. Verdict unchanged and now
stricter: none of the six passes v2; exactly one gate — cost robustness G8 — has
survivors (D05, D13, D14).

**Adopted tooling, run on real data**: the artifact store is hash-chained
(`results/runs/_CHAIN.jsonl`, one thousand two hundred seventy entries, verify OK — byte
changes now detectable without touching run_id); the trial ledger has a chained form
(`results/_trial_ledger.jsonl`); the data-integrity report runs clean on BTC 1h, ETH 5m
and SPX 1m; and the funding-interval tool confirmed on real files that the eight-hour
funding assumption is false in this data (JUP's modal interval is four hours; BTC's
history contains sixteen-hour intervals) — the pack engines charge from each symbol's own
settlement file and are unaffected.

## pack50c — the Qwen fifty-prompt pack (2026-10-27): KILLED — zero of forty-two runnable prompts clear anything

Source: `Downloads/Qwen_50 strategies.txt` (Q01-Q50; the user ordered the backtest
explicitly — this is the Qwen FIFTY pack, not the rejected ten-prompt pack, and the
rejection's code-defect lessons were applied: two-way costs, funding charged, no
synthetic fallbacks, purged splits). Adapter `pack50c`
(`code/pack50c_engine.py`, `code/pack50c_strats.py`) on the frozen core, with the v2
gate layer measured inside every artifact. Report `results/pack50c_report.md` (guard
OK), ids `results/_pack50c_ids.json`, audit `code/_pack50c_audit.py` (one hundred
thirteen checks). All forty-two artifacts pverify bit-for-bit.

- **This is the weakest pack measured in this repo.** The best profit factor is Q29 at
  0.886 (`0280329207f4d3d9`) — below one at the pack's own costs. The best expectancy
  95% lower bound in the whole pack is −0.919 bps (`f5148447ac6bc001`): not one prompt
  has a positive lower bound. Thirty-three of the forty-two books end ruined (at or
  below −99%) on the 1m/3m timeframes. Zero prompts pass the v1 gates, zero pass v2,
  and for the first time zero even pass G8 cost robustness.
- Several books are anti-edge with costs switched OFF: Q22 zero-cost factor 0.148
  (`ccc1bfa3d1d0b408`), Q26 0.637 (`380d53e834b0ba86`), Q16 0.693
  (`7889b45cf034d8de`), Q28 0.937, Q31 0.821, Q37 0.692, Q45 0.969, Q49 0.977.
- Eight NVDA prompts (Q02, Q11, Q23, Q27, Q35, Q36, Q42, Q47) are NO DATA, never
  estimated. "SPCX" is the SPXUSDT series on disk.
- **Process lessons (re-learned)**: the audit's no-stopless-entry group caught six
  VWAP/PSAR ports firing during ATR warmup BEFORE any market run; a Q08-style book
  traded nearly once per bar (~1.05M trades) and forced a memory-bounded chunked
  bootstrap (asserted identical to the audited one); bar-level alpha was switched to
  the daily basis (the reference layer's G5 convention) after a gigabyte-scale
  allocation; and the engine drifted mid-campaign twice, so every artifact was
  re-created under the final bytes — the pre-final versions remain as orphans that
  verify REFUSED by construction.

## pack50d — the DeepSeek fifty-prompt pack (2026-10-27): KILLED — zero of forty-eight clear the gates, but the strongest gross-edge showing so far

Source: `Downloads/deepseek_markdown_20261027_68930c.md` (P01-P50). Adapter `pack50d`
(`code/pack50d_engine.py`, `code/pack50d_strats.py`) on the frozen core with the v2 layer
inline. Report `results/pack50d_report.md` (guard OK), ids `results/_pack50d_ids.json`,
audit `code/_pack50d_audit.py` (one hundred twenty-one checks). All forty-eight artifacts
pverify bit-for-bit. P30 and P46 are NO DATA (NVDA); SPCX = SPXUSDT; P17 is a
dollar-neutral ETH/SOL pair and P23's BTC filter leg is hashed into its artifact.

- **Zero prompts pass the v1 gates; zero pass v2.** Eleven books ruined. But this pack
  has the strongest GROSS edge of any measured: seven prompts carry a zero-cost factor
  above the repo threshold (P01, P05, P06, P08, P27, P28, P44 — versus two in claude2
  and zero in Qwen), and **seven pass G8 cost robustness** (same seven minus P06 plus
  P24). The near-miss of the entire program to date is **P28 (momentum ignition, ETH 5m,
  `865a7b20d9592b0c`-family artifacts — see the ids file)**: net PF 1.316 on 266 trades,
  zero-cost 1.825, breakeven 14.26 bps per side, G2 and G8 passed, and its expectancy
  95% lower bound is −0.57 bps — half a basis point short of the gate. It still fails,
  it is the maximum over forty-eight candidates, and the program-level haircut applies;
  but it is the first book where the residual question is sample noise rather than
  absence of signal. P44 (weekend gap fade, SUI 1h) nets PF 1.188 with breakeven 15.82.
- P07 (daily EMA 50/200 cross) took exactly one trade in the window — infinite profit
  factor on one fill is a sample failure, never a result.
- Process: the audit caught a `_roll`-on-boolean crash (P26/P32), a tuple-returning
  rolling apply (P09), and a structurally-degenerate synthetic generator (fractal pivots
  cannot exist when o[i]=c[i-1] and wicks are constant multiples — P10's test needed
  noisy wicks); three engine import bugs surfaced as hard NameErrors mid-campaign, and
  the whole pack was re-created under the final bytes (drift is now caught by pverify's
  engine_sha256 check, which refuses cleanly).

## cand7 — the seven prespecified candidates (2026-10-28): KILLED — zero of seven clear the gates

Source `Downloads/strategy_candidates_v2-claude.md` (Batch v2.0). Adapter `cand7`
(`code/cand7_engine.py` on `code/cand7_core.py` / `code/cand7_strats.py`), audit
`code/_cand7_audit.py` (twenty-seven checks), report `results/cand7_report.md`
(guard OK). 1h taker klines, seven artifacts pverify-clean: C1 `1ced2d38c9a70140`,
C2 `40b92e7f9cc558dd`, C3 `8edeaafe5454c681`, C4 `ab39449d95dca11b`, C5
`0386e2f558e84371`, C6 `7c23b65596eb98c3`, C7 `f9fd115fb70b6e8e`.

- Zero of seven pass v1, zero pass v2. The closest is C7 (fails G6 only): PF
  1.4770 on 33 trades, five best 191.49% of PnL, -2.27% without them.
- Gross edges exist but are concentrated: C2 zero-cost PF 1.7765 on 12 trades;
  C4 1.2821 over 90 periods, net 9.40% against buy & hold 14.94%; C7 1.6217.
- Four books have no gross edge at all (C1, C3, C5, C6): their zero-cost returns
  are already negative, so cost is not the question.
- Design defects measured, not asserted: C4's book kill cannot bind and fired
  zero times in 90 traded periods; C5's dispersion gate fired 3 times in 699
  days; C6 was one-sided (14 long-SOL signals, 0 short) because SOL funding sat
  below BTC in 0.0689 of settlements against 0.0279 the other way; C2's
  breakeven is 28.42 bps per side but it has 12 trades.
- The audit caught four engine defects before publication: basket period rows
  missing fees and funding; the pair book marking both legs long (inverting the
  mirrored C6 direction); time exits labelled as signal exits; C4 flattening on
  a low-dispersion day instead of skipping the rebalance.

## 2026-11-04 — 1m fill accounting for the neutral paper book; the single-pair bot is retired

**The 15m record is not fill evidence.** The 2026-10-31 audit measured that the
15m convention fabricates the two-sided grid's covers (100% of the retired XRP
bot's closed trades were same-bar round trips). A forward book that records
those fills records the convention. So the live paper book now writes a SECOND,
separate record whose engine resolves a bar minute by minute — only when its 1m
tape is complete (at least fifteen distinct minutes); every other bar keeps the
original same-bar block byte for byte, which is why the day-0 baseline and the
whole pre-tape history cannot move.

- Engine `code/xrp_neutral_engine_paper_1m.py`, GENERATED by
  `code/_neutral_1m_build.py` from `code/xrp_neutral_engine_paper.py` (byte-
  identical copy of the engine the VPS runs; the builder refuses a base whose
  sha differs). Never hand-edited.
- A cover may fill only on a STRICTLY LATER minute than its entry. A same-
  minute touch is unresolvable from OHLC: it is counted and banned, never
  assumed.
- `code/_neutral_1m_audit.py` -> `_neutral_1m_audit.json`: twelve checks, all
  PASS (no-tape run bit-identical to the 15m engine over the full
  239,470-bar history; late tape leaves the prefix untouched; five ordering
  cases; exact reproduction of the published kill).
- The kill is now an ARTIFACT, not a probe log: 15m baseline
  `c7f1063c88f3268f` (PF 1.3019, n 3317, win 86.95, ret 17031.11, DD 20.54) and
  1m-resolved `18d686932bf06f78` (PF 0.9326, n 3018, win 77.53, ret -74.2,
  DD 81.46, 131,479 resolved bars, 290 same-minute bans), same data, same
  sizing, same slice (2023-01-01..2026-10-01 13:45). Both `verify` bit-for-bit.
  A third artifact `6f815d5b52cfd930` refreshes the full-history 15m run at the
  CURRENT data (the two validated v1/v2 artifacts went STALE on data
  extension; same fact, not a fabrication).
- Live: `~/neutral-paper/`, five isolated pair dirs (JUP XRP SOL HYPE SUI),
  each cycling 15m then, one minute later, 1m. Both runners share ONE lock per
  pair because they append to the SAME 15m kline CSV; the wait is bounded and a
  skipped cycle costs nothing because every cycle is a full replay. Status,
  events and artifact are `_1m`-suffixed; the day-0 file is SHARED, so the
  two records differ only by the fill model. `day0_replay_matches` re-runs the
  pure 15m path over the prefix and requires bit-for-bit equality with the
  frozen baseline.
- `daily_summary_1m.py` (00:20 UTC, chosen so every pair reports the same
  last_bar) and `weekly_report.py`'s `1M FILL ACCOUNTING` section carry the
  comparison as columns; invalid rows say INVALID rather than quoting a broken
  number. `status_all.py` prints both records.
- The single-pair XRP paper bot is RETIRED AND DELETED. `/home/ubuntu/xrp-paper-bot/`
  is gone; archive `/home/ubuntu/backups/xrp-paper-bot_retired_2026-11-04.tar.gz`;
  zero cron lines left.
- New adapter `xrpneutral1m` in `vrun.py` (the 15m `xrpneutral` adapter was not
  changed; its run_ids stand). Registry updated; report
  `results/xrp_neutral_1m_fill_accounting_2026-11-04.md` (guard OK, citing the
  three artifacts).

**No edge is claimed.** The 1m numbers are worse than the 15m ones, and worse
for the honest reason.
