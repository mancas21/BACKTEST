# `strategy_pack.py` — "QUANT CRYPTO BOT 10" — cross-timeframe backtest

Engine: `code/cbpack_engine.py`, a byte-identical copy of the attached `strategy_pack.py`, kept in-repo so the artifacts stay reproducible if the attached file is ever moved — which is exactly what destroyed SAX v3 (`Downloads/sax_engine-claude.py` is gone; all of its artifacts are now unverifiable).

- Costs: the pack's own defaults, 5.0 bps fee + 2.0 bps slippage per side = 14.0 bps round trip.
- Flow: **true taker flow** (`taker_buy_base`), not the candle-colour proxy.
- Execution: signal at bar close, fill at next open, adverse slippage, SL-first on ties, fees on both fills. Audited against known answers in `code/cbpack_audit.py`.
- Open interest is absent from the data, so **S08 (open-interest divergence) is SKIPPED everywhere** — never approximated. `funding_attached` is recorded per artifact; JUPUSDT has no funding file, so its funding-gated rows are SKIPPED too.
- Data: `data/binance_klines_<tf>_taker/`.

**Convention for `guard`:** every numeral is a value read from a cited artifact. Criteria, and tallies of how many cells did something, are written in words — a threshold is not a measurement, and `guard` cannot tell them apart.

## Coverage

| tf | symbol | bars | window | run_id |
|---|---|---|---|---|
| 1h | BTCUSDT | 17520 | 2024-10-14 → 2026-10-14 | `26237876f8e255f3` |
| 1h | ETHUSDT | 17520 | 2024-10-14 → 2026-10-14 | `99434312424041b2` |
| 1h | HYPEUSDT | 12075 | 2025-05-30 → 2026-10-15 | `b20ab929a0f760e9` |
| 1h | JUPUSDT | 17520 | 2024-10-15 → 2026-10-15 | `6a9729f901914b93` |
| 1h | SOLUSDT | 17520 | 2024-10-14 → 2026-10-14 | `814c80675d570aae` |
| 1h | SUIUSDT | 17520 | 2024-10-14 → 2026-10-14 | `cf001b8ff0148c27` |
| 1h | XRPUSDT | 17520 | 2024-10-14 → 2026-10-14 | `a30083333490d945` |
| 15m | BTCUSDT | 70080 | 2024-10-14 → 2026-10-14 | `343c496e9a293928` |
| 15m | ETHUSDT | 70080 | 2024-10-14 → 2026-10-14 | `5d7529ed3286ce22` |
| 15m | HYPEUSDT | 48301 | 2025-05-30 → 2026-10-15 | `ac4ff6d3a465a268` |
| 15m | JUPUSDT | 70080 | 2024-10-15 → 2026-10-15 | `40a20583a7d3c679` |
| 15m | SOLUSDT | 70080 | 2024-10-14 → 2026-10-14 | `53c36b64f8f3c6e9` |
| 15m | SUIUSDT | 70080 | 2024-10-14 → 2026-10-14 | `32ed16bf7b96cb35` |
| 15m | XRPUSDT | 70080 | 2024-10-14 → 2026-10-14 | `908481a873cf8113` |
| 5m | BTCUSDT | 210240 | 2024-10-14 → 2026-10-14 | `07c549d7d48d9c85` |
| 5m | ETHUSDT | 210240 | 2024-10-14 → 2026-10-14 | `76d109606da01088` |
| 5m | HYPEUSDT | 144904 | 2025-05-30 → 2026-10-15 | `7d7d70e160793a11` |
| 5m | JUPUSDT | 210240 | 2024-10-15 → 2026-10-15 | `b76b478cae5f1048` |
| 5m | SOLUSDT | 210240 | 2024-10-14 → 2026-10-14 | `862cc40167c27230` |
| 5m | SUIUSDT | 210240 | 2024-10-14 → 2026-10-14 | `2e3b6c6ba47d54bd` |
| 5m | XRPUSDT | 210240 | 2024-10-14 → 2026-10-14 | `002c42cdd4eeb360` |
| 1m | BTCUSDT | 1051200 | 2024-10-14 → 2026-10-14 | `4dd8b2d0284b8ccc` |
| 1m | ETHUSDT | 1051200 | 2024-10-14 → 2026-10-14 | `872ee427d61e4880` |
| 1m | HYPEUSDT | 724524 | 2025-05-30 → 2026-10-15 | `f3440cb869afd3dc` |
| 1m | JUPUSDT | 1051200 | 2024-10-15 → 2026-10-15 | `d2084bee13ee07ea` |
| 1m | SOLUSDT | 1051200 | 2024-10-14 → 2026-10-14 | `dd8b4389c96acb4a` |
| 1m | SUIUSDT | 1051200 | 2024-10-15 → 2026-10-15 | `1094ef7ea9f6d085` |
| 1m | XRPUSDT | 1051200 | 2024-10-15 → 2026-10-15 | `026442c1718e019b` |

## The headline

The pack's edge, such as it is, lives at **1h and nowhere else**. Going down the timeframes the whole stack degrades: the trade count rises, the per-trade cost carries every extra fill, and the net PF of nearly every strategy falls with it. The zero-cost control further down shows that is a **cost wall**, not a missing signal — several strategies still carry a real gross edge at 5m and 15m.

The per-cell lines below are the **in-sample** result: one cell, one strategy, the whole window, fixed default parameters. Clearing that bar is necessary, not sufficient — the out-of-sample gates later in this report are what actually decide, and one of the cells that clears the bar here is killed there.

- **1h** — three strategies clear the in-sample bar, and they sit inside two of the
  seven symbol cells, XRPUSDT (S02 and S10) and SOLUSDT (S10). Best-per-symbol net:
  XRPUSDT 184.22%, SOLUSDT 75.45%, SUIUSDT 34.42%, ETHUSDT 26.30%, JUPUSDT 23.58%,
  HYPEUSDT 19.29%, BTCUSDT 11.74%.
- **15m** — one strategy clears the bar, in one of the seven symbol cells (HYPEUSDT
  S07). Best-per-symbol net: JUPUSDT 37.08%, HYPEUSDT 22.10%, XRPUSDT 20.81%,
  SOLUSDT 20.25%, SUIUSDT 4.81%, ETHUSDT -4.30%, BTCUSDT -43.48%.
- **5m** — no cell clears the in-sample bar. Best-per-symbol net: HYPEUSDT -15.00%, SUIUSDT -22.28%, SOLUSDT -45.33%, XRPUSDT -47.02%, ETHUSDT -57.18%, JUPUSDT -73.21%, BTCUSDT -83.96%.
- **1m** — no cell clears the in-sample bar. Best-per-symbol net: HYPEUSDT -79.25%, SUIUSDT -93.42%, XRPUSDT -94.74%, ETHUSDT -95.69%, JUPUSDT -96.11%, SOLUSDT -96.21%, BTCUSDT -96.62%.

