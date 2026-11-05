# Strategy catalog family D (QS-031..QS-040, market structure and price action) — audit and backtest report

Date of record: 2026-10-31. Source: the Phase-3 strategy-catalog archive (exact filename in every artifact's provenance; extracted under code/_pack100cat/). These are the catalog's ten market-structure hypotheses: the confirmed swing breakout, trend-structure continuation, the change-of-character reversal, support/resistance zone rejection, the range sweep, the pivot breakout-retest with a higher-low requirement, compression inside a prior range, the momentum-exhaustion fade, multi-timeframe structural alignment (the HTF structure resampled from the same klines, closed HTF bars only), and the displacement continuation. Every pivot carries the k=3 confirmation delay (a pivot is KNOWN only k bars after its bar closes — the sheet's own fixed rule). Engine: the family-A G1-G7 machinery (`code/qs_engine.py` + `code/qs_run.py`) with the family-D signal layer `code/qs_d_strats.py` (adapter `qsd`). Known-answer audit: `code/_qs_d_audit.py` — twenty-six checks, ALL PASS, on the exact bytes before any artifact. The audit caught three real builder bugs before any number was measured: the QS-040 hold window included the displacement bar's own low (which sits below its 50% level by construction, poisoning the group minimum forever); the QS-036/QS-033 break episodes restarted on every re-arming break bar inside the retest window (which voided the higher-low comparison); and the QS-034 zone touch-exhaustion counted bars that predate the zone's own existence.

## VERDICT: KILLED by the gates — zero of ten PASS

Three hundred and sixty cells were measured (ten strategies x two-sided AND long-only x six symbols x three timeframes); all verify bit-for-bit. Verdicts: three hundred and five REJECT, twenty-four FAIL, thirty-one INCONCLUSIVE, zero PASS.

The decisive numbers:

- G4 viability (twenty bps at Base, positive at Adverse): fourteen of three hundred and sixty cells — but the meaningful ones concentrate in single-symbol 1h cells.

- one hundred and fifty-eight of three hundred and fifty-nine cells beat their own random-entry null.

- eighteen cells are EXECUTION-SENSITIVE.

- Per strategy (Base expectancy, null comparison, verdict mix):

  - QS-031 (e.g. `02c3815247963ec8`, Confirmed swing-high/swing-low breakout): beats its null in twenty-eight of thirty-six cells — FAIL five, REJECT thirty-one.

  - QS-032 (e.g. `0c50c4e242a1334e`, Trend structure continuation): beats its null in seven of thirty-six cells — FAIL two, REJECT thirty-four.

  - QS-033 (e.g. `03881d531f7d429c`, Confirmed change-of-character reversal): beats its null in twenty-nine of thirty-six cells — FAIL three, INCONCLUSIVE four, REJECT twenty-nine.

  - QS-034 (e.g. `091a7658ad88e079`, Support/resistance rejection): beats its null in eight of thirty-six cells — FAIL one, INCONCLUSIVE one, REJECT thirty-four.

  - QS-035 (e.g. `017b7ed0083d7bbf`, Range sweep and reversal): beats its null in six of thirty-six cells — FAIL one, INCONCLUSIVE one, REJECT thirty-four.

  - QS-036 (e.g. `07955425e2590016`, Breakout retest (pivot level + higher low)): beats its null in eight of thirty-six cells — FAIL one, INCONCLUSIVE one, REJECT thirty-four.

  - QS-037 (e.g. `081dad764ab7c110`, Compression inside a prior range): beats its null in sixteen of thirty-six cells — FAIL two, INCONCLUSIVE four, REJECT thirty.

  - QS-038 (e.g. `05ef8df067e96e95`, Momentum exhaustion reversal): beats its null in thirteen of thirty-five cells — INCONCLUSIVE eleven, REJECT twenty-five.

  - QS-039 (e.g. `0abf4781f8f79cef`, Multi-timeframe structural alignment): beats its null in twenty-seven of thirty-six cells — FAIL eight, INCONCLUSIVE two, REJECT twenty-six.

  - QS-040 (e.g. `08d7c015e758fb30`, Price displacement with continuation): beats its null in sixteen of thirty-six cells — FAIL one, INCONCLUSIVE seven, REJECT twenty-eight.

## The near-misses: two cells clear every gate except g6

The catalog's own verdict rule kills them; the honest record keeps what they cleared:

- `21f1495a22c44230` QS-037 (compression inside a prior range) two-sided ETHUSDT 1h: one hundred and twenty-two trades, expectancy +28.10 bps at Base / +22.39 at Adverse, PF 1.73, holdout +127.8 bps, null -6.3 bps, G5 PASSES. It fails g6 on fold profitability (one of five folds) and monthly consistency (fifty-eight percent of months positive against the sixty percent requirement).

- `aea9b2b6c8af346a` QS-039 (multi-timeframe structural alignment) long-only ETHUSDT 1h: one hundred and ten trades, +33.57 / +28.62 bps, PF 1.94, holdout +50.0 bps, null -7.2 bps, G5 PASSES, exp_lb95 positive. It fails g6 on fold profitability (three of five, with two-to-four trades per fold) and monthly consistency (fifty percent).

- QS-037 long-only ETH 1h `9b30be19ffef8d06` reaches +48.89 / +41.75 bps with holdout +299.5 bps on sixty-one trades — INCONCLUSIVE by the catalog's own out-of-sample floor (eighteen OOS trades against the thirty required).

Both survivors sit on ETHUSDT 1h alone — a one-symbol concentration, the same pattern the catalog campaign has shown in every family (HYPE in family C, SUI in the flow pack). The market-structure family confirms the campaign's shape: real gross edges exist at 1h scale, the gates' consistency requirements kill them, and nothing survives every gate.

## Provenance

- Adapter `qsd` in `code/vrun.py`; sources hashed: qs_engine, qs_strats, qs_d_strats, qs_run.

- All three hundred and sixty artifacts verify bit-for-bit (`pverify --strategy qsd`).

- Known-answer audit output: results/qs_d_audit_known_answers.txt (twenty-six checks, ALL PASS, run before any artifact).

