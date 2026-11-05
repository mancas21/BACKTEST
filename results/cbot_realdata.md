# QUANT CRYPTO BOT 10 (10-strategy suite) - real-data verdict

**Source pack:** `Downloads/QUANT CRYPTO BOT 10` -> reconstructed engine `code/cbot/`
**Adapter:** `cbot` in `code/vrun.py` (added this session; the suite had never been run through the harness)
**Data:** Binance USD-M futures 5m WITH kline field 9 (`taker_buy_base`), `data/binance_klines_5m_taker/`
**Window:** 2024-10-14 -> 2026-10-14, 210240 bars per symbol
**Costs:** taker 5 bp + slippage 1 bp per side, funding 1 bp/8h -> 12.03 bp round trip
**Pass bar (the pack's own gates):** net t > 2.5758 (Bonferroni over the ten tests), net return
positive, a permutation null at or above the ninetieth percentile, a calibration slope inside
0.7-1.3, and at least one hundred closed trades.

## RESULT - not one pass in the whole grid

| sym | run_id | bars | passes | AUC min-max | best net_t (id) | best net% (id) | max trades | buy&hold |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | `8a70837fb8e5deb2` | 210240 | 0/10 | 0.499-0.530 | +2.81 (S08) | +28.11% (S08) | 84 | +24.32% |
| ETHUSDT | `ca064d3283a086ee` | 210240 | 0/10 | 0.502-0.538 | +2.80 (S10) | +25.37% (S10) | 607 | -7.45% |
| SOLUSDT | `c5b4a8d8099671e0` | 210240 | 0/10 | 0.504-0.528 | +1.67 (S05) | +43.28% (S05) | 232 | -32.96% |
| XRPUSDT | `995a7fe94daf2126` | 210240 | 0/10 | 0.505-0.531 | +0.85 (S02) | +41.59% (S02) | 869 | +143.87% |
| SUIUSDT | `cbacef4f775d6551` | 210240 | 0/10 | 0.502-0.529 | +1.63 (S06) | +243.65% (S06) | 772 | -54.35% |

AUC never leaves 0.499-0.538. No feature family carries meaningful
directional information at a fifteen-minute horizon.

## net_t by symbol x strategy (closed trades in parentheses)

| id | BTCUSDT | ETHUSDT | SOLUSDT | XRPUSDT | SUIUSDT |
|---|---|---|---|---|---|
| S01 | +2.09 (84) | -1.69 (555) | +1.09 (205) | +0.79 (769) | +1.03 (745) |
| S02 | +1.81 (79) | -1.05 (607) | +1.41 (226) | +0.85 (869) | +0.53 (772) |
| S03 | +1.18 (83) | +0.24 (325) | +1.15 (232) | -2.08 (576) | -0.80 (502) |
| S04 | +1.17 (36) | -0.81 (205) | +0.17 (173) | -0.69 (314) | +0.02 (474) |
| S05 | -1.51 (4) | +0.86 (22) | +1.67 (28) | -3.00 (75) | -2.76 (67) |
| S06 | n/a (0) | +2.13 (37) | +0.92 (71) | -2.57 (357) | +1.63 (159) |
| S07 | -1.13 (22) | +0.28 (178) | +0.52 (56) | -0.19 (563) | +0.20 (384) |
| S08 | +2.81 (29) | -1.94 (259) | -0.01 (204) | -0.63 (414) | +0.13 (375) |
| S09 | -0.45 (3) | -0.54 (24) | +0.21 (32) | -2.13 (72) | -1.67 (79) |
| S10 | n/a (0) | +2.80 (9) | +1.20 (59) | -1.91 (22) | +1.30 (193) |

The pack's own standout, S05 taker-flow, is its real-data worst: it never reaches the
minimum trade count on any symbol and its best net_t is +1.67.

## Buy and hold decides it

On XRP the best strategy returns +41.59% against buy and hold's
+143.87%. On BTC the best strategy's +28.11%
barely edges buy and hold's +24.32%, and on 84 trades.
Where buy and hold lost (SOL -32.96%, SUI -54.35%)
the strategies also lost. There is no symbol here where the suite beats simply holding.

## Verdict

**KILLED on real data.** The two positive net_t values that clear the Bonferroni bar
(BTC S08 +2.81 on 29 trades, ETH S10 +2.80 on 9 trades) sit
far below the trade-count floor, so they are sampling noise rather than edge.

This does not contradict the pack's own published result (`suite_flow.md`, S05 PASS):
that report ran on a SYNTHETIC world in which the taker-flow field was constructed to
drive returns. It is a known-answer test of the engine. It is not evidence about markets.

## Reproduction

```
python code/vrun.py run    --strategy cbot --tf 5m --symbol BTCUSDT
python coderun.py verify 8a70837fb8e5deb2
```

All five artifacts reproduce bit-for-bit (`verify` exit 0).
Artifacts: `results/runs/<run_id>.json` for
`8a70837fb8e5deb2`, `ca064d3283a086ee`, `c5b4a8d8099671e0`, `995a7fe94daf2126`, `cbacef4f775d6551`.