Read that as a single sentence: **the pack's signal is real but small, and its cost drag is what kills it below 1h.**

## Full-window grid, pack costs

`best net%` is the best strategy in that cell; `pass` counts strategies with PF above the repo threshold and at least the repo minimum trade count.

| tf | symbol | best net% | best PF | best strategy | strategies passing | buy&hold% | run_id |
|---|---|---|---|---|---|---|---|
| 1h | BTCUSDT | 11.74 | 1.07 | S02 | 0 of 10 | 23.04 | `26237876f8e255f3` |
| 1h | ETHUSDT | 26.30 | 1.20 | S02 | 0 of 10 | -8.68 | `99434312424041b2` |
| 1h | HYPEUSDT | 19.29 | 1.19 | S02 | 0 of 10 | 134.13 | `b20ab929a0f760e9` |
| 1h | JUPUSDT | 23.58 | 1.15 | S02 | 0 of 10 | -67.98 | `6a9729f901914b93` |
| 1h | SOLUSDT | 75.45 | 1.64 | S10 | 1 of 10 | -33.71 | `814c80675d570aae` |
| 1h | SUIUSDT | 34.42 | 1.19 | S02 | 0 of 10 | -54.94 | `cf001b8ff0148c27` |
| 1h | XRPUSDT | 184.22 | 1.81 | S10 | 2 of 10 | 142.83 | `a30083333490d945` |
| 15m | BTCUSDT | -43.48 | 0.91 | S10 | 0 of 10 | 23.92 | `343c496e9a293928` |
| 15m | ETHUSDT | -4.30 | 0.98 | S07 | 0 of 10 | -7.73 | `5d7529ed3286ce22` |
| 15m | HYPEUSDT | 22.10 | 1.29 | S07 | 1 of 10 | 134.42 | `ac4ff6d3a465a268` |
| 15m | JUPUSDT | 37.08 | 1.07 | S10 | 0 of 10 | -67.13 | `40a20583a7d3c679` |
| 15m | SOLUSDT | 20.25 | 1.03 | S10 | 0 of 10 | -32.99 | `53c36b64f8f3c6e9` |
| 15m | SUIUSDT | 4.81 | 1.01 | S10 | 0 of 10 | -54.35 | `32ed16bf7b96cb35` |
| 15m | XRPUSDT | 20.81 | 1.04 | S10 | 0 of 10 | 144.34 | `908481a873cf8113` |
| 5m | BTCUSDT | -83.96 | 0.67 | S07 | 0 of 10 | 24.32 | `07c549d7d48d9c85` |
| 5m | ETHUSDT | -57.18 | 0.81 | S07 | 0 of 10 | -7.45 | `76d109606da01088` |
| 5m | HYPEUSDT | -15.00 | 0.93 | S07 | 0 of 10 | 132.31 | `7d7d70e160793a11` |
| 5m | JUPUSDT | -73.21 | 0.88 | S10 | 0 of 10 | -67.75 | `b76b478cae5f1048` |
| 5m | SOLUSDT | -45.33 | 0.83 | S07 | 0 of 10 | -32.96 | `862cc40167c27230` |
| 5m | SUIUSDT | -22.28 | 0.89 | S07 | 0 of 10 | -54.35 | `2e3b6c6ba47d54bd` |
| 5m | XRPUSDT | -47.02 | 0.93 | S07 | 0 of 10 | 143.87 | `002c42cdd4eeb360` |
| 1m | BTCUSDT | -96.62 | 0.33 | S06 | 0 of 10 | 23.84 | `4dd8b2d0284b8ccc` |
| 1m | ETHUSDT | -95.69 | 0.48 | S06 | 0 of 10 | -8.53 | `872ee427d61e4880` |
| 1m | HYPEUSDT | -79.25 | 0.69 | S06 | 0 of 10 | 132.69 | `f3440cb869afd3dc` |
| 1m | JUPUSDT | -96.11 | 0.69 | S06 | 0 of 10 | -67.33 | `d2084bee13ee07ea` |
| 1m | SOLUSDT | -96.21 | 0.58 | S06 | 0 of 10 | -33.42 | `dd8b4389c96acb4a` |
| 1m | SUIUSDT | -93.42 | 0.73 | S06 | 0 of 10 | -54.46 | `1094ef7ea9f6d085` |
| 1m | XRPUSDT | -94.74 | 0.61 | S06 | 0 of 10 | 139.84 | `026442c1718e019b` |

## Per-strategy PF, median across symbols

| strategy | 1h | 15m | 5m | 1m |
|---|---|---|---|---|
| S01 | 0.81 | 0.82 | 0.72 | 0.41 |
| S02 | 1.15 | 0.94 | 0.73 | 0.48 |
| S03 | 0.97 | 0.73 | 0.63 | 0.42 |
| S04 | 0.86 | 0.75 | 0.75 | 0.51 |
| S05 | 0.78 | 0.69 | 0.43 | 0.12 |
| S06 | 0.81 | 0.73 | 0.62 | 0.51 |
| S07 | 0.89 | 0.80 | 0.73 | 0.58 |
| S08 | — | — | — | — |
| S09 | 0.67 | 0.63 | 0.63 | 0.37 |
| S10 | 1.15 | 1.01 | 0.83 | 0.57 |

## The control that decides it: gross PF (zero fees, zero slippage)

A strategy whose *gross* PF is near 1 has no signal at all — its net PF is just noise minus cost. One whose gross PF is clearly above 1 but whose net PF collapses had a real signal that costs destroyed. Only this control separates the two, and they demand different responses (abandon vs trade cheaper).

