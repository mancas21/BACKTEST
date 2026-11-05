# Strategy catalog trade-flow hypotheses (QS-043/044/048/049/050/053/058/093) — audit and backtest report

Date of record: 2026-10-30. Source: the Phase-3 strategy-catalog archive (exact filename in every artifact's provenance; extracted under code/_pack100cat/). These are the catalog's eight PARTIAL trade-flow hypotheses — bar-level taker flow from the kline taker-buy fields (imbalance, cumulative delta, sell share), the catalog's own approximation, labeled PARTIAL because it is not tick-level order flow. Engine: the family-A G1-G7 machinery (`code/qs_engine.py` + `code/qs_run.py`) with the flow signal layer `code/qs_flow_strats.py` (adapter `qsf`). Known-answer audit: `code/_qs_flow_audit.py` — twenty-two checks, ALL PASS, on the exact bytes before any artifact (it caught one real sequencing bug: the QS-048 exhaustion entry AND'd the run condition with the down-close on the same bar, where the sheet's trigger is a down-close AFTER the exhausted run; plus five test-design fixes).

## VERDICT: KILLED — zero of eight pass; this family is WORSE than family A

Two hundred and eighty-eight cells were measured (eight strategies x two-sided AND long-only x six symbols x three timeframes); all verify bit-for-bit. Verdicts: three hundred and thirty-four REJECT, two FAIL, ninety-six INCONCLUSIVE, zero PASS.

The decisive numbers:

- The median strategy cell loses MORE than its random-entry null — only one hundred and fifty-seven of three hundred and fifty-six cells beat their own null — the OPPOSITE of family A, where the trend rules beat the null in the large majority of cells. Bar-level taker flow, as the catalog suspected, carries little exploitable information at these horizons.

- G4 viability (twenty bps at Base, positive at Adverse): eight of four hundred and thirty-two cells. The best expectancy in the campaign is `dd4ae8baf8036dcb` — QS-049 absorption, two-sided, SUS five-minute: +59.2 bps at Base / +30.9 at Adverse on 17 trades, verdict INCONCLUSIVE — it clears the twenty-bps bar on a seventeen-trade sample that the catalog's own G5 floor (thirty OOS trades) declares INCONCLUSIVE. Absorption is the one flow hypothesis worth a pre-registered re-look with more data; nothing here passes.

- eight cells are EXECUTION-SENSITIVE.

- Per strategy (median Base expectancy over the twelve symbol x timeframe cells, versus the null median):

  - QS-043 (e.g. `0114ca85061690fc`, Aggressive buy/sell trade-flow imbalance): beats its null in twenty-three of forty-six cells — INCONCLUSIVE eight, REJECT forty-four.

  - QS-044 (e.g. `17a238199a831a38`, Cumulative volume delta divergence): beats its null in twenty-one of fifty-six cells — FAIL two, INCONCLUSIVE one, REJECT fifty-three.

  - QS-048 (e.g. `0b7bdb4ae5f9079c`, Trade-flow exhaustion): beats its null in ten of thirty-five cells — INCONCLUSIVE eighteen, REJECT thirty-four.

  - QS-049 (e.g. `009c1d695cd9f9f6`, Volume absorption with price-only confirmation): beats its null in fourteen of thirty-one cells — INCONCLUSIVE thirty-one, REJECT twenty-five.

  - QS-050 (e.g. `025f8011204e7f46`, Trade-flow and price-displacement divergence): beats its null in twenty-eight of forty-seven cells — INCONCLUSIVE eleven, REJECT forty-one.

  - QS-053 (e.g. `05e64be79bd0c95c`, Price impact versus signed trade volume): beats its null in thirty-two of fifty-six cells — REJECT fifty-six.

  - QS-058 (e.g. `063afe5a3c12ab6f`, Trade-flow reversal after aggressive execution): beats its null in nine of twenty-nine cells — INCONCLUSIVE twenty-three, REJECT twenty-nine.

  - QS-093 (e.g. `0a4919aeda4b32f0`, VWAP plus trade-flow confluence): beats its null in twenty of fifty-six cells — INCONCLUSIVE four, REJECT fifty-two.

## The best cells (all still failing)

- `3630fe2670e70f15` QS-093 two-sided JUPUSDT 1h: n 89, expectancy +5.5 bps at Base / +2.2 at Adverse, PF 1.25, folds 2/5, verdict INCONCLUSIVE.

- `d2af104328358799` QS-093 two-sided JUPUSDT 1h: n 89, expectancy +5.5 bps at Base / +2.2 at Adverse, PF 1.25, folds 2/5, verdict INCONCLUSIVE.

- `e17118e771cb2766` QS-044 long-only BTCUSDT 1h: n 77, expectancy +3.7 bps at Base / -12.8 at Adverse, PF 1.18, folds 1/5, verdict INCONCLUSIVE (ES).

- `93735ee1e6277fda` QS-044 two-sided SOLUSDT 1h: n 247, expectancy +0.1 bps at Base / -3.1 at Adverse, PF 1.02, folds 3/5, verdict FAIL (ES).

- `dc9f7757161a5375` QS-044 two-sided SOLUSDT 1h: n 247, expectancy +0.1 bps at Base / -3.1 at Adverse, PF 1.02, folds 3/5, verdict FAIL (ES).

- `9e64cd2f76befc8a` QS-050 two-sided HYPEUSDT 15m: n 100, expectancy -2.3 bps at Base / -6.8 at Adverse, PF 0.95, folds 0/5, verdict REJECT.

The best cell (QS-093, VWAP-plus-flow confluence on JUP 1h) reaches five and a half basis points — a quarter of the catalog's viability threshold — and is INCONCLUSIVE on sample size anyway. Note the alignment with the repo's earlier EDGE family kill: CVD continuation and absorption were killed there too, with the same cost-wall arithmetic.

## Provenance

- Adapter `qsf` in `code/vrun.py`; sources hashed: qs_engine, qs_strats, qs_flow_strats, qs_run.

- All two hundred and eighty-eight artifacts verify bit-for-bit (`pverify --strategy qsf`).

- The zero-event 1h cells for QS-048/049/058 are the specs' own design (aggressor-imbalance runs are 5m/15m phenomena; a four-bar run above the imbalance threshold occurs once or twice per thousand 1h bars) — reported INCONCLUSIVE per the catalog's G5 rule, never estimated.

