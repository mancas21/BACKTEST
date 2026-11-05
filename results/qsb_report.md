# Strategy catalog family B (QS-011..QS-020, mean reversion) — audit and backtest report

Date of record: 2026-10-31. Source: the Phase-3 strategy-catalog archive (exact filename in every artifact's provenance; extracted under code/_pack100cat/). These are the catalog's twelve mean-reversion hypotheses: RSI oversold (a declared V1 cross event and its V2 persistent variant), Bollinger re-entry with bandwidth/ADX regime blocks, z-score deviation with a crisis filter, anchored VWAP (UTC day and week anchors), ATR-normalized VWAP deviation, displacement-candle fade with a six-sigma news block, range oscillation, volatility-expansion fade, the OU BTC/ETH dollar-neutral pair, and the liquidity-dislocation wick fade. Engine: the family-A G1-G7 machinery (`code/qs_engine.py` + `code/qs_run.py`) with the family-B signal layer `code/qs_b_strats.py` (adapter `qsb`); QS-019 executes through `code/qs_pair_run.py` over pack50_core.run_pair (dollar-neutral, funding on both legs, A/B-ratio benchmark). Known-answer audit: `code/_qs_b_audit.py` — nineteen checks, ALL PASS, on the exact bytes before any artifact (two engine-adjacent bugs were caught and fixed before any number was measured: the QS-019 validation path passed fraction costs to a BPS-named constructor — a thousand-fold cost understatement — and its trade conversion iterated a DataFrame as if it were a list of dicts).

## VERDICT: KILLED — zero of twelve pass; mean reversion is the weakest family of the three

Four hundred and two cells were measured (eleven single-leg strategies x two-sided AND long-only x six symbols x three timeframes, plus the QS-019 pair x two variants x three timeframes); all verify bit-for-bit. Verdicts: three hundred and six REJECT, nine FAIL, eighty-seven INCONCLUSIVE, zero PASS.

The decisive numbers:

- G4 viability (twenty bps at Base, positive at Adverse): five of four hundred and two cells. Every single one of them is below the G5 floor on trade count — the viable-looking cells are one-to-twenty-trade artifacts, not strategies.

- Mean reversion does not beat its random-entry null either: only one hundred and sixty-eight of three hundred and forty cells beat their own null. Family A (trend) beat the null in the majority of cells; the trade-flow family lost to it; family B sits between and loses where it counts.

- ten cells are EXECUTION-SENSITIVE (positive at Base, non-positive at Adverse) — of the ten FAIL cells, eight are.

- Per strategy (Base expectancy, null comparison, verdict mix):

  - QS-011 (e.g. `01a407872b71cb0a`, RSI oversold reversal (V1 event)): beats its null in twenty-one of thirty-six cells — FAIL two, INCONCLUSIVE two, REJECT thirty-two.

  - QS-011V2 (e.g. `00d40bcaa897bbfd`, RSI oversold reversal (V2 persistent)): beats its null in twenty-one of thirty-six cells — FAIL two, INCONCLUSIVE two, REJECT thirty-two.

  - QS-012 (e.g. `09287212dd03463f`, Bollinger Band reversion): beats its null in twenty-three of thirty-six cells — FAIL two, REJECT thirty-four.

  - QS-013 (e.g. `0685edcad4589c14`, Z-score deviation reversion): beats its null in thirteen of thirty-six cells — INCONCLUSIVE two, REJECT thirty-four.

  - QS-014 (e.g. `00251d7ed4a17735`, Anchored VWAP reversion (day anchor)): beats its null in nineteen of thirty-six cells — FAIL one, REJECT thirty-five.

  - QS-014W (e.g. `010fb19f5b02a312`, Anchored VWAP reversion (week anchor)): beats its null in twenty-one of thirty-six cells — INCONCLUSIVE two, REJECT thirty-four.

  - QS-015 (e.g. `07ff889ef11cd0d1`, VWAP deviation, ATR-normalized): beats its null in seven of twelve cells — FAIL one, INCONCLUSIVE twenty-four, REJECT eleven.

  - QS-016 (e.g. `0bb93f5a7e3e82dc`, Displacement-candle fade): beats its null in two of thirty-six cells — INCONCLUSIVE two, REJECT thirty-four.

  - QS-017 (e.g. `03c0a7653a2e32c8`, Range-bound oscillation): beats its null in zero of zero cells — INCONCLUSIVE thirty-six.

  - QS-018 (e.g. `05f101ed365807b0`, Volatility-expansion fade): beats its null in sixteen of thirty-four cells — INCONCLUSIVE eight, REJECT twenty-eight.

  - QS-019 (e.g. `0d65b1e656b54011`, OU-process spread reversion (BTC/ETH)): beats its null in three of six cells — FAIL one, INCONCLUSIVE two, REJECT three.

  - QS-020 (e.g. `0ea3abf0d1bc9f16`, Liquidity-dislocation wick fade): beats its null in twenty-two of thirty-six cells — INCONCLUSIVE seven, REJECT twenty-nine.

## The best cells (none viable)

- `ad15d7fbaaf993e1` QS-019 two-sided BTCUSDT+ETHUSDT 1h: n 34, expectancy +27.6 bps at Base / +19.6 at Adverse, PF 1.10, folds 2/5, verdict INCONCLUSIVE.

- `6df5df81357b57b3` QS-011 long-only SOLUSDT 1h: n 81, expectancy +17.8 bps at Base / +14.8 at Adverse, PF 1.31, folds 2/5, verdict INCONCLUSIVE.

- `da693d38d4bc9011` QS-011V2 long-only SOLUSDT 1h: n 81, expectancy +17.8 bps at Base / +14.8 at Adverse, PF 1.31, folds 2/5, verdict INCONCLUSIVE.

- `cf5025e43dc25bc3` QS-018 two-sided JUPUSDT 15m: n 47, expectancy +16.4 bps at Base / +13.2 at Adverse, PF 1.64, folds 4/5, verdict INCONCLUSIVE.

- `5265f1af9510182e` QS-020 two-sided BTCUSDT 1h: n 20, expectancy +14.9 bps at Base / +8.6 at Adverse, PF 1.46, folds 3/5, verdict INCONCLUSIVE.

- `2414d8ad47ab3a58` QS-011 long-only HYPEUSDT 1h: n 45, expectancy +12.8 bps at Base / +11.1 at Adverse, PF 1.21, folds 1/5, verdict INCONCLUSIVE.

The highest measured Base expectancy anywhere in the campaign is `9f637588ae1bf569` — QS-018 long-only JUPUSDT 1h — at +42.5 bps on 1 trades (verdict INCONCLUSIVE): the twenty-bps viability bar is reached only by cells with single-digit trade counts. The pattern is the same cost wall that killed families A and flow: reversion signals exist at bar scale but the roundtrip eats them, and where the signal is large the trade count is not. QS-019 is the honest null-referenced disappointment: on one-hour bars the random-entry null out-earns the OU book.

## Provenance

- Adapter `qsb` in `code/vrun.py`; sources hashed: qs_engine, qs_strats, qs_b_strats, qs_run, qs_pair_run, pack50_core.

- All four hundred and two artifacts verify bit-for-bit (`pverify --strategy qsb`).

- Known-answer audit output: results/qs_b_audit_known_answers.txt (nineteen checks, ALL PASS, run before any artifact).