| strategy | tf | gross PF (median) | net PF (median) | cost drag | symbols gross > 1 |
|---|---|---|---|---|---|
| S01 | 1h | 0.90 | 0.81 | 0.09 | 3 of 7 |
| S02 | 1h | 1.28 | 1.15 | 0.14 | 7 of 7 |
| S03 | 1h | 1.14 | 0.97 | 0.17 | 6 of 7 |
| S04 | 1h | 0.96 | 0.86 | 0.10 | 2 of 7 |
| S05 | 1h | 1.02 | 0.78 | 0.24 | 5 of 7 |
| S06 | 1h | 1.04 | 0.81 | 0.23 | 4 of 7 |
| S07 | 1h | 1.05 | 0.89 | 0.16 | 3 of 6 |
| S09 | 1h | 0.84 | 0.67 | 0.17 | 1 of 7 |
| S10 | 1h | 1.23 | 1.15 | 0.07 | 6 of 7 |
| S01 | 15m | 1.03 | 0.82 | 0.21 | 5 of 7 |
| S02 | 15m | 1.14 | 0.94 | 0.20 | 6 of 7 |
| S03 | 15m | 0.96 | 0.73 | 0.23 | 3 of 7 |
| S04 | 15m | 0.94 | 0.75 | 0.19 | 1 of 7 |
| S05 | 15m | 1.14 | 0.69 | 0.45 | 7 of 7 |
| S06 | 15m | 0.98 | 0.73 | 0.25 | 2 of 7 |
| S07 | 15m | 0.96 | 0.80 | 0.16 | 2 of 6 |
| S09 | 15m | 0.93 | 0.63 | 0.30 | 1 of 7 |
| S10 | 15m | 1.18 | 1.01 | 0.17 | 6 of 7 |
| S01 | 5m | 0.99 | 0.72 | 0.27 | 2 of 7 |
| S02 | 5m | 0.96 | 0.73 | 0.23 | 1 of 7 |
| S03 | 5m | 0.94 | 0.63 | 0.31 | 1 of 7 |
| S04 | 5m | 1.01 | 0.75 | 0.26 | 4 of 7 |
| S05 | 5m | 1.08 | 0.43 | 0.65 | 7 of 7 |
| S06 | 5m | 0.95 | 0.62 | 0.33 | 1 of 7 |
| S07 | 5m | 0.98 | 0.73 | 0.25 | 2 of 6 |
| S09 | 5m | 0.97 | 0.63 | 0.34 | 1 of 7 |
| S10 | 5m | 1.09 | 0.83 | 0.26 | 6 of 7 |
| — | 1m | — | — | — | *(not run: the zero-cost control covers 1h, 15m and 5m)* |

- 1h zero-cost artifacts (BTCUSDT, ETHUSDT, HYPEUSDT, JUPUSDT, SOLUSDT, SUIUSDT, XRPUSDT): `b4b13fe5a6120e68` `edbefc5b2592d29c` `2f0684e8f1457428` `cf055c3ff45a9c9a` `ca03a176425b8d76` `e9c756adeb09334d` `2cfa0d31d2122da2`
- 15m zero-cost artifacts (BTCUSDT, ETHUSDT, HYPEUSDT, JUPUSDT, SOLUSDT, SUIUSDT, XRPUSDT): `60896ccc75dcd8b0` `51d96017fb8b1129` `e8b50fd959ce2e9b` `a490560fc87080c7` `f1e8381a7133e767` `e62205adc5cc1a34` `a1dd7680e1a5f6e5`
- 5m zero-cost artifacts (BTCUSDT, ETHUSDT, HYPEUSDT, JUPUSDT, SOLUSDT, SUIUSDT, XRPUSDT): `60c20d2743bfd37f` `0f65b683264d46ae` `3d5ac1a3995ca2b0` `0f8affb10e41645c` `c0075a20867a8331` `124b463d2e99479b` `41a373bf7e5f90bd`

## Out-of-sample gates on the survivors

Three independent gates per candidate cell: a period split, the pack's own walk-forward at three different window geometries, and a rerun at repo-standard costs (6 bps fee + 5 bps slippage per side) instead of the pack's cheaper defaults.

| tf | symbol | strategy | net% | PF | n | periods green | WF positive | WF beats buy&hold | PF at repo costs | run_id |
|---|---|---|---|---|---|---|---|---|---|---|
| 15m | HYPEUSDT | S07 | 22.10 | 1.29 | 115 | 2 of 3 | 0 of 3 | 0 of 3 | 1.10 | `ac4ff6d3a465a268` |
| 1h | BTCUSDT | S02 | 11.74 | 1.07 | 250 | 2 of 3 | 1 of 3 | 1 of 3 | 0.96 | `26237876f8e255f3` |
| 1h | BTCUSDT | S10 | 3.40 | 1.03 | 178 | 2 of 3 | 2 of 3 | 2 of 3 | 0.96 | `26237876f8e255f3` |
| 1h | ETHUSDT | S02 | 26.30 | 1.14 | 249 | 2 of 3 | 3 of 3 | 3 of 3 | 1.06 | `99434312424041b2` |
| 1h | ETHUSDT | S10 | 23.17 | 1.20 | 182 | 3 of 3 | 2 of 3 | 2 of 3 | 1.14 | `99434312424041b2` |
| 1h | HYPEUSDT | S02 | 19.29 | 1.19 | 171 | 2 of 3 | 2 of 3 | 1 of 3 | 1.14 | `b20ab929a0f760e9` |
| 1h | HYPEUSDT | S10 | 10.97 | 1.15 | 119 | 2 of 3 | 3 of 3 | 2 of 3 | 1.09 | `b20ab929a0f760e9` |
| 1h | JUPUSDT | S02 | 23.58 | 1.15 | 238 | 2 of 3 | 3 of 3 | 2 of 3 | 1.11 | `6a9729f901914b93` |
| 1h | JUPUSDT | S10 | -23.75 | 0.74 | 174 | 0 of 3 | 1 of 3 | 0 of 3 | 0.72 | `6a9729f901914b93` |
| 1h | SOLUSDT | S02 | 15.30 | 1.08 | 263 | 2 of 3 | 3 of 3 | 3 of 3 | 1.03 | `814c80675d570aae` |
| 1h | SOLUSDT | S10 | 75.45 | 1.64 | 172 | 2 of 3 | 3 of 3 | 3 of 3 | 1.56 | `814c80675d570aae` |
| 1h | SUIUSDT | S02 | 34.42 | 1.19 | 237 | 2 of 3 | 3 of 3 | 3 of 3 | 1.15 | `cf001b8ff0148c27` |
| 1h | SUIUSDT | S10 | 11.44 | 1.12 | 165 | 2 of 3 | 2 of 3 | 2 of 3 | 1.08 | `cf001b8ff0148c27` |
| 1h | XRPUSDT | S02 | 184.01 | 1.61 | 224 | 3 of 3 | 3 of 3 | 3 of 3 | 1.47 | `a30083333490d945` |
| 1h | XRPUSDT | S10 | 184.22 | 1.81 | 168 | 3 of 3 | 2 of 3 | 2 of 3 | 1.75 | `a30083333490d945` |

### Walk-forward detail — every geometry, every candidate

Each row is one run: the grid is re-selected on the train window and traded untouched on the next test window; `oos net%` compounds the non-overlapping test segments. `folds won` is how many test segments were profitable.

