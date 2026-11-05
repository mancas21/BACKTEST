# Strategy catalog family C (QS-021..QS-030, volatility and breakout) — audit and backtest report

Date of record: 2026-10-31. Source: the Phase-3 strategy-catalog archive (exact filename in every artifact's provenance; extracted under code/_pack100cat/). These are the catalog's ten volatility-and-breakout hypotheses: ATR compression then expansion, Bollinger bandwidth squeeze, realized-vol regime breakout, the UTC-00:00 opening range (BTC/ETH/SOL, 5m/15m only — the catalog's own instrument restriction), Donchian with volume, NR7 expansion, the chandelier stop-and-reverse, the failed-breakout reversal, the breakout-with-retest, and the higher-timeframe-regime breakout (the HTF regime resampled from the same klines, closed bars only). Engine: the family-A G1-G7 machinery (`code/qs_engine.py` + `code/qs_run.py`) with the family-C signal layer `code/qs_c_strats.py` (adapter `qsc`). Known-answer audit: `code/_qs_c_audit.py` — twenty-three checks, ALL PASS, on the exact bytes before any artifact. The audit caught two real builder bugs before any number was measured: the bars-since helper (a cumsum-based formula that stays at zero between flags, which would have silently broken the within-N-bars windows of QS-026 and QS-028 on real data) and the QS-021 short mirror (both sides shared the top-30%-of-range close condition, so the short never fired on a bottom-closing expansion bar). It also corrected a spec reading: the failed-breakout recovery level is the broken 20-bar low, not the breakdown bar's own low.

## VERDICT: KILLED by the gates — zero of ten PASS — but this family carries the first G5-passing edges of the whole catalog campaign

Three hundred and thirty-six cells were measured (nine strategies x two-sided AND long-only x six symbols x three timeframes, plus QS-024 x two variants x three symbols x two timeframes); all verify bit-for-bit. Verdicts: two hundred and seventy-two REJECT, twenty-eight FAIL, thirty-six INCONCLUSIVE, zero PASS.

The decisive numbers:

- G4 viability (twenty bps at Base, positive at Adverse): seventeen of three hundred and thirty-six cells — an order of magnitude more than families A and B produced, and concentrated in 1h volatility breakouts.

- one hundred and sixty of three hundred and thirty-six cells beat their own random-entry null — between family A (trend, majority) and the trade-flow pack (minority).

- twenty cells are EXECUTION-SENSITIVE.

- Per strategy (Base expectancy, null comparison, verdict mix):

  - QS-021 (e.g. `0733c8773cc20a16`, ATR compression followed by expansion): beats its null in twelve of thirty-six cells — INCONCLUSIVE four, REJECT thirty-two.

  - QS-022 (e.g. `0208c54ab0e464e7`, Bollinger Band squeeze breakout): beats its null in nineteen of thirty-six cells — FAIL four, INCONCLUSIVE four, REJECT twenty-eight.

  - QS-023 (e.g. `0b5afb49810e5f1e`, Realized-volatility regime breakout): beats its null in twenty-six of thirty-six cells — FAIL one, INCONCLUSIVE thirteen, REJECT twenty-two.

  - QS-024 (e.g. `0b65afa71b51ed38`, Opening-range breakout (UTC 00:00 anchor)): beats its null in five of twelve cells — INCONCLUSIVE one, REJECT eleven.

  - QS-025 (e.g. `070162fcaf8e86a7`, Donchian breakout with volume confirmation): beats its null in twenty-one of thirty-six cells — FAIL seven, INCONCLUSIVE two, REJECT twenty-seven.

  - QS-026 (e.g. `00105142bc156266`, NR7 range expansion): beats its null in six of thirty-six cells — INCONCLUSIVE one, REJECT thirty-five.

  - QS-027 (e.g. `07bd47e23c7f9783`, Chandelier stop-and-reverse): beats its null in four of thirty-six cells — INCONCLUSIVE one, REJECT thirty-five.

  - QS-028 (e.g. `0471c069366f71d7`, Failed breakout reversal): beats its null in nineteen of thirty-six cells — FAIL two, INCONCLUSIVE three, REJECT thirty-one.

  - QS-029 (e.g. `0697a69a9f06ba62`, Breakout with retest confirmation): beats its null in seventeen of thirty-six cells — FAIL five, INCONCLUSIVE two, REJECT twenty-nine.

  - QS-030 (e.g. `00915ec321531a5d`, Breakout filtered by higher-timeframe regime): beats its null in thirty-one of thirty-six cells — FAIL nine, INCONCLUSIVE five, REJECT twenty-two.

## The near-misses: two cells clear every gate except g6

The catalog's own verdict rule kills them; the honest record keeps what they cleared:

- `b59bf7e6e53987ac` QS-022 (Bollinger squeeze) two-sided JUPUSDT 1h: one hundred and sixty-five trades, expectancy +27.09 bps at Base / +25.71 at Adverse, PF 1.49, out-of-sample fifty-two trades, four of five folds profitable (+56.0 / +94.5 / +177.4 / +17.0 / -101.4 bps), holdout +13.57 bps, null -17.17 bps, G5 PASSES. It fails ONLY the monthly consistency sub-gate: fifty-two to fifty-four percent of months positive against the sixty percent requirement (p95 drawdown -30.68 and worst month -7.07 both pass).

- `5c2128e5190aa4b7` QS-022 two-sided HYPEUSDT 1h: one hundred and twenty-one trades, +36.64 / +32.21 bps, PF 1.57, holdout +29.95 bps, null -0.78 bps, G5 PASSES; fails g6 on both fold profitability (three of five, with single-trade folds) and monthly consistency (fifty-three percent).

- The big QS-023 (realized-vol regime) expectancies — +330.76 bps on HYPE (`70112723ff2582c4`), +84.12 on ETH (`35d22c8b49373a01`) — sit on eight-to-nineteen-trade samples and are INCONCLUSIVE by the catalog's own G5 floor; they are recorded, never ranked.

QS-022 (bandwidth squeeze then band break) is the strongest single hypothesis measured across the three catalog families: it clears viability AND the sample floor on two symbols at 1h, and dies on monthly consistency, not on cost or sample. That is a pre-registered re-look candidate with more data, the same status the absorption cell holds in the flow family — and the same caution applies: the multiple-testing haircut over three hundred and thirty-six cells applies, and a two-symbol 1h concentration is a concentration fact, not an edge proof.

## Provenance

- Adapter `qsc` in `code/vrun.py`; sources hashed: qs_engine, qs_strats, qs_c_strats, qs_run.

- All three hundred and thirty-six artifacts verify bit-for-bit (`pverify --strategy qsc`).

- Known-answer audit output: results/qs_c_audit_known_answers.txt (twenty-three checks, ALL PASS, run before any artifact).

