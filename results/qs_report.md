# Strategy catalog family A (QS-001..QS-010) — audit and backtest report

Date of record: 2026-10-30. Source: the Phase-3 strategy-catalog archive delivered in Downloads (exact filename in every artifact's provenance.catalog_source; extracted under code/_pack100cat/) — the strategy-catalog specification (Phase-3; this campaign covers family A only, the ten trend-following hypotheses, per instruction). Engine: `code/qs_engine.py` + `code/qs_strats.py` + `code/qs_run.py` (adapter `qs`), implementing the catalog's own common blocks: G1 one-percent risk sizing with the three-times gross cap, daily-loss halt, risk halving at minus fifteen percent from peak and review halt at minus twenty-five; G2 next-open taker fills with gap-aware stop-market stops (fill at the worse of stop and open), SL-first ties, and the declared cost ladder Base fourteen / Adverse twenty-two / Stress thirty-five basis points round trip plus the eleven-point repo gate; G3 realized funding at the settlement instants; G4 five walk-forward folds plus a once-opened final twenty-percent holdout with embargo and purge, truncation causality, PSR, and a seeded random-entry null per cell. Known-answer audit: `code/_qs_audit.py` — twenty-two checks, ALL PASS, on the exact engine bytes before any artifact (it caught seven real defects: a NaN-poisoned Wilder smoother, an unseeded supertrend ratchet, a reversal path that never closed the old leg, a daily-halt check that required an open position, price-unit sigma in QS-005, a datetime-index misalignment in QS-007, and a box-age reading in QS-010).

## VERDICT: zero of ten strategies pass the catalog's own gates — two hundred and ninety-one cells REJECT, forty-three FAIL, twenty-six INCONCLUSIVE, zero PASS

Three hundred and sixty cells were measured (ten strategies as two-sided AND long-only hypotheses x six symbols x three timeframes); all three hundred and sixty verify bit-for-bit. Per the catalog's G7 thresholds:

- G4 economic viability (net expectancy at least twenty basis points per trade at Base AND positive at Adverse): twelve of five hundred and forty cells. The best cell in the whole campaign reaches seventeen basis points — under the threshold.

- G6 robustness (at least four of five walk-forward folds profitable): three of five hundred and forty cells. Fold instability, not expectancy, is the decisive killer here.

- Sixteen cells are flagged EXECUTION-SENSITIVE (profit only at Base costs).

- The random-entry null comparison: three hundred and sixty-nine of five hundred and thirty-nine cells beat their own seeded null — the trend rules carry real structure (they lose less than random entries), just never enough to clear the catalog's viability bar after costs.

## The best cells (all still failing)

- `97c9a2fdad2aad93` QS-006 long-only HYPEUSDT 1h: n 106, expectancy +17.0 bps at Base / +14.1 at Adverse, PF 1.39, holdout +78.6 bps, folds 2/5 profitable, p95 DD -26.8 percent, verdict INCONCLUSIVE.

- `72dbbae9805ec7f1` QS-006 long-only JUPUSDT 1h: n 138, expectancy +16.6 bps at Base / +8.3 at Adverse, PF 1.37, holdout +34.9 bps, folds 2/5 profitable, p95 DD -26.6 percent, verdict FAIL.

- `8794ecf1d3453af2` QS-006 long-only JUPUSDT 1h: n 138, expectancy +16.6 bps at Base / +8.3 at Adverse, PF 1.37, holdout +34.9 bps, folds 2/5 profitable, p95 DD -26.6 percent, verdict FAIL.

- `211926931b35f476` QS-006 long-only SUIUSDT 1h: n 131, expectancy +16.3 bps at Base / +14.0 at Adverse, PF 1.40, holdout +40.1 bps, folds 0/5 profitable, p95 DD -24.3 percent, verdict FAIL.

- `55f12badd0a22027` QS-006 long-only SUIUSDT 1h: n 131, expectancy +16.3 bps at Base / +14.0 at Adverse, PF 1.40, holdout +40.1 bps, folds 0/5 profitable, p95 DD -24.3 percent, verdict FAIL.

- `b0f0dd415c07b181` QS-004 two-sided ETHUSDT 1h: n 199, expectancy +13.5 bps at Base / +8.9 at Adverse, PF 1.26, holdout +11.8 bps, folds 1/5 profitable, p95 DD -37.2 percent, verdict FAIL.

- `f9f8a9be5f95a74a` QS-006 long-only ETHUSDT 1h: n 144, expectancy +11.7 bps at Base / +1.2 at Adverse, PF 1.29, holdout +76.7 bps, folds 3/5 profitable, p95 DD -33.9 percent, verdict FAIL.

- `eaf9bbbd0bf4a984` QS-004 two-sided SUIUSDT 1h: n 197, expectancy +10.0 bps at Base / +8.3 at Adverse, PF 1.34, holdout +18.1 bps, folds 2/5 profitable, p95 DD -25.4 percent, verdict FAIL.

Every top cell is one-hour (the five-minute and fifteen-minute books are destroyed by costs, exactly as each sheet's execution-challenges field predicts); every top cell fails fold stability; the strongest (QS-006, the ADX-filtered DI continuation, long-only) tops out three basis points under the viability threshold with two of five folds green.

## Provenance

- Adapter `qs` in `code/vrun.py`; all sources hashed into every run_id (qs_engine, qs_strats, qs_run).

- All three hundred and sixty artifacts verify bit-for-bit (`pverify --strategy qs`: three hundred and sixty OK, zero stale, zero refused).

- Scope per instruction: family A only. Families B-J remain SPECIFIED_NOT_IMPLEMENTED_NOT_BACKTESTED in the catalog; the PARTIAL taker-flow strategies (the eight trade-flow hypotheses, catalog IDs forty-three, forty-four, forty-eight through fifty, fifty-three, fifty-eight and ninety-three) are implementable against the taker klines on disk when ordered.