| tf | symbol | strategy | train/test days | folds | oos net% | folds won | oos buy&hold% | run_id |
|---|---|---|---|---|---|---|---|---|
| 15m | HYPEUSDT | S07 | 120/60 | 6 | -0.69 | 3 of 6 | 22.65 | `bbe07a17afe31e37` |
| 15m | HYPEUSDT | S07 | 90/30 | 13 | -0.62 | 4 of 13 | 12.94 | `9c7dd1925b43ce50` |
| 15m | HYPEUSDT | S07 | 180/90 | 3 | -0.45 | 2 of 3 | 47.55 | `9fde16a7db05ee9e` |
| 1h | BTCUSDT | S02 | 120/60 | 10 | 9.39 | 6 of 10 | 0.31 | `939b1368132ceb08` |
| 1h | BTCUSDT | S10 | 120/60 | 10 | 7.77 | 5 of 10 | 0.31 | `939b1368132ceb08` |
| 1h | BTCUSDT | S02 | 90/30 | 21 | -3.84 | 7 of 21 | 0.25 | `207f6f759e175517` |
| 1h | BTCUSDT | S10 | 90/30 | 21 | -7.42 | 7 of 21 | 0.25 | `207f6f759e175517` |
| 1h | BTCUSDT | S02 | 180/90 | 6 | -5.62 | 2 of 6 | 2.75 | `4fa9fbc1a2aaee16` |
| 1h | BTCUSDT | S10 | 180/90 | 6 | 6.51 | 3 of 6 | 2.75 | `4fa9fbc1a2aaee16` |
| 1h | ETHUSDT | S02 | 120/60 | 10 | 20.47 | 6 of 10 | 6.32 | `f96061efa23717a4` |
| 1h | ETHUSDT | S10 | 120/60 | 10 | 28.02 | 6 of 10 | 6.32 | `f96061efa23717a4` |
| 1h | ETHUSDT | S02 | 90/30 | 21 | 13.84 | 10 of 21 | 1.34 | `3157761960253bfe` |
| 1h | ETHUSDT | S10 | 90/30 | 21 | -11.94 | 10 of 21 | 1.34 | `3157761960253bfe` |
| 1h | ETHUSDT | S02 | 180/90 | 6 | 18.63 | 4 of 6 | 16.47 | `3b5193cb4cbf9226` |
| 1h | ETHUSDT | S10 | 180/90 | 6 | 62.44 | 4 of 6 | 16.47 | `3b5193cb4cbf9226` |
| 1h | HYPEUSDT | S02 | 120/60 | 6 | -5.31 | 1 of 6 | 22.63 | `02f93170c835d5d9` |
| 1h | HYPEUSDT | S10 | 120/60 | 6 | 26.71 | 5 of 6 | 22.63 | `02f93170c835d5d9` |
| 1h | HYPEUSDT | S02 | 90/30 | 13 | 38.44 | 7 of 13 | 8.06 | `15cf36ba04d458ef` |
| 1h | HYPEUSDT | S10 | 90/30 | 13 | 53.87 | 9 of 13 | 8.06 | `15cf36ba04d458ef` |
| 1h | HYPEUSDT | S02 | 180/90 | 3 | 7.21 | 1 of 3 | 47.18 | `52ef0460a7426e1c` |
| 1h | HYPEUSDT | S10 | 180/90 | 3 | 36.57 | 2 of 3 | 47.18 | `52ef0460a7426e1c` |
| 1h | JUPUSDT | S02 | 120/60 | 10 | 7.06 | 6 of 10 | -2.02 | `58b3350bea9ccbe4` |
| 1h | JUPUSDT | S10 | 120/60 | 10 | -4.69 | 5 of 10 | -2.02 | `58b3350bea9ccbe4` |
| 1h | JUPUSDT | S02 | 90/30 | 21 | 3.20 | 12 of 21 | -0.32 | `c0fad1ec6ad653d6` |
| 1h | JUPUSDT | S10 | 90/30 | 21 | -0.83 | 10 of 21 | -0.32 | `c0fad1ec6ad653d6` |
| 1h | JUPUSDT | S02 | 180/90 | 6 | 1.88 | 4 of 6 | 3.95 | `c3e2aaf6afcd2422` |
| 1h | JUPUSDT | S10 | 180/90 | 6 | 2.82 | 3 of 6 | 3.95 | `c3e2aaf6afcd2422` |
| 1h | SOLUSDT | S02 | 120/60 | 10 | 49.40 | 8 of 10 | -0.00 | `27ad992e1dd34a27` |
| 1h | SOLUSDT | S10 | 120/60 | 10 | 40.74 | 5 of 10 | -0.00 | `27ad992e1dd34a27` |
| 1h | SOLUSDT | S02 | 90/30 | 21 | 54.10 | 9 of 21 | 0.12 | `9ed7a880c34f36c0` |
| 1h | SOLUSDT | S10 | 90/30 | 21 | 23.36 | 9 of 21 | 0.12 | `9ed7a880c34f36c0` |
| 1h | SOLUSDT | S02 | 180/90 | 6 | 25.49 | 5 of 6 | 4.29 | `f7798500d5b0239e` |
| 1h | SOLUSDT | S10 | 180/90 | 6 | 8.42 | 3 of 6 | 4.29 | `f7798500d5b0239e` |
| 1h | SUIUSDT | S02 | 120/60 | 10 | 61.97 | 6 of 10 | -3.75 | `2fb599ca85852493` |
| 1h | SUIUSDT | S10 | 120/60 | 10 | 42.25 | 5 of 10 | -3.75 | `2fb599ca85852493` |
| 1h | SUIUSDT | S02 | 90/30 | 21 | 42.46 | 11 of 21 | -2.97 | `7380dbece4f1281a` |
| 1h | SUIUSDT | S10 | 90/30 | 21 | -7.74 | 6 of 21 | -2.97 | `7380dbece4f1281a` |
| 1h | SUIUSDT | S02 | 180/90 | 6 | 39.97 | 3 of 6 | -2.02 | `898b13b65e1deb27` |
| 1h | SUIUSDT | S10 | 180/90 | 6 | 72.24 | 4 of 6 | -2.02 | `898b13b65e1deb27` |
| 1h | XRPUSDT | S02 | 120/60 | 10 | 32.29 | 4 of 10 | -2.29 | `ef3c6a9bbda4bd71` |
| 1h | XRPUSDT | S10 | 120/60 | 10 | 7.25 | 4 of 10 | -2.29 | `ef3c6a9bbda4bd71` |
| 1h | XRPUSDT | S02 | 90/30 | 21 | 69.48 | 10 of 21 | -1.34 | `9840c3069c15f837` |
| 1h | XRPUSDT | S10 | 90/30 | 21 | 33.25 | 10 of 21 | -1.34 | `9840c3069c15f837` |
| 1h | XRPUSDT | S02 | 180/90 | 6 | 18.34 | 2 of 6 | -2.45 | `fe71b471b85bde19` |
| 1h | XRPUSDT | S10 | 180/90 | 6 | -17.93 | 1 of 6 | -2.45 | `fe71b471b85bde19` |

### Period split — strategy vs buy&hold on the *same* slice

AGENTS.md: a strategy that only wins by losing less than a collapsing market is not alpha. These rows put the strategy's return next to buy&hold on exactly the same bars.

| tf | symbol | strategy | period | net% | buy&hold% | excess | PF | n | exposure% | maxDD% | run_id |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 15m | HYPEUSDT | S07 | 1 | 9.50 | 13.14 | -3.64 | 1.56 | 29 | 5.1 | -5.5 | `9ffb987b7bc94841` |
| 15m | HYPEUSDT | S07 | 2 | -6.93 | 4.10 | -11.04 | 0.75 | 37 | 4.9 | -13.6 | `1198af0d0b86b1f3` |
| 15m | HYPEUSDT | S07 | 3 | 13.20 | 98.69 | -85.49 | 1.66 | 35 | 4.5 | -8.8 | `fb307b15a0d76c43` |
| 1h | BTCUSDT | S02 | 1 | -6.32 | 59.61 | -65.93 | 0.90 | 85 | 38.0 | -19.4 | `dd4af52ddf5a6a70` |
| 1h | BTCUSDT | S10 | 1 | -3.69 | 59.61 | -63.30 | 0.89 | 59 | 68.2 | -17.6 | `dd4af52ddf5a6a70` |
| 1h | BTCUSDT | S02 | 2 | 11.52 | -36.20 | 47.73 | 1.24 | 78 | 40.4 | -15.0 | `50fe9bebd9bb1333` |
| 1h | BTCUSDT | S10 | 2 | 1.69 | -36.20 | 37.89 | 1.05 | 56 | 74.5 | -17.0 | `50fe9bebd9bb1333` |
| 1h | BTCUSDT | S02 | 3 | 13.39 | 20.71 | -7.32 | 1.23 | 81 | 40.6 | -20.2 | `f4f39e13e9d3debe` |
| 1h | BTCUSDT | S10 | 3 | 4.22 | 20.71 | -16.50 | 1.10 | 59 | 72.1 | -14.9 | `f4f39e13e9d3debe` |
| 1h | ETHUSDT | S02 | 1 | -4.48 | -3.74 | -0.74 | 0.93 | 89 | 41.9 | -16.3 | `6b322e6cee0cbaef` |
| 1h | ETHUSDT | S10 | 1 | 0.49 | -3.74 | 4.23 | 1.01 | 60 | 68.3 | -12.7 | `6b322e6cee0cbaef` |
| 1h | ETHUSDT | S02 | 2 | 27.60 | -22.29 | 49.89 | 1.51 | 75 | 40.6 | -14.3 | `7d277daf043ab750` |
| 1h | ETHUSDT | S10 | 2 | 18.95 | -22.29 | 41.23 | 1.54 | 55 | 75.0 | -13.0 | `7d277daf043ab750` |
| 1h | ETHUSDT | S02 | 3 | 7.35 | 21.41 | -14.05 | 1.12 | 79 | 36.3 | -22.8 | `018e59b140d25b11` |
| 1h | ETHUSDT | S10 | 3 | 2.52 | 21.41 | -18.88 | 1.06 | 65 | 68.4 | -14.8 | `018e59b140d25b11` |
| 1h | HYPEUSDT | S02 | 1 | 1.83 | 14.06 | -12.23 | 1.05 | 56 | 44.0 | -16.7 | `0a53f204e2954b55` |
| 1h | HYPEUSDT | S10 | 1 | 13.17 | 14.06 | -0.90 | 1.81 | 35 | 76.6 | -9.1 | `0a53f204e2954b55` |
| 1h | HYPEUSDT | S02 | 2 | -5.21 | 3.77 | -8.97 | 0.86 | 61 | 36.6 | -13.9 | `bd4ff19eca389209` |
| 1h | HYPEUSDT | S10 | 2 | -10.37 | 3.77 | -14.13 | 0.58 | 41 | 71.4 | -13.2 | `bd4ff19eca389209` |
| 1h | HYPEUSDT | S02 | 3 | 26.40 | 101.48 | -75.08 | 1.94 | 50 | 43.0 | -9.8 | `7b5e7bbdaf404b71` |
| 1h | HYPEUSDT | S10 | 3 | 15.55 | 101.48 | -85.92 | 1.69 | 38 | 80.0 | -9.3 | `7b5e7bbdaf404b71` |
| 1h | JUPUSDT | S02 | 1 | 25.64 | -54.78 | 80.42 | 1.60 | 74 | 38.9 | -7.5 | `92a62a766d246281` |
| 1h | JUPUSDT | S10 | 1 | -10.14 | -54.78 | 44.64 | 0.67 | 55 | 69.0 | -20.4 | `92a62a766d246281` |
| 1h | JUPUSDT | S02 | 2 | -4.53 | -63.39 | 58.86 | 0.90 | 84 | 40.1 | -17.4 | `da9c7be30c2fcb23` |
| 1h | JUPUSDT | S10 | 2 | -2.52 | -63.39 | 60.87 | 0.92 | 54 | 71.0 | -11.9 | `da9c7be30c2fcb23` |
| 1h | JUPUSDT | S02 | 3 | 2.51 | 91.92 | -89.41 | 1.06 | 76 | 37.1 | -10.4 | `1dfa207ace52daf5` |
| 1h | JUPUSDT | S10 | 3 | -10.59 | 91.92 | -102.51 | 0.70 | 61 | 75.0 | -21.9 | `1dfa207ace52daf5` |
| 1h | SOLUSDT | S02 | 1 | 20.11 | -6.74 | 26.85 | 1.38 | 82 | 41.5 | -12.5 | `c74dccf1ea0ed3b4` |
| 1h | SOLUSDT | S10 | 1 | -0.53 | -6.74 | 6.21 | 0.99 | 62 | 71.7 | -19.6 | `c74dccf1ea0ed3b4` |
| 1h | SOLUSDT | S02 | 2 | -9.93 | -45.20 | 35.27 | 0.83 | 92 | 41.3 | -20.3 | `0882c654a7660843` |
| 1h | SOLUSDT | S10 | 2 | 45.52 | -45.20 | 90.71 | 2.80 | 47 | 78.2 | -8.5 | `0882c654a7660843` |
| 1h | SOLUSDT | S02 | 3 | 10.95 | 28.01 | -17.05 | 1.18 | 82 | 41.5 | -17.0 | `dec8c4aff3503bcb` |
| 1h | SOLUSDT | S10 | 3 | 21.42 | 28.01 | -6.59 | 1.66 | 59 | 73.3 | -16.9 | `dec8c4aff3503bcb` |
| 1h | SUIUSDT | S02 | 1 | 16.49 | 33.02 | -16.53 | 1.35 | 82 | 39.2 | -12.0 | `31b3100569b7f4a3` |
| 1h | SUIUSDT | S10 | 1 | -10.43 | 33.02 | -43.45 | 0.74 | 64 | 68.7 | -20.8 | `31b3100569b7f4a3` |
| 1h | SUIUSDT | S02 | 2 | 33.70 | -69.08 | 102.78 | 1.76 | 76 | 37.8 | -15.5 | `f0a1028e69644efa` |
| 1h | SUIUSDT | S10 | 2 | 20.45 | -69.08 | 89.53 | 1.66 | 52 | 75.2 | -11.8 | `f0a1028e69644efa` |
| 1h | SUIUSDT | S02 | 3 | -14.92 | 8.63 | -23.55 | 0.69 | 76 | 37.0 | -24.3 | `ff0e9b3c4d3caa3f` |
| 1h | SUIUSDT | S10 | 3 | 2.06 | 8.63 | -6.57 | 1.08 | 49 | 69.9 | -17.1 | `ff0e9b3c4d3caa3f` |
| 1h | XRPUSDT | S02 | 1 | 88.75 | 293.07 | -204.31 | 2.18 | 66 | 33.7 | -17.4 | `95555245d5353174` |
| 1h | XRPUSDT | S10 | 1 | 103.92 | 293.07 | -189.15 | 2.53 | 55 | 70.0 | -19.1 | `95555245d5353174` |
| 1h | XRPUSDT | S02 | 2 | 20.53 | -36.07 | 56.60 | 1.35 | 80 | 32.9 | -15.8 | `7e730d5c43c2adbe` |
| 1h | XRPUSDT | S10 | 2 | 29.99 | -36.07 | 66.06 | 1.97 | 52 | 71.6 | -14.8 | `7e730d5c43c2adbe` |
| 1h | XRPUSDT | S02 | 3 | 23.91 | -4.37 | 28.28 | 1.48 | 74 | 34.5 | -24.9 | `9eb69b6dece418a5` |
| 1h | XRPUSDT | S10 | 3 | 10.93 | -4.37 | 15.30 | 1.33 | 55 | 67.3 | -17.8 | `9eb69b6dece418a5` |

## Cross-sectional consistency — does the effect survive outside the cell that selected it?

This is the test that addresses selection directly. The 1h XRP and SOL cells were picked *because* they passed out of every cell tested, so a single passing cell proves little. If the effect is real it must also appear on the symbols the selection never saw.

**Net PF at 1h, pack costs**

| strategy | BTC | ETH | HYPE | JUP | SOL | SUI | XRP | symbols above 1 |
|---|---|---|---|---|---|---|---|---|
| S01 | 0.95 | 0.77 | 0.81 | 0.76 | 0.72 | 1.02 | 0.93 | 1 of 7 |
| S02 | 1.07 | 1.14 | 1.19 | 1.15 | 1.08 | 1.19 | 1.61 | 7 of 7 |
| S03 | 0.76 | 0.93 | 1.08 | 1.01 | 0.97 | 0.87 | 1.17 | 3 of 7 |
| S04 | 0.86 | 0.95 | 0.89 | 0.73 | 0.90 | 0.73 | 0.63 | 0 of 7 |
| S05 | 0.60 | 0.73 | 0.77 | 0.81 | 0.78 | 0.84 | 0.80 | 0 of 7 |
| S06 | 0.69 | 0.81 | 0.73 | 0.81 | 0.87 | 0.90 | 0.88 | 0 of 7 |
| S07 | 0.61 | 1.02 | 0.68 | — | 1.57 | 0.89 | 0.54 | 2 of 6 |
| S09 | 0.61 | 0.70 | 0.47 | 0.63 | 0.67 | 0.99 | 0.72 | 0 of 7 |
| S10 | 1.03 | 1.20 | 1.15 | 0.74 | 1.64 | 1.12 | 1.81 | 6 of 7 |

## What it means

- **Below 1h the pack is not a strategy, it is a fee generator.** The zero-cost control shows several strategies carry a real gross edge even at 5m — S05's median gross PF at 5m is 1.08 with the median net PF at 0.43, a cost drag of 0.65, tripled from 0.24 at 1h. That is a *cost* problem, not a signal problem, and the honest responses are different (trade cheaper or don't trade), not more parameter search.
- **At 1h the pack has a real but small edge.** S02 ("Donchian + Flow Breakout") has a median gross PF at 1h of 1.28 and S10 ("Vol-Targeted Time-Series Momentum") 1.23 — the only two strategies whose median gross PF at 1h clears the repo threshold. Their net PF survives at 1.15 and 1.15 respectively: **above break-even at the median, but under the repo's threshold**. Simple, cheap, low-turnover trend logic is the only part of this pack that pays.
- **Do not read the XRP number as alpha.** XRP is the best cell in the grid (184.01% for S02, 184.22% for S10) and both beat buy&hold. But in the first third of the window buy&hold made 293.07% while S02 made 88.75% and S10 103.92% — the strategies capture a fraction of the upside, with window exposure of 34.5% for S02 and 71.0% for S10. They earn their excess by *avoiding* the decline: in the second slice buy&hold fell -36.07% and S02 still made 20.53%. That is a risk-management result more than a market-beating one, and it is worth less than the headline suggests.
- **XRP and SOL are the best of seven symbols, and that is partly selection.** At 1h, S02 is above break-even on 7 of the 7 symbols while S10 is on 6, so the effect is not one symbol's accident — it is a small 1h edge whose strongest expressions are XRP and SOL. As a seven-symbol portfolio the pack does not clear the repo's bar; as a two-strategy 1h candidate on XRP and SOL it does, and it survives a period split, three walk-forward geometries and repo-standard costs.
- **The walk-forward keeps the win rate near a coin flip.** Fold win rates sit around half in most geometries: the edge is real but lumpy, carried by a minority of folds. Position sizing, not signal tuning, is where the risk lives.
- **The 1h parameter grid was never swept.** Every number here uses the pack's fixed default parameters; only the walk-forward re-selects from the grid, and it does so inside each train window. A full grid sweep at 1h would answer the "neighbourhood stable" criterion directly and has not been done.
- **S08 was never tested.** Binance serves roughly three weeks of open-interest history, which is a rounding error against a two-year window, so the open-interest strategy is reported SKIPPED rather than approximated. That is a gap in this report, not a pass for S08.

## The pack will not run here as shipped

Two plumbing defects, both fixed in the adapter and neither touching the pack's code.
They are not strategy findings, but they are the first thing anyone running
`strategy_pack.py` directly will hit in this environment.

- **Current pandas breaks its funding merge.** `attach_funding` merges a
  millisecond-resolution funding series into an index that `df.index + Timedelta` has
  just upcast to microseconds, and `merge_asof` refuses mixed resolutions. The adapter
  aligns the funding index unit before the call — same instants, no semantic change —
  and leaves the pack's own code intact.
- **`load_ohlcv` does not recognise this repo's timestamp column.** The Binance CSVs
  name it `open_ts`; the loader looks for `open_time`, `timestamp`, `time`, `datetime`
  or `date`. The adapter renames it before handing the frame over.

## Verdict

**KILLED below 1h, CONDITIONAL at 1h.**

Below 1h there is nothing to rescue: at 5m no cell clears the gate, and at 1m the pack
is not merely unprofitable but ruinous, on every symbol, at a trade count in the
hundreds. The zero-cost control is the part worth keeping: at 5m several strategies
carry a genuine gross edge that the round-trip cost wipes out, so the failure below 1h
is an execution-cost wall rather than an absence of signal — a different problem with a
different (and cheaper) remedy.

At 1h the pack holds a real but small edge, and two cells survive every gate applied
here — XRP S02 and SOL S10 — including a period split, three walk-forward geometries and
repo-standard costs. Three qualifications keep this from being a recommendation: the
strongest cell is a drawdown-avoidance result rather than market-beating alpha, the
median 1h net PF across the seven-symbol portfolio sits under the repo threshold, and
the neighbourhood-stability criterion was never tested because no parameter grid was
swept. Whoever picks these two cells up should start there, not with more symbols.

## How to reproduce



```
python code/vrun.py matrix --strategy cbpack            # the 4x7 grid
python code/vrun.py matrix --strategy cbpack --index-only  # rebuild the index
python code/_cbpack_cost.py                            # the zero-cost control
python code/_cbpack_gates.py 1h:XRPUSDT:S02,S10 ...    # the OOS gates
python code/_verify_strategy.py cbpack                 # verify every artifact
python code/vrun.py guard --report results/cbpack_backtest.md
```

## run_ids cited in this report

- `002c42cdd4eeb360` — cbpack XRPUSDT 5m params={}
- `018e59b140d25b11` — cbpack ETHUSDT 1h params={"slice_from": "2026-02-13T13:20:00+00:00", "slice_to": "2026-10-14T21:00:00+00:00"}
- `026442c1718e019b` — cbpack XRPUSDT 1m params={}
- `02f93170c835d5d9` — cbpack HYPEUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `07c549d7d48d9c85` — cbpack BTCUSDT 5m params={}
- `0882c654a7660843` — cbpack SOLUSDT 1h params={"slice_from": "2025-06-15T05:40:00+00:00", "slice_to": "2026-02-13T13:20:00+00:00"}
- `0a53f204e2954b55` — cbpack HYPEUSDT 1h params={"slice_from": "2025-05-30T10:00:00+00:00", "slice_to": "2025-11-14T02:40:00+00:00"}
- `0f65b683264d46ae` — cbpack ETHUSDT 5m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `0f8affb10e41645c` — cbpack JUPUSDT 5m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `1094ef7ea9f6d085` — cbpack SUIUSDT 1m params={}
- `112f41bfc1bfb8a5` — cbpack HYPEUSDT 15m params={"fee_bps": 6.0, "slippage_bps": 5.0}
- `1198af0d0b86b1f3` — cbpack HYPEUSDT 15m params={"slice_from": "2025-11-14T03:30:00+00:00", "slice_to": "2026-04-30T20:30:00+00:00"}
- `124b463d2e99479b` — cbpack SUIUSDT 5m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `15cf36ba04d458ef` — cbpack HYPEUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `1dfa207ace52daf5` — cbpack JUPUSDT 1h params={"slice_from": "2026-02-14T04:20:00+00:00", "slice_to": "2026-10-15T12:00:00+00:00"}
- `207f6f759e175517` — cbpack BTCUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `26237876f8e255f3` — cbpack BTCUSDT 1h params={}
- `27ad992e1dd34a27` — cbpack SOLUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `2cfa0d31d2122da2` — cbpack XRPUSDT 1h params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `2e3b6c6ba47d54bd` — cbpack SUIUSDT 5m params={}
- `2f0684e8f1457428` — cbpack HYPEUSDT 1h params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `2fb599ca85852493` — cbpack SUIUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `3157761960253bfe` — cbpack ETHUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `31b3100569b7f4a3` — cbpack SUIUSDT 1h params={"slice_from": "2024-10-14T22:00:00+00:00", "slice_to": "2025-06-15T05:40:00+00:00"}
- `32ed16bf7b96cb35` — cbpack SUIUSDT 15m params={}
- `343c496e9a293928` — cbpack BTCUSDT 15m params={}
- `3b5193cb4cbf9226` — cbpack ETHUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `3d5ac1a3995ca2b0` — cbpack HYPEUSDT 5m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `40a20583a7d3c679` — cbpack JUPUSDT 15m params={}
- `41a373bf7e5f90bd` — cbpack XRPUSDT 5m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `456f33e22d354596` — cbpack XRPUSDT 1h params={"ids": "S10,S02", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `47b9d0450ac4a7a7` — cbpack BTCUSDT 1h params={"fee_bps": 6.0, "slippage_bps": 5.0}
- `4dd8b2d0284b8ccc` — cbpack BTCUSDT 1m params={}
- `4fa9fbc1a2aaee16` — cbpack BTCUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `50fe9bebd9bb1333` — cbpack BTCUSDT 1h params={"slice_from": "2025-06-15T05:40:00+00:00", "slice_to": "2026-02-13T13:20:00+00:00"}
- `51d96017fb8b1129` — cbpack ETHUSDT 15m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `52ef0460a7426e1c` — cbpack HYPEUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `53c36b64f8f3c6e9` — cbpack SOLUSDT 15m params={}
- `55a80038d3f682d3` — cbpack XRPUSDT 1h params={"ids": "S10,S02", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `58b3350bea9ccbe4` — cbpack JUPUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `5d7529ed3286ce22` — cbpack ETHUSDT 15m params={}
- `60896ccc75dcd8b0` — cbpack BTCUSDT 15m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `60c20d2743bfd37f` — cbpack BTCUSDT 5m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `6a9729f901914b93` — cbpack JUPUSDT 1h params={}
- `6b322e6cee0cbaef` — cbpack ETHUSDT 1h params={"slice_from": "2024-10-14T22:00:00+00:00", "slice_to": "2025-06-15T05:40:00+00:00"}
- `7380dbece4f1281a` — cbpack SUIUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `76d109606da01088` — cbpack ETHUSDT 5m params={}
- `7b5e7bbdaf404b71` — cbpack HYPEUSDT 1h params={"slice_from": "2026-04-30T19:20:00+00:00", "slice_to": "2026-10-15T12:00:00+00:00"}
- `7d277daf043ab750` — cbpack ETHUSDT 1h params={"slice_from": "2025-06-15T05:40:00+00:00", "slice_to": "2026-02-13T13:20:00+00:00"}
- `7d7d70e160793a11` — cbpack HYPEUSDT 5m params={}
- `7e730d5c43c2adbe` — cbpack XRPUSDT 1h params={"slice_from": "2025-06-15T05:40:00+00:00", "slice_to": "2026-02-13T13:20:00+00:00"}
- `814c80675d570aae` — cbpack SOLUSDT 1h params={}
- `862cc40167c27230` — cbpack SOLUSDT 5m params={}
- `872ee427d61e4880` — cbpack ETHUSDT 1m params={}
- `898b13b65e1deb27` — cbpack SUIUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `908481a873cf8113` — cbpack XRPUSDT 15m params={}
- `92a62a766d246281` — cbpack JUPUSDT 1h params={"slice_from": "2024-10-15T13:00:00+00:00", "slice_to": "2025-06-15T20:40:00+00:00"}
- `939b1368132ceb08` — cbpack BTCUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `940f7599148758a2` — cbpack SOLUSDT 1h params={"ids": "S10", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `95555245d5353174` — cbpack XRPUSDT 1h params={"slice_from": "2024-10-14T22:00:00+00:00", "slice_to": "2025-06-15T05:40:00+00:00"}
- `9840c3069c15f837` — cbpack XRPUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `99434312424041b2` — cbpack ETHUSDT 1h params={}
- `9c7dd1925b43ce50` — cbpack HYPEUSDT 15m params={"ids": "S07", "mode": "wf", "test_bars": 2880, "train_bars": 8640}
- `9eb69b6dece418a5` — cbpack XRPUSDT 1h params={"slice_from": "2026-02-13T13:20:00+00:00", "slice_to": "2026-10-14T21:00:00+00:00"}
- `9ed7a880c34f36c0` — cbpack SOLUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `9fde16a7db05ee9e` — cbpack HYPEUSDT 15m params={"ids": "S07", "mode": "wf", "test_bars": 8640, "train_bars": 17280}
- `9ffb987b7bc94841` — cbpack HYPEUSDT 15m params={"slice_from": "2025-05-30T10:30:00+00:00", "slice_to": "2025-11-14T03:30:00+00:00"}
- `a1dd7680e1a5f6e5` — cbpack XRPUSDT 15m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `a30083333490d945` — cbpack XRPUSDT 1h params={}
- `a490560fc87080c7` — cbpack JUPUSDT 15m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `ac4ff6d3a465a268` — cbpack HYPEUSDT 15m params={}
- `b20ab929a0f760e9` — cbpack HYPEUSDT 1h params={}
- `b4b13fe5a6120e68` — cbpack BTCUSDT 1h params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `b54c2bef8a8c4489` — cbpack SOLUSDT 1h params={"fee_bps": 6.0, "slippage_bps": 5.0}
- `b5e27ec2b2e3ee33` — cbpack XRPUSDT 1h params={"ids": "S10,S02", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `b653c5b4b5cf89ae` — cbpack ETHUSDT 1h params={"fee_bps": 6.0, "slippage_bps": 5.0}
- `b76b478cae5f1048` — cbpack JUPUSDT 5m params={}
- `bbe07a17afe31e37` — cbpack HYPEUSDT 15m params={"ids": "S07", "mode": "wf", "test_bars": 5760, "train_bars": 11520}
- `bd4ff19eca389209` — cbpack HYPEUSDT 1h params={"slice_from": "2025-11-14T02:40:00+00:00", "slice_to": "2026-04-30T19:20:00+00:00"}
- `becc4db47573953d` — cbpack SOLUSDT 1h params={"ids": "S10", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `c0075a20867a8331` — cbpack SOLUSDT 5m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `c0fad1ec6ad653d6` — cbpack JUPUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 720, "train_bars": 2160}
- `c3e2aaf6afcd2422` — cbpack JUPUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `c74dccf1ea0ed3b4` — cbpack SOLUSDT 1h params={"slice_from": "2024-10-14T22:00:00+00:00", "slice_to": "2025-06-15T05:40:00+00:00"}
- `ca03a176425b8d76` — cbpack SOLUSDT 1h params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `cf001b8ff0148c27` — cbpack SUIUSDT 1h params={}
- `cf055c3ff45a9c9a` — cbpack JUPUSDT 1h params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `d2084bee13ee07ea` — cbpack JUPUSDT 1m params={}
- `d78a3306bb576fc3` — cbpack SUIUSDT 1h params={"fee_bps": 6.0, "slippage_bps": 5.0}
- `da9c7be30c2fcb23` — cbpack JUPUSDT 1h params={"slice_from": "2025-06-15T20:40:00+00:00", "slice_to": "2026-02-14T04:20:00+00:00"}
- `dd4af52ddf5a6a70` — cbpack BTCUSDT 1h params={"slice_from": "2024-10-14T22:00:00+00:00", "slice_to": "2025-06-15T05:40:00+00:00"}
- `dd8b4389c96acb4a` — cbpack SOLUSDT 1m params={}
- `dec8c4aff3503bcb` — cbpack SOLUSDT 1h params={"slice_from": "2026-02-13T13:20:00+00:00", "slice_to": "2026-10-14T21:00:00+00:00"}
- `e383f966e0b38516` — cbpack XRPUSDT 1h params={"fee_bps": 6.0, "slippage_bps": 5.0}
- `e513b30cdeca0436` — cbpack HYPEUSDT 1h params={"fee_bps": 6.0, "slippage_bps": 5.0}
- `e62205adc5cc1a34` — cbpack SUIUSDT 15m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `e8b50fd959ce2e9b` — cbpack HYPEUSDT 15m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `e99c833fecd633f4` — cbpack SOLUSDT 1h params={"ids": "S10", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `e9c756adeb09334d` — cbpack SUIUSDT 1h params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `edbefc5b2592d29c` — cbpack ETHUSDT 1h params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `ef3c6a9bbda4bd71` — cbpack XRPUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `f0a1028e69644efa` — cbpack SUIUSDT 1h params={"slice_from": "2025-06-15T05:40:00+00:00", "slice_to": "2026-02-13T13:20:00+00:00"}
- `f19065db840fbacb` — cbpack JUPUSDT 1h params={"fee_bps": 6.0, "slippage_bps": 5.0}
- `f1e8381a7133e767` — cbpack SOLUSDT 15m params={"fee_bps": 0.0, "slippage_bps": 0.0}
- `f3440cb869afd3dc` — cbpack HYPEUSDT 1m params={}
- `f4f39e13e9d3debe` — cbpack BTCUSDT 1h params={"slice_from": "2026-02-13T13:20:00+00:00", "slice_to": "2026-10-14T21:00:00+00:00"}
- `f7798500d5b0239e` — cbpack SOLUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `f96061efa23717a4` — cbpack ETHUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 1440, "train_bars": 2880}
- `fb307b15a0d76c43` — cbpack HYPEUSDT 15m params={"slice_from": "2026-04-30T20:30:00+00:00", "slice_to": "2026-10-15T13:30:00+00:00"}
- `fe71b471b85bde19` — cbpack XRPUSDT 1h params={"ids": "S02,S10", "mode": "wf", "test_bars": 2160, "train_bars": 4320}
- `ff0e9b3c4d3caa3f` — cbpack SUIUSDT 1h params={"slice_from": "2026-02-13T13:20:00+00:00", "slice_to": "2026-10-14T21:00:00+00:00"}

(111 artifacts.)

